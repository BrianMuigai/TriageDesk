"""Render the measured result cells of ``EVALS.md`` from the ONE report (D-08, Pitfall 16).

``EVALS.md`` is the published, auditable document: its narrative and its
planned-vs-measured framing are hand-written, but every *number* and *result marker* is
generated here, strictly from the report — so no figure is ever retyped by hand and a
fabricated number cannot enter the document (T-04-16, Pitfall 16).

What the generator writes (and nothing else):

* the §3 reliability-metrics table gains a ``Measured`` column (colour accuracy, the
  under/over direction split, the gate-delivery count, the invariant/stability counts,
  latency p50/p95, cost, the deferral rate and the small-sample calibration);
* the §4 per-case ``Runs (3×)`` and ``Result`` cells — an all-deferred failing case renders
  the deferral marker, never a bare failure (a coverage deferral is reduced coverage);
* the §5 invariant ``Result`` cells;
* the §6.1 coverage-deferral record — the moved case ids, the deferral fraction and the
  recorded unfixed gate failures, all DERIVED from the report so the narrative stays true
  whatever the run produces (never a hand-typed case list);
* a generated source line naming the report and its ``report_digest`` so each figure is
  traceable to the raw artefact.

The generator is idempotent (running it twice on the same report is byte-identical) and
refuses a report whose ``report_digest`` does not recompute, so a hand-edited report is
never silently published (T-04-18). It calls the ONE analyser
(:func:`triagedesk.evals.analysis.analyse`) — it never invents a number.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from triagedesk.evals.analysis import analyse
from triagedesk.evals.invariants import INV_1, INVARIANT_IDS
from triagedesk.evals.report import Analysis, Report, ReportCase, compute_report_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "evals" / "results" / "report.json"
DEFAULT_BASELINE = REPO_ROOT / "evals" / "results" / "report.baseline.json"
# The §3.3 comparison pair. When the adaptive arm was measured on a declared subset it lives in
# its own sealed report; the documented one-liner must still be able to check EVALS.md, so the
# pair is resolved from these fixed paths rather than only from ``--report``.
DEFAULT_COMPARISON_ADAPTIVE = REPO_ROOT / "evals" / "results" / "report.adaptive.json"
DEFAULT_EVALS = REPO_ROOT / "EVALS.md"

# The generated source block, fenced by stable markers so a re-run replaces it in place.
_BEGIN = "<!-- BEGIN GENERATED: source -->"
_END = "<!-- END GENERATED: source -->"

# The generated §3.3 adaptive-vs-baseline comparison (MEAS-02). Fenced and anchored on the
# hand-written heading so it can be inserted when first absent and refreshed in place after.
_CMP_BEGIN = "<!-- BEGIN GENERATED: comparison -->"
_CMP_END = "<!-- END GENERATED: comparison -->"
_CMP_ANCHOR = "**Measured arms and delta.**"

# The generated §6.1 coverage-deferral record. Fenced so a re-run replaces it in place;
# anchored on the §6.1 heading so it can be inserted when first absent.
_DEFERRAL_BEGIN = "<!-- BEGIN GENERATED: deferrals -->"
_DEFERRAL_END = "<!-- END GENERATED: deferrals -->"
_DEFERRAL_ANCHOR = "### 6.1 Coverage: delivered, clarified, deferred"

_PASS = "\u2705"  # ✅
_FAIL = "\u274c"  # ❌
# The §4 marker for a coverage deferral: an all-deferred case that missed its expected colour
# is reduced COVERAGE, not an answered-and-wrong run, so it is never rendered as a bare ❌
# (D8-11, D8-16, T-08-10). Derived from ``ReportCase.deferrals`` — never hand-entered.
_DEFERRAL = "\u23f8 deferral"  # ⏸ deferral
# A bounded clarification that missed its expected outcome is reduced coverage too — never
# an answered-and-wrong run, and never folded into the deferral count (COV-07).
_CLARIFY = "\u23f8 clarify"  # ⏸ clarify


def _split_row(line: str) -> list[str]:
    """Split one markdown table row into its trimmed cell values."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _render_row(cells: list[str]) -> str:
    """Render a cell list back to a canonical markdown table row."""
    return "| " + " | ".join(cells) + " |"


