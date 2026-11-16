# Quick Task: cover the local word "fit"

## Goal
`match_discriminators("fit")` must stop returning `no_candidate`, so a seizure presentation can
never be delivered as a vitals-only GREEN.

## Measured defect (nurse stress test 2026-11-16, S1)
`match_discriminators("fit")` → `{ids: [], status: "no_candidate", candidates: []}`;
`assess_confidence` → `deliver, moderate`; `score_priority` on normal vitals → GREEN.
The family exists and works for other words: "fitting" and "convulsion" → `seizure_current`
(matched), "post-ictal" → `seizure_post_ictal` (matched), "seizure" → `ambiguous` with
candidates `[seizure_current, seizure_post_ictal]`.

## Change — DATA ONLY
Inspect `data/sats_discriminators.yaml` (aliases) and, if that is how the ambiguous family is
declared, `data/text_terms.yaml`. Add "fit" so the matcher returns either:

- `matched` on a seizure discriminator (over-triage is fail-safe), or
- `ambiguous` with the seizure candidates (the tool then asks its one question),

but **never `no_candidate`**. Match the file's existing style; no code change, no threshold
change, no new discriminator id.

## Hard constraints
- Do NOT add an alias for "feeling unwell" or touch E-09 in any way. E-09 stays the declared,
  unfixed failure.
- Do not change any eval fixture or expectation.

## Acceptance
- Test: `match_discriminators("fit").retrieval_status in {"matched", "ambiguous"}` and the ids or
  candidates name a seizure discriminator; `retrieve_evidence("fit")` is consistent with it.
- Regression guard: `match_discriminators("feeling unwell")` still returns `no_candidate`.
- Full suite green (no eval fixture contains "fit").

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
