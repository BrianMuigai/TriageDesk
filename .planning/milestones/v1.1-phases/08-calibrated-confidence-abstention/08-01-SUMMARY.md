---
phase: 08-calibrated-confidence-abstention
plan: 01
subsystem: core
tags: [confidence, deferral, abstention, graph-routing, mcp-tool, safety-spine]

requires:
  - phase: 06-durable-execution-idempotent-gate
    provides: durable checkpointed graph + the gated commit the deferral must never reach
provides:
  - "`core/schema.py` confidence contract: `ConfidenceLevel`, `ConfidenceComponent`, `ConfidenceResult` (no float/percentage field)"
  - "NEW pure `core/confidence.py`: `assess(...)` four-component signal + `DEFERRAL_MIN_SATISFIED_COMPONENTS`"
  - "sixth owned MCP tool `assess_confidence` (audited, pure, store-free)"
  - "`graph/state.py` `confidence` channel; `graph/nodes.py` `_make_assess`; `graph/build.py` `route_after_assess` + `recheck -> assess -> approval_gate`"
  - "one-way safety proof suite (`tests/test_confidence.py`, `tests/test_graph_confidence.py`)"
  - "`docs/DECISIONS.md` D20 asymmetric-cost rationale"
affects: [09-retrieval-grounding, 10-desk-ux, 11-honest-evaluation, 12-milestone-close]

actuals:
  tokens: 6619
  tasks: 2
  commits: 2
  plan_head_before: 45fd1ddbdd2ddb6c4f8f17d44d48dd903250d74b
  plan_head_after: a01497384739ae6bb4a9651aebf611cf9a0b6a08

tech-stack:
  added: []
  patterns:
    - "Deterministic coverage/deferral signal as a pure core function of already-typed objects"
    - "Deferral enforced by graph topology (terminals have no edge to commit), not by convention"
    - "Deferral node placed immediately before the gate so a commit is prevented without suppressing the deterministic recheck"

key-files:
  created:
    - src/triagedesk/core/confidence.py
    - tests/test_confidence.py
    - tests/test_graph_confidence.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/graph/state.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/evals/tools.py
    - tests/conftest.py
    - tests/test_safety_spine.py
    - tests/test_mcp_server.py
    - docs/DECISIONS.md

key-decisions:
  - "The signal is four deterministic components (vitals coverage, discriminator coverage, override-vs-TEWS path, TEWS band distance) — never a model probability and never a percentage (D8-01/02/04)."
  - "`no_match` forces a deferral at `low` regardless of the other components, so a no-match case is never high confidence (D8-11)."
  - "`assess` sits immediately before `approval_gate` (recheck -> assess -> approval_gate); a deferral routes only to `escalate`/`request_missing_info`, both terminals with no edge to `commit` (D8-08/D8-12)."
  - "`DEFERRAL_MIN_SATISFIED_COMPONENTS = 2` is a named constant derived from the D20 asymmetric cost — never tuned to make a test green (D8-09)."
  - "A deferral routes to `escalate`/`request_missing_info` with the neutral (non-deferral) arm still on `approval_gate`; `route_after_score` and the `score` mapping are untouched, so the deterministic recheck still runs before the signal is consulted."

patterns-established:
  - "Pure coverage signal: `core/confidence.assess` mirrors `core/scorer.py`'s purity and reads bands/categories only through `core/rules.py`."
  - "One-way caution: confidence can only route to a safety terminal; it never reaches `commit` and never changes a scored colour."

requirements-completed: [AGENT-02]

