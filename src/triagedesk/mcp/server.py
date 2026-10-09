"""Owned MCP server (SDK v2, stdio) exposing ONE tool for Phase 1 (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. The tool returns the shared ``ExtractionResult`` schema (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/``; nothing depends on this server except the
adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.
"""

from __future__ import annotations

from mcp.server import MCPServer

from triagedesk.core import matcher, recheck, scorer
from triagedesk.core.schema import (
    CaseInput,
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


if __name__ == "__main__":
    server.run(transport="stdio")
