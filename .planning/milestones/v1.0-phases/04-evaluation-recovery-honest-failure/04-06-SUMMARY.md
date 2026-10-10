---
phase: 04-evaluation-recovery-honest-failure
plan: 06
subsystem: testing
tags: [eval, honest-failure, abort, gate-delivery, langgraph, gap-closure, report-digest]

# Dependency graph
requires:
  - phase: 04-evaluation-recovery-honest-failure
    provides: the honest eval harness (report/runner/analysis/generator) and the TEWS-0 baseline citation (04-05)
  - phase: 03-graph-safety-gate
    provides: graph/nodes.verify fail-close and the approval-gate graph terminal behaviour
provides:
  - an abort-aware eval capture that distinguishes delivered-through-the-gate from aborted-at-END
  - a first-class ABORT outcome that can never be counted as a pass
  - terminal facts (delivered/routes/attempts) sealed in report_digest
  - a Gate delivery metric rendered by the generator from the report's own aborted count
  - a regenerated real measured evals/results/report.json + EVALS.md
affects: [evaluation-recovery-honest-failure, demo-docs-freeze]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 14352
  tasks: 3
  commits: 3

# Measured commit ledger (#3968, #4670) — read by verify-work's same-instrument reconciliation.
commits: 3
plan_head_before: d44c7d054469cc20c0dfe7778ec55ea248d4d235
plan_head_after: 834df01247a42309188804c417e6bf8ea885f893

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Terminal honesty: a colour is recorded as an outcome only when the run produced a handover card through the gate; a card-less END is the declared ABORT terminal"
    - "Sealed terminal facts: delivered/routes/attempts are covered by report_digest, so a flipped abort is detectable"
    - "Report-sourced publication: the Gate delivery cell is rendered by the generator from the report's own aborted count, never hand-entered"

key-files:
  created:
    - tests/test_eval_honest_terminal.py
  modified:
    - src/triagedesk/evals/case.py
    - src/triagedesk/evals/runner.py
    - src/triagedesk/evals/report.py
    - src/triagedesk/evals/analysis.py
    - scripts/emit_evals.py
    - EVALS.md
    - evals/results/report.json

key-decisions:
  - "ABORT_OUTCOME is harness vocabulary declared once in evals/case.py and deliberately excluded from declared_outcomes — a card-less run can never be a valid `expected` token, so it can never be a pass (G-2, T-04-26)."
  - "runner._capture reads the graph's OWN terminal channels (handover/route/attempt) rather than re-deriving them, so a delivered run is exactly one that produced a handover card (G-2)."
  - "runner._outcome returns ABORT for a colour-present-but-not-delivered run; the RECOVER/ABSTAIN/RECHECK precedence is unchanged, so terminal outcomes are unaffected."
  - "ReportCase.delivered/routes/attempts are sealed in report_digest (alongside outcomes), so a hand-edited report that flips an abort to a colour fails the digest recompute and is refused (T-04-27)."
  - "analysis.analyse counts ABORT outcomes on their own — never folded into the under/over direction split or the colour accuracy figure (T-04-26)."
  - "scripts/emit_evals.py renders the Gate delivery cell as (total - aborted_cases)/total strictly from the report; the report remains the sole source of every published number (EVAL-05, T-04-28)."
  - "The committed evals/results/report.json is a REAL measured run (mode real, 55068/6866 tokens) produced WITHOUT --offline; the declared E-09 failure and the honest E-04/E-07/E-13 misses stay visible and were NOT tuned (D-04, D-05, Pitfall 16)."

patterns-established:
  - "Honest terminal: delivered-through-the-gate vs aborted-at-END is first-class, sealed, and rendered"
  - "Sole-source metric: a new published metric (Gate delivery) is generated from the report, never typed"

requirements-completed: [EVAL-01, EVAL-05]

