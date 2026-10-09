"""Deterministic alias matcher tests (Plan 02-02, D-05/D-06, SAFE-01, TOOL-02).

The matcher is proven to be a *deterministic alias lookup* over the closed
discriminator set: known alias phrases resolve to their id, short aliases never
fire inside unrelated words (the false-positive collision case), unknown
complaints return the explicit ``no_match`` (never a guess), and every returned id
is a member of the closed set. Expectations are derived from the loaded data — no
SATS alias or category is restated as an expected value (CONVENTIONS §1).
"""

from __future__ import annotations

import pytest

from triagedesk.core import matcher
from triagedesk.core.rules import DiscriminatorRules, get_discriminators
from triagedesk.core.schema import MatchResult


@pytest.fixture(scope="module")
def rules() -> DiscriminatorRules:
    """The discriminator substrate, loaded once through the one loader (D-08)."""
    return get_discriminators()


def _id_for_alias(rules: DiscriminatorRules, alias: str) -> str:
    """The id of the (unique) discriminator declaring *alias*."""
    return next(disc.id for disc in rules.discriminators if alias in disc.aliases)


def _closed_set(rules: DiscriminatorRules) -> set[str]:
    return {disc.id for disc in rules.discriminators}


def test_known_alias_phrase_returns_its_id(rules: DiscriminatorRules) -> None:
    expected = _id_for_alias(rules, "chest pain")
    result = matcher.match_discriminators("Patient reports chest pain on exertion")
    assert result.no_match is False
    assert expected in result.matched_ids


def test_matching_is_case_and_whitespace_insensitive(rules: DiscriminatorRules) -> None:
    expected = _id_for_alias(rules, "chest pain")
    result = matcher.match_discriminators("  CHEST\t PAIN  ")
    assert expected in result.matched_ids


def test_every_matching_discriminator_is_collected(rules: DiscriminatorRules) -> None:
    chest = _id_for_alias(rules, "chest pain")
    breath = _id_for_alias(rules, "shortness of breath")
    result = matcher.match_discriminators("chest pain and shortness of breath")
    assert {chest, breath} <= set(result.matched_ids)


def test_short_alias_does_not_fire_inside_an_unrelated_word(
    rules: DiscriminatorRules,
) -> None:
    """The false-positive collision case: boundaries, not raw substrings.

    "hypothermia" must not trigger the ``hypo`` alias and "sobbing" must not
    trigger the ``sob`` alias — unrelated words never raise the colour.
    """
    hypo_id = _id_for_alias(rules, "hypo")
    sob_id = _id_for_alias(rules, "sob")
    result = matcher.match_discriminators("The patient has hypothermia and is sobbing")
    assert hypo_id not in result.matched_ids
    assert sob_id not in result.matched_ids
    assert result.no_match is True, (
        f"an unrelated-word complaint matched {result.matched_ids!r} — substring leakage"
    )


def test_unmatched_complaint_returns_the_declared_no_match(
    rules: DiscriminatorRules,
) -> None:
    result = matcher.match_discriminators("the weather today is pleasant")
    assert result.no_match is True
    assert result.matched_ids == []
    assert result.warning == rules.no_match.warning


def test_ids_are_always_members_of_the_closed_set(rules: DiscriminatorRules) -> None:
    closed = _closed_set(rules)
    for complaint in (
        "chest pain",
        "active seizure",
        "abdominal pain",
        "nothing matches this sentence",
    ):
        result = matcher.match_discriminators(complaint)
        assert set(result.matched_ids) <= closed, (
            f"{complaint!r} produced ids outside the closed set: {result.matched_ids!r}"
        )


def test_repeated_calls_return_identical_sorted_ids() -> None:
    complaint = "chest pain with shortness of breath and vomiting blood"
    first = matcher.match_discriminators(complaint)
    second = matcher.match_discriminators(complaint)
    assert first.matched_ids == second.matched_ids
    assert first.matched_ids == sorted(first.matched_ids), "ids are not deterministically sorted"


async def test_owned_server_exposes_the_match_discriminators_tool() -> None:
    """TOOL-02: the owned server exposes match_discriminators over the shared contract."""
    from mcp import Client

    from triagedesk.mcp import server as server_module

    async with Client(server_module.server) as client:
        listed = await client.list_tools()
        call = await client.call_tool("match_discriminators", {"complaint": "chest pain"})

    names = {tool.name for tool in listed.tools}
    assert "match_discriminators" in names, f"owned server missing the tool: {names}"
    assert not call.is_error, f"match_discriminators tool errored: {call}"

    parsed = MatchResult.model_validate_json(call.content[0].text)
    assert parsed.matched_ids == matcher.match_discriminators("chest pain").matched_ids
