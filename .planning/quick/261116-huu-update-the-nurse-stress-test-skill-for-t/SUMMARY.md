# Quick Task SUMMARY — the nurse stress-test skill describes the shipped system

- **Task:** `261116-huu-update-the-nurse-stress-test-skill-for-t`
- **Branch:** `fix/nurse-stress-test-batch`
- **Commit:** `69e4a75` — `docs(quick-261116-huu): teach the nurse skill the nine-tool, three-way-coverage system`
- **Status:** complete. Documentation-only; one file changed.

## What changed

`.claude/skills/triage-nurse-stress-test/SKILL.md` only (+124 / −29). The packaged skill under
`src/triagedesk/skills/triagedesk-triage/` was **not** touched, and no source, test, data, or
scorer file changed.

| Section | Edit |
| --- | --- |
| Frontmatter | Added clarification/elicitation trigger phrases. |
| §1 tool table | Now all **nine** tools with **Model?** and **Queue write?** columns: added `plan_next_step` (model except the `finish_investigation` fast path; no queue write) and `request_clarification` (no model; no queue write; ≤3 questions). Fixed "the other eight tools" → the other **seven**; the two model users are `normalize_case` and the non-fast `plan_next_step`. |
| §1 · Coverage is three-way | Replaced the one-boolean `no_match` framing with `retrieval_status` (`matched` / `ambiguous` / `no_candidate`) mapped to `assess_confidence.action` (`deliver` / `clarify` / `defer`). States plainly: an `ambiguous` case asks one bounded question and **never** presents a colour; a second ambiguity defers. |
| §1 · Elicitation | Four outcomes (`accepted` / `declined` / `cancelled` / `unavailable`); only `accepted` carries answers; a decline is not a negative finding; an answered question is not an approval (the gate still pauses); `plan_next_step` proposes, the guard disposes. |
| §2 intro | New blockquote naming **E-09** as the one declared, unfixed failure — reported as declared, never tuned green. |
| §2.3 | Missing data must abstain; a colour with no citations is a raw-MCP trap. |
| §2.4 | Added the zero-vital rule: RR/HR/SBP `0` must return `abstained: true` with no colour and a re-measure request; a zero that becomes a colour is S1; `trauma: false` still scores. |
| §2.6 | Added local idiom `fit`, `fitting` (current seizure, not "physically fit"), `collapsed`, `post-ictal`; every probe now records `retrieval_status`, `matched_ids`, confidence action and colour. |
| §2.8 | Added the clarification path: an accepted answer must not approve; a decline/cancel/unavailable must not be converted into a value. |
| §2.10 | Timing updated: `normalize_case` 19–37 s; audited deterministic calls ~10 ms after the store cache (was 2.6–3.1 s); one patient ~21 s; ten patients ~3.5 min. |
| §3 Grading | FAIL/S1 now include a colour shown on an `ambiguous` case and an elicitation answer treated as approval. |
| §4 Report template | Coverage table gains `retrieval_status` and confidence-action columns, with a note that a `CLARIFY` is not a deferral. |
| §5 Competition lens | Added three-way coverage with bounded clarification to the wins. |
| §6 Done criteria | Requires `retrieval_status` + action per probe and E-09 reported as declared. |

The ten-section battery structure is intact (`### 2.1`–`### 2.10`, verified count = 10); edits
extend sections rather than renumber them. The read-only rule ("only reads and calls the MCP;
never changes `data/`, `src/`, or the scorer") is unchanged.

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest -q` | **982 passed** in 60.26 s |
| `uv run ruff check src tests` | **All checks passed!** |
| `git status` after commit | Only the four untracked `.planning/quick/` task dirs; no `.planning/` file staged, no `spans.jsonl`, `checkpoints.db`, `triage.db`, or `docs/assets/*` staged |
| Commit | `69e4a75`, 1 file changed (+124 / −29) |

## Deviations / judgement calls

- **Timing numbers follow the operative brief, not the PLAN.md text.** PLAN.md §6 still carries
  the pre-store-fix numbers (`~32 s`, `~5 min`); the task brief supplied the revised figures
  (`19–37 s`, `~10 ms` per audited call, `~21 s` per patient, `~3.5 min` for ten). The newer
  figures match `261116-hut`'s measured before/after and the phase-1 measurement, so they were
  used. Documented here rather than silently mixing scales.
- **Coverage/elicitation live in §1, the declared failure in §2's intro.** The brief requires the
  ten-section battery to stay ten sections, so the cross-cutting coverage and elicitation
  material was added as §1 subsections and the E-09 note as a pre-battery blockquote — no
  battery section was added or renumbered.

## Could not verify

- No live MCP/nurse run was repeated in this worktree, so the timing figures are transcribed from
  the recorded measurements (`261116-hut` SUMMARY and the 2026-11-16 brief) rather than
  re-measured here. The skill documents them as "measured on this CPU (2026-11-16)".
- The two S1s the 2026-11-16 run found (zero-vital scoring and the unresolved local "fit" idiom)
  are covered by the committed fixes `be570fa` and `536a73e`; the skill names them as tests to
  run, but this task did not re-drive those live probes.
