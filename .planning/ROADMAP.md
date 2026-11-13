# Roadmap: TriageDesk

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-10-10) — archived at `.planning/milestones/v1.0-ROADMAP.md`
- ✅ **v1.1 Score Uplift** — Phases 6–12 (shipped 2026-10-13) — archived at `.planning/milestones/v1.1-ROADMAP.md`
- ✅ **v1.2 Coverage Recovery** — Phases 15–18 (shipped 2026-11-13)

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

<details>
<summary>✅ v1.2 Coverage Recovery (Phases 15–18) — SHIPPED 2026-11-13</summary>

**Milestone goal:** turn a 49% coverage deferral into honest coverage — deliver when the vitals are the
complete answer, clarify when one question would resolve a genuine ambiguity, and never guess a colour to
raise the number. The four safety invariants are unchanged; retrieval informs coverage, never a colour.

**Measured baseline (real mode, 16 cases × 3 runs, 2026-10-13 report):** colour 19/19 correct,
coverage deferrals 18/37 (48.6%), colour stability 15/16 (E-11), p95 latency 55.03 s.

</details>

### Phase 15: Deterministic coverage classification — matched / ambiguous / no-candidate, from the closed set plus data-driven context terms

**Goal:** The matcher stops conflating "no discriminator exists" with "retrieval failed": a pure classifier returns `matched`, `ambiguous` or `no_candidate`, and only an `ambiguous` complaint can hold a case back.
**Requirements**: COV-01, COV-04
**Depends on:** Phase 14
**Plans:** 2/2 plans complete

Plans:

- [x] 15-01-PLAN.md — Retrieval classifier: stopwords, conservative stems, context terms (data-only)
- [x] 15-02-PLAN.md — Matcher/MatchResult contract carries status + candidates; purity and boundary tests

### Phase 16: Three-way confidence and the bounded clarification terminal

**Goal:** A no-candidate case with complete vitals is delivered with a `vitals-only` provenance fact; an ambiguous case gets at most three targeted questions, no colour, no gate, no commit; one answer round is allowed before deferring.
**Requirements**: COV-02, COV-03, COV-07
**Depends on:** Phase 15
**Plans:** 3/3 plans complete

Plans:

- [x] 16-01-PLAN.md — `ConfidenceResult.action` + questions; `assess` uses retrieval status and priority
- [x] 16-02-PLAN.md — Graph `clarify` terminal and routing; clarification channel in state/outcome
- [x] 16-03-PLAN.md — Desk surfaces the questions and accepts one answer round; eval counts clarify separately

### Phase 17: Extraction completeness — recover every stated vital the model drops

**Goal:** A stated RR/HR/systolic BP/SpO2 is recovered deterministically after extraction, so a dropped vital cannot turn an urgent case into RECOVER; nothing unstated is ever imputed.
**Requirements**: COV-05, COV-06
**Depends on:** Phase 16
**Plans:** 2/2 plans complete

Plans:

- [x] 17-01-PLAN.md — Single-vital deterministic readers in the one grounding module
- [x] 17-02-PLAN.md — E-11 repeated-run regression (≥9 runs) and the missing-vital safety proof

### Phase 18: Eval expansion, honest measurement and docs

**Goal:** Measure the new coverage honestly on a larger, partly held-out set — ambiguous+chronic, contradictory/incomplete/noisy vitals — and publish delivered/clarified/deferred plus latency without hand-typed numbers.
**Requirements**: COV-08, COV-09, COV-10
**Depends on:** Phase 17
**Plans:** 3/3 plans complete

Plans:

- [x] 18-01-PLAN.md — New synthetic cases: ambiguous+chronic, contradictory, incomplete, noisy, held-out
- [x] 18-02-PLAN.md — Analysis/gate/report: coverage vs clarification vs deferral, ECE and risk–coverage re-derived
- [x] 18-03-PLAN.md — Regenerate EVALS.md and sweep README/STATUS/ARCHITECTURE/DESK prose
