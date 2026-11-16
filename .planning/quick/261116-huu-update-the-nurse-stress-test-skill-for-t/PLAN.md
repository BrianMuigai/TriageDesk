# Quick Task: update the nurse stress-test skill for the shipped system

## Goal
`.claude/skills/triage-nurse-stress-test/SKILL.md` must describe the nine-tool system that ships
today, and its battery must catch the two S1s the 2026-11-16 run found.

## Required edits (this file only)
1. **Tool table — nine tools.** Add `plan_next_step` (model, no queue write) and
   `request_clarification` (no model, no queue write; at most three questions). Fix the
   "the other eight tools" sentence to match. Keep the model/queue/use columns.
2. **Coverage is three-way.** Replace the one-boolean `no_match` framing with
   `retrieval_status` (`matched` / `ambiguous` / `no_candidate`) plus
   `assess_confidence.action` (`deliver` / `clarify` / `defer`). State plainly:
   an `ambiguous` case must ask one bounded question and must NEVER present a colour;
   a second ambiguity defers.
3. **Elicitation.** Add a short subsection: the four outcomes
   (`accepted` / `declined` / `cancelled` / `unavailable`); only `accepted` carries answers; a
   decline is NOT a negative finding; an answered question is NOT an approval (the gate still
   pauses). `plan_next_step` proposes, the deterministic guard disposes.
4. **Battery additions** (keep the ten-section structure; extend rather than renumber):
   - 2.4: a recorded zero (RR/HR/SBP) must never be a colour — expect the re-measure abstain.
   - 2.6: include local idiom `fit`, `fitting`, `collapsed`, `post-ictal`; record
     `retrieval_status` and the confidence action for every probe.
   - 2.8: add the clarification path — an accepted answer must not approve; a decline must not be
     converted into a value.
5. **Declared failure.** Name E-09 explicitly as the one declared, unfixed failure; a tester must
   never "fix" it green.
6. **Timing.** Update the measured numbers: `normalize_case` 19–37 s on CPU; ~2.6–3.1 s per
   audited call until the store fix lands; one patient ~32 s; ten patients ~5 min.
7. **Report template.** Add columns for `retrieval_status` and the confidence action.

## Hard constraints
- Read-only skill: it must keep saying the battery never edits `data/`, `src/` or the scorer.
- Do NOT touch `src/triagedesk/skills/triagedesk-triage/` (a different, packaged skill).
- Documentation only: no source code changes.

## Acceptance
- `uv run pytest -q` unchanged and green; `uv run ruff check src tests` clean.
- The file no longer claims eight tools and no longer omits the planner/elicitation path.

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
