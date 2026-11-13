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

from triagedesk.core.rules import get_discriminators, get_text_terms
from triagedesk.core.schema import ExtractionResult, MatchResult

# The ONE token pattern: lower-case alphanumeric runs. It is applied to both the
# complaint and every alias, so the two sides are normalised identically and a
# match is always boundary-respecting.
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Negation scope (D-05, SAFE-01). A nurse documents what a patient *denies*; an
# alias behind a negator must not raise a colour. The scope is deliberately
# lexical, not clinical: a negator applies until the next clause boundary. The
# negator and boundary words live in ``data/text_terms.yaml`` (CONVENTIONS §1).
#
# Punctuation between two tokens also ends the scope (a new clause).
_CLAUSE_BREAKS = frozenset({",", ";", ".", "!", "?"})
# A bounded lookback keeps one negator from reaching across a long sentence.
_NEGATION_LOOKBACK = 8


def _tokens_with_spans(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Tokenise *text* and keep each token's character span.

    The spans let :func:`_is_negated` see the punctuation between two tokens —
    information the token list itself discards.
    """
    matches = list(_TOKEN_PATTERN.finditer(text.lower()))
    return [match.group(0) for match in matches], [
        (match.start(), match.end()) for match in matches
    ]


def _is_negated(
    tokens: list[str],
    spans: list[tuple[int, int]],
    text: str,
    index: int,
) -> bool:
    """True when the finding starting at *index* is inside a negation scope.

    Walk backwards from the token before the match. A negator wins immediately; a
    boundary token or intervening punctuation ends the scope. ``not only`` is a
    additive phrase, not a negation, so it is skipped.
    """
    terms = get_text_terms()
    lower = text.lower()
    stop = max(0, index - _NEGATION_LOOKBACK)
    for position in range(index - 1, stop - 1, -1):
        token = tokens[position]
        if token in terms.negators:
            if (
                token == "not"
                and position + 1 < len(tokens)
                and tokens[position + 1] == "only"
            ):
                continue
            return True
        if token in terms.negation_boundaries:
            return False
        gap = lower[spans[position][1] : spans[position + 1][0]]
        if any(break_char in gap for break_char in _CLAUSE_BREAKS):
            return False
    return False


def _has_unnegated_sequence(
    haystack: list[str],
    needle: list[str],
    spans: list[tuple[int, int]],
    text: str,
) -> bool:
    """True when *needle* occurs as a contiguous token sequence outside a negation."""
    span = len(needle)
    if span == 0:
        return False
    for index in range(len(haystack) - span + 1):
        if haystack[index : index + span] == needle and not _is_negated(
            haystack, spans, text, index
        ):
            return True
    return False


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


def tokenize_with_spans(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Public span-aware tokenisation for the other consumer of the phrase rule.

    Retrieval reuses this and :func:`alias_matches`, so it can never diverge from the
    matcher on a negated phrase (WR-01 regression).
    """
    return _tokens_with_spans(text)


def alias_matches(
    text: str,
    tokens: list[str],
    spans: list[tuple[int, int]],
    alias: str,
) -> bool:
    """True when *alias* is an unnegated contiguous token phrase of *text*."""
    alias_tokens = _tokens(alias)
    return bool(alias_tokens) and _has_unnegated_sequence(tokens, alias_tokens, spans, text)


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

    A finding the note negates ("no chest pain", "not confused", "denies
    shortness of breath") is not a positive finding and must not raise a colour,
    so an alias inside a negation scope is suppressed (SAFE-01, nurse stress
    test S1-1). Only the alias is suppressed; a genuine finding elsewhere in the
    same complaint still matches.
    """
    substrate = get_discriminators()
    tokens, spans = _tokens_with_spans(complaint)

    matched: set[str] = set()
    for discriminator in substrate.discriminators:
        for alias in discriminator.aliases:
            if _has_unnegated_sequence(tokens, _tokens(alias), spans, complaint):
                matched.add(discriminator.id)
                break

    if not matched:
        return MatchResult(
            matched_ids=[],
            no_match=True,
            warning=substrate.no_match.warning,
            # The matcher alone cannot tell "no discriminator applies" from "retrieval missed"
            # — it has no note and no context. It reports the neutral closed-set fact; the
            # composing tool overwrites this with the coverage verdict (COV-01).
            retrieval_status="no_candidate",
        )
    return MatchResult(
        matched_ids=sorted(matched),
        no_match=False,
        warning=None,
        retrieval_status="matched",
    )


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


def filter_discriminator_ids(result: ExtractionResult) -> ExtractionResult:
    """Constrain a model extraction's ids to the closed set — the ONE filter home (D-06).

    The model may only *structure* a note; it may not choose a discriminator outside the
    closed set declared in ``data/sats_discriminators.yaml``. Every caller that receives a
    model ``ExtractionResult`` — the owned ``normalize_case`` tool and the desk's online
    extraction seam — goes through this function, so the "unknown ids are dropped and
    ``no_discriminator_matched`` follows what survives" rule is stated exactly once
    (T-02-11, DRY).
    """
    ids = validate_discriminator_ids(result.matched_discriminator_ids)
    return result.model_copy(
        update={"matched_discriminator_ids": ids, "no_discriminator_matched": not ids}
    )
