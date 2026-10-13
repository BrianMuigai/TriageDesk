---
phase: 11-honest-evaluation-re-run-rigour-docs
plan: 02
subsystem: evals
tags: [honest-evaluation, real-rerun, report-projection, count-reconciliation, fail-closed-guard, declared-failure]

# Dependency graph
requires:
  - phase: 11-honest-evaluation-re-run-rigour-docs
    provides: "plan 11-01 — the age-contract fix, the D11-14 E-07 note repair and Provenance.extraction_schema_hash (all three move the measured report)"
  - phase: 08-calibrated-confidence-abstention
    provides: "the report digest + the deferral-aware gate (consumed, unchanged)"
provides:
  - "the regenerated evals/results/report.json (mode: real, 16 cases x 3 runs, digest recomputes)"
  - "the regenerated EVALS.md (16 §4 rows, the §6.2 D11-14 narrative, --check exits 0)"
  - "scripts/emit_evals.py::_assert_case_table_covers_report — the fail-closed §4 row-set guard"
  - "the §4 row-set reconciliation + measured-outcome honesty guards in tests/test_eval_report.py"
affects: [12 (the live technical review + the final doc refresh)]

# Actuals (#2632) — chars/4 over the realized diff, not a harness token count.
actuals:
  tokens: 14230
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []            # no new dependency (the phase installs nothing)
  patterns:
    - "The published document is a pure projection of the ONE report; the generator fails closed when a measured case has no published row"
    - "A drift guard reuses the renderer's own helpers so it cannot diverge from the thing it guards (DRY)"

key-files:
  created: []
  modified:
    - scripts/emit_evals.py
    - EVALS.md
    - evals/results/report.json
    - tests/test_eval_report.py

key-decisions:
  - "The §4 row-set guard lives in render_evals (per plan), so both --check and --write pass through it and a drift exits non-zero"
  - "The regenerated real report is recorded verbatim: E-04 -> RED and E-07 -> RECHECK (both now pass); E-08/E-13 remain honest stochastic misses; E-09 stays the declared failure"
  - "The research's A4 prediction (E-13 -> coverage deferral) did NOT hold on this run — E-13 stayed a null-age ABSTAIN in unexpected_failures, recorded as measured, never tuned (D11-03)"
  - "The §6.1 unfixed-failure record is derived from report.gate, so E-08/E-13 are named without a hand-typed list"

patterns-established:
  - "Fail-closed publication guard: a report case with no published row raises, mirroring validate_report's digest refusal"

requirements-completed: [EVAL-06, DOCS-05]

coverage:
  - id: D1
    description: "The real 16-case suite is re-run and report.json is regenerated (mode: real, 16 x 3, digest recomputes)"
    requirement: EVAL-06
    verification:
      - kind: other
        ref: "uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json (measured; digest 58c12b3b…)"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_committed_report_is_a_real_run"
        status: pass
    human_judgment: true
    rationale: "The local 1.5B model is stochastic; the verifier should re-measure the real path rather than trust a single recorded run."
  - id: D2
    description: "The two fixable failures reach their expected real-mode outcomes (E-04 RED x3; E-07 RECHECK x3)"
    requirement: EVAL-06
    verification:
      - kind: other
        ref: "evals/results/report.json — E-04 outcomes [RED,RED,RED]; E-07 outcomes [RECHECK,RECHECK,RECHECK] (measured)"
        status: pass
    human_judgment: true
    rationale: "Stochastic model measurement; re-measure to confirm."
  - id: D3
    description: "The §4 row set equals the report's case set and the generator fails closed on drift"
    requirement: DOCS-05
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_committed_section_4_rows_equal_the_report_case_set"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_case_table_guard_raises_when_a_report_case_has_no_row"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_section_4_row_count_equals_the_report_case_count"
        status: pass
    human_judgment: false
  - id: D4
    description: "The declared failure and every honest miss stay visible; EVALS.md is exactly the report's projection"
    requirement: DOCS-05
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_declared_failure_stays_visible_and_is_not_a_bare_pass"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_unfixed_gate_failures_appear_in_the_section_6_1_record"
        status: pass
      - kind: other
        ref: "uv run python scripts/emit_evals.py --check (exit 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The D11-14 E-07 fixture-note repair is documented honestly in the published EVALS.md §6.2"
    requirement: DOCS-05
    verification: []
    human_judgment: true
    rationale: "A prose narrative row; the correctness of its framing is a human judgment (no code control)."

# Metrics
duration: 19min
completed: 2026-10-13
status: complete
commits: 3
plan_head_before: 11c8b543a40504424ffb245e26fe87281bf20bf9
plan_head_after: 102aca992c6538687ae438a44e501cb07a8446ef
---

# Phase 11 Plan 02: The honest real re-run, the reconciled published artefacts and the fail-closed projection guard Summary

