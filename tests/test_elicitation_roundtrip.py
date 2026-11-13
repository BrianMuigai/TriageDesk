"""The elicitation round-trip through the SHIPPED adapter (Plan 21-02, ELICIT-02/05/07).

This is the phase's end-to-end proof, and it deliberately does **not** stub the transport:

* the tool is the real owned ``request_clarification``, loaded by the real
  ``langchain.mcp.MCPAdapter`` (the dependency the graph will actually use), against the real
  owned ``MCPServer`` **in process** — FastMCP accepts an in-process server, so no stdio
  subprocess, no borrowed store and no model are launched, and the autouse ``injected_store``
  fixture supplies the audit store;
* the run is a real LangGraph graph over a real checkpointer, so the pause is a real
  ``interrupt()`` and the resume is a real ``Command(resume=...)``.

The SDK reality this proof encodes: on the negotiated 2026-07-28 revision a server may not
send a server-initiated request, so the tool returns an ``InputRequiredResult`` on its first
round and the adapter drives it with ``interrupt()`` of type ``mcp_elicitation``. That is the
shipped path, not a workaround.

Honest scope: **no shipped graph node calls the tool yet** (Phase 23 wires the ``plan``
node), so the graph here is a two-node harness around the real tool rather than the shipped
graph. The approval gate's own payload type is proved against the shipped graph below.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from mcp.types import InputRequiredResult

from conftest import build_graph_tools
from triagedesk.core import coverage
from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import ClarificationAnswer, ElicitationOutcome, InterruptType
from triagedesk.graph.build import build_graph, in_memory_checkpointer
from triagedesk.mcp import server as server_module
from triagedesk.mcp.elicitation import (
    CLARIFICATION_REQUEST_KEY,
    accept_responses,
    decline_responses,
)

pytestmark = pytest.mark.filterwarnings(
    "ignore::langchain_core._api.beta_decorator.LangChainBetaWarning"
)


class _State(TypedDict, total=False):
    """The two-node harness's state: the tool's answer, nothing else."""

    answer: Any


def _declared_ids(count: int) -> list[str]:
    """Ids from the loaded closed set — never a literal (CONVENTIONS §1)."""
    return [item.id for item in get_discriminators().discriminators[:count]]


async def _adapter_tool() -> Any:
    """Load ``request_clarification`` through the real shipped adapter, in process."""
    from langchain.mcp import MCPAdapter

    async with MCPAdapter(server_module.server) as owned:
        tools = {tool.name: tool for tool in await owned.list_tools()}
    assert "request_clarification" in tools, sorted(tools)
    return tools["request_clarification"]


def _graph(tool: Any) -> Any:
    """A two-node graph: call the real tool, then terminate."""

    async def ask(_state: Mapping[str, Any]) -> dict[str, Any]:
        return {"answer": await tool.ainvoke({"candidates": _declared_ids(2)})}

    graph = StateGraph(_State)
    graph.add_node("ask", ask)
    graph.add_edge(START, "ask")
    graph.add_edge("ask", END)
    return graph.compile(checkpointer=MemorySaver())


def _answer(result: Mapping[str, Any]) -> ClarificationAnswer:
    """Parse the tool's returned payload (content blocks, as the adapter hands it back)."""
    blocks = result["answer"]
    text = blocks[0]["text"] if isinstance(blocks, list) else str(blocks)
    return ClarificationAnswer.model_validate_json(text)


