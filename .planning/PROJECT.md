# TriageDesk

## What This Is

TriageDesk is an agentic triage-support tool for the outpatient (OPD) triage desk of a busy public
hospital in Africa. It turns the vitals and presenting complaint a nurse already has in front of her
into a **sourced, SATS-grounded priority level in seconds** — and it never diagnoses, prescribes, or
moves a patient without a named clinician's approval. It is an entry in the *Agentic AI for Africa*
challenge (Health & Wellbeing track, **Symptom-based priority scoring**).

> Note: the **public submission docs** live at the repo root (`README.md`, `ARCHITECTURE.md`,
> `EVALS.md`, `DESCRIPTION.md`, `SECURITY.md`) and under `docs/` (`PROJECT.md`, `REQUIREMENTS.md`,
> `ROADMAP.md`, `DECISIONS.md`, `CONVENTIONS.md`). This `.planning/PROJECT.md` is GSD's internal
> working memory. Keep them consistent, but do not treat them as the same file.

## Core Value

**A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches
the queue without her approval.** If everything else fails, this must work.

## Current Milestone: v1.1 Score Uplift

**Goal:** Close the ranked gaps in `STATUS.md` — the submission blocker, cheap docs/eval fixes, the desk-facing UX, and the highest-leverage capability gaps — without regressing the frozen v1.0 safety spine.

**Target features:**
- Docs & rigour: one-command README; reconciled EVALS numbers; milestone-end documentation refresh
- Evaluation: fix E-04 + E-07; re-run the measured suite; calibrated confidence + abstention
- Desk UX: human-readable priority card; real approve/edit/dismiss gate; no-match banner; vitals-entry surface
- Agentic depth: exercise the borrowed MCP beyond `query`; durable checkpoints E2E; RAG grounding; span tracing + replay
- Review & demo: rehearse the live review; clinician review + quote if access allows; 2–3 min narrated demo

## Requirements

### Validated

- **v1.0 MVP** (shipped 2026-10-10, frozen at tag `v1.0-submission`): vitals + complaint → **cited** SATS priority in seconds; deterministic TEWS + discriminator-override scoring; own MCP server with 5 tools (incl. one gated write); borrowed SQLite MCP; human approval gate; hash-chained audit log; deterioration re-check flag; missing-vital recovery + safe abstention; local open-weights model end-to-end with no egress; 14-case honest evaluation incl. one declared failure; one-command run + ARCHITECTURE/EVALS/DESCRIPTION docs.
- **Durable execution + idempotent gate** — Phase 6 (2026-10-12): the lifecycle runs through the durable `checkpointed_graph` over `checkpoints.db`; a case paused at the gate resumes after a full process restart on a content-derived `thread_id` (`case_id_for`); the queue key covers the immutable `CaseInput` so an `edit` **supersedes in place** (one row, `position`/`created_at` preserved); `demo --durable` + `triagedesk resume` make the restart demonstrable; exactly one audit record per owned tool (no pre-gate replay).
- **Local observability + read-only replay** — Phase 7 (2026-10-12): tool/node/model spans are written by ONE JSONL writer from the existing seams (interceptor, node wrapper, model boundary) with cloud tracing provably inert (`harden_offline`); every `AuditRecord` carries a content-derived `trace_id` sealed in the chain digest and persisted through the borrowed store; `triagedesk replay` reconstructs a past case from the checkpoint + audit/span stream with no graph, no tool map and no model — proven to add zero queue rows and zero commits.
- **Calibrated confidence & abstention** — Phase 8 (2026-10-13): a deterministic four-component coverage/deferral signal (`core/confidence.py`) exposed by the sixth owned tool `assess_confidence` and wired through a new `assess` node placed immediately before the gate — low confidence routes only to `escalate`/`request_missing_info`, never `commit`, and can never downgrade a colour; `no_match` is an absolute deferral; the threshold derives from a stated asymmetric cost (D20); the deferral rate (12/32) and a declared-split calibration block (ECE + risk–coverage, small-sample) are published only by the generator.
- **Retrieval grounding & borrowed-MCP depth** — Phase 9 (2026-10-13): a pure, colour-free deterministic retrieval (`core/retrieval.py`) exposed by the seventh owned tool `retrieve_evidence` and a routing-neutral `ground` node (`score → ground → verify`) writing an advisory `evidence` channel isolated from `priority`/`citations`; one public `tokenize()`/`contains_sequence` owner shared with the matcher; the borrowed SQLite MCP server's read paths (`db_info`, `list_tables`, `get_table_schema`, `read_records`) are used behind the **unchanged** `Store` protocol under a read-tool allowlist and a fail-closed statement guard (hardened after review against `WITH`-DML, write-`PRAGMA`, multi-statement and `EXPLAIN PRAGMA`).
- **Desk UX & real approval gate** — Phase 10 (2026-10-13): a dependency-free local HTML surface (`src/triagedesk/desk/`, served by a stdlib `http.server` bridge, `uv run triagedesk desk`) renders the **suggested** priority card with adjacent citations, a loud typed-signal uncertainty banner, a real approve/edit/dismiss gate with a named approver (no commit on dismiss or timeout), and a vitals form validated through the ONE `CaseInput` schema; a one-screen `docs/DESK.md` quickstart plus a drift guard; loopback-only, CSRF/Host-hardened, no commit path in the surface.
- **Live review, demo & milestone-close documentation** — Phase 12 (2026-10-13): a rehearsed 10-minute live-review runbook (`docs/REVIEW.md`) whose headline beat is a **data-only** discriminator extension (demonstrated hermetically with `src/` byte-unchanged); a 2–3 min narrated demo script showing the committed measured projection plus the live E-09 failure; an honest clinical-fit re-declaration with a marked, empty, attributed clinician-quote slot; and every submission document swept to v1.1 (ARCHITECTURE word-neutral). The demo recording/upload and the clinician review are flagged human submission steps, never claimed.
- **Honest evaluation re-run & rigour docs** — Phase 11 (2026-10-13): E-04 fixed via a general structured-output-contract description (derived from the scored set) and E-07 via the owner-confirmed fixture-note repair (expectation unchanged); the 16-case suite re-run over the real graph; `EVALS.md` regenerated solely from `report.json` with the §4 row set reconciled fail-closed; and the README reduced to the literal one-command quickstart. The residual 1.5B-model misses (E-11, E-13) and the declared failure E-09 stay visible — nothing tuned.

