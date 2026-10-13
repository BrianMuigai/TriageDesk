---
phase: quick
plan: "261013-wjd"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/triagedesk/graph/build.py
  - src/triagedesk/evals/outcome.py
  - src/triagedesk/evals/runner.py
  - src/triagedesk/demo/run.py
autonomous: true
requirements: [QUICK-261013]
estimate:
  tokens: 46000
  raw_tokens: 30000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "The demo's escalation and refusal beats print byte-identically: `commit       : <commit.reason>` and `GATE REFUSED : no queue row written (rows added this beat: N)` are unchanged — `_print_outcome`'s format strings are untouched."
    - "`capture_outcome(result, payload)` returns the identical 12-key dict (`colour`, `citations`, `triggered_rules`, `matched_ids`, `recovery`, `escalation`, `second_look`, `delivered`, `route`, `attempt`, `confidence`, `error`) with identical values to the old `_capture`, and `error_capture(exc)` returns the identical fail-closed 12-key dict the old `_error_capture` did; both the eval runner and the demo read them from ONE public home (`evals/outcome.py`)."
    - "The in-memory checkpointer is built by ONE public factory (`graph.build.in_memory_checkpointer`) that applies the SAME `_allowed_msgpack_modules` allowlist as the durable saver; no PRODUCTION consumer (`evals/runner.py`, `demo/run.py`) constructs its own `InMemorySaver`/`JsonPlusSerializer`. Tests are out of scope for this truth — several test modules legitimately build a bare `InMemorySaver()` as a test double (e.g. `tests/test_graph_purity.py:72`)."
    - "`demo/run.py` imports neither `triagedesk.evals.runner` nor any private name; `evals/runner.py` imports no private name from `graph.build`; `_allowed_msgpack_modules` is referenced only inside `graph/build.py` (its owner)."
    - "The `graph/` purity/safety guards are unchanged and green: `tests/test_purity.py` and `tests/test_safety_spine.py` pass with `InMemorySaver` added to `graph/build.py` (root `langgraph` is neither a network client nor a non-local model provider)."
    - "Behaviour is unchanged — no scoring, routing, gate, audit or queue change; the `desk/` package is untouched and still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server`."
    - "No dependency is added or changed: `pyproject.toml` and `uv.lock` are untouched."
  artifacts:
    - path: src/triagedesk/graph/build.py
      provides: "`in_memory_checkpointer()` — the public in-memory flavour of the ONE msgpack-allowlisted saver, sitting beside `open_checkpointer` (durable) and applying the same private `_allowed_msgpack_modules` allowlist."
    - path: src/triagedesk/evals/outcome.py
      provides: "The ONE public home for the run-outcome projection contract: `capture_outcome(result, payload)` and `error_capture(exc)`, both returning the same 12-key captured-outcome dict."
    - path: src/triagedesk/evals/runner.py
      provides: "Imports `capture_outcome`/`error_capture` from `evals.outcome` and `in_memory_checkpointer` from `graph.build`; `_capture`, `_error_capture`, `_checkpointer` and the `_allowed_msgpack_modules` import are deleted."
    - path: src/triagedesk/demo/run.py
      provides: "Imports `capture_outcome` from `evals.outcome` and `in_memory_checkpointer` from `graph.build`; the `from triagedesk.evals.runner import _capture, _checkpointer` line is gone."
  key_links:
    - "`demo/run.py::_print_outcome` -> `evals.outcome.capture_outcome` (one projection home, no eval-runner import)."
    - "`demo/run.py::_run_beat` -> `graph.build.in_memory_checkpointer` (one saver home, no private `_checkpointer`)."
    - "`evals/runner.py` -> `evals.outcome.capture_outcome` + `error_capture` and -> `graph.build.in_memory_checkpointer` (public cross-module imports only)."
    - "`graph.build.in_memory_checkpointer` -> `_allowed_msgpack_modules` inside `graph/build.py` — the ONE allowlist; once Task 2 removes the runner's import, its owner is its only referencer."
---

<objective>
Give the run-outcome projection and the in-memory checkpointer ONE public home each, eliminating three private names that currently cross module boundaries: `_capture` and `_checkpointer` (defined in `evals/runner.py`, privately imported by `demo/run.py:30`) and `_allowed_msgpack_modules` (defined in `graph/build.py:356`, privately imported by `evals/runner.py:45`).

