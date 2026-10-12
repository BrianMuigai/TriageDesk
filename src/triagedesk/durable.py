"""The ONE durable pause/resume helper (AGENT-01, D6-01, D6-08…D6-15).

This module is the single home for the durable lifecycle: an entry point derives the
content-addressed ``thread_id``, runs the graph over the SQLite checkpointer
(``graph.build.checkpointed_graph``), pauses at the approval gate, and — in a LATER
process over the SAME file — resumes the paused thread to a committed handover.

It exists so ``demo --durable`` and ``triagedesk resume`` cannot drift: both drive the
same ``invoke_graph`` primitive and the same derivation. It sits ABOVE ``graph``,
``evals`` and ``store`` and never imports ``demo`` (so ``resume`` never depends on the
demo). It adds NO store resolver of its own: the gated commit and its audit interceptor
resolve the store through the ONE existing seam (``mcp.server.resolve_store``).

Design rules honoured here (DRY/SOLID):

* ``graph.nodes.case_id_for_note`` stays the ONE ``thread_id`` derivation — re-exported as
  :func:`derive_thread_id` (which strips first, matching the value ``ingest`` writes back
  into ``raw_note``, so the printed id equals the id the gate used — Pitfall 5).
* ``graph.build.checkpointed_graph`` stays the ONE durable saver factory.
* :func:`approval_decision` is the ONE place the CLI decision shape is validated, so the
  CLI stays a shell (SOLID: S).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langgraph.types import Command

from triagedesk.core.schema import CaseInput
from triagedesk.evals.case import TERMINAL_OUTCOMES, CaseSpec
from triagedesk.graph.build import checkpointed_graph
from triagedesk.graph.nodes import ToolMap, case_id_for_note

# The decisions the gate accepts (mirrors ``ApprovalToken.decision``).
_DECISIONS = ("approve", "edit", "dismiss")

# The placeholder case the resume tool mapping is built from. ``resume`` never runs a
# pre-gate node (the checkpoint short-circuits them), so this case is never read — it is
# present only to satisfy ``build_graph``'s allowlist assertion when the tool mapping is
# assembled. Its ``expected`` is a declared harness terminal (never a SATS colour literal,
# which must live only in ``data/*.yaml`` per CONVENTIONS §1).
_RESUME_PLACEHOLDER = CaseSpec(
    id="resume-placeholder",
    description="Placeholder case for the resume tool mapping; never read on resume.",
    note="",
    case=CaseInput(),
    expected=TERMINAL_OUTCOMES[0],
    pass_criteria="never evaluated: the checkpoint short-circuits every pre-gate node",
    source="src/triagedesk/durable.py",
)


class DurableError(RuntimeError):
    """Raised when a durable operation cannot be run (no pending gate, missing flag)."""


@dataclass(frozen=True)
class PausedRun:
    """The outcome of running a case to the approval gate (without resuming).

    ``paused`` is True only when the run stopped at the gate with a pending interrupt;
    ``payload`` carries the interrupt value the clinician would see. ``existed`` is True
    when a durable thread for the same case already had state — the caller cannot replay
    it without removing the checkpoint file.
    """

    thread_id: str
    config: dict[str, Any]
    result: Mapping[str, Any]
    payload: dict[str, Any] | None
    paused: bool
    existed: bool


def derive_thread_id(raw_note: str) -> str:
    """Derive the durable ``thread_id`` from the note — the ONE content derivation (D6-01).

    Delegates to ``graph.nodes.case_id_for_note`` (never a second hash scheme, never a random
    id, never a per-entry-point prefix). The note is stripped FIRST, matching the value
    ``ingest`` writes back into ``raw_note``, so the printed id equals the id the gate and
    the commit used (Pitfall 5).
    """
    return case_id_for_note(raw_note)


async def invoke_graph(
    graph: Any,
    initial: Mapping[str, Any],
    config: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    """Invoke the graph once, resuming past the gate if it paused — the shared primitive.

    The one invoke→interrupt→resume step, so the eval runner and the demo share a single
    implementation (each caller keeps its OWN ``thread_id`` policy — SOLID: S). Returns
    the final state and the interrupt payload (``None`` when the run never paused).
    """
    result = await graph.ainvoke(initial, config)
    payload: dict[str, Any] | None = None
    if result.get("__interrupt__"):
        payload = dict(result["__interrupt__"][0].value)
        result = await graph.ainvoke(Command(resume=dict(decision)), config)
    return result, payload


async def run_to_gate(
    tools: ToolMap,
    *,
    raw_note: str,
    case: CaseInput,
    db_path: str | Path,
    previous_case: CaseInput | None = None,
) -> PausedRun:
    """Run one case to the approval gate over the durable saver, WITHOUT resuming (D6-11).

    The thread id is content-derived, so the same case lands on the same thread from any
    entry point and after a restart. When the case already has durable state the run is
    NOT replayed: ``existed`` is True and no node runs.
    """
    thread_id = derive_thread_id(raw_note)
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    initial: dict[str, Any] = {"raw_note": raw_note, "case": case}
    if previous_case is not None:
        initial["previous_case"] = previous_case

    async with checkpointed_graph(tools, Path(db_path)) as graph:
        snapshot = await graph.aget_state(config)
        if snapshot.values:
            return PausedRun(
                thread_id=thread_id,
                config=config,
                result=dict(snapshot.values),
                payload=None,
                paused=False,
                existed=True,
            )
        result = await graph.ainvoke(initial, config)
        payload = (
            dict(result["__interrupt__"][0].value) if result.get("__interrupt__") else None
        )
        return PausedRun(
            thread_id=thread_id,
            config=config,
            result=result,
            payload=payload,
            paused=payload is not None,
            existed=False,
        )


async def resume_paused(
    tools: ToolMap,
    *,
    thread_id: str,
    decision: Mapping[str, Any],
    db_path: str | Path,
) -> Mapping[str, Any]:
    """Resume a paused thread to a committed handover, or refuse if nothing is pending.

    The pending-gate check runs BEFORE the graph is invoked, so an absent thread touches
    no store (and launches no borrowed subprocess) — it raises :class:`DurableError`.
    """
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    async with checkpointed_graph(tools, Path(db_path)) as graph:
        snapshot = await graph.aget_state(config)
        if not snapshot.next:
            raise DurableError(
                f"no pending approval gate for thread_id {thread_id} in {db_path}"
            )
        return await graph.ainvoke(Command(resume=dict(decision)), config)


def approval_decision(
    decision: str,
    *,
    approver: str | None = None,
    role: str | None = None,
    colour: str | None = None,
    approved_at: str | None = None,
) -> dict[str, Any]:
    """Build the resume value for the gate — the ONE place the CLI decision shape lives.

    A ``dismiss`` needs no identity and no colour (the gate refuses it and writes nothing),
    but it still carries the ``approved_at`` timestamp so it is a **well-formed**
    :class:`~triagedesk.core.schema.ApprovalToken`: the gate therefore reaches its own
    ``dismiss`` branch instead of reporting the token as malformed (WR-05). An
    ``approve``/``edit`` requires a non-empty ``--approver`` and ``--role`` — a
    whitespace-only value counts as absent and is rejected, so a fabricated blank identity
    can never approve (T-06-05, WR-06) — and an ``edit`` additionally requires ``--colour``;
    a missing flag raises :class:`DurableError` naming it rather than fabricating a value.
    """
    timestamp = approved_at or datetime.now(UTC).isoformat()
    if decision == "dismiss":
        return {"decision": "dismiss", "approved_at": timestamp}
    if decision not in _DECISIONS:
        raise DurableError(
            f"unknown decision {decision!r}; expected one of {', '.join(_DECISIONS)}"
        )
    if not (approver or "").strip():
        raise DurableError(f"--approver is required for a {decision!r} decision")
    if not (role or "").strip():
        raise DurableError(f"--role is required for a {decision!r} decision")
    token: dict[str, Any] = {
        "decision": decision,
        "approved_by": approver,
        "role": role,
        "approved_at": timestamp,
    }
    if decision == "edit":
        if not (colour or "").strip():
            raise DurableError("--colour is required for an 'edit' decision")
        token["final_colour"] = colour
    return token


async def resume_thread(
    *,
    thread_id: str,
    decision: Mapping[str, Any],
    db_path: str | Path,
) -> Mapping[str, Any]:
    """Resume a durable thread from the CLI — the ONE place the resume tools are built.

    The tool mapping is built in-process from the placeholder case (the owned tools are
    called in-process, so no owned MCP server is launched and no model is needed); the
    pre-gate nodes that would read the case are short-circuited by the checkpoint. The
    store is NOT resolved or injected here: the gated commit and its audit interceptor
    resolve it through the ONE existing seam (``mcp.server.resolve_store``), so there is
    exactly one store-resolution path.
    """
    from triagedesk.evals.tools import build_tools
    from triagedesk.evals.usage import UsageRecorder

    tools = build_tools(_RESUME_PLACEHOLDER, offline=True, recorder=UsageRecorder())
    return await resume_paused(
        tools, thread_id=thread_id, decision=decision, db_path=db_path
    )


__all__ = [
    "DurableError",
    "PausedRun",
    "approval_decision",
    "derive_thread_id",
    "invoke_graph",
    "resume_paused",
    "resume_thread",
    "run_to_gate",
]
