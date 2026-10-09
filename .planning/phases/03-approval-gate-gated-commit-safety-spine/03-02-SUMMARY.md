---
phase: 03-approval-gate-gated-commit-safety-spine
plan: 02
subsystem: database
tags: [mcp, mcp-sqlite, sqlite, idempotency, content-hash, store, protocol, approval-gate, pydantic, solid]

# Dependency graph
requires:
  - phase: 03-approval-gate-gated-commit-safety-spine
    provides: "the tracer graph, the side-effect-free approval_gate interrupt, the gated commit node, and ApprovalToken.final_colour (Plan 03-01)"
  - phase: 02-deterministic-scorer-owned-tools
    provides: "core.schema (ApprovalToken/CommitResult), the gated commit_priority stub contract, core.hashing.hash_value"
  - phase: 01-foundation-local-model-mcp-spike
    provides: "mcp.adapter.load_borrowed_tools (the separate borrowed adapter context) and the verified mcp-sqlite@1.0.9 handshake (evidence/mcp-spike.json)"
provides:
  - "store/ package: the ONE Store protocol (ensure_schema, read_queue_row, next_position, upsert_queue_row, read_case) + QueueRow/CaseRow contracts (D-10, D-13)"
  - "store/borrowed.py: the borrowed pinned mcp-sqlite@1.0.9 reached in its OWN adapter context; tool names declared once as data; BorrowedStore over an injected tool mapping (SOLID: O/L)"
  - "store/queue.py: the ONE idempotent write, keyed by (case_id, immutable content hash); volatile fields structurally excluded (D-06, Pitfall 14)"
  - "the real gated commit_priority: refuses (no store access) without a valid token or on dismiss; commits once through the injectable seam (GATE-02/GATE-03)"
  - "tests/conftest.py: ONE shared in-memory Store double + an autouse server-seam injection fixture (DRY, D-13)"
affects: [03-approval-gate-gated-commit-safety-spine, 04-evaluation, 05-demo]

# Actuals (#2632) — pairs with the plan's estimate (58000 tokens, low confidence).
# Same estimateTokens scale (chars/4 over the realized diff), never a harness count.
actuals:
  tokens: 11357
  tasks: 3
  commits: 3
  plan_head_before: 49e7063475b178b75565961a7bc0fbd92075f759
  plan_head_after: 42b7bd6e44a7a4432f16b678998effcfc9790124

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One narrow Store protocol the graph/server depend on; the borrowed SQLite MCP is one implementation behind it (SOLID: D/L)"
    - "Idempotency key = case_id + a content hash over IMMUTABLE fields only; volatile fields structurally excluded (D-06, Pitfall 14)"
    - "Crash-safety attributed to the idempotency key, not a transaction primitive the borrowed server does not expose"
    - "One shared in-memory Store test double + an autouse fixture injecting it into the server's store seam"

key-files:
  created:
    - src/triagedesk/store/__init__.py
    - src/triagedesk/store/borrowed.py
    - src/triagedesk/store/queue.py
    - tests/conftest.py
    - tests/test_borrowed_store.py
    - tests/test_commit_idempotent.py
  modified:
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/core/schema.py
    - tests/test_mcp_tools.py

key-decisions:
  - "The graph and the server depend on the Store protocol, never on the borrowed tool set; a World-B store swap touches store/borrowed.py alone (D-13, SOLID: D/L)"
  - "The borrowed server is reached in its OWN adapter context (load_borrowed_tools) — never merged with the owned server, so no protocol-era collapse"
  - "content_hash reads ONLY IMMUTABLE_FIELDS (colour, target, triggered_rules, citations, used_vitals); the approval timestamp and any volatile field are structurally excluded (D-06, Pitfall 14)"
  - "commit_to_queue is the ONE idempotent write: an existing (case_id, content_hash) key is returned unchanged and no second row is inserted; crash-safety IS the key"
  - "commit_priority became async (the borrowed store is async); the refusal path returns BEFORE any store call, so no path reaches the store without a valid named approval (GATE-02, T-03-09)"
  - "The committed colour is token.final_colour for an edit and the scored colour for an approve (D-05); final_colour is substrate-validated by ApprovalToken"
  - "The server hashes the immutable content available at the tool boundary (case_id + committed colour); the queue-level helper supports the fuller immutable set for richer callers"
  - "DOMAIN_DB_PATH is owned by the store package (single source); graph/build.py imports it rather than re-declaring the filename"

patterns-established:
  - "Borrowed-tool names declared once as module constants; the wiring reads them, never inlines string literals (SOLID: O)"
  - "Store seam: a module-level injected store with a set_store() hook + a default borrowed factory, resolved lazily by the commit path"

