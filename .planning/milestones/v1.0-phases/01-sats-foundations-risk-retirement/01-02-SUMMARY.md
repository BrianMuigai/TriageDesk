---
phase: 01-sats-foundations-risk-retirement
plan: 02
subsystem: data
tags: [sats, tews, discriminators, yaml, drl, dual-transcription, band-edge-tests, pydantic]

# Dependency graph
requires:
  - plan: "01-01"
    provides: "data/sats_tews.yaml (adult TEWS bands/thresholds), core/rules.py loader, core/schema.py, uv/Python-3.12 scaffold"
provides:
  - "data/sats_tews.yaml — complete adult TEWS chart (7 parameters, both colour thresholds, target times, fail-closed out_of_scope) re-verified"
  - "data/sats_discriminators.yaml — 41 adult discriminators (id/category/label/aliases) + explicit no_match (D-08/D-11)"
  - "core/rules.py — discriminator loader (load_discriminators/get_discriminators) alongside the TEWS loader"
  - "tests/test_sats_bands.py — exhaustive band-edge tests on both sides (D-10)"
  - "tests/test_sats_discriminators.py — discriminator shape/uniqueness/no-match tests"
  - "scripts/transcribe_diff.py + evidence/sats_transcription_b.yaml + evidence/sats-verification.md — dual independent transcription diff (D-10)"
affects: [01-03, 01-04, phase-2, phase-4]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 45000, raw_tokens: 35000).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 13218        # chars/4 over the full realized diff (52,873 chars)
  raw_tokens: 14307    # chars/4 over the 8 authored files (57,228 chars)
  tasks: 3
  commits: 3
  plan_head_before: 63da0fd3a385795b52c2d20c20f823b6be558619
  plan_head_after: 3d8da5290792fe24f69081aadfdeb79b9d470d2b

tech-stack:
  added: []
  patterns:
    - "Single source of truth as data: every SATS value read only through core/rules.py (CONVENTIONS §1)"
    - "Band-edge tests are data-driven — no SATS literal restated in code"
    - "Dual independent transcription diff as a repeatable verification gate (exit non-zero on any disagreement)"

key-files:
  created:
    - data/sats_discriminators.yaml
    - tests/test_sats_bands.py
    - tests/test_sats_discriminators.py
    - scripts/transcribe_diff.py
    - evidence/sats_transcription_b.yaml
    - evidence/sats-verification.md
  modified:
    - src/triagedesk/core/rules.py
    - docs/SATS.md

key-decisions:
  - "data/sats_tews.yaml was already complete from Plan 01-01; Task 1's deliverable was the exhaustive, data-driven band-edge test (no YAML change was needed)."
  - "Discriminators are consumed through the ONE loader (core/rules.py) — the plan's key_link requires it, so the discriminator models/loader were added there rather than read ad-hoc in the test (DRY/SOLID: D)."
  - "The alias lists deliberately EXCLUDE 'feeling unwell' so eval case E-09 remains the declared coverage-gap failure; the KB is not tuned green (EVALS §6, Pitfall 11)."
  - "Transcription B is an evidence artefact, never imported at runtime; it encodes numeric bands as range strings (a different route than A's explicit min/max), so a slip in either is caught. The diff is resolution-aware ('< 9' == '<= 8'; '> 38.4' == '>= 38.5')."
  - "The blank temperature 1-point column is encoded as 'no 1-point band' (data, never guessed) and recorded as residual uncertainty in both the report and docs/SATS.md."

patterns-established:
  - "Verification as a repeatable script: scripts/transcribe_diff.py exits non-zero on any band/threshold/discriminator disagreement"
  - "No SATS literal in code — tests derive every boundary from the loaded data"

requirements-completed: [INTAKE-04, INTAKE-05]

coverage:
  - id: D1
    description: "Every adult TEWS band and both colour thresholds live in data/sats_tews.yaml; every band edge is correct on both sides (INTAKE-04)."
    requirement: "INTAKE-04"
    verification:
      - kind: unit
        ref: "tests/test_sats_bands.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 41 adult discriminators + categories + explicit no_match live in data/sats_discriminators.yaml; ids unique, aliases unambiguous (INTAKE-05)."
    requirement: "INTAKE-05"
    verification:
      - kind: unit
        ref: "tests/test_sats_discriminators.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both data files were re-verified by a dual independent transcription diff that exits non-zero on any disagreement; residual uncertainty is flagged (D-10)."
    verification:
      - kind: automated
        ref: "uv run python scripts/transcribe_diff.py --report evidence/sats-verification.md"
        status: pass
    human_judgment: false
  - id: D4
    description: "The fail-closed out-of-scope predicate is data and abstains on a missing age (D-09)."
    verification:
      - kind: unit
        ref: "tests/test_sats_bands.py#test_out_of_scope_predicate_fails_closed_on_missing_age"
        status: pass
    human_judgment: false
  - id: D5
    description: "Discriminator matching is representable as a deterministic alias lookup with an explicit no-match (D-11)."
    requirement: "INTAKE-05"
    verification:
      - kind: unit
        ref: "tests/test_sats_discriminators.py#test_alias_lookup_is_deterministic_and_reports_no_match"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-10-09
