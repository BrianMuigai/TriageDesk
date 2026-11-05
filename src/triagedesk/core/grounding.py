"""Ground every sign an extraction claims against the note it came from (D-05, D-06).

The model may only *structure* a note and *select* ids from the closed set; it is never
trusted to have seen what it reports. This module is the ONE evidence check at the owned
tool boundary: a discriminator id survives only when one of its declared aliases occurs
as an unnegated contiguous token phrase of the note, and a numeric vital survives only
when its own numeric token occurs in the note.

Grounding is monotone removal: it can drop evidence but never add it. It constructs no
id, invents no value, converts no unit and touches no colour, target or destination —
the deterministic scorer remains the only place a colour is computed (D-01, D-03).

Pure module: it imports nothing from ``llm`` / ``mcp`` / ``store`` (D-13) and reads the
alias substrate only through the one loader (``core/rules.py``). No alias, colour, band
or threshold is inlined here (CONVENTIONS §1).
"""

from __future__ import annotations

import re

from triagedesk.core import matcher
from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import ExtractionResult

# Numeric tokens, with a comma decimal accepted as the desk writes it. This is the ONE
# numeric-stated rule, shared with the model client's post-check (``llm/notes.py``).
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

# The nine numeric ``CaseInput`` fields. This tuple is the ONE field list, used by both
# the tool-boundary grounding here and the model client's post-check.
NUMERIC_CASE_FIELDS: tuple[str, ...] = (
    "age_years",
    "age_months",
    "height_cm",
    "respiratory_rate",
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "temperature_c",
    "spo2",
)


def stated_numbers(note: str) -> set[str]:
    """Every numeric token in *note*, comma decimals normalised to a dot."""
    return {match.group(0).replace(",", ".") for match in _NUMBER.finditer(note)}


def value_is_stated(value: object, numbers: set[str]) -> bool:
    """True when a numeric *value* literally appears in the note.

    Booleans and non-numerics are not this guard's concern. A float is checked in both
    its compact and its plain form so ``38.9`` and ``38.90`` both pass.
    """
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, int):
        return str(value) in numbers
    if isinstance(value, float):
        return f"{value:g}" in numbers or str(value) in numbers
    return True


def ground_extraction(result: ExtractionResult, note: str) -> ExtractionResult:
    """Keep only the extracted evidence the note itself states — removal, never addition.

    The closed-set filter remains the ONE authority for which ids are candidates; this
    function then keeps an id only when at least one alias declared for it in
    ``data/sats_discriminators.yaml`` is an unnegated contiguous token phrase of *note*
    (the matcher's own boundary and negation rule). A numeric vital survives only when
    its own numeric token is in the note; an unstated value is nulled, never imputed or
    coerced. ``no_discriminator_matched`` follows what survives, so the shipped deferral
    path applies unchanged.
    """
    filtered = matcher.filter_discriminator_ids(result)
    tokens, spans = matcher.tokenize_with_spans(note)
    aliases_of = {
        discriminator.id: discriminator.aliases
        for discriminator in get_discriminators().discriminators
    }
    kept = [
        id_
        for id_ in filtered.matched_discriminator_ids
        if any(matcher.alias_matches(note, tokens, spans, alias) for alias in aliases_of[id_])
    ]
    numbers = stated_numbers(note)
    updates = {
        field: None
        for field in NUMERIC_CASE_FIELDS
        if getattr(filtered.case, field) is not None
        and not value_is_stated(getattr(filtered.case, field), numbers)
    }
    case = filtered.case.model_copy(update=updates) if updates else filtered.case
    return filtered.model_copy(
        update={
            "case": case,
            "matched_discriminator_ids": kept,
            "no_discriminator_matched": not kept,
        }
    )


__all__ = ["NUMERIC_CASE_FIELDS", "ground_extraction", "stated_numbers", "value_is_stated"]
