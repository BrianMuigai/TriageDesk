---
phase: 12-live-review-demo-milestone-close-documentation
plan: 03
subsystem: docs (milestone-close submission-document refresh)
tags: [docs-refresh, v1.1, word-budget, stale-claim-sweep, DOCS-06]
dependency_graph:
  requires:
    - "src/triagedesk/graph/build.py — TRACER_NODES (the 13-node authoritative graph)"
    - "docs/REVIEW.md + docs/DEMO.md + EVALS.md — produced by plans 12-01/12-02; linked, never restated"
    - "tests/test_docs_final.py — the ARCHITECTURE 700-word / DESCRIPTION ±10% / README / EVALS guards"
  provides:
    - "ARCHITECTURE.md node table naming the real 13-node graph (ground/assess/request_missing_info/escalate) at 694/700 words"
    - "DESCRIPTION.md v1.1 capability clause at 326 prose words"
    - "STATUS.md / docs/REQUIREMENTS.md / docs/ROADMAP.md swept to the v1.1 state (no stale v1.0 claim)"
    - "docs/DECISIONS.md D25 close-out row"
  affects:
    - "uv run pytest -q (453 baseline, unchanged)"
tech-stack:
  added: []
  patterns:
    - "word-neutral refresh (replace/tighten, never append) under a whole-file token-count guard"
    - "link-don't-restate (docs link EVALS.md/ARCHITECTURE.md; no measured number restated outside the projection)"
key-files:
  created: []
  modified:
    - ARCHITECTURE.md
    - DESCRIPTION.md
    - STATUS.md
    - docs/REQUIREMENTS.md
    - docs/ROADMAP.md
    - docs/DECISIONS.md
decisions:
  - "D25: the milestone close is demonstrated-not-claimed — the live extension is data-only (a fresh process, no hot reload); the demo shows the committed EVALS.md projection plus the live failure beat, not the ~10-min real run; the clinical-fit gap stays declared with a marked, attributed, empty slot; the video upload and the clinician review stay human flags"
  - "ARCHITECTURE refresh is word-budget-neutral: the four real graph nodes are added by replacing/tightening prose, landing 694/700 words and 93/110 lines"
metrics:
  duration: "18min"
  completed: "2026-10-13"
status: complete
actuals:
  tokens: 5770
  tasks: 3
  commits: 3
  plan_head_before: 142f9c602acbc657199cc8aab6e80b63382e1282
  plan_head_after: bba6473ae356413605bdf1271dc8b7ceaf2b6138
requirements-completed: [DOCS-06]
---

# Phase 12 Plan 03: Milestone-close submission-document refresh Summary

**Every remaining submission document swept to the v1.1 state with no stale v1.0 claim left behind:
`ARCHITECTURE.md`'s node table now names the real 13-node graph inside its 700-word one-page bound,
`DESCRIPTION.md` gained a v1.1 capability clause inside its ±10% bound, `STATUS.md` /
`docs/REQUIREMENTS.md` / `docs/ROADMAP.md` stopped under-claiming resolved work, and `docs/DECISIONS.md`
records the Phase-12 close-out rationale as D25.**

## What Was Built

**`ARCHITECTURE.md` (§3 node table, word-neutral refresh).** The table listed nine nodes; the shipped
graph is `TRACER_NODES` (13). Added `ground` (`retrieve_evidence`, no colour), `assess` (the
coverage/deferral signal), and ONE combined terminal row `request_missing_info · escalate`. The four
added rows were paid for by tightening §1/§2/§3/§4/§5/§6/§7/§8 prose (replace, never append): the file
lands at **694/700 words, 93/110 lines**, keeps `qwen2.5:1.5b` verbatim, and keeps the "seven tools"
framing. No guard file was touched.

**`DESCRIPTION.md` (v1.1 clause).** A durable-approve/resume sentence over `checkpoints.db` plus the
retrieval-grounded `no_match` deferral banner was added inside the workflow paragraph; the prose count
moves 302 → **326 words** (within 270–330). The `<!-- ~300-word … -->` header comment and the closing
count comment are preserved.

**`STATUS.md` / `docs/REQUIREMENTS.md` / `docs/ROADMAP.md` (v1.1 sweep).** These three are unguarded
(RESEARCH §Blast radius), so the sweep is a full honest reconciliation:

- `STATUS.md` — the model row reconciles to the measured default `qwen2.5:1.5b`; the "697 words / 94
  lines" restatement is replaced by a link to `ARCHITECTURE.md`; the "no desk surface + 13–17 s"
  criterion is re-scoped (the Phase-10 loopback desk surface exists; latency links `EVALS.md` §3); G7
  reads **resolved** (Phase 9 exercised the borrowed read paths); the UX actor table and the U-gap list
  reflect the real approve/edit/dismiss gate (re-scoped to what remains: latency, vitals-entry
  ergonomics, environment, approver authn); the SOTA table reads durable execution, tracing/replay,
  retrieval grounding and deferral as **present** (honest re-scope: no embedding retrieval, no
  calibrated probability, offline-only eval); the test count reconciles to the measured **453**.
- `docs/REQUIREMENTS.md` — JC-1/DQ-2 say **seven** tools; BW-3 is exercised (MCP-01); JC-3 drops the
  stale "no desk surface" clause but **keeps** the "no clinician interview" declaration; ST-1 reads
  **rehearsed**, linking `REVIEW.md`; G-9 stays **OPEN — human**; G-11 is re-scoped to the residual
  desk-UX gaps; the "Updated" line reads **2026-10-13**.
