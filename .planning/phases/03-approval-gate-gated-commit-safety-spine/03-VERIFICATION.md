---
phase: 03-approval-gate-gated-commit-safety-spine
verified: 2026-10-09T17:42:25Z
status: passed
score: 10/10 must-haves verified
covered_files: [".planning/phases/03-approval-gate-gated-commit-safety-spine/03-01-PLAN.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-01-SUMMARY.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-02-PLAN.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-02-SUMMARY.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-03-PLAN.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-03-SUMMARY.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-04-PLAN.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-04-SUMMARY.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-05-PLAN.md", ".planning/phases/03-approval-gate-gated-commit-safety-spine/03-05-SUMMARY.md", "scripts/spike_graph.py", "src/triagedesk/core/schema.py", "src/triagedesk/graph/__init__.py", "src/triagedesk/graph/build.py", "src/triagedesk/graph/nodes.py", "src/triagedesk/graph/state.py", "src/triagedesk/mcp/server.py", "src/triagedesk/store/__init__.py", "src/triagedesk/store/audit.py", "src/triagedesk/store/borrowed.py", "src/triagedesk/store/queue.py", "tests/conftest.py", "tests/test_audit_chain.py", "tests/test_borrowed_store.py", "tests/test_commit_idempotent.py", "tests/test_graph_purity.py", "tests/test_graph_recheck.py", "tests/test_graph_recovery.py", "tests/test_graph_tracer.py", "tests/test_mcp_tools.py", "tests/test_purity.py", "tests/test_safety_spine.py"]
covered_digest: "v3:sha256:e8499d9ab67a2a2bf62e99647d23702976dca53119003e80974dd25dee3a06f1"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: Approval Gate, Gated Commit & Safety Spine Verification Report

