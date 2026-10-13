---
phase: 09-retrieval-grounding-borrowed-mcp-depth
plan: 02
subsystem: store / mcp / borrowed-sqlite-adapter
tags: [mcp, sqlite, read-only-allowlist, fail-closed-guard, store-protocol, dry, solid]

requires:
  - phase: 01-05 (v1.0)
    provides: store/__init__.py (the Store protocol), store/borrowed.py (the borrowed adapter + its declared read-tool constants), mcp/server.py's refuse-before-touch posture
provides:
  - "store/borrowed.py — READ_TOOLS allowlist + fail-closed is_read_only_statement classifier applied at the ONE _call seam"
  - "BorrowedStore._call(name, arguments, *, write=False) — the single read-only enforcement point; refuses off-allowlist tool names and non-read statements BEFORE touching the injected tool mapping"
  - "ensure_schema read-path probe (_probe_read_paths) recording read_path_report for db_info/list_tables/get_table_schema/read_records"
  - "MCP-01 proof suite: read tools observed called, a mutation provably refused on the fake's call log, an unverified read shape provably degrading"
affects: [09-03 graph grounding, 10 UX adapter]

actuals:
  tokens: 4581
  tasks: 2
  commits: 2
  plan_head_before: 3db929ec0f53166910b2725a3558cd26647aaffe
  plan_head_after: 45f0b084c4b34ef6b27deb2eb3f1196907a6d264

tech-stack:
  added: []   # intentionally zero new dependencies
  patterns:
    - "Read-only by construction: ONE guarded dispatch seam (allowlist + fail-closed statement classifier) instead of scattered per-call checks"
    - "Privileged-write opt-in: write=True is a keyword-only flag reserved for schema bootstrap and the gated commit; the agent path cannot reach a mutation"
    - "Additive diagnostic probe: every borrowed read path is exercised on store open and any shape surprise is RECORDED as a degradation string, never raised"
    - "Unverified wire shapes are consumed defensively — a shape mismatch degrades instead of crashing the store-open path"

key-files:
  created: []
  modified:
    - src/triagedesk/store/borrowed.py
    - tests/test_borrowed_store.py
    - tests/test_observability.py

key-decisions:
  - "READ_TOOLS is the set-equality allowlist at the ONE _call seam; the three mutating record tools (create_record/update_records/delete_records) are unnameable by any caller (D9-12, T-09-21)"
  - "is_read_only_statement is a pure, fail-closed leading-keyword classifier (SELECT/PRAGMA/EXPLAIN/WITH/VALUES); the empty string is not a read (D9-12, T-09-20)"
  - "The guard runs BEFORE self._tools is dereferenced, so a refused call provably reaches no borrowed server — proven on the fake's call log, not merely on the raise"
  - "write=True is passed at exactly the four bootstrap DDL statements, the trace_id ALTER, upsert_queue_row, write_chain_head and append_audit_record — the gated commit's writes remain the only mutation route (D9-13)"
  - "The trace_id column check stays on the verified PRAGMA table_info read; get_table_schema is used additively by the probe only (RESEARCH Pitfall 3)"
  - "The read-path probe is additive diagnostics: db_info/list_tables/get_table_schema/read_records are exercised on store open; every probe is individually wrapped so a shape mismatch records a degradation and never fails the open (D9-11/D9-14, T-09-22)"

patterns-established:
  - "A single guarded dispatch seam is the read-only enforcement point; a second call path would bypass it, so no second path exists"
  - "Refuse-before-touch for the borrowed server mirrors commit_priority's refuse-before-store posture"
  - "Unverified external wire shapes get a recorded-degradation probe, never an unguarded call"

requirements-completed: [MCP-01]

coverage:
  - id: D1
    description: "The borrowed read tools (db_info/list_tables/get_table_schema/read_records) are actually reached through the adapter, not merely declared"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_ensure_schema_observes_the_borrowed_read_tools"
        status: pass
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_read_tools_are_exactly_the_five_reads"
        status: pass
    human_judgment: false
  - id: D2
    description: "The read paths are exercised behind the unchanged Store protocol — no protocol method signature changed"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "git diff --stat 3db929e HEAD -- src/triagedesk/store/__init__.py (empty)"
        status: pass
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_ensure_schema_creates_both_tables_via_the_query_tool"
        status: pass
    human_judgment: false
  - id: D3
    description: "A mutation statement and an off-allowlist tool name are refused BEFORE the borrowed tool is invoked (fail closed)"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_a_mutation_on_the_read_path_is_refused_before_the_borrowed_server"
        status: pass
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_an_off_allowlist_tool_name_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_classifier_fails_closed_on_everything_else"
        status: pass
    human_judgment: false
  - id: D4
    description: "A read-path shape mismatch degrades — recorded, and never crashes the store-open path"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_a_read_path_shape_mismatch_degrades_without_raising"
        status: pass
    human_judgment: false
  - id: D5
    description: "The gated write path still works: bootstrap DDL, the queue upsert, the chain-head write and the audit insert all still reach the borrowed server"
    requirement: MCP-01
    verification:
      - kind: integration
        ref: "uv run pytest tests/test_commit_idempotent.py tests/test_audit_chain.py tests/test_durable_cli.py -q"
        status: pass
      - kind: unit
        ref: "tests/test_observability.py#test_audit_trace_id_round_trips_through_the_borrowed_store"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-12
