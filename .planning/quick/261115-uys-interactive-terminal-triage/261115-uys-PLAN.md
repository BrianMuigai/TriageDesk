---
quick_id: 261115-uys
slug: interactive-terminal-triage
phase: quick-261115-uys
plan: 01
type: execute
wave: 1
depends_on: []
branch: feat/v1.3-adaptive-triage
status: complete
files_modified:
  - src/triagedesk/desk/interactive.py
  - src/triagedesk/cli.py
  - src/triagedesk/desk/extraction.py
  - src/triagedesk/llm/client.py
  - src/triagedesk/mcp/server.py
  - tests/test_interactive.py
  - tests/test_readme_runbook.py
  - README.md
  - docs/DESK.md
must_haves:
  truths:
    - "`uv run triagedesk triage` drives one patient through the shipped graph from the terminal — no browser and no pre-recorded fixture."
    - "A raw nurse note is accepted and read into the typed case by the ONE grounded composition; the extracted fields are shown, and an unstated value is dropped, never imputed."
    - "The surface adds no decision path: it delegates to `desk.pipeline` (`submit_case` / `answer_clarification` / `decide`) and the ONE elicitation vocabulary."
    - "An answer typed at a question is an observation, not an approval; the gate still pauses afterwards."
    - "A blank approver cannot commit, and a dismissal writes nothing."
  artifacts:
    - src/triagedesk/desk/interactive.py
    - tests/test_interactive.py
  key_links:
    - "docs/DESK.md — the terminal quickstart, next to the browser one"
---

# Quick task: interactive terminal triage (with raw notes)

## Context

The shipped surfaces were a browser desk (`triagedesk desk`) and a scripted storyboard
(`triagedesk demo`). A reviewer asked to run one patient from the terminal, supplying the details
directly, and then — a follow-up — to paste a **raw description** instead of answering fields.

## Tasks

1. **Intake** — `desk/interactive.py`: prompt for the vitals and complaint through the ONE
   `CaseInput` schema; blank skips a vital, the complaint is required, an impossible value is
   re-prompted. Offer a raw note first; read it through the grounded extraction composition and
   show what was understood (and what was not stated) for confirmation.
2. **Run** — delegate to `desk.pipeline.submit_case` / `answer_clarification` / `decide`; render the
   handover card or the honest safe terminal; loop until the operator stops.
3. **CLI** — add `triagedesk triage [--online] [--note TEXT|-]`; `--note` is the scripting path.
4. **DRY** — one note→case composition (`llm.client.extract_grounded`) shared by the owned
   `normalize_case` tool and the terminal intake; the model call stays injectable so the existing
   patchable seam still works.
5. **Tests** — intake validation, approve → one queue row, dismiss → none, blank approver never
   commits, raw-note accept/decline/offline-refusal, `--note` with and without `--online`, the
   clarification form declining on a blank, and the renderer never inventing a card.
6. **Docs** — `README.md` quickstart and `docs/DESK.md` terminal section; the README/DESK runbook
   guards execute the new command.

## Verification

`uv run pytest -q` → 967 passed · `uv run ruff check src tests` → clean · a real `--online --note`
run extracted a pasted note, scored ORANGE with citations, and committed one queue row on approval.