- `docs/ROADMAP.md` — the packaging framing notes the additive **v1.1 — Score Uplift** milestone
  (Phases 6–12) over the frozen `v1.0-submission` tag while remaining a *packaging* doc that **links**
  `.planning/ROADMAP.md` and does not repeat the phase plan (DRY). The upload is not claimed.

**`docs/DECISIONS.md` (D25).** One ADR-lite row records the four genuine close-out choices — the
data-only live extension (fresh process, no hot reload), the demo showing the committed `EVALS.md`
projection + the live `failure` beat rather than the ~10-minute run, the declared clinical-fit gap with
an empty attributed slot, and the two flagged human steps. It **links** `REVIEW.md`, `DEMO.md` and
`EVALS.md` and restates none of their content.

## Task Commits

Each task was committed atomically:

1. **Task 1: ARCHITECTURE word-neutral refresh + DESCRIPTION v1.1 clause** — `2718bcb` (docs)
2. **Task 2: STATUS / REQUIREMENTS / ROADMAP v1.1 sweep** — `1c87ee7` (docs)
3. **Task 3: Phase-12 close-out decision row (D25)** — `bba6473` (docs)

**Plan metadata:** not committed — `.planning/` is uncommitted by design (`commit_docs: false`).

## Files Created/Modified

- `ARCHITECTURE.md` — §3 node table now names `ground`/`assess`/`request_missing_info`/`escalate`;
  prose tightened to hold the 700-word bound (694 words / 93 lines); `qwen2.5:1.5b` kept.
- `DESCRIPTION.md` — a v1.1 capability clause (durable gate over `checkpoints.db`; retrieval-grounded
  `no_match` deferral banner); 326 prose words.
- `STATUS.md` — measured-default model, linked ARCHITECTURE, desk-surface + gate reflected, G7
  resolved, SOTA present/partial rows, 453-test count.
- `docs/REQUIREMENTS.md` — seven tools, exercised BW-3, JC-3 keeps the clinician declaration, ST-1
  rehearsed, G-11 re-scoped, dated 2026-10-13.
- `docs/ROADMAP.md` — v1.1 milestone noted; still a packaging doc that links.
- `docs/DECISIONS.md` — D25 close-out row.

## Decisions Made

- **D25** — the milestone close is demonstrated-not-claimed: data-only live extension (fresh process),
  the committed `EVALS.md` projection + live failure beat as the on-screen measured artefact, the
  declared clinical-fit gap with an empty attributed slot, and the two human steps flagged.
- The ARCHITECTURE refresh is word-budget-neutral by construction (replace/tighten), not by relaxing
  the guard.

## Deviations from Plan

None - plan executed exactly as written. The only judgement call was collapsing the four real graph
nodes into three added table rows (one combined terminal row) and reclaiming the words from the §1–§8
prose, exactly as the plan's Pitfall-5 guidance directed.

## Auth Gates

None.

## Known Stubs

None. `DESCRIPTION.md`'s durable-gate sentence references `checkpoints.db` and the desk surface, both
shipped in Phases 6 and 10; no placeholder text was introduced.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change. The plan's
threat-model mitigations are in place: T-12-10 (STATUS/REQUIREMENTS link `EVALS.md`/`ARCHITECTURE.md`
instead of restating a number; the close-out grep finds no stale token), T-12-11 (no guard file was
edited; the ARCHITECTURE word/line bound and the DESCRIPTION ±10% bound are re-run and unrelaxed), and
T-12-12 (resolved work reads resolved; the clinician gap and the un-uploaded video stay OPEN and human).

## Human-Needed Steps (flagged, not claimed — carried from 12-02)

1. **Record and publicly upload the demo video** — the one submission blocker (STATUS G1 / G-9).
2. **Obtain a triage nurse/clinician review** — none obtained as of 2026-10-13; README and `EVALS.md`
   §7 carry a marked, attributed, empty slot.

## Verification

- `uv run pytest -q` → **453 passed** (baseline unchanged; no source behaviour change).
- `uv run pytest tests/test_docs_final.py tests/test_demo_runbook.py tests/test_readme_runbook.py
  tests/test_desk_runbook.py tests/test_review_runbook.py -q` → **28 passed**.
- `uv run python scripts/emit_evals.py --check` → exits 0 (`EVALS.md` up to date; no generated cell
  hand-edited).
- `grep -rnE "(5 distinct tools|5 reusable tool contracts|no desk surface|not wired E2E|no spans|Known
  drift|before Day 5)"` over README, ARCHITECTURE, EVALS, DESCRIPTION, STATUS, `docs/REQUIREMENTS`,
  `docs/ROADMAP`, `docs/DEMO` → **nothing**.
- `ARCHITECTURE.md` = 694 words / 93 lines (`qwen2.5:1.5b` present); `DESCRIPTION.md` = 326 prose words.
- No repo-root `spans.jsonl` / `*.db` residue; `git status --porcelain -- src/ data/` is empty.

---

## Self-Check: PASSED

- `ARCHITECTURE.md` — FOUND
- `DESCRIPTION.md` — FOUND
- `STATUS.md` — FOUND
- `docs/REQUIREMENTS.md` — FOUND
- `docs/ROADMAP.md` — FOUND
- `docs/DECISIONS.md` — FOUND
- commit `2718bcb` — FOUND
- commit `1c87ee7` — FOUND
- commit `bba6473` — FOUND
- `uv run pytest -q` → 453 passed
- `uv run python scripts/emit_evals.py --check` → exits 0

---

*Phase: 12-live-review-demo-milestone-close-documentation*
*Completed: 2026-10-13*
