---
phase: 06-durable-execution-idempotent-gate
verified: 2026-10-13T13:15:32Z
status: passed
score: 9/9 must-haves verified
covered_files: [".planning/phases/06-durable-execution-idempotent-gate/06-01-PLAN.md", ".planning/phases/06-durable-execution-idempotent-gate/06-01-SUMMARY.md", ".planning/phases/06-durable-execution-idempotent-gate/06-02-PLAN.md", ".planning/phases/06-durable-execution-idempotent-gate/06-02-SUMMARY.md", "docs/DECISIONS.md", "docs/DEMO.md", "src/triagedesk/cli.py", "src/triagedesk/core/schema.py", "src/triagedesk/demo/run.py", "src/triagedesk/durable.py", "src/triagedesk/evals/runner.py", "src/triagedesk/evals/tools.py", "src/triagedesk/graph/build.py", "src/triagedesk/graph/nodes.py", "src/triagedesk/mcp/server.py", "src/triagedesk/store/__init__.py", "src/triagedesk/store/borrowed.py", "src/triagedesk/store/memory.py", "src/triagedesk/store/queue.py", "tests/conftest.py", "tests/test_audit_chain.py", "tests/test_borrowed_store.py", "tests/test_commit_idempotent.py", "tests/test_demo_runbook.py", "tests/test_durable_cli.py", "tests/test_eval_invariants.py", "tests/test_graph_durable.py", "tests/test_mcp_tools.py"]
covered_digest: "v3:sha256:6aec7da07159cb828a29db7d3a8fa512b17135978d49060db41e57f724a89dd3"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 9/9
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 6: Durable Execution & Idempotent Gate Verification Report

