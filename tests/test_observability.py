"""Local observability proof suite (Plan 07-01, AGENT-04, D7-01…D7-16).

Offline, deterministic proofs for the phase's two headline properties:

* **nothing left the machine** — tool/node/model spans land in ONE local JSONL sink, no
  span carries clinical text, and cloud tracing is provably disabled; and
* **every audit record joins to its spans** — a first-class, content-derived ``trace_id``
  survives the production (borrowed SQLite) store round-trip.

The suite is hermetic: the model is stubbed at its ONE seam, the borrowed server is a
stdlib-``sqlite3``-backed fake, and the span sink is redirected to ``tmp_path`` by the
autouse conftest fixture — no subprocess, no network, no repo-root artefact.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.mcp import server as server_module
from triagedesk.observability import bind_trace
from triagedesk.observability.spans import SPANS_PATH
from triagedesk.store.audit import GENESIS, AuditRecord, append, record_digest, verify
from triagedesk.store.borrowed import (
    CASES_TABLE,
    EXPECTED_TOOLS,
    QUEUE_TABLE,
    BorrowedStore,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_sink(tmp_path: Path) -> list[dict[str, Any]]:
    """Read the redirected span sink back as parsed JSON lines (the ONE reader)."""
    path = tmp_path / SPANS_PATH.name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class _SqliteBorrowedTools:
    """A stdlib-``sqlite3``-backed borrowed tool set: the ``query`` tool runs real SQL.

    Mirrors the Phase-1 handshake's tool surface (``EXPECTED_TOOLS``) but executes each
    statement against an in-memory database, so the audit round-trip (including the
    ``trace_id`` column) is exercised for real — the trap the in-memory double hides
    (Pitfall 1).
    """

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, name: str, arguments: Any) -> None:
        self.calls.append((name, dict(arguments)))

    def tools(self) -> dict[str, Any]:
        async def db_info(arguments: Any) -> Any:
            self._record("db_info", arguments)
            return {"tableCount": 2}

        async def query(arguments: Any) -> Any:
            self._record("query", arguments)
            cursor = self.conn.execute(arguments["sql"], arguments.get("values") or [])
            rows = [dict(row) for row in cursor.fetchall()]
            self.conn.commit()
            return rows

        async def list_tables(arguments: Any) -> Any:
            self._record("list_tables", arguments)
            return [QUEUE_TABLE, CASES_TABLE]

        async def get_table_schema(arguments: Any) -> Any:
            self._record("get_table_schema", arguments)
            return {"tableName": arguments.get("tableName")}

        async def create_record(arguments: Any) -> Any:
            self._record("create_record", arguments)
            return {"inserted": True}

        async def read_records(arguments: Any) -> Any:
            self._record("read_records", arguments)
            return []

        async def update_records(arguments: Any) -> Any:
            self._record("update_records", arguments)
            return {"updated": True}

        async def delete_records(arguments: Any) -> Any:
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


def test_expected_tools_match_the_phase_1_handshake() -> None:
    """The sqlite fake carries exactly the borrowed tool set Phase 1 verified (TOOL-06)."""
    assert set(EXPECTED_TOOLS) == set(_SqliteBorrowedTools().tools())


# ----------------------------------------------- Task 1: span writer + trace_id join


async def test_audit_trace_id_round_trips_through_the_borrowed_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """A real owned tool call emits one tool span AND an audit record whose trace_id
    survives the borrowed store's INSERT→SELECT round-trip (D7-06, Pitfall 1)."""
    fake = _SqliteBorrowedTools()
    store = BorrowedStore(fake.tools())
    await store.ensure_schema()
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=CaseInput(), matched_discriminator_ids=[]),
    )

    server_module.set_store(store)
    try:
        bind_trace("tr-1")
        await server_module.normalize_case("chest pain")
    finally:
        server_module.set_store(None)

    records = await store.read_audit_records()
    assert len(records) == 1, "a real tool call must append exactly one audit record"
    assert records[0].trace_id == "tr-1", "trace_id was silently dropped by the store"

    spans = _read_sink(tmp_path)
    assert [entry["kind"] for entry in spans] == ["tool"]
    assert spans[0]["trace_id"] == "tr-1"
    assert spans[0]["attributes"]["trace_id"] == "tr-1"


def test_trace_id_defaults_empty_and_is_sealed_by_the_digest() -> None:
    """``trace_id`` defaults to ``""`` and is covered by the canonical record digest."""
    common: dict[str, Any] = {
        "seq": 0,
        "ts": datetime(2026, 10, 9, 16, 0, tzinfo=UTC),
        "case_id": "c-1",
        "tool": "score_priority",
        "actor": "agent",
        "prev_hash": GENESIS,
    }
    assert AuditRecord(**common).trace_id == ""

    first = AuditRecord(**common, trace_id="tr-1")
    second = AuditRecord(**common, trace_id="tr-2")
    assert record_digest(first) != record_digest(second)


async def test_verify_stays_valid_for_a_chain_carrying_trace_ids(memory_store: Any) -> None:
    """A chain whose records all carry their own ``trace_id`` verifies (AUDIT-01, D7-06)."""
    await append(memory_store, {"tool": "normalize_case", "actor": "agent", "trace_id": "tr-1"})
    await append(memory_store, {"tool": "score_priority", "actor": "agent", "trace_id": "tr-1"})

    assert (await verify(memory_store)).valid is True


def test_no_spans_artifact_is_written_to_the_repo_root() -> None:
    """The autouse fixture keeps the sink out of the repository (Pitfall 5)."""
    assert not (REPO_ROOT / SPANS_PATH.name).exists()
