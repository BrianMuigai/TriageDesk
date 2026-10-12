"""One-way safety proof: a deferral reaches a terminal, never the gate or the commit.

AGENT-02, D8-08/D8-11/D8-12. A ``no_match`` case (or a low-coverage case) is deferred by
the ``assess`` node and routed to ``escalate`` / ``request_missing_info`` — terminals with
no edge to ``commit`` — so no ``commit_priority`` call and no queue row ever happen. The
deterministic ``recheck`` still runs *before* ``assess``, so a deferral prevents a commit
without suppressing the safety recheck.

Offline and deterministic: the tools are the shared fakes (``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import COMPLETE_CASE, build_graph_tools
from triagedesk.core import scorer
from triagedesk.core.schema import ConfidenceResult, PriorityResult
from triagedesk.evals.case import load_cases
from triagedesk.graph.build import build_graph, route_after_assess
from triagedesk.mcp import server as server_module

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, "
    "temperature 38.9, no trauma. Presenting with central chest pain."
)

# A complete-vitals case whose complaint matches no discriminator — the deferral class.
NO_MATCH_CASE = COMPLETE_CASE.model_copy(update={"complaint": "feeling unwell"})


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


# ---------------------------------------------------------------- structural topology


def test_a_deferral_cannot_reach_the_commit() -> None:
    """``recheck`` precedes ``assess``, and the deferral terminals have no edge to ``commit``."""
    graph = build_graph(build_graph_tools())
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("recheck", "assess") in edges, "recheck no longer precedes assess"
    assert ("assess", "approval_gate") in edges, "the neutral arm must still reach the gate"
    # ``commit`` is reachable only via ``approval_gate`` — the terminals cannot reach it.
    assert ("escalate", "commit") not in edges
    assert ("request_missing_info", "commit") not in edges


# --------------------------------------------------------- the deferral routing arms


def _deferral_signal() -> ConfidenceResult:
    """A deferring signal — the router reads only ``deferral`` (D8-12)."""
    return ConfidenceResult(deferral=True, level="low", components=[], reason="deferred")


def test_route_after_assess_sends_a_deferral_with_a_missing_vital_to_recovery() -> None:
    """The retained defensive arm routes a deferral with a missing scored vital to recovery.

    Under the current wiring this arm is unreachable (:func:`route_after_score` diverts
    every missing-vitals case before ``assess``); it is covered directly here so the intent
    is explicit and a future change to that diversion cannot silently drop the guard (WR-01).
    """
    state: dict[str, Any] = {
        "confidence": _deferral_signal(),
        "priority": PriorityResult(tews=0, missing_vitals=["temperature"]),
    }
    assert route_after_assess(state) == "request_missing_info"


def test_route_after_assess_escalates_a_deferral_and_gates_a_neutral_signal() -> None:
    """A deferral without a missing vital escalates; a non-deferral reaches the gate (D8-12)."""
    deferring: dict[str, Any] = {
        "confidence": _deferral_signal(),
        "priority": PriorityResult(tews=4),
    }
    assert route_after_assess(deferring) == "escalate"

    neutral: dict[str, Any] = {
        "confidence": ConfidenceResult(deferral=False, level="high", components=[], reason=""),
        "priority": PriorityResult(tews=4),
    }
    assert route_after_assess(neutral) == "approval_gate"


# ------------------------------------------------------- deferral on a committing case


async def test_a_forced_deferral_ends_at_a_terminal_with_no_write(memory_store) -> None:
    """A deferred otherwise-committing case ends at a terminal with zero writes (D8-12)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=NO_MATCH_CASE, calls=calls, store=memory_store)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE}, _config("deferral"))

    signal = result.get("confidence")
    assert signal is not None and signal.deferral is True, "the signal did not defer"
    assert result.get("escalation") is not None, "the deferral did not reach a terminal"
    assert result.get("commit_result") is None
    assert not result.get("__interrupt__"), "a deferral must not reach the approval gate"
    assert "commit_priority" not in [name for name, _ in calls]
    assert memory_store.rows == [], "a deferral wrote a queue row"


# --------------------------------------------------------------- E-09 end-to-end defer


async def test_no_match_e09_defers_to_a_terminal_without_a_queue_row(memory_store) -> None:
    """The declared failure E-09 is loudly deferred, not silently committed (D8-11)."""
    spec = next(case for case in load_cases(CASES_DIR) if case.id == "E-09")
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=spec.case, calls=calls, store=memory_store)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": spec.note}, _config("deferral-e09"))

    signal = result.get("confidence")
    assert signal is not None and signal.deferral is True
    assert result.get("escalation") is not None
    assert memory_store.rows == []
    assert "commit_priority" not in [name for name, _ in calls]


# ---------------------------------------------------- the scored colour is never changed


async def test_assess_does_not_change_the_scored_colour() -> None:
    """On the delivered path the colour is exactly the scorer's — ``assess`` never assigns it."""
    app = build_graph(build_graph_tools(case=COMPLETE_CASE), checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE}, _config("colour-unchanged"))

    assert result.get("__interrupt__"), "the matched case did not reach the gate"
    payload = result["__interrupt__"][0].value
    expected = scorer.score_priority(COMPLETE_CASE, list(result.get("matched_ids") or []))
    assert payload["colour"] == expected.colour
    assert result["priority"].colour == expected.colour


# --------------------------------------------------------- the tool is pure + audited


async def test_assess_confidence_is_pure_and_audited_exactly_once(memory_store) -> None:
    """The owned tool writes no queue row and appends exactly one audit record (D8-07)."""
    priority = scorer.score_priority(COMPLETE_CASE, ["chest_pain"])

    signal = await server_module.assess_confidence(["chest_pain"], False, priority)

    assert signal.deferral is False
    assert [record.tool for record in memory_store.audit_records] == ["assess_confidence"]
    assert memory_store.rows == [], "the pure tool wrote a queue row"