**Phase Goal:** The demo and CLI execute the whole triage lifecycle through the durable `checkpointed_graph`, so a case paused at the approval gate survives a process restart and resumes on a stable `thread_id` — and an edit decision updates the queue row instead of duplicating it.
**Verified:** 2026-10-13T13:15:32Z
**Status:** passed
**Re-verification:** Yes — **stale re-verification**. The prior report (2026-10-12T14:38:04Z, `passed`, 9/9, digest `v3:sha256:fd8ebca5…`) was marked stale by construction: Phases 7–12 additively edited several files that report covered (`cli.py`, `graph/nodes.py`, `mcp/server.py`, `store/borrowed.py`, `core/schema.py`, `docs/DECISIONS.md`, `docs/DEMO.md`, …), changing the covered-file digest. This pass re-confirms all four success criteria against the **current** codebase and regenerates the fingerprint (`v3:sha256:6aec7da0…`). No gap-closure round was requested (`gaps_remaining: []`, `regressions: []`).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 (SC1) | A case paused at the approval gate resumes to a committed handover after a **full process restart**, on a stable `thread_id` derived from the immutable case content (not a random id). | ✓ VERIFIED | `tests/test_graph_durable.py::test_restart_resumes_to_one_row_and_one_commit_audit` (two separate `checkpointed_graph` opens over one `tmp_path` SQLite file → `len(rows) == 1`). Re-confirmed **end-to-end across real processes** on the current tree: `triagedesk demo --durable --beat escalation --db …/checkpoints.db` → `[durable] thread_id=9300336d37c3651c paused at approval gate`; then a fresh `triagedesk resume --thread-id 9300336d37c3651c --decision approve --approver "Nurse Demo" --role "triage nurse" --db …` → `committed case 9300336d37c3651c at queue position 1 (ORANGE)`; reading the real `triage.db` queue returned **exactly one row** (`9300336d37c3651c | ORANGE | position 1`). |
| 2 (SC1 / 06-02 T5) | `thread_id` equals `case_id_for(note.strip())` — the ONE content derivation, stable regardless of surrounding whitespace or entry point (never random, never prefix-scoped). | ✓ VERIFIED | `src/triagedesk/durable.py:80-88` `derive_thread_id` delegates to `graph.nodes.case_id_for_note`, which strips then calls the raw primitive `case_id_for` (`nodes.py:93-102` → `nodes.py:83-90`, `hash_value({"raw_note": …})[:16]`); `grep -n "random\|uuid" durable.py` matches only a docstring ("never a random id"). Runtime re-check: `derive_thread_id(note) == case_id_for(note.strip()) == case_id_for_note(note)`, and `derive_thread_id("  "+note+"  ") == derive_thread_id(note)` all hold; printed id `9300336d37c3651c`. `test_thread_id_is_the_stripped_note_hash` binds the same. The graph names the case id via the same `case_id_for_note` (`nodes.py:380`), so the printed id equals the gate's/commit's id. |
| 3 (SC2) | An `edit` decision on resume **supersedes** the existing row in place — exactly one row reflects the edited colour, no second row is inserted, and `position`/`created_at` are preserved. | ✓ VERIFIED | `tests/test_commit_idempotent.py::test_an_edit_supersedes_the_row_in_place` (ORANGE→GREEN: one row, colour GREEN, `position == 1`, `created_at` unchanged) and `tests/test_graph_durable.py::test_edit_resume_supersedes_on_the_durable_path` (also asserts `content_hash == content_hash(thread_id, case.case)` — colour-independent). Re-confirmed against the **real borrowed store**: after the approve landed row `position 1`, a fresh pause + `resume --decision edit --colour GREEN` → `already committed case 9300336d37c3651c at queue position 1 (GREEN)`; the real `triage.db` showed **one** row, `GREEN`, position `1`, `created_at` unchanged (`2026-10-13T13:11:00.190760+00:00`). |
| 4 (SC2 / 06-01 T2) | The queue idempotency key is derived from the immutable `CaseInput` payload (schema-derived), so an `approve` and an `edit` of the same case re-derive the SAME key. | ✓ VERIFIED | `src/triagedesk/store/queue.py:35` `IMMUTABLE_FIELDS: tuple[str, ...] = tuple(CaseInput.model_fields)`; `content_hash` reads only `IMMUTABLE_FIELDS` (`queue.py:38-49`). Runtime: `python -c "…assert IMMUTABLE_FIELDS == tuple(CaseInput.model_fields)"` passes; `test_volatile_timestamp_does_not_change_the_content_hash` proves `approved_at` is structurally excluded (and `"approved_at" not in IMMUTABLE_FIELDS`). |
| 5 (SC2 / 06-01 T3) | The borrowed SQL queue write is an insert-or-update on `(case_id, content_hash)` that updates **only** `colour`/`target`. | ✓ VERIFIED | `src/triagedesk/store/borrowed.py:415-432` issues `INSERT INTO queue (…) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(case_id, content_hash) DO UPDATE SET colour = excluded.colour, target = excluded.target`, values parameterised; `_QUEUE_DDL` keeps `PRIMARY KEY (case_id, content_hash)` (`borrowed.py:114-123`). In-memory double matches (`memory.py:84-91`, replace-by-key, never bumps position). The hand-run in Truth 3 executed this real UPSERT via `npx mcp-sqlite` (one row, GREEN). |
| 6 (SC2 / 06-01 T4) | A retry of an identical commit still inserts no second row (v1.0 crash-safety preserved). | ✓ VERIFIED | `tests/test_commit_idempotent.py::test_crash_then_retry_yields_one_row` (`created is False`, one row, position preserved) and `test_commit_twice_yields_one_row`; `test_commit_priority_commits_once_through_the_injected_store` (repeat call → one row). |
| 7 (SC3) | A case run end-to-end produces exactly one queue row and **no pre-gate tool is replayed** — every per-tool audit count is exactly 1 (the reading resolved in `06-RESEARCH.md` A5 / "Open Questions (RESOLVED)" Q1). | ✓ VERIFIED | `tests/test_graph_durable.py::test_restart_resumes_to_one_row_and_one_commit_audit` asserts `len(rows) == 1` and `Counter(audit).get(tool) == 1` for `normalize_case`, `match_discriminators`, `score_priority`, `commit_priority` across the restart. Real-store cross-check after two CLI lifecycle runs: `SELECT tool, COUNT(*) FROM audit GROUP BY tool` → each of `assess_confidence`, `commit_priority`, `match_discriminators`, `retrieve_evidence`, `score_priority` = `2` (one record per tool per run; **no** within-run replay). |
| 8 (SC4 / 06-02 T7, T8) | The bare `uv run triagedesk demo` still runs its five-beat storyboard offline and **hermetically** (no model, no borrowed subprocess, no `*.db`), and `demo --durable` runs one case to the gate, prints exactly one greppable `thread_id=` line plus the exact `resume` command, then exits **without auto-resuming**. | ✓ VERIFIED | Re-confirmed on the current tree: `triagedesk demo` → exit 0, five `--- ` beats, **no `*.db`** created at repo root, zero `thread_id=` lines. `triagedesk demo --durable --beat escalation --db …` → exit 0, exactly one `[durable] thread_id=…` line and one `[durable] resume: uv run triagedesk resume …` line, no `--- outcome ---` block; checkpoint file created (61 KB). Tests: `test_durable_demo_pauses_and_prints_one_thread_id_line`, `test_durable_demo_resolves_the_injected_store_seam`, `test_demo_runbook.py`. Default path unchanged uses the in-memory saver, per locked decision **D6-08**. |
| 9 (SC4 / 06-02 T9) | `triagedesk resume --decision approve\|edit` completes a paused thread to a committed handover; `resume --decision dismiss` is refused by the gate and writes no queue row. | ✓ VERIFIED | Real process: `resume … --decision approve` → `committed … position 1 (ORANGE)` (exit 0); `resume … --decision edit --colour GREEN` → `already committed … position 1 (GREEN)`; `resume … --decision dismiss` on a **pending** thread → stderr `clinician dismissed the priority; refusing to commit`, exit 0, and no queue row written. Absent thread → exit 1 with `no pending approval gate for thread_id absent-thread in …`. Tests: `test_resume_absent_thread_never_touches_a_store`, `test_resume_approve_without_approver_names_the_flag`, `test_resume_rejects_a_whitespace_only_identity`, `test_resume_refused_edit_prints_reason_and_exits_nonzero`, `test_resume_reports_an_unexpected_failure_cleanly`. |

