---
phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai
verified: 2026-11-05T08:51:05Z
status: passed
score: 9/9 must-haves verified
covered_files: [".planning/phases/14-evidence-fidelity-ground-every-extracted-sign-in-the-complai/14-01-PLAN.md", ".planning/phases/14-evidence-fidelity-ground-every-extracted-sign-in-the-complai/14-01-SUMMARY.md", ".planning/phases/14-evidence-fidelity-ground-every-extracted-sign-in-the-complai/14-02-PLAN.md", ".planning/phases/14-evidence-fidelity-ground-every-extracted-sign-in-the-complai/14-02-SUMMARY.md", ".planning/phases/14-evidence-fidelity-ground-every-extracted-sign-in-the-complai/14-03-PLAN.md", ".planning/phases/14-evidence-fidelity-ground-every-extracted-sign-in-the-complai/14-03-SUMMARY.md", "ARCHITECTURE.md", "docs/REQUIREMENTS.md", "src/triagedesk/core/approval.py", "src/triagedesk/core/grounding.py", "src/triagedesk/core/schema.py", "src/triagedesk/graph/nodes.py", "src/triagedesk/llm/notes.py", "src/triagedesk/mcp/server.py", "tests/conftest.py", "tests/test_commit_idempotent.py", "tests/test_graph_durable.py", "tests/test_grounding.py", "tests/test_mcp_tools.py", "tests/test_safety_spine.py"]
covered_digest: "v4:sha256:85b305eaaa74944f5d1e153220d60cdee0128ff4eec357f5738a2f66bf0a4481"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 8/9
  gaps_closed:
    - "A note that legitimately states vitals and a finding in prose still grounds both (the real-mode extraction shape is not weakened)."
  gaps_remaining: []
  regressions: []
---

# Phase 14: Evidence Fidelity Verification Report

