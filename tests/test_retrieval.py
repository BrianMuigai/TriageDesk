"""Contract-shape and safety proofs for the pure retrieval capability (D9-01..D9-04, D9-09, D9-10).

AGENT-03, Phase-9 SC2: a free-text complaint is ranked into attributed, closed-set
discriminator passages under a contract in which a colour is *unrepresentable* — the
evidence contract has no colour/target/priority field, retrieval is deterministic, every
returned id is a member of the closed set read through the ONE loader, the ONE citation
helper builds every excerpt citation, and E-09's vague complaint stays an honest
``no_match`` (never tuned green with an alias). Offline and deterministic — the pure
module only; no model, no MCP subprocess.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from triagedesk.core import matcher, retrieval
from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import EvidencePassage, EvidenceResult
from triagedesk.evals.case import load_cases

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

# Field-name tokens that would mark a colour/priority smuggled onto the evidence contract.
_FORBIDDEN_FIELD_TOKENS = ("colour", "color", "target", "priority", "destination")


def _closed_id_set() -> set[str]:
    """The closed discriminator id set, derived from the ONE loader (D9-10)."""
    return {discriminator.id for discriminator in get_discriminators().discriminators}


def _seed_complaint() -> str:
    """A complaint built FROM a declared alias, so a match is guaranteed (never a literal)."""
    return get_discriminators().discriminators[0].aliases[0]


def test_retrieve_is_deterministic() -> None:
    """The same complaint yields an identical ranked result on repeat calls (D9-02)."""
    complaint = _seed_complaint()
    assert retrieval.retrieve(complaint) == retrieval.retrieve(complaint)


def test_returned_ids_are_members_of_the_closed_set() -> None:
    """Every returned id is in the loader-derived closed set, and the set is non-vacuous (D9-10)."""
    closed = _closed_id_set()
    assert closed, "the loader-derived closed set is empty — the guard would be vacuous"

    result = retrieval.retrieve(_seed_complaint())
    assert result.passages, "a complaint built from a declared alias must retrieve a passage"
    assert {passage.discriminator_id for passage in result.passages} <= closed


def test_rank_is_one_based_and_ordered_by_score_desc_then_id() -> None:
    """Passages are ranked 1..n and ordered by (score desc, discriminator_id asc) (D9-02)."""
    result = retrieval.retrieve(_seed_complaint())
    ranks = [passage.rank for passage in result.passages]
    assert ranks == list(range(1, len(result.passages) + 1))
    keys = [(-passage.score, passage.discriminator_id) for passage in result.passages]
    assert keys == sorted(keys)
    assert len(result.passages) <= retrieval.MAX_PASSAGES


def test_contract_carries_no_float_or_colour_field() -> None:
    """No evidence field is a float or colour-named, so a colour is unrepresentable (D9-03)."""
    for model in (EvidenceResult, EvidencePassage):
        for name, field in model.model_fields.items():
            assert field.annotation is not float, f"{model.__name__}.{name} is a float"
            lowered = name.lower()
            offenders = [token for token in _FORBIDDEN_FIELD_TOKENS if token in lowered]
            assert not offenders, f"{model.__name__}.{name} reads as {offenders}"

    # The serialised result carries no colour token as a key or as a scalar value.
    colours = {band.colour for band in get_tews().tews_to_colour}
    assert colours, "the loader-derived colour set is empty — the guard would be vacuous"
    dumped = retrieval.retrieve(_seed_complaint()).model_dump()
    keys: set[str] = set()
    values: set[Any] = set()
    _collect(dumped, keys, values)
    assert not colours & keys, f"a colour appears as a JSON key: {colours & keys}"
    assert not colours & values, f"a colour appears as a JSON value: {colours & values}"


def _collect(node: Any, keys: set[str], values: set[Any]) -> None:
    """Recursively collect every mapping key and scalar leaf from a dumped payload."""
    if isinstance(node, dict):
        keys.update(str(key) for key in node)
        for value in node.values():
            _collect(value, keys, values)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _collect(value, keys, values)
    else:
        values.add(node)


def test_contract_rejects_an_undeclared_field() -> None:
    """``extra="forbid"`` rejects a smuggled field (including a colour) at construction (D9-03)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EvidenceResult(passages=[], no_match=False, reason="", colour="RED")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        EvidencePassage(  # type: ignore[call-arg]
            discriminator_id="x", label="l", citation="c", score=1, rank=1, target="now"
        )


def test_e09_vague_complaint_is_an_honest_no_match() -> None:
    """E-09's complaint returns an explicit ``no_match`` with no passages (D9-09, never tuned)."""
    spec = next(case for case in load_cases(CASES_DIR) if case.id == "E-09")
    result = retrieval.retrieve(spec.case.complaint)
    assert result.no_match is True
    assert result.passages == []


def test_no_match_reason_is_read_from_the_substrate() -> None:
    """A nonsense complaint's reason equals the substrate ``no_match.warning`` (never restated)."""
    result = retrieval.retrieve("zzz qqq nonsense")
    assert result.no_match is True
    assert result.reason == get_discriminators().no_match.warning


def test_empty_and_whitespace_complaints_are_no_match() -> None:
    """An empty or whitespace-only complaint is an explicit ``no_match``."""
    for complaint in ("", "   \t\n"):
        result = retrieval.retrieve(complaint)
        assert result.no_match is True
        assert result.passages == []


def test_there_is_one_normalisation_owner() -> None:
    """Retrieval reuses the matcher's tokeniser — no second token pattern (DRY, D9 discretion)."""
    assert retrieval.tokenize is matcher.tokenize
    source = (REPO_ROOT / "src" / "triagedesk" / "core" / "retrieval.py").read_text(
        encoding="utf-8"
    )
    assert "re.compile" not in source
