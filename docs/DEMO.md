# DEMO — TriageDesk submission video runbook

> **One unedited screen recording, tool calls on screen, no slides.** The submission video is a real
> screen recording of the shipped CLI — every line is what `uv run triagedesk demo` prints. The
> repository file (`docs/assets/triagedesk-demo.mp4`) is a **2:29** re-recording (2026-11-15) on the
> local model `qwen2.5:1.5b`: the online `escalation` beat and the online `clarify` beat with **live MCP
> elicitation** (the agent stops inside `request_clarification`; the answer is typed at the real
> `[nurse] q1>` prompt), then the `refusal` beat and the declared E-09 `failure` on the offline golden
> fixture — each run's mode line says which — and the measured evaluation. The calls of **8** distinct
> owned tools are on screen. It is reproducible from the repository (see *Rendering the video* below).
>
> **Upload status.** The earlier **2:28 v1.0 recording** was uploaded to Google Drive during submission
> ([folder](https://drive.google.com/drive/folders/1s1sgXHJjr6XsGr-ggTlyY6BT3FSG9ZJ3)). The 2:29
> re-recording is **not yet uploaded**. The brief names YouTube or Vimeo, so hosting the re-recording
> there remains the platform step (`STATUS.md` G1, `docs/REQUIREMENTS.md` G-9) — and the Drive folder
> should be confirmed viewable by anyone with the link. This runbook documents the recording script.
>
> **Record against the current state (this commit), not the frozen `v1.0-submission` tag.** The
> Durable-mode and desk sections below document v1.1+ behaviour — `--durable`/`resume`/`replay`,
> `desk`, and v1.2's three-way coverage (delivered / clarified / deferred) — none of which exists at
> `v1.0-submission`, whose CLI exposes only `eval` and `demo`. **The 2:28 v1.0 recording uploaded to
> Google Drive predates v1.2**: it shows the earlier `no_match` deferral on the routine and
> deterioration beats (the 2:29 re-recording plays neither). The beats
> below are transcribed from the shipped v1.2 runner; where they differ from the recording, the text
> says so explicitly. The frozen tag remains the reference for the **freeze protocol**
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
uv run triagedesk demo --online --beat clarify   # live: the agent asks the nurse (see below)
```

The bare command runs all six beats in order, prints every owned tool call, and pauses at the
approval gate. Offline, the `clarify` beat shows the same E-09 terminal as `failure`, because the
deterministic planner never asks — the question appears only `--online` (see
[*Live final: the agent asks the nurse*](#live-final-the-agent-asks-the-nurse-online-clarify-beat)). `--beat <name>` runs just that beat; the beat names are exactly those
`uv run triagedesk demo --list` prints. Add `--online` only to drive the pulled local model instead of
the offline golden fixture. Every run opens with ONE mode line, so the screen says which path is live:
offline prints `mode: offline — golden fixture (no model)`, online prints
`mode: online — local model <tag> via Ollama` with the tag the model client actually uses.

## The measured eval on screen (not a live run)

The committed report is `mode: real`, takes **~20 minutes** (3 runs × 24 cases ≈ 18 s/case on local CPU)
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

## Rendering the video (reproducible)

The submission video is rendered from the shipped CLI by one script — no slides, no hand-edited output:

```bash
# record (real pty -> asciicast) -> agg (-> mp4) -> ffmpeg (caption band) -> duration guard
bash docs/render-demo.sh
```

- [`scripts/record_demo.py`](../scripts/record_demo.py) drives a real `bash` over a pty, types each
  `--beat` command, and captures the real output with real timings. The `escalation` and `clarify` beats
  run **online on the real local model** (Ollama up, model warm — timings vary run to run); the recorder
  waits for each run to return to the prompt, and in `clarify` types the nurse's answer only at the real
  `[nurse] q1>` prompt (Enter at each further prompt; never `--answer`) — a run in which the model asks
  nothing aborts the recording.
- It writes the asciicast **and** the caption track, timing each narration line from where the output it
  narrates appears — and refusing to burn one without it: a missing marker or mode line, a traceback or
  warning on screen, or a run that does not return in time aborts before any video is rendered. The beat
  **names** come from the ONE manifest, `demo/storyboard.yaml`; the projection caption's figures are
  computed from `evals/results/report.json`.
- `agg` renders the cast to mp4 and **never compresses idle time** (its idle limit is the duration
  limit); `ffmpeg` pads a caption band and burns `docs/assets/demo-captions.ass`.
- The script fails if the result is **≥ 3 min**.

It needs `agg` on `PATH` (`cargo install --git https://github.com/asciinema/agg`) plus `ffmpeg` and the
project's own `uv`. The narration lives in exactly one place — the caption track the recorder writes.

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
| 0:15–0:50 | `routine` | `uv run triagedesk demo --beat routine` | GREEN routine scores and, since v1.2, **delivers on its recorded vitals** — committed at position 1 after the named approval. |
| 0:50–1:20 | `escalation` | `uv run triagedesk demo --beat escalation` | ORANGE escalation **commits at queue position 1** — after the named nurse approves. |
| 1:20–1:45 | `deterioration` | `uv run triagedesk demo --beat deterioration` | A waiting patient flagged for a **second look** (`raise_recheck_flag`); since v1.2 the colour is delivered with the flag. |
| 1:45–2:10 | `refusal` | `uv run triagedesk demo --beat refusal` | The **approval gate refusing** to commit without the named nurse. |
| 2:10–2:40 | `failure` + the measured eval | open [`EVALS.md`](../EVALS.md), then `uv run triagedesk demo --beat failure` | The committed **measured** eval on screen, then the live **E-09 failure** (`DECLARED: ORANGE` / `MEASURED: GREEN`). |
| 2:40–2:50 | — (narration) | *(no command)* | Close: open source, offline, synthetic. |

## Expected on-screen output per beat

Every line below is transcribed from the shipped runner (`uv run triagedesk demo`, offline) — it is not
a hand-written mock. Tool calls print as `[tool] <name> <inputs> -> <outputs>`; each beat closes with a
`--- outcome ---` block carrying the **sourced priority** — colour, target, the matched discriminator
ids, and the citation(s) behind the colour. Case ids are content-derived, so they are stable per case.
Offline the run shows **eight of the nine owned tools**; `request_clarification` appears when the online
planner chooses to ask — the `clarify` beat (see *Live final: the agent asks the nurse* below). The beats that
reach a named approval (`routine`, `escalation`, `deterioration`) commit, and `refusal` writes no row.

**`routine` (E-01 → GREEN, then delivered).** Six tool calls — `normalize_case`,
`match_discriminators`, `plan_next_step`, `score_priority`, `retrieve_evidence`, `assess_confidence`
— then the named approval reaches the gated `commit_priority`:

> **Narration cue:** "Watch the routine case score GREEN. The complaint names no discriminator, so the
> recorded vitals are the complete SATS basis — it is delivered, and committed only after the named
> approval."

```
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  commit       : committed case <id> at queue position 1 (GREEN)
```

`match_discriminators` reports `retrieval_status: no_candidate` for "sore throat": no discriminator
applies, so the case is **not** deferred. (The 2:28 v1.0 video uploaded to Google Drive predates v1.2
and shows the earlier deferral here; the 2:29 re-recording does not play the routine beat. The shipped
behaviour is the delivery above.)

**`escalation` (E-02 → ORANGE, committed under the named nurse).** The same six calls plus
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

**`deterioration` (E-07 → second look, delivered).** The same six calls plus
`raise_recheck_flag` and the gated `commit_priority` — the flag marks the serial-vitals change
**without re-classifying** the patient:

> **Narration cue:** "Watch the second look raise a recheck flag without re-classifying the patient.
> Since v1.2 the vitals colour is delivered with that flag; the gate still waits for a named human."

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — heart_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — systolic_bp band
  second look  : {"flag":true,"deteriorations":["respiratory_rate","heart_rate","systolic_bp"], ...}
  commit       : committed case <id> at queue position 1 (ORANGE)
```

The `second look` line carries the deterioration facts and no colour of its own: the flag never
re-classifies, and the commit happens only through the named approval. (The 2:28 v1.0 Drive
recording predates v1.2 and shows the earlier deferral here; the re-recording does not play this
beat.)

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

Narrate the failure while it is on screen: the vague complaint's discriminator is **not retrieved**. Since
v1.2 the case is a **bounded clarification** — it asks for a capillary glucose and ketones and delivers
no colour — rather than a dead-end deferral. The printed colour is the residual vitals-only result shown
*before* the clarification routes the case to its terminal; the demo does not hide the miss. The 2:28 v1.0
Drive recording predates v1.2 and shows the earlier deferral; the 2:29 re-recording shows the output
above.

## Live final: the agent asks the nurse (online clarify beat)

The strongest answer to "is this genuinely agentic?" is the agent visibly asking a human mid-run and
acting on her answer — through MCP, live. The `clarify` beat runs E-09 (*"feeling unwell"*, known
diabetic) with the local model:

```bash
# Live, in front of the judges: the presenter types the answer at each `[nurse] q1>` prompt
# (name the finding, e.g. "low glucose, 2.1 mmol/L"); Enter on every prompt = decline.
uv run triagedesk demo --online --beat clarify

# Rehearsal / scripted: the answer is supplied up front (repeatable, in question order).
uv run triagedesk demo --online --beat clarify --answer "low glucose, 2.1 mmol/L"
```

Excerpt of a real run (2026-11-15, `qwen2.5:1.5b` via Ollama, the `--answer` form; long JSON elided with
`…`). The model decides whether to ask; temperature 0, so runs repeat, but it is a model — across two
runs the chosen actions were identical while the model's free-text rationale wording differed:

```
mode: online — local model qwen2.5:1.5b via Ollama
[tool] plan_next_step {…"retrieval_status": "ambiguous"…} -> {"action": "ask_question", …, "overridden": false, "proposed_action": "ask_question", …}
[elicit] request_clarification: One detail would resolve this triage case. Answer what you can — a blank field is an unanswered question, not a finding.
[elicit] request_clarification asks q1: Ask about: Hypoglycaemia — glucose < 3 mmol/L
[elicit] request_clarification asks q2: Ask about: Diabetic glucose > 11 with ketonuria
[elicit] request_clarification asks q3: Ask about: Diabetic glucose > 17 without ketonuria
[nurse] q1: low glucose, 2.1 mmol/L
[nurse] q2: (no answer)
[nurse] q3: (no answer)
[tool] request_clarification {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"]} -> [{… "text": "{\n  \"outcome\": \"accepted\",\n  \"answers\": [\n    \"low glucose, 2.1 mmol/L\"\n  ],\n  \"reason\": null\n}", "type": "text"}]
[tool] match_discriminators {"complaint": "feeling unwell low glucose, 2.1 mmol/L", …} -> {"candidates": ["hypoglycaemia"], "matched_ids": ["hypoglycaemia"], "no_match": false, "questions": [], "retrieval_status": "matched", "warning": null}
…
--- outcome ---
  colour       : RED
  target       : Immediate
  matched ids  : ['hypoglycaemia']
  answers      : ['low glucose, 2.1 mmol/L']
  elicitation  : accepted
  citation     : SATS Training Manual 2012 (EMSSA), adult clinical discriminators — SATS Table: Emergency discriminators
  commit       : committed case 52a30522f6fe4a61 at queue position 1 (RED)
  …
  DECLARED     : ORANGE (the eval expectation for the note alone — not compared: this run added a nurse answer)
```

**How it works.** The run pauses **inside** the `request_clarification` MCP tool call: the online beat
loads that one tool through the shipped `langchain.mcp` adapter, in process (a real 2026-07-28 MCP
session, `mcp/adapter.py`'s `with_live_clarification` seam), so the tool returns an input-required round
and the adapter raises a real `mcp_elicitation` interrupt. The `[elicit]` lines are the server's own
questions, read from that interrupt (each derived from the discriminator data — the demo authors none).
The answer resumes the **same** run; the `[tool] request_clarification` line prints after the resume, with
the tool's `accepted` result.

**Safety rules — what an answer can and cannot do.**

- The answer is an **observation**: it is appended to the complaint text and re-matched by the
  deterministic matcher. The colour is `score_priority`'s, never the model's or the answer's.
- The commit still needs the **named approval** — here the demo's synthetic nurse. An answer never
  answers the approval gate.
- A decline or a blank answer records nothing. A non-interactive run without `--answer` declines
  (`[nurse] declined — no answer given; nothing is recorded`) and **never waits** on stdin; the case then
  ends as the `failure` beat does (GREEN, `SHOWN MISMATCH`, no commit).
- **Alias-matching caveat.** Matching is alias text from `data/sats_discriminators.yaml`: an answer that
  names the finding as one of its aliases spells it (for example "low glucose") resolves it; a bare
  number such as "glucose 2.1" is recorded but matches nothing, so the case stays unresolved and defers.
  There is no number parsing.

**Why `DECLARED` has no verdict on an answered run.** The declared ORANGE is the eval expectation for the
note **alone**; this run added an observation the note did not contain, so comparing the two would
measure a different input. It is printed, not compared. The unanswered `failure` beat keeps its
`DECLARED` / `MEASURED` pair unchanged.

**The batch eval is unchanged.** `triagedesk eval` has no human to answer, so it keeps the in-process
tool, which records `unavailable` whenever its planner asks; its sealed reports are unchanged by this
beat and no new eval numbers are claimed. `--durable` never pauses at a question either — the two-command
durability story keeps the in-process tool.

## The desk surface (browser screen recording)

`docs/assets/desk-demo.mp4` is a **silent browser screen recording of the local desk surface** (the v1.1
`desk` bridge — not the terminal). It is **supplementary**: it shows the desk UX end to end (happy path
+ edge cases) so a reviewer can see the surface without running it. It is **not** the submission video —
that is the terminal recording above (`docs/assets/triagedesk-demo.mp4`), which carries the tool calls,
the measured eval and the declared failure. This capture is a separate, clearly-labelled artefact.

> **The recording predates the later desk additions.** It was captured on 2026-10-13, before the
> `Waiting room` / `New case` nav and live mode label, `--online`, the complaint precompute, and the
> keyboard-first form. It does not show any of those; the sections below describe the current page.

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
| Happy path | E-04 (emergency discriminator) | The **suggested** priority card — RED, target time, every "why" vital **next to its citation**, then the SATS evidence — then the real gate; a named nurse **approves** → `Approved by Nurse A. Demo (triage nurse) — committed to the queue at position 1`. |
| Edge — edit | E-10 | The nurse overrides the colour → `Edited to ORANGE by Nurse A. Demo (triage nurse) — committed to the queue at position 2`. A **different** patient (E-10, not E-04) is a genuinely new row, so the two approvals land at positions **1 and 2**. |
| Edge — dismiss | E-02 | `Dismissed — nothing has been committed`. There is no default approve. |
| Edge — recovery | E-05 | A scored vital is missing → `A scored vital is missing. Re-measure before scoring.` **No gate**. |
| Edge — deferred | E-09 | No discriminator matched, but a chronic condition is stated → the loud banner + a **read-only clarification panel** asking for capillary glucose/ketones. **No gate.** |
| Edge — escalation | E-06 | An out-of-scope (paediatric) case → `escalated for human review — no priority was committed`. **No gate**. |

The recording is **captioned on screen** — it carries no audio track, so the narration *is* the
on-screen line, and the pacing is deliberately human: the vitals are typed character by character, the
page scrolls with momentum rather than jumping, and the pointer and its clicks are visible. The happy
path is recorded at a careful pace; the edge beats move at a practiced-nurse pace. Duration 2:55.

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
  of 2026-10-13. The interview is prepared but unattested
  ([`CLINICIAN-INTERVIEW.md`](CLINICIAN-INTERVIEW.md)).
- The repository video (`docs/assets/triagedesk-demo.mp4`) is the 2:29 re-recording on the local
  model, not yet uploaded; the 2:28 v1.0 recording was **uploaded to Google Drive during submission**
  (folder link above). The brief's YouTube/Vimeo requirement is the residual platform caveat.

Record the close over the running terminal, not over slides: open source, offline, synthetic.
