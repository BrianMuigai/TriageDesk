---
phase: 26-clarify-desk-intake-and-review-flow-and-reset-the-demo-state
plan: "26-01"
subsystem: desk-ux
tags: [ux, intake, human-in-the-loop, confirm, review, demo-reset]
requires: []
provides:
  - "A guided Record → Confirm → Review & decide → Handover patient flow"
  - "A mandatory confirm checkpoint with note provenance and not-stated gaps"
  - "A real Edit details path back to the intake from confirm and review"
  - "A clean demo database state"
affects: [desk-surface, docs/DESK.md]
actuals:
  tokens: 0
  tasks: 3
  commits: 0
tech-stack:
  added: []
  patterns:
    - "One primary task per step; no graph run before the human confirm"
    - "Note provenance carried in a hidden form field, not a session store"
    - "Edit details as a POST /case action=back with the case values"
key-files:
  created: []
  modified:
    - src/triagedesk/desk/views.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/forms.py
    - src/triagedesk/desk/clarification.py
    - src/triagedesk/desk/copy.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - tests/test_desk.py
    - tests/test_desk_chat.py
    - docs/DESK.md
key-decisions:
  - "The nurse must explicitly confirm the exact values before the graph or scorer runs."
  - "The note helper is optional and lives above the form; it is not a parallel chat intake."
  - "Values read from a note are labelled From note on the confirm step."
  - "The review step shows the card and gate only; the intake is a summary with an Edit details path."
duration: —
completed: 2026-11-17
status: complete
---

# Phase 26 — Summary

**The desk now guides a nurse through one patient at a time: Record → Confirm → Review & decide
→ Handover. The confirm step is a real human checkpoint, and the demo database is clean.**

## What shipped

- **Guided step state**: `POST /case` now distinguishes `note`, `confirm`, `score`, and `back`.
  The no-action default still runs the graph for existing callers/tests.
- **Step 1 — Record**: full-width structured intake, optional compact note helper above it, and
  `Review details` as the primary action. No card or gate.
- **Step 2 — Confirm**: a read-only summary of every value, `From note` provenance for note-read
  fields, the not-stated gaps, and two actions: `Looks right — get suggested priority` and
  `Edit details`. No graph, scorer, card, gate, or queue write runs on this render.
- **Step 3 — Review & decide**: the priority card and the named gate only; a compact patient
  details card with `Edit details` returns to step 1 with the same values.
- **Step 4 — Handover**: the committed handover and `Start next patient`; a dismissal says
  nothing was committed.
- **Human-in-the-loop fixes**:
  - the vitals submit button stays enabled so its `name=action value=confirm` is not dropped;
  - the clarification panel carries the case values so the review summary survives an answer;
  - the outcome copy is conditional (committed vs dismissed vs refused).
- **Demo reset**: root `triage.db`, `checkpoints.db`, and `tests/triage.db` were moved to
  `/tmp/opencode/triagedesk-demo-reset-20261117-081612/`. A fresh desk served an empty waiting
  room and step 1.

## Verification

- `uv run pytest -q` — **1007 passed**.
- `uv run ruff check src tests` — clean.
- Browser-driven flow at 1360px and 375px: Record → Confirm → Review & decide → Handover.
- `GET /waiting` on the reset state: “No patients are waiting. Approved cases appear here.”

## Out of scope

No change to the scorer, matcher, retrieval, confidence, planner, graph topology, approval gate,
commit tool, or audit chain. MCP remains the station integration path.
