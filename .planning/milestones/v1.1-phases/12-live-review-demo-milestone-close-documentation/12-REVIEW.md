---
phase: 12-live-review-demo-milestone-close-documentation
reviewed: 2026-10-13T12:03:20Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - ARCHITECTURE.md
  - DESCRIPTION.md
  - EVALS.md
  - README.md
  - STATUS.md
  - docs/DECISIONS.md
  - docs/DEMO.md
  - docs/PROJECT.md
  - docs/REQUIREMENTS.md
  - docs/REVIEW.md
  - docs/ROADMAP.md
  - src/triagedesk/llm/client.py
  - scripts/spike_model.py
  - tests/test_data_extension.py
  - tests/test_review_runbook.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 12: Code Review Report

**Reviewed:** 2026-10-13T12:03:20Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** clean

## Summary

Final convergence review after the third fix pass. I verified each of the five fix commits against the
**current** source (not the fix descriptions), re-ran the shipped guards, and swept the submission docs
for cross-artifact contradictions. **No critical or warning findings remain.** The two remaining items
are sub-threshold advisories, listed at the end and neither blocks the phase.

**All five fixes are confirmed applied, correct, and free of side effects:**

- **`8c4e081` — WR-01 (DEMO↔ROADMAP timing bands).** `docs/ROADMAP.md:28-36`'s canonical *Demo
  storyboard* `Time` column is now byte-identical to `docs/DEMO.md:127-135`'s runbook bands — both are
  `0:00–0:15 · 0:15–0:50 · 0:50–1:20 · 1:20–1:45 · 1:45–2:10 · 2:10–2:40 · 2:40–2:50` (a line-for-line
  `diff` of the two columns is empty). `docs/DEMO.md:17-20`'s claim that the runbook "maps those timing
  bands" is therefore now **true**, and the two in-scope docs no longer present conflicting tables. The
  old bands (`0:20–1:10`, `1:10–1:50`, `1:50–2:30`, `2:30–2:50`, `2:50–3:00`) appear nowhere in the
  submission docs.
- **`014299e` — IN-01 (PROJECT.md compute row).** `docs/PROJECT.md:131` now reads "The Phase-1 spike
  selected **`qwen2.5:1.5b`** as the default (`qwen3.5:4b` is the verified fallback); see `DECISIONS.md`
  D3" — matching every other reconciled source (D3, NOTICE, ARCHITECTURE.md:91, STATUS.md:36,
  REQUIREMENTS.md BW-5/G-2) and the measured artefact.
- **`5eb12aa` — IN-02 (model constants/comment).** `src/triagedesk/llm/client.py` renames
  `PRIMARY_MODEL`→`BIG_MODEL` (`"qwen3.5:4b"`) and `FALLBACK_MODEL`→`SMALL_MODEL` (`"qwen2.5:1.5b"`),
  with `DEFAULT_MODEL = SMALL_MODEL`; the comment is corrected `587 → 641 MB`. I inspected the full diff
  (`git show 5eb12aa`): **it is naming/comment only** — no value, control flow, or call changed.
  Runtime-confirmed: `DEFAULT_MODEL` still resolves to `qwen2.5:1.5b` (unchanged). `scripts/spike_model.py`
  is updated consistently (imports `BIG_MODEL`/`SMALL_MODEL`); no stale `PRIMARY_MODEL`/`FALLBACK_MODEL`
  reference survives anywhere in `src/`, `tests/` or `scripts/` (only historical `.planning/` artifacts
  still mention the old names, which is expected).
- **`c8fe673` — IN-03 (STATUS §0 band).** `STATUS.md:24` now reads "🟡 **est. ~79–94**", exactly the sum
  of the §3 per-criterion estimates (`27–30 + 18–20 + 9–14 + 13–15 + 9–10 + 3–5 = 79–94`). The old
  `~75–90` band is gone.
- **`fa9e257` — IN-04 (STATUS pending confirmations).** `STATUS.md:21` now reads "✅ (two confirmations
  pending — G8 timing, G9 eligibility)", consistent with §1 row 6 (`G8`) and §5 (which lists both G8 and
  G9). No "one confirmation" text remains.

