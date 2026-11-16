"""The desk approval gate: render the named-human decision form and the edit colour set the
gate validates against (D10-18).
"""

from __future__ import annotations

from collections.abc import Mapping

from triagedesk.core.rules import get_tews
from triagedesk.desk.copy import _TIMEOUT_COPY
from triagedesk.desk.forms import _csrf_field
from triagedesk.desk.markup import _escaped


def editable_colours() -> list[str]:
    """The gate's own accepted colour set, in a stable order (D10-18).

    Derived from ``{band.colour for band in get_tews().tews_to_colour}`` — the SAME expression
    ``ApprovalToken`` validates ``final_colour`` against — so the surface can never offer a
    decision the gate would refuse. Never a hard-coded list; never a colour that exists only
    in ``target_times``.
    """
    return sorted({band.colour for band in get_tews().tews_to_colour})


def _gate_html(
    thread_id: str,
    csrf_token: str | None = None,
    case_values: Mapping[str, str] | None = None,
) -> str:
    """Render the approval gate, carrying the paused thread identity (D10-11/D10-18).

    The hidden ``thread_id`` value is the paused thread id — the ONE content-derived id the
    ``/decision`` POST returns to :func:`decide`. The hidden ``csrf_token`` is the per-server
    secret a cross-origin page cannot supply (WR-01). ``case_values`` are the paused case's
    form values, carried as hidden fields so the decision page repopulates the structured
    intake instead of appearing to discard it; they are presentation data only and are never
    read by :func:`decide`.
    """
    radios = "".join(
        '<label class="colour-choice">'
        f'<input type="radio" name="colour" value="{_escaped(colour)}">'
        f'<span class="colour-choice-name">{_escaped(colour)}</span></label>'
        for colour in editable_colours()
    )
    carried = "".join(
        f'<input type="hidden" name="{_escaped(name)}" value="{_escaped(value)}">'
        for name, value in (case_values or {}).items()
    )
    return (
        '<section class="approval-gate" aria-labelledby="gate-heading">'
        '<h2 id="gate-heading">Your decision</h2>'
        '<p class="framing">Approve the suggestion, dismiss it, or open Edit colour to '
        "record a different priority. Nothing is queued until you decide.</p>"
        '<form id="approval-gate-form" method="post" action="/decision">'
        f"{_csrf_field(csrf_token)}"
        f'<input type="hidden" name="thread_id" value="{_escaped(thread_id)}">'
        f"{carried}"
        '<div class="field"><label for="approver-name">Your name</label>'
        '<input id="approver-name" name="name" type="text" autocomplete="off" '
        "required autofocus></div>"
        '<div class="field"><label for="approver-role">Your role</label>'
        '<input id="approver-role" name="role" type="text" autocomplete="off" '
        "required></div>"
        '<div class="gate-actions">'
        '<button type="submit" name="decision" value="approve" class="primary">'
        "Approve suggestion</button>"
        '<button type="submit" name="decision" value="dismiss" formnovalidate>'
        "Dismiss (commit nothing)</button>"
        "</div>"
        '<details class="colour-edit">'
        "<summary>Edit colour</summary>"
        '<fieldset class="field colour-fieldset"><legend>New priority colour</legend>'
        f'<div class="colour-choices">{radios}</div></fieldset>'
        '<button type="submit" name="decision" value="edit">'
        "Commit edited colour</button>"
        "</details>"
        "</form></section>"
        f'<section id="gate-timeout" class="state-panel state-muted" hidden>'
        f"<p>{_escaped(_TIMEOUT_COPY)}</p></section>"
    )
