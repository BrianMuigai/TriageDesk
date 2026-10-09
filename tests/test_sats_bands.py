"""Band-edge tests for the TEWS single source of truth (D-10, Pitfall 3).

Every band edge is exercised on **both** sides, and no band value is restated in
code: the boundaries and points under test are read from ``data/sats_tews.yaml``
through ``core/rules.py`` (CONVENTIONS §1). A tiny local matcher — which contains
no SATS literal — scores a probe value against the loaded bands, so the *data*
itself is what is under test.

Boundaries exercised (derived from the data, not hard-coded): respiratory rate
8/9/14/15/20/21/29/30; heart rate 40/41/50/51/100/101/110/111/129/130; systolic
BP 70/71/80/81/100/101/199/200; temperature 34.9/35.0/38.4/38.5; TEWS→colour
2/3, 4/5, 6/7.
"""

from __future__ import annotations

import math

import pytest

from triagedesk.core.rules import Band, TewsRules, get_tews

# Parameter keys are structural names (not clinical values); pinning the set
# catches a parameter that is missing from the chart.
REQUIRED_PARAMETERS = {
    "mobility",
    "respiratory_rate",
    "heart_rate",
    "systolic_bp",
    "temperature",
    "avpu",
    "trauma",
}
NUMERIC_PARAMETERS = ("respiratory_rate", "heart_rate", "systolic_bp", "temperature")
CATEGORICAL_PARAMETERS = ("mobility", "avpu", "trauma")


@pytest.fixture(scope="module")
def rules() -> TewsRules:
    """The rule substrate, loaded once through the one loader (D-08)."""
    return get_tews()


def _match_numeric(bands: list[Band], value: float) -> Band | None:
    """Return the band whose inclusive [min, max] contains *value* (data-driven)."""
    for band in bands:
        low = band.min if band.min is not None else -math.inf
        high = band.max if band.max is not None else math.inf
        if low <= value <= high:
            return band
    return None


def _match_categorical(bands: list[Band], value: str) -> Band | None:
    """Return the band whose discrete ``value`` equals *value*."""
    for band in bands:
        if band.value == value:
            return band
    return None


def _boundaries(bands: list[Band]) -> list[float]:
    out: list[float] = []
    for band in bands:
        if band.min is not None:
            out.append(float(band.min))
        if band.max is not None:
            out.append(float(band.max))
    return out


def _step(boundaries: list[float]) -> float:
    """The resolution of a parameter's boundaries (1 for integer scales, else 0.1)."""
    return 1.0 if all(b.is_integer() for b in boundaries) else 0.1


# --------------------------------------------------------------------------- #
# Completeness
# --------------------------------------------------------------------------- #
def test_all_required_parameters_present(rules: TewsRules) -> None:
    assert set(rules.parameters) == REQUIRED_PARAMETERS


def test_every_parameter_declares_bands(rules: TewsRules) -> None:
    for name, param in rules.parameters.items():
        assert param.bands, f"parameter {name!r} declares no bands"


# --------------------------------------------------------------------------- #
# Numeric bands: a partition of the number line (no gaps, no overlaps)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", NUMERIC_PARAMETERS)
def test_numeric_bands_partition_the_number_line(rules: TewsRules, name: str) -> None:
    bands = rules.parameters[name].bands
    step = _step(_boundaries(bands))

    ordered = sorted(bands, key=lambda b: b.min if b.min is not None else -math.inf)
    # Full coverage: the line is open at both ends.
    assert ordered[0].min is None, f"{name}: lowest band must be open below"
    assert ordered[-1].max is None, f"{name}: highest band must be open above"

    # No gaps and no overlaps between consecutive bands.
    for lower, upper in zip(ordered, ordered[1:], strict=False):
        assert lower.max is not None, f"{name}: band below a bounded band must be bounded"
        assert upper.min is not None, f"{name}: band above a bounded band must be bounded"
        assert upper.min == pytest.approx(lower.max + step), (
            f"{name}: gap/overlap between {lower.max} and {upper.min}"
        )


@pytest.mark.parametrize("name", NUMERIC_PARAMETERS)
def test_numeric_bands_are_reachable(rules: TewsRules, name: str) -> None:
    """Every declared band is reachable — a mid-band probe maps back to it."""
    bands = rules.parameters[name].bands
    for band in bands:
        low = band.min if band.min is not None else band.max
        high = band.max if band.max is not None else band.min
        probe = (low + high) / 2
        assert _match_numeric(bands, probe) is band, f"{name}: band {band} unreachable"


