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
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.durable import derive_thread_id
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import build_graph
from triagedesk.llm import client as llm_client
from triagedesk.llm.client import DEFAULT_MODEL, extract
from triagedesk.mcp import server as server_module
from triagedesk.observability import bind_trace
from triagedesk.observability.offline import harden_offline
from triagedesk.observability.spans import SPANS_PATH
from triagedesk.store.audit import GENESIS, AuditRecord, append, record_digest, verify
from triagedesk.store.borrowed import (
    CASES_TABLE,
    EXPECTED_TOOLS,
    QUEUE_TABLE,
    BorrowedStore,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"


def _case(case_id: str) -> CaseSpec:
    """Load one bundled eval case by id (the fixture is the declared input)."""
    return next(case for case in load_cases(CASES_DIR) if case.id == case_id)


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


async def test_a_span_sink_failure_never_breaks_the_tool_or_its_audit_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """A best-effort span sink that cannot be written must not fail the tool or fabricate
    a failed-tool audit record (CR-01).

    The sink is made unwritable by putting a *directory* where the JSONL file belongs, so
    ``open(..., "a")`` raises ``IsADirectoryError``. The owned tool must still return its
    real result, and the audit record must carry that real result with NO ``error`` key —
    observability can never turn a successful clinical call into an error.
    """
    (tmp_path / SPANS_PATH.name).mkdir()  # the fixture's sink path is now a directory
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=CaseInput(), matched_discriminator_ids=[]),
    )

    bind_trace("tr-sink-fail")
    result = await server_module.normalize_case("chest pain")

    assert isinstance(result, ExtractionResult), "the tool did not return its real result"
    records = await injected_store.read_audit_records()
    assert len(records) == 1, "a successful tool call must append exactly one audit record"
    record = records[0]
    assert record.tool == "normalize_case"
    assert record.actor == "agent"
    assert record.trace_id == "tr-sink-fail"
    assert "error" not in record.outputs, "the audit claimed a failure that did not happen"
    assert record.outputs == result.model_dump(mode="json")


async def test_an_owned_tool_without_a_bound_trace_records_an_empty_trace_id(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """A tool reached with no bound trace records ``trace_id=""`` — the declared scope (WR-02).

    The binding is a ``contextvars`` value, so it does not cross the owned-MCP **subprocess**
    boundary: a child process sees the contextvar default (empty). The demonstrated in-process
    paths (demo/eval/resume/replay) bind the trace, so they are covered; this test pins the
    boundary honestly rather than over-claiming it.
    """
    bind_trace("")  # what a fresh process — the owned stdio subprocess — sees
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=CaseInput(), matched_discriminator_ids=[]),
    )

    await server_module.normalize_case("chest pain")

    records = await injected_store.read_audit_records()
    assert records[-1].trace_id == ""


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


# ------------------------------------------ Task 2: node spans + the ONE model span


async def test_node_spans_carry_the_content_trace_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """Every executed node emits ONE ``node`` span traced to the content-derived id, and a
    node that wraps a tool call is that tool span's ``parent_id`` (D7-05, D7-07)."""
    case = _case("E-02")
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=case.case, matched_discriminator_ids=[]),
    )
    tools = build_tools(case, offline=False, recorder=UsageRecorder())
    graph = build_graph(tools, checkpointer=InMemorySaver())
    thread_id = derive_thread_id(case.note)

    await graph.ainvoke(
        {"raw_note": case.note, "case": case.case},
        {"configurable": {"thread_id": thread_id}},
    )

    spans = _read_sink(tmp_path)
    node_spans = [entry for entry in spans if entry["kind"] == "node"]
    tool_spans = [entry for entry in spans if entry["kind"] == "tool"]

    names = [entry["name"] for entry in node_spans]
    assert len(names) == len(set(names)), f"a node must emit exactly one span: {names}"
    assert {
        "ingest",
        "normalize",
        "retrieve",
        "score",
        "verify",
        "recheck",
        "approval_gate",
    } <= set(names)
    assert all(entry["trace_id"] == thread_id for entry in node_spans)
    assert all(entry["span_id"] and entry["started"] and entry["ended"] for entry in node_spans)

    normalize_node = next(entry for entry in node_spans if entry["name"] == "normalize")
    normalize_tool = next(entry for entry in tool_spans if entry["name"] == "normalize_case")
    assert normalize_tool["parent_id"] == normalize_node["span_id"]


def test_model_span_carries_no_prompt_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ONE model call emits ONE minimal span — the model tag + token counts, no text."""
    secret = "SECRET-COMPLAINT-TOKEN"
    payload = ExtractionResult(
        case=CaseInput(respiratory_rate=24), matched_discriminator_ids=[]
    ).model_dump_json()
    response = {"response": payload, "prompt_eval_count": 11, "eval_count": 7}
    monkeypatch.setattr(llm_client.ollama, "generate", lambda **kwargs: response)

    bind_trace("tr-model")
    extract(f"{secret} central chest pain")

    spans = _read_sink(tmp_path)
    model_spans = [entry for entry in spans if entry["kind"] == "model"]
    assert len(model_spans) == 1
    attrs = model_spans[0]["attributes"]
    assert set(attrs) == {"model", "tokens_in", "tokens_out"}
    assert attrs["model"] == DEFAULT_MODEL
    assert (attrs["tokens_in"], attrs["tokens_out"]) == (11, 7)
    assert secret not in json.dumps(model_spans[0])


async def test_offline_run_emits_no_model_span(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """A run whose model is stubbed above ``extract`` emits NO model span (Pitfall 6)."""
    case = _case("E-02")
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=case.case, matched_discriminator_ids=[]),
    )
    tools = build_tools(case, offline=False, recorder=UsageRecorder())
    graph = build_graph(tools, checkpointer=InMemorySaver())

    await graph.ainvoke(
        {"raw_note": case.note, "case": case.case},
        {"configurable": {"thread_id": derive_thread_id(case.note)}},
    )

    spans = _read_sink(tmp_path)
    assert not [entry for entry in spans if entry["kind"] == "model"]
    assert any(entry["kind"] == "tool" for entry in spans)


# ------------------------------------------ Task 3: offline hardening + the asserted guard

_TRACING_VARS = (
    "LANGSMITH_TRACING",
    "LANGSMITH_TRACING_V2",
    "LANGCHAIN_TRACING",
    "LANGCHAIN_TRACING_V2",
)


def test_harden_offline_asserts_tracing_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """After ``harden_offline`` tracing is off and the four tracing vars are gone (D7-03)."""
    langsmith_utils = pytest.importorskip("langsmith.utils")
    for name in _TRACING_VARS:
        monkeypatch.setenv(name, "true")
    langsmith_utils.get_env_var.cache_clear()

    harden_offline()

    assert langsmith_utils.tracing_is_enabled() is False
    for name in _TRACING_VARS:
        assert name not in os.environ


def test_harden_offline_disables_a_primed_tracer(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cached env read cannot keep the tracer on: the cache is cleared (Pitfall 2)."""
    langsmith_utils = pytest.importorskip("langsmith.utils")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    langsmith_utils.get_env_var.cache_clear()
    assert langsmith_utils.tracing_is_enabled() is True, "the primed tracer was not on"

    harden_offline()

    assert langsmith_utils.tracing_is_enabled() is False


def test_harden_offline_is_import_safe_without_langsmith(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``harden_offline`` is a no-op success when langsmith cannot be imported (D7-03)."""
    monkeypatch.setitem(sys.modules, "langsmith", None)

    harden_offline()  # must not raise
