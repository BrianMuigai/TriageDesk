"""Report proof: direction split, sole source, reproducibility, cost (Plan 04-04, EVAL-04/05).

Offline and deterministic (the local model is never called). Six behaviours:

1. a crafted report with one under-triage and one over-triage reports both SEPARATELY,
   with the correct case in each direction (EVAL-04, D-03);
2. the direction is derived from the loaded substrate ordering — a crafted ordering change
   moves a case's direction with no code change (CONVENTIONS §1);
3. the report carries latency p50/p95 and token in/out totals, and a report missing them
   fails the analysis (EVAL-05);
4. ``report_digest`` recomputes from the non-volatile content and a mutated outcome
   changes it (reproducibility, D-08);
5. the generator is idempotent and every number it writes equals the value in the report
   (the report is the sole source; no hand-entered number);
6. the declared failure is present in the generated output and is NOT counted as a pass
   (honesty, D-04).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from triagedesk.core.hashing import hash_tool_schema
from triagedesk.core.schema import ExtractionResult
from triagedesk.evals.analysis import analyse, colour_urgency
from triagedesk.evals.report import (
    Analysis,
    Calibration,
    GateResult,
    Mode,
    Provenance,
    Report,
    ReportCase,
    RiskCoveragePoint,
    _digest_payload,
    build_provenance,
    compute_report_digest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "scripts" / "emit_evals.py"
REPORT_PATH = REPO_ROOT / "evals" / "results" / "report.json"
EVALS_PATH = REPO_ROOT / "EVALS.md"

_ALL_INVARIANTS = {"INV-1": True, "INV-2": True, "INV-3": True, "INV-4": True}

# The ONE synthetic provenance block the helpers below wrap reports with.
_PROVENANCE = Provenance(
    model_tag="test-model",
    ollama_version="test",
    prompt_hash="prompt",
    extraction_schema_hash="extraction-schema",
    sats_tews_hash="tews",
    sats_discriminators_hash="discriminators",
    harness_commit="commit",
)


def _load_generator() -> ModuleType:
    """Load ``scripts/emit_evals.py`` as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("emit_evals", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EMIT = _load_generator()

# A minimal EVALS.md carrying the three tables the generator rewrites. The narrative
# cells are placeholders here; only the result cells are asserted on. The §4 rows are
# supplied per test by ``_template_for`` so the row set matches the report's case set.
_TEMPLATE_BASE = """# EVALS — test fixture

## 3. Reliability metrics

| Metric | Definition | How reported |
| --- | --- | --- |
| Colour accuracy | x | per case |
| Error direction | x | aggregate |
| Citation completeness | x | per case |
| Safety invariants | x | per case |
| Colour stability | x | per case |
| Field stability | x | per case |
| Latency | x | aggregate |
| Cost per run | x | aggregate |
| Deferral rate | x | aggregate |
| Calibration (small-sample) | x | aggregate |

## 4. Test cases

| # | Case | Synthetic input (vitals / complaint) | Expected | Pass criteria | Runs (3×) | Result |
| --- | --- | --- | --- | --- | --- | --- |
{{ROWS}}

## 5. Safety invariant checks (every case, every run)

| Invariant | Check | Result |
| --- | --- | --- |
| INV-1 | check | TBD |
| INV-2 | check | TBD |
| INV-3 | check | TBD |
| INV-4 | check | TBD |

## 6. The failure we did not fix

### 6.1 Coverage deferrals — the `no_match` class now defers

Hand-written prose (preserved verbatim by the generator).
"""

# One §4 data row for the fixture; ``_template_for`` fills the id so the row set matches a report.
_ROW = "| {case_id} | Case | input | **GREEN** | criteria | TBD | \u26d4 |"


def _template_for(case_ids: list[str]) -> str:
    """The EVALS.md fixture whose §4 rows are exactly *case_ids*.

    The generator requires the §4 row set to EQUAL the report's case set (D11-06, WR-02), so a
    rendering test's fixture must carry a row for exactly its report's cases. Deriving the rows
    from the case ids keeps each fixture consistent with its report without a hand-kept row list.
    """
    rows = "\n".join(_ROW.format(case_id=case_id) for case_id in case_ids)
    return _TEMPLATE_BASE.replace("{{ROWS}}", rows)


# The base fixture (five §4 rows) is used by the guard tests, which assert a MISMATCH raises.
_TEMPLATE = _template_for(["E-01", "E-09", "D-1", "D-2", "H-9"])


def _report_case(
    case_id: str,
    expected: str,
    outcomes: list[str],
    *,
    colour_stable: bool = True,
    field_stable: bool = True,
    latency_s: tuple[float | None, ...] = (0.1, 0.2, 0.3),
    tokens_in: int = 10,
    tokens_out: int = 5,
    declared_failure: bool = False,
    passed: bool | None = None,
    held_out: bool = False,
    deferrals: list[bool | None] | None = None,
    confidence_levels: list[str | None] | None = None,
    confidence_satisfied: list[int | None] | None = None,
) -> ReportCase:
    """A synthetic report case carrying only the facts the analyser/generator read."""
    return ReportCase(
        case_id=case_id,
        expected=expected,
        runs=len(outcomes),
        colours=list(outcomes),
        outcomes=list(outcomes),
        colour_stable=colour_stable,
        field_stable=field_stable,
        invariants=dict(_ALL_INVARIANTS),
        invariants_pass=True,
        passed=passed if passed is not None else all(o == expected for o in outcomes),
        latency_s=list(latency_s),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        declared_failure=declared_failure,
        held_out=held_out,
        deferrals=deferrals if deferrals is not None else [False] * len(outcomes),
        confidence_levels=(
            confidence_levels if confidence_levels is not None else ["high"] * len(outcomes)
        ),
        confidence_satisfied=(
            confidence_satisfied if confidence_satisfied is not None else [3] * len(outcomes)
        ),
    )


def _report(cases: list[ReportCase], *, runs: int = 3, mode: Mode = "offline") -> Report:
    """A synthetic report wrapping *cases* with a valid provenance block."""
    return Report(
        mode=mode,
        runs=runs,
        cases_dir="evals/cases",
        provenance=_PROVENANCE,
        cases=cases,
        invariants=dict(_ALL_INVARIANTS),
        gate=GateResult(passed=True),
    )


def _cell(output: str, row_prefix: str, index: int) -> str:
    """The *index*-th cell (from the right) of the table row starting with *row_prefix*."""
    row = next(line for line in output.splitlines() if line.startswith(row_prefix))
    return row.split("|")[index].strip()


# ------------------------------------------------- 1. separate under/over directions (D-03)


def test_under_and_over_triage_are_reported_separately() -> None:
    """One under-triage and one over-triage are reported on their own sides (EVAL-04)."""
    report = _report(
        [
            _report_case("U", "ORANGE", ["GREEN"] * 3),  # measured below expected
            _report_case("O", "GREEN", ["ORANGE"] * 3),  # measured above expected
            _report_case("C", "YELLOW", ["YELLOW"] * 3),  # correct
        ]
    )
    analysis = analyse(report)
    assert analysis.under_triage == ["U"]
    assert analysis.under_triage_count == 3
    assert analysis.over_triage == ["O"]
    assert analysis.over_triage_count == 3
    # The two directions are NOT collapsed into one symmetric figure.
    assert analysis.colour_correct == 3
    assert analysis.colour_runs == 9


# ------------------------------------------ 2. direction derives from the substrate (§1)


def test_direction_is_derived_from_the_substrate_ordering() -> None:
    """A crafted ordering change moves a case's direction with no code change (§1)."""
    report = _report([_report_case("X", "YELLOW", ["ORANGE"])])

    # The default ordering is the loaded substrate (GREEN < YELLOW < ORANGE < RED).
    default = analyse(report)
    assert default.over_triage == ["X"], "ORANGE should be more urgent than YELLOW"
    assert default.under_triage == []

    # A crafted ordering (as a substrate edit would produce) with ORANGE less urgent than
    # YELLOW flips the direction — proving the split is data-derived, not hard-coded.
    flipped = analyse(report, urgency={"GREEN": 0, "ORANGE": 1, "YELLOW": 2, "RED": 3})
    assert flipped.under_triage == ["X"]
    assert flipped.over_triage == []


def test_colour_urgency_reads_the_substrate_ordering() -> None:
    """The default ordering is strictly increasing across the loaded colour bands."""
    urgency = colour_urgency()
    ordered = sorted(urgency, key=lambda colour: urgency[colour])
    assert len(ordered) >= 4
    assert urgency[ordered[0]] < urgency[ordered[-1]]


# --------------------------------------------- 3. latency + cost present, missing fails


def test_report_carries_latency_and_cost_and_fails_when_missing() -> None:
    """Latency p50/p95 and token totals are present; a report missing them fails (EVAL-05)."""
    report = _report(
        [
            _report_case(
                "A", "GREEN", ["GREEN"], latency_s=(0.1, 0.2, 0.3), tokens_in=7, tokens_out=3
            ),
            _report_case("B", "GREEN", ["GREEN"], latency_s=(0.4,), tokens_in=5, tokens_out=2),
        ]
    )
    analysis = analyse(report)
    assert analysis.latency_p50 == pytest.approx(0.2)
    assert analysis.latency_p95 == pytest.approx(0.4)
    assert analysis.tokens_in == 12
    assert analysis.tokens_out == 5

    # A report with no latency samples cannot be analysed.
    missing = _report([_report_case("C", "GREEN", ["GREEN"], latency_s=())])
    with pytest.raises(ValueError):
        analyse(missing)


def test_errored_run_latency_is_excluded_from_the_percentiles() -> None:
    """A ``None`` latency (an errored run) is dropped from the p50/p95 sample (IN-04).

    An errored run has no valid latency, so it must not inject a spurious ``0.0`` into the
    percentile sample and understate the published figure.
    """
    report = _report(
        [
            _report_case("A", "GREEN", ["GREEN"], latency_s=(1.0, 2.0, None)),
            _report_case("B", "GREEN", ["GREEN"], latency_s=(None, None, None)),
        ]
    )
    analysis = analyse(report)

    # Only A's two timed runs reach the sample: [1.0, 2.0] — the ``None``s are excluded.
    assert analysis.latency_p50 == pytest.approx(1.0)
    assert analysis.latency_p95 == pytest.approx(2.0)


def test_a_report_where_every_run_errored_still_analyses() -> None:
    """A report whose every run errored (latency all ``None``) analyses, never raises (IN-04).

    WR-04 requires an errored suite to still produce a report: an all-``None`` latency sample
    is present-but-unmeasurable, so it analyses to ``0.0`` rather than aborting the analyser.
    """
    report = _report([_report_case("A", "GREEN", ["GREEN"] * 3, latency_s=(None, None, None))])
    analysis = analyse(report)

    assert analysis.latency_p50 == 0.0
    assert analysis.latency_p95 == 0.0


# --------------------------------------------- 4. report_digest reproducibility (D-08)


def test_report_digest_recomputes_and_detects_a_mutation() -> None:
    """The digest recomputes from the non-volatile content; a mutation changes it (D-08)."""
    report = _report([_report_case("A", "GREEN", ["GREEN"] * 3)])
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    assert compute_report_digest(sealed) == sealed.report_digest

    mutated_case = sealed.cases[0].model_copy(update={"outcomes": ["RED", "GREEN", "GREEN"]})
    mutated = sealed.model_copy(update={"cases": [mutated_case]})
    assert compute_report_digest(mutated) != sealed.report_digest


# ------------------------------- 5. generator idempotent + the report is the sole source


def test_generator_is_idempotent_and_the_report_is_the_sole_source() -> None:
    """Rendering twice is byte-identical and every written number comes from the report."""
    report = _report(
        [
            _report_case(
                "E-01",
                "GREEN",
                ["GREEN"] * 3,
                latency_s=(0.1, 0.2, 0.3),
                tokens_in=11,
                tokens_out=4,
            )
        ]
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})

    first = _EMIT.render_evals(_template_for(["E-01"]), sealed)
    second = _EMIT.render_evals(first, sealed)
    assert first == second, "the generator is not idempotent"

    # The §4 result cell equals the report's own ``passed`` value — not a hand-entered one.
    assert _cell(first, "| E-01 ", -2) == "\u2705"
    # The §3 measured cells equal the report's own totals.
    assert "in 11 · out 4 tokens" in first

    # A tampered report (digest does not recompute) is refused.
    tampered = sealed.model_copy(update={"report_digest": "deadbeef"})
    with pytest.raises(ValueError):
        _EMIT.validate_report(tampered)


