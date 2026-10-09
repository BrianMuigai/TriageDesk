# Roadmap: TriageDesk

## Overview

TriageDesk turns a nurse's vitals and free-text complaint into a sourced, SATS-grounded priority
colour — and nothing reaches the queue without a named clinician's approval. The roadmap follows the
dependency DAG from the rule substrate outward: it front-loads the two riskiest unknowns (local-model
structured output; MCP wiring) in Phase 1, proves the pure deterministic scorer and its five owned MCP
tools in Phase 2, wires the explicit graph plus the protected approval gate, hash-chained audit, and
borrowed persistence in Phase 3, enforces an honest evaluation (including one declared failure) in
Phase 4, and lands a live demo plus a clean freeze before the 2026-10-15 deadline in Phase 5. Five
phases, coarse granularity, each one a vertical slice verifiable on its own.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: SATS Foundations & Risk Retirement** - Rule substrate, typed schema, scaffold; retire the model and MCP unknowns on evidence
- [ ] **Phase 2: Deterministic Scorer & Own MCP Server** - Pure cited scorer + the five contracted owned tools
- [ ] **Phase 3: Approval Gate, Gated Commit & Safety Spine** - The gate that refuses to commit without a named approver, plus audit and borrowed persistence
- [ ] **Phase 4: Evaluation, Recovery & Honest Failure** - Enforcing 13-case × 3-run evaluation with one declared failure
- [ ] **Phase 5: Demo, Docs & Freeze** - One-command run, live demo video, docs finalised, repo frozen

## Phase Details

### Phase 1: SATS Foundations & Risk Retirement
**Goal**: The published SATS rule substrate and the one typed case schema exist as the single source of truth, the project builds reproducibly, and both Day-1 unknowns are retired on evidence — the local model's schema-constrained output and the MCP beta-adapter / borrowed-server handshake.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: INTAKE-01, INTAKE-02, INTAKE-04, INTAKE-05, SAFE-04, QUAL-01
**Success Criteria** (what must be TRUE):
  1. Every TEWS band, colour threshold, discriminator, and category lives in exactly one `data/*.yaml` file (re-verified verbatim against the SATS manual) and appears nowhere else.
  2. A case — structured vitals plus a free-text complaint — is represented by one validated typed schema that rejects missing or implausible values instead of imputing them.
  3. A local open-weights model (1.5B vs 3B, chosen on measured evidence) returns valid schema-constrained JSON for the extraction task on this machine, and the 1.5B fallback has been run end-to-end.
  4. The MCP beta adapter lists and calls tools on both an owned-server stub and the borrowed SQLite server, or the pre-defined one-module World-B fallback swap is documented and chosen.
  5. A `uv`-pinned Python 3.12 rebuild is reproducible; dependencies, model tag, prompts, tool schemas, and scale data are pinned and hashed; a NOTICE records every third-party licence.
**Plans**: TBD

### Phase 2: Deterministic Scorer & Own MCP Server
**Goal**: A pure deterministic scorer converts typed vitals plus matched discriminators into a cited SATS colour and target time, and the owned MCP server exposes the intake and scoring capability as five contracted tools.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: INTAKE-03, SCORE-01, SCORE-02, SCORE-03, SCORE-04, SCORE-05, SAFE-01, TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05
**Success Criteria** (what must be TRUE):
  1. TEWS and discriminator-override scoring are computed deterministically from typed vitals — no number comes from the model — and every priority cites exactly the rules and vitals that fired (`citations == triggered_rules`).
  2. Paediatric / out-of-scope input fails closed: the system abstains and escalates rather than scoring a child, including when age is missing, expressed in months, or ambiguous.
  3. The owned MCP server exposes `normalize_case`, `match_discriminators`, `score_priority`, `raise_recheck_flag`, and a gated `commit_priority` stub, each validated against one shared contract.
  4. Every TEWS band edge on both sides, plus unit and boundary cases, is covered by tests; a missing vital is detected and never imputed (score inputs ⊆ nurse-provided fields).
  5. Discriminator matching is a deterministic data lookup with aliases in YAML and an explicit "no match" result, so injected or omitted complaint text cannot change the colour.
