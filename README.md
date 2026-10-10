# TriageDesk

**Sourced, nurse-approved triage support for public-hospital OPD desks.**

> **Agentic AI for Africa Innovation Challenge** — Health & Wellbeing track
> Sub-theme: **Symptom-based priority scoring**
> Challenge brief: <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> Organisers: Nairobi AI Community / Qhala Trust

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status: frozen submission](https://img.shields.io/badge/status-v1.0--submission-blue.svg)](#project-status)

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

**Frozen submission (`v1.0-submission`).** The agent, MCP server, and evaluation harness are built and
run offline. This README states what works and what is unfinished; the **measured** results — including
a failure we did not fix — live in [`EVALS.md`](EVALS.md), generated from `evals/results/report.json`.

| Area | State |
| --- | --- |
| Problem framing & scope | ✅ Documented → [`docs/PROJECT.md`](docs/PROJECT.md) |
| Challenge compliance tracking | ✅ Documented → [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) |
| Architecture | ✅ Documented → [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| SATS domain model | ✅ Documented → [`docs/SATS.md`](docs/SATS.md) |
| Decisions log | ✅ Documented → [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Security & hardening | ✅ Documented → [`SECURITY.md`](SECURITY.md) |
| MCP server / agent / evals | ✅ Built & tested → [`tests/`](tests) |
| Evaluation (measured) | ✅ Run → [`EVALS.md`](EVALS.md) |
| Demo video | 🎬 Human-recorded → [`docs/DEMO.md`](docs/DEMO.md) |
| Status & gap analysis | 🟡 Honest self-assessment → [`STATUS.md`](STATUS.md) |

**What is unfinished.** The measured run records honest misses, not a green sweep: the declared failure
**E-09** (a vague complaint is under-triaged) is shown, not hidden, and the other misses are recorded in
[`EVALS.md`](EVALS.md) §4–§6. Clinician validation remains a declared gap ([`EVALS.md`](EVALS.md) §7).
[`EVALS.md`](EVALS.md) is the single source for every number. A full honest gap analysis — the one
submission gap (video upload), UX considerations, and state-of-the-art gaps — is in [`STATUS.md`](STATUS.md).

## Quickstart

From a clean clone, two commands:

```bash
uv sync --locked              # deterministic install from the committed uv.lock
uv run triagedesk demo        # the whole demo, offline, on the bundled synthetic fixture
```

The bare demo runs **offline by default** — it needs only `uv` and the locked dependencies (no model
pulled, no network, no borrowed server). To drive the local open-weights model instead of the offline
fixture, add `--online` (after `ollama pull qwen2.5:1.5b`). A single beat can be re-run with
`uv run triagedesk demo --beat <name>`. The full presenter runbook — every beat, command, and the real
expected output — is [`docs/DEMO.md`](docs/DEMO.md); it does not restate the demo here (DRY).

## Repository map

```
triagedesk/
├── README.md              this file
├── ARCHITECTURE.md        agent shape; MCP servers built vs borrowed; why
├── EVALS.md               measured evaluation, cases, and honest failure
├── DESCRIPTION.md         ~300-word challenge submission description
├── SECURITY.md            threat model & hardening
├── STATUS.md              honest self-assessment vs the challenge
├── LICENSE                Apache-2.0
├── NOTICE                 third-party attributions
├── AGENTS.md              agent tooling + the iron-clad DRY + SOLID rule
├── docs/
│   ├── PROJECT.md         vision, users, scope, success criteria
│   ├── REQUIREMENTS.md    challenge compliance & traceability matrix
│   ├── ROADMAP.md         submission packaging & freeze protocol
│   ├── DECISIONS.md       key decisions and rationale (ADR-lite)
│   ├── CONVENTIONS.md     DRY + SOLID engineering standard
│   ├── SATS.md            SATS domain model
│   ├── DEMO.md            demo runbook
│   └── assets/            architecture diagram, demo tape + video
├── data/                  SATS rules (the single source of thresholds)
├── evals/                 case fixtures + the measured report.json
├── src/triagedesk/        core · graph · mcp · store · llm · evals · demo
└── tests/                 the offline proof suite (pytest)
```

## Traceability

Every challenge requirement, judging criterion, and instant-disqualifier is tracked in
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) with an owning artifact and a status.

## Language

Submission and interaction are in **English**. The architecture is kept
multilingual-*aware* but multilingual handling is **out of scope** for this build (see
[`docs/PROJECT.md`](docs/PROJECT.md) → Non-goals).

## Data & safety

TriageDesk is built on **synthetic patient data** and a **published triage scale** (SATS). No real
patient data is used, at any point, in any form. See [`docs/PROJECT.md`](docs/PROJECT.md) → Data conduct and
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) → DC-1…DC-4.

## License

Apache-2.0 — see [`LICENSE`](LICENSE). OSI-approved.
