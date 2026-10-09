"""The ONE MCP wiring module — the dependency-inversion seam (D-04/D-13).

Callers depend on :func:`load_tools` and the LangChain ``BaseTool`` interface,
never on ``MCPAdapter`` directly. Swapping World A -> World B (D-04) touches this
file and the dependency pins only.

World A (current): ``langchain.mcp.MCPAdapter`` + ``mcp==2.3.0``.
World B (fallback): ``langchain-mcp-adapters.MultiServerMCPClient`` + ``mcp<2``.
"""

from __future__ import annotations

from pathlib import Path

from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool

# The owned server, launched as a stdio subprocess by the adapter.
SERVER_PATH = Path(__file__).resolve().parent / "server.py"


async def load_tools() -> list[BaseTool]:
    """Discover the owned MCP server's tools as LangChain tools.

    This is the DIP seam: the graph (Phase 3) depends on this function, not on
    the concrete adapter, so the World A -> B swap is contained here.
    """
    async with MCPAdapter(SERVER_PATH) as owned:
        return await owned.list_tools()
