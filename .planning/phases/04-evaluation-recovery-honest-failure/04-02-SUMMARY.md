---
phase: 04-evaluation-recovery-honest-failure
plan: 02
subsystem: testing
tags: [eval, fixtures, honest-failure, terminal-outcomes, fault-injection, stability, exit-code, held-out]

# Dependency graph
requires:
  - phase: 04-evaluation-recovery-honest-failure
    provides: "the tracer harness: CaseSpec/load_cases, Report/ReportCase + canonical writer, run_eval, the injected ToolMap + usage recorder"
provides:
  - "the honest 14-case fixture set (E-01..E-14) plus two held-out bounds (H-01/H-02)"
  - "first-class terminal outcomes (RECOVER/ABSTAIN/RECHECK) read from the graph's own channels"
  - "per-case E-12 fault injection exercising the real bounded retry and deterministic fallback"
  - "the runner exit-code gate: a non-declared accuracy miss or colour/matched-set instability is non-zero"
  - "the seven-behaviour suite proof (tests/test_eval_suite.py)"
affects: [04-03, 04-04]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 10649
  tasks: 3
  commits: 3
  plan_head_before: 724a5f9d1f62f599978fd190594269cfd13ea708
  plan_head_after: f02f6dc3b62207a28aea879e9ec21f870f89f29a

# Tech tracking
tech-stack:
  added: []  # no new dependency; every import already pinned (SAFE-04, T-04-SC)
  patterns:
    - "first-class outcome mapping read from the graph terminal channels (recovery/escalation/second_look), never a re-derived colour"
    - "declared per-case fault injection wrapping the injected normalize callable, torn down with the case's tool mapping"
    - "accuracy verdict = every run's outcome equals expected AND colour + matched-set are stable"

key-files:
  created:
    - evals/cases/E-01.yaml
    - evals/cases/E-03.yaml
    - evals/cases/E-04.yaml
    - evals/cases/E-05.yaml
    - evals/cases/E-06.yaml
    - evals/cases/E-07.yaml
    - evals/cases/E-08.yaml
    - evals/cases/E-09.yaml
    - evals/cases/E-10.yaml
    - evals/cases/E-11.yaml
    - evals/cases/E-12.yaml
    - evals/cases/E-13.yaml
    - evals/cases/E-14.yaml
    - evals/cases/H-01.yaml
    - evals/cases/H-02.yaml
    - tests/test_eval_suite.py
  modified:
    - src/triagedesk/evals/case.py
    - src/triagedesk/evals/runner.py
    - src/triagedesk/evals/tools.py
    - src/triagedesk/evals/report.py
    - tests/test_eval_tracer.py

key-decisions:
  - "Terminal outcomes are read from the graph's own channels (escalation -> ABSTAIN, recovery -> RECOVER, a second_look flag on a RECHECK case -> RECHECK); the scored colour is never re-derived (ORCH-05, D-01)"
  - "A case passes only when every run's outcome equals expected AND colour + matched-set are stable; the declared failure is an ALLOWED miss, reported as passed=false, never silently passed (D-04)"
  - "The exit code is non-zero for any non-declared accuracy miss OR any colour/matched-set instability; field instability is reported but does not gate (D-02, T-04-08)"
  - "The E-12 fault is declared as data (inject: tool_timeout + malformed_json) and wrapped onto the injected normalize callable per case per run, so it exercises the REAL bounded retry and is torn down between cases (Pitfall 13, T-04-09)"
  - "Every expected value is frozen from EVALS.md §4 through the published substrate; E-04 earns RED from the declared emergency-AVPU alias wording with no data/*.yaml edit (D-05, Pitfall 11)"
  - "The E-09 coverage gap is preserved: the matcher still returns no_match for its complaint, asserted directly against core.matcher (T-04-07)"