requirements-completed: [TOOL-06, GATE-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "A borrowed, pinned SQLite MCP server (mcp-sqlite@1.0.9) provides case/queue storage behind a narrow injectable Store protocol; the gate stays ours"
    requirement: "TOOL-06"
    verification:
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_expected_tools_match_the_phase_1_handshake"
        status: pass
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_ensure_schema_creates_both_tables_via_the_query_tool"
        status: pass
      - kind: unit
        ref: "tests/test_borrowed_store.py#test_upsert_queue_row_inserts_through_the_query_tool"
        status: pass
    human_judgment: false
  - id: D2
    description: "Committing the same case twice (including across a simulated crash) yields exactly one queue row; a volatile timestamp never churns the key"
    requirement: "GATE-03"
    verification:
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_commit_twice_yields_one_row"
        status: pass
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_volatile_timestamp_does_not_change_the_content_hash"
        status: pass
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_crash_then_retry_yields_one_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "commit_priority refuses without a valid token (or on dismiss) and writes nothing; an edit commits the token's final_colour, an approve the scored colour"
    requirement: "GATE-03"
    verification:
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_commit_priority_refuses_without_a_token_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_commit_priority_refuses_a_dismiss_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_commit_priority_edit_commits_the_tokens_final_colour"
        status: pass
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_commit_priority_commits_once_through_the_injected_store"
        status: pass
    human_judgment: false

# Metrics
duration: 9min
completed: 2026-10-09
status: complete
---

# Phase 3 Plan 2: Borrowed Idempotent Queue Store + Real Gated Commit Summary

**A pinned borrowed SQLite MCP server (mcp-sqlite@1.0.9) now stores the queue behind a narrow injectable protocol, and the real `commit_priority` writes idempotently — keyed by `case_id` + an immutable content hash — so a retry or a crash cannot double-place a patient, while the refusal path still writes nothing without a named clinician's token.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-10-09T16:17:16Z
- **Completed:** 2026-10-09T16:25:48Z
- **Tasks:** 3
- **Files modified:** 10 (6 created, 4 modified)

## Accomplishments
- The `store/` package: ONE `Store` protocol (`ensure_schema`, `read_queue_row`, `next_position`, `upsert_queue_row`, `read_case`) with `QueueRow`/`CaseRow` contracts. The graph and the server depend on the protocol, never on the borrowed tool set (D-10, D-13, SOLID: D/L).
- `store/borrowed.py` is the ONE module that reaches `mcp-sqlite@1.0.9`, in its own adapter context (no era collapse); the borrowed tool names are declared once as data and `BorrowedStore` implements the protocol over an injected `name -> async callable` mapping (SOLID: O/L).
- The **idempotency key is the safety mechanism**: `content_hash` reads only immutable case content (`colour`, `target`, `triggered_rules`, `citations`, `used_vitals`) through the ONE hashing path; the approval timestamp and any volatile field are structurally excluded (D-06, Pitfall 14). A crash-retry re-derives the same key, so the upsert is a no-op and a second row cannot appear.
- The real gated `commit_priority`: the refusal path returns **before any store call** (absent/malformed/`dismiss`), and only a validated token reaches the store through the injectable seam — `edit` commits `token.final_colour`, `approve` the scored colour (GATE-02/GATE-03, D-05).
- `tests/conftest.py` provides ONE shared in-memory `Store` double plus an autouse fixture that injects it into the server's store seam, so the whole offline suite exercises the real commit path without launching the borrowed subprocess (DRY, D-13).

## Task Commits

Each task was committed atomically:

1. **Task 1: Borrowed SQLite MCP store behind the tool interface** - `3df1bbe` (feat)
2. **Task 2: Idempotent queue write keyed by case_id + immutable content hash** - `fedb6f1` (feat)
3. **Task 3: Real gated commit_priority — token required, refusal before any write** - `42b7bd6` (feat)

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified
- `src/triagedesk/store/__init__.py` - The ONE `Store` protocol + `QueueRow`/`CaseRow`; owns `DOMAIN_DB_PATH`; the lazy `default_store` factory
- `src/triagedesk/store/borrowed.py` - The borrowed mcp-sqlite@1.0.9 wiring: tool names as data, `BorrowedStore` over an injected tool mapping, `open_borrowed_store`
- `src/triagedesk/store/queue.py` - `content_hash` (immutable-only) + `commit_to_queue` (the ONE idempotent write)
- `src/triagedesk/mcp/server.py` - The real gated `commit_priority` (async), the `set_store`/`_resolve_store` injectable seam, updated module docstring
- `src/triagedesk/graph/build.py` - Imports `DOMAIN_DB_PATH` from `store` (single source) and declares `__all__`
- `src/triagedesk/core/schema.py` - `CommitResult` docstring updated off the stale "stub" language
- `tests/conftest.py` - The shared in-memory `Store` double + the autouse server-seam injection fixture
- `tests/test_borrowed_store.py` - Borrowed wiring proof against a fake tool set (the real handshake is Phase-1 evidence)
- `tests/test_commit_idempotent.py` - Double-commit, volatile-timestamp, crash-retry, refusal-no-write, edit-colour, seam-injection
- `tests/test_mcp_tools.py` - The two Phase-2 stub assertions replaced by the committed behaviour

## Decisions Made
- The graph and the server depend on the `Store` protocol, not the borrowed tool set; a World-B store swap touches `store/borrowed.py` alone (D-13, SOLID: D/L).
- The borrowed server is reached in its OWN adapter context (`load_borrowed_tools`), never merged with the owned server — avoiding the protocol-era collapse.
- `content_hash` reads only `IMMUTABLE_FIELDS`; an extra key (e.g. `approved_at`) cannot influence the digest, so a retry cannot churn the key (Pitfall 14).
- Crash-safety is the idempotency key itself — the borrowed server exposes no transaction call, so any store transaction is belt-and-braces only (D-06).
- `commit_priority` is now async (the borrowed store is async); the refusal path returns before any store call (GATE-02, T-03-09).
- `DOMAIN_DB_PATH` is owned by the `store` package; `graph/build.py` imports it instead of re-declaring the filename.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Single source for the domain DB path (`triage.db`)**
- **Found during:** Task 1 (introducing `store/DOMAIN_DB_PATH`)
- **Issue:** `graph/build.py` already declared `DOMAIN_DB_PATH = Path("triage.db")`; adding the store's own copy would duplicate the filename (DRY smell), and the plan's `files_modified` did not list `graph/build.py`.
- **Fix:** `graph/build.py` now imports `DOMAIN_DB_PATH` from `triagedesk.store` (the single source) and declares `__all__`; `test_checkpointer_and_domain_store_are_separate_files` still passes.
- **Files modified:** src/triagedesk/graph/build.py
- **Verification:** `uv run pytest -q` → 141 passed.
- **Committed in:** `3df1bbe` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Updated the stale `CommitResult` docstring**
- **Found during:** Task 3 (real commit)
- **Issue:** `core/schema.py`'s `CommitResult` docstring still described "the gated commit stub" and claimed `committed` is "only ever `True` once the real idempotent commit exists (Phase 3)" — now false.
- **Fix:** Rewrote the docstring to describe the real idempotent commit contract.
- **Files modified:** src/triagedesk/core/schema.py
- **Verification:** `uv run pytest -q` → 141 passed.
- **Committed in:** `42b7bd6` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 missing critical)
**Impact on plan:** Both are small DRY/documentation corrections forced by the plan's own store/commit introduction. No scope creep, no behaviour change.

