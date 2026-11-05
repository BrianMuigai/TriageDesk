"""Deterministic post-checks for free-text extraction (D-03, SAFE-01).

The local model *structures* a note; it is not trusted to be complete or exact. This
module applies the deterministic checks the nurse stress test showed are needed:

* a value the note does not state is dropped (the model must never impute);
* a serial reading resolves to the **AFTER** value (the current reading);
* an explicit (or physically impossible-Celsius) temperature is converted from °F;
* a stated age, mobility, AVPU or trauma is recovered even when the model drops it.

Every helper is pure and total: an invalid override is skipped, never raised, so a bad
note can only make the case *less* complete (which routes to recovery), never unsafe.
This module imports only the core package and Python's stdlib.
"""

from __future__ import annotations

import re

from pydantic import ValidationError

from triagedesk.core.grounding import (
    NUMERIC_CASE_FIELDS,
    stated_numbers,
    stated_temperature,
    value_is_stated,
)
from triagedesk.core.rules import get_text_terms
from triagedesk.core.schema import CaseInput

# Serial readings. The label is the only place the parameter is named; the values come
# from the note. BP is handled as a pair so the diastolic AFTER value is not lost.
_BP_SERIAL = re.compile(
    r"\b(?:bp|blood pressure)\s*[:=]?\s*(\d+)\s*/\s*(\d+)\s*(?:->|→|to)\s*"
    r"(\d+)\s*/\s*(\d+)",
    re.IGNORECASE,
)
_SERIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "respiratory_rate",
        re.compile(
            r"\b(?:rr|resp(?:iratory)? rate|breathing rate)\s*[:=]?\s*(\d+)\s*"
            r"(?:->|→|to)\s*(\d+)",
            re.IGNORECASE,
        ),
    ),
    (
        "heart_rate",
        re.compile(
            r"\b(?:hr|heart rate|pulse)\s*[:=]?\s*(\d+)\s*(?:->|→|to)\s*(\d+)",
            re.IGNORECASE,
        ),
    ),
    (
        "systolic_bp",
        re.compile(
            r"\b(?:sbp|systolic(?: blood pressure)?|bp|blood pressure)\s*[:=]?\s*"
            r"(\d+)(?:\s*/\s*\d+)?\s*(?:->|→|to)\s*(\d+)",
            re.IGNORECASE,
        ),
    ),
)
_TEMPERATURE_SERIAL = re.compile(
    r"\b(?:temp|temperature|t)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:->|→|to)\s*"
    r"(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)

# A single temperature is read by the ONE temperature rule in ``core.grounding`` (shared
# with the tool boundary), so the °F conversion has a single home.

_AGE_MONTHS = re.compile(r"\b(\d+)\s*(?:-\s*)?months?\s*old\b", re.IGNORECASE)
_AGE_YEARS = re.compile(r"\b(\d+)\s*(?:-\s*)?(?:year|yr)s?\s*old\b", re.IGNORECASE)
_AGE_ALT = re.compile(r"\b(?:aged?|age)\s*(\d+)\b|\b(\d+)\s*(?:yo|y/o)\b", re.IGNORECASE)


def _apply(case: CaseInput, updates: dict[str, object]) -> CaseInput:
    """Apply each update independently, skipping any that the schema rejects.

    One bad value (e.g. an out-of-range temperature) must not discard a valid age or a
    valid serial override, so validation is per field rather than all-or-nothing.
    """
    for field, value in updates.items():
        try:
            case = CaseInput.model_validate({**case.model_dump(), field: value})
        except ValidationError:
            continue
    return case


def _drop_unstated(case: CaseInput, note: str) -> CaseInput:
    """Null every numeric/categorical value the note does not state (never impute)."""
    numbers = stated_numbers(note)
    updates: dict[str, object] = {}
    for field in NUMERIC_CASE_FIELDS:
        value = getattr(case, field)
        if value is not None and not value_is_stated(value, numbers):
            updates[field] = None

    terms = get_text_terms()
    lower = note.lower()
    if case.mobility is not None and not any(item.term in lower for item in terms.mobility):
        updates["mobility"] = None
    if case.avpu is not None and not any(item.term in lower for item in terms.avpu):
        updates["avpu"] = None
    # A positive trauma finding with no textual support is an invention; an unsupported
    # negative is left alone because the prompt defines an unmentioned trauma as false.
    if case.trauma is True and not any(term in lower for term in terms.trauma_positive):
        updates["trauma"] = None
    return _apply(case, updates)


def _apply_serial(case: CaseInput, note: str) -> CaseInput:
    """Take the AFTER value of every serial reading (the patient's current reading)."""
    updates: dict[str, object] = {}
    pair = _BP_SERIAL.search(note)
    if pair is not None:
        updates["systolic_bp"] = int(pair.group(3))
        updates["diastolic_bp"] = int(pair.group(4))
    for field, pattern in _SERIAL_PATTERNS:
        match = pattern.search(note)
        if match is None:
            continue
        updates[field] = int(match.group(2))
    temperature = _TEMPERATURE_SERIAL.search(note)
    if temperature is not None:
        updates["temperature_c"] = float(temperature.group(2).replace(",", "."))
    return _apply(case, updates)


def _apply_temperature(case: CaseInput, note: str) -> CaseInput:
    """Set a single stated temperature, converting °F deterministically."""
    if _TEMPERATURE_SERIAL.search(note) is not None:
        return case  # the serial helper already took the AFTER value
    celsius = stated_temperature(note)
    if celsius is None:
        return case
    return _apply(case, {"temperature_c": celsius})


def _apply_age(case: CaseInput, note: str) -> CaseInput:
    """Recover a stated age the model dropped (months first, then years)."""
    months = _AGE_MONTHS.search(note)
    if months is not None:
        return _apply(case, {"age_months": int(months.group(1))})
    if case.age_years is not None:
        return case
    years = _AGE_YEARS.search(note) or _AGE_ALT.search(note)
    if years is None:
        return case
    value = next((group for group in years.groups() if group is not None), None)
    return _apply(case, {"age_years": int(value)}) if value is not None else case


def _apply_categoricals(case: CaseInput, note: str) -> CaseInput:
    """Recover a stated mobility/AVPU/trauma the model dropped; never invent one."""
    terms = get_text_terms()
    lower = note.lower()
    updates: dict[str, object] = {}
    if case.mobility is None:
        for item in terms.mobility:
            if item.term in lower:
                updates["mobility"] = item.value
                break
    if case.avpu is None:
        for item in terms.avpu:
            if item.term in lower:
                updates["avpu"] = item.value
                break
    if case.trauma is None:
        if any(term in lower for term in terms.trauma_negative):
            updates["trauma"] = False
        elif any(term in lower for term in terms.trauma_positive):
            updates["trauma"] = True
    return _apply(case, updates)


def grounded_case(case: CaseInput, note: str) -> CaseInput:
    """Return the case corrected against the note — the ONE extraction grounding step.

    Order matters: unstated values are dropped first (so an invented value cannot
    survive), then the deterministic serial/°F/age/categorical readers fill only what
    the note actually says.
    """
    grounded = _drop_unstated(case, note)
    grounded = _apply_serial(grounded, note)
    grounded = _apply_temperature(grounded, note)
    grounded = _apply_age(grounded, note)
    grounded = _apply_categoricals(grounded, note)
    return grounded


__all__ = ["grounded_case"]