**Score:** 9/9 truths verified (0 present-but-behavior-unverified)

### Reading Resolutions (documented, not gaps)

The phase's own research and the locked CONTEXT decisions resolve two ROADMAP wordings; the codebase is
verified against the resolved reading, and the tension is recorded here for transparency:

- **SC3 "exactly one audit record"** is literally false (a full run legitimately writes one record *per tool*). `06-RESEARCH.md` A5 / Open-Q1 **RESOLVED** it as *per-tool counts all `== 1`* (no tool replayed), which is what the plan and the test assert. Verified against that reading.
- **SC4 "`uv run triagedesk demo` runs its storyboard through the checkpointed graph"** conflicts with locked decision **D6-08** (the no-flag default stays hermetic on the in-memory saver; only `--durable` uses `checkpointed_graph`). Verified against the resolved reading: the default is hermetic and the **durable mode** executes through the checkpointed graph.

Note on the offline resume path's audit counts: `resume_thread` builds the tool mapping with `offline=True` (`durable.py:239`), and `evals/tools.build_tools` returns the golden extraction directly when `offline=True`, so no owned-tool call — and hence no audit record — is produced for `normalize_case`. This is the pre-existing v1.0 offline design (the fixture is not a tool invocation), not an un-audited owned call. The per-tool-exactly-1 proof runs with `offline=False` + a stubbed `extract`, exercising the real audited tool.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/triagedesk/durable.py` | ONE durable pause/resume helper | ✓ VERIFIED | 254 lines; `DurableError`, `derive_thread_id`, `PausedRun`, `invoke_graph`, `run_to_gate`, `resume_paused`, `resume_thread`, `approval_decision`, `_RESUME_PLACEHOLDER`. **0 commits since the prior pass** — unchanged. Imported by `cli.py`, `demo/run.py` (wired); `evals/runner.py` shares `invoke_graph` via lazy import. |
| `src/triagedesk/cli.py` | `resume` subcommand + demo `--durable`/`--db` | ✓ VERIFIED | `_build_parser` registers `resume` (`--thread-id`, `--decision {approve,edit,dismiss}`, `--approver`, `--role`, `--colour`, `--db`) and demo `--durable`/`--db`; dispatch delegates to `durable.approval_decision` + `durable.resume_thread`. No graph/store/decision logic inline. (Phase 7 added a sibling `replay` subcommand — additive.) |
| `src/triagedesk/store/queue.py` | Schema-derived `IMMUTABLE_FIELDS`; supersede in place | ✓ VERIFIED | `IMMUTABLE_FIELDS = tuple(CaseInput.model_fields)`; `commit_to_queue` returns `(updated, False)` on the existing-key branch preserving `position`/`created_at`. **0 commits since the prior pass** — unchanged. |
| `src/triagedesk/store/memory.py` / `borrowed.py` | upsert inserts-or-updates by key | ✓ VERIFIED | In-memory replace-by-key (`memory.py:84-91`, unchanged); borrowed `INSERT … ON CONFLICT … DO UPDATE` (`borrowed.py:415-432`). Later phases edited `borrowed.py` additively (audit `trace_id` migration, read-path probe, statement guard) without touching the queue UPSERT. |
| `src/triagedesk/mcp/server.py` | `commit_priority(case_id, colour, case: CaseInput, approval_token)` passes `content=case` | ✓ VERIFIED | Signature unchanged; `content=case` at `server.py:305-310`; refusal path (no token / malformed / dismiss) returns before any store call; `@audited` interceptor unchanged. Later phases added sibling owned tools (`assess_confidence`, `retrieve_evidence`, `raise_recheck_flag`) — additive. |
| `src/triagedesk/graph/nodes.py` | `_make_commit` forwards the typed case; ONE note derivation | ✓ VERIFIED | `_make_commit` adds `"case": state["case"].model_dump()` (`nodes.py:382`); `case_id_for_note` (`nodes.py:93-102`) is the ONE strip-then-derive helper used by the gate/commit/handover (WR-05). Later phases added sibling nodes — additive. |
| `src/triagedesk/evals/tools.py` | adapter validates + forwards `case` | ✓ VERIFIED | `CaseInput.model_validate(inp["case"])` → positional arg. |
| `src/triagedesk/core/schema.py` | WR-05 fix: dismiss token well-formed; identity/colour required for approve/edit | ✓ VERIFIED | `ApprovalToken._identity_and_colour_required` (`schema.py:313-328`) short-circuits `dismiss` and rejects whitespace-only identity/undeclared colour. Not D-18-protected. Later phases edited the schema additively (age contract, serial-vitals) — the token rule is intact. |
| `tests/test_graph_durable.py` / `tests/test_durable_cli.py` | restart/exactly-once/derivability + CLI proofs | ✓ VERIFIED | Present, substantive (24 test functions across the three Phase-6 suites), and green. |
| `docs/DEMO.md` / `docs/DECISIONS.md` | durable two-command runbook; D16 key-breadth note | ✓ VERIFIED | `DEMO.md` documents `demo --durable`, the `resume` subcommand, `checkpoints.db` reset and borrowed-store caveat (refreshed by Phase 11/12 to the shipped CLI); `DECISIONS.md` records "the idempotency key now covers the **immutable case input**". |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `demo/run.py` durable branch | `durable.run_to_gate` → `graph/build.checkpointed_graph` | `_run_durable` resolves the store seam then calls `run_to_gate` (`demo/run.py:227-233`) | ✓ WIRED | Observed live: pause printed `thread_id=9300336d37c3651c` and created the checkpoint file (61 KB). |
| `cli.py` resume dispatch | `durable.resume_thread` → `resume_paused` → `checkpointed_graph` | `main` → `approval_decision` + `asyncio.run(resume_thread(...))` (`cli.py:191-205`) | ✓ WIRED | Observed live in a fresh process; commit landed in the same store. |
| `graph/nodes.case_id_for_note` | ONE `thread_id` derivation | `durable.derive_thread_id` (delegate) | ✓ WIRED | `grep case_id_for src/triagedesk/demo/run.py` = 0; the demo/CLI use the one derivation. |
| `evals/runner._run_once` and `demo._run_beat` | shared `durable.invoke_graph` | runner lazy-imports; demo imports (`run.py:28`) | ✓ WIRED | One invoke→interrupt→resume primitive; each caller keeps its own `thread_id` policy. |
| `mcp/server.commit_priority` | `commit_to_queue` | `resolve_store()` then `content=case` (`server.py:305-310`) | ✓ WIRED | Signature widened to the typed `case`; the refusal path returns before any store call. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| queue row colour | committed `colour` | graph `commit` node → `commit_priority(content=case)` → `content_hash(IMMUTABLE_FIELDS)` → `commit_to_queue` → `store.upsert_queue_row` | ✓ (real graph + real borrowed SQLite; row observed with a live query) | ✓ FLOWING |
| durable `thread_id` | `derive_thread_id(note)` | `case_id_for_note` → `case_id_for` (content hash of the stripped note) | ✓ (recomputable; matches `case_id_for(note.strip())`) | ✓ FLOWING |