**No measured outcome or behaviour changed.** `uv run pytest -q` → **454 passed** (32.47 s);
`scripts/emit_evals.py --check` → exit **0** (`EVALS.md is up to date (report 12d6d1b909d33872)`), so the
published `EVALS.md` is still byte-identical to the generator's projection of `evals/results/report.json`
(digest unchanged). `git status --porcelain -- src/ data/` is empty; the `v1.0-submission` tag resolves
(`157a793e`); the recorded demo (`docs/assets/triagedesk-demo.mp4`) is 32.88 s ≈ the "33 s" the docs claim.

**Shipped entry point re-run.** `uv run triagedesk demo` exits `0` and reproduces every `docs/DEMO.md`
outcome block: **seven** owned tools; the `refusal` beat prints `clinician dismissed the priority;
refusing to commit` + `rows added this beat: 0`; the `failure` beat prints `DECLARED: ORANGE` /
`MEASURED: GREEN (SHOWN MISMATCH)`. `uv run triagedesk demo --list` prints exactly the five beat names the
runbook documents.

**Consistency sweep — clean.** Model name (every mention of `qwen2.5:1.5b` is "default/measured"; every
mention of `qwen3.5:4b` is "fallback"): consistent. No stale hard test count, no stale `587`/`~600 MB`
figure, no stale timing band, no broken internal link (all 22 referenced artifacts exist), and the
honesty invariants hold: the human upload stays flagged (`human_needed` in `docs/DEMO.md`/`docs/REVIEW.md`;
STATUS G1/G2), `EVALS.md` §7 keeps the **empty** clinician slot ("none obtained as of 2026-10-13"), and
the residual misses stay visible (`EVALS.md` §6 E-09; §6.1 E-11/E-13 recorded gate failures; the
`⏸ deferral` markers on E-01/E-08/E-09/E-14). Doc guards hold: `ARCHITECTURE.md` = 694 words / 93 lines
(within 700/110); `DESCRIPTION.md` = 326 prose words (within 270-330); `docs/REVIEW.md` still names
"reload" as a **fresh process**; the in-scope tests (`tests/test_data_extension.py`,
`tests/test_review_runbook.py`) pass and their referenced siblings (`tests/test_demo_runbook.py`,
`tests/test_docs_final.py`) exist.

## Advisories (sub-threshold; non-blocking)

### IN-01: `evidence/model-spike.json` uses `"fallback"` for the *small* model, while the docs use "verified fallback" for the 4B

**File:** `evidence/model-spike.json` (`"fallback": {model: "qwen2.5:1.5b"}`) vs `docs/DECISIONS.md:28,313`
(`qwen3.5:4b` = "verified fallback")

**Issue:** The evidence file's `fallback` key names the smaller Qwen (`qwen2.5:1.5b`) — the shipped
default — whereas every submission doc uses "verified fallback" for the 4B. A judge cross-referencing
D3 with the evidence could momentarily read two different "fallback" models. This is **pre-existing**
(not introduced by this phase), **outside the reviewed submission-doc set**, and the sense is now
documented in code: `src/triagedesk/llm/client.py:34` annotates `BIG_MODEL` as "docs' \"verified
fallback\"" and `scripts/spike_model.py:139-140` states "`\"primary\"` = the larger candidate
(qwen3.5:4b), `\"fallback\"` = the smaller candidate (qwen2.5:1.5b)". Because the collision is now
explicitly explained at the point of definition, it is an advisory, not a warning.

**Fix (optional):** if the sweep is to be fully unambiguous, either rename the evidence keys to
`larger`/`smaller` (or `candidate_big`/`candidate_small`) in `spike_model.py` and regenerate
`evidence/model-spike.json`, or add a one-line note in `docs/DECISIONS.md` D3 that the evidence file's
`fallback` key is the small candidate.

### IN-02: `scripts/spike_model.py:_run` does not fail loudly on a failed subprocess

**File:** `scripts/spike_model.py:38-39`

**Issue:** `_run` returns `subprocess.run(cmd, capture_output=True, text=True).stdout` without
`check=True`; a failed `free`/`ollama` invocation yields empty stdout, which `_free_available_mb` then
reports as `0` and `_licence` as `"unknown"`. On a re-run this could silently mis-evaluate the budget
gate (0 < 1024 → select the small model) rather than surfacing the tooling failure. This is a
spike/evidence script (not on the agent path) whose committed output already exists, so the impact is
sub-threshold.

**Fix (optional):** pass `check=True` (or assert the return code) so a missing/failed `free`/`ollama`
aborts the spike instead of degrading to `0`.

---

_Reviewed: 2026-10-13T12:03:20Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
