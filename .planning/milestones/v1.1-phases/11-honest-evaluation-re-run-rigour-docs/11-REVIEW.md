---
phase: 11-honest-evaluation-re-run-rigour-docs
reviewed: 2026-10-13T09:34:34Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - EVALS.md
  - README.md
  - STATUS.md
  - docs/DECISIONS.md
  - docs/DEMO.md
  - docs/REQUIREMENTS.md
  - docs/ROADMAP.md
  - evals/cases/E-07.yaml
  - evals/results/report.json
  - scripts/emit_evals.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/evals/report.py
  - tests/test_docs_final.py
  - tests/test_eval_fidelity.py
  - tests/test_eval_honest_terminal.py
  - tests/test_eval_report.py
  - tests/test_readme_runbook.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-10-13T09:34:34Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Iteration 3 (final) re-review. The two warnings the iteration-2 pass closed are genuinely resolved in
the **current source**, and the iteration-2 fix moved **no measured number**:

- **WR-02 (provenance) — resolved and honest.** `_git_commit()` (`src/triagedesk/evals/report.py:294-314`)
  now consults `git status --porcelain` through the one `_git()` helper and appends `-dirty` on a
  non-clean tree. The published report seals `harness_commit: f9924f77805ab54f8a6dc9aa52e3d85e0da044d6-dirty`
  and `EVALS.md` §8 (lines 194-208) names the sealed `extraction_schema_hash`—not the bare commit—as what
  reproduces the run, and states a non-clean run is named `-dirty`. I confirmed the iteration-2 commit
  `14974a0` changed **only** `.provenance.harness_commit` and `.report_digest` in `report.json` (a
  field-level JSON diff: no `cases`, `gate`, `analysis` or other provenance field moved). The
  `-dirty` suffix is truthful: `f9924f7` is the parent of `ae980c5` (the temperature-contract commit),
  and the report was produced from a tree carrying that then-uncommitted change.
- **WR-01 (STATUS row) and the doc restatements — resolved.** `STATUS.md:56` now reads "2 recorded gate
  failures + 1 declared deferral + 3 coverage deferrals"; `REQUIREMENTS.md` SB-3/SB-8/JC-4/G-10 and
  `ROADMAP.md:36` were synced (16 cases, one command, G3/G-10 resolved). Grep for `14 cases`,
  `two commands`, `440/443`, `13/34`, `12/32`, `20/20` across the non-planning docs returns nothing stale.
- **Measured artefact unchanged, honesty invariants intact.** `emit_evals.py --check` exits 0;
  `compute_report_digest(report) == report.report_digest` (`12d6d1b9…`); the sealed
  `extraction_schema_hash` still equals `hash_tool_schema(ExtractionResult.model_json_schema())`;
  `mode` is `real`; E-04 `RED×3`, E-07 `RECHECK×3`, E-09 the visible declared failure (⏸), and the gate
  failures are exactly `E-11, E-13`. `git diff 05eeccb..HEAD` touches no `data/*.yaml`, `core/scorer.py`,
  `core/matcher.py`, `core/recheck.py`, `core/citations.py`, graph topology or dependency file; the E-07
  diff is the single `note:` line (adds `Temperature 36.8.`) and `expected: RECHECK` is byte-identical.
  No alias, no threshold tune, no new dependency. `uv run pytest -q` = **444 passed**; no
  `spans.jsonl`/`*.db` left at the repo root.
- **New/changed tests are non-vacuous.** `test_git_commit_marks_a_dirty_tree` stubs the git shell-out and
  pins both branches; `test_case_table_guard_raises_when_a_row_has_no_report_case` pins the new fail-closed
  direction; `test_the_described_serial_vitals_equal_the_scored_numeric_vitals` asserts set equality with
  `assert scored`; `test_e07_note_states_every_scored_vital_its_golden_case_declares` loops the derived
  scored-vital set (non-vacuous `assert fields`).

One **warning** remains: `docs/DEMO.md`'s "Expected on-screen output per beat" section presents output the
shipped demo does not produce (verified by running `uv run triagedesk demo` and each `--beat`). It is a
residual of an earlier phase's deferral/retrieval change, left in place by this phase's DEMO.md touch, and
it directly contradicts the section's own "Every line below is real output from the shipped CLI" claim.
Three info items follow.

## Warnings

### WR-01: `docs/DEMO.md`'s per-beat expected output is not the shipped demo's output (three of five beats)

**File:** `docs/DEMO.md:110-155`
**Issue:** The section opens (line 112) "**Every line below is real output from the shipped CLI (not a
hand-written mock)**", and line 89 promises "the real expected output". I ran the shipped CLI
(`uv run triagedesk demo` and `uv run triagedesk demo --beat <name>`, offline default) and three of the
five documented beats do not match:

