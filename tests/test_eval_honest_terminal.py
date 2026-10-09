"""Honest-terminal proof: delivered-through-the-gate vs aborted-at-END (Plan 04-06, G-2).

Offline and deterministic (the model is never called). The harness reads the graph's own
terminal facts — ``delivered`` (a handover card was produced through the approval gate),
``route`` and ``attempt`` — and records a card-less ``END`` as the declared ``ABORT``
outcome, never as a delivered colour. This closes G-2: a fail-closed ``verify`` (a scored
priority that lost its citations) used to be reported as a passing colour.

1. a run whose scored priority loses its citations fail-closes at ``verify`` -> ``END`` and
   is recorded as ``ABORT`` with ``delivered: false``, a non-zero ``attempt`` and
   ``passed: false`` — never a GREEN pass (T-04-26);
2. a normal delivered run records ``delivered: true`` and its colour outcome;
3. an aborted non-declared case exits non-zero (the gate is the exit code);
4. the abort signal is surfaced by the analyser and rendered by the generator (added in
   Task 2).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from triagedesk.evals.case import ABORT_OUTCOME, CaseSpec
from triagedesk.evals.report import Report, compute_report_digest
from triagedesk.evals.runner import run_eval
from triagedesk.evals.tools import ToolMap, build_tools
from triagedesk.evals.usage import UsageRecorder

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"


def _strip_citations_factory(
    case: CaseSpec, offline: bool, recorder: UsageRecorder
) -> ToolMap:
    """Wrap the real tools so the scored priority loses its citations.

    The graph's ``verify`` then fail-closes (``len(citations) != len(triggered_rules)``
    and no evidence), routes ``retry`` once and stops at ``END`` — a card-less abort. Every
    other tool is the real owned tool, so the gate under test is the shipped gate
    (SOLID: L); only the evidence field is corrupted to force the fail-close.
    """
    tools = dict(build_tools(case, offline=offline, recorder=recorder))
    inner = tools["score_priority"]

    async def score_priority(inp: Mapping[str, Any]) -> Any:
        result = await inner(inp)
        return result.model_copy(update={"citations": []})

    tools["score_priority"] = score_priority
    return tools


async def _run_case(tmp_path: Path, case_id: str, **kwargs: Any) -> tuple[int, Report]:
    """Run one case offline and return (exit code, parsed report)."""
    report_path = tmp_path / "report.json"
    code = await run_eval(
        cases_dir=CASES_DIR,
        runs=3,
        report_path=report_path,
        offline=True,
        case_filter=case_id,
        **kwargs,
    )
    return code, Report.model_validate_json(report_path.read_text(encoding="utf-8"))


# ------------------------------------ 1. a card-less END is ABORT, never a colour pass


async def test_aborted_run_is_recorded_as_abort_not_a_pass(tmp_path: Path) -> None:
    """A fail-closed verify is recorded as ABORT/delivered=false, never a GREEN pass (G-2)."""
    _, report = await _run_case(tmp_path, "E-08", tool_factory=_strip_citations_factory)
    case = report.cases[0]

    assert case.case_id == "E-08"
    assert case.outcomes == [ABORT_OUTCOME] * 3, "a card-less END was reported as a colour"
    assert case.delivered == [False, False, False]
    assert all(attempt >= 1 for attempt in case.attempts), "the abort did not consume a retry"
    assert case.passed is False, "an aborted run was counted as a pass"
    # The residual colour is still captured (for audit), but it is NOT the outcome.
    assert case.colours == ["GREEN"] * 3


# ------------------------------------------ 2. a delivered run keeps its colour outcome


async def test_delivered_run_records_its_colour_and_delivered(tmp_path: Path) -> None:
    """A run that produced a handover card records delivered=true and its colour (G-2)."""
    _, report = await _run_case(tmp_path, "E-08")
    case = report.cases[0]

    assert case.delivered == [True, True, True]
    assert case.outcomes == ["GREEN"] * 3
    assert case.passed is True


# -------------------------------------------------- 3. an abort exits non-zero (the gate)


async def test_abort_of_a_non_declared_case_exits_non_zero(tmp_path: Path) -> None:
    """A non-declared case that aborts fails the gate and exits non-zero (D-06)."""
    code, report = await _run_case(tmp_path, "E-08", tool_factory=_strip_citations_factory)

    assert code != 0, "an aborted non-declared case did not fail the gate"
    assert report.gate.passed is False
    assert "E-08" in report.gate.unexpected_failures


# ------------------------------------------- 4. the terminal facts are sealed in the digest


async def test_terminal_facts_are_sealed_in_the_digest(tmp_path: Path) -> None:
    """``delivered``/``routes``/``attempts`` are sealed, so a flipped abort is detectable."""
    _, report = await _run_case(tmp_path, "E-08", tool_factory=_strip_citations_factory)
    case = report.cases[0]
    assert case.routes == ["retry"] * 3

    # Flipping the sealed terminal fact changes the digest — a hand-edit is detectable.
    tampered_case = case.model_copy(update={"delivered": [True, True, True]})
    tampered = report.model_copy(update={"cases": [tampered_case]})
    assert compute_report_digest(tampered) != report.report_digest
