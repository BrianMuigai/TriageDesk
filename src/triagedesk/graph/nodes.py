"""Thin, single-purpose graph nodes (D-02, D-13, SOLID: S/D).

Every node is narrow: it does ONE thing and delegates the actual work to an
injected tool callable or a pure ``core`` function. The nodes depend on a
``tools`` mapping (name -> async callable), never on a concrete MCP adapter, so
the World A -> B swap touches ``mcp/adapter.py`` alone (D-13, SOLID: D).

Model use is confined to ``normalize`` (through the owned ``normalize_case``
tool, which wraps the local Ollama client). The ``retrieve``, ``score`` and
``verify`` nodes touch no model — the discriminator set and the colour are
deterministic (D-02).

The safety spine lives here too: ``approval_gate`` performs **no side effect
before** :func:`interrupt` (a resumed node re-runs from its top, so any
pre-interrupt write would duplicate — D-04), and ``commit`` builds an
``ApprovalToken`` from the resumed value and calls the gated ``commit_priority``
tool, which refuses anything that is not a well-formed token (GATE-02, D-05).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from langgraph.types import interrupt
from pydantic import BaseModel

from triagedesk.core.hashing import hash_value
from triagedesk.core.schema import (
    CommitResult,
    ExtractionResult,
    HandoverCard,
    MatchResult,
    PriorityResult,
)
from triagedesk.graph.state import TriageState

# The injected tool interface: a name -> async callable mapping. The graph depends
# on THIS shape, not on any concrete adapter (D-13, SOLID: D).
ToolMap = Mapping[str, Callable[[Mapping[str, Any]], Awaitable[Any]]]

# A node reads the state and returns a partial update (sync or async — LangGraph
# accepts both; the tool-calling nodes are async).
NodeFn = Callable[[TriageState], Any]


def parse_tool_result[ModelT: BaseModel](model: type[ModelT], payload: Any) -> ModelT:
    """Validate an MCP tool payload back into its shared contract (D-14).

    The ONE parser for tool output: the adapter may hand back the typed model, a
    list of MCP content blocks (``{"type", "text"}``), a plain mapping, or raw JSON
    text. Every form is normalised to *model* here, so no node duplicates this
    decoding and the tool contract and the graph contract cannot drift.
    """
    if isinstance(payload, model):
        return payload
    if isinstance(payload, list):
        for block in payload:
            text = block.get("text") if isinstance(block, Mapping) else getattr(block, "text", None)
            if isinstance(text, str):
                return model.model_validate_json(text)
    if isinstance(payload, Mapping):
        return model.model_validate(payload)
    return model.model_validate_json(str(payload))


def case_id_for(raw_note: str) -> str:
    """Derive a stable, content-addressed case id from the note (D-06).

    The id is the one canonical hash of the raw note (``core.hashing``), truncated
    for legibility. It is deterministic, so the same note always yields the same id
    — the property the idempotent commit will key on (D-06).
    """
    return hash_value({"raw_note": raw_note})[:16]


def ingest(state: TriageState) -> dict[str, Any]:
    """Validate the raw note into an initial state — deterministic, no I/O (D-01).

    Seeds ``raw_note`` (stripped of surrounding whitespace) and ``attempt=0``. An
    empty note is recorded as a fail-closed ``error`` so nothing downstream guesses.
    """
    note = str(state.get("raw_note") or "").strip()
    if not note:
        return {"raw_note": "", "attempt": 0, "error": "empty triage note"}
    return {"raw_note": note, "attempt": 0, "error": None}


def _make_normalize(tools: ToolMap) -> NodeFn:
    """Build the ``normalize`` node over the injected tool mapping (D-02)."""

    async def normalize(state: TriageState) -> dict[str, Any]:
        """Structure the note through the owned ``normalize_case`` tool (D-02)."""
        result = parse_tool_result(
            ExtractionResult,
            await tools["normalize_case"]({"raw_note": state["raw_note"]}),
        )
        return {"case": result.case}

    return normalize


def _make_retrieve(tools: ToolMap) -> NodeFn:
    """Build the ``retrieve`` node over the injected tool mapping (D-05, D-06)."""

    async def retrieve(state: TriageState) -> dict[str, Any]:
        """Resolve the deterministic discriminator set from the complaint (D-06)."""
        case = state["case"]
        match = parse_tool_result(
            MatchResult,
            await tools["match_discriminators"]({"complaint": case.complaint}),
        )
        return {"matched_ids": list(match.matched_ids), "no_match": match.no_match}

    return retrieve


def _make_score(tools: ToolMap) -> NodeFn:
    """Build the ``score`` node over the injected tool mapping (D-02)."""

    async def score(state: TriageState) -> dict[str, Any]:
        """Score the typed case deterministically — no model on this path (D-02)."""
        payload = {
            "case": state["case"].model_dump(),
            "matched_discriminator_ids": list(state.get("matched_ids") or []),
        }
        priority = parse_tool_result(
            PriorityResult, await tools["score_priority"](payload)
        )
        return {"priority": priority}

    return score


def verify(state: TriageState) -> dict[str, Any]:
    """Deterministic evidence check — no model call (D-01, T-03-05).

    Asserts the citation invariant (``len(citations) == len(triggered_rules)``) and
    that a scored (non-abstained) priority cites at least one rule. Sets
    ``route="ok"`` when both hold, else ``route="retry"`` and bumps ``attempt`` so
    the retry edge is bounded (a stubborn uncited result cannot loop forever).
    """
    priority = state["priority"]
    invariant_holds = len(priority.citations) == len(priority.triggered_rules)
    has_evidence = (
        priority.abstained or priority.out_of_scope or len(priority.citations) >= 1
    )
    if invariant_holds and has_evidence:
        return {"route": "ok"}
    return {"route": "retry", "attempt": int(state.get("attempt") or 0) + 1}


def approval_gate(state: TriageState) -> dict[str, Any]:
    """Pause for a named clinician's decision — NO side effect before the gate (D-04).

    Builds the evidence payload (a pure read of the priority + retrieved ids) and
    then calls :func:`interrupt`. Because a resumed node re-runs from its top, this
    function must remain side-effect-free: the queue write and its audit belong in
    the *next* node, never here (D-04, T-03-02). The resumed value is stored in
    ``approval`` for the commit node to validate.
    """
    priority = state["priority"]
    payload = {
        "case_id": case_id_for(state["raw_note"]),
        "colour": priority.colour,
        "target": priority.target,
        "triggered_rules": [rule.model_dump(mode="json") for rule in priority.triggered_rules],
        "citations": list(priority.citations),
        "missing_vitals": list(priority.missing_vitals),
        "matched_ids": list(state.get("matched_ids") or []),
        "no_match": bool(state.get("no_match")),
    }
    approval = interrupt(payload)
    return {"approval": approval}


def _build_token(approval: Any, priority: PriorityResult) -> dict[str, Any] | None:
    """Build an ``ApprovalToken`` payload from the resumed value (D-05).

    The resume value is untrusted input to the commit node: it is copied verbatim
    and only *filled in* — never invented. An ``approve`` decision defaults
    ``final_colour`` to the scored colour (the clinician approved the shown
    colour); an ``edit`` must carry its own ``final_colour``. Anything missing or
    malformed is passed through unchanged and refused by the gated tool.
    """
    if not isinstance(approval, Mapping):
        return None
    token: dict[str, Any] = dict(approval)
    if token.get("decision") == "approve" and not token.get("final_colour"):
        token["final_colour"] = priority.colour
    return token


def _make_commit(tools: ToolMap) -> NodeFn:
    """Build the ``commit`` node over the injected tool mapping (GATE-02, D-05)."""

    async def commit(state: TriageState) -> dict[str, Any]:
        """Call the gated ``commit_priority`` tool — reachable only via the gate (D-05).

        The token is built from the resumed approval value; the tool validates it
        and refuses anything that is not well-formed, so no write happens without a
        named clinician (GATE-02, T-03-01).
        """
        priority = state["priority"]
        result = parse_tool_result(
            CommitResult,
            await tools["commit_priority"](
                {
                    "case_id": case_id_for(state["raw_note"]),
                    "colour": priority.colour or "",
                    "approval_token": _build_token(state.get("approval"), priority),
                }
            ),
        )
        return {"commit_result": result}

    return commit


def handover(state: TriageState) -> dict[str, Any]:
    """Render the clinician-facing card from the priority + commit — deterministic (D-11).

    A pure template over already-typed facts: no model, no new information. The
    card carries only sourced fields and the named approval; it has no field for a
    diagnosis, assessment, impression, plan or prescription (SAFE-02).
    """
    priority = state["priority"]
    approval = state.get("approval")
    approval = approval if isinstance(approval, Mapping) else {}
    card = HandoverCard(
        case_id=case_id_for(state["raw_note"]),
        colour=priority.colour,
        target=priority.target,
        citations=list(priority.citations),
        triggered_rules=list(priority.triggered_rules),
        missing_vitals=list(priority.missing_vitals),
        matched_discriminator_ids=list(state.get("matched_ids") or []),
        no_discriminator_matched=bool(state.get("no_match")),
        second_look=None,
        decision=approval.get("decision"),
        approved_by=approval.get("approved_by"),
        role=approval.get("role"),
    )
    return {"handover": card}


def make_nodes(tools: ToolMap) -> dict[str, NodeFn]:
    """Assemble the tracer's node functions over the injected tool mapping (D-13).

    The mapping is the graph's ONLY dependency on the outside world; the tool
    callables are injected here and never imported, so the graph stays decoupled
    from the adapter (SOLID: D).
    """
    return {
        "ingest": ingest,
        "normalize": _make_normalize(tools),
        "retrieve": _make_retrieve(tools),
        "score": _make_score(tools),
        "verify": verify,
        "approval_gate": approval_gate,
        "commit": _make_commit(tools),
        "handover": handover,
    }
