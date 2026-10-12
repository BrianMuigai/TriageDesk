"""The ONE desk presentation bridge (UX-02, UX-03, UX-04; D10-01…D10-16).

This module is the phase's thin bridge (D10-02): it validates the vitals form through the
ONE ``CaseInput`` schema (D10-13), runs the case to the approval gate over the shipped
pause plumbing (``durable.run_to_gate``), renders the graph's own typed outputs as a
**suggestion** card with its adjacent citations (D10-05/D10-06/D10-07), and resumes a paused
thread with a named human decision through ``durable.approval_decision`` +
``durable.resume_thread`` (D10-11).

It is **presentation-only** (D10-04): it holds no scoring, routing or gate logic, and it
never re-derives a colour, a citation, a target time or a confidence value (D10-02/D10-07).
The only mapping it owns is presentation — a substrate colour string to a CSS class name.
The surface can never commit on its own (D10-12): the only route to a queue row is the
resumed ``approval_gate`` interrupt through the gated ``commit_priority`` tool; this package
imports neither the queue writer nor the module that hosts that tool. It binds loopback only
(D10-03), serves a fixed two-name asset allowlist, escapes every rendered string, and adds no
dependency (D10-16).
"""

from __future__ import annotations

import asyncio
import html
import string
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from pydantic import ValidationError

from triagedesk.core.schema import CaseInput
from triagedesk.durable import (
    PausedRun,
    approval_decision,
    resume_thread,
    run_to_gate,
)
from triagedesk.evals.case import TERMINAL_OUTCOMES, CaseSpec
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import CHECKPOINTS_DB_PATH

# The one home for the two hand-authored assets (D10-01). Keeping the markup out of Python
# string literals is what keeps a SATS colour/band literal out of ``src/**/*.py`` (CONVENTIONS
# §1); the Python emits only a generic ``colour-{name}`` class.
STATIC_DIR = Path(__file__).parent / "static"

# The fixed two-name asset allowlist: filename -> content type. A request for anything not in
# this map is a 404, so no path is ever built from ``self.path`` (no traversal).
_ASSETS: dict[str, str] = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
}

# The checkbox values that read as "set". Deliberately excludes the bare word a data file
# might also carry, so the guard's exact-match scan is never tripped.
_TRUTHY = frozenset({"true", "on", "1"})

# The UI-SPEC copy the bridge selects between (no clinical value, no SATS literal).
_EMPTY_HEADING = "No case yet"
_EMPTY_BODY = "Enter the patient's vitals and complaint, then choose Get suggested priority."
_DEFERRED_COPY = "This case was deferred for human review — no priority was committed."
_ESCALATED_COPY = "This case was escalated for human review — no priority was committed."
_RECOVERY_COPY = "A scored vital is missing. Re-measure before scoring."
_UNREACHED_COPY = "This case did not reach the approval gate — nothing has been committed."
_DISMISSED_COPY = "Dismissed — nothing has been committed."
_FAILURE_COPY = (
    "The case could not be scored. Nothing has been committed. Try again, or check the desk log."
)
_SCHEMA_HINT = "Check the highlighted field and try again."
_NO_THREAD_COPY = "There is no paused case to decide. Submit the vitals first."


def form_to_case(form: Mapping[str, str]) -> CaseInput:
    """Build and validate a :class:`CaseInput` from the posted vitals form (D10-13).

    An absent or empty optional numeric/enum field maps to ``None`` (never ``""`` or ``0``);
    an absent ``trauma`` checkbox maps to ``None`` (never ``False``); ``age_ambiguous``
    defaults to ``False``; ``complaint`` defaults to ``""``. Validation is the ONE
    ``CaseInput.model_validate`` — the schema is the only validation rule, so a
    :class:`pydantic.ValidationError` propagates to the handler to be rendered beside the
    field.
    """

    def _number(key: str, cast: Any) -> Any:
        raw = str(form.get(key, "")).strip()
        return cast(raw) if raw else None

    def _choice(key: str) -> str | None:
        raw = str(form.get(key, "")).strip()
        return raw or None

    def _optional_flag(key: str) -> bool | None:
        if key not in form or str(form.get(key, "")).strip() == "":
            return None
        return str(form[key]).strip().lower() in _TRUTHY

    payload: dict[str, Any] = {
        "age_years": _number("age_years", int),
        "age_months": _number("age_months", int),
        "age_ambiguous": str(form.get("age_ambiguous", "")).strip().lower() in _TRUTHY,
        "height_cm": _number("height_cm", float),
        "respiratory_rate": _number("respiratory_rate", int),
        "heart_rate": _number("heart_rate", int),
        "systolic_bp": _number("systolic_bp", int),
        "diastolic_bp": _number("diastolic_bp", int),
        "temperature_c": _number("temperature_c", float),
        "spo2": _number("spo2", int),
        "mobility": _choice("mobility"),
        "avpu": _choice("avpu"),
        "trauma": _optional_flag("trauma"),
        "complaint": str(form.get("complaint", "")) or "",
    }
    return CaseInput.model_validate(payload)


