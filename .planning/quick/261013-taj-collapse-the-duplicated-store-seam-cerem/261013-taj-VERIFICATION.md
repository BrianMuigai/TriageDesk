---
phase: quick
verified: 2026-10-13T18:23:19Z
status: passed
score: 6/6 must-haves verified
covered_files: [".planning/quick/261013-taj-collapse-the-duplicated-store-seam-cerem/261013-taj-PLAN.md", ".planning/quick/261013-taj-collapse-the-duplicated-store-seam-cerem/261013-taj-SUMMARY.md", "src/triagedesk/demo/run.py", "src/triagedesk/desk/__init__.py", "src/triagedesk/desk/server.py", "src/triagedesk/durable.py", "src/triagedesk/evals/__init__.py", "src/triagedesk/evals/runner.py", "src/triagedesk/evals/tools.py", "src/triagedesk/mcp/server.py", "tests/test_desk.py", "tests/test_store_seam.py"]
covered_digest: "v3:sha256:11230cbf4f8dbd37cdfe64126ed08cb934d467867361755f412e0764210af42c"
behavior_unverified: 0
overrides_applied: 0
---

# Phase quick: 261013-taj — Collapse the store-seam ceremony & give the tool map a `CaseInput` entry point — Verification Report

**Phase Goal:** Collapse the duplicated store-seam ceremony and give the tool map a `CaseInput` entry point.
**Verified:** 2026-10-13T18:23:19Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | The store-seam ceremony (resolve-or-use-injected → install → restore) exists in exactly ONE place; `evals/runner.py`, `demo/run.py` (beat loop AND `--durable`) install through it; no caller repeats `set_store(x) try/finally set_store(None)` | ✓ VERIFIED | `mcp/server.py:82-111` defines `store_seam`. Call sites: `evals/runner.py:465`, `demo/run.py:224` (`_run_durable`), `demo/run.py:296` (`run_demo`). `grep --include=*.py "set_store(" src/` returns ONLY `mcp/server.py` (def at 59, install at 107, restore at 111). |
| 2   | `mcp.server.set_store` remains the single write path and `mcp.server.resolve_store` the single resolver; the seam doubles observed by `tests/conftest.py`, `tests/test_observability.py`, `tests/test_review_runbook.py` still govern a run unchanged | ✓ VERIFIED | `store_seam` is built ON `set_store`+`resolve_store` (lines 101-111) — it adds no second resolver and no second write path. Only one `def resolve_store` (`mcp/server.py:69`). conftest:193-197, test_observability:163-168, test_review_runbook:227 still call `set_store` directly and are green. |
| 3   | `build_tools(case: CaseSpec, *, offline, recorder)` keeps its exact signature and behaviour, so its direct callers are untouched (pure additive refactor) | ✓ VERIFIED | Base signature (`git show 939cc7b`) == current (`evals/tools.py:158`): `def build_tools(case: CaseSpec, *, offline: bool, recorder: UsageRecorder) -> dict[str, Any]`. All 14 callers still pass a `CaseSpec` unchanged. Delegate is behaviour-identical (`_tool_map(case.case, offline=offline, inject=case.inject, recorder=recorder)`). |
| 4   | A `CaseInput`-shaped entry point builds the offline tool map with no fabricated `CaseSpec`; `desk/server.py::_tools_for` and `durable.resume_thread` both use it, and `durable._RESUME_PLACEHOLDER` is deleted | ✓ VERIFIED | `evals/tools.py:168-177` adds `offline_tools(case: CaseInput, recorder)`; exported via `evals/__init__.py:42`. `desk/server.py:199` → `offline_tools(case, UsageRecorder())`; `durable.py:223` → `offline_tools(CaseInput(), UsageRecorder())`. `_RESUME_PLACEHOLDER` has ZERO matches in `src`/`tests`. |
| 5   | The desk package no longer imports `triagedesk.evals.case` directly, and still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server` | ✓ VERIFIED | `grep --include=*.py` over `src/triagedesk/desk/` for `evals.case`, `store.queue`, `mcp.server` → all empty. `desk/server.py` now imports only `offline_tools` (line 56). Guard `test_no_eval_harness_import_in_the_desk_package` (test_desk.py:749) and `test_no_self_commit_path_in_the_desk_package` both green. |
| 6   | Behaviour is unchanged: no scoring, routing, gate, audit or queue behaviour changes; the focused test subset is green | ✓ VERIFIED | `git diff --stat 939cc7b HEAD -- src/` touches only the 8 declared files; `graph/`, `core/`, `store/` are byte-identical; `replay.py` unchanged (intentional read-only `resolve_store()` retained at :152). Focused subset: **164 passed** (ran live). |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/triagedesk/mcp/server.py` | `store_seam` async CM: resolve-or-default → `set_store` → yield → `finally set_store(None)` | ✓ VERIFIED | Lines 82-111; `asynccontextmanager` + `AsyncIterator` imported; correct precedence injected > default > `resolve_store`. |
| `src/triagedesk/evals/runner.py` | `run_eval` installs via `store_seam(store, default=InMemoryStore)` | ✓ VERIFIED | Line 465 wraps the `report_cases` comprehension; `factory`/`mode` locals preserved. |
| `src/triagedesk/demo/run.py` | `_run_durable` via `store_seam(store)`; `run_demo` via `store_seam(store, default=InMemoryStore)`; manual try/finally gone | ✓ VERIFIED | Lines 224, 296; docstrings (11, 219, 276) name `store_seam`. `_run_durable` correctly passes NO default (keeps the borrowed/resolved store). |
| `src/triagedesk/evals/tools.py` | One `_tool_map(case, *, offline, inject, recorder)` core; `build_tools` + `offline_tools` delegate | ✓ VERIFIED | Core at 82-155; `build_tools` 158-165; `offline_tools` 168-177; `__all__` updated. |
| `src/triagedesk/durable.py` | `_RESUME_PLACEHOLDER` deleted; `resume_thread` uses `offline_tools(CaseInput(), UsageRecorder())`; `evals.case` import gone | ✓ VERIFIED | Import at line 34 is `core.schema.CaseInput`; no `TERMINAL_OUTCOMES`/`CaseSpec` anywhere in the file. |
| `src/triagedesk/desk/server.py` | `_tools_for` uses `offline_tools(case, UsageRecorder())`; fabricated `CaseSpec` + `evals.case` import gone | ✓ VERIFIED | Lines 56, 199; `CaseSpec` survives only as a docstring word (line 196). |
| `tests/test_store_seam.py` | Focused proof of install/yield/default/resolver/restore-on-exception | ✓ VERIFIED | 4 async tests (lines 20-68) — all green. |
| `tests/test_desk.py` | Sibling guard: no direct `triagedesk.evals.case` import in `desk/` | ✓ VERIFIED | `test_no_eval_harness_import_in_the_desk_package` (749-772) reuses `DESK_DIR`/`SRC_ROOT`/`resolved_imports`/`package_parts_for`; green. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `evals/runner.py`, `demo/run.py` | `mcp/server.py::store_seam` | `async with server_module.store_seam(...)` | ✓ WIRED | The ONE install path; no caller re-implements resolve/install/restore. |
| `evals/tools.py::build_tools` / `offline_tools` | `_tool_map` | one-line delegation | ✓ WIRED | Both share the single core; harness path and harness-free path cannot drift. |
| `desk/server.py` | `evals.tools.offline_tools` | import + call | ✓ WIRED | No desk module imports `evals.case`, `store.queue` or `mcp.server`; `mcp.server` reached only transitively via `evals.tools`. |
| `durable.py::resume_thread` | `evals.tools.offline_tools` | lazy import | ✓ WIRED | `offline_tools(CaseInput(), UsageRecorder())`, no placeholder spec. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `store_seam` | `resolved` | injected store / caller `default()` / `await resolve_store()` | Yes — yielded instance is installed and returned by `resolve_store()` (asserted in `test_store_seam.py`) | ✓ FLOWING |
| `_tool_map` | tool callables | the seven real owned tools on `server_module` | Yes — offline stubs only `normalize_case`; matcher/scorer/recheck/commit run for real | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Focused phase subset green | `uv run pytest <14 declared test files> -q` | `164 passed in 29.95s` | ✓ PASS |
| `store_seam` restore-on-exception (cleanup invariant) | `tests/test_store_seam.py::test_seam_is_cleared_on_exception` | passed (in subset) | ✓ PASS |
| Ruff clean on touched surface | `uv run ruff check src/triagedesk tests/test_store_seam.py tests/test_desk.py` | `All checks passed!` | ✓ PASS |
| Duplication greps print nothing | see Anti-Patterns | clean | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| QUICK-261013 | 261013-taj-PLAN.md | Collapse the duplicated store-seam ceremony; give the tool map a `CaseInput` entry point | ✓ SATISFIED | Truths 1-6 all VERIFIED; both named duplications removed and guarded. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER` in any touched file | — | None |

Duplication greps (all `--include=*.py`, all clean):
- `grep -rn "set_store(None)" src/triagedesk | grep -v "mcp/server.py"` → nothing
- `grep -rn "_RESUME_PLACEHOLDER" src tests` → nothing
- `grep -rn "from triagedesk.evals.case import" src/triagedesk/desk` → nothing
- `grep -rn "set_store(" src/` → only `mcp/server.py` (def + the ONE install + the ONE restore)

### Human Verification Required

None. This is a behaviour-preserving internal refactor; every claim resolves to live source and to passing automated tests. No visual, real-time, external-service or UX item is introduced.

### Gaps Summary

No gaps. Both findings the phase set out to collapse are provably gone:

1. **Store-seam ceremony** now exists once as `mcp.server.store_seam` (an `@asynccontextmanager`), built directly on `set_store`/`resolve_store`. All three installing call sites (`evals/runner.py`, `demo/run.py::_run_durable`, `demo/run.py::run_demo`) route through it; the manual `set_store(x) try/finally set_store(None)` ceremony is deleted. The resolver (`resolve_store`) remains single; `replay.py` keeps its read-only direct call by design.
2. **The two fabricated harness cases are gone.** `durable._RESUME_PLACEHOLDER` is deleted and the desk's throwaway `CaseSpec` is deleted; both now build the map from a bare `CaseInput` via the new `evals.tools.offline_tools`. `build_tools`'s signature is byte-identical to the base and delegating, so its 14 callers are untouched. The desk no longer imports `triagedesk.evals.case` and still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server`.

**Behaviour preservation:** the `git diff` of `939cc7b..HEAD` over `src/` touches only the eight declared files; `graph/`, `core/`, `store/` are untouched and `replay.py` is unchanged. Each store-seam replacement is semantically identical to the code it replaced (same resolve precedence, same `InMemoryStore` offline default, same `None` restore; `_run_durable` correctly keeps the borrowed-store default). Each `_tool_map` delegation is equivalent (the retired `CaseSpec`/placeholder carried `inject=None`, so `_tool_map(…, inject=None)` matches the old `build_tools` path exactly). Scoring, routing, gate, audit and queue code are byte-for-byte unchanged.

---

_Verified: 2026-10-13T18:23:19Z_
_Verifier: the agent (gsd-verifier)_
