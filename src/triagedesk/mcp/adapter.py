"""The ONE MCP wiring module — the dependency-inversion seam (D-04/D-13).

Callers depend on :func:`load_tools` and the LangChain ``BaseTool`` interface,
never on ``MCPAdapter`` directly. Swapping World A -> World B (D-04) touches this
file and the dependency pins only.

This module is the ONLY place that names ``MCPAdapter``. It exposes two loaders,
each in its OWN adapter context:

* :func:`load_tools` — the *owned* server's tools. This is the graph-facing DIP
  seam (SOLID: D): the graph (Phase 3) depends on this function, not on the
  concrete adapter, so the World A -> B swap is contained here.
* :func:`load_borrowed_tools` — the *borrowed* SQLite storage server's tools
  (D-05/D-06). The borrowed server is legacy TS; it is reached through a
  **separate** adapter context, never merged with the owned server into one
  ``MCPConfig``, because a fleet negotiates ONE protocol era for every backend —
  merging would collapse the modern owned server to the legacy era
  (01-RESEARCH Pattern 3). The borrowed server is storage only; the gate stays
  ours (D-06).

World A (current): ``langchain.mcp.MCPAdapter`` + ``mcp==2.3.0``.
World B (fallback): ``langchain-mcp-adapters.MultiServerMCPClient`` + ``mcp<2``.
"""

from __future__ import annotations

from pathlib import Path

from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool

# The owned server, launched as a stdio subprocess by the adapter.
SERVER_PATH = Path(__file__).resolve().parent / "server.py"

# The borrowed storage server, pinned to an exact version (D-05) — never
# `npx -y mcp-sqlite` unpinned, which would fetch `latest` at clone time and
# break deadline reproducibility. Its provenance is reviewed at a
# blocking-human package-legitimacy checkpoint before install.
BORROWED_SERVER_PACKAGE = "mcp-sqlite@1.0.9"


def borrowed_server_config(db_path: Path) -> dict:
    """Build the SEPARATE adapter target for the borrowed SQLite server.

    Returns an ``MCPConfig`` mapping for a single legacy backend. It is
    deliberately a standalone config (one backend) so it is never merged with
    the owned server's context — the era-collapse trap in 01-RESEARCH Pattern 3.
    """
    return {
        "mcpServers": {
            "sqlite": {
                "command": "npx",
                "args": ["-y", BORROWED_SERVER_PACKAGE, str(db_path)],
            }
        }
    }


async def load_tools() -> list[BaseTool]:
    """Discover the owned MCP server's tools as LangChain tools.

    This is the DIP seam: the graph (Phase 3) depends on this function, not on
    the concrete adapter, so the World A -> B swap is contained here.
    """
    async with MCPAdapter(SERVER_PATH) as owned:
        return await owned.list_tools()


async def load_borrowed_tools(db_path: Path) -> list[BaseTool]:
    """Discover the borrowed SQLite server's storage tools (separate context).

    Reached through its own adapter context so the legacy borrowed server and
    the modern owned server keep their own protocol eras (no era collapse).
    """
    async with MCPAdapter(borrowed_server_config(db_path)) as borrowed:
        return await borrowed.list_tools()
