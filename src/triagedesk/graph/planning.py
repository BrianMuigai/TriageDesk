"""The bounded investigation loop — five narrow nodes, one decision (ADAPT-01/06/07).

This module is the *adaptive* half of the graph: it investigates before the frozen safety
kernel scores, inside a hard budget, and it can only ever add a read-only fact. Every node
here returns a partial update that is disjoint from the clinical result channels, so no
investigation action can express a colour, an approval or a queue write (ADAPT-04).

The topology it plugs into (``graph/build.py`` owns the edges)::

    retrieve ─┬─(emergency fired)──→ finish_investigation
              └─(otherwise)────────→ plan
    plan ─┬→ gather_evidence → plan
          ├→ ask_question   → retrieve
          ├→ re_extract     → retrieve
          └→ finish_investigation → score

Design rules honoured here (DRY/SOLID):

* The planner's whole policy lives in ``core.planner``; these nodes only *carry* state to the
  tool and record what came back. They import no model and no adapter (SOLID: D).
* ``plan`` is the ONE writer of ``investigation``: it recomputes the accumulator from the
  previous facts, the decision it just made and the nurse's answers, so the step counter and
  the action history cannot be advanced twice.
* ``gather_evidence`` reuses ``graph.nodes.make_ground`` — "retrieve the attributable
  evidence" has exactly ONE implementation, shared with the post-score ``ground`` node.
* ``re_extract`` merges through ``core.merge.merge_monotone`` — the ONE monotone rule.

The planner's ``focus`` hint is deliberately NOT injected into the extraction note: a
planner-authored string must never become evidence. The decision (and its rationale) is the
record of *why* a re-extraction was attempted.
"""

from __future__ import annotations

from typing import Any, cast

from triagedesk.core.merge import merge_monotone
from triagedesk.core.rules import get_tews
from triagedesk.core.schema import (
    MAX_INVESTIGATION_STEPS,
    CaseInput,
    ClarificationAnswer,
    ElicitationOutcome,
    ExtractionResult,
    InvestigationFacts,
    InvestigationState,
    PlanAction,
    PlanDecision,
    RetrievalStatus,
)
from triagedesk.core.scorer import case_field
from triagedesk.graph.nodes import NodeFn, ToolMap, make_ground, parse_tool_result
from triagedesk.graph.state import TriageState
from triagedesk.observability import span

__all__ = [
    "finish_investigation",
    "make_planning_nodes",
    "missing_scored_parameters",
]


def missing_scored_parameters(case: CaseInput) -> list[str]:
    """The scored TEWS parameters the case does not supply — the planner's ``missing_vitals``.

    A projection of the substrate (``data/sats_tews.yaml``) onto the typed case: the parameter
    keys are read through the ONE loader and bound to schema fields through the ONE binding
    rule (``core.scorer.case_field``), so no parameter name and no field name is restated here.
    It is the same question the scorer answers when it reports ``missing_vitals``; a guard test
    pins the two answers together so they cannot drift (``tests/test_graph_planning.py``).

    Read-only and colour-free: it names what is absent, never what a value means.
    """
    return [
        name
        for name in get_tews().parameters
        if getattr(case, case_field(name), None) is None
    ]


def _facts(state: TriageState) -> InvestigationFacts:
    """The current accumulator, or a fresh one on the first visit (the ONE reader)."""
    facts = state.get("investigation")
    return facts if isinstance(facts, InvestigationFacts) else InvestigationFacts()


def _investigation_state(state: TriageState) -> InvestigationState:
    """Project the typed graph state onto the planner's narrow input (ADAPT-02, SOLID: I).

    The step and the remaining budget are DERIVED from ``InvestigationFacts.steps`` — never
    carried as an independent counter — so the budget decreases monotonically even if a node
    is re-executed after an interrupt (ADAPT-06).
    """
    case = state.get("case")
    facts = _facts(state)
    return InvestigationState(
        complaint=case.complaint if isinstance(case, CaseInput) else "",
        retrieval_status=cast(RetrievalStatus, state.get("retrieval_status") or "matched"),
        candidates=list(state.get("candidates") or []),
        questions=list(state.get("clarification_questions") or []),
        missing_vitals=missing_scored_parameters(case) if isinstance(case, CaseInput) else [],
        has_evidence=state.get("evidence") is not None,
        step=facts.steps,
        budget_left=max(MAX_INVESTIGATION_STEPS - facts.steps, 0),
        clarification_round=int(state.get("clarification_round") or 0),
        history=list(facts.history),
    )


def _make_plan(tools: ToolMap) -> NodeFn:
    """Build the ``plan`` node over the injected tool mapping (ADAPT-01/05)."""

    async def plan(state: TriageState) -> dict[str, Any]:
        """Ask the shipped planner tool for ONE next action and record the decision.

        The decision is the tool's typed output — the guard has already replaced any
        inadmissible proposal (ADAPT-02) — so this node never re-interprets it. It writes
        ``plan`` and the recomputed ``investigation`` accumulator and nothing else: it has no
        channel that could carry a colour, a priority or a commit (ADAPT-04).

        The ``decision`` span carries the structural facts only (action, step, budget,
        override) — never the rationale, the complaint or the note (D7-08). The full decision,
        rationale included, is the ``plan_next_step`` audit record (ADAPT-05).
        """
        attributes: dict[str, Any] = {}
        with span("decision", "plan", attributes=attributes):
            investigation = _investigation_state(state)
            decision = parse_tool_result(
                PlanDecision,
                await tools["plan_next_step"](
                    {"investigation": investigation.model_dump(mode="json")}
                ),
            )
            attributes.update(
                {
                    "action": decision.action.value,
                    "step": decision.step,
                    "budget_left": decision.budget_left,
                    "overridden": decision.overridden,
                    "proposed_action": (
                        decision.proposed_action.value if decision.proposed_action else None
                    ),
                }
            )
        facts = _facts(state)
        investigation_facts = InvestigationFacts(
            steps=decision.step,
            history=[*facts.history, decision.action],
            answers=list(state.get("nurse_answers") or []),
            guard_overrides=facts.guard_overrides + (1 if decision.overridden else 0),
        )
        return {"plan": decision, "investigation": investigation_facts}

    return plan


