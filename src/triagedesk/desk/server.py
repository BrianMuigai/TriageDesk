"""The ONE desk presentation bridge (UX-02, UX-03, UX-04; D10-01…D10-19).

This module is the phase's thin bridge (D10-02): it validates the vitals form through the
ONE ``CaseInput`` schema (D10-13), runs the case to the approval gate over the shipped
pause plumbing (``durable.run_to_gate``), renders the graph's own typed outputs as a
**suggestion** card with its adjacent citations and the attributed evidence grounding it
(D10-05/D10-06/D10-07), and resumes a paused thread with a named human decision through
``durable.approval_decision`` + ``durable.resume_thread`` (D10-11).

It is **presentation-only** (D10-04): it holds no scoring, routing or gate logic, and it
never re-derives a colour, a citation, a target time or a confidence value (D10-02/D10-07).
The only mapping it owns is presentation — a substrate colour string to a CSS class name.
The surface can never commit on its own (D10-12): the only route to a queue row is the
resumed ``approval_gate`` interrupt through the gated ``commit_priority`` tool; this package's
import graph — its static ``import`` statements AND its literal-argument
``importlib.import_module`` / ``__import__`` calls — reaches neither the queue writer nor the
module that hosts that tool. A *string-built* dynamic attribute access (e.g.
``getattr(mod, "commit_" + "priority")``) is not statically provable, so the guard's claim is
deliberately scoped to the literal import graph it scans, never asserted beyond it (WR-01). It
binds loopback only (D10-03), serves a fixed two-name asset allowlist, escapes every rendered
string, and adds no dependency (D10-16).

The uncertainty signal (UX-01, D10-09/D10-17) is read from the graph's typed channels —
``no_match`` OR ``confidence.deferral`` — never from a free-text reason, ``evidence.no_match``
or ``missing_vitals`` alone. Because Phase 8 routes any ``no_match``/deferral to a safe
terminal (D8-11/D8-12), a deferred case renders the loud banner plus a **read-only** card and
NO gate, while a committable case renders the card plus the real gate and no banner.

This module is now the HTTP layer plus the facade over the split presentation modules
(``copy``/``markup``/``assets``/``pipeline``/``forms``/``card``/``gate``/``views``): it keeps
the request handler, the loopback guards and the graph-runner re-exports, and imports every
moved name so ``triagedesk.desk.server`` stays the seam the CLI and the suite reach.
"""

from __future__ import annotations

import asyncio
import ipaddress
import secrets
import string
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, get_args
from urllib.parse import parse_qs

from pydantic import ValidationError

from triagedesk.core.rules import get_tews
from triagedesk.core.schema import CaseInput
from triagedesk.desk.assets import _ASSETS, STATIC_DIR
from triagedesk.desk.copy import (
    _BANNER_HEADLINE,
    _BANNER_LOW_CONFIDENCE_BODY,
    _BANNER_NO_MATCH_BODY,
    _CARD_FRAMING,
    _DEFERRED_COPY,
    _DISMISSED_COPY,
    _EMPTY_BODY,
    _EMPTY_HEADING,
    _ESCALATED_COPY,
    _FAILURE_COPY,
    _NO_EVIDENCE_LINE,
    _NO_THREAD_COPY,
    _READ_ONLY_FRAMING,
    _RECOVERY_COPY,
    _SCHEMA_HINT,
    _TIMEOUT_COPY,
    _UNREACHED_COPY,
)
from triagedesk.desk.markup import _escaped
from triagedesk.desk.pipeline import decide, submit_case
from triagedesk.durable import DurableError, PausedRun
from triagedesk.graph.build import CHECKPOINTS_DB_PATH

# The checkbox values that read as "set". Deliberately excludes the bare word a data file
# might also carry, so the guard's exact-match scan is never tripped.
_TRUTHY = frozenset({"true", "on", "1"})

# The form field carrying the per-server CSRF token (WR-01). The token is minted once per
# server on ``GET /`` and required on every POST, so a cross-origin page cannot satisfy it.
_CSRF_FIELD = "csrf_token"

# The host names the surface answers to beyond a loopback IP (WR-02). ``127.0.0.0/8`` and
# ``::1`` are recognised by ``ipaddress.is_loopback``; this set only adds the one name that is
# not an IP literal. A request whose ``Host`` is not loopback is refused before dispatch, so a
# DNS-rebinding page — same-origin with the surface and able to read the token — cannot satisfy
# the ``Origin`` check with a matching foreign ``Host``.
_LOOPBACK_HOSTNAMES = frozenset({"localhost"})

# The largest POST body the surface will read. A form is a few hundred bytes; an unbounded
# ``Content-Length`` would otherwise pin the request thread (IN-01). A body above this cap is
# refused with the documented failure panel, never read.
_MAX_BODY_BYTES = 64 * 1024

# The vitals form's field order and human labels (presentation only). Each control's kind,
# plausible range and select options are read from the ONE ``CaseInput`` schema at render
# time, so the form can never offer a range or an option the schema would reject and no
# bound is restated (CONVENTIONS §1, D10-13).
_VITALS_LAYOUT: tuple[tuple[str, str], ...] = (
    ("age_years", "Age (years)"),
    ("age_months", "Age (months)"),
    ("age_ambiguous", "Age unclear"),
    ("height_cm", "Height (cm)"),
    ("respiratory_rate", "Breathing rate"),
    ("heart_rate", "Heart rate"),
    ("systolic_bp", "Systolic BP"),
    ("diastolic_bp", "Diastolic BP"),
    ("temperature_c", "Temperature (°C)"),
    ("spo2", "Oxygen saturation"),
    ("mobility", "Mobility"),
    ("avpu", "Alertness (AVPU)"),
    ("trauma", "Trauma"),
    ("complaint", "Complaint"),
)