Purpose: `demo/run.py` is packaging that depends on the eval runner's internals, and `evals/runner.py` reaches into `graph.build`'s internals. Each is a cross-module dependency on a name its owner marked private — a SOLID dependency-inversion leak (`docs/CONVENTIONS.md` §2-D: depend on the published interface, not the concrete private name) and an interface-segregation leak (§2-I: a consumer reaches only the surface it needs). `graph/build.py` already owns the durable saver (`open_checkpointer`) AND the msgpack allowlist (`_allowed_msgpack_modules`); the in-memory flavour belongs beside it so there is ONE home for "a msgpack-allowlisted saver" in both flavours. The outcome projection is read by BOTH the eval runner and the demo, so it belongs in a module that is neither of them.

Output: ONE public `graph.build.in_memory_checkpointer()`; ONE public projection home `evals/outcome.py` exporting `capture_outcome`/`error_capture`; `demo/run.py` no longer imports the eval runner; `evals/runner.py` imports only public names; `_allowed_msgpack_modules` stays private and used only inside `graph/build.py`.

This is a behaviour-preserving refactor of WHERE the helpers live, not WHAT they compute or print: the projected dict's keys and values are identical, and every demo line is byte-identical.
</objective>

<execution_context>
@/home/brian/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/brian/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/CONVENTIONS.md
@AGENTS.md
@src/triagedesk/evals/runner.py
@src/triagedesk/demo/run.py
@src/triagedesk/graph/build.py
@tests/test_purity.py
@tests/test_safety_spine.py
</context>

<tasks>

<task type="tracer">
  <name>Task 1: The in-memory checkpointer gets ONE public home in `graph/build.py`, consumed end-to-end by the demo</name>
  <files>src/triagedesk/graph/build.py, src/triagedesk/demo/run.py</files>
  <action>Give the in-memory saver ONE public factory on its owner and prove it end-to-end through a real consumer. `graph/build.py` already owns the durable saver (`open_checkpointer`, ~line 328) and the ONE msgpack allowlist (`_allowed_msgpack_modules`, ~line 356) which `open_checkpointer` applies via `JsonPlusSerializer` (~line 338). The in-memory flavour belongs next to it so both flavours of "a msgpack-allowlisted saver" live in one module.

In `src/triagedesk/graph/build.py`, add an import `from langgraph.checkpoint.memory import InMemorySaver` beside the existing `langgraph.checkpoint.serde.jsonplus` / `langgraph.checkpoint.sqlite.aio` imports, and add a public function `in_memory_checkpointer() -> InMemorySaver` placed immediately after `open_checkpointer` (so the durable and in-memory saver factories sit together). Body: return `InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules()))` — the exact construction currently in `evals/runner.py::_checkpointer` (~lines 198-200), so the allowlist is applied once and never `True`. Docstring: name it as the in-memory flavour of the ONE saver factory, state it carries the SAME allowlist as `open_checkpointer` (so the eval/demo resume cannot trip the future strict-msgpack block), and that an allowlist — never `True` — is deliberate. Add `"in_memory_checkpointer"` to the module `__all__` (alphabetically, beside `checkpointed_graph`/`open_checkpointer`). Keep `_allowed_msgpack_modules` PRIVATE — it stays defined and used inside `graph/build.py` only. Note the end-state claim (the allowlist is referenced nowhere else) is asserted at Task 2's boundary, not here: `evals/runner.py` still imports and calls it (`runner.py:45`, `runner.py:199`) until Task 2 removes that import, so do not claim it in this task.

Do NOT touch `graph/__init__.py`: `open_checkpointer` is not re-exported there either, and every consumer imports from `triagedesk.graph.build` directly. Do NOT weaken or edit any guard.

In `src/triagedesk/demo/run.py`, rewire the ONE saver call site so the demo runs through the new public home: change the `from triagedesk.graph.build import CHECKPOINTS_DB_PATH, build_graph` import (~line 33) to also import `in_memory_checkpointer`, and change `graph = build_graph(_traced_tools(tools, _print_tool_call), checkpointer=_checkpointer())` (~line 178) to call `checkpointer=in_memory_checkpointer()`. Also drop `_checkpointer` from the `from triagedesk.evals.runner import _capture, _checkpointer` line (~line 30) so it becomes `from triagedesk.evals.runner import _capture` — the private `_capture` import is removed in Task 3. Do NOT change any printed string: `_print_outcome`'s format strings (including `commit       : {commit.reason}` and `GATE REFUSED : no queue row written (rows added this beat: {rows_added})`) are byte-identical and out of scope.