patterns-established:
  - "Fixture as declared data: previous_case, inject, held_out and declared_failure live on CaseSpec, so a new case is a YAML edit (SOLID: O)"
  - "Outcome vocabulary (RECOVER/ABSTAIN/RECHECK) is harness vocabulary declared once in case.py, never a colour literal (CONVENTIONS §1)"
  - "Fault injection is a wrapper around the injected tool interface, so it needs no change to graph/ or mcp/ (SOLID: D)"

requirements-completed: [EVAL-01]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "All 14 declared cases E-01..E-14 exist as fixtures with a declared expected outcome and run 3x through the same graph interface"
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py#test_all_declared_and_held_out_cases_load"
        status: pass
      - kind: unit
        ref: "tests/test_eval_suite.py#test_expected_tokens_are_declared_and_fixtures_are_synthetic_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "E-09 ships as the declared, unfixed failure (declared_failure: true), recorded failing and never tuned green"
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py#test_exactly_one_declared_failure_is_recorded_failing"
        status: pass
      - kind: unit
        ref: "tests/test_eval_suite.py#test_matcher_returns_no_match_for_e09_and_a_match_for_held_out"
        status: pass
    human_judgment: false
  - id: D3
    description: "Two held-out cases bound the E-09 failure: both classify correctly and pass offline"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py#test_held_out_cases_pass_and_bound_the_failure"
        status: pass
    human_judgment: false
  - id: D4
    description: "RECOVER/ABSTAIN/RECHECK are measured as first-class outcomes (E-05, E-06, E-07) and write no queue row"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py#test_terminal_outcomes_are_first_class_and_write_no_queue_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "The E-12 injected fault exercises the graph's bounded retry and deterministic fallback, and does not leak into another case"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py#test_e12_injection_retries_once_and_never_leaks"
        status: pass
    human_judgment: false

# Metrics
duration: ~7min
completed: 2026-10-09
status: complete
---

# Phase 4 Plan 2: Honest 14-Case Evaluation & Held-Out Bounds Summary

**The tracer's one case expanded into the honest, published 14-case suite plus two held-out bounds: every case runs 3× through the same graph, RECOVER/ABSTAIN/RECHECK are first-class measured outcomes, E-09 ships failing on purpose, and the run exits 0 with only that declared miss — while any non-declared accuracy miss or colour/matched-set instability exits non-zero.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-10-09T18:50:54Z
- **Completed:** 2026-10-09T18:57:42Z
- **Tasks:** 3
- **Files modified:** 21 (16 created, 5 modified)

## Accomplishments

- Authored the complete fixture set: 13 new declared cases (E-01, E-03..E-14) plus two held-out
  cases (H-01/H-02), every `expected` frozen from EVALS.md §4 through the published substrate and
  every fixture carrying a `source` back to its EVALS.md row. `load_cases('evals/cases')` yields 16
  cases; exactly one carries `declared_failure: true` (E-09).
- Wired first-class terminal outcomes into the runner: the outcome is read from the graph's own
  channels (`escalation` → ABSTAIN, `recovery` → RECOVER, a `second_look` flag on a RECHECK case →
  RECHECK, otherwise the scored colour) — never a re-derived colour (ORCH-05). The offline run
  reports E-05 → RECOVER, E-06 → ABSTAIN, E-07 → RECHECK and E-12 → RECOVER.
- Implemented the E-12 fault as declared data (`inject: {tool_timeout, malformed_json}`) wrapped onto
  the injected `normalize_case` callable per case per run. The wrapper raises on the first call and
  returns malformed JSON on the second, so the graph's real bounded retry is exhausted and the
  deterministic fallback recovers the already-structured case — landing on RECOVER with no uncited
  priority. The proof counts exactly two calls and confirms a non-injected case is unaffected.
- Added the exit-code gate: any non-declared accuracy miss OR any colour/matched-set instability
  returns non-zero. The declared E-09 miss is an allowed failure, so the full offline run exits 0.
- Held-out cases bound the declared failure: H-01 (a vague complaint that still carries a
  retrievable discriminator) and H-02 (a chronic-condition presentation with explicit retrievable
  wording) both classify correctly and pass — the E-09 miss is not universal (D-04).
