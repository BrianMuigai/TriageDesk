---
phase: quick
plan: "261013-wjd"
verified: 2026-10-13T21:14:45Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - ".planning/quick/261013-wjd-give-the-outcome-projection-and-the-in-m/261013-wjd-PLAN.md"
  - ".planning/quick/261013-wjd-give-the-outcome-projection-and-the-in-m/261013-wjd-SUMMARY.md"
  - "src/triagedesk/demo/run.py"
  - "src/triagedesk/evals/outcome.py"
  - "src/triagedesk/evals/runner.py"
  - "src/triagedesk/graph/build.py"
covered_digest: "v3:sha256:19e3bbfff813cc7811df7ea200872097925c21287652a4e04e21b7b4a3810605"
behavior_unverified: 0
overrides_applied: 0
human_verification: []
---

# Quick 261013-wjd Verification Report

**Goal:** Give the outcome projection and the in-memory checkpointer one public home instead of private cross-module imports.
**Verified:** 2026-10-13T21:14:45Z
**Status:** passed
**Re-verification:** No — initial verification

**Base commit (pre-task):** `ea6fcd2` (parent of the first task commit `c0882f7`)
**HEAD:** `c15b500`

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | The demo's escalation/refusal beats print byte-identically: `commit : <commit.reason>` and `GATE REFUSED : no queue row written (rows added this beat: N)` unchanged; `_print_outcome`'s format strings untouched. | ✓ VERIFIED | `_print_outcome` extracted from base vs HEAD differs **only** by the call-site rename `_capture(...)` → `capture_outcome(...)`; every `print(...)` string is byte-identical. The REAL demo (`uv run triagedesk demo`) printed `commit       : committed case 9300336d37c3651c at queue position 1 (ORANGE)`, `commit       : clinician dismissed the priority; refusing to commit`, and `GATE REFUSED : no queue row written (rows added this beat: 0)` — matching `docs/DEMO.md:178,214,215` exactly. |
| 2 | `capture_outcome(result, payload)` returns the identical 12-key dict and `error_capture(exc)` the identical fail-closed 12-key dict; both read from ONE public home (`evals/outcome.py`). | ✓ VERIFIED | Programmatic extraction of both `return {...}` blocks from base `_capture`/`_error_capture` and HEAD `capture_outcome`/`error_capture`: **byte-identical** (`capture_outcome return dict identical: True`, `error_capture return dict identical: True`); keys in the same order: `colour, citations, triggered_rules, matched_ids, recovery, escalation, second_look, delivered, route, attempt, confidence, error`. `demo/run.py` and `evals/runner.py` both import from `evals.outcome`. |
| 3 | The in-memory saver is built by ONE public factory (`graph.build.in_memory_checkpointer`) applying the SAME `_allowed_msgpack_modules` allowlist; no PRODUCTION consumer constructs its own `InMemorySaver`/`JsonPlusSerializer`. | ✓ VERIFIED | Factory at `graph/build.py:344`. Runtime: `in_memory_checkpointer()` → `InMemorySaver` whose serde carries a **16-entry** allowlist, `identical allowlists: True` vs the durable `open_checkpointer`, `neither is True: True`. `grep InMemorySaver\|JsonPlusSerializer` in `runner.py`/`demo/run.py` is empty (exit 1). |
| 4 | `demo/run.py` imports neither `triagedesk.evals.runner` nor any private name; `evals/runner.py` imports no private name from `graph.build`; `_allowed_msgpack_modules` referenced only inside `graph/build.py`. | ✓ VERIFIED | Three greps empty at HEAD, each **non-vacuous** (matched at base `ea6fcd2`): `\b(_capture\|_checkpointer)\b` (7 hits at base → 0 now); `from triagedesk.evals.runner import` in `demo/run.py` (1 hit at base → 0 now); `_allowed_msgpack_modules` outside `graph/build.py` (2 hits at base → 0 now; now only `graph/build.py:340,355,373`). |
| 5 | The `graph/` purity/safety guards are unchanged and green. | ✓ VERIFIED | `tests/test_purity.py` and `tests/test_safety_spine.py` pass in the 149-test run. `langgraph` (source of `InMemorySaver`) is in neither `_NETWORK_CLIENTS` nor `NON_LOCAL_MODEL_PROVIDERS`; `graph/` contains no `os.environ`/`getenv`/`.netrc` read (only a docstring mention of "NO environment variable"). |
| 6 | Behaviour unchanged — no scoring/routing/gate/audit/queue change; `desk/` untouched and still imports neither `store.queue` nor `mcp.server`. | ✓ VERIFIED | `git diff --name-status ea6fcd2..HEAD -- src/` lists exactly 4 files: `demo/run.py` (M), `evals/outcome.py` (A), `evals/runner.py` (M), `graph/build.py` (M). `desk/` untouched; `grep store.queue\|mcp.server src/triagedesk/desk/` empty. |
| 7 | No dependency added or changed: `pyproject.toml` and `uv.lock` untouched. | ✓ VERIFIED | `git diff --stat ea6fcd2..HEAD -- pyproject.toml uv.lock` empty. |

