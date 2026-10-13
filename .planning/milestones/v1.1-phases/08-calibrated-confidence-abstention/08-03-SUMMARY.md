---
phase: 08-calibrated-confidence-abstention
plan: 03
subsystem: evals
tags: [deferral, calibration, report-digest, evals-projection, honest-reporting, real-mode]

requires:
  - phase: 08-calibrated-confidence-abstention
    plan: 01
    provides: the deterministic `confidence` signal, the `assess` node and the deferral terminals this plan publishes
  - phase: 08-calibrated-confidence-abstention
    plan: 02
    provides: the per-case deferral facts, the separate deferral rate and the declared-split calibration this plan projects
  - phase: 04-evaluation-harness
    provides: the sole-source `EVALS.md` projection (`scripts/emit_evals.py`) and its `--check` digest gate

provides:
  - "`evals/report.py`: `_digest_payload` seals the per-case `held_out`/`confidence_levels`/`deferrals` (D8-14)"
  - "`scripts/emit_evals.py`: the §3 `Deferral rate` + `Calibration (small-sample)` rows, the §4 deferral marker, and a DERIVED §6.1 coverage-deferral record"
  - "`EVALS.md`: the structural §3 rows, the §3.2 small-sample declaration, and the truthful §6/§6.1 coverage-deferral record"
  - "the regenerated real-mode `evals/results/report.json` whose digest recomputes with the new payload"
affects: [11-honest-evaluation, 12-milestone-close]

actuals:
  tokens: 14971
  tasks: 2
  commits: 2
  plan_head_before: 7aed8e98528776ed52ef7e1ab4a8bf6b7d129379
  plan_head_after: d25766d6b5645c56d1e110168334f2ffd10df07b

tech-stack:
  added: []
  patterns:
    - "A generated narrative record: the §6 coverage-deferral prose is DERIVED from the report (moved cases, fraction, gate failures), so the published text cannot drift from what was measured"
    - "One deferral-marker predicate shared by the §4 table and the §6 record (DRY), rather than two parallel implementations"
    - "A terminal reached before `assess` carries `null` deferrals — 'no deferral fact' is the honest value, never a fabricated `False`"

key-files:
  created: []
  modified:
    - src/triagedesk/evals/report.py
    - scripts/emit_evals.py
    - EVALS.md
    - evals/results/report.json
    - tests/test_eval_report.py

key-decisions:
  - "REAL mode kept (owner decision, 2026-10-12): the committed report is `mode: real`; the real local model stably diverges on the pre-existing E-04/E-07/E-13 cases (identical to the committed v1.0 real report, never re-rolled). No fixture, threshold or mode was tuned, and the run was NOT flipped to `--offline`."
  - "E-13 short-circuits BEFORE `assess`, so its `deferrals == [null, null, null]` and it stays at its abstain terminal — correct behaviour, not a defect; E-07 reaches RECOVER in real mode, so it too carries `null` deferrals. A case that reaches a terminal before the confidence check cannot carry a deferral fact, so `null` is the right value."
  - "The gate reports `passed: false` with the pre-existing real-mode failures E-04/E-07/E-13. That is the honest measured state; Phase 11 owns fixing those."
  - "The §6.1 coverage-deferral record is DERIVED from the report — moved cases via the §4 predicate, the fraction via the analyser, the recorded unfixed gate failures via `report.gate` — never a hand-typed case list, so the published narrative is true of whatever the run produced."
  - "In real mode the moved cases are E-01/E-08/E-09/E-14 (all `deferrals == [true, true, true]`); the sealed digest recomputes over them."

patterns-established:
  - "Mode-appropriate honest publication: the same generator projects either mode truthfully; the §6 narrative is derived, so no mode-specific case list is hard-coded."

requirements-completed: [AGENT-02]

coverage:
  - id: D1
    description: "The per-case deferral facts (`held_out`/`confidence_levels`/`deferrals`) are sealed in `report_digest`; flipping one changes the digest (D8-14)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_report_digest_seals_the_per_case_deferral_facts"
        status: pass
    human_judgment: false
  - id: D2
    description: "The §3 `Deferral rate` (a fraction) and `Calibration (small-sample)` (both n's named) rows are generated from `report.json`; no number is hand-typed (D8-10, D8-15, D8-16)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_deferral_rate_and_declared_split_calibration_are_measured"
        status: pass
      - kind: integration
        ref: "tests/test_docs_final.py#test_evals_is_a_projection_of_the_report"
        status: pass
    human_judgment: false
  - id: D3
    description: "A coverage deferral is rendered visibly — the §4 deferral marker for an all-deferred failing case and a §6 record — never a silent pass or an unexplained failure (D8-11, D8-16)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_generator_renders_a_coverage_deferral_as_a_marker_not_a_failure"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_generator_derives_the_section_6_deferral_record_from_the_report"
        status: pass
    human_judgment: false
  - id: D4
    description: "The committed real-mode `evals/results/report.json` is regenerated by the shipped pipeline; its digest recomputes and `--check` exits 0 (D8-14)."
    requirement: "AGENT-02"
    verification:
      - kind: integration
        ref: "uv run python scripts/emit_evals.py --check"
        status: pass
    human_judgment: false
  - id: D5
    description: "The §6 record is truthful for the published real-mode report: no hard-coded list asserts E-13/E-07 defer (both carry `null` deferrals because they short-circuit before `assess`)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_generator_derives_the_section_6_deferral_record_from_the_report"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-10-12
