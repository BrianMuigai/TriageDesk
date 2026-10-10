---
phase: 02-deterministic-scorer-own-mcp-server
plan: 03
subsystem: core
tags: [python, pydantic, mcp, sats, recheck, approval-gate, closed-set, dry]

# Dependency graph
requires:
  - phase: 02-deterministic-scorer-own-mcp-server
    provides: "core/scorer.py score_priority, core/matcher.py closed-set ids + match_discriminators, PriorityResult/MatchResult contracts, mcp/server.py tool seam"
provides:
  - "core/recheck.py — the pure serial-vitals comparison (deterioration = a move to a higher-points TEWS band)"
  - "RecheckFlag/VitalChange + ApprovalToken/CommitResult contracts in the one schema module (D-07, D-08)"
  - "core/scorer.band_points() — the ONE band-selection authority reused by the recheck (DRY)"
  - "mcp/server.py exposes the remaining tools: contract-validated normalize_case, raise_recheck_flag, and the gated commit_priority stub"
  - "the completed five-tool owned surface (normalize_case, match_discriminators, score_priority, raise_recheck_flag, commit_priority)"
  - "tests/test_recheck.py + tests/test_mcp_tools.py — the recheck/tool-contract proof suite"
affects: [phase-3, phase-4]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 48000, raw_tokens: 33000).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 5746        # chars/4 over the realized diff (22987 chars, src + tests)
  raw_tokens: 5746    # same — nothing generated in this plan
  tasks: 3
  commits: 3
  plan_head_before: 9a9c06f5bd17700c3482a35ce4a59f97c35b3cb3
  plan_head_after: 4adb74123c5add59b86497e8ed968be9d6de5ebd

tech-stack:
  added: []
  patterns:
    - "Model-output constraining: model-returned discriminator ids are filtered to the closed set; unknown ids dropped, never trusted"
    - "Single band-selection authority: core.scorer.band_points() is reused by the recheck so deterioration direction is data-derived, not duplicated"
    - "Serial-vitals second look: a move to a higher-points TEWS band is a deterioration; the result carries before/after values and no colour"
    - "Gated stub: the only queue-affecting tool validates an approval-token shape and refuses without it, writing nothing (real gate is Phase 3)"

key-files:
  created:
    - src/triagedesk/core/recheck.py
    - tests/test_recheck.py
    - tests/test_mcp_tools.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/core/matcher.py
    - src/triagedesk/core/scorer.py
    - src/triagedesk/mcp/server.py
    - tests/test_mcp_server.py

key-decisions:
  - "normalize_case filters model-returned ids through core.matcher.validate_discriminator_ids — the ONE closed-set authority — so the server contract and the model contract cannot drift (D-09, T-02-11)."
  - "A missing vital stays None on the normalize path (never imputed); no_discriminator_matched is derived as `not ids` so an all-unknown model output is reported honestly."
  - "Deterioration direction is derived from data, not thresholds: the recheck compares the TEWS band points of the before/after value, so a move to a higher-points band is a deterioration (D-08)."
  - "The recheck reuses core.scorer.band_points() rather than re-deriving band selection, keeping one band-selection authority (CONVENTIONS §1/§2, DRY/SOLID)."
  - "RecheckFlag deliberately has no colour/target/destination field: the second look can never re-classify (D-08, T-02-10)."
  - "commit_priority validates ApprovalToken (named approver + role + decision in approve|edit|dismiss + timestamp) and refuses a missing/malformed token; it performs no store write and never fakes a commit (D-07, T-02-09)."

patterns-established:
  - "Closed-set constraining is a matcher responsibility, applied by the tool that consumes model output"
  - "The queue-affecting tool is the ONLY one gated; every other tool stays read-only and narrow (SOLID: I)"
  - "A contract-typed tool is a thin adapter over a pure core/ function; the stub returns a typed refusal rather than raising"

requirements-completed: [TOOL-01, TOOL-04, TOOL-05]

coverage:
  - id: D1
    description: "normalize_case returns the shared ExtractionResult with discriminator ids constrained to the closed set (unknown ids dropped) and missing vitals left None."
    requirement: "TOOL-01"
    verification:
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_normalize_case_drops_unknown_and_keeps_valid_ids"
        status: pass
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_normalize_case_leaves_a_missing_vital_none"
        status: pass
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_normalize_case_reports_no_match_when_all_ids_are_unknown"
        status: pass
    human_judgment: false
  - id: D2
    description: "raise_recheck_flag returns a second-look flag with before/after vitals for any deterioration, reports no flag for a stable case, never reports an improvement as deterioration, and carries no colour."
    requirement: "TOOL-04"
    verification:
      - kind: unit
        ref: "tests/test_recheck.py"
        status: pass
      - kind: unit
        ref: "tests/test_recheck.py#test_owned_server_exposes_the_raise_recheck_flag_tool"
        status: pass
    human_judgment: false
  - id: D3
    description: "commit_priority refuses any call without a well-formed approval token, accepts a well-formed token without committing, and performs no queue/store write on any path."
    requirement: "TOOL-05"
    verification:
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_commit_priority_refuses_without_a_token"
        status: pass
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_commit_priority_refuses_a_malformed_token"
        status: pass
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_commit_priority_path_imports_no_store"
        status: pass
    human_judgment: false
  - id: D4
    description: "The owned server exposes the completed five-tool surface as a superset."
    requirement: "TOOL-01"
    verification:
      - kind: unit
        ref: "tests/test_mcp_server.py#test_owned_server_lists_normalize_case_and_grows_its_tool_surface"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-09
