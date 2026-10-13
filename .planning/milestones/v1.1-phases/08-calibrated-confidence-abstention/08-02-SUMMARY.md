---
phase: 08-calibrated-confidence-abstention
plan: 02
subsystem: evals
tags: [deferral, calibration, risk-coverage, ece, eval-harness, honest-reporting]

requires:
  - phase: 08-calibrated-confidence-abstention
    provides: the deterministic `confidence` signal, the `assess` node and the deferral terminals (Plan 01) that this plan measures
  - phase: 04-evaluation-harness
    provides: the offline eval runner/report/analysis, the executable invariants, and the sole-source EVALS projection this plan extends

provides:
  - "`evals/report.py`: per-case `held_out`/`confidence_levels`/`deferrals`/`confidence_satisfied`; `RiskCoveragePoint` + `Calibration`; `Analysis.deferral_*` + `Analysis.calibration`"
  - "`evals/analysis.py`: the separate deferral tally and the declared-split calibration (ECE + risk–coverage, both n's named, small-sample caveat)"
  - "`evals/runner.py`: the graph `confidence` capture, the E-07 recheck-finding precedence, and the deferral-aware gate"
  - "the measured-consequence updates to every existing test whose outcome moves under D8-11"
affects: [08-calibrated-confidence-abstention, 10-desk-ux, 11-honest-evaluation, 12-milestone-close]

actuals:
  tokens: 9795
  tasks: 3
  commits: 3
  plan_head_before: a01497384739ae6bb4a9651aebf611cf9a0b6a08
  plan_head_after: 7aed8e98528776ed52ef7e1ab4a8bf6b7d129379

tech-stack:
  added: []
  patterns:
    - "Honest abstention accounting: a deferral is reported as reduced COVERAGE (its own rate/cases), never folded into the accuracy figure"
    - "Deferral-aware gate: an all-deferred non-declared case leaves unexpected_failures, but a wrong colour can never be excluded"
    - "Declared-split calibration: ECE + risk–coverage over an internal ordinal scalar confined to evals/, with both sample sizes named"

key-files:
  created: []
  modified:
    - src/triagedesk/evals/report.py
    - src/triagedesk/evals/analysis.py
    - src/triagedesk/evals/runner.py
    - tests/test_eval_report.py
    - tests/test_eval_suite.py
    - tests/test_scorer_baseline.py
    - tests/test_eval_honest_terminal.py
    - tests/test_eval_invariants.py
    - tests/test_demo.py

key-decisions:
  - "The deferral rate is derived from the report's own per-run `deferrals` (count / reached-assess runs), reported SEPARATELY from the under/over direction split (D8-10, D8-16)."
  - "Calibration is declared by the existing `held_out` flag: calibration E-01…E-14 (n=14) vs held-out H-01/H-02 (n=2); both n's are named and the caveat states the small-sample limit (D8-13, D8-15)."
  - "The internal ordinal scalar (`confidence_satisfied`) lives ONLY in evals/; ECE normalises it by the confidence contract's component count (a named constant) and is never presented as a validated probability (D8-04, A2)."
  - "The gate excludes a case from `unexpected_failures` ONLY when every run deferred; a wrong colour (any False/None deferral) is never excluded, and the moved cases stay visible in `Analysis.deferral_cases` (T-08-07)."
  - "`_outcome` surfaces a raised `second_look` RECHECK before the escalation collapse, preserving E-07's deterministic recheck while it also defers (semantic precedence, not a tuned exception)."
  - "`_digest_payload` is deliberately untouched: the committed `report.json` still recomputes, and Plan 03 seals the new per-case facts in the SAME change as the regeneration."

patterns-established:
  - "Reduced-coverage accounting: a deferral is a coverage fact (rate/cases), never an answered-but-wrong run."
  - "An exclusion from the gate must be provably unable to hide a wrong colour and must never be silent."

requirements-completed: [AGENT-02]