**Phase Goal:** The gate physically refuses to place a patient in the queue without a named clinician's approval — enforced by a LangGraph `interrupt()`, an idempotent approval-keyed commit, a single hash-chained audit interceptor, and borrowed SQLite persistence.
**Verified:** 2026-10-09T17:42:25Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | **SC1 — No code path (retry or deterministic fallback included) reaches `commit_priority` without a valid approval token carrying a named approver, role, and timestamp.** | ✓ VERIFIED | Compiled-graph edge dump (independent probe) shows `commit` has exactly one inbound edge: `approval_gate -> commit`; the recovery/escalation terminals and `verify -> __end__` have no edge to `commit`. `mcp/server.py::commit_priority` returns `CommitResult(refused=True)` before any store call for `None`/malformed/`dismiss` tokens. `tests/test_commit_idempotent.py` (no-token, dismiss) + `tests/test_graph_tracer.py::test_unapproved_resume_is_refused_and_writes_nothing` assert refused + zero writes. |
| 2 | **SC2 — The queue write is idempotent, keyed by `case_id` + an immutable content hash: committing the same case twice yields exactly one queue row, even across a simulated crash.** | ✓ VERIFIED | `store/queue.py::commit_to_queue` returns the existing row unchanged when `(case_id, content_hash)` exists; `content_hash` reads only `IMMUTABLE_FIELDS` (timestamp structurally excluded). `tests/test_commit_idempotent.py` (twice, volatile-timestamp, crash-then-retry) pass. Independent probe over the **real borrowed SQLite** store: repeat commit → `created=False`, 1 row. |
| 3 | **SC3 — Every tool call appends one canonical hash-chained record through a single shared helper; the chain verifies after a restart and the audit store and queue store never diverge.** | ✓ VERIFIED | `store/audit.py` is the ONE helper (`AuditRecord` shape, `record_digest`, `append`); `mcp/server.py::audited` is ONE decorator applied under all five `@server.tool()`. Independent probe over the real borrowed SQLite: 8 records, `verify()` valid; **reopened a fresh store handle over the same `triage.db` → chain still valid**; tampering a record → `verify().broken_at` reported; `reconcile()` detects a queue row lacking its approval record. |
| 4 | **SC4 — The full graph runs `ingest → normalize → retrieve → score → verify → (recheck) → gate → commit → handover` on the local model only, deterministic-first `verify`, and missing-vital / out-of-scope conditions route to recovery/abstention edges that never guess.** | ✓ VERIFIED | Independent edge dump matches the required order. `route_after_verify` is bounded (`_MAX_ATTEMPTS=2`). `route_after_score` routes out-of-scope → `escalate`, missing vital → `request_missing_info`. `scripts/spike_graph.py` ran end-to-end on real local `qwen2.5:1.5b` → ORANGE + 3 citations, paused at gate (exit 0). `tests/test_graph_recovery.py` proves both terminals never call `commit_priority`. |
| 5 | **SC5 — A deterioration re-check raises a visible second-look flag with before/after vitals and the queue position unchanged; the handover card renders only structured fields with no diagnosis or prescription language.** | ✓ VERIFIED | `graph/nodes.py::recheck` writes only `second_look` (no colour; `RecheckFlag` has no colour field); `recheck → approval_gate` edge reorders nothing. `tests/test_graph_recheck.py` (flag, unchanged position, stable/improved no-flag, no-commit). `HandoverCard` locked with `extra="forbid"` + `FORBIDDEN_FIELD_TOKENS`; `tests/test_safety_spine.py` proves no dx/rx token on an adversarial complaint and no dx/rx tool registered. |
| 6 | **The `approval_gate` node performs NO side effect before `interrupt()` (a resumed node re-runs from its top).** | ✓ VERIFIED | `graph/nodes.py::approval_gate` only reads state, builds a pure dict payload, then calls `interrupt(payload)`; no store/IO. `tests/test_graph_tracer.py::test_run_reaches_the_gate_without_committing` asserts `commit_result is None` and `commit_priority` was never called before the interrupt. |
| 7 | **A pinned borrowed SQLite MCP server provides case/queue + audit storage behind the injectable tool interface; the gate stays ours; runtime state and the clinical record are two separate SQLite files.** | ✓ VERIFIED | `store/borrowed.py` reaches `mcp-sqlite@1.0.9` in its own adapter context; `Store` protocol is the injectable seam. Independent probe launched the **real** borrowed server, wrote/read a queue row, appended an audit record, and reopened the same DB. `CHECKPOINTS_DB_PATH=checkpoints.db` vs `DOMAIN_DB_PATH=triage.db` (distinct files, asserted by test). |
| 8 | **An approval audit record captures the named approver and role.** | ✓ VERIFIED | `audited(approval=True)` records `approved_by`/`role` from the validated token on a successful commit. Real end-to-end approve run wrote audit seq 7: `commit_priority | clinician | Dr A. Nurse | triage clinician`. `tests/test_audit_chain.py::test_interceptor_records_the_named_approver_on_a_commit`. |
| 9 | **SAFE-03 — Tools are allowlisted with a loud startup assertion; the agent path performs no external network I/O and reads no credentials.** | ✓ VERIFIED | `OWNED_TOOL_ALLOWLIST` (the owned five) asserted by `assert_tool_allowlist` at both discovery and composition; `tests/test_safety_spine.py` proves missing/unexpected tool raises. AST guards prove no `graph/` module imports a network client/non-local model provider or reads credentials. |
| 10 | **QUAL-02 — `core/` does not import `llm/` or any MCP client (guard test).** | ✓ VERIFIED | `tests/test_purity.py` (parametrised over every `core/*.py`, relative-aware) passes; forbidden set names `fastmcp`/`langchain` explicitly. Independent grep of `src/triagedesk/core/` finds no forbidden import. `tests/test_graph_purity.py` proves the score path is model-free (model stubbed to raise → identical colour). |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/triagedesk/graph/{__init__,state,nodes,build}.py` | The full LangGraph safety spine | ✓ VERIFIED | 11 nodes; 3 route functions; injected `ToolMap`; no model/MCP import at node level |
| `src/triagedesk/store/{__init__,borrowed,queue,audit}.py` | Store protocol, borrowed wiring, idempotent write, audit helper | ✓ VERIFIED | All substantive; real borrowed server exercised end-to-end |
| `src/triagedesk/mcp/server.py` | Real gated `commit_priority` + uniform `audited` interceptor | ✓ VERIFIED | Refusal path returns before any store call; interceptor wraps all five tools |
| `src/triagedesk/core/schema.py` | `ApprovalToken.final_colour`, `HandoverCard`, `RecoveryRequest`, `Escalation` | ✓ VERIFIED | `HandoverCard` locked (`extra="forbid"`); `final_colour` substrate-validated |
| `scripts/spike_graph.py` | Real local-model end-to-end tracer | ✓ VERIFIED | Ran exit 0: ORANGE + 3 citations → gate pause → refusal |
| `tests/test_graph_tracer.py` etc. | Proof suites | ✓ VERIFIED | 72 phase-suite tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `graph/build.py` | MCP tool interface | injected `ToolMap` (`name -> async callable`) | ✓ WIRED | `build_graph` depends on the mapping, never `MCPAdapter`; `load_graph_tools` is the one composition seam |
| `graph/nodes.py::normalize` | owned `normalize_case` (local model) | tool call | ✓ WIRED | Model only structures; score node touches no model |
| `graph/nodes.py::score` | pure scorer | owned `score_priority` | ✓ WIRED | Proven model-free with model stubbed to raise |
| `approval_gate` | `commit` | graph edge | ✓ WIRED | Sole inbound edge to `commit`; interrupt precedes any write |
| `commit_priority` | `store/queue.py` | injectable `Store` seam | ✓ WIRED | Refusal returns before any store call; valid token commits once |
| every owned tool | `store/audit.append` | `@audited` decorator | ✓ WIRED | One record per call; uniform, cannot drift |
| `store/audit.py` | `core/hashing.canonical_json` | `record_digest` | ✓ WIRED | Sorted-key compact JSON; append + verify share the one seal |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `commit_priority` queue row | `QueueRow` | borrowed SQLite `queue` table | Yes | ✓ FLOWING — real row `2fe018ed4c458398/ORANGE/pos 1` written by the real approve run |
| audit chain | `AuditRecord` | borrowed SQLite `audit` + `audit_head` | Yes | ✓ FLOWING — 8 chained rows persisted; `verify()` valid after a fresh handle |
| handover card | `HandoverCard` | scored `PriorityResult` + resumed approval | Yes | ✓ FLOWING — rendered from typed facts, no model text |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full phase suite | `uv run pytest -q` | 179 passed | ✓ PASS |
| Phase-suite subset | `pytest test_graph_tracer test_commit_idempotent test_audit_chain test_borrowed_store test_graph_recovery test_graph_recheck test_safety_spine test_graph_purity test_purity -q` | 72 passed | ✓ PASS |
| Real local-model end-to-end tracer | `uv run python scripts/spike_graph.py` | exit 0; ORANGE, 3 citations, gate pause, refusal on unapproved resume | ✓ PASS |
| Graph structure (no bypass) | independent edge dump | `commit` inbound = `approval_gate` only | ✓ PASS |
| Real borrowed SQLite idempotency + restart | independent probe (`open_borrowed_store`) | repeat `created=False`; fresh handle over same file → `verify().valid=True` | ✓ PASS |
| Real end-to-end approved commit | graph + real owned server + real borrowed SQLite | `committed=True`; 1 queue row; audit names approver/role | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| `scripts/spike_graph.py` | `uv run python scripts/spike_graph.py` | exit 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| TOOL-06 | 03-02 | Borrowed maintained SQLite MCP provides case/queue + audit | ✓ SATISFIED | Real `mcp-sqlite@1.0.9` probe wrote/read queue + audit |
| ORCH-01 | 03-01/03-04 | Graph runs the full pipeline | ✓ SATISFIED | Edge dump + spike |
| ORCH-02 | 03-01 | Local open-weights model only | ✓ SATISFIED | Spike ran `qwen2.5:1.5b`; AST guard |
| ORCH-03 | 03-05 | Score path never imports model/MCP client | ✓ SATISFIED | `test_graph_purity.py` model-stub proof |
| ORCH-04 | 03-04 | Structured output, retry once, deterministic fallback | ✓ SATISFIED | `test_graph_recovery.py` |
| ORCH-05 | 03-04 | Missing-vital/out-of-scope conditional edges never guess | ✓ SATISFIED | recovery/escalation tests |
| GATE-01 | 03-01 | `interrupt()` pauses for a named clinician before any queue write | ✓ SATISFIED | spike + tracer tests |
| GATE-02 | 03-01/03-02 | `commit_priority` cannot run without a valid approval token | ✓ SATISFIED | refusal tests; no-token probe |
| GATE-03 | 03-02 | Idempotent write (case_id + content hash) | ✓ SATISFIED | double-commit + crash-retry + real probe |
| GATE-04 | 03-04 | Recheck second-look flag without reordering | ✓ SATISFIED | `test_graph_recheck.py` |
| AUDIT-01 | 03-03 | Every tool call appends a hash-chained record | ✓ SATISFIED | real DB: 8 chained rows |
| AUDIT-02 | 03-03 | Approval records capture approver + role | ✓ SATISFIED | real DB seq 7 |
| AUDIT-03 | 03-03 | Record shape defined once (one helper) | ✓ SATISFIED | `store/audit.py` single helper |
| SAFE-02 | 03-05 | No dx/rx output or tool | ✓ SATISFIED | `test_safety_spine.py` |
| SAFE-03 | 03-05 | Least privilege; no network/credentials | ✓ SATISFIED | allowlist + AST guards |
| QUAL-02 | 03-05 | Guard test: `core/` imports no `llm/` or MCP client | ✓ SATISFIED | `test_purity.py` |

No orphaned requirements: every requirement ID mapped to Phase 3 in REQUIREMENTS.md appears in a plan's `requirements` field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/triagedesk/core/schema.py` | 185 | Stale docstring: `ApprovalToken` still says "The Phase-2 `commit_priority` stub … the real LangGraph gate is Phase 3." | ℹ️ Info | Documentation only; the real gate exists. No behavioural impact. |
| `src/triagedesk/mcp/server.py` | 247-254 | Commit content hash at the tool boundary covers only `colour` (`content={"colour": committed_colour}`), not the fuller `IMMUTABLE_FIELDS` set the queue helper supports. | ℹ️ Info | Documented design (summary 03-02). A same-`case_id` re-commit with a *different* colour creates a second queue row (probe: 2 rows). Retry safety (the required property) is unaffected; flagged for awareness. |
| (roadmap wording) | — | SC2 says "one audit entry" but the audit deliberately records **every** tool call per AUDIT-01. | ℹ️ Info | Two commits of the same case → one queue row but two audit records (the second honest "already committed"). Interprets SC2's "one audit entry" at the per-write level; see Gaps Summary note. |

