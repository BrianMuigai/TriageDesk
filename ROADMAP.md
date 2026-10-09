# ROADMAP — TriageDesk

> Solo build. **~6 days**, today Oct 9 → deadline **Oct 15**. Challenge brief:
> <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> Scope is a scored skill — this plan optimises for a *working, honest, frozen* submission over breadth.

## Guiding rules

- **Front-load the risk.** The riskiest items (local model tool-calling, the gate, the demo recording)
  happen earliest.
- **Freeze early.** Repos are cloned at the deadline; post-deadline commits disqualify (EL-6).
- **Demo is a deliverable, not an afterthought.** Record it on Day 5.
- **Docs are living.** `EVALS.md` and `README.md` get real results as they land.
- **Explain what we ship.** AI coding tools are allowed (the brief says so), but nothing ships that we
  cannot explain line-by-line in the live review (`DECISIONS.md` D14).

## Day-by-day

### Day 1 — Foundations
- Encode adult SATS as data: `data/sats_tews.yaml` (parameters + bands + points),
  `data/sats_discriminators.yaml` (Emergency / Very Urgent / Urgent + citations). Source: `docs/SATS.md`.
- Scaffold repo: `uv`, Python 3.12, package layout, LICENSE, and a CI smoke test
  (`.github/workflows/smoke.yml`).
- Prove **Ollama + Qwen2.5** emits a valid structured tool call on this machine (RAM check → choose
  3B or 1.5B).
- **Exit criteria:** one case parsed into structured JSON by the local model.

### Day 2 — The MCP server (ours)
- Implement 5 tools: `normalize_case`, `match_discriminators`, `score_priority`, `raise_recheck_flag`,
  `commit_priority` (gated stub).
- Unit-test the deterministic scorer against hand-computed expected colours (E-01, E-02, E-04, E-10, E-11).
- **Exit criteria:** all scorer unit tests green.

### Day 3 — Graph, borrowed server, gate, logging
- Wire LangGraph: `ingest → normalize → retrieve → score → verify → (recheck) → gate → commit → handover`.
- Integrate the **borrowed SQLite MCP** server for the case/queue store + audit table.
- Implement the **approval gate** (`interrupt()`) and the **hash-chained audit log**.
- **Exit criteria:** an end-to-end run that refuses to commit without approval.

### Day 4 — Evals, recovery, honest failure
- Synthetic stream (20–30 cases) + the 13 eval cases with expected outcomes.
- Implement missing-vital recovery (E-05), safe abstention (E-06), deterioration (E-07).
- Run the eval harness **3×** per case; measure stability + latency; capture **E-09** as the unfixed failure.
- **Exit criteria:** `evals/results/report.json` populated; safety invariants pass.

### Day 5 — Demo + minimal surface
- Minimal terminal surface: stream tool calls + citations; show the approval gate and the failure.
- **Record the 3-minute demo** — unedited, tool calls on screen, failure included.
- **Exit criteria:** demo uploaded to YouTube/Vimeo, publicly visible.

### Day 6 — Docs, freeze, submit
- Finalise `README.md` (one-command run, honest status), `ARCHITECTURE.md`, `EVALS.md` (measured),
  `DESCRIPTION.md`.
- Verify a **clean clone runs the one command** on a fresh environment.
- Tag the release; **no commits after freeze**.
- Submit via the challenge portal.

## Milestones (mirrors the brief's schedule)

| Brief milestone | Our mapping | Checkpoint |
| --- | --- | --- |
| Paper Prototype review | Day 1 end | SATS data + model proof |
| Midpoint Stress Test | Day 3 end | Gate + audit + end-to-end run |
| Final submission | Day 6 | Frozen repo + video + docs |

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

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| RAM ceiling (6.9 GB) blocks the model | 3B target / 1.5B fallback; small context; constrained output; consider a beefier demo machine |
| Host Python 3.14 wheel gaps | Pin Python 3.12 via `uv` |
| Borrowed SQLite MCP unmaintained | Verify by Day 2; maintainer fork acceptable (community server) |
| Small model unreliable at multi-step calls | Explicit graph; bounded decisions; retry-once in `verify` |
| No clinician access | Literature grounding; declare gap; attempt one review before Day 5 |
| Overrun → no demo | Demo recorded Day 5 regardless of polish; polish last |

## Definition of done (submission gate)

- [ ] Clean clone runs `uv run triagedesk demo` in one command.
- [ ] CI smoke test green on a clean checkout.
- [ ] 13 eval cases with measured pass/fail + **E-09** documented as unfixed.
- [ ] Safety invariants INV-1…INV-4 pass on every run.
- [ ] Every priority cited; every commit gated; audit log present.
- [ ] README honest about what is unfinished.
- [ ] ARCHITECTURE.md one page; EVALS.md complete; DESCRIPTION.md ~300 words.
- [ ] Demo video < 3 min, unedited, failure included.
- [ ] OSI licence present; repo frozen and tagged.