## Issues Encountered
- The plan's Task 2 verify (`pytest tests/test_commit_idempotent.py -k "twice or crash or hash"`) references a file owned by Task 3. As in Plan 03-01, the test module was authored alongside and used to verify Task 2 against the working tree; its commit lands with Task 3, consistent with the plan's file ownership.

## Known Stubs
- `src/triagedesk/graph/nodes.py` (`handover`): `HandoverCard.second_look` is still always `None` in the tracer — the serial-vitals recheck is wired in a later Phase-3 plan (D-07). Unchanged by this plan; recorded in `.planning/WINDOWS.md` (entry #2, open).
- `src/triagedesk/mcp/server.py`: the Phase-2 `commit_priority` stub is now the real idempotent commit — WINDOWS.md entry #1 is marked fixed by this plan.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: borrowed-persistence | src/triagedesk/store/borrowed.py | The queue write now reaches a third-party (borrowed) MCP server over the pinned `mcp-sqlite@1.0.9`. Mitigated by the plan's T-03-10: a narrow protocol behind the tool interface, tool names as data, and the idempotency key — no new surface beyond the plan's threat model. |

## User Setup Required
None - no external service configuration required. (The borrowed server is fetched on demand by `npx -y mcp-sqlite@1.0.9` and was legitimacy-reviewed in Phase 1.)

## Next Phase Readiness
- The store protocol, the borrowed wiring, and the idempotent write are fixed and proven; later Phase-3 plans (audit interceptor, `store/audit.reconcile`, recheck/recovery edges) slot in behind the same `Store` interface.
- The gated commit now performs the real idempotent write; the graph's `commit` node reaches it unchanged via the injected tool mapping.
- Blocker carried forward: the audit append + reconciliation (`store/audit.reconcile`) is Plan 03-03 — the narrow queue-write/audit-append window is detected and reconciled there, not assumed atomic (D-09, T-03-08).

---
*Phase: 03-approval-gate-gated-commit-safety-spine*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 6 created files exist on disk (store package, conftest, both proof suites) and the 4 modified files are present.
- All 3 task commits are ancestors of HEAD: `3df1bbe`, `fedb6f1`, `42b7bd6`.

