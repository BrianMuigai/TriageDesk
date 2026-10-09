"""Tracer proof suite for the eval harness (Plan 04-01, D-01/D-02/D-08, EVAL-02).

Five offline, deterministic proofs (the real local-model run is 04-04's job):

1. ``run_eval`` over the E-02 fixture writes a report with three colours, three
   matched-discriminator sets and the three stability flags; the deterministic offline
   path is colour-stable (D-02);
2. a synthetic unstable case (a tool stub returning a different colour on the third run)
   is recorded as an instability, never resolved by a majority (D-02, Pitfall 12);
3. ``field_stable`` is computed independently of ``colour_stable`` — a stable colour with a
   varying evidence field is visible (Pitfall 6);
4. the report carries the provenance hashes and a ``report_digest`` that recomputes from
   the non-volatile content (D-08);
5. the harness drives the REAL gated ``commit_priority`` — an unapproved resume is refused
   and writes no queue row (the eval never bypasses the gate).

The model and the MCP subprocess are never launched: offline mode stubs the model and the
alternating cases inject a tool mapping (``tests/conftest.py``).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from conftest import build_graph_tools
from triagedesk.core.schema import PriorityResult, TriggeredRule
from triagedesk.evals.case import CaseSpec
from triagedesk.evals.report import Report, compute_report_digest
from triagedesk.evals.runner import ToolFactory, run_eval
from triagedesk.evals.usage import UsageRecorder
from triagedesk.store.memory import InMemoryStore

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

# A mutation applied to a run's scored result — used to make an instability real and
# observable in the graph output rather than simulated in an assertion.
Mutator = Callable[[PriorityResult, int], PriorityResult]


def _alternating_factory(mutate: Mutator) -> ToolFactory:
    """Build a tool factory whose third run mutates the scored result (real instability).

    The counter is closure state: the runner calls the factory once per run, so the third
    call is the third run. Every other tool is the shared offline fake, so only the scored
    field under test varies.
    """
    state = {"run": 0}

    def factory(case: CaseSpec, offline: bool, recorder: UsageRecorder) -> Any:
        state["run"] += 1
        run = state["run"]
        tools = build_graph_tools(case=case.case)
        base_score = tools["score_priority"]

        async def score_priority(inp: dict[str, Any]) -> PriorityResult:
            result = await base_score(inp)
            return mutate(result, run) if run == 3 else result

        tools["score_priority"] = score_priority
        return tools

    return factory


async def _run_e02(tmp_path: Path, *, expect_code: int = 0, **kwargs: Any) -> Report:
    """Run the E-02 fixture offline and return the parsed report.

    ``expect_code`` is the runner's exit code the caller expects: a stable pass is 0,
    while an injected colour/matched-set instability is a non-zero recorded failure
    (D-02, T-04-08).
    """
    report_path = tmp_path / "report.json"
    code = await run_eval(
        cases_dir=CASES_DIR,
        runs=kwargs.pop("runs", 3),
        report_path=report_path,
        offline=True,
        case_filter="E-02",
        **kwargs,
    )
    assert code == expect_code
    return Report.model_validate_json(report_path.read_text(encoding="utf-8"))


# ----------------------------------------------------- 1. report shape + stability flags


async def test_offline_tracer_records_three_runs_and_stability(tmp_path: Path) -> None:
    """E-02 runs three times and reports three colours, sets and stability flags (D-02)."""
    report = await _run_e02(tmp_path)

    assert report.mode == "offline"
    assert len(report.cases) == 1
    case = report.cases[0]
    assert case.case_id == "E-02"
    assert case.colours == ["ORANGE", "ORANGE", "ORANGE"]
    assert len(case.matched_discriminators) == 3
    assert len(case.citations) == 3
    # The deterministic offline path is stable on all three signals.
    assert case.colour_stable is True
    assert case.matched_set_stable is True
    assert case.field_stable is True
    assert len(case.latency_s) == 3
    assert all(latency >= 0 for latency in case.latency_s)


# -------------------------------------------- 2. an unstable colour is a recorded failure


async def test_unstable_colour_is_recorded_not_averaged(tmp_path: Path) -> None:
    """A colour that varies on the third run is an instability, never a majority (Pitfall 12)."""
    factory = _alternating_factory(
        lambda result, _run: result.model_copy(update={"colour": "GREEN"})
    )
    # An unstable colour is a recorded failure, so the run exits non-zero (T-04-08).
    report = await _run_e02(tmp_path, expect_code=1, tool_factory=factory)
    case = report.cases[0]

    assert case.colour_stable is False
    assert case.passed is False
    # All three colours are preserved — the odd one out is not hidden behind a majority.
    assert case.colours == ["ORANGE", "ORANGE", "GREEN"]
    assert len(set(case.colours)) == 2


# ---------------------------------- 3. field stability is independent of colour stability


def _add_evidence(result: PriorityResult, _run: int) -> PriorityResult:
    """Add one cited rule — a field change that keeps the citation invariant intact.

    Both ``triggered_rules`` and ``citations`` must move together: the graph's ``verify``
    asserts ``len(citations) == len(triggered_rules)``, so varying only one would fail the
    evidence check and change the outcome instead of isolating field stability.
    """
    rule = TriggeredRule(
        rule_id="extra", detail="extra -> 0 points", points=0, citation="extra citation"
    )
    return result.model_copy(
        update={
            "triggered_rules": [*result.triggered_rules, rule],
            "citations": [*result.citations, rule.citation],
        }
    )


async def test_field_stability_is_independent_of_colour_stability(tmp_path: Path) -> None:
    """A stable colour with a varying citation list is colour-stable but not field-stable."""
    factory = _alternating_factory(_add_evidence)
    report = await _run_e02(tmp_path, tool_factory=factory)
    case = report.cases[0]

    assert case.colour_stable is True
    assert case.matched_set_stable is True
    assert case.field_stable is False


# ------------------------------------------------------ 4. provenance + reproducible digest


async def test_report_carries_provenance_and_a_recomputing_digest(tmp_path: Path) -> None:
    """The report carries the provenance hashes and a digest that recomputes (D-08)."""
    report = await _run_e02(tmp_path)

    provenance = report.provenance
    assert provenance.model_tag
    assert provenance.prompt_hash
    assert provenance.sats_tews_hash
    assert provenance.sats_discriminators_hash
    assert provenance.harness_commit
    # The digest seals the non-volatile content and recomputes exactly.
    assert report.report_digest
    assert report.report_digest == compute_report_digest(report)


async def test_offline_digest_is_reproducible_across_runs(tmp_path: Path) -> None:
    """Re-running the same offline case reproduces the same digest (D-08, Pitfall 18)."""
    first = await _run_e02(tmp_path / "first")
    second = await _run_e02(tmp_path / "second")
    assert first.report_digest == second.report_digest


# ------------------------------------------- 5. the real gate is driven and refuses a dismiss


async def test_harness_drives_the_real_gate_and_writes_nothing_on_dismiss(tmp_path: Path) -> None:
    """An unapproved resume is refused by the real commit and writes no queue row (D-05)."""
    store = InMemoryStore()
    report_path = tmp_path / "report.json"

    code = await run_eval(
        cases_dir=CASES_DIR,
        runs=1,
        report_path=report_path,
        offline=True,
        case_filter="E-02",
        store=store,
    )

    assert code == 0
    assert store.rows == [], "an unapproved resume wrote a queue row"
    # The REAL gated tool ran in-process and recorded its refusal.
    commit_records = [record for record in store.audit_records if record.tool == "commit_priority"]
    assert commit_records, "the real gated commit_priority was never exercised"
    assert all(record.outputs.get("refused") is True for record in commit_records)
