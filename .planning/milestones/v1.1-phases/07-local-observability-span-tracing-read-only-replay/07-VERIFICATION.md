---
phase: 07-local-observability-span-tracing-read-only-replay
verified: 2026-10-13T13:14:02Z
status: passed
score: 8/8 must-haves verified
covered_files:
  [
    ".gitignore",
    ".planning/phases/07-local-observability-span-tracing-read-only-replay/07-01-PLAN.md",
    ".planning/phases/07-local-observability-span-tracing-read-only-replay/07-01-SUMMARY.md",
    ".planning/phases/07-local-observability-span-tracing-read-only-replay/07-02-PLAN.md",
    ".planning/phases/07-local-observability-span-tracing-read-only-replay/07-02-SUMMARY.md",
    "SECURITY.md",
    "docs/DECISIONS.md",
    "pyproject.toml",
    "src/triagedesk/cli.py",
    "src/triagedesk/graph/build.py",
    "src/triagedesk/llm/client.py",
    "src/triagedesk/mcp/server.py",
    "src/triagedesk/observability/__init__.py",
    "src/triagedesk/observability/context.py",
    "src/triagedesk/observability/offline.py",
    "src/triagedesk/observability/spans.py",
    "src/triagedesk/replay.py",
    "src/triagedesk/store/audit.py",
    "src/triagedesk/store/borrowed.py",
    "tests/conftest.py",
    "tests/test_observability.py",
    "tests/test_replay_read_only.py",
  ]
covered_digest: "v3:sha256:ab8b24e7d721eb6f53c14598810817f79f50e042ab0e00cd420e7eec4daed376"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 8/8
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 7: Local Observability — Span Tracing & Read-Only Replay Verification Report

