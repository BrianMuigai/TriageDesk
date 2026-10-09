---
phase: 02-deterministic-scorer-own-mcp-server
plan: 01
subsystem: core
tags: [python, pydantic, mcp, sats, tews, deterministic-scorer, citations, fail-closed]

# Dependency graph
requires:
  - phase: 01-sats-foundations-risk-retirement
    provides: "data/sats_tews.yaml + core/rules.py loader, core/citations.py helper, core/schema.py, mcp/server.py + mcp/adapter.py"
provides:
  - "core/scorer.py — the pure deterministic score_priority (TEWS from data, citations == triggered_rules, no model)"
  - "PriorityResult / TriggeredRule contracts in the one schema module; CaseInput gains age_months + age_ambiguous"
  - "mcp/server.py exposes score_priority as a thin owned tool (no model on this path)"
  - "scripts/spike_score.py — end-to-end typed case -> cited score -> owned tool"
  - "tests/test_scorer.py + test_scorer_safety.py + test_scorer_edges.py — the scorer's proof suite"
affects: [02-02, 02-03, phase-3, phase-4]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 60000, raw_tokens: 42000).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 9097        # chars/4 over the realized diff (36388 chars, src/tests/scripts; no generated files)
  raw_tokens: 9097    # same — nothing generated in this plan
  tasks: 3
  commits: 4
  plan_head_before: e2bd3797eef1aa335a87ad62ae5bc1c8c13b53ee
  plan_head_after: 199cf86a8f7c999425448881657276210347f6ce

tech-stack:
  added: []
  patterns:
    - "Pure scorer in core/: bands/thresholds/colours read only from data/sats_tews.yaml (no SATS literal)"
    - "Citation invariant by construction: citations = [rule.citation for rule in triggered_rules]"
    - "Fail-closed out-of-scope predicate (paediatric / missing / months / ambiguous age abstains)"
    - "Missing vitals reported, never imputed (used_vitals subset of nurse-provided fields)"
    - "Structural parameter->schema-field binding (temperature -> temperature_c) — no clinical value"

key-files:
  created:
    - src/triagedesk/core/scorer.py
    - scripts/spike_score.py
    - tests/test_scorer.py
    - tests/test_scorer_safety.py
    - tests/test_scorer_edges.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/mcp/server.py
    - tests/test_mcp_server.py

key-decisions:
  - "score_priority is a thin MCP tool over the pure core function; the tool touches no model, so no number can enter the score path (D-02, T-02-01)."
  - "The scorer iterates the loaded parameter keys and binds each to its schema field structurally (temperature -> temperature_c), so adding a parameter to the YAML auto-scores without editing the scorer (CONVENTIONS §1, SOLID: O)."
  - "Boolean parameters (trauma) map to their highest/lowest-points band by data, so the yes/no tokens are never inlined (DRY guard)."
  - "Gap distances are compared with a relative tolerance so an exact tie (temperature 34.95) resolves to the fail-closed higher-points band (SCORE-05)."
  - "The Phase-1 tool-surface test became a superset check so the surface may grow without re-editing the regression."

patterns-established:
  - "Tracer-first: one real typed case through core -> mcp before any expansion"
  - "Safety branches ship with the scorer, not after (fail-closed is correctness, not a feature)"

requirements-completed: [SCORE-01, SCORE-03, SCORE-04, SCORE-05, INTAKE-03, TOOL-03]

coverage:
  - id: D1
    description: "A typed adult case with complete vitals yields a colour, a TEWS total and a target time computed with no model involvement, exposed through the owned score_priority tool."
    requirement: "SCORE-01"
    verification:
      - kind: e2e
        ref: "uv run python scripts/spike_score.py"
        status: pass
      - kind: unit
        ref: "tests/test_scorer.py#test_pure_score_returns_a_cited_colour_with_no_model"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every priority's citations correspond 1:1 with its triggered rules (citations == triggered_rules)."
    requirement: "SCORE-03"
    verification:
      - kind: unit
        ref: "tests/test_scorer.py#test_pure_score_citations_match_triggered_rules_one_to_one"
        status: pass
    human_judgment: false
  - id: D3
    description: "Paediatric / missing-age / months-expressed / ambiguous-age input abstains and escalates and never receives an adult colour."
    requirement: "SCORE-04"
    verification:
      - kind: unit
        ref: "tests/test_scorer_safety.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "A missing scored vital is reported and never imputed; the score uses only nurse-provided fields."
    requirement: "INTAKE-03"
    verification:
      - kind: unit
        ref: "tests/test_scorer_safety.py#test_missing_vital_is_reported_and_never_imputed"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every TEWS band edge (both sides), the temperature gap value and every TEWS->colour boundary are correct; identical inputs give identical colour and citation set."
    requirement: "SCORE-05"
    verification:
      - kind: unit
        ref: "tests/test_scorer_edges.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "The owned MCP server exposes the score_priority tool, contract-typed to the shared PriorityResult schema."
    requirement: "TOOL-03"
    verification:
      - kind: unit
        ref: "tests/test_scorer.py#test_owned_score_priority_tool_returns_the_shared_contract"
        status: pass
    human_judgment: false

