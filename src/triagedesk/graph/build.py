"""Assemble the tracer graph — the composition root (D-01, D-09, D-13).

This module is the ONLY place the graph is wired to concrete dependencies: it
takes the injected ``tools`` mapping (built from ``mcp/adapter.load_tools`` at the
edge) and assembles the ``StateGraph``. The nodes themselves never import an
adapter (SOLID: D), so the World A -> B swap is confined to ``mcp/adapter.py``.

Two persistence paths are named here and nowhere else (D-09):

* ``DOMAIN_DB_PATH`` (``triage.db``) — the clinical record + audit, via the
  borrowed SQLite MCP (wired in a later plan; no write happens here).
* ``CHECKPOINTS_DB_PATH`` (``checkpoints.db``) — LangGraph runtime state only.

They are deliberately DIFFERENT files: an immutable clinical record and disposable
runtime state are distinct concerns, so a checkpointer write can never be mistaken
for an audit event (D-09).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from triagedesk.core import schema as schema_module
from triagedesk.graph.nodes import ToolMap, make_nodes
from triagedesk.graph.state import TriageState
from triagedesk.store import DOMAIN_DB_PATH

# The LangGraph runtime-state path, named once so no caller inlines a filename
# (D-09). ``DOMAIN_DB_PATH`` (``triage.db``) is the clinical record + audit, owned
# by the store package (single source); the two are deliberately DIFFERENT files.
CHECKPOINTS_DB_PATH = Path("checkpoints.db")

__all__ = [
    "CHECKPOINTS_DB_PATH",
    "DOMAIN_DB_PATH",
    "TRACER_NODES",
    "build_graph",
    "checkpointed_graph",
    "load_graph_tools",
    "route_after_verify",
    "run_case",
]

# The tracer's node set. A later plan may add recovery / recheck / escalation
# nodes; the proof suite checks a *superset*, so those additions do not
# invalidate this tracer.
TRACER_NODES: tuple[str, ...] = (
    "ingest",
    "normalize",
    "retrieve",
    "score",
    "verify",
    "approval_gate",
    "commit",
    "handover",
)

# The retry edge is bounded: after this many failed evidence checks the graph
# stops rather than looping (T-03-05).
_MAX_ATTEMPTS = 2


def route_after_verify(state: TriageState) -> str:
    """Choose the next node after ``verify`` — the bounded retry edge (T-03-05).

    ``ok`` routes to the gate; a failed check re-scores while the attempt budget
    lasts, and otherwise stops (``END``) — a fail-closed stop that never reaches
    the gate or the commit.
    """
    if state.get("route") == "ok":
        return "approval_gate"
    if int(state.get("attempt") or 0) < _MAX_ATTEMPTS:
        return "score"
    return END


def build_graph(tools: ToolMap, checkpointer: Any = None) -> Any:
    """Compile the tracer graph over the injected ``tools`` mapping (D-01, D-13).

    ``START -> ingest -> normalize -> retrieve -> score -> verify ->
    (approval_gate -> commit -> handover | score) -> END``. The ``verify`` edge is
    conditional and bounded. ``checkpointer`` is injected so the same builder
    serves both the in-memory test graph and the durable SQLite graph (D-09).
    """
    nodes = make_nodes(tools)
    graph: StateGraph = StateGraph(TriageState)
    for name in TRACER_NODES:
        graph.add_node(name, nodes[name])

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "normalize")
    graph.add_edge("normalize", "retrieve")
    graph.add_edge("retrieve", "score")
    graph.add_edge("score", "verify")
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {"approval_gate": "approval_gate", "score": "score", END: END},
    )
    graph.add_edge("approval_gate", "commit")
    graph.add_edge("commit", "handover")
    graph.add_edge("handover", END)
    return graph.compile(checkpointer=checkpointer)


async def load_graph_tools() -> ToolMap:
    """Compose the graph's tool mapping from the owned MCP server (the DIP seam).

    This is the ONE place the graph meets the concrete adapter: it calls the
    published ``load_tools`` seam and reduces the LangChain tools to the
    ``name -> async callable`` interface the nodes depend on (D-13, SOLID: D).
    """
    from triagedesk.mcp.adapter import load_tools

    owned = await load_tools()
    return {tool.name: tool.ainvoke for tool in owned}


async def run_case(
    raw_note: str,
    tools: ToolMap | None = None,
    config: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Run one case through the graph, resolving tools from the owned server by default.

    A thin entry point: ``tools`` defaults to the owned server's mapping (the DIP
    seam); the caller supplies a ``config`` (a ``thread_id``) when a checkpointer is
    in use so a paused run can be resumed.
    """
    resolved = tools if tools is not None else await load_graph_tools()
    graph = build_graph(resolved)
    return await graph.ainvoke({"raw_note": raw_note}, dict(config or {}))


@asynccontextmanager
async def checkpointed_graph(
    tools: ToolMap, db_path: Path = CHECKPOINTS_DB_PATH
) -> AsyncIterator[Any]:
    """Compile the graph over the durable SQLite checkpointer (D-09, M-6).

    Opens ``AsyncSqliteSaver`` over *db_path* (``checkpoints.db`` by default — a
    file separate from the domain store) and yields the compiled graph. The paused
    state survives a process restart: reopening the same file with a fresh saver
    still reports the pending interrupt.

    The saver's serializer is given an explicit allowlist of the schema types the
    state carries — so custom contracts (``CaseInput``, ``PriorityResult``, ...) are
    registered deliberately rather than tripping the future strict-msgpack block.
    """
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        saver.serde = JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
        yield build_graph(tools, checkpointer=saver)


def _allowed_msgpack_modules() -> list[tuple[str, str]]:
    """The ONE allowlist of state types the checkpointer may (de)serialise.

    Derived from the schema module rather than hand-listed, so a new state contract
    is covered automatically (DRY). An allowlist — never ``True`` — so the
    checkpointer cannot deserialise an arbitrary type from a tampered checkpoint.
    """
    return [
        (schema_module.__name__, name)
        for name, obj in vars(schema_module).items()
        if isinstance(obj, type)
        and issubclass(obj, BaseModel)
        and obj.__module__ == schema_module.__name__
    ]

