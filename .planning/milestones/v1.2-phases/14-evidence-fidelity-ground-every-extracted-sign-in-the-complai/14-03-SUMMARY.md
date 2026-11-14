---
phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai
plan: 03
subsystem: docs
tags: [documentation, verify-node, fail-closed, evals-honesty, prompt-injection]

# Dependency graph
requires:
  - phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai
    provides: extraction grounding (14-01) and the committed-target card carry (14-02) whose behaviour this prose must match
provides:
  - ARCHITECTURE.md verify row and edges line matching the shipped deterministic, fail-closed check
  - docs/REQUIREMENTS.md JC-1 and SW-1 matching the shipped check and stating the E-13 position honestly
affects: [verify-work, audit, submission-docs]

# Actuals (#2632) — chars/4 over the realized diff of the two changed docs.
actuals:
  tokens: 1178
  tasks: 2
  commits: 2

plan_head_before: 6e32a93
plan_head_after: 5bb8910

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Doc claims are checked against the shipped symbols (nodes.verify, build.route_after_verify), not against keyword search hits."
    - "Measured eval status is linked (EVALS.md §4), never restated, so the projection stays the single source of numbers."

key-files:
  created: []
  modified:
    - ARCHITECTURE.md
    - docs/REQUIREMENTS.md

key-decisions:
  - "ARCHITECTURE's verify row now says deterministic / fail-closed terminal (no gate/commit/card); the critic label and the retry claim are gone."
  - "The edges line routes an uncited priority to END instead of a retry."
  - "SW-1 records extraction grounding as shipped and unit-tested while the measured E-13 status is unchanged, linking EVALS.md §4 instead of copying numbers."

patterns-established:
  - "Honesty statement: describe the mitigation's test coverage and link the measured row; never imply a green result."

requirements-completed: [JC-1, JC-4, JC-5]

coverage:
  - id: D1
    description: "ARCHITECTURE.md describes one deterministic evidence check whose failure is a fail-closed terminal, within the one-page bound."
    requirement: JC-1
    verification:
      - kind: unit
        ref: "tests/test_docs_final.py#test_architecture_is_one_page"
        status: pass
      - kind: other
        ref: "wc -w ARCHITECTURE.md = 696; grep 'fail-closed terminal'; ! grep 'retry once'"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/REQUIREMENTS.md JC-1 matches the shipped check and SW-1 states the E-13 position as unit-tested with the measured status unchanged and linked."
    requirement: JC-4
    verification:
      - kind: other
        ref: "grep 'one deterministic evidence check' + 'unit-tested' docs/REQUIREMENTS.md; EVALS.md and report.json unchanged"
        status: pass
    human_judgment: true
    rationale: "The honesty framing (unit-tested vs measured) is a judgment call a reviewer should confirm; automation can prove the words exist but not that they read honestly."

# Metrics
duration: 5min
completed: 2026-11-05
status: complete
---

# Phase 14 Plan 03: Verify-prose fidelity Summary

**ARCHITECTURE and JC-1 now describe the one deterministic, fail-closed evidence check, and SW-1 states the E-13 mitigation as unit-tested with the measured status unchanged and linked.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-05T11:22:00+03:00
- **Completed:** 2026-11-05T11:26:31+03:00
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `ARCHITECTURE.md` no longer calls `verify` a critic and no longer claims a retry: the row is `deterministic` / fail-closed terminal, and the edges line routes an uncited priority to `END`.
- `docs/REQUIREMENTS.md` JC-1 describes one deterministic evidence check whose failure is a fail-closed terminal (no gate, no commit, no card) instead of a `verify`/retry loop.
- SW-1 records the extraction-grounding control (declared alias in the note for every extracted discriminator; own numeric token for every model-supplied vital), says it is shipped and unit-tested, and links `EVALS.md §4` for the unchanged measured E-13 row.

## Task Commits

Each task was committed atomically:

1. **Task 1: ARCHITECTURE describes the fail-closed check** - `e8ae1eb` (docs)
2. **Task 2: REQUIREMENTS matches the shipped check + honest E-13 position** - `5bb8910` (docs)

_Note: docs-only plan; no plan-metadata commit (`.planning/` is left uncommitted per the execution brief)._

## Files Created/Modified
- `ARCHITECTURE.md` - verify row (deterministic, fail-closed) and edges line (`uncited → END`); 696 words / 93 lines.
- `docs/REQUIREMENTS.md` - JC-1 answer and SW-1 row corrected; E-13 linked, not restated.

## Decisions Made
- Used `fail-closed terminal (no gate/commit/card)` in the table to keep the row net-shorter while carrying the full terminal semantics.
- Kept the E-13 honesty statement out of `ARCHITECTURE.md` (no word headroom) and in `docs/REQUIREMENTS.md`, where it can link `EVALS.md` without a bound.
- Marked SW-1 🟡 rather than ✅ so the row does not read as if the measured E-13 failure had passed.

## Deviations from Plan

None - plan executed exactly as written.

## Stale-prose audit (Task 2c)

| Hit | Determination | Action |
| --- | --- | --- |
| `ARCHITECTURE.md:26` critic / retry once | FALSE | Fixed in `e8ae1eb` |
| `ARCHITECTURE.md:34` uncited → retry | FALSE | Fixed in `e8ae1eb` |
| `docs/REQUIREMENTS.md:89` `verify`/retry loop | FALSE | Fixed in `5bb8910` |
| `_EXTRACTION_MAX_ATTEMPTS` in `src/triagedesk/graph/nodes.py` and `tests/test_graph_recovery.py` | TRUE — the extraction retry still exists | Left unchanged |
| `SECURITY.md:48` retry cap; `SECURITY.md:82` retried write; `docs/DECISIONS.md:128` retry/replay | TRUE — extraction retry / idempotent commit | Left unchanged |
| `STATUS.md:153` planner/executor/critic | TRUE — records the deliberate rejection of a critic multi-agent | Left unchanged |
| `docs/assets/architecture.mmd:77` `N5 -. critic .-> QWEN` (and `P2 verify_priority` at :39) | FALSE — verify makes no model call and no such prompt exists | Deferred: generated SVG/PDF need an `npx` package install, forbidden by T-14-SC; logged in `deferred-items.md` |
| `.planning/` (other than this phase) | History | Left unchanged |

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The architecture and requirements prose now match `graph/nodes.verify` and `graph/build.route_after_verify`.
- `EVALS.md` and `evals/results/report.json` are untouched; the projection check (`emit_evals.py --check`) passes.
- Open follow-up: the architecture diagram source still shows the `critic` edge (see `deferred-items.md`).

---
*Phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai*
*Completed: 2026-11-05*

## Self-Check: PASSED
