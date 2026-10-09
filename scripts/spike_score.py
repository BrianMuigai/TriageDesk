"""End-to-end tracer spike: typed case -> cited score -> owned score_priority tool.

Verification for Plan 02-01 task 1. Runs the phase's thin path once against a
fixed adult case with complete vitals and exits non-zero on any failure:

    data layer  -> the TEWS substrate is loaded through its one loader
    core layer  -> the pure scorer turns the typed case into a cited colour
    mcp layer   -> the owned tool is listed and called through the adapter seam

The owned tool must expose ``score_priority``; the tool's payload must match the
pure function (no model on this path) and cite exactly the rules that fired
(``citations == triggered_rules``).

Usage:
    uv run python scripts/spike_score.py
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from triagedesk.core import scorer
from triagedesk.core.rules import get_tews
from triagedesk.core.schema import CaseInput, PriorityResult
from triagedesk.mcp.adapter import load_tools

# A fixed adult case with every scored vital present (RR 24, HR 118, SBP 108,
# temp 38.9, alert, walking, no trauma). Age is an unambiguous adult-year integer.
CASE = CaseInput(
    age_years=40,
    mobility="walking",
    respiratory_rate=24,
    heart_rate=118,
    systolic_bp=108,
    temperature_c=38.9,
    avpu="alert",
    trauma=False,
)


def _as_priority(payload: Any) -> PriorityResult:
    """Validate an MCP tool payload back into the shared ``PriorityResult`` contract.

    The adapter returns MCP content blocks (a list of ``{"type", "text"}``); the
    in-memory client returns the JSON text directly. Both are accepted.
    """
    if isinstance(payload, PriorityResult):
        return payload
    if isinstance(payload, list):
        for block in payload:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                return PriorityResult.model_validate_json(block["text"])
    if isinstance(payload, dict):
        return PriorityResult.model_validate(payload)
    return PriorityResult.model_validate_json(str(payload))


async def main() -> int:
    # 1. Data layer: the TEWS substrate is loaded through its one loader.
    rules = get_tews()
    print(f"[data] loaded {len(rules.parameters)} TEWS parameters (v{rules.version})")

    # 2. Core layer: the pure scorer, with no model involvement.
    pure = scorer.score_priority(CASE, [])
    print(f"[core] pure score: colour={pure.colour} tews={pure.tews} target={pure.target}")
    if pure.colour is None or pure.tews is None:
        raise AssertionError("pure scorer abstained on a complete adult case")
    if len(pure.citations) != len(pure.triggered_rules):
        raise AssertionError("citation invariant broken in the pure scorer")

    # 3. MCP layer: list + call the owned tool through the adapter seam.
    tools = await load_tools()
    names = [t.name for t in tools]
    print(f"[mcp] owned tools: {names}")
    if "score_priority" not in names:
        raise AssertionError(f"score_priority not exposed by the owned server: {names}")

    tool = next(t for t in tools if t.name == "score_priority")
    payload = await tool.ainvoke(
        {"case": CASE.model_dump(), "matched_discriminator_ids": []}
    )
    result = _as_priority(payload)
    print(f"[mcp] score_priority -> colour={result.colour} tews={result.tews}")

    # The tool is a thin adapter over the pure function: same colour, same total,
    # same citations. No model touched this path (D-02).
    if result.colour != pure.colour:
        raise AssertionError(f"tool colour {result.colour!r} != pure colour {pure.colour!r}")
    if result.tews != pure.tews:
        raise AssertionError(f"tool tews {result.tews!r} != pure tews {pure.tews!r}")
    if result.citations != pure.citations:
        raise AssertionError("tool citations drifted from the pure scorer")
    if len(result.citations) != len(result.triggered_rules):
        raise AssertionError("citations and triggered_rules are not 1:1")
    if not result.citations:
        raise AssertionError("a non-trivial case fired no rules (no citation to show)")
    for citation in result.citations:
        if rules.citation not in citation:
            raise AssertionError(f"citation does not name the rule source: {citation!r}")

    print("[ok] end-to-end path works: typed case -> cited score -> owned tool")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
