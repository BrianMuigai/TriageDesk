"""End-to-end tracer spike: note -> typed case -> owned MCP tool call.

Verification for Plan 01-01 task 1. Runs the whole thin path once against a fixed
synthetic note and exits non-zero on any failure:

    data layer   -> load the rule substrate through its one loader
    llm layer    -> extract a validated typed case from the note
    mcp layer    -> list + call the owned tool through the adapter seam

Usage:
    uv run python scripts/spike_e2e.py
"""

from __future__ import annotations

import asyncio
import sys

from triagedesk.core.citations import format_citation
from triagedesk.core.rules import get_tews
from triagedesk.llm.client import extract
from triagedesk.mcp.adapter import load_tools

NOTE = "RR 24, HR 118, BP 108/70, temp 38.9, alert, coughing and fast breathing"


async def main() -> int:
    # 1. Data layer: the rule substrate is loaded through its one loader.
    tews = get_tews()
    print(f"[data] loaded {len(tews.parameters)} TEWS parameters (v{tews.version})")
    print(f"[data] citation: {format_citation(tews.citation, 'respiratory_rate band')}")

    # 2. LLM layer: free text -> one validated typed case (real local-model call).
    result = extract(NOTE)
    case = result.case
    print(f"[llm] extracted case: {case.model_dump()}")
    if not case.complaint:
        raise AssertionError("extraction dropped the nurse's complaint")
    if case.respiratory_rate != 24:
        raise AssertionError(f"respiratory_rate not extracted honestly: {case.respiratory_rate!r}")
    if case.avpu != "alert":
        raise AssertionError(f"avpu enum not extracted: {case.avpu!r}")

    # 3. MCP layer: list + call the owned tool through the adapter seam.
    tools = await load_tools()
    names = [t.name for t in tools]
    print(f"[mcp] owned tools: {names}")
    if "normalize_case" not in names:
        raise AssertionError(f"normalize_case not exposed by the owned server: {names}")

    tool = next(t for t in tools if t.name == "normalize_case")
    tool_result = await tool.ainvoke({"raw_note": NOTE})
    print(f"[mcp] normalize_case -> {tool_result}")
    if not tool_result:
        raise AssertionError("owned tool returned an empty result")

    print("[ok] end-to-end path works: note -> typed case -> owned MCP tool")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
