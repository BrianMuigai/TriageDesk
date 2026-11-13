# Roadmap: TriageDesk

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-10-10) — archived at `.planning/milestones/v1.0-ROADMAP.md`
- ✅ **v1.1 Score Uplift** — Phases 6–12 (shipped 2026-10-13) — archived at `.planning/milestones/v1.1-ROADMAP.md`
- ✅ **v1.2 Coverage Recovery** — Phases 15–18 (shipped 2026-11-13) — archived at `.planning/milestones/v1.2-phases/`
- 🚧 **v1.3 Adaptive Triage** — Phases 19–22 (started 2026-11-13)

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

- [x] **Phase 15: Deterministic coverage classification** (2/2 plans) — `matched` / `ambiguous` / `no_candidate` from the closed set plus data-driven context terms
- [x] **Phase 16: Three-way confidence and the bounded clarification terminal** (3/3 plans) — vitals-only delivery, at most three questions, one answer round
- [x] **Phase 17: Extraction completeness** (2/2 plans) — recover every stated vital the model drops
- [x] **Phase 18: Eval expansion, honest measurement and docs** (3/3 plans) — 24 cases (6 held-out), report-derived EVALS.md

</details>

---

## v1.3 Adaptive Triage

**Milestone goal:** replace the fixed investigation ladder with a bounded, audited planner that genuinely
decides what to do next — while the safety kernel (`score → verify → recheck → assess → gate → commit`)
stays a non-skippable suffix. The reviewer's challenge ("rules engine with an LLM extraction step?") is
answered by behaviour plus a structural proof, not by prose.

**Design in one line:** *an adaptive envelope around a frozen kernel.* The planner may choose only
read-only investigation actions; the model proposes and a deterministic guard disposes; the colour still
comes from exactly one place.

### Phase 19: Planner substrate — typed decision, closed action set, admissibility guard

**Goal:** A planner decision is a typed contract over a closed action set, proposed by the local model and validated by a deterministic guard that can only narrow what happens next — with the bounded-step policy implemented and tested before any graph edge moves.
**Requirements**: ADAPT-02, ADAPT-04, ADAPT-06
**Depends on:** Phase 18
**Plans:** 0/3 plans complete

Plans:

- [ ] 19-01-PLAN.md — `core/planner.py`: `PlanAction` closed set, `InvestigationState`, `admissible_actions`, `default_plan`, `validate_proposal`, budget/no-repeat policy
- [ ] 19-02-PLAN.md — Model proposal via structured output in the ONE `llm` wrapper, and the thin `plan_next_step` owned tool
- [ ] 19-03-PLAN.md — Guard tests: inadmissible / malformed / unparseable / exhausted-budget proposals all degrade to `conclude`; no proposal can widen the action set

### Phase 20: MCP elicitation end-to-end — `request_clarification` asks mid-call

**Goal:** The owned server genuinely asks the human for the missing measurement inside a tool call, the shipped adapter turns that into a LangGraph `interrupt()`, and a decline or cancel is treated as a refusal rather than an answer.
**Requirements**: ELICIT-01, ELICIT-02, ELICIT-03, ELICIT-04, ELICIT-05
**Depends on:** Phase 19
**Plans:** 0/3 plans complete

Plans:

- [ ] 20-01-PLAN.md — `request_clarification` tool with `ctx.elicit()`, typed form, at most three questions; the nine-name allowlist fan-out in one atomic change
- [ ] 20-02-PLAN.md — Adapter-level proof: real `MCPAdapter` call → `interrupt(mcp_elicitation)` → resume → answer returned; decline/cancel path
- [ ] 20-03-PLAN.md — Desk + CLI present the elicitation question distinctly from the approval gate; neither can commit from it

### Phase 21: Adaptive graph — the `plan` node, the bounded loop, and the frozen-kernel proof

**Goal:** The graph investigates adaptively before it scores — `plan → action → plan … → conclude` inside a hard budget — and a structural test proves no investigation node can reach `score`, the gate, or the commit, with every decision audited.
**Requirements**: ADAPT-01, ADAPT-03, ADAPT-05
**Depends on:** Phase 20
**Plans:** 0/3 plans complete

Plans:

- [ ] 21-01-PLAN.md — `plan` node + `gather_evidence` / `ask_question` / `re_extract` / `conclude` actions; loop back through `retrieve`; TRACER_NODES updated
- [ ] 21-02-PLAN.md — Structural proof: `conclude` is the only edge into `score`; `commit` keeps one inbound edge; no investigation node writes `priority`/`commit_result`
- [ ] 21-03-PLAN.md — Decision audit + span facts (action, rationale, signals, step index) and a replayable "why next?" record

### Phase 22: Measure the adaptivity, publish it honestly, and answer the reviewer

**Goal:** The suite measures whether the planner earns its keep — adaptive vs default-conclude on the same cases, with steps and latency — and the docs answer "is this a rules engine?" with the measured delta and the structural proof.
**Requirements**: MEAS-01, MEAS-02, MEAS-03, MEAS-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Depends on:** Phase 21
**Plans:** 0/3 plans complete

Plans:

- [ ] 22-01-PLAN.md — Eval facts: investigation steps, action sequence, elicitation occurred, guard override; new cases resolvable only by asking
- [ ] 22-02-PLAN.md — Report: adaptive-vs-baseline block, invariants re-proven, `EVALS.md` regenerated (`--check` exits 0)
- [ ] 22-03-PLAN.md — ARCHITECTURE/STATUS/README/DECISIONS/MCP.md + skill sweep; the written reviewer answer