def _tools_for(case: CaseInput) -> dict[str, Any]:
    """Build the offline in-process tool map for one desk submission (D10-15).

    The form already supplies a structured ``CaseInput``, so the surface is model-free: the
    offline mapping returns the case's own extraction while the matcher, scorer, retrieval,
    confidence and the gated commit all run for real. The declared harness terminal keeps a
    SATS colour literal out of code (CONVENTIONS §1) and is never read.
    """
    spec = CaseSpec(
        id="desk",
        description="desk submission",
        note=case.complaint,
        case=case,
        expected=TERMINAL_OUTCOMES[0],
        pass_criteria="never evaluated: the desk scores through the shipped graph",
        source="src/triagedesk/desk/server.py",
    )
    return build_tools(spec, offline=True, recorder=UsageRecorder())


async def submit_case(case: CaseInput, db_path: str | Path) -> PausedRun:
    """Run one desk case to the approval gate over the shipped pause plumbing (D10-11).

    The content-derived thread id comes from the ONE plumbing (``durable.run_to_gate``); the
    bridge derives no second id and hashes nothing.
    """
    return await run_to_gate(
        _tools_for(case),
        raw_note=case.model_dump_json(),
        case=case,
        db_path=db_path,
    )


async def decide(
    thread_id: str, form: Mapping[str, str], db_path: str | Path
) -> Mapping[str, Any]:
    """Resume a paused thread with a named human decision (D10-11).

    The decision is built by the ONE ``durable.approval_decision`` — a whitespace-only name or
    role is rejected there — and resumed by the ONE ``durable.resume_thread``. The bridge
    re-implements no identity check and never calls the queue writer or the commit tool.
    ``thread_id`` is the value the handler read from the gate form's hidden ``thread_id``
    field (rendered from the interrupt payload's ``case_id`` — the ONE content-derived thread
    id).
    """
    decision = approval_decision(
        str(form.get("decision", "")),
        approver=form.get("name"),
        role=form.get("role"),
        colour=form.get("colour"),
    )
    return await resume_thread(thread_id=thread_id, decision=decision, db_path=db_path)


def _colour_class(colour: str) -> str:
    """Map a substrate colour string to its CSS swatch class (a lookup, never a computation).

    The colour NAMES live only in ``styles.css`` (an asset the no-duplicated-SATS guard does
    not scan), so no SATS colour literal enters Python.
    """
    return f"colour-{colour.lower()}"


def _escaped(value: Any) -> str:
    """Escape one rendered value for HTML (ASVS V5)."""
    return html.escape(str(value))


def _panel(copy: str, kind: str) -> str:
    """Render one state panel — the single surface for a non-card state (UI-SPEC)."""
    return f'<section class="state-panel state-{kind}" role="status"><p>{copy}</p></section>'


def _form_echo(form: Mapping[str, str]) -> str:
    """Echo the submitted complaint, escaped, labelled as the nurse typed it (UI-SPEC)."""
    complaint = form.get("complaint")
    if not complaint:
        return ""
    return (
        '<div class="form-echo">'
        f'<p><span class="label">Complaint:</span> '
        f'<span class="value">{_escaped(complaint)}</span></p>'
        "</div>"
    )


