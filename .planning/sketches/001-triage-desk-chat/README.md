---
sketch: 001
name: triage-desk-chat
question: "What layout makes a chat-style triage desk feel modern without displacing the structured vitals form?"
winner: "A"
tags: [layout, chat, form, triage]
---

# Sketch 001: Triage desk chat

## Design Question

The desk needs a chat-style conversation that carries the nurse from a note/complaint to a
sourced suggestion and a named decision, while the structured vitals form stays authoritative
and keyboard-first. Which page structure does that best?

## How to View

Open `.planning/sketches/001-triage-desk-chat/index.html` in a browser.

## Variants

- **A: Workbench** — dark rail, conversation card, sticky structured intake. The default is a
  familiar clinical workspace: navigation on the left, the conversation in the middle, the
  scored form beside it.
- **B: Split console** — no rail; conversation and form are equal halves under a single top bar.
  More screen for the two working surfaces, less orientation.
- **C: Focus mode** — one narrow conversation column with the intake in a collapsible drawer.
  Calm and mobile-first, but the form is one interaction away.

## What to Look For

- Whether the conversation dominates without making the form feel secondary.
- Whether the suggestion card reads as a message, not a dashboard widget.
- Whether the composer's relationship to the structured form is obvious.
- Whether the waiting-room / MCP station link is discoverable without clutter.
- Density at 1280px and collapse behaviour at 980px and 620px.

## Outcome

Variant **A: Workbench** won. It keeps the nurse oriented (rail), gives the conversation a
readable column, and keeps the scored vitals visible and sticky beside it. The implementation
uses A's structure with B's dense two-column form grid and C's mobile single-column collapse.
