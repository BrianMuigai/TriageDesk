---
phase: quick
plan: "261013-taj"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/triagedesk/mcp/server.py
  - src/triagedesk/evals/runner.py
  - src/triagedesk/demo/run.py
  - src/triagedesk/evals/tools.py
  - src/triagedesk/evals/__init__.py
  - src/triagedesk/desk/server.py
  - src/triagedesk/desk/__init__.py
  - src/triagedesk/durable.py
  - tests/test_store_seam.py
  - tests/test_desk.py
autonomous: true
requirements: [QUICK-261013]
estimate:
  tokens: 48000
  raw_tokens: 32000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "The store-seam ceremony (resolve-or-use-injected -> install -> restore) exists in exactly ONE place; `evals/runner.py`, `demo/run.py` (the beat loop AND `--durable`) install the store through it and no caller repeats `set_store(x) try/finally set_store(None)`."
    - "`mcp.server.set_store` remains the single write path and `mcp.server.resolve_store` the single resolver; the seam doubles observed by `tests/conftest.py`, `tests/test_observability.py` and `tests/test_review_runbook.py` still govern a run unchanged."
    - "`build_tools(case: CaseSpec, *, offline, recorder)` keeps its exact signature and behaviour, so its 14 direct callers are untouched (pure additive refactor on that side)."
    - "A `CaseInput`-shaped entry point builds the offline tool map with no fabricated `CaseSpec`; `desk/server.py::_tools_for` and `durable.resume_thread` both use it, and `durable._RESUME_PLACEHOLDER` is deleted."
    - "The desk package no longer imports `triagedesk.evals.case` directly, and still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server` (`tests/test_desk.py::test_no_self_commit_path_in_the_desk_package` stays green; `triagedesk.mcp.server` is still reached only transitively via `evals.tools`)."
    - "Behaviour is unchanged: no scoring, routing, gate, audit or queue behaviour changes; the focused test subset is green."
  artifacts:
    - path: src/triagedesk/mcp/server.py
      provides: "`store_seam` async context manager: resolves-or-uses the store, installs it via `set_store`, yields it, and restores `None` in a `finally`."
    - path: src/triagedesk/evals/runner.py
      provides: "`run_eval` installs the store through `store_seam(store, default=InMemoryStore)`; the per-run `resolved_store` is the yielded value."
    - path: src/triagedesk/demo/run.py
      provides: "`_run_durable` installs via `store_seam(store)` and `run_demo` via `store_seam(store, default=InMemoryStore)`; the manual try/finally set_store ceremony is gone."
    - path: src/triagedesk/evals/tools.py
      provides: "One `_tool_map(case: CaseInput, *, offline, inject, recorder)` core with `build_tools` (CaseSpec) and the new `offline_tools(case: CaseInput, recorder)` both delegating to it."
    - path: src/triagedesk/durable.py
      provides: "`_RESUME_PLACEHOLDER` deleted; `resume_thread` builds its mapping from `offline_tools(CaseInput(), UsageRecorder())`; the `evals.case` import is gone."
    - path: src/triagedesk/desk/server.py
      provides: "`_tools_for` uses `offline_tools(case, UsageRecorder())`; the fabricated `CaseSpec` and the `triagedesk.evals.case` import are gone."
    - path: tests/test_store_seam.py
      provides: "Focused unit proof for `store_seam`: injected store installed+yielded, default-factory fallback, resolver fallback, and restore-to-None on exception."
    - path: tests/test_desk.py
      provides: "A sibling guard to `test_no_self_commit_path_in_the_desk_package` asserting no `desk/` module directly imports `triagedesk.evals.case`."
  key_links:
    - "`store_seam` calls `set_store`/`resolve_store` inside `mcp/server.py`; `runner`/`demo` call only `store_seam` — the one install path, no second seam write."
    - "`offline_tools` and `build_tools` share the ONE `_tool_map` core in `evals/tools.py` — the tool mapping is built in one place."
    - "`desk/server.py` -> `evals.tools.offline_tools` only; no desk module imports `evals.case`, `store.queue` or `mcp.server` (desk reaches `mcp.server` transitively, exactly as today)."
    - "`durable.py::resume_thread` -> `evals.tools.offline_tools` (lazy import), with no placeholder `CaseSpec`."
