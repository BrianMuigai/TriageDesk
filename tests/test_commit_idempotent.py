"""Idempotent queue write + real gated commit (Plan 03-02, GATE-02/GATE-03, D-05/D-06).

Task 2 (queue level): the write is idempotent on (``case_id``, immutable content
hash); a volatile approval timestamp never enters the key; a crash-retry yields one row.
An ``edit`` of the same case supersedes the row in place — one row, updated colour,
unchanged position (D6-06).
Task 3 (tool level): ``commit_priority`` refuses without a valid token (or on
``dismiss``) touching no store, and a valid token commits once with the token's
``final_colour`` through the injectable store seam.

The store is the shared in-memory double from ``conftest`` (D-13) — no borrowed
subprocess is launched.
"""

from __future__ import annotations

from typing import Any

from mcp import Client

from triagedesk.core.schema import CaseInput, CommitResult
from triagedesk.durable import approval_decision
from triagedesk.mcp import server as server_module
from triagedesk.store.queue import IMMUTABLE_FIELDS, commit_to_queue, content_hash

# One CaseInput-shaped payload — the immutable case content the idempotency key now
# covers (D6-04). Shared by the store- and tool-level tests so the key is meaningful.
_CASE: dict[str, Any] = {
    "respiratory_rate": 24,
    "heart_rate": 118,
    "avpu": "alert",
    "complaint": "central chest pain",
}
_CASE_INPUT = CaseInput(**_CASE)


def _token(decision: str, final_colour: str = "ORANGE", **overrides: Any) -> dict[str, Any]:
    """A well-formed approval-token payload (approver + role + decision + colour)."""
    token: dict[str, Any] = {
        "approved_by": "Dr A. Nurse",
        "role": "triage clinician",
        "decision": decision,
        "approved_at": "2026-10-09T16:00:00Z",
        "final_colour": final_colour,
    }
    token.update(overrides)
    return token


# --------------------------------------------------------------------------- Task 2


async def test_commit_twice_yields_one_row(memory_store) -> None:
    """Committing the same case content twice produces exactly one queue row (D-06)."""
    first, created_first = await commit_to_queue(
        memory_store, case_id="c-1", colour="ORANGE", content=_CASE_INPUT
    )
    second, created_second = await commit_to_queue(
        memory_store, case_id="c-1", colour="ORANGE", content=_CASE_INPUT
    )

    assert created_first is True
    assert created_second is False
    assert first.content_hash == second.content_hash
    assert len(memory_store.rows) == 1


async def test_an_edit_supersedes_the_row_in_place(memory_store) -> None:
    """An ``edit`` of the same case supersedes in place — one row, new colour, same seat.

    The idempotency key covers the immutable case input, so an approve and an edit of
    the same case re-derive the SAME key: the row is updated (``colour`` -> the edited
    colour) and its ``position``/``created_at`` are preserved, never duplicated (D6-04,
    D6-06).
    """
    first, created_first = await commit_to_queue(
        memory_store, case_id="c-1", colour="ORANGE", content=_CASE_INPUT
    )
    created_at = first.created_at
    assert created_first is True

    second, created_second = await commit_to_queue(
        memory_store, case_id="c-1", colour="GREEN", content=_CASE_INPUT
    )

    assert created_second is False
    assert second.colour == "GREEN"
    assert len(memory_store.rows) == 1
    assert memory_store.rows[0].colour == "GREEN"
    assert memory_store.rows[0].position == 1
    assert memory_store.rows[0].created_at == created_at


async def test_volatile_timestamp_does_not_change_the_content_hash() -> None:
    """The approval timestamp never enters the key — a retry cannot churn it (Pitfall 14)."""
    base = _CASE_INPUT.model_dump(mode="json")
    earlier = content_hash("c-1", {**base, "approved_at": "2026-10-09T16:00:00Z"})
    later = content_hash("c-1", {**base, "approved_at": "2026-10-09T18:30:00Z"})
    assert earlier == later
    # Only immutable fields are read; the volatile field is structurally excluded.
    assert "approved_at" not in IMMUTABLE_FIELDS


async def test_crash_then_retry_yields_one_row(memory_store) -> None:
    """A crash after the write but before acknowledgement, then a retry, yields one row.

    Crash-safety IS the idempotency key (``case_id`` + immutable content hash): the
    retry re-derives the same key, so the upsert is a no-op and a second row cannot
    appear. Any store transaction would be belt-and-braces only — the borrowed server
    exposes no transaction call (D-06, Pitfall 14).
    """
    # First attempt writes the row, then the process "crashes" before it acknowledges
    # (the returned row is discarded — no ack reached the caller).
    await commit_to_queue(memory_store, case_id="c-9", colour="RED", content=_CASE_INPUT)

    # Retry after restart: the same key is re-derived, so nothing new is inserted.
    retried, created = await commit_to_queue(
        memory_store, case_id="c-9", colour="RED", content=_CASE_INPUT
    )

    assert created is False
    assert len(memory_store.rows) == 1
    assert retried.position == 1


