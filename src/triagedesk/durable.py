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

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langgraph.types import Command

from triagedesk.core.schema import CaseInput, InterruptType
from triagedesk.graph.build import checkpointed_graph
from triagedesk.graph.nodes import ToolMap, case_id_for_note

# The decisions the gate accepts (mirrors ``ApprovalToken.decision``).
_DECISIONS = ("approve", "edit", "dismiss")

# The ONE policy contract: given an interrupt payload, return the value to resume with — or
# ``None`` to leave the run paused so the caller can present it. A policy is how the CLI, the
# desk and the eval runner answer different payload types without a second pause/resume loop.
RespondPolicy = Callable[[Mapping[str, Any]], Mapping[str, Any] | None]


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
    *,
    respond: RespondPolicy | None = None,
) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    """Invoke the graph, then answer every interrupt it raises — the shared primitive.

    The one invoke→interrupt→resume step, so the eval runner, the demo and the durable
    resume share a single implementation (each caller keeps its OWN ``thread_id`` policy —
    SOLID: S). Returns the final state and the FIRST interrupt payload (``None`` when the
    run never paused) — the payload the caller presents.

    ``respond`` decides what each payload is answered with, and returning ``None`` from it
    leaves the run paused. The default policy is the existing approval behaviour: it
    resumes an approval with *decision* and **stops** at an elicitation, so no current
    caller changes and an approval is never used to answer a question (ELICIT-05).
    """
    policy = respond or _approval_only(decision)
    result = await graph.ainvoke(initial, config)
    return await _drive(graph, config, result, policy)


def pending_interrupt(snapshot: Any) -> dict[str, Any] | None:
    """The value of the first pending interrupt in a checkpoint *snapshot*, or ``None``.

    The ONE reader of LangGraph's snapshot shape, so no caller reaches into
    ``snapshot.tasks[*].interrupts`` itself and a resume can decide what it is answering
    (an approval or a question) without guessing.
    """
    for task in getattr(snapshot, "tasks", ()) or ():
        for pending in getattr(task, "interrupts", ()) or ():
            value = getattr(pending, "value", None)
            if isinstance(value, Mapping):
                return dict(value)
    return None


def _approval_only(decision: Mapping[str, Any]) -> RespondPolicy:
    """The DEFAULT policy: answer an approval, stop at a question (ELICIT-05).

    Before elicitation existed the graph interrupted once, at the gate. Keeping this policy
    as the default means every current caller behaves exactly as before, while a question is
    never answered with an approval token — it is left paused for a surface to present.
    """

    def policy(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        # Read the ONE declaration in ``core.schema.InterruptType`` (not a literal), so the
        # discriminator cannot drift from the payload the graph and the adapter mint.
        if payload.get("type") == InterruptType.ELICITATION:
            return None
        return dict(decision)

    return policy


async def _drive(
    graph: Any,
    config: Mapping[str, Any],
    result: Mapping[str, Any],
    policy: RespondPolicy,
) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    """Answer interrupts until the run settles — the ONE pause/resume loop.

    Each round hands the payload to *policy*; a returned mapping resumes the graph, and
    ``None`` stops (the run stays paused and the caller presents the payload it already
    has). The FIRST payload is remembered, because that is what a caller shows a human.
    """
    payload: dict[str, Any] | None = None
    while result.get("__interrupt__"):
        value = dict(result["__interrupt__"][0].value)
        if payload is None:
            payload = value
        answer = policy(value)
        if answer is None:
            break
        result = await graph.ainvoke(Command(resume=dict(answer)), config)
    return result, payload


async def run_to_gate(
    tools: ToolMap,
    *,
    raw_note: str,
    case: CaseInput,
    db_path: str | Path,
    previous_case: CaseInput | None = None,
    clarification_round: int = 0,
) -> PausedRun:
    """Run one case to the approval gate over the durable saver, WITHOUT resuming (D6-11).

    The thread id is content-derived, so the same case lands on the same thread from any
    entry point and after a restart. When the case already has durable state the run is
    NOT replayed: ``existed`` is True and no node runs.
    """
    thread_id = derive_thread_id(raw_note)
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    initial: dict[str, Any] = {
        "raw_note": raw_note,
        "case": case,
        "clarification_round": clarification_round,
    }
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
    decision: Mapping[str, Any] | None = None,
    db_path: str | Path,
    respond: RespondPolicy | None = None,
) -> Mapping[str, Any]:
    """Resume a paused thread, answering each interrupt through the ONE policy.

    The pending-gate check runs BEFORE the graph is invoked, so an absent thread touches
    no store (and launches no borrowed subprocess) — it raises :class:`DurableError`.

    *decision* is the pre-built resume value (the historical shape: one approval). *respond*
    is the policy form: it receives the pending payload and returns the resume value, or
    ``None`` to leave the run paused — which is what a surface does when answering a question
    reveals an approval gate it must not decide. Exactly one of them is required.
    """
    if decision is None and respond is None:
        raise DurableError("a decision or a respond policy is required to resume a thread")
    policy = respond or _approval_only(decision or {})
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    async with checkpointed_graph(tools, Path(db_path)) as graph:
        snapshot = await graph.aget_state(config)
        if not snapshot.next:
            raise DurableError(
                f"no pending approval gate for thread_id {thread_id} in {db_path}"
            )
        pending = pending_interrupt(snapshot)
        answer = policy(pending) if pending is not None else dict(decision or {})
        if answer is None:
            return dict(snapshot.values)
        result = await graph.ainvoke(Command(resume=dict(answer)), config)
        final, _payload = await _drive(graph, config, result, policy)
        return final


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
    decision: Mapping[str, Any] | None = None,
    db_path: str | Path,
    respond: RespondPolicy | None = None,
) -> Mapping[str, Any]:
    """Resume a durable thread from a surface — the ONE place the resume tools are built.

    The tool mapping is built in-process from a bare ``CaseInput`` (``evals.tools.offline_tools``
    — no harness fixture and no declared terminal); the owned tools are called in-process, so no
    owned MCP server is launched and no model is needed, and the pre-gate nodes that would read
    the case are short-circuited by the checkpoint. The store is NOT resolved or injected here:
    the gated commit and its audit interceptor resolve it through the ONE existing seam
    (``mcp.server.resolve_store``), so there is exactly one store-resolution path.

    *decision* is the historical pre-built resume value; *respond* is the policy form the CLI
    and the desk use to answer whichever payload is pending. Both are forwarded to the ONE
    ``resume_paused``.
    """
    from triagedesk.evals.tools import offline_tools
    from triagedesk.evals.usage import UsageRecorder

    tools = offline_tools(CaseInput(), UsageRecorder())
    return await resume_paused(
        tools,
        thread_id=thread_id,
        decision=decision,
        db_path=db_path,
        respond=respond,
    )


__all__ = [
    "DurableError",
    "PausedRun",
    "RespondPolicy",
    "approval_decision",
    "derive_thread_id",
    "invoke_graph",
    "pending_interrupt",
    "resume_paused",
    "resume_thread",
    "run_to_gate",
]
