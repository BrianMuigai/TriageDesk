---
phase: "06"
slug: "durable-execution-idempotent-gate"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-12"
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| MCP client → owned tool | Untrusted tool arguments cross into `commit_priority`. | `colour`, `case` (`CaseInput`), `approval_token` |
| owned tool → store seam | The immutable case payload becomes the idempotency key of a persisted queue row. | case content hash (SHA-256) |
| tool arguments → SQL | `BorrowedStore` values cross into the borrowed SQLite `query` tool. | parameterised values |
| CLI args → resume decision | Untrusted `--approver`/`--role`/`--colour` cross into the graph's resumed value. | clinician identity + colour |
| `checkpoints.db` → process 2 | The on-disk file is untrusted input to the second process's deserialiser. | serialised LangGraph state |
| resume value → committed colour | The resumed decision drives the gated commit's `final_colour`. | approval decision |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Tampering | `store/queue.py` + `store/borrowed.py` idempotency key | high | mitigate | Key on `hash_value({case_id, **immutable CaseInput fields})` with `PRIMARY KEY (case_id, content_hash)`; `ON CONFLICT ... DO UPDATE` updates only `colour`/`target`, so a different case can never overwrite another case's row. Verified in `store/queue.py::content_hash`/`commit_to_queue` and `store/borrowed.py::upsert_queue_row`. | closed |
| T-06-02 | Tampering | `mcp/server.commit_priority` `case` parameter | medium | mitigate | `case` is a typed `CaseInput` validated by the ONE schema module (`core/schema.py`); no `**kwargs`, no dict passthrough into the key. Verified in `mcp/server.py::commit_priority`. | closed |
| T-06-03 | Repudiation | queue write vs audit record | high | mitigate | The refusal path stays before the store call and the `@audited` interceptor is unchanged, so every call still appends exactly one chained record; a supersede is still one audited call. Verified by `tests/test_graph_durable.py::test_restart_resumes_to_one_row_and_one_commit_audit` (per-tool audit counts all 1). | closed |
| T-06-04 | Tampering / Elevation | `graph/build.checkpointed_graph` deserialiser | high | mitigate | The `JsonPlusSerializer` allowlist is derived from `core.schema` (`_allowed_msgpack_modules`) and explicit; the plan adds no allowlist entry and never passes `True`. Verified in `graph/build.py`. | closed |
| T-06-05 | Spoofing | `durable.approval_decision` / `resume` CLI | high | mitigate | `--approver`/`--role` are required at runtime for `approve`/`edit` and rejected when **whitespace-only**; `ApprovalToken.approved_by`/`role` strip before validating; no fabricated default identity. Verified in `durable.py::approval_decision` and `core/schema.py::ApprovalToken`. | closed |
| T-06-06 | Tampering | resumed decision → `final_colour` | high | mitigate | The resume value is copied verbatim by `_build_token` (never invented) and validated by `ApprovalToken`; a `dismiss` is refused before the store is touched, via a well-formed token that reaches `commit_priority`'s own dismiss branch. Verified in `graph/nodes.py` and `mcp/server.py`. | closed |
| T-06-07 | Tampering | SQL reached through the durable commit path | medium | mitigate | The borrowed write stays parameterised (`values=[...]`); no case content is interpolated into SQL. Verified in `store/borrowed.py`. | closed |
| T-06-SC | Tampering | package installs | high | accept | No package is installed by this phase (no new dependency); no legitimacy gate is required. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-SC | Phase 6 installs no new package (no dependency added), so there is no supply-chain install surface to gate. | project owner | 2026-10-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-12 | 8 | 8 | 0 | gsd-secure-phase (ASVS L1, orchestrated) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-12

---

*Phase: 06-durable-execution-idempotent-gate*
*Verified: 2026-10-12 — 8 threats (7 mitigated, 1 accepted), 0 open*