coverage:
  - id: D1
    description: "The report carries per-case deferral facts and an aggregate deferral rate, next to (never inside) the outcome breakdown (D8-10, D8-16)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_deferral_rate_and_declared_split_calibration_are_measured"
        status: pass
      - kind: integration
        ref: "tests/test_eval_suite.py#test_terminal_outcomes_are_first_class_and_write_no_queue_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "Calibration (ECE + risk–coverage) is measured on a declared split with n named and the small-sample caveat explicit (D8-13, D8-15)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_deferral_rate_and_declared_split_calibration_are_measured"
        status: pass
    human_judgment: false
  - id: D3
    description: "The internal ordinal scalar stays inside evals/ — never in core/schema.py, never in the tool output, never a percentage shown as clinical risk (D8-04, A2)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_bare_models_and_a_report_without_analysis_construct"
        status: pass
      - kind: unit
        ref: "tests/test_confidence.py#test_contract_carries_no_float_or_probability_field"
        status: pass
    human_judgment: false
  - id: D4
    description: "A coverage deferral is surfaced (never silently excused); a wrong colour is never excluded from unexpected_failures (T-08-07)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py#test_deferral_gate_excludes_a_covered_run_but_never_a_wrong_colour"
        status: pass
      - kind: integration
        ref: "tests/test_eval_suite.py#test_terminal_outcomes_are_first_class_and_write_no_queue_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "E-09 is recorded as a deferral/terminal with no queue row, remains passed=False, and stays the sole declared_failure; the run still exits 0."
    requirement: "AGENT-02"
    verification:
      - kind: integration
        ref: "tests/test_eval_suite.py#test_exactly_one_declared_failure_is_recorded_failing"
        status: pass
    human_judgment: false
  - id: D6
    description: "E-07's deterministic RECHECK outcome is preserved while the case also defers."
    requirement: "AGENT-02"
    verification:
      - kind: integration
        ref: "tests/test_eval_suite.py#test_terminal_outcomes_are_first_class_and_write_no_queue_row"
        status: pass
      - kind: integration
        ref: "tests/test_demo.py#test_deterioration_beat_reaches_raise_recheck_flag"
        status: pass
    human_judgment: false
  - id: D7
    description: "Every existing test whose measured outcome moves under D8-11 is updated to the honest deferral expectation (no fixture/override tuned)."
    requirement: "AGENT-02"
    verification:
      - kind: integration
        ref: "tests/test_scorer_baseline.py#test_e08_defers_to_a_safe_terminal_and_never_reaches_the_gate"
        status: pass
      - kind: integration
        ref: "tests/test_eval_honest_terminal.py#test_deferred_case_records_a_terminal_and_no_delivery"
        status: pass
      - kind: integration
        ref: "tests/test_eval_invariants.py#test_e14_suppression_leaves_the_colour_unchanged_and_the_finding_cited"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-12
status: complete
---

# Phase 8 Plan 02: Calibrated Confidence & Abstention Summary

**The offline eval harness now measures the deferral honestly: per-case deferral facts, a separate deferral rate, a declared-split ECE / risk–coverage block, a deferral-aware gate that can never hide a wrong colour, and every moved test updated to the real outcome — 295 passed, 0 failed.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-10-12T16:13:29Z (last commit)
- **Tasks:** 3
- **Files modified:** 9 (3 source, 6 test)

## Accomplishments

