---
phase: 12-live-review-demo-milestone-close-documentation
verified: 2026-10-13T12:13:23Z
status: passed
score: 13/13 must-haves verified
# Owner decision (2026-10-13): all 13 must-haves are VERIFIED; the two `human_verification` items below are
# out-of-band SUBMISSION actions (record/upload the video; obtain a clinician review), not phase gaps. The
# phase is marked `passed` and both items are recorded as deferred submission steps in STATE.md.
deferred_human_submission_steps: 2
covered_files: [".planning/phases/12-live-review-demo-milestone-close-documentation/12-01-PLAN.md", ".planning/phases/12-live-review-demo-milestone-close-documentation/12-01-SUMMARY.md", ".planning/phases/12-live-review-demo-milestone-close-documentation/12-02-PLAN.md", ".planning/phases/12-live-review-demo-milestone-close-documentation/12-02-SUMMARY.md", ".planning/phases/12-live-review-demo-milestone-close-documentation/12-03-PLAN.md", ".planning/phases/12-live-review-demo-milestone-close-documentation/12-03-SUMMARY.md", "ARCHITECTURE.md", "DESCRIPTION.md", "EVALS.md", "README.md", "STATUS.md", "docs/DECISIONS.md", "docs/DEMO.md", "docs/REQUIREMENTS.md", "docs/REVIEW.md", "docs/ROADMAP.md", "scripts/spike_model.py", "src/triagedesk/llm/client.py", "tests/test_data_extension.py", "tests/test_review_runbook.py"]
covered_digest: "v3:sha256:b7cd8a6e1fea8b579d52c43e0e80713eb7534742b868b79f6714dea191abcdbc"
behavior_unverified: 0
overrides_applied: 0
gaps: []
human_verification:
  - test: "Record the 2–3 minute narrated demo from docs/DEMO.md and upload it PUBLICLY (YouTube/Vimeo), then paste the URL into the submission form."
    expected: "A public, unedited screen recording ≤3 min showing the seven owned tool calls, the measured EVALS.md projection, and the live E-09 failure beat (DECLARED: ORANGE / MEASURED: GREEN)."
    why_human: "Recording and hosting are physical/human actions outside the repository; the phase prepares the runbook + narration and flags this as the one submission blocker (STATUS G1, REQUIREMENTS G-9). It is never claimed as done. Note the existing local tape is 32.88 s (flagged thin at STATUS G5) — a re-recording to the retimed 2:50 script is the honest path."
  - test: "Obtain a single triage nurse/clinician review and, if arranged, paste the attributed quote (name/role/date, with consent) into EVALS.md §7 and README.md."
    expected: "Either an attributed quote lands in EVALS.md §7 / README, or the gap stays honestly declared with the marked, empty slot that already ships."
    why_human: "Access to a clinician is an external relationship, not a codebase change. The phase delivers the sanctioned alternative — an honest re-declaration with an empty, attributed slot and no invented quote — which IS criterion 3's fallback branch."
---

# Phase 12: Live Review, Demo & Milestone-Close Documentation Verification Report

