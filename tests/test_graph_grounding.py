"""Advisory-grounding proof suite: retrieval writes its own channel and routes nothing.

AGENT-03, D9-07/D9-08. The ``ground`` node surfaces attributable retrieval evidence in a
NEW ``evidence`` channel, placed ``score -> ground -> verify``. Two structural claims are
proven here:

1. CHANNEL ISOLATION — ``ground`` writes only ``evidence``. Running the graph with and
   without retrieval leaves ``priority``, its ``citations``, ``matched_ids`` and
   ``no_match`` byte-identical while ``evidence`` differs, and each run's colour equals a
   *direct* scorer call — the scorer remains the ONLY colour producer.
2. ROUTING NEUTRALITY — ``ground`` is wired by plain edges only; no router reads the new
   channel (proven by an edge-set assertion plus a source scan of all four route functions)
   and no edge from ``ground`` reaches ``commit``.

Offline and deterministic: the shared fakes (``tests/conftest.py``) plus ``InMemorySaver``;
the borrowed subprocess and the model are never launched.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import COMPLETE_CASE, build_graph_tools
from triagedesk.core import scorer
from triagedesk.core.schema import EvidenceResult
from triagedesk.evals.case import load_cases
from triagedesk.graph import build as build_module
from triagedesk.graph.build import build_graph
from triagedesk.graph.nodes import make_nodes

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "evals" / "cases"

NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, "
    "temperature 38.9, no trauma. Presenting with central chest pain."
)

# The evidence-channel name the four route functions must NOT name in their source, so the
# routing-neutrality proof is a real structural check rather than a tautology (D9-08).
_EVIDENCE_TOKEN = "evidence"

# The four routers the neutrality scan inspects — a router that named the channel would
# couple a decision to advisory data, which the phase forbids (D9-08).
_ROUTE_FUNCTIONS = (
    build_module.route_after_normalize,
    build_module.route_after_score,
    build_module.route_after_verify,
    build_module.route_after_assess,
)


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


# ------------------------------------------------ (i) the node writes only its channel


async def test_ground_writes_only_its_own_channel() -> None:
    """``ground`` returns exactly ``{"evidence": EvidenceResult}`` — no routed channel (D9-07)."""
    nodes = make_nodes(build_graph_tools())

    update = await nodes["ground"]({"case": COMPLETE_CASE})

    assert set(update) == {_EVIDENCE_TOKEN}, f"ground wrote extra channels: {set(update)}"
    assert isinstance(update[_EVIDENCE_TOKEN], EvidenceResult)


# ------------------------------------------------------------- (ii) channel isolation


def _no_match_evidence(inp: dict[str, Any]) -> EvidenceResult:
    """A deterministic no-match evidence stub for the isolation proof (differs by design)."""
    return EvidenceResult(passages=[], no_match=True, reason="stub no-match")


async def test_evidence_channel_is_isolated_from_every_routed_channel() -> None:
    """The scored colour and its routing signals are identical with and without retrieval.

    Two questions are answered at once: (a) the routed channels do not differ between a run
    with real retrieval and a run whose retrieval returns a no-match stub — so ``ground``
    cannot leak into them; and (b) each run's colour equals a direct ``scorer`` call on the
    same case and matched ids — so the colour is provably the scorer's, never retrieval's.
    """
    default_calls: list[tuple[str, Any]] = []
    app_default = build_graph(build_graph_tools(calls=default_calls), checkpointer=InMemorySaver())
    run_default = await app_default.ainvoke({"raw_note": NOTE}, _config("ground-default"))

    stub_calls: list[tuple[str, Any]] = []
    app_stub = build_graph(
        build_graph_tools(calls=stub_calls, retrieve_impl=_no_match_evidence),
        checkpointer=InMemorySaver(),
    )
    run_stub = await app_stub.ainvoke({"raw_note": NOTE}, _config("ground-stub"))

    # (a) The routed channels are identical across the two runs.
    assert run_default["priority"].colour == run_stub["priority"].colour
    assert run_default["priority"].citations == run_stub["priority"].citations
    assert run_default["matched_ids"] == run_stub["matched_ids"]
    assert bool(run_default.get("no_match")) == bool(run_stub.get("no_match"))
    # ...but the advisory channel genuinely differs — retrieval ran and wrote its own data.
    assert run_default["evidence"] != run_stub["evidence"]

    # (b) Each run's colour is provably the scorer's for its own matched ids.
    for run in (run_default, run_stub):
        expected = scorer.score_priority(COMPLETE_CASE, list(run["matched_ids"]))
        assert run["priority"].colour == expected.colour


# ---------------------------------------------------------- (iii) routing neutrality


def test_ground_is_wired_by_plain_edges_and_routes_nothing() -> None:
    """The edge set admits ``score -> ground -> verify`` and no ``ground`` edge reaches commit."""
    graph = build_graph(build_graph_tools())
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("score", "ground") in edges, "ground no longer follows score"
    assert ("ground", "verify") in edges, "the plain ground -> verify edge is missing"
    # ``ground`` must not sit on any path to the commit: its only outgoing edge is ``verify``.
    assert ("ground", "commit") not in edges
    assert {target for source, target in edges if source == "ground"} == {"verify"}

    # No router's source names the evidence channel — the structural neutrality guarantee.
    for route in _ROUTE_FUNCTIONS:
        source = inspect.getsource(route)
        assert _EVIDENCE_TOKEN not in source, (
            f"{route.__name__} names the evidence channel — a router reads advisory data"
        )


# ---------------------------------------------------------------- (iv) the tool is reached


async def test_ground_reaches_the_retrieve_evidence_tool() -> None:
    """The node calls the injected ``retrieve_evidence`` mapping with the case's complaint."""
    calls: list[tuple[str, Any]] = []
    app = build_graph(build_graph_tools(calls=calls), checkpointer=InMemorySaver())

    await app.ainvoke({"raw_note": NOTE}, _config("ground-tool"))

    retrieval_calls = [inp for name, inp in calls if name == "retrieve_evidence"]
    assert retrieval_calls, "the ground node never called retrieve_evidence"
    assert retrieval_calls[0]["complaint"] == COMPLETE_CASE.complaint