No static returns, hardcoded literals, mocks, or empty-prop stubs on the delivered paths.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite green + hermetic | `uv run pytest -q` | `454 passed in 33.59s` (expected 454); no non-cache `*.db`/`spans.jsonl` at repo root | ✓ PASS |
| Phase-6 focused suites | `uv run pytest tests/test_graph_durable.py tests/test_commit_idempotent.py tests/test_durable_cli.py -q` | `24 passed in 0.91s` | ✓ PASS |
| Bare demo hermetic storyboard | `triagedesk demo` (repo root) | exit 0, five beats, **no `*.db`**, zero `thread_id=` lines | ✓ PASS |
| Durable pause | `triagedesk demo --durable --beat escalation --db …/checkpoints.db` | exit 0; exactly one `thread_id=` line; one `resume:` line; checkpoint file created (61 KB) | ✓ PASS |
| Restart → resume approve | fresh `triagedesk resume --thread-id 9300336d37c3651c --decision approve … --db …` | `committed case … at queue position 1 (ORANGE)`; exit 0; real queue = **1** row | ✓ PASS |
| Edit supersedes (real store) | fresh pause + `resume … --decision edit --colour GREEN …` | `already committed … position 1 (GREEN)`; queue = **1** row, GREEN, position 1, `created_at` unchanged | ✓ PASS |
| dismiss refused, no write | `resume --thread-id <pending> --decision dismiss …` | exit 0; `clinician dismissed the priority; refusing to commit` | ✓ PASS |
| Absent thread | `resume --thread-id absent-thread --decision dismiss …` | exit 1; `no pending approval gate for thread_id absent-thread in …` | ✓ PASS |
| Per-tool audit exactly once per run | live `SELECT tool, COUNT(*) FROM audit GROUP BY tool` | each owned tool = 2 across two lifecycle runs (one per run; no within-run replay) | ✓ PASS |
| `thread_id` derivability | `derive_thread_id == case_id_for(note.strip()) == case_id_for_note(note)`; whitespace-independent | holds; id `9300336d37c3651c` | ✓ PASS |

