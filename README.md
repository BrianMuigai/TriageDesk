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

## Target users

TriageDesk serves the front line of a busy public-hospital OPD:

- **Triage nurse (primary user)** — enters vitals and a presenting complaint, receives a sourced
  priority, and confirms or overrides it.
- **Named clinician / SHCP (approver)** — the named senior professional whose approval releases a case
  card to the queue.
- **Patient (beneficiary)** — receives faster, better-sequenced care, and is never acted on by the
  agent alone.

Setting: a district or regional public-hospital OPD — one or two nurses, paper case cards, and basic
equipment (a blood-pressure cuff, a thermometer, a pulse oximeter). See [`docs/PROJECT.md`](docs/PROJECT.md) §3.

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
| Demo video | 🎬 Recorded (2:28) — awaiting public upload → [`docs/DEMO.md`](docs/DEMO.md) |
| Status & gap analysis | 🟡 Honest self-assessment → [`STATUS.md`](STATUS.md) |

**What is unfinished.** The measured run records honest misses, not a green sweep: the declared failure
**E-09** (a vague complaint's discriminator is not retrieved — deferred, not under-triaged) is shown, not
hidden, and the other misses are recorded in
[`EVALS.md`](EVALS.md) §4–§6. **No** triage nurse/clinician review was obtained as of 2026-10-13, so the
fit-to-desk claim is scoped to what was built and measured; if a review is arranged, an attributed quote
(name/role/date, with consent) will be added to [`EVALS.md`](EVALS.md) §7 — nothing is claimed until it
is. The demo video is **recorded** (`docs/assets/triagedesk-demo.mp4`, a 2:28 screen recording of the
shipped CLI with the tool calls on screen) but **not yet uploaded** — the one submission blocker
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

## Architecture

A **deterministic SATS scorer** inside an **explicit LangGraph plan** on a **local open-weights
model**, gated by **human approval before anything reaches a queue**. The LLM handles language; **no
number comes from the model**, so a priority is defensible under audit. The full shape, agent graph,
MCP servers and data flow are in [`ARCHITECTURE.md`](ARCHITECTURE.md); the diagram is
[`docs/assets/architecture.pdf`](docs/assets/architecture.pdf).

## Agent architecture

An explicit LangGraph plan — `ingest → normalize → retrieve → score → ground → verify → recheck →
assess → approval_gate → commit → handover`, with `request_missing_info` and `escalate` terminals. The
model is used only to structure language; the colour is computed deterministically from `data/*.yaml`.
Node table and edges: [`ARCHITECTURE.md`](ARCHITECTURE.md) §3.

## MCP implementation

TriageDesk implements MCP on **both sides**: it authors one server and consumes another, reached
through a single client adapter (`langchain.mcp`) over **stdio**. The graph depends on the **tool
interface**, not a concrete adapter (SOLID: dependency inversion), so the borrowed server can be
swapped in one module. Rationale: [`docs/DECISIONS.md`](docs/DECISIONS.md) D5, D13.

## MCP tools & servers

**Owned `triage` server — 7 tools.** Read-only: `normalize_case`, `match_discriminators`,
`retrieve_evidence`, `assess_confidence`. Acting: `score_priority`, `raise_recheck_flag`.
Acting and gated: `commit_priority`. Three of the seven act, and **only `commit_priority` mutates the
queue** — it refuses to run without a valid approval token.

**Borrowed server.** A maintained SQLite MCP server (`mcp-sqlite@1.0.9`) for persistence — *"persistence,
schema and query safety are solved; a hand-rolled DB adds zero triage value"* — its read paths are
exercised behind the unchanged `Store` protocol. Full tool contracts: [`ARCHITECTURE.md`](ARCHITECTURE.md) §4.

## Human-in-the-loop workflow

Every irreversible action is gated. A LangGraph `interrupt()` pauses at the **approval gate** and
presents the suggested priority with its citations; a **named clinician approves, edits, or dismisses**.
An edit supersedes the queue row in place; a dismiss commits nothing. `commit_priority` refuses to run
without a well-formed, named token, and a deterioration re-check raises a **second look** without
reordering the queue. See [`ARCHITECTURE.md`](ARCHITECTURE.md) §5 and the desk surface in
[`docs/DESK.md`](docs/DESK.md).

## Technology stack

| Layer | Choice |
| --- | --- |
| Runtime | Python 3.12, managed by `uv` (committed `uv.lock`) |
| Orchestration | **LangGraph** (explicit graph; `interrupt()` gate) |
| MCP | Owned server on the **MCP SDK v2**; borrowed **`mcp-sqlite@1.0.9`** |
| MCP client | `langchain.mcp` adapter (stdio) |
| Model | **Qwen2.5 1.5B** via **Ollama** (open weights, offline); `qwen3.5:4b` fallback |
| Schemas | **Pydantic** (one schema module) |
| Storage | SQLite (domain + audit) and `checkpoints.db` (runtime state) |
| Quality | `pytest`, `ruff`, `mypy` |

Rationale for every choice: [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Limitations

Honest, measured limitations — not aspirational claims:

- **No triage nurse/clinician review obtained.** The fit-to-desk claim is scoped to what is built and
  measured; expected colours derive from the published SATS rules ([`EVALS.md`](EVALS.md) §7).
- **Deferral over-covers benign complaints.** When a complaint matches no discriminator the case defers
  rather than scoring on vitals alone; the measured deferral rate is published in [`EVALS.md`](EVALS.md) §3.
- **Extraction latency is not "seconds".** The deterministic score is instant; the local model's
  extraction dominates (latency in [`EVALS.md`](EVALS.md) §3).
- **The desk surface is a prototype** — loopback, single-machine, English-only, with no hospital-system
  integration ([`docs/DESK.md`](docs/DESK.md)).
- **Approver identity is recorded, not authenticated** ([`SECURITY.md`](SECURITY.md) §6).
- **English-only and synthetic-data-only** by design.
- Two cases remain recorded, unfixed evaluation failures ([`EVALS.md`](EVALS.md) §6).

The full ranked gap analysis is [`STATUS.md`](STATUS.md).

## Future improvements

From [`STATUS.md`](STATUS.md) §7:

- **Calibrated confidence** — a true selective-prediction probability beyond today's deterministic
  coverage signal.
- **Model routing / caching / budgets** to attack the extraction latency.
- **Online evaluation + drift monitoring.**
- **Multimodal intake** (voice + cuff/chart photo) — the real desk UX.
- **Vitals-entry ergonomics** (numeric keypad, units, missing-vital prompting).
- **Approver authentication** (identity is recorded today, not authenticated).
- **MCP sampling / elicitation** — the current spec's agent↔server negotiation.

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
│   └── assets/            architecture diagram, demo video + render script
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
