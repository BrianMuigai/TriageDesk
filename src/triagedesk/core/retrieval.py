"""Pure deterministic lexical retrieval of attributed SATS KB excerpts
(D9-01, D9-02, D9-03, D9-04, D9-10).

A free-text complaint is ranked into attributed, closed-set discriminator passages
by one pure, deterministic function — no model, no MCP client, no I/O. It *shows*
the evidence that could ground a colour but can never *set* one: the contract it
returns (:class:`~triagedesk.core.schema.EvidenceResult`) has no colour field, so
a colour is unrepresentable rather than merely unused (D9-03, Phase-9 SC2).

This module imports nothing from ``llm`` / ``mcp`` / ``store`` (enforced by
``tests/test_purity.py``). The corpus is read ONLY through the one loader
(``core/rules.py``) — the discriminator catalogue and its categories — so no
label, alias, colour or citation is inlined here (CONVENTIONS §1, D9-01). Every
returned ``discriminator_id`` is a member of the closed set declared in
``data/sats_discriminators.yaml`` (D9-10), read through that loader.

The ranking is an in-house, deterministic integer lexical scorer — no embeddings,
no vector database, no ``rank-bm25`` (D9-02). A tie is broken explicitly on
``(score desc, discriminator_id asc)`` so the same complaint always yields the
same ranking, reproducibly and offline.
"""

from __future__ import annotations

from triagedesk.core.citations import format_citation
from triagedesk.core.matcher import contains_sequence, tokenize
from triagedesk.core.rules import Discriminator, get_discriminators
from triagedesk.core.schema import EvidencePassage, EvidenceResult

# The match bar (D9-02): a passage is admitted only when a complete alias phrase
# appears in the complaint. A partial token overlap must never fabricate a passage
# — a single stray token is not evidence of a clinical discriminator. Named and
# deterministic; never a value tuned to make a test green.
MATCH_MIN_SCORE: int = 1

# The evidence payload is bounded (D9-03): retrieval is a short, reviewable list of
# attributed excerpts, not a dump of the whole catalogue. Named and deterministic.
MAX_PASSAGES: int = 5


def _score(discriminator: Discriminator, complaint_tokens: list[str]) -> int:
    """The lexical score of *discriminator* against the complaint tokens (D9-02).

    Returns the length in tokens of the longest alias of *discriminator* that appears
    as a CONTIGUOUS token phrase of the complaint, or ``0`` when no alias appears. The
    phrase rule is the matcher's own (:func:`contains_sequence`), so retrieval and the
    deterministic matcher agree on which discriminators a complaint names: retrieval
    never fabricates a passage the matcher rejects. A set-subset, order-insensitive
    match would fire on a negated phrase ("patient is breathing, no distress" matching
    the alias "no breathing"), which is exactly the misleading grounding this channel
    must not produce. Both sides are tokenised through the ONE normalisation owner
    (:func:`tokenize`), so the comparison is boundary-respecting and reproducible.
    """
    best = 0
    for alias in discriminator.aliases:
        alias_tokens = tokenize(alias)
        if alias_tokens and contains_sequence(complaint_tokens, alias_tokens):
            best = max(best, len(alias_tokens))
    return best


def retrieve(complaint: str) -> EvidenceResult:
    """Rank *complaint* into attributed, closed-set discriminator passages (D9-04).

    Reads the discriminator substrate once through the ONE loader, scores every
    declared discriminator with :func:`_score`, keeps only those clearing
    ``MATCH_MIN_SCORE``, orders them by ``(-score, discriminator_id)`` (ties broken
    on the id ascending, so the ranking is deterministic), truncates to
    ``MAX_PASSAGES`` and assigns a 1-based ``rank``. Each passage's ``citation`` is
    built by the ONE citation helper from the discriminator's own category
    ``citation_ref`` and the substrate ``citation``; the ``label`` and
    ``discriminator_id`` come from the discriminator itself, so an id outside the
    closed set is unconstructible (D9-10).

    When nothing clears the bar — including an empty or whitespace-only complaint —
    the explicit ``no_match`` result carries the substrate's own coverage-gap
    ``no_match.warning`` READ from the data (never restated in code; D9-09).
    """
    substrate = get_discriminators()
    complaint_tokens = tokenize(complaint)

    scored = [
        (discriminator, _score(discriminator, complaint_tokens))
        for discriminator in substrate.discriminators
    ]
    matched = sorted(
        ((discriminator, score) for discriminator, score in scored if score >= MATCH_MIN_SCORE),
        key=lambda pair: (-pair[1], pair[0].id),
    )[:MAX_PASSAGES]

    if not matched:
        return EvidenceResult(no_match=True, reason=substrate.no_match.warning)

    passages = [
        EvidencePassage(
            discriminator_id=discriminator.id,
            label=discriminator.label,
            citation=format_citation(
                substrate.categories[discriminator.category].citation_ref,
                substrate.citation,
            ),
            score=score,
            rank=rank,
        )
        for rank, (discriminator, score) in enumerate(matched, start=1)
    ]
    return EvidenceResult(
        passages=passages,
        no_match=False,
        reason=f"{len(passages)} discriminator(s) matched the complaint",
    )


__all__ = ["MATCH_MIN_SCORE", "MAX_PASSAGES", "retrieve"]
