"""The ONE elicitation wire vocabulary (ELICIT-02, ELICIT-05, ELICIT-07).

One module owns every string and shape the elicitation round-trip speaks, so the server, the
CLI and the desk cannot drift apart:

* the **request key** the tool mints (``CLARIFICATION_REQUEST_KEY``) — a resumed answer is
  keyed by it, so the tool and the resume builder must agree;
* the **form property names** (``q1..qN``, via :func:`answer_field`) — the tool builds the
  schema with them and the surfaces read the answers back by them;
* the **resume value** shape ``{"responses": {key: {"action": ...}}}``, built by
  :func:`accept_responses` / :func:`decline_responses` — never restated at a call site;
* the **interrupt discriminator** comparison (:func:`is_elicitation`), which reads the ONE
  declaration in ``core.schema.InterruptType`` rather than a second literal.

The ``mcp_elicitation`` value itself is declared in ``core.schema.InterruptType`` because it
is a contract between the graph, the shipped adapter and the surfaces. ``tests/
test_elicitation_tool.py`` asserts it equals ``langchain.mcp.elicitation.
ELICITATION_INTERRUPT_TYPE``, so the contract cannot drift while this module — and therefore
the CLI's import path — stays free of the ``langchain.mcp`` import (and its beta warning).

Deliberately dependency-light: nothing here imports ``mcp.server`` (the desk's import guard
forbids reaching the commit host), ``store`` or ``llm``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from triagedesk.core.schema import InterruptType

# The one request key the tool mints for its form. A resumed answer is addressed by it.
CLARIFICATION_REQUEST_KEY = "clarification"

# The form property names the tool builds: q1, q2, … (MCP elicitation admits primitive
# properties only, so a flat string field per question is the only spec-valid shape).
ANSWER_FIELD_PREFIX = "q"

# The action values the wire accepts (mirrors ``langchain.mcp.elicitation._ACTIONS``).
ACCEPT = "accept"
DECLINE = "decline"


def answer_field(index: int) -> str:
    """The form property name for the *index*-th question (1-based) — the ONE naming rule."""
    return f"{ANSWER_FIELD_PREFIX}{index}"


def is_elicitation(payload: Mapping[str, Any] | None) -> bool:
    """True when *payload* is an elicitation interrupt rather than an approval one.

    Reads the ONE discriminator declaration (``core.schema.InterruptType``) so no surface
    repeats the literal. A payload with no ``type`` is not an elicitation: the approval gate
    is the pre-existing shape and must keep its meaning.
    """
    if not isinstance(payload, Mapping):
        return False
    return payload.get("type") == InterruptType.ELICITATION


def form_requests(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The form-mode requests in *payload*, in the order the server asked them.

    A ``url``-mode request asks the human to visit an address; this system has nothing to
    send them to, so it is not a question these surfaces can answer and is not offered.
    """
    requests = payload.get("requests") or []
    return [
        request
        for request in requests
        if isinstance(request, Mapping) and request.get("mode") == "form"
    ]


def answer_fields(request: Mapping[str, Any]) -> list[str]:
    """The property names of one form request, in schema order (the answer order)."""
    schema = request.get("requested_schema")
    properties = schema.get("properties") if isinstance(schema, Mapping) else None
    return list(properties) if isinstance(properties, Mapping) else []


def answer_prompts(request: Mapping[str, Any]) -> list[str]:
    """The human-facing text of each answer field, in schema order.

    The property's ``description`` (where the server puts the derived question) wins, then
    its ``title``, then the bare field name. Presentation only — never a value, never a
    clinical fact.
    """
    schema = request.get("requested_schema")
    properties = schema.get("properties") if isinstance(schema, Mapping) else None
    if not isinstance(properties, Mapping):
        return []
    prompts: list[str] = []
    for name, property_schema in properties.items():
        spec = property_schema if isinstance(property_schema, Mapping) else {}
        prompts.append(str(spec.get("description") or spec.get("title") or name))
    return prompts


def accept_responses(request_key: str, answers: Mapping[str, str]) -> dict[str, Any]:
    """Build the resume value for an ACCEPTED form — the ONE place the shape is written.

    Blank and whitespace-only answers are omitted: an empty string is the absence of an
    observation, not an observation of emptiness, and carrying it as an answer would let a
    nurse's untouched field become a finding (ELICIT-03/08).
    """
    content = {
        field: value
        for field, value in answers.items()
        if isinstance(value, str) and value.strip()
    }
    return {"responses": {request_key: {"action": ACCEPT, "content": content}}}


def decline_responses(request_key: str) -> dict[str, Any]:
    """Build the resume value for a DECLINE — no content, so no answer can be inferred.

    This is also the documented default when a surface has no answer to give: declining is
    the honest action, because a refusal is never converted into a value (ELICIT-03).
    """
    return {"responses": {request_key: {"action": DECLINE}}}


def answers_in_order(fields: Sequence[str], supplied: Sequence[str]) -> dict[str, str]:
    """Pair repeated surface answers with the question fields, in order.

    Extra supplied answers are ignored (a surface cannot invent a question), and missing
    ones simply leave the field unanswered.
    """
    return {field: value for field, value in zip(fields, supplied, strict=False)}


__all__ = [
    "ACCEPT",
    "ANSWER_FIELD_PREFIX",
    "CLARIFICATION_REQUEST_KEY",
    "DECLINE",
    "accept_responses",
    "answer_field",
    "answer_fields",
    "answer_prompts",
    "answers_in_order",
    "decline_responses",
    "form_requests",
    "is_elicitation",
]