def form_to_case(form: Mapping[str, str]) -> CaseInput:
    """Build and validate a :class:`CaseInput` from the posted vitals form (D10-13).

    An absent or empty optional numeric/enum field maps to ``None`` (never ``""`` or ``0``);
    an absent ``trauma`` checkbox maps to ``None`` (never ``False``); ``age_ambiguous``
    defaults to ``False``; ``complaint`` defaults to ``""``. Validation is the ONE
    ``CaseInput.model_validate`` — the schema is the only validation *and coercion* rule. A
    numeric field's raw string is handed to the schema as-is (no ``int()``/``float()``
    pre-cast here), so a browser-reachable value the schema rejects (e.g. ``1e2`` in a
    ``type=number`` field) yields the schema's own :class:`pydantic.ValidationError` — which
    the handler renders beside the field — rather than a bare ``ValueError`` escaping the
    request handler.
    """

    def _number(key: str) -> Any:
        """Pass the raw string through; the ONE schema coerces and validates it (D10-13)."""
        raw = str(form.get(key, "")).strip()
        return raw or None

    def _choice(key: str) -> str | None:
        raw = str(form.get(key, "")).strip()
        return raw or None

    def _optional_flag(key: str) -> bool | None:
        if key not in form or str(form.get(key, "")).strip() == "":
            return None
        return str(form[key]).strip().lower() in _TRUTHY

    payload: dict[str, Any] = {
        "age_years": _number("age_years"),
        "age_months": _number("age_months"),
        "age_ambiguous": str(form.get("age_ambiguous", "")).strip().lower() in _TRUTHY,
        "height_cm": _number("height_cm"),
        "respiratory_rate": _number("respiratory_rate"),
        "heart_rate": _number("heart_rate"),
        "systolic_bp": _number("systolic_bp"),
        "diastolic_bp": _number("diastolic_bp"),
        "temperature_c": _number("temperature_c"),
        "spo2": _number("spo2"),
        "mobility": _choice("mobility"),
        "avpu": _choice("avpu"),
        "trauma": _optional_flag("trauma"),
        "complaint": str(form.get("complaint", "")) or "",
    }
    return CaseInput.model_validate(payload)


def banner_trigger(state: Mapping[str, Any]) -> str | None:
    """The ONE banner rule (D10-09): the typed uncertainty signal, never a heuristic.

    Returns ``"no_match"`` when the state's ``no_match`` channel is true, else ``"deferral"``
    when the ``confidence`` channel is present and deferring, else ``None``. It deliberately
    does NOT consult ``evidence.no_match`` (a different fact: "no excerpt matched"), NOT
    ``missing_vitals`` alone (the recovery signal's job), and NOT any free-text reason string.
    """
    if bool(state.get("no_match")):
        return "no_match"
    confidence = state.get("confidence")
    if confidence is not None and bool(getattr(confidence, "deferral", False)):
        return "deferral"
    return None


def terminal_kind(state: Mapping[str, Any]) -> str | None:
    """Select the terminal copy from the graph's typed channels (never a string heuristic).

    ``"deferred"`` when the ``confidence`` channel defers (checked FIRST — a deferral always
    routes to ``escalate``/``request_missing_info``, so an escalated state may also carry a
    deferral); else ``"escalated"`` when the ``escalation`` channel is present; else
    ``"recovery"`` when the ``recovery`` channel is present; else ``None``. The kind is never
    inferred from ``Escalation.reason`` (a free-text field that varies).
    """
    confidence = state.get("confidence")
    if confidence is not None and bool(getattr(confidence, "deferral", False)):
        return "deferred"
    if state.get("escalation") is not None:
        return "escalated"
    if state.get("recovery") is not None:
        return "recovery"
    return None


def editable_colours() -> list[str]:
    """The gate's own accepted colour set, in a stable order (D10-18).

    Derived from ``{band.colour for band in get_tews().tews_to_colour}`` — the SAME expression
    ``ApprovalToken`` validates ``final_colour`` against — so the surface can never offer a
    decision the gate would refuse. Never a hard-coded list; never a colour that exists only
    in ``target_times``.
    """
    return sorted({band.colour for band in get_tews().tews_to_colour})


def _colour_class(colour: str) -> str:
    """Map a substrate colour string to its CSS swatch class (a lookup, never a computation).

    The colour NAMES live only in ``styles.css`` (an asset the no-duplicated-SATS guard does
    not scan), so no SATS colour literal enters Python.
    """
    return f"colour-{colour.lower()}"


def _panel(copy: str, kind: str) -> str:
    """Render one state panel — the single surface for a non-card state (UI-SPEC).

    The panel escapes its own copy, so every caller passes RAW text and there is exactly one
    escaping rule for a panel (the sibling of :func:`_error_panel`); a caller that passed
    dynamic text straight through can no longer leak markup.
    """
    return (
        f'<section class="state-panel state-{kind}" role="status">'
        f"<p>{_escaped(copy)}</p></section>"
    )


