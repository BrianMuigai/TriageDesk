"""The desk's ONE online-extraction seam (Plan 13-02, JC-1/JC-3).

The desk's default mode is offline: the form already carries a structured ``CaseInput``, so
the graph is handed the nurse's own case and no model is called. ``triagedesk desk --online``
opts into the REAL local extraction: the free-text complaint the form already posts is
structured by the one model wrapper, and the result feeds the graph's ``normalize`` node.

This module owns that seam and nothing else. It never computes a number, never produces a
``PriorityResult``, never touches a store and never calls the audited owned tool — so a
precompute cannot append an audit record or race the chain-head writer (T-13-08). The colour
and every citation still come from the deterministic scorer.

The nurse's typed values are authoritative: :func:`merge_case` overlays every non-``None``
form field on the extracted case, so a model value can never overwrite a value the nurse
entered (T-13-05). A blank field stays as the extraction reported it only when the note
itself stated it — the grounding step in ``llm.client`` already dropped unstated values.
"""

from __future__ import annotations

from triagedesk.core import matcher
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.llm.client import extract_async


async def extract_complaint(complaint: str) -> ExtractionResult:
    """Structure *complaint* through the real model and constrain it to the closed set.

    The call goes through the Plan-13-01 async path (``llm.client.extract_async``), so a
    slow model no longer pins the loop; the result is filtered by the ONE closed-set filter
    (``core.matcher.filter_discriminator_ids``), so the model may not choose an id outside
    the declared set. It never computes a number and never touches a store — the extraction
    is an input to the graph, not a priority.
    """
    result = await extract_async(complaint)
    return matcher.filter_discriminator_ids(result)


def merge_case(form: CaseInput, extracted: ExtractionResult) -> ExtractionResult:
    """Overlay the nurse's form on the extracted case — the form always wins (T-13-05).

    Every non-``None`` field of *form* replaces the extracted value, so the case that reaches
    the deterministic scorer is the nurse's case. A field the nurse left blank keeps what the
    extraction reported only when the note stated it (grounding already enforced upstream).
    """
    typed = {name: value for name, value in form.model_dump().items() if value is not None}
    return extracted.model_copy(update={"case": extracted.case.model_copy(update=typed)})