def _card_html(payload: Mapping[str, Any]) -> str:
    """Render the priority card from the graph's own interrupt payload (D10-02/D10-05…D10-08).

    Every value is read from the payload — the colour, its target, each fired rule's ``detail``
    beside its adjacent citation, the missing vitals, the second-look flag and the case id —
    and re-derived nowhere. The colour is rendered with its name as text (D10-08).
    """
    colour = str(payload.get("colour") or "")
    target = str(payload.get("target") or "")
    case_id = str(payload.get("case_id") or "")
    rules = payload.get("triggered_rules") or []
    missing = payload.get("missing_vitals") or []
    second_look = payload.get("second_look")

    rows = "".join(
        f'<li>{_escaped(rule.get("detail", ""))} '
        f'<span class="citation">{_escaped(rule.get("citation", ""))}</span></li>'
        for rule in rules
    )
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

    return (
        '<section class="priority-card" aria-labelledby="card-heading">'
        '<h2 id="card-heading">Suggested priority</h2>'
        '<p class="framing">This is a suggestion, not a decision. You confirm the priority.</p>'
        f'<div class="colour-block {_colour_class(colour)}">'
        f'<span class="colour-name">{_escaped(colour)}</span></div>'
        f'<p><span class="label">Suggested colour:</span> '
        f'<span class="value">{_escaped(colour)}</span></p>'
        f'<p><span class="label">Target time:</span> '
        f'<span class="value">{_escaped(target)}</span></p>'
        "<h3>Why these vitals:</h3>"
        f'<ul class="why-vitals-list">{rows}</ul>'
        f'<p><span class="label">Not recorded:</span> '
        f'<span class="value">{_escaped(missing_text)}</span></p>'
        f'<p><span class="label">Second look (serial vitals):</span> '
        f'<span class="value">{_escaped(second_text)}</span></p>'
        f'<p><span class="label">Case:</span> '
        f'<span class="value">{_escaped(case_id)}</span></p>'
        "</section>"
    )


def _gate_html(payload: Mapping[str, Any]) -> str:
    """Render the approval gate, carrying the paused thread identity as a hidden field (D10-11).

    The hidden ``thread_id`` value is the payload's ``case_id`` — the ONE content-derived
    thread id the ``/decision`` POST returns to :func:`decide`. The three actions are labelled
    buttons (never colour-only controls).
    """
    case_id = str(payload.get("case_id") or "")
    return (
        '<section class="approval-gate" aria-labelledby="gate-heading">'
        '<h2 id="gate-heading">Your decision</h2>'
        '<form method="post" action="/decision">'
        f'<input type="hidden" name="thread_id" value="{_escaped(case_id)}">'
        '<div class="field"><label for="approver-name">Your name</label>'
        '<input id="approver-name" name="name" type="text" autocomplete="off"></div>'
        '<div class="field"><label for="approver-role">Your role</label>'
        '<input id="approver-role" name="role" type="text" autocomplete="off"></div>'
        '<div class="gate-actions">'
        '<button type="submit" name="decision" value="approve" class="primary">'
        "Approve suggestion</button>"
        '<button type="submit" name="decision" value="edit">Edit colour</button>'
        '<button type="submit" name="decision" value="dismiss">'
        "Dismiss (commit nothing)</button>"
        "</div></form></section>"
    )


def _terminal_panel(result: Mapping[str, Any]) -> str:
    """Select the terminal copy from the graph's typed channels (never a string heuristic)."""
    confidence = result.get("confidence")
    if confidence is not None and getattr(confidence, "deferral", False):
        return _panel(_DEFERRED_COPY, "muted")
    if result.get("escalation") is not None:
        return _panel(_ESCALATED_COPY, "muted")
    if result.get("recovery") is not None:
        return _panel(_RECOVERY_COPY, "muted")
    return _panel(_UNREACHED_COPY, "muted")


