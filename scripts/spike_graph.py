"""End-to-end tracer spike: raw note -> sourced priority -> gate interrupt -> refusal.

Verification for Plan 03-01 task 1. Runs the phase's thin path ONCE against the
real local open-weights model and exits non-zero on any failure:

    ingest      -> the raw note is seeded
    normalize   -> the owned ``normalize_case`` tool structures it (LOCAL model only)
    retrieve    -> the deterministic matcher resolves the discriminator set
    score       -> the pure scorer produces a cited colour (no model)
    verify      -> the citation invariant holds
    approval_gate -> ``interrupt()`` pauses for a named clinician (NO side effect)

Then it resumes with a ``dismiss`` decision that names NO approver and asserts the
commit is refused and nothing reaches the queue — the phase's headline (GATE-02,
D-05).

Usage:
    uv run python scripts/spike_graph.py
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from triagedesk.graph.build import build_graph, load_graph_tools

# A fixed synthetic note with complete adult vitals and a discriminated complaint.
# The model only structures it; it never scores it (D-02).
NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, "
    "temperature 38.9, no trauma. Presenting with central chest pain."
)
CASE_ID = "spike-case-1"


def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Return the interrupt's evidence payload, or fail loudly."""
    interrupts = result.get("__interrupt__")
    if not interrupts:
        raise AssertionError(f"graph did not pause at the gate: {result}")
    return dict(interrupts[0].value)


async def main() -> int:
    tools = await load_graph_tools()
    names = sorted(tools)
    print(f"[tools] owned tools: {names}")
    for required in ("normalize_case", "match_discriminators", "score_priority", "commit_priority"):
        if required not in tools:
            raise AssertionError(f"owned server missing required tool {required!r}: {names}")

    config = {"configurable": {"thread_id": CASE_ID}}
    app = build_graph(tools, checkpointer=InMemorySaver())

    # 1. First pass: run to the interrupt.
    result = await app.ainvoke({"raw_note": NOTE}, config)

    payload = _interrupt_payload(result)
    print(f"[gate] paused; payload case_id={payload['case_id']} colour={payload['colour']}")
    if not payload["citations"]:
        raise AssertionError("the paused priority carries no citations (not sourced)")
    if payload["colour"] is None:
        raise AssertionError("the paused priority has no colour")
    # Nothing was written before the interrupt: no commit result exists yet.
    if result.get("commit_result") is not None:
        raise AssertionError("a commit occurred BEFORE the interrupt (D-04 violated)")
    n_citations = len(payload["citations"])
    print(f"[gate] sourced priority: colour={payload['colour']} citations={n_citations}")

    # 2. Resume with a dismiss that names no approver: the commit must be refused.
    resumed = await app.ainvoke(Command(resume={"decision": "dismiss"}), config)

    commit = resumed.get("commit_result")
    if commit is None:
        raise AssertionError("no commit result after resume")
    if not commit.refused or commit.committed:
        raise AssertionError(f"an unapproved resume was NOT refused: {commit}")
    print(f"[commit] refused as expected: {commit.reason}")

    handover = resumed.get("handover")
    if handover is None:
        raise AssertionError("handover card was not rendered")
    if not handover.citations or handover.colour is None:
        raise AssertionError("handover is missing the sourced priority fields")
    if handover.decision != "dismiss":
        raise AssertionError(f"handover did not record the decision: {handover.decision}")
    print(
        f"[handover] case={handover.case_id} colour={handover.colour} "
        f"target={handover.target} citations={len(handover.citations)} "
        f"decision={handover.decision} approved_by={handover.approved_by!r}"
    )

    print("[ok] raw note -> sourced priority -> gate pause -> refusal on unapproved resume")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
