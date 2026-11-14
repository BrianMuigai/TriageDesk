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

import functools
import inspect
from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from triagedesk.core import emergency as emergency_module
from triagedesk.core import schema as schema_module
from triagedesk.core.schema import CaseInput, PlanAction, PlanDecision
from triagedesk.graph.nodes import NodeFn, ToolMap, case_id_for_note, make_nodes
from triagedesk.graph.state import TriageState
from triagedesk.observability import bind_trace, span
from triagedesk.store import DOMAIN_DB_PATH

# The LangGraph runtime-state path, named once so no caller inlines a filename
# (D-09). ``DOMAIN_DB_PATH`` (``triage.db``) is the clinical record + audit, owned
# by the store package (single source); the two are deliberately DIFFERENT files.
CHECKPOINTS_DB_PATH = Path("checkpoints.db")

__all__ = [
    "CHECKPOINTS_DB_PATH",
    "DOMAIN_DB_PATH",
    "OWNED_TOOL_ALLOWLIST",
    "PLANNER_NODES",
    "TRACER_NODES",
    "assert_tool_allowlist",
    "build_graph",
    "checkpointed_graph",
    "in_memory_checkpointer",
    "load_graph_tools",
    "open_checkpointer",
    "route_after_emergency",
    "route_after_normalize",
    "route_after_plan",
    "route_after_retrieve",
    "route_after_score",
    "route_after_assess",
    "route_after_verify",
    "run_case",
]

# The least-privilege allowlist (SAFE-03, D-12): the graph may call ONLY these owned
# tools. Declared ONCE here and asserted at both edges (composition and discovery) so
# a missing or unexpected tool fails loudly instead of silently changing which
# capabilities the agent can reach (T-03-23). The owned surface is nine tools; the
# same nine-name set is mirrored at the harness, the test fake and the exact-set
# assertion, which must move together or composition raises (D9-05).
# ``plan_next_step`` and ``request_clarification`` are the v1.3 investigation tools: the
# ``plan`` node and the ``ask_question`` node call them (Phase 23), so all nine names are
# on the shipped path and the allowlist is exactly the callable surface.
OWNED_TOOL_ALLOWLIST: tuple[str, ...] = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "raise_recheck_flag",
    "plan_next_step",
    "request_clarification",
    "assess_confidence",
    "retrieve_evidence",
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
    "emergency_check",
    "normalize",
    "retrieve",
    # The bounded investigation loop (ADAPT-01): `retrieve -> plan -> action -> plan …` and
    # `finish_investigation` as the ONE door into the kernel. The emergency arm skips `plan`
    # and enters `finish_investigation` directly, so the kernel's inbound edge is exact.
    "plan",
    "gather_evidence",
    "ask_question",
    "re_extract",
    "finish_investigation",
    "score",
    "ground",
    "verify",
    "recheck",
    "assess",
    "approval_gate",
    "commit",
    "handover",
    "request_missing_info",
    "clarify",
    "escalate",
)

# The four nodes that exist ONLY on the adaptive arm (MEAS-02). The baseline arm omits them
# and wires ``retrieve -> finish_investigation`` directly, so it is exactly the v1.2 path.
# Declared once so the builder and the structural proof read the same set (DRY).
PLANNER_NODES: tuple[str, ...] = (
    "plan",
    "gather_evidence",
    "ask_question",
    "re_extract",
)

def route_after_emergency(state: TriageState) -> str:
    """Choose the fast or normal arm after the deterministic pre-check (EMERG-01).

    A fired verdict goes straight to ``retrieve`` — extraction is skipped, the kernel is
    not. Every other case (no structured case, incomplete vitals, out of scope, or a
    colour below the most urgent band) takes the normal arm through ``normalize``, so no
    value is ever guessed (EMERG-04).
    """
    verdict = state.get("emergency_verdict")
    if verdict is not None and verdict.fired:
        return "retrieve"
    return "normalize"

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


def route_after_retrieve(state: TriageState) -> str:
    """Choose the next node after ``retrieve`` — the emergency bypass or the planner (ADAPT-01).

    A fired emergency verdict goes straight to ``finish_investigation``: the vitals already
    carry the answer, so the model does not get a turn to delay the patient (EMERG-01/03).
    Every other case enters the bounded investigation loop at ``plan``.

    Both arms enter the kernel through ``finish_investigation``, which is what keeps
    ``predecessors("score") == {"finish_investigation"}`` exact rather than approximate
    (ADAPT-03).

    This router is used ONLY by the adaptive arm. The baseline arm
    (``build_graph(..., planner=False)``) has no ``plan`` node and wires ``retrieve`` to
    ``finish_investigation`` with a plain edge, so the baseline is exactly the v1.2 path
    (MEAS-02).
    """
    verdict = state.get("emergency_verdict")
    if verdict is not None and verdict.fired:
        return "finish_investigation"
    return "plan"


