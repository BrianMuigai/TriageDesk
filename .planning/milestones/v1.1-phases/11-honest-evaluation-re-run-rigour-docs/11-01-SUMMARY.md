---
phase: 11-honest-evaluation-re-run-rigour-docs
plan: 01
subsystem: evals
tags: [eval-fidelity, structured-output, pydantic-schema, ollama, provenance, digest]

# Dependency graph
requires:
  - phase: 10-desk-ux-real-approval-gate
    provides: the shipped CLI + desk surface (unchanged here)
  - phase: 08-calibrated-confidence-abstention
    provides: the report digest + the deferral-aware gate (consumed, unchanged)
provides:
  - "a general `CaseInput.age_years` Field(description=…) at the extraction seam (the E-04 fix)"
  - "a general serial-vitals Field(description=…) on the scored vitals (RR/HR/SBP)"
  - "the repaired E-07 fixture note (D11-14; expectation unchanged)"
  - "Provenance.extraction_schema_hash sealing the model INPUT, covered by report_digest"
  - "tests/test_eval_fidelity.py — the hermetic contract + fixture-consistency guards"
  - "docs/DECISIONS.md ### D24"
affects: [11-02 (the re-run + published artefacts), 12 (live technical review)]

# Actuals (#2632) — chars/4 over the realized diff, not a harness token count.
actuals:
  tokens: 5667
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []            # no new dependency (the phase installs nothing)
  patterns:
    - "Fix extraction fidelity at the CONTRACT the model fills (the schema), not by prose-engineering the prompt"
    - "Seal the model INPUT (the extraction schema) into the report provenance beside the prompt hash"

key-files:
  created:
    - tests/test_eval_fidelity.py
  modified:
    - src/triagedesk/core/schema.py
    - evals/cases/E-07.yaml
    - src/triagedesk/evals/report.py
    - tests/test_eval_report.py
    - tests/test_eval_honest_terminal.py
    - docs/DECISIONS.md

key-decisions:
  - "E-04 is an age-fidelity failure, not a discriminator-retrieval failure: fix the `age_years` contract, never the matcher"
  - "The 1.5B model is schema-sensitive: a generic example number ('a 74 year old patient') is required, and the age description must be emphatic enough to survive the larger contract"
  - "The scored-vitals serial description resolves a `before -> after` reading to the AFTER (current) value"
  - "E-07's fixture note is repaired to state its golden temperature (D11-14); the expectation stays RECHECK"
  - "Provenance.extraction_schema_hash is defaulted + excluded-from-digest-when-unset so the committed report.json stays valid until 11-02 regenerates it"

patterns-established:
  - "Contract-level fidelity fix: the model is a contract filler; the honest lever is the schema it fills (CONVENTIONS §1)"
  - "Fixture note ↔ golden case consistency: a note states every scored vital its golden case declares (E-02/E-05 already satisfied this)"

requirements-completed: [EVAL-06]

coverage:
  - id: D1
    description: "The general age contract reaches the model (model_json_schema description on age_years) and is fixture-independent"
    requirement: EVAL-06
    verification:
      - kind: unit
        ref: "tests/test_eval_fidelity.py#test_age_years_carries_a_schema_description"
        status: pass
      - kind: unit
        ref: "tests/test_eval_fidelity.py#test_age_years_description_is_general_not_tuned_to_a_fixture"
        status: pass
    human_judgment: false
  - id: D2
    description: "E-04 reaches RED on all three real runs over qwen2.5:1.5b (no null-age ABSTAIN)"
    requirement: EVAL-06
    verification:
      - kind: other
        ref: "uv run triagedesk eval --case E-04 --runs 3 (measured: colours/outcomes [RED,RED,RED])"
        status: pass
    human_judgment: true
    rationale: "The local 1.5B model is stochastic; the verifier should re-measure the real path rather than trust a single recorded run."
  - id: D3
    description: "E-07's note and golden case agree (D11-14) and E-07 reaches RECHECK on the real path"
    requirement: EVAL-06
    verification:
      - kind: unit
        ref: "tests/test_eval_fidelity.py#test_e07_note_states_every_scored_vital_its_golden_case_declares"
        status: pass
      - kind: unit
        ref: "tests/test_eval_fidelity.py#test_serial_vitals_carry_a_general_after_value_description"
        status: pass
      - kind: other
        ref: "uv run triagedesk eval --case E-07 --runs 3 (measured: outcomes [RECHECK,RECHECK,RECHECK])"
        status: pass
    human_judgment: true
    rationale: "The real-mode outcome is a stochastic model measurement; the verifier should re-measure."
  - id: D4
    description: "The report provenance seals the extraction schema (extraction_schema_hash), covered by report_digest"
    requirement: EVAL-06
    verification:
      - kind: unit
        ref: "tests/test_eval_report.py#test_provenance_seals_the_extraction_schema_hash"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_report_digest_seals_the_extraction_schema_hash"
        status: pass
      - kind: unit
        ref: "tests/test_eval_report.py#test_a_report_with_the_provenance_block_constructs_and_seals"
        status: pass
    human_judgment: false
  - id: D5
    description: "docs/DECISIONS.md records D24 (the contract-level age fix + the serial-vitals clarification + the D11-14 E-07 note repair), linking EVALS.md and restating no figure"
    verification: []
    human_judgment: true
    rationale: "An ADR-lite prose row; the correctness of its framing is a human judgment (no code control)."