**The 16-case suite was re-run over the real graph and both fixed failures reached their expected outcomes — E-04 now RED×3 and E-07 now RECHECK×3 — while E-09 and the two honest stochastic misses (E-08, E-13) stay visible; `EVALS.md` is a pure projection of the regenerated `mode: real` report and the §4 row set is reconciled fail-closed.**

## Performance

- **Duration:** 19 min
- **Started:** 2026-10-13T07:46:16Z
- **Completed:** 2026-10-13T08:05:29Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- **The §4 count drift is closed, fail-closed.** `scripts/emit_evals.py` gains `_assert_case_table_covers_report`, called from `render_evals` after `_render_case_table`, which raises a `ValueError` naming every report case with no §4 row — so both `--check` and `--write` exit non-zero on a drift (mirroring `validate_report`). The two held-out cases **H-01/H-02** now have §4 rows, so the row set (16) equals the report's case set (16).
- **The real measurement is republished honestly.** `uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json` re-ran all 16 cases × 3 over `qwen2.5:1.5b` (Ollama 0.30.6) in ~12.5 min. The regenerated report is `mode: real`, 16 cases × 3 runs, with `report_digest: 58c12b3be863b85f8f2bf507d6d7f00f03b2bbf1a926b83db2cd99de7505c370` that recomputes; the provenance now seals `extraction_schema_hash` (the plan-11-01 contract change).
- **Both fixed failures reach their expected outcomes (measured).** **E-04** → `outcomes ['RED','RED','RED']` / `colours ['RED','RED','RED']`, emergency discriminator cited on every run (`passed: true`). **E-07** → `outcomes ['RECHECK','RECHECK','RECHECK']` with the deterministic `second_look` flag raised (`passed: true`). Neither is in `gate.unexpected_failures` any more.
- **The declared failure and the honest misses stay visible.** `gate.unexpected_failures == ['E-08','E-13']`; **E-09** stays the declared failure (`declared_failure: true`), rendered as a coverage deferral (`⏸ deferral`), never a bare pass. The derived §6.1 record names the unfixed gate failures (`E-08, E-13`) — no hand-typed list.
- **The D11-14 repair is documented in the published artefact.** `EVALS.md` §6.2 records the E-07 note↔golden inconsistency, why a faithful extraction of the *original* note correctly took the safe `RECOVER` terminal, and that the repair states the declared temperature while leaving `expected: RECHECK` unchanged — nothing tuned green.
- **The honesty is locked in hermetically.** Four new guards in `tests/test_eval_report.py` read only the committed `report.json`/`EVALS.md`: the §4 row count equals the report's case count; every declared failure is visible and never a bare pass; every recorded unfixed failure appears in the §6.1 record; the report stays `mode: real`.

## Measured facts (verbatim from the regenerated `report.json`)

| Fact | Value |
|------|-------|
| `mode` / `runs` / cases | `real` / `3` / `16` |
| `report_digest` | `58c12b3be863b85f8f2bf507d6d7f00f03b2bbf1a926b83db2cd99de7505c370` |
| `gate.passed` | `false` |
| `gate.unexpected_failures` | `['E-08', 'E-13']` |
| `gate.violations` | `[]` |
| `analysis.colour_runs` / `colour_correct` | `21` / `21` (100.0%) |
| `analysis.deferral_count` / `deferral_runs` | `13` / `34` |
| `analysis.deferral_cases` | `['E-01', 'E-07', 'E-08', 'E-09', 'E-14']` |
| `analysis.terminal_counts` | `{'ABSTAIN': 18, 'RECHECK': 3, 'RECOVER': 6}` |
| `analysis.under_triage_count` / `over_triage_count` | `0` / `0` |

Per-case measured outcomes:

| Case | Expected | `outcomes` | `colours` | `deferrals` | `passed` |
|------|----------|-----------|-----------|-------------|----------|
| E-04 | RED | `[RED, RED, RED]` | `[RED, RED, RED]` | `[false,false,false]` | **true** |
| E-07 | RECHECK | `[RECHECK, RECHECK, RECHECK]` | `[ORANGE, ORANGE, ORANGE]` | `[true,true,true]` | **true** |
| E-09 | ORANGE | `[ABSTAIN, ABSTAIN, ABSTAIN]` | `[GREEN, GREEN, GREEN]` | `[true,true,true]` | false (declared) |
| E-13 | GREEN | `[ABSTAIN, ABSTAIN, ABSTAIN]` | `[None, None, None]` | `[None, None, None]` | false |
| E-08 | GREEN | `[ABSTAIN, ABSTAIN, ABSTAIN]` | `[GREEN, None, None]` | `[true, None, None]` | false |

## Task Commits

Each task was committed atomically:

1. **Task 1: Reconcile §4 to the report — the H-01/H-02 rows, the fail-closed row-set guard, and the repair narrative** - `53b1744` (feat)
2. **Task 2: Re-run the 16-case suite over the real graph and regenerate the published artefacts** - `509a80b` (chore)
3. **Task 3: Lock the honesty in — the measured-outcome and declared-failure guards over the committed artefacts** - `102aca9` (test)

