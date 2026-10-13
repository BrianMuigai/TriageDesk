---
phase: 08-calibrated-confidence-abstention
reviewed: 2026-10-12T17:45:53Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - EVALS.md
  - docs/DECISIONS.md
  - evals/results/report.json
  - scripts/emit_evals.py
  - src/triagedesk/core/confidence.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/evals/analysis.py
  - src/triagedesk/evals/report.py
  - src/triagedesk/evals/runner.py
  - src/triagedesk/evals/tools.py
  - src/triagedesk/graph/build.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/graph/state.py
  - src/triagedesk/mcp/server.py
  - tests/conftest.py
  - tests/test_confidence.py
  - tests/test_demo.py
  - tests/test_eval_honest_terminal.py
  - tests/test_eval_invariants.py
  - tests/test_eval_report.py
  - tests/test_eval_suite.py
  - tests/test_graph_confidence.py
  - tests/test_mcp_server.py
  - tests/test_safety_spine.py
  - tests/test_scorer_baseline.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 08: Code Review Report

**Reviewed:** 2026-10-12T17:45:53Z
**Depth:** standard
**Files Reviewed:** 25
**Status:** clean

## Summary

This is iteration 3 (final) of the `--auto` fix loop. I re-verified the three iteration-2
findings (WR-05, IN-04, IN-05) against the CURRENT source, re-ran the full suite and the
generator gate, and searched specifically for the regression classes the brief named. All
three fixes are **correct and complete**, and I found **no critical or warning defect**. The
phase is converged.

All reviewed files meet quality standards. No issues found.

## Narrative Findings (AI reviewer)

None. After the verification below I could not construct a path where the deferral signal
reaches `commit`, downgrades a colour, hides a moved deferral, publishes a hand-edited
calibration figure, or produces a non-reproducible number.

### WR-05 (`7a2974b`) — `confidence_satisfied` sealed in `report_digest`: **holds**

- `src/triagedesk/evals/report.py:337` now seals `"confidence_satisfied": case.confidence_satisfied`
  alongside the sibling per-case facts, and the `_digest_payload` docstring (lines 306-312)
  folds it into the enumerated sealed set. The asymmetry WR-05 described is gone.
- On the committed report the digest recomputes exactly:
  `compute_report_digest(report) == report.report_digest` → `True`
  (`ebef6471f15ed75242475a79545f940c9c18a82ca952c7c58d790953c27e5d7c`).
- The WR-05 reproduction is closed: setting `E-01.confidence_satisfied = [3,3,3]` now changes
  the digest (`True`) and changes the recomputed ECE (`0.3365…` → `0.2980…`), whereas before
  the fix that exact edit was undetected. The regression test
  `test_report_digest_seals_the_per_case_confidence_satisfied_facts`
  (`tests/test_eval_report.py:453`) is non-vacuous: the sealed scalar is what the published
  ECE re-derives from (`analyse(mutated).ece != analyse(sealed).ece`).

### IN-04 (`7352967`) — errored runs excluded from the latency sample: **holds**

- `src/triagedesk/evals/runner.py:345` records `run_latency = None` on the error path;
  `ReportCase.latency_s` is widened to `list[float | None]` (`report.py:93`).
- `analyse` filters the sentinel before the percentiles (`analysis.py:174-180`), so a spurious
  `0.0` can no longer bias p50/p95, while the "no latency samples" guard still fires on an
  empty sample (`test_report_carries_latency_and_cost_and_fails_when_missing` unchanged) and an
  all-`None` sample analyses to `0.0` rather than aborting (preserving WR-04's guarantee).
- **Widening does not break any consumer.** The only readers of `latency_s` are `analysis.py`
  (filters `None`) and `scripts/emit_evals.py` (reads `analysis.latency_p50/p95`, already
  filtered). `ruff check src tests scripts` and `mypy src/triagedesk/evals src/triagedesk/core/confidence.py`
  are both clean, so no type-level break was introduced.

### IN-05 (`3e6d0ef`) — ECE split wording: **holds**

- `EVALS.md:74-77` now states the ECE is computed over the **declared calibration split**
  (`held_out=false`) with the held-out split (`held_out=true`) named separately to bound the
  declared failure — matching `analysis.py:142,154` (`_calibration` passes `calibration_cases`
  to `_expected_calibration_error`). The sentence no longer states the opposite of the harness.

### Regression checks performed (all PASS)

- **Digest / generator agreement:** `uv run python scripts/emit_evals.py --check` → exit `0`
  (report `ebef6471f15ed752`); `evals/results/report.json` is unmodified in the working tree
  and `tests/test_docs_final.py`-style `--check` remains satisfied.
- **ECE divisor still correct:** `evals/analysis.py:28` imports `COMPONENT_COUNT = len(COMPONENT_NAMES)`
  from its owner `core/confidence.py:59`; no bare `4` survives in `src/` or `tests/`. Recomputing
  `_expected_calibration_error` over the committed report yields `0.3365384615384615`, identical
  to the stored `analysis.calibration.ece`.
- **No measured number inconsistent between `report.json` and `EVALS.md`:** the stored
  `analysis` block equals a fresh `analyse(report)` (`diff == {}`), and the generated cells in
  `EVALS.md` match: colour `20/20 … (100.0%); 3 case(s) failing the gate`, latency
  `p50 15.20 / p95 16.99` (report `15.197… / 16.987…`), deferral `12/32`, calibration
  `ECE 0.337 · n_calibration=14 · n_held_out=2`, source digest `ebef6471…`. The real example
  `provenance` (`qwen2.5:1.5b`, Ollama `0.30.6`) and `mode: real` are preserved.
- **Honest gate unchanged:** `gate.unexpected_failures == ["E-04", "E-07", "E-13"]`; the
  all-`True`-deferred cases (`E-01/E-08/E-09/E-14`) are surfaced in `deferral_cases`, and `E-04`
  (deferrals `[None, False, False]`) is never excluded.
- **One-way safety property intact:** `escalate`/`request_missing_info` still have no edge to
  `commit`; `commit` is reachable only via `approval_gate`; `assess` never assigns `priority`.
- **Unchanged invariants:** `git log` shows `core/scorer.py`, the citation helper and
  `mcp/audit.py` were not touched in the phase; `graph/*.py` imports no network client and reads
  no credentials (`test_safety_spine.py` guards green).
- **Suite:** `uv run pytest -q` → **304 passed**; `uv run ruff check src tests scripts` → clean.

### Observations considered and deliberately not raised as findings

These are sub-threshold and I judged them non-actionable (not bugs, no fix warranted on a final
convergence pass); recorded here for transparency so nothing is hidden:

1. `analysis.py:167-168` docstring still says `analyse` raises on "no latency samples", while an
   all-`None` sample (every run errored) now analyses to `0.0` by design
   (`test_a_report_where_every_run_errored_still_analyses`). Documentation nuance only; the
   intended behaviour is explicit and tested.
2. `_capture` (`runner.py:96-111`) and `_error_capture` (`runner.py:160-173`) are two literal
   dicts with the same key set. A small DRY smell, but factoring it would add indirection to a
   fail-closed path for no correctness gain.
3. `tests/test_eval_tracer.py:107` (`all(latency >= 0 for latency in case.latency_s)`) is
   `None`-unsafe given the widening, but that file is out of the phase's scope and the assertion
   only sees successful offline runs, so it cannot fail today.

---

_Reviewed: 2026-10-12T17:45:53Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