**Plans**: TBD

### Phase 3: Approval Gate, Gated Commit & Safety Spine
**Goal**: The gate physically refuses to place a patient in the queue without a named clinician's approval — enforced by a LangGraph `interrupt()`, an idempotent approval-keyed commit, a single hash-chained audit interceptor, and borrowed SQLite persistence.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: TOOL-06, ORCH-01, ORCH-02, ORCH-03, ORCH-04, ORCH-05, GATE-01, GATE-02, GATE-03, GATE-04, AUDIT-01, AUDIT-02, AUDIT-03, SAFE-02, SAFE-03, QUAL-02
**Success Criteria** (what must be TRUE):
  1. No code path — retry or deterministic fallback included — can reach `commit_priority` without a valid approval token carrying a named approver, role, and timestamp.
  2. The queue write is idempotent, keyed by `case_id` plus an immutable content hash: committing the same case twice yields exactly one queue row and one audit entry, even across a simulated crash.
  3. Every tool call appends one canonical hash-chained audit record through a single shared helper; the chain verifies after a restart and the audit store and queue store never diverge.
  4. The full graph runs `ingest → normalize → retrieve → score → verify → (recheck) → gate → commit → handover` on the local model only, with a deterministic-first `verify`, and missing-vital / out-of-scope conditions route to recovery or abstention edges that never guess.
  5. A deterioration re-check raises a visible second-look flag showing the before/after vitals with the queue position unchanged, and the handover card renders only structured fields with no diagnosis or prescription language.
**Plans**: TBD

### Phase 4: Evaluation, Recovery & Honest Failure
**Goal**: An honest, enforcing evaluation proves the system's behaviour — including one declared failure — and reports safety-relevant error directions and run-to-run stability.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, SAFE-05
**Success Criteria** (what must be TRUE):
  1. All 13 eval cases run 3× through the same graph interface; any run-to-run variation in colour or matched-discriminator set counts as a failure, and field-stability is reported separately from colour-stability.
  2. Under-triage and over-triage are reported separately, E-09 ships as a declared unfixed failure, and held-out cases show the failure is bounded rather than universal.
  3. INV-1…4 are executable assertions that non-zero-exit the run and gate CI whenever violated, and a suppression-direction injection case leaves the colour unchanged.
  4. The report carries per-run latency and token cost, is reproducible via recorded hashes, and is the sole source of numbers for `EVALS.md`.
**Plans**: TBD

### Phase 5: Demo, Docs & Freeze
**Goal**: A stranger can run the frozen system in one command, the demo video shows a live human-judged run including a failure, and the repository is frozen before the deadline.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DEMO-01
**Success Criteria** (what must be TRUE):
  1. A clean clone of the frozen tag runs the whole demo on the synthetic fixture in one command, and a CI smoke test exercises that path.
  2. `ARCHITECTURE.md`, `EVALS.md`, and `DESCRIPTION.md` are finalised, with every EVALS number sourced from `report.json` and the planned-vs-measured distinction preserved.
  3. The 3-minute unedited video shows a live run against the frozen commit with tool calls visible, including a human judging with evidence and a failure.
  4. The repo is tagged and `git log -1` predates the 2026-10-15 deadline; `commit_docs`/CI/hooks are disabled and the remote is audited for post-freeze commits.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. SATS Foundations & Risk Retirement | 0/TBD | Not started | - |
| 2. Deterministic Scorer & Own MCP Server | 0/TBD | Not started | - |
| 3. Approval Gate, Gated Commit & Safety Spine | 0/TBD | Not started | - |
| 4. Evaluation, Recovery & Honest Failure | 0/TBD | Not started | - |
| 5. Demo, Docs & Freeze | 0/TBD | Not started | - |
