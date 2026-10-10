---
phase: 04-evaluation-recovery-honest-failure
plan: 05
subsystem: testing
tags: [eval, invariants, scorer, citations, sats-tews, gap-closure, langgraph]

# Dependency graph
requires:
  - phase: 04-evaluation-recovery-honest-failure
    provides: the executable invariant evaluator (INV-1..4) and the honest eval harness that surfaced gap G-1
  - phase: 03-graph-safety-gate
    provides: graph/nodes.verify (the citation evidence check) and the approval-gate graph
  - phase: 02-deterministic-scorer
    provides: core/scorer.score_priority and the ONE citation helper (core/citations.format_citation)
provides:
  - a data-driven baseline citation (data/sats_tews.yaml baseline_citation) so a rule-less TEWS-0 priority is sourced
  - a cited TEWS-0 scorer contract where citations stay 1:1 with triggered_rules by construction
  - a strengthened INV-1 that fails any scored priority carrying zero citations
  - regression proofs incl. E-08 delivering a sourced GREEN card through the approval gate
affects: [evaluation-recovery-honest-failure, demo-docs-freeze]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 3133
  tasks: 2
  commits: 2

# Measured commit ledger (#3968, #4670) — read by verify-work's same-instrument reconciliation.
commits: 2
plan_head_before: 1a3a89eac2b5cd439c4c79589aa98a090d7d4ac1
plan_head_after: c7755ba101e2399651c8ca391855cf30d4c42ed8

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rule-less-but-scored evidence: a synthetic baseline entry is emitted only when no rule/override fired, keeping a real finding from ever being displaced"
    - "Machine-authority evidence text: the baseline reference lives in data/*.yaml and is formatted through the ONE citation helper, never inlined in code"

key-files:
  created:
    - tests/test_scorer_baseline.py
  modified:
    - data/sats_tews.yaml
    - src/triagedesk/core/rules.py
    - src/triagedesk/core/scorer.py
    - src/triagedesk/evals/invariants.py

key-decisions:
  - "The baseline citation is data-driven (data/sats_tews.yaml baseline_citation) and formatted through core/citations.format_citation; no reference string is inlined in code (CONVENTIONS §1, DRY)."
  - "The baseline rule is appended ONLY when no band rule AND no discriminator override fired AND at least one parameter was used, so a real finding is never replaced by baseline evidence (T-04-22)."
  - "citations == [rule.citation for rule in triggered_rules] holds by construction after the baseline is appended, so the shipped citation invariant is preserved (SCORE-03)."
  - "graph/nodes.verify is left unchanged: a genuinely uncited priority still fail-closes; only the scorer contract changed, not the safety check (T-04-24)."
  - "INV-1 is strengthened to fail a scored priority (a colour that is neither abstained nor out-of-scope) carrying zero citations; the baseline now makes that a genuine defect (T-04-23, EVAL-03)."

patterns-established:
  - "Baseline evidence: a rule-less in-scope priority gains exactly one data-driven citation so the routine patient is served, not silenced"
  - "Honest invariant: the citation contract is enforced at both the graph (verify) and the eval (INV-1) level"

requirements-completed: [EVAL-01, EVAL-03]

coverage:
  - id: D1
    description: "A routine, all-normal-vitals (TEWS 0) in-scope case is sourced by exactly one data-driven baseline citation, with citations == triggered_rules held by construction."
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/test_scorer_baseline.py#test_a_tews_zero_case_is_sourced_by_the_baseline_citation"
        status: pass
    human_judgment: false
  - id: D2
    description: "The routine patient (E-08) reaches the approval gate and, on an unapproved resume, receives a sourced GREEN handover card instead of a fail-closed END."
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/test_scorer_baseline.py#test_e08_reaches_the_gate_and_delivers_a_sourced_green_card"
        status: pass
      - kind: integration
        ref: "uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.ci.json --offline (exit 0; E-08 GREEN with citations, INV-1 true)"
        status: pass
    human_judgment: false
  - id: D3
    description: "INV-1 fails any scored priority carrying zero citations and passes the baseline-cited TEWS-0 priority, so the citation contract gates the exit code."
    requirement: "EVAL-03"
    verification:
      - kind: unit
        ref: "tests/test_scorer_baseline.py#test_inv1_fails_a_scored_priority_with_no_citation"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-10-09
status: complete
---

# Phase 4 Plan 5: Baseline citation & honest INV-1 Summary

**A routine all-normal-vitals (TEWS 0) patient is now sourced by a data-driven baseline citation and reaches the approval gate — the core value holds for the TEWS-0 family — while a scored priority with zero citations is now a genuine INV-1 failure.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-09T20:44:06Z
- **Completed:** 2026-10-09T20:51:02Z
- **Tasks:** 2
- **Files modified:** 5 (4 modified, 1 created)

## Accomplishments

