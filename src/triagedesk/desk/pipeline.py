"""The desk's thin graph-runner seam: build the offline tool map, run a case to the approval
gate, and resume it with a named decision (D10-11). Reuses the shipped plumbing and re-implements
none of it.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from triagedesk.core.schema import CaseInput
from triagedesk.durable import (
    PausedRun,
    approval_decision,
    resume_thread,
    run_to_gate,
)
from triagedesk.evals.tools import offline_tools
from triagedesk.evals.usage import UsageRecorder


def _tools_for(case: CaseInput) -> dict[str, Any]:
    """Build the offline in-process tool map for one desk submission (D10-15).

    The form already supplies a structured ``CaseInput``, so the surface is model-free: the
    offline mapping returns the case's own extraction while the matcher, scorer, retrieval,
    confidence and the gated commit all run for real. It needs no harness ``CaseSpec`` — the
    harness-free ``evals.tools.offline_tools`` builds the mapping from the ``CaseInput`` alone.
    """
    return offline_tools(case, UsageRecorder())


async def submit_case(case: CaseInput, db_path: str | Path) -> PausedRun:
    """Run one desk case to the approval gate over the shipped pause plumbing (D10-11).

    The content-derived thread id comes from the ONE plumbing (``durable.run_to_gate``); the
    bridge derives no second id and hashes nothing.
    """
    return await run_to_gate(
        _tools_for(case),
        raw_note=case.model_dump_json(),
        case=case,
        db_path=db_path,
    )


async def decide(
    thread_id: str, form: Mapping[str, str], db_path: str | Path
) -> Mapping[str, Any]:
    """Resume a paused thread with a named human decision (D10-11).

    The decision is built by the ONE ``durable.approval_decision`` — a whitespace-only name or
    role is rejected there — and resumed by the ONE ``durable.resume_thread``. The bridge
    re-implements no identity check and never calls the queue writer or the commit tool.
    ``thread_id`` is the value the handler read from the gate form's hidden ``thread_id``
    field (rendered from the interrupt payload's ``case_id`` — the ONE content-derived thread
    id).
    """
    decision = approval_decision(
        str(form.get("decision", "")),
        approver=form.get("name"),
        role=form.get("role"),
        colour=form.get("colour"),
    )
    return await resume_thread(thread_id=thread_id, decision=decision, db_path=db_path)
