"""Shape tests for the discriminator single source of truth (D-08, D-11, INTAKE-05).

Assert the data is well-formed and that matching can be a *deterministic alias
lookup with an explicit no-match* (D-11): every discriminator carries an id, a
category that exists, a non-empty label and at least one alias; ids are unique;
no alias is ambiguous across discriminators; and an explicit ``no_match`` entry
exists.

The expected colours of specific eval cases are deliberately NOT encoded here —
that belongs to Phase 4 (Pitfall 11: never freeze expectations in the rules'
own tests).
"""

from __future__ import annotations

import pytest

from triagedesk.core.rules import DiscriminatorRules, get_discriminators


@pytest.fixture(scope="module")
def rules() -> DiscriminatorRules:
    """The discriminator substrate, loaded once through the one loader (D-08)."""
    return get_discriminators()


def test_every_discriminator_is_well_formed(rules: DiscriminatorRules) -> None:
    for disc in rules.discriminators:
        assert disc.id, "discriminator without an id"
        assert disc.category in rules.categories, (
            f"{disc.id}: category {disc.category!r} is not declared in `categories`"
        )
        assert disc.label.strip(), f"{disc.id}: empty label"
        assert disc.aliases, f"{disc.id}: no aliases"
        assert all(a.strip() for a in disc.aliases), f"{disc.id}: blank alias"


def test_ids_are_unique(rules: DiscriminatorRules) -> None:
    ids = [disc.id for disc in rules.discriminators]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate discriminator ids: {sorted(duplicates)}"


def test_aliases_are_unambiguous_across_discriminators(rules: DiscriminatorRules) -> None:
    """No alias string maps to more than one discriminator (case-insensitive)."""
    index: dict[str, set[str]] = {}
    for disc in rules.discriminators:
        for alias in disc.aliases:
            index.setdefault(alias.casefold().strip(), set()).add(disc.id)
    ambiguous = {alias: sorted(ids) for alias, ids in index.items() if len(ids) > 1}
    assert not ambiguous, f"aliases matched by more than one discriminator: {ambiguous}"


def test_every_category_is_used(rules: DiscriminatorRules) -> None:
    used = {disc.category for disc in rules.discriminators}
    assert used == set(rules.categories), (
        f"declared-but-unused or used-but-undeclared categories: "
        f"declared={sorted(rules.categories)} used={sorted(used)}"
    )


def test_every_category_maps_to_a_colour(rules: DiscriminatorRules) -> None:
    for name, category in rules.categories.items():
        assert category.colour, f"category {name}: no colour"
        assert category.citation_ref, f"category {name}: no citation_ref"
    colours = [c.colour for c in rules.categories.values()]
    assert len(colours) == len(set(colours)), f"two categories share a colour: {colours}"


def test_explicit_no_match_entry_exists(rules: DiscriminatorRules) -> None:
    assert rules.no_match.result, "no_match.result is empty"
    assert rules.no_match.warning, "no_match.warning is empty"


def test_alias_lookup_is_deterministic_and_reports_no_match(
    rules: DiscriminatorRules,
) -> None:
    """A pure alias lookup returns the declared id, and an unknown complaint returns None."""
    index = {
        alias.casefold(): disc.id for disc in rules.discriminators for alias in disc.aliases
    }
    for disc in rules.discriminators:
        for alias in disc.aliases:
            assert index[alias.casefold()] == disc.id
    # Nothing matched -> the matcher's explicit no-match outcome, never a guess.
    assert index.get("__no_such_complaint__") is None
