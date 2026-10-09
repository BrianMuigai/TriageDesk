"""Owned MCP server (SDK v2, stdio) exposing ONE tool for Phase 1 (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. The tool returns the shared ``ExtractionResult`` schema (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/``; nothing depends on this server except the
adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.
"""

from __future__ import annotations

from mcp.server import MCPServer

from triagedesk.core.schema import ExtractionResult
from triagedesk.llm.client import extract

server = MCPServer("triagedesk-triage")


@server.tool()
def normalize_case(raw_note: str) -> ExtractionResult:
    """Parse a triage note into the typed case schema. Read-only."""
    return extract(raw_note)


if __name__ == "__main__":
    server.run(transport="stdio")
