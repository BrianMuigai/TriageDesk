"""Emergency-bypass proof suite (Phase 22, EMERG-01/03/05).

The counterweight to "more agentic": when the vitals already carry the answer, the model
is removed — and nothing else is. This suite proves both halves at once:

1. the fast arm never calls ``normalize_case`` while the deterministic kernel still runs
   (``match_discriminators``, ``score_priority``, ``retrieve_evidence``,
   ``raise_recheck_flag``, ``assess_confidence``);
2. the fast arm executes ``verify → recheck → assess → approval_gate`` and reaches the
   interrupt with NO queue write and NO ``commit_priority`` call;
3. the normal arm still extracts and its executed node order is today's order with the
   one new pre-check node inserted after ``ingest``;
4. the bypass is an audit/span fact — one ``emergency_check`` node span carrying the
   content-derived trace id — and the paused payload names the trigger;
5. a durable pause re-loads the verdict as a typed ``EmergencyVerdict`` (the checkpointer
   allowlist holds), so the provenance survives a restart.

The model and the MCP subprocess are never launched; the tools are the shared offline
fakes (``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import COMPLETE_CASE, EMERGENCY_CASE, build_graph_tools
from triagedesk.core.emergency import EmergencyVerdict
from triagedesk.core.scorer import score_priority
from triagedesk.graph.build import build_graph, checkpointed_graph
from triagedesk.graph.nodes import case_id_for_note
from triagedesk.observability.spans import read_spans

NOTE = "44 year old, walking, alert. RR 30, HR 130, systolic BP 70, temperature 37.0, no trauma."

# The executed node order each arm must have. The fast arm is the normal arm minus the
# ONE node it skips; nothing else may differ (EMERG-01, EMERG-04).
NORMAL_ORDER = [
    "ingest",
    "emergency_check",
    "normalize",
    "retrieve",
    "score",
    "ground",
    "verify",
    "recheck",
    "assess",
    "approval_gate",
]
FAST_ORDER = [name for name in NORMAL_ORDER if name != "normalize"]

_KERNEL_TOOLS = (
    "match_discriminators",
    "score_priority",
    "retrieve_evidence",
    "raise_recheck_flag",
    "assess_confidence",
)


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


def _call_names(calls: list[tuple[str, Any]]) -> list[str]:
    return [name for name, _ in calls]


def _node_order() -> list[str]:
    """The executed node names, in span-append order (the audit trail is the proof).

    Reads through the ONE span reader (``observability.spans.read_spans``), which resolves
    the autouse test sink, so the suite never re-implements the JSONL format (DRY).
    """
    return [entry["name"] for entry in read_spans() if entry["kind"] == "node"]


# ------------------------------------------------------- the fast arm: model skipped


async def test_fast_arm_skips_extraction_but_runs_the_kernel() -> None:
    """No ``normalize_case``; every kernel tool still runs (EMERG-01, EMERG-03)."""
    calls: list[tuple[str, Any]] = []
    writes: list[Any] = []
    app = build_graph(
        build_graph_tools(case=EMERGENCY_CASE, calls=calls, writes=writes),
        checkpointer=InMemorySaver(),
    )

    result = await app.ainvoke(
        {"raw_note": NOTE, "case": EMERGENCY_CASE, "previous_case": EMERGENCY_CASE},
        _config("bypass-kernel"),
    )

    names = _call_names(calls)
    assert "normalize_case" not in names, "the fast arm waited for extraction"
    for tool in _KERNEL_TOOLS:
        assert tool in names, f"the fast arm skipped the kernel tool {tool!r}"

    assert _node_order() == FAST_ORDER
    assert result.get("__interrupt__"), "the fast arm did not reach the clinician"
    assert result["priority"].colour is not None


async def test_fast_arm_writes_nothing_before_the_gate() -> None:
    """No queue write and no ``commit_priority`` call precede the interrupt (EMERG-03)."""
    calls: list[tuple[str, Any]] = []
    writes: list[Any] = []
    app = build_graph(
        build_graph_tools(case=EMERGENCY_CASE, calls=calls, writes=writes),
        checkpointer=InMemorySaver(),
    )

    result = await app.ainvoke(
        {"raw_note": NOTE, "case": EMERGENCY_CASE}, _config("bypass-no-write")
    )

    assert result.get("__interrupt__")
    assert result.get("commit_result") is None
    assert writes == []
    assert "commit_priority" not in _call_names(calls)


async def test_fast_arm_payload_carries_the_bypass_fact(tmp_path: Path) -> None:
    """The clinician sees that the case was fast-tracked, and why (EMERG-05)."""
    app = build_graph(
        build_graph_tools(case=EMERGENCY_CASE), checkpointer=InMemorySaver()
    )

    result = await app.ainvoke(
        {"raw_note": NOTE, "case": EMERGENCY_CASE}, _config("bypass-payload")
    )

    payload = result["__interrupt__"][0].value
    assert payload["emergency"] is not None
    assert payload["emergency"]["fired"] is True
    assert payload["emergency"]["reason"]
    assert payload["emergency"]["trigger"]


async def test_emergency_check_emits_one_span_with_the_trace_id() -> None:
    """The composition-root wrapper is the audit event — no extra writer (EMERG-05)."""
    app = build_graph(
        build_graph_tools(case=EMERGENCY_CASE), checkpointer=InMemorySaver()
    )

    await app.ainvoke({"raw_note": NOTE, "case": EMERGENCY_CASE}, _config("bypass-span"))

    emergency_spans = [
        entry
        for entry in read_spans()
        if entry["kind"] == "node" and entry["name"] == "emergency_check"
    ]
    assert len(emergency_spans) == 1, "the pre-check must emit exactly one node span"
    assert emergency_spans[0]["trace_id"] == case_id_for_note(NOTE)


# ----------------------------------------------------- the normal arm: unchanged


async def test_normal_arm_runs_the_unchanged_sequence() -> None:
    """The normal arm extracts and keeps today's node order plus the pre-check (EMERG-04)."""
    calls: list[tuple[str, Any]] = []
    app = build_graph(
        build_graph_tools(case=COMPLETE_CASE, calls=calls),
        checkpointer=InMemorySaver(),
    )

    result = await app.ainvoke(
        {"raw_note": NOTE, "case": COMPLETE_CASE, "previous_case": COMPLETE_CASE},
        _config("normal-unchanged"),
    )

    assert "normalize_case" in _call_names(calls)
    assert _node_order() == NORMAL_ORDER

    expected = score_priority(COMPLETE_CASE, list(result.get("matched_ids") or []))
    assert result["priority"].colour == expected.colour
    assert result["__interrupt__"][0].value["emergency"] is None


# ------------------------------------------------------------ durable provenance


async def test_a_paused_run_reloads_the_verdict_as_a_typed_model(tmp_path: Path) -> None:
    """The bypass fact survives a restart with its type intact (EMERG-05, D-09)."""
    db_path = tmp_path / "checkpoints.db"
    tools = build_graph_tools(case=EMERGENCY_CASE)
    config = _config("bypass-durable")

    async with checkpointed_graph(tools, db_path) as graph:
        result = await graph.ainvoke({"raw_note": NOTE, "case": EMERGENCY_CASE}, config)
        assert result["emergency"].fired is True

    async with checkpointed_graph(tools, db_path) as reopened:
        snapshot = await reopened.aget_state(config)

    verdict = snapshot.values["emergency"]
    assert isinstance(verdict, EmergencyVerdict), "the checkpointer downgraded the verdict"
    assert verdict.fired is True
