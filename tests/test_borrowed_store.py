"""Borrowed SQLite MCP store wiring tests (Plan 03-02, TOOL-06, D-10/D-13).

The real handshake with ``mcp-sqlite@1.0.9`` is Phase-1 evidence
(``evidence/mcp-spike.json``); this suite proves the WIRING. It exercises
:class:`BorrowedStore` through an injected fake tool set (the same
``name -> async callable`` seam ``mcp/adapter`` supplies), so no subprocess is
launched and the suite stays offline and deterministic.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from triagedesk.store import QueueRow
from triagedesk.store.borrowed import (
    CASES_TABLE,
    EXPECTED_TOOLS,
    QUEUE_TABLE,
    TOOL_QUERY,
    BorrowedStore,
)

# The exact tool surface Phase 1 verified on the borrowed server (evidence/mcp-spike.json).
PHASE_1_BORROWED_TOOLS = {
    "db_info",
    "query",
    "list_tables",
    "get_table_schema",
    "create_record",
    "read_records",
    "update_records",
    "delete_records",
}


class _FakeBorrowedTools:
    """A fake mcp-sqlite tool set: async callables, a call log and a canned response."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any]]] = []
        self.response: Any = []

    def _record(self, name: str, arguments: Mapping[str, Any]) -> None:
        self.calls.append((name, dict(arguments)))

    def tools(self) -> dict[str, Any]:
        async def db_info(arguments: Mapping[str, Any]) -> Any:
            self._record("db_info", arguments)
            return {"tableCount": 2}

        async def query(arguments: Mapping[str, Any]) -> Any:
            self._record("query", arguments)
            return self.response

        async def list_tables(arguments: Mapping[str, Any]) -> Any:
            self._record("list_tables", arguments)
            return [QUEUE_TABLE, CASES_TABLE]

        async def get_table_schema(arguments: Mapping[str, Any]) -> Any:
            self._record("get_table_schema", arguments)
            return {"tableName": arguments.get("tableName")}

        async def create_record(arguments: Mapping[str, Any]) -> Any:
            self._record("create_record", arguments)
            return {"inserted": True}

        async def read_records(arguments: Mapping[str, Any]) -> Any:
            self._record("read_records", arguments)
            return self.response

        async def update_records(arguments: Mapping[str, Any]) -> Any:
            self._record("update_records", arguments)
            return {"updated": True}

        async def delete_records(arguments: Mapping[str, Any]) -> Any:
            self._record("delete_records", arguments)
            return {"deleted": True}

        return {
            "db_info": db_info,
            "query": query,
            "list_tables": list_tables,
            "get_table_schema": get_table_schema,
            "create_record": create_record,
            "read_records": read_records,
            "update_records": update_records,
            "delete_records": delete_records,
        }


def _content_block(payload: Any) -> list[dict[str, str]]:
    """Wrap a payload as an MCP content block — the shape the adapter hands back."""
    return [{"type": "text", "text": json.dumps(payload)}]


def test_expected_tools_match_the_phase_1_handshake() -> None:
    """The wiring declares exactly the borrowed tool set Phase 1 verified (TOOL-06)."""
    assert set(EXPECTED_TOOLS) == PHASE_1_BORROWED_TOOLS


def test_borrowed_store_requires_the_full_tool_set() -> None:
    """A missing borrowed tool is rejected loudly — never silently ignored (SOLID: L)."""
    with pytest.raises(ValueError, match="missing required tools"):
        BorrowedStore({})


async def test_ensure_schema_creates_both_tables_via_the_query_tool() -> None:
    """``ensure_schema`` creates the queue and case tables through the borrowed tool."""
    fake = _FakeBorrowedTools()
    store = BorrowedStore(fake.tools())

    await store.ensure_schema()

    sql = [arguments["sql"] for name, arguments in fake.calls if name == TOOL_QUERY]
    assert any(f"CREATE TABLE IF NOT EXISTS {QUEUE_TABLE}" in statement for statement in sql)
    assert any(f"CREATE TABLE IF NOT EXISTS {CASES_TABLE}" in statement for statement in sql)


async def test_upsert_queue_row_inserts_through_the_query_tool() -> None:
    """The queue write goes through the borrowed ``query`` tool, keyed on both columns."""
    fake = _FakeBorrowedTools()
    store = BorrowedStore(fake.tools())
    row = QueueRow(
        case_id="c-1",
        content_hash="abc123",
        colour="ORANGE",
        target="< 10 min",
        position=1,
        created_at=datetime(2026, 10, 9, 16, 0, 0, tzinfo=UTC),
    )

    await store.upsert_queue_row(row)

    name, arguments = fake.calls[-1]
    assert name == TOOL_QUERY
    assert f"INSERT OR IGNORE INTO {QUEUE_TABLE}" in arguments["sql"]
    assert arguments["values"][0] == "c-1"
    assert arguments["values"][1] == "abc123"


async def test_read_queue_row_parses_a_content_block_row() -> None:
    """A row returned as an MCP content block decodes back to the shared contract."""
    fake = _FakeBorrowedTools()
    fake.response = _content_block(
        [
            {
                "case_id": "c-1",
                "content_hash": "abc123",
                "colour": "ORANGE",
                "target": "< 10 min",
                "position": 1,
                "created_at": "2026-10-09T16:00:00Z",
            }
        ]
    )
    store = BorrowedStore(fake.tools())

    row = await store.read_queue_row("c-1", "abc123")

    assert row is not None
    assert row.case_id == "c-1"
    assert row.colour == "ORANGE"


async def test_read_queue_row_returns_none_when_absent() -> None:
    """An empty result decodes to ``None`` — never a synthesised row."""
    fake = _FakeBorrowedTools()
    fake.response = _content_block([])
    store = BorrowedStore(fake.tools())

    assert await store.read_queue_row("c-1", "nope") is None


async def test_next_position_reads_the_max_plus_one() -> None:
    """``next_position`` parses the borrowed ``max(position) + 1`` result."""
    fake = _FakeBorrowedTools()
    fake.response = _content_block([{"next_position": 4}])
    store = BorrowedStore(fake.tools())

    assert await store.next_position() == 4