status: complete
---

# Phase 1 Plan 02: SATS Rule Substrate & Dual-Transcription Verification Summary

**The published adult SATS rules are encoded as the project's single source of truth — 7 TEWS parameters with both colour thresholds and a fail-closed out-of-scope predicate, plus 41 clinical discriminators with alias lists and an explicit no-match — proven by exhaustive band-edge tests and a dual independent transcription diff that passes with zero disagreements.**

## Performance

- **Duration:** ~13 min (12:07Z → 12:20Z)
- **Started:** 2026-10-09T12:07:17Z
- **Completed:** 2026-10-09T12:20:00Z
- **Tasks:** 3/3
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments

- **The TEWS chart is frozen and exhaustively edge-tested (D-10, Pitfall 3).** `tests/test_sats_bands.py` proves every band edge on **both** sides — RR 8/9/14/15/20/21/29/30; HR 40/41/50/51/100/101/110/111/129/130; SBP 70/71/80/81/100/101/199/200; T 34.9/35.0/38.4/38.5 — and the TEWS→colour boundaries 2/3, 4/5, 6/7. The bands are proven to partition the number line (no gaps, no overlaps) and every categorical value maps to its declared points. **No SATS value is restated in code**: every boundary is derived from `data/sats_tews.yaml` through `core/rules.py`.
- **All 41 adult discriminators are encoded with categories, labels and alias lists (D-08/D-11).** `data/sats_discriminators.yaml` covers the emergency (7 → RED), very-urgent (24 → ORANGE) and urgent (10 → YELLOW) lists from `docs/SATS.md` §5, plus an explicit `no_match` entry. Aliases are broad enough to cover the Phase-4 eval complaint phrasing (chest pain, fast breathing, reduced level of consciousness, uncontrolled arterial bleed, abdominal pain) while `feeling unwell` is **deliberately absent** so E-09 stays the declared coverage-gap failure.
- **The verification bar is a repeatable gate, not a one-off claim (D-10).** `scripts/transcribe_diff.py` normalises two independently-authored transcriptions (A = `data/*.yaml` via the loader; B = `evidence/sats_transcription_b.yaml`, written as range strings) to a common inclusive form and diffs bands, thresholds, target times, the out-of-scope predicate and discriminator categories. It exits **non-zero on any disagreement** and writes `evidence/sats-verification.md` — currently **PASS with zero disagreements**.
- **The fail-closed out-of-scope predicate is data (D-09).** `out_of_scope` declares the adult age/height boundaries and an explicit `on_missing_age: abstain`; the test proves a missing age never defaults to adult.

## Task Commits

Each task was committed atomically:

1. **Task 1: Complete the TEWS single source of truth** - `947596a` (test)
2. **Task 2: Discriminator single source of truth with alias lists and no-match** - `846097f` (feat)
3. **Task 3: Dual independent transcription diff and verification report** - `3d8da52` (feat)

**Plan metadata:** committed together with this SUMMARY and STATE.md (docs: complete plan)

## Files Created/Modified

- `data/sats_discriminators.yaml` — 41 adult discriminators (id/category/label/aliases) + categories→colour + explicit `no_match`; version + citation
- `data/sats_tews.yaml` — unchanged (already complete from Plan 01-01); re-verified by the diff
- `src/triagedesk/core/rules.py` — added `Discriminator`/`DiscriminatorCategory`/`NoMatch`/`DiscriminatorRules` models + `load_discriminators()`/`get_discriminators()`
- `tests/test_sats_bands.py` — data-driven band-edge tests (25 tests)
- `tests/test_sats_discriminators.py` — shape/uniqueness/ambiguity/no-match tests (7 tests)
- `scripts/transcribe_diff.py` — dual-transcription normaliser + diff + report writer
- `evidence/sats_transcription_b.yaml` — second independent transcription (range-string encoding)
- `evidence/sats-verification.md` — the generated verification report (PASS)
- `docs/SATS.md` — verification flag updated to cite the evidence, state the residual uncertainty, and restate the SC1 scoping note

## Decisions Made