# Metrics
duration: 56min
completed: 2026-10-13
status: complete
plan_head_before: 05eeccb49f5dbc1d2efa1f906bbb6fc0305b038b
plan_head_after: 9474aeaeab7268c3c44609652ed2bfa4394a7494
---

# Phase 11 Plan 01: Extraction-fidelity root causes fixed and the honest provenance sealed Summary

**E-04 fixed at the age contract and E-07 fixed by repairing its fixture note plus a general serial-vitals contract — both now reach their expected real-mode outcomes (RED×3 / RECHECK×3), and the extraction schema is sealed into the report provenance.**

## Performance

- **Duration:** 56 min
- **Started:** 2026-10-13T06:36:21Z
- **Completed:** 2026-10-13T07:32:32Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- **E-04 is fixed at its real root cause (age fidelity), not the CONTEXT's assumed cause.** The deterministic matcher already retrieved the emergency discriminator on every run; the failure was the 1.5B model intermittently dropping `age_years`, and a null age short-circuits to the fail-closed ABSTAIN. A general `Field(description=…)` on `CaseInput.age_years` now reaches the model as both the prompt text and the `format=` grammar. Measured real E-04: `colours == ['RED','RED','RED']`, `outcomes == ['RED','RED','RED']` (was `['ABSTAIN','RED','RED']` in the committed report).
- **E-07's fixture note↔golden inconsistency is repaired (D11-14) and the serial-arrow vitals are resolved.** The note now states `Temperature 36.8` (the value its golden `case` already declared); the golden `case`, `previous_case` and `expected: RECHECK` are byte-identical. The scored vitals (RR/HR/SBP) carry a general description resolving a `before -> after` reading to the AFTER (current) value. Measured real E-07: `outcomes == ['RECHECK','RECHECK','RECHECK']`.
- **The report provenance now seals the model INPUT.** `Provenance.extraction_schema_hash = hash_tool_schema(ExtractionResult.model_json_schema())` — `prompt_hash` covers the prompt template only, so a schema description changed the model input without moving it (Pitfall 4). The field is covered by `report_digest`.
- **Hermetic fidelity guards** (`tests/test_eval_fidelity.py`) pin the contract (the description reaches `model_json_schema()`; it is general — no fixture number, no SATS value) and the E-07 fixture consistency. `docs/DECISIONS.md` records **D24**.
- **No forbidden surface was touched:** `core/scorer.py`, `core/matcher.py`, `core/recheck.py`, `core/confidence.py`, `llm/prompts.py`, `uv.lock`, `evals/results/report.json`, `EVALS.md` and `evals/cases/E-04.yaml` are all unmodified. No expectation, golden value or threshold was edited; no dependency added.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "a stated age survives structuring" (E-04 → RED)** - `0c58ea6` (fix)
2. **Task 2: E-07 — repair the fixture note and resolve the serial-vitals arrow (E-07 → RECHECK)** - `3889341` (fix)
3. **Task 3: Seal the extraction schema into the report provenance + record D24** - `9474aea` (feat)

**Plan metadata:** (see the final docs commit below)

## Files Created/Modified

- `src/triagedesk/core/schema.py` - a general `age_years` description + a shared serial-vitals description on `respiratory_rate`/`heart_rate`/`systolic_bp` (the extraction-seam contract)
- `evals/cases/E-07.yaml` - the note now states `Temperature 36.8`; `case`/`previous_case`/`expected: RECHECK` unchanged (the ONE permitted fixture change, D11-14)
- `src/triagedesk/evals/report.py` - `Provenance.extraction_schema_hash` computed via `hash_tool_schema`, sealed by `report_digest`
- `tests/test_eval_fidelity.py` - the hermetic age-contract, serial-vitals-generality and E-07 fixture-consistency guards (NEW)
- `tests/test_eval_report.py` - the three provenance-sealing tests + the updated `_PROVENANCE` constructor
- `tests/test_eval_honest_terminal.py` - the updated `_synthetic_report` provenance constructor
- `docs/DECISIONS.md` - the `### D24` row

## Decisions Made