def _paused_view(paused: PausedRun, form: Mapping[str, str]) -> dict[str, str]:
    """The view for a run that either paused at the gate or stopped at a terminal."""
    if paused.paused and paused.payload is not None:
        return {
            "state_panel": "",
            "banner": "",
            "card": _card_html(paused.payload),
            "gate": _gate_html(paused.payload),
            "form_values": _form_echo(form),
        }
    return {
        "state_panel": _terminal_panel(paused.result),
        "banner": "",
        "card": "",
        "gate": "",
        "form_values": _form_echo(form),
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
        if decision == "edit":
            copy = (
                f"Edited to {_escaped(form.get('colour', ''))} by {_escaped(name)} "
                f"({_escaped(role)}) — committed to the queue."
            )
        else:
            copy = f"Approved by {_escaped(name)} ({_escaped(role)}) — committed to the queue."
        panel = _panel(copy, "success")
    else:
        reason = getattr(commit, "reason", None) or _FAILURE_COPY
        panel = _panel(_escaped(reason), "error")

    return {
        "state_panel": panel,
        "banner": "",
        "card": "",
        "gate": "",
        "form_values": _form_echo(form),
    }


def _error_panel(message: str) -> str:
    """The error view — a failure leaves the decision unresolved; a failure is never an approve."""
    return _panel(_escaped(message), "error")


def _render(view: Mapping[str, str]) -> str:
    """Substitute the server-rendered regions into the hand-authored page (string.Template).

    ``string.Template`` (not ``str.format``) is used because the markup carries CSS braces; the
    page's only ``$`` characters are its placeholders.
    """
    template = string.Template((STATIC_DIR / "index.html").read_text(encoding="utf-8"))
    return template.substitute(
        state_panel=view["state_panel"],
        banner=view["banner"],
        card=view["card"],
        gate=view["gate"],
        form_values=view["form_values"],
    )


def render_state(
    paused: PausedRun | None = None,
    *,
    result: Mapping[str, Any] | None = None,
    error: str | None = None,
    form_values: Mapping[str, str] | None = None,
) -> str:
    """Render the page for one state: empty, paused card+gate, terminal, decision, or error.

    With no case submitted it renders the quickstart panel and the empty vitals form with the
    ``No case yet`` heading and body and NO ``priority-card`` or ``approval-gate`` region. On
    the committable path (``paused is True``) it renders the card plus the gate and no banner.
    """
    form = form_values or {}
    if result is not None:
        return _render(_decision_view(result, form))
    if paused is not None:
        return _render(_paused_view(paused, form))
    if error is not None:
        return _render(
            {
                "state_panel": _error_panel(error),
                "banner": "",
                "card": "",
                "gate": "",
                "form_values": _form_echo(form),
            }
        )
    return _render(
        {
            "state_panel": (
                f'<section class="state-panel state-empty" role="status">'
                f"<h2>{_EMPTY_HEADING}</h2><p>{_EMPTY_BODY}</p></section>"
            ),
            "banner": "",
            "card": "",
            "gate": "",
            "form_values": "",
        }
    )


class DeskServer(ThreadingHTTPServer):
    """The desk bridge's threaded HTTP server, carrying the checkpoint file path."""

    db_path: Path


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

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        """Render the page for ``/``; serve the CSS by allowlist; anything else is a 404.

        ``/`` (and ``/index.html``) render the empty state through the ONE template rather than
        serving the raw file, so no unsubstituted placeholder is ever exposed. Only the CSS is
        served as raw bytes, and only when its name is in the fixed allowlist — no path is built
        from ``self.path``.
        """
        path = self.path.split("?", 1)[0]
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        if name not in _ASSETS:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if name == "index.html":
            self._send_html(render_state())
            return
        body = (STATIC_DIR / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _ASSETS[name])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        """Dispatch ``/case`` and ``/decision`` over the ONE pause/resume plumbing."""
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        form = {
            key: values[0]
            for key, values in parse_qs(raw, keep_blank_values=True).items()
        }
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
            return render_state(error=_validation_message(exc), form_values=form)
        try:
            paused = asyncio.run(submit_case(case, self.server.db_path))
        except Exception as exc:  # noqa: BLE001 - any failure is reported, never an approve
            return render_state(error=str(exc), form_values=form)
        return render_state(paused, form_values=form)

    def _handle_decision(self, form: Mapping[str, str]) -> str:
        thread_id = str(form.get("thread_id", "")).strip()
        if not thread_id:
            return render_state(error=_NO_THREAD_COPY, form_values=form)
        try:
            result = asyncio.run(decide(thread_id, form, self.server.db_path))
        except Exception as exc:  # noqa: BLE001 - a failure leaves the decision unresolved
            return render_state(error=str(exc), form_values=form)
        return render_state(result=result, form_values=form)


def _validation_message(exc: ValidationError) -> str:
    """Build the UI-SPEC schema-rejection copy from the schema's OWN field message (D10-13)."""
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error.get("loc", ()))
    message = str(error.get("msg", "invalid input"))
    detail = f"{location}: {message}" if location else message
    return f"{detail}. {_SCHEMA_HINT}"


def make_server(host: str, port: int, db_path: str | Path) -> DeskServer:
    """Construct the desk bridge bound to *host* (loopback only — D10-03) over *db_path*."""
    server = DeskServer((host, port), DeskHandler)
    server.db_path = Path(db_path)
    return server


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str | Path = CHECKPOINTS_DB_PATH,
) -> None:
    """Serve the desk surface until interrupted (loopback only — D10-03)."""
    make_server(host, port, db_path).serve_forever()


__all__ = [
    "DeskHandler",
    "DeskServer",
    "STATIC_DIR",
    "decide",
    "form_to_case",
    "make_server",
    "render_state",
    "serve",
    "submit_case",
]