**Phase Goal:** The live technical review is rehearsed end-to-end including a live one-line discriminator edit, the demo runs to 2–3 minutes with narration and the measured eval on screen, the clinical-fit gap is re-declared honestly, and every submission document is refreshed to the v1.1 state.
**Verified:** 2026-10-13T12:13:23Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1 | REV-01/SC1: A 10-minute live walkthrough runbook exists and every documented `uv run triagedesk …` invocation is accepted by the shipped CLI (driven through `triagedesk.cli.main` with all five side-effect seams spied, each reaching exactly one seam). | ✓ VERIFIED | `docs/REVIEW.md` (8 beats, all `uv run triagedesk …` lines fenced, no trailing comments); `tests/test_review_runbook.py` passes; `uv run pytest -q` → **454 passed**. |
| 2 | REV-01/SC1: The "add a discriminator live, reload, re-score" extension is **data-only** — demonstrated (not asserted) through the shipped matcher/scorer with `src/` byte-unchanged, and the substrate-shape safety suite stays green WITH the addition. | ✓ VERIFIED | `tests/test_data_extension.py`: BEFORE `no_match is True`/`[]`; AFTER redirecting `rules.DISCRIMINATORS_PATH` + `get_discriminators.cache_clear()` → `matched_ids == ["severe_headache"]`, a normal-vitals GREEN overridden to ORANGE, and the shipped `test_sats_discriminators` predicates run against the extended loader. `git status --porcelain -- src/` returns nothing. |
| 3 | REV-01: The live-extension alias is unique across the substrate and absent from every `evals/cases/*.yaml` complaint/note, so the demonstration adds a capability rather than re-tuning a published case (E-09). | ✓ VERIFIED | `test_the_extension_is_well_formed_and_unambiguous` (alias count == 1) and `test_the_chosen_alias_is_absent_from_every_published_case` (loads all fixtures via the shipped `load_cases`, asserts non-vacuous) both pass. |
| 4 | REV-01/D12-05: `docs/REVIEW.md` states plainly that "reload" means a **fresh process** (no `--reload`, no cache-clear flag) and flags the recording and the public upload as **HUMAN** actions. | ✓ VERIFIED | `docs/REVIEW.md` blockquotes 2–3; guard asserts `human`, `upload`, `fresh process`, `data/sats_discriminators.yaml`, `no code`, `E-09` — all present, test green. |
| 5 | DEMO-02/D12-10: `docs/DEMO.md` stops contradicting the shipped CLI — `routine`/`deterioration` show **no** `commit` line (they defer), `escalation` commits at **queue position 1**, the run names **seven owned tools**, and the Phase-11 "Known drift" note is deleted. | ✓ VERIFIED | Live `uv run triagedesk demo` reproduces every block: routine/deterioration defer with no `commit`; `commit : committed case 9300336d37c3651c at queue position 1 (ORANGE)`; refusal prints `clinician dismissed the priority; refusing to commit` + `rows added this beat: 0`; `grep -c "Known drift" docs/DEMO.md` → 0; `grep -c "five owned tools"` → 0. `tests/test_demo_runbook.py` green. |
| 6 | DEMO-02/SC2: The demo shows the measured eval honestly — the committed `EVALS.md` projection plus the live `failure` beat — and states plainly that the ~10-minute `mode: real` run is silent and **NOT streamed**. | ✓ VERIFIED | `docs/DEMO.md` §"The measured eval on screen (not a live run)" + retimed 2:50 table (measured-eval beat at 2:10–2:40); `report.json` is `mode: real`, 3 runs × 16 cases; `failure` beat prints `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)`. |
| 7 | DEMO-02/D12-05: The recording and the public upload are flagged `human_needed` and never claimed as done. | ✓ VERIFIED | `docs/DEMO.md` header blockquotes ("The recording is a HUMAN action" / "human_needed — the public upload … never claims a video is recorded or hosted"); README "recorded but not yet uploaded"; STATUS G1/G2. No doc asserts a hosted video. |
| 8 | FIT-01/SC3: README and `EVALS.md` §7 re-declare the clinical-fit gap honestly (no review obtained as of 2026-10-13) with a marked, attributed, **empty** quote slot and **no invented quote** — the criterion's sanctioned fallback. | ✓ VERIFIED | `EVALS.md` §7: "**Clinician review: none obtained as of 2026-10-13.** If a triage nurse/clinician review is arranged, add their attributed quote here (name/role/date, with consent). Nothing is claimed until it is."; README "What is unfinished" mirrors it; `grep -c "before Day 5" EVALS.md` → 0. No name/date/quote invented. |
| 9 | DOCS-06: `ARCHITECTURE.md` names the real graph (`ground`, `assess`, `request_missing_info`, `escalate`) while staying ≤ 700 words AND ≤ 110 lines, with `qwen2.5:1.5b` still present. | ✓ VERIFIED | `ARCHITECTURE.md` = **694 words / 93 lines** (independently counted); node table rows for `ground`/`assess`/`request_missing_info · escalate`; `qwen2.5:1.5b` present; `tests/test_docs_final.py` one-page + model guards green. |
| 10 | DOCS-06: `DESCRIPTION.md` stays within ±10% of 300 prose words and names a v1.1 capability. | ✓ VERIFIED | 326 prose words (within 270–330); names the durable approve/resume gate over `checkpoints.db` and the retrieval-grounded `no_match` deferral banner; header/closing count comments preserved; guard green. |
| 11 | DOCS-06/SC4: STATUS.md, `docs/REQUIREMENTS.md` and `docs/ROADMAP.md` carry no stale v1.0 claim — resolved work marked resolved, the genuinely open items (no clinician review, un-uploaded video) stay open. | ✓ VERIFIED | Stale-token grep (`5 distinct tools`/`5 reusable tool contracts`/`no desk surface`/`not wired E2E`/`no spans`/`Known drift`/`before Day 5`) → nothing across all refreshed docs; REQUIREMENTS JC-1/DQ-2 = seven tools, ST-1 rehearsed (links `REVIEW.md`), G-9 OPEN-human, dated 2026-10-13; STATUS links ARCHITECTURE/EVALS rather than restating counts/latency; ROADMAP storyboard bands byte-match DEMO.md. |
| 12 | DOCS-06/D12-09/D12-11: `EVALS.md` remains only the `emit_evals.py` projection of `report.json`, and every existing doc guard stays green (no guard weakened). | ✓ VERIFIED | `uv run python scripts/emit_evals.py --check` → exit 0 ("EVALS.md is up to date (report 12d6d1b909d33872)"); `git log --name-only` over the phase shows **no** edit to `test_docs_final.py`/`test_demo_runbook.py`/`test_readme_runbook.py`/`test_desk_runbook.py`/`test_sats_discriminators.py`; the 6 doc/runbook guards pass (33 passed). |
| 13 | Cross-cutting prohibitions: no permanent `data/*.yaml` change, no new dependency, no source-*behaviour* change, no doc-guard relaxation. | ✓ VERIFIED | `git status --porcelain -- src/ data/` empty; no `pyproject.toml`/`uv.lock`/`requirements*.txt` change in the phase; `DEFAULT_MODEL` still resolves to `qwen2.5:1.5b`; 454 tests pass. See WARNING on the behaviour-neutral `src/` rename below. |

