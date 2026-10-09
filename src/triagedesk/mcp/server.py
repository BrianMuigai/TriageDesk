"""Owned MCP server (SDK v2, stdio) exposing ONE tool for Phase 1 (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. The tool returns the shared ``ExtractionResult`` schema (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/``; nothing depends on this server except the
adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.
"""

from __future__ import annotations

from mcp.server import MCPServer

from triagedesk.core import scorer
from triagedesk.core.schema import CaseInput, ExtractionResult, PriorityResult
from triagedesk.llm.client import extract

# The owned server. Name is positional; everything else is keyword (SDK v2).
server = MCPServer("triagedesk-triage", version="0.1.0")


@server.tool()
def normalize_case(raw_note: str) -> ExtractionResult:
    """Parse a triage note into the typed case schema. Read-only.

    Single-purpose and contract-typed: it returns the one shared
    ``ExtractionResult`` schema (D-14), so the server contract and the model
    contract cannot drift. Read-only — it never writes to the queue (D-06).
    """
    return extract(raw_note)


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


if __name__ == "__main__":
    server.run(transport="stdio")