- **Discriminators go through the ONE loader.** The plan's `key_link` says `data/*.yaml` are consumed only through `core/rules.py`; the discriminator models and `load_discriminators()`/`get_discriminators()` were therefore added there rather than parsed ad-hoc in the test. This keeps DRY (one loader) and DIP (callers depend on the loader, not on YAML).
- **`feeling unwell` is not an alias anywhere.** E-09 is the declared, un-fixed failure (EVALS §6); adding it would tune the KB to pass and violate Pitfall 11. The omission is documented in the data file and the report.
- **Range-string encoding for transcription B.** Writing B as the manual's table rows (e.g. `<9`, `>=30`, `35.0–38.4`) makes it a genuinely different route from A's explicit min/max, so a transcription slip in either is caught by the resolution-aware diff.
- **The temperature 1-point column is empty — as data.** Both transcriptions encode no 1-point band; the ambiguity is recorded as *resolved* (no 1-point band) with the residual uncertainty (the original manual was not available) flagged in `evidence/sats-verification.md` and `docs/SATS.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added the discriminator loader to `core/rules.py`**
- **Found during:** Task 2 (discriminator single source of truth)
- **Issue:** The plan's Task 2 `<files>` listed only `data/sats_discriminators.yaml` and the test, but the plan's own `key_link` states "`data/*.yaml` are consumed only through `core/rules.py`". Without a discriminator loader, the test (and Phase 2) would parse YAML ad-hoc — a DRY/DIP violation.
- **Fix:** Added typed discriminator models and `load_discriminators()` / `get_discriminators()` to the existing one loader; the test and diff script consume it.
- **Files modified:** `src/triagedesk/core/rules.py`
- **Verification:** `uv run pytest tests/test_sats_discriminators.py` passes; the diff script loads A through the loader.
- **Committed in:** `846097f` (Task 2 commit)

**2. [Rule 1 - Bug] YAML 1.1 coerced transcription B's unquoted `no`/`yes` to booleans**
- **Found during:** Task 3 (dual-transcription diff) — the diff correctly reported a `trauma` band mismatch.
- **Issue:** In `evidence/sats_transcription_b.yaml`, `{points: 0, value: no}` was parsed by YAML 1.1 as `False`, whereas `data/sats_tews.yaml` quotes `"no"`/`"yes"` and keeps them strings — so the two transcriptions disagreed on the `trauma` band.
- **Fix:** Quoted the values in B (`value: "no"` / `value: "yes"`) so both transcriptions encode the same categorical facts.
- **Files modified:** `evidence/sats_transcription_b.yaml`
- **Verification:** `uv run python scripts/transcribe_diff.py` exits 0; the `trauma` mismatch disappears.
- **Committed in:** `3d8da52` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** The loader addition keeps the DRY/DIP contract the plan itself specifies; the boolean-coercion fix is exactly the kind of transcription slip the dual-transcription gate exists to catch (it worked). No scope creep.

## Issues Encountered

- **Pre-existing lint findings (out of scope).** `ruff check` on the whole repo reports `F841` in `scripts/spike_model.py` and `E501` in `src/triagedesk/llm/prompts.py` — both from Plan 01-01, untouched here. Per the scope boundary they were **not** fixed; logged in `deferred-items.md`. All files touched by this plan lint clean.
- **Task 1 was a no-op on the YAML.** `data/sats_tews.yaml` was already complete and correct from Plan 01-01, so Task 1's deliverable was the exhaustive band-edge test. The dual-transcription diff independently re-verifies the YAML values.

## User Setup Required

None — data and tests only; no new installs, no external services.

## Next Phase Readiness

- **Phase 2 (deterministic scorer)** can now read both substrates through `core/rules.py`: `get_tews()` for bands/thresholds and `get_discriminators()` for the closed discriminator set (which `ExtractionResult.matched_discriminator_ids` can now be validated against — the closed set noted as outstanding in the 01-01 summary).
- **Phase 4 (evaluation)** inherits frozen expectations: the rules were re-verified before the scorer exists (Pitfall 11), and E-09's coverage gap is preserved by design.
- **Plan 01-03** still owns the executable DRY/purity guards (`test_no_duplicated_sats.py`, `test_purity.py`); this plan verified the DRY property manually (`grep` over `src/` shows no TEWS band, colour literal or discriminator string outside `data/`).
- **Residual uncertainty carried forward:** the original SATS manual was not available in the build window; verification is a dual transcription of `docs/SATS.md`. Flagged in `evidence/sats-verification.md` and `docs/SATS.md`.

---

*Phase: 01-sats-foundations-risk-retirement*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 8 key files exist on disk (data, tests, script, evidence, loader, docs).
- All 3 task commits are ancestors of HEAD: `947596a`, `846097f`, `3d8da52`.
- `uv run pytest -q` → 38 passed; `scripts/transcribe_diff.py` exits 0.
- Working tree clean (no untracked files).
