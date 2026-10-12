"""The ONE in-memory :class:`~triagedesk.store.Store` double (D-13, SOLID: D/L).

A single in-process implementation of the store protocol, so the eval harness and the
test suite share ONE double rather than each defining its own (DRY — a duplicated store
double would be two sources of truth). The production path uses the borrowed SQLite MCP
server; this double is the injectable alternative for anything that must run without a
subprocess or a network.

The backing state lives in a separate object so :meth:`InMemoryStore.restart` can hand
back a *fresh handle over the same data* — the way the audit suite simulates a process
restart without a real SQLite file (M-6).

The narrow ``_note`` hook records the queue-protocol calls a test cares about (so a
refusal can be shown to have touched no store); it is a no-op here and overridden by the
test recorder. It deliberately does NOT record the audit-seam calls: the audit append is
a separate concern and its internal reads are not store *writes* (D-09).
"""

from __future__ import annotations

from triagedesk.store import CaseRow, QueueRow
from triagedesk.store.audit import GENESIS, AuditRecord


class _Memory:
    """The shared backing state of the in-memory store — the "database" a restart reopens."""

    def __init__(self) -> None:
        self.rows: list[QueueRow] = []
        self.cases: dict[str, CaseRow] = {}
        self.audit_records: list[AuditRecord] = []
        self.chain_head: str = GENESIS


class InMemoryStore:
    """A complete in-memory :class:`~triagedesk.store.Store` (queue + case + audit).

    Implements the whole protocol — including the audit half — so a caller that depends
    on the store never needs a concrete borrowed implementation (SOLID: L). The
    ``_note`` hook is the single seam a test subclass uses to record queue-protocol
    calls (DRY, ISP).
    """

    def __init__(self, memory: _Memory | None = None) -> None:
        self._memory = memory if memory is not None else _Memory()

    def _note(self, name: str, *args: object) -> None:
        """Record a queue-protocol call — a no-op here, overridden by the test recorder."""

    def restart(self) -> InMemoryStore:
        """Return a fresh handle over the same backing state — a simulated restart (M-6)."""
        return type(self)(self._memory)

    @property
    def rows(self) -> list[QueueRow]:
        return self._memory.rows

    @property
    def cases(self) -> dict[str, CaseRow]:
        return self._memory.cases

    @property
    def audit_records(self) -> list[AuditRecord]:
        return self._memory.audit_records

    @property
    def chain_head(self) -> str:
        return self._memory.chain_head

    async def ensure_schema(self) -> None:
        self._note("ensure_schema")

    async def read_queue_row(self, case_id: str, content_hash: str) -> QueueRow | None:
        self._note("read_queue_row", case_id, content_hash)
        for row in self.rows:
            if row.case_id == case_id and row.content_hash == content_hash:
                return row
        return None

    async def next_position(self) -> int:
        self._note("next_position")
        return len(self.rows) + 1

    async def upsert_queue_row(self, row: QueueRow) -> None:
        self._note("upsert_queue_row", row.case_id, row.content_hash)
        key = (row.case_id, row.content_hash)
        for index, existing in enumerate(self.rows):
            if (existing.case_id, existing.content_hash) == key:
                self.rows[index] = row  # supersede in place (list order == position)
                return
        self.rows.append(row)

    async def read_case(self, case_id: str) -> CaseRow | None:
        self._note("read_case", case_id)
        return self.cases.get(case_id)

    async def read_queue_rows(self) -> list[QueueRow]:
        return list(self.rows)

    async def read_chain_head(self) -> str:
        return self._memory.chain_head

    async def write_chain_head(self, head: str) -> None:
        self._memory.chain_head = head

    async def append_audit_record(self, record: AuditRecord) -> None:
        self._memory.audit_records.append(record)

    async def read_audit_records(self) -> list[AuditRecord]:
        return list(self._memory.audit_records)


__all__ = ["InMemoryStore"]
