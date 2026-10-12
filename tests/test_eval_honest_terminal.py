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

import importlib.util
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from triagedesk.evals.analysis import analyse
from triagedesk.evals.case import ABORT_OUTCOME, CaseSpec
from triagedesk.evals.report import (
    GateResult,
    Provenance,
    Report,
    ReportCase,
    compute_report_digest,
)
from triagedesk.evals.runner import run_eval
from triagedesk.evals.tools import ToolMap, build_tools
from triagedesk.evals.usage import UsageRecorder

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"
GENERATOR_PATH = REPO_ROOT / "scripts" / "emit_evals.py"

_ALL_INVARIANTS = {"INV-1": True, "INV-2": True, "INV-3": True, "INV-4": True}
_COLOURS = {"GREEN", "YELLOW", "ORANGE", "RED"}


def _load_generator() -> ModuleType:
    """Load ``scripts/emit_evals.py`` as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("emit_evals", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EMIT = _load_generator()

# A minimal EVALS.md carrying the three tables the generator rewrites, including the
# hand-written ``Gate delivery`` narrative row the generator fills the Measured cell of.
_TEMPLATE = """# EVALS — test fixture

## 3. Reliability metrics

| Metric | Definition | How reported |
| --- | --- | --- |
| Colour accuracy | x | per case |
| Error direction | x | aggregate |
| Citation completeness | x | per case |
| Gate delivery | x | per case |
| Safety invariants | x | per case |
| Colour stability | x | per case |
| Field stability | x | per case |
| Latency | x | aggregate |
| Cost per run | x | aggregate |

## 4. Test cases

| # | Case | Synthetic input | Expected | Pass criteria | Runs (3×) | Result |
| --- | --- | --- | --- | --- | --- | --- |
| E-08 | No false alarm | input | **GREEN** | criteria | TBD | ⛔ |
| E-01 | Routine | input | **GREEN** | criteria | TBD | ⛔ |

## 5. Safety invariant checks (every case, every run)

| Invariant | Check | Result |
| --- | --- | --- |
| INV-1 | check | TBD |
| INV-2 | check | TBD |
| INV-3 | check | TBD |
| INV-4 | check | TBD |
"""


def _cell(output: str, row_prefix: str, index: int) -> str:
    """The *index*-th cell (from the right) of the table row starting with *row_prefix*."""
    row = next(line for line in output.splitlines() if line.startswith(row_prefix))
    return row.split("|")[index].strip()


def _synthetic_case(
    case_id: str, expected: str, outcomes: list[str], *, passed: bool | None = None
) -> ReportCase:
    """A synthetic report case carrying only the facts the analyser/generator read."""
    return ReportCase(
        case_id=case_id,
        expected=expected,
        runs=len(outcomes),
        colours=[outcome if outcome in _COLOURS else None for outcome in outcomes],
        outcomes=list(outcomes),
        colour_stable=True,
        field_stable=True,
        invariants=dict(_ALL_INVARIANTS),
        invariants_pass=True,
        passed=passed if passed is not None else all(o == expected for o in outcomes),
        latency_s=[0.1, 0.2, 0.3],
        tokens_in=10,
        tokens_out=5,
    )


def _synthetic_report(cases: list[ReportCase]) -> Report:
    """A synthetic report wrapping *cases* with a valid provenance block."""
    return Report(
        mode="offline",
        runs=3,
        cases_dir="evals/cases",
        provenance=Provenance(
            model_tag="test-model",
            ollama_version="test",
            prompt_hash="prompt",
            sats_tews_hash="tews",
            sats_discriminators_hash="discriminators",
            harness_commit="commit",
        ),
        cases=cases,
        invariants=dict(_ALL_INVARIANTS),
        gate=GateResult(passed=True),
    )


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
    """A matched run that produced a handover card records delivered=true and its colour (G-2)."""
    _, report = await _run_case(tmp_path, "E-02")
    case = report.cases[0]

    assert case.case_id == "E-02"
    assert case.delivered == [True, True, True]
    assert case.outcomes == ["ORANGE"] * 3
    assert case.passed is True


async def test_deferred_case_records_a_terminal_and_no_delivery(tmp_path: Path) -> None:
    """Under D8-11 E-08 defers: a terminal outcome with ``delivered=false``, never a colour."""
    _, report = await _run_case(tmp_path, "E-08")
    case = report.cases[0]

    assert case.case_id == "E-08"
    assert case.outcomes == ["ABSTAIN"] * 3
    assert case.delivered == [False, False, False]
    assert case.deferrals == [True, True, True]
    assert case.passed is False, "a deferred case was counted as a delivered pass"


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


# ------------------------------------------- 5. the analyser surfaces the abort signal


def test_analysis_surfaces_aborted_cases_and_runs() -> None:
    """``analyse`` names the aborted case and counts its runs, on their own (G-2)."""
    report = _synthetic_report(
        [
            _synthetic_case("E-08", "GREEN", [ABORT_OUTCOME] * 3, passed=False),
            _synthetic_case("E-01", "GREEN", ["GREEN"] * 3),
        ]
    )
    analysis = analyse(report)

    assert analysis.aborted_cases == ["E-08"]
    assert analysis.aborted_count == 3
    # The abort is NOT folded into the direction split or the colour accuracy figure.
    assert analysis.under_triage == []
    assert analysis.over_triage == []
    assert analysis.colour_runs == 3, "an abort leaked into the colour accuracy figure"


# ------------------------------ 6. the generator renders Gate delivery from the report


def test_generator_renders_gate_delivery_from_the_report_and_is_idempotent() -> None:
    """The ``Gate delivery`` cell equals the report's own aborted count; rendering is stable."""
    report = _synthetic_report(
        [
            _synthetic_case("E-08", "GREEN", [ABORT_OUTCOME] * 3, passed=False),
            _synthetic_case("E-01", "GREEN", ["GREEN"] * 3),
        ]
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})

    first = _EMIT.render_evals(_TEMPLATE, sealed)
    second = _EMIT.render_evals(first, sealed)
    assert first == second, "the generator is not idempotent"

    # 2 cases, 1 of which aborted -> "1/2 cases" — rendered from the report, never typed.
    assert _cell(first, "| Gate delivery ", -2) == "1/2 cases"


# --------------------------------------- 7. an aborted run is rendered failing, not a pass


def test_aborted_case_is_rendered_failing() -> None:
    """A case whose runs aborted is rendered ❌ in §4 — an abort is never a pass (G-2)."""
    report = _synthetic_report(
        [_synthetic_case("E-08", "GREEN", [ABORT_OUTCOME] * 3, passed=False)]
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    output = _EMIT.render_evals(_TEMPLATE, sealed)

    assert _cell(output, "| E-08 ", -2) == "\u274c", "an aborted run was rendered as a pass"
    assert _cell(output, "| Gate delivery ", -2) == "0/1 cases"