**Phase Goal:** Tool, node, and model spans emit to a local sink with no egress, each audit record carries a `trace_id` linking it to those spans, and replay reconstructs a past case read-only — structurally unable to re-run the gated commit.
**Verified:** 2026-10-13T13:14:02Z
**Status:** passed
**Re-verification:** Yes — STALE re-verification (later phases 8–12 additively edited shared source files the prior report covered). Prior report: `passed`, 8/8, no `gaps:` section — this pass is a full regression re-check with a freshly computed fingerprint.

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1 (R1) | Tool, node, and model spans are written to a local file with no network/egress, and cloud tracing remains disabled. | ✓ VERIFIED | Three emit seams drive the ONE writer `emit_span` (`observability/spans.py:89`): tool span `mcp/server.py:156` (`with span("tool", …)`), node span `graph/build.py:213` (`_spanned` wrapper applied in the `add_node` loop at `build.py:242`), model span `llm/client.py:104` (`with span("model", …)`). `emit_span` writes one JSONL line to a local `Path` via `path.open("a")` — no network path. `harden_offline()` (`observability/offline.py:37`) pops the 4 LangSmith/LangChain tracer vars + 2 OTLP endpoint vars, calls `langsmith.utils.get_env_var.cache_clear()`, and raises unless `tracing_is_enabled() is False`; `cli.main` calls it as its FIRST statement (`cli.py:161`). Behavioral tests: `test_audit_trace_id_round_trips_through_the_borrowed_store`, `test_node_spans_carry_the_content_trace_id`, `test_model_span_carries_no_prompt_text`, `test_offline_run_emits_no_model_span`, `test_harden_offline_asserts_tracing_is_disabled`, `test_harden_offline_disables_a_primed_tracer`, `test_harden_offline_is_import_safe_without_langsmith`, `test_importing_the_cli_pulls_no_tracer_capable_stack`. Full suite hermetic: `uv run pytest -q` → **454 passed** in 34.55s, and **no repo-root `spans.jsonl`/`*.db` after the run**. |
| 2 (R2) | Every audit record carries a first-class `trace_id` linking it to its spans in the local stream. | ✓ VERIFIED | `AuditRecord.trace_id: str = ""` (`store/audit.py:63`), sealed by `record_digest` when non-empty (`audit.py:84-87`, omitting an empty value keeps legacy rows verifying). The `@audited` interceptor passes `current_trace_id()` (`mcp/server.py:148`); the borrowed store persists the column through all four coordinated edits — DDL (`borrowed.py:145`), guarded idempotent `ALTER TABLE` (`borrowed.py:153-155`, applied in `ensure_schema` lines 308-312), INSERT columns/values (`borrowed.py:498-515`), SELECT (`borrowed.py:526-529`). Round-trip proven by `test_audit_trace_id_round_trips_through_the_borrowed_store` against a real `sqlite3`-backed fake. Demo/eval/resume/replay run the owned tools **in-process**, so the binding reaches the interceptor. The stdio-subprocess boundary is declared (`SECURITY.md` §10) and pinned by `test_an_owned_tool_without_a_bound_trace_records_an_empty_trace_id`. |
| 3 (R3) | A past case is reconstructed for replay from the checkpoint plus the audit/span stream, without re-running the model. | ✓ VERIFIED | `replay.read_recorded` (`replay.py:56`) opens the SQLite saver via `open_checkpointer` (`graph/build.py:327`, a saver factory that builds no graph) and returns `aget_tuple(config).checkpoint["channel_values"]`; `replay_case` (`replay.py:127`) reads the audit records filtered by `trace_id` and the span stream via `read_spans(..., trace_id=…)`. No `ainvoke`, no resume, no graph. Behavioral tests: `test_replay_writes_nothing` (real committed case, reads back colour/target/citations) and `test_replay_never_calls_the_model` (patches `triagedesk.llm.client.extract` to raise; replay does not raise and emits no new `model` span). |
| 4 (R4) | Replaying a gated case adds zero queue rows and zero commits, and the replayed outcome equals the original. | ✓ VERIFIED | `test_replay_writes_nothing` runs a case to a committed handover over a real SQLite checkpointer, snapshots queue-row count / `commit_priority` count / total audit count / store-call count, calls `replay_case`, and asserts all four deltas are unchanged; then asserts the recorded `colour`, `target` and every citation appear in the rendered view and the single queue row's colour equals the recorded priority colour. `test_replay_leaves_the_queue_and_audit_chain_unchanged` additionally pins the chain head unchanged and `verify()` still valid. |
| 5 (P1c) | The `@audited` interceptor's audit behaviour is byte-equivalent apart from the added field (exactly one chained record per call; refusal path and actor/approver logic unchanged). | ✓ VERIFIED | `mcp/server.py:138-150` still calls `append(store, {...})` once per call; the refusal logic in `commit_priority` (lines 290-299) is untouched; `record()`'s `error`/`approved_by`/`role` logic is unchanged. Additive diff only. `test_a_span_sink_failure_never_breaks_the_tool_or_its_audit_record` asserts exactly one record with a real (non-error) output; existing audit/borrowed/mcp suites green under the full 454-test run. |
| 6 (P1d) | `graph/` still reads no environment variable and imports no external network client or non-local model provider. | ✓ VERIFIED | `grep -rn "os.environ\|getenv" src/triagedesk/graph/` → nothing. Module-level imports of `graph/build.py` are stdlib + langgraph + pydantic + `triagedesk.observability` + `triagedesk.store` only (no network client). `test_safety_spine.py` + `test_purity.py` + `test_graph_purity.py` → 23 passed. All env logic lives in `observability/offline.py`, outside `graph/`. |
| 7 (P2c) | Read-only is structural: `replay.py` constructs NO tool mapping and compiles NO graph. | ✓ VERIFIED | `grep -cE "build_graph\|checkpointed_graph\|resume_paused\|load_graph_tools" src/triagedesk/replay.py` → 0; `grep -c "aget_tuple" src/triagedesk/replay.py` → 1. `replay.py` imports only `CHECKPOINTS_DB_PATH` + `open_checkpointer` (a saver factory that builds no graph), the `resolve_store` seam, `read_spans`, and the `Store` protocol. No tool surface exists in the module, so `commit_priority` is unreachable by construction. |
| 8 (P2d) | The `replay` CLI parses and dispatches through the ONE replay function; an absent thread raises a typed `ReplayError` naming the thread id and the checkpoint file. | ✓ VERIFIED | `cli.py:125-137` registers the `replay` subparser (`--thread-id` required, `--db` default `None`); dispatch at `cli.py:224-240` calls `replay_case`. `ReplayError` (`replay.py:52`) is raised with `f"no checkpoint for thread_id {thread_id} in {db_path}"`. `test_replay_parser_parses_its_flags`, `test_replay_absent_thread_raises_replay_error` (asserts thread id + db path in the message), and `test_replay_cli_reports_an_absent_thread_cleanly` (exit 1, clean message, borrowed store never launched) all pass. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Deferred Items

None — no gap was deferred to a later milestone phase.

### Advisory (New Scope, Unevidenced)

