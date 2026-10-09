"""Pure scorer + owned-tool contract tests (Plan 02-01, SCORE-01/SCORE-03, TOOL-03).

Two layers are exercised:

* the pure ``core.scorer.score_priority`` function, directly (no model, no MCP);
* the owned ``score_priority`` MCP tool over the SDK's in-memory client, whose
  payload must validate back to the shared ``PriorityResult`` contract.

Every expected value is derived from ``data/sats_tews.yaml`` through the one
loader — no SATS band or colour is restated here (CONVENTIONS §1).
"""

from __future__ import annotations

import math

from mcp import Client

from triagedesk.core import scorer
from triagedesk.core.rules import Parameter, TewsRules, get_tews
from triagedesk.core.schema import CaseInput, PriorityResult
from triagedesk.mcp import server as server_module

# A fixed adult case with complete vitals; the values are inputs, not expected
# outputs — the expected score is derived from the loaded data below.
ADULT = CaseInput(
    age_years=40,
    mobility="walking",
    respiratory_rate=24,
    heart_rate=118,
    systolic_bp=108,
    temperature_c=38.9,
    avpu="alert",
    trauma=False,
)


def _reference_points(param: Parameter, value: object) -> int:
    """Reference band points for *value*, read entirely from the loaded data."""
    if isinstance(value, bool):
        ordered = sorted(param.bands, key=lambda band: band.points)
        return ordered[-1].points if value else ordered[0].points
    if any(band.value is not None for band in param.bands):
        return next(band for band in param.bands if band.value == value).points
    for band in param.bands:
        low = band.min if band.min is not None else -math.inf
        high = band.max if band.max is not None else math.inf
        if low <= value <= high:
            return band.points
    raise AssertionError(f"reference matcher found no band for {value!r}")


def _reference_colour(rules: TewsRules, total: int) -> str:
    for band in rules.tews_to_colour:
        high = band.max if band.max is not None else math.inf
        if band.min <= total <= high:
            return band.colour
    raise AssertionError(f"no colour band covers TEWS total {total}")


def test_pure_score_returns_a_cited_colour_with_no_model() -> None:
    rules = get_tews()
    result = scorer.score_priority(ADULT)

    expected_tews = sum(
        _reference_points(param, getattr(ADULT, scorer.case_field(name)))
        for name, param in rules.parameters.items()
    )
    expected_colour = _reference_colour(rules, expected_tews)

    assert result.out_of_scope is False
    assert result.abstained is False
    assert result.tews == expected_tews
    assert result.colour == expected_colour
    assert result.target == rules.target_times[expected_colour].target
    assert result.destination == rules.target_times[expected_colour].destination


def test_pure_score_citations_match_triggered_rules_one_to_one() -> None:
    rules = get_tews()
    result = scorer.score_priority(ADULT)

    assert result.triggered_rules, "a non-trivial case should fire at least one rule"
    assert all(rule.points > 0 for rule in result.triggered_rules)
    assert len(result.citations) == len(result.triggered_rules)
    assert result.citations == [rule.citation for rule in result.triggered_rules]
    # Every citation names the rule source from the loaded data.
    for citation in result.citations:
        assert rules.citation in citation


async def test_owned_score_priority_tool_returns_the_shared_contract() -> None:
    async with Client(server_module.server) as client:
        listed = await client.list_tools()
        call = await client.call_tool(
            "score_priority", {"case": ADULT.model_dump()}
        )

    names = {tool.name for tool in listed.tools}
    assert "score_priority" in names, f"owned server does not expose score_priority: {names}"
    assert not call.is_error, f"score_priority tool errored: {call}"

    parsed = PriorityResult.model_validate_json(call.content[0].text)
    pure = scorer.score_priority(ADULT)
    assert parsed.colour == pure.colour
    assert parsed.tews == pure.tews
    assert len(parsed.citations) == len(parsed.triggered_rules)