- Extended `ReportCase` with the per-run coverage-signal captures (`confidence_levels`/`deferrals`/`confidence_satisfied`) and `held_out`, and added `RiskCoveragePoint` + `Calibration` models plus `Analysis.deferral_*` / `Analysis.calibration` — all additive and defaulted (D8-10, D8-13, D8-16).
- Taught `analyse` to tally the deferral rate SEPARATELY from the direction split and to build the declared-split calibration: `n_calibration=14` / `n_held_out=2`, a risk–coverage sweep over the deterministic rank, a 4-bin ECE and an explicit small-sample caveat (observed `deferral_rate≈0.462`, `deferral_cases=[E-01,E-07,E-08,E-09,E-13,E-14]`, `ece≈0.227`).
- Captured the graph's OWN `confidence` channel in the runner (never re-derived), derived the three per-run lists, and passed `held_out` through (D8-08, T-08-08).
- Made the gate deferral-aware: an all-deferred non-declared case leaves `unexpected_failures` (reduced coverage ≠ a wrong answer), while a wrong colour with any `False`/`None` deferral is never excluded — pinned by a focused gate test (T-08-07).
- Preserved E-07's deterministic RECHECK by surfacing a raised `second_look` flag ahead of the escalation collapse in `_outcome`, while E-07 still counts as a deferral (D8-11).
- Updated every previously-red test to the honest outcome: E-01/E-08/E-09/E-13/E-14 move to an `ABSTAIN` deferral terminal, E-07's RECHECK and demo beat are preserved, E-14's colour/citation are unchanged — no fixture, threshold or override was touched.
- Confirmed `tests/test_graph_tracer.py` and `tests/test_observability.py` are unaffected (matched cases; superset/subset assertions) and deliberately left them unmodified.

## Task Commits

Each task was committed atomically:

1. **Task 1: Report contract + analyser** - `4c9fcb9` (feat)
2. **Task 2: Runner capture + recheck precedence + deferral-aware gate** - `477753c` (feat)
3. **Task 3: Update every existing test whose measured outcome moves** - `7aed8e9` (test)

**Plan metadata:** not committed — `commit_docs: false` in this workspace (see below).

_Note: not a TDD plan; each task is one commit._

## Files Created/Modified

- `src/triagedesk/evals/report.py` - `ReportCase` deferral/held-out fields; `RiskCoveragePoint`, `Calibration`; `Analysis.deferral_*` + `calibration`. `_digest_payload` untouched.
- `src/triagedesk/evals/analysis.py` - separate deferral tally; `_risk_coverage`, `_expected_calibration_error`, `_calibration`.
- `src/triagedesk/evals/runner.py` - `confidence` capture; per-run deferral lists; `_outcome` recheck precedence; deferral-aware `_build_gate`.
- `tests/test_eval_report.py` - deferral/calibration contract proofs + the nested-`default_factory` bare-construction proof.
- `tests/test_eval_suite.py` - E-09/E-07/E-01 deferral expectations, the moved-case surfacing guard, and the focused gate test.
- `tests/test_scorer_baseline.py` - E-08 reworked to the honest deferral; the TEWS-0 citation contract stays proven at the scorer level.
- `tests/test_eval_honest_terminal.py` - delivered-run proof moved to E-02; explicit E-08 deferral terminal.
- `tests/test_eval_invariants.py` - E-14 colour/citation unchanged; the case now defers.
- `tests/test_demo.py` - the escalation beat reaches `assess_confidence` (five tools); E-07's recheck beat preserved.

## Decisions Made

- Deferral rate = `deferral_count / deferral_runs` where a run counted only when it reached `assess` (non-`None` deferral); the ternary `signal["deferral"] if signal is not None else None` is deliberate — a literal `or None` would fold a reached-but-non-deferring run into `None` and skew the rate.
- ECE normalises the internal scalar by the confidence contract's component count (a named `_COMPONENT_COUNT = 4` constant in `evals/analysis.py`); the scalar never leaves `evals/` and ECE is never a clinical probability (D8-04, A2). Binning is the plan's discretion (`_ECE_BINS = 4`, coarse for a ~14-case split).
- The `_outcome` RECHECK precedence is a semantic rule (a `second_look` flag can only be set on a case that passed `verify`, so it can never coincide with a short-circuit) — not needed for green tests, only to preserve E-07.
- `_digest_payload` intentionally unchanged, so the committed `report.json`/`EVALS.md` still recompute; Plan 03 seals the new per-case facts together with the regeneration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed a `spans.jsonl` artifact written to the repo root**
- **Found during:** whole-suite verification
- **Issue:** a temporary observation script I ran wrote the production span sink to `spans.jsonl` at the repo root, failing `tests/test_observability.py#test_no_spans_artifact_is_written_to_the_repo_root`.
- **Fix:** deleted the gitignored, untracked artifact (not part of the task).
- **Files modified:** none (untracked artifact removed).

