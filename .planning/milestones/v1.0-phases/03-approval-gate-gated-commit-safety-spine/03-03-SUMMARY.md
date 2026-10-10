---
phase: 03-approval-gate-gated-commit-safety-spine
plan: 03
subsystem: database
tags: [audit, hash-chain, tamper-evidence, mcp, store, interceptor, dr-y, solid, pydantic]

# Dependency graph
requires:
  - phase: 03-approval-gate-gated-commit-safety-spine
    provides: "the Store protocol + borrowed mcp-sqlite@1.0.9 wiring, the idempotent queue write, and the injectable store seam (Plan 03-02)"
  - phase: 02-deterministic-scorer-owned-tools
    provides: "core.hashing.canonical_json/hash_value (the ONE canonical serialisation path) and the shared core.schema contracts"
  - phase: 03-approval-gate-gated-commit-safety-spine
    provides: "the gated commit_priority (refuses without a valid named approval) and the ApprovalToken contract (Plans 03-01/03-02)"
provides:
  - "store/audit.py: the ONE audit helper — AuditRecord (the single record-shape source), record_digest (the one sealing path), append (the single write path, chained to the persisted head), verify (recompute + report the first break), reconcile (queue-vs-audit divergence detection)"
  - "the Store protocol's audit seam (read/write chain head, append/read records, read_queue_rows), implemented by the borrowed store and the in-memory double (AUDIT-01, D-08)"
  - "mcp/server.audited: ONE uniform interceptor wrapping every owned tool, so no owned tool call escapes the audit (AUDIT-03, T-03-15)"
  - "the persisted chain head (audit_head table), so the chain verifies after a restart (M-6)"
affects: [03-approval-gate-gated-commit-safety-spine, 04-evaluation, 05-demo]

# Actuals (#2632) — pairs with the plan's estimate (54000 tokens, low confidence).
# Same estimateTokens scale (chars/4 over the realized diff), never a harness count.
actuals:
  tokens: 9537
  tasks: 3
  commits: 3
  plan_head_before: d305326e68dfa896d6487019a3e532398cf82521
  plan_head_after: 1d1d9e7facd89a42cc2f65f4ea6ca23ad20587f9

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One record shape (AuditRecord) + one sealing function (record_digest) shared by append and verify, so the writer and the verifier cannot drift (DRY)"
    - "The chain head is persisted in the authoritative store (audit_head), not reconstructed from an in-memory tail, so verification survives a restart (M-6)"
    - "append is the ONLY write path; verify/reconcile are read-only — no second write path, no claimed transaction primitive"
    - "ONE uniform @audited decorator applied under each @server.tool(); the record's tool name is the wrapped function's own name (no name drift)"
    - "The audit append happens AFTER the tool's own logic, so a refused commit (and a raising tool) is recorded honestly"

key-files:
  created:
    - src/triagedesk/store/audit.py
    - tests/test_audit_chain.py
  modified:
    - src/triagedesk/store/__init__.py
    - src/triagedesk/store/borrowed.py
    - src/triagedesk/mcp/server.py
    - tests/conftest.py

key-decisions:
  - "The audit-record shape is defined ONCE as AuditRecord; record_digest is the one canonical seal used by both append and verify (AUDIT-03, DRY)"
  - "The chain head is persisted in the store's audit_head table; the InMemoryStore restart() hands back a fresh handle over the same backing state, simulating a restart (M-6)"
  - "append reads the persisted head + the record count, builds the record with prev_hash=head, seals it, then writes the record and the new head — the only write path"
  - "verify recomputes every record's digest plus the prev_hash link and cross-checks the persisted head; a tampered record is reported by seq (T-03-11)"
  - "reconcile cross-checks every committed queue row against its approval audit record and reports any row without one; the window closes by re-issuing the idempotent commit (D-09, T-03-08)"
  - "ONE uniform @audited interceptor wraps every @server.tool(); the record's tool name is fn.__name__, so the audit name cannot drift from the registered tool name (AUDIT-01/03, T-03-15)"
  - "The gated commit records actor=clinician and, only on a successful commit, the named approver and role from the validated token (AUDIT-02)"
  - "A refused commit and a raising tool are both recorded (after the tool's logic), so the audit never claims a write that did not happen and no call escapes the audit"

patterns-established:
  - "Audit seam on the Store protocol (read/write head, append/read records, read queue rows), satisfied by both the borrowed store and the shared in-memory double (SOLID: L)"
  - "Uniform tool-call interception via a decorator under @server.tool(), keeping the tool bodies free of audit code"

