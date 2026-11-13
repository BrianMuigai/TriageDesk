"""Durable restart + exactly-once proof suite (Plan 06-02, AGENT-01, D6-12, D6-13).

Proves the headline durable properties against the REAL owned tools over a REAL SQLite
checkpointer:

1. a case paused at the approval gate resumes to ONE committed handover row after a
   restart (two separate ``checkpointed_graph`` instances over one file), with each
   owned tool's audit count exactly 1 — no pre-gate tool is replayed;
2. the durable ``thread_id`` is the stripped-note content hash, recomputable by hand;
3. resuming a thread with no pending gate raises ``DurableError`` naming the thread id
   and the checkpoint file.

The tools are the real owned tools called in-process (only the model is stubbed, via the
one ``extract_async`` seam), and the store is the shared in-memory double — so the suite
launches no borrowed ``npx mcp-sqlite`` subprocess and no model.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from conftest import async_return
from triagedesk.core.rules import get_tews
from triagedesk.core.schema import ExtractionResult, InterruptType
from triagedesk.durable import (
    DurableError,
    approval_decision,
    derive_thread_id,
    invoke_graph,
    pending_interrupt,
    resume_paused,
    run_to_gate,
)
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import checkpointed_graph
from triagedesk.graph.nodes import case_id_for, case_id_for_note
from triagedesk.mcp import server as server_module
from triagedesk.mcp.elicitation import CLARIFICATION_REQUEST_KEY, decline_responses
from triagedesk.store.queue import content_hash

CASES_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"

# A declared substrate colour the E-02 case does NOT score, so an edit decision supersedes
# the row's colour in place (the durable analogue of the 06-01 key contract).
EDITED_COLOUR = "GREEN"

# The four owned tools a delivered case reaches; each must run exactly ONCE across a
# restart (no pre-gate replay). ``raise_recheck_flag`` is excluded: E-02 has no serial
# previous case, so the recheck node returns without a tool call.
ONCE_PER_TOOL = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "commit_priority",
)


def _case(case_id: str) -> CaseSpec:
    """Load one bundled eval case by id (the fixture is the declared input)."""
    return next(case for case in load_cases(CASES_DIR) if case.id == case_id)


async def test_restart_resumes_to_one_row_and_one_commit_audit(
    tmp_path: Path, injected_store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A paused case survives a restart: one queue row, one audit record per tool (D6-12)."""
    case = _case("E-02")
    # The model is stubbed through the ONE owned ``extract_async`` seam, so ``normalize_case``
    # runs as the real audited owned tool with no model call (offline, deterministic).
    monkeypatch.setattr(
        server_module,
        "extract_async",
        async_return(ExtractionResult(case=case.case, matched_discriminator_ids=[])),
    )
    tools = build_tools(case, offline=False, recorder=UsageRecorder())
    thread_id = derive_thread_id(case.note)
    config = {"configurable": {"thread_id": thread_id}}
    db_path = tmp_path / "checkpoints.db"

    # Process 1: run the case to the approval gate on the durable saver.
    async with checkpointed_graph(tools, db_path) as first:
        paused = await first.ainvoke({"raw_note": case.note, "case": case.case}, config)
        assert paused.get("__interrupt__"), "the first process did not pause at the gate"

    # Process 2: a FRESH saver over the SAME file (a real restart) resumes to a commit.
    async with checkpointed_graph(tools, db_path) as second:
        snapshot = await second.aget_state(config)
        assert snapshot.next == ("approval_gate",), f"pending node drifted: {snapshot.next}"
        await second.ainvoke(
            Command(
                resume=approval_decision(
                    "approve", approver="Dr A. Nurse", role="triage clinician"
                )
            ),
            config,
        )

    rows = await injected_store.read_queue_rows()
    assert len(rows) == 1, "a restart duplicated the queue row"
    counts = Counter(record.tool for record in injected_store.audit_records)
    for tool in ONCE_PER_TOOL:
        assert counts[tool] == 1, f"{tool} ran {counts[tool]} times across the restart"


def test_thread_id_is_the_stripped_note_hash() -> None:
    """``derive_thread_id`` is the one content hash of the stripped note (D6-01, Pitfall 5)."""
    note = _case("E-02").note
    assert derive_thread_id(note) == case_id_for(note.strip())
    # The strip-then-derive rule lives once, in the shared note normaliser (WR-05).
    assert derive_thread_id(note) == case_id_for_note(note)
    # Surrounding whitespace never changes the id — the same stripped value the gate uses.
    assert derive_thread_id(f"  {note}  ") == derive_thread_id(note)


