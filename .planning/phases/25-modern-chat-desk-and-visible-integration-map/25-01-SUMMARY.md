---
phase: 25-modern-chat-desk-and-visible-integration-map
plan: "25-01"
subsystem: desk-ui
tags: [ui, chat, integration, mcp, approval-gate, accessibility]
requires: []
provides:
  - "A modern chat workspace beside the structured vitals intake"
  - "A truthful note-intake composer (offline complaint, online grounded prefill)"
  - "A visible /system map of desk → core → MCP, the wire protocol, and the nine tools"
  - "UI-review blockers fixed: gate colour intent, autofocus scroll, contradictory banner"
affects: [desk-surface, docs/DESK.md, docs/MCP.md, README.md]
actuals:
  tokens: 0
  tasks: 3
  commits: 0
tech-stack:
  added: []
  patterns:
    - "Chat transcript as a presentation-only projection of the current request"
    - "Static system fragment reuses the one app shell and one stylesheet"
    - "Tool-list honesty by test-time comparison with the MCP server's registration"
key-files:
  created:
    - src/triagedesk/desk/chat.py
    - src/triagedesk/desk/static/system.html
    - tests/test_desk_chat.py
    - tests/test_system_page.py
  modified:
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - src/triagedesk/desk/views.py
    - src/triagedesk/desk/forms.py
    - src/triagedesk/desk/card.py
    - src/triagedesk/desk/gate.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/waiting.py
    - src/triagedesk/desk/copy.py
    - tests/test_desk.py
    - tests/test_desk_forms.py
    - docs/DESK.md
    - docs/MCP.md
    - README.md
key-decisions:
  - "The desk is explicitly the demo surface: it runs the core graph in-process and does not call the MCP server over the wire."
  - "The MCP server is the station integration path: MCP over stdio (JSON-RPC 2.0), nine typed tools, borrowed SQLite MCP storage."
  - "The chat composer is an intake step, never a scoring, approval, or commit step."
  - "A colour belongs to the Edit colour disclosure; Approve carries no colour and the server refuses an approve carrying one."
  - "The uncertainty banner belongs only where a suggestion (or deferred read-only card) exists."
patterns-established:
  - "A visible integration map is a first-class review surface, not a paragraph in a README."
  - "A UI tool list can be honest without importing the server: compare it in the test layer."
requirements-completed: []
coverage:
  - id: D1
    description: "Modern chat workspace + structured intake and note intake"
    verification:
      - kind: unit
        ref: "tests/test_desk_chat.py"
        status: pass
      - kind: unit
        ref: "tests/test_desk_forms.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Visible /system map of desk, core, MCP, the wire, and the nine tools"
    verification:
      - kind: unit
        ref: "tests/test_system_page.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "The three UI-review blockers are closed"
    verification:
      - kind: unit
        ref: "tests/test_desk_chat.py::test_approve_with_a_selected_colour_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_desk_forms.py::test_the_empty_page_does_not_scroll_to_the_form"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py::test_ambiguous_case_renders_a_clarification_and_no_gate"
        status: pass
    human_judgment: false
  - id: D4
    description: "No regression in the safety, gate, loopback, CSRF, or no-external-request suites"
    verification:
      - kind: unit
        ref: "uv run pytest -q"
        status: pass
    human_judgment: false
duration: —
completed: 2026-11-16
status: complete
---

# Phase 25 — Summary

**The desk now demonstrates the system: a modern chat workspace beside the structured intake, plus
a `/system` page that makes the desk → core → MCP distinction and the protocol visible. The three
UI-review blockers are closed.**

## What shipped

- **Chat workspace** (`desk/chat.py`, `index.html`, `styles.css`, `views.py`): a dark orientation
  rail, a conversation card, a sticky-first structured intake, assistant/nurse bubbles, a composer,
  and a responsive single-column collapse.
- **Note intake** (`server._handle_case`, `forms.merge_form_over_case`, `case_to_form_values`):
  offline the note becomes the complaint; online `extract_note` pre-fills the form and the nurse's
  typed values win. The composer never runs the graph or the gate.
- **System map** (`static/system.html`, `GET /system`, `test_system_page.py`): three layer cards,
  the ordered wire, a shared/different table, the nine MCP tools, and the integration rule.
- **UI-review blockers**:
  - gate colour radios moved into an Edit disclosure; Approve carries no colour; the server refuses
    an approve carrying one; the client clears stale radios;
  - no vitals autofocus on load; a schema error focuses the offending field; the gate focuses the
    approver name;
  - the uncertainty banner is suppressed on clarification, recovery, and escalation terminals.
- **Polish**: distinguishable RED/ORANGE swatches, 44px nav targets, a single waiting-room heading,
  a responsive waiting table, humanized rule details and decision labels.

## Verification

- `uv run pytest -q` — **1002 passed**.
- `uv run ruff check src/triagedesk/desk tests` — clean.
- `GET /system` and the gate were driven in a real browser (Playwright) at desktop and 375px.
- The GSD UI review scored the first implementation 14/24 and flagged three blockers; all three
  are covered by the new tests above.

## Deviations

- The sketch's sticky intake was deliberately made static on long forms; the page scrolls instead
  of clipping the complaint field behind a sticky action row.
- The desk does not add a station HTTP endpoint: MCP is the integration surface, as requested.
