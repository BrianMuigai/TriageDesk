# Roadmap: TriageDesk

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-10-10) — archived at `.planning/milestones/v1.0-ROADMAP.md`
- 🚧 **v1.1 Score Uplift** — Phases 6–12 (in progress)

## Overview

TriageDesk turns a nurse's vitals and free-text complaint into a sourced, SATS-grounded priority
colour — and nothing reaches the queue without a named clinician's approval. v1.1 "Score Uplift" is
**additive engineering onto the frozen v1.0 safety spine** (tag `v1.0-submission`): every capability
attaches at a published seam — a new node, a new tool, a new contract, or an adapter behind an
existing protocol — and never edits the scorer, the citation helper, or the audit interceptor.

The order is set by risk and dependency. Phase 6 front-loads the milestone's first HIGH blocker: the
durable approval-gate lifecycle plus its idempotency-key breadth bug (an edit must supersede, not
duplicate, the queue row). Phase 7 retires the second HIGH blocker — replay must be read-only and
structurally unable to re-commit — riding on Phase 6's checkpoint. Phases 8 and 9 land the two
pure/additive capabilities (calibrated confidence + abstention; retrieval grounding + deeper
borrowed-MCP read paths), Phase 10 consumes all three in the desk-facing UX with a real
approve/edit/dismiss gate, and Phases 11–12 close the honesty loop: the measured evaluation re-run,
the live review rehearsal, the narrated demo, and a full milestone-end documentation refresh. Seven
phases, coarse granularity, each a vertical slice verifiable on its own.

## Phases

