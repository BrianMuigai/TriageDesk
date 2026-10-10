# ROADMAP — TriageDesk (submission packaging)

> **Phase-level execution plan (authoritative): [`../.planning/ROADMAP.md`](../.planning/ROADMAP.md)** — GSD,
> 5 phases, 44 mapped requirements, in `.planning/`.
> This file covers **submission packaging only** — what the challenge needs delivered and frozen. It
> deliberately does **not** repeat the phase plan (DRY).

## Brief milestones → our phases

| Brief milestone | Our phase | Checkpoint |
| --- | --- | --- |
| Paper Prototype review | **Phase 1** | SATS data + model/MCP proof |
| Midpoint Stress Test | **Phase 3** | Gate + audit + end-to-end run |
| Final submission | **Phase 5** | Frozen repo + video + docs |

Six days off the calendar (Oct 9 → Oct 15) map onto the five phases; the phase plan is the single
source of truth for sequencing.

## Demo storyboard (< 3 min, unedited)

Unedited screen recording, **tool calls on screen, no slides**; uploaded publicly to YouTube or Vimeo.

| Time | Content |
| --- | --- |
| 0:00–0:20 | The desk problem: 60–90 min wait; unsourced flags are dangerous. |
| 0:20–1:10 | Routine case → GREEN, then an escalated case → ORANGE, **tool calls + citations on screen**. |
| 1:10–1:50 | Deterioration re-check: a waiting patient flagged for a second look. |
| 1:50–2:30 | **Approval gate:** the agent refuses to commit a queue position without the named nurse. |
| 2:30–2:50 | The **E-09 failure**, shown and explained. |
| 2:50–3:00 | Close: open source, offline, synthetic. |

## Submission gate (Definition of Done)

- [ ] Clean clone runs `uv run triagedesk demo` in one command.
- [ ] CI smoke test green on a clean checkout.
- [ ] 14 eval cases with measured pass/fail + **E-09** documented as unfixed.
- [ ] Safety invariants INV-1…INV-4 pass on every run.
- [ ] Every priority cited; every commit gated; audit log present.
- [ ] README honest about what is unfinished.
- [ ] `../ARCHITECTURE.md` one page; `../EVALS.md` complete; `../DESCRIPTION.md` ~300 words.
- [ ] Demo video < 3 min, unedited, failure included.
- [ ] OSI licence present; repo frozen and tagged.

## Freeze protocol (disqualification protection)

- Freeze on **Day 6 morning**; create the submission tag.
- **Disable `commit_docs`, CI, and hooks** after freeze — GSD auto-commits planning docs, and a
  post-deadline commit disqualifies. Audit the remote for any post-freeze commit.
- Repositories are cloned at the deadline; there are no exceptions.

For risks and their mitigations, see [`REQUIREMENTS.md`](REQUIREMENTS.md) §10.
