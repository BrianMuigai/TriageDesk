---
phase: "08"
slug: "calibrated-confidence-abstention"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-13"
---

# Phase 8 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| graph node → owned MCP tool | The `assess` node hands typed state across the tool boundary; the tool must stay pure and contract-typed. | matched ids, `no_match`, `PriorityResult` |
| owned server → audit interceptor | Every owned tool call routes through the ONE `@audited` interceptor. | tool inputs/outputs |
| claim → reader | "confidence" must never be readable as a clinical probability. | deferral decision + component facts |
| measured run → `report.json` | The report seals non-volatile content with a recomputing digest. | per-case facts + digest |
| `report.json` → `EVALS.md` | `EVALS.md` is a projection; every figure crosses through the generator only. | published numbers |
| deferral → published result | A coverage deferral must be visible, never a delivered pass or a hidden failure. | deferral facts |
| graph channel → report | The runner reads the graph's own `confidence` channel. | the signal |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-08-01 | Tampering | `core/schema.py::ConfidenceResult` | high | mitigate | The contract has no float/`score`/`probability`/`percent` field, so a model-derived number is unrepresentable rather than discouraged; `tests/test_confidence.py` rejects one (D8-02/D8-04). | closed |
| T-08-02 | Elevation | `assess` routing | high | mitigate | `route_after_assess` reaches only `escalate`/`request_missing_info`, both of which end at `END` with no edge to `commit`; `tests/test_graph_confidence.py` proves a deferral writes no row and calls no commit (D8-12). | closed |
| T-08-03 | Tampering | `core/confidence.py` | medium | mitigate | The override component reads `rule.rule_id ∈ get_discriminators().categories` and the band distance reads `get_tews().tews_to_colour` — it never produces a colour, so a second colour producer cannot appear. | closed |
| T-08-04 | Information disclosure | `core/confidence.py`, `graph/*.py` | high | mitigate | The new core module is auto-covered by `tests/test_purity.py` (no `llm`/`mcp`/`store`/`fastmcp`/`langchain`); the graph AST guards assert no `os.environ`/`getenv`/network client in `graph/`. | closed |
| T-08-05 | Tampering | `HandoverCard` | medium | mitigate | The signal goes to a NEW state channel; `HandoverCard`'s exact field set is untouched (Phase 10 owns rendering). | closed |
| T-08-06 | Tampering | `EVALS.md` / `evals/results/report.json` | high | mitigate | Both are regenerated only by the shipped pipeline; `emit_evals.validate_report` refuses a report whose digest does not recompute and `tests/test_docs_final.py` runs `--check`. The `_digest_payload` extension shipped in the same change as the regeneration. | closed |
| T-08-07 | Tampering | `evals/runner.py::_build_gate` | high | mitigate | The deferral exclusion applies ONLY when every run deferred; a wrong colour (any `False`/`None` deferral) is never excluded — pinned by a focused gate test. Moved cases are surfaced in `Analysis.deferral_cases`/`deferral_rate`, so a moved case cannot be quietly excused. | closed |
| T-08-08 | Repudiation | `Analysis.calibration` | medium | mitigate | ECE is confined to `evals/` (never in `core/schema.py` or the tool output), reported with `n` named and an explicit small-sample caveat; never presented as a validated calibrated probability (D8-15). | closed |
| T-08-09 | Tampering | `EVALS.md` / `report.json` (per-case facts) | high | mitigate | `_digest_payload` seals every per-case fact the published figures derive from — `held_out`, `confidence_levels`, `deferrals` and now `confidence_satisfied` — so tampering with any of them changes the digest and is refused by `validate_report` (fixed in `7a2974b`, pinned by a digest-mutation test). | closed |
| T-08-10 | Repudiation | `scripts/emit_evals.py` §4 result cell | medium | mitigate | An all-deferred case renders a deferral marker derived from `ReportCase.deferrals` (never a bare pass or an unexplained failure), pinned by a generator test. | closed |
| T-08-11 | Repudiation | `Analysis.calibration` | medium | mitigate | ECE is published with the sample sizes named and an explicit small-sample caveat; never presented as a validated calibrated probability (D8-15). | closed |
| T-08-SC | Tampering | npm/pip/cargo installs | high | accept | This phase adds no dependency of any kind; no package-legitimacy checkpoint is required. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-08-01 | T-08-SC | Phase 8 installs no new package (no dependency added), so there is no supply-chain install surface to gate. | project owner | 2026-10-13 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-13 | 12 | 12 | 0 | gsd-secure-phase (ASVS L1, orchestrated) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-13

---

*Phase: 08-calibrated-confidence-abstention*
*Verified: 2026-10-13 — 12 threats (11 mitigated, 1 accepted), 0 open*
