"""Pure serial-vitals recheck tests (Plan 02-03, TOOL-04, D-08, T-02-10).

The recheck compares two typed cases and returns a second-look flag carrying the
before/after values of any vital that deteriorated. It is proven to never
re-classify: the result contract has no colour field and the pure function lives
in ``core/`` with no queue/store access (``tests/test_purity.py`` is authoritative
for that boundary). Deterioration direction is derived from ``data/sats_tews.yaml``
band points — no threshold is restated here (CONVENTIONS §1).
"""

from __future__ import annotations

from mcp import Client

from triagedesk.core import recheck
from triagedesk.core.schema import CaseInput, RecheckFlag, VitalChange
from triagedesk.mcp import server as server_module

# A baseline adult case and its deteriorated follow-up (the plan's <behavior> case:
# SBP 118 -> 96, RR 16 -> 26, HR 80 -> 122). Values are inputs, not expected outputs.
BASELINE = CaseInput(
    age_years=40,
    mobility="walking",
    respiratory_rate=16,
    heart_rate=80,
    systolic_bp=118,
    temperature_c=37.0,
    avpu="alert",
    trauma=False,
)

DETERIORATED = BASELINE.model_copy(
    update={"systolic_bp": 96, "respiratory_rate": 26, "heart_rate": 122}
)


def _change(result: RecheckFlag, parameter: str) -> VitalChange:
    return next(change for change in result.changes if change.parameter == parameter)


def test_deterioration_raises_a_flag_with_before_after_values() -> None:
    result = recheck.compare_vitals(BASELINE, DETERIORATED)

    assert result.flag is True
    assert set(result.deteriorations) == {"systolic_bp", "respiratory_rate", "heart_rate"}
    sbp = _change(result, "systolic_bp")
    assert sbp.before == 118
    assert sbp.after == 96
    assert sbp.points_after > sbp.points_before
    assert result.reason, "a raised flag must explain itself"


def test_stable_follow_up_raises_no_flag() -> None:
    # RR 16 -> 18 and HR 80 -> 84 stay within the same band: no deterioration.
    stable = BASELINE.model_copy(update={"respiratory_rate": 18, "heart_rate": 84})
    result = recheck.compare_vitals(BASELINE, stable)

    assert result.flag is False
    assert result.deteriorations == []


def test_improvement_is_not_reported_as_a_deterioration() -> None:
    improved = DETERIORATED.model_copy(update={"systolic_bp": 130, "heart_rate": 70})
    result = recheck.compare_vitals(DETERIORATED, improved)

    # SBP 96 -> 130 and HR 122 -> 70 move toward normal: neither is a deterioration.
    assert "systolic_bp" not in result.deteriorations
    assert "heart_rate" not in result.deteriorations
    assert result.flag is False


def test_recheck_result_never_reclassifies() -> None:
    # The contract has no colour/target/destination field: this result cannot move
    # a patient's priority (D-08, M-4).
    assert "colour" not in RecheckFlag.model_fields
    assert "target" not in RecheckFlag.model_fields
    assert "destination" not in RecheckFlag.model_fields


def test_repeated_comparison_is_deterministic() -> None:
    first = recheck.compare_vitals(BASELINE, DETERIORATED)
    second = recheck.compare_vitals(BASELINE, DETERIORATED)
    assert first.model_dump() == second.model_dump()


async def test_owned_server_exposes_the_raise_recheck_flag_tool() -> None:
    """TOOL-04: the owned server exposes raise_recheck_flag over the shared contract."""
    async with Client(server_module.server) as client:
        listed = await client.list_tools()
        call = await client.call_tool(
            "raise_recheck_flag",
            {"previous": BASELINE.model_dump(), "current": DETERIORATED.model_dump()},
        )

    names = {tool.name for tool in listed.tools}
    assert "raise_recheck_flag" in names, f"owned server missing the tool: {names}"
    assert not call.is_error, f"raise_recheck_flag tool errored: {call}"

    parsed = RecheckFlag.model_validate_json(call.content[0].text)
    assert parsed.flag is True
    assert set(parsed.deteriorations) == set(
        recheck.compare_vitals(BASELINE, DETERIORATED).deteriorations
    )