---

<objective>
Collapse two duplications the review surfaced, without changing behaviour: (1) the copy-pasted store-seam ceremony (resolve-or-inject -> `set_store(x)` -> `try/finally set_store(None)`) that appears three times across two modules, and (2) the fabricated throwaway `CaseSpec` that the desk surface and the durable resume path each invent only to satisfy `build_tools`'s harness-shaped signature.

Purpose: Both duplications are DRY violations under the iron-clad rule (`docs/CONVENTIONS.md` §1/§4). The store-seam ceremony has three owners of one concern (install/restore the seam); the fabricated `CaseSpec` forces the desk presentation surface to import the evaluation harness (`triagedesk.evals.case`) purely to build a case it admits is "never read" (`_tools_for` docstring) and to host a placeholder whose terminal is never evaluated (`_RESUME_PLACEHOLDER`). Collapsing both removes the duplication and the false coupling, and leaves every published seam — `mcp.server.set_store`/`resolve_store`, `build_tools` — exactly as it is for the surfaces that already depend on them.

Output: ONE `store_seam` context manager on the seam host (`mcp/server.py`) used by all three installing call sites; ONE `CaseInput`-shaped entry point (`evals/tools.offline_tools`) on the shared tool seam, with `build_tools` delegating to a shared core; `durable._RESUME_PLACEHOLDER` and the desk's fabricated `CaseSpec` deleted; two regression guards added.

This is a behaviour-preserving refactor: no scoring, routing, gate, audit or queue behaviour changes.
</objective>

<execution_context>
@/home/brian/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/brian/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/CONVENTIONS.md
@src/triagedesk/mcp/server.py
@src/triagedesk/evals/runner.py
@src/triagedesk/demo/run.py
@src/triagedesk/evals/tools.py
@src/triagedesk/durable.py
@src/triagedesk/desk/server.py
@tests/conftest.py
@tests/test_desk.py
</context>

<tasks>

<task type="tracer">
  <name>Task 1: One `store_seam` replaces the four-site store-seam ceremony (Finding 1)</name>
  <files>src/triagedesk/mcp/server.py, src/triagedesk/evals/runner.py, src/triagedesk/demo/run.py</files>
  <action>Introduce ONE async context manager on the seam host and route every installing caller through it end-to-end. The hard constraint is that it must be built ON `mcp.server.set_store` (never bypass it) and must NOT add a second resolver — `mcp.server.resolve_store` stays the ONE resolver.

In `src/triagedesk/mcp/server.py`, add `store_seam` immediately after `resolve_store`. Extend the `contextlib`/`collections.abc` imports with `asynccontextmanager` and `AsyncIterator` (`Callable` and `Store` are already imported). Signature: `async def store_seam(store: Store | None = None, *, default: Callable[[], Store] | None = None) -> AsyncIterator[Store]`. Body: resolve once — `store` when not `None`, else `default()` when a caller passed an offline factory, else `await resolve_store()` (the ONE resolver, borrowed default). Then `set_store(resolved)`, `yield resolved`, and in a `finally` `set_store(None)` — restoring `None`, byte-for-byte the current behaviour (do NOT save/restore a prior store; the tests and conftest rely on the `None` reset). Docstring: name it as the ONE place the seam is installed for a block, why the restore always clears (an offline run must never leak an injected double into a later call), and that the resolved store is yielded so a caller reads the same instance it installed.

In `src/triagedesk/evals/runner.py::run_eval` (currently ~lines 462-475), replace the `resolved_store = store if store is not None else InMemoryStore()` line and the `server_module.set_store(resolved_store) / try: / finally: server_module.set_store(None)` block with a single `async with server_module.store_seam(store, default=InMemoryStore) as resolved_store:` wrapping the same `report_cases = [...]` list comprehension (the comprehension keeps passing `store=resolved_store`). Keep the `factory`/`mode` locals exactly as they are.

In `src/triagedesk/demo/run.py::_run_durable` (currently ~lines 223-235), drop the `resolved_store = store if store is not None else await server_module.resolve_store()` line and the manual set/finally; wrap the `run_to_gate(...)` call in `async with server_module.store_seam(store):` (no binding needed — the block only needs the seam installed). `_run_durable`'s store MUST still default to the ONE resolver (`resolve_store`), not in-memory, so pass no `default` here — this preserves the durable pause landing on the borrowed/resolved store.

