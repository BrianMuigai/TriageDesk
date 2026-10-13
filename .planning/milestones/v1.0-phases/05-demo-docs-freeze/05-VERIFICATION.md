---
phase: 05-demo-docs-freeze
verified: 2026-10-09T22:33:23Z
status: human_needed
score: 7/8 must-haves verified
covered_files: [".github/workflows/eval-gate.yml", ".github/workflows/smoke.yml", ".planning/config.json", ".planning/phases/05-demo-docs-freeze/05-01-PLAN.md", ".planning/phases/05-demo-docs-freeze/05-01-SUMMARY.md", ".planning/phases/05-demo-docs-freeze/05-02-PLAN.md", ".planning/phases/05-demo-docs-freeze/05-02-SUMMARY.md", ".planning/phases/05-demo-docs-freeze/05-03-PLAN.md", ".planning/phases/05-demo-docs-freeze/05-03-SUMMARY.md", "ARCHITECTURE.md", "DESCRIPTION.md", "EVALS.md", "README.md", "demo/storyboard.yaml", "docs/DEMO.md", "src/triagedesk/cli.py", "src/triagedesk/demo/__init__.py", "src/triagedesk/demo/run.py", "tests/test_demo.py", "tests/test_demo_runbook.py", "tests/test_docs_final.py", "tests/test_eval_invariants.py"]
covered_digest: "v3:sha256:a5d1eb9df39c81dc27779cf278161b3d30005f5d0aa43cfd7a0eae21044250ce"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Record the 3-minute unedited screen recording (tool calls on screen, no slides, incl. the human-judged run and the E-09 failure) against the frozen tag v1.0-submission, following docs/DEMO.md; upload publicly."
    expected: "An unedited <3-min video showing the live run against the frozen commit with tool calls visible, a human judging with evidence, and the E-09 failure shown."
    why_human: "DEMO-01 is an explicit human action (D-07); the agent produces only the runbook + the scripted `triagedesk demo` entry point, never the video."
  - test: "In the GitHub repo settings, disable GitHub Actions and branch protection for the frozen repository before the 2026-10-15 deadline."
    expected: "No post-freeze push can start a CI run or accept a branch write; the frozen tag remains the submission."
    why_human: "The in-repo workflows are workflow_dispatch-only, but the account-level Actions/branch-protection toggles are outside the repository and cannot be set from code."
  - test: "Confirm the submission tag points at the intended commit and that no post-freeze commit reaches the remote."
    expected: "v1.0-submission resolves to the final functional commit (9b1cddb) and origin/main has no commits beyond it."
    why_human: "Final human sign-off that the frozen artifact is the intended submission (programmatically confirmed here: tag → 9b1cddb == HEAD == origin/main)."
audit_acknowledged:
  milestone: v1.0
  at: 2026-10-13
  status: human_needed
---

# Phase 5: Demo, Docs & Freeze Verification Report

