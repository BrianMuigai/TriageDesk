"""The ONE module that reaches the borrowed SQLite MCP server (D-10, D-13).

``jparkerweb/mcp-sqlite`` (pinned ``mcp-sqlite@1.0.9``) is the storage authority for
cases and the queue; the gate stays ours (TOOL-06). It is reached through its OWN
adapter context (``mcp/adapter.load_borrowed_tools``) — never merged with the owned
server, which would collapse the modern owned server to the borrowed server's legacy
protocol era.

The borrowed tool names are declared ONCE here as data, so the wiring is a
configuration change (SOLID: O), not scattered string literals. :class:`BorrowedStore`
implements the :class:`~triagedesk.store.Store` protocol over an injected
``name -> async callable`` tool mapping, so a World-B swap replaces this module alone
(SOLID: L) and the wiring is unit-testable without launching the borrowed subprocess.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any, cast

from triagedesk.store import CaseRow, QueueRow, Store

# The borrowed server's tool surface, pinned to what Phase 1 verified
# (evidence/mcp-spike.json). Declared once; the wiring reads these names, never
# inlines them.
TOOL_DB_INFO = "db_info"
TOOL_QUERY = "query"
TOOL_LIST_TABLES = "list_tables"
TOOL_GET_TABLE_SCHEMA = "get_table_schema"
TOOL_CREATE_RECORD = "create_record"
TOOL_READ_RECORDS = "read_records"
TOOL_UPDATE_RECORDS = "update_records"
TOOL_DELETE_RECORDS = "delete_records"

EXPECTED_TOOLS: tuple[str, ...] = (
    TOOL_DB_INFO,
    TOOL_QUERY,
    TOOL_LIST_TABLES,
    TOOL_GET_TABLE_SCHEMA,
    TOOL_CREATE_RECORD,
    TOOL_READ_RECORDS,
    TOOL_UPDATE_RECORDS,
    TOOL_DELETE_RECORDS,
)

# The two domain tables the borrowed server owns (D-09: clinical record, not runtime).
QUEUE_TABLE = "queue"
CASES_TABLE = "cases"

# The one async-tool interface the borrowed wiring depends on (SOLID: D): the same
# shape ``mcp/adapter`` supplies (``tool.name -> tool.ainvoke``).
BorrowedTool = Callable[[Mapping[str, Any]], Awaitable[Any]]

# Belt-and-braces DDL: the PRIMARY KEY on the idempotency key makes a duplicate insert
# a no-op even if the read-then-write check ever raced (the key is the real mechanism).
_QUEUE_DDL = (
    f"CREATE TABLE IF NOT EXISTS {QUEUE_TABLE} ("
    "case_id TEXT NOT NULL, "
    "content_hash TEXT NOT NULL, "
    "colour TEXT NOT NULL, "
    "target TEXT, "
    "position INTEGER NOT NULL, "
    "created_at TEXT NOT NULL, "
    "PRIMARY KEY (case_id, content_hash))"
)

_CASES_DDL = (
    f"CREATE TABLE IF NOT EXISTS {CASES_TABLE} ("
    "case_id TEXT PRIMARY KEY, "
    "payload TEXT NOT NULL)"
)

_ROW_KEYS = ("rows", "records", "results", "data")


def _rows(payload: Any) -> list[dict[str, Any]]:
    """Decode a borrowed tool's row payload into a list of dicts.

    The borrowed server returns MCP content blocks carrying JSON text (and may wrap
    rows under a key); the possible shapes are normalised here so the wiring never
    guesses. A bare object is treated as a single row.
    """
    value = payload
    if isinstance(value, list):
        texts = [
            block.get("text") if isinstance(block, Mapping) else getattr(block, "text", None)
            for block in value
        ]
        texts = [text for text in texts if isinstance(text, str)]
        if not texts:
            return [dict(item) for item in value if isinstance(item, Mapping)]
        value = texts[0] if len(texts) == 1 else texts
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, Mapping):
        for key in _ROW_KEYS:
            nested = value.get(key)
            if isinstance(nested, list):
                return [dict(item) for item in nested if isinstance(item, Mapping)]
        return [dict(value)]
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


class BorrowedStore:
    """The borrowed SQLite MCP server behind the :class:`Store` protocol (D-10).

    Constructed from an injected ``name -> async callable`` tool mapping (the same
    seam ``mcp/adapter`` supplies), so the wiring is unit-testable without launching
    the borrowed subprocess (D-13). The production factory is
    :func:`open_borrowed_store`.
    """

    def __init__(self, tools: Mapping[str, BorrowedTool]) -> None:
        missing = [name for name in EXPECTED_TOOLS if name not in tools]
        if missing:
            raise ValueError(f"borrowed server is missing required tools: {missing}")
        self._tools = dict(tools)

    async def _call(self, name: str, arguments: Mapping[str, Any]) -> Any:
        """Invoke one borrowed tool through the injected mapping (D-13)."""
        return await self._tools[name](dict(arguments))

    async def ensure_schema(self) -> None:
        """Create the case/queue tables if absent, via the borrowed ``query`` tool."""
        await self._call(TOOL_QUERY, {"sql": _QUEUE_DDL})
        await self._call(TOOL_QUERY, {"sql": _CASES_DDL})

    async def read_queue_row(self, case_id: str, content_hash: str) -> QueueRow | None:
        """Return the row for the idempotency key, or ``None`` (borrowed ``query``)."""
        rows = _rows(
            await self._call(
                TOOL_QUERY,
                {
                    "sql": (
                        "SELECT case_id, content_hash, colour, target, position, created_at "
                        f"FROM {QUEUE_TABLE} WHERE case_id = ? AND content_hash = ? LIMIT 1"
                    ),
                    "values": [case_id, content_hash],
                },
            )
        )
        return QueueRow.model_validate(rows[0]) if rows else None

    async def next_position(self) -> int:
        """Return ``max(position) + 1`` (the next free queue position)."""
        rows = _rows(
            await self._call(
                TOOL_QUERY,
                {
                    "sql": (
                        f"SELECT COALESCE(MAX(position), 0) + 1 AS next_position FROM {QUEUE_TABLE}"
                    )
                },
            )
        )
        if not rows:
            raise ValueError("borrowed server returned no position row")
        return int(rows[0]["next_position"])

    async def upsert_queue_row(self, row: QueueRow) -> None:
        """Insert the row, ignoring a duplicate idempotency key (belt-and-braces)."""
        await self._call(
            TOOL_QUERY,
            {
                "sql": (
                    f"INSERT OR IGNORE INTO {QUEUE_TABLE} "
                    "(case_id, content_hash, colour, target, position, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                "values": [
                    row.case_id,
                    row.content_hash,
                    row.colour,
                    row.target,
                    row.position,
                    row.created_at.isoformat(),
                ],
            },
        )

    async def read_case(self, case_id: str) -> CaseRow | None:
        """Return the stored case payload, or ``None`` (borrowed ``query``)."""
        rows = _rows(
            await self._call(
                TOOL_QUERY,
                {
                    "sql": f"SELECT case_id, payload FROM {CASES_TABLE} WHERE case_id = ? LIMIT 1",
                    "values": [case_id],
                },
            )
        )
        if not rows:
            return None
        payload = rows[0].get("payload")
        data = json.loads(payload) if isinstance(payload, str) else (payload or {})
        return CaseRow(case_id=str(rows[0]["case_id"]), payload=dict(data))


async def open_borrowed_store(db_path: Path) -> Store:
    """Open the borrowed store: load its tools in their own context, ensure schema.

    ``load_borrowed_tools`` keeps the borrowed server in its OWN adapter context, so
    the owned and borrowed servers keep their own protocol eras (no era collapse).
    """
    from triagedesk.mcp.adapter import load_borrowed_tools

    tools: dict[str, BorrowedTool] = {
        tool.name: cast(BorrowedTool, tool.ainvoke)
        for tool in await load_borrowed_tools(db_path)
    }
    store = BorrowedStore(tools)
    await store.ensure_schema()
    return store


__all__ = [
    "CASES_TABLE",
    "EXPECTED_TOOLS",
    "QUEUE_TABLE",
    "BorrowedStore",
    "open_borrowed_store",
]
