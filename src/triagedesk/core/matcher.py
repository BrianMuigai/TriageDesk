"""Deterministic discriminator alias matcher (D-05, D-06, SAFE-01).

A complaint is free, untrusted text (SECURITY.md T-1). This module turns it into
ids from the *closed* discriminator set declared in
``data/sats_discriminators.yaml`` — or the explicit ``no_match`` outcome — using
nothing but a deterministic alias lookup. There is no model and no fuzzy
judgement on this path (D-02), and the colour is never read from the complaint,
so injected or omitted text cannot set a priority (D-05).

Aliases match on word/token boundaries, never as raw substrings: the complaint is
tokenised with a fixed word pattern and each alias is matched as a contiguous
token sequence, so a short alias cannot fire inside an unrelated word
("hypothermia" never triggers ``hypo``; "sobbing" never triggers ``sob``).

Pure module: it imports nothing from ``llm`` / ``mcp`` / ``store`` (D-13) and
reads the discriminator substrate only through the one loader (``core/rules.py``).
No alias, category or colour is inlined here (CONVENTIONS §1).
"""

from __future__ import annotations

import re

from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import MatchResult

# The ONE token pattern: lower-case alphanumeric runs. It is applied to both the
# complaint and every alias, so the two sides are normalised identically and a
# match is always boundary-respecting.
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Tokenise *text* into lower-case alphanumeric runs (the shared boundary rule).

    The ONE normalisation owner (CONVENTIONS §1): the matcher and the retrieval
    module both reuse this, so the two sides compare identically and no second
    token pattern is introduced. Behaviour is unchanged from the former private
    ``_tokens`` helper.
    """
    return _TOKEN_PATTERN.findall(text.lower())


# The internal name the call sites below (``match_discriminators``) and the module's
# former private helper used. It is an alias of the public ``tokenize`` so there is
# exactly ONE owner and no second regex anywhere.
_tokens = tokenize


def contains_sequence(haystack: list[str], needle: list[str]) -> bool:
    """True when *needle* appears as a contiguous token sequence of *haystack*.

    The ONE boundary-respecting phrase rule (CONVENTIONS §1): the matcher and the
    retrieval module both reuse this, so a phrase one admits the other admits too and
    no second matching semantics is introduced. ``["chest", "pain"]`` matches a
    complaint whose tokens contain that adjacent pair, while ``["hypo"]`` does not
    match the single unrelated token ``"hypothermia"``.
    """
    span = len(needle)
    if span == 0:
        return False
    return any(haystack[i : i + span] == needle for i in range(len(haystack) - span + 1))


def match_discriminators(complaint: str) -> MatchResult:
    """Match *complaint* to closed-set discriminator ids, or an explicit no_match.

    Deterministic and pure (D-05): the same input always yields the same, sorted
    id list. Only ids declared in the discriminator data are returned (D-06); an
    unmatched complaint yields ``no_match=True`` with the declared warning and an
    empty id list — never a guessed id.
    """
    substrate = get_discriminators()
    tokens = _tokens(complaint)

    matched: set[str] = set()
    for discriminator in substrate.discriminators:
        for alias in discriminator.aliases:
            if contains_sequence(tokens, _tokens(alias)):
                matched.add(discriminator.id)
                break

    if not matched:
        return MatchResult(
            matched_ids=[],
            no_match=True,
            warning=substrate.no_match.warning,
        )
    return MatchResult(matched_ids=sorted(matched), no_match=False, warning=None)


def validate_discriminator_ids(ids: list[str]) -> list[str]:
    """Filter *ids* to the closed discriminator set, dropping any unknown id (D-06).

    The ONE authority for constraining model-returned ids: a caller (e.g. the
    owned ``normalize_case`` tool) may not trust the model's id list, so ids that
    are not declared in ``data/sats_discriminators.yaml`` are dropped rather than
    passed downstream (T-02-11). The result is deduplicated and sorted, so
    repeated identical model output yields an identical constrained list — the
    matcher never invents an id.
    """
    closed = {discriminator.id for discriminator in get_discriminators().discriminators}
    return sorted({id_ for id_ in ids if id_ in closed})