None — this pass produced no new-scope Step 7 finding. (See the ℹ️ Info note under Anti-Patterns for an environmental observation about the repo-root span artifact.)

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/triagedesk/observability/spans.py` | `SPANS_PATH`, `emit_span`, `span`, `set_sink`, `read_spans` | ✓ VERIFIED | 207 lines; all five symbols present (lines 42, 89, 169, 49, 132); the ONE writer + the ONE reader colocated; `__all__` lists all five. |
| `src/triagedesk/observability/context.py` | `bind_trace`, `current_trace_id`, `push_span`, `pop_span`, `current_parent_id` | ✓ VERIFIED | 66 lines; all five symbols present (`contextvars`), no env/network. |
| `src/triagedesk/observability/offline.py` | `harden_offline` | ✓ VERIFIED | 64 lines; pops tracer env, clears lru_cache, asserts `tracing_is_enabled() is False`. |
| `src/triagedesk/observability/__init__.py` | Barrel re-exports; never imports `offline` | ✓ VERIFIED | 21 lines; re-exports writer + context; does not import `observability.offline`. |
| `src/triagedesk/store/audit.py` | `AuditRecord.trace_id` (additive, digest-sealed) | ✓ VERIFIED | Field at line 63; `record_digest` omits an empty `trace_id` so pre-migration rows verify. |
| `src/triagedesk/store/borrowed.py` | audit `trace_id` column + 4 coordinated edits | ✓ VERIFIED | DDL (`145`), migration constant (`153`), guarded `ensure_schema` (`308-312`), INSERT column/value (`498-515`), SELECT (`526-529`). |
| `src/triagedesk/mcp/server.py` | Tool span + `trace_id` in the interceptor | ✓ VERIFIED | `span("tool", …)` at line 156; `"trace_id": current_trace_id()` at line 148. |
| `src/triagedesk/graph/build.py` | `_spanned` node wrapper in the `add_node` loop | ✓ VERIFIED | `_spanned` defined line 193, applied line 242; topology edges unchanged. |
| `src/triagedesk/llm/client.py` | Model span inside `extract` | ✓ VERIFIED | `with span("model", model, attributes=attrs)` at line 104; minimal attributes (model + token counts). |
| `src/triagedesk/replay.py` | `ReplayError`, `read_recorded`, `replay_case` | ✓ VERIFIED | 162 lines; all three present; imports no graph-building entry point. |
| `src/triagedesk/cli.py` | `replay` subcommand + dispatch; `harden_offline()` at startup | ✓ VERIFIED | `harden_offline()` at `main`'s first statement (line 161); `replay` parser (125-137) + dispatch branch (224-240). |
| `tests/test_observability.py` | Span kinds, trace_id join, round-trip, no-egress, redaction | ✓ VERIFIED | 419 lines; 14 tests. |
| `tests/test_replay_read_only.py` | Zero-write, no-model, outcome-equality, absent-thread, CLI | ✓ VERIFIED | 301 lines; 9 tests. |
| `.gitignore` | `spans.jsonl` entry | ✓ VERIFIED | Line 22. |
| `docs/DECISIONS.md` | D19 row | ✓ VERIFIED | `### D19` at line 150. |
| `SECURITY.md` | Observability/read-only-replay subsection | ✓ VERIFIED | §10 "Local observability & read-only replay" at line 95. |
| `tests/conftest.py` | `_spans_sink` autouse fixture | ✓ VERIFIED | Lines 200-212; redirects the sink to `tmp_path`. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `graph/build._spanned` | `mcp/server` interceptor | `bind_trace(trace_id)` → `current_trace_id()` → `append({"trace_id": …})` | ✓ WIRED | `build.py:212` binds; `server.py:148` reads. |
| `graph/build._spanned` | `store/borrowed` audit table | `append` → INSERT `trace_id` column/value → SELECT | ✓ WIRED | Round-trip test passes on a real `sqlite3` fake. |
| `mcp/server.audited` wrapper | `observability.spans.emit_span` | `span("tool", tool_name)` → `emit_span` → `SPANS_PATH` | ✓ WIRED | `server.py:156`; asserted by `test_audit_trace_id_round_trips_through_the_borrowed_store`. |
| `llm/client.extract` | `observability.spans.emit_span` | `span("model", model)` → `emit_span` | ✓ WIRED | `client.py:104`; asserted by `test_model_span_carries_no_prompt_text`. |
| `cli.main` | `observability.offline.harden_offline` | direct import + first statement | ✓ WIRED | `cli.py:26,161`; `tracing_is_enabled()` asserted False. |
| `replay.replay_case` | checkpoint / audit store / span reader | `read_recorded` + `resolve_store().read_audit_records()` + `read_spans(trace_id=)` | ✓ WIRED | `replay.py:151-158`; all three read seams exercised by the replay suite. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `observability/spans.py` | span line (`trace_id`, `span_id`, `parent_id`, `kind`, `name`, …) | live `span()` blocks at the 3 seams | Yes — real `uuid4` ids, real `perf_counter` timings, real token counts from the ollama response | ✓ FLOWING |
| `replay.py` | rendered view (`colour`, `target`, `citations`, `decision`, span timeline) | `aget_tuple(...).checkpoint["channel_values"]` + `read_audit_records()` + `read_spans()` | Yes — read back from the recorded checkpoint and streams, not re-derived | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite green + hermetic | `uv run pytest -q` | **454 passed** in 34.55s; no repo-root `spans.jsonl`/`checkpoints.db`/`triage.db` after the run | ✓ PASS |
| Phase proof suites | `uv run pytest tests/test_observability.py tests/test_replay_read_only.py -q` | **23 passed** | ✓ PASS |
| Graph purity / safety spine | `uv run pytest tests/test_safety_spine.py tests/test_purity.py tests/test_graph_purity.py -q` | 23 passed | ✓ PASS |
| Graph reads no env / imports no network client | `grep -rn "os.environ\|getenv" src/triagedesk/graph/` | nothing | ✓ PASS |
| Replay constructs no graph / no tool map | `grep -cE "build_graph\|checkpointed_graph\|resume_paused\|load_graph_tools" src/triagedesk/replay.py` | 0 | ✓ PASS |
| No new dependency | `git diff --stat -- pyproject.toml uv.lock` | empty | ✓ PASS |

