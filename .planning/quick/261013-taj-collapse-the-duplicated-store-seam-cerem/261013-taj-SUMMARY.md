---
phase: quick
plan: "261013-taj"
subsystem: refactor
tags: [dry, solid, store-seam, context-manager, evals, desk, durable]

# Dependency graph
requires: []
provides:
  - "mcp.server.store_seam: the ONE async context manager that resolves/installs/restores the store seam"
  - "evals.tools.offline_tools(CaseInput, recorder): the harness-free tool-map entry point"
  - "evals.tools._tool_map: the shared core both build_tools and offline_tools delegate to"
  - "tests/test_store_seam.py + test_no_eval_harness_import_in_the_desk_package: two regression guards"
affects: [evals, demo, desk, durable]

actuals:
  tokens: 5991        # chars/4 over the realized diff (23964 chars across src + tests)
  tasks: 3
  commits: 3          # MEASURED: git rev-list --count 939cc7b..HEAD
plan_head_before: 939cc7b4b77742ae7d071fd1c42abb0c648013b9
plan_head_after: ab58bbdbaa591f5ca92f2de2a146be3d180f6a0d

tech-stack:
  added: []
  patterns:
    - "One concern lives in one place: the store-seam ceremony is now a single context manager on the seam host (mcp/server.py)"
    - "Shared private core + thin public delegates (build_tools / offline_tools -> _tool_map) so a harness-shaped and a harness-free entry point cannot drift"

key-files:
  created:
    - tests/test_store_seam.py
  modified:
    - src/triagedesk/mcp/server.py
    - src/triagedesk/evals/runner.py
    - src/triagedesk/demo/run.py
    - src/triagedesk/evals/tools.py
    - src/triagedesk/evals/__init__.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/__init__.py
    - src/triagedesk/durable.py
    - tests/test_desk.py

key-decisions:
  - "store_seam is built ON set_store (never bypasses it) and keeps resolve_store the ONE resolver; it always restores None (never a saved prior store) so an injected offline double can never leak into a later call"
  - "replay.py keeps its direct read-only resolve_store() call — it installs no store, so it is the intentional non-change"
  - "offline_tools is offline=True with no injected fault, exposing the same seven real owned tools build_tools exposed; build_tools keeps its exact signature and delegates"
  - "the desk drops its direct triagedesk.evals.case import and reaches mcp.server/evals.case only transitively through evals.tools"

patterns-established:
  - "Store-seam install: one async context manager (mcp.server.store_seam) instead of copy-pasted set_store(x)/try/finally"
  - "Harness-free tool map: evals.tools.offline_tools(CaseInput, recorder) requires no fabricated CaseSpec"

requirements-completed: [QUICK-261013]

coverage:
  - id: D1
    description: "The store-seam ceremony exists in exactly one place (mcp.server.store_seam); every installing caller routes through it"
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_store_seam.py"
        status: pass
      - kind: integration
        ref: "uv run pytest tests/test_eval_suite.py tests/test_demo.py tests/test_demo_runbook.py tests/test_durable_cli.py tests/test_graph_durable.py tests/test_observability.py tests/test_replay_read_only.py tests/test_review_runbook.py -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "offline_tools(CaseInput, recorder) exists; build_tools and offline_tools share one _tool_map core; the desk builds its map with no CaseSpec and no evals.case import; durable._RESUME_PLACEHOLDER is deleted"
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "tests/test_desk.py::test_no_eval_harness_import_in_the_desk_package"
        status: pass
      - kind: integration
        ref: "uv run pytest tests/test_desk.py tests/test_durable_cli.py tests/test_graph_durable.py tests/test_eval_suite.py tests/test_review_runbook.py -q"
        status: pass
    human_judgment: false
  - id: D3
    description: "Two regression guards lock the collapses (store_seam contract + the desk's harness-free direct import graph)"
    requirement: "QUICK-261013"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_store_seam.py tests/test_desk.py -q"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-13
status: complete
---

# Quick Task 261013-taj: Collapse the store-seam ceremony and the fabricated harness cases

**One `store_seam` context manager replaces three copy-pasted store-install ceremonies, and one `offline_tools(CaseInput)` entry point retires the two fabricated `CaseSpec`s the desk and the durable resume each invented.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-10-13T18:14:38Z
- **Completed:** 2026-10-13T18:20:36Z
- **Tasks:** 3
- **Files modified:** 10 (9 modified, 1 created)

## Accomplishments

