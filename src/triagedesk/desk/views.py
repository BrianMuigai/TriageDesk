"""The desk view assembly: choose the view for one state and substitute it into the ONE
hand-authored template.
"""

from __future__ import annotations

import string
from collections.abc import Mapping
from typing import Any

from triagedesk.desk.assets import STATIC_DIR
from triagedesk.desk.card import _card_html, _card_payload_from_state
from triagedesk.desk.copy import (
    _BANNER_HEADLINE,
    _BANNER_LOW_CONFIDENCE_BODY,
    _BANNER_NO_MATCH_BODY,
    _DEFERRED_COPY,
    _DISMISSED_COPY,
    _EMPTY_BODY,
    _EMPTY_HEADING,
    _ESCALATED_COPY,
    _FAILURE_COPY,
    _RECOVERY_COPY,
    _UNREACHED_COPY,
)
from triagedesk.desk.forms import _csrf_field, _vitals_fields
from triagedesk.desk.gate import _gate_html
from triagedesk.desk.markup import _escaped
from triagedesk.durable import PausedRun


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
