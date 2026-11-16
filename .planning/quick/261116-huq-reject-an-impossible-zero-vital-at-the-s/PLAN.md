# Quick Task: a zero vital must abstain, not score

## Goal
A recorded `0` for respiratory rate, heart rate or systolic BP must return the fail-closed
abstain ("re-measure"), never a colour.

## Measured defect (nurse stress test 2026-11-16, S1)
`score_priority` with RR 0, HR 0, and SBP 0 each returned `colour: "YELLOW", tews: 3,
target: "< 1 hour"`. A patient with no recordable pulse or BP is peri-arrest; YELLOW is a
six-band under-triage. The schema allows `>= 0`, and the bands read "< 9 / < 41 / < 71" as
3 points.

## Change
In `src/triagedesk/mcp/server.py::score_priority` (the TOOL, not the scorer), before scoring:
map a recorded zero for `respiratory_rate`, `heart_rate`, `systolic_bp` to "not recorded" on a
COPY of the case, so the scorer's existing `missing_vitals` abstain fires with its existing
reason ("missing scored vitals: …; re-measure before scoring").

- Name the zero set once as a module-level constant with a docstring: a zero is not a
  measurement, so the honest answer is "re-measure", not a band.
- Do NOT edit `core/scorer.py` (frozen kernel). Do NOT change any YAML.
- The graph calls this tool, so it is covered too.

## Acceptance
- New/updated tests (e.g. `tests/test_zero_vitals.py`): for each of the three fields,
  `score_priority` returns `abstained=True`, `colour is None`, `tews is None`,
  `missing_vitals == [field]`, `citations == []`, reason contains "re-measure".
- A normal case is unchanged (GREEN, TEWS 0, baseline citation).
- A legitimate zero elsewhere (e.g. `trauma: false`) is untouched.

## Operating constraints

- Work only in the git worktree `/tmp/opencode/triage-batch` (branch `fix/nurse-stress-test-batch`).
- Stage ONLY the files this plan names. Never stage `.planning/`, `spans.jsonl`, `checkpoints.db`,
  `triage.db`, or any untracked `docs/assets/*` file.
- Commit atomically with a conventional message.
- Follow `docs/CONVENTIONS.md` (DRY + SOLID). Do not edit the scorer's arithmetic (`core/scorer.py`),
  the citation helper or the `@audited` interceptor unless this plan explicitly says so (D-18).
- Run the targeted tests you add/update, plus `uv run ruff check src tests`.

## Report back

Commit hash, files changed, test names, targeted + full-suite counts, ruff result, any deviation.
