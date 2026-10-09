"""Purity guards for the score path (Plan 03-05, ORCH-03, QUAL-02, D-02).

``core/`` stays pure (``tests/test_purity.py``) and the graph's score path is
**model-free** — the colour can never come from the model:

1. the score node returns the identical colour and citations with the model stubbed to
   raise, proving no model sits on the scoring branch;
2. the full score path still reaches the gate with the extraction tool unavailable,
   scoring the caller's typed case deterministically;
3. the score node's own factory references no model client.

The model and the MCP subprocess are never launched; the tools are the shared offline
fakes (``tests/conftest.py``). There is deliberately no second copy of the ``core/``
purity scan — that guard lives in ``tests/test_purity.py`` and is extended there (DRY).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import COMPLETE_CASE, build_graph_tools
from triagedesk.core import scorer
from triagedesk.graph import nodes as nodes_module
from triagedesk.graph.build import build_graph

GRAPH_DIR = Path(__file__).resolve().parents[1] / "src" / "triagedesk" / "graph"

NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, "
    "temperature 38.9, no trauma. Presenting with central chest pain."
)

# Tokens that would mark a model dependency on the scoring branch (D-02).
_MODEL_REFERENCES = {"llm", "extract", "ollama", "model_client"}


def _model_must_not_run(*args: Any, **kwargs: Any) -> Any:
    """A model stub that raises — proves nothing on the score path calls the model."""
    raise AssertionError("the model must not be on the score path (ORCH-03, D-02)")


def _extraction_must_not_run(inp: dict[str, Any]) -> Any:
    """An extraction stub that raises, standing in for an unavailable model."""
    raise RuntimeError("extraction tool unavailable (model off the path)")


async def test_score_node_returns_the_same_colour_with_the_model_stubbed_to_raise(
    monkeypatch,
) -> None:
    """The score node scores the typed case identically with the model stubbed to raise.

    ORCH-03, D-02: the colour cannot come from the model, so removing the model
    cannot change it.
    """
    monkeypatch.setattr("triagedesk.llm.client.extract", _model_must_not_run)

    node = nodes_module.make_nodes(build_graph_tools())["score"]
    update = await node({"case": COMPLETE_CASE, "matched_ids": []})

    expected = scorer.score_priority(COMPLETE_CASE, [])
    assert update["priority"].colour == expected.colour
    assert update["priority"].citations == expected.citations


async def test_full_score_path_reaches_the_gate_without_the_model() -> None:
    """With the model unavailable, the typed case still scores and reaches the gate (ORCH-03)."""
    tools = build_graph_tools(normalize_impl=_extraction_must_not_run)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke(
        {"raw_note": NOTE, "case": COMPLETE_CASE},
        {"configurable": {"thread_id": "purity-score-path"}},
    )

    assert result.get("__interrupt__"), "the model-free score path did not reach the gate"
    expected = scorer.score_priority(COMPLETE_CASE, [])
    assert result["priority"].colour == expected.colour


def test_scoring_branch_references_no_model_client() -> None:
    """The score node's own factory names no model client (ORCH-03, D-02)."""
    tree = ast.parse((GRAPH_DIR / "nodes.py").read_text(encoding="utf-8"))
    factory = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_make_score"
    )
    refs: set[str] = set()
    for node in ast.walk(factory):
        if isinstance(node, ast.Name):
            refs.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr.lower())
    offenders = refs & _MODEL_REFERENCES
    assert not offenders, f"the scoring branch references a model client: {offenders}"
