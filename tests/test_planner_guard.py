"""The admissibility guard's safety proof (Plan 20-03, ADAPT-02/04/06/08).

Three one-way properties are pinned here:

1. **Every degradation cause lands on the exit.** An inadmissible, missing (``None``), malformed,
   unparseable or budget-exhausted proposal returns ``finish_investigation`` with
   ``overridden=True`` and a reason naming the cause. The only ``overridden=False`` decisions are
   an admissible proposal and the routine default.
2. **The boundary matrix of ``admissible_actions``.** Ambiguity offers one question, a spent
   clarification round does not, ``no_candidate`` offers none, missing vitals offer a
   re-extraction, history suppresses repeats, and a spent budget offers only the exit.
3. **No proposal can widen the action set.** Over the whole state × proposal cross-product the
   decision's action is always a member of ``admissible_actions(state)``, and the decision
   contract cannot express a colour, a priority or a queue effect.

The production code under test is the shipped guard (``core.planner``) and the shipped wrapper
(``llm.client``); nothing here re-implements admissibility.
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest

from triagedesk.core.planner import (
    FINISH_ONLY,
    admissible_actions,
    default_plan,
    validate_proposal,
)
from triagedesk.core.schema import InvestigationState, PlanAction, PlanDecision, PlanProposal
from triagedesk.llm import client

# A state that admits nothing but the exit — the fast path, and the exhausted-budget case.
_EXHAUSTED = InvestigationState(complaint="chest pain", has_evidence=True, budget_left=0)

# A state that admits every read-only action, so a proposal can be accepted or rejected on its
# own merits rather than on the budget.
_OPEN = InvestigationState(
    complaint="chest pain",
    retrieval_status="ambiguous",
    candidates=["acute_coronary_syndrome"],
    missing_vitals=["temperature"],
)


# ------------------------------------------------------------------- guard degradation


@pytest.mark.parametrize(
    ("proposal", "reason_fragment", "echo"),
    [
        (PlanProposal(action="ask_question"), "inadmissible", PlanAction.ASK_QUESTION),
        (None, "no proposal", None),
        ({"action": "score"}, "malformed", None),
        ({"nonsense": 1}, "malformed", None),
    ],
    ids=["inadmissible", "missing", "malformed-action", "malformed-shape"],
)
def test_a_bad_proposal_degrades_to_the_exit(
    proposal: Any, reason_fragment: str, echo: PlanAction | None
) -> None:
    """Every wrong proposal becomes the default with the cause recorded (ADAPT-02)."""
    state = InvestigationState(complaint="chest pain", retrieval_status="matched")
    decision = validate_proposal(proposal, state)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is True
    assert reason_fragment in (decision.override_reason or "")
    assert decision.proposed_action is echo


def test_an_exhausted_budget_degrades_a_proposal_to_the_exit() -> None:
    """A spent budget admits nothing but the exit, so a proposal is overridden (ADAPT-06)."""
    decision = validate_proposal(PlanProposal(action="gather_evidence"), _EXHAUSTED)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is True
    assert "budget" in (decision.override_reason or "")
    assert decision.proposed_action is PlanAction.GATHER_EVIDENCE
    assert decision.budget_left == 0


def test_the_exit_itself_is_never_overridden_at_an_exhausted_budget() -> None:
    """Proposing the exit is always admissible — even with nothing left to spend."""
    decision = validate_proposal(PlanProposal(action="finish_investigation"), _EXHAUSTED)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is False
    assert decision.proposed_action is PlanAction.FINISH_INVESTIGATION


def test_the_routine_default_is_not_an_override() -> None:
    """The fast path reports no override: no proposal was consulted, so none was replaced."""
    decision = default_plan(_EXHAUSTED)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is False
    assert decision.proposed_action is None


@pytest.mark.parametrize(
    "response",
    [
        {"response": "", "prompt_eval_count": 0, "eval_count": 0},
        {"response": "{not json", "prompt_eval_count": 0, "eval_count": 0},
        {"response": '{"action": "score"}', "prompt_eval_count": 0, "eval_count": 0},
        {
            "response": '{"action": "gather_evidence", "colour": "RED"}',
            "prompt_eval_count": 0,
            "eval_count": 0,
        },
    ],
    ids=["empty", "invalid-json", "outside-the-closed-set", "undeclared-field"],
)
async def test_an_unparseable_response_is_none_and_then_degrades(
    monkeypatch: pytest.MonkeyPatch, response: dict[str, Any]
) -> None:
    """The wrapper never raises on a bad plan payload; the guard then finishes (ADAPT-02)."""
    state = InvestigationState(complaint="chest pain", has_evidence=False)

    async def fake_generate(**kwargs: Any) -> Any:
        return response

    monkeypatch.setattr(client, "_async_generate", fake_generate)
    proposal = await client.propose_plan_async(state)
    assert proposal is None

    decision = validate_proposal(proposal, state)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is True


async def test_a_transport_failure_is_none_and_then_degrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreachable model is a `None` proposal, not an exception on the triage path."""
    state = InvestigationState(complaint="chest pain", has_evidence=False)

    async def broken(**kwargs: Any) -> Any:
        raise ConnectionError("ollama is not running")

    monkeypatch.setattr(client, "_async_generate", broken)
    proposal = await client.propose_plan_async(state)
    assert proposal is None
    assert validate_proposal(proposal, state).action is PlanAction.FINISH_INVESTIGATION


