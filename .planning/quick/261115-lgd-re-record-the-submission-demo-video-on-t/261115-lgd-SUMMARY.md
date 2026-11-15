---
quick_id: 261115-lgd
phase: quick-261115-lgd
plan: 01
subsystem: demo
status: complete
tags: [demo, video, recorder, mcp-elicitation, docs]
requires: [quick-261115-jlr live MCP elicitation seam]
provides:
  - scripts/record_demo.py (online beats, scripted answer at the real nurse prompt, honesty guards)
  - docs/assets/triagedesk-demo.mp4 (2:29 re-recording on qwen2.5:1.5b)
  - docs/assets/demo-captions.ass
affects: [docs/DEMO.md, README.md, STATUS.md, docs/REQUIREMENTS.md]
tech-stack:
  added: []
  patterns:
    - "Captions are timed from, and guarded by, the output they narrate (SystemExit before rendering)"
    - "Screen literals (mode_line, TOOL/ELICIT/NURSE prefixes) imported from triagedesk.demo.run"
key-files:
  created:
    - tests/test_record_demo.py
  modified:
    - scripts/record_demo.py
    - docs/render-demo.sh
    - src/triagedesk/demo/run.py
    - pyproject.toml
    - docs/assets/triagedesk-demo.mp4
    - docs/assets/demo-captions.ass
    - docs/DEMO.md
    - README.md
    - STATUS.md
    - docs/REQUIREMENTS.md
decisions:
  - "Offline beats print their whole outcome in one burst, so cues in a segment are staggered (MIN_DWELL 4.5 s); a cue may start after its output but never before it"
  - "mypy_path = src in [tool.mypy] so scripts/ type-check against the source package (it ships no py.typed)"
  - "Committed the attempt-2 render (149.1 s) with the exact recorder settings that produced it; attempt 3 (longer dwell) went over the limit under host load and was discarded"
requirements: [SB-4, SB-5, JC-6]
metrics:
  duration: ~45 min
  completed: 2026-11-15
actuals:
  tokens: 17800
  tasks: 3
  commits: 3
plan_head_before: 413b2f41ff66a65371f8d93743d315a2131a8836
plan_head_after: 6949b6ec5cf1e6d76925525a4509a5b579141403
---

# Quick 261115-lgd Plan 01: Re-record the submission demo video Summary

The repository's demo video is now a 2:29 (149.1 s) unedited real-pty recording on `qwen2.5:1.5b`. It shows online escalation (ORANGE, committed), an online clarify beat where the model really asked through `request_clarification` and the answer was typed at the real `[nurse] q1>` prompt (RED, committed), offline refusal, a report-derived EVALS §3 projection, and the declared E-09 failure. Every caption is timed from, and checked against, the output it narrates.

## What was built

- **Task 1 (f105ce6)**: reworked the recorder in `scripts/record_demo.py`:
  - `Cue`/`Segment` data and one `command_for(segment)`, which adds `--online` from the flag and never adds `--answer`.
  - A `Terminal` pty class with `VIRTUAL_ENV` removed from the child's environment.
  - `run_segment` waits for the shell prompt and types the scripted answer only after a real nurse prompt appears.
  - `check_segment` refuses a missing mode line, cue marker or expected outcome, zero prompts in clarify, a traceback, or a `warning:`.
  - `projection_caption` gets its figures from `Report` + `analyse` + `INVARIANT_IDS`.
  - `tools_on_screen` produces the end-of-run summary.
  - `TOOL_PREFIX` is now named once in `triagedesk.demo.run`.
  - In `render-demo.sh`, one `LIMIT_S=180` sets both agg's idle limit and the duration guard, and the recorder runs under `uv run`.
  - `tests/test_record_demo.py` has 27 Ollama-free tests, including a real-pty answer round-trip.
- **Task 2 (71b209c)**: rendered the video and caption track. The recorder summary was `cast … (337 events, 148.6s)`, `captions … (12 cues)` and `tools on screen: 8 (assess_confidence, commit_priority, match_discriminators, normalize_case, plan_next_step, request_clarification, retrieve_evidence, score_priority)`. ffprobe measured 149.12 s.
- **Task 3 (6949b6e)**: DEMO.md, README.md, STATUS.md and REQUIREMENTS.md (SB-4/SB-5/JC-6) now cite the measured 2:29 and the 8 tools. Every 2:28 mention is explicitly the Google-Drive-uploaded v1.0 recording, and the re-recording is described as not yet uploaded.

