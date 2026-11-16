"""The desk's mid-call question panel (ELICIT-05, ELICIT-08).

One renderer, one shape: when the paused payload is an **elicitation** the surface shows the
questions the server derived, one free-text field each, and a decline control — instead of the
approval gate. The panel deliberately has **no** decision field, no approve/edit/dismiss
control, no colour control and no hidden commit input, so answering a question cannot be
mistaken for approving a priority (a question is not a decision).

The questions, their field names and their order are read from the payload through
``triagedesk.mcp.elicitation`` (the ONE wire vocabulary), never re-derived here: the panel
shows exactly what the server asked. Every rendered string is escaped.

The shipped tool mints exactly one form request, so the panel presents the FIRST form request;
a payload with none renders an explicit "could not be delivered" line rather than an empty
form a nurse might submit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from triagedesk.desk.copy import (
    _QUESTION_ACCEPT,
    _QUESTION_DECLINE,
    _QUESTION_FRAMING,
    _QUESTION_HEADING,
    _QUESTION_UNAVAILABLE,
)
from triagedesk.desk.forms import _csrf_field
from triagedesk.desk.markup import _escaped
from triagedesk.mcp.elicitation import (
    CLARIFICATION_REQUEST_KEY,
    answer_fields,
    answer_prompts,
    form_requests,
)

# The form field prefix the answer inputs carry, so one POST names each answer by its
# question field without colliding with the panel's own controls.
_ANSWER_FIELD_PREFIX = "answer."


def _question_html(
    payload: Mapping[str, Any], thread_id: str, csrf_token: str | None = None
) -> str:
    """Render the question panel for one elicitation payload — a question, not a gate.

    *thread_id* is the paused thread id the ``/clarify`` POST resumes; *csrf_token* is the
    per-server secret every POST must carry (WR-01). A payload with no form request renders
    the "could not be delivered" line and no form, so there is nothing to submit.
    """
    requests = form_requests(payload)
    if not requests:
        return (
            '<section class="clarification-panel" role="status">'
            f"<p>{_escaped(_QUESTION_UNAVAILABLE)}</p></section>"
        )
    request = requests[0]
    request_key = str(request.get("key") or CLARIFICATION_REQUEST_KEY)
    prompts = answer_prompts(request)
    fields = answer_fields(request)
    controls = "".join(
        f'<div class="field"><label for="clarify-{_escaped(field)}">{_escaped(prompt)}</label>'
        f'<input id="clarify-{_escaped(field)}"'
        f' name="{_ANSWER_FIELD_PREFIX}{_escaped(field)}"'
        ' type="text" autocomplete="off"></div>'
        for field, prompt in zip(fields, prompts, strict=False)
    )
    return (
        '<section class="clarification-panel" aria-labelledby="clarification-heading">'
        f'<h2 id="clarification-heading">{_escaped(_QUESTION_HEADING)}</h2>'
        f'<p class="clarification-framing">{_escaped(_QUESTION_FRAMING)}</p>'
        '<form id="clarification-form" method="post" action="/clarify">'
        f"{_csrf_field(csrf_token)}"
        f'<input type="hidden" name="thread_id" value="{_escaped(thread_id)}">'
        f'<input type="hidden" name="request_key" value="{_escaped(request_key)}">'
        f"{controls}"
        '<div class="clarification-actions">'
        '<button type="submit" name="action" value="accept" class="primary">'
        f"{_escaped(_QUESTION_ACCEPT)}</button>"
        '<button type="submit" name="action" value="decline" formnovalidate>'
        f"{_escaped(_QUESTION_DECLINE)}</button>"
        "</div></form></section>"
    )


def answers_from_form(form: Mapping[str, str]) -> dict[str, str]:
    """The posted answers, keyed by question field — the panel's own field prefix only.

    A field the panel did not render is ignored, so a hand-crafted POST cannot introduce an
    answer to a question that was never asked.
    """
    return {
        key[len(_ANSWER_FIELD_PREFIX) :]: value
        for key, value in form.items()
        if key.startswith(_ANSWER_FIELD_PREFIX)
    }


__all__ = ["answers_from_form"]
