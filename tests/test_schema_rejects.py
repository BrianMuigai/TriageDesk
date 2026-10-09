"""Schema honesty tests (Roadmap SC2, T-01-01-03).

Prove the one schema module rejects implausible / wrong-unit values and never
imputes a missing vital. Runs offline — no Ollama call.

The bounds exercised here are *physiological plausibility* bounds (a schema
concern), NOT SATS TEWS scoring thresholds — those live only in
``data/sats_tews.yaml`` (CONVENTIONS §1), so no TEWS band edge appears in this
test.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from triagedesk.core.schema import CaseInput, ExtractionResult


def test_out_of_physiological_range_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CaseInput(heart_rate=-5)
    with pytest.raises(ValidationError):
        CaseInput(respiratory_rate=999)
    with pytest.raises(ValidationError):
        CaseInput(spo2=150)


def test_wrong_scale_temperature_is_rejected() -> None:
    # 98.6 is a Fahrenheit magnitude on a Celsius field — it must be rejected,
    # never accepted and scored into a TEWS band.
    with pytest.raises(ValidationError):
        CaseInput(temperature_c=98.6)


def test_missing_vitals_stay_none_and_are_never_imputed() -> None:
    case = CaseInput(complaint="no vitals recorded")
    assert case.heart_rate is None
    assert case.respiratory_rate is None
    assert case.temperature_c is None
    assert case.systolic_bp is None
    assert case.diastolic_bp is None
    assert case.spo2 is None
    assert case.mobility is None
    assert case.avpu is None
    assert case.trauma is None
    assert case.age_years is None


def test_enum_fields_reject_out_of_set_values() -> None:
    with pytest.raises(ValidationError):
        CaseInput(mobility="flying")
    with pytest.raises(ValidationError):
        CaseInput(avpu="asleep")


def test_plausible_values_still_validate() -> None:
    case = CaseInput(
        respiratory_rate=24,
        heart_rate=118,
        systolic_bp=108,
        temperature_c=38.9,
        avpu="alert",
    )
    assert case.temperature_c == 38.9
    assert case.avpu == "alert"


def test_extraction_result_defaults_are_empty_not_fabricated() -> None:
    result = ExtractionResult(case=CaseInput())
    assert result.matched_discriminator_ids == []
    assert result.no_discriminator_matched is False
