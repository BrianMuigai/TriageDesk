# Requirements: TriageDesk

**Defined:** 2026-10-10 (milestone **v1.1 Score Uplift**)
**Core Value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.

> Iron-clad engineering rule: **DRY + SOLID** (`docs/CONVENTIONS.md`) — every requirement below must be
> met without duplicating logic or violating the single-source-of-truth rule. v1.0 is frozen at tag
> `v1.0-submission`; every v1.1 change attaches at a published seam and must never edit the scorer, the
> citation helper, or the audit interceptor (`docs/DECISIONS.md` D-18).

---

## v1.1 Requirements

### Durable Execution

- [ ] **AGENT-01**: The demo and CLI run through the durable `checkpointed_graph` (SQLite `checkpoints.db`), a case paused at the approval gate resumes after a process restart on a stable `thread_id`, and an **edit** decision supersedes rather than duplicates the queue row (idempotency key covers the immutable case content, not `colour` alone).

### Confidence & Abstention

- [ ] **AGENT-02**: The system computes a deterministic **coverage/deferral** signal (never a model probability and never a percentage shown as clinical risk), an `assess_confidence` tool exposes it, and low confidence **routes to escalate or request-missing-info and never to `commit`** — it can only make the system more cautious, never downgrade a scored colour.

### Retrieval Grounding

- [ ] **AGENT-03**: A `retrieve_evidence` tool and a `ground` node placed **after** `score` fetch attributed SATS KB excerpts (derived from `data/*.yaml`, not re-authored); retrieval returns **only** closed-set discriminator ids, a rank, and an explicit `no_match`, so it can never set a colour or emit an uncited rule; the declared failure E-09 is addressed by real retrieval (or reported as a clean defer), never by adding a literal alias.

### Observability

- [ ] **AGENT-04**: Tool, node, and model spans are emitted from the **existing** audit interceptor and wrappers to a **local** exporter (no cloud/egress), a `trace_id` links spans to the audit record, and **replay is read-only** — it reconstructs from the checkpoint + audit/span stream and structurally cannot re-run the gated commit.

### Desk UX & Gate

- [ ] **UX-01**: A loud "no discriminator matched / low confidence — nurse to confirm" banner is shown, backed by a typed uncertainty field that drives routing, so the E-09 class becomes a visible flag rather than a buried JSON key.
- [ ] **UX-02**: A human-readable priority card renders the **suggested** colour, target time, and the "why" vitals next to adjacent citations — framed as a suggestion, never a verdict, and never a diagnosis.
- [ ] **UX-03**: The approval gate is a real **approve / edit / dismiss** interaction that records a named approver and commits no artefact on dismiss or on timeout (no default approve) — the human decision is no longer a hardcoded value.
- [ ] **UX-04**: A minimal vitals-entry surface (validating through the one shared schema) plus a one-screen desk quickstart give a first desk-facing interaction without coupling to graph internals.

### Borrowed MCP

- [ ] **MCP-01**: The borrowed SQLite MCP server is exercised beyond `query` — its read paths (`list_tables`, schema, `read_records`, `db_info`) are used behind the unchanged `Store` protocol, and the borrowed server stays **read-only in the agent path** with a tool allowlist and statement guard.

### Evaluation

- [ ] **EVAL-06**: The two fixable measured failures (E-04 emergency discriminator; E-07 deterioration recheck) reach their expected outcomes, the 14-case suite is re-run over the real graph, and `EVALS.md` is regenerated **only** from `report.json` (no hand-edited numbers).

### Review & Demo

- [ ] **REV-01**: The live technical review is rehearsed end-to-end: a 10-minute walkthrough plus a dry-run "add a discriminator to `data/sats_discriminators.yaml` live, reload, and re-score" that passes the safety suite.
- [ ] **DEMO-02**: The demo runs to 2–3 minutes with narration and the measured eval run on screen, still unedited and still showing a failure.
- [ ] **FIT-01**: A single triage nurse or clinician review is obtained and quoted in README/EVALS if access can be arranged; if not, the gap is re-declared honestly rather than over-claimed.

### Docs & Rigour

