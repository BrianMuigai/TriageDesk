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
from triagedesk.store.audit import GENESIS, AuditRecord

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
# The audit chain lives in the SAME authoritative store as the queue, so the queue and
# the audit never diverge (D-09, AUDIT-03). ``audit_head`` holds the single persisted
# chain head, so verification survives a restart (M-6).
AUDIT_TABLE = "audit"
AUDIT_HEAD_TABLE = "audit_head"

# The one async-tool interface the borrowed wiring depends on (SOLID: D): the same
# shape ``mcp/adapter`` supplies (``tool.name -> tool.ainvoke``).
BorrowedTool = Callable[[Mapping[str, Any]], Awaitable[Any]]

# Belt-and-braces DDL: the PRIMARY KEY on the idempotency key makes the upsert safe even
# if the read-then-write check ever raced — a same-key insert updates only the mutable
# fields (the key is the real mechanism; D6-06).
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

# The audit chain: one row per record, ordered by ``seq``. ``inputs``/``outputs`` are
# stored as canonical JSON text so untrusted complaint text can never break parsing
# (M-13). ``audit_head`` is a single-row table holding the persisted chain head (M-6).
_AUDIT_DDL = (
    f"CREATE TABLE IF NOT EXISTS {AUDIT_TABLE} ("
    "seq INTEGER PRIMARY KEY, "
    "ts TEXT NOT NULL, "
    "case_id TEXT NOT NULL, "
    "tool TEXT NOT NULL, "
    "actor TEXT NOT NULL, "
    "inputs TEXT NOT NULL, "
    "outputs TEXT NOT NULL, "
    "approved_by TEXT, "
    "role TEXT, "
    "prev_hash TEXT NOT NULL, "
    "hash TEXT NOT NULL)"
)

_AUDIT_HEAD_DDL = (
    f"CREATE TABLE IF NOT EXISTS {AUDIT_HEAD_TABLE} ("
    "id INTEGER PRIMARY KEY CHECK (id = 1), "
    "head TEXT NOT NULL)"
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
        """Create the case/queue and audit tables if absent, via the borrowed ``query`` tool."""
        await self._call(TOOL_QUERY, {"sql": _QUEUE_DDL})
        await self._call(TOOL_QUERY, {"sql": _CASES_DDL})
        await self._call(TOOL_QUERY, {"sql": _AUDIT_DDL})
        await self._call(TOOL_QUERY, {"sql": _AUDIT_HEAD_DDL})

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
        """Insert, or update the mutable fields (``colour``/``target``) by key.

        The SQLite UPSERT form updates only the mutable columns, so
        ``position``/``created_at`` are preserved and no second row appears (D6-06,
        Pitfall 2). ``values`` stays parameterised — no string interpolation of case
        content (T-06-01).
        """
        await self._call(
            TOOL_QUERY,
            {
                "sql": (
                    f"INSERT INTO {QUEUE_TABLE} "
                    "(case_id, content_hash, colour, target, position, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(case_id, content_hash) DO UPDATE SET "
                    "colour = excluded.colour, target = excluded.target"
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

    async def read_queue_rows(self) -> list[QueueRow]:
        """Return every committed queue row, ordered by position (for reconciliation)."""
        rows = _rows(
            await self._call(
                TOOL_QUERY,
                {
                    "sql": (
                        "SELECT case_id, content_hash, colour, target, position, created_at "
                        f"FROM {QUEUE_TABLE} ORDER BY position"
                    )
                },
            )
        )
        return [QueueRow.model_validate(row) for row in rows]

    async def read_chain_head(self) -> str:
        """Return the persisted chain head, or :data:`GENESIS` when the chain is empty (M-6)."""
        rows = _rows(
            await self._call(
                TOOL_QUERY,
                {"sql": f"SELECT head FROM {AUDIT_HEAD_TABLE} WHERE id = 1"},
            )
        )
        return str(rows[0]["head"]) if rows else GENESIS

    async def write_chain_head(self, head: str) -> None:
        """Persist the chain head in its single-row table (M-6)."""
        await self._call(
            TOOL_QUERY,
            {
                "sql": (
                    f"INSERT OR REPLACE INTO {AUDIT_HEAD_TABLE} (id, head) VALUES (1, ?)"
                ),
                "values": [head],
            },
        )

    async def append_audit_record(self, record: AuditRecord) -> None:
        """Insert one audit record; the ``seq`` PRIMARY KEY makes a replay a no-op."""
        await self._call(
            TOOL_QUERY,
            {
                "sql": (
                    f"INSERT OR IGNORE INTO {AUDIT_TABLE} "
                    "(seq, ts, case_id, tool, actor, inputs, outputs, approved_by, role, "
                    "prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                "values": [
                    record.seq,
                    record.ts.isoformat(),
                    record.case_id,
                    record.tool,
                    record.actor,
                    json.dumps(record.inputs),
                    json.dumps(record.outputs),
                    record.approved_by,
                    record.role,
                    record.prev_hash,
                    record.hash,
                ],
            },
        )

    async def read_audit_records(self) -> list[AuditRecord]:
        """Return the records in chain order, decoding the JSON text columns."""
        rows = _rows(
            await self._call(
                TOOL_QUERY,
                {
                    "sql": (
                        "SELECT seq, ts, case_id, tool, actor, inputs, outputs, "
                        "approved_by, role, prev_hash, hash "
                        f"FROM {AUDIT_TABLE} ORDER BY seq"
                    )
                },
            )
        )
        records: list[AuditRecord] = []
        for row in rows:
            data = dict(row)
            for column in ("inputs", "outputs"):
                value = data.get(column)
                data[column] = json.loads(value) if isinstance(value, str) else (value or {})
            records.append(AuditRecord.model_validate(data))
        return records


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
    "AUDIT_HEAD_TABLE",
    "AUDIT_TABLE",
    "CASES_TABLE",
    "EXPECTED_TOOLS",
    "QUEUE_TABLE",
    "BorrowedStore",
    "open_borrowed_store",
]
