---
phase: quick
plan: "261013-sbd"
subsystem: ui
tags: [desk, mcp, pydantic, tdd, quick]

# Dependency graph
requires: []
provides:
  - "CommitResult.position: int | None — the typed queue position on the ONE gated-commit contract (additive; default None)"
  - "mcp/server.py::commit_priority sets position=row.position (reason string byte-identical)"
  - "desk/server.py::_decision_view names the position on the committed panel, falling back to today's exact copy when absent"
  - "docs/DESK.md + docs/DEMO.md quote the position-bearing committed copy; docs/DECISIONS.md D26 records the WHY"
affects: [desk, demo, decisions]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 3121
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Typed channel over free-text: the desk reads a new typed CommitResult field, never string-parses the free-text reason"

# TDD gate evidence (Task 1 was type=tracer tdd=true)
tdd:
  red:
    command: "uv run pytest tests/test_desk.py -q -k form_to_card_to_gate_to_commit"
    exit_code: 1
    target_test: "tests/test_desk.py::test_form_to_card_to_gate_to_commit"
    expected: "Approved by Nurse Demo (triage nurse) — committed to the queue at position 1."
    actual: "AssertionError — the panel rendered the position-free copy (no position clause)"
    semanticAssessment: "The named target test executed and failed on the planned assertion for the intended reason — the position clause was absent. Not a syntax/import/fixture fault."
    commit: "1d3efde"
  green:
    commit: "d343469"
    note: "Schema field + tool wiring + desk render made the target test pass; focused subset green."
  refactor:
    commit: null
    note: "No refactor needed — GREEN was already minimal (one suffix variable shared by both committed copies)."

key-files:
  created: []
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/desk/server.py
    - tests/test_desk.py
    - tests/test_mcp_tools.py
    - tests/test_commit_idempotent.py
    - docs/DESK.md
    - docs/DEMO.md
    - docs/DECISIONS.md

key-decisions:
  - "The committed queue position is a typed CommitResult.position field, never parsed from the free-text reason (D26)."
  - "CommitResult stays the one contract model without extra='forbid', so the field is additive and every existing reader is unaffected."

patterns-established:
  - "Typed channel over free-text: the desk names the position off getattr(commit, 'position', None), never off CommitResult.reason."

requirements-completed: [QUICK-261013]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "The desk post-decision panel names the queue position the gated write assigned."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_form_to_card_to_gate_to_commit"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_committed_panel_names_the_queue_position_when_present"
        status: pass
    human_judgment: false
  - id: D2
    description: "A CommitResult without a position renders today's exact position-free copy (no crash, no behaviour change)."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_committed_panel_falls_back_to_the_position_free_copy_when_absent"
        status: pass
    human_judgment: false
  - id: D3
    description: "A repeat and an edit of the SAME case keep the SAME typed position with exactly one queue row."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_commit_priority_commits_once_through_the_injected_store"
        status: pass
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_an_edit_supersedes_the_same_case_keeping_the_same_position"
        status: pass
    human_judgment: false
  - id: D4
    description: "The pinned transcripts (docs/DESK.md, docs/DEMO.md) quote the position-bearing copy and docs/DECISIONS.md records D26."
    requirement: "QUICK-261013"
    verification:
      - kind: automated_ui
        ref: "tests/test_desk_runbook.py, tests/test_demo_runbook.py (11 passed)"
        status: pass
    human_judgment: false

# Metrics
plan_head_before: 7f8e367
plan_head_after: ae611b447069fba27a7e9fdbf1435b0623d30743
duration: 4min
completed: 2026-10-13
status: complete
---

# Quick Task 261013-sbd: Desk panel shows the queue position Summary