**Phase Goal:** A stranger can run the frozen system in one command, the demo video shows a live human-judged run including a failure, and the repository is frozen before the deadline.
**Verified:** 2026-10-09T22:33:23Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | A stranger runs the bare `uv run triagedesk demo` from a clean clone (offline, no pulled model) and sees the whole storyboard: routine→GREEN, escalation→ORANGE (committed under a named nurse), deterioration second-look, the gate **refusing** (0 rows), and the E-09 declared-vs-measured failure (DOCS-01). | ✓ VERIFIED | Ran `uv run triagedesk demo` → exit 0; all 5 beats printed in order; refusal beat shows `GATE REFUSED : no queue row written (rows added this beat: 0)`; failure beat shows `DECLARED : ORANGE` / `MEASURED : GREEN (SHOWN MISMATCH)`. HEAD == tag commit `9b1cddb`, so the frozen tree is what ran. |
| 2 | The offline path launches no borrowed subprocess and no network (D-01, T-05-10). | ✓ VERIFIED | `strace -f -e trace=execve,connect,socket uv run triagedesk demo` → **0 `connect()` calls**; no `npx`/`node`/`mcp-sqlite` execve (only the `triagedesk` console script). `run.py` injects `server_module.set_store(...)` in a `try`/`finally` (lines 234-247), so `_resolve_store()` never falls through to `default_store()`. |
| 3 | CI runs that exact bare one-command path (DOCS-03). | ✓ VERIFIED | `.github/workflows/smoke.yml` step `Demo smoke (the exact one-command path, offline)` runs `uv run triagedesk demo`; setup mirrors `eval-gate.yml` (`setup-uv@v5`, `uv python install 3.12`, `uv sync --locked`). |
| 4 | `ARCHITECTURE.md` is a genuine one page (≤700 words / ≤110 lines) naming the measured model (DOCS-02, D-03). | ✓ VERIFIED | `wc -w`=697, `wc -l`=94; contains `qwen2.5:1.5b` (measured default); guard test `test_architecture_is_one_page` passes. |
| 5 | Every `EVALS.md` number derives solely from `evals/results/report.json`, planned-vs-measured preserved, E-09 + honest misses visible (DOCS-02, D-04). | ✓ VERIFIED | `uv run python scripts/emit_evals.py --report evals/results/report.json --check` → exit 0 ("EVALS.md is up to date"); header reads "complete — the results below are **measured**"; E-09/E-04/E-07/E-13 carry ❌ in §4. |
| 6 | `DESCRIPTION.md` ~300 words; `README.md` honest with the real one-command quickstart (DOCS-02, D-05, D-06). | ✓ VERIFIED | DESCRIPTION 302 prose words (guard `test_description_is_about_300_words`); README carries `uv sync --locked` + `uv run triagedesk demo`, no stale "Not built"/"pre-build" rows, names E-09 and links `EVALS.md`. |
| 7 | `docs/DEMO.md` runbook is grounded against `triagedesk demo --list`; the recording is declared a human action (DEMO-01). | ✓ VERIFIED | All 5 documented `--beat` names match `demo --list` exactly (guard `test_demo_runbook.py`, 5 tests); runbook declares an unedited HUMAN screen recording against `v1.0-submission`; E-09 shown. |
| 8 | The 3-minute unedited video shows a live run against the frozen commit with tool calls visible, incl. a human judging with evidence and a failure (DEMO-01). | ⚠️ HUMAN NEEDED | The video itself does not exist — it is a **declared human action** (D-07). The agent deliverable (runbook + grounded scripted CLI) is complete; `REQUIREMENTS.md` still marks DEMO-01 `[ ]` Pending. See Human Verification. |
| 9 | Repo tagged, `git log -1` predates 2026-10-15; `commit_docs`/CI/hooks disabled; remote audited for post-freeze commits (D-08). | ✓ VERIFIED | Tag `v1.0-submission` → `9b1cddb` (== HEAD), date `2026-10-10` (< 2026-10-15); `.planning/config.json` `commit_docs:false` + `hooks.context_warnings:false`; `eval-gate.yml`/`smoke.yml` `on: workflow_dispatch:` only; `git ls-remote` shows `refs/heads/main` == `9b1cddb` and `git log origin/main..HEAD` empty. |

