# Roadmap: TriageDesk

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-10-10) — archived at `.planning/milestones/v1.0-ROADMAP.md`
- ✅ **v1.1 Score Uplift** — Phases 6–12 (shipped 2026-10-13) — archived at `.planning/milestones/v1.1-ROADMAP.md`

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-10-10</summary>

Archived at `.planning/milestones/v1.0-ROADMAP.md` (requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`).

- [x] **Phase 1: SATS Foundations & Risk Retirement** - Rule substrate, typed schema, scaffold; retire the model and MCP unknowns on evidence
- [x] **Phase 2: Deterministic Scorer & Own MCP Server** - Pure cited scorer + the five contracted owned tools
- [x] **Phase 3: Approval Gate, Gated Commit & Safety Spine** - The gate that refuses to commit without a named approver, plus audit and borrowed persistence
- [x] **Phase 4: Evaluation, Recovery & Honest Failure** - Enforcing 14-case × 3-run evaluation with one declared failure
- [x] **Phase 5: Demo, Docs & Freeze** - One-command run, live demo video, docs finalised, repo frozen

</details>

<details>
<summary>✅ v1.1 Score Uplift (Phases 6–12) — SHIPPED 2026-10-13</summary>

Archived at `.planning/milestones/v1.1-ROADMAP.md` (requirements: `.planning/milestones/v1.1-REQUIREMENTS.md`;
audit: `.planning/milestones/v1.1-MILESTONE-AUDIT.md`). 7 phases, 19 plans, 42 tasks.

- [x] **Phase 6: Durable Execution & Idempotent Gate** (2/2 plans) — completed 2026-10-12
- [x] **Phase 7: Local Observability — Span Tracing & Read-Only Replay** (2/2 plans) — completed 2026-10-12
- [x] **Phase 8: Calibrated Confidence & Abstention** (3/3 plans) — completed 2026-10-13
- [x] **Phase 9: Retrieval Grounding & Borrowed-MCP Depth** (3/3 plans) — completed 2026-10-13
- [x] **Phase 10: Desk UX & Real Approval Gate** (3/3 plans) — completed 2026-10-13
- [x] **Phase 11: Honest Evaluation Re-run & Rigour Docs** (3/3 plans) — completed 2026-10-13
- [x] **Phase 12: Live Review, Demo & Milestone-Close Documentation** (3/3 plans) — completed 2026-10-13

</details>

### Phase 13: Desk Fit — queue-shaped, model-real surface: (1) non-blocking async extraction and a persistent desk event loop; (2) online free-text extraction with precompute during vitals entry; (3) acuity-ordered waiting-room panel and keyboard-first vitals entry

**Goal:** An OPD triage nurse can enter vitals at the desk while the local model works in the background, and read the whole waiting room in acuity order — with no new path to the queue and no uncited colour.
**Requirements**: JC-1, JC-3
**Depends on:** Phase 12
**Plans:** 3/3 plans complete

Plans:

- [x] 13-01-PLAN.md — Non-blocking async extraction and one persistent desk event loop
- [x] 13-02-PLAN.md — Online free-text extraction with background precompute during vitals entry
- [x] 13-03-PLAN.md — Acuity-ordered waiting room and keyboard-first vitals entry

### Phase 14: Evidence Fidelity — ground every extracted sign in the complaint text (E-13 injection), carry the committed target through an edit, and correct the stale verify-retry prose in ARCHITECTURE.md and docs/REQUIREMENTS.md

**Goal:** Every extracted sign is grounded in the note it came from, the committed target travels with the committed colour through an edit, and the architecture docs describe the shipped fail-closed verify — with the measured eval status left unchanged.
**Requirements**: JC-1, JC-4, JC-5
**Depends on:** Phase 13
**Plans:** 3/3 plans complete

Plans:

- [x] 14-01-PLAN.md — Ground every extracted discriminator and vital in the complaint text (E-13 unit regression)
- [x] 14-02-PLAN.md — Carry the committed target through an edit so the card and queue row agree
- [x] 14-03-PLAN.md — Correct the stale verify-retry prose and state the E-13 position honestly
