"""The ONE waiting-room projection: order committed rows by acuity, then age, then position.

This module is a pure READ projection (Plan 13-03, JC-3). It calls exactly
``Store.read_queue_rows`` and nothing else — it never reaches ``upsert_queue_row``,
``next_position`` or any audit writer — so the waiting room cannot mutate a queue row and
cannot reach the commit path. The order is presentation only: the stored ``position`` and
the idempotency key are untouched, so no approval, edit or retry changes identity.

Every rendered colour is a committed row's own value, shown as a swatch AND as text through
the ONE ``card._colour_class`` mapping; no colour is computed here. The urgency rank is the
ONE data-derived order in :func:`core.rules.colour_urgency` (CONVENTIONS §1).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from triagedesk.core.rules import colour_urgency
from triagedesk.desk.card import _colour_class
from triagedesk.desk.copy import _WAITING_EMPTY, _WAITING_HEADING
from triagedesk.desk.markup import _escaped
from triagedesk.store import QueueRow, Store, default_store

# The table's column headings (presentation only, no clinical value).
_WAITING_COLUMNS: tuple[str, ...] = ("Position", "Priority", "Waiting", "Target")


def _as_utc(value: datetime) -> datetime:
    """Return *value* as an aware UTC datetime, treating a naive value as UTC.

    The store may hand back a naive ``created_at`` (an older file, a bare SQLite text
    column), so normalising here keeps the sort and the wait arithmetic total: a naive row
    can never raise ``TypeError`` against an aware one.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _epoch(value: datetime) -> float:
    """The POSIX timestamp of *value*, with a naive datetime treated as UTC."""
    return _as_utc(value).timestamp()


def order_rows(rows: Sequence[QueueRow]) -> list[QueueRow]:
    """Order *rows* by acuity (most urgent first), then ``created_at``, then ``position``.

    The rank comes from the substrate (``core.rules.colour_urgency``), so the order is
    derived from ``data/sats_tews.yaml`` rather than a colour literal. A colour the
    substrate does not band (the declared-but-unreachable ``BLUE``) sorts last rather than
    raising. ``position`` stays the stable identity and is the final, total tie-break.
    """
    urgency = colour_urgency()
    return sorted(
        rows,
        key=lambda row: (
            -urgency.get(row.colour, -1.0),
            _epoch(row.created_at),
            row.position,
        ),
    )


def wait_minutes(created_at: datetime, now: datetime) -> int:
    """Whole minutes waited since *created_at*, never negative (naive is treated as UTC)."""
    elapsed = _as_utc(now) - _as_utc(created_at)
    return max(0, int(elapsed // timedelta(minutes=1)))


def _row_html(row: QueueRow, now: datetime) -> str:
    """One waiting-room row: position, labelled colour swatch, wait timer, target."""
    return (
        "<tr>"
        f'<td class="waiting-position">{_escaped(row.position)}</td>'
        f'<td><span class="colour-block {_escaped(_colour_class(row.colour))}">'
        f'<span class="colour-name">{_escaped(row.colour)}</span></span></td>'
        f'<td><time datetime="{_escaped(row.created_at.isoformat())}">'
        f"Waiting {_escaped(wait_minutes(row.created_at, now))} min</time></td>"
        f"<td>{_escaped(row.target or '')}</td>"
        "</tr>"
    )


def waiting_html(
    rows: Sequence[QueueRow], *, now: datetime | None = None, error: str | None = None
) -> str:
    """Render the waiting-room panel, or the failure panel when *error* is given.

    A failure renders a panel and NOTHING else — never a partial table — so a store error
    is visible without ever showing an incomplete queue. Otherwise the rows are ordered by
    :func:`order_rows` and each renders its committed colour (swatch plus name) and its
    wait timer; no rows renders the empty copy.
    """
    if error is not None:
        return (
            '<section class="state-panel state-error" role="status">'
            f"<p>{_escaped(error)}</p></section>"
        )
    ordered = order_rows(rows)
    moment = now if now is not None else datetime.now(UTC)
    if not ordered:
        body = f'<p class="waiting-empty">{_escaped(_WAITING_EMPTY)}</p>'
    else:
        headers = "".join(
            f'<th scope="col">{_escaped(column)}</th>' for column in _WAITING_COLUMNS
        )
        body = (
            '<table class="waiting-table">'
            f'<caption class="waiting-caption">{_escaped(_WAITING_HEADING)}</caption>'
            f"<thead><tr>{headers}</tr></thead><tbody>"
            f"{''.join(_row_html(row, moment) for row in ordered)}"
            "</tbody></table>"
        )
    return (
        '<section class="waiting-room" aria-labelledby="waiting-heading">'
        f'<h2 id="waiting-heading">{_escaped(_WAITING_HEADING)}</h2>'
        f"{body}</section>"
    )


async def read_rows(store: Store | None = None) -> list[QueueRow]:
    """Return the committed queue rows — the ONLY store call the waiting room makes.

    The injected *store* is the desk's test seam; when it is ``None`` the ONE store factory
    (``store.default_store``) resolves the borrowed store on demand.
    """
    resolved = store if store is not None else await default_store()
    return await resolved.read_queue_rows()


__all__ = ["order_rows", "read_rows", "wait_minutes", "waiting_html"]
