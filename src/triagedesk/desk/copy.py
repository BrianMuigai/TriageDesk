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
_EMPTY_HEADING = "No case yet"
_EMPTY_BODY = "Enter the patient's vitals and complaint, then choose Get suggested priority."
_CARD_FRAMING = "This is a suggestion, not a decision. You confirm the priority."
_READ_ONLY_FRAMING = (
    "Not confirmed and not queued — this is what the system computed from the vitals alone."
)
_NO_EVIDENCE_LINE = "No evidence excerpt matched this complaint."
_DEFERRED_COPY = "This case was deferred for human review — no priority was committed."
_ESCALATED_COPY = "This case was escalated for human review — no priority was committed."
_RECOVERY_COPY = "A scored vital is missing. Re-measure before scoring."
_UNREACHED_COPY = "This case did not reach the approval gate — nothing has been committed."
_DISMISSED_COPY = "Dismissed — nothing has been committed."
_TIMEOUT_COPY = "No decision was made — nothing has been committed."
_FAILURE_COPY = (
    "The case could not be scored. Nothing has been committed. Try again, or check the desk log."
)
_SCHEMA_HINT = "Check the highlighted field and try again."
_NO_THREAD_COPY = "There is no paused case to decide. Submit the vitals first."
