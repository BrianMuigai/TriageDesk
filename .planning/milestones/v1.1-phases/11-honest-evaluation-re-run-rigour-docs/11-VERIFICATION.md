---
phase: 11-honest-evaluation-re-run-rigour-docs
verified: 2026-10-13T13:28:39Z
status: passed
score: 12/12 must-haves verified
covered_files: [".planning/phases/11-honest-evaluation-re-run-rigour-docs/11-01-PLAN.md", ".planning/phases/11-honest-evaluation-re-run-rigour-docs/11-01-SUMMARY.md", ".planning/phases/11-honest-evaluation-re-run-rigour-docs/11-02-PLAN.md", ".planning/phases/11-honest-evaluation-re-run-rigour-docs/11-02-SUMMARY.md", ".planning/phases/11-honest-evaluation-re-run-rigour-docs/11-03-PLAN.md", ".planning/phases/11-honest-evaluation-re-run-rigour-docs/11-03-SUMMARY.md", "AGENTS.md", "ARCHITECTURE.md", "EVALS.md", "README.md", "STATUS.md", "docs/DECISIONS.md", "docs/DEMO.md", "docs/REQUIREMENTS.md", "docs/ROADMAP.md", "evals/cases/E-07.yaml", "evals/results/report.json", "scripts/emit_evals.py", "src/triagedesk/core/schema.py", "src/triagedesk/evals/report.py", "tests/test_docs_final.py", "tests/test_eval_fidelity.py", "tests/test_eval_honest_terminal.py", "tests/test_eval_report.py", "tests/test_readme_runbook.py"]
covered_digest: "v3:sha256:9b98aabaa392d9d1f38a5d013ba14310aa845031f0db2087a6c2004ae3ab3f48"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 12/12
  gaps_closed: []
  gaps_remaining: []
  regressions: []
advisory: []
---

# Phase 11: Honest Evaluation Re-run & Rigour Docs Verification Report