**The gated commit exposes its assigned queue position as a typed `CommitResult.position`, and the desk's post-decision panel names it ("… at position N") while falling back to today's exact copy when it is absent.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-13T17:29:38Z
- **Completed:** 2026-10-13T17:33:45Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- `CommitResult.position: int | None = None` added to the ONE gated-commit contract (additive — `CommitResult` is the single contract model without `extra="forbid"`, so every existing constructor/reader still validates).
- `mcp/server.py::commit_priority` sets `position=row.position` on the success return; the CLI `reason` string is left byte-identical (DEMO.md:178 and the demo-runbook guard stay green).
- `desk/server.py::_decision_view` names the position off the typed channel (`getattr(commit, "position", None)`) for BOTH the approve and edit copies, and renders today's exact position-free copy when it is absent — no new import, route, store access, or reason parsing in the desk package.
- Contract locked by tests: a repeat (mcp_tools) and an edit (idempotent) of the SAME case keep the SAME position with exactly one row; two hermetic render tests pin the position-bearing copy and the `None` fallback.
- Pinned docs resynced: `docs/DESK.md`, `docs/DEMO.md` storyboard rows 267–268 (the edit beat now reads position 2 with an accurate two-row gloss — E-10 is a different patient, a genuinely new row), and `docs/DECISIONS.md` D26 recording the WHY.

## Task Commits

Each task was committed atomically (Task 1 is a TDD tracer → RED + GREEN):

1. **Task 1 (RED): assert the committed panel names the queue position** — `1d3efde` (test)
2. **Task 1 (GREEN): name the committed queue position on the desk panel** — `d343469` (feat)
3. **Task 2: lock the typed position contract and the None fallback** — `96c5479` (test)
4. **Task 3: quote the position-bearing copy and record the WHY** — `ae611b4` (docs)

_No REFACTOR commit — GREEN was already minimal._

## Files Created/Modified

- `src/triagedesk/core/schema.py` — `CommitResult.position: int | None = None`; docstring names the field.
- `src/triagedesk/mcp/server.py` — `commit_priority` passes `position=row.position`; reason byte-identical.
- `src/triagedesk/desk/server.py` — `_decision_view` names the position off the typed channel, falling back to today's copy.
- `tests/test_desk.py` — happy-path assertion updated; two hermetic render tests added; `CommitResult` imported.
- `tests/test_mcp_tools.py` — repeat keeps the same position assertion.
- `tests/test_commit_idempotent.py` — approve+edit-same-case keep one position, one row.
- `docs/DESK.md` — sample committed line names the position.
- `docs/DEMO.md` — storyboard rows 267–268 quote the real beats.
- `docs/DECISIONS.md` — D26 typed-field rationale appended.

## Decisions Made

- The queue position is a typed field (`CommitResult.position`), never parsed from the free-text `reason` — the desk module reads typed channels only (module docstring; `terminal_kind()`'s explicit avoidance of `Escalation.reason`). Recorded as D26.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification

- Focused subset (plan's `<verification>`): `uv run pytest tests/test_desk.py tests/test_mcp_tools.py tests/test_commit_idempotent.py tests/test_desk_runbook.py tests/test_demo_runbook.py -q` → **100 passed**.
- Doc-content checks: `committed to the queue at position 1` in `docs/DESK.md`, `committed to the queue at position 2` in `docs/DEMO.md`, `D26` in `docs/DECISIONS.md` — all present.
- Must-have structural guards: `test_no_self_commit_path_in_the_desk_package` — the desk package imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server` (green).

## Self-Check

- FOUND: src/triagedesk/core/schema.py
- FOUND: src/triagedesk/mcp/server.py
- FOUND: src/triagedesk/desk/server.py
- FOUND: tests/test_desk.py
- FOUND: tests/test_mcp_tools.py
- FOUND: tests/test_commit_idempotent.py
- FOUND: docs/DESK.md
- FOUND: docs/DEMO.md
- FOUND: docs/DECISIONS.md
- FOUND: 1d3efde (test)
- FOUND: d343469 (feat)
- FOUND: 96c5479 (test)
- FOUND: ae611b4 (docs)

## Self-Check: PASSED

---
*Quick task: 261013-sbd*
*Completed: 2026-10-13*