def route_after_plan(state: TriageState) -> str:
    """Choose the next node from the decision the guard honoured (ADAPT-01, ADAPT-03).

    The returned token is the decision's own ``PlanAction`` value, which is also the node
    name for that action — so the closed set of actions and the set of reachable nodes are
    one declaration (``core.schema.PlanAction``), and a new action cannot be routed in one
    place and forgotten in another (DRY).

    ``finish_investigation`` is the only value that reaches ``score``. A plan that is absent
    (an impossible state on this arm) degrades to the exit, so the kernel still runs.
    """
    decision = state.get("plan")
    if isinstance(decision, PlanDecision):
        return decision.action.value
    return PlanAction.FINISH_INVESTIGATION.value


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


def route_after_assess(state: TriageState) -> str:
    """Choose the next node after ``assess`` — no deferral or clarification reaches the gate.

    The confidence signal can only make the system *more* cautious. A **clarification**
    (COV-03) routes to the bounded ``clarify`` terminal, which asks at most three questions
    and has no edge to ``commit``; it is allowed on the first round only, so a second
    ambiguity cannot spin. A **deferral** routes to a safe terminal — ``escalate``, or
    ``request_missing_info`` when the priority still reports a missing scored vital — both of
    which end at ``END`` with no edge to ``commit``. The neutral, delivered arm proceeds to
    ``approval_gate`` as before. Because the deterministic ``recheck`` runs *before* ``assess``,
    neither terminal suppresses the safety recheck.

    The ``request_missing_info`` arm is a deliberately RETAINED defensive guard. Under the
    current wiring :func:`route_after_score` already diverts every ``missing_vitals`` case
    to ``request_missing_info``, so such a case never reaches ``assess`` and this arm is
    unreachable today (covered directly by ``tests/test_graph_confidence.py``). It is kept
    so a deferral can never fall through to the gate if that score-time diversion is ever
    changed: the one-way safety property then holds by construction, not by the accident of
    the current upstream routing.
    """
    signal = state.get("confidence")
    if signal is not None:
        # A clarification (COV-03) is bounded to ONE answer round: on the second
        # ambiguity the case defers rather than asking again, so the loop cannot spin.
        if signal.action == "clarify" and int(state.get("clarification_round") or 0) < 1:
            return "clarify"
        if signal.deferral:
            priority = state.get("priority")
            # Defensive arm (see docstring): unreachable while ``route_after_score`` diverts
            # missing-vitals cases, but retained so a deferral always lands on a safe terminal.
            if priority is not None and priority.missing_vitals:
                return "request_missing_info"
            return "escalate"
    return "approval_gate"


def route_after_verify(state: TriageState) -> str:
    """Choose the next node after ``verify`` — a failed check is terminal (T-03-05).

    ``ok`` routes to the second look and then the gate. A failed check stops at
    ``END``: the check is a structural invariant the deterministic scorer upholds by
    construction, so re-running the same deterministic ``score`` on the same case
    cannot change the outcome. The terminal is fail-closed — no gate, no commit, no
    card.
    """
    if state.get("route") == "ok":
        return "recheck"
    return END


def _spanned(name: str, node: NodeFn) -> NodeFn:
    """Wrap ONE node so it binds the trace id and opens a ``node`` span (D7-01, D7-05).

    The wrapper is applied at the composition root (:func:`build_graph`), never inside a
    node body, so every node keeps its single responsibility and the topology is
    untouched (SOLID: S). It derives the trace id from the state's ``raw_note`` through
    the ONE note derivation (``graph.nodes.case_id_for_note`` — the same value
    ``durable.derive_thread_id`` produces), binds it for the node's tool/model calls, and
    runs the node inside one ``node`` span (D7-05, D7-07). ``functools.wraps`` preserves
    the node's ``__name__`` so LangGraph node identity and tracebacks are unchanged.

    This module reads NO environment variable and imports no external network client or
    non-local model provider: it imports only the span context/writer
    (``triagedesk.observability``), so the safety-spine AST guards stay green (D7-04).
    """

    @functools.wraps(node)
    async def wrapped(state: TriageState) -> Any:
        trace_id = case_id_for_note(str(state.get("raw_note") or ""))
        bind_trace(trace_id)
        with span("node", name):
            result = node(state)
            return await result if inspect.isawaitable(result) else result

    return wrapped