def _banner_html(trigger: str) -> str:
    """Render the loud uncertainty banner with a trigger-conditional body (D10-09).

    The headline is verbatim from UX-01; the body is the no-match body when the trigger is
    ``"no_match"`` and the low-confidence body when it is ``"deferral"`` — so the banner never
    asserts a fact its trigger did not establish.
    """
    body = _BANNER_NO_MATCH_BODY if trigger == "no_match" else _BANNER_LOW_CONFIDENCE_BODY
    return (
        f'<p class="banner-headline">{_escaped(_BANNER_HEADLINE)}</p>'
        f'<p class="banner-body">{_escaped(body)}</p>'
    )


def _csrf_field(token: str | None) -> str:
    """Render the per-server CSRF token as a hidden field (WR-01), or nothing without one.

    Every rendered form carries this field, so a same-origin submission from the surface always
    satisfies the POST check while a cross-origin page (which cannot read the token) cannot.
    """
    if not token:
        return ""
    return f'<input type="hidden" name="{_CSRF_FIELD}" value="{_escaped(token)}">'


def _base_annotation(name: str) -> Any:
    """The non-``None`` annotation of a ``CaseInput`` field (unwrapping ``| None``)."""
    annotation = CaseInput.model_fields[name].annotation
    non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
    return non_none[0] if non_none else annotation


def _annotation_kind(name: str) -> str:
    """Classify a ``CaseInput`` field into the form control it needs (from the schema)."""
    base = _base_annotation(name)
    if base is bool:
        return "checkbox"
    if base is int:
        return "int"
    if base is float:
        return "float"
    if get_args(base):  # a Literal[...] enum field
        return "select"
    return "text"


def _enum_values(name: str) -> list[str]:
    """The ``Literal`` options of an enum field, read from the schema (never restated)."""
    return [str(value) for value in get_args(_base_annotation(name))]


def _bounds(name: str) -> tuple[Any, Any]:
    """The ``(ge, le)`` plausible bounds of a numeric field, read from its ``FieldInfo``."""
    metadata = CaseInput.model_fields[name].metadata
    low = next((getattr(m, "ge", None) for m in metadata if hasattr(m, "ge")), None)
    high = next((getattr(m, "le", None) for m in metadata if hasattr(m, "le")), None)
    return low, high