def _find_table(lines: list[str], prefix_cells: list[str]) -> int | None:
    """Index of the table header whose leading cells equal *prefix_cells* (or ``None``)."""
    for index, line in enumerate(lines):
        if line.strip().startswith("|"):
            cells = _split_row(line)
            if cells[: len(prefix_cells)] == prefix_cells:
                return index
    return None


def _table_end(lines: list[str], start: int) -> int:
    """Index just past the contiguous run of table rows starting at *start*."""
    end = start
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    return end


def _pad(cells: list[str], width: int) -> list[str]:
    """Right-pad *cells* with empty strings up to *width*."""
    return cells + [""] * (width - len(cells))


def _measured_metrics(report: Report, analysis: Analysis) -> dict[str, str]:
    """The measured value for each §3 metric row, from the report + analysis."""
    total = len(report.cases)
    citation_ok = sum(
        1 for case in report.cases if case.invariants.get(INV_1, False)
    )
    invariants_ok = sum(1 for held in report.invariants.values() if held)
    accuracy = f"{analysis.colour_accuracy * 100:.1f}%"
    # The colour denominator deliberately EXCLUDES terminal outcomes (D-03) and the gate can
    # still fail on other cases, so the cell names both facts: a bare "100.0%" beside a failing
    # gate reads as "nothing failed" (IN-03). ``failed`` is the report's OWN gate verdict.
    failed = len(report.gate.unexpected_failures)
    gate_status = "gate passes" if report.gate.passed else f"{failed} case(s) failing the gate"
    return {
        "Colour accuracy": (
            f"{analysis.colour_correct}/{analysis.colour_runs} of colour-expected runs correct "
            f"({accuracy}); {gate_status}"
        ),
        "Error direction": (
            f"under-triage {analysis.under_triage_count} · "
            f"over-triage {analysis.over_triage_count}"
        ),
        "Citation completeness": f"{citation_ok}/{total} cases",
        "Gate delivery": f"{total - len(analysis.aborted_cases)}/{total} cases",
        "Safety invariants": f"{invariants_ok}/{len(INVARIANT_IDS)}",
        "Colour stability": f"{len(analysis.colour_stable_cases)}/{total} cases",
        "Field stability": f"{len(analysis.field_stable_cases)}/{total} cases",
        "Latency": f"p50 {analysis.latency_p50:.2f} s · p95 {analysis.latency_p95:.2f} s",
        "Cost per run": f"in {analysis.tokens_in} · out {analysis.tokens_out} tokens",
        # The deferral rate is a FRACTION, never a percentage: a coverage deferral is reduced
        # coverage, not a probability or a risk figure (D8-04, D8-10).
        "Deferral rate": f"{analysis.deferral_count}/{analysis.deferral_runs}",
        # Coverage vs clarification (COV-07): a delivered colour and a bounded question are
        # different outcomes and are never folded together.
        "Coverage rate": f"{analysis.delivered_runs}/{analysis.deferral_runs}",
        "Clarification rate": f"{analysis.clarification_count}/{analysis.deferral_runs}",
        # ECE + risk–coverage with both sample sizes NAMED; it is a small-sample measure,
        # never a validated calibrated probability (D8-13, D8-15).
        "Calibration (small-sample)": (
            f"ECE {analysis.calibration.ece:.3f} · "
            f"n_calibration={analysis.calibration.n_calibration} · "
            f"n_held_out={analysis.calibration.n_held_out}"
        ),
    }


def _render_metrics_table(lines: list[str], report: Report, analysis: Analysis) -> list[str]:
    """Add (or refresh) the §3 ``Measured`` column from the report (EVAL-04/05)."""
    start = _find_table(lines, ["Metric", "Definition"])
    if start is None:
        return lines
    end = _table_end(lines, start)
    header = _split_row(lines[start])
    if "Measured" not in header:
        header = header + ["Measured"]
    measured_index = header.index("Measured")
    separator = _split_row(lines[start + 1])
    separator = separator + ["---"] * (len(header) - len(separator))
    measured = _measured_metrics(report, analysis)

    rows = [_render_row(header), _render_row(separator)]
    for line in lines[start + 2 : end]:
        cells = _pad(_split_row(line), len(header))
        cells[measured_index] = measured.get(cells[0], cells[measured_index])
        rows.append(_render_row(cells))
    return lines[:start] + rows + lines[end:]


