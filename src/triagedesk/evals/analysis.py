"""The ONE aggregate analyser over a measured eval report (EVAL-04, EVAL-05, D-03).

The analyser turns a :class:`~triagedesk.evals.report.Report` into the safety-relevant
aggregate block the report carries and ``EVALS.md`` publishes:

* the error DIRECTION split — **under-triage and over-triage reported SEPARATELY**, with
  the offending case ids and run counts, never collapsed into one symmetric accuracy
  figure (D-03, Pitfall 8);
* the terminal-outcome correctness counts (RECOVER/ABSTAIN/RECHECK), which are
  deliberately EXCLUDED from the colour direction split and reported on their own;
* the abort signal (``ABORT`` — a run that stopped at ``END`` without a handover card),
  reported on its own so a fail-closed run is visible and never read as a colour pass;
* the two stability summaries kept distinct (colour stability vs field stability, D-02);
* the latency percentiles (p50/p95) and the token totals (EVAL-05, D-08).

The colour urgency ordering is derived from the loaded substrate
(``core.rules.get_tews().tews_to_colour`` — each band's lower TEWS bound), so a new
colour or band is a data edit, not a code edit (CONVENTIONS §1). The analyser is pure
over the report: it reuses the per-case facts the run already computed and never re-runs
the graph or re-reads the model.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from triagedesk.core.confidence import COMPONENT_COUNT
from triagedesk.core.rules import get_tews
from triagedesk.evals.case import ABORT_OUTCOME, TERMINAL_OUTCOMES
from triagedesk.evals.report import Analysis, Calibration, Report, ReportCase, RiskCoveragePoint

# The divisor that normalises the per-run ordinal scalar for the offline ECE ONLY is read
# from its ONE owner (``core.confidence``), never restated as a literal: the scalar never
# leaves ``evals/`` and is never a clinical figure (D8-04, A2), and a change to the signal's
# component arity cannot silently mis-normalise a published figure (CONVENTIONS §1).

# The coarse fixed bin count for the small-sample ECE (D8-15): a ~14-case calibration split
# cannot support fine binning, so the bins are deliberately coarse and the sample size is named.
_ECE_BINS = 4


def colour_urgency() -> dict[str, int]:
    """The colour urgency ordering from the loaded substrate (the ONE authority).

    The rank is the colour band's lower TEWS bound — the SAME data-derived ordering the
    scorer and the discriminator override use, so a new colour or band is a data edit,
    not a code edit (CONVENTIONS §1). A higher rank is more urgent.
    """
    return {
        band.colour: band.min if band.min is not None else 0
        for band in get_tews().tews_to_colour
    }


def _percentile(values: Sequence[float], fraction: float) -> float:
    """The nearest-rank percentile of *values* at *fraction* (no interpolation).

    *fraction* is a proportion in ``(0, 1]`` (e.g. ``0.5`` for the median, ``0.95`` for
    the tail). Nearest-rank keeps the reported figure an actual measured sample rather
    than an interpolated one.
    """
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _risk_coverage(cases: Sequence[ReportCase]) -> list[RiskCoveragePoint]:
    """Sweep the deterministic rank into a risk–coverage curve (D8-13).

    Each measured run of *cases* that reached ``assess`` contributes its ordinal scalar
    (``confidence_satisfied``) and whether it was correct (``outcome == expected``). The
    sweep is over the DISTINCT observed scalars, descending: ``coverage`` is the fraction of
    runs at or above the threshold and ``risk`` the error rate among them. It ranks the
    deterministic signal — never a probability (D8-04).
    """
    runs = [
        (satisfied, outcome != case.expected)
        for case in cases
        for satisfied, outcome in zip(case.confidence_satisfied, case.outcomes, strict=False)
        if satisfied is not None
    ]
    if not runs:
        return []
    total = len(runs)
    points: list[RiskCoveragePoint] = []
    for threshold in sorted({satisfied for satisfied, _ in runs}, reverse=True):
        selected = [error for satisfied, error in runs if satisfied >= threshold]
        points.append(
            RiskCoveragePoint(
                threshold=threshold,
                coverage=len(selected) / total,
                risk=(sum(selected) / len(selected)) if selected else 0.0,
            )
        )
    return points


def _expected_calibration_error(cases: Sequence[ReportCase]) -> float:
    """The offline ECE over the calibration split, coarsely binned (D8-15).

    The predicted value is the internal ordinal scalar normalised by the component count; the
    actual value is the empirical correctness (``outcome == expected``). It is computed ONLY
    inside the offline analyser — the scalar is never emitted by a tool or a node, and the ECE
    is never presented as a validated calibrated probability (D8-04, A2). Returns ``0.0`` when
    the split carries no measured scalar.
    """
    samples = [
        (satisfied / COMPONENT_COUNT, outcome == case.expected)
        for case in cases
        for satisfied, outcome in zip(case.confidence_satisfied, case.outcomes, strict=False)
        if satisfied is not None and outcome is not None
    ]
    if not samples:
        return 0.0
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(_ECE_BINS)]
    for predicted, correct in samples:
        index = min(int(predicted * _ECE_BINS), _ECE_BINS - 1)
        buckets[index].append((predicted, correct))
    total = len(samples)
    ece = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        mean_predicted = sum(predicted for predicted, _ in bucket) / len(bucket)
        mean_correct = sum(1 for _, correct in bucket if correct) / len(bucket)
        ece += (len(bucket) / total) * abs(mean_predicted - mean_correct)
    return ece


def _calibration(cases: Sequence[ReportCase]) -> Calibration:
    """Build the declared-split calibration block from the report (D8-13, D8-15).

    The split is declared by the existing ``held_out`` flag: the calibration split is the
    ``held_out=False`` cases (where the D8-09 threshold is justified) and the held-out split
    the ``held_out=True`` cases (which bound the declared failure). Both ``n``s are named and
    the small-sample caveat states them explicitly — a 2-case held-out split is a declared
    bound, not a validated figure.
    """
    calibration_cases = [case for case in cases if not case.held_out]
    held_out_cases = [case for case in cases if case.held_out]
    caveat = (
        f"small-sample measure: n_calibration={len(calibration_cases)}, "
        f"n_held_out={len(held_out_cases)}; not a validated calibrated probability (D8-15)"
    )
    return Calibration(
        calibration_ids=[case.case_id for case in calibration_cases],
        held_out_ids=[case.case_id for case in held_out_cases],
        n_calibration=len(calibration_cases),
        n_held_out=len(held_out_cases),
        risk_coverage=_risk_coverage(calibration_cases),
        ece=_expected_calibration_error(calibration_cases),
        ece_bins=_ECE_BINS,
        small_sample_caveat=caveat,
    )


def analyse(report: Report, *, urgency: Mapping[str, int] | None = None) -> Analysis:
    """Aggregate *report* into the safety-relevant analysis block (EVAL-04, EVAL-05).

    ``urgency`` overrides the colour ordering (a test seam that proves the direction is
    data-derived, not hard-coded); the default reads the loaded substrate. The function
    is pure over the report — it never re-runs the graph or re-reads the model.

    Raises ``ValueError`` when the report carries no cases or no latency samples: the
    analysis cannot be produced from a report that omits the measured cost (EVAL-05).
    """
    ranks = dict(urgency) if urgency is not None else colour_urgency()
    cases = report.cases
    if not cases:
        raise ValueError("cannot analyse a report with no cases")
    latency = [sample for case in cases for sample in case.latency_s]
    if not latency:
        raise ValueError("cannot analyse a report with no latency samples")

    terminals = set(TERMINAL_OUTCOMES)
    # The most urgent colour is the substrate's own — the top of the loaded ordering,
    # never a re-declared "RED" literal (CONVENTIONS §1).
    most_urgent = max(ranks, key=lambda colour: ranks[colour]) if ranks else ""

    under_cases: list[str] = []
    over_cases: list[str] = []
    under_runs = 0
    over_runs = 0
    colour_runs = 0
    colour_correct = 0
    terminal_runs = 0
    terminal_correct = 0
    terminal_counts: dict[str, int] = {}
    terminal_misses: list[str] = []
    aborted_cases: list[str] = []
    aborted_runs = 0
    colour_stable: list[str] = []
    colour_unstable: list[str] = []
    field_stable: list[str] = []
    field_unstable: list[str] = []
    red_runs = 0
    red_misses = 0
    red_miss_cases: list[str] = []
    deferral_count = 0
    deferral_runs = 0
    deferral_cases: list[str] = []

    for case in cases:
        (colour_stable if case.colour_stable else colour_unstable).append(case.case_id)
        (field_stable if case.field_stable else field_unstable).append(case.case_id)

        # The coverage deferral is tallied SEPARATELY from the direction split (D8-10): a
        # deferral is reduced coverage, not an answered-but-wrong run, so a `False`/`None`
        # flag is a delivered run and a `True` flag a deferral (never folded together).
        if any(flag is True for flag in case.deferrals):
            deferral_cases.append(case.case_id)
        for flag in case.deferrals:
            if flag is not None:
                deferral_runs += 1
                if flag:
                    deferral_count += 1

        expected_is_colour = case.expected in ranks
        if expected_is_colour and case.expected == most_urgent:
            red_runs += len(case.outcomes)

        saw_under = False
        saw_over = False
        for outcome in case.outcomes:
            if outcome is None:
                continue
            if outcome == ABORT_OUTCOME:
                # A card-less END is reported on its own — never folded into the
                # under/over direction split, the colour accuracy, or a terminal miss.
                aborted_runs += 1
                if case.case_id not in aborted_cases:
                    aborted_cases.append(case.case_id)
                continue
            if outcome in terminals:
                terminal_counts[outcome] = terminal_counts.get(outcome, 0) + 1
                if not expected_is_colour:
                    terminal_runs += 1
                    if outcome == case.expected:
                        terminal_correct += 1
                    elif case.case_id not in terminal_misses:
                        terminal_misses.append(case.case_id)
                # A terminal outcome on a colour-expected case is EXCLUDED from the
                # direction split (D-03); it is a miss, not an under/over-triage.
                continue
            if not expected_is_colour:
                # A colour where a terminal outcome was expected: a terminal miss.
                terminal_runs += 1
                if case.case_id not in terminal_misses:
                    terminal_misses.append(case.case_id)
                continue
            outcome_rank = ranks.get(outcome)
            if outcome_rank is None:
                continue
            colour_runs += 1
            delta = outcome_rank - ranks[case.expected]
            if delta == 0:
                colour_correct += 1
            elif delta < 0:
                under_runs += 1
                saw_under = True
                if case.expected == most_urgent:
                    red_misses += 1
                    if case.case_id not in red_miss_cases:
                        red_miss_cases.append(case.case_id)
            else:
                over_runs += 1
                saw_over = True

        if saw_under and case.case_id not in under_cases:
            under_cases.append(case.case_id)
        if saw_over and case.case_id not in over_cases:
            over_cases.append(case.case_id)

    return Analysis(
        colour_runs=colour_runs,
        colour_correct=colour_correct,
        colour_accuracy=(colour_correct / colour_runs) if colour_runs else 0.0,
        under_triage=under_cases,
        under_triage_count=under_runs,
        over_triage=over_cases,
        over_triage_count=over_runs,
        terminal_runs=terminal_runs,
        terminal_correct=terminal_correct,
        terminal_counts=terminal_counts,
        terminal_misses=terminal_misses,
        aborted_cases=aborted_cases,
        aborted_count=aborted_runs,
        colour_stable_cases=colour_stable,
        colour_unstable_cases=colour_unstable,
        field_stable_cases=field_stable,
        field_unstable_cases=field_unstable,
        latency_p50=_percentile(latency, 0.5),
        latency_p95=_percentile(latency, 0.95),
        tokens_in=sum(case.tokens_in for case in cases),
        tokens_out=sum(case.tokens_out for case in cases),
        red_expected_count=red_runs,
        red_miss_count=red_misses,
        red_miss_cases=red_miss_cases,
        deferral_count=deferral_count,
        deferral_runs=deferral_runs,
        deferral_rate=(deferral_count / deferral_runs) if deferral_runs else 0.0,
        deferral_cases=deferral_cases,
        calibration=_calibration(cases),
    )


__all__ = ["analyse", "colour_urgency"]