In `src/triagedesk/demo/run.py::run_demo` (currently ~lines 299-312), replace the `resolved_store = store if store is not None else InMemoryStore()` line and the manual set/try/finally around the beat loop with `async with server_module.store_seam(store, default=InMemoryStore) as resolved_store:` wrapping the `for index, beat in enumerate(...)` loop (the loop keeps passing `store=resolved_store`). The offline default stays `InMemoryStore` so no borrowed `npx mcp-sqlite` subprocess is launched.

Update the docstrings that describe the old manual ceremony so prose matches code: the `demo/run.py` module docstring (~lines 10-13), `_run_durable` (~lines 218-222) and `run_demo` (~lines 279-281) now name `mcp.server.store_seam` instead of the hand-written `set_store(...)`/`finally`. Leave `replay.py` UNCHANGED: it resolves a store read-only and never installs it (it calls no tools), so `resolve_store()` there stays a direct call — this is the intentional non-change and the reason the resolver stays the ONE resolver.

Do not touch `build_tools`, the graph, the scorer, the gate, the audit interceptor or `store/`. This is a pure move of one concern into one place.</action>
  <verify>
    <automated>uv run pytest tests/test_eval_suite.py tests/test_eval_invariants.py tests/test_eval_honest_terminal.py tests/test_eval_tracer.py tests/test_demo.py tests/test_demo_runbook.py tests/test_durable_cli.py tests/test_graph_durable.py tests/test_observability.py tests/test_replay_read_only.py tests/test_review_runbook.py -q</automated>
  </verify>
  <done>An eval run and both demo paths install their store through `store_seam`; no caller repeats the set_store/try/finally ceremony; the eval, demo, durable, observability and replay subsets are green; `build_tools` and `resolve_store` are untouched.</done>
</task>

<task type="auto">
  <name>Task 2: One `offline_tools(CaseInput)` entry point; delete the fabricated harness cases (Finding 2)</name>
  <files>src/triagedesk/evals/tools.py, src/triagedesk/evals/__init__.py, src/triagedesk/desk/server.py, src/triagedesk/desk/__init__.py, src/triagedesk/durable.py</files>
  <action>Add ONE `CaseInput`-shaped entry point to the shared tool seam and make the two non-harness callers use it, so neither fabricates a `CaseSpec`. `build_tools` must keep its exact signature and behaviour — it is a pure additive refactor on that side (14 test files call it directly).

In `src/triagedesk/evals/tools.py`, extract the current `build_tools` body into a private core `_tool_map(case: CaseInput, *, offline: bool, inject: FaultInjection | None, recorder: UsageRecorder) -> dict[str, Any]`. The core takes a `CaseInput` (so the offline branch returns `ExtractionResult(case=case, matched_discriminator_ids=[])`) and an `inject` fault (so the `normalize` wrapper is `normalize_case if inject is None else _injected_normalize(normalize_case, inject)`). The other six tools are unchanged. Then: `build_tools(case: CaseSpec, *, offline: bool, recorder: UsageRecorder) -> dict[str, Any]` becomes a one-line delegate `return _tool_map(case.case, offline=offline, inject=case.inject, recorder=recorder)`; and a new `offline_tools(case: CaseInput, recorder: UsageRecorder) -> dict[str, Any]` is a one-line delegate `return _tool_map(case, offline=True, inject=None, recorder=recorder)`. Keep `_injected_normalize`, `recorded_extract_seam` and `ToolMap` as they are. Add `offline_tools` to `__all__` and update the module docstring to name it as the harness-free entry point (no `CaseSpec` required). In `src/triagedesk/evals/__init__.py`, re-export `offline_tools` from `triagedesk.evals.tools` and add it to `__all__`, so the seam is exported beside `build_tools`.