def build_graph(tools: ToolMap, checkpointer: Any = None, planner: bool = True) -> Any:
    """Compile the tracer graph over the injected ``tools`` mapping (D-01, D-13).

    ``START -> ingest -> emergency_check -> (fast: retrieve | normal: normalize) ->
    (retrieve -> finish_investigation | plan) -> (plan -> gather_evidence | ask_question |
    re_extract | finish_investigation) -> finish_investigation -> score -> (score: escalate |
    request_missing_info | ground) -> (ground -> verify) -> (verify -> recheck) -> assess ->
    (approval_gate -> commit -> handover | escalate | request_missing_info) -> END``.

    The ``emergency_check``, ``normalize``, ``retrieve``, ``plan``, ``score``, ``verify`` and
    ``assess`` edges are conditional. The fast arm skips ``normalize`` ONLY (EMERG-01) and
    rejoins the kernel at ``finish_investigation``; the investigation loop runs between
    ``retrieve`` and ``finish_investigation`` and every one of its actions loops back to the
    planner (or to retrieval) — none of them has an edge to ``score`` (ADAPT-03). The
    recovery/abstention terminals have no edge to ``commit``, and a deferral from ``assess``
    only reaches those terminals (D8-12).
    ``ground`` sits between ``score`` and ``verify`` and is ROUTING-NEUTRAL (D9-07/D9-08):
    it writes only its own ``evidence`` channel and is wired by a plain edge, so no router
    reads it and the path taken is unchanged. ``checkpointer`` is injected so the same
    builder serves both the in-memory test graph and the durable SQLite graph (D-09).

    ``planner=False`` selects the **baseline arm** (MEAS-02): the four planner nodes are not
    added and ``retrieve`` is wired straight to ``finish_investigation`` with a plain edge —
    exactly the v1.2 path, no model proposal and no investigation. The kernel, the gate and
    the commit are identical on both arms, so ``predecessors("score")`` and
    ``predecessors("commit")`` are unchanged by the switch; only what happens *before* the
    kernel differs. That is what makes the adaptive-vs-baseline measurement a comparison of
    the envelope, not of the safety spine.

    The injected tool surface is asserted against the allowlist FIRST, so a drifted or
    unexpected tool fails loudly at composition rather than silently reaching the
    agent (SAFE-03, T-03-23).
    """
    assert_tool_allowlist(tools.keys())
    nodes = make_nodes(tools)
    graph: StateGraph = StateGraph(TriageState)
    node_names = TRACER_NODES if planner else tuple(
        name for name in TRACER_NODES if name not in PLANNER_NODES
    )
    for name in node_names:
        graph.add_node(name, _spanned(name, nodes[name]))

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "emergency_check")
    graph.add_conditional_edges(
        "emergency_check",
        route_after_emergency,
        {"retrieve": "retrieve", "normalize": "normalize"},
    )
    graph.add_conditional_edges(
        "normalize",
        route_after_normalize,
        {"escalate": "escalate", "retrieve": "retrieve"},
    )
    # ``retrieve`` is the fork between the deterministic bypass and the bounded
    # investigation loop (ADAPT-01). Both arms converge on ``finish_investigation``, the
    # kernel's ONLY inbound edge, so the emergency arm skips ``plan`` and nothing else.
    # The baseline arm (``planner=False``) has no loop at all: every case goes straight to
    # ``finish_investigation``, which is the v1.2 path (MEAS-02).
    if planner:
        graph.add_conditional_edges(
            "retrieve",
            route_after_retrieve,
            {"finish_investigation": "finish_investigation", "plan": "plan"},
        )
        # The plan's edge map is DERIVED from the closed action set: every action's value is the
        # node that implements it, so the router cannot name a node the planner cannot choose.
        graph.add_conditional_edges(
            "plan",
            route_after_plan,
            {action.value: action.value for action in PlanAction},
        )
        # The investigation actions are read-only and all but the exit loop back: evidence and a
        # re-extraction return to the planner, a question returns to retrieval so the answer is
        # matched. None of them has an edge to ``score`` (ADAPT-03).
        graph.add_edge("gather_evidence", "plan")
        graph.add_edge("ask_question", "retrieve")
        graph.add_edge("re_extract", "retrieve")
    else:
        graph.add_edge("retrieve", "finish_investigation")
    graph.add_edge("finish_investigation", "score")
    graph.add_conditional_edges(
        "score",
        route_after_score,
        {
            "escalate": "escalate",
            "request_missing_info": "request_missing_info",
            "verify": "ground",
        },
    )
    # ``ground`` is advisory and routing-neutral (D9-08): it is entered by the ``score``
    # conditional edge's ``verify`` route LABEL (the decision is unchanged) but wired by a
    # PLAIN edge to ``verify``, so the path taken is identical whether or not retrieval runs.
    graph.add_edge("ground", "verify")
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {"recheck": "recheck", END: END},
    )
    graph.add_edge("recheck", "assess")
    graph.add_conditional_edges(
        "assess",
        route_after_assess,
        {
            "escalate": "escalate",
            "request_missing_info": "request_missing_info",
            "clarify": "clarify",
            "approval_gate": "approval_gate",
        },
    )
    graph.add_edge("approval_gate", "commit")
    graph.add_edge("commit", "handover")
    graph.add_edge("handover", END)
    graph.add_edge("request_missing_info", END)
    graph.add_edge("clarify", END)
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
    clarification_round: int = 0,
) -> Mapping[str, Any]:
    """Run one case through the graph, resolving tools from the owned server by default.

    A thin entry point: ``tools`` defaults to the owned server's mapping (the DIP
    seam); the caller supplies a ``config`` (a ``thread_id``) when a checkpointer is
    in use so a paused run can be resumed. ``previous_case`` is the optional earlier
    serial case: when present it seeds the state so the recheck node can raise a
    second-look flag against the current vitals (GATE-04, D-07).

    ``clarification_round`` bounds the clarification terminal (COV-03). The first pass
    is round 0; a caller that has the nurse's answer runs once more with
    ``clarification_round=1`` and the answer appended to the note. A second ambiguity
    then defers rather than asking a third time.
    """
    resolved = tools if tools is not None else await load_graph_tools()
    graph = build_graph(resolved)
    initial: dict[str, Any] = {
        "raw_note": raw_note,
        "clarification_round": clarification_round,
    }
    if previous_case is not None:
        initial["previous_case"] = previous_case
    return await graph.ainvoke(initial, dict(config or {}))


