# DESK — TriageDesk desk-surface quickstart

> **One local surface.** The desk surface is served by the shipped `triagedesk` command. It binds
> to **loopback only** (`127.0.0.1`), makes **no external request**, needs **no build step**, and
> adds **no dependency**. A nurse opens it, enters the patient's vitals and complaint, reads the
> sourced suggestion with its evidence, and approves, edits, or dismisses it.

## One-time setup (from a clean clone)

```bash
# Deterministic install (no network surprises; uses the committed uv.lock).
uv sync --locked
```

## Start the desk

```bash
# The one command — serves the local page (loopback only, no external request):
uv run triagedesk desk

# Overrides: a different loopback address, port, or checkpoint file.
uv run triagedesk desk --host 127.0.0.1 --port 8765 --db checkpoints.db

# Offline is the default (no model called). Add --online to run the local model on the
# free-text complaint; the deterministic scorer still decides the colour.
uv run triagedesk desk --online
```

Then open **http://127.0.0.1:8765** in a browser and stop the server with `Ctrl-C`.

## Terminal instead of a browser

The same graph, the same gate, no page — one patient at a time:

```bash
uv run triagedesk triage            # structured input only, no model call
uv run triagedesk triage --online   # read a pasted note (or the fields) with the local model
uv run triagedesk triage --online --note "40M, RR 24, HR 118, BP 108/70, temp 38.9, chest pain"
uv run triagedesk triage --online --note - < note.txt   # read the note from stdin
```

It offers a **raw note** first: paste the nurse's note and the owned extraction tool reads it
into the typed case, showing what it understood (and what was *not* stated) for you to confirm.
Decline and you answer the vitals field by field instead. Blank skips a vital, never imputes one.
Then the graph runs, asks you the same targeted question the desk would if the planner chooses
one, shows the suggested priority with its citations, and asks for a named decision.

`--note` skips the prompts entirely — one note in, one case run — which is the scripting path.
A raw note needs `--online`; without it the CLI says so and falls back to the fields.

The pasted note is the text the graph both classifies and identifies the case by, so a condition
it names (for example "known diabetic") is not lost at the extraction boundary: an ambiguous case
asks its one question instead of being offered a vitals-only colour.

An answer typed at a question is an observation, not an approval: the gate still pauses
afterwards. `Ctrl-C` at any prompt stops without committing. Nothing is pre-recorded: the note
you paste is the case that runs.

## What you will see

_An illustrative transcript: the edit colours and the target time shown are read from the
loaded SATS substrate, and a guard in the test suite keeps them equal to it._

```text
Triage workspace
  Conversation · Triage assistant                         Suggestion only
    TriageDesk assistant: Record the vitals, add the presenting complaint, and I
      will return a sourced SATS suggestion for you to confirm.
    You: coughing and fast breathing since last night
    TriageDesk assistant: Suggested priority
      Suggested colour: GREEN            Target time: < 4 hours
      Why these vitals: …                Evidence from the SATS knowledge base: …
    TriageDesk assistant: Your decision
      Your name: ______    Your role: ______
      Choose the priority colour:  GREEN   ORANGE   RED   YELLOW
      [ Approve suggestion ]   [ Edit colour ]   [ Dismiss (commit nothing) ]

  Structured intake · Patient vitals                    Scored input
    Age (years) · Age (months) · Age unclear · Height (cm) · Alertness (AVPU) · Breathing rate
    Oxygen saturation · Heart rate · Systolic BP · Diastolic BP · Temperature (°C) · Mobility
    Trauma · Complaint
    [ Get suggested priority ]   [ Clear form ]

Handover
  Case …  Priority GREEN  Target < 4 hours
  Approved by NAME (ROLE) — committed to the queue at position 1.
  Citations …  Read-only projection. The committed queue row and the hash-chained audit
  record remain authoritative.

Approved by NAME (ROLE) — committed to the queue at position 1.
Dismissed — nothing has been committed.
No decision was made — nothing has been committed.

No discriminator matched / low confidence — nurse to confirm
```

The left rail carries **New case** and **Waiting room**, the live mode label, and the
**Station link: MCP** note. The page is a conversation beside the structured intake, not a
replacement for it: the intake form remains the scored input, and the conversation is a
truthful projection of the current case.

> **Since this transcript was written:** the page carries a live **conversation** and a
> separate **structured intake** card. `GET /waiting` renders the committed queue as an
> acuity-ordered, **read-only** waiting room — it never writes a row. The complaint field
> precomputes its extraction in the background while you finish the vitals, and the form is
> keyboard-first: the DOM order is the tab order, so no pointer is required.

## The chat composer and note intake

Type in **Message the triage assistant** and choose **Send note** (or press `Ctrl`/`Cmd` +
`Enter`). The composer is associated with the vitals form, so it posts the values already
entered plus the per-server token; it is an intake step, never a scoring or decision step.

- **Offline (the default):** the note becomes the presenting complaint. Complete the vitals
  in the structured intake; the deterministic scorer uses those values. No model is called.
- **Online (`--online`):** the local model reads the note through the grounded extraction
  seam, and the form is prefilled for review. A value you typed is never overwritten; a
  blank field may take what the note stated. A failed read is reported honestly and leaves
  the form untouched.

Nothing is scored from the composer. It never runs the graph, never reaches the approval
gate, and never writes a queue row.

## Handover and the station link

After a named approval, the conversation renders a **Handover** card: the committed colour,
target, approver, decision, queue position, citations and the not-recorded/second-look
facts. It is the same sourced projection the **TriageDesk MCP server** returns to another
station — the desk is triage-only and does not write to a hospital station itself. The
handover card is read-only; the committed queue row and the hash-chained audit record remain
authoritative. See [`MCP.md`](MCP.md) for the MCP surface.

Open **System map** in the rail (`GET /system`) for the visible distinction between the
demo desk, the core solution, and the MCP integration path, including the transport at each
hop and the nine tools. The desk runs the core graph in-process; a station app connects to
the MCP server over stdio. The desk is a demo surface, not the integration API.

A case that cannot be confirmed from the vitals alone shows the same banner above a read-only
card and **no decision controls** — nothing can be queued from it.

When the complaint is *near* a discriminator but names none, the page asks **one bounded question**
instead of dead-ending — e.g. a vague complaint in a known diabetic shows "Check: capillary glucose
(mmol/L) and ketones". Answer it in the complaint field and resubmit; a second ambiguity defers rather
than asking again. A clarification never shows a colour, a target or a decision control.

With `--online`, the agent itself may ask mid-run. The page then pauses on a **question panel**: the
questions the server derived, one answer field each, a "Send answer" button and a "Decline to answer" control
— and no decision controls. Answering resumes the **same** case: the answer is matched as text, so the
next screen is the approval gate when it names the finding (e.g. "low glucose" — a bare number such as
"2.1" is not matched, and the case then stays unresolved). Declining adds nothing, and nothing is
committed either way until a named nurse decides at the gate. Offline the desk never asks.

A complaint that names **no** discriminator at all (a routine review, a sore throat) is not a
clarification: the recorded vitals are the complete SATS basis, so the case is delivered normally with
its baseline citation.

## What the surface never does

- **A timeout is no approve.** If you do not decide, nothing is committed — there is no default
  colour and no auto-approval.
- **A dismiss commits nothing.** Dismissing the suggestion writes nothing to the queue.
- **The surface never commits on its own.** The only route to the queue is your own approval
  through the gate.
