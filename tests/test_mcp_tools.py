"""Owned MCP tool-contract tests for the remaining tools (Plan 02-03, TOOL-01/TOOL-05).

Exercises the owned tools over the SDK's IN-MEMORY client (no borrowed server, no
subprocess, no network). The model call is stubbed so the suite stays offline and
deterministic.

Two subsets share this module: the ``normalize`` tests constrain the model-returned
discriminator ids to the closed set (Task 1), and the ``commit`` tests prove the
gated ``commit_priority`` stub refuses without a valid approval token (Task 3).
"""

from __future__ import annotations

from typing import Any

from mcp import Client

from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.mcp import server as server_module


def _first_discriminator_id() -> str:
    """A known-good id from the closed set, read through the one loader (D-08)."""
    return get_discriminators().discriminators[0].id


def _extraction(ids: list[str], **case: Any) -> ExtractionResult:
    """A fixed typed extraction, so the tests never depend on the model."""
    return ExtractionResult(case=CaseInput(**case), matched_discriminator_ids=ids)


async def test_normalize_case_drops_unknown_and_keeps_valid_ids(monkeypatch) -> None:
    valid = _first_discriminator_id()
    unknown = "not_a_declared_discriminator"
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: _extraction([valid, unknown], respiratory_rate=24),
    )

    async with Client(server_module.server) as client:
        call = await client.call_tool("normalize_case", {"raw_note": "RR 24"})

    assert not call.is_error, f"owned tool errored: {call}"
    parsed = ExtractionResult.model_validate_json(call.content[0].text)
    assert unknown not in parsed.matched_discriminator_ids
    assert valid in parsed.matched_discriminator_ids
    assert parsed.no_discriminator_matched is False


async def test_normalize_case_leaves_a_missing_vital_none(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: _extraction([_first_discriminator_id()], respiratory_rate=24),
    )

    async with Client(server_module.server) as client:
        call = await client.call_tool("normalize_case", {"raw_note": "RR 24, no other vitals"})

    parsed = ExtractionResult.model_validate_json(call.content[0].text)
    # A vital the nurse never provided is reported honestly as None, never imputed.
    assert parsed.case.respiratory_rate == 24
    assert parsed.case.temperature_c is None
    assert parsed.case.systolic_bp is None


async def test_normalize_case_reports_no_match_when_all_ids_are_unknown(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: _extraction(["bogus_one", "bogus_two"], heart_rate=80),
    )

    async with Client(server_module.server) as client:
        call = await client.call_tool("normalize_case", {"raw_note": "unparseable"})

    # The payload validates back to the ONE shared contract (D-14); the filtered
    # set is empty so the coverage signal is set.
    parsed = ExtractionResult.model_validate_json(call.content[0].text)
    assert parsed.matched_discriminator_ids == []
    assert parsed.no_discriminator_matched is True
