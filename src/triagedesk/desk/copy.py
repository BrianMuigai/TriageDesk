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
_EMPTY_BODY = "Enter the patient's vitals and complaint, then choose Review details."
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
# The mid-call question panel (ELICIT-05): a QUESTION, never a decision. The framing line is
# what stops a nurse (or a reviewer) mistaking this surface for the approval gate.
_QUESTION_HEADING = "A question before this case continues"
_QUESTION_FRAMING = "Answering is not an approval — nothing is queued from this form."
_QUESTION_ACCEPT = "Send answer"
_QUESTION_DECLINE = "Decline to answer"
_QUESTION_SENT = "Answer sent — the case continues; nothing has been committed."
_QUESTION_DECLINED = "You declined to answer — nothing has been committed."
_QUESTION_UNAVAILABLE = "The question could not be delivered — nothing has been committed."
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
_WAITING_CAPTION = "Committed queue"
_WAITING_EMPTY = "No patients are waiting. Approved cases appear here."
_WAITING_FAILED = (
    "The waiting room could not be read. Nothing has been changed. "
    "Try again, or check the desk log."
)

# The chat workspace's own copy (presentation only, no clinical value). The assistant is a
# triage-support surface: it says what it heard and what the deterministic scorer recommends,
# and it never claims to give clinical advice or to act on its own.
_CHAT_ASSISTANT = "TriageDesk assistant"
_CHAT_NURSE = "You"
_CHAT_WELCOME_LEAD = (
    "Record the vitals, add the presenting complaint, and I will return a sourced SATS "
    "suggestion for you to confirm."
)
_CHAT_WELCOME_BODY = (
    "This workspace supports triage only. It does not give clinical advice, and nothing "
    "reaches the queue without a named clinician's approval."
)
_CHAT_WELCOME_STEPS = (
    "1. Add the complaint or paste a note. 2. Complete the structured intake. "
    "3. Review the suggestion and its evidence. 4. Approve, edit, or dismiss."
)
_CHAT_COMPOSER_LABEL = "Paste a note"
_CHAT_COMPOSER_PLACEHOLDER = "Paste the nurse's note, or describe the complaint…"
_CHAT_COMPOSER_HINT = (
    "The note only fills the structured intake. Online, the local model reads it into the "
    "fields; offline, the text becomes the presenting complaint. You confirm every value "
    "before anything is scored."
)
_CHAT_SEND_NOTE = "Fill form from note"
_CHAT_NOTE_OFFLINE = (
    "Added as the presenting complaint. Complete the vitals in the structured intake; the "
    "deterministic scorer uses those values."
)
_CHAT_NOTE_FAILED = (
    "I could not read that note. Your form is unchanged — complete it manually, or try again."
)
_CHAT_NOTE_EMPTY = "Type a complaint or paste a note before sending."
_CHAT_EXTRACTION_HEADING = "Here is what I read"
_CHAT_EXTRACTION_BODY = "Review and correct the structured intake. Nothing has been scored yet."
_CHAT_EXTRACTION_NOT_STATED = "Not stated"
_CHAT_PANEL_CONVERSATION = "Conversation"
_CHAT_PANEL_INTAKE = "Structured intake"
_CHAT_PANEL_WAITING = "Queue"
_CHAT_PANEL_WAITING_COPY = "Approved cases, ordered by acuity."
_CHAT_BADGE_SUGGESTION = "Suggestion only"
_CHAT_BADGE_SCORED = "Scored input"
_CHAT_RAIL_STATION_EYEBROW = "Station link"
_CHAT_RAIL_STATION_TITLE = "MCP"
_CHAT_RAIL_STATION_BODY = (
    "TriageDesk is triage-only. Other hospital stations read the same triage result through "
    "the TriageDesk MCP server."
)
_CHAT_RAIL_FOOT = "Triage support only. Nothing is queued without a named clinician's approval."
_CHAT_HANDOVER_HEADING = "Handover"
_CHAT_HANDOVER_FRAMING = (
    "Approved by a named clinician. These are the same sourced facts the MCP server returns "
    "to another station."
)
_CHAT_HANDOVER_CASE = "Case"
_CHAT_HANDOVER_PRIORITY = "Priority"
_CHAT_HANDOVER_TARGET = "Target"
_CHAT_HANDOVER_APPROVED_BY = "Approved by"
_CHAT_HANDOVER_DECISION = "Decision"
_CHAT_HANDOVER_QUEUE = "Queue position"
_CHAT_HANDOVER_CITATIONS = "Citations"
_CHAT_HANDOVER_NOT_RECORDED = "Not recorded"
_CHAT_HANDOVER_SECOND_LOOK = "Second look"
_CHAT_HANDOVER_NONE = "None"
_CHAT_HANDOVER_MCP = (
    "Read-only projection. The committed queue row and the hash-chained audit record remain "
    "authoritative."
)

# The guided patient flow (Phase 26). One primary task per step; the confirm step is the
# human checkpoint before any scoring or graph run.
_STEP_RECORD = "Record"
_STEP_CONFIRM = "Confirm"
_STEP_REVIEW = "Review & decide"
_STEP_HANDOVER = "Handover"
_STEP_NAV_LABEL = "Triage steps"
_RECORD_HEADING = "Start with a note (optional)"
_RECORD_COPY = (
    "Paste the nurse's note and the local model will fill the structured intake below. "
    "The form is always the scored input."
)
_RECORD_OFFLINE_HINT = (
    "Offline, the note becomes the presenting complaint; the vitals stay yours to record."
)
_RECORD_ONLINE_HINT = (
    "Online, the note is read into the fields for your review. You confirm every value."
)
_FORM_PRIMARY = "Review details"
_FORM_LOADING = "Checking the details…"
_CONFIRM_HEADING = "Confirm what will be scored"
_CONFIRM_COPY = (
    "Check every value and the gaps below. Nothing is scored until you choose "
    "\u201cLooks right — get suggested priority\u201d."
)
_CONFIRM_SCORE = "Looks right — get suggested priority"
_CONFIRM_EDIT = "Edit details"
_CONFIRM_GAPS = "Not stated"
_CONFIRM_PROVENANCE = "From note"
_CONFIRM_PROVENANCE_NOTE = (
    "Values marked From note were read from your note. Edit anything that is wrong."
)
_REVIEW_HEADING = "Review & decide"
_REVIEW_COPY = (
    "This is a suggestion, not a decision. Check the evidence, then record a named decision."
)
_REVIEW_PATIENT = "Patient details"
_REVIEW_EDIT = "Edit details"
_REVIEW_GATE_TITLE = "Your decision"
_START_NEXT = "Start next patient"
_OUTCOME_KICKER = "Complete"
_OUTCOME_COPY = "The case is complete. Start a new patient when you are ready."
_OUTCOME_TERMINAL_COPY = "Nothing was committed. Review the patient details or start a new patient."
