# Roadmap: TriageDesk

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-10-10) — archived at `.planning/milestones/v1.0-ROADMAP.md`
- ✅ **v1.1 Score Uplift** — Phases 6–12 (shipped 2026-10-13) — archived at `.planning/milestones/v1.1-ROADMAP.md`
- ✅ **v1.2 Coverage Recovery** — Phases 15–18 (shipped 2026-11-13) — archived at `.planning/milestones/v1.2-phases/`
- 🚧 **v1.3 Adaptive Triage** — Phases 19–24 (started 2026-11-13)

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
comes from exactly one place. A deterministic emergency check runs before any model call and may skip the
model and the planner — never the kernel or the clinician.

**Diagrams (proposed, Phase 19):** `docs/assets/architecture-workflow.pdf` (clinical) ·
`docs/assets/architecture-components.pdf` (engineering) · `docs/assets/architecture-v1.3.pdf` (reference).

### Phase 19: Architecture documentation — two diagrams, one vocabulary, honest labels

**Goal:** A judge understands the clinical workflow in under a minute and an engineer can trace a model call, an MCP interaction, a database access, a checkpoint write and an audit record — with every element marked implemented, tested, proposed or outstanding.
**Requirements**: DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05, DIAG-06
**Depends on:** Phase 18
**Plans:** 0/3 plans complete

Plans:

- [ ] 19-01-PLAN.md — Diagram A (clinical workflow) and Diagram B (components) as one-renderer sources, with the shared legend
- [ ] 19-02-PLAN.md — Honest labelling pass: implemented / tested / proposed / outstanding; source-name parity check
- [ ] 19-03-PLAN.md — `ARCHITECTURE.md` links both, `README.md` stays high-level, `SECURITY.md` inventory, `STATUS.md` four-state separation

### Phase 20: Planner substrate — typed decision, closed action set, admissibility guard

**Goal:** A planner decision is a typed contract over a closed action set, proposed by the local model and validated by a deterministic guard that can only narrow what happens next — with the bounded-step policy implemented and tested before any graph edge moves.
**Requirements**: ADAPT-02, ADAPT-04, ADAPT-06, ADAPT-08
**Depends on:** Phase 19
**Plans:** 0/3 plans complete

Plans:

- [ ] 20-01-PLAN.md — `core/planner.py`: `PlanAction` closed set (`finish_investigation`), `InvestigationState`, `admissible_actions`, `default_plan`, `validate_proposal`, budget/no-repeat policy
- [ ] 20-02-PLAN.md — Model proposal via structured output in the ONE `llm` wrapper, and the thin `plan_next_step` owned tool
- [ ] 20-03-PLAN.md — Guard tests: inadmissible / malformed / unparseable / exhausted-budget proposals all degrade to `finish_investigation`; no proposal can widen the action set

### Phase 21: MCP elicitation end-to-end — `request_clarification` asks mid-call

**Goal:** The owned server genuinely asks the human for the missing measurement inside a tool call, the shipped adapter turns that into a LangGraph `interrupt()`, and all four outcomes are distinguished — with a refusal never treated as an answer.
**Requirements**: ELICIT-01, ELICIT-02, ELICIT-03, ELICIT-04, ELICIT-05, ELICIT-06, ELICIT-07, ELICIT-08
**Depends on:** Phase 20
**Plans:** 0/3 plans complete

Plans:

- [ ] 21-01-PLAN.md — `request_clarification` with `ctx.elicit()`, data-sourced questions only, four outcomes; the nine-name allowlist fan-out in one atomic change
- [ ] 21-02-PLAN.md — Adapter-level proof: real `MCPAdapter` call → `interrupt(mcp_elicitation)` → resume → answer; decline/cancel/unavailable paths; idempotent resume
- [ ] 21-03-PLAN.md — Desk + CLI present the question distinctly from the gate; an answer is an observation, not an approval

### Phase 22: Deterministic emergency bypass — the model does not delay a critical patient

**Goal:** A structured case that the pure scorer already puts in the most urgent band reaches the kernel without waiting for extraction or the planner — and still cannot commit without the clinician.
**Requirements**: EMERG-01, EMERG-02, EMERG-03, EMERG-04, EMERG-05
**Depends on:** Phase 21
**Plans:** 0/2 plans complete

Plans:

- [ ] 22-01-PLAN.md — `core/emergency.py` + the `emergency_check` node and route; skips `normalize` and `plan`, never the kernel
- [ ] 22-02-PLAN.md — Proof: incomplete/unstructured cases never fire; the arm still hits verify/recheck/assess/gate; the bypass is audited and spanned

### Phase 23: Adaptive graph — the `plan` node, the bounded loop, and the frozen-kernel proof

**Goal:** The graph investigates adaptively before it scores — `plan → action → plan … → finish_investigation` inside a hard budget — and a structural test proves no investigation node can reach `score`, the gate or the commit, with every decision audited and re-extraction monotone.
**Requirements**: ADAPT-01, ADAPT-03, ADAPT-05, ADAPT-07
**Depends on:** Phase 22
**Plans:** 0/3 plans complete

Plans:

- [ ] 23-01-PLAN.md — `plan` node + `gather_evidence` / `ask_question` / `re_extract` / `finish_investigation`; loop back through `retrieve`; monotone merge; TRACER_NODES updated
- [ ] 23-02-PLAN.md — Structural proof: `finish_investigation` is the only edge into `score`; `commit` keeps one inbound edge; no investigation node writes `priority`/`commit_result`
- [ ] 23-03-PLAN.md — Decision audit + span facts (action, rationale, signals, step index) and a replayable "why next?" record

### Phase 24: Measure the adaptivity, publish it honestly, and answer the reviewer

**Goal:** The suite measures whether the planner earns its keep — adaptive vs default-finish on the same cases, with steps and latency — and the docs answer "is this a rules engine?" with the measured delta and the structural proof.
**Requirements**: MEAS-01, MEAS-02, MEAS-03, MEAS-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06
**Depends on:** Phase 23
**Plans:** 0/3 plans complete

Plans:

- [ ] 24-01-PLAN.md — Eval facts: investigation steps, action sequence, elicitation outcome, guard override, emergency bypass; cases resolvable only by asking
- [ ] 24-02-PLAN.md — Report: adaptive-vs-baseline block, invariants re-proven, `EVALS.md` regenerated (`--check` exits 0)
- [ ] 24-03-PLAN.md — ARCHITECTURE/STATUS/README/DECISIONS/MCP.md + skill sweep; regenerate the canonical diagrams from shipped code; the written reviewer answer
