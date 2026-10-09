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
5. E-08 runs through the ONE graph interface with the offline eval tools, reaches the
   approval gate, and on an unapproved resume delivers a sourced GREEN handover card
   (T-04-24) — the routine patient is served, not silenced.

Offline and deterministic: the model and the MCP subprocess are never launched (the
autouse store fixture injects the in-memory store; the eval tools call the real owned
tools in-process).
"""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from triagedesk.core import matcher, scorer
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
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


# ------------------- 5. E-08 reaches the gate and delivers a sourced GREEN card

async def test_e08_reaches_the_gate_and_delivers_a_sourced_green_card() -> None:
    """The routine patient gets a sourced GREEN card through the gate, not a fail-close."""
    case = _case("E-08")
    tools = build_tools(case, offline=True, recorder=UsageRecorder())
    app = build_graph(tools, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "E-08-baseline"}}

    paused = await app.ainvoke({"raw_note": case.note, "case": case.case}, config)

    assert paused.get("__interrupt__"), (
        "E-08 fail-closed at verify instead of reaching the approval gate (G-1)"
    )
    payload = paused["__interrupt__"][0].value
    assert payload["colour"] == case.expected  # GREEN
    assert payload["citations"], "the routine priority carries no citation"
    assert len(payload["citations"]) == len(payload["triggered_rules"])

    # An unapproved resume still renders the card (the commit is refused, then handover).
    done = await app.ainvoke(Command(resume={"decision": "dismiss"}), config)

    card = done["handover"]
    assert card is not None, "the routine patient received no handover card"
    assert card.colour == case.expected  # GREEN
    assert card.citations, "the delivered card carries no citation"
    assert len(card.citations) == len(card.triggered_rules)
