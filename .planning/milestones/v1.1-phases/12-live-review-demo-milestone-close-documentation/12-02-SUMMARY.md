---
phase: 12-live-review-demo-milestone-close-documentation
plan: 02
subsystem: docs (demo runbook + README + EVALS §7)
tags: [demo-runbook, honest-eval, clinical-fit, drift-close, DEMO-02, FIT-01, DOCS-06]
dependency_graph:
  requires:
    - "src/triagedesk/demo/run.py + demo/storyboard.yaml (the shipped five-beat runner; the demo doc's source of truth)"
    - "scripts/emit_evals.py + evals/results/report.json (the EVALS.md projection guard)"
    - "tests/test_demo_runbook.py / test_docs_final.py / test_readme_runbook.py (the doc contracts)"
  provides:
    - "docs/DEMO.md refreshed to the shipped CLI (Phase-11 drift closed; seven tools; measured-eval beat; human flags)"
    - "README.md v1.1 status + honest clinical-fit re-declaration"
    - "EVALS.md §7 marked, attributed, empty clinician-review slot"
  affects:
    - "docs/DEMO.md / README.md / EVALS.md (the v1.1 submission docs)"
tech-stack:
  added: []
  patterns:
    - "re-transcribe-from-the-shipped-runner (the runner is the source of truth; the doc is derived)"
    - "flag-don't-claim (a human step is marked human_needed and never asserted)"
    - "link-don't-restate (docs link EVALS.md; no measured number is restated outside the projection)"
key-files:
  created: []
  modified:
    - docs/DEMO.md
    - README.md
    - EVALS.md
decisions:
  - "D12-04: a 2–3 minute narrated demo script with a one-line narration cue pinned per beat"
  - "D12-05: the recording and the public upload are flagged human_needed and never claimed"
  - "D12-06: the clinical-fit gap is re-declared honestly with a marked, attributed, empty slot"
  - "D12-10: the Phase-11 docs/DEMO.md output drift is closed by re-transcription from the shipped runner"
  - "Q2: the committed EVALS.md projection plus the live failure beat is the on-screen measured artefact; the ~10-min silent real run is NOT streamed"
metrics:
  duration: "4min"
  completed: "2026-10-13"
status: complete
actuals:
  tokens: 3890
  tasks: 3
  commits: 3
  plan_head_before: f63968222bbc4fe24401df2fc3abc95a33ffb640
  plan_head_after: 142f9c602acbc657199cc8aab6e80b63382e1282
requirements-completed: [DEMO-02, FIT-01, DOCS-06]
coverage:
  - id: D1
    description: "docs/DEMO.md re-transcribed from the shipped CLI: routine/deterioration defer with no commit, escalation commits at queue position 1, seven owned tools, handover-card lines, the Phase-11 'Known drift' note deleted, a per-beat narration cue, and a measured-eval-on-screen beat."
    requirement: DEMO-02
    verification:
      - kind: unit
        ref: "tests/test_demo_runbook.py"
        status: pass
    human_judgment: true
    rationale: "The guard proves the documented beats match `demo --list` both ways and the honesty clauses are present, but the byte-level faithfulness of the outcome blocks (no commit on routine/deterioration, the escalation commit line) and the honesty of the measured-eval narration are prose a human must confirm."
  - id: D2
    description: "README.md v1.1 status badge + capability sentence, and the honest clinical-fit re-declaration (no review obtained as of 2026-10-13; demo recorded but not yet uploaded)."
    requirement: FIT-01
    verification:
      - kind: unit
        ref: "tests/test_docs_final.py"
        status: pass
      - kind: unit
        ref: "tests/test_readme_runbook.py"
        status: pass
    human_judgment: true
    rationale: "The guards prove the structural constraints (one-command quickstart, no stale rows, EVALS.md/E-09 pointer, CLI-accepted invocations); 'no invented review / no over-claim' is prose honesty a human must read."
  - id: D3
    description: "EVALS.md §7 re-declares the gap with a marked, attributed, empty clinician-review slot; the generator projection is untouched."
    requirement: FIT-01
    verification:
      - kind: unit
        ref: "uv run python scripts/emit_evals.py --check"
        status: pass
      - kind: unit
        ref: "tests/test_docs_final.py"
        status: pass
    human_judgment: true
    rationale: "The projection guard proves no generated cell was hand-edited; the emptiness/attribution of the slot and the absence of an invented quote are prose a human must confirm."
---

# Phase 12 Plan 02: Live demo runbook, honest clinical-fit re-declaration Summary

**`docs/DEMO.md` re-transcribed from the shipped demo runner (Phase-11 drift closed), README taken to v1.1 with the clinical-fit gap re-declared, and EVALS.md §7 given a marked, attributed, empty clinician-review slot.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-13T10:30:43Z
- **Completed:** 2026-10-13T10:34:51Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **Closed the Phase-11 `docs/DEMO.md` output drift (D12-10).** The five `--- outcome ---` blocks were
  re-transcribed from a live `uv run triagedesk demo` run: `routine` (E-01) and `deterioration` (E-07)
  now **defer** (no `commit` line), `escalation` (E-02) commits at **queue position 1**, and the doc names
  **seven owned tools**. The stale "Known drift" blockquote and the false "queue positions accumulate
  across the run" sentence are gone.