### Active

- [x] **Docs & rigour** — one-command README, EVALS counts reconciled, milestone-end documentation refresh ✅ (Phases 11–12)
- [x] **Evaluation** — E-04 and E-07 fixed; suite re-run; `EVALS.md` regenerated from `report.json` ✅ (Phase 11)
- [x] **Desk UX** — priority card, real approve/edit/dismiss gate, loud no-match/low-confidence banner, minimal vitals-entry surface ✅ (Phase 10)
- [x] **Agentic depth** — borrowed MCP exercised beyond `query` ✅; RAG grounding over the SATS KB ✅ (Phase 9)
- [x] **Review & demo** — live-review rehearsal + demo script + honest clinical-fit re-declaration ✅ (Phase 12); the video upload and a clinician review remain flagged **human** submission steps

### Out of Scope

- **Paediatric SATS scoring** — the agent abstains + escalates rather than mis-scoring a child
- **Diagnosis / prescribing / autonomous queue movement** — forbidden by the challenge
- **Multilingual input** — deferred; architecture stays aware
- **Real patient data** — synthetic only
- **Long-term memory / runtime self-learning** — unsafe at the point of care
- **Live hospital-system integration** — out of scope for the prototype

## Business Context

_(Not monetized. This is a challenge submission; delete this section if it becomes noise.)_

- **Customer**: public-hospital OPD triage desks (nurse-led)
- **Revenue model**: none (open source, Apache-2.0)
- **Success metric**: a nurse does a real thing faster under queue pressure; priority survives audit
- **Strategy notes**: `../docs/ROADMAP.md` (submission plan) and post-MVP roadmap in `~/.opencode/plan/`

## Context

- **Problem**: the OPD bottleneck is the triage desk (60–90 min wait before a patient is seen); a
  genuinely urgent patient can queue behind routine follow-ups.
- **Domain**: an existing, published triage scale is mandatory — we build on the **South African
  Triage Scale (SATS)** (TEWS vitals score + clinical discriminator overrides → 5 colours).
- **Prior work**: eleven design docs already exist at the repo root (vision, compliance matrix,
  architecture, evals, decisions, security, SATS domain model). These are deep context, not scratch.
- **Environment**: host has ~6.9 GB RAM with low headroom → use the installed **`qwen3.5:4b`**; Phase 1
  measures RAM fit and keeps a smaller-Qwen fallback. Host Python is 3.14 → pin 3.12 via `uv`.
- **Known gap**: no guaranteed access to a triage nurse/clinician during the build window.

## Constraints

- **Team**: solo — scope discipline is a scored skill.
- **Timeline**: ~6 days (today 2026-10-09 → deadline 2026-10-15); repos are cloned at the deadline and
  post-deadline commits disqualify.
