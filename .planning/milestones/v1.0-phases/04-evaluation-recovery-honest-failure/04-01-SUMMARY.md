---
phase: 04-evaluation-recovery-honest-failure
plan: 01
subsystem: testing
tags: [eval, harness, langgraph, pydantic, provenance, hashing, argparse, usage-sink]

# Dependency graph
requires:
  - phase: 03-approval-gate-gated-commit-safety-spine
    provides: "graph.build.build_graph + the ONE TriageState interface, the interrupt() approval gate and the real gated commit_priority"
  - phase: 02-owned-tools-deterministic-scorer
    provides: "core matcher/scorer/recheck and the five owned MCP tools (server.py)"
  - phase: 01-foundation-substrate
    provides: "core/hashing.hash_value (the ONE canonical hash path) and the loaded SATS substrate"
provides:
  - "`triagedesk eval` console entry point (stdlib argparse) -> evals.runner.run_eval"
  - "triagedesk.evals package: CaseSpec/load_cases, Report/ReportCase + canonical writer, provenance + report_digest"
  - "the injectable usage_sink seam on llm.client.extract (token cost from the SAME ollama response)"
  - "the shared in-memory Store double (store/memory.py) reused by the harness and the test suite"
  - "the E-02 tracer fixture and the five-behaviour tracer proof suite"
affects: [04-02, 04-03, 04-04]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 13417
  tasks: 3
  commits: 3
  plan_head_before: e6fd09dfa195956357119f56f9d409fa9a2234b6
  plan_head_after: b0927db3f5bfe3435ab773bf76d073a1dfbae691

# Tech tracking
tech-stack:
  added: []  # no new dependency (stdlib argparse; every other import already pinned)
  patterns:
    - "usage_sink seam: an optional keyword-only callable on extract() read from the one model response"
    - "one canonical report digest over the non-volatile content (excludes latency/tokens/timestamps)"
    - "injected tool factory + injected store seams so the harness is deterministic and testable offline"

key-files:
  created:
    - src/triagedesk/cli.py
    - src/triagedesk/evals/__init__.py
    - src/triagedesk/evals/case.py
    - src/triagedesk/evals/report.py
    - src/triagedesk/evals/tools.py
    - src/triagedesk/evals/usage.py
    - src/triagedesk/evals/runner.py
    - src/triagedesk/store/memory.py
    - evals/cases/E-02.yaml
    - tests/test_eval_tracer.py
  modified:
    - pyproject.toml
    - src/triagedesk/llm/client.py
    - tests/conftest.py

key-decisions:
  - "The eval consumes the ONE graph interface (TriageState + interrupt) — no bespoke code path (D-01)"
  - "Colour, matched-set and field stability are three SEPARATE flags; an unstable colour/matched-set is recorded, never averaged (D-02, Pitfall 12)"
  - "Token cost is read from the SAME ollama response via an injected usage_sink on extract — never a second model call (D-08, Pitfall 16)"
  - "The report carries a report_digest over the non-volatile content (case ids, outcomes, stability flags, provenance), excluding latency/tokens/timestamps (D-08, Pitfall 18)"
  - "The expected token set is the loaded colour set plus the three terminal outcomes; colours come from data/sats_tews.yaml, never a literal (CONVENTIONS §1)"
  - "Offline mode stubs ONLY the model; the matcher, scorer, recheck and the real gated commit all run for real (SOLID: L)"

patterns-established:
  - "Usage seam: extract(note, *, usage_sink=...) — an injected dependency, return type unchanged (Liskov)"
  - "One in-memory Store double in src/ shared by the harness and the suite (DRY)"
  - "Injected ToolFactory + Store seams keep run_eval deterministic and offline-testable (SOLID: D)"

