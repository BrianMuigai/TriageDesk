"""The ONE approval-token → committed-colour rule (D-05, CONVENTIONS §1).

The gate commits the clinician's ``final_colour`` for an ``edit`` decision and the scored
colour for an ``approve``. That rule has exactly one home here so the shipped gate
(``mcp/server.py``) and every stand-in for it (the graph fake in the test suite) cannot
drift apart (SOLID: L) and the rule is never restated.

Pure module: no I/O, and it imports only the shared schema (D-13). ``final_colour`` is the
one place an ``edit`` records the colour the clinician chose (``ApprovalToken`` docstring),
so the committed colour is always the approved colour and never a re-derived one (D-05).
"""

from __future__ import annotations

from triagedesk.core.schema import ApprovalToken


def committed_colour(token: ApprovalToken, scored_colour: str) -> str:
    """Return the colour a validated approval token commits (D-05).

    An ``edit`` commits the clinician's ``final_colour``; an ``approve`` commits the
    ``scored_colour`` the clinician approved. A ``dismiss`` never reaches this function —
    the gate refuses it before any store access — so its empty ``final_colour`` is never
    read.
    """
    return token.final_colour if token.decision == "edit" else scored_colour
