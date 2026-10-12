"""Baseline-citation proof suite (Plan 04-05, G-1, SCORE-03, EVAL-01/03).

The core-value gap (G-1): a routine, all-normal-vitals patient (TEWS 0) fired no band
rule, carried no citation, and was treated by ``verify`` as "no evidence" — so the run
fail-closed to ``END`` with no approval gate and no handover card. This suite proves the
fix end-to-end and that it did NOT weaken the citation contract for genuinely uncited
priorities:

1. a TEWS-0 in-scope case is sourced by exactly ONE data-driven baseline rule, and
   ``citations == [rule.citation for rule in triggered_rules]`` still holds;
2. a case that fired a band rule carries NO baseline rule;
3. a discriminator-override case carries NO baseline rule (a real finding is never
   displaced by baseline evidence, T-04-22);
4. an out-of-scope/abstained case still carries no citations and no triggered rules;
5. E-08 runs through the ONE graph interface with the offline tools; under the ``no_match``
   deferral (D8-11) it now DEFERS to a safe terminal — it never reaches the approval gate,
   writes no queue row and produces no handover card. The graph-level "served through the
   gate" path this proof used to assert is superseded by D8-11; the TEWS-0 baseline *citation*
   contract is still proven at the scorer level by test 1.
6. INV-1 fails a *scored* priority with zero citations and passes the baseline-cited one
   (T-04-23, EVAL-03).

Offline and deterministic: the model and the MCP subprocess are never launched (the
autouse store fixture injects the in-memory store; the graph uses the shared offline tools).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import build_graph_tools
from triagedesk.core import matcher, scorer
from triagedesk.core.schema import PriorityResult
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.invariants import INV_1, RunEvidence, evaluate
from triagedesk.graph.build import build_graph

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

# The baseline rule's structural id — a code-side structural token, not a SATS value
# (CONVENTIONS §1). Declared once so the suite names it in exactly one place.
BASELINE_RULE_ID = "tews_baseline"

_CASES: dict[str, CaseSpec] = {case.id: case for case in load_cases(CASES_DIR)}


def _case(case_id: str) -> CaseSpec:
    """The loaded fixture for *case_id* (fails loudly if it is missing)."""
    return _CASES[case_id]


# ------------------------------------------------ 1. a TEWS-0 case is sourced

def test_a_tews_zero_case_is_sourced_by_the_baseline_citation() -> None:
    """A routine all-normal-vitals case carries exactly one baseline citation (G-1)."""
    case = _case("E-08")
    result = scorer.score_priority(case.case)

    assert result.out_of_scope is False
    assert result.abstained is False
    assert result.colour == case.expected  # GREEN
    assert result.tews == 0

    assert len(result.triggered_rules) == 1, "a rule-less case must gain exactly one baseline"
    baseline = result.triggered_rules[0]
    assert baseline.rule_id == BASELINE_RULE_ID
    assert baseline.points == 0
    # The citation invariant still holds by construction.
    assert result.citations == [rule.citation for rule in result.triggered_rules]
    assert result.citations, "the routine priority carries no citation"
    # The citation names the loaded source (the reference text is never inlined in code).
    assert result.citations[0].endswith("within normal SATS bands")


# ------------------------------- 2. a case that fired a rule carries no baseline

def test_a_firing_case_carries_no_baseline_rule() -> None:
    """An in-scope non-zero case keeps exactly its own fired rules (T-04-22)."""
    result = scorer.score_priority(_case("E-02").case)

    assert result.triggered_rules, "E-02 should fire at least one band rule"
    assert all(rule.rule_id != BASELINE_RULE_ID for rule in result.triggered_rules)
    assert all(rule.points > 0 for rule in result.triggered_rules)
    assert result.citations == [rule.citation for rule in result.triggered_rules]


# --------------------- 3. a discriminator-override case carries no baseline

def test_a_discriminator_override_case_carries_no_baseline_rule() -> None:
    """A case overridden by a discriminator keeps exactly its own rules (T-04-22)."""
    case = _case("E-03")
    matched = matcher.match_discriminators(case.case.complaint).matched_ids
    assert matched, "E-03's complaint matched no discriminator"

    result = scorer.score_priority(case.case, matched)

    assert result.colour == case.expected  # ORANGE, earned by the override
    assert all(rule.rule_id != BASELINE_RULE_ID for rule in result.triggered_rules)
    assert result.citations == [rule.citation for rule in result.triggered_rules]


# ------------------------------------- 4. an abstained case stays uncited

def test_an_out_of_scope_case_stays_uncited() -> None:
    """An out-of-scope/abstained case carries no citations and no triggered rules."""
    result = scorer.score_priority(_case("E-06").case)

    assert result.out_of_scope is True
    assert result.abstained is True
    assert result.citations == []
    assert result.triggered_rules == []


# ------------------- 5. E-08 now defers — never reaches the gate (D8-11)

async def test_e08_defers_to_a_safe_terminal_and_never_reaches_the_gate(
    memory_store: Any,
) -> None:
    """Under D8-11 the routine TEWS-0 (no_match) case defers — never committed, no card.

    E-08 runs ``score -> verify -> recheck -> assess -> escalate`` and stops: there is no
    ``__interrupt__`` (the deferral denies the gate), no ``commit_priority`` call and no queue
    row. The graph-level "served through the gate" path this proof used to assert is superseded
    by the ``no_match`` deferral; the TEWS-0 baseline *citation* contract is still proven at the
    scorer level by ``test_a_tews_zero_case_is_sourced_by_the_baseline_citation``.
    """
    case = _case("E-08")
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=case.case, calls=calls, store=memory_store)
    app = build_graph(tools, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "E-08-baseline"}}

    done = await app.ainvoke({"raw_note": case.note}, config)

    # The scored colour is unchanged, but the deferral denies the gate.
    assert done["priority"].colour == case.expected  # GREEN
    assert not done.get("__interrupt__"), "the deferred case still reached the approval gate"
    signal = done.get("confidence")
    assert signal is not None and signal.deferral is True, "E-08 did not defer"
    assert done.get("escalation") is not None, "the deferral did not reach a safe terminal"
    assert done.get("handover") is None, "a deferred case produced a handover card"
    assert done.get("commit_result") is None
    assert "commit_priority" not in [name for name, _ in calls]
    assert memory_store.rows == [], "the deferred routine case wrote a queue row"


# ------------------- 6. INV-1 enforces "a scored priority is always sourced"

async def test_inv1_fails_a_scored_priority_with_no_citation() -> None:
    """INV-1 fails a scored priority with zero citations; the baseline-cited one passes."""
    uncited = PriorityResult(colour="GREEN", tews=0, citations=[], triggered_rules=[])
    failed = await evaluate(RunEvidence(case_id="X", expected="GREEN", priority=uncited))
    assert failed.results[INV_1] is False
    assert "citation" in failed.reasons[INV_1]

    sourced = scorer.score_priority(_case("E-08").case)
    passed = await evaluate(RunEvidence(case_id="E-08", expected="GREEN", priority=sourced))
    assert passed.results[INV_1] is True