coverage:
  - id: D1
    description: "An aborted-at-END run (fail-closed verify) is recorded as ABORT with delivered:false, a non-zero attempt and passed:false — never a GREEN pass; the terminal facts are sealed in report_digest."
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_aborted_run_is_recorded_as_abort_not_a_pass"
        status: pass
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_abort_of_a_non_declared_case_exits_non_zero"
        status: pass
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_terminal_facts_are_sealed_in_the_digest"
        status: pass
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_delivered_run_records_its_colour_and_delivered"
        status: pass
    human_judgment: false
  - id: D2
    description: "The analysis names aborted cases and runs and EVALS.md renders a Gate delivery metric generated from the report's own aborted count; the generator stays idempotent and the report is the sole source."
    requirement: "EVAL-05"
    verification:
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_analysis_surfaces_aborted_cases_and_runs"
        status: pass
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_generator_renders_gate_delivery_from_the_report_and_is_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_eval_honest_terminal.py#test_aborted_case_is_rendered_failing"
        status: pass
      - kind: integration
        ref: "uv run python scripts/emit_evals.py --report evals/results/report.json --check (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The committed evals/results/report.json is a real measured run (mode real, non-zero tokens) regenerated into EVALS.md; the declared E-09 failure and honest E-04/E-07/E-13 misses stay visible."
    requirement: "EVAL-05"
    verification:
      - kind: integration
        ref: "uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json (no --offline; mode real; 55068/6866 tokens)"
        status: pass
      - kind: integration
        ref: "uv run python -c \"...assert mode==real and no ABORT run passed and delivered/routes present...\" (measured report honest)"
        status: pass
    human_judgment: false

# Metrics
duration: 21min
completed: 2026-10-09
status: complete
---

# Phase 4 Plan 6: Honest terminal (delivered vs aborted-at-END) & regenerated measured EVALS Summary

**The eval harness now records whether each run actually delivered a handover card through the approval gate or aborted at END — a card-less fail-close is the first-class `ABORT` outcome, never a passing colour — and EVALS.md is regenerated from a fresh real measured run that keeps the declared E-09 failure and every honest miss visible.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-10-09T20:56:21Z
- **Completed:** 2026-10-09T21:18:17Z
- **Tasks:** 3
- **Files modified:** 8 (1 created, 7 modified)

## Accomplishments

- **Gap G-2 closed:** `runner._capture` now reads the graph's OWN terminal facts (`handover`, `route`, `attempt`) and `runner._outcome` records a colour **only when the run delivered a handover card through the gate**. A run that fail-closes at `verify` → `END` (no card, no gate, no commit) is the declared `ABORT` outcome — it can no longer masquerade as a GREEN pass.
- **The abort is first-class and sealed:** `ABORT_OUTCOME` is declared once in `evals/case.py` and deliberately excluded from `declared_outcomes`, so it can never be a valid `expected` token. `ReportCase.delivered`/`routes`/`attempts` are sealed in `report_digest`, so a hand-edited report that flips an abort to a colour fails the digest recompute and is refused by the generator (T-04-27).
- **`Gate delivery` metric published:** `analysis.analyse` names the aborted cases and counts their runs on their own (never folded into the under/over direction split or the colour accuracy figure), and `scripts/emit_evals.py` renders a `Gate delivery` cell strictly from the report's own aborted count. EVALS.md §3 carries the hand-written narrative row; the generator fills its Measured cell (EVAL-05).
- **The published artefact is a real measured run:** `evals/results/report.json` was re-run WITHOUT `--offline` against `qwen2.5:1.5b` (Ollama 0.30.6) — `mode: real`, 55068/6866 tokens — and EVALS.md was regenerated from it. The declared **E-09** failure and the honest **E-04/E-07/E-13** misses stay visible; nothing was tuned to force a green run (D-04, D-05, Pitfall 16).
- **E-08 now delivers:** the routine all-normal-vitals case (G-1 closed by 04-05) reaches the gate and delivers a sourced GREEN card (`delivered: true`); the measured run records **zero aborts** (`Gate delivery 16/16`), and the honesty mechanism guarantees any future card-less run would be surfaced as an abort.

## Task Commits

Each task was committed atomically:

1. **Task 1: Record the true terminal: delivered vs aborted-at-END** - `ce01d5b` (feat)
2. **Task 2: Surface the abort signal in the analysis and render a Gate delivery metric** - `1d28a3d` (feat)
3. **Task 3: Re-run the measured evaluation and regenerate EVALS.md from the honest report** - `834df01` (feat)

**Plan metadata:** (docs commit, below)

## Files Created/Modified

- `src/triagedesk/evals/case.py` - declares `ABORT_OUTCOME`, excluded from `declared_outcomes` (never a valid expectation)
- `src/triagedesk/evals/runner.py` - `_capture` reads `handover`/`route`/`attempt`; `_outcome` maps a card-less END to `ABORT`; `_run_case` populates `delivered`/`routes`/`attempts`
- `src/triagedesk/evals/report.py` - `ReportCase` gains `delivered`/`routes`/`attempts` (sealed in `_digest_payload`); `Analysis` gains `aborted_cases`/`aborted_count`
- `src/triagedesk/evals/analysis.py` - counts `ABORT` outcomes on their own, excluded from the direction split and accuracy
- `scripts/emit_evals.py` - renders the `Gate delivery` cell from the report's own aborted count (sole writer)
- `EVALS.md` - §3 gains the `Gate delivery` narrative row; result cells regenerated from the new report
- `evals/results/report.json` - the real measured run carrying the honest terminal facts
- `tests/test_eval_honest_terminal.py` - 7 proofs: abort ≠ pass, delivered colour, non-zero exit, sealed digest, analyser surface, generator render/idempotence, aborted case rendered failing

