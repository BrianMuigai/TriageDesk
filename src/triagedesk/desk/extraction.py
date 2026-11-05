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

import asyncio

from triagedesk.core import matcher
from triagedesk.core.hashing import hash_value
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.llm.client import extract_async

# The hard bound on precomputed complaints held at once (T-13-07). A nurse works one patient
# at a time, so this is generous; beyond it the oldest inserted entry is cancelled and dropped.
_MAX_ENTRIES = 32


def complaint_key(complaint: str) -> str:
    """The ONE cache key for a complaint — a hash through the ONE hashing helper (D-17).

    Derived from the complaint text alone, so the precompute route and the submit path (which
    both see the same posted text) always agree on the key. Never ``hash()`` (randomised per
    process) and never a second digest scheme.
    """
    return hash_value({"complaint": complaint})


class PrecomputeCache:
    """Background extractions keyed by :func:`complaint_key` — the ONE precompute store.

    Every method is called ON the desk loop (from ``DeskServer.loop.run``), so the dict needs
    no lock: one thread runs every coroutine that touches it. The cache holds the *precompute*
    only — the submit path re-derives the key from the same complaint text, reuses a hit, and
    falls back to one in-path :func:`extract_complaint` on a miss or a failure (T-13-07).

    ``start`` never awaits the model, so the request that triggered it returns immediately;
    ``take`` is the only place a result (or a failure) is observed. At most one task exists per
    complaint key, and the mapping is bounded to :data:`_MAX_ENTRIES` with FIFO eviction.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[ExtractionResult]] = {}

    async def start(self, complaint: str) -> None:
        """Start one background extraction for *complaint* (no-op when blank or already keyed)."""
        if not complaint.strip():
            return
        key = complaint_key(complaint)
        if key in self._tasks:
            return
        self._tasks[key] = asyncio.ensure_future(extract_complaint(complaint))
        while len(self._tasks) > _MAX_ENTRIES:
            oldest_key = next(iter(self._tasks))
            self._tasks.pop(oldest_key).cancel()

    async def take(self, complaint: str) -> ExtractionResult | None:
        """Pop and await the precomputed extraction for *complaint*, or ``None`` to degrade.

        A miss (never started, or already taken) and a failed extraction both return ``None``,
        so the caller runs the normal path instead of inheriting an error. Cancellation is a
        teardown signal, not a failure, so it is re-raised rather than swallowed.
        """
        task = self._tasks.pop(complaint_key(complaint), None)
        if task is None:
            return None
        try:
            return await task
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — a failed precompute degrades to the normal path
            return None

    def __len__(self) -> int:
        """The number of held precomputes (pending or finished), for the bound proof."""
        return len(self._tasks)


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
