---
phase: "11"
slug: "honest-evaluation-re-run-rigour-docs"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-13"
---

# Phase 11 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| fixture → deterministic consumers | The case fixture's note and golden case must agree, or the deterministic path and the real path diverge. | a complaint note, structured vitals |
| model → structured case | The extraction contract shapes what the model emits. | `ExtractionResult` / `CaseInput` JSON schema |
| report → published doc | Every published figure crosses through the generator only. | the measured numbers |
| run → provenance | The report must name what actually reproduces it. | commit sha, schema hash, digest |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-11-01 | Tampering | an expectation/golden value | high | mitigate | The ONLY fixture change is the D11-14 E-07 note repair; its `expected: RECHECK` is byte-identical (a diff check is pinned). No alias, no threshold move. | closed |
| T-11-02 | Repudiation | the E-04 fix's generality | high | mitigate | The `age_years` description is general clinical guidance — no fixture number, case id, colour or discriminator; the guard asserts the described serial set EQUALS the substrate's scored set (not a hand-listed fixture set). | closed |
| T-11-03 | Tampering | the provenance record | high | mitigate | A non-clean tree is marked `-dirty`; `EVALS.md` §8 names the sealed `extraction_schema_hash` as what reproduces the run (not the bare commit). The schema hash is covered by `report_digest`, so mutating it moves the digest. | closed |
| T-11-04 | Tampering | `evals/results/report.json` | high | mitigate | Regenerated only by the shipped pipeline; `validate_report` refuses a digest that does not recompute and `--check` exits non-zero on drift. | closed |
| T-11-05 | Repudiation | `EVALS.md` | high | mitigate | `EVALS.md` is the exact generator projection (`--check` exits 0); no figure is hand-typed; the §4 row set reconciles with the report's case set fail-closed in BOTH directions. | closed |
| T-11-06 | Repudiation | a stale published count | medium | mitigate | The §4 row-id set must EQUAL the report's case-id set (a stale or missing row fails `--check`); the count drift is closed and pinned by tests. | closed |
| T-11-07 | Repudiation | a hidden honest miss | high | mitigate | The declared failure E-09 stays visible (a `⏸` marker, `declared_failure: true`) and every unexpected failure (E-11, E-13) renders `❌` and is named in the generated §6.1 record; the deferral-aware gate never excludes a wrong colour. | closed |
| T-11-08 | Tampering | the extraction contract (a fixture-specific hack) | medium | mitigate | The description set is derived from the substrate's scored parameters, so no single fixture can shape it; the derived-vs-scored equality guard is non-vacuous. | closed |
| T-11-09 | Elevation of privilege | the README's unguarded claim | medium | mitigate | A CLI-driving drift guard extracts every `uv run triagedesk …` invocation from the README and drives each through the public `cli.main`; the doc guard forbids the stale two-step install. | closed |
| T-11-10 | Tampering | `docs/DEMO.md` currency claim | low | mitigate | The demo doc's output blocks are known to drift since Phases 8/9/10; the claim was softened, a dated drift note added, and the full refresh deferred to Phase 12 (DOCS-06) with a recorded reason — no wrong output is presented as right. | closed |
| T-11-11 | Information disclosure | the report's provenance | low | mitigate | The provenance carries only a commit sha, a schema hash and digests — no clinical text, no paths beyond the repo. | closed |
| T-11-SC | Tampering | npm/pip/cargo installs | high | mitigate | This phase installs ZERO packages. The standing package-legitimacy gate remains in force. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-11-01 | T-11-10 | `docs/DEMO.md`'s recorded CLI output is known to drift; a faithful refresh needs a demo re-run and belongs to Phase 12's DOCS-06 submission-doc refresh. A dated drift note + a softened claim keep a reader from being misled in the meantime. | project owner | 2026-10-13 |

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

*Phase: 11-honest-evaluation-re-run-rigour-docs*
*Verified: 2026-10-13 — 12 threats (11 mitigated, 1 accepted), 0 open*