# ------------------------------------------------------------------ admissibility boundaries


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (
            InvestigationState(complaint="x"),
            {PlanAction.FINISH_INVESTIGATION, PlanAction.GATHER_EVIDENCE},
        ),
        (
            InvestigationState(complaint="x", has_evidence=True),
            {PlanAction.FINISH_INVESTIGATION},
        ),
        (
            InvestigationState(
                complaint="x",
                retrieval_status="ambiguous",
                candidates=["acs"],
                clarification_round=0,
            ),
            {
                PlanAction.FINISH_INVESTIGATION,
                PlanAction.GATHER_EVIDENCE,
                PlanAction.ASK_QUESTION,
            },
        ),
        (
            InvestigationState(
                complaint="x",
                retrieval_status="ambiguous",
                candidates=["acs"],
                clarification_round=1,
            ),
            {PlanAction.FINISH_INVESTIGATION, PlanAction.GATHER_EVIDENCE},
        ),
        (
            InvestigationState(
                complaint="x",
                retrieval_status="no_candidate",
                candidates=["acs"],
                clarification_round=0,
            ),
            {PlanAction.FINISH_INVESTIGATION, PlanAction.GATHER_EVIDENCE},
        ),
        (
            InvestigationState(complaint="x", missing_vitals=["temperature"]),
            {
                PlanAction.FINISH_INVESTIGATION,
                PlanAction.GATHER_EVIDENCE,
                PlanAction.RE_EXTRACT,
            },
        ),
        (
            InvestigationState(
                complaint="x",
                missing_vitals=["temperature"],
                history=[PlanAction.RE_EXTRACT],
            ),
            {PlanAction.FINISH_INVESTIGATION, PlanAction.GATHER_EVIDENCE},
        ),
        (
            InvestigationState(complaint="x", history=[PlanAction.GATHER_EVIDENCE]),
            {PlanAction.FINISH_INVESTIGATION},
        ),
        (
            InvestigationState(
                complaint="x",
                retrieval_status="ambiguous",
                candidates=["acs"],
                missing_vitals=["temperature"],
                budget_left=0,
            ),
            {PlanAction.FINISH_INVESTIGATION},
        ),
    ],
    ids=[
        "fresh",
        "evidence-in-hand",
        "ambiguous-round-0",
        "ambiguous-round-1",
        "no-candidate",
        "missing-vitals",
        "re-extract-taken",
        "gather-taken",
        "budget-spent",
    ],
)
def test_admissible_actions_boundaries(
    state: InvestigationState, expected: set[PlanAction]
) -> None:
    """The admissibility matrix is exactly the approved policy (ADAPT-02, ADAPT-06)."""
    assert admissible_actions(state) == frozenset(expected)
    assert PlanAction.FINISH_INVESTIGATION in admissible_actions(state)


def test_the_exit_is_admissible_in_every_state() -> None:
    """The exit can never be blocked, or an investigation could deadlock (ADAPT-06)."""
    for budget in (0, 1, 3):
        for status in ("matched", "ambiguous", "no_candidate"):
            state = InvestigationState(complaint="x", budget_left=budget, retrieval_status=status)
            assert PlanAction.FINISH_INVESTIGATION in admissible_actions(state)


def test_an_exhausted_budget_admits_only_the_exit() -> None:
    """Budget exhaustion concludes the investigation; it never falls through (ADAPT-06)."""
    assert admissible_actions(_OPEN.model_copy(update={"budget_left": 0})) == FINISH_ONLY


# ------------------------------------------------------------------------ no widening


def _state_matrix() -> list[InvestigationState]:
    """The explicit state cross-product the no-widen property is checked over."""
    return [
        InvestigationState(
            complaint="chest pain",
            budget_left=budget,
            has_evidence=has_evidence,
            retrieval_status=status,
            candidates=candidates,
            missing_vitals=missing,
            clarification_round=round_,
        )
        for budget, has_evidence, status, candidates, missing, round_ in itertools.product(
            (0, 2),
            (False, True),
            ("matched", "ambiguous", "no_candidate"),
            ([], ["acute_coronary_syndrome"]),
            ([], ["temperature"]),
            (0, 1),
        )
    ]


@pytest.mark.parametrize("state", _state_matrix(), ids=lambda s: (
    f"b{s.budget_left}-e{int(s.has_evidence)}-{s.retrieval_status}"
    f"-c{len(s.candidates)}-m{len(s.missing_vitals)}-r{s.clarification_round}"
))
def test_no_proposal_can_widen_the_action_set(state: InvestigationState) -> None:
    """Over every state and every proposal, the decision is admissible (ADAPT-02, ADAPT-04)."""
    admissible = admissible_actions(state)
    proposals: list[Any] = [None, {"action": "score"}, *PlanAction]
    for proposal in proposals:
        decision = validate_proposal(proposal, state)
        assert decision.action in admissible, (state, proposal)
        assert decision.step == state.step + 1
        assert 0 <= decision.budget_left <= state.budget_left


def test_the_decision_contract_cannot_express_a_queue_effect() -> None:
    """No `PlanDecision` field names a colour, priority, queue row or approval (ADAPT-04)."""
    forbidden = ("colour", "priority", "commit", "queue", "approval", "token")
    for name in PlanDecision.model_fields:
        lowered = name.lower()
        assert not any(token in lowered for token in forbidden), name
