"""Evidence-grounding tests at the owned tool boundary (D-05, D-06, SAFE-01).

Every sign an extraction claims is checked against the note it came from: a
discriminator id survives only when a declared alias is an unnegated phrase of the
note, and a numeric vital survives only when the note states it. Grounding can only
remove evidence — never add it.

Expectations are derived from the loaded data — no alias or id is restated here
(CONVENTIONS §1).
"""

from __future__ import annotations

from mcp import Client

from conftest import async_return
from triagedesk.core import grounding, matcher
from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.mcp import server as server_module


def _declared(index: int) -> str:
    """A declared discriminator id, read through the one loader (CONVENTIONS §1)."""
    return get_discriminators().discriminators[index].id


def _first_alias(discriminator_id: str) -> str:
    """The first declared alias of *discriminator_id* — never a literal."""
    for discriminator in get_discriminators().discriminators:
        if discriminator.id == discriminator_id:
            return discriminator.aliases[0]
    raise AssertionError(f"{discriminator_id!r} is not a declared discriminator")


async def test_normalize_case_keeps_only_the_evidenced_id(monkeypatch) -> None:
    """A declared id whose alias is absent from the note does not survive."""
    evidenced = _declared(0)
    unevidenced = _declared(1)
    note = f"{_first_alias(evidenced)}. RR 24"
    extraction = ExtractionResult(
        case=CaseInput(respiratory_rate=24),
        matched_discriminator_ids=[evidenced, unevidenced],
    )
    monkeypatch.setattr(server_module, "extract_async", async_return(extraction))

    async with Client(server_module.server) as client:
        call = await client.call_tool("normalize_case", {"raw_note": note})

    assert not call.is_error, f"owned tool errored: {call}"
    parsed = ExtractionResult.model_validate_json(call.content[0].text)
    assert parsed.matched_discriminator_ids == [evidenced]
    assert parsed.no_discriminator_matched is False


async def test_normalize_case_drops_an_unevidenced_declared_id(monkeypatch) -> None:
    """A declared id the note never mentions is dropped and sets the coverage signal."""
    unevidenced = _declared(1)
    extraction = ExtractionResult(
        case=CaseInput(respiratory_rate=24),
        matched_discriminator_ids=[unevidenced],
    )
    monkeypatch.setattr(server_module, "extract_async", async_return(extraction))

    async with Client(server_module.server) as client:
        call = await client.call_tool("normalize_case", {"raw_note": "RR 24"})

    parsed = ExtractionResult.model_validate_json(call.content[0].text)
    assert parsed.matched_discriminator_ids == []
    assert parsed.no_discriminator_matched is True


def test_grounded_ids_are_a_subset_of_the_closed_set_filter() -> None:
    """Grounding is removal-only: it never adds an id the filter did not admit."""
    evidenced = _declared(0)
    note = f"{_first_alias(evidenced)}. RR 24"
    extraction = ExtractionResult(
        case=CaseInput(respiratory_rate=24),
        matched_discriminator_ids=[evidenced, _declared(1), "not_a_declared_discriminator"],
    )

    filtered = matcher.filter_discriminator_ids(extraction)
    grounded = grounding.ground_extraction(extraction, note)

    assert set(grounded.matched_discriminator_ids) <= set(filtered.matched_discriminator_ids)
    assert grounded.matched_discriminator_ids == [evidenced]
