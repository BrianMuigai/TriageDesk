"""The planner's whole policy — pure, deterministic, and the only authority (ADAPT-02/06/08).

A planner *decision* is a typed contract over a closed action set. The local model may
**propose** an action (``core.schema.PlanProposal``), but this module decides: it computes
which actions the current typed state admits and replaces anything else with the default
``finish_investigation``. The model is never the authority, and a bad proposal can never
widen what the graph is able to do (ADAPT-02).

Three rules live here and nowhere else:

* :func:`admissible_actions` — the closed set narrowed by the state: the exit is always
  admissible; evidence gathering only before evidence exists; one clarifying question only
  while the retrieval classification is ``ambiguous`` and no round has been spent; a
  re-extraction only while a scored vital is missing; **nothing** but the exit once the
  budget is spent; and an action already taken is never offered again (ADAPT-06).
* :func:`default_plan` — exactly today's behaviour: finish and let the deterministic kernel
  answer. This is the baseline arm the Phase 24 measurement compares against.
* :func:`validate_proposal` — the guard. An inadmissible, missing, malformed or
  budget-exhausted proposal becomes the default with ``overridden=True`` and a reason naming
  why, so the audit record shows the substitution rather than hiding it.

This module imports nothing from ``llm`` / ``mcp`` / ``store`` (enforced by
``tests/test_purity.py``) and reads no SATS value: every clinical threshold stays in
``data/*.yaml`` (CONVENTIONS §1). It calls no model — the wrapper does that above this
boundary (SOLID: D).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from triagedesk.core.schema import (
    MAX_INVESTIGATION_STEPS,
    InvestigationState,
    PlanAction,
    PlanDecision,
    PlanProposal,
)

__all__ = [
    "FINISH_ONLY",
    "MAX_INVESTIGATION_STEPS",
    "admissible_actions",
    "default_plan",
    "validate_proposal",
]

# The one exit, as a set. Declared once so the tool's "do not call the model" fast path and
# the guard compare against the SAME value instead of each writing ``frozenset({...})``.
FINISH_ONLY: frozenset[PlanAction] = frozenset({PlanAction.FINISH_INVESTIGATION})

# The ONE default rationale: finishing is not a failure, it is the baseline behaviour.
_DEFAULT_RATIONALE = (
    "finish_investigation is the default: the case proceeds to the deterministic kernel "
    "unchanged"
)

# The ONE reason text per degradation cause, so the audit record, the tool's caller and the
# tests read the same words (DRY).
_NO_PROPOSAL_REASON = "no proposal was produced; defaulting to finish_investigation"
_MALFORMED_REASON = "the proposal is malformed; defaulting to finish_investigation"
_EXHAUSTED_REASON = "the investigation budget is spent; defaulting to finish_investigation"
_INADMISSIBLE_REASON = (
    "proposed action {action!r} is inadmissible for this state; "
    "defaulting to finish_investigation"
)


def admissible_actions(state: InvestigationState) -> frozenset[PlanAction]:
    """Return the actions the current typed state admits (ADAPT-02, ADAPT-06).

    ``finish_investigation`` is **always** admissible — the exit can never be blocked, or an
    investigation could deadlock. The three read-only investigation actions are admitted only
    by the state that needs them, only while budget remains, and never twice:

    * ``gather_evidence`` — no evidence has been gathered yet;
    * ``ask_question`` — the complaint is near a discriminator family but names none, there is
      a candidate to ask about, and the one clarification round is unspent;
    * ``re_extract`` — a scored vital is missing from the note.

    Once ``budget_left`` is zero the set is exactly :data:`FINISH_ONLY`: budget exhaustion
    concludes the investigation, it never raises and never falls through to the gate.
    """
    actions: set[PlanAction] = {PlanAction.FINISH_INVESTIGATION}
    if state.budget_left <= 0:
        return FINISH_ONLY
    taken = set(state.history)
    if not state.has_evidence and PlanAction.GATHER_EVIDENCE not in taken:
        actions.add(PlanAction.GATHER_EVIDENCE)
    if (
        state.retrieval_status == "ambiguous"
        and state.candidates
        and state.clarification_round < 1
        and PlanAction.ASK_QUESTION not in taken
    ):
        actions.add(PlanAction.ASK_QUESTION)
    if state.missing_vitals and PlanAction.RE_EXTRACT not in taken:
        actions.add(PlanAction.RE_EXTRACT)
    return frozenset(actions)


def _next_counters(state: InvestigationState) -> tuple[int, int]:
    """The step and budget AFTER one decision — the ONE monotone-decrement rule (ADAPT-06).

    Every decision consumes one step, including the exit (the loop is over, so the decrement
    is harmless and there is no special case to get wrong). The budget is floored at zero, so
    a caller that keeps asking can never drive it negative.
    """
    return state.step + 1, max(state.budget_left - 1, 0)


def default_plan(state: InvestigationState) -> PlanDecision:
    """Finish the investigation without a model — today's behaviour, the baseline arm.

    ``overridden`` is ``False``: nothing was replaced, because no proposal was consulted.
    The routine case therefore costs exactly what it costs today (no model call).
    """
    step, budget_left = _next_counters(state)
    return PlanDecision(
        action=PlanAction.FINISH_INVESTIGATION,
        rationale=_DEFAULT_RATIONALE,
        step=step,
        budget_left=budget_left,
    )


def _as_proposal(value: PlanProposal | Mapping[str, Any]) -> PlanProposal | None:
    """Coerce a mapping to a proposal, or ``None`` when it does not validate.

    The model wrapper hands over a validated :class:`PlanProposal`; a direct tool caller (or a
    future adapter) may hand over a mapping. Both go through the ONE contract, and anything
    that fails validation is reported as malformed rather than guessed at.
    """
    if isinstance(value, PlanProposal):
        return value
    try:
        return PlanProposal.model_validate(dict(value))
    except ValueError:
        return None


def _override(
    state: InvestigationState,
    proposed: PlanAction | None,
    reason: str,
) -> PlanDecision:
    """The ONE degradation shape: the exit, flagged, with the cause recorded (ADAPT-02)."""
    step, budget_left = _next_counters(state)
    return PlanDecision(
        action=PlanAction.FINISH_INVESTIGATION,
        rationale=_DEFAULT_RATIONALE,
        step=step,
        budget_left=budget_left,
        proposed_action=proposed,
        overridden=True,
        override_reason=reason,
    )


def validate_proposal(
    proposal: PlanProposal | Mapping[str, Any] | None,
    state: InvestigationState,
) -> PlanDecision:
    """Validate one model proposal and return the decision the guard will honour.

    A proposal can be wrong in four ways, and every one of them lands on the same safe
    default with ``overridden=True`` and a reason naming the cause:

    * **missing** (``None``) — the model wrapper could not produce a payload;
    * **malformed** — a mapping that does not validate against :class:`PlanProposal`;
    * **inadmissible** — an action this state does not admit (including any action once the
      budget is spent);
    * an action already taken (suppressed by :func:`admissible_actions`).

    An admissible proposal is returned unchanged as the decision's ``action`` with
    ``proposed_action`` echoing it. The returned action is therefore always a member of
    :func:`admissible_actions`, in every state and for every input.
    """
    if proposal is None:
        return _override(state, None, _NO_PROPOSAL_REASON)
    parsed = _as_proposal(proposal)
    if parsed is None:
        return _override(state, None, _MALFORMED_REASON)
    if parsed.action not in admissible_actions(state):
        reason = (
            _EXHAUSTED_REASON
            if state.budget_left <= 0
            else _INADMISSIBLE_REASON.format(action=parsed.action.value)
        )
        return _override(state, parsed.action, reason)
    step, budget_left = _next_counters(state)
    return PlanDecision(
        action=parsed.action,
        rationale=parsed.rationale,
        signals=list(parsed.signals),
        step=step,
        budget_left=budget_left,
        proposed_action=parsed.action,
    )
