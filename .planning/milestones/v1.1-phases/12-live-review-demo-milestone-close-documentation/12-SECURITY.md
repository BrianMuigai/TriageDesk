---
phase: "12"
slug: "live-review-demo-milestone-close-documentation"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-13"
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| data edit → running system | A live YAML edit must extend behaviour without touching code. | discriminator data |
| report → published doc | Every published figure crosses through the generator only. | measured numbers |
| claim → reader | A status claim (review, demo, clinician) must match reality. | status prose |
| doc → guard | A documented command must be the shipped one. | CLI invocations |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-12-01 | Tampering | the data-only extension claim | high | mitigate | A hermetic harness adds a discriminator to a tmp substrate, clears the loader cache, and shows a before→after re-score through the shipped matcher/scorer; `git status --porcelain -- src/` must be empty (the alias is absent from every fixture). | closed |
| T-12-02 | Repudiation | the live-review runbook | high | mitigate | Every documented invocation is driven through the public `cli.main`; a multi-command beat is proven RUNNABLE (a compose assertion on a shared `--db` plus a real pause→resume over a tmp checkpoint). | closed |
| T-12-03 | Spoofing | the demo status claim | high | mitigate | The recording/public upload is FLAGGED `human_needed`, never claimed; `docs/DEMO.md` documents only what the shipped CLI prints. | closed |
| T-12-04 | Repudiation | the clinical-fit claim | high | mitigate | The gap is re-declared honestly (no clinician review obtained); README/`EVALS.md` §7 carry a marked, attributed, EMPTY slot — nothing invented. | closed |
| T-12-05 | Tampering | `EVALS.md` | high | mitigate | It remains ONLY the `emit_evals.py` projection of `report.json` (`--check` exits 0); §7's narrative was edited, no generated cell. | closed |
| T-12-06 | Repudiation | a stale figure published as current | medium | mitigate | Every submission doc was swept; a hard test count was dropped in favour of the suite; the model name, tool count, case/run counts and outcomes were reconciled across all docs. | closed |
| T-12-07 | Tampering | `ARCHITECTURE.md`'s word budget | low | mitigate | The refresh was word-neutral (694/700 words, 93/110 lines); the one-page guard stays green. | closed |
| T-12-08 | Elevation of privilege | a doc guard weakened to pass | high | mitigate | No guard file was weakened; the data-only harness's `src/` assertion checks the `git` returncode and diffs before/after (non-vacuous). | closed |
| T-12-09 | Repudiation | the demo doc's output blocks | medium | mitigate | The Phase-11 drift is closed: the blocks were re-transcribed from a real run (routine/deterioration defer with no `commit`; escalation commits at queue position 1; seven tools). | closed |
| T-12-10 | Tampering | a permanent `data/*.yaml` change | medium | mitigate | The extension is temporary and reverted; `data/*.yaml` is byte-unchanged at rest. | closed |
| T-12-11 | Information disclosure | the published provenance/model name | low | mitigate | The docs name the shipped/measured model (`qwen2.5:1.5b`), reconciled with `NOTICE` and the report's `model_tag`; no clinical text is published. | closed |
| T-12-12 | Repudiation | the model-name disclosure | medium | mitigate | `docs/DECISIONS.md` D3, the DQ-8 table, `docs/PROJECT.md` and the code comments now agree on the default vs the alternative model. | closed |
| T-12-13 | Tampering | the milestone-close decision record | low | mitigate | D25 records the four close-out choices and LINKS the artefacts rather than restating them. | closed |
| T-12-SC | Tampering | npm/pip/cargo installs | high | mitigate | This phase installs ZERO packages. The standing package-legitimacy gate remains in force. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-12-01 | T-12-03 | The demo video is recorded but the public upload is a human step outside the repository; it is flagged as the one submission blocker rather than claimed as done. | project owner | 2026-10-13 |
| AR-12-02 | T-12-04 | No triage nurse/clinician review was obtained; the gap is re-declared honestly with an empty attributed slot, which is the sanctioned alternative to over-claiming. | project owner | 2026-10-13 |

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

*Phase: 12-live-review-demo-milestone-close-documentation*
*Verified: 2026-10-13 — 14 threats (12 mitigated, 2 accepted), 0 open*