def _shows_deferral_marker(case: ReportCase) -> bool:
    """True when *case* is a coverage deferral that missed its expected outcome.

    The ONE predicate behind both the §4 result cell and the §6.1 record (DRY): an
    all-deferred FAILING case reads as reduced coverage, not a wrong answer (D8-11,
    D8-16). A case that passed keeps its ``✅`` — deferring is not itself a failure.
    """
    return (
        not case.passed
        and bool(case.deferrals)
        and all(deferral is True for deferral in case.deferrals)
    )


def _shows_clarify_marker(case: ReportCase) -> bool:
    """True when *case* asked its bounded question on EVERY run and so missed its outcome.

    A clarification is reduced coverage, not a wrong answer (COV-07): the case delivered no
    colour by design. It is marked apart from a deferral so the two reduced-coverage forms
    are never conflated.
    """
    return (
        not case.passed
        and bool(case.outcomes)
        and all(outcome == "CLARIFY" for outcome in case.outcomes)
    )


def _render_case_table(lines: list[str], report: Report) -> list[str]:
    """Fill the §4 per-case ``Runs (3×)`` and ``Result`` cells from the report."""
    start = _find_table(lines, ["#", "Case"])
    if start is None:
        return lines
    end = _table_end(lines, start)
    header = _split_row(lines[start])
    runs_index = header.index("Runs (3×)")
    result_index = header.index("Result")
    by_id = {case.case_id: case for case in report.cases}

    rows = [_render_row(header), lines[start + 1]]
    for line in lines[start + 2 : end]:
        cells = _pad(_split_row(line), len(header))
        case = by_id.get(cells[0])
        if case is not None:
            cells[runs_index] = str(report.runs)
            # An all-deferred FAILING case reads as a coverage deferral, not a wrong answer;
            # a passed case (e.g. an offline RECHECK) keeps its ✅ (D8-11, T-08-10).
            if _shows_deferral_marker(case):
                cells[result_index] = _DEFERRAL
            elif _shows_clarify_marker(case):
                cells[result_index] = _CLARIFY
            else:
                cells[result_index] = _PASS if case.passed else _FAIL
        rows.append(_render_row(cells))
    return lines[:start] + rows + lines[end:]


def _assert_case_table_covers_report(lines: list[str], report: Report) -> None:
    """Refuse to publish unless the §4 row set EQUALS the report's case set (D11-06, T-11-06).

    The §4 case table is hand-authored narrative; :func:`_render_case_table` only fills the
    result cells of rows already present, so nothing forces the two sets to agree. The guard is
    therefore **bidirectional**, and fails closed in both directions (a ``ValueError`` naming the
    offending ids, the same posture as :func:`validate_report`):

    * a report case with no §4 row — a newly-measured case (e.g. a held-out H-01/H-02) would be
      published unlisted (the real 14-vs-16 drift this guard closes);
    * a §4 row with no report case — a stale row (e.g. a case removed from ``evals/cases/`` while
      its hand-authored row remains) would keep its previous ``Runs``/``Result`` cells and pass
      ``--check`` (WR-02).

    Enforcing set equality means neither drift can reach the published document.
    """
    start = _find_table(lines, ["#", "Case"])
    if start is None:
        raise ValueError("EVALS.md is missing the §4 case table; refusing to publish")
    end = _table_end(lines, start)
    row_ids = {
        _split_row(line)[0]
        for line in lines[start + 2 : end]
        if line.strip().startswith("|")
    }
    report_ids = {case.case_id for case in report.cases}
    missing = report_ids - row_ids
    if missing:
        raise ValueError(
            f"EVALS.md §4 is missing rows for report cases: {sorted(missing)} "
            "(every measured case must be listed; D11-06)"
        )
    extra = row_ids - report_ids
    if extra:
        raise ValueError(
            f"EVALS.md §4 has rows for cases not in the report: {sorted(extra)} "
            "(a stale row must not be published; D11-06)"
        )