Confirm the guards before finishing: `InMemorySaver` comes from `langgraph.checkpoint.memory` (root `langgraph`), which is neither in `tests/test_safety_spine.py`'s `_NETWORK_CLIENTS` (`requests, httpx, urllib3, aiohttp, socket, http`) nor `tests/conftest.py`'s `NON_LOCAL_MODEL_PROVIDERS`, and `graph/build.py` reads no `os.environ`/`getenv`/`.netrc` — so `test_safety_spine.py` and `test_purity.py` stay green. This is additive on the graph side: no node, router, edge or scorer changes.</action>
  <verify>
    <automated>uv run python -c "from langgraph.checkpoint.memory import InMemorySaver; from triagedesk.graph.build import in_memory_checkpointer; s = in_memory_checkpointer(); assert isinstance(s, InMemorySaver); assert s.serde is not None" && uv run pytest tests/test_demo.py tests/test_graph_purity.py tests/test_graph_durable.py tests/test_replay_read_only.py tests/test_purity.py tests/test_safety_spine.py -q</automated>
  </verify>
  <done>`graph.build.in_memory_checkpointer()` exists and returns an `InMemorySaver` carrying a `JsonPlusSerializer`; `demo/run.py::_run_beat` builds its graph through it; the demo runs end-to-end and the graph purity/safety/durable/replay subsets are green. (The allowlist's end-state — `_allowed_msgpack_modules` referenced only inside `graph/build.py` — is asserted at Task 2, which removes the runner's import.)</done>
</task>

<task type="auto">
  <name>Task 2: The outcome projection gets ONE public home (`evals/outcome.py`); the runner stops importing private names</name>
  <files>src/triagedesk/evals/outcome.py, src/triagedesk/evals/runner.py</files>
  <action>Move the run-outcome projection into ONE public home that is NOT the eval runner, and make the runner consume it plus the new public saver factory. Both projections belong in the one module because they return the SAME 12-key captured-outcome contract: keeping them together preserves the single representation of that contract (DRY — `docs/CONVENTIONS.md` §1) rather than splitting the shape across two modules. `_error_capture` is used only by the runner today, but it projects the same contract, so it moves with `_capture`.

Create `src/triagedesk/evals/outcome.py`. Module docstring: name it as the ONE home for the run-outcome projection contract (the 12-key dict of graph terminal facts), consumed by the eval runner and the demo. It imports only `from __future__ import annotations` and `from typing import Any` — it depends on no graph, store or model module (it reads objects passed in). Move the body of `evals/runner.py::_capture` (~lines 60-111) VERBATIM into `def capture_outcome(result: Any, payload: dict[str, Any] | None) -> dict[str, Any]:` — keep the docstring and every expression identical so the keys and values are byte-identical (the demo reads `captured['colour']`, `captured['matched_ids']`, `captured['citations']`; the runner and its tests read the same shape). Move the body of `evals/runner.py::_error_capture` (~lines 151-173) VERBATIM into `def error_capture(exc: Exception) -> dict[str, Any]:` — keep the fail-closed 12-key dict identical; where its docstring cross-referenced `:func:`_outcome``, reference the runner's first-class-outcome mapping by name without asserting co-location. Add `__all__ = ["capture_outcome", "error_capture"]`.

In `src/triagedesk/evals/runner.py`: add `from triagedesk.evals.outcome import capture_outcome, error_capture` with the other `triagedesk.evals.*` imports (between the `evals.invariants` and `evals.report` imports). Change `from triagedesk.graph.build import _allowed_msgpack_modules, build_graph` (~line 45) to `from triagedesk.graph.build import build_graph, in_memory_checkpointer` — the private allowlist import is gone. Delete the now-dead `from langgraph.checkpoint.memory import InMemorySaver` and `from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer` imports (~lines 23-24): after `_checkpointer` is deleted they are used nowhere else in the file. Delete `_capture` (~60-111), `_error_capture` (~151-173) and `_checkpointer` (~191-200). Rewire the three call sites: `graph = build_graph(tools, checkpointer=_checkpointer())` (~line 218) -> `checkpointer=in_memory_checkpointer()`; `return _capture(result, payload), latency, result` (~line 228) -> `capture_outcome(result, payload)`; `captured = _error_capture(exc)` (~line 342) -> `error_capture(exc)`.

