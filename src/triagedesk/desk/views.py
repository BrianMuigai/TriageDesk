"""The desk view assembly: choose the view for one state and substitute it into the ONE
hand-authored template.
"""

from __future__ import annotations

import string
from collections.abc import Mapping, Sequence
from typing import Any

from triagedesk.desk.assets import STATIC_DIR
from triagedesk.desk.card import _card_html, _card_payload_from_state
from triagedesk.desk.chat import (
    extraction_bubble,
    note_failed_bubble,
    note_offline_bubble,
    nurse_bubble,
)
from triagedesk.desk.chat import (
    handover_html as _handover_html,
)
from triagedesk.desk.clarification import _question_html
from triagedesk.desk.copy import (
    _BANNER_HEADLINE,
    _BANNER_LOW_CONFIDENCE_BODY,
    _BANNER_NO_MATCH_BODY,
    _BANNER_VITALS_ONLY_BODY,
    _BANNER_VITALS_ONLY_HEADLINE,
    _CHAT_BADGE_SCORED,
    _CHAT_COMPOSER_HINT,
    _CHAT_COMPOSER_LABEL,
    _CHAT_COMPOSER_PLACEHOLDER,
    _CHAT_PANEL_INTAKE,
    _CHAT_PANEL_WAITING_COPY,
    _CHAT_RAIL_FOOT,
    _CHAT_RAIL_STATION_BODY,
    _CHAT_RAIL_STATION_EYEBROW,
    _CHAT_RAIL_STATION_TITLE,
    _CHAT_SEND_NOTE,
    _CLARIFICATION_COPY,
    _CONFIRM_COPY,
    _CONFIRM_EDIT,
    _CONFIRM_GAPS,
    _CONFIRM_HEADING,
    _CONFIRM_PROVENANCE,
    _CONFIRM_PROVENANCE_NOTE,
    _CONFIRM_SCORE,
    _DEFERRED_COPY,
    _DISMISSED_COPY,
    _EMPTY_BODY,
    _EMPTY_HEADING,
    _ESCALATED_COPY,
    _FAILURE_COPY,
    _FORM_PRIMARY,
    _MODE_OFFLINE,
    _OUTCOME_COPY,
    _OUTCOME_KICKER,
    _OUTCOME_TERMINAL_COPY,
    _RECORD_COPY,
    _RECORD_HEADING,
    _RECORD_OFFLINE_HINT,
    _RECORD_ONLINE_HINT,
    _REVIEW_COPY,
    _REVIEW_EDIT,
    _REVIEW_HEADING,
    _REVIEW_PATIENT,
    _START_NEXT,
    _STEP_CONFIRM,
    _STEP_HANDOVER,
    _STEP_NAV_LABEL,
    _STEP_RECORD,
    _STEP_REVIEW,
    _UNREACHED_COPY,
    recovery_copy,
)
from triagedesk.desk.forms import (
    _VITALS_LAYOUT,
    _csrf_field,
    _vitals_fieldset,
    case_to_form_values,
    display_form_value,
)
from triagedesk.desk.gate import _gate_html
from triagedesk.desk.markup import _escaped
from triagedesk.durable import PausedRun
from triagedesk.mcp.elicitation import is_elicitation


def banner_trigger(state: Mapping[str, Any]) -> str | None:
    """The ONE banner rule (D10-09, COV-02): the typed signal, never a heuristic.

    Returns ``"vitals_only"`` when the case was delivered because **no discriminator applies**
    (``retrieval_status == "no_candidate"``) — a calm, informational note, not an alarm;
    ``"no_match"`` when the complaint is genuinely ambiguous or the legacy no-match path fired;
    else ``"deferral"`` when the ``confidence`` channel defers; else ``None``. It deliberately
    does NOT consult ``evidence.no_match`` (a different fact: "no excerpt matched"), NOT
    ``missing_vitals`` alone (the recovery signal's job), and NOT any free-text reason string.
    """
    status = str(state.get("retrieval_status") or "")
    confidence = state.get("confidence")
    if (
        status == "no_candidate"
        and confidence is not None
        and getattr(confidence, "action", "") == "deliver"
    ):
        return "vitals_only"
    if bool(state.get("no_match")):
        return "no_match"
    if confidence is not None and bool(getattr(confidence, "deferral", False)):
        return "deferral"
    return None


