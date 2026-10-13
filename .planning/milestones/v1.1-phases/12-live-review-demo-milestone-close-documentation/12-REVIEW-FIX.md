---
phase: 12-live-review-demo-milestone-close-documentation
fixed_at: 2026-10-13T11:55:34Z
review_path: /home/brian/Desktop/brij/ai/TriageDesk/.planning/phases/12-live-review-demo-milestone-close-documentation/12-REVIEW.md
iteration: 3
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-10-13T11:55:34Z
**Source review:** /home/brian/Desktop/brij/ai/TriageDesk/.planning/phases/12-live-review-demo-milestone-close-documentation/12-REVIEW.md
**Iteration:** 3

**Summary:**
- Findings in scope: 5 (1 warning + 4 info; `fix_scope: critical_warning` — the four Info advisories are
  the enumerated-sweep residuals this final pass was explicitly asked to close)
- Fixed: 5
- Skipped: 0

**Verification environment:** the **main checkout**. `workflow.use_worktrees` is `false`, so no isolated
worktree was created — fixes were edited and committed in the main working tree and every gate below ran
there. Each fix is its own commit with **explicit paths** (the GSD `commit` verb is disabled by this
project's freeze policy, `commit_docs: false`, exactly as the iteration-2 fixes were committed); nothing
unrelated was staged.

## Fixed Issues

### WR-01: `docs/DEMO.md`'s beat table timing bands contradict the canonical storyboard it claims to map

**Files modified:** `docs/ROADMAP.md`
**Commit:** `8c4e081`
**Applied fix:** **Direction chosen: updated the canonical storyboard to the runbook's bands** — the
runbook (`docs/DEMO.md`) is the retimed, presenter-facing, *shipped* artefact. `docs/ROADMAP.md`
§*Demo storyboard* now carries the same seven `Time` bands as `docs/DEMO.md`'s beat table:
`0:00–0:15 · 0:15–0:50 · 0:50–1:20 · 1:20–1:45 · 1:45–2:10 · 2:10–2:40 · 2:40–2:50`, with `routine` and
`escalation` split into their own rows as the runbook does. `docs/DEMO.md:17-20`'s "maps those timing
bands" claim is now **TRUE**; `docs/DEMO.md` itself was not changed (it was already the shipped bands).
The two in-scope docs no longer present conflicting timing tables.

### IN-01: `docs/PROJECT.md` still named `qwen3.5:4b` as the compute choice

**Files modified:** `docs/PROJECT.md`
**Commit:** `014299e`
**Applied fix:** §8 Constraints → **Compute** row now states the resolved outcome: "The Phase-1 spike
selected **`qwen2.5:1.5b`** as the default (`qwen3.5:4b` is the verified fallback); see `DECISIONS.md`
D3." (was "Use the installed **`qwen3.5:4b`**; Phase 1 measures RAM fit; smaller Qwen fallback
otherwise."). This aligns the row with D3, `NOTICE:52-53`, `ARCHITECTURE.md:91`, `STATUS.md:36`,
`REQUIREMENTS.md` BW-5/G-2, and the measured `report.json` `provenance.model_tag`.

### IN-02: `src/triagedesk/llm/client.py` model constants/comment disagree with the reconciled docs

**Files modified:** `src/triagedesk/llm/client.py`, `scripts/spike_model.py`
**Commit:** `5eb12aa`
**Applied fix:** **comment/naming-only** — no behaviour, default-model, or measured-outcome change.
- Corrected the stale RAM figure **587 → 641 MB** (the value `evidence/model-spike.json`
  `primary.ram_after.available_mb` records, matching `docs/DECISIONS.md:28`).
- Removed the inverted "fallback" naming: `PRIMARY_MODEL` → `BIG_MODEL` (the larger, **aspirational
  alternative** — the docs' "verified fallback"), `FALLBACK_MODEL` → `SMALL_MODEL` (the measured
  default); `DEFAULT_MODEL = SMALL_MODEL` (value unchanged: `qwen2.5:1.5b`).
- `scripts/spike_model.py` (the only importer) updated to the renamed constants; its evidence-JSON
  schema — the `"primary"`/`"fallback"` keys — is untouched, so no measured artefact changes. Verified:
  `from triagedesk.llm.client import BIG_MODEL, SMALL_MODEL, DEFAULT_MODEL` →
  `qwen3.5:4b / qwen2.5:1.5b / qwen2.5:1.5b`; `DEFAULT_MODEL == "qwen2.5:1.5b"` (the value
  `scripts/hash_data.py` cross-checks against the spike evidence).

### IN-03: `STATUS.md` §0 score band did not equal its own §3 per-criterion sum

**Files modified:** `STATUS.md`
**Commit:** `c8fe673`
**Applied fix:** §0 Judging-criteria band `~75–90` → **`~79–94`** — the exact sum of §3's per-criterion
bands (27–30 + 18–20 + 9–14 + 13–15 + 9–10 + 3–5). No per-criterion figure was altered.

### IN-04: `STATUS.md` §0 counted one pending confirmation while §1/§5 list two

**Files modified:** `STATUS.md`
**Commit:** `fa9e257`
**Applied fix:** §0 "Eligible / not disqualified" now reads "✅ (two confirmations pending — G8 timing,
G9 eligibility)", matching §1 row 6 (G8) and §5 (G8 + G9).

## Skipped Issues

None — all in-scope findings were fixed.

## Honesty & guard state (post-fix)

- `uv run pytest -q` → **454 passed** (31.7–32.2 s), unchanged from the pre-pass count.
- `scripts/emit_evals.py --check` → exit **0** (`EVALS.md is up to date (report 12d6d1b909d33872)`);
  `EVALS.md` remains the generator projection of `evals/results/report.json` and **no measured number was
  tuned**.
- `ARCHITECTURE.md` = **694 words / 93 lines** (≤ 700/110). `DESCRIPTION.md` = **326 prose words**
  (within 270–330).
- Untouched by this pass: `core/scorer.py` arithmetic, the citation helper, the `@audited` audit
  behaviour, the graph topology, `data/*.yaml`, `evals/results/report.json`, and every expectation. No
  new dependency. `git status --porcelain -- src/ data/ evals/` is empty.
- **Hermeticity:** a probe had left an untracked, gitignored `spans.jsonl` (44 KB) in the repo root,
  failing `test_no_spans_artifact_is_written_to_the_repo_root`; it was removed, so the suite is green and
  hermetic. No repo-root `spans.jsonl`/`*.db` remains.
- **No over-claim.** The human steps stay flagged (`docs/DEMO.md` `human_needed`; `docs/REVIEW.md` "What
  is human"; `EVALS.md` §7 marked/attributed **empty** clinician slot; `STATUS.md` G1/G2); the residual
  misses stay visible (`EVALS.md` §6 E-09; §6.1 E-11/E-13 recorded gate failures; the deferral markers on
  E-01/E-08/E-09/E-14). The `failure` beat still prints `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN
  MISMATCH)`.

---

_Fixed: 2026-10-13T11:55:34Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 3_
