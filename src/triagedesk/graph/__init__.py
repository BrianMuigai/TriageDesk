"""The triage graph package (Phase 3, D-01).

The whole path runs on the local open-weights model: ``ingest -> normalize ->
retrieve -> score -> verify -> approval_gate -> commit -> handover``. The gate is
the phase's protected headline — nothing reaches the queue without a named
clinician's approval (D-05).

The graph depends on an injected tool mapping (``build_graph``), never on a
concrete adapter (D-13, SOLID: D); ``mcp/adapter.load_tools`` is the one seam that
supplies the real tools.
"""

from __future__ import annotations

from triagedesk.graph.build import (
    CHECKPOINTS_DB_PATH,
    DOMAIN_DB_PATH,
    TRACER_NODES,
    build_graph,
    checkpointed_graph,
    load_graph_tools,
    route_after_normalize,
    route_after_score,
    route_after_verify,
    run_case,
)
from triagedesk.graph.nodes import make_nodes, parse_tool_result
from triagedesk.graph.state import TriageState

__all__ = [
    "CHECKPOINTS_DB_PATH",
    "DOMAIN_DB_PATH",
    "TRACER_NODES",
    "TriageState",
    "build_graph",
    "checkpointed_graph",
    "load_graph_tools",
    "make_nodes",
    "parse_tool_result",
    "route_after_normalize",
    "route_after_score",
    "route_after_verify",
    "run_case",
]