**Environmental note.** The first `uv run pytest -q` on this tree reported `1 failed, 453 passed`: `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root` (a **Phase 7** hermeticity guard) tripped on a stale, **gitignored** `spans.jsonl` at the repo root (mtime `2026-10-13T12:10:29Z`, ~1 h before this pass — a leftover from an earlier run, not written by the suite). After removing that generated artifact, the suite is `454 passed` and the artifact does not reappear (confirmed by a second full run). This is an environment artefact, not a Phase 6 regression.

### Probe Execution

No probes declared in PLAN/SUMMARY and no `scripts/*/tests/probe-*.sh` in the repo — not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| AGENT-01 | 06-01-PLAN.md, 06-02-PLAN.md | Durable `checkpointed_graph` E2E; paused case resumes after restart on a stable `thread_id`; `edit` supersedes rather than duplicates (key covers immutable case content, not `colour` alone). | ✓ SATISFIED | Truths 1–9. `REQUIREMENTS.md` maps AGENT-01 → Phase 6 (marked Complete, line 90). No other requirement ID maps to Phase 6 ⇒ **no orphaned requirements**. |

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/test_graph_durable.py` | AGENT-01 | 4 | 0 | 0 | Behavioral (multi-step restart/exactly-once/edit-supersede) | ✓ PASS |
| `tests/test_commit_idempotent.py` | AGENT-01 | 9 | 0 | 0 | Behavioral (one-row/supersede/crash-retry) | ✓ PASS |
| `tests/test_durable_cli.py` | AGENT-01 | 9 | 0 | 0 | Behavioral (CLI parse/dispatch/refusal) | ✓ PASS |

**Disabled tests on requirements:** 0 → no BLOCKER. **Circular patterns detected:** 0 → no BLOCKER. **Insufficient assertions:** 0 → no WARNING.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts. (`check.decision-coverage-verify`: `total: 15, honored: 15, not_honored: []`.)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX` markers, no empty-implementation or hollow-prop patterns in any covered file. (`_RESUME_PLACEHOLDER` in `durable.py:47` is a documented, intentional constant whose docstring states it is never read on resume; `nodes.escalate` `return {}` is an idempotent no-op; `borrowed.py` `return []` is an unparseable-JSON guard — none is a debt marker or stub.) | ℹ️ Info | None |

