"""Owned MCP server contract regression tests (Plan 01-03, D-07).

Exercises the owned tool over the SDK's IN-MEMORY client (no borrowed server, no
subprocess, no network). The model call is stubbed so the suite stays offline and
deterministic; the real end-to-end call on both servers is covered by
``scripts/spike_mcp.py``.
"""

from __future__ import annotations

from mcp import Client

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.mcp import server as server_module


def _stub_result() -> ExtractionResult:
    """A fixed typed result, so the test never depends on the model."""
    return ExtractionResult(
        case=CaseInput(respiratory_rate=24, heart_rate=118, avpu="alert"),
    )


async def test_owned_server_lists_normalize_case_and_grows_its_tool_surface() -> None:
    async with Client(server_module.server) as client:
        listed = await client.list_tools()
    names = {t.name for t in listed.tools}
    # A superset check preserves the Phase-1 normalize_case contract without
    # forbidding the tool surface from growing (Phase 2 adds score_priority).
    assert names >= {"normalize_case", "score_priority"}, (
        f"owned server tool surface drifted: {names}"
    )


async def test_owned_server_call_returns_the_shared_schema(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "extract", lambda note: _stub_result())
    async with Client(server_module.server) as client:
        result = await client.call_tool("normalize_case", {"raw_note": "RR 24, alert"})
    assert not result.is_error, f"owned tool errored: {result}"
    # The tool's declared contract is the ONE shared schema (D-14): the payload
    # must validate back to ExtractionResult, so server and model cannot drift.
    parsed = ExtractionResult.model_validate_json(result.content[0].text)
    assert parsed.case.respiratory_rate == 24
    assert parsed.case.avpu == "alert"
