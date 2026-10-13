# TriageDesk

**Sourced, nurse-approved triage support for public-hospital OPD desks.**

> **Agentic AI for Africa Innovation Challenge** — Health & Wellbeing track
> Sub-theme: **Symptom-based priority scoring**
> Challenge brief: <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> Organisers: Nairobi AI Community / Qhala Trust

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status: v1.1 milestone close](https://img.shields.io/badge/status-v1.1--milestone-close-blue.svg)](#project-status)

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

**v1.1 milestone close (additive).** The v1.1 line adds durable approve/resume over `checkpoints.db`, a
`no_match` deferral banner with audit-trail retrieval grounding, and a loopback desk surface
([`docs/DESK.md`](docs/DESK.md)). It extends the frozen v1.0 build at published seams and changes no
v1.0 behaviour.

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
**E-09** (a vague complaint's discriminator is not retrieved — deferred, not under-triaged) is shown, not
hidden, and the other misses are recorded in
[`EVALS.md`](EVALS.md) §4–§6. **No** triage nurse/clinician review was obtained as of 2026-10-13, so the
fit-to-desk claim is scoped to what was built and measured; if a review is arranged, an attributed quote
(name/role/date, with consent) will be added to [`EVALS.md`](EVALS.md) §7 — nothing is claimed until it
is. The demo video is **recorded but not yet uploaded** — the one submission blocker
([`docs/DEMO.md`](docs/DEMO.md)). [`EVALS.md`](EVALS.md) is the single source for every number. A full
honest gap analysis — the video upload, UX considerations, and state-of-the-art gaps — is in
[`STATUS.md`](STATUS.md).

## Quickstart

From a clean clone, one command:

```bash
# The whole demo, offline, on the bundled synthetic fixture. `uv run` syncs the locked
# environment from the committed uv.lock before it runs — there is no separate install step.
uv run triagedesk demo

# The optional second command: serve the local desk surface (loopback only, no external request).
uv run triagedesk desk
```

The bare demo runs **offline by default** — it needs only `uv` and the locked dependencies (no model
pulled, no network, no borrowed server). How to drive it in full — the storyboard beats and the desk
surface — is in [Running the demos](#running-the-demos) below. Prefer plain `pip`? Pinned
`requirements.txt` (runtime) and `requirements-dev.txt` (dev tools) are generated from `uv.lock`.

## Running the demos

Those two commands are the whole surface. The full presenter scripts are
[`docs/DEMO.md`](docs/DEMO.md) (storyboard) and [`docs/DESK.md`](docs/DESK.md) (desk); this section
shows how to drive them and does not restate them (DRY).

### The storyboard demo

```bash
# The whole demo, offline, on the bundled synthetic fixture (the default).
uv run triagedesk demo

# Drive the local open-weights model instead of the offline fixture
# (after `ollama pull qwen2.5:1.5b`).
uv run triagedesk demo --online

# Re-run a single beat by name; repeat the flag to compose a shorter run.
uv run triagedesk demo --beat <name>

# Run ONE beat to the durable approval gate, print its thread id, and stop.
uv run triagedesk demo --durable
```

To list the beat names, use `uv run triagedesk demo --list`. The `--durable` flag pauses ONE beat at
the gate, prints its content-derived thread id, and exits **without** resuming; its printed follow-up
is `uv run triagedesk resume --thread-id <id> --decision approve --approver <name> --role <role>` —
add `--db <file>` only if the checkpoint was moved.

### The desk surface

```bash
# Serve the local desk surface (loopback only, no external request).
uv run triagedesk desk
```

Open **<http://127.0.0.1:8765>** in a browser and stop the server with **Ctrl-C**. The surface binds
loopback only and makes no external request. The recorded walkthrough is
[`docs/assets/desk-demo.mp4`](docs/assets/desk-demo.mp4); the nurse-facing quickstart is
[`docs/DESK.md`](docs/DESK.md).

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
├── requirements.txt       pinned runtime deps (generated from uv.lock)
├── requirements-dev.txt   pinned dev tools (generated from uv.lock)
├── AGENTS.md              agent tooling + the iron-clad DRY + SOLID rule
├── docs/
│   ├── PROJECT.md         vision, users, scope, success criteria
│   ├── REQUIREMENTS.md    challenge compliance & traceability matrix
│   ├── ROADMAP.md         submission packaging & freeze protocol
│   ├── DECISIONS.md       key decisions and rationale (ADR-lite)
│   ├── CONVENTIONS.md     DRY + SOLID engineering standard
│   ├── SATS.md            SATS domain model
│   ├── DEMO.md            demo runbook
│   ├── DESK.md            loopback desk-surface quickstart
│   ├── REVIEW.md          live-review (Stage 2) rehearsal runbook
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
