# DESK — TriageDesk desk-surface quickstart

> **One local page, nothing else.** The desk surface is a single local HTML page served by the
> shipped `triagedesk` command. It binds to **loopback only** (`127.0.0.1`), makes **no external
> request**, needs **no build step**, and adds **no dependency**. A nurse opens it, enters the
> patient's vitals and complaint, reads the sourced suggestion with its evidence, and approves,
> edits, or dismisses it.

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
```

Then open **http://127.0.0.1:8765** in a browser and stop the server with `Ctrl-C`.

## What you will see

```text
Start here
  1. Enter the vitals and the complaint.
  2. Choose Get suggested priority.
  3. Check the suggestion and its evidence.
  4. Approve, edit, or dismiss — nothing is committed until you do.

No case yet
  Enter the patient's vitals and complaint, then choose Get suggested priority.

Patient vitals
  Age (years) · Age (months) · Age unclear · Height (cm) · Breathing rate · Heart rate
  Systolic BP · Diastolic BP · Temperature (°C) · Oxygen saturation · Mobility · Alertness (AVPU)
  Trauma · Complaint
  [ Get suggested priority ]

Suggested priority
  This is a suggestion, not a decision. You confirm the priority.
  Suggested colour: GREEN            Target time: < 4 hours
  Why these vitals: …                Evidence from the SATS knowledge base: …

Your decision
  Your name: ______    Your role: ______
  Choose the priority colour:  GREEN   ORANGE   YELLOW   RED
  [ Approve suggestion ]   [ Edit colour ]   [ Dismiss (commit nothing) ]

Approved by NAME (ROLE) — committed to the queue.
Dismissed — nothing has been committed.
No decision was made — nothing has been committed.

No discriminator matched / low confidence — nurse to confirm
```

A case that cannot be confirmed from the vitals alone shows the same banner above a read-only
card and **no decision controls** — nothing can be queued from it.

## What the surface never does

- **A timeout is no approve.** If you do not decide, nothing is committed — there is no default
  colour and no auto-approval.
- **A dismiss commits nothing.** Dismissing the suggestion writes nothing to the queue.
- **The surface never commits on its own.** The only route to the queue is your own approval
  through the gate.