duration: 16min
completed: 2026-10-09
status: complete
---

# Phase 2 Plan 01: Deterministic Scorer & Own MCP Server Summary

**A pure `score_priority` turns a typed case into a cited SATS colour, TEWS total and target time from data alone — `citations == triggered_rules`, missing vitals never imputed, out-of-scope input fails closed — and the owned MCP server exposes it as `score_priority`.**

## Performance

- **Duration:** ~16 min (14:32Z → 14:48Z)
- **Started:** 2026-10-09T14:32:23Z
- **Completed:** 2026-10-09T14:48:07Z
- **Tasks:** 3/3
- **Files modified:** 8 (5 created, 3 modified)

## Accomplishments

- **The phase architecture is proven end-to-end on one real slice.** `scripts/spike_score.py` builds a fixed adult case, scores it in `core/`, lists the owned tools through `load_tools()`, calls `score_priority` and asserts the tool payload equals the pure result with one citation per triggered rule — exit 0.
- **No number comes from the model (D-02).** `core/scorer.py` imports nothing from `llm|mcp|store` (purity guard green); every band, threshold, colour, target and destination is read from `data/sats_tews.yaml` via the one loader; the DRY guard confirms no SATS literal leaked into `src/`.
- **The citation invariant holds by construction (D-01/SCORE-03):** `citations = [rule.citation for rule in triggered_rules]`, each citation produced by the one helper `format_citation`.
- **Fail-closed safety (D-03/D-04):** paediatric, missing-age, months-expressed and ambiguous-age input abstains with a reason and never yields an adult colour; a missing scored vital is listed in `missing_vitals` and contributes zero points — never defaulted to a 0-point band.
- **Band totality (SCORE-05):** every numeric band edge is inclusive and correct on both sides, the temperature gap value (34.95) resolves to the fail-closed higher-points band, and every TEWS→colour boundary is exact.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end typed case → cited score through the owned score_priority tool (tracer)** - `41d4a8f` (feat)
2. **Task 2: Fail-closed out-of-scope and missing-vital detection** - `b4dfbd6` (test)
3. **Task 3: Exhaustive band-edge, colour-boundary and determinism tests** - `199cf86` (test), preceded by the tie-break fix `1e066b8` (fix)

**Plan metadata:** committed together with this SUMMARY and STATE.md (docs: complete plan)

_Note: TDD tasks may have multiple commits (test → feat → refactor). See "Deviations" — Task 2's RED collapsed to GREEN because the safety branches shipped with the Task-1 tracer (Rule 2)._

## Files Created/Modified

- `src/triagedesk/core/scorer.py` — the pure `score_priority` (band selection, gap totality, colour mapping, citation derivation, out-of-scope/missing-vital branches) and the `case_field` parameter→field binding
- `src/triagedesk/core/schema.py` — added `TriggeredRule`, `PriorityResult`; added `age_months` + `age_ambiguous` to `CaseInput`
- `src/triagedesk/mcp/server.py` — added the `score_priority` tool (thin adapter over the pure function; `normalize_case` untouched)
- `scripts/spike_score.py` — the end-to-end tracer verification
- `tests/test_scorer.py` — pure-function + in-memory MCP-tool contract tests
- `tests/test_scorer_safety.py` — fail-closed out-of-scope + missing-vital tests
- `tests/test_scorer_edges.py` — exhaustive band-edge / colour-boundary / determinism tests
- `tests/test_mcp_server.py` — tool-surface test relaxed to a superset check (growth allowed)

## Decisions Made

- **The MCP tool is a thin adapter over the pure function.** `score_priority` calls `core.scorer.score_priority` and touches no model, so the score path cannot be contaminated (SOLID: S/D, T-02-01).
- **Parameter keys bind to schema fields structurally.** The YAML key `temperature` maps to the schema field `temperature_c` via `case_field()` (exact match, else unique prefix) — no clinical value is inlined and a new YAML parameter auto-scores (SOLID: O).
- **Boolean parameters are band-mapped by points.** `trauma` maps to its highest/lowest-points band, so the `yes`/`no` tokens never appear as literals (DRY guard).
- **Gap ties are tolerance-aware.** Exact-tie edge distance resolves to the higher-points band so a valid in-range value never under-triages.
- **`used_vitals` added to `PriorityResult`** so a caller can verify the score's inputs are a subset of the nurse-provided fields (INTAKE-03).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fail-closed safety branches shipped with the Task-1 tracer**
- **Found during:** Task 1 (tracer)
- **Issue:** The plan sequenced the out-of-scope and missing-vital branches into Task 2, but a scorer that returns an adult colour for a paediatric/missing-age case is unsafe the moment it exists (D-03, T-02-04). Leaving the tracer's scorer fail-open would have shipped a known safety hole after Task 1.
- **Fix:** Implemented the out-of-scope predicate and `missing_vitals` detection in `core/scorer.py` alongside the tracer; Task 2 then added the proving test suite. Task 2's TDD RED therefore collapsed to GREEN (the feature already existed) — documented here rather than fabricating a RED.
- **Files modified:** `src/triagedesk/core/scorer.py`
- **Verification:** `tests/test_scorer_safety.py` (11 tests) pass.
- **Committed in:** `41d4a8f` (Task 1) and `b4dfbd6` (Task 2 tests)