def _make_ask_question(tools: ToolMap) -> NodeFn:
    """Build the ``ask_question`` node over the injected tool mapping (ELICIT-01, ADAPT-01)."""

    async def ask_question(state: TriageState) -> dict[str, Any]:
        """Ask at most three targeted questions and append only what the nurse answered.

        The tool decides the outcome (``accepted``/``declined``/``cancelled``/``unavailable``)
        and the ONE contract refuses to carry answers on anything but an acceptance, so this
        node cannot turn a refusal into a clinical fact. Only an acceptance appends to
        ``nurse_answers`` and spends the one clarification round; every other outcome appends
        nothing, and its record is the tool's audit entry, the outcome on this node's
        ``decision`` span, and the ``elicitation_outcome`` channel the eval harness reads
        (MEAS-01).

        The call is deliberately not wrapped in a ``try``: on a 2026-07-28 connection the
        adapter pauses the run with an ``mcp_elicitation`` interrupt raised from inside the
        call, and that interrupt must propagate to LangGraph.
        """
        candidates = list(state.get("candidates") or [])
        answer = parse_tool_result(
            ClarificationAnswer,
            await tools["request_clarification"]({"candidates": candidates}),
        )
        with span(
            "decision",
            "ask_question",
            attributes={
                "outcome": answer.outcome.value,
                "candidates": len(candidates),
                "answers": len(answer.answers),
            },
        ):
            pass
        if answer.outcome is not ElicitationOutcome.ACCEPTED or not answer.answers:
            return {"elicitation_outcome": answer.outcome.value}
        return {
            "nurse_answers": [*list(state.get("nurse_answers") or []), *answer.answers],
            "clarification_round": int(state.get("clarification_round") or 0) + 1,
            "elicitation_outcome": answer.outcome.value,
        }

    return ask_question


def _make_re_extract(tools: ToolMap) -> NodeFn:
    """Build the ``re_extract`` node over the injected tool mapping (ADAPT-07)."""

    async def re_extract(state: TriageState) -> dict[str, Any]:
        """Re-normalise the note and merge the result MONOTONICALLY (ADAPT-07).

        The merge fills only fields the recorded case leaves ``None``, so a re-extraction can
        recover a missing vital but can never overwrite a recorded one, the original complaint
        or a nurse's answer (``core.merge``). A failed extraction adds nothing: the run
        continues to ``retrieve`` and the deterministic kernel still scores what the desk has.

        The planner's hint is recorded on the decision that selected this action; it is not
        injected into the note, because planner-authored text must never become evidence.
        """
        case = state.get("case")
        if not isinstance(case, CaseInput):
            return {}
        try:
            result = parse_tool_result(
                ExtractionResult,
                await tools["normalize_case"]({"raw_note": str(state.get("raw_note") or "")}),
            )
        except Exception:  # noqa: BLE001 — the tool boundary is external (model/MCP)
            return {}
        merged = merge_monotone(case, result.case)
        filled = [
            name
            for name in CaseInput.model_fields
            if getattr(case, name) is None and getattr(merged, name) is not None
        ]
        with span("decision", "re_extract", attributes={"filled": filled}):
            pass
        return {"case": merged}

    return re_extract


def finish_investigation(state: TriageState) -> dict[str, Any]:
    """Close the investigation and hand control to the frozen kernel (ADAPT-03, ADAPT-08).

    A pure no-op marker with NO state write: the decision was recorded when it was made, and
    this node exists so that ``score`` has exactly ONE inbound edge — ``finish_investigation``
    — on both arms. The emergency arm skips ``plan`` and enters here directly, so the
    structural claim "no investigation action reaches ``score``" is exact rather than
    approximate.

    It emits the closing ``decision`` fact (the action and its step, or the bypass marker when
    no plan was taken) and returns an empty update, which is what makes it provably unable to
    touch the colour, the gate or the commit.
    """
    decision = state.get("plan")
    with span(
        "decision",
        "finish_investigation",
        attributes={
            "action": decision.action.value if isinstance(decision, PlanDecision) else None,
            "step": decision.step if isinstance(decision, PlanDecision) else None,
            "bypassed_plan": decision is None,
        },
    ):
        pass
    return {}


def make_planning_nodes(tools: ToolMap) -> dict[str, NodeFn]:
    """Assemble the investigation nodes over the injected tool mapping (D-13, SOLID: D).

    ``gather_evidence`` IS the shipped ``ground`` node: retrieving the attributable evidence
    has one implementation, so the investigation step and the post-score advisory step cannot
    diverge (DRY). The node names are the ``PlanAction`` values, which is what lets
    ``build.route_after_plan`` derive its edge map from the closed set instead of listing it.
    """
    return {
        PlanAction.GATHER_EVIDENCE.value: make_ground(tools),
        PlanAction.ASK_QUESTION.value: _make_ask_question(tools),
        PlanAction.RE_EXTRACT.value: _make_re_extract(tools),
        "plan": _make_plan(tools),
        PlanAction.FINISH_INVESTIGATION.value: finish_investigation,
    }