status: complete
---

# Phase 8 Plan 03: Calibrated Confidence & Abstention Summary

**The deferral facts are sealed in `report_digest` and the measurement is published: a real-mode `report.json` regenerated by the shipped pipeline, a §3 deferral rate and small-sample calibration projected from it, and a §6 coverage-deferral record derived from the report — no number hand-typed, `--check` exits 0, whole suite green (298 passed).**

## Performance

- **Duration:** ~30 min (Task 1 in the prior session; Task 2 after a resolved `blocking-human` checkpoint)
- **Started:** 2026-10-12T16:18:18Z (plan ledger)
- **Completed:** 2026-10-12T16:48:00Z (approx)
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Extended `_digest_payload` to seal the per-case `held_out`/`confidence_levels`/`deferrals`, so a flipped deferral moves `report_digest` (D8-14) — pinned by a digest-mutation test.
- Added the §3 `Deferral rate` (a fraction, never a percentage) and `Calibration (small-sample)` (ECE + both named `n`'s) rows to the generator, and rendered an all-deferred failing case with an explicit **⏸ deferral** marker in §4 instead of a bare ❌ (D8-10, D8-15, D8-16).
- Regenerated `evals/results/report.json` (mode `real`) through the shipped pipeline and `EVALS.md` via `--write`, closing the transient red opened by the digest extension; `emit_evals.py --check` now exits 0.
- Made the §6/§6.1 narrative **truthful for the real-mode report**: the coverage-deferral record is now DERIVED from the report (moved cases, fraction, recorded unfixed gate failures), replacing static wording that wrongly asserted E-13 (and E-07) defer.
- Factored the §4 deferral-marker predicate into ONE shared helper used by the §4 table and the §6 record (DRY), and added a regression test proving the §6 record is derived and idempotent.
- Confirmed the whole suite green: **298 passed**; `uv run pytest tests/test_docs_final.py tests/test_eval_report.py -q` → 21 passed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Seal the deferral facts and generate the deferral/calibration rows + the §4 deferral marker** - `8b89d4c` (feat)
2. **Task 2: Regenerate report.json and EVALS.md through the shipped pipeline** - `d25766d` (feat)

**Plan metadata:** not committed — `commit_docs: false` in this workspace (see below).

_Note: not a TDD plan; each task is one commit. Tasks 1 and 2 are one logical change (the digest extension and the regeneration ship together)._

## Files Created/Modified

- `src/triagedesk/evals/report.py` - `_digest_payload` seals the per-case deferral facts; the aggregate calibration stays in `Analysis` (never sealed).
- `scripts/emit_evals.py` - `Deferral rate` + `Calibration (small-sample)` §3 rows; the §4 deferral marker; the DERIVED §6.1 coverage-deferral record; one shared `_shows_deferral_marker` predicate.
- `EVALS.md` - the structural §3 rows, the §3.2 small-sample declaration, and the corrected §6/§6.1 record (all hand-written except the generated cells/blocks).
- `evals/results/report.json` - regenerated real-mode report; digest recomputes with the new payload.
- `tests/test_eval_report.py` - the digest-mutation proof, the deferral-marker generator proof, and the §6.1 derived-record proof.

## Decisions Made

- **Real mode kept (owner decision, 2026-10-12).** The committed report is `mode: real`; the real local model stably diverges on the pre-existing E-04/E-07/E-13 cases (identical to the committed v1.0 real report, never re-rolled). No fixture, threshold or mode was tuned.
- **Mode-appropriate expectations.** In real mode E-01/E-08/E-09/E-14 defer (`deferrals == [true, true, true]`). E-13 short-circuits BEFORE `assess`, so it carries `null` deferrals and stays at its abstain terminal (correct, not a defect); E-07 reaches RECOVER in real mode, so it too carries `null` deferrals. A case that reaches a terminal before the confidence check cannot carry a deferral fact.
- **The gate's `passed: false` is honest.** The pre-existing real-mode failures (E-04, E-07, E-13) are recorded, not re-rolled; Phase 11 owns fixing them.
- **The §6.1 record is derived, not hand-typed.** Moved cases come from the §4 predicate, the fraction from the analyser, and the recorded unfixed gate failures from `report.gate` — so the published narrative is true of the run and cannot drift.
- **One marker predicate (DRY).** `_shows_deferral_marker` is shared by the §4 table and the §6.1 record.

## Deviations from Plan

### Continuation-sanctioned adjustments

**1. [Rule 2 - Correctness] Made the §6.1 narrative truthful for the real-mode report**
- **Found during:** Task 2 (regeneration)
- **Issue:** Task 1's hand-written §6.1 asserted "E-01, E-08, E-09, E-13 and E-14 now show the deferral marker" and "E-07 keeps its RECHECK outcome — it also defers". In the published `mode: real` report this is false: E-13 short-circuits before `assess` (no deferral fact; renders ❌) and E-07 reaches RECOVER (no deferral fact).
- **Fix:** Replaced the static case list with a generator-produced §6.1 record derived from the report, and rewrote the surrounding prose to be mode-agnostic. The D8-11 override and the honest E-09 gap record are unchanged.
- **Files modified:** scripts/emit_evals.py, EVALS.md, tests/test_eval_report.py
- **Verification:** `tests/test_eval_report.py#test_generator_derives_the_section_6_deferral_record_from_the_report`; `--check` exits 0; §6.1 renders `E-01, E-08, E-09, E-14` and gate failures `E-04, E-07, E-13`.
- **Committed in:** `d25766d` (Task 2 commit)

**2. [Rule 1 - DRY] Factored the §4 deferral-marker predicate into one helper**
- **Found during:** Task 2
- **Issue:** The §6.1 record needed the same "all-deferred failing case" predicate the §4 table already inlined; duplicating it would violate the iron-clad DRY rule.
- **Fix:** Extracted `_shows_deferral_marker(case)` and used it in both the §4 table and the §6.1 record.
- **Files modified:** scripts/emit_evals.py
- **Verification:** `ruff check` clean; both generator tests pass.
- **Committed in:** `d25766d`

---

**Total deviations:** 1 correctness correction (continuation-sanctioned by the resolved checkpoint decision), 1 DRY refactor.
**Impact on plan:** No scope creep; both adjustments are required for the published document to be honest and DRY.

## Issues Encountered

- **Resolved `blocking-human` checkpoint — the mode contradiction.** The plan's original acceptance text assumed the offline deferral pattern; the committed report is `mode: real`, which stably diverges on E-04/E-07/E-13. The owner resolved it on 2026-10-12: **keep the real-mode regeneration**, do not flip to `--offline`, do not tune anything, and read the corrected mode-appropriate expectations. The plan's `<fails_when>`/acceptance were corrected accordingly (E-13/E-07 carry `null`; the gate's pre-existing failures are honest and belong to Phase 11).
- **`gsd_run query git.base-branch --is-protected <branch>` returns the base branch for any input** (known broken predicate in this gsd-core build). This workspace declares `git.branching_strategy: "none"` and all recent phase commits are on `main`; Task 2 was committed on `main` consistently. The guard's intent (no commit to an unintended branch) is satisfied.
- **`commit_docs` is `false`** in this workspace, so the SUMMARY/STATE/ROADMAP edits are made on disk but not committed (the established, documented workspace posture — see STATE.md).
- **`ruff format` is not the enforced gate** (CI runs `uv run ruff check`, which passes). The committed `scripts/emit_evals.py` predates format-normalisation on unrelated lines; new code was kept format-consistent without reformatting pre-existing lines.

## User Setup Required

None - no external service configuration required. (Real-mode regeneration used the already-running local Ollama server + the pulled `qwen2.5:1.5b`; no new setup.)

## Next Phase Readiness

- The publication half of Phase 8 is complete: the deferral facts are sealed in the digest, the deferral rate and small-sample calibration are published, and the coverage deferrals are visible in §4/§6 — all from `report.json` by the one generator.
- Phase 11 (honest evaluation) inherits the recorded, unfixed real-mode gate failures (E-04, E-07, E-13); it owns fixing them, not this phase.

---

*Phase: 08-calibrated-confidence-abstention*
*Completed: 2026-10-12*

## Self-Check: PASSED

- FOUND: src/triagedesk/evals/report.py
- FOUND: scripts/emit_evals.py
- FOUND: EVALS.md
- FOUND: evals/results/report.json
- FOUND: tests/test_eval_report.py
- FOUND: .planning/phases/08-calibrated-confidence-abstention/08-03-SUMMARY.md
- FOUND: commit 8b89d4c (Task 1)
- FOUND: commit d25766d (Task 2)
- `uv run python scripts/emit_evals.py --check` → exit 0
- `uv run pytest -q` → 298 passed
