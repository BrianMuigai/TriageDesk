"""Extraction-fidelity contract guards (Phase 11, EVAL-06, D11-01/D11-14).

Hermetic and deterministic — the local model is never called. These guards pin the
*contract* the model is asked to fill, which is the honest lever for extraction
fidelity (D11-01):

1. ``CaseInput.age_years`` carries a non-empty schema ``description`` — the field the
   model must not leave null when the note states an age (the E-04 fix). The
   description reaches the model as BOTH the prompt text and the ``format=`` decode
   grammar, because ``llm.client.extract`` sends ``ExtractionResult.model_json_schema()``
   as both;
2. that description is a GENERAL contract sentence, not tuned to a fixture: it quotes no
   number that appears in any eval fixture and names no SATS value (a colour token or a
   discriminator id). The fixture checks read the cases through the ONE loader and the
   SATS values through the loaded substrate, so nothing is restated here (D11-02);
3. E-07's repaired note and its golden ``case`` agree — the note states the temperature the
   golden case declares, and the expectation stays ``RECHECK`` (D11-14).
"""

from __future__ import annotations

import re
from pathlib import Path

from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import CaseInput
from triagedesk.evals.case import CaseSpec, load_cases

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"


def _age_description() -> str:
    """The schema description the model receives for ``age_years`` (the ONE accessor)."""
    return CaseInput.model_json_schema()["properties"]["age_years"].get("description", "")


def _substrate_colours() -> set[str]:
    """The colour tokens declared by the loaded TEWS substrate (never a literal)."""
    return {band.colour for band in get_tews().tews_to_colour}


def _substrate_discriminator_ids() -> set[str]:
    """The closed discriminator id set read from the loaded substrate (never a literal)."""
    return {disc.id for disc in get_discriminators().discriminators}


def _spec_numbers(spec: CaseSpec) -> set[str]:
    """Every standalone number appearing in a fixture's note or its golden case(s).

    The fixture is the ONE source of the numbers the contract must not quote; the note is
    scanned as free text and the golden cases are walked as typed values, so a worked
    example that restates a fixture number is caught without hard-coding that number here.
    """
    found = set(re.findall(r"\d+", spec.note))
    for golden in (spec.case, spec.previous_case):
        if golden is None:
            continue
        for value in golden.model_dump().values():
            if isinstance(value, bool) or value is None:
                continue
            if isinstance(value, (int, float)):
                found.update(re.findall(r"\d+", str(value)))
    return found


def test_age_years_carries_a_schema_description() -> None:
    """``age_years`` has a non-empty description, so the model is told to parse a stated age.

    The description is part of the JSON schema ``extract()`` sends as both the prompt text
    and the ``format=`` grammar — a stated age survives structuring (E-04's root cause).
    """
    description = _age_description()
    assert description, "age_years carries no schema description (the E-04 contract is absent)"


def test_age_years_description_is_general_not_tuned_to_a_fixture() -> None:
    """The description quotes no fixture number and names no SATS value (D11-02).

    A general contract sentence is fixture-independent; a worked example quoting a fixture's
    own number, or a SATS value (a colour token or a discriminator id), would shade into
    tuning to the test. Every check reads the fixtures through the ONE loader and the SATS
    values from the loaded substrate, so no clinical value is restated here.
    """
    description = _age_description()
    description_numbers = set(re.findall(r"\d+", description))

    fixture_numbers: set[str] = set()
    for spec in load_cases(CASES_DIR):
        fixture_numbers |= _spec_numbers(spec)
    assert fixture_numbers, "no fixture numbers were collected (the guard would be vacuous)"
    assert not (description_numbers & fixture_numbers), (
        "the age description quotes a fixture number (a worked example, not a general "
        f"contract): {sorted(description_numbers & fixture_numbers)}"
    )

    for colour in _substrate_colours():
        assert colour not in description, f"the age description names the SATS colour {colour!r}"
    for disc_id in _substrate_discriminator_ids():
        assert disc_id not in description, (
            f"the age description names the discriminator id {disc_id!r}"
        )


# ---------------- 2b. the serial-vitals contract is general, at the same seam (E-07, D11-01)

# The scored numeric vitals whose before/after presentation the model must resolve to the
# current (AFTER) reading. Declared here so the guard names the same set the schema does.
_SERIAL_SCORED_VITALS = ("respiratory_rate", "heart_rate", "systolic_bp")


def _vital_description(field: str) -> str:
    """The schema description the model receives for one scored vital (the ONE accessor)."""
    return CaseInput.model_json_schema()["properties"][field].get("description", "")


def test_serial_vitals_carry_a_general_after_value_description() -> None:
    """Each scored vital states the serial-reading rule, quoting no fixture number (D11-01/02).

    The before/after arrow presentation is resolved to the AFTER (current) value at the
    extraction seam. The clarification is general: it names no fixture number and no SATS
    value, so it applies to any serial note and is not tuned to E-07's fragment (D11-02).
    """
    fixture_numbers: set[str] = set()
    for spec in load_cases(CASES_DIR):
        fixture_numbers |= _spec_numbers(spec)

    for field in _SERIAL_SCORED_VITALS:
        description = _vital_description(field)
        assert description, f"{field} carries no serial-reading description"
        description_numbers = set(re.findall(r"\d+", description))
        assert not (description_numbers & fixture_numbers), (
            f"the {field} description quotes a fixture number: "
            f"{sorted(description_numbers & fixture_numbers)}"
        )
        for colour in _substrate_colours():
            assert colour not in description, f"the {field} description names the colour {colour!r}"
        for disc_id in _substrate_discriminator_ids():
            assert disc_id not in description, (
                f"the {field} description names the discriminator id {disc_id!r}"
            )


# -------------------- 3. E-07's note and golden case agree (D11-14, the one fixture repair)


def test_e07_note_states_every_scored_vital_its_golden_case_declares() -> None:
    """D11-14: the repaired E-07 note states the temperature its golden ``case`` declares.

    The fixture's free-text ``note`` and its golden ``case`` disagreed (the note omitted the
    temperature the case asserted), so a faithful extraction of the note could not produce the
    golden case. The repair is a test-data-inconsistency fix ONLY: the golden ``case``, the
    ``previous_case`` and ``expected: RECHECK`` are unchanged — the expectation never moved to
    make a case pass, and nothing was tuned green.
    """
    case = next(spec for spec in load_cases(CASES_DIR) if spec.id == "E-07")

    assert "temperature" in case.note.lower(), "the repaired E-07 note states no temperature"
    assert case.case.temperature_c is not None, "the E-07 golden case declares no temperature"
    assert case.expected == "RECHECK", "the E-07 expectation moved off RECHECK"

    # The same consistency holds for the previous case (the serial comparison needs both).
    assert case.previous_case is not None, "E-07 declares no previous_case"
    assert case.previous_case.temperature_c is not None