async def test_no_pending_thread_raises_naming_thread_and_db(tmp_path: Path) -> None:
    """Resuming an unknown thread raises ``DurableError`` naming the thread and file."""
    case = _case("E-02")
    tools = build_tools(case, offline=True, recorder=UsageRecorder())
    db_path = tmp_path / "checkpoints.db"

    with pytest.raises(DurableError) as excinfo:
        await resume_paused(
            tools,
            thread_id="absent-thread",
            decision={"decision": "dismiss"},
            db_path=db_path,
        )

    message = str(excinfo.value)
    assert "absent-thread" in message
    assert str(db_path) in message


async def test_edit_resume_supersedes_on_the_durable_path(
    tmp_path: Path, injected_store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An edit on the durable path supersedes the row in place — one row, edited colour (D6-06).

    Two separate paused threads of the SAME case (fresh checkpoint files, one shared
    store) are resumed with different decisions: the first ``approve``s the scored colour,
    the second ``edit``s it. The queue key covers the immutable case input, so both
    re-derive the SAME key and exactly one row exists — its colour is the edited colour,
    its position is unchanged, and its ``content_hash`` is colour-independent.
    """
    case = _case("E-02")
    monkeypatch.setattr(
        server_module,
        "extract_async",
        async_return(ExtractionResult(case=case.case, matched_discriminator_ids=[])),
    )
    tools = build_tools(case, offline=False, recorder=UsageRecorder())
    thread_id = derive_thread_id(case.note)
    approver, role = "Dr A. Nurse", "triage clinician"

    # Two fresh paused threads for the same case (same thread_id, separate checkpoint files).
    first = await run_to_gate(
        tools, raw_note=case.note, case=case.case, db_path=tmp_path / "thread-a.db"
    )
    second = await run_to_gate(
        tools, raw_note=case.note, case=case.case, db_path=tmp_path / "thread-b.db"
    )
    assert first.paused and second.paused
    assert first.thread_id == second.thread_id == thread_id

    # Thread 1: approve the scored colour.
    approved = await resume_paused(
        tools,
        thread_id=thread_id,
        decision=approval_decision("approve", approver=approver, role=role),
        db_path=tmp_path / "thread-a.db",
    )
    rows = await injected_store.read_queue_rows()
    assert len(rows) == 1
    scored_colour, scored_target, position = rows[0].colour, rows[0].target, rows[0].position
    assert scored_colour != EDITED_COLOUR, "the edit must change the committed colour"
    # The card shows what the queue holds: the scored colour and target on an approve.
    assert approved["handover"].colour == scored_colour
    assert approved["handover"].target == scored_target

    # Thread 2: edit the SAME case to a different declared colour — it supersedes in place.
    edited = await resume_paused(
        tools,
        thread_id=thread_id,
        decision=approval_decision(
            "edit", approver=approver, role=role, colour=EDITED_COLOUR
        ),
        db_path=tmp_path / "thread-b.db",
    )

    rows = await injected_store.read_queue_rows()
    assert len(rows) == 1, "an edit on the durable path inserted a second row"
    assert rows[0].colour == EDITED_COLOUR
    assert rows[0].position == position, "the supersede moved the queue position"
    assert rows[0].content_hash == content_hash(thread_id, case.case)
    # The end-to-end regression: card colour AND target equal the queue row after an
    # edit. The expected target is read from the substrate, never a literal (D-08).
    expected_target = get_tews().target_times[EDITED_COLOUR].target
    assert rows[0].target == expected_target
    assert edited["handover"].colour == EDITED_COLOUR == rows[0].colour
    assert edited["handover"].target == rows[0].target
    assert edited["handover"].target != scored_target, "the edit must change the target"


# ------------------------------------------------- the ONE respond loop (Plan 21-02)
# A two-interrupt graph: the first payload is a question, the second the approval gate. The
# node records each resumed value in state, so the loop's answers are asserted from the state
# rather than from a side list a re-run would duplicate.
class _TwoInterrupts(TypedDict, total=False):
    first: Any
    second: Any


_ELICITATION_PAYLOAD: dict[str, Any] = {
    "type": InterruptType.ELICITATION.value,
    "tool_name": "request_clarification",
    "requests": [],
}
_APPROVAL_PAYLOAD: dict[str, Any] = {
    "type": InterruptType.APPROVAL.value,
    "case_id": "c-policy",
}


def _interrupting_graph(
    payloads: list[dict[str, Any]], seen: list[Any] | None = None
) -> Any:
    """A graph whose one node interrupts once per payload, recording each resume value.

    *seen* collects every value an ``interrupt()`` returned. A resumed node re-runs from its
    top, so the same value can be recorded more than once — assertions therefore test
    membership, never a count.
    """

    def node(_state: Mapping[str, Any]) -> dict[str, Any]:
        values: list[Any] = []
        for payload in payloads:
            value = interrupt(payload)
            values.append(value)
            if seen is not None:
                seen.append(value)
        return {
            "first": values[0],
            "second": values[1] if len(values) > 1 else None,
        }

    graph = StateGraph(_TwoInterrupts)
    graph.add_node("ask", node)
    graph.add_edge(START, "ask")
    graph.add_edge("ask", END)
    return graph.compile(checkpointer=MemorySaver())


async def test_the_default_policy_answers_the_gate_and_stops_at_an_elicitation() -> None:
    """No ``respond``: an approval is answered as before, a question is left paused (ELICIT-05)."""
    graph = _interrupting_graph([_ELICITATION_PAYLOAD])
    config = {"configurable": {"thread_id": "policy-default"}}

    _result, payload = await invoke_graph(
        graph, {}, config, approval_decision("dismiss")
    )

    assert payload == _ELICITATION_PAYLOAD, "the caller must be shown the question"
    snapshot = await graph.aget_state(config)
    assert snapshot.next, "the default policy resumed a question with an approval token"


async def test_a_respond_policy_answers_the_question_then_stops_at_the_gate() -> None:
    """A policy that answers the question and declines the approval leaves the gate pending."""
    seen: list[Any] = []
    graph = _interrupting_graph([_ELICITATION_PAYLOAD, _APPROVAL_PAYLOAD], seen)
    config = {"configurable": {"thread_id": "policy-then-gate"}}
    visited: list[str] = []
    decline = decline_responses(CLARIFICATION_REQUEST_KEY)

    def policy(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        visited.append(str(payload.get("type")))
        return decline if payload.get("type") == InterruptType.ELICITATION else None

    _result, payload = await invoke_graph(graph, {}, config, {}, respond=policy)

    assert payload == _ELICITATION_PAYLOAD, "the FIRST payload is what a human is shown"
    assert visited == ["mcp_elicitation", "approval"]
    assert decline in seen, "the question was answered with the policy's value"
    snapshot = await graph.aget_state(config)
    assert snapshot.next == ("ask",), "the gate must stay pending for the clinician"


async def test_a_respond_policy_that_answers_both_payloads_reaches_the_terminal() -> None:
    """Answering the question and the gate completes the run — one loop, two payload types."""
    graph = _interrupting_graph([_ELICITATION_PAYLOAD, _APPROVAL_PAYLOAD])
    config = {"configurable": {"thread_id": "policy-both"}}
    decision = approval_decision("dismiss")

    def policy(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if payload.get("type") == InterruptType.ELICITATION:
            return decline_responses(CLARIFICATION_REQUEST_KEY)
        return decision

    result, payload = await invoke_graph(graph, {}, config, {}, respond=policy)

    assert payload == _ELICITATION_PAYLOAD
    assert not result.get("__interrupt__"), "the loop left the run paused"
    assert result["second"] == decision


async def test_pending_interrupt_reads_the_paused_payload(tmp_path: Path) -> None:
    """``pending_interrupt`` is the ONE reader of the snapshot's pending payload (DRY)."""
    case = _case("E-02")
    tools = build_tools(case, offline=True, recorder=UsageRecorder())
    db_path = tmp_path / "pending.db"
    config = {"configurable": {"thread_id": "pending-payload"}}

    async with checkpointed_graph(tools, db_path) as graph:
        await graph.ainvoke({"raw_note": case.note, "case": case.case}, config)
        snapshot = await graph.aget_state(config)

    payload = pending_interrupt(snapshot)
    assert payload is not None
    assert payload["type"] == InterruptType.APPROVAL
    assert payload["case_id"] == derive_thread_id(case.note)


async def test_resume_paused_leaves_the_thread_paused_when_the_policy_returns_none(
    tmp_path: Path, injected_store
) -> None:
    """A ``None`` policy is a real "present it": the gate stays pending and nothing is written."""
    case = _case("E-02")
    tools = build_tools(case, offline=True, recorder=UsageRecorder())
    db_path = tmp_path / "policy-none.db"
    thread_id = derive_thread_id(case.note)
    config = {"configurable": {"thread_id": thread_id}}

    async with checkpointed_graph(tools, db_path) as graph:
        await graph.ainvoke({"raw_note": case.note, "case": case.case}, config)

    result = await resume_paused(
        tools, thread_id=thread_id, db_path=db_path, respond=lambda _payload: None
    )

    assert result.get("priority") is not None, "the state is returned so a surface can render"
    async with checkpointed_graph(tools, db_path) as graph:
        snapshot = await graph.aget_state(config)
    assert snapshot.next == ("approval_gate",), "a None policy resumed the gate anyway"
    assert injected_store.rows == [], "a None policy committed a queue row"