def _render_invariant_table(lines: list[str], report: Report) -> list[str]:
    """Fill the §5 invariant ``Result`` cells from the report's aggregate verdicts."""
    start = _find_table(lines, ["Invariant", "Check"])
    if start is None:
        return lines
    end = _table_end(lines, start)
    header = _split_row(lines[start])
    result_index = header.index("Result")

    rows = [_render_row(header), lines[start + 1]]
    for line in lines[start + 2 : end]:
        cells = _pad(_split_row(line), len(header))
        held = report.invariants.get(cells[0])
        if held is not None:
            cells[result_index] = _PASS if held else _FAIL
        rows.append(_render_row(cells))
    return lines[:start] + rows + lines[end:]


def _render_source_block(lines: list[str], report: Report) -> list[str]:
    """Insert (or refresh) the generated source line naming the report and its digest."""
    body = [
        _BEGIN,
        f"> **Measured source:** `evals/results/report.json` · mode `{report.mode}` · "
        f"`report_digest: {report.report_digest}` · {report.runs} runs/case.",
        _END,
    ]
    if _BEGIN in lines:
        start = lines.index(_BEGIN)
        end = lines.index(_END)
        return lines[:start] + body + lines[end + 1 :]
    metrics_start = _find_table(lines, ["Metric", "Definition"])
    if metrics_start is None:
        return lines
    end = _table_end(lines, metrics_start)
    return lines[:end] + [""] + body + lines[end:]


def _render_deferral_block(lines: list[str], report: Report, analysis: Analysis) -> list[str]:
    """Insert (or refresh) the §6.1 derived coverage-deferral record.

    Every fact is DERIVED from the report — the moved case ids from the same predicate the
    §4 table uses, the deferral fraction from the analyser, and the recorded unfixed gate
    failures from ``report.gate`` — so the narrative cannot drift from what was measured and
    no case list is ever hand-typed (D8-11, D8-14, D8-16). A case that reached a terminal
    before the confidence check simply never appears here: it carries no deferral fact.
    """
    marker_cases = [case.case_id for case in report.cases if _shows_deferral_marker(case)]
    failed = list(report.gate.unexpected_failures)
    body = [
        _DEFERRAL_BEGIN,
        f"> **Measured coverage deferrals:** {analysis.deferral_count}/"
        f"{analysis.deferral_runs} reached-assess runs deferred. Moved cases rendering the "
        f"§4 `{_DEFERRAL}` marker: `{', '.join(marker_cases) or 'none'}`.",
    ]
    if failed:
        body.append(
            "> Recorded, unfixed gate failures (this phase does not fix them): "
            f"`{', '.join(failed)}`."
        )
    clarified = [case.case_id for case in report.cases if _shows_clarify_marker(case)]
    body.append(
        "> **Measured clarifications:** "
        f"{analysis.clarification_count}/{analysis.deferral_runs} reached-assess runs asked a "
        f"bounded question. Cases rendering the §4 `{_CLARIFY}` marker: "
        f"`{', '.join(clarified) or 'none'}`."
    )
    body.append(_DEFERRAL_END)
    if _DEFERRAL_BEGIN in lines:
        start = lines.index(_DEFERRAL_BEGIN)
        end = lines.index(_DEFERRAL_END)
        return lines[:start] + body + lines[end + 1 :]
    anchor = next(
        (index for index, line in enumerate(lines) if line.startswith(_DEFERRAL_ANCHOR)),
        None,
    )
    if anchor is None:
        return lines
    return lines[: anchor + 1] + [""] + body + lines[anchor + 1 :]


def _arm_label(report: Report) -> str:
    """The arm's honest name, from the report's own ``planner`` flag (MEAS-02)."""
    return "adaptive arm `planner=True`" if report.planner else "baseline arm `planner=False`"


