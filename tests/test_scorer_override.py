"""Most-urgent-wins discriminator override tests (Plan 02-02, SCORE-02, T-02-08).

The override raises the TEWS colour to the most urgent matched discriminator
category and never lowers it: the winning category's colour, target time and
destination are read from ``data/*.yaml``, the result is independent of the order
the matched ids arrive in, and a lower-urgency match cannot override a higher
TEWS colour. Every expected value is derived from the loaded data — no SATS
colour, category or target is restated here (CONVENTIONS §1).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from triagedesk.core import scorer
from triagedesk.core.rules import (
    Band,
    DiscriminatorRules,
    Parameter,
    TewsRules,
    get_discriminators,
    get_tews,
)
from triagedesk.core.schema import CaseInput


@pytest.fixture(scope="module")
def tews() -> TewsRules:
    return get_tews()


@pytest.fixture(scope="module")
def disc() -> DiscriminatorRules:
    return get_discriminators()


def _case_with(pick: Callable[[Parameter], Band]) -> CaseInput:
    """A complete adult case whose every vital sits in the band chosen by *pick*."""
    rules = get_tews()
    values: dict[str, object] = {}
    for name, param in rules.parameters.items():
        field = scorer.case_field(name)
        band = pick(param)
        if field == "trauma":
            values[field] = band.points > 0
        else:
            values[field] = (
                band.value if band.value is not None else (band.min if band.min is not None else band.max)
            )
    values["age_years"] = rules.out_of_scope.adult_min_age_years + 1
    return CaseInput(**values)


def _low_case() -> CaseInput:
    """All vitals at their lowest-points band -> the least urgent TEWS colour."""
    return _case_with(lambda p: min(p.bands, key=lambda b: b.points))


def _high_case() -> CaseInput:
    """All vitals at their highest-points band -> the most urgent TEWS colour."""
    return _case_with(lambda p: max(p.bands, key=lambda b: b.points))


def _ids_in_category(disc: DiscriminatorRules, category: str) -> list[str]:
    return [d.id for d in disc.discriminators if d.category == category]


def _categories_by_urgency(tews: TewsRules, disc: DiscriminatorRules) -> list[str]:
    """Category names ordered least -> most urgent, derived from the TEWS colours."""
    urgency = {band.colour: band.min for band in tews.tews_to_colour}
    return sorted(disc.categories, key=lambda name: urgency[disc.categories[name].colour])


def test_a_more_urgent_discriminator_overrides_low_vitals(
    tews: TewsRules, disc: DiscriminatorRules
) -> None:
    case = _low_case()
    baseline = scorer.score_priority(case)
    winner = _categories_by_urgency(tews, disc)[-1]
    colour = disc.categories[winner].colour

    result = scorer.score_priority(case, _ids_in_category(disc, winner))

    assert result.colour == colour
    assert result.colour != baseline.colour, "a more urgent discriminator did not override"
    assert result.target == tews.target_times[colour].target
    assert result.destination == tews.target_times[colour].destination


def test_most_urgent_category_wins_independent_of_input_order(
    tews: TewsRules, disc: DiscriminatorRules
) -> None:
    order = _categories_by_urgency(tews, disc)
    least, most = order[0], order[-1]
    ids = _ids_in_category(disc, least) + _ids_in_category(disc, most)
    case = _low_case()

    forward = scorer.score_priority(case, list(ids))
    reversed_ = scorer.score_priority(case, list(reversed(ids)))

    assert forward.colour == disc.categories[most].colour
    assert reversed_.colour == forward.colour
    assert reversed_.target == forward.target
    assert reversed_.destination == forward.destination


def test_empty_matched_set_leaves_the_tews_colour_unchanged(
    tews: TewsRules,
) -> None:
    case = _low_case()
    baseline = scorer.score_priority(case)
    result = scorer.score_priority(case, [])
    assert result.colour == baseline.colour
    assert result.target == baseline.target
    assert result.destination == baseline.destination


def test_a_lower_urgency_discriminator_cannot_lower_a_higher_colour(
    tews: TewsRules, disc: DiscriminatorRules
) -> None:
    case = _high_case()
    baseline = scorer.score_priority(case)
    least = _categories_by_urgency(tews, disc)[0]
    urgency = {band.colour: band.min for band in tews.tews_to_colour}
    if urgency[disc.categories[least].colour] >= urgency[baseline.colour]:
        pytest.skip("baseline TEWS colour is not more urgent than the least category")

    result = scorer.score_priority(case, _ids_in_category(disc, least))

    assert result.colour == baseline.colour, "a lower-urgency match lowered the colour"
    assert result.target == baseline.target
    assert all(rule.rule_id != least for rule in result.triggered_rules)


def test_override_rule_is_cited_and_citations_match_triggered_rules(
    tews: TewsRules, disc: DiscriminatorRules
) -> None:
    winner = _categories_by_urgency(tews, disc)[-1]
    result = scorer.score_priority(_low_case(), _ids_in_category(disc, winner))

    assert result.citations == [rule.citation for rule in result.triggered_rules]
    override_rules = [rule for rule in result.triggered_rules if rule.rule_id == winner]
    assert len(override_rules) == 1, "the firing category must be triggered exactly once"
    assert disc.categories[winner].citation_ref in override_rules[0].citation


def test_unknown_discriminator_ids_are_ignored(tews: TewsRules) -> None:
    case = _low_case()
    baseline = scorer.score_priority(case)
    result = scorer.score_priority(case, ["__not_a_discriminator__"])
    assert result.colour == baseline.colour
    assert result.target == baseline.target