def _fmt_bound(value: Any) -> str:
    """Render a numeric bound without a trailing ``.0`` (so ``30.0`` -> ``30``)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _option_label(value: str) -> str:
    """The human label for a schema enum value (``with_help`` -> ``With help``)."""
    return value.replace("_", " ").capitalize()


def _vitals_field(
    name: str,
    label: str,
    form: Mapping[str, str],
    field_error: tuple[str, str] | None = None,
) -> str:
    """Render one vitals field, repopulated from *form* and bounded by the schema (D10-13).

    The controls are generated from the ONE ``CaseInput`` schema: a numeric field's ``min``/
    ``max`` come from its own ``FieldInfo`` bounds and a select's options from its ``Literal``,
    so no range or option is restated in markup and the form can never offer a value the schema
    would reject.

    When *field_error* names this field, the control is marked ``aria-invalid`` and the ONE
    schema's own rejection renders inside this ``.field`` — the UI-SPEC ``## UI Considerations``
    requirement that an invalid field's message appear **beside that field**, which is what makes
    the mandated "Check the highlighted field" copy literally true.
    """
    kind = _annotation_kind(name)
    raw = str(form.get(name, ""))
    checked_layout = kind == "checkbox"
    if kind in ("int", "float"):
        low, high = _bounds(name)
        step = "1" if kind == "int" else "0.1"
        mode = ' inputmode="numeric"' if kind == "int" else ""
        control = (
            f'<input id="{name}" name="{name}" type="number"{mode} step="{step}" '
            f'min="{_escaped(_fmt_bound(low))}" max="{_escaped(_fmt_bound(high))}" '
            f'value="{_escaped(raw.strip())}">'
        )
    elif kind == "checkbox":
        checked = " checked" if raw.strip().lower() in _TRUTHY else ""
        # A checkbox alone cannot express False: an unchecked box is not a successful control,
        # so the browser omits the key entirely and the ONE schema reads the field as absent
        # (``None``). For a scored vital (``trauma``) that omission is the recovery terminal, so
        # the common "no trauma" patient could never reach the gate (CR-01). Pair the checkbox
        # with a hidden ``false``: the checkbox MUST come first, because the form data set is
        # built in tree order and the handler keeps ``parse_qs(...)[key][0]`` — a checked box
        # yields ``["true", "false"]`` -> True while an unchecked box yields ``["false"]`` ->
        # False. The hidden input carries no ``id`` (the checkbox owns the ``<label for>``).
        control = (
            f'<input id="{name}" name="{name}" type="checkbox" value="true"{checked}>'
            f'<input type="hidden" name="{name}" value="false">'
        )
    elif kind == "select":
        options = "".join(
            f'<option value="{_escaped(value)}"'
            f'{" selected" if raw.strip() == value else ""}>'
            f"{_escaped(_option_label(value))}</option>"
            for value in _enum_values(name)
        )
        control = (
            f'<select id="{name}" name="{name}">'
            f'<option value="">—</option>{options}</select>'
        )
    else:
        control = f'<textarea id="{name}" name="{name}" rows="3">{_escaped(raw)}</textarea>'

    label_html = f'<label for="{name}">{_escaped(label)}</label>'
    classes = "field field-check" if checked_layout else "field"
    if field_error is not None and field_error[0] == name:
        classes += " field-error"
        # Mark the control itself invalid for assistive tech (the first ``>`` closes the
        # opening tag), then render the ONE schema's own message beside it inside this field.
        control = control.replace(">", ' aria-invalid="true">', 1)
        message = (
            f'<p class="field-error-message" role="alert">{_escaped(field_error[1])}</p>'
        )
    else:
        message = ""
    inner = f"{control}{label_html}" if checked_layout else f"{label_html}{control}"
    return f'<div class="{classes}">{inner}{message}</div>'


def _vitals_fields(form: Mapping[str, str], field_error: tuple[str, str] | None = None) -> str:
    """Render the vitals form's field block, repopulated from *form* (WR-03).

    The controls are generated from the ONE ``CaseInput`` schema (D10-13): a numeric
    field's ``min``/``max`` come from its own ``FieldInfo`` bounds and a select's options
    from its ``Literal``, so no range or option is restated in markup and the form can
    never offer a value the schema would reject. The submitted values are rendered back,
    so a rejected submission never discards what the nurse typed. *field_error* names the
    offending field so its message renders beside it (never only below the form).
    """
    return "".join(
        _vitals_field(name, label, form, field_error) for name, label in _VITALS_LAYOUT
    )


def _why_vitals_rows(payload: Mapping[str, Any]) -> str:
    """One row per ``triggered_rules`` entry: its ``detail`` beside its own ``citation``.

    The baseline row is already one such entry (``core/scorer.py`` emits a ``tews_baseline``
    rule for the rule-less TEWS-0 case), so the card never reads the substrate's baseline
    citation directly (D10-06).
    """
    rules = payload.get("triggered_rules") or []
    return "".join(
        f'<li>{_escaped(rule.get("detail", ""))} '
        f'<span class="citation">{_escaped(rule.get("citation", ""))}</span></li>'
        for rule in rules
    )


def _evidence_rows(evidence: Any) -> str:
    """One ranked row per ``evidence.passages`` entry, or the verbatim no-evidence line.

    The evidence list is read from the paused state snapshot's ``evidence`` channel (the
    interrupt payload omits it) and is capped by the substrate's own ``MAX_PASSAGES``, never
    by the surface.
    """
    passages = (
        list(getattr(evidence, "passages", None) or []) if evidence is not None else []
    )
    if not passages:
        return f'<li class="no-evidence">{_escaped(_NO_EVIDENCE_LINE)}</li>'
    return "".join(
        f'<li><span class="evidence-label">{_escaped(passage.label)}</span> '
        f'<span class="citation">{_escaped(passage.citation)}</span></li>'
        for passage in passages
    )


def _card_html(
    payload: Mapping[str, Any], evidence: Any = None, *, read_only: bool = False
) -> str:
    """Render the priority card from the graph's own outputs (D10-02/D10-05…D10-08).

    Every value is read from the payload (or a payload built from the state snapshot) — the
    colour, its target, each fired rule's ``detail`` beside its adjacent citation, the
    evidence grounding it, the missing vitals, the second-look flag and the case id — and
    re-derived nowhere. The colour is rendered with its name as text (D10-08). ``read_only``
    swaps the framing line for the deferred/read-only card (D10-17); the card itself is the
    same presentation in both cases.
    """
    colour = str(payload.get("colour") or "")
    target = str(payload.get("target") or "")
    case_id = str(payload.get("case_id") or "")
    missing = payload.get("missing_vitals") or []
    second_look = payload.get("second_look")

    rows = _why_vitals_rows(payload)
    evidence_rows = _evidence_rows(evidence)
    missing_text = ", ".join(str(item) for item in missing) if missing else "None"
    if second_look:
        flagged = bool(second_look.get("flag"))
        deteriorations = second_look.get("deteriorations") or []
        second_text = (
            "Flagged: " + ", ".join(str(item) for item in deteriorations)
            if flagged
            else "Not flagged"
        )
    else:
        second_text = "—"

    framing = _READ_ONLY_FRAMING if read_only else _CARD_FRAMING
    return (
        '<section class="priority-card" aria-labelledby="card-heading">'
        '<h2 id="card-heading">Suggested priority</h2>'
        f'<p class="framing">{_escaped(framing)}</p>'
        f'<div class="colour-block {_escaped(_colour_class(colour))}">'
        f'<span class="colour-name">{_escaped(colour)}</span></div>'
        f'<p><span class="label">Suggested colour:</span> '
        f'<span class="value">{_escaped(colour)}</span></p>'
        f'<p><span class="label">Target time:</span> '
        f'<span class="value">{_escaped(target)}</span></p>'
        "<h3>Why these vitals:</h3>"
        f'<ul class="why-vitals-list">{rows}</ul>'
        "<h3>Evidence from the SATS knowledge base:</h3>"
        f'<ul class="evidence-list">{evidence_rows}</ul>'
        f'<p><span class="label">Not recorded:</span> '
        f'<span class="value">{_escaped(missing_text)}</span></p>'
        f'<p><span class="label">Second look (serial vitals):</span> '
        f'<span class="value">{_escaped(second_text)}</span></p>'
        f'<p><span class="label">Case:</span> '
        f'<span class="value">{_escaped(case_id)}</span></p>'
        "</section>"
    )


def _card_payload_from_state(state: Mapping[str, Any], thread_id: str) -> dict[str, Any]:
    """Build the card's payload-shaped facts from a paused STATE snapshot (D10-17/D10-19).

    The interrupt payload is absent on the deferred and repeat-submission paths, so the card
    facts are read from the state's typed ``priority``/``second_look`` objects. Nothing is
    re-derived: ``case_id`` is the paused thread id (the ONE content-derived id).
    """
    priority = state.get("priority")
    second_look = state.get("second_look")
    rules = (
        [rule.model_dump(mode="json") for rule in priority.triggered_rules]
        if priority is not None
        else []
    )
    return {
        "case_id": thread_id,
        "colour": getattr(priority, "colour", None),
        "target": getattr(priority, "target", None),
        "triggered_rules": rules,
        "missing_vitals": list(getattr(priority, "missing_vitals", None) or []),
        "second_look": (
            second_look.model_dump(mode="json") if second_look is not None else None
        ),
    }


def _gate_html(thread_id: str, csrf_token: str | None = None) -> str:
    """Render the approval gate, carrying the paused thread identity (D10-11/D10-18).

    The hidden ``thread_id`` value is the paused thread id — the ONE content-derived id the
    ``/decision`` POST returns to :func:`decide`. The hidden ``csrf_token`` is the per-server
    secret a cross-origin page cannot supply (WR-01). The three actions are labelled buttons
    (never colour-only controls); the edit control is a radio group built from
    :func:`editable_colours` with NO value preselected, so a missing choice is a rejected
    decision rather than a silent default. The gate-scoped timeout panel is inert until the
    inline client timer reveals it on expiry (D10-10); no decision is ever preselected.

    ``Your name``/``Your role`` carry a client-side ``required`` affordance so an approve/edit
    is refused before the round-trip when the identity is blank; the dismiss action carries
    ``formnovalidate`` so it stays available without an identity (dismiss commits nothing). The
    server still enforces non-blank (whitespace-only) identity through ``durable`` — the
    affordance is a cue, never the enforcement.
    """
    radios = "".join(
        '<label class="colour-choice">'
        f'<input type="radio" name="colour" value="{_escaped(colour)}">'
        f'<span class="colour-choice-name">{_escaped(colour)}</span></label>'
        for colour in editable_colours()
    )
    return (
        '<section class="approval-gate" aria-labelledby="gate-heading">'
        '<h2 id="gate-heading">Your decision</h2>'
        '<form id="approval-gate-form" method="post" action="/decision">'
        f"{_csrf_field(csrf_token)}"
        f'<input type="hidden" name="thread_id" value="{_escaped(thread_id)}">'
        '<div class="field"><label for="approver-name">Your name</label>'
        '<input id="approver-name" name="name" type="text" autocomplete="off" required></div>'
        '<div class="field"><label for="approver-role">Your role</label>'
        '<input id="approver-role" name="role" type="text" autocomplete="off" required></div>'
        '<fieldset class="field colour-fieldset"><legend>Choose the priority colour</legend>'
        f'<div class="colour-choices">{radios}</div></fieldset>'
        '<div class="gate-actions">'
        '<button type="submit" name="decision" value="approve" class="primary">'
        "Approve suggestion</button>"
        '<button type="submit" name="decision" value="edit">Edit colour</button>'
        '<button type="submit" name="decision" value="dismiss" formnovalidate>'
        "Dismiss (commit nothing)</button>"
        "</div></form></section>"
        f'<section id="gate-timeout" class="state-panel state-muted" hidden>'
        f"<p>{_escaped(_TIMEOUT_COPY)}</p></section>"
    )


def _terminal_panel(state: Mapping[str, Any]) -> str:
    """Select the terminal copy from the graph's typed channels (never a string heuristic)."""
    kind = terminal_kind(state)
    if kind == "deferred":
        return _panel(_DEFERRED_COPY, "muted")
    if kind == "escalated":
        return _panel(_ESCALATED_COPY, "muted")
    if kind == "recovery":
        return _panel(_RECOVERY_COPY, "muted")
    return _panel(_UNREACHED_COPY, "muted")


