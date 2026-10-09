"""The ONE audit helper: canonical hash-chained record + append (AUDIT-01, D-08).

This module is the single source of the audit-record shape and the single append path
(CONVENTIONS §1: "one logging function; every tool call routes through it"). Every
owned tool call — and the gated commit's approval — is serialised here, canonicalised
through ``core.hashing`` (never string-concatenated, M-13), chained to the previous
record's hash, and written to the authoritative store (the same store as the queue,
D-09/AUDIT-03).

The record shape is defined ONCE, as :class:`AuditRecord`; no other module restates it
(AUDIT-03, DRY). The chain head is persisted in the store (not reconstructed from an
in-memory tail), so the chain verifies after a restart (M-6).

The module depends only on ``core.hashing`` + ``pydantic`` + the narrow
:class:`AuditStore` seam (SOLID: D, ISP); it never imports the concrete borrowed store.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from triagedesk.core.hashing import hash_value

# The genesis ``prev_hash`` for the first record in a chain — nothing precedes it.
GENESIS = ""

# The owned tool whose record carries a named clinician's approval (AUDIT-02).
COMMIT_TOOL = "commit_priority"

# The two actor classes the record distinguishes: the graph-driven agent and the
# named clinician whose approval the gate requires (ARCHITECTURE §6).
Actor = Literal["agent", "clinician"]


class AuditRecord(BaseModel):
    """One canonical, hash-chained audit record (ARCHITECTURE §6, D-08).

    This is the ONLY definition of the audit-record shape (AUDIT-03): the tool
    interceptor, the approval path and the chain verifier all speak it. ``seq`` is the
    record's monotonic position in the chain — a stable id used to report a break;
    ``prev_hash`` chains the record to its predecessor and ``hash`` seals its own
    canonical content. An approval record carries a named ``approved_by`` and ``role``
    so the queue write is attributable to a person (AUDIT-02).
    """

    seq: int
    ts: datetime
    case_id: str = ""
    tool: str
    actor: Actor
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    role: str | None = None
    prev_hash: str
    hash: str = ""


def record_digest(record: AuditRecord) -> str:
    """Return the canonical digest sealing a record's content (the ONE sealing path).

    Hashes every field EXCEPT ``hash`` itself — including ``prev_hash`` — through the
    one canonical JSON path (``core.hashing.hash_value``), so dict key order and
    whitespace never churn the digest (M-13) while any real field change does. Both
    :func:`append` and :func:`verify` call THIS, so the append and the verification can
    never drift (DRY).
    """
    return hash_value(record.model_dump(mode="json", exclude={"hash"}))


class ChainVerification(BaseModel):
    """The result of recomputing the audit chain (AUDIT-01, T-03-11).

    ``valid`` is ``True`` when every record's ``prev_hash`` links to its predecessor,
    every ``hash`` matches the record's recomputed canonical digest, and the persisted
    chain head equals the last record's hash. On a break, ``broken_at`` names the first
    offending record's ``seq`` and ``reason`` explains the mismatch.
    """

    valid: bool
    broken_at: int | None = None
    reason: str | None = None


class Reconciliation(BaseModel):
    """The result of cross-checking the queue against the audit (D-09).

    ``missing`` lists the ``case_id`` of every committed queue row that has no matching
    approval audit record — the narrow queue-write/audit-append window. A divergence is
    reported (never silently assumed atomic) and can be closed by re-issuing the
    idempotent commit.
    """

    ok: bool
    missing: list[str] = Field(default_factory=list)
    reason: str | None = None


@runtime_checkable
class AuditStore(Protocol):
    """The narrow audit seam the one helper depends on (SOLID: D, ISP).

    The store the tool interceptor resolves (the same instance that holds the queue,
    D-09) implements this in addition to the queue protocol. Only these five methods
    are needed: read/write the persisted chain head, append/read the records, and read
    the queue rows :func:`reconcile` cross-checks against.
    """

    async def read_chain_head(self) -> str:
        """Return the persisted chain head, or :data:`GENESIS` when the chain is empty."""
        ...

    async def write_chain_head(self, head: str) -> None:
        """Persist *head* as the current chain head (survives a restart, M-6)."""
        ...

    async def append_audit_record(self, record: AuditRecord) -> None:
        """Append *record* to the audit store."""
        ...

    async def read_audit_records(self) -> list[AuditRecord]:
        """Return the records in chain order (ascending ``seq``)."""
        ...

    async def read_queue_rows(self) -> list[Any]:
        """Return every committed queue row (for :func:`reconcile`)."""
        ...


async def append(store: AuditStore, fields: Mapping[str, Any]) -> AuditRecord:
    """Append ONE canonical record, chained to the persisted head (AUDIT-01, D-08).

    The single append path: (1) read the persisted chain head, (2) build the record
    with ``prev_hash`` = head, (3) seal it through the one canonical digest
    (:func:`record_digest`), and (4) write the record and the new head to the
    authoritative store. Nothing else writes an audit record, so no tool call escapes
    the audit (AUDIT-03, DRY).

    ``fields`` supplies the record's content (``tool``, ``actor``, ``case_id``,
    ``inputs``, ``outputs`` and — for an approval — ``approved_by``/``role``); the
    chain fields (``seq``, ``ts``, ``prev_hash``, ``hash``) are computed here.
    """
    prev_hash = await store.read_chain_head()
    seq = len(await store.read_audit_records())
    record = AuditRecord(
        seq=seq,
        ts=datetime.now(UTC),
        prev_hash=prev_hash or GENESIS,
        **fields,
    )
    sealed = record.model_copy(update={"hash": record_digest(record)})
    await store.append_audit_record(sealed)
    await store.write_chain_head(sealed.hash)
    return sealed


async def verify(store: AuditStore) -> ChainVerification:
    """Recompute the whole chain and report the first break (AUDIT-01, T-03-11).

    Walks the records in order, recomputing each record's digest from its canonical
    fields plus the previous hash, and reports the first mismatching record's ``seq``
    (or valid). The chain head is read back from the store and compared to the
    recomputed tail, so verification resumes from the persisted head after a restart
    (M-6) and a backfill or a lost in-memory tail cannot silently invalidate the chain.
    Read-only — this never writes (D-09).
    """
    records = await store.read_audit_records()
    expected_prev = GENESIS
    for record in records:
        if record.prev_hash != expected_prev:
            return ChainVerification(
                valid=False,
                broken_at=record.seq,
                reason="prev_hash does not match the previous record's hash",
            )
        if record_digest(record) != record.hash:
            return ChainVerification(
                valid=False,
                broken_at=record.seq,
                reason="record hash does not match its canonical content",
            )
        expected_prev = record.hash
    head = await store.read_chain_head()
    if (head or GENESIS) != expected_prev:
        return ChainVerification(
            valid=False,
            broken_at=records[-1].seq if records else None,
            reason="persisted chain head does not match the recomputed chain",
        )
    return ChainVerification(valid=True)


async def reconcile(store: AuditStore) -> Reconciliation:
    """Detect any committed queue row lacking its approval audit record (D-09).

    Cross-checks every committed queue row against the audit records and reports any row
    without a matching approval record — the narrow queue-write/audit-append window.
    Read-only; the window is closed by re-issuing the idempotent commit, never by a
    second write path here.
    """
    rows = await store.read_queue_rows()
    records = await store.read_audit_records()
    approved = {
        record.case_id
        for record in records
        if record.tool == COMMIT_TOOL and record.approved_by
    }
    missing = [
        str(getattr(row, "case_id", row))
        for row in rows
        if str(getattr(row, "case_id", row)) not in approved
    ]
    if missing:
        return Reconciliation(
            ok=False,
            missing=missing,
            reason=(
                "queue row(s) lack an approval audit record; "
                "re-issue the idempotent commit to close the window"
            ),
        )
    return Reconciliation(ok=True)


__all__ = [
    "GENESIS",
    "COMMIT_TOOL",
    "Actor",
    "AuditRecord",
    "AuditStore",
    "ChainVerification",
    "Reconciliation",
    "append",
    "reconcile",
    "record_digest",
    "verify",
]