- **Added the printed `handover card:` line** (the carried IN-06 finding) to the `escalation` and
  `refusal` blocks, where the CLI prints it.
- **Made the measured-eval beat honest (DEMO-02, resolve Q2).** A new runbook section states plainly that
  the committed report is `mode: real`, takes ~10 minutes and is **silent**, so it is **not** streamed in a
  2–3 minute recording; the on-screen artefact is the committed `EVALS.md` projection plus the live
  `failure` beat (`DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)`). The timing table was retimed
  to 2–3 minutes and gained the measured-eval beat.
- **Added a one-line narration cue per beat (D12-04)**, so the presenter's wording is pinned on the page.
- **Flagged the human steps (D12-05).** The recording and the public upload are marked `human_needed`; the
  upload is named the one submission blocker and is never claimed.
- **README → v1.1 (FIT-01, DOCS-06).** The badge is `status-v1.1--milestone-close`; a concise v1.1
  capability sentence (durable approve/resume over `checkpoints.db`, `no_match` deferral banner with
  audit-trail retrieval grounding, loopback desk surface) was added while the frozen `v1.0-submission`
  tag is kept. The "What is unfinished" section re-declares the clinical-fit gap honestly (no review as of
  2026-10-13) and states the demo is recorded but not yet uploaded.
- **EVALS.md §7 (FIT-01).** The stale "before Day 5" mitigation bullet was replaced with a marked,
  attributed, **empty** slot: "Clinician review: none obtained as of 2026-10-13 … Nothing is claimed
  until it is." No generated cell was touched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refresh docs/DEMO.md** - `20aa3db` (docs)
2. **Task 2: README v1.1 status + clinical-fit re-declaration** - `76e3077` (docs)
3. **Task 3: EVALS.md §7 marked empty clinician slot** - `142f9c6` (docs)

**Plan metadata:** `_pending_` (docs: complete plan) — `.planning/` is uncommitted by design
(`commit_docs: false`).

## Files Created/Modified

- `docs/DEMO.md` — re-transcribed outcome blocks, seven tools, handover-card lines, per-beat narration
  cues, the measured-eval-on-screen section, retimed 2–3 minute table, `human_needed` upload flag.
- `README.md` — v1.1 status badge + capability sentence; honest clinical-fit re-declaration; demo
  "recorded but not yet uploaded".
- `EVALS.md` — §7 narrative only (stale date → marked, attributed, empty clinician-review slot).

## Decisions Made

- **D12-04** — a 2–3 minute narrated demo script with a pinned one-line cue per beat.
- **D12-05** — the recording and the public upload are `human_needed`; never claimed.
- **D12-06** — the clinical-fit gap is re-declared with a marked, attributed, empty slot; no quote invented.
- **D12-10** — the Phase-11 `docs/DEMO.md` drift is closed by re-transcription from the shipped runner.
- **Q2** — the on-screen measured artefact is the committed `EVALS.md` projection plus the live `failure`
  beat; the ~10-minute silent real run is **not** streamed.

## Deviations from Plan

None - plan executed exactly as written. The three outcome blocks that carried drift were corrected
exactly as specified, and the `refusal`/`failure` blocks kept their measured values while gaining the
faithfully-transcribed `matched ids` and (for `refusal`) `handover card` lines the plan's point (5)
directed be included where the CLI prints them.

## Auth Gates

None.

## Known Stubs

None. The `<content-id>` tokens in the durable-mode section are documented presenter placeholders for the
content-derived thread id the CLI prints at runtime — deliberate presenter inputs, not unimplemented code.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change. The phase edits prose
only; the threat-model mitigations T-12-06 (recording/upload flagged, never asserted), T-12-07
(clinical-fit re-declared with an empty attributed slot), T-12-08 (`emit_evals --check` exits 0 — no
hand-tuned generated cell) and T-12-09 (docs link `EVALS.md`, never restate a number) are all in place.

## Human-Needed Steps (flagged, not claimed)

1. **Record and publicly upload the demo video** — the upload to YouTube/Vimeo (Public) is the one
   submission blocker (STATUS G1). This plan prepares the script and never hosts a video.
2. **Obtain a triage nurse/clinician review** — none obtained as of 2026-10-13; README and `EVALS.md` §7
   carry a marked, attributed, empty slot. If access is arranged before the deadline, paste the attributed
   quote; nothing is claimed until it is.

## Issues Encountered

None.

## Next Phase Readiness

- The demo runbook, README and `EVALS.md` §7 now tell the truth: a failure is shown, the real eval is not
  streamed, and the clinical gap is re-declared with an empty attributed slot.
- `uv run pytest -q` → **453 passed**; `uv run python scripts/emit_evals.py --check` exits 0.
- No `src/` or `data/` change (`git status --porcelain -- src/ data/` prints nothing).

---

## Self-Check: PASSED

- `docs/DEMO.md` — FOUND
- `README.md` — FOUND
- `EVALS.md` — FOUND
- commit `20aa3db` — FOUND
- commit `76e3077` — FOUND
- commit `142f9c6` — FOUND
- `grep -c "Known drift" docs/DEMO.md` → 0
- `grep -c "before Day 5" EVALS.md` → 0
- `uv run pytest -q` → 453 passed
- `uv run python scripts/emit_evals.py --check` → exits 0

---

*Phase: 12-live-review-demo-milestone-close-documentation*
*Completed: 2026-10-13*
