# DEMO — TriageDesk submission video runbook

> **The recording is a HUMAN action.** The 2–3 minute video is an **unedited screen recording**
> (`2–3 min`) — **tool calls on screen, no slides** — uploaded publicly to YouTube or Vimeo. This
> document is the runbook a person follows to record it; the agent does **not** record the video.
>
> **`human_needed` — the public upload.** The recording **and** the public upload are **HUMAN** actions.
> The upload is the **one submission blocker** (`STATUS.md` G1, `docs/REQUIREMENTS.md` G-9); this runbook
> prepares the script and never claims a video is recorded or hosted. A local recording exists
> (`docs/assets/triagedesk-demo.mp4`) but is **not yet uploaded**; paste the public URL into the
> submission form once it is.
>
> **Record against the v1.1 state (this commit), not the frozen `v1.0-submission` tag.** The
> Durable-mode and desk sections below document v1.1-only behaviour — `--durable`/`resume`/`replay`,
> `desk`, and the `no_match` **deferral** — none of which exists at `v1.0-submission`, whose CLI
> exposes only `eval` and `demo`. The frozen tag remains the reference for the **freeze protocol**
> ([`ROADMAP.md`](ROADMAP.md) §Freeze), not for this runbook's commands. The canonical storyboard is
> the table in [`ROADMAP.md`](ROADMAP.md) → *Demo storyboard*; this runbook maps those timing bands to
> exact commands and expected output and does **not** restate the storyboard (DRY — it links to the
> single source).

## One-time setup (from a clean clone)

```bash
# 1. Deterministic install (no network surprises; uses the committed uv.lock).
uv sync --locked

# 2. Offline is the DEFAULT — the bare demo needs no model pulled. Only if you record the
#    real-model path (`--online`) do you additionally pull the small local model:
ollama pull qwen2.5:1.5b
```

The offline path needs only `uv`; it launches **no model and no borrowed server** and reaches for **no
credentials or network**. Everything it prints is synthetic (D-01).

## The one-command path

```bash
# Full sequence, one command, offline (the exact path CI runs):
uv run triagedesk demo

# A single beat by name (repeatable) — for re-recording one beat or pausing between beats:
uv run triagedesk demo --beat routine
uv run triagedesk demo --beat escalation
uv run triagedesk demo --beat deterioration
uv run triagedesk demo --beat refusal
uv run triagedesk demo --beat failure
```

The bare command runs all five beats in order, prints every owned tool call, and pauses at the
approval gate. `--beat <name>` runs just that beat; the beat names are exactly those
`uv run triagedesk demo --list` prints. Add `--online` only to drive the pulled local model instead of
the offline golden fixture.

## The measured eval on screen (not a live run)

The committed report is `mode: real`, takes **~10 minutes** (3 runs × 16 cases ≈ 13 s/case on local CPU)
and the harness is **silent** — `uv run triagedesk eval …` writes `evals/results/report.json` and prints
nothing. A 2–3 minute recording therefore **cannot** stream the real eval run. The honest on-screen
artefact is the committed [`EVALS.md`](../EVALS.md) projection (generated from `report.json`) plus the
live `failure` beat:

```bash
# Open the committed measured projection, then run the live declared-failure beat:
uv run triagedesk demo --beat failure
```

The `failure` beat prints `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)` on screen — the
declared-versus-measured mismatch, shown rather than hidden. Narrate it plainly: the committed projection
**is** the measured artefact, and the real ~10-minute run is **not** streamed.

## Durable mode (two-command durability story)

The bare one-command path above is unchanged and hermetic — it runs the in-memory saver and needs no
file state and no model. Durable mode is the OPT-IN path that makes the headline property demonstrable:
a case paused at the approval gate survives a process restart. It runs exactly **one** beat to the gate
over `checkpoints.db`, prints the content-derived `thread_id` and the exact `resume` command, then
**exits without resuming** — a single in-process pause would prove nothing about persistence.

```bash
# 1. Run one case to the approval gate over the durable saver; note the printed thread_id.
uv run triagedesk demo --durable --beat escalation
```

On screen — `[durable] thread_id=` is the **only** line carrying that marker, and the `thread_id` is a
hash of the note, so a reviewer can recompute it by hand and it is the same id from any entry point:

```text
[durable] thread_id=<content-id> paused at approval gate
[durable] resume: uv run triagedesk resume --thread-id <content-id> --decision approve --approver NAME --role ROLE --db checkpoints.db
```

```bash
# 2. In a FRESH process, resume the SAME thread through the gate to a committed handover:
uv run triagedesk resume --thread-id <content-id> --decision approve --approver "Nurse Demo" --role "triage nurse"
```

`resume` prints the gate's outcome — the committed row, or the gate's own refusal reason — so an
operator can tell a commit from a refusal. The gate refuses a dismissal and writes no queue row (the
durable analogue of the refusal beat). Dismiss a **pending** thread (a fresh pause on a throwaway
checkpoint file, so the refusal is shown rather than a completed case):