- Preserved the coverage gap honestly: `core.matcher.match_discriminators` still returns `no_match`
  for the E-09 complaint (asserted directly against the substrate, not the harness), so the gap was
  not tuned green (D-05, T-04-07). `data/*.yaml` is unchanged by this plan.

## Task Commits

Each task was committed atomically:

1. **Task 1: Honest 14-case fixtures + held-out bounds; extend the case loader** - `f11e4a6` (feat)
2. **Task 2: First-class outcomes, E-12 fault injection and the exit-code gate** - `7a9b1fc` (feat)
3. **Task 3: Honest-suite proof** - `f02f6dc` (test)

**Plan metadata:** `_pending_` (docs: complete plan)

_Note: no TDD tasks in this plan._

## Files Created/Modified

- `evals/cases/E-01.yaml` … `E-14.yaml` (13 new) - the declared fixtures; expected values derived
  from EVALS.md §4 through `data/sats_tews.yaml` + `data/sats_discriminators.yaml`
- `evals/cases/H-01.yaml`, `evals/cases/H-02.yaml` - the two held-out bounds (`held_out: true`)
- `src/triagedesk/evals/case.py` - `CaseSpec` gains `previous_case`, `inject` (`FaultInjection`),
  `held_out`; `declared_outcomes` already accepted the terminals (Plan 04-01)
- `src/triagedesk/evals/runner.py` - `_capture` reads the terminal channels; `_outcome` maps them to
  first-class outcomes; `_run_case` persists `outcomes`/`passed`; `run_eval` returns the gate exit code
- `src/triagedesk/evals/tools.py` - `_injected_normalize` wraps `normalize_case` with the declared fault
- `src/triagedesk/evals/report.py` - `ReportCase` gains `outcomes` + `passed`; both flow into the digest payload
- `tests/test_eval_suite.py` - the seven-behaviour suite proof
- `tests/test_eval_tracer.py` - the shared helper now asserts the expected exit code (see Deviations)

## Decisions Made

- Outcomes come from the graph's own terminals, never a re-scored colour — the runner reads
  `recovery`/`escalation`/`second_look` and the gate payload (ORCH-05, D-01).
- A case's accuracy verdict requires outcome==expected AND colour/matched-set stability; the declared
  failure is recorded `passed=false` and treated as an allowed miss (D-04, T-04-08).
- The E-12 fault is data on the fixture, not a harness special-case, so it is reviewable and cannot
  leak (Pitfall 13, T-04-09).
- E-04's RED is earned from the declared emergency-AVPU alias wording ("responds only to pain") in the
  golden complaint — no `data/*.yaml` edit and no expectation edit (D-05).
- E-11's derivation is documented in the fixture: `with_help` (1) + RR 24 (2) + HR 122 (2) + SBP 92 (1)
  = TEWS 6 → ORANGE, with the very-urgent trauma discriminator matched; the trauma TEWS point is not
  applied on top so the case stays at the published ORANGE rather than tipping to RED.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `src/triagedesk/evals/report.py` edited (not listed in `files_modified`)**
- **Found during:** Task 2 (outcome mapping)
- **Issue:** Task 2's action requires the outcome and pass/fail verdict to be persisted "on the
  `ReportCase`", but `ReportCase` lives in `report.py`, which the plan's `files_modified` list omitted.
  The runner cannot persist outcomes without extending the model.
- **Fix:** Added `outcomes: list[str | None]` and `passed: bool` to `ReportCase` and included `outcomes`
  in the `report_digest` payload (the digest seals the measured outcomes; `passed` is derived from
  fields already covered).
- **Files modified:** `src/triagedesk/evals/report.py`
- **Verification:** `tests/test_eval_suite.py` (7 passed), full suite (192 passed); the offline run
  exits 0 and the report carries `outcomes`/`passed` for every case.
- **Committed in:** `7a9b1fc` (Task 2)