Leave `_outcome` (the first-class-outcome mapping, ~line 114), `_errored_invariant_report`, `_fold_invariants`, `_build_gate`, `_run_once`, `_evidence`, `_run_case` and `run_eval` unchanged except for the three rewired call sites above. Do NOT change any scoring, routing, gate, audit or queue behaviour, and do NOT touch `tests/`.</action>
  <verify>
    <automated>uv run pytest tests/test_eval_suite.py tests/test_eval_tracer.py tests/test_eval_invariants.py tests/test_eval_honest_terminal.py tests/test_eval_fidelity.py tests/test_eval_report.py tests/test_purity.py tests/test_safety_spine.py -q && ! grep -n "_allowed_msgpack_modules" src/triagedesk/evals/runner.py</automated>
  </verify>
  <done>`evals/outcome.py` exports `capture_outcome` and `error_capture` with identical keys/values; `evals/runner.py` imports both plus `in_memory_checkpointer` and contains no `_capture`/`_error_capture`/`_checkpointer`/`_allowed_msgpack_modules`/`InMemorySaver`/`JsonPlusSerializer` reference; the eval, purity and safety subsets are green; `_allowed_msgpack_modules` is referenced only inside `graph/build.py` (its owner).</done>
</task>

<task type="auto">
  <name>Task 3: The demo consumes both public homes and no longer imports the eval runner</name>
  <files>src/triagedesk/demo/run.py</files>
  <action>Finish the demo's decoupling so it depends only on public surfaces. In `src/triagedesk/demo/run.py`, replace the remaining private import `from triagedesk.evals.runner import _capture` (~line 30) with `from triagedesk.evals.outcome import capture_outcome` — the demo must import NOTHING from `triagedesk.evals.runner`. Rewire the ONE projection call site: `captured = _capture(result, payload)` (~line 134) -> `captured = capture_outcome(result, payload)`. `in_memory_checkpointer` was already wired in Task 1.

Do NOT change any printed line. `_print_outcome`'s format strings are pinned by `docs/DEMO.md` and the demo tests: in particular `print(f"  commit       : {commit.reason}")` and `print(f"  GATE REFUSED : no queue row written (rows added this beat: {rows_added})")` must come out byte-identical, and the demo must still display the substrate's `commit.reason` (it shows exactly what the graph returned) and measure the queue-row delta to prove a refusal wrote nothing. This task moves WHERE the projection helper lives, never what the demo prints.

