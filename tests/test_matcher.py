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


# Lay/OPD phrasing the nurse stress test logged as unmatched (report S2-1). Each phrase
# must now reach the discriminator that declares *anchor_alias* — the declared alias
# naming the same clinical finding. The id is never restated here: it is read from the
# loaded substrate through ``_id_for_alias`` (CONVENTIONS §1).
_LAY_PHRASING: tuple[tuple[str, str], ...] = (
    ("can't catch my breath", "shortness of breath"),
    ("can't catch his breath", "shortness of breath"),
    ("can't catch her breath", "shortness of breath"),
    ("hard to breathe", "shortness of breath"),
    ("struggling to breathe", "shortness of breath"),
    ("trouble breathing", "shortness of breath"),
    ("tight chest", "chest pain"),
    ("chest feels tight", "chest pain"),
    ("heavy chest", "chest pain"),
    ("heart attack", "chest pain"),
    ("passed out", "reduced level of consciousness"),
    ("fainted", "reduced level of consciousness"),
    ("blacked out", "reduced level of consciousness"),
    ("car crash", "high energy transfer"),
    ("car accident", "high energy transfer"),
    ("road traffic accident", "high energy transfer"),
    ("rta", "high energy transfer"),
    ("motorbike accident", "high energy transfer"),
    ("motor vehicle crash", "high energy transfer"),
    ("broken arm", "closed fracture"),
    ("broken leg", "closed fracture"),
    ("broken wrist", "closed fracture"),
    ("broken ankle", "closed fracture"),
    ("broken bone", "closed fracture"),
    ("fractured arm", "closed fracture"),
    ("fractured leg", "closed fracture"),
    ("fractured wrist", "closed fracture"),
    ("fractured ankle", "closed fracture"),
    ("stomach ache", "abdominal pain"),
    ("tummy ache", "abdominal pain"),
)


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


@pytest.mark.parametrize(("phrase", "anchor_alias"), _LAY_PHRASING)
def test_lay_phrasing_matches_its_declared_discriminator(
    rules: DiscriminatorRules, phrase: str, anchor_alias: str
) -> None:
    """Lay/OPD phrasing reaches its discriminator instead of deferring (report S2-1).

    Every phrase here returned ``no_match`` before this task; it now resolves to the
    discriminator that declares *anchor_alias*.
    """
    expected = _id_for_alias(rules, anchor_alias)
    result = matcher.match_discriminators(phrase)
    assert result.no_match is False, f"{phrase!r} still defers"
    assert expected in result.matched_ids, f"{phrase!r} did not reach {expected!r}"


def test_every_declared_alias_matches_through_the_matcher(
    rules: DiscriminatorRules,
) -> None:
    """Every declared alias still matches through the matcher (the expansion shadows none).

    The sweep also pins aliases that begin with a negator (``no pulse``, ``not alert``):
    the negation scope must keep admitting them as positive findings.
    """
    failures = [
        f"{disc.id}: {alias!r} -> {matcher.match_discriminators(alias).matched_ids!r}"
        for disc in rules.discriminators
        for alias in disc.aliases
        if disc.id not in matcher.match_discriminators(alias).matched_ids
    ]
    assert failures == [], "\n".join(failures)


def test_a_negated_finding_does_not_match(rules: DiscriminatorRules) -> None:
    """A denied symptom is not a positive finding (nurse stress test S1-1)."""
    for complaint in (
        "no chest pain",
        "denies chest pain",
        "patient denies any chest pain",
        "not confused",
        "no shortness of breath",
    ):
        result = matcher.match_discriminators(complaint)
        assert result.matched_ids == [], (
            f"{complaint!r} produced a positive match {result.matched_ids!r} from a denial"
        )
        assert result.no_match is True


def test_negation_ends_at_a_contrast_or_conjunction(rules: DiscriminatorRules) -> None:
    """A finding after ``but``/``and`` is positive even if an earlier finding was denied."""
    breath = _id_for_alias(rules, "shortness of breath")
    chest = _id_for_alias(rules, "chest pain")

    after_but = matcher.match_discriminators("no fever but short of breath")
    assert breath in after_but.matched_ids, "the contrast did not end the negation scope"

    after_and = matcher.match_discriminators("no fever and chest pain")
    assert chest in after_and.matched_ids, "the conjunction did not end the negation scope"


def test_negation_continues_across_or(rules: DiscriminatorRules) -> None:
    """``no chest pain or shortness of breath`` denies both findings."""
    result = matcher.match_discriminators("no chest pain or shortness of breath")
    assert result.matched_ids == []
    assert result.no_match is True


def test_a_positive_finding_next_to_a_denied_one_still_matches(
    rules: DiscriminatorRules,
) -> None:
    chest = _id_for_alias(rules, "chest pain")
    breath = _id_for_alias(rules, "shortness of breath")
    result = matcher.match_discriminators("chest pain, no shortness of breath")
    assert chest in result.matched_ids
    assert breath not in result.matched_ids


def test_not_only_is_not_a_negation(rules: DiscriminatorRules) -> None:
    """``not only chest pain`` is an additive phrase, not a denial."""
    chest = _id_for_alias(rules, "chest pain")
    assert chest in matcher.match_discriminators("not only chest pain").matched_ids


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