def _empty_view() -> dict[str, str]:
    """The view with no case submitted — the empty state, no card and no gate."""
    return {
        "state_panel": (
            '<section class="state-panel state-empty" role="status">'
            f"<h2>{_EMPTY_HEADING}</h2><p>{_EMPTY_BODY}</p></section>"
        ),
        "banner": "",
        "card": "",
        "gate": "",
    }


def _paused_view(paused: PausedRun, csrf_token: str | None = None) -> dict[str, str]:
    """The view for a run that paused at the gate, deferred, escalated, or repeated (D10-17).

    The banner fires only from :func:`banner_trigger`; a committable case (paused at the gate)
    always has both triggers false, so it renders the card plus the real gate and no banner.
    A deferred case renders the banner plus a READ-ONLY card and NO gate; an escalated or
    recovery case renders its terminal copy with no card and no gate. A repeat submission
    (``existed=True``) is re-rendered from the snapshot: a deferred repeat stays a deferred
    terminal, while a committable repeat re-renders the card and gate with the SAME thread id
    (D10-19). Every gate carries the per-server CSRF token (WR-01).
    """
    state = paused.result
    trigger = banner_trigger(state)
    banner = _banner_html(trigger) if trigger is not None else ""
    evidence = state.get("evidence")

    if paused.paused and paused.payload is not None:
        return {
            "state_panel": "",
            "banner": banner,
            "card": _card_html(paused.payload, evidence),
            "gate": _gate_html(str(paused.payload.get("case_id") or ""), csrf_token),
        }

    kind = terminal_kind(state)
    if kind is not None:
        card = (
            _card_html(
                _card_payload_from_state(state, paused.thread_id),
                evidence,
                read_only=True,
            )
            if kind == "deferred"
            else ""
        )
        return {
            "state_panel": _terminal_panel(state),
            "banner": banner,
            "card": card,
            "gate": "",
        }

    # ``existed=True`` with no terminal: a repeat submission whose thread has a pending gate
    # (D10-19). A thread that already committed shows the gate's own outcome instead of a
    # fresh gate — the surface restates no gate logic.
    commit = state.get("commit_result")
    if commit is not None:
        committed = bool(getattr(commit, "committed", False))
        reason = getattr(commit, "reason", None) or _FAILURE_COPY
        return {
            "state_panel": _panel(reason, "success" if committed else "error"),
            "banner": banner,
            "card": "",
            "gate": "",
        }
    if paused.existed:
        return {
            "state_panel": "",
            "banner": banner,
            "card": _card_html(_card_payload_from_state(state, paused.thread_id), evidence),
            "gate": _gate_html(paused.thread_id, csrf_token),
        }
    return {
        "state_panel": _terminal_panel(state),
        "banner": banner,
        "card": "",
        "gate": "",
    }


