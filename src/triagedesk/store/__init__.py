"""The store package — borrowed case/queue persistence behind ONE protocol (D-10, D-13).

The graph and the owned MCP server depend on the :class:`Store` protocol, never on
the borrowed SQLite MCP server's concrete tool set (SOLID: D/L). The borrowed server
(``jparkerweb/mcp-sqlite``, pinned ``mcp-sqlite@1.0.9``) is the storage authority; the
gate stays ours (TOOL-06, D-10).

``store/`` is the ONLY layer that reaches the borrowed server, and it does so in its
own adapter context (``mcp/adapter.load_borrowed_tools``) — never merged with the owned
server, which would collapse the modern owned server to the borrowed server's legacy
protocol era (01-RESEARCH Pattern 3).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from triagedesk.store.audit import (
    COMMIT_TOOL,
    GENESIS,
    AuditRecord,
    AuditStore,
    ChainVerification,
    Reconciliation,
    append,
    reconcile,
    record_digest,
    verify,
)

# The domain store path — the clinical record + audit, via the borrowed MCP (D-09).
# Named once here so no caller inlines the filename (DRY).
DOMAIN_DB_PATH = Path("triage.db")


class QueueRow(BaseModel):
    """One immutable queue placement (D-06).

    The row is keyed by (``case_id``, ``content_hash``): the idempotency key is the
    whole crash-safety mechanism, so committing the same case twice yields exactly one
    row. ``created_at`` is volatile and is deliberately NOT part of the key
    (Pitfall 14).
    """

    case_id: str
    content_hash: str
    colour: str
    target: str | None = None
    position: int
    created_at: datetime


class CaseRow(BaseModel):
    """One stored case payload (TOOL-06)."""

    case_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Store(Protocol):
    """The narrow, injectable case/queue store the callers depend on (D-13).

    A World-B swap (an owned store) implements this same protocol and touches this
    package alone (SOLID: L). Every method is async because the borrowed server is
    reached over async MCP tool calls.
    """

    async def ensure_schema(self) -> None:
        """Create the case/queue tables if they do not already exist."""
        ...

    async def read_queue_row(self, case_id: str, content_hash: str) -> QueueRow | None:
        """Return the queue row for the idempotency key, or ``None``."""
        ...

    async def next_position(self) -> int:
        """Return the next free queue position."""
        ...

    async def upsert_queue_row(self, row: QueueRow) -> None:
        """Insert, or update the mutable fields (``colour``/``target``) by key.

        Matching on (``case_id``, ``content_hash``) preserves ``position`` and
        ``created_at``, so an ``edit`` supersedes the existing row in place rather than
        inserting a second one (D6-06).
        """
        ...

    async def read_case(self, case_id: str) -> CaseRow | None:
        """Return the stored case payload, or ``None``."""
        ...

    async def read_queue_rows(self) -> list[QueueRow]:
        """Return every committed queue row (for the audit reconciliation, D-09)."""
        ...

    # -- Audit seam (AUDIT-01, D-08): the same store holds the queue and the chain, so
    #    the two never diverge (D-09). The one audit helper (``store/audit.append``)
    #    is the only writer; these methods are the narrow read/write surface it needs.
    async def read_chain_head(self) -> str:
        """Return the persisted chain head, or the genesis value when empty (M-6)."""
        ...

    async def write_chain_head(self, head: str) -> None:
        """Persist the chain head so verification survives a restart (M-6)."""
        ...

    async def append_audit_record(self, record: AuditRecord) -> None:
        """Append one chained audit record (written only by ``store/audit.append``)."""
        ...

    async def read_audit_records(self) -> list[AuditRecord]:
        """Return the audit records in chain order (ascending ``seq``)."""
        ...


async def default_store(db_path: Path | None = None) -> Store:
    """Build the default store — the borrowed SQLite MCP server (D-10).

    Imported lazily so naming the interface does not pull the adapter/langchain stack
    (SOLID: D). The borrowed server is opened in its own adapter context and its schema
    is ensured before it is returned.
    """
    from triagedesk.store.borrowed import open_borrowed_store

    return await open_borrowed_store(db_path or DOMAIN_DB_PATH)


__all__ = [
    "COMMIT_TOOL",
    "DOMAIN_DB_PATH",
    "GENESIS",
    "AuditRecord",
    "AuditStore",
    "CaseRow",
    "ChainVerification",
    "QueueRow",
    "Reconciliation",
    "Store",
    "append",
    "default_store",
    "reconcile",
    "record_digest",
    "verify",
]
