---
phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai
plan: 01
subsystem: core-grounding
tags: [evidence, grounding, injection, mcp, dry]
requires:
  - core/matcher.py (alias_matches, tokenize_with_spans, filter_discriminator_ids)
  - core/rules.py (get_discriminators)
  - llm/notes.py (the numeric-stated rule, moved)
provides:
  - core/grounding.py (ground_extraction, stated_numbers, value_is_stated, NUMERIC_CASE_FIELDS)
  - evidence-grounded normalize_case tool contract
affects:
  - mcp/server.py::normalize_case
  - llm/notes.py::_drop_unstated
tech-stack:
  added: []
  patterns: [pure-core-module, single-owner, removal-only grounding]
key-files:
  created:
    - src/triagedesk/core/grounding.py
    - tests/test_grounding.py
  modified:
    - src/triagedesk/mcp/server.py
    - src/triagedesk/llm/notes.py
    - tests/test_mcp_tools.py
decisions:
  - "Ground ids by reusing matcher.alias_matches over loader-declared aliases — no second matcher, no inline alias list."
  - "Move the numeric-stated rule into core/grounding.py as the one owner; llm/notes.py imports it, preserving behaviour."
  - "E-13 regression poisons a non-stated vital (SpO2) so genuine prose vitals stay unchanged and the vitals colour is provable."
metrics:
  duration: "~30m"
  completed: "2026-11-05"
status: complete
actuals:
  tokens: 5125
  tasks: 3
  commits: 3
plan_head_before: abee2242049724e8600a835542bde827dca74096
plan_head_after: 0e7357cce78b87abeeec0fe8e6f5cf67e5b3bc93
---

# Phase 14 Plan 01: Evidence Fidelity — Ground Every Extracted Sign Summary

`normalize_case` now returns only discriminator ids whose declared alias is an unnegated
contiguous token phrase of the note and only numeric vitals whose own token the note states —
using one shared numeric-stated rule and the E-13 injection regression.

## What Was Built

- **`core/grounding.py`** — one pure module with one public extraction gate,
  `ground_extraction(result, note)`. It starts from `matcher.filter_discriminator_ids`
  (the ONE closed-set filter), tokenises the note once with `matcher.tokenize_with_spans`,
  and keeps an id only when `matcher.alias_matches` finds a declared alias from
  `get_discriminators()`. It also nulls any numeric `CaseInput` field whose value is not
  literally present in the note, via the shared `stated_numbers` / `value_is_stated` /
  `NUMERIC_CASE_FIELDS` rule. Grounding is monotone removal: no id, value, colour, target or
  destination is ever added.
- **`mcp/server.py::normalize_case`** — calls `grounding.ground_extraction(result, raw_note)`
  instead of the bare closed-set filter. Signature, read-only guarantee and `@audited`
  wrapper are unchanged; `no_discriminator_matched` follows what survives.
- **`llm/notes.py`** — `_NUMBER`, `_numbers` and `_is_stated` were deleted; `_drop_unstated`
  imports `NUMERIC_CASE_FIELDS`, `stated_numbers` and `value_is_stated` from
  `core.grounding`. `grounded_case` behaviour is unchanged (proved by the unedited
  `tests/test_llm_notes.py` suite).
- **Tests** — `tests/test_grounding.py` covers the tool-boundary id gate, the subset
  property, hallucinated-vital nulling, prose-stated vitals, comma decimals, untouched
  categoricals, the E-13 poisoned extraction, the complementary real-mode finding, and
  monotone removal. `tests/test_mcp_tools.py` now builds its normalize note from the chosen
  id's own declared alias.

## Verification

- `uv run pytest -q --ignore=tests/test_triage_skill.py` → **596 passed**.
- `uv run ruff check src tests` → **All checks passed**.
- `uv run triagedesk demo` → exit 0 offline.
- Manual audit: `core/grounding.py` contains no alias, colour, band or threshold literal;
  every such value is read through `core/rules.py` or `core/matcher.py`.

## Deviations from Plan

None — plan executed exactly as written. (One in-task test note initially omitted the
diastolic `80`; the test note was corrected to `BP 130/80` so the prose-stated case is
complete. No production code changed for this.)

## Known Stubs

None.

## Threat Flags

None — no new endpoint, auth path, file access pattern or schema change. Grounding only
removes evidence at the existing tool boundary.

## Self-Check: PASSED

- `src/triagedesk/core/grounding.py` — FOUND
- `tests/test_grounding.py` — FOUND
- `64e9753` ancestor of HEAD — FOUND
- `bb0f388` ancestor of HEAD — FOUND
- `0e7357c` ancestor of HEAD — FOUND