def terminal_kind(state: Mapping[str, Any]) -> str | None:
    """Select the terminal copy from the graph's typed channels (never a string heuristic).

    ``"clarification"`` when the bounded clarification terminal is present (COV-03) — a
    first-class ask that is neither a deferral nor a colour; else ``"deferred"`` when the
    ``confidence`` channel defers (checked next — a deferral always routes to
    ``escalate``/``request_missing_info``, so an escalated state may also carry a
    deferral); else ``"escalated"`` when the ``escalation`` channel is present; else
    ``"recovery"`` when the ``recovery`` channel is present; else ``None``. The kind is
    never inferred from ``Escalation.reason`` (a free-text field that varies).
    """
    if state.get("clarification") is not None:
        return "clarification"
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
        f'<section class="state-panel state-{kind}" role="status"><p>{_escaped(copy)}</p></section>'
    )


def _banner_html(trigger: str) -> str:
    """Render the uncertainty note with a trigger-conditional body (D10-09).

    The headline is verbatim from UX-01 for the genuine uncertainty triggers; a
    ``vitals_only`` delivery uses the calmer COV-02 note because no discriminator applies
    and the recorded vitals are the complete basis. The banner never asserts a fact its
    trigger did not establish.
    """
    if trigger == "vitals_only":
        return (
            f'<p class="banner-headline">{_escaped(_BANNER_VITALS_ONLY_HEADLINE)}</p>'
            f'<p class="banner-body">{_escaped(_BANNER_VITALS_ONLY_BODY)}</p>'
        )
    body = _BANNER_NO_MATCH_BODY if trigger == "no_match" else _BANNER_LOW_CONFIDENCE_BODY
    return (
        f'<p class="banner-headline">{_escaped(_BANNER_HEADLINE)}</p>'
        f'<p class="banner-body">{_escaped(body)}</p>'
    )


def _terminal_panel(state: Mapping[str, Any]) -> str:
    """Select the terminal copy from the graph's typed channels (never a string heuristic)."""
    kind = terminal_kind(state)
    if kind == "clarification":
        clarification = state.get("clarification")
        questions = list(getattr(clarification, "questions", None) or [])
        items = "".join(f"<li>{_escaped(question)}</li>" for question in questions)
        return (
            f'<section class="state-panel state-clarification" role="status">'
            f"<p>{_escaped(_CLARIFICATION_COPY)}</p>"
            f'<ul class="clarification-questions">{items}</ul></section>'
        )
    if kind == "deferred":
        return _panel(_DEFERRED_COPY, "muted")
    if kind == "escalated":
        return _panel(_ESCALATED_COPY, "muted")
    if kind == "recovery":
        recovery = state.get("recovery")
        missing = list(getattr(recovery, "missing_vitals", None) or [])
        return _panel(recovery_copy(missing), "muted")
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
        "clarification": "",
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
    kind = terminal_kind(state)
    trigger = banner_trigger(state)
    # The uncertainty banner is about a SUGGESTION that may be incomplete. A clarification,
    # recovery or escalation has no suggestion to qualify, so the banner would contradict the
    # terminal's own "nothing was committed" copy (UI review 25-01, BLOCKER 3).
    suppress_banner = kind in ("clarification", "recovery", "escalated")
    banner = _banner_html(trigger) if trigger is not None and not suppress_banner else ""
    evidence = state.get("evidence")
    paused_case = state.get("case")
    case_values = case_to_form_values(paused_case) if paused_case is not None else None

    if paused.paused and paused.payload is not None:
        # A QUESTION, not a decision: an elicitation payload renders the question panel and
        # no gate, no card and no commit path (ELICIT-05/08). Checked FIRST, so an
        # elicitation can never fall through to the approval-gate branch.
        if is_elicitation(paused.payload):
            return {
                "state_panel": "",
                "banner": "",
                "card": "",
                "gate": "",
                "clarification": _question_html(
                    paused.payload, paused.thread_id, csrf_token, case_values
                ),
            }
        return {
            "state_panel": "",
            "banner": banner,
            "card": _card_html(paused.payload, evidence),
            "gate": _gate_html(str(paused.payload.get("case_id") or ""), csrf_token, case_values),
            "clarification": "",
        }

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
            "clarification": "",
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
            "clarification": "",
        }
    if paused.existed:
        return {
            "state_panel": "",
            "banner": banner,
            "card": _card_html(_card_payload_from_state(state, paused.thread_id), evidence),
            "gate": _gate_html(paused.thread_id, csrf_token, case_values),
            "clarification": "",
        }
    return {
        "state_panel": _terminal_panel(state),
        "banner": banner,
        "card": "",
        "gate": "",
        "clarification": "",
    }


