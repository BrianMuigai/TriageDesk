"""The desk approval gate: render the named-human decision form and the edit colour set the
gate validates against (D10-18).
"""

from __future__ import annotations

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


def _gate_html(thread_id: str, csrf_token: str | None = None) -> str:
    """Render the approval gate, carrying the paused thread identity (D10-11/D10-18).

    The hidden ``thread_id`` value is the paused thread id — the ONE content-derived id the
    ``/decision`` POST returns to :func:`decide`. The hidden ``csrf_token`` is the per-server
    secret a cross-origin page cannot supply (WR-01). The three actions are labelled buttons
    (never colour-only controls); the edit control is a radio group built from
    :func:`editable_colours` with NO value preselected, so a missing choice is a rejected
    decision rather than a silent default. The gate-scoped timeout panel is inert until the
    inline client timer reveals it on expiry (D10-10); no decision is ever preselected.

    ``Your name``/``Your role`` carry a client-side ``required`` affordance so an approve/edit
    is refused before the round-trip when the identity is blank; the dismiss action carries
    ``formnovalidate`` so it stays available without an identity (dismiss commits nothing). The
    server still enforces non-blank (whitespace-only) identity through ``durable`` — the
    affordance is a cue, never the enforcement.
    """
    radios = "".join(
        '<label class="colour-choice">'
        f'<input type="radio" name="colour" value="{_escaped(colour)}">'
        f'<span class="colour-choice-name">{_escaped(colour)}</span></label>'
        for colour in editable_colours()
    )
    return (
        '<section class="approval-gate" aria-labelledby="gate-heading">'
        '<h2 id="gate-heading">Your decision</h2>'
        '<form id="approval-gate-form" method="post" action="/decision">'
        f"{_csrf_field(csrf_token)}"
        f'<input type="hidden" name="thread_id" value="{_escaped(thread_id)}">'
        '<div class="field"><label for="approver-name">Your name</label>'
        '<input id="approver-name" name="name" type="text" autocomplete="off" required></div>'
        '<div class="field"><label for="approver-role">Your role</label>'
        '<input id="approver-role" name="role" type="text" autocomplete="off" required></div>'
        '<fieldset class="field colour-fieldset"><legend>Choose the priority colour</legend>'
        f'<div class="colour-choices">{radios}</div></fieldset>'
        '<div class="gate-actions">'
        '<button type="submit" name="decision" value="approve" class="primary">'
        "Approve suggestion</button>"
        '<button type="submit" name="decision" value="edit">Edit colour</button>'
        '<button type="submit" name="decision" value="dismiss" formnovalidate>'
        "Dismiss (commit nothing)</button>"
        "</div></form></section>"
        f'<section id="gate-timeout" class="state-panel state-muted" hidden>'
        f"<p>{_escaped(_TIMEOUT_COPY)}</p></section>"
    )
