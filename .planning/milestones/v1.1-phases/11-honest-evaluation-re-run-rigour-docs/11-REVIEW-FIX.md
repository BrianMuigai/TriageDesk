---
phase: 11-honest-evaluation-re-run-rigour-docs
fixed_at: 2026-10-13T09:41:57Z
review_path: .planning/phases/11-honest-evaluation-re-run-rigour-docs/11-REVIEW.md
iteration: 3
findings_in_scope: 4
fixed: 3
deferred: 1
skipped: 0
status: partial
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-10-13T09:41:57Z
**Source review:** `.planning/phases/11-honest-evaluation-re-run-rigour-docs/11-REVIEW.md`
**Iteration:** 3 (final)

**Scope note:** the declared `fix_scope` was `critical_warning`, so the single remaining Warning
(**WR-01**) is in scope. The orchestrator additionally requested the three Info items
(**IN-01..IN-03**) and an explicit, recorded **deferral** of WR-01 to Phase 12 (DOCS-06). All four
in-scope items are dispositioned below; nothing was skipped for error.

**Summary:**
- Findings in scope: 4 (1 Warning + 3 Info)
- Fixed: 3 (IN-01, IN-02, IN-03)
- Deferred by design: 1 (WR-01 → Phase 12, DOCS-06)
- Skipped (error): 0

**Verification (run in the main checkout — `workflow.use_worktrees` is `false`, so no isolated worktree was created):**
- `uv run pytest -q` → **444 passed** (unchanged from the pre-pass baseline)
- `uv run pytest tests/test_docs_final.py tests/test_demo_runbook.py tests/test_readme_runbook.py tests/test_eval_fidelity.py -q` → **23 passed**
- `uv run python scripts/emit_evals.py --report evals/results/report.json --check` → exits **0** (report `12d6d1b909d33872`)
- `ARCHITECTURE.md` stays inside the one-page guard (the docs-final test passes): **698 words**, 94 lines ≤ the 700 / 110 bound
- no repo-root `spans.jsonl` / `*.db` left behind; no new dependency (`pyproject.toml` / `uv.lock` untouched)
- **Honesty:** `mode` stays `real`; no measured number was touched. `evals/results/report.json`,
  `core/scorer.py`, the citation helper, the `@audited` interceptor, the graph topology, `data/*.yaml`
  and every expectation are untouched, so `EVALS.md` remains exactly the generator's projection.

## Fixed Issues

### IN-01: the owned server exposes seven tools, not five

**Files modified:** `STATUS.md`, `docs/REQUIREMENTS.md`, `ARCHITECTURE.md`
**Commit:** `b1c3d14`
**Applied fix:** corrected every stale "5 tools" count to the shipped **seven** and named the full set,
derived from `src/triagedesk/graph/build.py::OWNED_TOOL_ALLOWLIST` — `normalize_case`,
`match_discriminators`, `retrieve_evidence`, `score_priority`, `assess_confidence`,
`raise_recheck_flag`, `commit_priority`. Fixed the two `STATUS.md` occurrences (§1 evidence row, and the
SOTA "Tool use / MCP craft" row), the BW-1 row in `docs/REQUIREMENTS.md`, and the `triage`-server
heading and table in `ARCHITECTURE.md`. In `ARCHITECTURE.md` the two added tools are listed under the
existing read-only rows; the now-redundant restatement of the retry behaviour was dropped (the `verify`
node row already states it) to keep the doc inside its one-page bound — **698 / 700 words**.

### IN-02: `AGENTS.md` still said "the 14 eval cases"

**Files modified:** `AGENTS.md`
**Commit:** `d4e44d1`
**Applied fix:** "the 16 eval cases" (E-01…E-14 + H-01/H-02), matching `EVALS.md` §4 and the measured
report.

### IN-03: `docs/ROADMAP.md` cross-referenced the wrong REQUIREMENTS section

**Files modified:** `docs/ROADMAP.md`
**Commit:** `951a632`
**Applied fix:** §10 → **§11** — §11 is the risks table; §10 is the traceability matrix (per
`docs/REQUIREMENTS.md` §0).

### E-09 framing — verified, no change required

Every non-planning doc that names **E-09** already frames it as a **deferral, not a delivered
under-triage** (`README.md:71`, `EVALS.md` §6/§6.1, `STATUS.md:78`, `docs/DEMO.md`, `docs/DECISIONS.md`).
Grep for `under-triage` across the submission docs returns only correct usages, so no edit was made.

## Deferred (by design — recorded, not skipped for error)

### WR-01: `docs/DEMO.md`'s per-beat expected output is not the shipped demo's output

**File:** `docs/DEMO.md:110` — the "Expected on-screen output per beat" section
**Commit:** `ddb7a9e` (the drift note)
**Deferral recorded at:** `.planning/STATE.md` → *Blockers/Concerns* → `[Phase 12, DOCS-06]`
**Reason:** a faithful refresh requires **re-running the shipped CLI and re-transcribing** three of the
five beats — `routine` (E-01) and `deterioration` (E-07) now **defer** with **no** `commit` line (the
graph routes to the safe `escalate` terminal), `escalation` (E-02) commits at **queue position 1** (not
2), and the owned server exposes **seven** tools. That exact re-run + re-transcription *is* Phase 12's
**DOCS-06** ("every submission document refreshed to the v1.1 state"), so it is deferred there rather
than half-done here.
**What was done instead (so no reader is misled meanwhile):** added a dated **"Known drift — refreshed in
Phase 12 (DOCS-06)"** blockquote at the affected section, stating plainly that the recorded blocks
predate Phases 8/9/10 and that the shipped output differs, and softened the section's opening claim so
the runbook no longer asserts the blocks are byte-exact current output. The stale blocks are **kept**
(the wrong output is **not** re-transcribed as if it were right).
**Not done here:** the durable guard the reviewer suggested (extending `tests/test_demo_runbook.py` to
drive each beat and assert its documented outcome block) is part of the Phase-12 refresh, so the drift
remains unguarded until then — by design.

## Notes

- `AGENTS.md`'s stack block is GSD-generated (`source:research/STACK.md`); the "14 eval cases" literal is
  **not** present in `.planning/research/STACK.md`, so it was corrected in place in `AGENTS.md`.
- `.planning/STATE.md` is a planning artifact; per this workspace's `commit_docs: false` it is left
  uncommitted (like the other `.planning/` edits), while the public docs are committed normally.
- **Worktree note:** `workflow.use_worktrees` is `false`, so every edit/commit above ran in the **main
  checkout** (no isolated worktree) — the verification numbers are reproducible from this tree.

---
_Fixed: 2026-10-13T09:41:57Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 3_