def _decision_view(result: Mapping[str, Any], form: Mapping[str, str]) -> dict[str, str]:
    """The view after a gate decision was resumed — committed, dismissed, or refused."""
    decision = str(form.get("decision", "")).strip()
    name = str(form.get("name", ""))
    role = str(form.get("role", ""))
    commit = result.get("commit_result")

    if decision == "dismiss":
        panel = _panel(_DISMISSED_COPY, "muted")
        outcome = "dismissed"
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
        handover = result.get("handover")
        handover_html = _handover_html(handover, commit) if handover is not None else ""
        panel = _panel(copy, "success") + handover_html
        outcome = "committed"
    else:
        reason = getattr(commit, "reason", None) or _FAILURE_COPY
        panel = _panel(reason, "error")
        outcome = "refused"

    return {
        "state_panel": panel,
        "banner": "",
        "card": "",
        "gate": "",
        "clarification": "",
        "outcome": outcome,
    }


def _error_panel(message: str) -> str:
    """The error view — a failure leaves the decision unresolved; a failure is never an approve."""
    return _panel(message, "error")


def _note_fields_hidden(note_fields: Sequence[str]) -> str:
    """Carry note provenance through the form without a session store."""
    if not note_fields:
        return ""
    value = ",".join(note_fields)
    return f'<input type="hidden" name="note_fields" value="{_escaped(value)}">'


def _intake_panel(
    form: Mapping[str, str],
    csrf_token: str | None,
    field_error: tuple[str, str] | None,
    clarification_round: int = 0,
    note_fields: Sequence[str] = (),
) -> str:
    """The structured intake — the scored input, and the primary surface in step 1."""
    round_field = (
        f'<input type="hidden" name="clarification_round" value="{clarification_round}">'
        if clarification_round
        else ""
    )
    focus_name = field_error[0] if field_error is not None else None
    return (
        '<section class="intake-panel" aria-labelledby="intake-heading">'
        '<header class="panel-head">'
        f'<div><p class="eyebrow">{_escaped(_CHAT_PANEL_INTAKE)}</p>'
        '<h2 id="intake-heading">Patient details</h2></div>'
        f'<span class="badge">{_escaped(_CHAT_BADGE_SCORED)}</span></header>'
        '<form id="vitals-form" class="vitals-form" method="post" action="/case">'
        f"{_csrf_field(csrf_token)}{round_field}{_note_fields_hidden(note_fields)}"
        f"{_vitals_fieldset(form, field_error, autofocus_name=focus_name)}"
        '<div class="form-actions">'
        '<button type="submit" name="action" value="confirm" id="submit-vitals" '
        f'class="primary">{_escaped(_FORM_PRIMARY)}</button>'
        '<button type="reset" class="ghost" data-confirm="Clear form: this removes the '
        'vitals you have typed. Clear the form?">Clear form</button>'
        "</div></form></section>"
    )


def _composer() -> str:
    """The optional note helper, associated with the intake form below it."""
    return (
        '<div class="composer">'
        f'<label class="composer-label" for="note-input">'
        f"{_escaped(_CHAT_COMPOSER_LABEL)}</label>"
        '<div class="composer-row">'
        '<textarea id="note-input" name="note" form="vitals-form" rows="2" '
        f'enterkeyhint="enter" placeholder="{_escaped(_CHAT_COMPOSER_PLACEHOLDER)}">'
        "</textarea>"
        '<button type="submit" form="vitals-form" name="action" value="note" '
        'class="primary composer-send">'
        f"{_escaped(_CHAT_SEND_NOTE)}</button></div>"
        f'<p class="composer-hint">{_escaped(_CHAT_COMPOSER_HINT)}</p>'
        "</div>"
    )


def _note_status(
    view: Mapping[str, str],
    note: str | None,
    extraction: Any,
    note_failed: bool,
) -> str:
    """The result of the optional note helper — not a conversation log."""
    if note_failed:
        return note_failed_bubble()
    if extraction is not None:
        return extraction_bubble(extraction)
    if note:
        return nurse_bubble(note) + note_offline_bubble()
    return view["state_panel"]