# --------------------------------------------- (v) E-09 is an honest defer, never an alias


async def test_e09_grounding_is_an_honest_no_match_defer_with_no_write(memory_store) -> None:
    """E-09's grounding is a ``no_match`` defer (the committed outcome) — never tuned green.

    This outcome is the DECLARED, COMMITTED deferral (D9-09 / D8-11): real retrieval surfaces
    the coverage gap and the graph defers to a safe terminal with no queue row. It must NEVER
    be "fixed" by adding a literal discriminator alias, fixture or threshold to make it pass.
    """
    spec = next(case for case in load_cases(CASES_DIR) if case.id == "E-09")
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=spec.case, calls=calls, store=memory_store)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": spec.note}, _config("ground-e09"))

    evidence = result["evidence"]
    assert isinstance(evidence, EvidenceResult)
    assert evidence.no_match is True, "E-09's grounding was tuned green"
    assert evidence.passages == []
    assert spec.declared_failure is True
    assert result.get("escalation") is not None, "E-09 did not reach a safe terminal"
    assert "commit_priority" not in [name for name, _ in calls]
    assert memory_store.rows == [], "the deferred E-09 wrote a queue row"


# ---------------------------------------------------- (vi) the delivered colour is unchanged


async def test_ground_does_not_change_the_delivered_colour() -> None:
    """A matched case reaches the gate, and the payload colour equals the direct scorer's."""
    app = build_graph(build_graph_tools(case=COMPLETE_CASE), checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE}, _config("ground-colour"))

    assert result.get("__interrupt__"), "the matched case did not reach the gate"
    payload = result["__interrupt__"][0].value
    expected = scorer.score_priority(COMPLETE_CASE, list(result.get("matched_ids") or []))
    assert payload["colour"] == expected.colour
    assert result["priority"].colour == expected.colour
