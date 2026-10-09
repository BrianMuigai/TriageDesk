"""Owned MCP tool-contract tests for the remaining tools (Plan 02-03, TOOL-01/TOOL-05).

Exercises the owned tools over the SDK's IN-MEMORY client (no borrowed server, no
subprocess, no network). The model call is stubbed so the suite stays offline and
deterministic; the store is the shared in-memory double injected by ``conftest``.

Two subsets share this module: the ``normalize`` tests constrain the model-returned
discriminator ids to the closed set (Task 1), and the ``commit`` tests prove the real
gated ``commit_priority`` refuses without a valid approval token and commits once —
idempotently — through the injectable store seam (Plan 03-02, GATE-02/GATE-03).
"""

from __future__ import annotations

from typing import Any

from mcp import Client

from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import CaseInput, CommitResult, ExtractionResult
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


async def test_commit_priority_refuses_without_a_token() -> None:
    async with Client(server_module.server) as client:
        call = await client.call_tool("commit_priority", {"case_id": "c-1", "colour": "RED"})

    assert not call.is_error, f"commit_priority errored instead of refusing: {call}"
    parsed = CommitResult.model_validate_json(call.content[0].text)
    assert parsed.refused is True
    assert parsed.committed is False


async def test_commit_priority_refuses_a_malformed_token() -> None:
    malformed = {
        "approved_by": "",
        "role": "",
        "decision": "maybe",
        "approved_at": "not-a-timestamp",
    }
    async with Client(server_module.server) as client:
        call = await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "approval_token": malformed},
        )

    assert not call.is_error, f"commit_priority errored instead of refusing: {call}"
    parsed = CommitResult.model_validate_json(call.content[0].text)
    assert parsed.refused is True
    assert parsed.committed is False


async def test_commit_priority_commits_once_through_the_injected_store(injected_store) -> None:
    token = {
        "approved_by": "Dr A. Nurse",
        "role": "triage clinician",
        "decision": "approve",
        "approved_at": "2026-10-09T15:00:00Z",
        "final_colour": "RED",
    }
    async with Client(server_module.server) as client:
        first = await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "approval_token": token},
        )
        repeat = await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "approval_token": token},
        )

    # A valid token now performs the real idempotent write: it commits once, and a
    # repeat of identical content inserts no second row (GATE-03, D-06).
    assert CommitResult.model_validate_json(first.content[0].text).committed is True
    assert CommitResult.model_validate_json(repeat.content[0].text).committed is True
    assert len(injected_store.rows) == 1


async def test_commit_priority_resolves_its_store_through_the_injectable_seam(
    injected_store,
) -> None:
    """The commit path resolves its store through the injectable seam (D-13).

    It depends on the ``Store`` protocol and the injected instance — not on a
    hard-coded concrete import — so a World-B store swap is a single injection.
    """
    token = {
        "approved_by": "Dr A. Nurse",
        "role": "triage clinician",
        "decision": "approve",
        "approved_at": "2026-10-09T15:00:00Z",
        "final_colour": "RED",
    }
    async with Client(server_module.server) as client:
        await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "approval_token": token},
        )

    # The injected (swapped) store is the one used — its row list holds the write.
    assert len(injected_store.rows) == 1
    assert injected_store.rows[0].case_id == "c-1"


async def test_commit_priority_is_listed_by_the_owned_server() -> None:
    async with Client(server_module.server) as client:
        listed = await client.list_tools()

    names = {tool.name for tool in listed.tools}
    assert "commit_priority" in names, f"owned server missing the tool: {names}"