def _record_workspace(
    view: Mapping[str, str],
    form: Mapping[str, str],
    csrf_token: str | None,
    field_error: tuple[str, str] | None,
    note: str | None,
    extraction: Any,
    note_failed: bool,
    note_fields: Sequence[str],
    clarification_round: int,
    online: bool,
) -> str:
    """Step 1: one structured intake, with a compact optional note helper above it."""
    mode_hint = _RECORD_ONLINE_HINT if online else _RECORD_OFFLINE_HINT
    status = _note_status(view, note, extraction, note_failed)
    status_html = f'<div class="note-status" role="status">{status}</div>' if status else ""
    return (
        '<div class="record-stack">'
        '<section class="note-assistant" aria-labelledby="note-heading">'
        '<header class="note-head">'
        f'<p class="eyebrow">{_escaped(_RECORD_HEADING)}</p>'
        '<p class="note-copy">'
        f"{_escaped(_RECORD_COPY)}</p></header>"
        f"{_composer()}"
        f'<p class="note-mode-hint">{_escaped(mode_hint)}</p>'
        f"{status_html}"
        "</section>"
        f"{_intake_panel(form, csrf_token, field_error, clarification_round, note_fields)}"
        "</div>"
    )


def _confirm_rows(form: Mapping[str, str], note_fields: Sequence[str]) -> tuple[str, str]:
    """The confirm summary rows and the not-stated list, from the validated form values."""
    note_set = set(note_fields)
    rows: list[str] = []
    gaps: list[str] = []
    for name, label in _VITALS_LAYOUT:
        raw = str(form.get(name, ""))
        value = display_form_value(name, raw)
        if not raw.strip():
            gaps.append(label)
        provenance = (
            f'<span class="provenance">{_escaped(_CONFIRM_PROVENANCE)}</span>'
            if name in note_set and raw.strip()
            else ""
        )
        rows.append(
            '<div class="confirm-fact">'
            f"<dt>{_escaped(label)}{provenance}</dt>"
            f"<dd>{_escaped(value)}</dd></div>"
        )
    gap_text = (
        f'<p class="confirm-gaps"><span class="label">'
        f"{_escaped(_CONFIRM_GAPS)}:</span> {_escaped(', '.join(gaps))}</p>"
        if gaps
        else ""
    )
    return "".join(rows), gap_text


def _hidden_form_values(form: Mapping[str, str], csrf_token: str | None) -> str:
    """A form's values as hidden inputs, for the confirm and edit-details posts.

    ``action`` is excluded so the submit button is the ONLY action in the resulting POST;
    a hidden action would otherwise be the first value and win the handler's ``action`` read.
    """
    hidden = "".join(
        f'<input type="hidden" name="{_escaped(name)}" value="{_escaped(value)}">'
        for name, value in form.items()
        if name not in ("csrf_token", "action", "note")
    )
    return f"{_csrf_field(csrf_token)}{hidden}"


def _confirm_workspace(
    form: Mapping[str, str],
    note_fields: Sequence[str],
    csrf_token: str | None,
) -> str:
    """Step 2: the human checkpoint before any scoring or graph run."""
    rows, gaps = _confirm_rows(form, note_fields)
    provenance_note = (
        f'<p class="confirm-provenance-note">{_escaped(_CONFIRM_PROVENANCE_NOTE)}</p>'
        if note_fields
        else ""
    )
    hidden = _hidden_form_values(form, csrf_token)
    return (
        '<section class="confirm-panel" aria-labelledby="confirm-heading">'
        '<header class="panel-head">'
        f'<div><p class="eyebrow">{_escaped(_STEP_CONFIRM)}</p>'
        f'<h2 id="confirm-heading">{_escaped(_CONFIRM_HEADING)}</h2></div>'
        '<span class="badge">Human checkpoint</span></header>'
        '<div class="confirm-body">'
        f'<p class="confirm-copy">{_escaped(_CONFIRM_COPY)}</p>'
        f"{provenance_note}"
        f'<dl class="confirm-grid">{rows}</dl>'
        f"{gaps}"
        '<form id="confirm-form" method="post" action="/case">'
        f"{hidden}"
        '<div class="confirm-actions">'
        '<button type="submit" name="action" value="score" class="primary">'
        f"{_escaped(_CONFIRM_SCORE)}</button>"
        '<button type="submit" name="action" value="back">'
        f"{_escaped(_CONFIRM_EDIT)}</button>"
        "</div></form></div></section>"
    )