In `src/triagedesk/desk/server.py`, delete the `from triagedesk.evals.case import TERMINAL_OUTCOMES, CaseSpec` import and change `from triagedesk.evals.tools import build_tools` to `from triagedesk.evals.tools import offline_tools`. Rewrite `_tools_for(case: CaseInput) -> dict[str, Any]` to `return offline_tools(case, UsageRecorder())` and drop the fabricated `CaseSpec(id="desk", ...)` construction and the docstring sentence about the never-read declared terminal. Do NOT add any direct import of `triagedesk.mcp.server` or `triagedesk.store.queue` to the desk package — it must keep reaching `mcp.server` only transitively through `evals.tools`. Update the `src/triagedesk/desk/__init__.py` docstring (~line 6) to name `evals.tools.offline_tools`.

In `src/triagedesk/durable.py`, delete `_RESUME_PLACEHOLDER` (the `CaseSpec(...)` block, ~lines 42-55) and the now-unused `from triagedesk.evals.case import TERMINAL_OUTCOMES, CaseSpec` import. In `resume_thread`, replace `tools = build_tools(_RESUME_PLACEHOLDER, offline=True, recorder=UsageRecorder())` with a lazy `from triagedesk.evals.tools import offline_tools` and `tools = offline_tools(CaseInput(), UsageRecorder())` (`CaseInput` is already imported at module level). Update the `resume_thread` docstring so it no longer refers to a placeholder case/spec.

Keep the `durable` module docstring's claim that it adds no store resolver and resolves through `mcp.server.resolve_store` — that remains true.</action>
  <verify>
    <automated>uv run pytest tests/test_desk.py tests/test_desk_runbook.py tests/test_durable_cli.py tests/test_graph_durable.py tests/test_eval_suite.py tests/test_eval_invariants.py tests/test_eval_honest_terminal.py tests/test_eval_tracer.py tests/test_demo_runbook.py tests/test_observability.py tests/test_replay_read_only.py -q</automated>
  </verify>
  <done>`offline_tools(CaseInput, recorder)` exists and both `build_tools` and `offline_tools` delegate to one `_tool_map` core; the desk builds its mapping with no `CaseSpec` and no `evals.case` import; `durable._RESUME_PLACEHOLDER` is gone and `resume_thread` uses `offline_tools(CaseInput(), UsageRecorder())`; the desk/durable/eval/tool subsets are green.</done>
</task>

<task type="auto">
  <name>Task 3: Lock both collapses with two focused guards</name>
  <files>tests/test_store_seam.py, tests/test_desk.py</files>
  <action>Add regression guards so neither duplication can creep back. No production-code change in this task.

Create `tests/test_store_seam.py` with focused async tests for the new seam (the repo runs `asyncio_mode = "auto"`, so plain `async def` tests work). Cover: (1) an injected store is installed and yielded — `async with server_module.store_seam(injected_store) as resolved: assert resolved is injected_store` and `assert await server_module.resolve_store() is injected_store` inside the block (the autouse `injected_store` fixture provides the double; do not launch the borrowed store); (2) when no store is injected but a `default` factory is given, the factory's instance is yielded and used (`store_seam(default=lambda: made)`); (3) when neither is given, `resolve_store` is consulted — monkeypatch `server_module.resolve_store` with a stub returning a sentinel `InMemoryStore` and assert `store_seam()` yields it; (4) the seam is cleared on exception — monkeypatch `server_module.default_store` with a stub returning a sentinel, raise inside `async with server_module.store_seam(InMemoryStore()):`, and assert that after the block `await server_module.resolve_store() is sentinel` (proving the seam was reset to `None`, not left holding the injected store). Import `InMemoryStore` from `triagedesk.store.memory` and the module as `from triagedesk.mcp import server as server_module`, matching the existing tests' idiom.

In `tests/test_desk.py`, add a sibling to `test_no_self_commit_path_in_the_desk_package` named `test_no_eval_harness_import_in_the_desk_package`: recurse `DESK_DIR.rglob("*.py")`, run each module's source through the existing `resolved_imports(source, package_parts_for(path, SRC_ROOT))`, and assert none resolves to `triagedesk.evals.case` (the harness module the desk no longer needs directly). Reuse the already-imported helpers and constants (`DESK_DIR`, `SRC_ROOT`, `resolved_imports`, `package_parts_for`) — add no new helper and restate nothing. This guard scans direct imports only, so the desk's legitimate transitive reach into `mcp.server`/`evals.case` via `evals.tools` is untouched; it locks only the direct `evals.case` import removed in Task 2.</action>
  <verify>
    <automated>uv run pytest tests/test_store_seam.py tests/test_desk.py -q</automated>
  </verify>
  <done>`store_seam`'s install/yield/default/resolve/restore contract is asserted; the desk package is proven not to import `triagedesk.evals.case` directly; both new guards are green and no existing desk guard regresses.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| caller -> store seam | A refactor moves *who installs* the store, not *what* is installed; `set_store` stays the one write path and `resolve_store` the one resolver. |
