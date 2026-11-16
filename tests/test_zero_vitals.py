"""A recorded zero vital must abstain, not score (nurse stress test 2026-11-16, S1).

Before this guard, ``score_priority`` with ``respiratory_rate=0``, ``heart_rate=0`` or
``systolic_bp=0`` returned ``colour="YELLOW", tews=3`` — the "< 9 / < 41 / < 71" band —
a six-band under-triage for a peri-arrest patient. A zero is not a measurement, so the
tool now drops it to "not recorded" on a copy of the case and the scorer's own
missing-vitals abstain answers "re-measure".

These tests drive the registered MCP tool over the SDK's in-memory client (no borrowed
server, no subprocess, no network, no model); the store seam is the shared fake injected
by ``conftest``.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp import Client

from triagedesk.core.schema import CaseInput, PriorityResult
from triagedesk.mcp import server as server_module

# The three scored vitals a patient cannot be waiting in the queue with at zero. Declared
# literally here so the parametrisation cannot go vacuous if the server set is emptied;
# ``test_the_zero_set_names_only_impossible_zero_vitals`` pins the two together.
_ZERO_VITAL_FIELDS = ("respiratory_rate", "heart_rate", "systolic_bp")

# One fully-recorded adult case with every vital inside its 0-point band: it scores TEWS 0
# with the data-driven baseline citation. Each zero test perturbs exactly one field.
_NORMAL_CASE: dict[str, Any] = {
    "age_years": 30,
    "mobility": "walking",
    "respiratory_rate": 12,
    "heart_rate": 70,
    "systolic_bp": 120,
    "temperature_c": 36.8,
    "avpu": "alert",
    "trauma": False,
    "complaint": "routine review",
}


async def _score(case: dict[str, Any]) -> PriorityResult:
    """Call the registered ``score_priority`` tool and parse its shared contract (D-14)."""
    async with Client(server_module.server) as client:
        call = await client.call_tool("score_priority", {"case": case})
    assert not call.is_error, f"score_priority errored instead of abstaining: {call}"
    return PriorityResult.model_validate_json(call.content[0].text)


def test_the_zero_set_names_only_impossible_zero_vitals() -> None:
    """The tool's declared set is exactly the three vitals a zero cannot be (DRY)."""
    assert server_module._ZERO_IS_NOT_RECORDED == _ZERO_VITAL_FIELDS


@pytest.mark.parametrize("field", _ZERO_VITAL_FIELDS)
async def test_a_zero_vital_abstains_and_asks_to_re_measure(field: str) -> None:
    """A zero on *field* must fail closed, never receive a colour (S1)."""
    parsed = await _score(dict(_NORMAL_CASE, **{field: 0}))

    assert parsed.abstained is True
    assert parsed.colour is None
    assert parsed.tews is None
    assert parsed.target is None
    assert parsed.destination is None
    assert parsed.missing_vitals == [field]
    assert parsed.citations == []
    assert parsed.triggered_rules == []
    assert "re-measure" in (parsed.reason or "")


async def test_a_normal_case_is_unchanged() -> None:
    """The guard must not disturb an all-normal case: GREEN, TEWS 0, one baseline citation."""
    parsed = await _score(dict(_NORMAL_CASE))

    assert parsed.abstained is False
    assert parsed.colour == "GREEN"
    assert parsed.tews == 0
    assert parsed.missing_vitals == []
    assert len(parsed.citations) == len(parsed.triggered_rules) == 1
    assert "within normal SATS bands" in parsed.citations[0]


async def test_a_legitimate_zero_outside_the_set_is_untouched() -> None:
    """A zero on an unscored vitals column, and ``trauma: false``, still score as recorded."""
    parsed = await _score(dict(_NORMAL_CASE, trauma=False, diastolic_bp=0))

    assert parsed.abstained is False
    assert parsed.colour == "GREEN"
    assert parsed.tews == 0
    assert "trauma" in parsed.used_vitals


async def test_the_supplied_case_is_not_mutated() -> None:
    """The zero is dropped on a COPY; the caller's typed case keeps its recorded value."""
    case = CaseInput(**dict(_NORMAL_CASE, heart_rate=0))

    await server_module.score_priority(case)

    assert case.heart_rate == 0
