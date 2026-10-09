# TriageDesk

## What This Is

TriageDesk is an agentic triage-support tool for the outpatient (OPD) triage desk of a busy public
hospital in Africa. It turns the vitals and presenting complaint a nurse already has in front of her
into a **sourced, SATS-grounded priority level in seconds** — and it never diagnoses, prescribes, or
moves a patient without a named clinician's approval. It is an entry in the *Agentic AI for Africa*
challenge (Health & Wellbeing track, **Symptom-based priority scoring**).

> Note: the repository-root `PROJECT.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `EVALS.md`,
> `DECISIONS.md`, `SECURITY.md` are the **public submission artifacts**. This `.planning/PROJECT.md`
> is GSD's internal working memory. Keep them consistent, but do not treat them as the same file.

## Core Value

**A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches
the queue without her approval.** If everything else fails, this must work.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Turn vitals + complaint into a **cited** SATS priority in seconds
- [ ] **Deterministic** TEWS + discriminator-override scoring (no LLM arithmetic)
- [ ] Our own **MCP server** with ≥3 tools, incl. acting + one gated write
- [ ] One **borrowed** MCP server (SQLite) for case/queue storage + audit
- [ ] **Human approval gate** on every queue-affecting action
- [ ] **Hash-chained audit log** (inputs, outputs, timestamps, named approver)
- [ ] **Deterioration re-check flag** (second look; no auto re-classification)
- [ ] **Missing-vital recovery** + **safe abstention** (paediatric / out-of-scope)
- [ ] **Open-weights local model** end-to-end, no data egress
- [ ] **13 honest eval cases** incl. one unfixed failure, run-to-run variation measured
- [ ] One-command run + 3-min demo video + ARCHITECTURE/EVALS/DESCRIPTION docs

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
- **Strategy notes**: `../ROADMAP.md` (submission plan) and post-MVP roadmap in `~/.opencode/plan/`

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
- **Compliance**: every challenge requirement is tracked in `../REQUIREMENTS.md`.
- **Engineering standards**: **DRY + SOLID are iron-clad** (`../CONVENTIONS.md`); a violation blocks the phase.

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
*Last updated: 2026-10-09 after initialization*