requirements-completed: [EVAL-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "`triagedesk eval --cases <dir> --runs 3 --report <path>` runs each case 3x through the SAME graph interface and writes one machine-generated JSON report"
    requirement: "EVAL-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_offline_tracer_records_three_runs_and_stability"
        status: pass
    human_judgment: false
  - id: D2
    description: "The report separates colour_stable, matched_set_stable and field_stable; a run-to-run colour/matched-set difference is recorded as an instability, never hidden behind a majority"
    verification:
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_unstable_colour_is_recorded_not_averaged"
        status: pass
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_field_stability_is_independent_of_colour_stability"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every report carries per-run wall-clock latency, token totals, the provenance hashes (model tag, ollama version, prompt + SATS YAML hashes, harness commit SHA) and a reproducible report_digest"
    verification:
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_report_carries_provenance_and_a_recomputing_digest"
        status: pass
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_offline_digest_is_reproducible_across_runs"
        status: pass
    human_judgment: false
  - id: D4
    description: "The usage_sink seam on llm.client.extract reports token counts read from the SAME ollama response (no second model call)"
    verification:
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_offline_tracer_records_three_runs_and_stability (mode: offline, tokens_* = 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The harness drives the REAL gated commit_priority; an unapproved resume yields a refusal and writes no queue row"
    verification:
      - kind: unit
        ref: "tests/test_eval_tracer.py#test_harness_drives_the_real_gate_and_writes_nothing_on_dismiss"
        status: pass
    human_judgment: false

# Metrics
duration: ~23min
completed: 2026-10-09
status: complete
---

# Phase 4 Plan 1: Tracer Evaluation Harness Summary

**A real `triagedesk eval` command that runs one case three times through the same LangGraph interface and writes a machine-generated `report.json` carrying colour, matched-discriminator sets, three separate stability flags, per-run latency, token cost and the provenance hashes.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-10-09T18:14:53Z (phase-4 execution start)
- **Completed:** 2026-10-09T18:37:34Z
- **Tasks:** 3
- **Files modified:** 13 (10 created, 3 modified)

## Accomplishments

- Stood up the thinnest honest eval slice end-to-end: a YAML case → the real graph → a measured
  JSON report → the process exit code. `triagedesk eval --cases evals/cases --runs 3 --report
  evals/results/report.json --offline --case E-02` exits 0 and writes a report.
- The report records, per case, the three run colours, the three matched-discriminator sets and the
  three SEPARATE stability flags (`colour_stable`, `matched_set_stable`, `field_stable`); a run-to-run
  colour or matched-set difference is recorded as an instability, never averaged away (D-02, Pitfall 12).
- Token cost is measured through a new injectable `usage_sink` seam on `llm.client.extract`, read from
  the SAME `ollama.generate` response the extraction consumes — never a second model call (D-08, Pitfall 16).
- Every report carries the provenance hashes (model tag, Ollama version, prompt hash, the two SATS YAML
  hashes, harness commit SHA) recomputed through the ONE hashing path, plus a `report_digest` sealing the
  non-volatile content (latency/tokens/timestamps excluded) so the same behaviour reproduces and a real
  change does not (D-08, Pitfall 18).
- The harness drives the REAL gated `commit_priority` in-process; an unapproved (`dismiss`) resume is
  refused and writes no queue row — the eval never bypasses the gate (D-05).
- Promoted the in-memory `Store` double into `src/triagedesk/store/memory.py` so the harness and the
  suite share ONE implementation; `tests/conftest.py` keeps only the test-only queue-call recorder.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end one case × 3 runs → report.json through the real graph** - `c706d21` (feat)
2. **Task 2: Shared in-memory store, real/offline tool modes and hash provenance** - `bff2124` (refactor)
3. **Task 3: Tracer proof suite** - `b0927db` (test)

**Plan metadata:** `_pending_` (docs: complete plan)

_Note: no TDD tasks in this plan._

## Files Created/Modified

- `pyproject.toml` - added `[project.scripts] triagedesk` and the evals/ TID251 per-file ignore
- `src/triagedesk/cli.py` - the `triagedesk eval` argparse entry point (stdlib only)
- `src/triagedesk/evals/__init__.py` - the package's public surface
- `src/triagedesk/evals/case.py` - `CaseSpec` + `load_cases`; `expected` validated against the loaded colours + terminals
- `src/triagedesk/evals/report.py` - `Report`/`ReportCase`, provenance, `report_digest`, canonical-JSON writer
- `src/triagedesk/evals/usage.py` - `UsageRecorder` + `recorded_extract` (the ONE token recorder)
- `src/triagedesk/evals/tools.py` - the injected `ToolMap` builder (real owned tools; model stubbed offline) + the extract seam
- `src/triagedesk/evals/runner.py` - `run_eval`; N runs through the graph, stability split, resume-on-gate
- `src/triagedesk/llm/client.py` - the injectable `usage_sink` seam on `extract`
- `src/triagedesk/store/memory.py` - the ONE in-memory `Store` double (queue + case + audit)
- `evals/cases/E-02.yaml` - the tracer fixture (ORANGE, frozen from EVALS.md §4 + the substrate)
- `tests/conftest.py` - `RecordingStore` subclasses the package store double
- `tests/test_eval_tracer.py` - the five-behaviour tracer proof suite

## Decisions Made

- Colours are read from `data/sats_tews.yaml`; the three terminal tokens (RECOVER/ABSTAIN/RECHECK) are
  declared once in `case.py` as harness vocabulary — no colour literal is inlined (CONVENTIONS §1).
- The report is serialised through `core.hashing.canonical_json` (compact, sorted keys) so untrusted
  complaint text is never concatenated into the document (T-04-03, M-13).
- `run_eval` exposes injected `store` and `tool_factory` seams so the proof suite can observe the real
  gate and inject a real instability without the model or the borrowed subprocess (SOLID: D).
- The in-memory checkpointer registers the graph's ONE msgpack allowlist so a resumed eval run does not
  trip the future strict-msgpack block.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created `src/triagedesk/store/memory.py` during Task 1 (plan assigned it to Task 2)**
- **Found during:** Task 1 (end-to-end tracer)
- **Issue:** The tracer's offline run must inject an in-memory store so the `@audited` interceptor on the
  real `commit_priority` never falls back to the borrowed SQLite subprocess. The plan deferred the store
  promotion to Task 2, but Task 1's verify (`... --offline --case E-02`) and done criteria cannot run
  without it.
- **Fix:** Created the shared `InMemoryStore` in `src/triagedesk/store/memory.py` in Task 1; Task 2 then
  performed the planned promotion by refactoring `tests/conftest.py` onto it.
- **Files modified:** `src/triagedesk/store/memory.py`, `tests/conftest.py`
- **Verification:** `uv run pytest -q` (185 passed); the offline tracer exits 0.
- **Committed in:** `c706d21` (Task 1) and `bff2124` (Task 2)

**2. [Rule 2 - Missing Critical] Provenance block and `report_digest` implemented in Task 1 (plan placed them in Task 2)**
- **Found during:** Task 1 (end-to-end tracer)
- **Issue:** Task 1's done criteria require the report to carry "the provenance hashes"; deferring the
  whole provenance/digest block to Task 2 would have left the Task 1 artifact without the honesty stamps
  its own success criteria demand.
- **Fix:** Implemented the provenance block (recomputed hashes) and the `report_digest` in Task 1; Task 2
  then confirmed reproducibility (`uv run triagedesk eval ... --offline --case E-02` twice → identical digest).
- **Files modified:** `src/triagedesk/evals/report.py`, `src/triagedesk/evals/runner.py`
- **Verification:** `tests/test_eval_tracer.py#test_report_carries_provenance_and_a_recomputing_digest` and
  `#test_offline_digest_is_reproducible_across_runs`.
- **Committed in:** `c706d21` (Task 1), confirmed in `bff2124` (Task 2)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing-critical) — both are ordering/placement adjustments, no scope creep.
**Impact on plan:** Task 2's remaining delta collapsed to the `tests/conftest.py` promotion; the tracer is
complete and honest from Task 1 onward. No functional scope was added.

## Issues Encountered

- The in-memory checkpointer initially emitted LangGraph "unregistered type" warnings on resume; resolved by
  reusing `graph.build`'s ONE msgpack allowlist for the eval's saver (DRY), so no state type is re-listed.
- `ruff`/`mypy` were not clean repo-wide before this plan (pre-existing `prompts.py` E501, `scripts/`
  F841, and `graph/nodes.py`/`build.py` mypy errors). The NEW files under `src/triagedesk/evals/`,
  `cli.py`, `store/memory.py` and `llm/client.py` are ruff- and mypy-clean; the pre-existing findings are
  out of scope (scope-boundary rule).

## User Setup Required

None - no external service configuration required. (The real measured run in 04-04 needs the local Ollama
server up with the pinned model pulled; the offline tracer here needs neither.)

## Known Stubs

None. Offline mode is an intentional, explicitly labelled path (`mode: offline`, `tokens_* = 0`); the real
measured run is produced in 04-04.

## Next Phase Readiness

- The proven tracer skeleton fixes the case-file format, the report schema, the graph-invocation path, the
  stability semantics (D-02) and the hash provenance (D-08), so 04-02 (the 14-case expansion + held-out
  cases), 04-03 (the invariant gate) and 04-04 (error-direction split + measured report) build on a proven
  base rather than a guess.
- `ReportCase` carries `colours`/`matched_discriminators`/`citations` per run and the three stability flags;
  `run_eval` exposes `store`/`tool_factory` seams for the suite and the runner's exit code is a single
  return point for 04-03 to extend.
- Transient artifact note: the offline report written to `evals/results/report.json` by the Task 1 verify is
  NOT committed — 04-04 owns the committed, REAL measured `evals/results/report.json`.

---
*Phase: 04-evaluation-recovery-honest-failure*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 11 created/updated files exist on disk (10 new artifacts + this SUMMARY).
- All 3 task commits are ancestors of HEAD: `c706d21`, `bff2124`, `b0927db`.
