---
phase: 08-calibrated-confidence-abstention
fixed_at: 2026-10-12T17:39:35Z
review_path: .planning/phases/08-calibrated-confidence-abstention/08-REVIEW.md
iteration: 2
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-10-12T17:39:35Z
**Source review:** `.planning/phases/08-calibrated-confidence-abstention/08-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 3 (WR-05 — the one warning; plus the two info items IN-04 / IN-05 the
  iteration-2 brief asked to fix if cheap)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-05: `confidence_satisfied` is not sealed in `report_digest`, so the published ECE can be tampered with undetected

**Files modified:** `src/triagedesk/evals/report.py`, `tests/test_eval_report.py`,
`evals/results/report.json`, `EVALS.md`
**Commit:** `7a2974b`
**Applied fix:**
- Added `"confidence_satisfied": case.confidence_satisfied` to `_digest_payload`'s per-case
  dict in `src/triagedesk/evals/report.py`, giving the scalar the same treatment as the other
  sealed per-case coverage facts (`held_out`, `confidence_levels`, `deferrals`). Updated the
  `_digest_payload` docstring to fold `confidence_satisfied` into the enumerated sealed facts
  and to state that the published ECE / risk–coverage re-derive from it, so a change in the
  published calibration behaviour must move the digest (D8-14).
- Added `test_report_digest_seals_the_per_case_confidence_satisfied_facts` to
  `tests/test_eval_report.py`, mirroring the existing deferral-digest test: it asserts the
  digest recomputes, that flipping a `ReportCase.confidence_satisfied` entry moves
  `compute_report_digest`, and that the mutated report's `analyse(...).calibration.ece` differs
  — proving the sealed scalar is exactly what the published ECE re-derives from.
- Regenerated the committed report and `EVALS.md` through the shipped pipeline:
  `uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json`
  (real mode) then `uv run python scripts/emit_evals.py --write`. **No measured number was
  hand-edited and nothing was tuned.** The real re-run reproduced the committed report's
  non-volatile safety content byte-for-byte — same per-case outcomes, same `confidence_satisfied`
  vectors, same gate (`E-04`, `E-07`, `E-13`), same deferral rate (12/32) and the same ECE
  (0.3365). The only non-volatile diffs are `report_digest` (now a function of the new field)
  and `provenance.harness_commit` (the re-run records the current HEAD); the only other diffs —
  per-run `latency_s`/tokens and the unsealed `run_errors` field — are volatile/diagnostic and
  never sealed.

**Verified:** `compute_report_digest(report) == report.report_digest` on the committed report
(`ebef6471…`); tampering any `confidence_satisfied` entry now changes the digest (the WR-05
reproduction is closed); `emit_evals.py --check` exits 0.

### IN-04: An errored run contributes `latency = 0.0` to the latency sample

**Files modified:** `src/triagedesk/evals/runner.py`, `src/triagedesk/evals/analysis.py`,
`src/triagedesk/evals/report.py`, `tests/test_eval_report.py`
**Commit:** `7352967`
**Applied fix:**
- `runner.py`: the error branch now records `run_latency = None` instead of `0.0`, so an errored
  run contributes no `0.0` to the sample. The per-run entry stays index-aligned with
  `run_errors` (still visible there and in the fail-closed `ABORT` outcome / gate) — only its
  latency contribution is dropped. Widened `ReportCase.latency_s` (and the runner's local list)
  to `list[float | None]` and documented the sentinel.
- `analysis.py`: `analyse` now filters `None` out of the percentile input before computing
  p50/p95. The "no latency samples" guard still fires when the report carries **no** latency
  entries at all (the existing missing-cost test is unchanged), while an all-`None` sample
  (every run errored) analyses to `0.0` rather than aborting — preserving WR-04's guarantee that
  an errored suite still writes a report.
- Added two tests to `tests/test_eval_report.py`: `None` entries are excluded from p50/p95
  (valid samples `[1.0, 2.0]` → p50 1.0, p95 2.0), and a report whose every run errored still
  analyses.

### IN-05: `EVALS.md` §3.2 describes the ECE split imprecisely

**Files modified:** `EVALS.md`
**Commit:** `3e6d0ef`
**Applied fix:** Reworded the §3.2 sentence to state that the ECE is computed over the
**declared calibration split** (`held_out=false`), with the held-out split (`held_out=true`)
named separately to bound the declared failure — and that the generated cell names both sample
sizes (`n_calibration`, `n_held_out`) from the report, so the split stays auditable rather than
chosen after seeing the result (D8-13). The wording now matches the code (`analysis.py`
computes the ECE over `held_out=False`) and no longer states the opposite. The sentence is
hand-written narrative (outside the generated markers), so `emit_evals.py --check` still exits
0.

## Skipped Issues

None — all in-scope findings were fixed.

## Verification

- **Where the gates ran:** the main checkout (`workflow.use_worktrees` is `false`, so no
  isolated worktree was created and the fixes were committed directly on `main`).
- `uv run pytest -q` → **304 passed** (301 baseline + 2 IN-04 tests + 1 WR-05 test).
- `uv run ruff check src tests scripts` → clean.
- `uv run python scripts/emit_evals.py --check` → exits 0 (report `ebef6471f15ed752`).
- The real eval was re-run to regenerate the report; the CLI's span sink wrote a gitignored
  `spans.jsonl` at the repo root, which was removed so the repository state matches the
  pre-pass state (and `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`
  stays green).
- **Commit mechanism note:** the project's `.planning/config.json` sets `commit_docs: false`,
  which makes the `gsd_run query commit` helper report `skipped_commit_docs_false` for every
  path. The three fixes were therefore committed with plain `git commit` (staging only the files
  named above), matching the existing iteration-1 `fix(08): …` commits on `main`.

---

_Fixed: 2026-10-12T17:39:35Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 2_
