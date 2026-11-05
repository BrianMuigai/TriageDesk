"""The desk's online-extraction proof suite (Plan 13-02, JC-1/JC-3).

Hermetic like ``test_desk.py``: the model is stubbed at the desk's ONE extraction seam
(``triagedesk.desk.extraction.extract_async``), the store is the shared in-memory double and
the checkpoint files live under ``tmp_path``. Nothing here reaches Ollama, the borrowed SQLite
subprocess or a repo-root artefact.

The safety claims under test: the nurse's form always wins the merge, the online path yields
the same colour and citations as the offline path, the closed-set filter has one home, and the
offline default calls no model at all.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from conftest import COMPLETE_CASE, async_return
from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.desk import extraction as extraction_module
from triagedesk.desk.extraction import extract_complaint, merge_case
from triagedesk.desk.pipeline import submit_case


def _extraction(case: CaseInput | None = None, ids: list[str] | None = None) -> ExtractionResult:
    """A fixed typed extraction, so no test depends on the model."""
    return ExtractionResult(
        case=case if case is not None else CaseInput(complaint="central chest pain"),
        matched_discriminator_ids=list(ids or []),
    )


def _first_discriminator_id() -> str:
    """A known-good id from the closed set, read through the one loader (D-08)."""
    return get_discriminators().discriminators[0].id


# ---------------------------------------------------- Task 1: the extraction seam


def test_online_and_offline_yield_the_same_colour_and_citations(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """For the same form case, the online path changes latency — never the priority (T-13-05).

    The stub extraction reports only fields the nurse left blank (``spo2``/``diastolic_bp``,
    captured but not scored), so the merged case differs from the form case in exactly the
    places the scorer does not read. The colour and every citation must still be identical.
    """
    offline = asyncio.run(submit_case(COMPLETE_CASE, tmp_path / "offline.db"))

    stub = _extraction(CaseInput(spo2=88, diastolic_bp=50, complaint="central chest pain"))
    monkeypatch.setattr(extraction_module, "extract_async", async_return(stub))
    extracted = asyncio.run(extract_complaint(COMPLETE_CASE.complaint))
    online = asyncio.run(submit_case(COMPLETE_CASE, tmp_path / "online.db", extraction=extracted))

    assert offline.payload is not None and online.payload is not None
    assert offline.payload["citations"]
    assert online.payload["colour"] == offline.payload["colour"]
    assert online.payload["citations"] == offline.payload["citations"]


def test_the_model_cannot_overwrite_a_nurse_value() -> None:
    """Every non-``None`` form field survives the merge — the nurse's vitals win (T-13-05)."""
    extracted = _extraction(CaseInput(respiratory_rate=60, heart_rate=200, complaint="model words"))

    merged = merge_case(COMPLETE_CASE, extracted)

    assert merged.case.respiratory_rate == COMPLETE_CASE.respiratory_rate == 24
    assert merged.case.heart_rate == COMPLETE_CASE.heart_rate == 118
    assert merged.case.complaint == COMPLETE_CASE.complaint
    form_values = COMPLETE_CASE.model_dump()
    merged_values = merged.case.model_dump()
    for name, value in form_values.items():
        if value is not None:
            assert merged_values[name] == value, name


def test_extract_complaint_filters_to_the_closed_set(monkeypatch: Any) -> None:
    """The one closed-set filter drops unknown ids and sets the coverage signal (T-02-11)."""
    valid = _first_discriminator_id()
    unknown = "not_a_declared_discriminator"
    monkeypatch.setattr(
        extraction_module,
        "extract_async",
        async_return(_extraction(ids=[valid, unknown])),
    )
    filtered = asyncio.run(extract_complaint("central chest pain"))
    assert filtered.matched_discriminator_ids == [valid]
    assert filtered.no_discriminator_matched is False

    monkeypatch.setattr(
        extraction_module,
        "extract_async",
        async_return(_extraction(ids=[unknown, "also_unknown"])),
    )
    none_survived = asyncio.run(extract_complaint("central chest pain"))
    assert none_survived.matched_discriminator_ids == []
    assert none_survived.no_discriminator_matched is True


def test_offline_submit_calls_no_model(tmp_path: Path, monkeypatch: Any) -> None:
    """The default desk path never touches the model, even when the seam would raise."""

    async def exploding(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the offline path called the model")

    monkeypatch.setattr(extraction_module, "extract_async", exploding)

    paused = asyncio.run(submit_case(COMPLETE_CASE, tmp_path / "offline.db"))

    assert paused.paused and paused.payload is not None
    assert paused.payload["colour"]
    assert paused.payload["citations"]