## Decisions Made

- `ABORT_OUTCOME` is harness vocabulary declared once in `evals/case.py` and NOT added to `declared_outcomes` — a card-less run can never be a valid expectation, so it can never pass (G-2, T-04-26).
- `_capture` reads the graph's own terminal channels (`handover`/`route`/`attempt`), never re-deriving them; a delivered run is exactly one whose `handover` card exists (G-2).
- `_outcome` returns `ABORT` only for a colour-present-but-not-delivered run; the RECOVER/ABSTAIN/RECHECK precedence is unchanged, so terminal outcomes are unaffected.
- `delivered`/`routes`/`attempts` are sealed in `report_digest`, so a hand-edit that flips an abort to a colour is detectable and refused (T-04-27).
- The `Gate delivery` cell is generated as `(total - aborted_cases)/total` strictly from the report; the report remains the sole source of every published number (EVAL-05, T-04-28).
- The measured run was produced WITHOUT `--offline`; every miss (declared E-09 plus honest E-04/E-07/E-13) is recorded as-is and never tuned to green (D-04, D-05).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The repository's `main` branch is a protected branch, but this project uses `branching_strategy: none` with worktree isolation disabled and all prior Phase-4 plan commits live on `main`. Per the established project practice (04-05), the three task commits were made on `main`. No phase branch was created.
- The real measured run exited non-zero (gate fails) by design: E-04 (unstable colour), E-07 (RECHECK→RECOVER), and E-13 (injection→ABSTAIN) are honest non-declared misses, and E-09 is the declared failure. This is the expected honest outcome, not a defect; the report and EVALS.md show all four as failures.

## User Setup Required

None - no external service configuration required. (The Task-3 precondition — a reachable Ollama server with `qwen2.5:1.5b` pulled — was confirmed before the measured run.)

## Known Stubs

None. No placeholder values, TODOs, or unwired data paths were introduced. The `Gate delivery` metric is rendered from the report's real aborted count, and the terminal facts are genuine graph channels.

## Threat Flags

None. The change introduces no new network endpoint, auth path, file-access pattern, or schema change at a trust boundary — it is an honest-terminal capture, two sealed report fields, one generated metric, and a re-run of the existing harness.

## Verification

- `uv run pytest tests/test_eval_honest_terminal.py tests/test_eval_report.py -x` — **14 passed** (Task 2).
- Full suite `uv run pytest -q` — **219 passed** (was 212; +7 new honest-terminal proofs).
- `uv run ruff check` — All checks passed.
- `uv run mypy src/triagedesk/evals/` — Success, no issues (8 source files).
- Measured run `uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json` (no `--offline`) — `mode: real`, tokens 55068/6866, `aborted_count: 0`, `Gate delivery 16/16`; `gate.passed: false` with `unexpected_failures [E-04, E-07, E-13]` and the declared E-09 under-triage.
- Honest-report assertion — `mode == 'real'`, no `ABORT` run passed, every case carries `delivered`/`routes` → `measured report honest`.
- `uv run python scripts/emit_evals.py --report evals/results/report.json --check` — exit 0 (EVALS.md == generated output; `report_digest ea5ac20d…`).

## Next Phase Readiness

- Gap G-2 is closed: the eval harness distinguishes a delivered card from an aborted-at-END run, seals the terminal facts, and can never report a card-less fail-close as a passing colour.
- The published EVALS.md is regenerated from a real measured run with the declared failure and all honest misses visible; the report is the sole source of every number.
- Phase 5 (Demo, Docs & Freeze) can publish the honest measured evaluation as-is.

---

*Phase: 04-evaluation-recovery-honest-failure*
*Completed: 2026-10-09*

## Self-Check: PASSED

- `tests/test_eval_honest_terminal.py` — FOUND
- `evals/results/report.json` (mode real, aborted_count 0) — FOUND
- Commit `ce01d5b` — FOUND (ancestor of HEAD)
- Commit `1d28a3d` — FOUND (ancestor of HEAD)
- Commit `834df01` — FOUND (ancestor of HEAD)
