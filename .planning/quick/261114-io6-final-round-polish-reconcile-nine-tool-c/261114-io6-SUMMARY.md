---
phase: quick-261114-io6
plan: 01
quick_id: 261114-io6
subsystem: cli-demo + judge-facing docs
status: complete
tags: [demo, logging, docs, mcp, evals, polish]
requires: []
provides:
  - "cli._quiet_http_logs(): the ONE place the httpx logger is raised to WARNING"
  - "demo.run.mode_line(*, offline): the ONE source of the demo's mode header"
  - "ARCHITECTURE.md §4 nine-tool inventory (other docs link to it)"
affects: [docs/DEMO.md, docs/MCP.md, README.md, STATUS.md, docs/REQUIREMENTS.md, EVALS.md, skills]
tech-stack:
  added: []
  patterns: ["stdlib logging level on one named logger", "CLI-output-to-runbook drift test"]
key-files:
  created: []
  modified:
    - src/triagedesk/cli.py
    - src/triagedesk/demo/run.py
    - src/triagedesk/evals/tools.py
    - tests/test_demo.py
    - tests/test_demo_runbook.py
    - ARCHITECTURE.md
    - README.md
    - STATUS.md
    - docs/REQUIREMENTS.md
    - EVALS.md
    - docs/DEMO.md
    - docs/MCP.md
    - src/triagedesk/skills/triagedesk-triage/SKILL.md
    - .claude/skills/triage-nurse-stress-test/SKILL.md
decisions:
  - "httpx quieting is called from main() right after harden_offline(), before the skill early return, so every command gets it from one place; root logger and the mcp RichHandler are untouched"
  - "mode_line imports DEFAULT_MODEL (the call-path default, no env override) so the screen names the model actually used"
  - "EVALS §3.3 denominator note names no count at all (not even the 3-run figure) and points to the Measured source line instead; the generator owns every number"
requirements: [BW-1, SB-5, JC-1, DQ-2, SW-1]
metrics:
  duration: 5min
  completed: 2026-11-14
estimate:
  tokens: 70000
  tasks: 3
actuals:
  tokens: 8556
  tasks: 3
  commits: 3
plan_head_before: c0e7f5e006b817ee985389e8f5e9e69e622f89ef
plan_head_after: 202840353828abfa726760377c1cfdced241b0f6
---

# Quick 261114-io6: final-round polish (nine-tool docs + live-demo legibility) Summary

The CLI raises only the `httpx` logger to WARNING in one function, so an online demo prints no rich
`HTTP Request` lines. Every demo run opens with exactly one `mode:` line, which names either the offline
golden fixture or the imported `DEFAULT_MODEL` tag. All judge-facing docs now say nine tools, and the
2:28 recording keeps its seven tools labelled "recorded before v1.3".

## Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | (tracer, TDD) CLI quiets httpx once; demo opens with one mode line | e98e2d3 | src/triagedesk/cli.py, src/triagedesk/demo/run.py, tests/test_demo.py |
| 2 | Judge-facing docs say nine tools; SW-1 matches EVALS; EVALS §3.3 denominator note | b5dce09 | ARCHITECTURE.md, README.md, STATUS.md, docs/REQUIREMENTS.md, EVALS.md |
| 3 | (TDD) Runbook, MCP guide and skills match the current runner, plus a mode-line drift guard | 2028403 | docs/DEMO.md, docs/MCP.md, both SKILL.md files, tests/test_demo_runbook.py, src/triagedesk/evals/tools.py |

## Verification

- TDD: Task 1 tests A–C failed at collection (`ImportError: mode_line`) before the code existed, then passed. Task 3's drift test failed before DEMO.md carried the line, then passed.
- Tracer gate (end-to-end, Ollama up): `uv run triagedesk demo --online --beat routine` gave 0 `HTTP Request` lines on stderr, and its first line was `mode: online — local model qwen2.5:1.5b via Ollama`. The offline first line matches `mode: offline — golden fixture (no model)` verbatim.
- `uv run pytest -q`: 904 passed (baseline 900 + 4 new). `uv run ruff check` is clean. `scripts/emit_evals.py --check` exits 0.
- mypy on the two touched modules shows only the pre-existing `yaml` stubs error in demo/run.py and nothing new.
- Every grep gate in the plan hit its EXPECT value. ARCHITECTURE.md is now 688 words / 94 lines (bound 700 / 110).
- Final discovery grep: the only remaining "seven" hits are the three "recorded before v1.3" historical lines and MCP.md's correct "seven kernel tools plus …".
- Live per-beat tool order, offline: routine and escalation run `normalize_case, match_discriminators, plan_next_step, score_priority, retrieve_evidence, assess_confidence, commit_priority`. Deterioration runs the same calls but adds `raise_recheck_flag` after `retrieve_evidence`.
- No `spans.jsonl` is left at the repo root. The untracked `docs/assets/*` files were not touched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, docstring] Stale tool counts in src/triagedesk/evals/tools.py**
- **Found during:** Task 3 (flagged by the orchestrator)
- **Issue:** The `online_tools` docstring said "the other six tools", but `_tool_map` returns nine tools, so "other" means eight. The `offline_tools` docstring also said "the same eight real owned tools" when there are nine.
- **Fix:** "other six" became "other eight", and "same eight" became "same nine". These are docstring-only edits with no behaviour change.
- **Commit:** 2028403

**2. [DRY wording] EVALS §3.3 note avoids the "3-run" figure**
- **Issue:** The plan's suggested wording included "3-run report". That is still a number the generator owns, even though it is not an x/y fraction.
- **Fix:** The note refers to "the report its *Measured source* line names (several runs per case)", so it restates no count.

**3. [Wording] DEMO.md deterioration lead-in**
- The lead-in used to read "which flags the serial-vitals change". With `commit_priority` now in the list, it reads "the flag marks the serial-vitals change **without re-classifying** the patient", so the clause still refers to the flag rather than the commit.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/triagedesk/cli.py (`_quiet_http_logs`), src/triagedesk/demo/run.py (`mode_line`), tests/test_demo.py, tests/test_demo_runbook.py
- FOUND commits: e98e2d3, b5dce09, 2028403 (all ancestors of HEAD; `git rev-list --count c0e7f5e..HEAD` = 3)
