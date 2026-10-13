---
phase: "07"
slug: "local-observability-span-tracing-read-only-replay"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-12"
---

# Phase 7 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| complaint note → node/model span | Untrusted clinical text is in scope at the model boundary; it must not enter the sink. | complaint text (never emitted) |
| process env → transitive tracer | `LANGSMITH_*` / `LANGCHAIN_TRACING*` decide whether LangChain egresses. | env vars |
| audit record → borrowed SQL | The record shape and the SQL column list are separate sources of truth. | `trace_id` + record fields |
| `checkpoints.db` → replay process | The on-disk file is untrusted input to the deserialiser. | serialised LangGraph state |
| replay → queue/audit store | Replay must be a pure read; it must never reach a write. | none written |
| stored audit/span stream → rendered view | A tampered stream must not mislead the reviewer into a false outcome. | audit + span records |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-07-01 | Information Disclosure | transitive LangSmith/OTLP tracer (`observability/offline.py`) | high | mitigate | `harden_offline()` pops the four tracing env vars AND calls `langsmith.utils.get_env_var.cache_clear()`, then asserts `tracing_is_enabled() is False`; `main()` runs it first so no import can prime a tracer; OTLP is inert (no SDK installed). Verified in `observability/offline.py` + `cli.py` and by `tests/test_observability.py`. | closed |
| T-07-02 | Information Disclosure | span sink (`observability/spans.py` emit sites) | high | mitigate | Span attributes are minimal (ids, kind, timings, colour/rule ids, token counts); the model span carries the model tag + `(prompt_eval_count, eval_count)` only — never the note/prompt/completion (D7-08). Verified by `test_model_span_carries_no_prompt_text`. | closed |
| T-07-03 | Tampering / Repudiation | `AuditRecord.trace_id` | medium | mitigate | `trace_id` is content-derived (`case_id_for_note`) and sealed inside `record_digest` when non-empty, so a forged id breaks the chain digest rather than silently mis-joining a record to spans. Legacy (empty-`trace_id`) rows still verify. | closed |
| T-07-04 | Elevation | `graph/*.py` env/credential read | high | mitigate | All env logic stays in `observability/offline.py` (outside `graph/`); the safety-spine AST guard (`tests/test_safety_spine.py::test_graph_reads_no_credentials`) stays green and `grep -rn "os.environ\|getenv" src/triagedesk/graph/` returns nothing. | closed |
| T-07-05 | Tampering / Repudiation | replay re-executing the gated commit | high | mitigate | `replay.py` builds NO tool mapping and compiles NO graph, so `commit_priority` is structurally unreachable (`grep -cE "build_graph\|checkpointed_graph\|load_graph_tools"` == 0); the zero-write test proves zero queue rows and zero `commit_priority` records after replay. | closed |
| T-07-06 | Tampering / Elevation | `AsyncSqliteSaver` deserialiser over a tampered `checkpoints.db` | high | mitigate | The saver's serde is `JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())` — the ONE schema-derived allowlist, never `True`. | closed |
| T-07-07 | Repudiation | replay becoming a second, unaudited write path | medium | mitigate | Replay calls only read-only store methods (`read_audit_records`, `read_queue_rows`); no append/upsert/commit appears in `replay.py`, and an absent thread resolves no store at all. | closed |
| T-07-SC | Tampering | npm/pip/cargo installs | high | accept | This phase installs no package (no new dependency); no legitimacy gate is required. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Declared scope of the read-only property (WR-01, honest wording)

Replay is read-only **at the row level**: it adds zero queue rows and zero commits, and its audit chain
still verifies. Opening the checkpoint and the domain store necessarily runs the SQLite WAL pragma and the
store's idempotent schema-ensure (DDL / guarded `ALTER TABLE`); those create or migrate *files*, not rows.
The ROADMAP criterion (no queue row, no commit) is met and asserted.

The `contextvars` trace binding does not cross the stdio-subprocess boundary, so an owned-MCP-subprocess
run records `trace_id=""`; the in-process paths (demo, eval, resume, replay) carry the trace. Declared in
`SECURITY.md` §10 and `docs/DECISIONS.md` D19.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-SC | Phase 7 installs no new package (no dependency added), so there is no supply-chain install surface to gate. | project owner | 2026-10-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-12 | 9 | 9 | 0 | gsd-secure-phase (ASVS L1, orchestrated) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-12

---

*Phase: 07-local-observability-span-tracing-read-only-replay*
*Verified: 2026-10-12 — 9 threats (7 mitigated, 2 accepted), 0 open*
