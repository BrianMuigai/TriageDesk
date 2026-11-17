---
sketch: 002
name: desk-step-flow
question: "How do we stop the intake form and the chat composer competing, while keeping the review and decision clear?"
winner: "A"
tags: [layout, intake, review, stepper]
---

# Sketch 002: Desk step flow

## Design Question

The Phase 25 desk put a chat transcript and a full structured form on screen at the same time. The
nurse had to choose between typing in the composer and filling the form, and after scoring the card
and gate were buried in a long conversation while the form stayed open beside it. What flow makes
the next action obvious?

## How to View

Open `.planning/sketches/002-desk-step-flow/index.html` in a browser.

## Variants

- **A: Record → Review** — a two-step workspace. Step 1 puts a compact "start with a note" band above
  a full-width structured form; step 2 replaces the intake with the priority card, gate and a
  collapsed patient summary. The recommended direction.
- **B: Three-step wizard** — Record → Review → Decide, one task per screen. Clearest for a new user,
  but adds a click and hides the full form behind a choice.
- **C: Structured / Note tabs** — an explicit mode switch beside the form. Keeps both surfaces, but
  still asks the nurse to choose a mode and keeps the form visible while reviewing.

## What to Look For

- Whether the structured form feels like the primary intake in step 1.
- Whether the note composer reads as an optional helper, not a second place to record the case.
- Whether the card and gate dominate step 2 without the form competing.
- Whether the patient summary is discoverable when the nurse needs to correct a value.
- Density at 1280px and collapse at 375px.

## Outcome

Variant **A: Record → Review** won. It gives one primary action per state, keeps the note as an
optional intake helper above the form, and makes the review/decision step the only thing on screen
after scoring. The shipped implementation uses A's two-step staging with a collapsed patient-details
form in the review step.
