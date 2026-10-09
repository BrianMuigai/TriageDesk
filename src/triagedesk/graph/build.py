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

from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from triagedesk.core import schema as schema_module
from triagedesk.core.schema import CaseInput
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
    "OWNED_TOOL_ALLOWLIST",
    "TRACER_NODES",
    "assert_tool_allowlist",
    "build_graph",
    "checkpointed_graph",
    "load_graph_tools",
    "route_after_normalize",
    "route_after_score",
    "route_after_verify",
    "run_case",
]

# The least-privilege allowlist (SAFE-03, D-12): the graph may call ONLY these owned
# tools. Declared ONCE here and asserted at both edges (composition and discovery) so
# a missing or unexpected tool fails loudly instead of silently changing which
# capabilities the agent can reach (T-03-23).
OWNED_TOOL_ALLOWLIST: tuple[str, ...] = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "raise_recheck_flag",
    "commit_priority",
)


def assert_tool_allowlist(tool_names: Iterable[str]) -> None:
    """Fail loudly unless *tool_names* equals the declared allowlist (SAFE-03, D-12).

    The ONE allowlist check, reused at both the discovery seam and graph composition,
    so the surface cannot drift: a missing tool or an unexpected tool raises rather
    than silently changing behaviour (T-03-23).
    """
    discovered = set(tool_names)
    expected = set(OWNED_TOOL_ALLOWLIST)
    missing = expected - discovered
    unexpected = discovered - expected
    if missing or unexpected:
        raise RuntimeError(
            "owned tool surface drifted from the allowlist (SAFE-03): "
            f"missing={sorted(missing)} unexpected={sorted(unexpected)}"
        )


# The tracer's node set. The proof suite checks a *superset*, so a later plan may
# add nodes without invalidating the tracer. The recovery/abstention terminals and
# the serial-vitals recheck are part of the full safety spine (Plan 03-04).
TRACER_NODES: tuple[str, ...] = (
    "ingest",
    "normalize",
    "retrieve",
    "score",
    "verify",
    "recheck",
    "approval_gate",
    "commit",
    "handover",
    "request_missing_info",
    "escalate",
)

# The retry edge is bounded: after this many failed evidence checks the graph
# stops rather than looping (T-03-05).
_MAX_ATTEMPTS = 2


def route_after_normalize(state: TriageState) -> str:
    """Choose the next node after ``normalize`` — recovery vs the scored path (ORCH-04).

    A failed extraction that exhausted its bounded retry (and had no structured
    fallback) sets ``route="escalate"`` and stops at the escalation terminal; every
    other case proceeds to ``retrieve``. The graph never falls through to score on
    an unparseable case.
    """
    if state.get("route") == "escalate":
        return "escalate"
    return "retrieve"


def route_after_score(state: TriageState) -> str:
    """Choose the next node after ``score`` — safe terminals vs ``verify`` (ORCH-05).

    The scored ``PriorityResult`` carries the deterministic signals: an out-of-scope
    case escalates, a case missing a scored vital asks for re-measure, and only a
    fully-scored case proceeds to ``verify``. Neither terminal has an edge to
    ``commit``, so no missing/out-of-scope case is ever written (D-03).
    """
    priority = state.get("priority")
    if priority is not None and priority.out_of_scope:
        return "escalate"
    if priority is not None and priority.missing_vitals:
        return "request_missing_info"
    return "verify"


def route_after_verify(state: TriageState) -> str:
    """Choose the next node after ``verify`` — the bounded retry edge (T-03-05).

    ``ok`` routes to the second look and then the gate; a failed check re-scores
    while the attempt budget lasts, and otherwise stops (``END``) — a fail-closed
    stop that never reaches the gate or the commit.
    """
    if state.get("route") == "ok":
        return "recheck"
    if int(state.get("attempt") or 0) < _MAX_ATTEMPTS:
        return "score"
    return END


def build_graph(tools: ToolMap, checkpointer: Any = None) -> Any:
    """Compile the tracer graph over the injected ``tools`` mapping (D-01, D-13).

    ``START -> ingest -> normalize -> (retrieve -> score | escalate) ->
    (verify -> recheck -> approval_gate -> commit -> handover |
    request_missing_info | escalate) -> END``. The ``normalize``, ``score`` and
    ``verify`` edges are conditional; the recovery/abstention terminals have no edge
    to ``commit``. ``checkpointer`` is injected so the same builder serves both the
    in-memory test graph and the durable SQLite graph (D-09).

    The injected tool surface is asserted against the allowlist FIRST, so a drifted or
    unexpected tool fails loudly at composition rather than silently reaching the
    agent (SAFE-03, T-03-23).
    """
    assert_tool_allowlist(tools.keys())
    nodes = make_nodes(tools)
    graph: StateGraph = StateGraph(TriageState)
    for name in TRACER_NODES:
        graph.add_node(name, nodes[name])

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "normalize")
    graph.add_conditional_edges(
        "normalize",
        route_after_normalize,
        {"escalate": "escalate", "retrieve": "retrieve"},
    )
    graph.add_edge("retrieve", "score")
    graph.add_conditional_edges(
        "score",
        route_after_score,
        {
            "escalate": "escalate",
            "request_missing_info": "request_missing_info",
            "verify": "verify",
        },
    )
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {"recheck": "recheck", "score": "score", END: END},
    )
    graph.add_edge("recheck", "approval_gate")
    graph.add_edge("approval_gate", "commit")
    graph.add_edge("commit", "handover")
    graph.add_edge("handover", END)
    graph.add_edge("request_missing_info", END)
    graph.add_edge("escalate", END)
    return graph.compile(checkpointer=checkpointer)


async def load_graph_tools() -> ToolMap:
    """Compose the graph's tool mapping from the owned MCP server (the DIP seam).

    This is the ONE place the graph meets the concrete adapter: it calls the
    published ``load_tools`` seam and reduces the LangChain tools to the
    ``name -> async callable`` interface the nodes depend on (D-13, SOLID: D).

    The DISCOVERED tool names are asserted against the allowlist before they are
    reduced, so a drifted owned server fails loudly at startup (SAFE-03, D-12).
    """
    from triagedesk.mcp.adapter import load_tools

    owned = await load_tools()
    assert_tool_allowlist(tool.name for tool in owned)
    return {tool.name: tool.ainvoke for tool in owned}


async def run_case(
    raw_note: str,
    tools: ToolMap | None = None,
    config: Mapping[str, Any] | None = None,
    previous_case: CaseInput | None = None,
) -> Mapping[str, Any]:
    """Run one case through the graph, resolving tools from the owned server by default.

    A thin entry point: ``tools`` defaults to the owned server's mapping (the DIP
    seam); the caller supplies a ``config`` (a ``thread_id``) when a checkpointer is
    in use so a paused run can be resumed. ``previous_case`` is the optional earlier
    serial case: when present it seeds the state so the recheck node can raise a
    second-look flag against the current vitals (GATE-04, D-07).
    """
    resolved = tools if tools is not None else await load_graph_tools()
    graph = build_graph(resolved)
    initial: dict[str, Any] = {"raw_note": raw_note}
    if previous_case is not None:
        initial["previous_case"] = previous_case
    return await graph.ainvoke(initial, dict(config or {}))


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
