# PROJECT — TriageDesk

> Companion to the challenge brief:
> <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> This document defines *what we are building and what we are not*, before any code exists.

---

## 1. One-line vision

Give the triage nurse at a busy public-hospital OPD desk a **sourced, nurse-confirmed priority** for
each patient in **seconds**, so the wait itself stops being where the risk is.

## 2. The problem

The bottleneck in public OPDs is not the doctor's room — it is the **triage desk**. One or two nurses
with basic equipment (BP cuff, thermometer, pulse oximeter) work through every walk-in before anyone
gets a priority. A genuinely urgent patient can wait **60–90 minutes** behind routine follow-ups
because nothing at the desk tells the nurse to look twice.

The failure is one of **attention allocation under load**, not of missing skill. The nurse knows how to
triage; she simply cannot see everyone at once, early enough.

## 3. Who it serves

| Actor | Role in the workflow |
| --- | --- |
| **Triage nurse** *(primary user)* | Enters vitals + presenting complaint; receives a sourced priority; **confirms or overrides** it. |
| **Triage clinician / SHCP** *(approver)* | The named senior healthcare professional whose approval releases a case card to the queue. |
| **Patient** | Receives faster, better-sequenced care; is **never** acted on by the agent alone. |

**Facility archetype & workflow.** A district/regional public hospital OPD: a physical triage desk at
the entrance, paper case cards, a streaming model (majors / minors / resus). The agent sits *at the
desk*, invoked per patient, and augments — never replaces — the nurse's judgement.

> **Honest note:** we do not have guaranteed access to a working triage nurse/clinician during the
> build window. Fit-to-desk is therefore grounded in the published SATS process and OPD workflow
> literature and is flagged as a validation gap (see `../EVALS.md` → Clinician validation and
> `REQUIREMENTS.md` → JC-3).

### 3.1 What the nurse does faster — assumption-based model

We cannot yet measure at a real desk (no clinician access). The model below is an **explicitly
assumption-labelled estimate** of where time is saved — it is *not* a measured result, and the README
says so.

| Step | Today (assumed) | With TriageDesk (assumed) |
| --- | --- | --- |
| Measure + read vitals and complaint | 30–60 s | unchanged |
| Complete the case card | 20–30 s | unchanged |
| **Decide urgency** | 15–45 s (worsens under load) | **draft priority in seconds**; nurse confirms/overrides |
| **Time-to-first-assessment (urgent)** | 60–90 min | shorter where urgency is surfaced earlier |

The claim is deliberately narrow: TriageDesk reduces **decision latency at the desk**, not the clinical
workload. It is falsified by the same measure the brief names — time-to-first-assessment.

## 4. Sub-theme

**Symptom-based priority scoring** (one theme, as required).

Rationale: it is the most *defensible* and most *testable* of the four themes. Its correctness can be
measured against a published scale with deterministic cases, which directly serves the
Evaluation & reliability and Defensibility judging criteria. **Deterioration watch** is included as a
single differentiated *acting* capability (the re-check flag); **referral routing** is a stretch.

> **Single-theme entry.** This is entered under Symptom-based priority scoring **only**. The
> deterioration re-check is a *capability of the same agent*, not a second submission under the
> "Deterioration watch" theme — the rules forbid entering one project under more than one theme
> (`REQUIREMENTS.md` EL-2).

## 5. The safety boundary (non-negotiable)

TriageDesk is an **advisory scoring tool**, not a decision-maker.

1. It **scores** or **sequences** — it never **diagnoses**, **prescribes**, or **decides who gets seen**.
2. A **named nurse or clinician confirms** every priority before a case card is sent to a bay/queue.
3. A **deterioration flag raises a patient for a second look** — the agent cannot re-classify a patient
   on its own.
4. **Every priority cites** the vitals or symptom entry behind it. An unsourced urgency flag is treated
   as a system failure, not a feature.

The boundary is enforced structurally: the only tool that writes to a queue position refuses to run
without a recorded human approval.

## 6. Scope

### In scope (MVP)
- Adult SATS: five-step process, adult **TEWS**, and the adult **clinical discriminator** overrides.
- One MCP server (ours) with **≥3 tools**, including **acting** tools and one gated write.
- One **borrowed** MCP server (SQLite) for the case/queue store + audit log.
- Open-weights **local** model orchestration (Qwen2.5 via Ollama), fully offline.
- Sourced priorities with exact rule/vital citations.
- **Deterioration re-check flag** from serial vitals / patient-reported change.
- Named-approver **gate** on every irreversible action.
- Full **tool-call audit log** (inputs, outputs, timestamps, approver).
- **8+ evaluation cases** with pass/fail, run-to-run variation, and one honest unfixed failure.

### Out of scope (explicitly not built)
- **Paediatric triage** (SAT-TEWS child charts). The agent **detects paediatric input and safely
  abstains + escalates** rather than mis-scoring a child.
- Diagnosis, prescribing, or treatment advice of any kind.
- Multilingual input handling (architecture stays aware of it; English only for the build).
- Live hospital-system integration (real queue/EMR/PACS integration).
- Referral & department routing (stretch only if time allows).
- Any use of real patient data.

### Stretch (only if the MVP is done and frozen)
- C-1: Referral/department routing tool.
- C-2: "Additional investigations" column from the SATS chart.
- C-3: Frontier-model comparison on synthetic data (never required to run).

## 7. Success criteria

We succeed if a stranger can clone the repo, run one command, and watch the agent:

1. turn a synthetic case into a **cited** priority grounded in SATS;
2. **recover** from a missing or invalid vital instead of guessing;
3. **abstain safely** on paediatric / out-of-scope input;
4. **raise a second-look flag** when a patient deteriorates while waiting;
5. **refuse to write** a queue position until a named clinician approves;
6. produce a complete **audit log** and an **honest eval report** that includes a failure we did not fix.

Each maps to a judging criterion (see `REQUIREMENTS.md` → Judging criteria).

## 8. Constraints

| Constraint | Value | Consequence |
| --- | --- | --- |
| Team | **Solo** | Scope discipline is a scored skill; no parallel workstreams. |
| Window | **~6 days** (today Oct 9 → deadline Oct 15) | Aggressive front-loading; freeze early. |
| Compute | **Local CPU, ~6.9 GB total RAM, low headroom** | Use the installed **`qwen3.5:4b`**; Phase 1 measures RAM fit; smaller Qwen fallback otherwise. |
| Runtime | Python 3.12 (interpreter managed by `uv`) | Avoids wheel gaps on the host's Python 3.14. |
| Languages | English only | Keeps prompt/eval surface small. |
| Clinical access | **Not guaranteed** | Fit-to-desk validated from literature; gap declared honestly. |
| Data | Synthetic only | No egress, no consent problem. |
| **Engineering standards** | **DRY + SOLID (iron-clad)** | Violations block a phase; see `CONVENTIONS.md`. |

## 9. Data conduct

- We build on a **published triage scale** (SATS, EMSSA) and a **self-constructed synthetic patient
  stream**.
- We use **no real patient data**, consenting or otherwise.
- Synthetic is the **default, not the fallback**.
- Any borrowed MCP server and any model runs **locally**; synthetic patient records do not leave the
  machine.

## 10. Non-goals (values we protect)

- We will not ship a **chatbot wrapper** with no autonomous tool use.
- We will not ship an MCP server that **proxies a single endpoint**.
- We will not produce a priority level **without a source**.
- We will not present **untrue results**.
- We will not let a patient's **queue position move without human approval**.