No `TBD`/`FIXME`/`XXX` debt markers in any phase-modified file. `core/` is import-pure. `.planning/WINDOWS.md` has `open_count: 0` (both phase stubs marked fixed).

### Human Verification Required

None. The external service (borrowed SQLite MCP) and the local-model end-to-end path were both exercised directly by the verifier, not merely asserted.

### Gaps Summary

No gaps. The phase goal is achieved and independently reproduced:

- **The gate refuses.** The compiled graph has exactly one inbound edge to `commit` (`approval_gate`), and the owned `commit_priority` tool returns `refused=True` before touching any store for absent/malformed/`dismiss` tokens. Verified structurally and on the real local-model spike (dismiss resume → refused, queue empty).
- **The commit is idempotent.** The write is keyed on `(case_id, content_hash)` over immutable content; a volatile timestamp never enters the key. Verified at the unit, tool, and real-borrowed-SQLite levels.
- **The audit is one chained helper.** One `@audited` interceptor under all five tools; one `store/audit.append`. The chain verified after a genuine reopen of the real SQLite file, and tampering is detected.
- **Borrowed persistence is real.** The pinned `mcp-sqlite@1.0.9` server stored the queue row and the audit chain; `triage.db` and `checkpoints.db` are distinct files.

**Interpretation note (for human awareness, not a blocker):** roadmap SC2 literally reads "exactly one queue row and one audit entry". The implementation yields exactly one queue row (verified) but records one audit record per tool call, so two commit calls produce two audit records — the second marked "already committed". This is the deliberate design of AUDIT-01 ("every tool call appends a hash-chained record") and Plan 03-03 ("a refused commit is still recorded as a refused call"), and it is strictly more conservative (nothing is silently dropped). The safety property in SC2 — that a retry cannot double-place a patient — is fully satisfied.

---

_Verified: 2026-10-09T17:42:25Z_
_Verifier: the agent (gsd-verifier)_