**2. [Rule 1 - Bug] Parameter key `temperature` did not match the schema field `temperature_c`**
- **Found during:** Task 1 (tracer spike)
- **Issue:** Iterating the loaded parameter keys and reading `getattr(case, name)` silently treated `temperature` as missing (the field is `temperature_c`), dropping the temperature contribution and under-scoring the case (tews 4 instead of 6).
- **Fix:** Added `case_field()` — exact field-name match, else the unique field whose name starts with the parameter key — and used it in the scorer and tests.
- **Files modified:** `src/triagedesk/core/scorer.py`, `tests/test_scorer.py`
- **Verification:** The spike now reports ORANGE/tews 6; `tests/test_scorer.py` passes.
- **Committed in:** `41d4a8f` (Task 1)

**3. [Rule 1 - Bug] Floating-point tie-break under-triaged the temperature gap value**
- **Found during:** Task 3 (band-edge tests)
- **Issue:** 34.95 °C is mathematically equidistant from the `< 35` band (34.9) and the `35.0-38.4` band (35.0), but binary floating point made `35.0-34.95` a hair smaller, so the 0-point band won and the value was under-triaged.
- **Fix:** Compare gap distances with a relative tolerance and, on a tie, select the higher-points band (never under-triage); band selection stays total over the schema's accepted range.
- **Files modified:** `src/triagedesk/core/scorer.py`
- **Verification:** `tests/test_scorer_edges.py#test_temperature_gap_value_is_total_and_fail_closed` passes.
- **Committed in:** `1e066b8` (Task 3 fix commit)

**4. [Rule 3 - Blocking] The MCP adapter returns content blocks, not a bare payload**
- **Found during:** Task 1 (tracer spike)
- **Issue:** `load_tools()`'s tool returns a list of MCP content blocks (`[{"type": "text", "text": "<json>"}]`), so validating the payload directly failed; the in-memory `Client` returns the JSON text directly.
- **Fix:** `scripts/spike_score.py` `_as_priority()` accepts a `PriorityResult`, a content-block list, a dict, or JSON text.
- **Files modified:** `scripts/spike_score.py`
- **Verification:** `uv run python scripts/spike_score.py` exits 0.
- **Committed in:** `41d4a8f` (Task 1)

---

**Total deviations:** 4 auto-fixed (2 bugs, 1 missing critical, 1 blocking)
**Impact on plan:** All auto-fixes were necessary for correctness (fail-closed safety, an under-scoring field binding, an under-triage tie-break) or to unblock the tracer. No scope creep; the scorer stays pure and data-driven.

## Issues Encountered

- **Task 2 is marked `tdd="true"` but no genuine RED was possible** — the safety branches were already implemented in Task 1 (deviation 1). The test suite (`tests/test_scorer_safety.py`) now locks the behaviour. `workflow.tdd_mode` is disabled and this plan is `type: execute`, so the plan-level RED/GREEN gate is not enforced; no `## TDD Gate Compliance` violation is recorded.

## User Setup Required

None - no external service configuration required. (No package installs occurred; the reserved package-legitimacy gate stays in force for any future install.)

## Next Phase Readiness

- `core/scorer.py` is a pure, cited, fail-closed scorer with a complete proof suite (22 scorer tests); `mcp/server.py` exposes both `normalize_case` and `score_priority`.
- **For Plan 02-02 (discriminators):** `score_priority` already accepts `matched_discriminator_ids` and passes them through to `PriorityResult`; the discriminator override (most-urgent wins) is the next seam to fill, sourcing the closed set from `data/sats_discriminators.yaml`.
- **For Plan 02-03 (remaining owned tools):** the pattern is set — a thin `@server.tool()` adapter over a pure `core/` function, contract-typed to the shared schema.
- **Carried forward:** the borrowed `mcp-sqlite` handshake and `matched_discriminator_ids` closed-set sourcing remain as noted from Phase 1.

---

*Phase: 02-deterministic-scorer-own-mcp-server*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 8 key files exist on disk (scorer, schema, server, spike, 4 test files).
- All 4 plan commits are ancestors of HEAD: `41d4a8f`, `b4dfbd6`, `1e066b8`, `199cf86`.
- Full suite green: `uv run pytest -q` → 81 passed; `uv run python scripts/spike_score.py` → exit 0.