**Phase Goal:** The two fixable measured failures reach their expected outcomes, the 14-case suite
is re-run over the real graph, and `EVALS.md` is regenerated solely from `report.json` with
reconciled counts — alongside a literal one-command README.
**Verified:** 2026-10-13T13:28:39Z
**Status:** passed
**Re-verification:** Yes — stale re-verification after Phase 12's additive edits to the shared docs
(`README.md`, `docs/DECISIONS.md`, `STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ROADMAP.md`). The
verified truths are preserved; the covered-input fingerprint was recomputed and every truth was
re-checked against the current codebase. No regression found.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | E-04 (emergency discriminator) reaches `RED` on all three real runs | ✓ VERIFIED | `evals/results/report.json` — E-04 `outcomes ['RED','RED','RED']`, `colours ['RED','RED','RED']`, `passed: true`. Re-measured live this pass: `uv run triagedesk eval --case E-04 --runs 3` → `['RED','RED','RED']`, `passed True`. |
| 2 | E-07 (deterioration recheck) reaches `RECHECK` on all three real runs | ✓ VERIFIED | `report.json` — E-07 `outcomes ['RECHECK','RECHECK','RECHECK']`, `colours ['ORANGE','ORANGE','ORANGE']`, `passed: true`. Re-measured live this pass: `uv run triagedesk eval --case E-07 --runs 3` → `['RECHECK','RECHECK','RECHECK']`, `passed True`. |
| 3 | The suite is re-run over the REAL graph and `report.json` recomputes its digest | ✓ VERIFIED | `report.json`: `mode 'real'`, `runs 3`, 16 cases; `compute_report_digest(Report) == report.report_digest` (`12d6d1b909d33872…`, recomputed this pass); provenance `model_tag qwen2.5:1.5b`, `ollama_version 0.30.6`. |
| 4 | `EVALS.md` is regenerated ONLY from `report.json`; `emit_evals.py --check` exits 0; the §4 row-id set equals the report's case-id set (16) | ✓ VERIFIED | `uv run python scripts/emit_evals.py --check` → "up to date (report 12d6d1b909d33872)", exit 0. §4 row ids `[E-01…E-14, H-01, H-02]` == report case ids (set equality confirmed programmatically this pass); `_assert_case_table_covers_report` fail-closed; row count 16 == `len(report.cases)`. |
| 5 | The declared failure E-09 and every honest miss stay VISIBLE (never hidden, never tuned green) | ✓ VERIFIED | `report.json` E-09 `declared_failure: true`, `passed: false`; `EVALS.md` §4 renders E-09 `⏸ deferral` (line 103), §6 names it the one declared failure; §6.1 derived record names unfixed gate failures `E-11, E-13`; §4 renders E-11/E-13 `❌`. |
| 6 | The README quickstart is the literal `uv run triagedesk demo`, no separate install step, and names the optional `uv run triagedesk desk` | ✓ VERIFIED | `README.md` §Quickstart (lines 93/96) contains `uv run triagedesk demo` and `uv run triagedesk desk`; `grep -c "uv sync" README.md` → 0. Guard `tests/test_docs_final.py::test_readme_has_the_one_command_quickstart` asserts both directions. |
| 7 | The README's claimed command is guarded by a test driving the shipped CLI | ✓ VERIFIED | `tests/test_readme_runbook.py` extracts every `uv run triagedesk <cmd>` fenced invocation and drives it through `triagedesk.cli.main` with `run_demo`/`serve` spied — asserts exit 0 and the seam reached (non-vacuous `assert invocations`). Passes this pass. |
| 8 | The extraction contract carries a GENERAL `age_years` description reaching the model as prompt text AND `format=` grammar | ✓ VERIFIED | `CaseInput.model_json_schema()['properties']['age_years']['description']` = "The patient's age in whole years, parsed from a stated age such as 'a 74 year old patient'. It must never be left null when the note states an age." — general, quotes no fixture number / SATS value (`test_age_years_description_is_general_not_tuned_to_a_fixture` passes); `llm/client.py` sends `ExtractionResult.model_json_schema()` as both `prompt` and `format=`. |
| 9 | E-07's fixture note and golden `case` agree (D11-14); `expected: RECHECK` unchanged | ✓ VERIFIED | `git diff 05eeccb..HEAD -- evals/cases/E-07.yaml` shows only the `note:` line changed (now states `Temperature 36.8.`); `case`/`previous_case`/`expected: RECHECK` byte-identical; guard `test_e07_note_states_every_scored_vital_its_golden_case_declares` passes. |
| 10 | The report provenance seals the extraction schema the model was asked to fill (covered by `report_digest`) | ✓ VERIFIED | `Provenance.extraction_schema_hash == hash_tool_schema(ExtractionResult.model_json_schema()) == 40b65a88…` (report, live recompute, and `build_provenance` agree); the field is serialized into the digest payload (non-empty ⇒ sealed). |
| 11 | `docs/DECISIONS.md` records the fix (D24), linking `EVALS.md`, restating no figure | ✓ VERIFIED | `docs/DECISIONS.md:256` `### D24 — Extraction fidelity is fixed at the contract the model fills` with `**Decision:**`/`**Why:**`; names the age contract, the scored-vital serial contract and the D11-14 note repair; cites `EVALS.md` §4, restates no measured figure. (Line shifted 255→256 from Phase 12's additive rows above it; heading and body intact.) |
| 12 | No expectation/golden/threshold edit, no literal alias, no dependency; scorer/matcher/recheck/citation/@audited/graph topology/`data/*.yaml` unchanged | ✓ VERIFIED | `git diff --name-only 05eeccb..HEAD -- src/` = `core/schema.py`, `evals/report.py` (Phase 11) + `llm/client.py` (Phase 12, cosmetic const rename only — see below); `pyproject.toml`/`uv.lock` UNCHANGED; `data/` unchanged; E-07 is the only fixture diff (`expected` unchanged); no alias string added. |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

### Re-verification regression check (Phase 12's additive shared-doc edits)

The Phase 12 doc edits were re-scanned for regression against the Phase 11 truths:

- **`README.md`** (+32/−…): quickstart still the literal one-liner (truth 6); no `uv sync`; guard passes.
- **`docs/DECISIONS.md`**: D24 intact (truth 11); Phase 12 added D25 below it.
- **`EVALS.md`**: still a pure projection — `emit_evals.py --check` exits 0 (truths 4/5).
- **`STATUS.md` / `docs/REQUIREMENTS.md` / `docs/ROADMAP.md`**: no Phase 11 truth asserts content in these beyond the requirement mapping, which is unchanged (EVAL-06/DOCS-04/DOCS-05).
- **`src/triagedesk/llm/client.py`** (Phase 12 IN-02): comment/const rename `PRIMARY_MODEL→BIG_MODEL`, `FALLBACK_MODEL→SMALL_MODEL`; `DEFAULT_MODEL = SMALL_MODEL` is still `qwen2.5:1.5b`. No eval-path behaviour change; no dangling references (grep clean). Not a regression of truth 12's "scorer/matcher/recheck/citation/@audited/graph topology unchanged" invariant.

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/triagedesk/core/schema.py` | general `age_years` + scored-vital `Field(description=…)` | ✓ VERIFIED | Descriptions present, general; described serial set == substrate scored numeric vitals (`test_the_described_serial_vitals_equal_the_scored_numeric_vitals`). |
| `evals/cases/E-07.yaml` | note states its golden temperature; `expected: RECHECK` unchanged | ✓ VERIFIED | Only the `note:` line changed (`Temperature 36.8.`); golden `case`/`previous_case`/`expected` unchanged. |
| `src/triagedesk/evals/report.py` | `Provenance.extraction_schema_hash` via the ONE hashing helper | ✓ VERIFIED | `hash_tool_schema(ExtractionResult.model_json_schema())`; `_git_commit` marks a non-clean tree `-dirty`. |
| `tests/test_eval_fidelity.py` | hermetic contract + fixture-consistency guards | ✓ VERIFIED | 5 non-vacuous guards; passes. |
| `docs/DECISIONS.md` | `### D24` row | ✓ VERIFIED | Present at line 256. |
| `scripts/emit_evals.py` | `_assert_case_table_covers_report` fail-closed guard | ✓ VERIFIED | Bidirectional set-equality guard called from `render_evals` after `_render_case_table`. |
| `EVALS.md` | 16 §4 rows, §6.2 D11-14 narrative, regenerated cells | ✓ VERIFIED | 16 rows; §3 names `mode real` + digest; §6.2 present; §8 documents `extraction_schema_hash`. |
| `evals/results/report.json` | regenerated `mode: real` report | ✓ VERIFIED | `real` / 16 / 3, recomputing digest. |
| `tests/test_eval_report.py` | row-set + honesty guards | ✓ VERIFIED | Row-set equality, declared-failure visibility, §6.1 coverage, mode-real guards pass. |
| `README.md` | literal one-command quickstart | ✓ VERIFIED | `uv run triagedesk demo`, no `uv sync`. |
| `tests/test_docs_final.py` | corrected one-command guard | ✓ VERIFIED | Asserts one-liner present and two-step absent. |
| `tests/test_readme_runbook.py` | CLI-driving README drift guard | ✓ VERIFIED | Drives public `main`, spies seams. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `CaseInput.age_years` description | `ExtractionResult.model_json_schema()` → `llm/client.extract` | prompt text AND `format=` | ✓ WIRED | `schema = ExtractionResult.model_json_schema()` used for `prompt` and `format=schema`. |
| `hash_tool_schema(ExtractionResult.model_json_schema())` | `Provenance.extraction_schema_hash` → `_digest_payload` → `report_digest` | report provenance | ✓ WIRED | Hashes equal (`40b65a88…`); digest recomputes (`12d6d1b9…`). |
| `evals/cases/E-07.yaml` note | real extraction → `score_priority` → `recheck` → RECHECK | real graph | ✓ WIRED | Re-measured live this pass `RECHECK×3`. |
| `evals.runner.run_eval` | `report.json` → `emit_evals.render_evals` → `EVALS.md` | pipeline | ✓ WIRED | `--check` exit 0; digest sealed. |
| `_render_case_table` rows | `report.cases` ids | row-set guard | ✓ WIRED | Set equality enforced fail-closed both directions. |
| `report.gate.unexpected_failures` | §6.1 generated record | derived record | ✓ WIRED | `E-11, E-13` named in §6.1, matching `gate.unexpected_failures`. |
| README fenced block | `uv run triagedesk demo` → `triagedesk.cli.main` | CLI-driving guard | ✓ WIRED | Documented invocations accepted (exit 0), seams reached. |
| `uv run` auto-sync from `uv.lock` | no separate install step | README rationale | ✓ WIRED (documented) | README states the rationale; the guard proves the invocation, not the clean-clone sync (documented A2 boundary). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `evals/results/report.json` | `cases[].outcomes/colours` | real graph run (`run_eval`, model `qwen2.5:1.5b`) | Yes — `mode: real`, sealed provenance, digest recomputes | ✓ FLOWING |
| `EVALS.md` §3–§6 | measured cells | `scripts/emit_evals.py` projection of `report.json` | Yes — `--check` exit 0, no hand-typed cell | ✓ FLOWING |
| `README.md` quickstart | documented invocations | README fenced blocks | Yes — driven through shipped `main` | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full suite (hermetic, no model) | `uv run pytest -q` | `454 passed in 33.39s` | ✓ PASS |
| Phase guards | `uv run pytest -q tests/test_eval_fidelity.py tests/test_eval_report.py tests/test_eval_honest_terminal.py tests/test_docs_final.py tests/test_readme_runbook.py` | `52 passed` | ✓ PASS |
| `EVALS.md` is the report's projection | `uv run python scripts/emit_evals.py --check` | exit 0 ("up to date (report 12d6d1b909d33872)") | ✓ PASS |
| One-command demo | `uv run triagedesk demo` | exit 0, shown mismatch for E-09 rendered (`DECLARED: ORANGE / MEASURED: GREEN`) | ✓ PASS |
| E-04 real-mode (re-measured this pass) | `uv run triagedesk eval --case E-04 --runs 3 --report /tmp/opencode/e04.json` | `['RED','RED','RED']`, passed | ✓ PASS |
| E-07 real-mode (re-measured this pass) | `uv run triagedesk eval --case E-07 --runs 3 --report /tmp/opencode/e07.json` | `['RECHECK','RECHECK','RECHECK']`, passed | ✓ PASS |
| `report.json` digest recomputes | `compute_report_digest(Report) == report.report_digest` | True (`12d6d1b9…`) | ✓ PASS |
| §4 row-id set == report case-id set | programmatic set comparison | equal (16 ids) | ✓ PASS |

### Probe Execution

Not applicable — this phase declares no probes and is not a migration/CLI-tooling phase.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts. (14/14 honored, 0 not honored;
non-blocking gate.)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| EVAL-06 | 11-01, 11-02 | The two fixable measured failures (E-04, E-07) reach their expected outcomes; the suite is re-run over the real graph; `EVALS.md` regenerated only from `report.json` | ✓ SATISFIED | E-04 `RED×3`, E-07 `RECHECK×3` (report + live re-measure); `mode: real` 16×3; `--check` exit 0. |
| DOCS-04 | 11-03 | A stranger gets running in one command — `uv run triagedesk demo`, no separate install | ✓ SATISFIED | README literal one-liner, no `uv sync`; CLI-driving guard. |
| DOCS-05 | 11-02 | `EVALS.md` case/run counts reconciled (no 14-vs-16 / 29-vs-32 drift); every number emitted from `report.json` | ✓ SATISFIED | §4 row-id set == report case-id set (16), fail-closed; `--check` exit 0. |

**Orphaned requirements:** none — `REQUIREMENTS.md` maps Phase 11 exactly to EVAL-06, DOCS-04, DOCS-05, all declared across the plans (11-01: EVAL-06; 11-02: EVAL-06, DOCS-05; 11-03: DOCS-04).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `tests/test_eval_fidelity.py` | EVAL-06 | 5 | 0 | none | Value | PASS |
| `tests/test_eval_report.py` | EVAL-06, DOCS-05 | 27 | 0 | none | Value/Behavioral | PASS |
| `tests/test_eval_honest_terminal.py` | EVAL-06 | 12 | 0 | none | Behavioral | PASS |
| `tests/test_docs_final.py` | DOCS-04 | (in suite) | 0 | none | Value | PASS |
| `tests/test_readme_runbook.py` | DOCS-04 | (in suite) | 0 | none | Behavioral | PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0 (`scripts/emit_evals.py` reads `report.json` and renders; it imports `analysis`/`invariants`/`report`, not the scorer/graph under test). **Insufficient assertions:** 0.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | No real `TBD`/`FIXME`/`XXX` debt markers in phase-modified production files | ℹ️ Info | None — completion is auditable. |
| `tests/test_eval_report.py` | 107–110, 120 | Literal `TBD` strings | ℹ️ Info | False positive — these are placeholder cells inside the `_TEMPLATE_BASE` markdown fixture used to exercise the EVALS.md parser/renderer, not unresolved work markers. Not a debt marker; does not block. |
| `tests/test_eval_honest_terminal.py` | 88–91, 97 | Literal `TBD` strings | ℹ️ Info | Same as above — test-fixture table content, not debt. |
| `11-02-SUMMARY.md` | 146 | Stale `gate.unexpected_failures == ['E-08','E-13']` (pre-WR-01-fix) | ℹ️ Info | Planning-artifact detail only; the authoritative `report.json`/`EVALS.md` are consistent at `['E-11','E-13']` (owner-confirmed publish-as-measured). Not a codebase gap. |

### Advisory (New Scope, Unevidenced)

None. No new-scope findings were raised this re-verification pass.

### Deferred (owner-confirmed, not a phase-11 gap)

| Item | Addressed In | Evidence |
| --- | --- | --- |
| `docs/DEMO.md` per-beat output-block drift | Phase 12 (DOCS-06) — now CLOSED | Deferred by hand with a recorded reason + a dated drift note (`11-REVIEW-DISPOSITION.md`; `11-REVIEW-FIX.md` WR-01; `STATE.md` Blockers/Concerns `[Phase 12, DOCS-06]`; AR-11-01 accepted risk). Phase 12's commits (e.g. `8c4e081 fix(12): WR-01 retime ROADMAP storyboard`, `e418ced fix(12): CR-01 pause before the Beat-3 dismissal`) closed it; Phase 12 verification is `passed`. |

### Human Verification Required

None. The two behavior-dependent truths (E-04/E-07 real-mode outcomes) were confirmed by
re-measuring the real graph in this verification run (`RED×3` / `RECHECK×3`), not by symbol
presence alone.

### Gaps Summary

No gaps. All three ROADMAP success criteria hold against the current codebase:

1. **E-04 and E-07 reach their expected outcomes.** The committed `report.json` records E-04
   `RED×3` (emergency discriminator cited every run) and E-07 `RECHECK×3`, both `passed: true`;
   both were independently re-measured live over `qwen2.5:1.5b` this pass and reproduced.
2. **The suite was re-run over the real graph and `EVALS.md` is a pure projection.** `mode: real`,
   16 cases × 3 runs, a recomputing `report_digest`, `emit_evals.py --check` exits 0, and the §4
   row-id set equals the report's case-id set (16) under a bidirectional fail-closed guard.
3. **A stranger gets running in one command.** `README.md` carries the literal `uv run triagedesk
   demo` (no `uv sync`), names the optional `uv run triagedesk desk`, and the claim is proven
   against the shipped `triagedesk.cli.main` by a CLI-driving guard; the command runs (exit 0).

The residual 1.5B-model misses (`gate.unexpected_failures == ['E-11','E-13']`, E-08 an all-deferred
coverage marker, E-09 the declared failure) are HONEST and visible in §4/§6.1, not a phase-11
failure — the phase's criteria are E-04 and E-07, both met. No expectation, golden value, threshold
or alias was edited (only the D11-14 E-07 note repair, `expected: RECHECK` unchanged); no
dependency was added; the scorer, matcher, recheck, citation helper, `@audited` interceptor, graph
topology and `data/*.yaml` are untouched.

---

_Verified: 2026-10-13T13:28:39Z_
_Verifier: the agent (gsd-verifier)_