# --------------------------------------------------------------------------- Task 3


async def test_commit_priority_refuses_without_a_token_and_writes_nothing(
    injected_store,
) -> None:
    """A token-less call is refused and touches no store (GATE-02, T-03-09)."""
    async with Client(server_module.server) as client:
        call = await client.call_tool(
            "commit_priority", {"case_id": "c-1", "colour": "RED", "case": _CASE}
        )

    result = CommitResult.model_validate_json(call.content[0].text)
    assert result.refused is True
    assert result.committed is False
    assert injected_store.calls == []
    assert injected_store.rows == []


async def test_commit_priority_refuses_a_dismiss_and_writes_nothing(injected_store) -> None:
    """A ``dismiss`` decision is refused before any store access (D-05)."""
    async with Client(server_module.server) as client:
        call = await client.call_tool(
            "commit_priority",
            {
                "case_id": "c-1",
                "colour": "RED",
                "case": _CASE,
                "approval_token": _token("dismiss", "RED"),
            },
        )

    result = CommitResult.model_validate_json(call.content[0].text)
    assert result.refused is True
    assert result.committed is False
    assert injected_store.calls == []


async def test_approval_decision_dismiss_reaches_the_dismiss_branch(injected_store) -> None:
    """The ONE dismiss builder emits a token the gate recognises as a dismissal (WR-05).

    Before the fix ``approval_decision("dismiss")`` produced ``{"decision": "dismiss"}``,
    which ``ApprovalToken`` rejected as malformed — so the gate's ``dismiss`` branch was
    unreachable and the refusal read as a malformed token. The builder now emits a
    well-formed dismissal token (decision + timestamp, no identity/colour), so the gate
    reaches its own branch and reports the dismissal reason, still writing nothing.
    """
    token = approval_decision("dismiss")
    async with Client(server_module.server) as client:
        call = await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "RED", "case": _CASE, "approval_token": token},
        )

    result = CommitResult.model_validate_json(call.content[0].text)
    assert result.refused is True
    assert result.reason is not None and "dismissed" in result.reason
    assert injected_store.calls == []
    assert injected_store.rows == []


async def test_commit_priority_commits_once_through_the_injected_store(injected_store) -> None:
    """A valid token commits exactly once; a repeat is idempotent (GATE-03, D-06)."""
    token = _token("approve", "ORANGE")
    async with Client(server_module.server) as client:
        first = await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "ORANGE", "case": _CASE, "approval_token": token},
        )
        repeat = await client.call_tool(
            "commit_priority",
            {"case_id": "c-1", "colour": "ORANGE", "case": _CASE, "approval_token": token},
        )

    assert CommitResult.model_validate_json(first.content[0].text).committed is True
    assert CommitResult.model_validate_json(repeat.content[0].text).committed is True
    assert len(injected_store.rows) == 1


async def test_commit_priority_edit_commits_the_tokens_final_colour(injected_store) -> None:
    """An ``edit`` commits the clinician's ``final_colour``, not the scored colour (D-05)."""
    token = _token("edit", "GREEN")
    async with Client(server_module.server) as client:
        call = await client.call_tool(
            "commit_priority",
            {"case_id": "c-2", "colour": "RED", "case": _CASE, "approval_token": token},
        )

    assert CommitResult.model_validate_json(call.content[0].text).committed is True
    assert len(injected_store.rows) == 1
    assert injected_store.rows[0].colour == "GREEN"


async def test_commit_priority_uses_the_injected_store_seam(memory_store) -> None:
    """The commit path resolves its store through the injectable seam, not a concrete import.

    A swapped store is the one written to, so a World-B store is a single injection
    (D-10, D-13, SOLID: D/L).
    """
    token = _token("approve", "ORANGE")
    async with Client(server_module.server) as client:
        await client.call_tool(
            "commit_priority",
            {"case_id": "c-3", "colour": "ORANGE", "case": _CASE, "approval_token": token},
        )

    # The autouse seam injected THIS store instance; the row landed in it.
    assert len(memory_store.rows) == 1
    assert memory_store.rows[0].case_id == "c-3"