**Score:** 7/8 truths verified (0 present-behavior-unverified; 1 human-only deliverable)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/triagedesk/demo/run.py` | demo runner + tool-call tracer | ✓ VERIFIED | Substantive (258 lines); reuses `load_cases`/`build_tools`/`build_graph`; injects store via `set_store` in `finally`; no hard-coded output. |
| `src/triagedesk/demo/__init__.py` | demo package seam | ✓ VERIFIED | Exports `run_demo`, `list_beats`, `load_storyboard`; imported by `cli.py`. |
| `src/triagedesk/cli.py` | `demo` subcommand | ✓ VERIFIED | `demo` parser with `--online`/`--beat`/`--list`/`--fixture`; dispatches to `run_demo`. |
| `demo/storyboard.yaml` | beat manifest | ✓ VERIFIED | 5 `{name,case,label}` beats over bundled `evals/cases`; read directly, not globbed. |
| `.github/workflows/smoke.yml` | CI smoke of the one-command path | ✓ VERIFIED | Runs the exact bare `uv run triagedesk demo`. |
| `tests/test_demo.py` | demo-path regression proof | ✓ VERIFIED | 6 tests; asserts escalation writes exactly one row, refusal writes none, tracer covers the 4+1 owned tools. |
| `docs/DEMO.md` | demo runbook | ✓ VERIFIED | Human-recording declaration + tag, one-time setup, per-beat command/output mapping, E-09 close. |
| `tests/test_demo_runbook.py` | runbook-vs-CLI grounding | ✓ VERIFIED | 5 tests; fenced-block parse + public `main` surface. |
| `ARCHITECTURE.md` | one-page finalised | ✓ VERIFIED | 697 words / 94 lines; §3–§8 preserved; measured model. |
| `DESCRIPTION.md` | ~300-word submission description | ✓ VERIFIED | 302 prose words. |
| `README.md` | honest README + real quickstart | ✓ VERIFIED | Real quickstart; honest unfinished note; no stale rows. |
| `EVALS.md` | report projection | ✓ VERIFIED | `emit_evals.py --check` exit 0. |
| `tests/test_docs_final.py` | docs guard | ✓ VERIFIED | 9 tests (bounds, quickstart, projection, E-09). |
| `.planning/config.json` | post-freeze config | ✓ VERIFIED | `commit_docs:false`, `hooks.context_warnings:false`. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `cli demo` | `demo.run.run_demo` | import + dispatch | ✓ WIRED | `cli.py` imports `list_beats, run_demo` and calls `run_demo(...)`. |
| `demo.run` | `graph.build.build_graph` | direct call | ✓ WIRED | Builds the real graph per beat. |
| `demo.run` | `evals.tools.build_tools` | direct call | ✓ WIRED | Reuses the offline golden extraction + real owned tools. |
| `demo.run` | `mcp.server.set_store` | injection in `try`/`finally` | ✓ WIRED | Prevents the borrowed-subprocess fallthrough (strace-confirmed). |
| `.github/workflows/smoke.yml` | `uv run triagedesk demo` | workflow step | ✓ WIRED | Exact bare command. |
| `EVALS.md` | `report.json` | `emit_evals.py --check` | ✓ WIRED | Exit 0. |
| `docs/DEMO.md` beats | `demo --list` | grounding test | ✓ WIRED | Sets equal in both directions. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `demo.run` outcome | `colour`, `citations`, `commit_result`, `second_look` | real graph run over bundled `evals/cases` fixtures | Yes — every value read from `graph.ainvoke` result / store row delta | ✓ FLOWING |
| `demo.run` refusal climax | `rows_added` | `len(store.read_queue_rows())` before/after | Yes — `0` measured, not asserted | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Bare demo runs the full storyboard, exit 0 | `uv run triagedesk demo` | 5 beats, exit 0 | ✓ PASS |
| Beat list is exposed | `uv run triagedesk demo --list` | 5 beats printed | ✓ PASS |
| Offline: no subprocess, no network | `strace -f -e trace=execve,connect,socket … demo` | 0 connect(); no npx/node execve | ✓ PASS |
| EVALS is the report's projection | `emit_evals.py --report … --check` | exit 0 | ✓ PASS |
| Full suite green | `uv run pytest -q` | 239 passed | ✓ PASS |
| Lint green | `uv run ruff check` | All checks passed | ✓ PASS |

### Probe Execution

No phase-declared probes (`scripts/*/tests/probe-*.sh`) exist; not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| DOCS-01 | 05-01 | README gets a stranger running in one command | ✓ SATISFIED | `uv run triagedesk demo` exit 0 offline; README quickstart. |
| DOCS-02 | 05-03 | ARCHITECTURE (one page), EVALS, DESCRIPTION (~300w) finalised | ✓ SATISFIED | 697w/94l; `--check` exit 0; 302 prose words. |
| DOCS-03 | 05-01 | CI smoke runs the demo on the synthetic fixture | ✓ SATISFIED | `smoke.yml` runs the exact bare command. |
| DEMO-01 | 05-02 | 3-minute unedited demo video with tool calls, incl. a failure | ⚠️ NEEDS HUMAN | Video is a declared human action; runbook + scripted CLI complete. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `docs/DEMO.md` | 52-59, 81-92 | `--beat <name>` run alone starts a fresh store, so its `queue position` differs from the bare-run number quoted in the expected-output block (e.g. `--beat escalation` alone → position 1, not 2). | ℹ️ Info | The runbook notes "queue positions accumulate across the run"; the quoted block is real bare-run output. Cosmetic doc nuance only; no goal impact. |

No debt markers (`TBD`/`FIXME`/`XXX`) in any phase-modified file.

### Human Verification Required

#### 1. Record the 3-minute demo video (DEMO-01)

**Test:** Against the frozen tag `v1.0-submission`, follow `docs/DEMO.md` and record an unedited `<3 min` screen capture (tool calls on screen, no slides), narrating the human-judged run and the E-09 failure; upload publicly.
**Expected:** An unedited video showing the live run against the frozen commit, tool calls visible, a human judging with evidence, and the E-09 failure shown (not hidden).
**Why human:** DEMO-01 is an explicit human action (D-07); the agent produces only the runbook and the scripted `triagedesk demo` entry point, never the recording.

#### 2. Disable GitHub Actions + branch protection in repo settings

**Test:** Before 2026-10-15, disable GitHub Actions and branch protection for the frozen repository.
**Expected:** No post-freeze push can start CI or accept a branch write.
**Why human:** The workflows are `workflow_dispatch`-only in-repo, but the account-level toggles are outside the repository.

#### 3. Confirm the frozen tag/remote sign-off

**Test:** Confirm `v1.0-submission` points at the intended commit and the remote carries no post-freeze commit.
**Expected:** Tag resolves to `9b1cddb`; `origin/main` has nothing beyond it.
**Why human:** Final human sign-off (already confirmed programmatically: tag → `9b1cddb` == HEAD == `origin/main`).

### Gaps Summary

No goal-blocking gaps. Seven of eight must-have truths are verified by independent reproduction: the one-command offline demo runs the full five-beat storyboard (including the gate refusing with 0 rows and the E-09 shown mismatch) with no subprocess and no network; CI runs that exact path; the four docs are finalised to their declared bounds with EVALS a pure projection of `report.json`; the runbook is grounded against the CLI; and the repository is frozen (tag at the final commit, `commit_docs`/hooks off, CI `workflow_dispatch`-only, remote clean) before the deadline. The only unmet success criterion — the 3-minute video — is a **declared human action** (DEMO-01), not an agent deliverable, so it routes to human verification rather than a gap.

---

_Verified: 2026-10-09T22:33:23Z_
_Verifier: the agent (gsd-verifier)_
