"""Deterministic retrieval-coverage classification (COV-01, COV-04).

The matcher answers *"which closed-set discriminators does this complaint name?"*. That
is not the same question as *"is there a discriminator here at all?"* — and conflating
them is what made a routine "sore throat" defer. This module answers the second
question with one pure, deterministic classifier:

* ``matched`` — an alias hit (the matcher's own authority).
* ``ambiguous`` — no alias hit, but a *strong* content token of the complaint (or a
  stated high-risk condition) points at a discriminator family. One question could
  resolve it, so the case is a clarification, not a dead end.
* ``no_candidate`` — nothing in the closed set is implicated: no discriminator applies,
  and the recorded vitals are the complete SATS basis.

The classifier **never admits an id into scoring**. ``matched_ids`` remain the matcher's
alone; a candidate here only decides whether to ask the nurse a question. That keeps the
safety property intact — retrieval can reduce coverage, never invent a colour.

Pure module: it imports nothing from ``llm`` / ``mcp`` / ``store`` (D-13). Every term,
stem rule and condition mapping is read from ``data/text_terms.yaml`` through the one
loader (CONVENTIONS §1); nothing is inlined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from triagedesk.core.matcher import match_discriminators, tokenize
from triagedesk.core.rules import get_discriminators, get_text_terms
from triagedesk.core.schema import RetrievalStatus

# The bound on a clarification (COV-03). Three questions is enough to disambiguate the
# families a single complaint can plausibly straddle, and short enough to ask at the
# desk. Named and structural — never tuned to a fixture.
MAX_CLARIFICATION_QUESTIONS = 3


@dataclass(frozen=True)
class CoverageVerdict:
    """The classifier's answer: a closed-set status, candidates, questions and a reason."""

    status: RetrievalStatus
    candidates: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    reason: str = ""


def _stem(token: str) -> str:
    """Apply the data-declared suffix rules conservatively (retrieval comparison only)."""
    for rule in get_text_terms().stems:
        if token.endswith(rule.suffix) and len(token) - len(rule.suffix) >= 3:
            return token[: len(token) - len(rule.suffix)] + rule.replacement
    return token


def _content_tokens(text: str) -> set[str]:
    """Stemmed content tokens: stopwords removed, nothing else altered."""
    stop = set(get_text_terms().stopwords)
    return {_stem(token) for token in tokenize(text) if token not in stop}


def _strong_tokens(text: str) -> set[str]:
    """Content tokens that can, on their own, implicate a discriminator family."""
    weak = set(get_text_terms().weak_terms)
    return {token for token in _content_tokens(text) if token not in weak}


@lru_cache(maxsize=1)
def _vocabulary() -> dict[str, set[str]]:
    """Stemmed token -> the closed-set discriminator ids whose wording contains it.

    Built once per process, beside the other substrate loaders: the catalogue is immutable
    data, so rebuilding it on every complaint would add latency to the desk path for nothing.
    """
    vocabulary: dict[str, set[str]] = {}
    for discriminator in get_discriminators().discriminators:
        for phrase in (discriminator.label, *discriminator.aliases):
            for token in _content_tokens(phrase):
                vocabulary.setdefault(token, set()).add(discriminator.id)
    return vocabulary


def _is_benign_review(complaint: str) -> bool:
    """True when routine-review phrasing dominates and no clinical token remains.

    A benign phrase is not a licence to ignore the rest of the sentence: "wound check,
    spurting" must still be a clarification. The phrases are removed first, and the case is
    benign only when **no** residual strong token appears in the discriminator vocabulary.
    """
    residual = complaint.lower()
    found = False
    for phrase in get_text_terms().benign_phrases:
        if phrase in residual:
            residual = residual.replace(phrase, " ")
            found = True
    if not found:
        return False
    vocabulary = _vocabulary()
    return not any(token in vocabulary for token in _strong_tokens(residual))


def _ordered(ids: list[str]) -> list[str]:
    """Order candidate ids by the substrate's category order, then id (deterministic).

    Category order is the YAML order — the manual's own urgency order — so the most
    urgent family is asked about first. An id the substrate does not declare is dropped
    rather than raising, so a data typo cannot crash the graph. No colour or threshold is
    read.
    """
    order = {
        category: index
        for index, category in enumerate(get_discriminators().categories)
    }
    by_id = {item.id: item for item in get_discriminators().discriminators}
    known = [id_ for id_ in ids if id_ in by_id]
    return sorted(known, key=lambda id_: (order.get(by_id[id_].category, 99), id_))


def question_for(discriminator_id: str) -> str:
    """One nurse-facing question naming a candidate discriminator (never a colour)."""
    by_id = {item.id: item for item in get_discriminators().discriminators}
    return f"Ask about: {by_id[discriminator_id].label}"


def _context(note: str) -> tuple[list[str], str]:
    """Candidate ids and the targeted question for a stated high-risk condition."""
    lower = note.lower()
    ids: list[str] = []
    question = ""
    for condition in get_text_terms().context_conditions:
        if any(term in lower for term in condition.terms):
            ids.extend(condition.discriminators)
            if not question:
                question = condition.clarify
    return _ordered(sorted(set(ids))), question


def classify(complaint: str, note: str = "") -> CoverageVerdict:
    """Classify *complaint* (optionally in the context of *note*) — pure and deterministic.

    Order matters: routine-review phrasing is stripped first, and it is benign only when no
    clinical token remains (a dressing check does not become a haemorrhage question, but a
    dressing check *with* spurting does); a stated high-risk condition is consulted only when
    the complaint itself offers no strong token, because a complaint that names a discriminator
    is already the stronger signal.
    """
    match = match_discriminators(complaint)
    if match.matched_ids:
        return CoverageVerdict(
            status="matched",
            candidates=list(match.matched_ids),
            reason="an alias of a closed-set discriminator matched",
        )

    if _is_benign_review(complaint):
        return CoverageVerdict(
            status="no_candidate",
            reason="routine review phrasing; no discriminator applies",
        )

    vocabulary = _vocabulary()
    hits: set[str] = set()
    for token in _strong_tokens(complaint):
        hits.update(vocabulary.get(token, set()))
    if hits:
        candidates = _ordered(list(hits))[:MAX_CLARIFICATION_QUESTIONS]
        return CoverageVerdict(
            status="ambiguous",
            candidates=candidates,
            questions=[question_for(id_) for id_ in candidates],
            reason="the complaint is near a discriminator family but names none",
        )

    context_ids, context_question = _context(note or complaint)
    if context_ids:
        candidates = context_ids[:MAX_CLARIFICATION_QUESTIONS]
        return CoverageVerdict(
            status="ambiguous",
            candidates=candidates,
            questions=[f"Check: {context_question}"] if context_question else [
                question_for(id_) for id_ in candidates
            ],
            reason=(
                f"a stated condition maps to a discriminator family; check {context_question}"
                if context_question
                else "a stated condition maps to a discriminator family"
            ),
        )

    return CoverageVerdict(
        status="no_candidate",
        reason="no discriminator applies; the recorded vitals are the complete basis",
    )


__all__ = [
    "MAX_CLARIFICATION_QUESTIONS",
    "CoverageVerdict",
    "classify",
    "question_for",
]