### Probe Execution

No phase-declared probes and no `scripts/*/tests/probe-*.sh` exist; this is not a migration/tooling phase. N/A.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| AGENT-04 | 07-01, 07-02 | Tool/node/model spans emitted from the existing interceptor + wrappers to a local exporter (no cloud/egress), a `trace_id` links spans to the audit record, and replay is read-only — reconstructs from checkpoint + audit/span stream and structurally cannot re-run the gated commit. | ✓ SATISFIED | Truths 1–8 above; both plans declare `requirements: [AGENT-04]`; AGENT-04 is the only Phase-7 requirement id in REQUIREMENTS.md (marked `[x]`, "Complete", mapped to Phase 7). No orphaned requirements. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` or empty-return stub found in any phase file. (`spans.py:151 return []` is the correct empty-stream-on-missing-file case, not a stub.) | — | Debt-marker gate: clean. |
| repo root `spans.jsonl` | — | A stale, gitignored `spans.jsonl` left at the repo root by a manual/demo run (not by the test suite) makes `test_no_spans_artifact_is_written_to_the_repo_root` fail when the suite is run with that leftover present. | ℹ️ Info | Environmental, not a Phase-7 defect: the autouse `_spans_sink` fixture correctly redirects the sink (a guard-only run did not modify the leftover file), and a clean `uv run pytest -q` passes 454/454 and leaves **no** repo-root artifact. Recorded so a reviewer running the suite against a dirty tree is not misled. |

### Human Verification Required

N/A — Infrastructure/foundation phase with no user-facing elements. Every roadmap success criterion and every plan must-have is backed by an automated behavioral test that exercises the property (spans written, trace-id round-trip, no-egress assertion, replay reconstruction, zero-write deltas, no-model). No truth is left ⚠️ PRESENT_BEHAVIOR_UNVERIFIED, so `human_verification` is empty.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria and all 8 merged must-have truths verify against the current codebase after later phases' additive edits:

- The three span kinds emit through the ONE writer to ONE local JSONL sink; cloud tracing is neutralised and asserted off at CLI startup; the run is hermetic (454 passed, no repo-root artifact).
- The audit record's first-class content-derived `trace_id` persists through the production borrowed store and joins record-to-span for every demonstrated in-process path (demo/eval/resume/replay).
- Replay reconstructs a committed case from the checkpoint + audit/span stream with no model call and no graph, and adds zero queue rows and zero commits, with the replayed outcome equal to the recorded one.

Honest scope (declared, tested, **not** gaps):

- **The `contextvars` trace binding does not cross the stdio-subprocess boundary.** When the graph reaches the owned server over its stdio subprocess, the child process sees the contextvar default, so its records carry `trace_id=""`. Declared at `SECURITY.md` §10 and pinned by `test_an_owned_tool_without_a_bound_trace_records_an_empty_trace_id`; the graded flow (demo/eval/resume/replay) runs the owned tools in-process, so it is covered.
- **Replay is read-only at the ROW level, not the SQLite-file level.** The checkpointer's read method necessarily runs its idempotent `setup()` (`PRAGMA journal_mode=WAL` + `CREATE TABLE IF NOT EXISTS`), so opening a checkpoint may create/touch `checkpoints.db`, and resolving the default audit store runs the borrowed server's `ensure_schema` (idempotent DDL). These are schema initialisations only — never a queue write or a commit. Declared at `SECURITY.md` §10 and `replay.py`'s module docstring, and asserted by `test_replay_leaves_the_queue_and_audit_chain_unchanged`. The ROADMAP row-level criterion is met and proven.

---

_Verified: 2026-10-13T13:14:02Z_
_Verifier: the agent (gsd-verifier)_
