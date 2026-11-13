"""The frozen-kernel structural proof (ADAPT-03, ADAPT-04, ADAPT-06).

The adaptive loop may investigate; it may not touch the kernel. This suite proves that on the
COMPILED graph and on the DECLARED contracts, not on a copy:

1. ``predecessors("score") == {"finish_investigation"}`` — one door into the kernel;
2. ``predecessors("commit") == {"approval_gate"}`` — the gate keeps one inbound edge;
3. no investigation node's partial update contains ``priority``, ``commit_result`` or
   ``handover``;
4. ``PlanAction`` cannot express a kernel effect;
5. the loop is bounded: at most ``MAX_INVESTIGATION_STEPS`` investigation actions, no repeat,
   and a spent budget admits only the exit;
6. the emergency arm skips the planner entirely and still enters through the one door.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from conftest import EMERGENCY_CASE, build_graph_tools
from triagedesk.core import planner
from triagedesk.core.schema import (
    MAX_INVESTIGATION_STEPS,
    CaseInput,
    InvestigationState,
    PlanAction,
    PlanProposal,
)
from triagedesk.graph.build import TRACER_NODES, build_graph
from triagedesk.graph.nodes import make_nodes
from triagedesk.observability.spans import read_spans

NOTE = (
    "44 year old, walking, alert. RR 30, HR 130, systolic BP 70, temperature 37.0, no trauma."
)

# A case that makes every investigation action admissible at once: an ambiguous complaint
# (a stated condition points at a family) AND a scored vital missing AND no evidence yet.
MAXIMAL_CASE = CaseInput(
    age_years=52,
    mobility="walking",
    avpu="alert",
    respiratory_rate=16,
    heart_rate=88,
    systolic_bp=130,
    trauma=False,
    complaint="feeling unwell",
)
MAXIMAL_NOTE = (
    "52 year old woman, walking, alert, no trauma, known type 2 diabetic. "
    "RR 16, HR 88, systolic BP 130. Complaint: feeling unwell."
)

# The clinical result channels no investigation node may write (ADAPT-04).
_CLINICAL_CHANNELS = frozenset({"priority", "commit_result", "handover"})

_INVESTIGATION_NODES = (
    "plan",
    "gather_evidence",
    "ask_question",
    "re_extract",
    "finish_investigation",
)


def _predecessors(graph: Any) -> dict[str, set[str]]:
    """Inbound edges of the compiled graph, keyed by target (the ONE reader)."""
    predecessors: dict[str, set[str]] = {}
    for edge in graph.get_graph().edges:
        predecessors.setdefault(edge.target, set()).add(edge.source)
    return predecessors


def _node_order() -> list[str]:
    return [entry["name"] for entry in read_spans() if entry["kind"] == "node"]


def _maximal_investigator() -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
    """A model stub that always wants the next investigation action the state admits."""

    async def plan_next_step(inp: Mapping[str, Any]) -> Any:
        state = InvestigationState.model_validate(inp["investigation"])
        allowed = planner.admissible_actions(state)
        for action in (
            PlanAction.GATHER_EVIDENCE,
            PlanAction.ASK_QUESTION,
            PlanAction.RE_EXTRACT,
        ):
            if action in allowed:
                return planner.validate_proposal(PlanProposal(action=action), state)
        return planner.default_plan(state)

    return plan_next_step


# ------------------------------------------------------- 1-2: one door into the kernel


def test_score_has_exactly_one_inbound_edge() -> None:
    """Only ``finish_investigation`` reaches the scorer (ADAPT-03)."""
    graph = build_graph(build_graph_tools())

    assert _predecessors(graph)["score"] == {"finish_investigation"}


def test_commit_has_exactly_one_inbound_edge() -> None:
    """The gate is still the only way to the commit (GATE-01, ADAPT-03)."""
    graph = build_graph(build_graph_tools())

    assert _predecessors(graph)["commit"] == {"approval_gate"}


def test_every_investigation_node_is_on_the_compiled_graph() -> None:
    """The five loop nodes are declared AND compiled — the proof cannot drift from the build."""
    graph = build_graph(build_graph_tools())

    assert set(_INVESTIGATION_NODES) <= set(TRACER_NODES)
    assert set(_INVESTIGATION_NODES) <= set(graph.get_graph().nodes)


# ------------------------------------- 3: no investigation node writes a clinical channel


@pytest.mark.parametrize("name", _INVESTIGATION_NODES)
async def test_no_investigation_node_writes_a_clinical_channel(name: str) -> None:
    """Every loop node returns a partial update disjoint from the clinical result (ADAPT-04)."""
    tools = build_graph_tools(case=MAXIMAL_CASE)
    nodes = make_nodes(tools)
    state: dict[str, Any] = {
        "raw_note": MAXIMAL_NOTE,
        "case": MAXIMAL_CASE,
        "retrieval_status": "ambiguous",
        "candidates": ["diabetic_hyperglycaemia_ketonuria"],
    }

    update = nodes[name](state)
    if inspect.isawaitable(update):
        update = await update

    assert isinstance(update, Mapping)
    assert set(update) & _CLINICAL_CHANNELS == set(), f"{name} wrote {set(update)}"


# --------------------------------------------- 4: the action set cannot express a kernel effect


def test_plan_action_cannot_express_a_kernel_effect() -> None:
    """The closed set has exactly four members and none of them is a kernel step (ADAPT-08)."""
    members = {action.value for action in PlanAction}

    assert members == {
        "gather_evidence",
        "ask_question",
        "re_extract",
        "finish_investigation",
    }
    assert members & {"score", "approval_gate", "commit", "handover"} == set()


# ------------------------------------------------------------- 5: the loop is bounded


async def test_the_loop_is_bounded_and_never_repeats_an_action() -> None:
    """A model that always wants to investigate still takes at most three steps (ADAPT-06)."""
    tools = build_graph_tools(case=MAXIMAL_CASE)
    tools["plan_next_step"] = _maximal_investigator()
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke(
        {"raw_note": MAXIMAL_NOTE, "case": MAXIMAL_CASE}, {"configurable": {"thread_id": "bound"}}
    )

    history = list(result["investigation"].history)
    investigation = [action for action in history if action is not PlanAction.FINISH_INVESTIGATION]
    assert len(investigation) == MAX_INVESTIGATION_STEPS
    assert len(set(history)) == len(history), f"an action was repeated: {history}"
    assert history[-1] is PlanAction.FINISH_INVESTIGATION
    # The budget is spent, not negative, and only the exit was admissible at the end.
    assert result["plan"].budget_left == 0
    assert planner.admissible_actions(
        InvestigationState(complaint="x", budget_left=0)
    ) == planner.FINISH_ONLY


async def test_a_spent_budget_reaches_finish_investigation() -> None:
    """Budget exhaustion concludes the investigation — it never raises or skips the kernel."""
    tools = build_graph_tools(case=MAXIMAL_CASE)
    tools["plan_next_step"] = _maximal_investigator()
    app = build_graph(tools, checkpointer=InMemorySaver())

    await app.ainvoke(
        {"raw_note": MAXIMAL_NOTE, "case": MAXIMAL_CASE}, {"configurable": {"thread_id": "spent"}}
    )

    order = _node_order()
    assert "finish_investigation" in order
    assert order.index("finish_investigation") < order.index("score")


# ------------------------------------------------- 6: the emergency arm skips the planner


async def test_the_emergency_arm_reaches_finish_investigation_without_planning() -> None:
    """A fired verdict never asks for a next step, and still enters the one door (ADAPT-03)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=EMERGENCY_CASE, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    await app.ainvoke(
        {"raw_note": NOTE, "case": EMERGENCY_CASE}, {"configurable": {"thread_id": "bypass"}}
    )

    assert "plan_next_step" not in [name for name, _ in calls]
    order = _node_order()
    assert "plan" not in order
    assert order.index("retrieve") < order.index("finish_investigation") < order.index("score")
