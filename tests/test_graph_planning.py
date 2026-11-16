"""The adaptive investigation loop, end to end, with fake tools (ADAPT-01/06/07).

The graph is the SHIPPED one (``build_graph``) and the planner fake is the SHIPPED guard
(``core.planner.validate_proposal``) fed a scripted proposal, so every path here exercises the
real node bodies and the real policy — only the model and the transport are stubbed.

Covered: the adaptive happy path (ambiguous -> ask -> answer -> re-match -> matched -> kernel),
the guard override, the evidence path, the monotone re-extraction, a refusal that appends
nothing, and the drift guard that pins the planner's missing-vital projection to the scorer's
own report.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from conftest import build_graph_tools
from triagedesk.core import planner, scorer
from triagedesk.core.schema import (
    CaseInput,
    ClarificationAnswer,
    ElicitationOutcome,
    ExtractionResult,
    InvestigationState,
    PlanAction,
    PlanProposal,
)
from triagedesk.graph.build import build_graph, checkpointed_graph
from triagedesk.graph.planning import missing_scored_parameters
from triagedesk.observability.spans import read_spans

NOTE = (
    "52 year old woman, walking, alert, no trauma, known type 2 diabetic. "
    "RR 16, HR 88, systolic BP 130, temperature 36.9. Complaint: feeling unwell."
)

# The vague complaint the context condition turns into a targeted clarification.
AMBIGUOUS_CASE = CaseInput(
    age_years=52,
    mobility="walking",
    avpu="alert",
    respiratory_rate=16,
    heart_rate=88,
    systolic_bp=130,
    temperature_c=36.9,
    trauma=False,
    complaint="feeling unwell",
)

# An answer that states the discriminator the question asked about.
ANSWER = "high glucose with ketones"

# The complete routine case (every scored vital stated).
COMPLETE_CASE = CaseInput(
    age_years=40,
    mobility="walking",
    avpu="alert",
    respiratory_rate=24,
    heart_rate=118,
    systolic_bp=108,
    temperature_c=38.9,
    trauma=False,
    complaint="central chest pain",
)


def _scripted(*actions: PlanAction) -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
    """A model stub that proposes *actions* in order — decided by the SHIPPED guard.

    It returns what the real tool would return (a ``PlanDecision``), because it IS the real
    policy applied to a scripted proposal. When the script runs out it proposes nothing, which
    the guard turns into the exit.
    """
    pending = list(actions)

    async def plan_next_step(inp: Mapping[str, Any]) -> Any:
        state = InvestigationState.model_validate(inp["investigation"])
        proposal = PlanProposal(action=pending.pop(0)) if pending else None
        return planner.validate_proposal(proposal, state)

    return plan_next_step


def _answering(
    text: str, calls: list[tuple[str, Any]] | None = None
) -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
    """A clarification stub that reports one ACCEPTED answer (the shipped contract)."""

    async def request_clarification(inp: Mapping[str, Any]) -> Any:
        if calls is not None:
            calls.append(("request_clarification", inp))
        return ClarificationAnswer(outcome=ElicitationOutcome.ACCEPTED, answers=[text])

    return request_clarification


def _refusing() -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
    """A clarification stub that reports a DECLINE — never a value (ELICIT-03)."""

    async def request_clarification(inp: Mapping[str, Any]) -> Any:
        return ClarificationAnswer(outcome=ElicitationOutcome.DECLINED, reason="declined")

    return request_clarification


def _node_order() -> list[str]:
    """The executed node names, in span-append order (the ONE span reader)."""
    return [entry["name"] for entry in read_spans() if entry["kind"] == "node"]


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


async def test_adaptive_happy_path_asks_then_matches_then_scores() -> None:
    """Ambiguous -> ask -> answer -> re-match -> matched -> finish -> kernel (ADAPT-01)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=AMBIGUOUS_CASE, calls=calls)
    tools["plan_next_step"] = _scripted(
        PlanAction.ASK_QUESTION, PlanAction.FINISH_INVESTIGATION
    )
    tools["request_clarification"] = _answering(ANSWER, calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE, "case": AMBIGUOUS_CASE}, _config("adaptive"))

    # The question was asked exactly once, and the answer was matched on the next retrieve.
    names = [name for name, _ in calls]
    assert names.count("request_clarification") == 1
    assert result["nurse_answers"] == [ANSWER]
    assert result["matched_ids"], "the answer did not resolve the ambiguity"
    expected = scorer.score_priority(AMBIGUOUS_CASE, list(result["matched_ids"]))
    assert result["priority"].colour == expected.colour
    assert result["investigation"].history == [
        PlanAction.ASK_QUESTION,
        PlanAction.FINISH_INVESTIGATION,
    ]
    assert result["investigation"].steps == 2
    # The kernel still runs, and the run still stops at the clinician's gate.
    assert result.get("__interrupt__")
    assert "score_priority" in names


async def test_the_plan_node_does_not_reach_the_gate_before_finishing() -> None:
    """Every plan decision is followed by its action, never by a scored colour."""
    tools = build_graph_tools(case=AMBIGUOUS_CASE)
    tools["plan_next_step"] = _scripted(
        PlanAction.ASK_QUESTION, PlanAction.FINISH_INVESTIGATION
    )
    tools["request_clarification"] = _answering(ANSWER)
    app = build_graph(tools, checkpointer=InMemorySaver())

    await app.ainvoke({"raw_note": NOTE, "case": AMBIGUOUS_CASE}, _config("adaptive-order"))

    order = _node_order()
    assert order.index("finish_investigation") < order.index("score")
    assert order.count("plan") == 2


