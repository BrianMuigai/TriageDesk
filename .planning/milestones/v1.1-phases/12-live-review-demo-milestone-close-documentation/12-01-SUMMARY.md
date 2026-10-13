---
phase: 12-live-review-demo-milestone-close-documentation
plan: 01
subsystem: docs + tests (live-review rehearsal)
tags: [runbook, guard, data-only-extension, hermetic-harness, REV-01]
requirements-completed: [REV-01]
dependency_graph:
  requires:
    - "src/triagedesk/core/rules.py (the ONE loader + DISCRIMINATORS_PATH + @lru_cache get_discriminators)"
    - "src/triagedesk/core/matcher.py (match_discriminators)"
    - "src/triagedesk/core/scorer.py (score_priority)"
    - "src/triagedesk/cli.py (public main; lazily-imported handlers)"
  provides:
    - "docs/REVIEW.md — the guarded 10-minute Stage-2 live-review runbook (REV-01)"
    - "tests/test_review_runbook.py — the CLI-drift + honesty guard for docs/REVIEW.md"
    - "tests/test_data_extension.py — the hermetic data-only-extension proof (D12-02)"
  affects:
    - "uv run pytest -q (444 baseline -> 453)"
tech-stack:
  added: []
  patterns:
    - "runbook-drift guard (fenced block -> public main + spied side-effect seams)"
    - "hermetic loader redirect (monkeypatch DISCRIMINATORS_PATH + cache_clear) — the fresh-process equivalent"
key-files:
  created:
    - docs/REVIEW.md
    - tests/test_review_runbook.py
    - tests/test_data_extension.py
  modified: []
decisions:
  - "D12-01: docs/REVIEW.md scripts the walkthrough as literal, ordered, guarded beats"
  - "D12-02: the live extension is demonstrated (not asserted) with a hermetic tmp-substrate harness"
  - "D12-03: every documented command is driven through the shipped triagedesk.cli.main with all seams spied"
  - "Q2 resolved: the ~10-min real eval is NOT streamed; the measured artefact is the committed EVALS.md plus the live E-09 failure beat"
  - "Q4 resolved: doc edits must land before the repository freeze; the freeze itself is not rehearsed"
metrics:
  duration: "20min"
  completed: "2026-10-13"
status: complete
actuals:
  tokens: 5304
  tasks: 2
  commits: 2
  plan_head_before: ddb7a9e28fa7c94d61c364a45b84a8de30ac3b69
  plan_head_after: f639682
---

# Phase 12 Plan 01: Live-review rehearsal runbook and the data-only-extension proof Summary

Delivered the guarded live-review rehearsal runbook `docs/REVIEW.md` (REV-01) and the two guards
that make its headline claim true rather than aspirational: a runbook-drift guard that drives every
documented command through the shipped CLI, and a hermetic harness proving that ONE discriminator
added to the substrate re-scores through the **shipped** matcher/scorer with `src/` byte-unchanged.

## What Was Built

**`docs/REVIEW.md`** — a one-page, ordered, literal runbook for the 10-minute Stage-2 live review. It
opens with three blockquote declarations (one page driven from the page; what is human; "reload" means
a fresh process) and then eight beats: baseline suite, the demo, the durable resume, a legitimate
refusal, read-only replay, the desk surface, the measured eval shown honestly, and the headline live
data-only extension. Every `uv run triagedesk …` line lives in a bash fenced block with no trailing
comment, so the guard extracts the exact argv.

**`tests/test_review_runbook.py`** — mirrors `tests/test_desk_runbook.py` + `tests/test_readme_runbook.py`.
It fences-joins, strips any trailing `# …`, and `shlex.split`s each documented invocation, then drives
the shipped `triagedesk.cli.main` with **all five** side-effect seams spied (`run_demo` async→0,
`run_eval` async→0, `resume_thread` async→`{}` mapping, `replay_case` async→str, `serve` sync) and
asserts each invocation reaches exactly one seam. It also asserts the honesty clauses.

**`tests/test_data_extension.py`** — the hermetic data-only-extension proof. It asserts the BEFORE
state (`no_match`, empty ids), writes the real substrate + ONE addition (`severe_headache`,
`very_urgent`, alias `severe headache`) to `tmp_path`, redirects the ONE loader
(`monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)` + `get_discriminators.cache_clear()`), and
asserts the AFTER state through the shipped matcher/scorer (matched id + a normal-vitals GREEN
overridden to ORANGE). It runs the shipped substrate-shape predicates against the redirected loader,
proves the alias is unique and absent from every `evals/cases/*.yaml` fixture, and asserts
`git status --porcelain -- src/` is empty. The cache is cleared in a `finally` in every loader-redirecting
test, so no other test sees the tmp substrate.

## Verification

- `uv run pytest tests/test_review_runbook.py tests/test_data_extension.py -q` → 9 passed.
- The four existing doc/runbook guards (`test_docs_final`, `test_demo_runbook`, `test_readme_runbook`,
  `test_desk_runbook`) stay green.
- `git status --porcelain -- src/ data/` prints nothing (no source or data change).
- `uv run pytest -q` → **453 passed** (444 baseline + 9 new guards).

## TDD Notes

Task 2 carries `tdd="true"` but the plan frontmatter is `type: execute` (not `tdd`), so the plan-level
TDD gate does not apply. Task 2 is a **demonstration harness** (it proves existing shipped behaviour),
so its RED is the asserted BEFORE state — the phrase matches nothing (`no_match is True`, empty ids)
before the data edit — and its GREEN is the AFTER re-score through the shipped path. No production
code was added, so there is no separate failing-first implementation cycle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stale repo-root `spans.jsonl` broke the baseline**
- **Found during:** pre-execution baseline run
- **Issue:** a leftover, gitignored `spans.jsonl` at the repo root made
  `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root` fail (443 passed,
  1 failed) — the baseline is documented as 444 passing.
- **Fix:** removed the stale runtime artifact (`rm -f spans.jsonl`); it is gitignored, so no repo state
  changed. The test then passed and the suite returned to 444.
- **Files modified:** none (untracked, gitignored runtime artifact)
- **Commit:** none (artifact removal, not tracked)

**2. [Rule 1 - Bug] `from tests.test_sats_discriminators import …` failed under pytest**
- **Found during:** Task 2 first run
- **Issue:** `tests/` is not an importable package under pytest (no `__init__.py`), so the plan's
  preferred direct import of the shipped substrate-shape predicates raised `ModuleNotFoundError`.
- **Fix:** load the shipped predicate module by file path via `importlib.util.spec_from_file_location`,
  then call the shipped predicate functions — still the real predicates, never a hand-copied list (the
  plan's stated fallback was avoided in favour of genuinely reusing the shipped checks).
- **Files modified:** tests/test_data_extension.py
- **Commit:** f639682

## Auth Gates

None.

## Known Stubs

None. The `<content-id>` tokens in `docs/REVIEW.md` are documented runbook placeholders for the
presenter to paste the content-derived thread id printed by `demo --durable` — they are deliberate
presenter inputs, not unimplemented code stubs.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change. Every documented
command is local/loopback; the harness writes only under `tmp_path` (T-12-01/02/03/05 mitigations are
implemented as the runbook revert steps, the demonstrated (not asserted) extension, the fixture-absence
assertion, and the hermetic tmp substrate).

## Self-Check: PASSED

- `docs/REVIEW.md` — FOUND
- `tests/test_review_runbook.py` — FOUND
- `tests/test_data_extension.py` — FOUND
- commit 189be1a — FOUND
- commit f639682 — FOUND
