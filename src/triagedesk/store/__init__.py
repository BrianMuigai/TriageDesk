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
        """Insert the row, ignoring a duplicate idempotency key (belt-and-braces)."""
        ...

    async def read_case(self, case_id: str) -> CaseRow | None:
        """Return the stored case payload, or ``None``."""
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
    "DOMAIN_DB_PATH",
    "CaseRow",
    "QueueRow",
    "Store",
    "default_store",
]