status: complete
---

# Phase 2 Plan 03: Remaining Owned Tools Summary

**The owned server completes its five-tool surface: `normalize_case` now constrains model-returned discriminator ids to the closed set, a pure `raise_recheck_flag` turns serial vitals into a before/after second-look flag (never a colour), and a gated `commit_priority` stub refuses any call without a well-formed approval token and writes nothing.**

## Performance

- **Duration:** ~10 min (15:03:35Z → 15:13Z)
- **Started:** 2026-10-09T15:03:35Z
- **Completed:** 2026-10-09T15:13:00Z
- **Tasks:** 3/3
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- **The model can no longer smuggle an id (D-06, T-02-11).** `normalize_case` runs the model extraction, then filters `matched_discriminator_ids` through `core.matcher.validate_discriminator_ids` — the ONE closed-set authority — dropping any id not declared in `data/sats_discriminators.yaml`. An all-unknown output sets `no_discriminator_matched`; a missing vital stays `None` (never imputed); the payload still validates back to the shared `ExtractionResult`.
- **Serial vitals now yield a second look, not a re-score (D-08, TOOL-04, T-02-10).** `core/recheck.py` compares the TEWS band points of the previous and current value for every scored parameter; a move to a *higher-points* band is a deterioration. The `RecheckFlag` carries the before/after value and band points per vital — and deliberately has **no colour field**, so it can never re-classify or reorder a patient.
- **Deterioration direction is data-derived, not hard-coded.** The recheck reuses `core.scorer.band_points()` — the single band-selection authority — so the same inclusive bands/thresholds from `data/sats_tews.yaml` drive both scoring and rechecking; the DRY guard stays green.
- **The queue-affecting tool is gated and inert (D-07, TOOL-05, T-02-09).** `commit_priority` validates the `ApprovalToken` shape (named approver + role + decision in `approve|edit|dismiss` + timestamp) and refuses (`refused=True`) a missing or malformed token. It performs **no store write on any path** and never fakes a commit — the real LangGraph `interrupt()` gate and idempotent content-hash commit are Phase 3 (GATE-01..04).
- **The five-tool contract is machine-verified.** `tests/test_mcp_server.py` asserts the surface as a superset `>= {normalize_case, match_discriminators, score_priority, raise_recheck_flag, commit_priority}` — SC3's "all five tools" claim is now checked in code while still allowing growth.

## Task Commits

Each task was committed atomically:

1. **Task 1: Contract-validated normalize_case with closed-set discriminator ids** - `6f65772` (feat)
2. **Task 2: Pure raise_recheck_flag over serial vitals (never re-classifies)** - `9c51d7c` (feat)
3. **Task 3: Gated commit_priority stub that refuses without an approval token** - `4adb741` (feat)

**Plan metadata:** committed together with this SUMMARY, STATE.md and WINDOWS.md (docs: complete plan)

## Files Created/Modified

- `src/triagedesk/core/recheck.py` — the pure `compare_vitals(previous, current) -> RecheckFlag` (data-derived deterioration, before/after detail, no colour)
- `src/triagedesk/core/schema.py` — added `VitalChange`, `RecheckFlag` (D-08) and `ApprovalToken`, `CommitResult` (D-07)
- `src/triagedesk/core/matcher.py` — added `validate_discriminator_ids()` (the closed-set constraining authority)
- `src/triagedesk/core/scorer.py` — added `band_points()` (the shared band-selection authority reused by the recheck)
- `src/triagedesk/mcp/server.py` — constrained `normalize_case`; added `raise_recheck_flag` and the gated `commit_priority` stub
- `tests/test_mcp_tools.py` — normalize (closed-set/None/no-match) and commit (refused/accepted/no-store/listed) contract tests
- `tests/test_recheck.py` — deterioration, stable follow-up, improvement, no-colour contract, determinism, owned-tool tests
- `tests/test_mcp_server.py` — tool-surface test tightened to the completed five-tool superset

## Decisions Made

