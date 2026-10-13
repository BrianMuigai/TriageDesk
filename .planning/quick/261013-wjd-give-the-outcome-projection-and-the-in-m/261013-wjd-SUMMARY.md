---
phase: quick
plan: "261013-wjd"
subsystem: refactor
tags: [refactor, solid, dip, dry, checkpointer, evals, demo]

# Dependency graph
requires:
  - phase: quick-261013-taj
    provides: "the ONE store_seam context manager and the offline_tools(CaseInput) entry point"
provides:
  - "graph.build.in_memory_checkpointer() — the ONE public in-memory saver factory, carrying the same private _allowed_msgpack_modules allowlist as the durable open_checkpointer"
  - "evals/outcome.py — the ONE public home for the 12-key run-outcome projection (capture_outcome, error_capture)"
  - "a demo and eval runner that import only public names across module boundaries"
affects: [evals, demo, graph]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 4025
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One public factory per saver flavour, both applying the ONE private allowlist (DRY)"
    - "A projection shared by two consumers lives in a third module that is neither of them (SOLID: D, I)"

key-files:
  created:
    - src/triagedesk/evals/outcome.py
  modified:
    - src/triagedesk/graph/build.py
    - src/triagedesk/evals/runner.py
    - src/triagedesk/demo/run.py

key-decisions:
  - "in_memory_checkpointer() sits beside open_checkpointer on its owner graph/build.py so both flavours of 'a msgpack-allowlisted saver' live in one module; the allowlist stays PRIVATE and is applied once, never True."
  - "capture_outcome and error_capture move together into evals/outcome.py because they return the SAME 12-key captured-outcome contract — keeping the shape in one module (DRY) rather than splitting it across two."
  - "demo/run.py now imports nothing from triagedesk.evals.runner; the eval runner imports no private name from graph.build."

patterns-established:
  - "Cross-module consumers depend on published factory names (in_memory_checkpointer, capture_outcome), never on a private name (_checkpointer, _capture) the owner marked private."

requirements-completed: [QUICK-261013]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "graph.build.in_memory_checkpointer() exists and returns an InMemorySaver carrying a JsonPlusSerializer with the ONE allowlist; demo/run.py::_run_beat builds its graph through it."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "uv run python -c \"from triagedesk.graph.build import in_memory_checkpointer; ...\"; tests/test_demo.py"
        status: pass
      - kind: unit
        ref: "tests/test_purity.py#test_core_imports_nothing_from_llm_mcp_or_store; tests/test_safety_spine.py#test_graph_imports_no_external_network_client_or_model_provider"
        status: pass
    human_judgment: false
  - id: D2
    description: "evals/outcome.py exports capture_outcome/error_capture returning the identical 12-key dict (colour, citations, triggered_rules, matched_ids, recovery, escalation, second_look, delivered, route, attempt, confidence, error)."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_eval_suite.py; tests/test_eval_tracer.py; tests/test_eval_invariants.py; tests/test_eval_fidelity.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "evals/runner.py imports only public names (capture_outcome, error_capture, in_memory_checkpointer); _capture, _error_capture, _checkpointer and the _allowed_msgpack_modules import are deleted."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "grep -rnE \"\\b(_capture|_checkpointer)\\b\" src/triagedesk --include=*.py (empty); grep _allowed_msgpack_modules outside graph/build.py (empty)"
        status: pass
    human_judgment: false
  - id: D4
    description: "demo/run.py imports capture_outcome from evals.outcome and imports nothing from triagedesk.evals.runner; every printed line is byte-identical (commit reason + GATE REFUSED)."
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_demo.py (capsys-pinned output); tests/test_demo_runbook.py; tests/test_durable_cli.py; tests/test_review_runbook.py"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-10-13
status: complete
---

# Quick 261013-wjd: One public home for the outcome projection and the in-memory checkpointer