def _decision_view(result: Mapping[str, Any], form: Mapping[str, str]) -> dict[str, str]:
    """The view after a gate decision was resumed — committed, dismissed, or refused."""
    decision = str(form.get("decision", "")).strip()
    name = str(form.get("name", ""))
    role = str(form.get("role", ""))
    commit = result.get("commit_result")

    if decision == "dismiss":
        panel = _panel(_DISMISSED_COPY, "muted")
    elif commit is not None and getattr(commit, "committed", False):
        # The position comes off the typed CommitResult channel — never parsed from
        # the free-text reason (the module reads typed channels only). A CommitResult
        # built without the field (older checkpoint state, the eval stub) falls back
        # to the position-free copy.
        position = getattr(commit, "position", None)
        suffix = (
            f"committed to the queue at position {position}."
            if position is not None
            else "committed to the queue."
        )
        if decision == "edit":
            copy = f"Edited to {form.get('colour', '')} by {name} ({role}) — {suffix}"
        else:
            copy = f"Approved by {name} ({role}) — {suffix}"
        panel = _panel(copy, "success")
    else:
        reason = getattr(commit, "reason", None) or _FAILURE_COPY
        panel = _panel(reason, "error")

    return {
        "state_panel": panel,
        "banner": "",
        "card": "",
        "gate": "",
    }


def _error_panel(message: str) -> str:
    """The error view — a failure leaves the decision unresolved; a failure is never an approve."""
    return _panel(message, "error")


def _render(
    view: Mapping[str, str],
    form: Mapping[str, str],
    csrf_token: str | None = None,
    field_error: tuple[str, str] | None = None,
) -> str:
    """Substitute the server-rendered regions into the hand-authored page (string.Template).

    ``string.Template`` (not ``str.format``) is used because the markup carries CSS braces; the
    page's only ``$`` characters are its placeholders. The vitals field block is rendered
    from *form* (the submitted values), so a rejected submission repopulates the form and — when
    *field_error* names the offending field — renders the schema's own message beside it. The
    ``csrf_field`` region carries the per-server token into the vitals form (WR-01).
    """
    template = string.Template((STATIC_DIR / "index.html").read_text(encoding="utf-8"))
    return template.substitute(
        vitals_fields=_vitals_fields(form, field_error),
        csrf_field=_csrf_field(csrf_token),
        state_panel=view["state_panel"],
        banner=view["banner"],
        card=view["card"],
        gate=view["gate"],
    )


def render_state(
    paused: PausedRun | None = None,
    *,
    result: Mapping[str, Any] | None = None,
    error: str | None = None,
    field_error: tuple[str, str] | None = None,
    form_values: Mapping[str, str] | None = None,
    csrf_token: str | None = None,
) -> str:
    """Render the page for one state: empty, paused card+gate, terminal, decision, or error.

    With no case submitted it renders the quickstart panel and the empty vitals form with the
    ``No case yet`` heading and body and NO ``priority-card`` or ``approval-gate`` region. On
    the committable path (``paused is True``) it renders the card plus the gate and no banner.
    *error* is a server/graph failure and renders in the state panel (the ``state-panel`` is the
    single surface for that copy). *field_error* is a schema rejection — ``(field, message)`` —
    and renders beside the offending field instead, so the mandated "Check the highlighted field"
    copy is literally true (the UI-SPEC ``## UI Considerations`` ``error | vitals-form`` row).
    *csrf_token* is the per-server secret the rendered forms carry (WR-01); it is optional so a
    direct (non-request) render — a test or a proof — needs no server.
    """
    form = form_values or {}
    if result is not None:
        return _render(_decision_view(result, form), form, csrf_token)
    if paused is not None:
        return _render(_paused_view(paused, csrf_token), form, csrf_token)
    if error is not None:
        return _render(
            {
                "state_panel": _error_panel(error),
                "banner": "",
                "card": "",
                "gate": "",
            },
            form,
            csrf_token,
        )
    if field_error is not None:
        return _render(
            {"state_panel": "", "banner": "", "card": "", "gate": ""},
            form,
            csrf_token,
            field_error,
        )
    return _render(_empty_view(), form, csrf_token)


