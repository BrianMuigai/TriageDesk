"""The waiting-room projection proofs (Plan 13-03, JC-3).

Proves the ONE read projection: rows order by acuity (data-derived), then ``created_at``,
then the stable ``position``; every row renders its committed colour as a swatch AND as
text plus a wait timer; the projection makes exactly one read and contains no write call;
and an in-place edit keeps its position while moving in the rendered order.
"""

from __future__ import annotations

import ast
import asyncio
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import COMPLETE_CASE, RecordingStore
from triagedesk.core import scorer
from triagedesk.core.rules import colour_urgency, get_tews
from triagedesk.desk.copy import _WAITING_EMPTY
from triagedesk.desk.waiting import order_rows, read_rows, wait_minutes, waiting_html
from triagedesk.store import QueueRow
from triagedesk.store.queue import commit_to_queue

WAITING_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "triagedesk" / "desk" / "waiting.py"
)

# The write methods the projection must never call (T-13-10).
_WRITE_CALLS = frozenset(
    {
        "upsert_queue_row",
        "next_position",
        "commit_to_queue",
        "append_audit_record",
        "write_chain_head",
    }
)


def _band_colours() -> list[str]:
    """Every substrate colour, least urgent first — never a colour literal."""
    bands = sorted(get_tews().tews_to_colour, key=lambda band: band.min)
    return [band.colour for band in bands]


def _row(
    colour: str,
    position: int,
    created_at: datetime,
    case_id: str = "case",
    target: str = "< 1 hour",
) -> QueueRow:
    """One committed queue row for the projection (the store read returns this shape)."""
    return QueueRow(
        case_id=case_id,
        content_hash=f"hash-{position}",
        colour=colour,
        target=target,
        position=position,
        created_at=created_at,
    )


def test_order_is_acuity_then_age_then_position() -> None:
    """Acuity first, then the older wait, then the stable position; unbanded last."""
    colours = _band_colours()
    least, most = colours[0], colours[-1]
    day1 = datetime(2026, 1, 1, tzinfo=UTC)
    day2 = datetime(2026, 1, 2, tzinfo=UTC)
    rows = [
        _row(most, 5, day1, "most"),
        _row(least, 9, day1, "least-late-position"),
        _row(least, 2, day2, "least-newer"),
        _row(least, 4, day1, "least-early-position"),
        _row("BLUE", 1, day1, "unbanded"),
    ]

    ordered = order_rows(rows)

    assert [row.case_id for row in ordered] == [
        "most",
        "least-early-position",
        "least-late-position",
        "least-newer",
        "unbanded",
    ]


def test_colour_urgency_is_data_derived() -> None:
    """The rank equals the substrate's own band mins, and the scorer delegates to it."""
    expected = {
        band.colour: float(band.min) for band in get_tews().tews_to_colour
    }
    assert colour_urgency(get_tews()) == expected
    assert scorer._colour_urgency(get_tews()) == expected


def test_wait_minutes_is_never_negative_and_handles_naive() -> None:
    """A future timestamp yields 0, and a naive ``created_at`` cannot raise."""
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert wait_minutes(datetime(2026, 1, 1, 13, 0, tzinfo=UTC), now) == 0
    assert wait_minutes(datetime(2026, 1, 1, 11, 30), now) == 30
    assert wait_minutes(datetime(2026, 1, 1, 11, 59, 30, tzinfo=UTC), now) == 0


def test_waiting_html_orders_renders_and_labels_every_colour() -> None:
    """Rows render in ``order_rows`` order, each with a labelled swatch and a wait timer."""
    colours = _band_colours()
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    rows = [
        _row(colours[-1], 2, now - timedelta(minutes=10), "urgent"),
        _row(colours[0], 1, now - timedelta(minutes=5), "routine"),
    ]

    body = waiting_html(rows, now=now)

    positions = [
        int(value)
        for value in re.findall(r'class="waiting-position">(\d+)<', body)
    ]
    assert positions == [row.position for row in order_rows(rows)]
    for colour in {row.colour for row in rows}:
        assert f"colour-{colour.lower()}" in body
        assert f'<span class="colour-name">{colour}</span>' in body
    assert '<time datetime=' in body
    assert "Waiting 10 min" in body


def test_waiting_html_escapes_every_value() -> None:
    """A hostile target (or case id) cannot inject markup into the panel."""
    hostile = "<script>alert(1)</script>"
    rows = [_row(_band_colours()[0], 1, datetime.now(UTC), case_id=hostile, target=hostile)]

    body = waiting_html(rows)

    assert hostile not in body
    assert "&lt;script&gt;" in body


def test_waiting_html_empty_and_error_states() -> None:
    """No rows renders the empty copy; an error renders a panel and no table."""
    empty = waiting_html([])
    assert _WAITING_EMPTY in empty
    assert "waiting-table" not in empty

    failed = waiting_html([], error="the store is unavailable")
    assert "state-panel state-error" in failed
    assert "the store is unavailable" in failed
    assert "waiting-table" not in failed
    assert "waiting-room" not in failed


def test_read_rows_makes_exactly_one_read() -> None:
    """The projection's only store call is one ``read_queue_rows`` (no write)."""
    store = RecordingStore()

    rows = asyncio.run(read_rows(store))

    assert rows == []
    assert store.calls == [("read_queue_rows", ())]


def test_waiting_module_has_no_write_call() -> None:
    """AST guard: the waiting room module calls no write method (a non-vacuous proof)."""
    tree = ast.parse(WAITING_PATH.read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called.isdisjoint(_WRITE_CALLS), sorted(called & _WRITE_CALLS)
    assert "read_queue_rows" in called, "the guard is vacuous: the read call is missing"


def test_edit_keeps_position_and_the_row_moves_in_order() -> None:
    """An in-place edit keeps position/created_at and reorders by the new acuity."""
    colours = _band_colours()
    least, most = colours[0], colours[-1]
    edited_case = COMPLETE_CASE.model_copy(update={"complaint": "headache"})

    async def scenario() -> tuple[QueueRow, QueueRow, QueueRow, list[QueueRow]]:
        store = RecordingStore()
        first, created = await commit_to_queue(
            store, case_id="first", colour=least, content=COMPLETE_CASE
        )
        assert created
        second, created = await commit_to_queue(
            store, case_id="second", colour=least, content=edited_case
        )
        assert created
        edited, created_again = await commit_to_queue(
            store, case_id="second", colour=most, content=edited_case
        )
        assert created_again is False
        return first, second, edited, order_rows(await read_rows(store))

    first, second, edited, ordered = asyncio.run(scenario())

    assert edited.position == second.position
    assert edited.created_at == second.created_at
    assert ordered[0].case_id == "second"
    assert ordered[0].position == second.position
    assert ordered[-1].position == first.position
