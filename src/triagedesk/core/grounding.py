"""Ground every sign an extraction claims against the note it came from (D-05, D-06).

The model may only *structure* a note and *select* ids from the closed set; it is never
trusted to have seen what it reports. This module is the ONE evidence check at the owned
tool boundary: a discriminator id survives only when one of its declared aliases occurs
as an unnegated contiguous token phrase of the note.

Grounding is monotone removal: it can drop evidence but never add it. It constructs no
id, invents no value and touches no colour, target or destination — the deterministic
scorer remains the only place a colour is computed (D-01, D-03).

Pure module: it imports nothing from ``llm`` / ``mcp`` / ``store`` (D-13) and reads the
alias substrate only through the one loader (``core/rules.py``). No alias, colour, band
or threshold is inlined here (CONVENTIONS §1).
"""

from __future__ import annotations

from triagedesk.core import matcher
from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import ExtractionResult


def ground_extraction(result: ExtractionResult, note: str) -> ExtractionResult:
    """Keep only the extracted evidence the note itself states — removal, never addition.

    The closed-set filter remains the ONE authority for which ids are candidates; this
    function then keeps an id only when at least one alias declared for it in
    ``data/sats_discriminators.yaml`` is an unnegated contiguous token phrase of *note*
    (the matcher's own boundary and negation rule). ``no_discriminator_matched`` follows
    what survives, so the shipped deferral path applies unchanged.
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
    return filtered.model_copy(
        update={
            "matched_discriminator_ids": kept,
            "no_discriminator_matched": not kept,
        }
    )


__all__ = ["ground_extraction"]