async def test_an_inadmissible_proposal_is_overridden_and_still_finishes() -> None:
    """The guard replaces a bad proposal; the run still enters the kernel (ADAPT-02/03)."""
    tools = build_graph_tools(case=COMPLETE_CASE)
    # A complete case has no missing vital, so re_extract is inadmissible.
    tools["plan_next_step"] = _scripted(PlanAction.RE_EXTRACT)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE, "case": COMPLETE_CASE}, _config("override"))

    decision = result["plan"]
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.proposed_action is PlanAction.RE_EXTRACT
    assert decision.overridden is True
    assert decision.override_reason
    assert result["investigation"].guard_overrides == 1
    assert result["priority"].colour is not None
    assert result.get("__interrupt__")


async def test_gather_evidence_writes_the_evidence_channel_and_returns_to_plan() -> None:
    """The evidence action fills ``evidence`` only, then the planner decides again."""
    tools = build_graph_tools(case=COMPLETE_CASE)
    tools["plan_next_step"] = _scripted(
        PlanAction.GATHER_EVIDENCE, PlanAction.FINISH_INVESTIGATION
    )
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE, "case": COMPLETE_CASE}, _config("evidence"))

    assert result["evidence"] is not None
    order = _node_order()
    assert order.index("gather_evidence") < order.index("finish_investigation")
    assert order.count("plan") == 2
    assert result["investigation"].history[0] is PlanAction.GATHER_EVIDENCE


async def test_re_extract_fills_a_missing_vital_and_never_overwrites_a_stated_one() -> None:
    """ADAPT-07: the merge adds the absent temperature and keeps the recorded heart rate."""
    incomplete = COMPLETE_CASE.model_copy(update={"temperature_c": None})
    contradictory = COMPLETE_CASE.model_copy(
        update={"temperature_c": 39.4, "heart_rate": 200}
    )
    extracted: list[CaseInput] = [incomplete, contradictory]

    def normalize_impl(_inp: Mapping[str, Any]) -> ExtractionResult:
        # The first call is ``normalize``; the second is ``re_extract``.
        case = extracted.pop(0) if len(extracted) > 1 else contradictory
        return ExtractionResult(case=case, matched_discriminator_ids=[])

    tools = build_graph_tools(case=incomplete, normalize_impl=normalize_impl)
    tools["plan_next_step"] = _scripted(
        PlanAction.RE_EXTRACT, PlanAction.FINISH_INVESTIGATION
    )
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE, "case": incomplete}, _config("re-extract"))

    assert result["case"].temperature_c == 39.4, "the missing vital was not filled"
    assert result["case"].heart_rate == incomplete.heart_rate, "a recorded vital was overwritten"
    assert result["investigation"].history[0] is PlanAction.RE_EXTRACT


async def test_a_declined_question_appends_nothing() -> None:
    """A refusal is not an observation: no answer, no round spent, no fact (ELICIT-03/08)."""
    tools = build_graph_tools(case=AMBIGUOUS_CASE)
    tools["plan_next_step"] = _scripted(
        PlanAction.ASK_QUESTION, PlanAction.FINISH_INVESTIGATION
    )
    tools["request_clarification"] = _refusing()
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE, "case": AMBIGUOUS_CASE}, _config("declined"))

    assert not result.get("nurse_answers")
    assert int(result.get("clarification_round") or 0) == 0


@pytest.mark.parametrize(
    "case",
    [
        COMPLETE_CASE,
        COMPLETE_CASE.model_copy(update={"temperature_c": None}),
        COMPLETE_CASE.model_copy(update={"respiratory_rate": None, "spo2": None}),
        COMPLETE_CASE.model_copy(update={"mobility": None, "avpu": None}),
        CaseInput(age_years=30, complaint="x"),
    ],
    ids=["complete", "no-temp", "no-rr", "no-categorical", "bare"],
)
def test_the_planners_missing_vitals_equal_the_scorers_report(case: CaseInput) -> None:
    """The planner's projection and the scorer's own report cannot drift (DRY)."""
    assert set(missing_scored_parameters(case)) == set(
        scorer.score_priority(case).missing_vitals
    )


async def test_a_paused_investigation_round_trips_through_the_durable_saver(
    tmp_path: Any,
) -> None:
    """The accumulator survives a restart with its types intact (D-09, T-07-06).

    The checkpointer's msgpack allowlist is derived from ``core.schema``, so the new
    ``InvestigationFacts`` model AND its ``PlanAction`` members must both deserialise as
    themselves — a blocked enum would silently come back as a bare string.
    """
    tools = build_graph_tools(case=COMPLETE_CASE)
    tools["plan_next_step"] = _scripted(
        PlanAction.GATHER_EVIDENCE, PlanAction.FINISH_INVESTIGATION
    )
    config = _config("durable-investigation")
    db_path = Path(tmp_path) / "checkpoints.db"

    async with checkpointed_graph(tools, db_path) as graph:
        paused = await graph.ainvoke({"raw_note": NOTE, "case": COMPLETE_CASE}, config)
        assert paused.get("__interrupt__")

    async with checkpointed_graph(tools, db_path) as reopened:
        snapshot = await reopened.aget_state(config)

    facts = snapshot.values["investigation"]
    assert all(isinstance(action, PlanAction) for action in facts.history)
    assert facts.history[0] is PlanAction.GATHER_EVIDENCE
    assert snapshot.values["plan"].action is PlanAction.FINISH_INVESTIGATION