- **Compute**: local CPU only; small quantised open-weights model.
- **Stack**: required MCP + open-source orchestration; no closed no-code builders.
- **Data**: synthetic only; no health data leaves the machine.
- **Compliance**: every challenge requirement is tracked in `../docs/REQUIREMENTS.md`.
- **Engineering standards**: **DRY + SOLID are iron-clad** (`../docs/CONVENTIONS.md`); a violation blocks the phase.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid: deterministic scorer + LLM orchestration | Defensible, reproducible, honest evaluation | — Pending |
| Build on SATS (not MCTS/Manchester) | Openly published, African context; MTS is licensed | — Pending |
| Local open-weights model (Qwen2.5) via Ollama | Eligibility + data residency | — Pending |
| LangGraph orchestration | `interrupt()` maps to the approval gate | — Pending |
| Borrow SQLite MCP server | Don't hand-roll persistence | — Pending |
| Safe abstention on paediatric/out-of-scope | Never mis-score a child | — Pending |
| Apache-2.0 licence | OSI-approved + patent grant | — Pending |
| Explicit graph over free-form ReAct | Reliable on a small CPU model | — Pending |
| SATS rules in YAML data | Live-review extensibility (add a rule in one line) | — Pending |
| Hash-chained audit log | Auditability / defensibility | — Pending |
| **DRY + SOLID as iron-clad rule** | Maintainability; enforced at plan-check, code-review, and verifier gates | — Pending |
| Queue identity = the immutable case input (not the scored colour) | An `edit` must supersede, not duplicate, so the idempotency key cannot be a derived output | ✅ Phase 6 (D6-04/D6-06) |
| `thread_id` = content hash of the note (`case_id_for`) | The same case resumes from any entry point and after a restart; no random ids | ✅ Phase 6 (D6-01) |
| `checkpoints.db` is the real execution path (`demo --durable` + `resume`) | Durability must be demonstrable, not only unit-tested; the default demo stays hermetic | ✅ Phase 6 (D6-08/D6-11) |
| Local JSONL span sink + content-derived `trace_id` on every audit record | Observability must not require egress; the trace must be recomputable from the case, not random | ✅ Phase 7 (D7-02/D7-05/D7-06) |
| Replay reads the checkpoint directly — no graph, no tool map | Read-only must be structural, not conventional; the gated commit must be unreachable | ✅ Phase 7 (D7-09/D7-10) |
| Confidence is a deterministic coverage signal, never a model probability | A fabricated or model-derived number would be over-trusted at the point of care | ✅ Phase 8 (D8-01/D8-02/D8-04) |
| `no_match` forces a deferral (absolute) | Discriminator coverage is the known gap; the colour would rest on TEWS alone, so the human decides | ✅ Phase 8, owner-confirmed (D8-11) |
| Retrieval is colour-free and advisory (`evidence` channel only) | Grounding must *show* provenance, never *set* a priority; one place a colour is produced | ✅ Phase 9 (D9-03/D9-07) |
| The borrowed server stays read-only on the agent path (allowlist + fail-closed guard) | The borrowed MCP is the storage authority; the agent path must not mutate it | ✅ Phase 9 (D9-12), hardened after review |

## Current State

**Shipped:** v1.0 MVP (2026-10-10) — all 5 phases complete & verified.
**Complete:** v1.1 Score Uplift — all 7 phases (6–12) complete (2026-10-13).

- Frozen at tag `v1.0-submission`; pushed at `github.com/BrianMuigai/TriageDesk`.
- 454 tests pass; one-command `uv run triagedesk demo` runs offline from a clean clone (no model, no borrowed subprocess).
- Phase 6: durable execution (`demo --durable` + `triagedesk resume`; an edit supersedes the queue row in place).
- Phase 7: local observability (one JSONL span sink, cloud tracing inert, `trace_id` on every audit record) and a structurally read-only `triagedesk replay`.
- Phase 8: calibrated confidence & abstention (the `assess_confidence` tool + `assess` node; a one-way safety property; a deferral rate and calibration block in the published report). The published report remains `mode: real`, honestly showing the pre-existing E-04/E-07/E-13 failures that **Phase 11** owns.
- Phase 9: retrieval grounding (`retrieve_evidence` + a routing-neutral `ground` node and an advisory `evidence` channel) and borrowed-MCP read-path depth behind the unchanged `Store` protocol with a fail-closed statement guard.
- Milestone archive: `.planning/milestones/v1.0-ROADMAP.md`, `v1.0-REQUIREMENTS.md`.
- Demo video recorded: `docs/triagedesk-demo.mp4` (human upload to YouTube/Vimeo pending).

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-13 after Phase 12 (milestone v1.1 complete)*
