---
phase: 05-demo-docs-freeze
plan: 01
subsystem: demo-cli
tags: [cli, langgraph, mcp, argparse, github-actions, pytest, offline-demo]

# Dependency graph
requires:
  - phase: 04-evals
    provides: "the shipped eval seams (load_cases, build_tools) + the real measured run"
  - phase: 03-graph-safety
    provides: "the graph (build_graph), the approval gate (interrupt) and the gated commit_priority"
  - phase: 02-scorer-tools
    provides: "the five owned MCP tools + the store seam (mcp.server.set_store)"
provides:
  - "a one-command offline demo: `uv run triagedesk demo` runs the whole storyboard on the bundled fixture"
  - "a tool-call tracer that prints every owned tool call (name + inputs -> outputs) for the demo video"
  - "demo/storyboard.yaml — the beat manifest over the bundled eval cases"
  - ".github/workflows/smoke.yml — CI smoke of the exact bare one-command path"
  - "tests/test_demo.py — the demo-path regression proof"
affects: [05-demo-docs-freeze, README-quickstart, demo-runbook]

actuals:
  tokens: 5049
  tasks: 3
  commits: 3
plan_head_before: b0381f2e85e461e83bf78c6d714f6c80e8905185
plan_head_after: e4c20cc69972165ec7ce6cf3e8cc42404b73f01e

tech-stack:
  added: []
  patterns:
    - "Demo runner reuses the eval seams (load_cases + build_tools + build_graph) — no bespoke graph path (DRY)"
    - "Tool-call tracer wraps the injected ToolMap so every owned call is visible without touching the tools"
    - "Offline store injection (mcp.server.set_store, restored in finally) so the demo launches no borrowed subprocess"
    - "Refusal climax read from the store row delta, not asserted by fiat"

key-files:
  created:
    - src/triagedesk/demo/__init__.py
    - src/triagedesk/demo/run.py
    - demo/storyboard.yaml
    - .github/workflows/smoke.yml
    - tests/test_demo.py
  modified:
    - src/triagedesk/cli.py
    - pyproject.toml

key-decisions:
  - "run_demo reuses evals.runner's _capture and _checkpointer rather than re-implementing the outcome capture / msgpack allowlist (DRY; the private cross-module import is the established pattern)"
  - "The unapproved resume value (a bare `dismiss` naming no approver) is declared ONCE in the demo module; the refusal beat is selected by its manifest name"
  - "The named approval is a well-formed ApprovalToken (incl. approved_at); the graph fills final_colour for an approve, so the gated commit validates it and writes exactly one row"
  - "The refusal beat's climax is shown from the real store row delta (rows added: 0), so no value is hard-coded"
  - "The demo package is exempted from the core/ TID251 import ban (it is an edge module like evals/graph, legitimately depending on mcp/store)"

patterns-established:
  - "One-command demo: a thin CLI subcommand over an async runner that reuses the shipped graph seams"
  - "Per-beat run isolation with a per-beat thread_id and a fresh store in tests"

requirements-completed: [DOCS-01, DOCS-03]

coverage:
  - id: D1
    description: "A stranger runs the bare `uv run triagedesk demo` (offline by default) and sees the whole storyboard run to sourced priorities and the approval gate refuse"
    requirement: DOCS-01
    verification:
      - kind: unit
        ref: "tests/test_demo.py#test_full_storyboard_returns_zero"
        status: pass
      - kind: unit
        ref: "tests/test_demo.py#test_manifest_names_every_declared_beat"
        status: pass
    human_judgment: false
  - id: D2
    description: "The gated commit refuses without a named nurse: the escalation beat (named approval) writes exactly one queue row, the refusal beat writes none"
    requirement: DOCS-01
    verification:
      - kind: unit
        ref: "tests/test_demo.py#test_named_approval_commits_exactly_one_row"
        status: pass
      - kind: unit
        ref: "tests/test_demo.py#test_refusal_writes_no_queue_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every owned tool call is visible on screen (name + inputs -> outputs); the escalation beat reaches four tools, the deterioration beat reaches raise_recheck_flag"
    requirement: DOCS-01
    verification:
      - kind: unit
        ref: "tests/test_demo.py#test_escalation_beat_reaches_four_owned_tools"
        status: pass
      - kind: unit
        ref: "tests/test_demo.py#test_deterioration_beat_reaches_raise_recheck_flag"
        status: pass
    human_judgment: false
  - id: D4
    description: "CI runs the exact bare one-command path (`.github/workflows/smoke.yml`) and fails the build if it breaks"
    requirement: DOCS-03
    verification:
      - kind: other
        ref: ".github/workflows/smoke.yml runs `uv run triagedesk demo`; the same command exits 0 (tests/test_demo.py + task verify)"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-10
status: complete
---

# Phase 5 Plan 01: Demo, Docs & Freeze — One-Command Demo Summary

**A one-command offline demo (`uv run triagedesk demo`) that runs the whole five-beat storyboard through the real graph, prints every owned tool call, and shows the approval gate refusing without a named nurse — plus a CI smoke workflow on that exact path.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-09T21:58:38Z
- **Completed:** 2026-10-09T22:02:53Z
- **Tasks:** 3
- **Files modified:** 7 (5 created, 2 modified)

