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

## What you will see

_An illustrative transcript: the edit colours and the target time shown are read from the
loaded SATS substrate, and a guard in the test suite keeps them equal to it._

```text
Start here
  1. Enter the vitals and the complaint.
  2. Choose Get suggested priority.
  3. Check the suggestion and its evidence.
  4. Approve, edit, or dismiss — nothing is committed until you do.

No case yet
  Enter the patient's vitals and complaint, then choose Get suggested priority.

Patient vitals
  Age (years) · Age (months) · Age unclear · Height (cm) · Alertness (AVPU) · Breathing rate
  Oxygen saturation · Heart rate · Systolic BP · Diastolic BP · Temperature (°C) · Mobility
  Trauma · Complaint
  [ Get suggested priority ]

Suggested priority
  This is a suggestion, not a decision. You confirm the priority.
  Suggested colour: GREEN            Target time: < 4 hours
  Why these vitals: …                Evidence from the SATS knowledge base: …

Your decision
  Your name: ______    Your role: ______
  Choose the priority colour:  GREEN   ORANGE   RED   YELLOW
  [ Approve suggestion ]   [ Edit colour ]   [ Dismiss (commit nothing) ]

Approved by NAME (ROLE) — committed to the queue at position 1.
Dismissed — nothing has been committed.
No decision was made — nothing has been committed.

No discriminator matched / low confidence — nurse to confirm
```

> **Since this transcript was written:** the page now carries a `Waiting room` / `New case` nav and a
> live mode label (offline by default; `--online` says the local model reads the complaint). `GET
> /waiting` renders the committed queue as an acuity-ordered, **read-only** waiting room — it never
> writes a row. The complaint field precomputes its extraction in the background while you finish the
> vitals, and the form is keyboard-first: the DOM order is the tab order, so no pointer is required.

A case that cannot be confirmed from the vitals alone shows the same banner above a read-only
card and **no decision controls** — nothing can be queued from it.

When the complaint is *near* a discriminator but names none, the page asks **one bounded question**
instead of dead-ending — e.g. a vague complaint in a known diabetic shows "Check: capillary glucose
(mmol/L) and ketones". Answer it in the complaint field and resubmit; a second ambiguity defers rather
than asking again. A clarification never shows a colour, a target or a decision control.

A complaint that names **no** discriminator at all (a routine review, a sore throat) is not a
clarification: the recorded vitals are the complete SATS basis, so the case is delivered normally with
its baseline citation.

## What the surface never does

- **A timeout is no approve.** If you do not decide, nothing is committed — there is no default
  colour and no auto-approval.
- **A dismiss commits nothing.** Dismissing the suggestion writes nothing to the queue.
- **The surface never commits on its own.** The only route to the queue is your own approval
  through the gate.