The module docstring's prose mention of `evals.runner.run_eval` (as a sibling that installs the store the same way) is not an import and may stay. Do NOT touch `desk/`, the graph, the scorer, the gate, the audit interceptor or `store/`.</action>
  <verify>
    <automated>uv run pytest tests/test_demo.py tests/test_demo_runbook.py tests/test_durable_cli.py tests/test_review_runbook.py tests/test_purity.py tests/test_safety_spine.py -q && ! grep -rn "from triagedesk.evals.runner import" src/triagedesk/demo/run.py && ! grep -rnE "\b(_capture|_checkpointer)\b" src/triagedesk --include=*.py && ! grep -rn "store.queue\|mcp.server" src/triagedesk/desk/ --include=*.py</automated>
  </verify>
  <done>`demo/run.py` imports `capture_outcome` from `evals.outcome` and `in_memory_checkpointer` from `graph.build`, and imports nothing from `evals.runner`; the demo, runbook, durable-CLI and review-runbook subsets are green; no private `_capture`/`_checkpointer` name remains anywhere under `src/triagedesk`; the desk package still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server`.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| consumer -> helper module | A refactor moves *where* a helper lives, not *what* it computes; no untrusted input crosses a new boundary and no privilege changes. |
| `graph/` -> its import graph | `InMemorySaver` (root `langgraph`) is added to `graph/build.py`; the safety-spine AST guard bounds what `graph/` may import/read and is unchanged. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-01 | Tampering | `graph/build.py::in_memory_checkpointer` | low | accept | The factory constructs the SAME `JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())` as the durable saver — an allowlist, never `True` — so the in-memory saver's deserialisation surface is unchanged from today's `_checkpointer`; no checkpoint becomes able to deserialise an arbitrary type. |
| T-quick-02 | Information Disclosure | `evals/outcome.py::capture_outcome` | low | accept | The projection reads the graph's own typed channels and re-derives nothing; the keys/values are byte-identical to `_capture`, so no new fact (colour, citation, confidence) is exposed and none is dropped. |
| T-quick-03 | Elevation of Privilege | `evals/runner.py` imports | low | accept | The runner now imports only public names (`capture_outcome`, `error_capture`, `in_memory_checkpointer`); it gains no new capability and no store/queue write path. |
| T-quick-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency is added or changed: `pyproject.toml` and `uv.lock` are untouched, so the package-legitimacy gate has nothing new to admit. |
</threat_model>

<verification>
Run the FULL set of guard and consumer suites named for this task (this repo carries an extensive structural suite; this subset is the touched surface plus the guards that constrain it):

```
uv run pytest tests/test_demo.py tests/test_demo_runbook.py tests/test_durable_cli.py tests/test_purity.py tests/test_safety_spine.py tests/test_review_runbook.py tests/test_eval_suite.py tests/test_eval_tracer.py tests/test_eval_invariants.py tests/test_eval_honest_terminal.py tests/test_eval_fidelity.py tests/test_eval_report.py tests/test_graph_durable.py tests/test_replay_read_only.py tests/test_graph_purity.py tests/test_observability.py tests/test_graph_tracer.py -q
```

Every importer of the three privates and of `evals.runner`/`graph.build` was grepped and named above; the eval-runner suites (`test_eval_suite.py`, `test_eval_tracer.py`, `test_eval_invariants.py`, `test_eval_honest_terminal.py`, `test_eval_fidelity.py`, `test_eval_report.py`) and the graph/observability suites (`test_observability.py`, `test_graph_durable.py`, `test_replay_read_only.py`, `test_graph_tracer.py`, `test_graph_purity.py`) that consume `_capture`/the checkpointer are all in the command. No test imports `_capture`, `_checkpointer` or `_allowed_msgpack_modules` directly (grep confirmed), so no test source changes are required.

Confirm the smell is gone — each grep must print nothing:

```
grep -rnE "\b(_capture|_checkpointer)\b" src/triagedesk --include=*.py
grep -rn "from triagedesk.evals.runner import" src/triagedesk/demo/run.py
grep -rn "_allowed_msgpack_modules" src/triagedesk --include=*.py | grep -v "graph/build.py"
```

The word-boundary pattern deliberately does NOT match the public names `open_checkpointer`/`in_memory_checkpointer` (underscore is a word character, so there is no boundary inside them). The third grep proves the allowlist is used only by its owner `graph/build.py`; the first proves no private name remains; the second proves the demo no longer imports the runner.

Lint/type sanity on the touched surface (strict ruff + mypy are configured):

```
uv run ruff check src/triagedesk/graph/build.py src/triagedesk/evals/outcome.py src/triagedesk/evals/runner.py src/triagedesk/demo/run.py
uv run mypy src/triagedesk/graph/build.py src/triagedesk/evals/outcome.py src/triagedesk/evals/runner.py src/triagedesk/demo/run.py
```
</verification>

<success_criteria>
- `graph/build.py::in_memory_checkpointer()` is the ONE public in-memory saver factory, carrying the same `_allowed_msgpack_modules` allowlist as `open_checkpointer`; the PRODUCTION consumers (`evals/runner.py` and `demo/run.py`) both build their in-memory saver through it and neither constructs its own `InMemorySaver`/`JsonPlusSerializer` (test modules that build a bare `InMemorySaver()` as a test double are out of scope).
- `evals/outcome.py` is the ONE public home for the run-outcome projection (`capture_outcome`, `error_capture`), returning the identical 12-key dict; both the eval runner and the demo consume it.
- `demo/run.py` imports nothing from `triagedesk.evals.runner` and no private name; `evals/runner.py` imports no private name from `graph.build`; `_allowed_msgpack_modules` is referenced only inside `graph/build.py`.
- The projected dict's keys and values are byte-identical, and every demo printed line (including `commit       : {commit.reason}` and `GATE REFUSED : no queue row written (rows added this beat: N)`) is unchanged.
- The `graph/` purity/safety guards are unchanged and green; the `desk/` package is untouched and still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server`.
- No dependency is added or changed; scoring, routing, gate, audit and queue behaviour are unchanged; the full named pytest subset is green and the three greps print nothing.
</success_criteria>

<output>
Create `.planning/quick/261013-wjd-give-the-outcome-projection-and-the-in-m/261013-wjd-SUMMARY.md` when done
</output>
