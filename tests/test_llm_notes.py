"""Deterministic extraction-grounding tests (nurse stress test S1-2/S1-3).

The model is not trusted to be complete or exact. These tests prove the post-checks:
unstated values are dropped, serial readings take the AFTER value, °F is converted, and a
stated age/categorical is recovered — all without a model call.
"""

from __future__ import annotations

from triagedesk.core.schema import CaseInput
from triagedesk.llm.notes import grounded_case


def test_serial_reading_takes_the_after_value() -> None:
    """RR 18 -> 24 / HR 92 -> 118 is the patient's current 24/118, not the before."""
    case = CaseInput(
        age_years=60,
        respiratory_rate=18,
        heart_rate=92,
        systolic_bp=130,
        temperature_c=37.2,
        mobility="walking",
        avpu="alert",
        trauma=False,
        complaint="chest pain",
    )
    note = (
        "60 year old man, RR 18 -> 24, HR 92 -> 118, BP 130/80, temp 37.2, "
        "alert, walking. Complaint: chest pain."
    )
    result = grounded_case(case, note)
    assert result.respiratory_rate == 24
    assert result.heart_rate == 118


def test_bp_serial_pair_keeps_the_after_diastolic() -> None:
    case = CaseInput(systolic_bp=130, diastolic_bp=80, complaint="bleeding")
    result = grounded_case(case, "BP 130/80 -> 92/50. Complaint: bleeding.")
    assert result.systolic_bp == 92
    assert result.diastolic_bp == 50


def test_fahrenheit_is_converted_deterministically() -> None:
    """98.6 °F is 37.0 °C, not the model's guessed 37.2 — and stated categories survive."""
    case = CaseInput(
        age_years=50,
        temperature_c=37.2,
        respiratory_rate=20,
        heart_rate=90,
        systolic_bp=120,
        complaint="fever",
    )
    note = (
        "50 year old woman, temp 98.6, RR 20, HR 90, BP 120/80, alert, walking, "
        "no trauma. Complaint: fever."
    )
    result = grounded_case(case, note)
    assert result.temperature_c == 37.0
    assert result.mobility == "walking"
    assert result.avpu == "alert"
    assert result.trauma is False


def test_unstated_mobility_is_dropped_not_invented() -> None:
    """The model invented ``walking`` on a note that never mentioned mobility."""
    case = CaseInput(
        age_years=40,
        respiratory_rate=24,
        heart_rate=118,
        systolic_bp=108,
        diastolic_bp=70,
        temperature_c=38.9,
        mobility="walking",
        avpu="alert",
        trauma=False,
        complaint="coughing and fast breathing",
    )
    note = (
        "40 year old man, RR 24, HR 118, BP 108/70, temp 38.9, alert, "
        "coughing and fast breathing"
    )
    result = grounded_case(case, note)
    assert result.mobility is None, "an unstated mobility was kept"
    assert result.avpu == "alert"


def test_unstated_temperature_is_dropped() -> None:
    case = CaseInput(
        age_years=30,
        respiratory_rate=16,
        heart_rate=78,
        systolic_bp=118,
        temperature_c=36.8,
        mobility="walking",
        avpu="alert",
        trauma=False,
        complaint="sore throat",
    )
    note = (
        "30 year old woman, walking, alert, RR 16, HR 78, systolic BP 118. "
        "Complaint: sore throat."
    )
    result = grounded_case(case, note)
    assert result.temperature_c is None, "an unstated temperature was kept"


def test_a_dropped_stated_age_is_recovered() -> None:
    case = CaseInput(
        age_years=None,
        respiratory_rate=14,
        heart_rate=80,
        systolic_bp=120,
        temperature_c=36.8,
        mobility="walking",
        avpu="alert",
        trauma=False,
        complaint="no chest pain",
    )
    note = (
        "28 year old woman, no chest pain, no shortness of breath, RR 14, HR 80, "
        "BP 120/80, temp 36.8, walking, alert, no trauma."
    )
    result = grounded_case(case, note)
    assert result.age_years == 28
    assert result.age_months is None


def test_a_stated_age_in_months_is_recovered() -> None:
    case = CaseInput(
        age_years=None,
        age_months=None,
        respiratory_rate=30,
        heart_rate=130,
        temperature_c=38.5,
        mobility="walking",
        avpu="alert",
        trauma=False,
        complaint="fever",
    )
    note = "18 month old boy, RR 30, HR 130, temp 38.5, alert, walking. Complaint: fever."
    result = grounded_case(case, note)
    assert result.age_months == 18


def test_a_fully_stated_case_is_unchanged() -> None:
    case = CaseInput(
        age_years=30,
        respiratory_rate=16,
        heart_rate=78,
        systolic_bp=118,
        temperature_c=36.8,
        mobility="walking",
        avpu="alert",
        trauma=False,
        complaint="sore throat",
    )
    note = (
        "30 year old woman, walking, alert, no trauma. RR 16, HR 78, systolic BP 118, "
        "temperature 36.8. Complaint: sore throat."
    )
    assert grounded_case(case, note) == case