@asynccontextmanager
async def open_checkpointer(db_path: str | Path) -> AsyncIterator[AsyncSqliteSaver]:
    """Open the SQLite checkpointer with the ONE explicit state-type allowlist (D-09, T-07-06).

    The ONE saver factory: the durable graph (:func:`checkpointed_graph`) and the read-only
    replay projection (:func:`triagedesk.replay.read_recorded`) both open their checkpointer
    here, so the serializer allowlist AND the saver wiring exist once (DRY, SOLID: D). The
    allowlist is explicit — never ``True`` — so a tampered checkpoint cannot deserialise an
    arbitrary type.
    """
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        saver.serde = JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
        yield saver


def in_memory_checkpointer() -> InMemorySaver:
    """The in-memory flavour of the ONE saver factory, carrying the SAME allowlist (D-09, T-07-06).

    The ephemeral counterpart to :func:`open_checkpointer`, sitting beside it so both flavours
    of "a msgpack-allowlisted saver" have one home (DRY, SOLID: D). It registers the SAME
    explicit state-type allowlist as the durable saver — never ``True`` — so an eval or demo
    resume cannot trip the future strict-msgpack block and the in-memory saver's
    deserialisation surface is exactly the durable saver's. An allowlist is deliberate: a
    tampered checkpoint cannot deserialise an arbitrary type.
    """
    return InMemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
    )


@asynccontextmanager
async def checkpointed_graph(
    tools: ToolMap, db_path: Path = CHECKPOINTS_DB_PATH
) -> AsyncIterator[Any]:
    """Compile the graph over the durable SQLite checkpointer (D-09, M-6).

    Opens the durable saver through :func:`open_checkpointer` (the ONE saver factory) and
    yields the compiled graph. The paused state survives a process restart: reopening the
    same file with a fresh saver still reports the pending interrupt.
    """
    async with open_checkpointer(db_path) as saver:
        yield build_graph(tools, checkpointer=saver)


def _allowed_msgpack_modules() -> list[tuple[str, str]]:
    """The ONE allowlist of state types the checkpointer may (de)serialise.

    Derived from the modules that declare state contracts — ``core.schema`` and
    ``core.emergency`` — rather than hand-listed, so a new contract is covered
    automatically (DRY). An allowlist — never ``True`` — so the checkpointer cannot
    deserialise an arbitrary type from a tampered checkpoint. ``core.emergency`` is listed
    explicitly because a blocked type is silently downgraded to a plain dict on resume,
    which would erase the verdict's type (EMERG-05).

    Enums declared in those modules are part of the allowlist too: a state contract carries
    them as members (``InvestigationFacts.history`` is a ``list[PlanAction]``, the interrupt
    vocabulary is ``InterruptType``), and a blocked enum is silently downgraded to a bare
    ``str`` on resume — the same class of loss as a blocked model. The scan is by module, so
    it stays one rule instead of a growing literal list.
    """
    state_modules = (schema_module, emergency_module)
    return [
        (module.__name__, name)
        for module in state_modules
        for name, obj in vars(module).items()
        if isinstance(obj, type)
        and issubclass(obj, (BaseModel, Enum))
        and obj.__module__ == module.__name__
    ]