class DeskServer(ThreadingHTTPServer):
    """The desk bridge's threaded HTTP server, carrying the checkpoint file path.

    Safe by construction: the loopback guard runs in ``__init__`` (IN-04), so a direct
    ``DeskServer((host, port), DeskHandler)`` cannot bind a wildcard the way ``make_server``
    would refuse. The per-server CSRF token (WR-01) and the submission lock (IN-03) are minted
    here too, so every construction path — factory or direct — is protected identically.
    """

    db_path: Path
    csrf_token: str
    db_lock: threading.Lock

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler: type[BaseHTTPRequestHandler],
        *,
        allow_non_loopback: bool = False,
        bind_and_activate: bool = True,
    ) -> None:
        if not allow_non_loopback:
            _refuse_non_loopback(server_address[0])
        super().__init__(
            server_address, request_handler, bind_and_activate=bind_and_activate
        )
        # One token per server lifetime: minted before any request, so ``GET /`` always
        # renders the token the surface will require on the next POST (WR-01).
        self.csrf_token = secrets.token_urlsafe(32)
        # Serialise the checkpoint-touching submissions: each POST runs its own event loop
        # against the one SQLite file, so concurrent writes could contend for the lock (IN-03).
        self.db_lock = threading.Lock()


def _loopback_host(host_header: str) -> bool:
    """True when a ``Host`` header names loopback (WR-02).

    The port is deliberately ignored: a DNS-rebinding page reaches the real server port, so the
    port matches in the attack and cannot be the discriminator — the *hostname* is. The hostname
    is parsed by hand (the bracketed IPv6 form, else the part before the last colon) rather than
    by ``urlsplit``, which would silently accept a ``user@host`` userinfo trick; ``ipaddress``
    then accepts any ``127.0.0.0/8`` address and ``::1``. Anything else — a foreign name, a
    malformed header, an absent ``Host`` — is not loopback, so the request is refused before it
    can reach a commit path.
    """
    host = host_header.strip()
    if host.startswith("["):
        end = host.find("]")
        if end == -1:
            return False
        hostname = host[1:end]
    else:
        hostname = host.rsplit(":", 1)[0]
    if hostname.lower() in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


class DeskHandler(BaseHTTPRequestHandler):
    """The desk bridge's request handler — loopback only, allowlisted assets, escaped output."""

    server: DeskServer

    def _send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _page(self, **kwargs: Any) -> str:
        """Render a state with the per-server CSRF token threaded into the forms (WR-01)."""
        return render_state(csrf_token=self.server.csrf_token, **kwargs)

    def _host_ok(self) -> bool:
        """True only for a loopback ``Host`` header (WR-02).

        The ``Host`` header is client-controlled, so it can never be the trust anchor for
        "same origin": a DNS-rebinding page is same-origin with the surface and can read the
        token, then POST with a matching foreign ``Host``/``Origin``. Pinning the accepted host
        to loopback refuses that request before dispatch, which is what makes the ``Origin``
        comparison below meaningful.
        """
        return _loopback_host(self.headers.get("Host") or "")

    def _cross_origin(self) -> bool:
        """True when a present ``Origin`` header is not this surface's own origin (WR-01).

        A cross-origin page's POST carries the page's own ``Origin``, which cannot match the
        loopback ``Host`` — so the request is refused before it can reach a commit path. An
        absent ``Origin`` (a non-browser client) is not a cross-origin signal; the CSRF token
        is the defence there, and it is required on every POST regardless.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return False
        return origin != f"http://{self.headers.get('Host')}"

    def _csrf_ok(self, form: Mapping[str, str]) -> bool:
        """True when *form* carries the per-server CSRF token (WR-01), compared in constant time.

        Both sides are compared as UTF-8 **bytes**: ``compare_digest`` raises ``TypeError`` on a
        ``str`` carrying non-ASCII characters, and ``supplied`` is attacker-controlled
        (``parse_qs`` percent-decodes UTF-8), so a ``str`` comparison would let a single
        non-ASCII token crash the handler instead of rendering the failure panel. The token
        itself is ASCII (``token_urlsafe``), so encoding both sides is total and cannot raise.
        """
        supplied = str(form.get(_CSRF_FIELD, ""))
        return bool(supplied) and secrets.compare_digest(
            supplied.encode("utf-8"), self.server.csrf_token.encode("utf-8")
        )

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        """Render the page for ``/``; serve the CSS by allowlist; anything else is a 404.

        A non-loopback ``Host`` is refused with 403 (WR-02), so the token page is never served
        under a foreign host a DNS-rebinding page could read. ``/`` (and ``/index.html``) render
        the empty state through the ONE template rather than serving the raw file, so no
        unsubstituted placeholder is ever exposed. Only the CSS is served as raw bytes, and only
        when its name is in the fixed allowlist — no path is built from ``self.path``.
        """
        if not self._host_ok():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        path = self.path.split("?", 1)[0]
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        if name not in _ASSETS:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if name == "index.html":
            self._send_html(self._page())
            return
        body = (STATIC_DIR / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _ASSETS[name])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        """Dispatch ``/case`` and ``/decision`` over the ONE pause/resume plumbing.

        Three defences run before dispatch: a non-loopback ``Host`` renders the documented
        failure panel (WR-02), so a DNS-rebinding page cannot satisfy the origin check with a
        matching foreign ``Host``; a cross-origin ``Origin`` is refused with 403 (WR-01); and a
        POST missing the per-server CSRF token renders the same failure panel (WR-01). The
        header/body parse is guarded too: a malformed ``Content-Length`` (non-numeric, negative
        or above ``_MAX_BODY_BYTES``) or a body that is not valid UTF-8 renders that panel rather
        than crashing the handler, dropping the connection, or pinning the thread on a body that
        never arrives (IN-01).
        """
        if not self._host_ok():
            self._send_html(self._page(error=_FAILURE_COPY))
            return
        if self._cross_origin():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > _MAX_BODY_BYTES:
                raise ValueError("invalid Content-Length")
            raw = self.rfile.read(length).decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError):
            self._send_html(self._page(error=_FAILURE_COPY))
            return
        form = {
            key: values[0]
            for key, values in parse_qs(raw, keep_blank_values=True).items()
        }
        if not self._csrf_ok(form):
            self._send_html(self._page(error=_FAILURE_COPY))
            return
        path = self.path.split("?", 1)[0]
        if path == "/case":
            self._send_html(self._handle_case(form))
        elif path == "/decision":
            self._send_html(self._handle_decision(form))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_case(self, form: Mapping[str, str]) -> str:
        try:
            case = form_to_case(form)
        except ValidationError as exc:
            # A schema rejection renders BESIDE the offending field (the UI-SPEC ``## UI
            # Considerations`` ``error | vitals-form`` row), so the mandated "Check the
            # highlighted field" copy is literally true. A model-level error with no field
            # falls back to the error panel rather than mis-highlighting a field.
            field = _validation_field(exc)
            if field is None:
                return self._page(error=_validation_message(exc), form_values=form)
            return self._page(
                field_error=(field, _validation_message(exc)), form_values=form
            )
        except (TypeError, ValueError):
            # Defence in depth: any coercion failure that somehow bypassed the schema's own
            # validator is still reported, never an approve (the surface's stated contract).
            return self._page(error=_FAILURE_COPY, form_values=form)
        try:
            # The lock serialises submissions over the one checkpoint file (IN-03).
            with self.server.db_lock:
                paused = asyncio.run(submit_case(case, self.server.db_path))
        except Exception:  # noqa: BLE001 - any failure is reported, never an approve
            return self._page(error=_FAILURE_COPY, form_values=form)
        return self._page(paused=paused, form_values=form)

    def _handle_decision(self, form: Mapping[str, str]) -> str:
        thread_id = str(form.get("thread_id", "")).strip()
        if not thread_id:
            return self._page(error=_NO_THREAD_COPY, form_values=form)
        try:
            with self.server.db_lock:
                result = asyncio.run(decide(thread_id, form, self.server.db_path))
        except DurableError as exc:
            # The gate's OWN refusal (blank identity, missing colour, no pending gate): the
            # surface shows that reason and restates no gate logic.
            return self._page(error=str(exc), form_values=form)
        except Exception:  # noqa: BLE001 - a server/graph failure leaves the decision unresolved
            return self._page(error=_FAILURE_COPY, form_values=form)
        return self._page(result=result, form_values=form)


def _validation_field(exc: ValidationError) -> str | None:
    """The field the schema's first error names (the ``loc`` head), or ``None``.

    Used to render a schema rejection beside the offending field. ``CaseInput`` carries only
    field-level constraints, so a real rejection always names a field; ``None`` is the honest
    fallback for a hypothetical model-level error, which then renders in the error panel.
    """
    location = exc.errors()[0].get("loc", ())
    return str(location[0]) if location else None


def _validation_message(exc: ValidationError) -> str:
    """Build the UI-SPEC schema-rejection copy from the schema's OWN field message (D10-13)."""
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error.get("loc", ()))
    message = str(error.get("msg", "invalid input"))
    detail = f"{location}: {message}" if location else message
    return f"{detail}. {_SCHEMA_HINT}"