## Render attempts (honest log)

| # | Outcome | Recording | Note |
|---|---------|-----------|------|
| 1 | Guards all passed, duration guard FAILED | 206.1 s cast / 206.6 s mp4 | Host under load (load avg ~9.5, the user's flutter tests, 9 GB swap). Escalation took ~63 s and clarify ~58 s to the question. Exposed the offline-cue flash (see deviation 2). |
| 2 | **exit 0, committed** | 148.6 s cast / 149.1 s mp4 | Load ~2–4. The model asked q1–q3, the answer was typed at the real `[nurse] q1>` prompt, Enter at q2/q3, RED committed. |
| 3 | Guards passed, duration guard FAILED | 218.3 s cast / 218.8 s mp4 | Tried MIN_DWELL 6.0 and longer offline holds (11/12 s) for easier reading. Load rose to ~8 again. Discarded: the attempt-2 mp4 + .ass were restored together and the recorder reverted to the attempt-2 settings, so the committed script reproduces the committed video. |

The model asked in all three attempts, so `--answer` was never needed. No cast or caption was edited by hand.

## Visual QA (attempt 2, frames 1.5 s after each cue)

I checked these frames:
- Escalation start: the online mode line is visible.
- Escalation commit: `committed … queue position 1 (ORANGE)`.
- The clarify `[elicit]` q1–q3 questions with `[nurse] q1> ` waiting.
- The typed answer (`[nurse] q1> low glucose, 2.1 mmol/L`, then `q2>`, `q3>`).
- Clarify `elicitation : accepted` with `colour : RED` and the RED commit.
- Refusal: the offline mode line and `GATE REFUSED`.
- The projection table through the `Measured source` line.
- The failure, `MEASURED : GREEN (SHOWN MISMATCH)`, and the close.

In every frame the caption matches the screen, sits inside the bottom band, and takes at most two lines.

## Deviations from Plan

**1. [Rule 3 - Blocking] `mypy_path = "src"` added to `[tool.mypy]` in pyproject.toml**
- Found during: Task 1. `uv run mypy scripts/record_demo.py` reported `import-untyped` for every `triagedesk` import, because the installed package has no `py.typed`. `scripts/emit_evals.py` has the same problem at HEAD.
- Fix: one mypy config line. `uv run mypy src` is unchanged (29 pre-existing errors), and mypy is now clean on `scripts/record_demo.py`, `emit_evals.py` and `install_mcp.py`. Commit f105ce6.

**2. [Rule 1 - Bug] Offline-beat cues are staggered (`stagger`, `MIN_DWELL = 4.5`, `LAST_CUE_MARGIN = 1.0`)**
- Found during: Task 2, attempt 1. An offline beat prints its mode line and outcome in one ~0.1 s burst, so the first caption of refusal and failure was on screen for 0.1 s.
- Fix: each cue now starts at the later of its marker time and the previous cue's start plus MIN_DWELL. It can start after its output appears, but never before. If the hold cannot fit the last cue, the recording aborts. Two tests were added. Commit 71b209c.

## Known limitations

- Reading time for the offline-beat captions is short: about 4.5 s for the first cue and 4–5.6 s for the second, at roughly 110–120 characters each. A re-render with `MIN_DWELL = 6.0` and refusal/failure holds of 11/12 s (about +8 s, still about 157 s on a quiet host) would read more comfortably. That is what attempt 3 tried before host load pushed it over the limit.
- Online timings depend on host load. Render on a quiet machine (no concurrent heavy jobs).
- Uploading the 2:29 re-recording to YouTube/Vimeo is a user action (G1 / G-9).

## Threat surface

There is no new network or auth surface. The T-lgd-01/02/04/05 mitigations are implemented and tested. Staging used explicit paths only, the user's untracked `docs/assets/*` files stayed unstaged, and the stray `spans.jsonl` was removed.

## Self-Check: PASSED

- FOUND: scripts/record_demo.py, tests/test_record_demo.py, docs/render-demo.sh, docs/assets/triagedesk-demo.mp4 (149.1 s), docs/assets/demo-captions.ass (12 Dialogue lines)
- FOUND commits: f105ce6, 71b209c, 6949b6e (3 commits since 413b2f4)
- Verify commands for Tasks 1–3 all passed. Last run: 46 tests passed across the demo, runbook, docs and record_demo suites; ruff and mypy are clean on the recorder.
