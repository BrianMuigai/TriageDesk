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

import asyncio
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

# The ONE cached default store, as a ``(db_path, event loop, store)`` triple (see
# ``default_store``). ``None`` until the first resolve; :func:`reset_default_store` drops it.
_DEFAULT_STORE: tuple[Path, asyncio.AbstractEventLoop, Store] | None = None


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
    """Return the ONE default store for ``(db_path, running event loop)`` — opened once (D-10).

    Opening the borrowed store is expensive: it launches ``npx mcp-sqlite@1.0.9`` and ensures
    the schema, ~2.3 s on the demo host. Resolving it per *call* therefore put a ~2.6-3.1 s
    floor under every audited tool call — including ``score_priority``, which is pure integer
    arithmetic (nurse stress test 2026-11-16, S4). The store is opened once per process per
    event loop and reused afterwards.

    The lifetime is a ``(db_path, loop, store)`` triple, for the SAME reason
    ``llm.client._async_client`` is loop-keyed (commit ``4a24c8f``): the borrowed store holds
    async subprocess transports bound to the loop that created them, so reusing one across a
    second ``asyncio.run(...)`` (``desk.interactive.main`` runs two loops) fails immediately.
    A different loop - or a different ``db_path`` - rebuilds; one loop reuses one store. A
    closed loop's store is dropped, never closed, because its loop is already gone. The cache
    holds ONE entry: alternating db paths rebuild (a test-only pattern; production names one
    domain db). Tests call :func:`reset_default_store` to force a fresh open.

    An **injected** store never reaches here: ``mcp.server.resolve_store`` returns the seam
    first, so :func:`set_store` still wins and is never cached. Because a loop has exactly one
    cached store, the audit chain keeps its single writer — this adds no concurrency.

    Imported lazily so naming the interface does not pull the adapter/langchain stack
    (SOLID: D). The borrowed server is opened in its own adapter context and its schema is
    ensured before it is returned (once per open, not once per call).
    """
    global _DEFAULT_STORE
    path = db_path or DOMAIN_DB_PATH
    loop = asyncio.get_running_loop()
    cached = _DEFAULT_STORE
    if cached is not None and cached[0] == path and cached[1] is loop:
        return cached[2]

    from triagedesk.store.borrowed import open_borrowed_store

    store = await open_borrowed_store(path)
    _DEFAULT_STORE = (path, loop, store)
    return store


def reset_default_store() -> None:
    """Drop the cached default store so the next resolve opens a fresh one (tests, reload).

    The ONE way to invalidate the cache: a test that must prove the open path launches, or a
    caller that deliberately wants a new store, resets rather than reaching into the module
    state. The dropped store is not closed — the borrowed transports belong to the caller's
    loop, which either still owns them or has already gone away.
    """
    global _DEFAULT_STORE
    _DEFAULT_STORE = None


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
    "reset_default_store",
    "verify",
]
