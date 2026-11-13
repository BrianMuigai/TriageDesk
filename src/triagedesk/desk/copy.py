"""The desk surface's ONE home for every user-facing string (UX copy). Imported by the render
modules and the HTTP layer; restated nowhere.
"""

from __future__ import annotations

# The UI-SPEC copy the bridge selects between (no clinical value, no SATS literal). The
# banner headline is verbatim from UX-01; the banner BODY varies with the trigger so the
# banner never asserts a fact its trigger did not establish (D10-09).
_BANNER_HEADLINE = "No discriminator matched / low confidence — nurse to confirm"
_BANNER_NO_MATCH_BODY = (
    "No discriminator matched this complaint, so this suggestion may be incomplete. "
    "Confirm before you act."
)
_BANNER_LOW_CONFIDENCE_BODY = (
    "Confidence is low for this suggestion, so it may be incomplete. Confirm before you act."
)
# A no-discriminator-applies delivery is NOT an uncertainty alarm: the vitals are the complete
# basis, so the note is quieter than the banner (COV-02). Showing the loud banner on every
# routine case would train alarm fatigue.
_BANNER_VITALS_ONLY_HEADLINE = "No discriminator applies — prioritised on the recorded vitals"
_BANNER_VITALS_ONLY_BODY = (
    "The complaint names no closed-set discriminator, so the suggested colour comes from the "
    "recorded vitals alone. Confirm before you act."
)
_EMPTY_HEADING = "No case yet"
_EMPTY_BODY = "Enter the patient's vitals and complaint, then choose Get suggested priority."
_CARD_FRAMING = "This is a suggestion, not a decision. You confirm the priority."
# The mode label the page always shows (Plan 13-02): which extraction path is live, and the
# one fact that never changes — the deterministic scorer decides the colour in both modes.
_MODE_OFFLINE = (
    "Offline mode: the desk uses the vitals you enter, and no model is called. "
    "The deterministic scorer decides the colour."
)
_MODE_ONLINE = (
    "Online mode: the local model reads the complaint text you type. "
    "The deterministic scorer still decides the colour."
)
_READ_ONLY_FRAMING = (
    "Not confirmed and not queued — this is what the system computed from the vitals alone."
)
_NO_EVIDENCE_LINE = "No evidence excerpt matched this complaint."
_DEFERRED_COPY = "This case was deferred for human review — no priority was committed."
# The bounded clarification terminal (COV-03): one question round, then defer. It states
# plainly that no priority was committed, because a question is not a decision.
_CLARIFICATION_COPY = (
    "One detail would resolve this case. Answer below and resubmit — no priority has been "
    "committed."
)
# The word the read-only card shows instead of a colour (nurse stress test S2-3).
_DEFERRED_BADGE = "DEFERRED"
_ESCALATED_COPY = "This case was escalated for human review — no priority was committed."
_RECOVERY_COPY = "A scored vital is missing. Re-measure before scoring."


def recovery_copy(missing: list[str] | tuple[str, ...]) -> str:
    """Name the missing scored vitals in the recovery panel (nurse stress test S2-2).

    The generic sentence is the fallback when the typed ``missing_vitals`` list is
    empty; otherwise the nurse is told exactly what to re-measure. Presentation only —
    the list comes from the graph's ``RecoveryRequest``, never re-derived here.
    """
    names = ", ".join(str(item) for item in missing)
    if not names:
        return _RECOVERY_COPY
    return f"A scored vital is missing ({names}). Re-measure before scoring."
_UNREACHED_COPY = "This case did not reach the approval gate — nothing has been committed."
_DISMISSED_COPY = "Dismissed — nothing has been committed."
_TIMEOUT_COPY = "No decision was made — nothing has been committed."
_FAILURE_COPY = (
    "The case could not be scored. Nothing has been committed. Try again, or check the desk log."
)
_SCHEMA_HINT = "Check the highlighted field and try again."
_NO_THREAD_COPY = "There is no paused case to decide. Submit the vitals first."

# The waiting room's own copy (Plan 13-03): its heading, the no-rows line, and the line the
# failure panel shows when the store read raises. Presentation only — no clinical value.
_WAITING_HEADING = "Waiting room"
_WAITING_EMPTY = "No patients are waiting. Approved cases appear here."
_WAITING_FAILED = (
    "The waiting room could not be read. Nothing has been changed. "
    "Try again, or check the desk log."
)
