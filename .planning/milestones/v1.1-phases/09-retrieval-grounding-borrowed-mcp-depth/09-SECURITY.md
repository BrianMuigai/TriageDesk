---
phase: "09"
slug: "retrieval-grounding-borrowed-mcp-depth"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-13"
---

# Phase 9 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| complaint text → retrieval | Untrusted clinical text is tokenised for matching; it must never be interpreted as instructions or a colour. | complaint tokens |
| retrieval → graph state | Evidence is advisory display; it must not reach a decision channel. | attributed passages |
| agent path → borrowed SQLite server | The borrowed server must stay read-only on the agent path. | read statements only |
| `data/*.yaml` → retrieval | The corpus is the machine authority; nothing may be re-authored. | discriminator ids/labels |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-09-01 | Spoofing | `core/retrieval.retrieve` / `EvidencePassage` | high | mitigate | Passages are built FROM `get_discriminators().discriminators`, so an id outside the closed set is unconstructible; `tests/test_retrieval.py` asserts membership against the loader-derived set. | closed |
| T-09-02 | Tampering | `retrieve_evidence` input handling | high | mitigate | The complaint is only lower-cased and tokenised — never executed, never interpreted as instructions, never parsed for a colour; a token in no alias produces `no_match` (proven on the E-09 fixture). | closed |
| T-09-03 | Information disclosure | `EvidencePassage.citation` | low | mitigate | The citation is built by `core.citations.format_citation` from the data `citation_ref` + substrate citation only; complaint text can never reach it. | closed |
| T-09-04 | Tampering | retrieval determinism | medium | mitigate | Integer scoring with an explicit `(-score, discriminator_id)` tie-break, so a repeat call is identical; retrieval writes no `matched_ids`, so matched-set stability cannot flap. | closed |
| T-09-05 | Elevation of privilege | owned-tool surface / `assert_tool_allowlist` | high | mitigate | The allowlist is set-equality at four sites with explicit MISSING and UNEXPECTED sub-case tests; a drifted surface raises at composition and at discovery. | closed |
| T-09-10 | Tampering | `ground` node return value | high | mitigate | The node returns exactly one key (`evidence`); the isolation proof asserts `priority`, its citations, `matched_ids` and `no_match` are equal across a run with and without retrieval, and each run's priority equals a direct scorer call. | closed |
| T-09-11 | Tampering | graph routing | high | mitigate | `ground` is wired by plain edges only; no router reads the new channel (edge-set assertions + a source scan of all four route functions), and no edge from `ground` reaches `commit`. | closed |
| T-09-12 | Repudiation | `retrieve_evidence` audit trail | medium | mitigate | The tool joins the ONE `@audited()` interceptor, so exactly one chained record is appended per call and its tool span is emitted by the same seam — the node carries no audit code. | closed |
| T-09-20 | Tampering | `BorrowedStore._call` statement path | high | mitigate | The fail-closed classifier refuses any statement whose leading keyword is not a read; the refusal raises before `self._tools` is dereferenced, and the proof asserts the fake's call log stayed clean. | closed |
| T-09-21 | Elevation of privilege | borrowed tool surface | high | mitigate | `READ_TOOLS` is an allowlist; the three mutating record tools are unnameable by any caller, and the only mutation route is the gated commit's parameterised `query` writes (`write=True`). | closed |
| T-09-22 | Denial of service | `ensure_schema` read-path probe | medium | mitigate | Every probe is individually wrapped and records a degradation string; a shape mismatch or a missing tool can never raise out of the store-open path used by demo/eval/resume/commit. | closed |
| T-09-23 | Tampering | SQL construction in the adapter | medium | mitigate | Values remain parameterised (`values=[...]`), never interpolated; the classifier is a second, independent barrier rather than the only one. | closed |
| T-09-24 | Tampering | borrowed statement classifier (review-discovered) | high | mitigate | The code review found the classifier was not fail-closed: `WITH`-prefixed DML, write-`PRAGMA`, multi-statement strings, and (after the first fix) `EXPLAIN PRAGMA writable_schema=1` were admitted. Fixed by refusing a `WITH` head, admitting only the read-only `PRAGMA` subset at a name boundary, refusing any non-trailing `;`, refusing `load_extension`, and dropping `EXPLAIN` from the admitted prefixes. Re-verified over 33 adversarial vectors; no real caller is broken. | closed |
| T-09-SC | Tampering | npm/pip/cargo installs | high | mitigate | This phase installs ZERO packages; `BORROWED_SERVER_PACKAGE` stays pinned at the reviewed `mcp-sqlite@1.0.9`. The standing package-legitimacy gate remains in force — any `uv add` in this phase is a defect. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| *(none)* | | No accepted risks in this phase — every threat is mitigated and closed. | — | — |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-13 | 14 | 14 | 0 | gsd-secure-phase (ASVS L1, orchestrated) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-13

---

*Phase: 09-retrieval-grounding-borrowed-mcp-depth*
*Verified: 2026-10-13 — 14 threats (14 mitigated, 0 accepted), 0 open*