def _patient_summary(form: Mapping[str, str], csrf_token: str | None) -> str:
    """A compact, read-only patient summary beside the review, with an edit path."""
    key_fields = (
        "age_years",
        "complaint",
        "avpu",
        "respiratory_rate",
        "spo2",
        "heart_rate",
        "systolic_bp",
        "temperature_c",
        "mobility",
    )
    labels = dict(_VITALS_LAYOUT)
    rows = "".join(
        '<div class="patient-fact">'
        f"<dt>{_escaped(labels[name])}</dt>"
        f"<dd>{_escaped(display_form_value(name, str(form.get(name, ''))))}</dd>"
        "</div>"
        for name in key_fields
    )
    hidden = _hidden_form_values(form, csrf_token)
    return (
        '<aside class="patient-details" aria-labelledby="patient-details-heading">'
        f'<h2 id="patient-details-heading">{_escaped(_REVIEW_PATIENT)}</h2>'
        f'<dl class="patient-facts">{rows}</dl>'
        '<form id="edit-details-form" method="post" action="/case">'
        f"{hidden}"
        '<input type="hidden" name="action" value="back">'
        '<button type="submit" class="ghost">'
        f"{_escaped(_REVIEW_EDIT)}</button>"
        "</form></aside>"
    )


def _review_workspace(
    view: Mapping[str, str],
    form: Mapping[str, str],
    csrf_token: str | None,
) -> str:
    """Step 3: the suggestion and the named gate, with the intake collapsed to a summary."""
    banner = view["banner"]
    banner_html = (
        f'<div class="uncertainty-banner" aria-live="polite">{banner}</div>' if banner else ""
    )
    main = "".join(
        [
            view["state_panel"],
            banner_html,
            view["card"],
            view["gate"],
            view.get("clarification", ""),
        ]
    )
    return (
        '<div class="review-layout">'
        '<section class="review-main" aria-labelledby="review-heading">'
        '<header class="review-head">'
        f'<p class="eyebrow">{_escaped(_STEP_REVIEW)}</p>'
        f'<h2 id="review-heading">{_escaped(_REVIEW_HEADING)}</h2>'
        f'<p class="review-copy">{_escaped(_REVIEW_COPY)}</p></header>'
        f"{main}</section>"
        f"{_patient_summary(form, csrf_token)}"
        "</div>"
    )


def _outcome_workspace(view: Mapping[str, str]) -> str:
    """The completion state: handover/terminal facts and a clear next-patient action."""
    banner = view["banner"]
    banner_html = (
        f'<div class="uncertainty-banner" aria-live="polite">{banner}</div>' if banner else ""
    )
    main = "".join([view["state_panel"], banner_html, view["card"], view["gate"]])
    outcome = str(view.get("outcome", "refused"))
    if outcome == "committed":
        copy = _OUTCOME_COPY
        note = ""
    elif outcome == "dismissed":
        copy = _DISMISSED_COPY
        note = ""
    else:
        copy = _OUTCOME_COPY
        note = f'<p class="outcome-note">{_escaped(_OUTCOME_TERMINAL_COPY)}</p>'
    return (
        '<section class="outcome-panel" aria-labelledby="outcome-heading">'
        '<header class="outcome-head">'
        f'<p class="eyebrow">{_escaped(_OUTCOME_KICKER)}</p>'
        f'<h2 id="outcome-heading">{_escaped(_STEP_HANDOVER)}</h2>'
        f'<p class="page-copy">{_escaped(copy)}</p></header>'
        f"{main}{note}"
        '<div class="page-actions">'
        f'<a class="button-link" href="/">{_escaped(_START_NEXT)}</a></div>'
        "</section>"
    )