requirements-completed: [AUDIT-01, AUDIT-02, AUDIT-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Every owned tool call appends exactly one canonical hash-chained record through ONE shared helper; the chain verifies after a restart and reports tampering at the altered row"
    requirement: "AUDIT-01"
    verification:
      - kind: unit
        ref: "tests/test_audit_chain.py#test_chain_links_each_record_to_the_previous"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_chain_verifies_after_a_restart"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_verify_reports_a_break_when_a_record_is_tampered"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_verify_on_an_empty_chain_is_valid"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_every_tool_call_appends_exactly_one_chained_record"
        status: pass
    human_judgment: false
  - id: D2
    description: "An approval record captures the named approver and role, so the queue write is attributable to a person"
    requirement: "AUDIT-02"
    verification:
      - kind: unit
        ref: "tests/test_audit_chain.py#test_approver_and_role_are_captured_on_an_approval_record"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_interceptor_records_the_named_approver_on_a_commit"
        status: pass
    human_judgment: false
  - id: D3
    description: "ONE shared helper owns the record shape and serialisation; one uniform interceptor routes every tool call through it; reconcile detects any queue row lacking its approval audit record"
    requirement: "AUDIT-03"
    verification:
      - kind: unit
        ref: "tests/test_audit_chain.py#test_canonical_record_hash_is_independent_of_key_order"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_interceptor_appends_exactly_one_record_per_call"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_interceptor_records_a_refused_commit_as_refused"
        status: pass
      - kind: unit
        ref: "tests/test_audit_chain.py#test_reconcile_reports_a_queue_row_without_an_approval_record"
        status: pass
    human_judgment: false

# Metrics
duration: 13min
completed: 2026-10-09
status: complete
---

# Phase 3 Plan 3: Hash-Chained Audit Spine Summary

**One shared helper now defines, canonicalises, chains and appends a tamper-evident audit record for every owned tool call — through ONE uniform interceptor — and the chain verifies after a restart from a persisted head while `reconcile` reports any queue row that lacks its approval record.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-10-09T16:58:55Z
- **Completed:** 2026-10-09T17:11:48Z
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- `store/audit.py` is the ONE audit helper (AUDIT-03, D-08): `AuditRecord` is the single definition of the ARCHITECTURE §6 record shape (extended with `seq` and `role`), `record_digest` is the one canonical sealing path (sorted-key compact JSON → sha256 via `core.hashing`), and `append` is the only write — it reads the persisted head, builds the record with `prev_hash = head`, seals it, then writes the record and the new head. Nothing else writes an audit record.
- The chain head is **persisted in the authoritative store** (`audit_head`), not reconstructed from an in-memory tail, so `verify` survives a restart (M-6). `verify` recomputes every record's digest plus the `prev_hash` link and cross-checks the persisted head, reporting the first break by `seq`; an empty chain verifies as valid (T-03-11).
- `reconcile` cross-checks every committed queue row against its matching approval audit record and reports any row without one — the narrow queue-write/audit-append window (D-09, T-03-08). It is read-only; the window closes by re-issuing the idempotent commit. No unsupported transaction primitive is claimed.
- The `Store` protocol gained the audit seam (`read_chain_head`, `write_chain_head`, `append_audit_record`, `read_audit_records`, `read_queue_rows`), implemented by **both** the borrowed `BorrowedStore` (new `audit`/`audit_head` tables in the domain store) and the shared in-memory double — so the audit store and the queue store are one authoritative place (AUDIT-03, SOLID: L).
- `mcp/server.audited` is ONE uniform interceptor applied under every `@server.tool()` (AUDIT-01/03, T-03-15): no owned tool call escapes the audit. The record's `tool` is the wrapped function's own name (no drift), the append happens **after** the tool's logic so a refused commit is recorded as a refused call, and a raising tool is recorded too. The gated commit records `actor="clinician"` and, on a successful commit, the named approver and role from the validated token (AUDIT-02).

## Task Commits

Each task was committed atomically:

1. **Task 1: The ONE audit helper — canonical record shape + hash-chain append** - `519da53` (feat)
2. **Task 2: Persist the chain head and verify the chain after restart** - `4ebd873` (feat)
3. **Task 3: Intercept every owned tool call through the one helper** - `1d1d9e7` (feat)

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified
- `src/triagedesk/store/audit.py` - The ONE audit helper: `AuditRecord`, `record_digest`, `append`, `verify`, `reconcile`, `ChainVerification`, `Reconciliation`, and the narrow `AuditStore` seam
- `src/triagedesk/store/__init__.py` - The `Store` protocol gains the audit + `read_queue_rows` seam; the helper and record shape are re-exported from the one store package
- `src/triagedesk/store/borrowed.py` - `BorrowedStore` implements the audit seam over two new tables (`audit`, `audit_head`) in the authoritative domain store
- `src/triagedesk/mcp/server.py` - `audited` — the ONE uniform tool interceptor — applied under each `@server.tool()`
- `tests/conftest.py` - The shared in-memory `Store` double gains the audit seam and a `restart()` handle over the same backing state (DRY, D-13)
- `tests/test_audit_chain.py` - Chain-link, canonical-hash, approver/role, restart, tamper, empty-chain, reconcile, one-record-per-call, refused-commit, named-approver, and every-tool-call-forms-one-chain proofs

## Decisions Made
- The record shape is defined ONCE (`AuditRecord`); `record_digest` is shared by `append` and `verify`, so the writer and verifier cannot drift (DRY).
- The chain head is persisted (`audit_head`); `InMemoryStore.restart()` shares the backing state, simulating a restart without a real SQLite file (M-6).
- `append` is the only write path; `verify`/`reconcile` are read-only (no second write path, no claimed transaction primitive).
- ONE uniform `@audited` interceptor; the record's tool name is `fn.__name__`, so the audit name cannot drift from the registered tool name.
- The append happens after the tool's logic, so a refused commit and a raising tool are recorded honestly.
- The gated commit captures the named approver/role only on a successful commit (AUDIT-02).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical / Rule 3 - Blocking] Extended the `Store` protocol with the audit seam and implemented it in `BorrowedStore`**
- **Found during:** Task 1 (the audit helper needs the authoritative store to persist records + the head)
- **Issue:** The audit helper persists records and the chain head to the same authoritative store (D-09). That requires the store to expose an audit seam. The plan's `files_modified` listed `store/__init__.py` but not `store/borrowed.py`; without the seam on `BorrowedStore`, the production default store would fail at runtime and would no longer satisfy the extended `Store` protocol (SOLID: L).
- **Fix:** Added `read_chain_head`/`write_chain_head`/`append_audit_record`/`read_audit_records`/`read_queue_rows` to the `Store` protocol and implemented them in `BorrowedStore` over two new tables (`audit`, `audit_head`) in the domain store.
- **Files modified:** src/triagedesk/store/__init__.py, src/triagedesk/store/borrowed.py
- **Verification:** `uv run pytest -q` → 167 passed; both `BorrowedStore` and `InMemoryStore` satisfy `isinstance(..., Store)`.
- **Committed in:** `519da53` (Task 1 commit)