- **The fix lives at the contract, not the scorer** (D11-01): a general schema description on `age_years` and on the scored vitals — the model is a contract filler, so the honest lever is the schema it fills.
- **The description must be general** (D11-02): the age example is a generic `'a 74 year old patient'` — **not** a fixture number (validated by loading every fixture and asserting no overlap). The guard reads fixtures through the ONE loader and SATS values from the loaded substrate, so nothing is restated.
- **The age description must be emphatic to survive the larger contract.** The 1.5B model is highly schema-sensitive: the age-only description measured 10/10 clean, but adding *any* vitals description silently regressed the age to 0/8 until the age sentence was strengthened with "It must never be left null when the note states an age." (measured 0/6 null after the change).
- **E-07's expectation is unchanged** (D11-14): the repair is a test-data-inconsistency fix, never a tuned green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The added serial-vitals descriptions destabilised the age extraction (E-04 regressed)**
- **Found during:** Task 2 (E-07 measurement)
- **Issue:** The plan's conditional vitals `description=` fixed E-07 (3/3 RECHECK) but silently regressed E-04 to ABSTAIN 3/3 — the 1.5B model's structuring is schema-sensitive, and the larger contract caused it to drop `age_years` (measured 0/8 null). A first attempt to shorten the vitals text made *both* worse.
- **Fix:** Strengthened the `age_years` description with an explicit "must never be left null when the note states an age" clause (still general, no fixture number), keeping the general serial-vitals description on all three scored vitals. Re-measured: E-04 age 0/6 null **and** E-07 golden-match 6/6; the authoritative CLI runs then gave E-04 `[RED,RED,RED]` and E-07 `[RECHECK,RECHECK,RECHECK]`.
- **Files modified:** `src/triagedesk/core/schema.py`
- **Verification:** `uv run triagedesk eval --case E-04 --runs 3` and `--case E-07 --runs 3`; the hermetic guards pass; the offline control unregressed.
- **Committed in:** `3889341` (Task 2 commit)

**2. [Rule 3 - Blocking] A required provenance field invalidated the committed `report.json` (suite would go red)**
- **Found during:** Task 3 (full-suite run)
- **Issue:** Adding a *required* `Provenance.extraction_schema_hash` made the committed `mode: real` `evals/results/report.json` (which predates the field) fail validation, so `tests/test_docs_final.py::test_evals_is_a_projection_of_the_report` failed (`emit_evals.py --check` → non-zero). The plan defers the report regeneration to 11-02 and this plan's constraint forbids clobbering the committed report, so regenerating it here was not permitted.
- **Fix:** Gave `extraction_schema_hash` an empty-string default and made `_digest_payload` dump the provenance with `exclude_defaults=True`. A pre-field report therefore still validates and its `report_digest` recomputes unchanged (verified: committed digest `ebef6471…` still matches), while every report the pipeline produces supplies a non-empty hash that IS sealed. 11-02 regenerates the report with the field sealed.
- **Files modified:** `src/triagedesk/evals/report.py`
- **Verification:** `uv run pytest -q` → 431 passed; `emit_evals.py --check` exits 0 on the committed report; `test_report_digest_seals_the_extraction_schema_hash` proves a changed hash moves the digest.
- **Committed in:** `9474aea` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both were necessary — the first to deliver the plan's primary success criterion (E-04 RED 3/3) after the conditional vitals fix regressed it; the second to keep the suite green without clobbering a published artefact the next plan owns. No scope creep: no scorer/matcher/recheck/prompt edit, no expectation/golden/threshold edit, no new dependency.

## Issues Encountered

- **The E-04 root cause contradicted the CONTEXT premise** (the research had already found this): the matcher retrieved the emergency discriminator on every run; the failure was age instability. The fix targeted `age_years`, not the complaint wording (Pitfall 1).
- **The 1.5B model's schema-sensitivity** required a measured iteration to a stable contract (see deviation 1). Recorded so 11-02's re-run is not surprised by a stochastic E-04/E-07 outcome.
- **The plan's Task-2 vitals description was conditional** ("only if the current vitals are not recovered"). The initial CLI measurement (`[RECOVER, RECHECK, RECHECK]`) met the condition; the resulting fix was kept once it was made compatible with E-04.

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file access or schema change at a trust boundary. The provenance addition is additive and covered by `report_digest`; the schema descriptions strengthen input validation (ASVS V5) rather than loosen it.

## Next Phase Readiness

- The extraction-seam fixes are landed and measured; plan **11-02** owns the 14-case real re-run and the regenerated `evals/results/report.json` + `EVALS.md` (now carrying `extraction_schema_hash`).
- The committed report is **intentionally stale** (its outcomes predate these fixes) and remains valid until 11-02 regenerates it.
- Expected movement for 11-02's honest report: E-04 → RED, E-07 → RECHECK, and **E-13** should move from `unexpected_failures` to a coverage deferral once the age fix lands (the research's A4) — reflected honestly, never hidden.

---

*Phase: 11-honest-evaluation-re-run-rigour-docs*
*Completed: 2026-10-13*

## Self-Check: PASSED

- FOUND: src/triagedesk/core/schema.py
- FOUND: evals/cases/E-07.yaml
- FOUND: src/triagedesk/evals/report.py
- FOUND: tests/test_eval_fidelity.py
- FOUND: tests/test_eval_report.py
- FOUND: tests/test_eval_honest_terminal.py
- FOUND: docs/DECISIONS.md
- FOUND: 0c58ea6
- FOUND: 3889341
- FOUND: 9474aea
