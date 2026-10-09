# TriageDesk

**Sourced, nurse-approved triage support for public-hospital OPD desks.**

> **Agentic AI for Africa Innovation Challenge** — Health & Wellbeing track
> Sub-theme: **Symptom-based priority scoring**
> Challenge brief: <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> Organisers: Nairobi AI Community / Qhala Trust

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status: pre-build](https://img.shields.io/badge/status-pre--build-orange.svg)](#project-status)

---

## What it is

TriageDesk turns the two things a triage nurse already has in front of her — a set of **vitals** and a
**presenting complaint** — into a **sourced priority level in seconds**, grounded in the
**South African Triage Scale (SATS)**.

It does **not** diagnose, does **not** prescribe, and does **not** move a patient. It scores and
sequences the queue; a named nurse or clinician confirms every priority before a case card reaches a
queue position. If a patient's condition changes while they wait, TriageDesk can raise the patient for
a **second look** — it cannot act on it.

Every priority carries the exact vital sign or symptom entry that produced it. There is no such thing
as an unsourced urgency flag in this system.

## Why it exists

In busy public outpatient departments (OPDs) across Africa, the queue does not start at the doctor's
door — it starts at triage. One or two nurses, a blood-pressure cuff, a thermometer, a pulse oximeter,
and a stack of case cards work through everyone who walks in before anyone is assigned a priority. On
a busy morning that single desk is the bottleneck for the whole department: a patient with a genuinely
urgent condition can sit in the same queue as a routine follow-up, because nothing at that desk tells
the nurse to look twice until she physically reaches that card.

- **60–90 min** — typical wait before a patient is even seen at the triage desk in a busy public OPD.
- **Seconds** — what the agent should take to turn vitals + complaint into a *cited* priority level.
- **Nurse decides** — the agent stops here and hands over a sourced priority, not a diagnosis.

## The one non-negotiable rule

> TriageDesk **scores or sequences** the queue. It **never diagnoses**, **never prescribes**, and
> **never decides who gets seen**. A triage nurse or clinician confirms every priority level before a
> patient is sent to a bay. Every priority level must cite the vitals or symptom entry behind it.

This boundary is enforced in code (see `ARCHITECTURE.md`), not just in policy: the write that places a
case card in the queue is gated behind a named human approver.

## Project status

**Pre-build.** This repository currently contains the design and compliance documentation required
*before* implementation begins. Nothing here claims a working agent yet. The status section of this
README will be updated with measured results as the build lands — including what is unfinished.

| Area | State |
| --- | --- |
| Problem framing & scope | ✅ Documented → [`PROJECT.md`](PROJECT.md) |
| Challenge compliance tracking | ✅ Documented → [`REQUIREMENTS.md`](REQUIREMENTS.md) |
| Architecture | ✅ Documented → [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Evaluation plan | ✅ Documented → [`EVALS.md`](EVALS.md) |
| SATS domain model | ✅ Documented → [`docs/SATS.md`](docs/SATS.md) |
| Decisions log | ✅ Documented → [`DECISIONS.md`](DECISIONS.md) |
| Build plan | ✅ Documented → [`ROADMAP.md`](ROADMAP.md) |
| Security & hardening | ✅ Documented → [`SECURITY.md`](SECURITY.md) |
| MCP server / agent / evals | ⛔ Not built yet |
| Demo video | ⛔ Not recorded yet |

## Quickstart

> **Planned one-command run.** Not functional until implementation lands.

```bash
# Prerequisites: Python 3.12+, uv, ollama
uv run triagedesk demo        # pulls the local model, runs the graph, streams tool calls
```

For a stranger to run this end to end they will need: a machine able to run a small open-weights
model locally (see `DECISIONS.md` → D3 for the RAM sizing note), and Ollama. A fully offline
`synthetic` fixture ships in-repo so no external data or network is required.

Expected shape of the output:

```
[case 0417] ingest ......... ok
[case 0417] normalize ...... RR=24 HR=118 SBP=108 T=38.9 AVPU=A complaint="cough, fast breathing"
[case 0417] match_discriminators ... "shortness of breath - acute" (VERY URGENT)
[case 0417] score_priority .. TEWS=6  -> ORANGE   (<10 min)
             source: RR 24 -> TEWS +2 (21-29); HR 118 -> TEWS +2 (111-129); T 38.9 -> TEWS +2 (>38.4)
[case 0417] raise_recheck_flag ... n/a
[case 0417] commit_priority . BLOCKED — awaiting named clinician approval
```

## Repository map (target)

```
triagedesk/
├── README.md              this file
├── PROJECT.md             vision, users, scope, success criteria
├── REQUIREMENTS.md        challenge compliance & traceability matrix
├── ARCHITECTURE.md        agent shape; MCP servers built vs borrowed; why
├── EVALS.md               evaluation plan, cases, and honest failure
├── DECISIONS.md           key decisions and rationale (ADR-lite)
├── ROADMAP.md             6-day build plan and risks
├── DESCRIPTION.md         ~300-word challenge submission description
├── SECURITY.md            threat model & hardening
├── LICENSE                Apache-2.0
├── docs/
│   └── SATS.md            South African Triage Scale domain model
└── (source tree — added during build)
```

## Traceability

Every challenge requirement, judging criterion, and instant-disqualifier is tracked in
[`REQUIREMENTS.md`](REQUIREMENTS.md) with an owning artifact and a status.

## Language

Submission and interaction are in **English**. The architecture is kept
multilingual-*aware* but multilingual handling is **out of scope** for this build (see
[`PROJECT.md`](PROJECT.md) → Non-goals).

## Data & safety

TriageDesk is built on **synthetic patient data** and a **published triage scale** (SATS). No real
patient data is used, at any point, in any form. See [`PROJECT.md`](PROJECT.md) → Data conduct and
[`REQUIREMENTS.md`](REQUIREMENTS.md) → DC-1…DC-4.

## License

Apache-2.0 — see [`LICENSE`](LICENSE). OSI-approved.
