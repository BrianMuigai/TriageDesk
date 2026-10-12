"""Suite proof for the honest 14-case evaluation (Plan 04-02, EVAL-01, D-04/D-05).

Offline and deterministic (the model and the MCP subprocess are never launched — the
golden extractions are the fixtures, and the REAL matcher, scorer, recheck and gated
commit run in-process). Seven proofs:

1. coverage — all 14 declared ids E-01..E-14 load, plus at least two held-out cases;
2. exactly one declared failure (E-09) and the run records it failing, never passing it;
3. every held-out case passes, bounding the E-09 failure (it is not universal);
4. the real matcher returns ``no_match`` for the E-09 complaint and a match for
   H-01/H-02, so the fixture set is honest and the coverage gap is not tuned;
5. E-05 -> RECOVER, E-06 -> ABSTAIN, E-07 -> RECHECK, E-12 -> RECOVER, none writes a
   queue row, and the injected E-12 fault does not leak into a non-injected case;
6. the E-12 injection exercises the graph's bounded retry (exactly one retry) and a
   non-injected case is unaffected (T-04-09);
7. every expected token is a declared colour/terminal and every fixture is synthetic-only
   (T-04-06, T-04-10).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from triagedesk.core import matcher
from triagedesk.evals.case import ABORT_OUTCOME, CaseSpec, declared_outcomes, load_cases
from triagedesk.evals.report import Report, ReportCase
from triagedesk.evals.runner import run_eval
from triagedesk.evals.tools import ToolMap, build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.store.memory import InMemoryStore

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

# The 14 published cases (EVALS.md §4). E-02 already exists; this plan adds the rest.
DECLARED_IDS = [f"E-{index:02d}" for index in range(1, 15)]

# The synthetic-only guard (challenge data conduct, T-04-10): no fixture may carry a
# name/identifier-shaped token.
_IDENTIFIER_PATTERN = re.compile(
    r"\b(mrn|patient id|hospital number|id number|national id|name\s*:)\b",
    re.IGNORECASE,
)


@pytest.fixture
async def suite(tmp_path: Path) -> tuple[int, Report, InMemoryStore]:
    """Run the whole fixture set offline once and return (exit code, report, store)."""
    store = InMemoryStore()
    report_path = tmp_path / "report.json"
    code = await run_eval(
        cases_dir=CASES_DIR,
        runs=3,
        report_path=report_path,
        offline=True,
        store=store,
    )
    report = Report.model_validate_json(report_path.read_text(encoding="utf-8"))
    return code, report, store


def _report_case(report: Report, case_id: str) -> ReportCase:
    """The single report case for *case_id* (fails loudly if it is missing or duplicated)."""
    matches = [case for case in report.cases if case.case_id == case_id]
    assert len(matches) == 1, f"expected exactly one report case {case_id}, got {len(matches)}"
    return matches[0]


# ----------------------------------------------------------- 1. coverage (EVAL-01)


def test_all_declared_and_held_out_cases_load() -> None:
    """Every declared id E-01..E-14 loads, plus at least two held-out cases (EVAL-01)."""
    cases = load_cases(CASES_DIR)
    ids = {case.id for case in cases}
    missing = set(DECLARED_IDS) - ids
    assert not missing, f"missing declared ids: {sorted(missing)}"
    held_out = [case for case in cases if case.held_out]
    assert len(held_out) >= 2, "the E-09 failure is not bounded by held-out cases"


# ------------------------------------------------- 2. the one declared failure (D-04)


async def test_exactly_one_declared_failure_is_recorded_failing(
    suite: tuple[int, Report, InMemoryStore],
) -> None:
    """E-09 is the sole declared failure, records a terminal deferral, and fails (D-04)."""
    code, report, store = suite
    declared = [case.id for case in load_cases(CASES_DIR) if case.declared_failure]
    assert declared == ["E-09"], f"unexpected declared failures: {declared}"

    e09 = _report_case(report, "E-09")
    assert e09.declared_failure is True
    assert e09.passed is False, "the declared failure was silently passed"
    # Under D8-11 E-09 defers to a terminal — a recorded deferral, not a delivered colour.
    assert e09.outcomes == ["ABSTAIN"] * 3, "the no_match deferral did not fire for E-09"
    assert e09.deferrals == [True, True, True]
    assert store.rows == [], "the deferred declared failure wrote a queue row"
    # Only the declared failure misses, so the run must exit 0 (EVAL honesty).
    assert code == 0


# ------------------------------------------------------- 3. held-out bound (D-04)


async def test_held_out_cases_pass_and_bound_the_failure(
    suite: tuple[int, Report, InMemoryStore],
) -> None:
    """Every held-out case passes, so the E-09 failure is bounded, not universal (D-04)."""
    _, report, _ = suite
    held_out_ids = {case.id for case in load_cases(CASES_DIR) if case.held_out}
    assert held_out_ids, "no held-out cases loaded"
    for case_id in sorted(held_out_ids):
        case = _report_case(report, case_id)
        assert case.passed is True, f"held-out case {case_id} did not pass"


# ------------------------------------------ 4. the matcher is honest, not tuned (D-05)


def test_matcher_returns_no_match_for_e09_and_a_match_for_held_out() -> None:
    """The E-09 complaint matches nothing; H-01/H-02 match — the gap is not tuned (D-05)."""
    cases = {case.id: case for case in load_cases(CASES_DIR)}

    e09 = matcher.match_discriminators(cases["E-09"].case.complaint)
    assert e09.no_match is True
    assert e09.matched_ids == []

    for case_id in ("H-01", "H-02"):
        result = matcher.match_discriminators(cases[case_id].case.complaint)
        assert result.no_match is False, f"{case_id} retrieved no discriminator"
        assert result.matched_ids, f"{case_id} retrieved no discriminator"


# --------------------------------- 5. terminal outcomes are first-class, no queue write


async def test_terminal_outcomes_are_first_class_and_write_no_queue_row(
    suite: tuple[int, Report, InMemoryStore],
) -> None:
    """RECOVER/ABSTAIN/RECHECK are measured outcomes and no terminal case writes (ORCH-05)."""
    _, report, store = suite

    assert _report_case(report, "E-05").outcomes == ["RECOVER"] * 3
    assert _report_case(report, "E-06").outcomes == ["ABSTAIN"] * 3
    # E-07 keeps its deterministic RECHECK outcome AND is a coverage deferral (dual nature).
    assert _report_case(report, "E-07").outcomes == ["RECHECK"] * 3
    assert _report_case(report, "E-07").deferrals == [True, True, True]
    assert _report_case(report, "E-12").outcomes == ["RECOVER"] * 3

    assert store.rows == [], "a recovery/abstention/recheck case wrote a queue row"

    # E-01 is now a COVERAGE DEFERRAL: the no_match override denies it the gate, so it must be
    # reported as a deferral (surfaced in ``deferral_cases``), never silently excused (D8-11).
    e01 = _report_case(report, "E-01")
    assert e01.outcomes == ["ABSTAIN"] * 3
    assert e01.deferrals == [True, True, True]
    assert e01.passed is False

    # The gate's exclusion can never be silent: every moved non-declared case is surfaced.
    assert {"E-01", "E-08", "E-13", "E-14"} <= set(report.analysis.deferral_cases)


# ----------------------------- 5b. the deferral-aware gate never masks a wrong colour


def test_deferral_gate_excludes_a_covered_run_but_never_a_wrong_colour() -> None:
    """An all-deferred case is excluded from ``unexpected_failures``; a wrong colour is not."""
    from triagedesk.evals.runner import _build_gate

    def case(case_id: str, deferrals: list[bool | None]) -> ReportCase:
        return ReportCase(
            case_id=case_id,
            expected="GREEN",
            runs=len(deferrals),
            outcomes=["ABSTAIN"] * len(deferrals),
            invariants={"INV-1": True, "INV-2": True, "INV-3": True, "INV-4": True},
            invariants_pass=True,
            passed=False,
            deferrals=deferrals,
        )

    gate = _build_gate(
        [
            case("covered", [True, True, True]),
            case("wrong", [False, False, False]),
            case("partial", [True, False, True]),
        ]
    )
    assert "covered" not in gate.unexpected_failures
    assert "wrong" in gate.unexpected_failures
    assert "partial" in gate.unexpected_failures, "a partially-deferred case was excused"


# -------------------------------------- 6. the injected fault exercises the real retry


class _CountingFactory:
    """A tool factory that counts ``normalize_case`` calls per run (T-04-09, Pitfall 13).

    It wraps the default injected mapping (so the E-12 fault is applied) and counts how
    many times the graph calls ``normalize_case`` — proving the bounded retry was consumed
    (first call timeout, second malformed) and that a non-injected case calls it once.
    """

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, case: CaseSpec, offline: bool, recorder: UsageRecorder) -> ToolMap:
        tools = dict(build_tools(case, offline=offline, recorder=recorder))
        inner = tools["normalize_case"]

        async def counted(inp: object) -> object:
            self.calls += 1
            return await inner(inp)  # type: ignore[arg-type]

        tools["normalize_case"] = counted
        return tools


async def test_e12_injection_retries_once_and_never_leaks(tmp_path: Path) -> None:
    """The E-12 fault consumes exactly one retry; a non-injected case is unaffected."""
    injected = _CountingFactory()
    code = await run_eval(
        cases_dir=CASES_DIR,
        runs=1,
        report_path=tmp_path / "e12.json",
        offline=True,
        case_filter="E-12",
        tool_factory=injected,
    )
    # First call times out, second returns malformed JSON, then the deterministic fallback.
    assert injected.calls == 2, f"E-12 normalize called {injected.calls} times, expected 2"
    assert code == 0  # RECOVER is the expected outcome

    clean = _CountingFactory()
    await run_eval(
        cases_dir=CASES_DIR,
        runs=1,
        report_path=tmp_path / "e01.json",
        offline=True,
        case_filter="E-01",
        tool_factory=clean,
    )
    assert clean.calls == 1, "a non-injected case was affected by the E-12 fault"


# ------------------------------------- 6b. a run that errors is surfaced, not lost (WR-04)


class _RaisingFactory:
    """A tool factory whose ``match_discriminators`` always raises — a run that errors.

    The raise happens after ``normalize`` (whose own failures the graph retries internally),
    so the exception escapes ``graph.ainvoke`` and the runner must record the run rather than
    lose it (WR-04).
    """

    def __call__(self, case: CaseSpec, offline: bool, recorder: UsageRecorder) -> ToolMap:
        tools = dict(build_tools(case, offline=offline, recorder=recorder))

        async def boom(inp: object) -> object:
            raise RuntimeError("injected runner error")

        tools["match_discriminators"] = boom
        return tools


async def test_a_run_that_errors_is_surfaced_not_conflated_with_a_short_circuit(
    tmp_path: Path,
) -> None:
    """An errored run is recorded (ABORT + run_errors); the suite still writes a report (WR-04)."""
    report_path = tmp_path / "error.json"
    code = await run_eval(
        cases_dir=CASES_DIR,
        runs=3,
        report_path=report_path,
        offline=True,
        case_filter="E-02",
        tool_factory=_RaisingFactory(),
    )
    report = Report.model_validate_json(report_path.read_text(encoding="utf-8"))
    case = report.cases[0]

    assert code != 0, "a suite with an errored run did not fail the gate"
    assert case.outcomes == [ABORT_OUTCOME] * 3, "an errored run was folded into a colour/None"
    assert len(case.run_errors) == case.runs, "the per-run error state is not run-aligned"
    assert all(err and "injected runner error" in err for err in case.run_errors)
    assert case.passed is False, "an errored run was counted as a pass"
    assert "E-02" in report.gate.unexpected_failures


# ------------------------------------- 7. declared tokens + synthetic-only fixtures


def test_expected_tokens_are_declared_and_fixtures_are_synthetic_only() -> None:
    """Every expectation is a declared token and every fixture is synthetic-only."""
    allowed = declared_outcomes()
    for case in load_cases(CASES_DIR):
        assert case.expected in allowed, f"{case.id} has a free-form expectation"

    for source in sorted(CASES_DIR.glob("*.yaml")):
        text = source.read_text(encoding="utf-8")
        assert not _IDENTIFIER_PATTERN.search(text), (
            f"{source.name} carries name/identifier-shaped content"
        )