# ------------------- 5b. deferral rate + declared-split calibration (D8-10, D8-13, D8-15)


def test_deferral_rate_and_declared_split_calibration_are_measured() -> None:
    """The deferral rate is derived from the report; calibration names its declared split."""
    report = _report(
        [
            _report_case(
                "D-1",
                "GREEN",
                ["ABSTAIN"] * 3,
                deferrals=[True] * 3,
                confidence_levels=["low"] * 3,
                confidence_satisfied=[1, 1, 1],
                passed=False,
            ),
            _report_case(
                "D-2",
                "GREEN",
                ["GREEN"] * 3,
                deferrals=[False] * 3,
                confidence_satisfied=[3, 3, 3],
            ),
            _report_case(
                "H-9",
                "ORANGE",
                ["ORANGE"] * 3,
                held_out=True,
                deferrals=[False] * 3,
                confidence_satisfied=[3, 3, 3],
            ),
        ]
    )
    analysis = analyse(report)

    # The deferral rate is derived SEPARATELY from the direction split (D8-10).
    assert analysis.deferral_count == 3
    assert analysis.deferral_runs == 9
    assert analysis.deferral_rate == pytest.approx(3 / 9)
    assert analysis.deferral_cases == ["D-1"]

    # The calibration split is declared by ``held_out`` with both sample sizes named (D8-13).
    calibration = analysis.calibration
    assert calibration.calibration_ids == ["D-1", "D-2"]
    assert calibration.held_out_ids == ["H-9"]
    assert calibration.n_calibration == 2
    assert calibration.n_held_out == 1
    assert "n_calibration=2" in calibration.small_sample_caveat
    assert "n_held_out=1" in calibration.small_sample_caveat

    # ECE is coarsely binned; risk–coverage is swept from the internal scalar only (D8-15, A2).
    assert calibration.ece_bins == 4
    assert 0.0 <= calibration.ece <= 1.0
    assert [point.threshold for point in calibration.risk_coverage] == [3, 1]
    assert all(isinstance(point, RiskCoveragePoint) for point in calibration.risk_coverage)

    # Rendering stays idempotent with the deferral/calibration facts present.
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    first = _EMIT.render_evals(_template_for(["D-1", "D-2", "H-9"]), sealed)
    second = _EMIT.render_evals(first, sealed)
    assert first == second

    # The generated §3 cells carry the measured deferral rate (a FRACTION) and the NAMED
    # sample sizes — no hand-entered figure (D8-10, D8-14, D8-15).
    assert _cell(first, "| Deferral rate ", -2) == "3/9"
    calibration_cell = _cell(first, "| Calibration (small-sample) ", -2)
    assert "n_calibration=2" in calibration_cell
    assert "n_held_out=1" in calibration_cell


