"""The planner contract and pure policy (Plan 20-01, ADAPT-02/06/08).

The planner's action set is **closed**, the default is **finish**, and the budget **decreases**.
These tests pin the contract itself: the four members (and the absence of a score/approve/commit
member or a synonym for the exit), the narrow state shape, the baseline decision, an accepted
proposal, and the monotone counters. The degradation and boundary matrices live in
``tests/test_planner_guard.py`` (Plan 20-03) so the two files do not restate each other (DRY).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from triagedesk.core.planner import (
    MAX_INVESTIGATION_STEPS,
    admissible_actions,
    default_plan,
    validate_proposal,
)
from triagedesk.core.schema import (
    InvestigationState,
    PlanAction,
    PlanDecision,
    PlanProposal,
)

# The four declared actions, written once as the enum members (never as bare strings).
_DECLARED = {
    PlanAction.GATHER_EVIDENCE,
    PlanAction.ASK_QUESTION,
    PlanAction.RE_EXTRACT,
    PlanAction.FINISH_INVESTIGATION,
}


def _state(**overrides: object) -> InvestigationState:
    """A fresh investigation of one complaint, with the named fields overridden."""
    return InvestigationState(complaint="chest pain", **overrides)  # type: ignore[arg-type]


# --------------------------------------------------------------------- closed action set


def test_plan_action_is_exactly_the_four_declared_members() -> None:
    """The action set is closed: four members, no more (ADAPT-02)."""
    assert set(PlanAction) == _DECLARED
    assert len(PlanAction) == 4


def test_no_action_can_score_approve_or_commit() -> None:
    """The planner cannot express a kernel or queue effect (ADAPT-02, ADAPT-04)."""
    values = {action.value for action in PlanAction}
    for forbidden in ("score", "approval_gate", "commit", "commit_priority", "deliver"):
        assert forbidden not in values


def test_the_exit_has_one_name_and_no_synonym() -> None:
    """`finish_investigation` is the only exit name (ADAPT-08 — no synonym drift)."""
    values = {action.value for action in PlanAction}
    for synonym in ("stop", "done", "finish", "complete", "end"):
        assert synonym not in values
    assert "finish_investigation" in values


def test_plan_action_round_trips_from_its_declared_value() -> None:
    """A stored/audited action name resolves back to the enum member."""
    assert PlanAction("finish_investigation") is PlanAction.FINISH_INVESTIGATION


# ------------------------------------------------------------------------- state contract


def test_investigation_state_defaults_to_the_one_declared_budget() -> None:
    """A fresh investigation starts with the bound declared beside the contract (ADAPT-06)."""
    state = _state()
    assert state.budget_left == MAX_INVESTIGATION_STEPS
    assert state.step == 0
    assert state.clarification_round == 0
    assert state.history == []
    assert state.has_evidence is False


def test_investigation_state_rejects_an_undeclared_field() -> None:
    """The tool's input is narrow: a smuggled colour/priority field is unrepresentable."""
    with pytest.raises(ValidationError):
        InvestigationState(complaint="chest pain", colour="RED")


def test_investigation_state_rejects_a_negative_counter() -> None:
    """Counters are non-negative, so a caller cannot claim a spent budget below zero."""
    with pytest.raises(ValidationError):
        InvestigationState(complaint="chest pain", budget_left=-1)


def test_proposal_selects_a_member_and_rejects_an_unknown_action() -> None:
    """The model's proposal is constrained to the closed set, not to free text."""
    assert PlanProposal(action="gather_evidence").action is PlanAction.GATHER_EVIDENCE
    with pytest.raises(ValidationError):
        PlanProposal(action="score")


def test_proposal_rejects_an_undeclared_field() -> None:
    """A proposal cannot carry a field the guard does not read."""
    with pytest.raises(ValidationError):
        PlanProposal(action="gather_evidence", colour="RED")


# --------------------------------------------------------------------------- default plan


def test_default_plan_is_finish_investigation() -> None:
    """The default is the exit with no override — today's behaviour, the baseline arm."""
    state = _state(step=2, budget_left=1)
    decision = default_plan(state)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is False
    assert decision.proposed_action is None
    assert decision.override_reason is None


def test_a_decision_reports_the_counters_after_it() -> None:
    """One decision consumes one step and one unit of budget (ADAPT-06)."""
    decision = default_plan(_state(step=2, budget_left=1))
    assert decision.step == 3
    assert decision.budget_left == 0


def test_the_budget_is_floored_at_zero() -> None:
    """A caller that keeps asking cannot drive the budget negative."""
    decision = default_plan(_state(step=9, budget_left=0))
    assert decision.budget_left == 0


# ----------------------------------------------------------------------------- accept path


@pytest.mark.parametrize(
    "state",
    [
        InvestigationState(complaint="chest pain"),
        InvestigationState(
            complaint="chest pain", retrieval_status="ambiguous", candidates=["acs"]
        ),
        InvestigationState(complaint="chest pain", missing_vitals=["temperature"]),
    ],
    ids=["gather", "ask", "re-extract"],
)
def test_an_admissible_proposal_is_honoured(state: InvestigationState) -> None:
    """Every action the state admits can be accepted, with the proposal echoed for audit."""
    for action in admissible_actions(state):
        decision = validate_proposal(PlanProposal(action=action), state)
        assert decision.action is action
        assert decision.overridden is False
        assert decision.proposed_action is action
        assert decision.step == state.step + 1
        assert decision.budget_left == max(state.budget_left - 1, 0)


def test_an_accepted_proposal_keeps_the_models_advisory_text() -> None:
    """The rationale and signals ride along for the audit record; `focus` is not forwarded."""
    proposal = PlanProposal(
        action="gather_evidence",
        rationale="no excerpt is in hand yet",
        focus="the complaint wording",
        signals=["no_evidence"],
    )
    decision = validate_proposal(proposal, _state())
    assert decision.rationale == proposal.rationale
    assert decision.signals == proposal.signals
    assert "focus" not in PlanDecision.model_fields


def test_the_budget_decreases_monotonically_across_a_chain() -> None:
    """A three-step investigation reaches a spent budget and never spins (ADAPT-06)."""
    state = _state(missing_vitals=["temperature"])

    first = validate_proposal(PlanProposal(action="gather_evidence"), state)
    assert first.action is PlanAction.GATHER_EVIDENCE
    state = state.model_copy(
        update={
            "step": first.step,
            "budget_left": first.budget_left,
            "has_evidence": True,
            "history": [*state.history, first.action],
        }
    )

    second = validate_proposal(PlanProposal(action="re_extract"), state)
    assert second.action is PlanAction.RE_EXTRACT
    state = state.model_copy(
        update={
            "step": second.step,
            "budget_left": second.budget_left,
            "missing_vitals": [],
            "history": [*state.history, second.action],
        }
    )

    # Nothing but the exit is left, so the routine default answers without a proposal.
    third = default_plan(state)

    budgets = [first.budget_left, second.budget_left, third.budget_left]
    steps = [first.step, second.step, third.step]
    assert budgets == sorted(budgets, reverse=True)
    assert budgets[-1] == 0
    assert steps == sorted(steps)
    assert len(set(steps)) == len(steps)