def _stepper(step: str) -> str:
    """The one step indicator: Record → Confirm → Review & decide → Handover."""
    labels = (
        ("record", "1", _STEP_RECORD),
        ("confirm", "2", _STEP_CONFIRM),
        ("review", "3", _STEP_REVIEW),
        ("outcome", "4", _STEP_HANDOVER),
    )
    order = [key for key, _, _ in labels]
    current = order.index(step) if step in order else 0
    parts: list[str] = []
    for index, (_key, number, label) in enumerate(labels):
        status = "current" if index == current else ("done" if index < current else "")
        current_attr = ' aria-current="step"' if index == current else ""
        parts.append(
            f'<span class="step {status}"{current_attr}>'
            f'<span class="num">{number}</span>{_escaped(label)}</span>'
        )
        if index < len(labels) - 1:
            parts.append('<span class="step-line" aria-hidden="true"></span>')
    return f'<nav class="steps" aria-label="{_escaped(_STEP_NAV_LABEL)}">{"".join(parts)}</nav>'


def _workspace(
    step: str,
    view: Mapping[str, str],
    form: Mapping[str, str],
    csrf_token: str | None,
    field_error: tuple[str, str] | None,
    note: str | None,
    extraction: Any,
    note_failed: bool,
    note_fields: Sequence[str],
    clarification_round: int,
    online: bool,
) -> str:
    """Compose the one primary task for *step*, under the one step indicator."""
    if step == "confirm":
        body = _confirm_workspace(form, note_fields, csrf_token)
    elif step == "review":
        body = _review_workspace(view, form, csrf_token)
    elif step == "outcome":
        body = _outcome_workspace(view)
    else:
        body = _record_workspace(
            view,
            form,
            csrf_token,
            field_error,
            note,
            extraction,
            note_failed,
            note_fields,
            clarification_round,
            online,
        )
    return f"{_stepper(step)}{body}"


def _waiting_page(waiting: str) -> str:
    """The waiting-room page: the same shell, the queue in place of the conversation."""
    return (
        '<section class="waiting-page" aria-label="Waiting room">'
        f'<p class="page-copy">{_escaped(_CHAT_PANEL_WAITING_COPY)}</p>'
        f"{waiting}"
        '<div class="page-actions">'
        '<a class="button-link" href="/">New case</a></div>'
        "</section>"
    )


def _render(
    view: Mapping[str, str],
    form: Mapping[str, str],
    csrf_token: str | None = None,
    field_error: tuple[str, str] | None = None,
    mode_label: str = _MODE_OFFLINE,
    waiting: str = "",
    note: str | None = None,
    extraction: Any = None,
    note_failed: bool = False,
    note_fields: Sequence[str] = (),
    clarification_round: int = 0,
    step: str = "record",
    online: bool = False,
    system: bool = False,
) -> str:
    """Substitute the one step workspace into the hand-authored app shell.

    ``string.Template`` (not ``str.format``) is used because the markup carries CSS braces;
    the page's only ``$`` characters are its placeholders. The step is chosen by the caller and
    rendered by :func:`_workspace`; a rejected submission repopulates the form and, when
    *field_error* names the offending field, renders the schema's message beside it. The
    per-server CSRF token travels into every POST form. ``waiting`` selects the queue page and
    defaults to the triage workspace. ``note``/``extraction``/``note_fields`` carry the optional
    note helper and its provenance; ``online`` selects the mode-specific hint.
    """
    template = string.Template((STATIC_DIR / "index.html").read_text(encoding="utf-8"))
    if system:
        workspace = (STATIC_DIR / "system.html").read_text(encoding="utf-8")
        page_title = "System map"
        page_eyebrow = "Integration"
        topbar_action = '<a class="topbar-action" href="/">New case</a>'
        new_case_flag = ""
        waiting_flag = ""
        system_flag = ' aria-current="page"'
    elif waiting:
        workspace = _waiting_page(waiting)
        page_title = "Waiting room"
        page_eyebrow = "Queue"
        topbar_action = '<a class="topbar-action" href="/">New case</a>'
        new_case_flag = ""
        waiting_flag = ' aria-current="page"'
        system_flag = ""
    else:
        workspace = _workspace(
            step,
            view,
            form,
            csrf_token,
            field_error,
            note,
            extraction,
            note_failed,
            note_fields,
            clarification_round,
            online,
        )
        page_title = "New patient"
        page_eyebrow = "Triage workspace"
        topbar_action = '<a class="topbar-action" href="/waiting">Waiting room</a>'
        new_case_flag = ' aria-current="page"'
        waiting_flag = ""
        system_flag = ""
    return template.substitute(
        mode_label=mode_label,
        workspace=workspace,
        page_title=page_title,
        page_eyebrow=page_eyebrow,
        topbar_action=topbar_action,
        new_case_current=new_case_flag,
        waiting_current=waiting_flag,
        system_current=system_flag,
        rail_station_eyebrow=_escaped(_CHAT_RAIL_STATION_EYEBROW),
        rail_station_title=_escaped(_CHAT_RAIL_STATION_TITLE),
        rail_station_body=_escaped(_CHAT_RAIL_STATION_BODY),
        rail_foot=_escaped(_CHAT_RAIL_FOOT),
    )


