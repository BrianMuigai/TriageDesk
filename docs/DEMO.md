# DEMO — TriageDesk submission video runbook

> **The recording is a HUMAN action.** The 3-minute video is an **unedited screen recording**
> (`< 3 min`) — **tool calls on screen, no slides** — uploaded publicly to YouTube or Vimeo. This
> document is the runbook a person follows to record it; the agent does **not** record the video.
>
> Record against the **frozen submission tag `v1.0-submission`** — the commit the freeze protocol in
> [`ROADMAP.md`](ROADMAP.md) creates (tagged in plan 05-03). The canonical storyboard is the table
> in [`ROADMAP.md`](ROADMAP.md) → *Demo storyboard*; this runbook maps those timing bands to exact
> commands and expected output and does **not** restate the storyboard (DRY — it links to the single
> source).

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

| Time (ROADMAP) | Beat(s) | Command | Expected on screen |
| --- | --- | --- | --- |
| 0:00–0:20 | — (narration) | *(no command)* | The desk problem: 60–90 min wait; unsourced flags are dangerous. |
| 0:20–1:10 | `routine` → `escalation` | `uv run triagedesk demo --beat routine` then `--beat escalation` (or the bare command) | GREEN routine, then ORANGE escalation — **tool calls + citations on screen**. |
| 1:10–1:50 | `deterioration` | `uv run triagedesk demo --beat deterioration` | A waiting patient flagged for a **second look** (`raise_recheck_flag`). |
| 1:50–2:30 | `refusal` | `uv run triagedesk demo --beat refusal` | The **approval gate refusing** to commit without the named nurse. |
| 2:30–2:50 | `failure` | `uv run triagedesk demo --beat failure` | The **E-09 failure**, shown and explained. |
| 2:50–3:00 | — (narration) | *(no command)* | Close: open source, offline, synthetic. |

## Expected on-screen output per beat

Every line below is real output from the shipped CLI (not a hand-written mock). Tool calls print as
`[tool] <name> <inputs> -> <outputs>`; each beat closes with a `--- outcome ---` block carrying the
**sourced priority** — colour, target, the matched discriminator ids, and the citation(s) behind the
colour. Case ids are content-derived, so they are stable per case; queue positions accumulate across
the run.

**`routine` (E-01 → GREEN).** Four tool calls — `normalize_case`, `match_discriminators`,
`score_priority`, `commit_priority` — then:

```
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  commit       : committed case <content-id> at queue position 1 (GREEN)
```

**`escalation` (E-02 → ORANGE, committed under the named nurse).** Same four tools, three citations:

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  matched ids  : ['acute_shortness_of_breath']
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — heart_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — temperature band
  commit       : committed case <content-id> at queue position 2 (ORANGE)
```

**`deterioration` (E-07 → second look).** Reaches the fifth owned tool, `raise_recheck_flag`, which
flags the serial-vitals change **without re-classifying** the patient:

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — heart_rate band
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — systolic_bp band
  second look  : {"flag":true,"deteriorations":["respiratory_rate","heart_rate","systolic_bp"], ...}
  commit       : committed case <content-id> at queue position 3 (ORANGE)
```

**`refusal` (the climax).** The same E-02 priority is scored, but the gate is resumed with a `dismiss`
naming **no approver**, so the gated commit refuses and writes nothing — the refusal is read from the
real store row delta, not asserted:

```
--- outcome ---
  colour       : ORANGE
  target       : < 10 min
  commit       : clinician dismissed the priority; refusing to commit
  GATE REFUSED : no queue row written (rows added this beat: 0)
```

**`failure` (E-09, the declared failure — shown, not hidden).** The vague complaint *"feeling unwell"*
matches no discriminator, so the score falls back to vitals alone. The beat prints the declared vs the
measured outcome on screen:

```
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — all recorded parameters within normal SATS bands
  DECLARED     : ORANGE
  MEASURED     : GREEN (SHOWN MISMATCH)
```

Narrate the failure while it is on screen: the under-triage of a vague complaint is a real, declared
limitation, and the demo does not hide it.

## What is unfinished

The video must be as honest as the docs. Point the close at what the repository itself declares:

- [`EVALS.md`](../EVALS.md) §6 — **E-09**, the failure we did not fix (free-text discriminator
  selection); plus the other honest misses recorded in the measured report. Do not restate the numbers
  here — `EVALS.md` is generated from `evals/results/report.json` and is the single source.
- [`README.md`](../README.md) — the honest "what is unfinished" statement and the one-command
  quickstart.
- Clinician validation remains a **declared gap** (`EVALS.md` §7): the expected colours come from the
  published SATS rules, not clinician adjudication.

Record the close over the running terminal, not over slides: open source, offline, synthetic.
