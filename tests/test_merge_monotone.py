"""The monotone re-extraction merge (ADAPT-07).

``core.merge.merge_monotone`` is the whole rule: a re-extraction may FILL a field that is
missing and may never overwrite a stated one. This suite proves it field by field, including
the contradiction the safety argument depends on ("an extraction that disagrees with a
recorded vital loses"), and proves the inputs are not mutated.
"""

from __future__ import annotations

from triagedesk.core.merge import merge_monotone
from triagedesk.core.schema import CaseInput

# The recorded case: every scored field stated, plus a note-derived complaint.
RECORDED = CaseInput(
    age_years=52,
    mobility="walking",
    avpu="alert",
    respiratory_rate=16,
    heart_rate=88,
    systolic_bp=130,
    temperature_c=36.9,
    trauma=False,
    complaint="feeling unwell",
)


def test_every_missing_field_is_filled() -> None:
    """A field the recorded case leaves ``None`` takes the extracted value."""
    current = CaseInput(complaint="chest pain")
    extracted = CaseInput(
        age_years=61,
        respiratory_rate=22,
        heart_rate=104,
        systolic_bp=98,
        temperature_c=38.4,
        spo2=94,
        mobility="with_help",
        avpu="voice",
        trauma=True,
    )

    merged = merge_monotone(current, extracted)

    for name in ("age_years", "respiratory_rate", "heart_rate", "systolic_bp",
                 "temperature_c", "spo2", "mobility", "avpu", "trauma"):
        assert getattr(merged, name) == getattr(extracted, name), name


def test_a_stated_value_always_wins() -> None:
    """Every field the recorded case states is preserved, whatever the extraction says."""
    extracted = CaseInput(
        age_years=18,
        mobility="stretcher",
        avpu="unresponsive",
        respiratory_rate=40,
        heart_rate=180,
        systolic_bp=70,
        temperature_c=41.0,
        trauma=True,
        complaint="the model rewrote the complaint",
    )

    merged = merge_monotone(RECORDED, extracted)

    assert merged == RECORDED


def test_an_extraction_that_contradicts_a_recorded_vital_loses() -> None:
    """The recorded vital is the clinical record; a disagreeing extraction is discarded."""
    extracted = CaseInput(temperature_c=40.0, heart_rate=150)

    merged = merge_monotone(RECORDED, extracted)

    assert merged.temperature_c == RECORDED.temperature_c
    assert merged.heart_rate == RECORDED.heart_rate


def test_the_original_complaint_is_never_overwritten() -> None:
    """``complaint`` is non-nullable, so it can never be replaced by an extraction."""
    merged = merge_monotone(RECORDED, CaseInput(complaint="something else entirely"))

    assert merged.complaint == "feeling unwell"


def test_an_ambiguity_flag_is_never_downgraded() -> None:
    """``age_ambiguous`` is fail-closed: a re-extract cannot turn it off (D-03)."""
    current = CaseInput(age_ambiguous=True, age_months=30)
    extracted = CaseInput(age_ambiguous=False, age_years=2)

    merged = merge_monotone(current, extracted)

    assert merged.age_ambiguous is True
    assert merged.age_months == 30
    assert merged.age_years == 2  # a genuinely missing field is still filled


def test_the_merge_is_monotone_over_repeated_application() -> None:
    """Applying a second extraction to the merged case can only add information."""
    first = merge_monotone(CaseInput(complaint="x"), CaseInput(heart_rate=90, spo2=97))
    second = merge_monotone(first, CaseInput(heart_rate=40, temperature_c=39.1))

    assert second.heart_rate == 90
    assert second.spo2 == 97
    assert second.temperature_c == 39.1


def test_the_inputs_are_not_mutated_and_no_fill_returns_the_same_value() -> None:
    """The merge is pure: the recorded case is untouched, and a no-op returns it unchanged."""
    before = RECORDED.model_dump()

    assert merge_monotone(RECORDED, CaseInput()) is RECORDED
    assert RECORDED.model_dump() == before
