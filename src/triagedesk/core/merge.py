"""The ONE monotone case merge (ADAPT-07).

Re-extraction may only **fill** a field that is missing. This module is the whole rule, and it
is pure: no model, no store, no SATS value, no I/O. A stated value always wins — a recorded
vital, the note-derived complaint and a nurse's answer are never overwritten by a later
extraction, so a re-extract can add evidence but can never rewrite what the desk already has.

It lives beside the schema (``core``) rather than in a node because it is a contract property
of ``CaseInput``, and it imports nothing from ``llm`` / ``mcp`` / ``store`` (D-13, enforced by
``tests/test_purity.py``).
"""

from __future__ import annotations

from triagedesk.core.schema import CaseInput

__all__ = ["merge_monotone"]


def merge_monotone(current: CaseInput, extracted: CaseInput) -> CaseInput:
    """Fill only the fields *current* leaves ``None``; every stated value wins (ADAPT-07).

    The field set is read from ``CaseInput.model_fields`` — never hand-listed — so a new case
    field is covered automatically and cannot be forgotten here (DRY). A field whose current
    value is ``None`` takes the extracted value when the extraction supplies one; anything the
    extraction reports for a field that already has a value is discarded, which is what makes
    the merge monotone: re-running it with any extraction can only add information.

    The non-nullable fields (``complaint``, ``age_ambiguous``) are therefore never replaced:
    an empty complaint stays the recorded one and an ambiguity flag can never be downgraded by
    a later extraction. The inputs are not mutated; a new ``CaseInput`` is returned only when
    at least one field is filled.

    ``age_ambiguous`` is a fail-closed flag: ``True`` (an ambiguous or months-expressed age)
    must survive a re-extract that reports ``False``, because downgrading it would let a
    paediatric case be scored as an adult (D-03). Keeping every non-``None`` value is what
    guarantees that without a special case.
    """
    updates = {
        name: getattr(extracted, name)
        for name in CaseInput.model_fields
        if getattr(current, name) is None and getattr(extracted, name) is not None
    }
    return current.model_copy(update=updates) if updates else current