**2. [Rule 3 - Blocking] `ruff` B905 on the new `zip()` calls**
- **Found during:** lint of the new analyser
- **Fix:** added explicit `strict=False` (the two lists are the same length in practice, but a committed legacy report carries an empty `confidence_satisfied`, so `strict=True` would raise).

### Minor, in-plan adjustments

- `tests/test_scorer_baseline.py` reworked to drive E-08 through the shared `conftest.build_graph_tools` fake (the established graph-proof pattern) so it can assert the call list and the queue-row absence directly; the removed `build_tools`/`Command`/`UsageRecorder` imports were dropped.
- Renamed `test_escalation_beat_reaches_four_owned_tools` → `..._five_owned_tools` to match the sixth tool it now reaches.
- Hoisted the synthetic `Provenance` in `tests/test_eval_report.py` into one `_PROVENANCE` constant (DRY) for reuse by the bare-construction proof.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced; the new deferral/calibration fields are populated from the report.

## Threat Flags

None. Every change stays inside the plan's declared trust boundaries: the report seals the same explicit key set (T-08-06), the gate exclusion is pinned against masking a wrong colour and the moved cases are surfaced (T-08-07), and ECE is confined to `evals/` with the sample size named (T-08-08). No dependency was added (T-08-SC).

## Issues Encountered

- **The `gsd_run query git.base-branch --is-protected <branch>` predicate is not wired in this gsd-core build** — it returns the resolved base-branch string for any input (including an empty/unknown branch), so the guard's literal `!= "false"` test would spuriously fail for every branch. This workspace declares `git.branching_strategy: "none"` and its recent phase commits (Plan 08-01 `fd77bbc`, `a014973`) are on `main`; commits were made on `main` consistently. The guard's intent (no commit to an unintended branch) is satisfied: HEAD stayed on `main`. Flagged for the orchestrator; the equivalent top-level verb `gsd_run git base-branch --is-protected` behaves identically.
- **`commit_docs` is `false`** in this workspace, so the SUMMARY/STATE/ROADMAP edits are made on disk but not committed (the established, documented workspace posture — see STATE.md).
- **The committed `evals/results/report.json` and `EVALS.md` are NOT regenerated here.** Plan 03 owns `scripts/emit_evals.py` + `EVALS.md` + the regenerated report; `tests/test_docs_final.py#test_evals_is_a_projection_of_the_report` stays green because `_digest_payload` is unchanged, so the committed report still recomputes against the current `EVALS.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 08-03 (publication): the report/analysis now carry every measured field (`deferral_rate`/`deferral_cases`, `calibration.ece`/`risk_coverage`, both n's) that the generator projects into `EVALS.md` §3/§4/§6.
- Plan 03 must regenerate `evals/results/report.json` + `EVALS.md` from a fresh run and seal the new per-case deferral facts in `_digest_payload` in the SAME change.

---

*Phase: 08-calibrated-confidence-abstention*
*Completed: 2026-10-12*

## Self-Check: PASSED

- FOUND: src/triagedesk/evals/report.py
- FOUND: src/triagedesk/evals/analysis.py
- FOUND: src/triagedesk/evals/runner.py
- FOUND: tests/test_eval_report.py
- FOUND: .planning/phases/08-calibrated-confidence-abstention/08-02-SUMMARY.md
- FOUND: commit 4c9fcb9 (Task 1)
- FOUND: commit 477753c (Task 2)
- FOUND: commit 7aed8e9 (Task 3)
- Plan metadata commit: skipped (`skipped_commit_docs_false`)
