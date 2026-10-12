"""The ONE audit helper proof suite (Plan 03-03, AUDIT-01..03, D-08/D-09).

Proves the audit spine: a single helper appends one canonical, hash-chained record per
tool call, the chain links each record to the previous one, the record hashes its
canonical content (so key order never churns the digest), and an approval record carries
the named approver and role. Later sections prove the chain verifies after a restart and
reports a tampered row, that reconciliation detects a queue row lacking its approval
record, and that the owned server intercepts every tool call through the one helper.

The store is the shared in-memory ``Store`` double from ``conftest`` (DRY, D-13) — the
same store the queue uses, so the audit and the queue are one authoritative place (D-09).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp import Client

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.mcp import server as server_module
from triagedesk.store.audit import (
    COMMIT_TOOL,
    GENESIS,
    AuditRecord,
    append,
    reconcile,
    record_digest,
    verify,
)
from triagedesk.store.queue import commit_to_queue


def _fields(**overrides: Any) -> dict[str, Any]:
    """The content fields of a record; the chain fields are computed by ``append``."""
    base: dict[str, Any] = {
        "tool": "score_priority",
        "actor": "agent",
        "case_id": "c-1",
        "inputs": {"case": {"colour": "RED"}},
        "outputs": {"colour": "RED"},
    }
    base.update(overrides)
    return base


# One CaseInput-shaped payload — the immutable case content the commit now keys on
# (D6-04). Shared so the key is meaningful wherever a case crosses into the tool.
_CASE: dict[str, Any] = {
    "respiratory_rate": 24,
    "heart_rate": 118,
    "avpu": "alert",
    "complaint": "central chest pain",
}


# ------------------------------------------------------------------- Task 1: the helper


async def test_chain_links_each_record_to_the_previous(memory_store) -> None:
    """A second record's ``prev_hash`` is the first record's ``hash`` (AUDIT-01)."""
    first = await append(memory_store, _fields(tool="normalize_case"))
    second = await append(memory_store, _fields(tool="score_priority"))

    assert first.prev_hash == GENESIS
    assert second.prev_hash == first.hash
    assert second.seq == first.seq + 1
    assert memory_store.chain_head == second.hash


def test_canonical_record_hash_is_independent_of_key_order() -> None:
    """The same logical record hashes identically regardless of dict key order (M-13)."""
    ts = datetime(2026, 10, 9, 16, 0, tzinfo=UTC)
    common: dict[str, Any] = {
        "seq": 0,
        "ts": ts,
        "case_id": "c-1",
        "tool": "score_priority",
        "actor": "agent",
        "prev_hash": GENESIS,
    }
    first = AuditRecord(**common, inputs={"a": 1, "b": 2}, outputs={"x": 1, "y": 2})
    second = AuditRecord(**common, inputs={"b": 2, "a": 1}, outputs={"y": 2, "x": 1})

    assert record_digest(first) == record_digest(second)


async def test_approver_and_role_are_captured_on_an_approval_record(memory_store) -> None:
    """An approval record names the approver and role, so the write is attributable (AUDIT-02)."""
    record = await append(
        memory_store,
        _fields(
            tool=COMMIT_TOOL,
            actor="clinician",
            approved_by="Dr A. Nurse",
            role="triage clinician",
        ),
    )

    assert record.approved_by == "Dr A. Nurse"
    assert record.role == "triage clinician"
    assert record.approved_by and record.role


# ------------------------------------------------- Task 2: persisted head + verification


async def test_chain_verifies_after_a_restart(memory_store) -> None:
    """A fresh handle over the same store still verifies the chain — head persisted (M-6)."""
    await append(memory_store, _fields(tool="normalize_case"))
    await append(memory_store, _fields(tool="score_priority"))

    restarted = memory_store.restart()

    assert restarted is not memory_store
    assert restarted.chain_head == memory_store.chain_head
    assert (await verify(restarted)).valid is True


async def test_verify_reports_a_break_when_a_record_is_tampered(memory_store) -> None:
    """Mutating a stored record makes ``verify`` report a break at that record (T-03-11)."""
    await append(memory_store, _fields(tool="normalize_case"))
    await append(memory_store, _fields(tool="score_priority"))

    memory_store.audit_records[0] = memory_store.audit_records[0].model_copy(
        update={"outputs": {"colour": "GREEN"}}
    )

    report = await verify(memory_store)
    assert report.valid is False
    assert report.broken_at == 0


async def test_verify_on_an_empty_chain_is_valid(memory_store) -> None:
    """An empty chain verifies — absence is not an error (AUDIT-01)."""
    report = await verify(memory_store)

    assert report.valid is True
    assert report.broken_at is None


async def test_reconcile_reports_a_queue_row_without_an_approval_record(memory_store) -> None:
    """A queue row with no matching approval audit record is detected (D-09, T-03-08)."""
    await commit_to_queue(
        memory_store, case_id="c-1", colour="RED", content=CaseInput(**_CASE)
    )

    before = await reconcile(memory_store)
    assert before.ok is False
    assert before.missing == ["c-1"]

    await append(
        memory_store,
        _fields(
            tool=COMMIT_TOOL,
            actor="clinician",
            case_id="c-1",
            approved_by="Dr A. Nurse",
            role="triage clinician",
        ),
    )

    after = await reconcile(memory_store)
    assert after.ok is True
    assert after.missing == []


# ------------------------------------------- Task 3: the uniform tool interceptor


def _token(decision: str = "approve", colour: str = "RED") -> dict[str, str]:
    """A well-formed approval-token payload (approver + role + decision + colour)."""
    return {
        "approved_by": "Dr A. Nurse",
        "role": "triage clinician",
        "decision": decision,
        "approved_at": "2026-10-09T16:00:00Z",
        "final_colour": colour,
    }


async def test_interceptor_appends_exactly_one_record_per_call(injected_store) -> None:
    """One owned tool call appends exactly one chained record (AUDIT-01, T-03-15)."""
    async with Client(server_module.server) as client:
        await client.call_tool("match_discriminators", {"complaint": "central chest pain"})

    records = injected_store.audit_records
    assert len(records) == 1
    assert records[0].tool == "match_discriminators"
    assert records[0].actor == "agent"
    assert records[0].hash
    assert injected_store.chain_head == records[0].hash


async def test_interceptor_records_a_refused_commit_as_refused(injected_store) -> None:
    """A refused commit is recorded as a clinician call that wrote nothing (AUDIT-01)."""
    async with Client(server_module.server) as client:
        await client.call_tool(
            "commit_priority", {"case_id": "c-1", "colour": "RED", "case": _CASE}
        )

    record = injected_store.audit_records[0]
    assert record.tool == COMMIT_TOOL
    assert record.actor == "clinician"
    assert record.approved_by is None
    assert injected_store.rows == [], "a refused commit must not write to the queue"


async def test_interceptor_records_the_named_approver_on_a_commit(injected_store) -> None:
    """A committed approval names the approver and role in the audit record (AUDIT-02)."""
    async with Client(server_module.server) as client:
        await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "case": _CASE, "approval_token": _token()},
        )

    record = injected_store.audit_records[0]
    assert record.approved_by == "Dr A. Nurse"
    assert record.role == "triage clinician"
    assert record.actor == "clinician"
    # The committed row and its approval record agree, so reconciliation is clean.
    assert (await reconcile(injected_store)).ok is True


async def test_every_tool_call_appends_exactly_one_chained_record(
    monkeypatch, injected_store
) -> None:
    """Every owned tool appends one record, forming a single unbroken chain (AUDIT-01/03)."""
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(
            case=CaseInput(respiratory_rate=24), matched_discriminator_ids=[]
        ),
    )
    case = _CASE
    async with Client(server_module.server) as client:
        await client.call_tool("normalize_case", {"raw_note": "RR 24"})
        await client.call_tool("score_priority", {"case": case})
        await client.call_tool("match_discriminators", {"complaint": "central chest pain"})
        await client.call_tool("raise_recheck_flag", {"previous": case, "current": case})
        await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "case": case, "approval_token": _token()},
        )

    records = injected_store.audit_records
    assert [record.tool for record in records] == [
        "normalize_case",
        "score_priority",
        "match_discriminators",
        "raise_recheck_flag",
        COMMIT_TOOL,
    ]
    # One chain, no gaps: each record links to the one before it.
    assert records[0].prev_hash == GENESIS
    for earlier, later in zip(records, records[1:], strict=False):
        assert later.prev_hash == earlier.hash
    assert (await verify(injected_store)).valid is True