status: complete
---

# Phase 9 Plan 02: Borrowed-MCP Depth — Read Paths, Allowlist & Fail-Closed Guard Summary

**The borrowed SQLite MCP server's read paths (`db_info`, `list_tables`, `get_table_schema`, `read_records`) are now genuinely reached behind the unchanged `Store` protocol, with a tool allowlist and a fail-closed statement guard proving the agent path can never issue a mutation.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-10-12T18:20Z (approx)
- **Completed:** 2026-10-12T18:31Z
- **Tasks:** 2
- **Files modified:** 3 (2 test, 1 source)

## Accomplishments

- **The read-path deepening.** `BorrowedStore` previously declared `TOOL_DB_INFO` / `TOOL_LIST_TABLES` / `TOOL_GET_TABLE_SCHEMA` / `TOOL_READ_RECORDS` but only ever called `query`. `ensure_schema` now sets `read_path_report = await self._probe_read_paths()`, which exercises all four tools through the guarded seam and records an `ok` / `degraded: …` verdict per tool. This is MCP-01 demonstrated, not asserted (D9-11/D9-14).
- **The read-only allowlist.** `READ_TOOLS` is the five read tools; the three mutating record tools are excluded so no caller can name them. Asserted as set-equality, plus a disjointness check.
- **The fail-closed statement guard.** `is_read_only_statement` accepts only a leading `SELECT`/`PRAGMA`/`EXPLAIN`/`WITH`/`VALUES`; everything else — including the empty string — is not a read. Applied at the ONE dispatch seam `_call(name, arguments, *, write=False)`.
- **Refuse-before-touch, proven on the evidence.** Both refusals (`not in the read-only allowlist`, `non-read statement`) raise before `self._tools` is dereferenced. The proof asserts on the fake's call log (`fake.calls == []`), not merely on the raise — mirroring `commit_priority`'s refuse-before-store posture.
- **Safe degradation for unverified shapes.** The real `mcp-sqlite@1.0.9` arg shapes for `read_records`/`get_table_schema` are unverified (RESEARCH Pitfall 4 / A1). Each probe is individually wrapped: a raising `db_info` and a scalar `read_records` payload are recorded as degradations while `ensure_schema` completes and the queue read/upsert still function.
- **The gated write path is intact.** `write=True` is passed only at the four bootstrap DDL statements, the `trace_id` ALTER, `upsert_queue_row`, `write_chain_head` and `append_audit_record`. The idempotency and audit-chain suites stay green.
- **`_SqliteBorrowedTools` now reads the live connection** for `get_table_schema` (real `PRAGMA table_info` columns) and `read_records` (real bounded rows), closing the RESEARCH Pitfall 3 trap so the stand-in can no longer lie about columns.

## Task Commits

Each task was committed atomically:

1. **Task 1: the read-path deepening, the read-only tool allowlist, and the fail-closed statement guard** — `576efd4` (feat)
2. **Task 2: the MCP-01 proofs and the stdlib stand-in's real read shapes** — `45f0b08` (test)

**Plan metadata:** skipped (commit_docs disabled — see Issues Encountered)

## Files Created/Modified

- `src/triagedesk/store/borrowed.py` — `READ_TOOLS`, `_READ_PREFIXES`, `_PROBE_LIMIT`, `is_read_only_statement`, the guarded `_call(write=…)`, the `read_path_report` probe in `ensure_schema`, `write=True` at the seven privileged call sites, `__all__` and docstring updated
- `tests/test_borrowed_store.py` — 19 new proofs: read tools observed called; mutation refused with a clean call log; off-allowlist tool refused; fail-closed classifier table; unverified-shape degradation; allowlist set-equality
- `tests/test_observability.py` — the stdlib `sqlite3` stand-in's `get_table_schema`/`read_records` now query the live connection instead of returning a column-less stub

## Decisions Made

