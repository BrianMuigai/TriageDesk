"""The ONE approval-token → committed-field rule (D-05, CONVENTIONS §1).

The gate commits the clinician's ``final_colour`` for an ``edit`` decision and the scored
colour for an ``approve``. That rule has exactly one home here so the shipped gate
(``mcp/server.py``) and every stand-in for it (the graph fake in the test suite) cannot
drift apart (SOLID: L) and the rule is never restated.

``committed_or_scored`` is likewise the ONE home for "the committed field wins": the
handover card asks it for the colour and target it should show, so the fallback rule is
never restated at a render site.

Pure module: no I/O of its own (the SATS substrate is read through the cached
``core.rules`` loader, never inline), and it imports only ``core.rules`` and the shared
schema (D-13). ``final_colour`` is the one place an ``edit`` records the colour the
clinician chose (``ApprovalToken`` docstring), so the committed colour is always the
approved colour and never a re-derived one (D-05).
"""

from __future__ import annotations

from triagedesk.core.rules import get_tews
from triagedesk.core.schema import ApprovalToken, CommitResult, PriorityResult


def committed_colour(token: ApprovalToken, scored_colour: str) -> str:
    """Return the colour a validated approval token commits (D-05).

    An ``edit`` commits the clinician's ``final_colour``; an ``approve`` commits the
    ``scored_colour`` the clinician approved. A ``dismiss`` never reaches this function —
    the gate refuses it before any store access — so its empty ``final_colour`` is never
    read.
    """
    return token.final_colour if token.decision == "edit" else scored_colour


def target_for_colour(colour: str) -> str | None:
    """Return the target time the SATS substrate declares for *colour* (D-08).

    The target is a pure lookup of the committed colour in ``data/sats_tews.yaml`` — the
    same table the scorer uses — so there is no literal target time and no second table.
    An undeclared colour degrades to ``None`` rather than raising: the row still records
    the colour and simply has no target (T-14-05). ``ApprovalToken`` already rejects an
    undeclared edit colour, so this is defence in depth, not the primary guard.
    """
    entry = get_tews().target_times.get(colour)
    return entry.target if entry is not None else None


def committed_or_scored(
    commit_result: CommitResult | None, priority: PriorityResult
) -> tuple[str | None, str | None]:
    """Return the ``(colour, target)`` a reader should present for one patient.

    This is the ONE home for "the committed field wins". When a commit happened, the
    committed colour and target are returned, each falling back to the scored value when
    that committed field is ``None``; otherwise (a dismissal, a refusal, or no commit at
    all) both scored values are returned.
    """
    if commit_result is not None and commit_result.committed:
        return (
            commit_result.colour or priority.colour,
            commit_result.target or priority.target,
        )
    return priority.colour, priority.target