- **`routine` (E-01).** The demo emits **five** tool calls — `normalize_case`, `match_discriminators`,
  `score_priority`, `retrieve_evidence`, `assess_confidence` — and **no** `commit` line: the complaint
  "sore throat" matches no discriminator, so `assess_confidence` returns `deferral: true` and the graph
  routes to the `escalate` terminal (never the gate). `DEMO.md:118-119` claims "Four tool calls —
  `normalize_case`, `match_discriminators`, `score_priority`, `commit_priority`" and `DEMO.md:127` prints
  `commit : committed case <content-id> at queue position 1 (GREEN)` — a line the demo never emits.
- **`deterioration` (E-07).** The demo calls `raise_recheck_flag` (flag set) then `assess_confidence`
  defers → `escalate` → **no** `commit` line. `DEMO.md:154` claims
  `commit : committed case <content-id> at queue position 3 (ORANGE)`.
- **`escalation` (E-02).** The demo makes **six** tool calls (not "Same four tools", `DEMO.md:130`) and
  commits at **queue position 1**, because the `routine` beat no longer commits. `DEMO.md:140` claims
  "queue position 2", and line 116 states "queue positions accumulate across the run" (so the whole
  accumulation in the block is off by one).

The `refusal` and `failure` beats are accurate. This matters because the runbook is the presenter's
script for a submission artefact whose honesty is a scored property: it implies the agent commits a
GREEN routine case and a deferred deterioration case, overstating commitment relative to the shipped
safe-deferral behaviour. `tests/test_demo_runbook.py` does not cover the output blocks (it only checks
that documented `--beat` names exist and that the E-09/refusal strings are present), so the drift is
unguarded. It is a residual of the Phase-8 deferral routing / Phase-9 retrieval node, not of this
phase's measured-artefact work — but the phase edits `docs/DEMO.md` and leaves the false claim standing.

**Fix:** Regenerate the three blocks from the shipped CLI (re-run each `--beat` and paste the real
`--- outcome ---` line(s), dropping the phantom `commit` lines and the "four tool calls"/queue-position
framing), or reword the section to say the blocks are illustrative rather than exact. The durable fix is
to extend `tests/test_demo_runbook.py` to drive each beat and assert its documented outcome block, in the
style of `test_readme_runbook.py` — so the block cannot drift again.

## Info

### IN-01: The docs say the owned server exposes "5 tools"; it exposes seven

**Files:** `STATUS.md:32`; `docs/REQUIREMENTS.md:51` (BW-1)
**Issue:** Both docs state "5 tools: `normalize_case`, `match_discriminators`, `score_priority`,
`raise_recheck_flag`, `commit_priority`". The shipped owned server registers **seven** tools —
`assess_confidence` and `retrieve_evidence` were added (Phases 8 and 9) and are `@server.tool()`
decorated (`src/triagedesk/mcp/server.py`, whose own docstring says "the seven triage tools";
`await triagedesk.mcp.server.server.list_tools()` returns 7). `ARCHITECTURE.md:38` ("`triage` server
(5 tools)") is stale too, though that file is outside this phase's scope. The requirement ("three or more
tools") is comfortably met, so this understates rather than overclaims — hence Info, not Warning.
**Fix:** Update the count/list in the two in-scope docs to the registered set (or link to it) —
consistent with D11-12's one-source rule.

### IN-02: `AGENTS.md:89` still says "the 14 eval cases"

**File:** `AGENTS.md:89`
**Issue:** "Test suite incl. the 14 eval cases" — stale (16). This file is outside the phase's declared
file scope and the line lives in a GSD-managed block (`<!-- GSD:stack-start source:research/STACK.md -->`),
so it is noted for completeness rather than as a phase defect; it is nevertheless a repo-level restatement
of the superseded count that D11-12 aims to eliminate.
**Fix:** Regenerate the AGENTS.md stack block from the corrected `research/STACK.md`, or drop the count.

### IN-03: `docs/ROADMAP.md:51` cross-references the wrong REQUIREMENTS section

**File:** `docs/ROADMAP.md:51`
**Issue:** "For risks and their mitigations, see [`REQUIREMENTS.md`](REQUIREMENTS.md) **§10**." §10 is the
traceability matrix; the risks table is §11 (`REQUIREMENTS.md:19`: "Section 11 lists open gaps and
risks"). A reader following the link lands on the wrong table.
**Fix:** Change `§10` to `§11` (or point at `../STATUS.md`).

---

_Reviewed: 2026-10-13T09:34:34Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
