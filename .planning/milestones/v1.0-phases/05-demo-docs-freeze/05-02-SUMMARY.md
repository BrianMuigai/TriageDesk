---
phase: 05-demo-docs-freeze
plan: 02
subsystem: demo-runbook
tags: [docs, runbook, demo, cli-grounding, pytest, demo-01]

# Dependency graph
requires:
  - phase: 05-demo-docs-freeze
    provides: "the one-command demo CLI (05-01): `uv run triagedesk demo`, `--beat <name>`, `--list`"
  - phase: 04-evals
    provides: "the measured report + the E-09 declared failure (the honesty clause the runbook shows)"
provides:
  - "docs/DEMO.md — the demo runbook: storyboard timing -> exact commands -> expected on-screen output, recording declared human"
  - "tests/test_demo_runbook.py — the runbook-vs-CLI grounding proof"
affects: [05-demo-docs-freeze, demo-recording, submission-video]

actuals:
  tokens: 2532
  tasks: 2
  commits: 2
plan_head_before: abd3da2e06ba6ca3012471ba757776c8be6be361
plan_head_after: 4b5758cf9e8a8ff8b080754dec3c421669982b5c

tech-stack:
  added: []
  patterns:
    - "Runbook maps the ROADMAP storyboard to commands + expected output and links the storyboard (DRY: no restate)"
    - "Expected output quotes the real CLI output, never a hand-written mock"
    - "Grounding test parses fenced command blocks and drives the CLI through its public main surface"

key-files:
  created:
    - docs/DEMO.md
    - tests/test_demo_runbook.py
  modified: []

key-decisions:
  - "The runbook links ROADMAP.md for the canonical storyboard and maps each timing band to its beat(s) + command, rather than restating the table (DRY)"
  - "Expected on-screen output is quoted from a real `uv run triagedesk demo` run, so the runbook points at shipped behaviour, not a mock"
  - "The grounding test drives the CLI via its public main surface (the console-script entry point), never a private helper"
  - "The runbook documents the bare one-command path and each `--beat <name>` so a presenter can re-record a single beat"

requirements-completed: [DEMO-01]

coverage:
  - id: D1
    description: "A written runbook maps the < 3 min storyboard to the exact terminal commands and the expected on-screen output per beat"
    requirement: DEMO-01
    verification:
      - kind: unit
        ref: "tests/test_demo_runbook.py#test_no_cli_beat_is_omitted"
        status: pass
      - kind: unit
        ref: "tests/test_demo_runbook.py#test_runbook_documents_the_bare_one_command_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "The runbook declares the 3-minute screen recording a HUMAN action against the frozen tag, with tool calls visible and the failure shown"
    requirement: DEMO-01
    verification:
      - kind: unit
        ref: "tests/test_demo_runbook.py#test_runbook_declares_the_recording_a_human_action"
        status: pass
      - kind: unit
        ref: "tests/test_demo_runbook.py#test_runbook_shows_the_e09_failure"
        status: pass
    human_judgment: true
  - id: D3
    description: "Every command the runbook documents is exercised against the real CLI, so the runbook cannot drift from the shipped entry point"
    requirement: DEMO-01
    verification:
      - kind: unit
        ref: "tests/test_demo_runbook.py#test_documented_beats_exist_in_the_cli"
        status: pass
    human_judgment: false

duration: 2min
completed: 2026-10-10
status: complete
---

# Phase 5 Plan 02: Demo, Docs & Freeze — Demo Runbook Summary

**A demo runbook (`docs/DEMO.md`) that maps the ROADMAP storyboard timing bands to the exact `uv run triagedesk demo` commands and the real expected on-screen output, declares the 3-minute screen recording a HUMAN action against the frozen `v1.0-submission` tag, and is kept honest by a test that grounds every documented beat against `triagedesk demo --list`.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-10-10T01:05:00Z (approx)
- **Completed:** 2026-10-10T01:07:17Z
- **Tasks:** 2
- **Files modified:** 2 (2 created)

