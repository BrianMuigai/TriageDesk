"""The desk's chat transcript — a presentation-only projection of one triage turn.

The conversation is not a second decision path. Every bubble is built from text or typed
values the rest of the desk already produced: the nurse's complaint/note, the grounded
extraction, the scored priority, the question, the gate, and the terminal outcome. This
module never scores, approves, commits, or writes a queue row (SOLID: S).

Markup lives in ``static/``; this module emits only escaped, semantic fragments and the
generic ``colour-{name}`` class through the ONE mapping in :mod:`triagedesk.desk.card`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.desk.card import _colour_class
from triagedesk.desk.copy import (
    _CHAT_ASSISTANT,
    _CHAT_EXTRACTION_BODY,
    _CHAT_EXTRACTION_HEADING,
    _CHAT_EXTRACTION_NOT_STATED,
    _CHAT_HANDOVER_APPROVED_BY,
    _CHAT_HANDOVER_CASE,
    _CHAT_HANDOVER_CITATIONS,
    _CHAT_HANDOVER_DECISION,
    _CHAT_HANDOVER_FRAMING,
    _CHAT_HANDOVER_HEADING,
    _CHAT_HANDOVER_MCP,
    _CHAT_HANDOVER_NONE,
    _CHAT_HANDOVER_NOT_RECORDED,
    _CHAT_HANDOVER_PRIORITY,
    _CHAT_HANDOVER_QUEUE,
    _CHAT_HANDOVER_SECOND_LOOK,
    _CHAT_HANDOVER_TARGET,
    _CHAT_NOTE_FAILED,
    _CHAT_NOTE_OFFLINE,
    _CHAT_NURSE,
    _CHAT_WELCOME_BODY,
    _CHAT_WELCOME_LEAD,
    _CHAT_WELCOME_STEPS,
)
from triagedesk.desk.forms import _VITALS_LAYOUT
from triagedesk.desk.markup import _escaped


def _bubble(role: str, author: str, body: str) -> str:
    """One chat message: a labelled speaker and an already-safe body fragment."""
    return (
        f'<article class="chat-message {_escaped(role)}">'
        f'<p class="chat-author">{_escaped(author)}</p>'
        f'<div class="chat-body">{body}</div>'
        "</article>"
    )


def welcome_bubble() -> str:
    """The assistant's opening message — scope, the safe sequence, and the approval rule."""
    body = (
        f'<p class="chat-lead">{_escaped(_CHAT_WELCOME_LEAD)}</p>'
        f'<p class="chat-copy">{_escaped(_CHAT_WELCOME_BODY)}</p>'
        f'<p class="chat-steps">{_escaped(_CHAT_WELCOME_STEPS)}</p>'
    )
    return _bubble("assistant", _CHAT_ASSISTANT, body)


def nurse_bubble(text: str) -> str:
    """The nurse's own words: the presenting complaint, or a pasted note."""
    return _bubble("nurse", _CHAT_NURSE, f"<p>{_escaped(text)}</p>")


def _stated_fields(case: CaseInput) -> tuple[list[tuple[str, str]], list[str]]:
    """The fields the extraction actually stated, and the labels it left unstated.

    Labels come from the ONE clinical layout in ``desk.forms``; a blank value is reported as
    unstated and is never imputed. ``age_ambiguous`` is only shown when true, because a false
    default is not a statement the note made.
    """
    stated: list[tuple[str, str]] = []
    unstated: list[str] = []
    for name, label in _VITALS_LAYOUT:
        if name == "complaint":
            continue
        value = getattr(case, name)
        if name == "age_ambiguous":
            if value:
                stated.append((label, "Flagged"))
            continue
        if value is None or value == "":
            unstated.append(label)
            continue
        if name == "trauma":
            stated.append((label, "Present" if value else "Absent"))
        else:
            stated.append((label, str(value)))
    if case.complaint.strip():
        stated.append(("Complaint", case.complaint.strip()))
    else:
        unstated.append("Complaint")
    return stated, unstated


def extraction_bubble(extraction: ExtractionResult) -> str:
    """The grounded read of a pasted note — stated facts beside the honest gaps."""
    stated, unstated = _stated_fields(extraction.case)
    rows = "".join(
        f"<dt>{_escaped(label)}</dt><dd>{_escaped(value)}</dd>" for label, value in stated
    )
    stated_block = (
        f'<dl class="chat-facts">{rows}</dl>'
        if rows
        else '<p class="chat-copy">No field could be read from the note.</p>'
    )
    missing = (
        f'<p class="chat-missing"><span class="label">'
        f"{_escaped(_CHAT_EXTRACTION_NOT_STATED)}:</span> "
        f"{_escaped(', '.join(unstated))}</p>"
        if unstated
        else ""
    )
    body = (
        f'<p class="chat-lead">{_escaped(_CHAT_EXTRACTION_HEADING)}</p>'
        f'<p class="chat-copy">{_escaped(_CHAT_EXTRACTION_BODY)}</p>'
        f"{stated_block}{missing}"
    )
    return _bubble("assistant", _CHAT_ASSISTANT, body)


def note_offline_bubble() -> str:
    """The offline note path: the text becomes the complaint; the form still scores."""
    return _bubble(
        "assistant",
        _CHAT_ASSISTANT,
        f'<p class="chat-copy">{_escaped(_CHAT_NOTE_OFFLINE)}</p>',
    )