**2. [Rule 1 - Bug] `tests/test_eval_tracer.py` updated for the new exit-code semantics**
- **Found during:** Task 2 (exit-code gate)
- **Issue:** The new gate makes an injected colour instability a non-zero failure (T-04-08), but the
  tracer's shared `_run_e02` helper asserted `code == 0` unconditionally, so
  `test_unstable_colour_is_recorded_not_averaged` would fail against the correct new behaviour.
- **Fix:** `_run_e02` gained an `expect_code` parameter (default 0); the unstable-colour test now
  expects 1 and also asserts `passed is False`. This is a direct consequence of the Task 2 change.
- **Files modified:** `tests/test_eval_tracer.py`
- **Verification:** `tests/test_eval_tracer.py` (6 passed); full suite (192 passed).
- **Committed in:** `7a9b1fc` (Task 2)

**3. [Rule 2 - Missing Critical] Added a seventh suite test proving the E-12 retry and non-leakage**
- **Found during:** Task 3 (suite proof)
- **Issue:** The plan's six behaviours assert E-12's outcome is RECOVER, but RECOVER is also what the
  golden case yields with no fault — the outcome alone does not prove the graph consumed its bounded
  retry. The plan's must-have ("proves the graph retries once") and T-04-09 (injection must not leak)
  both require an explicit proof.
- **Fix:** Added `test_e12_injection_retries_once_and_never_leaks`, which counts `normalize_case` calls
  (exactly 2 for E-12, exactly 1 for a non-injected case) via a wrapping tool factory.
- **Files modified:** `tests/test_eval_suite.py`
- **Verification:** the test passes; the offline run still exits 0.
- **Committed in:** `f02f6dc` (Task 3)

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 bug, 1 missing-critical) — all are direct
consequences of the plan's own requirements, no scope creep.
**Impact on plan:** The plan's intent is fully delivered; the only additions are the model fields the
runner must write and the one proof the must-haves require.

## Issues Encountered

- E-11's published vitals (HR 122, SBP 92, RR 24, walking/help) already sum to TEWS 6, so the
  very-urgent trauma discriminator cannot *raise* the colour; the discriminator is still retrieved and
  recorded, and the colour is the published ORANGE. The fixture comment documents the derivation. No
  expectation was weakened to make a colour pass.
- E-07 requires every scored parameter present on the current case (a missing vital routes to the
  recovery terminal before the recheck node), so the golden case carries a normal temperature, AVPU and
  mobility alongside the deteriorating serial vitals.

## User Setup Required

None - the suite runs fully offline (golden extractions; the real matcher, scorer, recheck and gated
commit run in-process). The real measured run with the local Ollama model remains 04-04's job.

## Known Stubs

None. The offline mode is the explicitly labelled deterministic CI path (`mode: offline`); the E-09
declared failure is an intentional, documented outcome, not a stub.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change at a trust boundary was
introduced. The plan's threat-register mitigations are implemented and asserted: T-04-06 (declared
`expected` tokens + `source`), T-04-07 (matcher `no_match` for E-09), T-04-08 (instability is a
recorded non-zero failure), T-04-09 (per-case injection, non-leak asserted), T-04-10 (synthetic-only
fixture scan), T-04-SC (no new dependency).

## Next Phase Readiness

- 04-03 (the invariant gate) can extend `run_eval`'s single return point: the exit-code computation is
  now one place, and every `ReportCase` already carries `outcomes`, `passed` and the three stability
  flags.
- 04-04 (error-direction split + measured report) can consume the same `ReportCase`: `expected` and
  `outcomes` are per case, so under-triage vs over-triage can be split without re-running.
- The committed `evals/results/report.json` is intentionally NOT written by this plan (only the
  transient offline report is produced); 04-04 owns the committed, REAL measured report.

---

*Phase: 04-evaluation-recovery-honest-failure*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 21 created/updated files exist on disk (16 new artifacts + 5 modified + this SUMMARY).
- All 3 task commits are ancestors of HEAD: `f11e4a6`, `7a9b1fc`, `f02f6dc`.
- `data/sats_tews.yaml` and `data/sats_discriminators.yaml` are unchanged since the plan base.