```bash
uv run triagedesk demo --durable --beat escalation --db /tmp/durable-dismiss.db
uv run triagedesk resume --thread-id <content-id> --decision dismiss --db /tmp/durable-dismiss.db
```

The second command prints `clinician dismissed the priority; refusing to commit` — the gate's own
reason — and writes no queue row. A `dismiss` is a legitimate refusal and exits `0`; an `approve` or
`edit` the gate refuses exits non-zero, so a refusal is never mistaken for a commit.

`resume --decision approve|edit` needs `--approver` and `--role` (the gate refuses a fabricated
identity); a `dismiss` needs neither. Resuming a thread that has no pending gate exits non-zero naming
the thread id.

`--durable` resolves the real store seam, so it **may launch the borrowed `npx mcp-sqlite`** server
(`triage.db`) the first time a write lands; the default demo never does. The checkpoint file is
`checkpoints.db` (override with `--db`). A durable thread already exists for a case once it has paused,
so **removing `checkpoints.db` replays the story** from a clean checkpoint.

## Beat-by-beat runbook

Each storyboard timing band maps to the beat(s) it plays and the command to run for that band. Every
command is exercised against the shipped CLI by [`tests/test_demo_runbook.py`](../tests/test_demo_runbook.py),
so the runbook cannot drift from what a presenter will actually run (T-05-06).

| Time | Beat(s) | Command | Expected on screen |
| --- | --- | --- | --- |
| 0:00–0:15 | — (narration) | *(no command)* | The desk problem: 60–90 min wait; unsourced flags are dangerous. |
| 0:15–0:50 | `routine` | `uv run triagedesk demo --beat routine` | GREEN routine scores, then **defers** — no commit (nothing reaches the queue unapproved). |
| 0:50–1:20 | `escalation` | `uv run triagedesk demo --beat escalation` | ORANGE escalation **commits at queue position 1** — after the named nurse approves. |
| 1:20–1:45 | `deterioration` | `uv run triagedesk demo --beat deterioration` | A waiting patient flagged for a **second look** (`raise_recheck_flag`); the case defers. |
| 1:45–2:10 | `refusal` | `uv run triagedesk demo --beat refusal` | The **approval gate refusing** to commit without the named nurse. |
| 2:10–2:40 | `failure` + the measured eval | open [`EVALS.md`](../EVALS.md), then `uv run triagedesk demo --beat failure` | The committed **measured** eval on screen, then the live **E-09 failure** (`DECLARED: ORANGE` / `MEASURED: GREEN`). |
| 2:40–2:50 | — (narration) | *(no command)* | Close: open source, offline, synthetic. |

## Expected on-screen output per beat

Every line below is transcribed from the shipped runner (`uv run triagedesk demo`, offline) — it is not
a hand-written mock. Tool calls print as `[tool] <name> <inputs> -> <outputs>`; each beat closes with a
`--- outcome ---` block carrying the **sourced priority** — colour, target, the matched discriminator
ids, and the citation(s) behind the colour. Case ids are content-derived, so they are stable per case.
The run shows **seven owned tools** — `normalize_case`, `match_discriminators`, `score_priority`,
`retrieve_evidence`, `assess_confidence`, `raise_recheck_flag`, `commit_priority` — and only the
`escalation` beat commits a queue row (at position 1).

**`routine` (E-01 → GREEN, then deferred).** Five tool calls — `normalize_case`,
`match_discriminators`, `score_priority`, `retrieve_evidence`, `assess_confidence` (no commit) — then:

> **Narration cue:** "Watch the routine case score GREEN and then DEFER — no commit, because nothing
> reaches the queue unapproved."

```
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
```

The `no_match` complaint (`sore throat` matches no discriminator) routes the case to a safe terminal, so
there is **no `commit` line** — nothing reached the queue.

**`escalation` (E-02 → ORANGE, committed under the named nurse).** Six tool calls — the five above plus
`commit_priority` — and three citations:

> **Narration cue:** "Watch an ORANGE escalation commit at queue position 1 — only after a named
> approver says yes."

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  matched ids  : ['acute_shortness_of_breath']
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — heart_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — temperature band
  commit       : committed case 9300336d37c3651c at queue position 1 (ORANGE)
  handover card: {"case_id":"9300336d37c3651c","colour":"ORANGE","target":"< 10 min", ...}
```

**`deterioration` (E-07 → second look, then deferred).** Six tool calls — the five above plus
`raise_recheck_flag` — which flags the serial-vitals change **without re-classifying** the patient:

> **Narration cue:** "Watch the second look raise a recheck flag — the case defers rather than
> committing a stale colour."

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — heart_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — systolic_bp band
  second look  : {"flag":true,"deteriorations":["respiratory_rate","heart_rate","systolic_bp"], ...}
```

The `second look` line is the only queue-facing output — the case **defers** rather than committing a
stale colour, so there is **no `commit` line**.

**`refusal` (the climax).** The same E-02 priority is scored, but the gate is resumed with a `dismiss`
naming **no approver**, so the gated commit refuses and writes nothing — the refusal is read from the
real store row delta, not asserted:

