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
DEFAULT_EVALS = REPO_ROOT / "EVALS.md"

# The generated source block, fenced by stable markers so a re-run replaces it in place.
_BEGIN = "<!-- BEGIN GENERATED: source -->"
_END = "<!-- END GENERATED: source -->"

# The generated §6.1 coverage-deferral record. Fenced so a re-run replaces it in place;
# anchored on the §6.1 heading so it can be inserted when first absent.
_DEFERRAL_BEGIN = "<!-- BEGIN GENERATED: deferrals -->"
_DEFERRAL_END = "<!-- END GENERATED: deferrals -->"
_DEFERRAL_ANCHOR = "### 6.1 Coverage deferrals"

_PASS = "\u2705"  # ✅
_FAIL = "\u274c"  # ❌
# The §4 marker for a coverage deferral: an all-deferred case that missed its expected colour
# is reduced COVERAGE, not an answered-and-wrong run, so it is never rendered as a bare ❌
# (D8-11, D8-16, T-08-10). Derived from ``ReportCase.deferrals`` — never hand-entered.
_DEFERRAL = "\u23f8 deferral"  # ⏸ deferral


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
    return {
        "Colour accuracy": f"{analysis.colour_correct}/{analysis.colour_runs} ({accuracy})",
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
            else:
                cells[result_index] = _PASS if case.passed else _FAIL
        rows.append(_render_row(cells))
    return lines[:start] + rows + lines[end:]


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


def render_evals(template: str, report: Report) -> str:
    """Render *template* (the current ``EVALS.md``) with the report's measured cells.

    The narrative is preserved verbatim — only the result cells and the generated source
    block are rewritten. ``render_evals`` is idempotent: feeding its own output back
    produces byte-identical text. It calls the ONE analyser, so it never invents a number.
    """
    analysis = analyse(report)
    lines = template.splitlines()
    lines = _render_metrics_table(lines, report, analysis)
    lines = _render_source_block(lines, report)
    lines = _render_case_table(lines, report)
    lines = _render_invariant_table(lines, report)
    lines = _render_deferral_block(lines, report, analysis)
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
    current = args.evals.read_text(encoding="utf-8")
    generated = render_evals(current, report)

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