| desk package -> its import graph | The desk drops a direct `triagedesk.evals.case` import; the commit-path guard and the new harness-import guard bound what `desk/` may import. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-01 | Tampering | `mcp/server.py::store_seam` | low | accept | The CM only calls the existing `set_store`/`resolve_store`; it adds no new write path and no second resolver, so the seam's single-writer property is unchanged (proven by the store-seam unit tests). |
| T-quick-02 | Tampering | `desk/server.py::_tools_for` | low | accept | The desk still builds the offline-only tool map (model stubbed) and gains no store/queue/commit import; `test_no_self_commit_path_in_the_desk_package` plus the new harness-import guard keep the desk's write-path reach bounded. |
| T-quick-03 | Elevation of Privilege | `evals/tools.py::offline_tools` | low | accept | `offline_tools` is `offline=True` with no injected fault, so it exposes exactly the same seven real owned tools `build_tools` did; the graph's own `assert_tool_allowlist` still gates the mapping at `build_graph`. |
| T-quick-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency is added or changed: `pyproject.toml` and `uv.lock` are untouched, so the package-legitimacy gate has nothing new to admit. |
</threat_model>

<verification>
Run the focused subset that covers the touched surface (this repo carries an extensive structural/guard suite; the whole suite is not needed):

```
uv run pytest tests/test_store_seam.py tests/test_desk.py tests/test_desk_runbook.py tests/test_durable_cli.py tests/test_graph_durable.py tests/test_eval_suite.py tests/test_eval_invariants.py tests/test_eval_honest_terminal.py tests/test_eval_tracer.py tests/test_demo.py tests/test_demo_runbook.py tests/test_observability.py tests/test_replay_read_only.py tests/test_review_runbook.py -q
```

Confirm the duplication is gone (the ceremony and the fabricated cases no longer exist):

```
grep -rn "set_store(None)" src/triagedesk | grep -v "mcp/server.py"
grep -rn "_RESUME_PLACEHOLDER" src tests
grep -rn "from triagedesk.evals.case import" src/triagedesk/desk
```

Each must print nothing. Note `store_seam` itself contains the ONE `set_store(None)` in `src/triagedesk/mcp/server.py`, which the first grep deliberately excludes.

Lint/type sanity on the touched surface (strict mypy + ruff are configured):

```
uv run ruff check src/triagedesk tests/test_store_seam.py tests/test_desk.py
uv run mypy src/triagedesk/mcp/server.py src/triagedesk/evals/tools.py src/triagedesk/desk/server.py src/triagedesk/durable.py
```
</verification>

<success_criteria>
- `mcp/server.py::store_seam` is the ONE place the seam is installed for a block; `evals/runner.py` and both `demo/run.py` sites use it; no other module repeats the set_store/try/finally ceremony.
- `mcp.server.set_store` is still the single write path and `mcp.server.resolve_store` the single resolver; `replay.py` keeps its read-only direct `resolve_store()` call.
- `evals/tools.offline_tools(case: CaseInput, recorder)` exists; `build_tools` keeps its signature and delegates to the shared `_tool_map` core.
- `durable._RESUME_PLACEHOLDER` and the desk's fabricated `CaseSpec` are deleted; the desk imports neither `triagedesk.evals.case`, `triagedesk.store.queue` nor `triagedesk.mcp.server`.
- Scoring, routing, gate, audit and queue behaviour are unchanged; the focused pytest subset is green; the duplication greps print nothing.
- Two guards (`tests/test_store_seam.py`, `test_no_eval_harness_import_in_the_desk_package`) lock the collapses.
</success_criteria>

<output>
Create `.planning/quick/261013-taj-collapse-the-duplicated-store-seam-cerem/261013-taj-SUMMARY.md` when done
</output>