def _refuse_non_loopback(host: str) -> None:
    """Fail closed on a non-loopback bind (D10-03).

    The surface has no authentication and gates the approve-to-queue path, so a wildcard
    or routable bind would expose patient vitals/complaints and the commit path to the
    whole network. A host that is not a literal loopback address (including a name that
    cannot be proven loopback) is refused; the caller must opt in explicitly to override.
    """
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError(
            f"the desk surface binds loopback only (D10-03); refusing {host!r}"
        ) from exc
    if not address.is_loopback:
        raise ValueError(
            f"the desk surface binds loopback only (D10-03); refusing {host!r}"
        )


def make_server(
    host: str,
    port: int,
    db_path: str | Path,
    *,
    allow_non_loopback: bool = False,
) -> DeskServer:
    """Construct the desk bridge bound to *host* (loopback only — D10-03) over *db_path*.

    A non-loopback *host* is refused unless the caller passes ``allow_non_loopback=True``
    explicitly — the surface is an unauthenticated local prototype, so binding a wildcard
    is never the default (WR-02). The refusal lives in :class:`DeskServer` itself (IN-04), so
    this factory and a direct construction are protected identically.
    """
    server = DeskServer(
        (host, port), DeskHandler, allow_non_loopback=allow_non_loopback
    )
    server.db_path = Path(db_path)
    return server


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str | Path = CHECKPOINTS_DB_PATH,
    allow_non_loopback: bool = False,
) -> None:
    """Serve the desk surface until interrupted (loopback only — D10-03).

    A non-loopback *host* is refused unless ``allow_non_loopback=True`` is passed (WR-02).
    """
    make_server(
        host, port, db_path, allow_non_loopback=allow_non_loopback
    ).serve_forever()


__all__ = [
    "DeskHandler",
    "DeskServer",
    "STATIC_DIR",
    "banner_trigger",
    "decide",
    "editable_colours",
    "form_to_case",
    "make_server",
    "render_state",
    "serve",
    "submit_case",
    "terminal_kind",
]