**Score:** 13/13 truths verified (0 present-but-behaviour-unverified)

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `docs/REVIEW.md` | Guarded 10-min live-review runbook | ✓ VERIFIED | 147 lines, 8 ordered beats, three blockquote declarations, all `uv run triagedesk …` lines fenced + comment-free; guard drives every invocation. |
| `tests/test_review_runbook.py` | CLI-drift + honesty guard (incl. runnable durable dismissal) | ✓ VERIFIED | Drives shipped `main` with 5 spied seams; `test_documented_durable_dismissal_runs_end_to_end` runs a real pause→resume over `tmp_path`. |
| `tests/test_data_extension.py` | Hermetic data-only-extension proof | ✓ VERIFIED | Writes only under `tmp_path`; clears the loader cache in every `finally`; non-vacuous `src/` guard asserts the `git` returncode. |
| `docs/DEMO.md` | Refreshed honest demo runbook | ✓ VERIFIED | Re-transcribed from the shipped runner; retimed 2:50; per-beat narration cues; measured-eval beat; human flags. |
| `README.md` | v1.1 status + honest clinical-fit re-declaration | ✓ VERIFIED | Badge `status-v1.1--milestone-close`; capability sentence; no `uv sync --locked`; no stale row; keeps `uv run triagedesk demo`/`desk`, `EVALS.md`, `E-09`. |
| `EVALS.md` §7 | Marked, attributed, empty clinician slot | ✓ VERIFIED | Narrative-only edit; projection intact (`--check` exit 0). |
| `ARCHITECTURE.md` | Real-graph node table within budget | ✓ VERIFIED | 694/700 words, 93/110 lines; four real nodes named; model kept. |
| `DESCRIPTION.md` | v1.1 clause within ±10% | ✓ VERIFIED | 326 prose words; durable gate + deferral banner. |
| `STATUS.md` / `docs/REQUIREMENTS.md` / `docs/ROADMAP.md` | v1.1 sweep | ✓ VERIFIED | Resolved marked resolved; open kept open; links not restatements. |
| `docs/DECISIONS.md` | One close-out ADR-lite row | ✓ VERIFIED | D25 (highest D-number) records the four close-out choices, links `REVIEW.md`/`DEMO.md`/`EVALS.md`. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `docs/REVIEW.md` fenced blocks | `triagedesk.cli.main` | `tests/test_review_runbook.py` fence extractor + `shlex.split` + `main(argv)` with spied seams | ✓ WIRED | Every documented invocation returns 0 and reaches exactly one seam; durable dismissal runs end-to-end. |
| `tests/test_data_extension.py` | `rules.DISCRIMINATORS_PATH` → `get_discriminators.cache_clear()` → `match_discriminators` + `score_priority` | `monkeypatch.setattr` + cache clear (fresh-process equivalent) | ✓ WIRED | BEFORE→AFTER re-score demonstrated through the shipped path; ORANGE override fires. |
| `docs/DEMO.md` outcome blocks | `uv run triagedesk demo` shipped output | live run re-transcription | ✓ WIRED | Live run reproduces all five blocks (seven tools, escalation pos 1, refusal string, failure mismatch). |
| `README.md` / `EVALS.md` §7 | single marked clinician-review slot | prose only, no number restated | ✓ WIRED | No invented quote; other docs link `EVALS.md`. |
| `ARCHITECTURE.md` node table | `triagedesk.graph.build.TRACER_NODES` | node names (`ground`/`assess`/terminals) | ✓ WIRED | Table names the real nodes; DESK guard unaffected. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `EVALS.md` | generated cells/blocks | `evals/results/report.json` via `scripts/emit_evals.py` | Yes (`--check` exit 0; digest 12d6d1b909d33872) | ✓ FLOWING |
| `docs/DEMO.md` outcome blocks | beat outcomes | live `uv run triagedesk demo` | Yes (re-run reproduces every line) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Whole suite green | `uv run pytest -q` | 454 passed in 32.13s | ✓ PASS |
| EVALS projection intact | `uv run python scripts/emit_evals.py --check` | exit 0 | ✓ PASS |
| Demo runs end-to-end | `uv run triagedesk demo` | exit 0; five beats; failure mismatch printed | ✓ PASS |
| Demo beat names | `uv run triagedesk demo --list` | 5 beat names = the runbook's | ✓ PASS |
| Data-only extension | `uv run pytest tests/test_data_extension.py -q` | pass (BEFORE→AFTER through shipped path) | ✓ PASS |
| Runbook drift + runnability | `uv run pytest tests/test_review_runbook.py -q` | pass (incl. end-to-end dismissal) | ✓ PASS |
| No src/data change | `git status --porcelain -- src/ data/` | empty | ✓ PASS |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` probes are declared by this phase (docs + guards only).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| REV-01 | 12-01 | Live technical review rehearsed end-to-end incl. a live data-only discriminator edit that passes the safety suite | ✓ SATISFIED | `docs/REVIEW.md` + `tests/test_review_runbook.py` + `tests/test_data_extension.py` all green; extension demonstrated data-only with `src/` unchanged. |
| DEMO-02 | 12-02 | 2–3 min narrated demo showing the measured eval on screen, unedited, still showing a failure | ✓ SATISFIED (script) / human (recording+upload) | `docs/DEMO.md` retimed 2:50 with narration cues + honest measured-eval beat; recording/upload flagged human (see Human Verification). |
| FIT-01 | 12-02 | Clinician review obtained+quoted, or the gap re-declared honestly | ✓ SATISFIED (fallback branch) | README + `EVALS.md` §7 honest re-declaration with empty attributed slot; obtaining a review is human. |
| DOCS-06 | 12-02, 12-03 | Every submission doc refreshed to v1.1 with no stale v1.0 claims | ✓ SATISFIED | Stale-token grep clean; all seven docs refreshed; guards green. |

**Orphaned requirements:** none — REQUIREMENTS.md maps exactly REV-01/DEMO-02/FIT-01/DOCS-06 to Phase 12, and every one is claimed by a plan.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/test_review_runbook.py` | REV-01 | 5 | 0 | No | Behavioral (drives `main`, end-to-end pause→resume) | ✓ strong |
| `tests/test_data_extension.py` | REV-01 | 4 | 0 | No (tmp substrate; shipped matcher/scorer driven) | Value + Behavioral (matched id, ORANGE colour, git status) | ✓ strong |
| `tests/test_docs_final.py` | DOCS-06 | 8 | 0 | No | Value (word/line bounds, projection `--check`) | ✓ strong |
| `tests/test_demo_runbook.py` | DEMO-02 | 4 | 0 | No | Value (beat-set equality, verbatim refusal) | ✓ strong |