> **Narration cue:** "Watch a dismiss attempt — the agent refuses to commit and says why, in its own
> words."

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  matched ids  : ['acute_shortness_of_breath']
  commit       : clinician dismissed the priority; refusing to commit
  GATE REFUSED : no queue row written (rows added this beat: 0)
  handover card: {"case_id":"9300336d37c3651c","colour":"ORANGE","target":"< 10 min", ...}
```

**`failure` (E-09, the declared failure — shown, not hidden).** The vague complaint *"feeling unwell"*
matches no discriminator, so the score falls back to vitals alone. The beat prints the declared vs the
measured outcome on screen:

> **Narration cue:** "Watch the honest failure — the declared ORANGE meets a measured GREEN, shown
> rather than hidden."

```
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — all recorded parameters within normal SATS bands
  DECLARED     : ORANGE
  MEASURED     : GREEN (SHOWN MISMATCH)
```

Narrate the failure while it is on screen: the vague complaint's discriminator is **not retrieved** — a
deferral, not a delivered under-triage. The printed colour is the residual vitals-only result shown
*before* the deferral routes the case to a safe terminal (`escalate`/`request_missing_info`); the demo
does not hide the miss.

## The desk surface (browser screen recording)

`docs/assets/desk-demo.mp4` is a **silent browser screen recording of the local desk surface** (the v1.1
`desk` bridge — not the terminal). It is **supplementary**: it shows the desk UX end to end (happy path
+ edge cases) so a reviewer can see the surface without running it. It is **not** the narrated 2–3
minute submission video — that remains the terminal recording above
(`docs/assets/triagedesk-demo.mp4`), which carries the measured eval and the declared failure. The "the
agent does not record the video" rule at the top of this document applies to *that* video; this capture
is a separate, clearly-labelled artefact.

Run the surface it records (offline, local, CPU-only — no egress):

```bash
uv run triagedesk desk --port 8765 --db /tmp/desk-demo.db
```

Then open `http://127.0.0.1:8765/`. Nothing here is a new project dependency: the surface is the shipped
stdlib bridge, and the capture used Playwright only as **dev-only** tooling — it is never added to
`pyproject.toml` and no runtime path imports it.

**What the recording covers** — the happy path, then five edge cases. Every gate beat is a **distinct
case**: the thread id is content-addressed, so re-submitting the *same* case resumes the paused thread
instead of rendering a fresh gate.

| Beat | Case | What is on screen |
| --- | --- | --- |
| Happy path | E-04 (emergency discriminator) | The **suggested** priority card — RED, target time, every "why" vital **next to its citation**, then the SATS evidence — then the real gate; a named nurse **approves** → `Approved by Nurse A. Demo (triage nurse) — committed to the queue`. |
| Edge — edit | E-10 | The nurse overrides the colour → `Edited to ORANGE by Nurse A. Demo … committed to the queue`; the row is superseded, not duplicated. |
| Edge — dismiss | E-02 | `Dismissed — nothing has been committed`. There is no default approve. |
| Edge — recovery | E-05 | A scored vital is missing → `A scored vital is missing. Re-measure before scoring.` **No gate**. |
| Edge — deferred | E-09 | No discriminator matched → the loud banner + a **read-only** card (`Not confirmed and not queued`). **No gate**. |
| Edge — escalation | E-06 | An out-of-scope (paediatric) case → `escalated for human review — no priority was committed`. **No gate**. |

The recording is **captioned on screen** (it has no audio track). Duration 2:48.

> **Note — a defect this recording surfaced.** Driving the real page (not the request-level tests, which
> POST directly) exposed that the gate's `submit` handler disabled **the submitting button** before the
> form data set was built. A disabled submit button is not a successful control, so its
> `name=decision value=approve|edit|dismiss` was dropped and the server refused **every** decision
> (`unknown decision ''`) — the gate was unusable through its own UI. It is fixed in
> `src/triagedesk/desk/static/index.html` (disable only the *siblings*, block a second decision with a
> flag) and guarded by
> `tests/test_desk.py::test_the_gate_script_keeps_the_submitting_button_enabled`.

## What is unfinished

The video must be as honest as the docs. Point the close at what the repository itself declares:

- [`EVALS.md`](../EVALS.md) §6 — **E-09**, the failure we did not fix (free-text discriminator
  selection); plus the other honest misses recorded in the measured report. Do not restate the numbers
  here — `EVALS.md` is generated from `evals/results/report.json` and is the single source.
- [`README.md`](../README.md) — the honest "what is unfinished" statement and the one-command
  quickstart.
- Clinician validation remains a **declared gap** (`EVALS.md` §7): the expected colours come from the
  published SATS rules, not clinician adjudication. **No** triage nurse/clinician review was obtained as
  of 2026-10-13.
- The video is recorded but **not yet uploaded** — the one submission blocker (see the `human_needed`
  note above).

Record the close over the running terminal, not over slides: open source, offline, synthetic.