**Phase Goal:** Every extracted sign is grounded in the complaint text, the committed target travels with the committed colour through an edit, and the docs describe the shipped fail-closed evidence check.
**Verified:** 2026-11-05T08:51:05Z
**Verdict:** **PASS WITH NOTES** (`status: passed`; the one deferred diagram asset is unchanged)
**Re-verification:** Yes — after gap closure (`acd4ac8`)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | A discriminator id returned by `normalize_case` survives only when a declared alias is an unnegated contiguous token phrase of the note. | ✓ VERIFIED | `core/grounding.py:76-86` reuses `matcher.filter_discriminator_ids` + `matcher.alias_matches` over `get_discriminators()` aliases; `mcp/server.py:225` calls it. `tests/test_grounding.py:36-70` (two tool-boundary tests) pass. |
| 2 | A numeric vital survives only when its own numeric token occurs in the note; otherwise `None`, never imputed. | ✓ VERIFIED | `core/grounding.py:50-62,87-93`; `tests/test_grounding.py:89-96` (HR 140 vs "RR 14" → `None`) passes. |
| 3 | `no_discriminator_matched` is `True` exactly when no grounded id survives. | ✓ VERIFIED | `core/grounding.py:95-100` sets `not kept`; `tests/test_grounding.py:56-70` passes. |
| 4 | Grounding is monotone removal: output ids are a subset of the filtered input, and case values are input-or-`None`; no id, value or colour is added. | ✓ VERIFIED | `core/grounding.py:76-101`; `tests/test_grounding.py:73-86,217-230` pass. |
| 5 | A note that legitimately states vitals and a finding in prose still grounds both (the real-mode extraction shape is not weakened). | ✓ VERIFIED | Celsius prose still grounds (`tests/test_grounding.py:99-120`). Fahrenheit now grounds too: `core/grounding.py:78-101,128-139` accepts a `temperature_c` equal to `stated_temperature(note)` (the note's stated value through the ONE `to_celsius` rule), while a hallucinated value is still nulled. Fixed by `acd4ac8`; `tests/test_grounding.py:133-191` (4 new tests). Verifier probe: `ground_extraction(37.0, "temp 98.6") → 37.0`, `normalize_case` end-to-end → `37.0`; `38.5` vs `"temp 98.6"` → `None`; `26.7` vs `"BP 120/80"` → `None`. |
| 6 | E-13's injected imperative produces no discriminator and no hallucinated vital; scoring the grounded result yields the vitals colour with citations. | ✓ VERIFIED | `tests/test_grounding.py:166-185` poisons a declared id + SpO2 88 against E-13's note; asserts `[]`, `True`, `spo2 is None`, equal vitals colour, non-empty citations, `len(citations) == len(triggered_rules)`. Passes. |
| 7 | `CommitResult` carries the target the queue row holds on a commit, and `None` on a refusal. | ✓ VERIFIED | `core/schema.py:366-371`; `mcp/server.py:372-377` returns `colour=row.colour, target=row.target`; refusal branches at :352-361 return before store access. `tests/test_commit_idempotent.py:142,206-209,227-230,273-276` and `tests/test_mcp_tools.py:145,195-199` pass. |
| 8 | `commit_priority` persists a target derived from the committed colour through the loaded substrate; `handover` uses one helper; an edit's card colour AND target equal the queue row. | ✓ VERIFIED | `core/approval.py:36-46` (`target_for_colour` reads `get_tews().target_times`), `:49-64` (`committed_or_scored`); `mcp/server.py:363-371`; `graph/nodes.py:402-410` (no inline conditional); `tests/test_graph_durable.py:137-204` asserts `rows[0].target == expected` and `edited["handover"].target == rows[0].target`; `tests/test_safety_spine.py:131-150` covers committed/refused/no-commit. Pass. |
| 9 | The docs describe the shipped fail-closed check, no retry loop; E-13 is unit-tested only; measured status unchanged; `EVALS.md`/`report.json` untouched; ARCHITECTURE within bound. | ✓ VERIFIED | `ARCHITECTURE.md:26` (`deterministic`; fail-closed terminal), `:34` (`uncited → END`); `docs/REQUIREMENTS.md:89` (JC-1), `:116` (SW-1 says "shipped + unit-tested; measured E-13 status unchanged"). `wc -w`=696, `wc -l`=93. `git diff --name-only abee224..HEAD -- EVALS.md evals/` is empty. `EVALS.md:107,149` and `report.json.gate.unexpected_failures` still record E-13 as a measured failure. `tests/test_docs_final.py` 9 passed. See deviation note on the diagram asset. |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/triagedesk/core/grounding.py` | NEW — one public `ground_extraction`; shared numeric rule | ✓ VERIFIED | 157 lines; `ground_extraction`, `stated_numbers`, `value_is_stated`, `stated_temperature`, `to_celsius`, `NUMERIC_CASE_FIELDS`; the ONE °F formula (`:86`, repo-wide grep finds no other); no alias/colour/threshold literal. |
| `src/triagedesk/mcp/server.py` | `normalize_case` calls the one grounding function; commit persists/reports row target | ✓ VERIFIED | `:225` grounding call; `:363-377` target derivation and `CommitResult(colour=row.colour, target=row.target)`. |
| `src/triagedesk/llm/notes.py` | Imports the one numeric-stated rule; no second copy | ✓ VERIFIED | `:22-27` imports `NUMERIC_CASE_FIELDS, stated_numbers, stated_temperature, value_is_stated`; `:135` calls `stated_temperature`. `acd4ac8` deleted the local `_TEMPERATURE`/`_CELSIUS_MAX`/formula, leaving only `_TEMPERATURE_SERIAL` (the distinct serial-reading rule). No `_NUMBER`/`_numbers`/`_is_stated` copy. |
| `src/triagedesk/core/approval.py` | `target_for_colour`, `committed_or_scored` | ✓ VERIFIED | `:36-46`, `:49-64`; `committed_colour` unchanged at `:25-33`. |
| `src/triagedesk/core/schema.py` | `CommitResult.target` | ✓ VERIFIED | `:358-371`; additive field, model has no `extra="forbid"`. |
| `src/triagedesk/graph/nodes.py` | `handover` uses the one helper; no duplicated conditional | ✓ VERIFIED | `:402` `committed_or_scored(...)`; no `commit_result.colour`/`.target` conditional in `handover`; the only `priority.target` is the approval-gate payload at `:332`. |
| `tests/test_grounding.py` | NEW — tool-boundary, numeric, E-13, monotone tests | ✓ VERIFIED | 14 tests (10 + 4 from `acd4ac8`), all pass. |
| `tests/conftest.py` | Stand-in gate mirrors committed colour + target | ✓ VERIFIED | `:341-359` uses `committed_colour`/`target_for_colour` and persists both. |
| `ARCHITECTURE.md` / `docs/REQUIREMENTS.md` | Corrected prose | ✓ VERIFIED | See truth 9. |
| `docs/assets/architecture.mmd` | Should describe the shipped check | ⚠️ DEVIATION | `:39` still lists `verify_priority`; `:77` still has `N5 -. critic .-> QWEN`. Logged in `deferred-items.md`; generated SVG/PDF unchanged. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `mcp/server.normalize_case` | `core/grounding.ground_extraction` | direct call | ✓ WIRED | `mcp/server.py:225`. |
| `core/grounding.ground_extraction` | `core/matcher.filter_discriminator_ids` / `alias_matches` | direct calls | ✓ WIRED | `grounding.py:76-86`; no second matcher or inline alias list. |
| `core/grounding.ground_extraction` | `core/rules.get_discriminators` | alias substrate | ✓ WIRED | `grounding.py:78-81`. |
| `llm/notes._drop_unstated` | `core/grounding.stated_numbers/value_is_stated/NUMERIC_CASE_FIELDS` | import | ✓ WIRED | `notes.py:22-27,91-98`. |
| `llm/notes._apply_temperature` | `core/grounding.stated_temperature` → `to_celsius` | import + call | ✓ WIRED | `notes.py:135`; the single-value regex and °F formula live only in `core/grounding.py:37-41,78-101` (repo-wide grep). |
| `mcp/server.commit_priority` | `core/approval.committed_colour` + `target_for_colour` → `store/queue.commit_to_queue(target=...)` | direct calls | ✓ WIRED | `server.py:363-371`; `store/queue.py:52-88` persists/supersedes target. |
| `mcp/server.commit_priority` | `CommitResult(colour=row.colour, target=row.target)` | return | ✓ WIRED | `server.py:372-377`. |
| `graph/nodes.handover` | `core/approval.committed_or_scored` | direct call | ✓ WIRED | `nodes.py:402-410`. |
| `tests/conftest` stand-in | `committed_colour` / `target_for_colour` | import + calls | ✓ WIRED | `conftest.py:341-359`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `normalize_case` | `matched_discriminator_ids` | model extraction → closed-set filter → alias grounding | Yes (aliases from `data/sats_discriminators.yaml`) | ✓ FLOWING |
| `normalize_case` | numeric `CaseInput` fields | model extraction → client `grounded_case` → tool-boundary numeric check (temperature: literal token OR `stated_temperature`) | Yes; stated °C, stated °F and bare >45 all flow through; an unstated value is `None` | ✓ FLOWING |
| `commit_priority` | `CommitResult.target` | committed colour → `get_tews().target_times` → `QueueRow.target` | Yes | ✓ FLOWING |
| `handover` | `HandoverCard.colour/target` | `committed_or_scored(commit_result, priority)` | Yes (row values on commit; scored values on fallback) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full suite | `uv run pytest -q --ignore=tests/test_triage_skill.py` | `600 passed in 83.77s` | ✓ PASS |
| Lint | `uv run ruff check src tests` | `All checks passed!` | ✓ PASS |
| Offline demo | `uv run triagedesk demo` | exit 0 | ✓ PASS |
| E-13 unit regression | `uv run pytest -q tests/test_grounding.py` | 14 passed (includes `test_e13_injection_adds_no_evidence_and_cannot_set_the_colour`) | ✓ PASS |
| Docs guard | `uv run pytest -q tests/test_docs_final.py` | 9 passed; `wc -w ARCHITECTURE.md`=696, `wc -l`=93 | ✓ PASS |
| Fahrenheit note through the shipped tool | script: `grounded_case` → `normalize_case` with the project's own `temp 98.6` note | `grounded_case` temp 37.0; `normalize_case` temp **37.0** | ✓ PASS (was Gap 1) |
| Explicit `°F` unit | `ground_extraction(CaseInput(temperature_c=38.0), "temperature 100.4 F")` | `38.0` | ✓ PASS |
| Hallucinated temperature | `ground_extraction(CaseInput(temperature_c=38.5), "temp 98.6")` | `None` | ✓ PASS |
| Unrelated numeric token | `ground_extraction(CaseInput(temperature_c=26.7), "BP 120/80")` | `None`; BP fields kept | ✓ PASS |
| Pre-phase Celsius prose shape | `ground_extraction` over E-13-style prose vitals | age/RR/HR/SBP/temperature all retained (`36.8`) | ✓ PASS |
| Phase range contains no planning/harness files | `git diff --name-only abee224..HEAD` | only 14 src/tests/docs files; no `.planning/`, no harness artifacts | ✓ PASS |

> Environment note (not a phase gap): `uv run triagedesk demo` writes the gitignored runtime sink `spans.jsonl` into the repo root, so `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root` fails if the demo is run first. The 600-passed run was taken with that stale artifact removed; the test's own autouse fixture keeps the sink out of the repo. This is pre-existing demo behaviour, unrelated to `acd4ac8`.

### Probe Execution

Not applicable — no `probe-*.sh` declared or implied by the phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| JC-1 | 14-01, 14-02, 14-03 | Agentic depth & MCP craft; reusable tool boundaries; docs match the shipped graph | ✓ SATISFIED | Grounded `normalize_case`; typed `CommitResult.target`; corrected JC-1 prose (`docs/REQUIREMENTS.md:89`). |
| JC-4 | 14-03 | Evaluation/reliability reported honestly, including the unfixed case | ✓ SATISFIED | SW-1 (`docs/REQUIREMENTS.md:116`) says shipped + unit-tested, measured E-13 unchanged; `EVALS.md`/`report.json` untouched and still record the E-13 failure. |
| JC-5 | 14-01, 14-02, 14-03 | Priority survives audit; extracted signs traceable to the note; card and row agree | ✓ SATISFIED | Discriminators and hallucinated vitals are grounded; a stated °F temperature is retained as its deterministic Celsius value (`acd4ac8`); the card/row target is consistent. |

No orphaned requirements found: all three phase requirements are claimed by at least one plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | No `TBD`/`FIXME`/`XXX` in any file modified by the phase | — | None. |

No stubs, placeholder returns, or hardcoded empty data found in the phase's modified files.

### Deviations and Notes

1. **Gap 1 (blocker) — RESOLVED in `acd4ac8`.**
   - Original defect: `llm/notes.py::_apply_temperature` converted a stated °F (or bare >45) to Celsius, then `mcp/server.py:225` re-grounded the converted value against the raw note and `core/grounding.py` nulled it because `37.0` is not literally in a note that says `98.6`.
   - Fix: `core/grounding.py:78-101` now owns the ONE temperature rule — `to_celsius` (the °F formula, `:86`) and `stated_temperature` (the single-value regex, `:37-41`). `ground_extraction` (`:128-139`) keeps `temperature_c` when it is literally stated **or** equals `stated_temperature(note)`; every other field keeps the literal-token rule, and the value is never rewritten.
   - `llm/notes.py:22-27,135` imports and calls `stated_temperature`; the duplicate regex, `_CELSIUS_MAX` and conversion were deleted in the same commit. Repo-wide grep for the formula returns exactly one hit (`core/grounding.py:86`).
   - Verifier evidence: `ground_extraction(CaseInput(temperature_c=37.0), "… temp 98.6 …") → 37.0`; end-to-end `grounded_case` → `normalize_case` with the project's own note → `37.0` (was `None`); `38.5` against `"temp 98.6"` → `None`; `26.7` against `"BP 120/80"` → `None`; explicit `"temperature 100.4 F"` grounds `38.0`. Four regressions at `tests/test_grounding.py:133-191` cover these paths and pass.

2. **Deviation (warning, deferred — unchanged): `docs/assets/architecture.mmd` still shows the retired critic edge.**
   - `:39` `P2["verify_priority"]` and `:77` `N5 -. critic .-> QWEN`; the generated `architecture.svg`/`.pdf` carry the same. This is the one doc asset that still misdescribes `verify`; it is explicitly logged in `deferred-items.md` and was not fixed because regenerating the derivatives needs `npx @mermaid-js/mermaid-cli` (T-14-SC zero-install). The prose docs the phase names are correct. Carried forward as a post-submission note; it does not affect the phase goal.

3. **Observation (not a phase-14 regression): the numeric rule is value-level, not field-level.**
   - `value_is_stated` (`core/grounding.py:50-62`) checks a value against every numeric token in the note, so an unrelated token of the same magnitude can support a vital (e.g. age 60 supports HR 60). This is the plan-specified token-level rule and the same rule the pre-existing `_drop_unstated` used; it is not introduced by this phase, but it means "grounded in the note" is weaker than "stated for that vital".

4. **Observation (per plan): the desk online path does not call `ground_extraction`.**
   - `desk/extraction.py:103` only closed-set filters; `evals/tools.py::_tool_map` returns a supplied extraction unchanged for `online_tools`, so the new boundary check is not applied there. The plan deliberately left this seam alone because the extraction ids are not consumed by the graph and the case already passes through `llm.client._parsed`/`grounded_case`. Not a gap against the plan; noted for reviewers.

### Human Verification Required

None — all checks are deterministic; no human judgement call is required.

### Gaps Summary

No blocking gaps. The phase delivers the intended grounding rule (one owner, removal-only, E-13 regression), the committed-target carry (row → `CommitResult` → one helper → card), and the corrected prose (no retry, no critic in `ARCHITECTURE.md`, honest SW-1). The suite (600), ruff, and the offline demo all pass, and no `.planning/` or harness files were committed in `abee224..HEAD`.

The one blocker from the initial verification — a stated °F temperature converted by the client and then nulled by the tool-boundary re-ground — is resolved by `acd4ac8`: the conversion formula and single-temperature reader now live once in `core/grounding.py`, and `ground_extraction` accepts a `temperature_c` the note states in either unit while still dropping a hallucinated value. `llm/notes.py` imports the rule rather than duplicating it, and four tool-boundary regressions cover the stated-°F, explicit-unit, hallucinated and unrelated-token cases.

The only open item is the deferred diagram asset (`docs/assets/architecture.mmd`, logged in `deferred-items.md`), which is unchanged by this fix and does not affect the phase goal.

---

_Verified: 2026-11-05T08:51:05Z_
_Verifier: the agent (gsd-verifier)_

## Reviewer spot-check list

1. Confirm the resolved blocker: `uv run pytest -q tests/test_grounding.py -k "fahrenheit or unrelated_numeric or hallucinated_temperature"` (4 pass), or run `grounded_case` → `normalize_case` over the `temp 98.6` note and see `temperature_c == 37.0`; `git show acd4ac8` shows the single-home move.
2. Read `core/grounding.py:37-101,128-139` and confirm the id rule is `filter_discriminator_ids` + `alias_matches` only, with no inline alias/colour list, and the °F formula appears once.
3. Read `graph/nodes.py:388-421` and confirm `handover` has no duplicated committed-field conditional; the only `priority.target` is the approval-gate payload at `:332`.
4. Read `tests/test_graph_durable.py:137-204` and `tests/test_safety_spine.py:131-150`; confirm the edit card and row agree on both colour and target, and the refusal/no-commit paths fall back to the scored pair.
5. Run `git diff --name-only abee224..HEAD` and confirm only the 14 declared files; `EVALS.md` and `evals/results/report.json` are absent.
6. Inspect `docs/assets/architecture.mmd:39,77` and decide whether the deferred critic edge is acceptable for the submission or must be regenerated.
