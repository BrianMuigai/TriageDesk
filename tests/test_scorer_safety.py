"""Fail-closed safety tests for the pure scorer (Plan 02-01, SCORE-04, INTAKE-03).

Two safety branches are proven here, with every boundary derived from the loaded
data (no SATS literal):

* out-of-scope input (paediatric / missing / months-expressed / ambiguous age)
  abstains and never receives an adult colour (D-03);
* a missing scored vital is reported and never imputed — the score uses only
  nurse-provided fields (D-04).
"""

from __future__ import annotations

import pytest

from triagedesk.core import scorer
from triagedesk.core.rules import Parameter, TewsRules, get_tews
from triagedesk.core.schema import CaseInput


def _probe_for_points(param: Parameter, points: int) -> object:
    """A probe value that lands in a band with *points* (data-driven)."""
    band = next(b for b in param.bands if b.points == points)
    if band.value is not None:
        return band.value
    return band.min if band.min is not None else band.max


def _full_case(**overrides: object) -> CaseInput:
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


def _adult_colour_tokens(rules: TewsRules) -> set[str]:
    return {band.colour for band in rules.tews_to_colour}


def _assert_abstained(result) -> None:
    rules = get_tews()
    assert result.out_of_scope is True
    assert result.abstained is True
    assert result.colour is None
    assert result.colour not in _adult_colour_tokens(rules)
    assert result.tews is None
    assert result.target is None
    assert result.destination is None
    assert result.citations == []
    assert result.triggered_rules == []
    assert result.reason


def test_missing_age_abstains_and_names_the_missing_age() -> None:
    result = scorer.score_priority(_full_case(age_years=None, height_cm=None))
    _assert_abstained(result)
    assert "age" in (result.reason or "").lower()


def test_months_expressed_age_abstains_even_with_adult_years() -> None:
    # age_years is present AND adult, but a months-expressed age must still abstain.
    result = scorer.score_priority(_full_case(age_months=18))
    _assert_abstained(result)


def test_ambiguous_age_abstains() -> None:
    result = scorer.score_priority(_full_case(age_ambiguous=True))
    _assert_abstained(result)


def test_paediatric_age_abstains() -> None:
    rules = get_tews()
    child = rules.out_of_scope.adult_min_age_years  # at the boundary, not adult
    result = scorer.score_priority(_full_case(age_years=child, height_cm=None))
    _assert_abstained(result)


def test_height_at_or_below_boundary_with_no_age_abstains() -> None:
    rules = get_tews()
    # height is not > adult_min_height_cm and there is no age -> fail closed.
    result = scorer.score_priority(
        _full_case(age_years=None, height_cm=rules.out_of_scope.adult_min_height_cm)
    )
    _assert_abstained(result)


def test_missing_vital_is_reported_and_never_imputed() -> None:
    rules = get_tews()
    temp_param = rules.parameters["temperature"]
    two_point_band = next(b for b in temp_param.bands if b.points == 2)
    two_point = (
        two_point_band.value
        if two_point_band.value is not None
        else (two_point_band.min if two_point_band.min is not None else two_point_band.max)
    )
    two_point_points = two_point_band.points

    present = scorer.score_priority(_full_case(temperature_c=two_point))
    missing = scorer.score_priority(_full_case(temperature_c=None))

    # The omitted vital is reported by its data parameter name and is not used.
    assert "temperature" in missing.missing_vitals
    assert "temperature" not in missing.used_vitals
    # It contributes no points: the total drops by exactly that band's points and
    # is never defaulted to a 0-point band (which would silently under-score).
    assert present.tews == missing.tews + two_point_points
    assert missing.tews == 0


def test_score_inputs_are_a_subset_of_nurse_provided_fields() -> None:
    case = _full_case(temperature_c=None, spo2=None)
    result = scorer.score_priority(case)

    assert not set(result.used_vitals) & set(result.missing_vitals)
    for name in result.used_vitals:
        assert getattr(case, scorer.case_field(name)) is not None
    for name in result.missing_vitals:
        assert getattr(case, scorer.case_field(name)) is None


@pytest.mark.parametrize("overrides", [
    {"age_years": None, "height_cm": None},
    {"age_months": 18},
    {"age_ambiguous": True},
    {"age_years": 4, "height_cm": None},
])
def test_out_of_scope_never_receives_an_adult_colour(overrides: dict) -> None:
    result = scorer.score_priority(_full_case(**overrides))
    rules = get_tews()
    assert result.colour is None
    assert result.colour not in _adult_colour_tokens(rules)
