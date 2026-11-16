"""Interactive terminal triage — drive the shipped graph from a prompt (CLI surface).

The web desk (``triagedesk desk``) and the scripted storyboard (``triagedesk demo``) both need a
browser or a fixed fixture. This module adds the third surface a reviewer actually asks for: type
a patient in, watch the graph investigate, answer a question if it asks one, and approve the
priority — all in the terminal.

It is **presentation only**. Every step delegates to the shipped seams, so this surface can never
become a second decision path (SOLID: S/D):

* the case is built and validated by the ONE ``core.schema.CaseInput``;
* the run uses the desk's own ``pipeline.submit_case`` / ``decide`` / ``answer_clarification``,
  which in turn use ``durable.run_to_gate`` / ``resume_thread`` and the ONE store seam;
* the elicitation vocabulary (request key, form fields, resume shape, interrupt discriminator)
  comes from ``mcp.elicitation`` — never restated here;
* the gate's identity rule is ``durable.approval_decision``; this module never re-checks it.

An answer typed here is an observation, not an approval: the question path resumes with
``respond=lambda _payload: None``, so the approval gate stays paused afterwards (ELICIT-08).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

from pydantic import ValidationError

from triagedesk.core.rules import get_tews
from triagedesk.core.schema import AVPU, CaseInput, ExtractionResult, HandoverCard, Mobility
from triagedesk.desk.extraction import extract_complaint, extract_note
from triagedesk.desk.pipeline import answer_clarification, decide, submit_case
from triagedesk.durable import DurableError
from triagedesk.mcp.elicitation import (
    ACCEPT,
    CLARIFICATION_REQUEST_KEY,
    DECLINE,
    answer_fields,
    form_requests,
    is_elicitation,
)

# The prompts, in the order the desk form asks them. Declared once so the CLI and any future
# text surface share one intake order; ``required`` is the only per-field difference.
Ask = Callable[[str], str]
Tell = Callable[[str], None]

_DECISIONS: tuple[str, ...] = ("approve", "edit", "dismiss")


class _Quit(Exception):
    """The operator asked to stop — never an error, never a partial commit."""


@dataclass(frozen=True)
class Intake:
    """One patient, however it was entered — the structured form or a raw note.

    ``extraction`` is the model's grounded read of a raw note, or ``None`` for the structured
    path. Passing it to the pipeline means the model ran once, before the graph, exactly as the
    desk's online precompute does.
    """

    case: CaseInput
    extraction: ExtractionResult | None = None
    raw_note: str | None = None


def _read(ask: Ask, label: str) -> str:
    """Read one line, translating EOF/^C into a clean quit rather than a traceback."""
    try:
        return ask(label).strip()
    except (EOFError, KeyboardInterrupt) as exc:  # pragma: no cover - terminal dependent
        raise _Quit from exc


def _ask_text(ask: Ask, label: str, *, required: bool = False, default: str = "") -> str:
    """Ask for free text; an empty answer is allowed unless *required*."""
    while True:
        value = _read(ask, label)
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print("  (required — please enter a value)")


def _ask_int(ask: Ask, label: str, low: int, high: int) -> int | None:
    """Ask for an optional integer inside its schema-plausible range."""
    while True:
        raw = _read(ask, label)
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            print(f"  (enter a whole number between {low} and {high}, or blank to skip)")
            continue
        if low <= value <= high:
            return value
        print(f"  (out of range: {low}–{high}; blank to skip)")


def _ask_float(ask: Ask, label: str, low: float, high: float) -> float | None:
    """Ask for an optional decimal inside its schema-plausible range."""
    while True:
        raw = _read(ask, label)
        if not raw:
            return None
        try:
            value = float(raw)
        except ValueError:
            print(f"  (enter a number between {low:g} and {high:g}, or blank to skip)")
            continue
        if low <= value <= high:
            return value
        print(f"  (out of range: {low:g}–{high:g}; blank to skip)")


def _ask_choice(ask: Ask, label: str, choices: Sequence[str]) -> str | None:
    """Ask for one of *choices* by number or by name; blank skips."""
    rendered = " · ".join(f"{index}) {choice}" for index, choice in enumerate(choices, start=1))
    while True:
        raw = _read(ask, f"{label} [{rendered}] ").lower()
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        if raw in choices:
            return raw
        print(f"  (choose one of: {', '.join(choices)}, or blank to skip)")


def _ask_bool(ask: Ask, label: str) -> bool | None:
    """Ask a two-way question; blank skips it (unknown, never a false answer).

    Only the single-letter forms are accepted on purpose: the words themselves are loaded
    discriminator aliases, and the DRY guard forbids restating a loaded value under ``src/``
    (CONVENTIONS §1). ``y`` / ``n`` are structural input tokens, not clinical vocabulary.
    """
    while True:
        raw = _read(ask, f"{label} [y/n] ").lower()
        if not raw:
            return None
        if raw in ("y", "1"):
            return True
        if raw in ("n", "0"):
            return False
        print("  (answer y or n, or blank to skip)")


def _read_note(ask: Ask) -> str:
    """Read a free-text note: one line, or several until a blank line ends it."""
    print("Paste the nurse's note (blank line to finish, blank first line to skip):")
    lines: list[str] = []
    while True:
        line = _read(ask, "  > ")
        if not line:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def describe_case(case: CaseInput) -> list[str]:
    """The extracted fields, for the operator to confirm before the graph runs."""
    lines: list[str] = []
    for name, value in case.model_dump().items():
        if value is None or value == "" or value is False:
            continue
        lines.append(f"    {name}: {value}")
    missing = [name for name, value in case.model_dump().items() if value is None]
    if missing:
        lines.append(f"    (not stated: {', '.join(missing)})")
    return lines


def collect_case(ask: Ask = input, *, online: bool = False) -> Intake | None:
    """Prompt for one patient — a raw note or the structured fields — as an :class:`Intake`.

    Returns ``None`` when the operator quits. A raw note is offered first and read through the
    owned extraction tool (``--online`` only); declining it falls back to the fields. Every
    vital is optional — a blank answer stays ``None`` and is never imputed — but a complaint is
    required. An impossible value is re-prompted here, so a wrong-unit entry never reaches the
    scorer (T-01-01-03).
    """
    print("\n── New patient ─────────────────────────────────────────────")
    print("   Blank skips a vital. Ctrl-C or 'quit' at any prompt exits.\n")
    try:
        note = _read_note(ask)
        if note:
            if not online:
                print(
                    "  (a raw note needs the model — re-run with --online; "
                    "using the fields instead)"
                )
            else:
                extraction = asyncio.run(extract_note(note))
                print("\n  The model read this case as:")
                for line in describe_case(extraction.case):
                    print(line)
                if _ask_bool(ask, "  Use this extraction?"):
                    return Intake(case=extraction.case, extraction=extraction, raw_note=note)
                print("  (discarded — answer the fields instead)")
        age_years = _ask_int(ask, "Age (years)          ", 0, 130)
        age_months: int | None = None
        age_ambiguous = False
        if age_years is None:
            age_months = _ask_int(ask, "Age (months)         ", 0, 1560)
            if age_months is None:
                age_ambiguous = bool(_ask_bool(ask, "Age unclear?        "))
        avpu = _ask_choice(ask, "Alertness (AVPU)    ", list(get_args(AVPU)))
        respiratory_rate = _ask_int(ask, "Respiratory rate     ", 0, 100)
        spo2 = _ask_int(ask, "SpO2 (%)             ", 0, 100)
        heart_rate = _ask_int(ask, "Heart rate           ", 0, 350)
        systolic_bp = _ask_int(ask, "Systolic BP          ", 0, 400)
        diastolic_bp = _ask_int(ask, "Diastolic BP         ", 0, 300)
        temperature_c = _ask_float(ask, "Temperature (°C)     ", 20.0, 45.0)
        mobility = _ask_choice(ask, "Mobility             ", list(get_args(Mobility)))
        trauma = _ask_bool(ask, "Trauma?             ")
        complaint = _ask_text(
            ask, "Complaint (one line) ", required=True
        )
        if complaint.lower() in ("quit", "exit"):
            raise _Quit
        case = CaseInput(
            age_years=age_years,
            age_months=age_months,
            age_ambiguous=age_ambiguous,
            respiratory_rate=respiratory_rate,
            spo2=spo2,
            heart_rate=heart_rate,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            temperature_c=temperature_c,
            mobility=mobility,
            avpu=avpu,
            trauma=trauma,
            complaint=complaint,
        )
    except _Quit:
        return None
    except ValidationError as exc:  # pragma: no cover - the prompts already bound every field
        print(f"  (the case was rejected by the schema: {exc.errors()[0]['msg']})")
        return None
    return Intake(case=case)


def _clarification_form(payload: Mapping[str, Any], ask: Ask) -> dict[str, str]:
    """Read the answers to a paused question — a blank answer declines, never guesses.

    The form property names come from the server's own requested schema through
    ``mcp.elicitation.answer_fields``, so the CLI cannot drift from the tool's field naming.
    """
    requests = form_requests(payload)
    form: dict[str, str] = {"request_key": CLARIFICATION_REQUEST_KEY, "action": ACCEPT}
    print("\n── The agent needs one measurement ─────────────────────────")
    for request in requests:
        print(f"  {request.get('message', '')}")
        for field in answer_fields(request):
            description = (
                (request.get("requested_schema") or {}).get("properties", {}).get(field, {})
            )
            label = description.get("description") or field
            answer = _ask_text(ask, f"  {label}\n  > ")
            if answer:
                form[field] = answer
    if not any(key.startswith("q") and form[key] for key in form):
        print("  (nothing entered — declining the question)")
        form["action"] = DECLINE
    return form


def _gate_form(payload: Mapping[str, Any], ask: Ask) -> dict[str, str]:
    """Read the clinician's decision for a paused priority.

    The colour and target shown are the payload's own values (the scored suggestion); the
    identity rule is enforced later by ``durable.approval_decision``, so a blank name is
    rejected by the shipped gate rather than by a second check here.
    """
    colours = sorted({band.colour for band in get_tews().tews_to_colour})
    print("\n── Suggested priority ──────────────────────────────────────")
    print(f"  Colour : {payload.get('colour')}")
    print(f"  Target : {payload.get('target')}")
    print("  Why    :")
    for citation in payload.get("citations") or []:
        print(f"    · {citation}")
    if payload.get("missing_vitals"):
        print(f"  Missing: {', '.join(payload['missing_vitals'])}")
    print("  This is a suggestion. Nothing is queued until you decide.\n")
    decision = _ask_choice(ask, "Decision (approve/edit/dismiss)", list(_DECISIONS))
    if decision is None:
        return {"decision": "dismiss"}
    form = {"decision": decision}
    if decision == "dismiss":
        return form
    form["name"] = _ask_text(ask, "Your name ", required=True)
    form["role"] = _ask_text(ask, "Your role ", required=True)
    if decision == "edit":
        colour = _ask_choice(ask, "New colour", colours)
        if colour is not None:
            form["colour"] = colour
    return form


def render_outcome(state: Mapping[str, Any], tell: Tell = print) -> None:
    """Print the delivered card — or the terminal the graph actually reached.

    Reads only the graph's own channels: a handover card means the gate delivered; an
    escalation / recovery / clarification means it deliberately did not, and saying so is
    more honest than printing an empty card.
    """
    card = state.get("handover")
    if isinstance(card, HandoverCard):
        tell("\n── Handover card ───────────────────────────────────────────")
        tell(f"  Case   : {card.case_id}")
        tell(f"  Colour : {card.colour}    Target: {card.target}")
        tell(f"  Approved by: {card.approved_by} ({card.role}) — {card.decision}")
        for citation in card.citations:
            tell(f"    · {citation}")
        if card.missing_vitals:
            tell(f"  Missing: {', '.join(card.missing_vitals)}")
        commit = state.get("commit_result")
        if commit is not None and getattr(commit, "committed", False):
            tell(f"  Queue  : position {commit.position} ({commit.colour})")
        elif commit is not None:
            tell(f"  Queue  : not written — {getattr(commit, 'reason', 'refused')}")
        return
    escalation = state.get("escalation")
    recovery = state.get("recovery")
    clarification = state.get("clarification")
    tell("\n── No priority delivered ───────────────────────────────────")
    if escalation is not None:
        tell(f"  Escalated: {escalation.reason}")
    elif recovery is not None:
        tell(f"  Re-measure: {', '.join(recovery.missing_vitals)} — {recovery.reason}")
    elif clarification is not None:
        tell(f"  Questions: {'; '.join(clarification.questions)}")
        tell(f"  Why: {clarification.reason}")
    else:
        tell("  The run ended without a card (a fail-closed terminal).")


async def run_one(
    intake: Intake,
    db_path: str | Path,
    *,
    online: bool,
    ask: Ask = input,
    tell: Tell = print,
) -> Mapping[str, Any]:
    """Drive one patient through the shipped graph and return its final state.

    ``online`` runs the local model on the complaint (the same ``extract_complaint`` seam the
    desk uses); offline the structured answers are the case. The question path resumes with a
    policy that leaves the next pause intact, so an answer can never approve a priority.
    """
    case = intake.case
    if intake.extraction is not None:
        # A raw note was already read into the typed case (one model call, before the graph).
        extraction = intake.extraction
    elif online:
        extraction = await extract_complaint(case.complaint)
    else:
        extraction = None
    paused = await submit_case(case, db_path, extraction=extraction, note=intake.raw_note)
    if paused.existed:
        tell(
            f"\nThis exact case already has a durable thread ({paused.thread_id}); "
            "nothing was re-run. Change a field or remove the checkpoint file to run it again."
        )
        return paused.result

    payload = paused.payload
    state: Mapping[str, Any] = paused.result
    if payload is not None and is_elicitation(payload):
        form = _clarification_form(payload, ask)
        state = await answer_clarification(paused.thread_id, form, db_path)
        pending = state.get("__interrupt__")
        payload = dict(pending[0].value) if pending else None

    if payload is not None:
        state = await decide(paused.thread_id, _gate_form(payload, ask), db_path)
    return state


def main(
    *,
    db_path: str | Path,
    online: bool,
    note: str | None = None,
    ask: Ask = input,
    tell: Tell = print,
) -> int:
    """The interactive loop: one patient at a time until the operator stops."""
    tell("TriageDesk — interactive terminal triage")
    tell(f"  model: {'local (online)' if online else 'offline (structured input only)'}")
    tell(f"  state: {db_path}")
    tell("  Nothing reaches the queue without your named approval.")
    try:
        if note is not None:
            if not online:
                tell("A raw note needs the model: re-run with --online.")
                return 1
            intake = asyncio.run(_intake_from_note(note))
            tell("\n  The model read this case as:")
            for line in describe_case(intake.case):
                tell(line)
            state = asyncio.run(run_one(intake, db_path, online=online, ask=ask, tell=tell))
            render_outcome(state, tell)
            return 0
        while True:
            intake = collect_case(ask, online=online)
            if intake is None:
                tell("\nStopped.")
                return 0
            state: Mapping[str, Any] | None = None
            try:
                state = asyncio.run(run_one(intake, db_path, online=online, ask=ask, tell=tell))
            except DurableError as exc:
                # The gate's OWN refusal (a blank identity, a missing colour, no pending
                # gate). Nothing was written; show the reason and let the operator retry.
                tell(f"\nThe gate refused the decision: {exc}")
            if state is not None:
                render_outcome(state, tell)
            again = _ask_bool(ask, "\nNext patient?")
            if not again:
                tell("Stopped.")
                return 0
    except _Quit:  # pragma: no cover - terminal dependent
        tell("\nStopped.")
        return 0


async def _intake_from_note(note: str) -> Intake:
    """Read one raw note into an ``Intake`` (the ``--note`` path, no confirmation)."""
    extraction = await extract_note(note)
    return Intake(case=extraction.case, extraction=extraction, raw_note=note)


__all__ = ["Intake", "collect_case", "extract_note", "main", "render_outcome", "run_one"]