- [ ] **DOCS-04**: A stranger gets running in **one command** — `uv run triagedesk demo` is the literal one-liner (uv auto-syncs); no separate install step is required.
- [ ] **DOCS-05**: `EVALS.md` case and run counts are reconciled (no 14-vs-16 / 29-vs-32 drift) and every number is emitted from `report.json`.
- [ ] **DOCS-06**: At milestone end, every submission document (README, ARCHITECTURE, EVALS, DESCRIPTION, STATUS, `docs/REQUIREMENTS`, `docs/ROADMAP`) is refreshed to reflect the v1.1 capabilities and current measured results, with no stale v1.0 claims.

## Future Requirements

Deferred to a later milestone. Tracked but not in the v1.1 roadmap.

- **AGENT-05**: Model routing / caching / budgets to attack the 14–17 s desk latency.
- **AGENT-06**: Online eval, calibration, and drift monitoring.
- **MCP-02**: A second borrowed (vector) MCP server for retrieval.
- **UX-05**: Multimodal intake (voice + chart/cuff photo) — the real desk UX.
- **CAL-02**: Full calibration report (Brier score / reliability curves) at larger sample size.
- **PAED-01**: Paediatric SATS age-banded charts.
- **LANG-01**: Multilingual clinical lexicon.
- **DISC-01**: Mandatory clarifying-question loop when no discriminator matches.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Generative RAG that writes clinical guidance prose | Hallucination risk; the agent must never diagnose or advise |
| A pseudo-probability shown as clinical risk ("87% sure this is ORANGE") | Miscalibrated and over-trust-inducing; confidence is a deferral signal only |
| Auto-commit on gate timeout, or a default-approve | Defeats the human approval boundary (challenge disqualifier) |
| Replay that re-runs the model or the gated commit | Would create a second, un-audited queue write |
| Cloud tracing (LangSmith egress) or any network call in the agent path | Data residency; the agent path stays offline |
| Editing code (or `docs/SATS.md`) to add a rule | Rules are data (`data/*.yaml`) — the single source of truth |
| Adding a literal discriminator alias to make E-09 pass | Would tune the test green and hide a real coverage gap |
| Vector platform / heavy embedding stack (chromadb, faiss, torch, sentence-transformers) | Does not fit the CPU-only, offline, low-RAM budget |

## Traceability

Which phases cover which requirements (filled by the roadmap).

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGENT-01 | Phase 6 | Pending |
| AGENT-02 | Phase 8 | Pending |
| AGENT-03 | Phase 9 | Pending |
| AGENT-04 | Phase 7 | Pending |
| UX-01 | Phase 10 | Pending |
| UX-02 | Phase 10 | Pending |
| UX-03 | Phase 10 | Pending |
| UX-04 | Phase 10 | Pending |
| MCP-01 | Phase 9 | Pending |
| EVAL-06 | Phase 11 | Pending |
| REV-01 | Phase 12 | Pending |
| DEMO-02 | Phase 12 | Pending |
| FIT-01 | Phase 12 | Pending |
| DOCS-04 | Phase 11 | Pending |
| DOCS-05 | Phase 11 | Pending |
| DOCS-06 | Phase 12 | Pending |

**Coverage:**

- v1.1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

**By phase:**

- Phase 6 (Durable Execution & Idempotent Gate): AGENT-01
- Phase 7 (Local Observability — Span Tracing & Read-Only Replay): AGENT-04
- Phase 8 (Calibrated Confidence & Abstention): AGENT-02
- Phase 9 (Retrieval Grounding & Borrowed-MCP Depth): AGENT-03, MCP-01
- Phase 10 (Desk UX & Real Approval Gate): UX-01, UX-02, UX-03, UX-04
- Phase 11 (Honest Evaluation Re-run & Rigour Docs): EVAL-06, DOCS-04, DOCS-05
- Phase 12 (Live Review, Demo & Milestone-Close Documentation): REV-01, DEMO-02, FIT-01, DOCS-06

---
*Requirements defined: 2026-10-10*
*Last updated: 2026-10-10 — milestone v1.1 requirements mapped to Phases 6–12 (roadmap created)*