def note_failed_bubble() -> str:
    """A failed online extraction is reported, never converted into a score."""
    return _bubble(
        "assistant",
        _CHAT_ASSISTANT,
        f'<p class="chat-copy">{_escaped(_CHAT_NOTE_FAILED)}</p>',
    )


def _fact(label: str, value: Any) -> str:
    """One labelled fact in the handover summary."""
    return (
        f'<div class="handover-fact"><dt>{_escaped(label)}</dt>'
        f"<dd>{_escaped(str(value))}</dd></div>"
    )


def _decision_label(value: str) -> str:
    """The human label for a recorded decision (presentation only)."""
    return {
        "approve": "Approved",
        "edit": "Edited",
        "dismiss": "Dismissed",
    }.get(value, value)


def handover_html(handover: Any, commit: Any = None) -> str:
    """Render the approved handover from the graph's typed ``HandoverCard`` (D-11).

    The same sourced facts the MCP server exposes: the committed colour and target, the named
    approver and decision, the citations, the missing vitals and the serial-vitals flag. The
    card is explicitly a read-only projection; the queue row and audit chain stay
    authoritative.
    """
    colour = str(getattr(handover, "colour", "") or "")
    target = str(getattr(handover, "target", "") or "")
    decision = str(getattr(handover, "decision", "") or "")
    approver = str(getattr(handover, "approved_by", "") or "")
    role = str(getattr(handover, "role", "") or "")
    case_id = str(getattr(handover, "case_id", "") or "")
    position = getattr(commit, "position", None)

    swatch = (
        f'<div class="colour-block {_escaped(_colour_class(colour))}">'
        f'<span class="colour-name">{_escaped(colour)}</span></div>'
        if colour
        else ""
    )
    facts = "".join(
        part
        for part in (
            _fact(_CHAT_HANDOVER_CASE, case_id) if case_id else "",
            _fact(_CHAT_HANDOVER_PRIORITY, colour) if colour else "",
            _fact(_CHAT_HANDOVER_TARGET, target) if target else "",
            _fact(
                _CHAT_HANDOVER_APPROVED_BY,
                f"{approver} ({role})" if approver and role else approver or "—",
            ),
            _fact(_CHAT_HANDOVER_DECISION, _decision_label(decision)) if decision else "",
            _fact(_CHAT_HANDOVER_QUEUE, position) if position is not None else "",
        )
        if part
    )
    citations = list(getattr(handover, "citations", None) or [])
    citation_rows = "".join(
        f'<li class="citation">{_escaped(citation)}</li>' for citation in citations
    )
    citation_list = citation_rows if citation_rows else f"<li>{_escaped(_CHAT_HANDOVER_NONE)}</li>"
    missing = list(getattr(handover, "missing_vitals", None) or [])
    second_look = getattr(handover, "second_look", None)
    if second_look is not None and bool(getattr(second_look, "flag", False)):
        deteriorations = list(getattr(second_look, "deteriorations", None) or [])
        second_text = ", ".join(str(item) for item in deteriorations) or "Flagged"
    else:
        second_text = _CHAT_HANDOVER_NONE
    return (
        '<section class="handover-card" aria-labelledby="handover-heading">'
        f'<h2 id="handover-heading">{_escaped(_CHAT_HANDOVER_HEADING)}</h2>'
        f'<p class="framing">{_escaped(_CHAT_HANDOVER_FRAMING)}</p>'
        f"{swatch}"
        f'<dl class="handover-facts">{facts}</dl>'
        f"<h3>{_escaped(_CHAT_HANDOVER_CITATIONS)}</h3>"
        f'<ul class="evidence-list">{citation_list}</ul>'
        f'<p class="handover-fact-inline"><span class="label">'
        f"{_escaped(_CHAT_HANDOVER_NOT_RECORDED)}:</span> "
        f"{_escaped(', '.join(str(item) for item in missing) or _CHAT_HANDOVER_NONE)}</p>"
        f'<p class="handover-fact-inline"><span class="label">'
        f"{_escaped(_CHAT_HANDOVER_SECOND_LOOK)}:</span> "
        f"{_escaped(second_text)}</p>"
        f'<p class="handover-mcp">{_escaped(_CHAT_HANDOVER_MCP)}</p>'
        "</section>"
    )


def transcript(
    form: Mapping[str, str],
    *,
    note: str | None = None,
    extraction: ExtractionResult | None = None,
    note_failed: bool = False,
) -> str:
    """Assemble the transcript for the current request — no hidden state, no history store.

    Every page is a projection of the request that produced it: the welcome guidance, the
    nurse's words (a note when one was sent, else the complaint already in the form), and the
    extraction summary when the note was read. The scored result, question, gate and terminal
    render beside this transcript in their own chat bubble.
    """
    bubbles = [welcome_bubble()]
    complaint = str(form.get("complaint", "")).strip()
    if note:
        bubbles.append(nurse_bubble(note))
    elif complaint:
        bubbles.append(nurse_bubble(complaint))
    if note_failed:
        bubbles.append(note_failed_bubble())
    elif extraction is not None:
        bubbles.append(extraction_bubble(extraction))
    elif note:
        bubbles.append(note_offline_bubble())
    return "".join(bubbles)


__all__ = [
    "extraction_bubble",
    "handover_html",
    "note_failed_bubble",
    "note_offline_bubble",
    "nurse_bubble",
    "transcript",
    "welcome_bubble",
]
