"""Exhaustive band-edge, colour-boundary and determinism tests (Plan 02-01, SCORE-05).

Every boundary is read from ``data/sats_tews.yaml`` through the one loader; no
SATS literal is restated here (CONVENTIONS §1). A tiny local reference matcher —
which contains no clinical value — says what the *data* requires, and the scorer
is asserted to agree with it at each edge, on both sides.

Covered: every numeric band edge on both sides; the temperature gap value
(strictly between adjacent bands) resolving total and fail-closed; every
TEWS->colour boundary; and determinism (identical input -> identical colour and
citation set).
"""

from __future__ import annotations

import math

import pytest

from triagedesk.core import scorer
from triagedesk.core.rules import Band, Parameter, TewsRules, get_tews
from triagedesk.core.schema import CaseInput

NUMERIC_PARAMETERS = ("respiratory_rate", "heart_rate", "systolic_bp", "temperature")


# --------------------------------------------------------------------------- #
# Data-driven helpers (no SATS literal)
# --------------------------------------------------------------------------- #
def _probe_for_points(param: Parameter, points: int) -> object:
    """A probe value that lands in a band with *points* (data-driven)."""
    band = next(b for b in param.bands if b.points == points)
    if band.value is not None:
        return band.value
    return band.min if band.min is not None else band.max


def _baseline(**overrides: object) -> CaseInput:
    """A complete adult case with every scored vital at its zero-point value."""
    rules = get_tews()
    values: dict[str, object] = {}
    for name, param in rules.parameters.items():
        field = scorer.case_field(name)
        if field == "trauma":
            values[field] = False
        else:
            values[field] = _probe_for_points(param, 0)
    values["age_years"] = rules.out_of_scope.adult_min_age_years + 1
    values.update(overrides)
    return CaseInput(**values)


def _points_for(name: str, value: object) -> int:
    """The scorer's total for a baseline case with one vital set to *value*.

    The baseline scores zero, so the returned total is that parameter's points.
    """
    return scorer.score_priority(_baseline(**{scorer.case_field(name): value})).tews  # type: ignore[arg-type]


def _reference_band(bands: list[Band], value: float) -> Band | None:
    for band in bands:
        low = band.min if band.min is not None else -math.inf
        high = band.max if band.max is not None else math.inf
        if low <= value <= high:
            return band
    return None


def _reference_colour(rules: TewsRules, total: int) -> str | None:
    for band in rules.tews_to_colour:
        high = band.max if band.max is not None else math.inf
        if band.min <= total <= high:
            return band.colour
    return None


def _step(bands: list[Band]) -> float:
    bounds = [b for band in bands for b in (band.min, band.max) if b is not None]
    return 1.0 if all(float(b).is_integer() for b in bounds) else 0.1


# --------------------------------------------------------------------------- #
# Numeric band edges, both sides
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", NUMERIC_PARAMETERS)
def test_every_numeric_band_edge_is_inclusive_and_correct_on_both_sides(name: str) -> None:
    bands = get_tews().parameters[name].bands
    step = _step(bands)

    for band in bands:
        if band.min is not None:
            assert _points_for(name, band.min) == band.points, (
                f"{name}: lower edge {band.min} is exclusive or mis-scored"
            )
            below = _reference_band(bands, band.min - step)
            assert below is not None and below is not band
            assert _points_for(name, band.min - step) == below.points, (
                f"{name}: one step below {band.min} did not cross to the band below"
            )
        if band.max is not None:
            assert _points_for(name, band.max) == band.points, (
                f"{name}: upper edge {band.max} is exclusive or mis-scored"
            )
            above = _reference_band(bands, band.max + step)
            assert above is not None and above is not band
            assert _points_for(name, band.max + step) == above.points, (
                f"{name}: one step above {band.max} did not cross to the band above"
            )


def test_temperature_gap_value_is_total_and_fail_closed() -> None:
    """A valid in-range value between adjacent bands resolves to a real band."""
    bands = get_tews().parameters["temperature"].bands
    below = next(b for b in bands if b.min is None and b.max is not None)
    above = min(
        (b for b in bands if b.min is not None and b.min > below.max),
        key=lambda b: b.min,
    )
    gap = (below.max + above.min) / 2  # strictly between the two bands
    assert below.max < gap < above.min

    points = _points_for("temperature", gap)
    assert points in {below.points, above.points}
    assert points == max(below.points, above.points), (
        "a tie between adjacent bands must resolve to the fail-closed (higher-points) band"
    )


# --------------------------------------------------------------------------- #
# TEWS -> colour boundaries, both sides
# --------------------------------------------------------------------------- #
def _case_for_total(rules: TewsRules, total: int) -> CaseInput:
    """A case whose TEWS total is exactly *total*, built from data-driven probes."""
    params = rules.parameters
    rr_max = max(b.points for b in params["respiratory_rate"].bands)
    hr_max = max(b.points for b in params["heart_rate"].bands)
    trauma_max = max(b.points for b in params["trauma"].bands)

    rr_points = min(total, rr_max)
    rest = total - rr_points
    hr_points = min(rest, hr_max)
    rest -= hr_points
    trauma_points = rest
    assert 0 <= trauma_points <= trauma_max, f"cannot build TEWS total {total}"

    return _baseline(
        respiratory_rate=_probe_for_points(params["respiratory_rate"], rr_points),
        heart_rate=_probe_for_points(params["heart_rate"], hr_points),
        trauma=bool(trauma_points),
    )


def test_tews_to_colour_boundaries_are_exact_on_both_sides() -> None:
    rules = get_tews()
    for band in rules.tews_to_colour:
        for total in (band.min, band.max):
            if total is None:
                continue
            result = scorer.score_priority(_case_for_total(rules, total))
            assert result.tews == total
            assert result.colour == _reference_colour(rules, total), (
                f"TEWS {total} did not map to its data-declared colour"
            )


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_identical_input_gives_identical_colour_and_citation_set() -> None:
    rules = get_tews()
    case = _baseline(
        respiratory_rate=_probe_for_points(rules.parameters["respiratory_rate"], 2),
        heart_rate=_probe_for_points(rules.parameters["heart_rate"], 2),
        temperature_c=_probe_for_points(rules.parameters["temperature"], 2),
    )
    first = scorer.score_priority(case)
    second = scorer.score_priority(case)

    assert first.colour == second.colour
    assert first.tews == second.tews
    assert first.citations == second.citations
    assert set(first.citations) == set(second.citations)
    assert first.triggered_rules == second.triggered_rules


# --------------------------------------------------------------------------- #
# Unit safety
# --------------------------------------------------------------------------- #
def test_scorer_only_sees_valid_celsius() -> None:
    """A Fahrenheit-magnitude temperature is rejected by the schema upstream.

    This does not re-test the schema: it asserts the scorer accepts a valid
    Celsius value and scores it without error (it never handles a wrong unit).
    """
    rules = get_tews()
    celsius = _probe_for_points(rules.parameters["temperature"], 0)
    result = scorer.score_priority(_baseline(temperature_c=celsius))
    assert result.colour is not None
    assert result.abstained is False
