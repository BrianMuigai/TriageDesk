---
phase: 07-local-observability-span-tracing-read-only-replay
plan: 01
subsystem: observability
tags: [span-tracing, jsonl, contextvars, trace-id, audit-chain, offline, langsmith, borrowed-store]

requires:
  - phase: 06-durable-execution-idempotent-gate
    provides: content-derived identity (case_id_for == derive_thread_id), the checkpointed graph, the ONE audit interceptor
provides:
  - ONE local span writer (observability/spans.emit_span) + span(kind, name) context manager
  - per-task trace/span context (observability/context: bind_trace/current_trace_id/push_span/pop_span/current_parent_id)
  - first-class AuditRecord.trace_id (content-derived, digest-sealed) persisted through the borrowed audit table
  - tool/node/model span emission at the three existing seams
  - observability/offline.harden_offline — the asserted no-egress guard, called at CLI startup
affects: [07-02 read-only replay, 08 calibration, 09 retrieval]

actuals:
  tokens: 7429
  tasks: 3
  commits: 3

tech-stack:
  added: []  # no new dependency (stdlib only: contextvars, json, time, uuid, datetime, pathlib, os)
  patterns:
    - "ONE writer per concern: emit_span is the only function that writes a span line (mirrors audit.append)"
    - "ONE content derivation: case_id_for(raw_note.strip()) is both the thread_id and the span trace_id"
    - "contextvars for per-asyncio-task trace + span-stack isolation (no cross-run leak)"
    - "injectable module-global seam set_sink (mirrors mcp.server.set_store) redirected to tmp_path in tests"

key-files:
  created:
    - src/triagedesk/observability/__init__.py
    - src/triagedesk/observability/spans.py
    - src/triagedesk/observability/context.py
    - src/triagedesk/observability/offline.py
    - tests/test_observability.py
  modified:
    - src/triagedesk/store/audit.py
    - src/triagedesk/store/borrowed.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/llm/client.py
    - src/triagedesk/cli.py
    - tests/conftest.py
    - .gitignore

key-decisions:
  - "trace_id is content-derived (case_id_for(note.strip())) — one case, one trace across restart and replay; never a random uuid (D7-05)"
  - "trace_id is a first-class AuditRecord field (defaulted, sealed by record_digest), not a key buried in inputs/outputs (D7-06)"
  - "the borrowed audit table needs all FOUR coordinated edits (DDL, idempotent ALTER, INSERT columns/values, SELECT) or the field is silently dropped on the production store (Pitfall 1)"
  - "node spans wrap the callables in build_graph's add_node loop with functools.wraps; node bodies and topology are unchanged"
  - "all environment logic lives in observability/offline.py, OUTSIDE graph/, so the safety-spine AST guards stay green (D7-04)"
  - "harden_offline pops the four tracer vars + clears langsmith's cached env read + asserts tracing_is_enabled() is False; it mutates no process-wide tracer flag (see Deviations)"

patterns-established:
  - "Span tree: trace_id + span_id + parent_id + kind(tool|node|model) + start/end, joined to the audit by the shared trace_id (D7-07)"
  - "Minimal model-span attributes only (model tag + token counts); never the note/prompt/completion (D7-08)"
  - "Assert-at-startup for an egress property: the assertion (tracing_is_enabled() is False) IS the proof (D7-03/D7-14)"

requirements-completed: [AGENT-04]

coverage:
  - id: D1
    description: "Tool/node/model spans are appended to ONE local JSONL sink with no network; a node span parents its tool span"
    requirement: AGENT-04
    verification:
      - kind: unit
        ref: "tests/test_observability.py#test_audit_trace_id_round_trips_through_the_borrowed_store"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_node_spans_carry_the_content_trace_id"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_model_span_carries_no_prompt_text"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_offline_run_emits_no_model_span"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_no_spans_artifact_is_written_to_the_repo_root"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every audit record carries a first-class content-derived trace_id that round-trips through the production (borrowed SQLite) store"
    requirement: AGENT-04
    verification:
      - kind: unit
        ref: "tests/test_observability.py#test_audit_trace_id_round_trips_through_the_borrowed_store"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_trace_id_defaults_empty_and_is_sealed_by_the_digest"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_verify_stays_valid_for_a_chain_carrying_trace_ids"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cloud tracing is provably disabled at CLI startup; the run stays hermetic"
    requirement: AGENT-04
    verification:
      - kind: unit
        ref: "tests/test_observability.py#test_harden_offline_asserts_tracing_is_disabled"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_harden_offline_disables_a_primed_tracer"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_harden_offline_is_import_safe_without_langsmith"
        status: pass
      - kind: integration
        ref: "uv run triagedesk demo"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-12