def _arm_cells(report: Report, analysis: Analysis) -> dict[str, str]:
    """The comparison cells for one arm — every value read from the sealed report (MEAS-02).

    ``Colour`` is correct/runs, not a bare percentage: the denominator is the colour-expected
    runs, and the gate verdict is published separately. ``Steps`` and ``Overrides`` come from
    the ``adaptive`` block the analyser derived from the per-run facts, so a baseline report
    (no planner) reads ``0.0`` and ``0/0`` honestly rather than being blank.
    """
    adaptive = analysis.adaptive
    overrides = round(adaptive.guard_override_rate * adaptive.runs_with_investigation)
    return {
        "Colour correctness": f"{analysis.colour_correct}/{analysis.colour_runs}",
        "Coverage (delivered/reached)": (
            f"{analysis.delivered_runs}/{analysis.deferral_runs}"
        ),
        "Clarified": str(analysis.clarification_count),
        "Deferred": str(analysis.deferral_count),
        "Mean steps": f"{adaptive.mean_steps:.1f}",
        "Guard overrides": (
            f"{overrides}/{adaptive.runs_with_investigation}"
            if adaptive.runs_with_investigation
            else "0/0"
        ),
        "Latency p50 (s)": f"{analysis.latency_p50:.2f}",
        "Latency p95 (s)": f"{analysis.latency_p95:.2f}",
    }


def _delta(metric: str, adaptive: dict[str, str], baseline: dict[str, str]) -> str:
    """The signed difference for one metric, formatted for its unit (never a bare ``+``).

    ``Colour correctness`` is a fraction difference in percentage points; ``Coverage`` is the
    delivered-run difference; ``Mean steps`` and the latencies are numeric differences. The
    delta is stated even when it is zero or negative — that is the point of the measurement
    (MEAS-02).
    """
    if metric == "Colour correctness":
        def rate(cells: dict[str, str]) -> float:
            correct, _, runs = cells[metric].partition("/")
            return (int(correct) / int(runs) * 100.0) if int(runs) else 0.0

        return f"{rate(adaptive) - rate(baseline):+.1f} pp"
    if metric == "Coverage (delivered/reached)":
        def delivered(cells: dict[str, str]) -> int:
            return int(cells[metric].partition("/")[0])

        return f"{delivered(adaptive) - delivered(baseline):+d} runs"
    if metric == "Guard overrides":
        def ratio(cells: dict[str, str]) -> float:
            count, _, runs = cells[metric].partition("/")
            return (int(count) / int(runs) * 100.0) if int(runs) else 0.0

        return f"{ratio(adaptive) - ratio(baseline):+.1f} pp"
    return f"{float(adaptive[metric]) - float(baseline[metric]):+.2f}"


def _render_comparison_block(
    lines: list[str], report: Report, baseline: Report | None
) -> list[str]:
    """Insert (or refresh) the §3.3 adaptive-vs-baseline comparison from BOTH reports.

    The section is generated in exactly one place and every cell is derived from the two
    sealed reports through the ONE analyser (DRY). The arm labels carry the report's own
    ``planner`` flag, so a baseline report can never be presented as the adaptive arm.
    """
    if baseline is None:
        return lines
    adaptive_cells = _arm_cells(report, analyse(report))
    baseline_cells = _arm_cells(baseline, analyse(baseline))
    body = [
        _CMP_BEGIN,
        f"> **Measured comparison:** {_arm_label(report)} (mode `{report.mode}`) vs "
        f"{_arm_label(baseline)} (mode `{baseline.mode}`), same {len(report.cases)} cases × "
        f"{report.runs} run(s).",
        "",
        "| Metric | Adaptive | Baseline | Delta |",
        "| --- | --- | --- | --- |",
    ]
    for metric in adaptive_cells:
        body.append(
            _render_row(
                [
                    metric,
                    adaptive_cells[metric],
                    baseline_cells[metric],
                    _delta(metric, adaptive_cells, baseline_cells),
                ]
            )
        )
    body.append(_CMP_END)
    if _CMP_BEGIN in lines:
        start = lines.index(_CMP_BEGIN)
        end = lines.index(_CMP_END)
        return lines[:start] + body + lines[end + 1 :]
    anchor = next(
        (index for index, line in enumerate(lines) if line.startswith(_CMP_ANCHOR)),
        None,
    )
    if anchor is None:
        return lines
    return lines[: anchor + 1] + [""] + body + lines[anchor + 1 :]