- `mcp.server.store_seam` is now the ONE place the store seam is installed for a block: it resolves once (injected store → caller's offline `default` factory → the ONE `resolve_store`), installs through `set_store`, yields the SAME instance, and always restores `None` in a `finally`. `evals/runner.py` and both `demo/run.py` sites now route through it; no caller repeats the `set_store(x)` / `try/finally set_store(None)` ceremony.
- `evals.tools.offline_tools(case: CaseInput, recorder)` is the harness-free tool-map entry point, and `build_tools` keeps its exact signature and behaviour as a one-line delegate — both share the ONE private `_tool_map` core.
- The desk's fabricated `CaseSpec` and `durable._RESUME_PLACEHOLDER` are deleted; the desk package no longer imports `triagedesk.evals.case` directly (it still reaches `mcp.server` only transitively via `evals.tools`), and `durable.resume_thread` builds its map from `offline_tools(CaseInput(), UsageRecorder())`.
- Two guards lock the collapses: `tests/test_store_seam.py` pins the seam's install/yield/default/resolve/restore-on-exception contract, and `test_no_eval_harness_import_in_the_desk_package` forbids a direct `triagedesk.evals.case` import in the whole `desk/` package.

## Task Commits

Each task was committed atomically:

1. **Task 1: One `store_seam` replaces the four-site store-seam ceremony (Finding 1)** - `514999d` (refactor)
2. **Task 2: One `offline_tools(CaseInput)` entry point; delete the fabricated harness cases (Finding 2)** - `c9e8303` (refactor)
3. **Task 3: Lock both collapses with two focused guards** - `ab58bbd` (test)

**Plan metadata:** (orchestrator handles the docs commit — `commit_docs: false`)

## Files Created/Modified

- `src/triagedesk/mcp/server.py` - added `store_seam` (+ `asynccontextmanager`/`AsyncIterator` imports); the ONE install path
- `src/triagedesk/evals/runner.py` - `run_eval` installs via `store_seam(store, default=InMemoryStore)`
- `src/triagedesk/demo/run.py` - `_run_durable` via `store_seam(store)`; `run_demo` via `store_seam(store, default=InMemoryStore)`; docstrings updated
- `src/triagedesk/evals/tools.py` - extracted `_tool_map` core; `build_tools` delegates; added `offline_tools`; `__all__` + module docstring updated
- `src/triagedesk/evals/__init__.py` - re-exports `offline_tools`
- `src/triagedesk/desk/server.py` - `_tools_for` uses `offline_tools(case, UsageRecorder())`; dropped the `CaseSpec`/`TERMINAL_OUTCOMES` import and the fabricated `CaseSpec`
- `src/triagedesk/desk/__init__.py` - docstring names `evals.tools.offline_tools`
- `src/triagedesk/durable.py` - deleted `_RESUME_PLACEHOLDER` + the `evals.case` import; `resume_thread` uses `offline_tools(CaseInput(), UsageRecorder())`
- `tests/test_store_seam.py` - new focused guard for the seam contract
- `tests/test_desk.py` - added `test_no_eval_harness_import_in_the_desk_package`

## Decisions Made

- `store_seam` restores `None` unconditionally (never a saved prior store), matching the current behaviour the conftest/seam tests rely on — an offline injected double must never leak into a later call.
- `replay.py` is deliberately left unchanged: it resolves a store read-only and installs none, so it keeps calling `resolve_store()` directly.
- `offline_tools` is `offline=True` with no injected fault, so it exposes exactly the same seven real owned tools `build_tools` did; the graph's own `assert_tool_allowlist` still gates the mapping at `build_graph`.

## Deviations from Plan

None - plan executed exactly as written.

(One pre-existing, out-of-scope finding is noted under Issues Encountered: an unchanged `no-any-return` mypy error in `durable.py::resume_paused`. It is present at the base commit (`durable.py:175`) and was not touched by this refactor.)

## Issues Encountered

- **Pre-existing mypy `no-any-return` in `durable.py`.** `uv run mypy src/triagedesk/mcp/server.py src/triagedesk/evals/tools.py src/triagedesk/desk/server.py src/triagedesk/durable.py` reports one error at `durable.py:159` (`return await graph.ainvoke(...)` in `resume_paused`). This line was **not modified** by the refactor; an isolated worktree at the base commit `939cc7b` reproduces the identical error at `durable.py:175` (its pre-deletion line number), among 30 pre-existing strict-mypy errors across 6 untouched files. Left alone per the scope boundary (pre-existing warnings in unmodified code are out of scope) — not a regression.
- The plan's `_RESUME_PLACEHOLDER` grep was scoped with `--include='*.py'` (plan-checker advisory #2) so stale `__pycache__/*.pyc` bytes cannot produce a false match; the plan's `contextlib` import note (advisory #1) was handled — `from contextlib import asynccontextmanager` did not previously exist in `mcp/server.py` and was added.

## Verification

Focused subset (plan `<verification>`), all green:

```
uv run pytest tests/test_store_seam.py tests/test_desk.py tests/test_desk_runbook.py \
  tests/test_durable_cli.py tests/test_graph_durable.py tests/test_eval_suite.py \
  tests/test_eval_invariants.py tests/test_eval_honest_terminal.py tests/test_eval_tracer.py \
  tests/test_demo.py tests/test_demo_runbook.py tests/test_observability.py \
  tests/test_replay_read_only.py tests/test_review_runbook.py -q
# 164 passed
```

Duplication greps (each prints nothing; `.py`-scoped):

```
grep -rn --include='*.py' "set_store(None)" src/triagedesk | grep -v "mcp/server.py"   # clean
grep -rn --include='*.py' "_RESUME_PLACEHOLDER" src tests                              # clean
grep -rn --include='*.py' "from triagedesk.evals.case import" src/triagedesk/desk       # clean
```

`grep -rn --include='*.py' "set_store(" src/triagedesk` shows only `mcp/server.py` (the definition, the one install, the one restore) — the seam has exactly one writer.

Lint: `uv run ruff check src/triagedesk tests/test_store_seam.py tests/test_desk.py` → All checks passed.

## Next Phase Readiness

- Behaviour is unchanged: no scoring, routing, gate, audit or queue behaviour was touched; the focused subset is green and every `build_tools` caller (8 test files) still passes.
- Both duplications are collapsed and guarded, so neither can creep back.

---
*Quick task: 261013-taj*
*Completed: 2026-10-13*

## Self-Check: PASSED

- FOUND: `tests/test_store_seam.py`
- FOUND: `.planning/quick/261013-taj-collapse-the-duplicated-store-seam-cerem/261013-taj-SUMMARY.md`
- FOUND: `514999d` (Task 1, ancestor of HEAD)
- FOUND: `c9e8303` (Task 2, ancestor of HEAD)
- FOUND: `ab58bbd` (Task 3, ancestor of HEAD)
- Working tree clean of task files; pre-existing `docs/assets/architecture.pdf` (modified) and `docs/render-architecture.sh` (untracked) left untouched and unstaged as required.