## Files Created/Modified

- `scripts/emit_evals.py` - added `_assert_case_table_covers_report` (the fail-closed §4 row-set guard), called from `render_evals` after `_render_case_table`
- `EVALS.md` - the H-01/H-02 §4 rows (row set now 16), the §6.2 D11-14 narrative, and the regenerated measured cells (only generator-written cells changed by `--write`)
- `evals/results/report.json` - the regenerated `mode: real` report (16 × 3, recomputing digest)
- `tests/test_eval_report.py` - the guard-raises test, the committed row-set/count reconciliation tests, and the declared-failure / §6.1-coverage / mode-real honesty guards

## Decisions Made

- **The row-set guard lives in `render_evals`** (per the plan), so the drift gate protects both `--check` and `--write`; it fails closed by raising, mirroring `validate_report`.
- **The re-run is recorded verbatim, not tuned.** The regenerated report keeps `mode: real` and whatever the model measured; no expectation, golden value or threshold was touched.
- **E-13 and E-08 are honest misses, re-declared (D11-03).** The research's **A4** predicted E-13 would move to a coverage deferral once the age fix landed; on this run it did **not** — E-13 stayed a null-age `ABSTAIN` before `assess` (`deferrals [None,None,None]`), so it remains an unexpected gate failure. E-08 likewise lost the age on two of three runs. Both are named in the derived §6.1 record, never hidden.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test fixture] The §4 row-set guard broke two existing generator tests**
- **Found during:** Task 1
- **Issue:** Calling `_assert_case_table_covers_report` from `render_evals` (as the plan directs) makes the generator refuse any synthetic report whose case has no §4 row. Two existing tests in `tests/test_eval_report.py` render synthetic reports with case ids (`D-1`, `D-2`, `H-9`) absent from the shared `_TEMPLATE`, so the guard raised and the suite went red.
- **Fix:** Added rows for `D-1`, `D-2`, `H-9` to the `_TEMPLATE` §4 table — the same "every rendered case needs a row" invariant the guard enforces on the real `EVALS.md`. No production behaviour changed; the guard is unchanged.
- **Files modified:** `tests/test_eval_report.py`
- **Committed in:** `53b1744` (Task 1 commit)

**2. [Rule 3 - Blocking] The real eval run wrote a generated `spans.jsonl` that broke an observability test**
- **Found during:** Task 2 (full-suite verification after the re-run)
- **Issue:** Running `uv run triagedesk eval …` writes the local span sink `spans.jsonl` to the repo root (it is gitignored, but not produced by the test suite, whose autouse fixture keeps the sink elsewhere). `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root` then failed on the leftover artefact.
- **Fix:** Removed the generated `spans.jsonl` (an untracked, gitignored runtime artefact — not source). The suite returned green.
- **Files modified:** none (removed a generated artefact)
- **Verification:** `uv run pytest -q` → 440 passed.

---

**Total deviations:** 2 auto-fixed (1 test-fixture, 1 blocking).
**Impact on plan:** Both were necessary to keep the suite green; neither changed the shipped generator/report semantics. No expectation, golden value or threshold was edited; no dependency added.

## Assumption-Delta Outcomes (research A4)

The research's **A4** (E-13 moves from `gate.unexpected_failures` to a coverage deferral once the age fix lands) did **not** hold on this run: E-13's injection note still lost the age stably (all three runs short-circuited before `assess`), so E-13 remains an unexpected gate failure. E-08 also recorded two null-age runs and moved *into* `unexpected_failures`. Per D11-03 these are recorded as measured, never re-run until they pass and never tuned.

## Issues Encountered

- **E-04/E-07 are fixed; E-08/E-13 are residual stochastic extraction misses.** The 1.5B model occasionally drops a stated age even with the strengthened contract (E-08: 2/3; E-13: 3/3 under the injection text). This is the honest residual gap the plan anticipated; it is visible in §4 (`❌`) and named in the §6.1 record.
- **The real run is slow (~12.5 min for 48 runs).** Recorded so the verifier budgets for a re-measurement.

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file access or schema change at a trust boundary. The new generator guard only tightens publication (a report case with no row now fails closed); the regenerated report seals its provenance and recomputes its digest.

## Next Phase Readiness

- The published artefacts (`report.json`, `EVALS.md`) are regenerated and reconciled; `emit_evals.py --check` exits 0 and the full suite is green at 440 passed.
- Phase 12 (the live technical review + the final doc refresh) can cite the regenerated `mode: real` report and its digest; `STATUS.md`'s historical 29/32 framing remains for Phase 12 to refresh (out of scope here).

---

*Phase: 11-honest-evaluation-re-run-rigour-docs*
*Completed: 2026-10-13*

## Self-Check: PASSED

- FOUND: scripts/emit_evals.py
- FOUND: EVALS.md
- FOUND: evals/results/report.json
- FOUND: tests/test_eval_report.py
- FOUND: 53b1744
- FOUND: 509a80b
- FOUND: 102aca9