status: complete
---

# Phase 7 Plan 01: Local Observability — Span Tracing Summary

**One local JSONL span writer (tool/node/model spans) plus a first-class, content-derived `trace_id` that joins every audit record to its spans through the borrowed SQLite store, with cloud tracing provably inert.**

## Performance

- **Duration:** ~8 min (commit window)
- **Started:** 2026-10-12T16:10:44+03:00
- **Completed:** 2026-10-12T16:18:01+03:00
- **Tasks:** 3
- **Files modified:** 13 (5 created, 8 modified)

## Accomplishments

- **The `observability/` package** (stdlib only, no new dependency): `spans.py` (the ONE writer `emit_span` + the `span(kind, name)` context manager + the injectable `set_sink` seam), `context.py` (the per-task `contextvars` trace id and span stack), `offline.py` (`harden_offline`), and a barrel `__init__.py` that never imports `offline`.
- **`trace_id` widened additively** on `AuditRecord` (defaulted `""`, sealed by the unchanged `record_digest`) and persisted through **all four** borrowed-store edits — DDL, idempotent guarded `ALTER TABLE`, INSERT columns/values, SELECT — so the field is not silently dropped on the production store (the InMemoryStore double would have hidden that).
- **Tool spans** emitted in the ONE `@audited` interceptor (audit behaviour byte-equivalent + the new `trace_id` + one span); **node spans** via `_spanned` in `build_graph`'s `add_node` loop with `functools.wraps` (topology and node bodies untouched); **model spans** inside `llm/client.extract` with minimal attributes (model tag + token counts only).
- **`harden_offline()`** pops the four tracer vars plus the OTLP endpoints, clears `langsmith.utils.get_env_var`'s `lru_cache`, and asserts `tracing_is_enabled() is False`; it runs at every CLI startup, and all environment logic stays OUTSIDE `graph/`.
- **266 tests green** (255 baseline + 11 new); the test suite writes no repo-root `spans.jsonl`.

## Task Commits

Each task was committed atomically:

1. **Task 1: ONE span writer + trace context → a tool span joined to its audit record through the production store** — `658269e` (feat)
2. **Task 2: Node spans at the composition root + model spans at the ONE model boundary** — `e32fea1` (feat)
3. **Task 3: Offline hardening module + the asserted no-egress guard at CLI startup** — `5b8a5d3` (feat)

**Plan metadata:** skipped (see `commit_docs` note below).

## Files Created/Modified

- `src/triagedesk/observability/spans.py` — NEW: `SPANS_PATH`, `emit_span` (the ONE writer), `span` context manager, `set_sink`.
- `src/triagedesk/observability/context.py` — NEW: `bind_trace`, `current_trace_id`, `push_span`, `pop_span`, `current_parent_id` (`contextvars`).
- `src/triagedesk/observability/offline.py` — NEW: `harden_offline` (the D7-03 guard).
- `src/triagedesk/observability/__init__.py` — NEW: re-exports the writer + trace context; never imports `offline`.
- `src/triagedesk/store/audit.py` — `AuditRecord.trace_id: str = ""` (additive; digest-sealed).
- `src/triagedesk/store/borrowed.py` — audit `trace_id` column: `_AUDIT_DDL`, `_AUDIT_TRACE_ID_MIGRATION` + guarded `ensure_schema`, INSERT columns/values, SELECT.
- `src/triagedesk/mcp/server.py` — tool span in the `@audited` wrapper; `trace_id` in the `record()` append mapping.
- `src/triagedesk/graph/build.py` — `_spanned` node wrapper applied in the `add_node` loop.
- `src/triagedesk/llm/client.py` — model span around the ONE `ollama.generate` call.
- `src/triagedesk/cli.py` — `harden_offline()` at `main` startup.
- `tests/conftest.py` — autouse `_spans_sink` fixture (redirects the sink to `tmp_path`).
- `tests/test_observability.py` — NEW proof suite (11 tests: A–I).
- `.gitignore` — `spans.jsonl` in the runtime-artefacts block.

## Decisions Made