coverage:
  - id: D1
    description: "`assess_confidence` returns a deterministic four-component coverage/deferral signal (vitals, discriminator, override-vs-TEWS, TEWS band distance)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_confidence.py#test_assess_reports_the_four_named_components"
        status: pass
      - kind: unit
        ref: "tests/test_confidence.py#test_assess_is_deterministic"
        status: pass
    human_judgment: false
  - id: D2
    description: "The contract carries no float and nothing readable as a clinical probability (deferral bool + closed-set level + component breakdown + reason)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_confidence.py#test_contract_carries_no_float_or_probability_field"
        status: pass
    human_judgment: false
  - id: D3
    description: "A deferral routes only to `escalate`/`request_missing_info`; it never reaches `commit` and writes no queue row, while the scored colour is unchanged."
    requirement: "AGENT-02"
    verification:
      - kind: integration
        ref: "tests/test_graph_confidence.py#test_a_forced_deferral_ends_at_a_terminal_with_no_write"
        status: pass
      - kind: integration
        ref: "tests/test_graph_confidence.py#test_assess_does_not_change_the_scored_colour"
        status: pass
      - kind: unit
        ref: "tests/test_graph_confidence.py#test_a_deferral_cannot_reach_the_commit"
        status: pass
    human_judgment: false
  - id: D4
    description: "`no_match` forces a deferral and E-09 ends at a terminal with no queue row; the scorer has no confidence input."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_confidence.py#test_no_match_forces_a_deferral_never_high_confidence"
        status: pass
      - kind: integration
        ref: "tests/test_graph_confidence.py#test_no_match_e09_defers_to_a_terminal_without_a_queue_row"
        status: pass
      - kind: unit
        ref: "tests/test_confidence.py#test_scorer_has_no_confidence_input_and_does_not_import_confidence"
        status: pass
    human_judgment: false
  - id: D5
    description: "The owned-tool allowlist is exactly six and `assess_confidence` is registered, audited once, and pure (no queue row)."
    requirement: "AGENT-02"
    verification:
      - kind: unit
        ref: "tests/test_safety_spine.py#test_graph_startup_asserts_the_tool_allowlist"
        status: pass
      - kind: integration
        ref: "tests/test_graph_confidence.py#test_assess_confidence_is_pure_and_audited_exactly_once"
        status: pass
    human_judgment: false
  - id: D6
    description: "`docs/DECISIONS.md` D20 records the asymmetric-cost rationale for `DEFERRAL_MIN_SATISFIED_COMPONENTS`."
    verification: []
    human_judgment: true
    rationale: "The decision record is prose rationale (why a missed emergency vastly outweighs a needless deferral); its correctness is a human read, not a test."

duration: 19min
completed: 2026-10-12
status: complete
---

# Phase 8 Plan 01: Calibrated Confidence & Abstention Summary

**A deterministic four-component coverage/deferral signal with a sixth owned `assess_confidence` tool and an `assess` node that routes a deferral to `escalate`/`request_missing_info` — never to `commit`, never downgrading a colour.**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-10-12T15:38:00Z (approx)
- **Completed:** 2026-10-12T15:57:16Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added the ONE-schema confidence contract (`ConfidenceLevel`, `ConfidenceComponent`, `ConfidenceResult`) with deliberately **no** float/`score`/`probability`/`percent` field — a model-derived number is unrepresentable, proven by a shape test (D8-02/D8-04, T-08-01).
- Created the pure `core/confidence.py` (`assess` + `DEFERRAL_MIN_SATISFIED_COMPONENTS`): four deterministic components read bands/categories only through `core/rules.py`, never re-deriving a colour (D8-01/D8-03, T-08-03).
- Added the sixth owned tool `assess_confidence` (audited by the ONE interceptor, pure — no store, no token, no queue row) and grew the set-equality allowlist **five → six** across all three sites in one atomic commit (`graph/build.py`, `mcp/server.py`, `evals/tools.py`, `tests/conftest.py`, `tests/test_safety_spine.py`) (D8-05/D8-06/D8-07).
- Wired the `assess` node **immediately before `approval_gate`** (`recheck → assess → approval_gate`), so a deferral prevents a commit without suppressing the deterministic recheck; the `score` mapping and `route_after_score` are untouched (D8-08, A4).
- Proved the one-way property: a forced deferral on an otherwise-committing case ends at a terminal with no `__interrupt__`, no `commit_priority` call and `memory_store.rows == []`; `no_match` is never high confidence; the scorer has no confidence input (D8-11/D8-12).

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end `assess_confidence` deferral — one case path through every layer** - `fd77bbc` (feat)
2. **Task 2: Prove the one-way safety property and record the asymmetric-cost decision** - `a014973` (test)

**Plan metadata:** not committed — `commit_docs: false` in this workspace (see below).

_Note: not a TDD plan; each task is one commit._

## Files Created/Modified