def render_system(mode_label: str = _MODE_OFFLINE) -> str:
    """Render the read-only system / integration map page."""
    return _render(
        _empty_view(),
        {},
        mode_label=mode_label,
        system=True,
    )


def render_confirmation(
    form_values: Mapping[str, str],
    *,
    note_fields: Sequence[str] = (),
    csrf_token: str | None = None,
    mode_label: str = _MODE_OFFLINE,
    online: bool = False,
) -> str:
    """Render step 2 — the human confirmation checkpoint before any scoring."""
    return _render(
        _empty_view(),
        form_values,
        csrf_token,
        mode_label=mode_label,
        note_fields=note_fields,
        step="confirm",
        online=online,
    )


def render_state(
    paused: PausedRun | None = None,
    *,
    result: Mapping[str, Any] | None = None,
    error: str | None = None,
    field_error: tuple[str, str] | None = None,
    form_values: Mapping[str, str] | None = None,
    csrf_token: str | None = None,
    mode_label: str = _MODE_OFFLINE,
    waiting: str = "",
    note: str | None = None,
    extraction: Any = None,
    note_failed: bool = False,
    note_fields: Sequence[str] = (),
    step: str = "record",
    online: bool = False,
) -> str:
    """Render the page for one step: record, confirm, review/decide, outcome, or waiting.

    With no case submitted it renders step 1 — the optional note helper and the structured
    intake — with the ``No case yet`` heading and body and NO ``priority-card`` or
    ``approval-gate`` region. A confirmed form renders step 2 via
    :func:`render_confirmation`; a paused run renders step 3 (card + gate); a decision renders
    the outcome. *error* is a server/graph failure and renders in the state panel; *field_error*
    is a schema rejection rendered beside the offending field. *csrf_token* is the per-server
    secret every POST form carries (WR-01). *note*/*extraction*/*note_fields* carry the optional
    note helper and its provenance; *online* selects the mode-specific hint.
    """
    form = form_values or {}
    if result is not None:
        return _render(
            _decision_view(result, form),
            form,
            csrf_token,
            mode_label=mode_label,
            waiting=waiting,
            note=note,
            extraction=extraction,
            note_failed=note_failed,
            note_fields=note_fields,
            step="outcome",
            online=online,
        )
    if paused is not None:
        return _render(
            _paused_view(paused, csrf_token),
            form,
            csrf_token,
            mode_label=mode_label,
            waiting=waiting,
            note=note,
            extraction=extraction,
            note_failed=note_failed,
            note_fields=note_fields,
            clarification_round=(1 if terminal_kind(paused.result) == "clarification" else 0),
            step="review",
            online=online,
        )
    if error is not None:
        return _render(
            {
                "state_panel": _error_panel(error),
                "banner": "",
                "card": "",
                "gate": "",
                "clarification": "",
            },
            form,
            csrf_token,
            mode_label=mode_label,
            waiting=waiting,
            note=note,
            extraction=extraction,
            note_failed=note_failed,
            note_fields=note_fields,
            step="record",
            online=online,
        )
    if field_error is not None:
        return _render(
            {
                "state_panel": "",
                "banner": "",
                "card": "",
                "gate": "",
                "clarification": "",
            },
            form,
            csrf_token,
            field_error,
            mode_label=mode_label,
            waiting=waiting,
            note=note,
            extraction=extraction,
            note_failed=note_failed,
            note_fields=note_fields,
            step="record",
            online=online,
        )
    return _render(
        _empty_view(),
        form,
        csrf_token,
        mode_label=mode_label,
        waiting=waiting,
        note=note,
        extraction=extraction,
        note_failed=note_failed,
        note_fields=note_fields,
        step=step,
        online=online,
    )