## Accomplishments
- `docs/DEMO.md` is the submission-video runbook: one-time setup (`uv sync --locked`; `ollama pull` only for `--online`), the bare one-command path, and a per-beat command + expected-output mapping for every storyboard timing band (DEMO-01, D-07).
- The recording is declared an **unedited HUMAN screen recording** (`< 3 min`, tool calls on screen, no slides, uploaded publicly) recorded against the **frozen tag `v1.0-submission`** (created in 05-03) — the actual video is a declared human action.
- The expected output per beat is quoted from a **real** `uv run triagedesk demo` run — colour, target, matched ids, citations, the refusal's `GATE REFUSED : ... (rows added this beat: 0)`, and the E-09 `DECLARED : ORANGE` / `MEASURED : GREEN (SHOWN MISMATCH)` — never a hand-written mock.
- `tests/test_demo_runbook.py` (5 tests) parses the runbook's fenced command blocks and proves every documented `--beat` exists in `triagedesk demo --list`, no CLI beat is omitted, and the human-recording + E-09 clauses are present (T-05-06).
- The "what is unfinished" close links `EVALS.md` §6/§7 and `README.md` rather than restating numbers (DRY).

## Task Commits

Each task was committed atomically:

1. **Task 1: Write `docs/DEMO.md` — the demo runbook** - `162b66e` (docs)
2. **Task 2: Ground the runbook against the shipped CLI** - `4b5758c` (test)

**Plan metadata:** _(this SUMMARY commit)_

## Files Created/Modified
- `docs/DEMO.md` — the demo runbook: human-recording declaration + `v1.0-submission` tag, one-time setup, the bare one-command path and `--beat <name>` commands, the timing-band → command → expected-output table, real per-beat output, and the unfinished close.
- `tests/test_demo_runbook.py` — the runbook-vs-CLI grounding proof (fenced-block parse + public `main` surface).

## Decisions Made
- The runbook **links** `ROADMAP.md` for the canonical storyboard and adds only the mapping (timing → beat → command → output); it does not restate the storyboard table (CONVENTIONS §1: docs link, never duplicate).
- Expected output is quoted from a real CLI run so the runbook points at shipped behaviour; case ids are noted as content-derived and queue positions as accumulating across the run.
- The grounding test drives the CLI through its public `main` surface (the console-script entry point), never by importing a private helper.
- The runbook documents both the bare one-command path and each `--beat <name>` so a presenter can re-record a single beat.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. The demo CLI from 05-01 printed every owned tool call and the sourced outcome exactly as the runbook documents; the grounding test found no drift.

## Threat Surface

- **T-05-05 (Information Disclosure) — mitigated:** the runbook carries only synthetic fixtures and the demo identity `Nurse Demo`; no credentials or real data; the documented commands run offline by default (bare `triagedesk demo` — no model, no borrowed server).
- **T-05-06 (Repudiation) — mitigated:** `tests/test_demo_runbook.py` exercises every documented beat against the real CLI; no staged or mocked output.
- **T-05-SC (Tampering) — mitigated:** the runbook's only install step is `uv sync --locked`; no new packages introduced.

No new security-relevant surface beyond the plan's threat model.

## User Setup Required
None automated. The **3-minute screen recording is a declared HUMAN action** (DEMO-01) to be performed against the frozen `v1.0-submission` tag using this runbook; the agent produces the runbook and the scripted CLI, not the video.

## Next Phase Readiness
- The runbook + the one-command demo (05-01) are ready for the human recording (DEMO-01, declared human).
- No blockers. Plan 05-03 finalises the submission docs and runs the freeze protocol (tag, disable `commit_docs`/CI/hooks, audit the remote).

---

## Self-Check: PASSED

- All 2 created artifacts exist on disk.
- All 2 task commits (`162b66e`, `4b5758c`) are ancestors of HEAD.
- `uv run pytest tests/test_demo_runbook.py -q` → 5 passed; `uv run pytest -q` → 230 passed; `uv run ruff check` → clean.