**Score:** 7/7 truths verified (0 present-behavior-unverified).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/triagedesk/graph/build.py` | `in_memory_checkpointer()` beside `open_checkpointer`, applying the same private allowlist | ✓ VERIFIED | Exists, substantive, wired (consumed by `runner.py:125`, `demo/run.py:179`); `InMemorySaver` imported from `langgraph.checkpoint.memory`; name added to `__all__` (line 54). |
| `src/triagedesk/evals/outcome.py` | ONE public home: `capture_outcome`, `error_capture` | ✓ VERIFIED | New module; imports only `from __future__ import annotations` + `typing.Any`; `__all__ = ["capture_outcome", "error_capture"]`; bodies byte-identical to base. |
| `src/triagedesk/evals/runner.py` | Imports public names; privates deleted | ✓ VERIFIED | Imports `capture_outcome, error_capture` from `evals.outcome` and `in_memory_checkpointer` from `graph.build`; `_capture`/`_error_capture`/`_checkpointer` and the `InMemorySaver`/`JsonPlusSerializer`/`_allowed_msgpack_modules` imports are gone. |
| `src/triagedesk/demo/run.py` | Imports `capture_outcome` + `in_memory_checkpointer`; no runner import | ✓ VERIFIED | Line 30 `from triagedesk.evals.outcome import capture_outcome`; line 33 imports `in_memory_checkpointer`; the runner import line is gone (only a prose mention of `evals.runner.run_eval` remains in the docstring — not an import). |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `demo/run.py::_print_outcome` | `evals.outcome.capture_outcome` | call site line 134 | ✓ WIRED | Confirmed by import + call site; demo runs end-to-end. |
| `demo/run.py::_run_beat` | `graph.build.in_memory_checkpointer` | call site line 179 | ✓ WIRED | Graph built through the public factory. |
| `evals/runner.py` | `evals.outcome.capture_outcome` + `error_capture`; `graph.build.in_memory_checkpointer` | imports lines 31, 43 | ✓ WIRED | Public cross-module imports only. |
| `graph.build.in_memory_checkpointer` | `_allowed_msgpack_modules` inside `graph/build.py` | line 355 | ✓ WIRED | Runtime: serde carries the 16-entry allowlist; allowlist's only referencers are inside its owner. |

### Data-Flow Trace (Level 4)

Not applicable — this is a behaviour-preserving move of helpers. The projection still reads the graph's own typed channels (`result`/`payload` passed in by the caller); no rendered value's data source changed. Verified instead by the byte-identical return-dict comparison and the live demo output.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Factory returns a msgpack-allowlisted `InMemorySaver` | `uv run python -c "from triagedesk.graph.build import in_memory_checkpointer; ..."` | `is InMemorySaver: True`, serde `JsonPlusSerializer`, 16-entry allowlist, not `True` | ✓ PASS |
| In-memory and durable allowlists are identical | async compare `in_memory_checkpointer()` vs `open_checkpointer()` | `identical allowlists: True`, neither `True` | ✓ PASS |
| The REAL demo runs offline end-to-end | `uv run triagedesk demo` | exit 0; pinned `commit :` / `GATE REFUSED :` lines match `docs/DEMO.md` | ✓ PASS |
| HEAD tree imports the demo package | `uv run pytest tests/test_demo.py` (in 149-test run) | pass | ✓ PASS |

### Probe Execution

Not applicable — the plan declares no probes and this is not a migration/tooling phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| QUICK-261013 | `261013-wjd-PLAN.md` | One public home for the outcome projection + in-memory checkpointer; retire the three private cross-module names | ✓ SATISFIED | All 7 truths verified; three greps empty (non-vacuous); 149-test named subset green. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers in any touched file | — | Clean |
| (commit `3e68e9a`) | — | **Bisect-hostile intermediate commit** — see below | ⚠️ Warning | Does not affect HEAD; see narrative |

### Guard Evidence (read, not assumed)

- `tests/test_safety_spine.py::test_graph_imports_no_external_network_client_or_model_provider` scans every `graph/*.py` import root against `_NETWORK_CLIENTS = {requests, httpx, urllib3, aiohttp, socket, http}` ∪ `NON_LOCAL_MODEL_PROVIDERS = {openai, anthropic, google, cohere, mistralai, azure, boto3, vertexai}`. `InMemorySaver`'s root is `langgraph` — in neither set. Passes.
- `tests/test_safety_spine.py::test_graph_reads_no_credentials` AST-walks `graph/*.py` for `environ`/`getenv`/`.netrc`. The only textual hit is the docstring at `build.py:206` ("reads NO environment variable"), which is not an AST attribute/name/`.netrc`-constant. Passes.

### Human Verification Required

None. Every must-have is programmatically verifiable and was verified against live source plus a real end-to-end demo run.

### Gaps Summary

No gaps. All 7 must-haves are VERIFIED against the live codebase at HEAD; the phase goal (one public home for the projection and the in-memory checkpointer, with the three private cross-module names retired) is achieved. The 149-test named subset is green; `ruff check` is clean on all four touched files; mypy introduces no new errors.

## Executor's Flagged Deviation — CONFIRMED (reported, not fixed)

The executor's SUMMARY notes a transient break between the Task 2 and Task 3 commits. **This is true.** Materialised the tree at each task commit and attempted the import:

| Commit | Task | `import triagedesk.demo.run` |
| ------ | ---- | --------------------------- |
| `c0882f7` | Task 1 | `IMPORT OK` |
| `3e68e9a` | Task 2 | **`ImportError: cannot import name '_capture' from 'triagedesk.evals.runner'`** |
| `c15b500` (HEAD) | Task 3 | OK (149 tests pass; demo runs) |

**Finding (commit hash `3e68e9a`):** At Task 2 the runner deleted `_capture`, but `demo/run.py` still imported `_capture` from it (Task 1 had only dropped `_checkpointer`); the fix landed in Task 3. The tree at `3e68e9a` is therefore **bisect-hostile** for any bisect that imports/executes the demo package (e.g. `tests/test_demo.py`, `uv run triagedesk demo`) — that command fails at `3e68e9a`. A bisect that runs only the Task-2 verify subset (which does not exercise the demo) would still be green, so the impact is partial. HEAD is green. **Not fixed** per instructions.

---

_Verified: 2026-10-13T21:14:45Z_
_Verifier: gsd-verifier (goal-backward, adversarial)_