def render_evals(
    template: str,
    report: Report,
    baseline: Report | None = None,
    adaptive: Report | None = None,
) -> str:
    """Render *template* (the current ``EVALS.md``) with the report's measured cells.

    The narrative is preserved verbatim — only the result cells and the generated source
    block are rewritten. ``render_evals`` is idempotent: feeding its own output back
    produces byte-identical text. It calls the ONE analyser, so it never invents a number.

    ``baseline`` is the second arm's sealed report (MEAS-02). When given, the §3.3
    adaptive-vs-baseline comparison is generated from both reports; when ``None`` the
    section is left untouched, so every pre-Phase-24 caller keeps its exact behaviour.
    """
    analysis = analyse(report)
    lines = template.splitlines()
    lines = _render_metrics_table(lines, report, analysis)
    lines = _render_source_block(lines, report)
    lines = _render_case_table(lines, report)
    _assert_case_table_covers_report(lines, report)
    lines = _render_invariant_table(lines, report)
    lines = _render_deferral_block(lines, report, analysis)
    lines = _render_comparison_block(lines, adaptive or report, baseline)
    return "\n".join(lines) + "\n"


def validate_report(report: Report) -> None:
    """Refuse a report whose ``report_digest`` does not recompute (T-04-18)."""
    if report.report_digest != compute_report_digest(report):
        raise ValueError(
            "report_digest does not recompute from the report's non-volatile content; "
            "refusing to publish a tampered report (D-08, T-04-18)"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render EVALS.md result cells from a report.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="report JSON path")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="the baseline arm's report (default: evals/results/report.baseline.json)",
    )
    parser.add_argument(
        "--comparison-adaptive",
        type=Path,
        default=None,
        help=(
            "the adaptive arm's report for the §3.3 comparison, when it differs from the "
            "primary report (default: the --report file)"
        ),
    )
    parser.add_argument("--evals", type=Path, default=DEFAULT_EVALS, help="EVALS.md path")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when EVALS.md differs from the generated output",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="write the generated output to EVALS.md (idempotent)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse *argv*, validate the report, and render / check / write ``EVALS.md``."""
    args = _build_parser().parse_args(argv)
    report = Report.model_validate_json(args.report.read_text(encoding="utf-8"))
    validate_report(report)
    if not args.baseline.is_file():
        print(
            f"baseline report missing: {args.baseline}\n"
            "run the baseline arm first: uv run triagedesk eval --cases evals/cases "
            "--runs 3 --report evals/results/report.baseline.json --no-planner",
            file=sys.stderr,
        )
        return 2
    baseline = Report.model_validate_json(args.baseline.read_text(encoding="utf-8"))
    validate_report(baseline)
    adaptive = None
    comparison_path = args.comparison_adaptive
    if comparison_path is None and DEFAULT_COMPARISON_ADAPTIVE.is_file():
        comparison_path = DEFAULT_COMPARISON_ADAPTIVE
    if comparison_path is not None:
        adaptive = Report.model_validate_json(
            comparison_path.read_text(encoding="utf-8")
        )
        validate_report(adaptive)
    current = args.evals.read_text(encoding="utf-8")
    generated = render_evals(current, report, baseline, adaptive)

    if args.check:
        if generated != current:
            print(
                f"{args.evals} is out of date; re-run with --write (report "
                f"{report.report_digest[:16]})",
                file=sys.stderr,
            )
            return 1
        print(f"{args.evals} is up to date (report {report.report_digest[:16]})")
        return 0
    if args.write:
        if generated != current:
            args.evals.write_text(generated, encoding="utf-8")
            print(f"wrote {args.evals} (report {report.report_digest[:16]})")
        else:
            print(f"{args.evals} already matches the report; no change")
        return 0
    sys.stdout.write(generated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