**Phase Numbering:**
- Integer phases (6, 7, 8): Planned milestone work for v1.1 Score Uplift
- Decimal phases (6.1, 6.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order. Phase numbering continues
from v1.0 (which ended at Phase 5); it never restarts.

### 🚧 v1.1 Score Uplift (In Progress)

**Milestone Goal:** Close the ranked gaps in `STATUS.md` — the submission blocker, cheap docs/eval
fixes, the desk-facing UX, and the highest-leverage capability gaps — without regressing the frozen
v1.0 safety spine.

- [ ] **Phase 6: Durable Execution & Idempotent Gate** - Durable `checkpointed_graph` E2E, stable-thread resume after restart, and an edit that supersedes the queue row instead of duplicating it
- [ ] **Phase 7: Local Observability — Span Tracing & Read-Only Replay** - Local-only spans linked to the audit record, plus replay that reconstructs read-only and can never re-commit
- [ ] **Phase 8: Calibrated Confidence & Abstention** - A deterministic coverage/deferral signal where low confidence escalates or asks for missing info, never commits
- [ ] **Phase 9: Retrieval Grounding & Borrowed-MCP Depth** - Attributed SATS KB retrieval behind a closed-set contract that cannot set a colour, plus borrowed read paths kept read-only
- [ ] **Phase 10: Desk UX & Real Approval Gate** - Priority card, no-match/low-confidence banner, a real approve/edit/dismiss gate, and a minimal vitals-entry surface
- [ ] **Phase 11: Honest Evaluation Re-run & Rigour Docs** - E-04/E-07 fixed, 14-case suite re-run, `EVALS.md` regenerated from `report.json`, and a literal one-command README
- [ ] **Phase 12: Live Review, Demo & Milestone-Close Documentation** - Rehearsed live review + live rule edit, 2–3 min narrated demo, honest clinical fit, all submission docs refreshed

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-10-10</summary>

Archived at `.planning/milestones/v1.0-ROADMAP.md` (requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`).

- [x] **Phase 1: SATS Foundations & Risk Retirement** - Rule substrate, typed schema, scaffold; retire the model and MCP unknowns on evidence
- [x] **Phase 2: Deterministic Scorer & Own MCP Server** - Pure cited scorer + the five contracted owned tools
- [x] **Phase 3: Approval Gate, Gated Commit & Safety Spine** - The gate that refuses to commit without a named approver, plus audit and borrowed persistence
- [x] **Phase 4: Evaluation, Recovery & Honest Failure** - Enforcing 14-case × 3-run evaluation with one declared failure
- [x] **Phase 5: Demo, Docs & Freeze** - One-command run, live demo video, docs finalised, repo frozen

</details>

## Phase Details

### Phase 6: Durable Execution & Idempotent Gate
**Goal**: The demo and CLI execute the whole triage lifecycle through the durable `checkpointed_graph`, so a case paused at the approval gate survives a process restart and resumes on a stable `thread_id` — and an edit decision updates the queue row instead of duplicating it.
**Depends on**: Nothing (first phase of v1.1; attaches to the frozen v1.0 spine)
**Requirements**: AGENT-01
**Success Criteria** (what must be TRUE):
  1. A case paused at the approval gate resumes to a committed handover after a full process restart, using a stable `thread_id` derived from the immutable case content rather than a random id.
  2. An `edit` decision on resume supersedes the existing queue row — exactly one row reflects the edited colour and no second row is inserted, because the idempotency key covers the immutable case content, not `colour` alone.
  3. A case run end-to-end produces exactly one audit record and one queue row, proving `interrupt()` re-entry does not replay pre-gate side effects.
  4. `uv run triagedesk demo` runs its storyboard through the checkpointed graph from a clean clone, with a durable mode and a documented resume subcommand.
**Plans**: TBD

### Phase 7: Local Observability — Span Tracing & Read-Only Replay
**Goal**: Tool, node, and model spans emit to a local sink with no egress, each audit record carries a `trace_id` linking it to those spans, and replay reconstructs a past case read-only — structurally unable to re-run the gated commit.
**Depends on**: Phase 6
**Requirements**: AGENT-04
**Success Criteria** (what must be TRUE):
  1. Tool, node, and model spans are written to a local file with no network/egress, and cloud tracing remains disabled.
  2. Every audit record carries a `trace_id` that links it to its spans in the local stream.
  3. A past case is reconstructed for replay from the checkpoint plus the audit/span stream, without re-running the model.
  4. Replaying a gated case adds zero queue rows and zero commits, and the replayed outcome equals the original.
**Plans**: TBD

### Phase 8: Calibrated Confidence & Abstention
**Goal**: The system computes a deterministic coverage/deferral signal — never a model probability — exposed by an `assess_confidence` tool and wired to routing, so low confidence can only make the system more cautious (escalate or request-missing-info), never `commit` and never downgrade a scored colour.
**Depends on**: Phase 6
**Requirements**: AGENT-02
**Success Criteria** (what must be TRUE):
  1. `assess_confidence` returns a deterministic coverage/deferral signal derived from vitals coverage, discriminator coverage, the override-vs-TEWS path, and TEWS distance from the band edge — never a model probability and never a percentage presented as clinical risk.
  2. Low confidence routes to `escalate` or `request_missing_info` and never to `commit`; the signal can only make the system more cautious and can never downgrade a scored colour.
  3. The threshold is derived from a stated asymmetric cost, the deferral rate is reported, and a no-match case is never reported as high confidence.
  4. Calibration is measured offline on a held-out split and reported with ECE / risk–coverage, declared as a small-sample measure.
**Plans**: TBD

### Phase 9: Retrieval Grounding & Borrowed-MCP Depth
**Goal**: A read-only `retrieve_evidence` tool plus a `ground` node placed after `score` surface attributed SATS KB excerpts under a closed-set contract that cannot set a colour, and the borrowed SQLite MCP server is exercised through its read paths behind the unchanged `Store` protocol — read-only in the agent path.
**Depends on**: Phase 6
**Requirements**: AGENT-03, MCP-01
**Success Criteria** (what must be TRUE):
  1. A `retrieve_evidence` tool and a `ground` node placed after `score` return attributed SATS KB excerpts derived from `data/*.yaml`.
  2. Retrieval returns only closed-set discriminator ids, a rank, and an explicit `no_match` — it can never emit a colour or an uncited rule — and the `ground` node writes a separate `evidence` channel without touching `priority`/`citations`.
  3. The declared failure E-09 is addressed by real retrieval or reported as a clean defer, never by adding a literal alias.
  4. The borrowed SQLite MCP server's read paths (`list_tables`, schema, `read_records`, `db_info`) are used behind the unchanged `Store` protocol, with a tool allowlist and statement guard keeping the borrowed server read-only in the agent path.
**Plans**: TBD

### Phase 10: Desk UX & Real Approval Gate
**Goal**: The desk-facing surface renders the suggestion plus its evidence and requires a named human to approve, edit, or dismiss — nothing commits without that interaction.
**Depends on**: Phase 8, Phase 9
**Requirements**: UX-01, UX-02, UX-03, UX-04
**Success Criteria** (what must be TRUE):
  1. A human-readable priority card renders the **suggested** colour, target time, and the "why" vitals next to their adjacent citations — framed as a suggestion and never a diagnosis.
  2. A loud "no discriminator matched / low confidence — nurse to confirm" banner shows whenever the typed uncertainty signal fires, so the E-09 class is a visible flag rather than a buried JSON key.
  3. The gate is a real approve / edit / dismiss interaction that records a named approver and commits no artefact on dismiss or timeout (no default approve).
  4. A minimal vitals-entry surface validates through the one shared schema, and a one-screen desk quickstart gives a first desk-facing interaction without coupling to graph internals.
**Plans**: TBD
**UI hint**: yes

### Phase 11: Honest Evaluation Re-run & Rigour Docs
**Goal**: The two fixable measured failures reach their expected outcomes, the 14-case suite is re-run over the real graph, and `EVALS.md` is regenerated solely from `report.json` with reconciled counts — alongside a literal one-command README.
**Depends on**: Phase 10
**Requirements**: EVAL-06, DOCS-04, DOCS-05
**Success Criteria** (what must be TRUE):
  1. E-04 (emergency discriminator) and E-07 (deterioration recheck) reach their expected outcomes in the measured run.
  2. The 14-case suite is re-run over the real graph and `EVALS.md` is regenerated **only** from `report.json` (no hand-edited numbers), with case and run counts reconciled (no 14-vs-16 / 29-vs-32 drift).
  3. A stranger gets running in one command — `uv run triagedesk demo` is the literal one-liner (uv auto-syncs; no separate install step).
**Plans**: TBD

### Phase 12: Live Review, Demo & Milestone-Close Documentation
**Goal**: The live technical review is rehearsed end-to-end including a live one-line discriminator edit, the demo runs to 2–3 minutes with narration and the measured eval on screen, the clinical-fit gap is re-declared honestly, and every submission document is refreshed to the v1.1 state.
**Depends on**: Phase 11
**Requirements**: REV-01, DEMO-02, FIT-01, DOCS-06
**Success Criteria** (what must be TRUE):
  1. A 10-minute live walkthrough plus a dry-run "add a discriminator to `data/sats_discriminators.yaml` live, reload, and re-score" passes the safety suite — the extension is data-only, with no code edit.
  2. The demo runs to 2–3 minutes with narration, showing the measured eval run on screen, still unedited and still showing a failure.
  3. A single triage nurse or clinician review is obtained and quoted in README/EVALS if access can be arranged; if not, the gap is re-declared honestly rather than over-claimed.
  4. Every submission document (README, ARCHITECTURE, EVALS, DESCRIPTION, STATUS, `docs/REQUIREMENTS`, `docs/ROADMAP`) reflects the v1.1 capabilities and current measured results, with no stale v1.0 claims.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8 → 9 → 10 → 11 → 12
(Phases 7, 8, and 9 each depend only on Phase 6 and are independent of one another; Phase 10 consumes 8 and 9.)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. SATS Foundations & Risk Retirement | v1.0 | 4/4 | Complete | 2026-10-09 |
| 2. Deterministic Scorer & Own MCP Server | v1.0 | 3/3 | Complete | 2026-10-09 |
| 3. Approval Gate, Gated Commit & Safety Spine | v1.0 | 5/5 | Complete | 2026-10-09 |
| 4. Evaluation, Recovery & Honest Failure | v1.0 | 6/6 | Complete | 2026-10-10 |
| 5. Demo, Docs & Freeze | v1.0 | 3/3 | Complete | 2026-10-10 |
| 6. Durable Execution & Idempotent Gate | v1.1 | 0/TBD | Not started | - |
| 7. Local Observability — Span Tracing & Read-Only Replay | v1.1 | 0/TBD | Not started | - |
| 8. Calibrated Confidence & Abstention | v1.1 | 0/TBD | Not started | - |
| 9. Retrieval Grounding & Borrowed-MCP Depth | v1.1 | 0/TBD | Not started | - |
| 10. Desk UX & Real Approval Gate | v1.1 | 0/TBD | Not started | - |
| 11. Honest Evaluation Re-run & Rigour Docs | v1.1 | 0/TBD | Not started | - |
| 12. Live Review, Demo & Milestone-Close Documentation | v1.1 | 0/TBD | Not started | - |