**Disabled tests on requirements:** 0 · **Circular patterns detected:** 0 · **Insufficient assertions:** 0

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (11/11; D12-01…D12-11 each referenced in ≥3 phase artifacts).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/triagedesk/llm/client.py` | 33–42 | Phase review-fix commit `5eb12aa` renamed `PRIMARY_MODEL`→`BIG_MODEL` / `FALLBACK_MODEL`→`SMALL_MODEL` + corrected a comment — a literal `src/` edit, though behaviour-neutral | ⚠️ WARNING | No truth fails: `DEFAULT_MODEL` still resolves to `qwen2.5:1.5b`, no value/control-flow/call changed, 454 tests pass, and the convergence review explicitly verified "naming/comment only". The plan prohibition "MUST NOT edit `src/`" is literally touched; its stated intent "(no source-behaviour change)" holds. Flagged for human awareness, not a blocker. |
| `docs/assets/architecture.pdf` | — | Working tree shows the PDF modified (same byte size) | ℹ️ Info | mtime is 2026-10-10 (pre-phase-12); not produced by this phase and not `src/` or `data/`. No impact. |

No `TBD`/`FIXME`/`XXX` debt markers in any phase-modified file.

### Human Verification Required

#### 1. Record and publicly upload the demo video

**Test:** Follow `docs/DEMO.md` to record the retimed 2:50 narrated walkthrough and upload it PUBLICLY (YouTube/Vimeo), then paste the URL into the submission form.
**Expected:** A public, unedited screen recording ≤3 min showing the seven owned tool calls, the committed `EVALS.md` projection, and the live E-09 failure (`DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)`).
**Why human:** Recording/hosting are physical actions outside the repo; the phase prepares the script + narration and flags this as the one submission blocker (STATUS G1 / REQUIREMENTS G-9). The existing local tape is 32.88 s (STATUS G5 flags it as thin) — a re-recording to the retimed script is the honest path.

#### 2. Obtain a triage nurse/clinician review

**Test:** Arrange a single triage nurse/clinician review; if obtained, paste the attributed quote (name/role/date, with consent) into `EVALS.md` §7 and `README.md`.
**Expected:** Either an attributed quote lands in `EVALS.md` §7 / README, or the gap stays honestly declared with the marked, empty slot that already ships.
**Why human:** Clinician access is an external relationship, not a codebase change. The phase delivers the sanctioned alternative (the honest re-declaration), which IS criterion 3's fallback branch.

### Gaps Summary

No actionable gaps. All four ROADMAP success criteria are delivered in the codebase, and all plan must-have truths resolve to VERIFIED (13/13). The two remaining items are the genuinely human steps the brief itself sanctions (record/upload the demo; obtain a clinician review) — the phase delivers the runnable script + narration and the honest, empty, attributed re-declaration respectively, and flags both rather than claiming them. The single deviation — a behaviour-neutral `src/triagedesk/llm/client.py` constant rename from the review-fix loop — is recorded as a WARNING because it literally touches `src/`, but it changes no behaviour and no truth fails.

---

_Verified: 2026-10-13T12:13:23Z_
_Verifier: the agent (gsd-verifier)_
