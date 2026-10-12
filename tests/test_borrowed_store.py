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
    READ_TOOLS,
    TOOL_DELETE_RECORDS,
    TOOL_QUERY,
    BorrowedStore,
    is_read_only_statement,
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


class _DegradingBorrowedTools(_FakeBorrowedTools):
    """A fake whose read paths surprise the adapter (an unverified wire shape).

    ``db_info`` raises and ``read_records`` returns a scalar, so the probe must record a
    degradation rather than let the surprise crash the store-open path (D9-14, T-09-22).
    """

    def tools(self) -> dict[str, Any]:
        tools = super().tools()

        async def db_info(arguments: Mapping[str, Any]) -> Any:
            self._record("db_info", arguments)
            raise RuntimeError("borrowed db_info is unavailable")

        async def read_records(arguments: Mapping[str, Any]) -> Any:
            self._record("read_records", arguments)
            return 42  # a scalar is not a row payload — the shape surprise under test

        tools["db_info"] = db_info
        tools["read_records"] = read_records
        return tools


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
    assert f"INSERT INTO {QUEUE_TABLE}" in arguments["sql"]
    assert "ON CONFLICT(case_id, content_hash) DO UPDATE" in arguments["sql"]
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


# ---------------------------------------------- MCP-01: read paths used, mutations refused


def test_read_tools_are_exactly_the_five_reads() -> None:
    """The allowlist is the five read tools; the three mutating record tools are excluded."""
    assert set(READ_TOOLS) == {
        "db_info",
        "query",
        "list_tables",
        "get_table_schema",
        "read_records",
    }
    assert {"create_record", "update_records", "delete_records"}.isdisjoint(READ_TOOLS)


async def test_ensure_schema_observes_the_borrowed_read_tools() -> None:
    """MCP-01 is demonstrated, not asserted: the read tools are OBSERVED being called (D9-14).

    After ``ensure_schema`` the fake's call log carries every read tool, and the recorded
    ``read_path_report`` marks each as ``ok`` — so the borrowed read paths are genuinely
    reached behind the unchanged ``Store`` protocol, not merely declared as constants.
    """
    fake = _FakeBorrowedTools()
    store = BorrowedStore(fake.tools())

    await store.ensure_schema()

    observed = [name for name, _ in fake.calls]
    assert {"db_info", "list_tables", "get_table_schema", "read_records"} <= set(observed)
    assert store.read_path_report == {
        "db_info": "ok",
        "list_tables": "ok",
        "get_table_schema": "ok",
        "read_records": "ok",
    }


async def test_a_mutation_on_the_read_path_is_refused_before_the_borrowed_server() -> None:
    """A mutation statement is refused BEFORE reaching the borrowed server (D9-12, T-09-20).

    The guard seam is driven directly because IT is the enforcement point; the fake's call
    log is the evidence that nothing was touched — the refusal happens before ``self._tools``
    is dereferenced, so no recorded call can carry the mutation.
    """
    fake = _FakeBorrowedTools()
    store = BorrowedStore(fake.tools())
    statement = "DELETE FROM queue"

    with pytest.raises(ValueError, match="non-read statement"):
        await store._call(TOOL_QUERY, {"sql": statement})

    assert all(arguments.get("sql") != statement for _, arguments in fake.calls)
    assert fake.calls == [], "a refused statement must reach no borrowed tool"


async def test_an_off_allowlist_tool_name_is_refused() -> None:
    """A tool outside the allowlist is refused fail-closed and never reaches the server (D9-12)."""
    fake = _FakeBorrowedTools()
    store = BorrowedStore(fake.tools())

    with pytest.raises(ValueError, match="read-only allowlist"):
        await store._call(TOOL_DELETE_RECORDS, {"table": QUEUE_TABLE})

    assert all(name != TOOL_DELETE_RECORDS for name, _ in fake.calls)
    assert fake.calls == [], "a refused tool must reach no borrowed tool"


_READ_ONLY_STATEMENTS = (
    "SELECT 1",
    "  select * from queue",
    "PRAGMA table_info(audit)",
    "PRAGMA table_info (audit)",
    "PRAGMA index_list(queue)",
    "VALUES (1)",
)
# Every entry here must be refused (D9-12, fail closed). The compound/mutating
# statements below pin the three bypasses a leading-keyword-only classifier admitted:
# a WITH-prefixed DML, a PRAGMA write, and a multi-statement string.
_NOT_READ_STATEMENTS = (
    "INSERT INTO queue VALUES (1)",
    "UPDATE queue SET colour = 'RED'",
    "DELETE FROM queue",
    "CREATE TABLE t (a)",
    "DROP TABLE t",
    "ALTER TABLE t ADD COLUMN a",
    # a CTE may prefix DML, so a WITH head is not provably a read — even this read-only CTE
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "WITH x AS (SELECT 1) DELETE FROM queue",
    # PRAGMA writes are not reads (a bare/unknown PRAGMA mutates state)
    "PRAGMA writable_schema = 1",
    "PRAGMA journal_mode = DELETE",
    # an unknown pragma sharing an admitted prefix is refused (name-boundary match)
    "PRAGMA table_infox(queue)",
    # EXPLAIN executes PRAGMA at compile time, so an EXPLAIN-prefixed PRAGMA write is a
    # write; EXPLAIN is refused outright (no caller issues it)
    "EXPLAIN SELECT 1",
    "EXPLAIN PRAGMA writable_schema = 1",
    "EXPLAIN QUERY PLAN PRAGMA cache_size = 100",
    # a side-effecting function is not a read, even behind a SELECT head
    "SELECT load_extension('evil')",
    # a compound string is not a single read statement
    "SELECT 1; DELETE FROM queue",
    "",
    "   ",
)


@pytest.mark.parametrize("statement", _READ_ONLY_STATEMENTS)
def test_classifier_accepts_reads(statement: str) -> None:
    """A read-only leading keyword is recognised, including lowercase and leading space."""
    assert is_read_only_statement(statement) is True


@pytest.mark.parametrize("statement", _NOT_READ_STATEMENTS)
def test_classifier_fails_closed_on_everything_else(statement: str) -> None:
    """Anything not recognised as a read — mutations and the empty string — is refused."""
    assert is_read_only_statement(statement) is False


async def test_a_read_path_shape_mismatch_degrades_without_raising() -> None:
    """An unverified read shape degrades — recorded, never raising out of ``ensure_schema``.

    The real ``mcp-sqlite@1.0.9`` shapes for ``get_table_schema``/``read_records`` are
    unverified, so a surprise must not crash the store-open path the demo, eval, resume and
    commit all depend on (D9-14, T-09-22). The store must remain fully usable afterwards.
    """
    fake = _DegradingBorrowedTools()
    store = BorrowedStore(fake.tools())

    await store.ensure_schema()  # must not raise

    assert store.read_path_report["db_info"].startswith("degraded")
    assert store.read_path_report["read_records"].startswith("degraded")
    assert store.read_path_report["list_tables"] == "ok"
    assert store.read_path_report["get_table_schema"] == "ok"

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
    read_row = await store.read_queue_row("c-1", "abc123")
    assert read_row is not None and read_row.colour == "ORANGE"
    await store.upsert_queue_row(read_row)
