"""The desk's thin graph-runner seam: build the offline tool map, run a case to the approval
gate, and resume it with a named decision (D10-11). Reuses the shipped plumbing and re-implements
none of it.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.desk.clarification import answers_from_form
from triagedesk.desk.extraction import merge_case
from triagedesk.durable import (
    PausedRun,
    approval_decision,
    resume_thread,
    run_to_gate,
)
from triagedesk.evals.tools import offline_tools, online_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.mcp.elicitation import (
    CLARIFICATION_REQUEST_KEY,
    accept_responses,
    decline_responses,
)


def _tools_for(case: CaseInput, extraction: ExtractionResult | None = None) -> dict[str, Any]:
    """Build the in-process tool map for one desk submission (D10-15, Plan 13-02).

    The form already supplies a structured ``CaseInput``, so the default surface is
    model-free: the offline mapping returns the case's own extraction while the matcher,
    scorer, retrieval, confidence and the gated commit all run for real. When *extraction*
    is supplied (the online mode), the same mapping is built with that already-merged
    extraction returned by ``normalize_case`` — one seam, no second code path, and the six
    other tools are identical (SOLID: L).
    """
    recorder = UsageRecorder()
    if extraction is not None:
        return online_tools(case, extraction, recorder)
    return offline_tools(case, recorder)


async def submit_case(
    case: CaseInput,
    db_path: str | Path,
    *,
    extraction: ExtractionResult | None = None,
    clarification_round: int = 0,
) -> PausedRun:
    """Run one desk case to the approval gate over the shipped pause plumbing (D10-11).

    The content-derived thread id comes from the ONE plumbing (``durable.run_to_gate``); the
    bridge derives no second id and hashes nothing. ``raw_note`` stays the form case's JSON in
    both modes, so the thread id is the same offline and online. When *extraction* is given,
    the nurse's form is merged over it before the tool map is built, so the model can change
    latency but never a vital (T-13-05).
    """
    merged = merge_case(case, extraction) if extraction is not None else None
    return await run_to_gate(
        _tools_for(case, merged),
        raw_note=case.model_dump_json(),
        case=case,
        db_path=db_path,
        clarification_round=clarification_round,
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


async def answer_clarification(
    thread_id: str, form: Mapping[str, str], db_path: str | Path
) -> Mapping[str, Any]:
    """Resume a paused **question** with the nurse's answers — never a decision (ELICIT-05/08).

    The resume value is built by the ONE wire module (``mcp.elicitation``): an ``accept``
    carries the posted answers keyed by their question field, and anything else — a decline,
    a missing action, an unknown action — declines. A decline is the honest default because a
    refusal is never converted into a value.

    The run is resumed with that value and a policy that returns ``None``: whatever comes next
    (the approval gate) is left PAUSED for the handler to render, so answering a question can
    never approve a priority. The bridge re-implements no identity check, no scoring and no
    queue write.
    """
    request_key = str(form.get("request_key") or CLARIFICATION_REQUEST_KEY)
    if str(form.get("action") or "").strip() == "accept":
        resume = accept_responses(request_key, answers_from_form(form))
    else:
        resume = decline_responses(request_key)
    return await resume_thread(
        thread_id=thread_id,
        decision=resume,
        db_path=db_path,
        respond=lambda _payload: None,
    )