**2. [Rule 3 - Blocking] The shared in-memory `Store` double gained the audit seam in Task 1**
- **Found during:** Task 1 (the Task 1/2 proof suite uses the shared `memory_store` fixture)
- **Issue:** The plan's Task 3 mentions extending `tests/conftest.py` with the audit seam, but Tasks 1 and 2 already need the shared `Store` double to satisfy the extended protocol; deferring the seam to Task 3 would have forced a duplicated per-test double (a DRY violation).
- **Fix:** Extended `InMemoryStore` with the audit seam (and a `restart()` handle) in Task 1; Task 3's interceptor tests reuse the same seam, so no further conftest change was needed.
- **Files modified:** tests/conftest.py
- **Verification:** `uv run pytest -q` → 167 passed.
- **Committed in:** `519da53` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both are forced by the plan's own decision to keep the audit and the queue in one authoritative store (D-09) and to use the shared Store double (DRY). No scope creep; the end state matches the plan's intent.

## Issues Encountered
- As in Plans 03-01/03-02, the `tests/test_audit_chain.py` module is authored incrementally alongside each task and committed with the task that owns it in the plan (Task 2). The Task 1 commit therefore lands the source files only, while the Task 1 verify runs against the working tree.

## Known Stubs
- None. Every function in `store/audit.py` and the interceptor is fully implemented and proven.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: borrowed-persistence | src/triagedesk/store/borrowed.py | The audit chain now persists to the borrowed `mcp-sqlite@1.0.9` server (two new tables: `audit`, `audit_head`). Mitigated by the plan's T-03-11/13/14/15: canonical serialisation, a persisted head, and the one uniform interceptor — no new surface beyond the plan's threat model. |

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The audit spine is complete: every owned tool call is chained through one helper, the chain verifies after a restart, and `reconcile` detects the queue/audit divergence window.
- The interceptor resolves its store through the same injectable seam as the commit path, so the whole offline suite exercises it without the borrowed subprocess (D-13).
- The remaining Phase-3 plan (03-05) can build on the audit seam unchanged; the `store/audit.reconcile` detection is available for a recovery path.

---
*Phase: 03-approval-gate-gated-commit-safety-spine*
*Completed: 2026-10-09*

## Self-Check: PASSED

- Created files exist: `src/triagedesk/store/audit.py`, `tests/test_audit_chain.py`.
- All 3 task commits are ancestors of HEAD: `519da53`, `4ebd873`, `1d1d9e7`.