- **Closed-set constraining belongs to the matcher, applied by the tool.** `validate_discriminator_ids` is the single filter; the server calls it rather than re-implementing the closed set (DRY, SOLID: S/D).
- **`no_discriminator_matched` is derived (`not ids`).** An all-unknown model output is reported honestly as a coverage gap rather than silently passing ids downstream.
- **Deterioration = a move to a higher-points band, read from data.** No threshold is inlined; the recheck reuses the scorer's band selection so the two paths cannot disagree.
- **The recheck contract has no colour.** The absence of the field is the structural guarantee that a second look never re-classifies (T-02-10).
- **The commit stub returns a typed refusal, not an exception.** A missing or malformed token yields `CommitResult(refused=True, committed=False, reason=...)`, so a caller always sees an explicit, auditable refusal and can never mistake the stub for a write.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `core.scorer.band_points()` so the recheck does not duplicate band selection**
- **Found during:** Task 2 (raise_recheck_flag)
- **Issue:** The plan's Task-2 file list did not include `core/scorer.py`, but the recheck needs the *band points* of a vital to decide whether it deteriorated. Re-implementing band selection in `core/recheck.py` would duplicate the one band-selection algorithm (CONVENTIONS §1/§2 — DRY/SOLID, iron-clad).
- **Fix:** Added a small public wrapper `band_points(param, value) -> int` in `core/scorer.py` over the existing `_select_band`, and imported it in `core/recheck.py`. It is behaviour-preserving (the scorer's own loop is untouched) and makes the band-selection logic a single authority.
- **Files modified:** `src/triagedesk/core/scorer.py`, `src/triagedesk/core/recheck.py`
- **Verification:** `tests/test_recheck.py` (6 tests) pass; `tests/test_purity.py` + `tests/test_no_duplicated_sats.py` remain green; full suite green.
- **Committed in:** `9c51d7c` (Task 2)

---

**Total deviations:** 1 auto-fixed (1 missing critical — DRY/single-authority)
**Impact on plan:** The change is minimal and additive; it preserves the iron-clad DRY rule by avoiding a duplicated band-selection path. No scope creep — no behaviour outside the recheck changed.

## Known Stubs

- **`commit_priority` is a gated stub** (`src/triagedesk/mcp/server.py`): it validates the approval-token shape and refuses without one, but performs no queue/store write and never sets `committed=True`. This is the **locked Phase-2 scope** (D-07), not an incomplete implementation — the real LangGraph `interrupt()` gate, idempotent content-hash commit and queue write are Phase 3 (GATE-01..04, TOOL-06). Recorded in `.planning/WINDOWS.md`.

## Issues Encountered

- **Task 2 is marked `tdd="true"`.** The RED state was a genuine collection failure (the `recheck` module and `RecheckFlag` contract did not exist); the GREEN state followed the implementation. Because the plan is `type: execute` and `workflow.tdd_mode` is disabled, the plan-level RED/GREEN commit gate is not enforced; Task 2 shipped as one atomic feat commit (implementation + tests), consistent with Plan 02-02's task commits. No `## TDD Gate Compliance` violation is recorded.
- Pre-existing ruff findings in `src/triagedesk/llm/prompts.py` (E501) and pre-existing mypy findings in `core/rules.py` (missing `types-PyYAML`) and `mcp/adapter.py` (`dict` type-arg) are outside this plan's scope and were left untouched.

## User Setup Required

None - no external service configuration required. (No package installs occurred; the reserved package-legitimacy gate stays in force for any future install.)

## Next Phase Readiness

- **For Phase 3 (graph wiring + the real gate):** the owned server now exposes all five contracted tools as narrow, contract-typed seams. `commit_priority` is the single queue-affecting tool and is already gated — Phase 3 replaces the stub with the LangGraph `interrupt()` gate, idempotent content-hash commit and the queue write (GATE-01..04, TOOL-06). `raise_recheck_flag` gives the graph a pure second-look signal with no colour.
- **For Phase 4 (evaluation):** `normalize_case`'s closed-set constraining and the recheck's data-derived deterioration are deterministic, model-free behaviours the evaluation can pin run-to-run.
- **Carried forward:** the borrowed `mcp-sqlite` handshake (Phase 1 risk) remains open; the DRY + SOLID iron-clad rule stays in force for every later phase.

---

*Phase: 02-deterministic-scorer-own-mcp-server*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 8 key files exist on disk (recheck, schema, matcher, scorer, server, 3 test files).
- All 3 plan commits are ancestors of HEAD: `6f65772`, `9c51d7c`, `4adb741`.
- Full suite green: `uv run pytest -q` → 116 passed; `uv run python scripts/spike_score.py` → exit 0.
- Guards green: `tests/test_purity.py`, `tests/test_no_duplicated_sats.py` pass (recheck is pure; no SATS value inlined under `src/`).
