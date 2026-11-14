"""The two-arm measurement: baseline vs adaptive, and the facts that prove the difference.

Offline and deterministic (no model, no MCP subprocess). Six proofs:

1. ``build_graph(..., planner=False)`` omits the four planner nodes and wires
   ``retrieve -> finish_investigation`` directly (MEAS-02);
2. on BOTH arms ``predecessors("score") == {"finish_investigation"}`` and
   ``predecessors("commit") == {"approval_gate"}`` — the switch changes the envelope, never the
   kernel (MEAS-03);
3. a run records its investigation steps, action sequence, guard overrides, elicitation
   outcome and emergency-bypass fact; a baseline run records ``None``/empty for the same slots
   (MEAS-01);
4. the recorded facts are NOT sealed in ``report_digest`` — adding them leaves the digest
   unchanged, so the published digest contract does not move (MEAS-01);
5. the analyser publishes the ``adaptive`` block from those facts, and a baseline report
   yields an all-zero block rather than an error (MEAS-01/02);
6. ``run_eval(..., planner=False)`` writes ``planner=False`` and the SAME delivered colour as
   the adaptive arm on the same case (MEAS-02).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from conftest import COMPLETE_CASE, EMERGENCY_CASE, build_graph_tools
from triagedesk.core.schema import InvestigationState, PlanAction, PlanDecision
from triagedesk.evals.analysis import analyse
from triagedesk.evals.report import (
    Analysis,
    Provenance,
    Report,
    ReportCase,
    _digest_payload,
    compute_report_digest,
)
from triagedesk.evals.runner import run_eval
from triagedesk.graph.build import PLANNER_NODES, build_graph, in_memory_checkpointer
from triagedesk.store.memory import InMemoryStore

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

_PROVENANCE = Provenance(
    model_tag="test-model",
    ollama_version="test",
    prompt_hash="prompt",
    sats_tews_hash="tews",
    sats_discriminators_hash="discriminators",
    harness_commit="deadbeef",
)


def _predecessors(graph: Any) -> dict[str, set[str]]:
    """Inbound edges of the compiled graph, keyed by target (the ONE reader)."""
    predecessors: dict[str, set[str]] = {}
    for edge in graph.get_graph().edges:
        predecessors.setdefault(edge.target, set()).add(edge.source)
    return predecessors


def _report(cases: list[ReportCase], *, planner: bool = True) -> Report:
    """A minimal sealed-shaped report over *cases* (no write, no digest yet)."""
    return Report(
        mode="offline",
        runs=3,
        cases_dir=str(CASES_DIR),
        provenance=_PROVENANCE,
        planner=planner,
        cases=cases,
    )


def _case(case_id: str = "E-01", **overrides: Any) -> ReportCase:
    """One passing GREEN case with a latency sample, plus any overridden facts."""
    base = ReportCase(
        case_id=case_id,
        expected="GREEN",
        runs=1,
        colours=["GREEN"],
        outcomes=["GREEN"],
        matched_discriminators=[[]],
        citations=[["RR-band"]],
        delivered=[True],
        routes=["ok"],
        attempts=[1],
        colour_stable=True,
        matched_set_stable=True,
        field_stable=True,
        invariants={"INV-1": True, "INV-2": True, "INV-3": True, "INV-4": True},
        invariants_pass=True,
        passed=True,
        latency_s=[0.1],
    )
    return base.model_copy(update=overrides)


# ------------------------------------------------- 1. the baseline graph is the v1.2 path


def test_baseline_graph_omits_the_planner_nodes() -> None:
    """``planner=False`` adds no planner node and wires retrieve straight to the kernel."""
    adaptive = build_graph(build_graph_tools(case=COMPLETE_CASE))
    baseline = build_graph(build_graph_tools(case=COMPLETE_CASE), planner=False)

    adaptive_nodes = set(adaptive.get_graph().nodes)
    baseline_nodes = set(baseline.get_graph().nodes)
    assert set(PLANNER_NODES) <= adaptive_nodes
    assert not set(PLANNER_NODES) & baseline_nodes
    assert "finish_investigation" in baseline_nodes

    baseline_edges = {
        (edge.source, edge.target) for edge in baseline.get_graph().edges
    }
    assert ("retrieve", "finish_investigation") in baseline_edges


# --------------------------------------- 2. the kernel is identical on both arms (MEAS-03)


def test_both_arms_keep_the_kernel_edges_exact() -> None:
    """The switch changes the envelope only: score and commit keep one inbound edge."""
    for planner in (True, False):
        graph = build_graph(build_graph_tools(case=COMPLETE_CASE), planner=planner)
        predecessors = _predecessors(graph)
        assert predecessors["score"] == {"finish_investigation"}, planner
        assert predecessors["commit"] == {"approval_gate"}, planner


# ------------------------------------------ 3. the recorded facts (MEAS-01)


def _planning_tools(
    actions: list[PlanAction], calls: list[tuple[str, Any]]
) -> dict[str, Any]:
    """Tools whose planner returns *actions* in order, then finishes (deterministic)."""
    tools = build_graph_tools(case=COMPLETE_CASE, calls=calls)
    queue = list(actions)

    async def plan_next_step(inp: Mapping[str, Any]) -> Any:
        state = InvestigationState.model_validate(inp["investigation"])
        action = queue.pop(0) if queue else PlanAction.FINISH_INVESTIGATION
        return PlanDecision(
            action=action,
            rationale="test",
            step=state.step + 1,
            budget_left=max(state.budget_left - 1, 0),
        )

    tools["plan_next_step"] = plan_next_step
    return tools


async def test_adaptive_run_records_steps_actions_and_elicitation() -> None:
    """An ask_question run records its two steps, its action history and the outcome."""
    calls: list[tuple[str, Any]] = []
    graph = build_graph(
        _planning_tools([PlanAction.ASK_QUESTION], calls),
        checkpointer=in_memory_checkpointer(),
    )
    result = await graph.ainvoke(
        {"raw_note": "note", "case": COMPLETE_CASE},
        {"configurable": {"thread_id": "adaptive-facts"}},
    )

    facts = result["investigation"]
    assert facts.steps == 2
    assert [action.value for action in facts.history] == ["ask_question", "finish_investigation"]
    assert facts.guard_overrides == 0
    # In-process there is no MCP client, so the shipped tool honestly answers ``unavailable``.
    assert result["elicitation_outcome"] == "unavailable"


async def test_emergency_run_records_the_bypass_and_no_plan() -> None:
    """The fast arm records the bypass fact and never writes an investigation accumulator."""
    graph = build_graph(
        build_graph_tools(case=EMERGENCY_CASE), checkpointer=in_memory_checkpointer()
    )
    result = await graph.ainvoke(
        {"raw_note": "note", "case": EMERGENCY_CASE},
        {"configurable": {"thread_id": "emergency-facts"}},
    )

    assert result["emergency_verdict"].fired is True
    assert "investigation" not in result


# ------------------------------------- 4. the new facts stay out of the digest (MEAS-01)


def test_adaptive_facts_are_not_sealed_in_the_report_digest() -> None:
    """Adding volatile investigation facts leaves ``report_digest`` unchanged."""
    plain = _case()
    measured = plain.model_copy(
        update={
            "investigation_steps": [2],
            "plan_actions": [["ask_question", "finish_investigation"]],
            "guard_overrides": [0],
            "elicitation_outcomes": ["unavailable"],
            "emergency_bypass": [False],
        }
    )
    assert compute_report_digest(_report([plain])) == compute_report_digest(
        _report([measured])
    )
    payload = _digest_payload(_report([measured]))
    case_payload = payload["cases"][0]
    for volatile in (
        "investigation_steps",
        "plan_actions",
        "guard_overrides",
        "elicitation_outcomes",
        "emergency_bypass",
    ):
        assert volatile not in case_payload


# --------------------------------------------- 5. the adaptive analysis block (MEAS-01/02)


def test_adaptive_analysis_publishes_the_recorded_facts() -> None:
    """The analyser derives the adaptive block from the per-run facts, not from a re-run."""
    case = _case(
        investigation_steps=[2, 3, None],
        plan_actions=[
            ["ask_question", "finish_investigation"],
            ["gather_evidence", "finish_investigation"],
            [],
        ],
        guard_overrides=[1, 0, 0],
        elicitation_outcomes=["unavailable", None, None],
        emergency_bypass=[False, False, False],
        outcomes=["GREEN", "GREEN", "GREEN"],
        latency_s=[0.1, 0.2, 0.3],
    )
    analysis = analyse(_report([case]))
    adaptive = analysis.adaptive
    assert adaptive.runs_with_investigation == 2
    assert adaptive.mean_steps == pytest.approx(2.5)
    assert adaptive.max_steps == 3
    assert adaptive.action_counts["finish_investigation"] == 2
    assert adaptive.action_counts["ask_question"] == 1
    assert adaptive.guard_override_rate == pytest.approx(0.5)
    assert adaptive.elicitation_counts == {"unavailable": 1}
    assert adaptive.emergency_bypass_cases == []


def test_baseline_report_yields_an_empty_adaptive_block() -> None:
    """A baseline report (all ``None``) analyses to zeros, never an error."""
    case = _case(investigation_steps=[None], plan_actions=[[]], guard_overrides=[0])
    adaptive = analyse(_report([case], planner=False)).adaptive
    assert adaptive.runs_with_investigation == 0
    assert adaptive.mean_steps == 0.0
    assert adaptive.max_steps == 0
    assert adaptive.action_counts == {}
    assert adaptive.guard_override_rate == 0.0


def test_a_bare_analysis_constructs_with_the_adaptive_block() -> None:
    """The defaulted block keeps a bare ``Analysis()`` constructible (report contract)."""
    assert Analysis().adaptive.runs_with_investigation == 0


# --------------------------------------------- 6. run_eval selects the arm (MEAS-02)


async def test_run_eval_baseline_records_the_arm_and_the_same_colour(tmp_path: Path) -> None:
    """The baseline arm reports ``planner=False``, no steps, and the same delivered colour."""
    adaptive_path = tmp_path / "adaptive.json"
    baseline_path = tmp_path / "baseline.json"
    adaptive_code = await run_eval(
        cases_dir=CASES_DIR,
        runs=1,
        report_path=adaptive_path,
        offline=True,
        case_filter="E-01",
        store=InMemoryStore(),
    )
    baseline_code = await run_eval(
        cases_dir=CASES_DIR,
        runs=1,
        report_path=baseline_path,
        offline=True,
        case_filter="E-01",
        planner=False,
        store=InMemoryStore(),
    )
    adaptive = Report.model_validate_json(adaptive_path.read_text(encoding="utf-8"))
    baseline = Report.model_validate_json(baseline_path.read_text(encoding="utf-8"))

    assert adaptive_code == baseline_code == 0
    assert adaptive.planner is True
    assert baseline.planner is False
    assert adaptive.cases[0].colours == baseline.cases[0].colours
    assert adaptive.cases[0].investigation_steps == [1]
    assert baseline.cases[0].investigation_steps == [None]
    assert baseline.analysis.adaptive.runs_with_investigation == 0