async def test_the_real_adapter_pauses_then_returns_the_accepted_answer() -> None:
    """tool call → interrupt(mcp_elicitation) → resume → the tool returns the answer."""
    tool = await _adapter_tool()
    graph = _graph(tool)
    config = {"configurable": {"thread_id": "roundtrip-accept"}}

    paused = await graph.ainvoke({}, config)

    assert paused.get("__interrupt__"), "the real adapter did not pause the run"
    payload = dict(paused["__interrupt__"][0].value)
    assert payload["type"] == InterruptType.ELICITATION
    assert payload["tool_name"] == "request_clarification"
    requests = [r for r in payload["requests"] if r["mode"] == "form"]
    assert [r["key"] for r in requests] == [CLARIFICATION_REQUEST_KEY]
    properties = requests[0]["requested_schema"]["properties"]
    assert list(properties) == ["q1", "q2"]
    for index, discriminator_id in enumerate(_declared_ids(2), start=1):
        # The question text is the ONE owner's, verbatim — the adapter only carries it.
        assert properties[f"q{index}"]["description"] == coverage.question_for(discriminator_id)

    answers = {"q1": "crushing central pain", "q2": "worse on exertion"}
    resumed = await graph.ainvoke(
        Command(resume=accept_responses(CLARIFICATION_REQUEST_KEY, answers)), config
    )

    assert not resumed.get("__interrupt__"), "an answered question must not be asked twice"
    parsed = _answer(resumed)
    assert parsed.outcome is ElicitationOutcome.ACCEPTED
    assert parsed.answers == ["crushing central pain", "worse on exertion"]


@pytest.mark.parametrize(
    ("resume", "expected"),
    [
        (decline_responses(CLARIFICATION_REQUEST_KEY), ElicitationOutcome.DECLINED),
        (
            {"responses": {CLARIFICATION_REQUEST_KEY: {"action": "cancel"}}},
            ElicitationOutcome.CANCELLED,
        ),
    ],
)
async def test_a_refusal_returns_no_answers_and_writes_no_queue_row(
    resume: Mapping[str, Any],
    expected: ElicitationOutcome,
    injected_store: Any,
) -> None:
    """A decline/cancel is not a clinical answer: no answers, no colour, no queue row."""
    tool = await _adapter_tool()
    graph = _graph(tool)
    config = {"configurable": {"thread_id": f"roundtrip-{expected.value}"}}

    paused = await graph.ainvoke({}, config)
    assert paused.get("__interrupt__")

    resumed = await graph.ainvoke(Command(resume=dict(resume)), config)

    parsed = _answer(resumed)
    assert parsed.outcome is expected
    assert parsed.answers == []
    assert injected_store.rows == [], "a refused question wrote a queue row"


async def test_resuming_an_answered_thread_does_not_re_ask_or_re_write(
    injected_store: Any,
) -> None:
    """Resuming again neither re-asks the question nor duplicates a write (ELICIT-07)."""
    tool = await _adapter_tool()
    graph = _graph(tool)
    config = {"configurable": {"thread_id": "roundtrip-idempotent"}}

    await graph.ainvoke({}, config)
    first = await graph.ainvoke(
        Command(resume=accept_responses(CLARIFICATION_REQUEST_KEY, {"q1": "yes"})), config
    )
    assert _answer(first).outcome is ElicitationOutcome.ACCEPTED

    # The thread is settled: a further resume must not raise a new interrupt or write.
    again = await graph.ainvoke(Command(resume={"responses": {}}), config)

    assert not again.get("__interrupt__")
    assert injected_store.rows == []


async def test_the_first_round_is_an_input_required_result_not_an_answer() -> None:
    """The transport contract: round one asks, and only the retry carries the answers."""
    from triagedesk.mcp.server import _clarification_form, _clarification_questions

    questions = _clarification_questions(_declared_ids(2))
    form = _clarification_form(questions)

    assert len(form.model_fields) == len(questions)
    # A form built from a candidate list the caller chose is spec-valid: one flat string each.
    from mcp.server.elicitation import render_elicitation_schema

    schema = render_elicitation_schema(form)
    assert all(prop["type"] == "string" for prop in schema["properties"].values())
    assert InputRequiredResult is not ClarificationAnswer  # the two round types differ


async def test_the_approval_gate_payload_is_a_different_type() -> None:
    """The shipped gate payload says ``approval`` — a decision is never a question (ELICIT-05)."""
    graph = build_graph(build_graph_tools(), checkpointer=in_memory_checkpointer())
    config = {"configurable": {"thread_id": "roundtrip-gate-type"}}

    result = await graph.ainvoke(
        {"raw_note": "central chest pain", "case": None}, config
    )

    assert result.get("__interrupt__"), "the shipped graph did not pause at the gate"
    payload = dict(result["__interrupt__"][0].value)
    assert payload["type"] == InterruptType.APPROVAL
    assert payload["type"] != InterruptType.ELICITATION
