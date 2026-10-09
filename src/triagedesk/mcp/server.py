"""Owned MCP server (SDK v2, stdio) exposing ONE tool for Phase 1 (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. The tool returns the shared ``ExtractionResult`` schema (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/``; nothing depends on this server except the
adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.
"""

from __future__ import annotations

from mcp.server import MCPServer
from pydantic import ValidationError

from triagedesk.core import matcher, recheck, scorer
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    CommitResult,
    ExtractionResult,
    MatchResult,
    PriorityResult,
    RecheckFlag,
)
from triagedesk.llm.client import extract

# The owned server. Name is positional; everything else is keyword (SDK v2).
server = MCPServer("triagedesk-triage", version="0.1.0")


@server.tool()
def normalize_case(raw_note: str) -> ExtractionResult:
    """Parse a triage note into the typed case schema. Read-only.

    Single-purpose and contract-typed: it returns the one shared
    ``ExtractionResult`` schema (D-14), so the server contract and the model
    contract cannot drift. Read-only — it never writes to the queue (D-06).

    The model may only *structure* a note; it may not choose a discriminator
    outside the closed set. Model-returned ids are therefore filtered to the
    declared set (unknown ids dropped) and ``no_discriminator_matched`` is set
    when nothing survives (T-02-11). Missing vitals stay ``None`` — never imputed.
    """
    result = extract(raw_note)
    ids = matcher.validate_discriminator_ids(result.matched_discriminator_ids)
    return result.model_copy(
        update={"matched_discriminator_ids": ids, "no_discriminator_matched": not ids}
    )


@server.tool()
def score_priority(
    case: CaseInput,
    matched_discriminator_ids: list[str] | None = None,
) -> PriorityResult:
    """Score a typed case deterministically — no model on this path (D-02).

    A thin, contract-typed adapter over the pure ``core.scorer.score_priority``
    function (SOLID: S/D): it touches no model and cannot inject a colour. The
    returned ``PriorityResult`` carries the colour, TEWS total, target time and
    one citation per triggered rule.
    """
    return scorer.score_priority(case, matched_discriminator_ids)


@server.tool()
def match_discriminators(complaint: str) -> MatchResult:
    """Match a free-text complaint to closed-set discriminator ids (D-05, D-06).

    A thin, contract-typed adapter over the pure ``core.matcher`` function
    (SOLID: S/D): a deterministic alias lookup with no model and no fuzzy
    judgement. It returns ids from the closed discriminator set only, or an
    explicit ``no_match`` result — never a guessed id (SAFE-01).
    """
    return matcher.match_discriminators(complaint)


@server.tool()
def raise_recheck_flag(previous: CaseInput, current: CaseInput) -> RecheckFlag:
    """Compare serial vitals into a second-look flag — never a re-classification (D-08).

    A thin, contract-typed adapter over the pure ``core.recheck.compare_vitals``
    function (SOLID: S/D): it returns a flag and the before/after vitals only. It
    never returns a colour and never reorders the queue (TOOL-04, T-02-10).
    """
    return recheck.compare_vitals(previous, current)


@server.tool()
def commit_priority(
    case_id: str, colour: str, approval_token: dict[str, object] | None = None
) -> CommitResult:
    """The queue-affecting gate — a Phase-2 stub that refuses without approval (D-07).

    This is the ONLY queue-affecting tool. In Phase 2 it is a gated *stub*: it
    validates the approval-token shape (named approver + role + decision in
    approve|edit|dismiss + timestamp) and refuses (``refused=True``) any call that
    lacks a well-formed token. It performs NO queue or store write on any path — the
    real LangGraph ``interrupt()`` gate, idempotent content-hash commit and queue
    write are Phase 3 (TOOL-05, GATE-01..04).
    """
    if approval_token is None:
        return CommitResult(refused=True, reason="no approval token supplied; refusing to commit")
    try:
        ApprovalToken.model_validate(approval_token)
    except ValidationError:
        return CommitResult(refused=True, reason="approval token is malformed; refusing to commit")
    return CommitResult(
        refused=False,
        reason="approval token accepted; the gate and idempotent commit are enforced in Phase 3",
    )


if __name__ == "__main__":
    server.run(transport="stdio")
