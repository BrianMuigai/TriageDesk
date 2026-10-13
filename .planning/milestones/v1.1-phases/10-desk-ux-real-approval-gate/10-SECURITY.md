---
phase: "10"
slug: "desk-ux-real-approval-gate"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-13"
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser → local bridge | An untrusted HTTP client (the nurse's browser, or a hostile page in it) talks to the surface. | form fields, decisions |
| rendered string → HTML | Graph-owned and nurse-entered text is interpolated into markup. | complaint, citations, approver, colour |
| bridge → graph | The surface drives the existing pause/resume plumbing. | a `CaseInput`, a decision |
| bridge → network | The surface must not egress. | none |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-10-01 | Tampering | `desk/server.py` rendered strings | high | mitigate | `html.escape` on every rendered string (complaint, approver, role, citations, colour class) — pinned by an escaping test. | closed |
| T-10-02 | Elevation of privilege | the `desk/` package | high | mitigate | No commit path exists in the bridge: the package imports neither `store.queue` nor `mcp.server`; every decision flows through `durable`. Proven structurally (a recursive AST/import scan with relative-import resolution) plus a row-delta. | closed |
| T-10-03 | Information disclosure | bind address, asset serving, outbound requests | high | mitigate | Loopback is enforced in `DeskServer.__init__` (a non-loopback host is refused unless explicitly opted in); the asset route is an allowlist (traversal 404s, no source leak); no CDN/`@import`/external URL; `harden_offline()` runs before the handler import. | closed |
| T-10-04 | Spoofing | `desk/server.py` `decide` | high | mitigate | The decision is built by the ONE `durable.approval_decision` — a whitespace-only approver/role is refused; a fabricated identity is surfaced by the gate. | closed |
| T-10-05 | Elevation of privilege | the timeout path | high | mitigate | Timeout is "no decision POST arrives": the bridge holds no server-side default and never resumes on its own. A timeout adds zero rows — proven by a row delta. | closed |
| T-10-06 | Tampering | the edit colour control | high | mitigate | The control is built from `{band.colour for band in get_tews().tews_to_colour}` — exactly the set `ApprovalToken` validates — so the surface cannot offer a decision the gate would refuse (D10-18). | closed |
| T-10-07 | Spoofing | the banner trigger and its body | high | mitigate | The trigger reads the typed facts (`no_match` / `confidence.deferral`); the body is trigger-conditional, so the banner never asserts a fact its trigger did not establish. | closed |
| T-10-08 | Repudiation | the deferred / escalated / recovery terminal | medium | mitigate | The terminal kind is read from the typed `confidence`/`escalation`/`recovery` channels; the deferred path renders a read-only card with NO gate (D10-17). | closed |
| T-10-09 | Information disclosure | rendered clinical copy | medium | mitigate | The card renders only graph-owned fields; the prohibited-token set (`HandoverCard.FORBIDDEN_FIELD_TOKENS`) is scanned and no percentage/probability appears. | closed |
| T-10-10 | Repudiation | `docs/DESK.md` quickstart | medium | mitigate | The guard test drives the shipped public `cli.main` over every `desk` invocation in the doc, so the quickstart cannot drift from the CLI. | closed |
| T-10-11 | Tampering | `docs/DECISIONS.md` | low | mitigate | Exactly one D23 row is asserted present (a duplicate id or a missing row fails). | closed |
| T-10-12 | Tampering | the unauthenticated local surface (review-discovered) | high | mitigate | The code review found the surface CSRF-reachable — a drive-by page could `POST /case` then `POST /decision` with a fabricated identity and commit a row. Fixed with a per-server `secrets` CSRF token required on every POST (compared as UTF-8 bytes, constant-time) plus an `Origin`/`Host` same-origin check. A fabricated decision commits zero rows. | closed |
| T-10-13 | Spoofing | the `Origin` check's trust in `Host` (review-discovered) | high | mitigate | The review then found the `Origin` check trusted the attacker-controlled `Host`, so a DNS-rebinding page could post with a matching foreign `Host`+`Origin` and commit. Fixed by pinning `Host` to a loopback allowlist before anything else. 11 adversarial vectors were probed; every refusal wrote zero rows and rendered the failure panel. | closed |
| T-10-SC | Tampering | npm/pip/cargo installs | high | mitigate | This phase installs ZERO packages (D10-16). The standing package-legitimacy gate remains in force — any `uv add` in this phase is a defect. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| *(none)* | | No accepted risks — every threat is mitigated and closed. | — | — |

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

*Phase: 10-desk-ux-real-approval-gate*
*Verified: 2026-10-13 — 14 threats (14 mitigated, 0 accepted), 0 open*