@pytest.mark.parametrize("name", NUMERIC_PARAMETERS)
def test_numeric_band_edges_inclusive_on_both_sides(rules: TewsRules, name: str) -> None:
    """At each edge, the value is inside its own band; one step away it is not."""
    bands = rules.parameters[name].bands
    step = _step(_boundaries(bands))

    for band in bands:
        if band.min is not None:
            assert _match_numeric(bands, band.min) is band, (
                f"{name}: lower edge {band.min} is exclusive (must be inclusive)"
            )
            below = _match_numeric(bands, band.min - step)
            assert below is not None and below is not band, (
                f"{name}: lower edge {band.min} overlaps the band below"
            )
        if band.max is not None:
            assert _match_numeric(bands, band.max) is band, (
                f"{name}: upper edge {band.max} is exclusive (must be inclusive)"
            )
            above = _match_numeric(bands, band.max + step)
            assert above is not None and above is not band, (
                f"{name}: upper edge {band.max} overlaps the band above"
            )


# --------------------------------------------------------------------------- #
# Categorical bands
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", CATEGORICAL_PARAMETERS)
def test_categorical_bands_map_to_declared_points(rules: TewsRules, name: str) -> None:
    bands = rules.parameters[name].bands
    for band in bands:
        assert band.value is not None, f"{name}: categorical band without a value"
        assert _match_categorical(bands, band.value) is band


@pytest.mark.parametrize("name", CATEGORICAL_PARAMETERS)
def test_categorical_unknown_value_has_no_match(rules: TewsRules, name: str) -> None:
    bands = rules.parameters[name].bands
    assert _match_categorical(bands, "__no_such_value__") is None


# --------------------------------------------------------------------------- #
# TEWS -> colour thresholds (both sides of every boundary)
# --------------------------------------------------------------------------- #
def _colour_for(bands, total: int):
    for band in bands:
        high = band.max if band.max is not None else math.inf
        if band.min <= total <= high:
            return band
    return None


def test_colour_thresholds_partition_from_zero(rules: TewsRules) -> None:
    bands = sorted(rules.tews_to_colour, key=lambda b: b.min)
    assert bands[0].min == 0, "colour thresholds must start at TEWS 0"
    assert bands[-1].max is None, "the highest colour must be open above"
    for lower, upper in zip(bands, bands[1:], strict=False):
        assert lower.max is not None
        assert upper.min == lower.max + 1, (
            f"colour gap/overlap between TEWS {lower.max} and {upper.min}"
        )


def test_colour_threshold_edges_inclusive_on_both_sides(rules: TewsRules) -> None:
    bands = rules.tews_to_colour
    for band in bands:
        assert _colour_for(bands, band.min) is band, (
            f"colour {band.colour}: lower edge {band.min} exclusive"
        )
        if band.max is not None:
            assert _colour_for(bands, band.max) is band, (
                f"colour {band.colour}: upper edge {band.max} exclusive"
            )
            above = _colour_for(bands, band.max + 1)
            assert above is not None and above is not band, (
                f"colour {band.colour}: upper edge {band.max} overlaps the next colour"
            )


def test_every_colour_has_a_target_time_and_destination(rules: TewsRules) -> None:
    colours = {band.colour for band in rules.tews_to_colour}
    assert colours <= set(rules.target_times), "a TEWS colour has no target time"
    for colour in colours:
        entry = rules.target_times[colour]
        assert entry.target
        assert entry.destination


# --------------------------------------------------------------------------- #
# Out-of-scope predicate: data, and fail-closed on a missing age (D-09)
# --------------------------------------------------------------------------- #
def _classify(age: int | None, height_cm: float | None, scope) -> str:
    """Evaluate the out-of-scope predicate from its data (no SATS literal).

    Adult = age > adult_min_age_years OR height > adult_min_height_cm. A missing
    age never defaults to adult: the declared ``on_missing_age`` behaviour is
    returned (fail-closed — Roadmap SC2).
    """
    if height_cm is not None and height_cm > scope.adult_min_height_cm:
        return "adult"
    if age is None:
        return scope.on_missing_age
    return "adult" if age > scope.adult_min_age_years else "out_of_scope"


def test_out_of_scope_predicate_fails_closed_on_missing_age(rules: TewsRules) -> None:
    scope = rules.out_of_scope
    # The missing-age behaviour is explicit data and is not "adult".
    assert scope.on_missing_age == "abstain"
    assert _classify(None, None, scope) == scope.on_missing_age
    assert _classify(None, None, scope) != "adult"


def test_out_of_scope_boundaries_hold_on_both_sides(rules: TewsRules) -> None:
    scope = rules.out_of_scope
    # Age boundary: age > adult_min_age_years is adult.
    assert _classify(scope.adult_min_age_years, None, scope) != "adult"
    assert _classify(scope.adult_min_age_years + 1, None, scope) == "adult"
    # Height boundary: height > adult_min_height_cm is adult, even with no age.
    assert _classify(None, scope.adult_min_height_cm, scope) != "adult"
    assert _classify(None, scope.adult_min_height_cm + 1, scope) == "adult"