- **Keep the `trace_id` column check on the verified `PRAGMA table_info` read.** `get_table_schema` is used additively by the probe only. Switching the check to the unverified tool would risk a duplicate-column ALTER (RESEARCH Pitfall 3) — and the stand-in was fixed in the same wave regardless, per the plan.
- **`write=True` as a keyword-only opt-in.** One flag on the one seam keeps the privileged route explicit and reviewable, and it is impossible to pass positionally by accident.
- **Degrade, do not probe live.** Per the plan's `assumption_delta_decision`, the phase proves MCP-01 hermetically against the stdlib stand-in and does not block on a live `npx` borrowed-server run; a degraded entry in `read_path_report` is visible evidence to act on during the pre-demo real run.
- **No second classifier, no second call path.** DRY/SOLID: the allowlist and classifier live once and are enforced once, so the guard cannot be bypassed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **The `#3819` pre-commit HEAD assertion cannot be honoured as written in this repo, and the phase's own precedent confirms the intent.** The template's check is `gsd_run query git.base-branch --is-protected "$ACTUAL_BRANCH"`; the installed SDK's `git base-branch` verb takes no such flag and returns the *default-branch name* (`main`), so the result is never the boolean the assertion expects. This repository is configured with `git.branching_strategy: "none"` and `workflow.use_worktrees: false`, has no `git.allow_default_branch_commits` override, and this phase's sibling plan 09-01 already committed to `main` in the same run — the orchestrator spawned this as a **sequential executor on the main working tree** instructed to use normal git commits. Commits were therefore made on `main`, consistent with the repo configuration and the phase's established precedent. **Not a deviation from the plan** (the plan is silent on branching); recorded here because it is a divergence from the executor template's literal guard text and a reviewer should see it.
- **Plan metadata commit skipped.** `commit_docs: false` in `.planning/config.json`, so the SDK's metadata commit is an intentional no-op; `.planning/` artefacts are deliberately left out of git history, matching plan 09-01.
- **Pre-existing `ruff format` drift, out of scope.** `ruff format --check` reports reformatting for lines untouched by this plan (e.g. `_CASES_DDL`), verified against `HEAD`'s blob — it was already dirty. `ruff check` (the lint gate) passes. Left as-is per the scope boundary.

## Known Stubs

None. Every probe entry is either `"ok"` or an explicit, recorded `"degraded: …"` string — a degradation is a visible diagnostic, not a stub, and it cannot mask a failure because the store remains fully usable and `read_path_report` is recorded.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change at a trust boundary was introduced beyond the plan's threat model. This plan *closes* T-09-20/T-09-21/T-09-22/T-09-23: the allowlist, the fail-closed classifier, the individually-wrapped probe and the unchanged parameterised `values` are the mitigations.

## User Setup Required

None - no external service configuration required. No package is installed by this plan; `BORROWED_SERVER_PACKAGE` stays pinned at the reviewed `mcp-sqlite@1.0.9`.

## Next Phase Readiness

- Plan 09-03 (the `ground` node, the `evidence` state channel, `score → ground → verify`) is unblocked; the borrowed read-path depth no longer gates it.
- The ONE `_call` seam is now the read-only enforcement point: any future borrowed read must go through it, and any new mutating need must justify a `write=True` site explicitly.
- On the pre-demo real run, inspect `store.read_path_report`; a `degraded:` entry for `read_records`/`get_table_schema` is the expected signal that the unverified `mcp-sqlite@1.0.9` arg shape differs from the stand-in's and needs a live shape dump (RESEARCH A1).
- No blockers. `src/triagedesk/store/__init__.py` is byte-identical (the `Store` protocol shape is unchanged); no dependency was added; `data/*.yaml`, the scorer's arithmetic, `core/citations.py` and the `@audited` interceptor are untouched.

---

**Full suite:** `uv run pytest -q` → **334 passed** (315 baseline + 19 new).

---
*Phase: 09-retrieval-grounding-borrowed-mcp-depth*
*Completed: 2026-10-12*

## Self-Check: PASSED

- FOUND: `src/triagedesk/store/borrowed.py`
- FOUND: `tests/test_borrowed_store.py`
- FOUND: `tests/test_observability.py`
- FOUND: `.planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-02-SUMMARY.md`
- FOUND: commit `576efd4` (Task 1)
- FOUND: commit `45f0b08` (Task 2)
- `git diff --stat 3db929e HEAD -- src/triagedesk/store/__init__.py` → empty (the `Store` protocol shape is unchanged)
- `git diff --stat` for this plan: 3 files changed, 309 insertions(+), 11 deletions(-); commits measured `git rev-list --count <ledger>..HEAD` = 2