- **Gap G-1 closed:** a rule-less, in-scope TEWS-0 priority now carries exactly one baseline citation, so `graph/nodes.verify`'s `has_evidence` check holds and the run proceeds to the gate instead of fail-closing to `END`.
- **Core value restored for routine patients:** E-08 (RR 14, HR 80, SBP 120, T 36.8, walking, alert, no trauma) pauses at the approval gate and, on an unapproved resume, delivers a **sourced GREEN handover card** — the nurse gets a confirmable priority, not silence.
- **Citation contract preserved honestly:** the baseline is emitted only when no rule and no discriminator override fired and a parameter was used, so a real finding is never displaced; `citations == [rule.citation for rule in triggered_rules]` holds by construction.
- **INV-1 hole closed:** `_check_inv1` now fails any *scored* priority (a colour that is neither abstained nor out-of-scope) carrying zero citations, so the citation contract gates the CI exit code (EVAL-03). `graph/nodes.verify` was deliberately left unchanged — a genuinely uncited priority still fail-closes.
- **Data-driven, not inlined:** the baseline reference text lives in `data/sats_tews.yaml` and is formatted through the ONE citation helper (`core/citations.format_citation`), honouring CONVENTIONS §1 (DRY).

## Task Commits

Each task was committed atomically:

1. **Task 1: Baseline citation so a TEWS-0 priority is sourced and reaches the gate** - `1a238e3` (feat)
2. **Task 2: Strengthen INV-1 so a scored priority must carry a citation** - `c7755ba` (feat)

**Plan metadata:** (docs commit, below)

## Files Created/Modified

- `data/sats_tews.yaml` - added the `baseline_citation` key (the no-rule-fired reference; machine authority)
- `src/triagedesk/core/rules.py` - `TewsRules` gains the `baseline_citation: str` field (loaded, never hard-coded)
- `src/triagedesk/core/scorer.py` - appends exactly ONE baseline `TriggeredRule` when no rule/override fired and a parameter was used; citation built via the ONE helper
- `src/triagedesk/evals/invariants.py` - `_check_inv1` fails a scored priority with zero citations
- `tests/test_scorer_baseline.py` - proves the TEWS-0 sourcing, the firing/override cases staying unchanged, the abstained case staying uncited, the E-08 sourced GREEN card through the gate, and the strengthened INV-1

## Decisions Made

- The baseline citation is data-driven (`data/sats_tews.yaml` → `TewsRules.baseline_citation`) and formatted through `core/citations.format_citation`; no reference string is inlined in code (CONVENTIONS §1).
- The baseline is appended only when `not triggered and used` — i.e. no band rule and no discriminator override fired and at least one parameter was present — so a real finding is never replaced by baseline evidence (T-04-22).
- `citations` stays derived 1:1 from `triggered_rules` after the baseline is appended, so the shipped citation invariant holds by construction (SCORE-03).
- `graph/nodes.verify` was left unchanged: a genuinely uncited priority still fail-closes; the fix is confined to the scorer contract (T-04-24).
- INV-1 now fails a scored priority with zero citations; the baseline makes that a genuine defect rather than an artefact of firing no rule (T-04-23, EVAL-03).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The repository's `main` branch is a protected branch, but this project uses `branching_strategy: none` with worktree isolation disabled and all prior Phase-4 plan commits live on `main`. Per the execute-phase protected-branch step for the `"none"` strategy (which warns but continues on the current branch), the two task commits were made on `main`, consistent with the established project practice. No phase branch was created.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. No placeholder values, TODOs, or unwired data paths were introduced. The baseline citation is real, data-driven evidence rendered through the shipped citation helper.

## Threat Flags

None. The change introduces no new network endpoint, auth path, file-access pattern, or schema change at a trust boundary — it is one data key plus a pure-scorer edit using existing modules, plus an invariant predicate strengthening.

## Verification

- `uv run pytest tests/test_scorer_baseline.py -x` — 5 passed (Task 1).
- `uv run pytest tests/test_scorer_baseline.py tests/test_eval_invariants.py -x` — 13 passed (Task 2).
- Full suite `uv run pytest -q` — **212 passed** (was 206; +6 new baseline/invariant proofs).
- `uv run ruff check` — All checks passed.
- `uv run mypy src/triagedesk/core/scorer.py src/triagedesk/evals/invariants.py` — Success, no issues.
- Offline eval gate `uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.ci.json --offline` — **exit 0**; E-08 records GREEN with the baseline citation and `INV-1=true`; the aggregate INV-1 verdict is true; the declared failure E-09 remains the sole accuracy miss.
- `graph/nodes.py::verify` unchanged (diff confirms no edit).

## Next Phase Readiness

- Gap G-1 and the mirrored INV-1 hole are closed; the TEWS-0 family now yields a sourced, confirmable GREEN card through the gate.
- The real measured report (`evals/results/report.json`) predates this change; re-running the live model (`triagedesk eval` without `--offline`) and regenerating EVALS.md would refresh the published measured artefact. This was out of scope for this gap-closure plan (no new dependency; the change is data + pure-scorer + invariant only).

---
*Phase: 04-evaluation-recovery-honest-failure*
*Completed: 2026-10-09*

## Self-Check: PASSED

- `tests/test_scorer_baseline.py` — FOUND
- Commit `1a238e3` — FOUND (ancestor of HEAD)
- Commit `c7755ba` — FOUND (ancestor of HEAD)