# --------------------------- 5c. the nested default_factory contract (build shape)


def test_bare_models_and_a_report_without_analysis_construct() -> None:
    """A bare ``Calibration``/``Analysis`` and an analysis-less ``Report`` build cleanly."""
    assert Calibration().n_calibration == 0
    assert Analysis().calibration.ece_bins == 0
    assert ReportCase(case_id="X", expected="GREEN", runs=1).deferrals == []

    # The exact shape ``run_eval`` (runner.py:372) and the helpers use: a Report built
    # WITHOUT the ``analysis`` argument must instantiate without raising.
    report = Report(
        mode="offline",
        runs=1,
        cases_dir="evals/cases",
        provenance=_PROVENANCE,
        cases=[_report_case("X", "GREEN", ["GREEN"])],
        invariants=dict(_ALL_INVARIANTS),
        gate=GateResult(passed=True),
    )
    assert report.analysis.calibration.n_calibration == 0


# ------------------------------------------- 6. the declared failure is shown, not hidden


def test_declared_failure_is_shown_and_not_counted_as_a_pass() -> None:
    """E-09 is rendered failing (never a pass) and the under-triage is surfaced (D-04)."""
    report = _report(
        [_report_case("E-09", "ORANGE", ["GREEN"] * 3, declared_failure=True, passed=False)]
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    output = _EMIT.render_evals(_template_for(["E-09"]), sealed)

    assert _cell(output, "| E-09 ", -2) == "\u274c", "the declared failure was shown as a pass"
    # The dangerous direction is explicit, not hidden behind an average.
    assert "under-triage 3" in output


# ------------------- 7. the digest seals the deferral facts; a deferral renders visible (D8-14)


def test_report_digest_seals_the_per_case_deferral_facts() -> None:
    """Flipping a ``ReportCase.deferrals`` entry changes ``compute_report_digest`` (D8-14)."""
    report = _report(
        [_report_case("A", "GREEN", ["ABSTAIN"] * 3, deferrals=[True] * 3, passed=False)]
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    assert compute_report_digest(sealed) == sealed.report_digest

    # Mutating the per-run deferral facts is a change in the published safety behaviour.
    mutated_case = sealed.cases[0].model_copy(update={"deferrals": [False, True, True]})
    mutated = sealed.model_copy(update={"cases": [mutated_case]})
    assert compute_report_digest(mutated) != sealed.report_digest


def test_report_digest_seals_the_per_case_confidence_satisfied_facts() -> None:
    """Flipping a ``ReportCase.confidence_satisfied`` entry changes the digest (WR-05, D8-14).

    The published offline ECE and risk–coverage re-derive from this scalar, so a hand-edit of
    it must move ``report_digest`` — otherwise a tampered report would be published with a
    silently different calibration figure. This mirrors the deferral-digest test above.
    """
    report = _report([_report_case("A", "GREEN", ["GREEN"] * 3, confidence_satisfied=[3, 3, 3])])
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    assert compute_report_digest(sealed) == sealed.report_digest

    mutated_case = sealed.cases[0].model_copy(update={"confidence_satisfied": [1, 1, 1]})
    mutated = sealed.model_copy(update={"cases": [mutated_case]})
    assert compute_report_digest(mutated) != sealed.report_digest

    # The seal is load-bearing: the scalar is exactly what the published ECE re-derives from.
    assert analyse(mutated).calibration.ece != analyse(sealed).calibration.ece


def test_generator_renders_a_coverage_deferral_as_a_marker_not_a_failure() -> None:
    """An all-deferred failing case renders the deferral marker; a bare fail still renders ❌."""
    report = _report(
        [
            _report_case("E-01", "GREEN", ["ABSTAIN"] * 3, deferrals=[True] * 3, passed=False),
            _report_case("E-09", "ORANGE", ["GREEN"] * 3, declared_failure=True, passed=False),
        ]
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    output = _EMIT.render_evals(_template_for(["E-01", "E-09"]), sealed)

    assert _cell(output, "| E-01 ", -2) == "\u23f8 deferral", "a deferral read as a wrong answer"
    assert _cell(output, "| E-09 ", -2) == "\u274c", "a non-deferred failure stopped showing ❌"


def test_generator_derives_the_section_6_deferral_record_from_the_report() -> None:
    """The §6.1 record names the DERIVED moved cases and gate failures — never a hand-typed list.

    A case that reaches a terminal before the confidence check carries no deferral fact, so it
    must NOT be named however the report turned out (D8-11, D8-14, D8-16).
    """
    report = _report(
        [
            _report_case("D-1", "GREEN", ["ABSTAIN"] * 3, deferrals=[True] * 3, passed=False),
            _report_case("D-2", "GREEN", ["GREEN"] * 3, deferrals=[False] * 3),
        ]
    )
    report = report.model_copy(
        update={"gate": GateResult(passed=False, unexpected_failures=["D-2"])}
    )
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    output = _EMIT.render_evals(_template_for(["D-1", "D-2"]), sealed)

    marker_line = output.split("Moved cases")[1].splitlines()[0]
    assert "`D-1`" in marker_line, "the moved deferral case was not named from the report"
    assert "D-2" not in marker_line, "a non-deferred case was mis-labelled as a deferral"
    assert "3/6 reached-assess runs deferred" in output
    # The recorded gate failures are derived from the report's gate, not hard-typed.
    assert "Recorded, unfixed gate failures (this phase does not fix them): `D-2`." in output

    # The block is replaced in place, never duplicated (the generator is idempotent).
    again = _EMIT.render_evals(output, sealed)
    assert again == output
    assert output.count("<!-- BEGIN GENERATED: deferrals -->") == 1


# --------------------------- 8. the provenance seals the extraction schema (D11-02, T-11-03)


def test_provenance_seals_the_extraction_schema_hash() -> None:
    """``build_provenance`` seals the LIVE extraction schema through the ONE hashing helper.

    ``prompt_hash`` covers the ``EXTRACTION_PROMPT`` template only, so a ``Field(description=…)``
    changes the model INPUT without moving it (Pitfall 4). The provenance therefore also carries
    ``extraction_schema_hash`` — the hash the model was actually asked to fill.
    """
    provenance = build_provenance("offline")
    assert provenance.extraction_schema_hash == hash_tool_schema(
        ExtractionResult.model_json_schema()
    )


def test_report_digest_seals_the_extraction_schema_hash() -> None:
    """Changing the sealed extraction-schema hash moves ``compute_report_digest`` (T-11-03)."""
    report = _report([_report_case("A", "GREEN", ["GREEN"] * 3)])
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    assert compute_report_digest(sealed) == sealed.report_digest

    # A different extraction schema (a contract change) is a different sealed provenance.
    mutated_provenance = sealed.provenance.model_copy(
        update={"extraction_schema_hash": "a-different-schema"}
    )
    mutated = sealed.model_copy(update={"provenance": mutated_provenance})
    assert compute_report_digest(mutated) != sealed.report_digest, (
        "a changed extraction schema left the sealed report digest unmoved"
    )


def test_a_report_with_the_provenance_block_constructs_and_seals() -> None:
    """The additive provenance field does not break the hand-built report constructors.

    The two hand-built ``Provenance(...)`` helpers in the suite supply the new field, so an
    otherwise-identical report still constructs and its digest recomputes (no silent drift).
    """
    report = _report([_report_case("A", "GREEN", ["GREEN"] * 3)])
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})

    assert sealed.provenance.extraction_schema_hash == _PROVENANCE.extraction_schema_hash
    assert compute_report_digest(sealed) == sealed.report_digest


def test_a_report_written_before_the_provenance_field_still_validates() -> None:
    """A report written BEFORE ``extraction_schema_hash`` existed still validates (T-11-03, IN-03).

    ``Provenance.extraction_schema_hash`` defaults to the empty string and ``_digest_payload``
    dumps the provenance with ``exclude_defaults=True``, so an older report's ``report_digest``
    recomputes and it is left untouched until a re-run regenerates it. That property depends on a
    subtle mechanism and is otherwise untested: a future change to ``exclude_defaults`` (or a new
    defaulted field the pipeline does not always supply) would silently unseal every old report.
    """
    report = _report([_report_case("A", "GREEN", ["GREEN"] * 3)])
    # Simulate the on-disk report written BEFORE the field existed: its JSON has no
    # ``extraction_schema_hash`` key at all, so it validates to the empty default.
    payload = json.loads(report.model_dump_json())
    payload["provenance"].pop("extraction_schema_hash", None)
    legacy = Report.model_validate(payload)
    assert legacy.provenance.extraction_schema_hash == ""

    # The defaulted field is omitted from the sealed payload (so an old digest stays valid)...
    assert "extraction_schema_hash" not in _digest_payload(legacy)["provenance"]
    # ...while a report the pipeline produced supplies a real hash, which IS sealed.
    assert "extraction_schema_hash" in _digest_payload(report)["provenance"]

    # The legacy report's digest recomputes through the ONE sealing path (it is left untouched).
    sealed = legacy.model_copy(update={"report_digest": compute_report_digest(legacy)})
    assert compute_report_digest(sealed) == sealed.report_digest


# --------------------------- 9. the §4 row set reconciles with the report (D11-06, DOCS-05)


def _section_4_row_ids(lines: list[str]) -> set[str]:
    """The §4 row ids, read through the generator's OWN helpers (never re-implemented).

    Reusing ``_find_table``/``_table_end``/``_split_row`` means this guard cannot drift from
    the renderer's notion of the §4 table (DRY, D11-06).
    """
    start = _EMIT._find_table(lines, ["#", "Case"])
    assert start is not None, "EVALS.md is missing the §4 case table"
    end = _EMIT._table_end(lines, start)
    return {
        _EMIT._split_row(line)[0]
        for line in lines[start + 2 : end]
        if line.strip().startswith("|")
    }


def test_case_table_guard_raises_when_a_report_case_has_no_row() -> None:
    """The §4 row-set guard fails closed for a report case with no §4 row (D11-06, T-11-06).

    A newly-measured case (e.g. a held-out H-01/H-02) that has no §4 row must stop the
    generator, so the 14-vs-16 drift cannot silently return.
    """
    report = _report([_report_case("E-42", "GREEN", ["GREEN"] * 3)])
    with pytest.raises(ValueError, match="E-42"):
        _EMIT._assert_case_table_covers_report(_TEMPLATE.splitlines(), report)


def test_case_table_guard_raises_when_a_row_has_no_report_case() -> None:
    """The §4 row-set guard fails closed for a STALE §4 row with no report case (D11-06, WR-02).

    A row whose case is absent from the report (e.g. a case removed from ``evals/cases/`` while
    its hand-authored row remains) must stop the generator: otherwise the row keeps its previous
    ``Runs``/``Result`` cells and ``--check``/``--write`` exit 0, publishing a stale row. The
    guard is symmetric with the missing-row direction above.
    """
    report = _report([_report_case("E-01", "GREEN", ["GREEN"] * 3)])
    with pytest.raises(ValueError, match="E-09"):
        _EMIT._assert_case_table_covers_report(_TEMPLATE.splitlines(), report)


def test_committed_section_4_rows_equal_the_report_case_set() -> None:
    """The committed §4 row-id set equals the committed report's case-id set (D11-06).

    The report is the sole source (CONVENTIONS §1): the row count is the report's own case
    count, so §3's "16/16" and §4's rows can never disagree.
    """
    report = Report.model_validate_json(REPORT_PATH.read_text(encoding="utf-8"))
    lines = EVALS_PATH.read_text(encoding="utf-8").splitlines()
    row_ids = _section_4_row_ids(lines)

    assert row_ids == {case.case_id for case in report.cases}, "§4 rows and the report disagree"
    assert len(row_ids) == len(report.cases)


# ------------------- 10. the committed artefacts lock the honesty in (D11-07, D11-08)


def test_section_4_row_count_equals_the_report_case_count() -> None:
    """The §4 row count equals the report's own case count (no 14-vs-16 drift; D11-06)."""
    report = Report.model_validate_json(REPORT_PATH.read_text(encoding="utf-8"))
    lines = EVALS_PATH.read_text(encoding="utf-8").splitlines()
    assert len(_section_4_row_ids(lines)) == len(report.cases)


def test_declared_failure_stays_visible_and_is_not_a_bare_pass() -> None:
    """Every declared failure is present in EVALS.md and never rendered as a bare pass (D11-07).

    The report declares the failure; EVALS.md must show it. Both facts are read from the
    committed artefacts — no colour, count or case list is hard-coded (CONVENTIONS §1).
    """
    report = Report.model_validate_json(REPORT_PATH.read_text(encoding="utf-8"))
    evals_text = EVALS_PATH.read_text(encoding="utf-8")

    declared = {case.case_id for case in report.cases if case.declared_failure}
    assert declared, "the report declares no failure"
    for case_id in declared:
        assert case_id in evals_text, f"the declared failure {case_id} is not visible in EVALS.md"
        assert _cell(evals_text, f"| {case_id} ", -2) != "\u2705", (
            f"the declared failure {case_id} was rendered as a bare pass"
        )


def test_unfixed_gate_failures_appear_in_the_section_6_1_record() -> None:
    """Every case the gate names as an unfixed failure is visible in the §6.1 record (D11-07).

    The §6.1 block is DERIVED from ``report.gate``; this guard proves the derived record never
    silently drops a recorded failure (and is vacuous when the gate names none — the report,
    not the test, decides).
    """
    report = Report.model_validate_json(REPORT_PATH.read_text(encoding="utf-8"))
    evals_text = EVALS_PATH.read_text(encoding="utf-8")
    start = evals_text.index("<!-- BEGIN GENERATED: deferrals -->")
    end = evals_text.index("<!-- END GENERATED: deferrals -->")
    record = evals_text[start:end]

    for case_id in report.gate.unexpected_failures:
        assert case_id in record, (
            f"the recorded unfixed failure {case_id} is missing from the §6.1 record"
        )


def test_committed_report_is_a_real_run() -> None:
    """The published report is ``mode: real`` — the strongest evidence (D11-08)."""
    report = Report.model_validate_json(REPORT_PATH.read_text(encoding="utf-8"))
    assert report.mode == "real", "the published report is not a real measured run"