Carried **Info** findings from `06-REVIEW.md` (status: clean; 0 critical / 0 warning), all dispositions `open` and explicitly outside the `critical_warning` fix scope — none blocks a must-have:

- **IN-06** — `docs/DEMO.md` per-beat expected-output blocks omit the `handover card:`/`commit:` lines the CLI prints (inaccurate claim, not behaviour; docs sweep).
- **IN-07** — `store/queue.py:75` supersede unconditionally writes the caller's `target`; harmless today (the real path always passes `target=None`) but latent if a future caller sets one.
- **IN-08** — the borrowed UPSERT is string-asserted only in the suite, never executed in an automated test. Partially mitigated by this re-verification: the real `INSERT … ON CONFLICT … DO UPDATE` was exercised by hand against the live `npx mcp-sqlite` store (Truth 3 / spot-checks); an integration test would still close the gap.

### Advisory (New Scope, Unevidenced)

None. Re-verification ran; no new-scope Step-7 finding was raised, so nothing was downgraded to advisory and nothing blocks.

### D-18 / Iron-Clad Guardrails

- `git diff 818b1ec HEAD -- src/triagedesk/core/scorer.py src/triagedesk/core/citations.py` is **empty** — the scorer and citation helper are untouched by Phase 6 **and** by Phases 7–12.
- The `@audited` interceptor body is unchanged; Phase 7 added `trace_id` plumbing at the audit seam but preserved the one-record-per-call behaviour (per-tool counts still exactly 1 per run).
- DRY/SOLID: the key derivation lives once (`content_hash` fed by the schema-derived `IMMUTABLE_FIELDS`); the strip-then-derive rule lives once (`case_id_for_note`); the pause/resume plumbing lives once (`durable.py`); the store resolves through the one `mcp.server.resolve_store` seam; the decision shape lives once (`approval_decision`). The purity guard (`tests/test_purity.py`) and the SATS-duplication guard (`tests/test_no_duplicated_sats.py`) are green in the 454-pass run.

### Human Verification Required

None. Every success criterion — including the process-restart, edit-supersede, dismissal-refusal, and per-tool-audit properties — was re-exercised end-to-end against real processes and the real borrowed SQLite store on the current tree; nothing remains that grep/presence checks cannot see.

### Gaps Summary

No gaps. All four ROADMAP Phase 6 success criteria are TRUE against the current codebase (SC3/SC4 under the reading resolved in `06-RESEARCH.md` and locked decision D6-08). All 9 must-haves verified, all artifacts present/substantive/wired, all key links wired, data flows end-to-end, requirement AGENT-01 satisfied with no orphans, and no debt markers or blockers. Phases 7–12's additive changes did **not** regress any Phase 6 property: the durable semantics, the content-derived `thread_id`, the immutable-case-input key, and the supersede-in-place write all hold. `uv run pytest -q` → **454 passed** (hermetic: no repo-root `*.db`/`spans.jsonl` needed by the suite).

---

_Verified: 2026-10-13T13:15:32Z_
_Verifier: the agent (gsd-verifier)_
