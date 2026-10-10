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

### Active

- [ ] **Docs & rigour** — README is literally one command; EVALS counts reconciled (no 14-vs-16 drift); milestone-end documentation refresh
- [ ] **Evaluation** — the two fixable failures (E-04, E-07) pass; suite re-run and `EVALS.md` regenerated; calibrated confidence + abstention
- [ ] **Desk UX** — human-readable priority card; real approve/edit/dismiss gate; loud no-match/low-confidence banner; minimal vitals-entry surface
- [ ] **Agentic depth** — borrowed MCP exercised beyond `query`; durable `checkpoints.db` wired E2E; RAG grounding over the SATS KB; span tracing + replay
- [ ] **Review & demo** — live-review rehearsal; clinician review + quote if access allows; 2–3 min narrated demo (with the human video upload as the release gate)

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

## Current State

**Shipped:** v1.0 MVP (2026-10-10) — all 5 phases complete & verified.

- Frozen at tag `v1.0-submission`; pushed to `github.com/BrianMuigai/TriageDesk`.
- 239 tests pass; one-command `uv run triagedesk demo` runs offline from a clean clone.
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
*Last updated: 2026-10-10 — v1.1 Score Uplift started*
