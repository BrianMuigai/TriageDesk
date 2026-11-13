"""Deterministic emergency pre-check and fast-arm suite (Phase 22, EMERG-01/02/04).

Offline, deterministic proofs for the pre-check contract and the two arms:

1. ``assess_emergency`` fires on a complete case whose deterministic score is the most
   urgent band, and does not fire on a complete lower-band case;
2. it never fires on an incomplete, out-of-scope or unstructured case (no imputation);
3. the verdict has no colour field — the pre-check cannot become a second colour source;
4. across every bundled eval case, ``fired`` equals the data-derived predicate;
5. the fast arm reaches the approval interrupt without calling ``normalize_case`` while
   the normal arm still calls it;
6. the paused payload carries the bypass fact on the fast arm and ``None`` otherwise;
7. the drawn topology and ``TRACER_NODES`` contain the new node and both arms.

The model and the MCP subprocess are never launched; the tools are the shared offline
fakes (``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import COMPLETE_CASE, EMERGENCY_CASE, build_graph_tools
from triagedesk.core.emergency import EmergencyVerdict, assess_emergency
from triagedesk.core.rules import colour_urgency
from triagedesk.core.schema import CaseInput
from triagedesk.core.scorer import score_priority
from triagedesk.evals.case import load_cases
from triagedesk.graph.build import TRACER_NODES, build_graph, route_after_emergency

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"


def _most_urgent() -> str:
    """The most urgent band, derived from the loaded substrate (never a literal)."""
    urgency = colour_urgency()
    return max(urgency, key=lambda colour: urgency[colour])


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


def _call_names(calls: list[tuple[str, Any]]) -> list[str]:
    return [name for name, _ in calls]


# --------------------------------------------------------------- verdict contract


def test_fires_on_a_complete_most_urgent_case() -> None:
    """A complete case the scorer puts in the most urgent band fires the pre-check (EMERG-01)."""
    verdict = assess_emergency(EMERGENCY_CASE)

    assert verdict.fired is True
    scored = score_priority(EMERGENCY_CASE, [])
    assert scored.colour == _most_urgent()
    assert f"colour={scored.colour}" in verdict.trigger
    assert any(fact.startswith("tews=") for fact in verdict.trigger)


def test_does_not_fire_on_a_complete_lower_band_case() -> None:
    """A complete case below the most urgent band takes the normal path (EMERG-04)."""
    verdict = assess_emergency(COMPLETE_CASE)

    assert verdict.fired is False
    assert verdict.reason


def test_does_not_fire_when_a_scored_vital_is_missing() -> None:
    """An incomplete case never fires — no value is imputed (EMERG-04)."""
    incomplete = EMERGENCY_CASE.model_copy(update={"respiratory_rate": None})

    verdict = assess_emergency(incomplete)

    assert verdict.fired is False
    assert "missing" in verdict.reason


def test_does_not_fire_on_an_out_of_scope_case() -> None:
    """A paediatric/out-of-scope case never fires — the scorer abstains first (EMERG-04)."""
    child = EMERGENCY_CASE.model_copy(update={"age_years": 8})

    assert assess_emergency(child).fired is False


def test_does_not_fire_on_an_unstructured_case() -> None:
    """A case with no structured vitals never fires (EMERG-04)."""
    assert assess_emergency(CaseInput()).fired is False
    assert assess_emergency(CaseInput(complaint="unwell")).fired is False


def test_verdict_has_no_colour_or_priority_field() -> None:
    """The verdict cannot carry a colour — a pre-check colour is unrepresentable (EMERG-02)."""
    fields = set(EmergencyVerdict.model_fields)

    assert fields == {"fired", "reason", "trigger"}
    for forbidden in ("colour", "priority", "target", "destination", "tews"):
        assert forbidden not in fields


def test_firing_matches_the_data_derived_predicate_across_bundled_cases() -> None:
    """For every eval case, ``fired`` equals the declared predicate — no hidden rule."""
    most_urgent = _most_urgent()
    for case in load_cases(CASES_DIR):
        scored = score_priority(case.case, [])
        expected = (
            not scored.abstained
            and not scored.out_of_scope
            and not scored.missing_vitals
            and scored.colour == most_urgent
        )
        assert assess_emergency(case.case).fired is expected, case.id


# --------------------------------------------------------------------- both arms


async def test_fast_arm_reaches_the_gate_without_extraction() -> None:
    """The fast arm skips ``normalize_case`` and still reaches the approval gate (EMERG-01)."""
    calls: list[tuple[str, Any]] = []
    app = build_graph(
        build_graph_tools(case=EMERGENCY_CASE, calls=calls),
        checkpointer=InMemorySaver(),
    )

    result = await app.ainvoke(
        {"raw_note": "44 year old, shocked", "case": EMERGENCY_CASE}, _config("fast-arm")
    )

    assert result.get("__interrupt__"), "the fast arm did not reach the gate"
    assert "normalize_case" not in _call_names(calls)
    assert result["emergency_verdict"].fired is True
    payload = result["__interrupt__"][0].value
    assert payload["emergency_verdict"] is not None
    assert payload["emergency_verdict"]["fired"] is True
    assert payload["emergency_verdict"]["trigger"]
    assert result.get("commit_result") is None


async def test_normal_arm_still_extracts_and_carries_no_bypass_fact() -> None:
    """The normal arm still calls ``normalize_case`` and reports no bypass (EMERG-04)."""
    calls: list[tuple[str, Any]] = []
    app = build_graph(
        build_graph_tools(case=COMPLETE_CASE, calls=calls),
        checkpointer=InMemorySaver(),
    )

    result = await app.ainvoke({"raw_note": "40 year old, chest pain"}, _config("normal-arm"))

    assert result.get("__interrupt__")
    assert "normalize_case" in _call_names(calls)
    assert result["emergency_verdict"].fired is False
    assert result["__interrupt__"][0].value["emergency_verdict"] is None


async def test_unstructured_note_takes_the_normal_arm() -> None:
    """A raw note with no structured case never fires the pre-check (EMERG-04)."""
    calls: list[tuple[str, Any]] = []
    app = build_graph(build_graph_tools(case=COMPLETE_CASE, calls=calls))

    result = await app.ainvoke({"raw_note": "40 year old, chest pain"})

    assert "normalize_case" in _call_names(calls)
    assert result["emergency_verdict"].fired is False


def test_route_after_emergency_selects_the_arm() -> None:
    """The ONE router maps the verdict to the fast or normal arm."""
    fired = EmergencyVerdict(fired=True)
    not_fired = EmergencyVerdict(fired=False)
    assert route_after_emergency({"emergency_verdict": fired}) == "retrieve"
    assert route_after_emergency({"emergency_verdict": not_fired}) == "normalize"
    assert route_after_emergency({}) == "normalize"


def test_topology_has_the_pre_check_and_both_arms() -> None:
    """``ingest → emergency_check → (retrieve | normalize)`` is drawn, and the kernel stays."""
    graph = build_graph(build_graph_tools())
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert "emergency_check" in TRACER_NODES
    assert ("ingest", "emergency_check") in edges
    assert ("emergency_check", "retrieve") in edges
    assert ("emergency_check", "normalize") in edges
    # The fast arm rejoins the unchanged kernel; nothing downstream was rewired.
    assert ("retrieve", "score") in edges
    assert ("normalize", "retrieve") in edges
