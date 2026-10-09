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
    await commit_to_queue(memory_store, case_id="c-1", colour="RED", content={"colour": "RED"})

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
