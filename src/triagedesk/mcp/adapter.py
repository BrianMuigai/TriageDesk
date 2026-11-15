"""The ONE MCP wiring module — the dependency-inversion seam (D-04/D-13).

Callers depend on :func:`load_tools` and the LangChain ``BaseTool`` interface,
never on ``MCPAdapter`` directly. Swapping World A -> World B (D-04) touches this
file and the dependency pins only.

This module is the ONLY place that names ``MCPAdapter``. It exposes two loaders,
each in its OWN adapter context, and one opt-in tool-map seam:

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
* :func:`with_live_clarification` — the ONE opt-in seam a surface with a human present
  applies to its tool map, so ``request_clarification`` is the adapter-loaded owned tool
  (loaded in process) and a question genuinely pauses the run.

World A (current): ``langchain.mcp.MCPAdapter`` + ``mcp==2.3.0``.
World B (fallback): ``langchain-mcp-adapters.MultiServerMCPClient`` + ``mcp<2``.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from langchain_core._api.beta_decorator import LangChainBetaWarning
from langchain_core.tools import BaseTool

# ``langchain.mcp`` is a beta API on purpose: it is the recorded, exact-pinned World A choice
# (STACK flag, D-04). Its import-time ``LangChainBetaWarning`` would otherwise print on the live
# demo screen, so it is silenced here, at its ONE source. ``langchain_core`` installs its own
# warning filter when it is imported, so this ignore filter only wins when it is installed
# AFTER ``langchain_core`` (imported above) — hence the import sits last.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=LangChainBetaWarning)
    from langchain.mcp import MCPAdapter

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


# The one owned tool the live seam replaces — the graph's ``ask_question`` node calls it.
_CLARIFICATION_TOOL = "request_clarification"


async def _owned_tool(name: str) -> BaseTool:
    """Load ONE owned tool through the shipped adapter, in process.

    The server module is imported lazily: ``server`` → ``store`` → ``borrowed`` imports this
    module, so a top-level import would make the graph cyclic. A missing tool raises
    ``LookupError`` — a discovery failure must never become a clinical answer.
    """
    from triagedesk.mcp import server as server_module

    async with MCPAdapter(server_module.server) as owned:
        tools = {tool.name: tool for tool in await owned.list_tools()}
    if name not in tools:
        raise LookupError(f"the owned server does not expose {name!r}")
    return tools[name]


def with_live_clarification(tools: Mapping[str, Any]) -> dict[str, Any]:
    """Return a NEW tool map whose ``request_clarification`` is the adapter-loaded owned tool.

    The ONE opt-in seam for a surface where a human is present to answer (the online demo,
    the online desk, a resume of a paused question). "In process" is a real 2026-07-28 MCP
    session over the adapter's in-memory transport — not a direct function call — so the tool
    returns its ``InputRequiredResult`` and the adapter raises the ``mcp_elicitation``
    interrupt; the store seam and the audit interceptor apply as on any MCP call, and no stdio
    subprocess or borrowed store is launched.

    It is opt-in because a human must be present: the eval harness has none, so it keeps the
    in-process tool that honestly answers ``unavailable``. Only this one key is replaced
    (SOLID: I) — every other callable passes through by identity, the input mapping is not
    mutated, and the adapter's full tool list (which includes the gated commit) is never
    exposed. The tool is loaded at call time, so the seam costs nothing unless the planner
    actually asks.

    The call is deliberately not wrapped in a ``try``: the interrupt must propagate to
    LangGraph, and a transport failure must fail loudly rather than invent an answer.
    """

    async def request_clarification(inp: Mapping[str, Any]) -> Any:
        tool = await _owned_tool(_CLARIFICATION_TOOL)
        return await tool.ainvoke({"candidates": list(inp.get("candidates") or [])})

    return {**tools, _CLARIFICATION_TOOL: request_clarification}