## Accomplishments
- `uv run triagedesk demo` runs the full storyboard offline on the bundled synthetic fixture in one command (DOCS-01, D-01) — no pulled model, no borrowed subprocess.
- Every owned tool call is traced on screen (`[tool] <name> <inputs> -> <outputs>`) so the tool path is visible for the demo video (D-07).
- The five beats run in order: routine → GREEN, escalation → ORANGE (committed under a named nurse), deterioration → second-look `raise_recheck_flag`, the approval gate **refusing** (no queue row), and the E-09 declared failure shown as declared ORANGE vs measured GREEN.
- `.github/workflows/smoke.yml` runs that exact bare command and fails the build if it breaks (DOCS-03, D-02).
- `tests/test_demo.py` proves the demo path against the shipped seams (6 tests, all passing).

## Task Commits

Each task was committed atomically:

1. **Task 1: `triagedesk demo` — one beat end-to-end on the bundled fixture** - `f237b81` (feat)
2. **Task 2: Full storyboard sequence — incl. the refusal beat and the E-09 failure** - `dc65cc0` (feat)
3. **Task 3: CI smoke test on the exact one-command path + demo regression test** - `e4c20cc` (test)

**Plan metadata:** _(this SUMMARY commit)_

## Files Created/Modified
- `src/triagedesk/demo/__init__.py` - the demo package seam (exports `run_demo`, `list_beats`, `load_storyboard`)
- `src/triagedesk/demo/run.py` - the demo runner: storyboard loader, tool-call tracer, per-beat graph run, store injection, refusal climax
- `demo/storyboard.yaml` - the beat manifest (`{name, case, label}`) over the bundled `evals/cases/*.yaml`
- `src/triagedesk/cli.py` - the `demo` subcommand (`--online`, `--beat`, `--list`, `--fixture`)
- `.github/workflows/smoke.yml` - CI smoke of the exact bare `uv run triagedesk demo`
- `tests/test_demo.py` - the demo-path regression proof
- `pyproject.toml` - TID251 per-file-ignore for the `demo/` edge package (Rule 3)

## Decisions Made
- `run_demo` reuses `evals.runner._capture` and `evals.runner._checkpointer` instead of duplicating the outcome capture and the msgpack allowlist (DRY; the private cross-module import matches the existing `graph.build._allowed_msgpack_modules` usage).
- The unapproved resume value (`{"decision": "dismiss"}`, naming no approver) is declared once in the demo module; the refusal beat is selected by its manifest name.
- The named approval is a well-formed `ApprovalToken` including `approved_at`; the graph fills `final_colour` from the scored colour for an `approve`, so the gated commit validates it and writes exactly one queue row (T-05-11).
- The refusal beat's climax is derived from the real store row delta (`rows added this beat: 0`), not asserted by fiat (T-05-01, T-05-03).
- The `demo/` package is exempted from the core/ TID251 import ban because it is an edge module (like `evals/`/`graph/`) that legitimately depends on `mcp`/`store`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Exempted the `demo/` edge package from the core/ TID251 import ban**
- **Found during:** Task 1 (lint before the first commit)
- **Issue:** `ruff check` failed with three TID251 errors — `demo/run.py` imports `triagedesk.mcp` and `triagedesk.store`, which the banned-api rule (scoped for `core/`) flags. The plan's verification requires `uv run ruff check` to stay green, and the ban is meant for `core/` only.
- **Fix:** Added `"src/triagedesk/demo/**" = ["TID251"]` to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`, matching the existing `evals/**`, `graph/**`, `store/**` exemptions.
- **Files modified:** `pyproject.toml`
- **Verification:** `uv run ruff check` → "All checks passed!"; full suite 225 passed.
- **Committed in:** `f237b81` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The lint exemption is necessary to keep the repo's lint gate green for a legitimate edge module. No scope creep — no new dependency, no scoring-logic change.

## Issues Encountered
None. The demo reuses the shipped seams exactly as the plan specified; the tracer wraps the injected `ToolMap` without touching the real tools.

## User Setup Required
None - the offline demo runs fully in-process (no model, no borrowed server, no credentials). The `--online` flag is the opt-in path to the pulled local model.

## Next Phase Readiness
- The one-command demo path (DOCS-01) and its CI smoke (DOCS-03) are shipped and proven; the demo is ready for the human screen recording (DEMO-01, declared a human action).
- No blockers. The remaining Phase-5 plans finalise the submission docs (ARCHITECTURE/EVALS/DESCRIPTION/README) and the freeze protocol.

---
*Phase: 05-demo-docs-freeze*
*Completed: 2026-10-10*

## Self-Check: PASSED

- All 6 created/modified artifacts exist on disk.
- All 3 task commits (`f237b81`, `dc65cc0`, `e4c20cc`) are ancestors of HEAD.
- `uv run pytest tests/test_demo.py -q` → 6 passed; `uv run triagedesk demo` → exit 0; `uv run ruff check` → clean; full suite → 225 passed.

