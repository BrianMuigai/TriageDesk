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
one ``extract`` seam), and the store is the shared in-memory double — so the suite
launches no borrowed ``npx mcp-sqlite`` subprocess and no model.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from langgraph.types import Command

from triagedesk.core.schema import ExtractionResult
from triagedesk.durable import (
    DurableError,
    approval_decision,
    derive_thread_id,
    resume_paused,
    run_to_gate,
)
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import checkpointed_graph
from triagedesk.graph.nodes import case_id_for
from triagedesk.mcp import server as server_module
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
    # The model is stubbed through the ONE owned ``extract`` seam, so ``normalize_case``
    # runs as the real audited owned tool with no model call (offline, deterministic).
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=case.case, matched_discriminator_ids=[]),
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
        "extract",
        lambda note: ExtractionResult(case=case.case, matched_discriminator_ids=[]),
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
    await resume_paused(
        tools,
        thread_id=thread_id,
        decision=approval_decision("approve", approver=approver, role=role),
        db_path=tmp_path / "thread-a.db",
    )
    rows = await injected_store.read_queue_rows()
    assert len(rows) == 1
    scored_colour, position = rows[0].colour, rows[0].position
    assert scored_colour != EDITED_COLOUR, "the edit must change the committed colour"

    # Thread 2: edit the SAME case to a different declared colour — it supersedes in place.
    await resume_paused(
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