- `src/triagedesk/core/schema.py` - `ConfidenceLevel`, `ConfidenceComponent`, `ConfidenceResult` (the ONE schema module).
- `src/triagedesk/core/confidence.py` (NEW) - pure `assess(...)` four-component signal + `DEFERRAL_MIN_SATISFIED_COMPONENTS`.
- `src/triagedesk/graph/state.py` - the `confidence` channel.
- `src/triagedesk/graph/nodes.py` - `_make_assess` factory + registration.
- `src/triagedesk/graph/build.py` - allowlist (+1), `TRACER_NODES` (+1), `route_after_assess`, the `recheck → assess` edge, `__all__`, docstring topology.
- `src/triagedesk/mcp/server.py` - the sixth owned tool `assess_confidence` (audited, pure).
- `src/triagedesk/evals/tools.py` - the sixth tool closure on the eval factory.
- `tests/conftest.py` - the sixth-tool fake (calls the real `core.confidence.assess`).
- `tests/test_safety_spine.py` - exact-set allowlist assertion updated to six.
- `tests/test_mcp_server.py` - superset comment updated five → six.
- `tests/test_confidence.py` (NEW) - pure-signal unit + contract-shape + one-way guards.
- `tests/test_graph_confidence.py` (NEW) - deferral routing / no-write integration proofs.
- `docs/DECISIONS.md` - D20 asymmetric-cost rationale.

## Decisions Made

- Placement (binding): `assess` sits immediately before `approval_gate`; the direct `recheck → approval_gate` edge was replaced by `recheck → assess → approval_gate`, and `route_after_score` + the `score` mapping were left untouched (the plan's revised A4/D8-08).
- `route_after_assess`'s neutral arm is `approval_gate`; the `request_missing_info` deferral arm is defensive/unreachable in practice (a deferral only occurs after `route_after_score` has already diverted any missing-vitals case), so an observed deferral routes to `escalate` — stated honestly rather than pretended.
- `DEFERRAL_MIN_SATISFIED_COMPONENTS = 2` is the named constant; the level thresholds (high ≥ 3, moderate ≥ 2, else low) are single-digit structural margins, not clinical values.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced.

## Threat Flags

None. Every file touches only the plan's declared trust boundaries (graph node → owned tool, owned server → audit interceptor, claim → reader); the mitigations T-08-01…T-08-05 are implemented and tested.

## Issues Encountered

- **Knowingly red until Plan 02 (the plan's explicit D8-11 carve-out, not a regression).** After Plan 01 alone, 6 existing tests fail because the `no_match` override moves E-01/E-07/E-08/E-09/E-13/E-14 to a terminal: `tests/test_scorer_baseline.py::test_e08_reaches_the_gate_and_delivers_a_sourced_green_card`, `tests/test_eval_honest_terminal.py::test_delivered_run_records_its_colour_and_delivered`, `tests/test_eval_invariants.py` (2), `tests/test_eval_suite.py` (2). All six are in **Plan 02's** `files_modified` (the plan states Plan 02 owns "the updates to every existing test whose measured outcome moves"); the fixtures, the override and the thresholds were **not** adjusted. The plan's scoped verification command (9 files, 55 tests) is fully green; the phase-level `uv run pytest -q` is green at phase end (Plan 02/03).
- **`commit_docs` is `false`** in this workspace, so the SUMMARY/STATE/ROADMAP edits are made on disk but not committed (the established, documented workspace posture — see STATE.md).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 08-02 (measurement + accounting): the signal is persisted on the `confidence` channel for the runner/report to read, and the deferral terminal is in place.
- Plan 02 must (per its own plan) update the six moved-outcome tests and add the deferral rate / calibration fields; it must not retune the fixture or the threshold.

---
*Phase: 08-calibrated-confidence-abstention*
*Completed: 2026-10-12*

## Self-Check: PASSED

- FOUND: src/triagedesk/core/confidence.py
- FOUND: tests/test_confidence.py
- FOUND: tests/test_graph_confidence.py
- FOUND: .planning/phases/08-calibrated-confidence-abstention/08-01-SUMMARY.md
- FOUND: commit fd77bbc (Task 1)
- FOUND: commit a014973 (Task 2)
- Plan metadata commit: skipped (`skipped_commit_docs_false`)