- **Reused the ONE content derivation** (`case_id_for(note.strip())`, == `derive_thread_id`) as the trace root — one case, one trace across restart and replay; no random uuid and no second hash.
- **Applied the node wrapper at the composition root** (`build_graph`) rather than in node bodies, so node single-responsibility and the topology stayed untouched (the plan's discretion explicitly allowed either).
- **Made the four borrowed-store edits together** and proved the round-trip on a real `sqlite3`-backed fake — the double would pass even when the production store silently dropped the field.
- **Kept all environment logic in `observability/offline.py`** (outside `graph/`) so the safety-spine AST guards (`test_graph_reads_no_credentials`, `test_graph_imports_no_external_network_client_or_model_provider`) stay green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Dropped the optional private `_GLOBAL_TRACING_ENABLED` override from `harden_offline`**

- **Found during:** Task 3 (full-suite verification)
- **Issue:** The plan marked the private `langsmith._internal._context._GLOBAL_TRACING_ENABLED = False` override as *optional belt-and-braces*. Setting it introduced a process-wide flag that leaked across the test session (e.g. `test_durable_cli.py` calls `main → harden_offline`), which made `test_harden_offline_disables_a_primed_tracer` fail (the primed tracer read as already-off) and would have left global state behind in any long-lived process.
- **Fix:** Removed the optional override; `harden_offline` still pops the env keys, clears `get_env_var`'s cache, and asserts `tracing_is_enabled() is False` — the assertion is the proof (D7-03/D7-14), and no global state is mutated. Also removed the now-unneeded per-test restore fixture.
- **Files modified:** `src/triagedesk/observability/offline.py`, `tests/test_observability.py`
- **Verification:** `uv run pytest -q` → 266 passed; `uv run triagedesk demo` exits 0.
- **Committed in:** `5b8a5d3` (Task 3 commit)

### Plan-faithful choice (not a deviation, noted for the record)

- Test D/F run the graph with the **real owned tools** (`build_tools` + stubbed `extract`) rather than the `build_graph_tools` fakes. The fakes emit no tool spans, so the required node-span→tool-span `parent_id` linkage could only be observed with the real `@audited` interceptor in the loop. The behavior (D7-05/D7-07) is proven end-to-end as specified.

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** No scope creep. The dropped override was explicitly optional; removing it makes the guard stateless and the test suite order-independent without weakening the asserted guarantee.

## Issues Encountered

- The `gsd_run`-on-PATH copy of `git base-branch --is-protected` (npm `@opengsd/gsd-core`) does not support the `--is-protected` flag and returns the base branch name instead of `true`/`false`, so the generic pre-commit protected-branch assertion is inoperative in this environment. Commits were made on `main` as the orchestrator directed for sequential execution, consistent with the project's `branching_strategy: none` and its entire commit history.
- A manual `uv run triagedesk demo` verification run writes a repo-root `spans.jsonl` (the production default sink, per D7-02). It is gitignored and removed after the run; the **test suite itself** writes no repo-root artefact (the autouse `_spans_sink` fixture redirects it).

## User Setup Required

None — no external service configuration required. No new dependency was added (`pyproject.toml`/`uv.lock` unchanged).

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced.

## Threat Flags

None — this plan added no new network endpoint, auth path, or schema change beyond the planned audit `trace_id` column. The mitigation for T-07-01 (transitive tracer egress) is implemented and asserted; T-07-02 (sink content) is enforced by minimal attributes (asserted in `test_model_span_carries_no_prompt_text`).

## Next Phase Readiness

- Criterion 1 (nothing left the machine) and criterion 2 (every audit record joins to its spans) are now **provable**: 11 new tests plus the full 266-test suite green.
- Ready for plan 07-02 (read-only replay), which consumes the span stream (`SPANS_PATH`) and the audit reader (`store.read_audit_records`) this plan publishes.
- **Operational note:** widening the persisted `AuditRecord` means a stale local `triage.db` (11-column audit rows) must be deleted before a durable demo — synthetic and disposable, consistent with Phase 6's posture. The idempotent `ALTER TABLE` covers a pre-existing file structurally.

---
*Phase: 07-local-observability-span-tracing-read-only-replay*
*Completed: 2026-10-12*

## Self-Check: PASSED

- Created files present: `observability/{__init__,spans,context,offline}.py`, `tests/test_observability.py`, `07-01-SUMMARY.md`.
- Task commits present: `658269e`, `e32fea1`, `5b8a5d3` (all ancestors of HEAD).
- `uv run pytest -q` → 266 passed; `uv run triagedesk demo` → exit 0; no repo-root `spans.jsonl` from the test suite.
