"""Tracer proof suite for the approval-gate graph (Plan 03-01, GATE-01/02, ORCH-01/02).

Four offline, deterministic proofs (the real local-model run is the spike's job):

1. the graph compiles and its node set is a *superset* of the eight tracer nodes;
2. a run reaches the interrupt with a cited priority and calls NO commit first;
3. an absent / malformed resume is refused and performs no write;
4. no non-local model provider is imported by ``graph/``.

The tools are injected as fake async callables, so the suite never launches the
MCP subprocess or the model.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from conftest import build_graph_tools
from triagedesk.graph import build as build_module
from triagedesk.graph.build import (
    CHECKPOINTS_DB_PATH,
    DOMAIN_DB_PATH,
    TRACER_NODES,
    build_graph,
    checkpointed_graph,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = REPO_ROOT / "src" / "triagedesk" / "graph"

NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, "
    "temperature 38.9, no trauma. Presenting with central chest pain."
)

# Model-provider SDK roots that must NEVER appear on the graph path (ORCH-02).
_NON_LOCAL_PROVIDERS = {
    "openai",
    "anthropic",
    "google",
    "cohere",
    "mistralai",
    "azure",
    "boto3",
    "vertexai",
}


def _imported_modules(source: str) -> list[str]:
    """Return the absolute dotted module names imported by *source*."""
    modules: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


def test_graph_compiles_with_the_tracer_node_set() -> None:
    """The graph compiles and exposes a superset of the full safety-spine nodes (ORCH-01)."""
    graph = build_graph(build_graph_tools())
    node_names = set(graph.get_graph().nodes)
    expected = set(TRACER_NODES) | {"recheck", "request_missing_info", "escalate"}
    missing = expected - node_names
    assert not missing, f"tracer nodes missing from the compiled graph: {missing}"


async def test_run_reaches_the_gate_without_committing() -> None:
    """A run reaches the interrupt with a cited priority; no commit precedes it (GATE-01, D-04)."""
    calls: list[tuple[str, Any]] = []
    app = build_graph(build_graph_tools(calls=calls), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "case-gate"}}

    result = await app.ainvoke({"raw_note": NOTE}, config)

    assert result.get("__interrupt__"), "the graph did not pause at the gate"
    payload = result["__interrupt__"][0].value
    assert payload["colour"] is not None
    assert payload["citations"], "the paused priority carries no citations"
    assert len(payload["citations"]) == len(payload["triggered_rules"])
    # No queue-affecting write happened before the interrupt (D-04).
    assert result.get("commit_result") is None
    assert "commit_priority" not in [name for name, _ in calls]


async def test_unapproved_resume_is_refused_and_writes_nothing() -> None:
    """An absent/malformed approval is refused and performs no write (GATE-02, D-05)."""
    calls: list[tuple[str, Any]] = []
    writes: list[Any] = []
    app = build_graph(build_graph_tools(calls=calls, writes=writes), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "case-refuse"}}

    await app.ainvoke({"raw_note": NOTE}, config)
    resumed = await app.ainvoke(Command(resume={"decision": "dismiss"}), config)

    commit = resumed["commit_result"]
    assert commit.refused is True
    assert commit.committed is False
    assert writes == [], "an unapproved resume performed a write"
    # The gate WAS resumed and the commit node ran — with a malformed token.
    assert "commit_priority" in [name for name, _ in calls]


def test_graph_imports_no_non_local_model_provider() -> None:
    """The graph path reaches only the local Ollama client (ORCH-02, T-03-03)."""
    offenders: list[tuple[str, str]] = []
    for path in sorted(GRAPH_DIR.rglob("*.py")):
        for module in _imported_modules(path.read_text(encoding="utf-8")):
            if module.split(".")[0] in _NON_LOCAL_PROVIDERS:
                offenders.append((path.name, module))
            # Any model reference must be the local Ollama wrapper.
            parts = module.split(".")
            if "llm" in parts and parts[:2] != ["triagedesk", "llm"]:
                offenders.append((path.name, module))
    assert not offenders, f"graph/ must not reach a non-local model provider: {offenders}"


def test_checkpointer_and_domain_store_are_separate_files() -> None:
    """Runtime state and the clinical record are distinct files (D-09)."""
    assert CHECKPOINTS_DB_PATH.name == "checkpoints.db"
    assert DOMAIN_DB_PATH.name == "triage.db"
    assert CHECKPOINTS_DB_PATH != DOMAIN_DB_PATH


async def test_checkpoint_survives_a_fresh_saver(tmp_path: Path) -> None:
    """A paused thread re-loaded from a fresh saver still reports the interrupt (D-09, M-6)."""
    db_path = tmp_path / "checkpoints.db"
    tools = build_graph_tools()
    config = {"configurable": {"thread_id": "case-checkpoint"}}

    async with checkpointed_graph(tools, db_path) as graph:
        result = await graph.ainvoke({"raw_note": NOTE}, config)
        assert result.get("__interrupt__"), "the first pass did not pause"

    # A fresh saver over the SAME file — simulating a process restart.
    async with checkpointed_graph(tools, db_path) as reopened:
        snapshot = await reopened.aget_state(config)
        assert snapshot.next == ("approval_gate",), f"pending node drifted: {snapshot.next}"
        assert snapshot.tasks and snapshot.tasks[0].interrupts, "the interrupt was not persisted"


@pytest.mark.parametrize("attempt", [0, 1, 2])
def test_route_after_verify_is_bounded(attempt: int) -> None:
    """A failed evidence check retries while the budget lasts, then stops (T-03-05)."""
    retry_state: dict[str, Any] = {"route": "retry", "attempt": attempt}
    expected = "score" if attempt < build_module._MAX_ATTEMPTS else "__end__"
    assert build_module.route_after_verify(retry_state) == expected
    assert build_module.route_after_verify({"route": "ok"}) == "recheck"