**Three cross-module private-name leaks retired: `_capture`/`_checkpointer` (runner → demo) and `_allowed_msgpack_modules` (build → runner) replaced by public `evals.outcome.capture_outcome`/`error_capture` and `graph.build.in_memory_checkpointer`, with byte-identical demo output and an unchanged 12-key projection.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-13T20:47:06Z
- **Completed:** 2026-10-13T20:53:02Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `graph.build.in_memory_checkpointer()` is the ONE public in-memory saver factory, sitting beside the durable `open_checkpointer` and applying the SAME private `_allowed_msgpack_modules` allowlist (never `True`).
- `evals/outcome.py` is the ONE public home for the run-outcome projection: `capture_outcome` and `error_capture`, both returning the identical 12-key captured-outcome dict.
- `demo/run.py` imports nothing from `triagedesk.evals.runner`; `evals/runner.py` imports no private name from `graph.build`; `_allowed_msgpack_modules` is now referenced only inside its owner `graph/build.py`.
- Behaviour is unchanged: the demo's printed lines (including `commit       : {commit.reason}` and `GATE REFUSED : no queue row written (rows added this beat: N)`) are byte-identical; no scoring, routing, gate, audit or queue change; `desk/` untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: in-memory checkpointer gets ONE public home (tracer)** - `c0882f7` (refactor)
2. **Task 2: outcome projection gets ONE public home** - `3e68e9a` (refactor)
3. **Task 3: the demo imports only public homes** - `c15b500` (refactor)

**Plan metadata:** orchestrator handles the docs commit (SUMMARY/STATE/PLAN are not committed here — `commit_docs: false`).

## Files Created/Modified
- `src/triagedesk/graph/build.py` - added `in_memory_checkpointer()` beside `open_checkpointer`; imported `InMemorySaver`; added the name to `__all__`.
- `src/triagedesk/evals/outcome.py` - NEW. ONE public projection home: `capture_outcome(result, payload)` and `error_capture(exc)`, bodies moved verbatim from the runner.
- `src/triagedesk/evals/runner.py` - imports `capture_outcome`/`error_capture` + `in_memory_checkpointer`; deleted `_capture`, `_error_capture`, `_checkpointer` and the private `_allowed_msgpack_modules` import; dropped the now-unused `InMemorySaver`/`JsonPlusSerializer` imports.
- `src/triagedesk/demo/run.py` - imports `capture_outcome` from `evals.outcome` and `in_memory_checkpointer` from `graph.build`; no longer imports the eval runner.

## Decisions Made
- The in-memory saver belongs on `graph/build.py` beside the durable saver, because that module already owns the ONE msgpack allowlist both flavours apply. The allowlist stays private and is applied once — never `True`.
- `capture_outcome` and `error_capture` move together into `evals/outcome.py` because they return the SAME 12-key contract; splitting the shape across modules would be a DRY defect.
- The `_error_capture` docstring's `:func:`_outcome`` cross-reference became a by-name reference to the runner's first-class-outcome mapping, since the two are no longer co-located.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Transient intermediate state between Task 2 and Task 3: deleting `_capture` from `runner.py` (Task 2) left `demo/run.py` importing a now-absent name until Task 3 rewired it. This is the plan's deliberate ordering — Task 2's `<verify>` does not exercise the demo — and the final state is green. No deviation; noted for the record.
- Pre-existing mypy errors in `graph/build.py` (StateGraph type-arg / add_node overload / load_graph_tools / run_case) and `demo/run.py` (missing `yaml` stubs) are unchanged and out of scope. The one new mypy note introduced at Task 2's boundary (`demo/run.py: has no attribute "_capture"`) disappeared at Task 3.
- A pre-existing `ruff format` diff in `demo/run.py` (the `_run_durable` call at ~line 294, not touched by this plan) is left alone per the scope boundary. `ruff check` (the plan's lint gate) is clean.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three private-name leaks are retired; the `graph/` purity/safety guards are green with `InMemorySaver` added to `graph/build.py`.
- No dependency added or changed (`pyproject.toml`, `uv.lock` untouched).

---

*Quick task: 261013-wjd*
*Completed: 2026-10-13*

## Self-Check: PASSED

- All 5 expected files present (outcome.py created; build.py, runner.py, run.py modified; SUMMARY.md written).
- All 3 task commits are ancestors of HEAD: c0882f7, 3e68e9a, c15b500.
- Full named pytest subset: 149 passed. Task-level subsets: 42 (Task 1), 82 (Task 2), 48 (Task 3) passed.
- Three smell greps print nothing: no `_capture`/`_checkpointer` under `src/triagedesk`; no `evals.runner` import in `demo/run.py`; `_allowed_msgpack_modules` only in `graph/build.py`.
- `ruff check` clean on all four touched files; no new mypy errors introduced.
