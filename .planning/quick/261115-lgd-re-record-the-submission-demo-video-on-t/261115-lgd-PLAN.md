---
quick_id: 261115-lgd
slug: re-record-the-submission-demo-video-on-t
phase: quick-261115-lgd
plan: 01
type: execute
wave: 1
depends_on: []
branch: feat/v1.3-adaptive-triage
files_modified:
  - scripts/record_demo.py
  - tests/test_record_demo.py
  - docs/render-demo.sh
  - src/triagedesk/demo/run.py
  - docs/assets/triagedesk-demo.mp4
  - docs/assets/demo-captions.ass
  - docs/DEMO.md
  - README.md
  - STATUS.md
  - docs/REQUIREMENTS.md
autonomous: true
requirements: [SB-4, SB-5, JC-6]

estimate:
  tokens: 95000
  raw_tokens: 95000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`bash docs/render-demo.sh` writes `docs/assets/triagedesk-demo.mp4` from ONE unedited real-pty recording, under 180 s, with no idle-time compression (agg's idle limit equals the duration limit, both read from one shell variable), and the render exits 0"
    - "The escalation and clarify beats run ONLINE on the real local model: each segment's command is built by the one `command_for(segment)` and includes `--online`; the recording fails unless the segment's output shows the online mode line from `triagedesk.demo.run.mode_line(offline=False)`"
    - "In the clarify beat the recorder types the scripted nurse answer only AFTER a real `[nurse] <field>> ` prompt appears on screen, presses Enter for each further prompt it sees (count read from the output, not hard-coded), and never passes `--answer`; a clarify run in which the model asks nothing ABORTS the recording instead of producing a video"
    - "Every caption cue appears only when the output it narrates appears; a cue marker that never shows, a missing `expect` pattern, a traceback or a warning on screen, or a segment that does not return to the shell prompt within its timeout aborts the recording (no video is rendered over a screen that contradicts its captions)"
    - "The projection caption's figures (cases, runs per case, colour-expected runs correct, under-triage count, invariants held) are computed from `evals/results/report.json` via the same `Report` + `analyse` the EVALS generator uses — none is hand-typed; the projection command shows EVALS.md §3 from its heading through the measured-source line"
    - "docs/DEMO.md, README.md, STATUS.md and docs/REQUIREMENTS.md (SB-4, SB-5, JC-6) cite the MEASURED new duration and the measured count of distinct owned tools shown; every remaining 2:28 mention is explicitly the Google-Drive-uploaded v1.0 submission recording, and the new file is described as a re-recording not yet uploaded to YouTube"
    - "The recorder's pure helpers and its pty answer loop are covered by tests that need no Ollama; ruff and mypy are clean on scripts/record_demo.py"
  artifacts:
    - path: scripts/record_demo.py
      provides: "Segment/Cue script, one command builder with the online flag, completion-wait + scripted-answer pty session, honesty guards, report-derived projection caption, tools-on-screen summary"
    - path: tests/test_record_demo.py
      provides: "Ollama-free tests for command building, caption consistency, report-derived figures, prompt detection, guards, and a real-pty answer round-trip"
    - path: docs/render-demo.sh
      provides: "runs the recorder under the project env; one LIMIT variable feeds agg's idle limit and the duration guard"
    - path: docs/assets/triagedesk-demo.mp4
      provides: "the re-recorded submission video (< 3:00) with online escalation + live MCP elicitation"
    - path: docs/assets/demo-captions.ass
      provides: "the burned caption track, timed from the recording it narrates"
  key_links:
    - from: scripts/record_demo.py
      to: src/triagedesk/demo/run.py
      via: "imports mode_line, NURSE_PREFIX, ELICIT_PREFIX, TOOL_PREFIX, load_storyboard (one source for every on-screen literal the recorder matches)"
    - from: scripts/record_demo.py
      to: evals/results/report.json
      via: "Report.model_validate_json + triagedesk.evals.analysis.analyse + INVARIANT_IDS build the projection caption"
    - from: docs/render-demo.sh
      to: scripts/record_demo.py
      via: "uv run python scripts/record_demo.py --cast … --captions docs/assets/demo-captions.ass"
    - from: tests/test_record_demo.py
      to: scripts/record_demo.py
      via: "importlib spec_from_file_location (the tests/test_install_mcp.py pattern; module registered in sys.modules before exec)"
---

<objective>
Re-record the submission demo video (`docs/assets/triagedesk-demo.mp4`) so the repository shows the
CURRENT system on the REAL local model (`qwen2.5:1.5b` via Ollama), including the live MCP elicitation
`clarify` beat — still one unedited real-pty recording, tool calls on screen, no slides, under 3:00.

Purpose: TriageDesk is in the top 100; the video is what judges and the community see in the repo. The
current file (148.2 s, recorded before v1.3) plays offline beats only and its captions narrate stale
facts (old case count, old deferral behaviour). The new recording must prove the agentic claim on
screen — the agent stops inside an MCP tool call, the nurse answers, a cited SATS rule decides the
colour, and nothing commits without a named approval — without faking any of it.

Output: a reworked `scripts/record_demo.py` (+ tests), a one-line-variable render-script fix, the
re-rendered mp4 + caption track, and docs citing the measured duration.

Segment list (≈2:30 measured budget; the two ONLINE beats are the must-haves):
intro → `--online --beat escalation` (ORANGE, commit under the named nurse) → `--online --beat clarify`
(the recorder types the answer at the real `[nurse] q1>` prompt; RED, committed) → `--beat refusal`
offline (same E-02, gate refuses; its mode line says offline) → EVALS §3 projection (report-derived
caption) → `--beat failure` offline (E-09 unanswered: declared ORANGE, measured GREEN, shown mismatch)
→ close. Order keeps the declared failure as the honest final beat (orchestrator's proposal, kept).

DRY/SOLID (docs/CONVENTIONS.md, iron-clad): every on-screen literal the recorder matches (mode line,
`[nurse]`, `[elicit]`, `[tool]`) is imported from `triagedesk.demo.run` — the recorder re-types none;
beat names come from `load_storyboard`; the projection figures come from the report via the same
`Report` + `analyse` that `scripts/emit_evals.py` uses; the beat command is built once by
`command_for(segment)`; the duration limit lives in one shell variable. SRP: the pty session (I/O),
the segment script (data), the pure guard/format helpers, and `record()` (orchestration) are separate
units. No SATS threshold, band or discriminator id is written into the recorder; the nurse's typed
answer is presenter input (the same words the runbook's documented live run uses), not a rule.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md
@docs/CONVENTIONS.md
@scripts/record_demo.py
@docs/render-demo.sh
@demo/storyboard.yaml

# On-screen literals and the mode line (import, never re-type): lines ~55-102 and ~140-220, ~295-330
@src/triagedesk/demo/run.py
# Report loading + analysis exactly as the EVALS generator does it: lines ~34-36, ~112-156, ~539
@scripts/emit_evals.py
# Path-loading a script module in a test (sys.modules registration before exec): lines ~40-60
@tests/test_install_mcp.py
# The documented live clarify run and its answer wording: lines ~280-345; video citations at ~5, ~10-24, ~85-100, ~196, ~418
@docs/DEMO.md

<interfaces>
From src/triagedesk/demo/run.py (verified at HEAD 413b2f4):
- `mode_line(*, offline: bool) -> str` — online text is "mode: online — local model qwen2.5:1.5b via Ollama"; offline is "mode: offline — golden fixture (no model)". It is the FIRST line every demo run prints.
- `ELICIT_PREFIX = "[elicit]"`, `NURSE_PREFIX = "[nurse]"` (module constants).
- `load_storyboard(path) -> list[Beat]` with `Beat.name`, `Beat.case`, `Beat.label`.
- Interactive prompt (online, TTY, no `--answer`): `input(f"{NURSE_PREFIX} {field}> ")` once per field (q1, q2, q3 observed); Enter = blank; typed answers are NOT re-printed as `[nurse] q1: …` lines.
- `_print_tool_call` prints `f"[tool] {name} {inputs} -> {outputs}"` — the `[tool]` literal is inline today (no constant).
- Outcome block lines (observed offline at HEAD): `  colour       : ORANGE`, `  commit       : committed case 9300336d37c3651c at queue position 1 (ORANGE)`, `  GATE REFUSED : no queue row written (rows added this beat: 0)`, `  MEASURED     : GREEN (SHOWN MISMATCH)`, `  elicitation  : accepted` (online clarify, per DEMO.md's real-run excerpt).

From scripts/emit_evals.py: `Report.model_validate_json(path.read_text(encoding="utf-8"))`, `analyse(report)` → `Analysis` with `colour_correct`, `colour_runs`, `under_triage_count`; invariants held = `sum(1 for held in report.invariants.values() if held)` over `len(INVARIANT_IDS)` (`from triagedesk.evals.invariants import INVARIANT_IDS`). Current values: 24 cases, 3 runs, 48/48, under-triage 0, invariants 4/4.

Measured online timings (warm model): escalation ~23 s, clarify ~56 s incl. elicitation; offline refusal ~3.4 s, failure ~2.8 s. Variation run-to-run is real.
</interfaces>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Recorder drives one scripted-answer segment end-to-end through a real pty (online flag, completion wait, honesty guards, report-derived captions)</name>
  <files>scripts/record_demo.py, tests/test_record_demo.py, docs/render-demo.sh, src/triagedesk/demo/run.py</files>
  <behavior>
    - Segment script: every "beat" segment names a beat in `load_storyboard(demo/storyboard.yaml)`; the escalation and clarify segments are `online=True`; refusal and failure are offline; the clarify segment carries exactly one scripted answer.
    - `command_for(segment)`: online beat → "uv run triagedesk demo --online --beat clarify"; offline beat → "uv run triagedesk demo --beat refusal" (no `--online`); "cmd" → its target verbatim; "hold" → None; no segment's command contains "--answer".
    - Captions: intro + every cue across all segments, in order; each caption ≤ MAX_CAPTION_CHARS (170), has no "{", "}" or newline (ASS override/line-break safety); `write_captions` over synthetic increasing cue times writes exactly that many `Dialogue:` lines, each with start < end, the last ending at `total`.
    - `projection_caption(report_path)` contains the case count, runs/case, colour_correct/colour_runs, under-triage count and invariants-held/len(INVARIANT_IDS), each equal to what the test computes from `evals/results/report.json` with `Report` + `analyse`.
    - `PROJECTION_CMD` run with `bash -c` at the repo root prints `PROJECTION_MARKER` and "Measured source" in fewer than 30 lines (it is a heading-to-source-line range, not a line-number range).
    - `nurse_prompts(text)` returns ["q1", "q2"] for sample output holding `[elicit] … asks q1: …` lines, `[nurse] q1> low glucose, 2.1 mmol/L` and a trailing `[nurse] q2> `; it ignores `[nurse] q1: …` echo lines; `answer_for(0, (A,)) == A`, `answer_for(1, (A,)) == ""`.
    - `check_segment(segment, output, answered)` raises SystemExit when: a beat's output lacks its `mode_line(offline=not online)`; a cue marker or an `expect` pattern is absent; the segment has answers but `answered == 0`; the output contains "Traceback (most recent call last)" or any case-insensitive "warning:" (e.g. "LangChainBetaWarning:"); it passes on a well-formed synthetic output. A JSON `"warning": null` field does NOT trip it.
    - `tools_on_screen(text)` returns the sorted distinct tool names from `[tool] <name> …` lines.
    - Real-pty round-trip (no Ollama; skip if not POSIX): a `Terminal` session runs a tmp_path script that calls `input()` twice with `NURSE_PREFIX`-built prompts and prints `got <repr a> <repr b>`; running it as a "cmd" segment with `answers=(CLARIFY_ANSWER,)` types the answer at the first prompt, Enter at the second, returns when the shell prompt comes back, and the output contains `got 'low glucose, 2.1 mmol/L' ''`. The session is closed in a `finally`.
  </behavior>
  <action>
RED first: write tests/test_record_demo.py covering every behavior above, loading scripts/record_demo.py by path exactly as tests/test_install_mcp.py `_installer()` does (spec_from_file_location, register in sys.modules before exec_module, module-scoped fixture). Run it and confirm it fails, then implement.

In src/triagedesk/demo/run.py add `TOOL_PREFIX = "[tool]"` beside ELICIT_PREFIX/NURSE_PREFIX (extend that comment: the three screen prefixes, named once) and use it in `_print_tool_call`'s f-string. Output is byte-identical, so tests/test_demo.py stays green.

Rework scripts/record_demo.py (keep the module docstring accurate: online beats now run the real local model; captions are timed from, and guarded by, the output they narrate):
- Import from `triagedesk.demo.run`: `mode_line`, `NURSE_PREFIX`, `ELICIT_PREFIX`, `TOOL_PREFIX`, `load_storyboard`; from `triagedesk.evals.report`: `Report`; from `triagedesk.evals.analysis`: `analyse`; from `triagedesk.evals.invariants`: `INVARIANT_IDS`. Drop the direct `yaml` import (the `beat_names()` helper becomes a set over `load_storyboard(STORYBOARD)`), which also removes mypy's missing-stubs error.
- Constants: `PROMPT = "desk $ "` used for BOTH the child's PS1 and completion detection; COLS/ROWS/TYPE_DELAY/INTRO_HOLD unchanged; `ANSWER_PAUSE` (~1.8 s, so viewers read the question before the answer is typed); `SEGMENT_TIMEOUT` (150 s); `MAX_CAPTION_CHARS = 170` (two lines in the 142 px band); `CLARIFY_ANSWER = "low glucose, 2.1 mmol/L"` (the presenter's typed words — chosen to match the live run documented in docs/DEMO.md "Live final"; comment that it is the nurse's free-text observation, not a rule); `REPORT = REPO / "evals" / "results" / "report.json"`; `PROJECTION_CMD = "sed -n '/^## 3. Reliability metrics/,/Measured source/p' EVALS.md"` (heading-to-measured-source range, so line drift in EVALS.md cannot cut the table); `PROJECTION_MARKER = "Reliability metrics"`; a compiled `FORBIDDEN_OUTPUT` regex for a traceback or case-insensitive "warning:".
- Frozen dataclasses: `Cue(marker: str | None, text: str)` (marker is a regex; None = the segment's own start, for the silent tail) and `Segment(kind, target, cues, hold, online=False, answers=(), expect=())` — `hold` is the reading pause AFTER the run returns to the prompt (for "hold" kind, the whole tail).
- `segments() -> list[Segment]` builds the script at call time (import stays side-effect free) — cues per segment, using `re.escape(mode_line(offline=...))` as each beat's first marker (replacing the hard-coded single-beat header marker):
  escalation (online; hold ~5 s): mode line → "Online: the local open-weights model reads the nurse's note on CPU. Each [tool] line is a real MCP tool call; the colour comes from SATS rules, never the model."; marker `commit\s*:\s*committed case \S+ at queue position \d+ \(ORANGE\)` → "ORANGE, cited to the SATS TEWS bands - committed at queue position 1 only after a named nurse approves."
  clarify (online; answers=(CLARIFY_ANSWER,); hold ~6 s; expect the RED commit line `commit\s*:\s*committed case \S+ at queue position \d+ \(RED\)`): mode line → "Live MCP elicitation on the same local model. A vague note: 'feeling unwell', known diabetic, normal vitals. The planner picks its next step."; marker `re.escape(ELICIT_PREFIX)` → "The agent stops INSIDE the request_clarification MCP call and asks the nurse. She types what she measured."; marker `elicitation\s*:\s*accepted` → "Her answer is re-matched by the deterministic matcher: a cited SATS discriminator makes it RED, committed under her named approval."
  refusal (offline; hold ~8 s): mode line → "Same E-02 case, replayed offline from the golden fixture (the mode line says so) - this time no named nurse approves."; marker `GATE REFUSED` → "The approval gate REFUSES: no queue row is written. Nothing reaches the queue without her."
  projection ("cmd"; hold ~10 s): marker `re.escape(PROJECTION_MARKER)` → `projection_caption(REPORT)`.
  failure (offline; hold ~8 s): mode line → "And the failure we did NOT hide: the same vague E-09 note, with no nurse answer (offline fixture)."; marker `MEASURED\s*:\s*GREEN \(SHOWN MISMATCH\)` → "Declared ORANGE, the rules alone measure GREEN - shown, not hidden. The agent can ask; it never guesses a colour."
  close ("hold"; ~6 s; marker None) → "Open source, local, synthetic data. Every priority cited; every commit gated by a named nurse. TriageDesk."
  Keep the existing INTRO text but end it with "a named nurse". Caption wording may be tightened to fit MAX_CAPTION_CHARS, but every factual claim must stay one the screen shows; the stale case-count and deferral wording from the old SEGMENTS list must be gone.
- `projection_caption(report_path)`: load as emit_evals does, call `analyse`, and format e.g. "The committed, measured evaluation: {cases} cases x {runs} runs on the local model - {correct}/{runs_expected} colour-expected runs correct, under-triage {n}, safety invariants {held}/{total}." — every number from the report.
- Pure helpers: `command_for(segment)` (the ONE builder; inserts `--online` from the flag), `nurse_prompts(text)` (regex built from `re.escape(NURSE_PREFIX)` + `(\S+)> `), `answer_for(index, answers)`, `tools_on_screen(text)` (regex from `re.escape(TOOL_PREFIX)`), `check_segment(segment, output, answered)` (all guards in the behavior list; message names the segment and the missing marker), and `write_captions(path, timed, total)` taking the ordered `(start, text)` list (intro at 0.3 s) with each end = next start, last end = total.
- `Terminal` class (single responsibility: the pty child + timestamped event log): start bash `--norc --noprofile -i` in a given cwd with PS1=PROMPT, TERM, the window size, and `VIRTUAL_ENV` REMOVED from the child env (the recorder itself now runs under `uv run`; the typed `uv run` must behave like a stranger's shell and print no venv-mismatch warning); `pump(seconds)`, `type(text)` at TYPE_DELAY, `enter()`, `output_since(t)`, `first_match_after(t, pattern)` returning the timestamp of the event whose arrival first makes the cumulative output match, `wait_for(pattern, timeout)`, and `close()` (exit the shell, reap the child).
- `run_segment(term, segment) -> list[float]` (cue start times): hold kind → pump(hold), return [start]. Otherwise type `command_for(segment)`, Enter, then loop in short pump slices until PROMPT appears in the output since Enter — on each new `nurse_prompts` entry beyond those answered: pump(ANSWER_PAUSE), type `answer_for(i, segment.answers)`, Enter; on SEGMENT_TIMEOUT raise SystemExit naming the segment. Then pump(segment.hold), run `check_segment`, compute each cue's start via `first_match_after(enter_time, marker)`, and raise SystemExit if cue starts are not non-decreasing.
- `record(cast, captions)`: validate beat names against the storyboard, start the Terminal, wait for the first PROMPT, pump(INTRO_HOLD), run every segment, final Enter + short pump (keeps the closing caption to the last frame, as today), close, write the cast (asciicast v2, same header) and captions, and print a summary: total seconds, cue count, and `tools on screen: N (names…)` from `tools_on_screen` over the whole session output — Task 3 reads N from here instead of guessing.

In docs/render-demo.sh: run the recorder as `uv run python scripts/record_demo.py` (it now imports the project); introduce one `LIMIT_S=180` variable used both as agg's `--idle-time-limit` (so agg never compresses an idle gap — the video is the real timeline the captions were timed against) and passed to the Python duration guard via argv (replacing its literal); update the header comment (online beats use the real model, so timings vary; the recorder waits for each run and refuses to caption output that did not appear). Keep the spans.jsonl snapshot logic unchanged.

Do not change any SATS data, the storyboard, the graph, or eval reports.
  </action>
  <verify>
    <automated>uv run pytest tests/test_record_demo.py tests/test_demo.py tests/test_demo_runbook.py -q && uv run ruff check scripts/record_demo.py tests/test_record_demo.py src/triagedesk/demo/run.py && uv run mypy scripts/record_demo.py && test "$(grep -v '^\s*#' scripts/record_demo.py | grep -c '16 cases\|DEFERS')" -eq 0 && test "$(grep -c 'idle-time-limit 60' docs/render-demo.sh)" -eq 0 && test "$(grep -c 'TOOL_PREFIX' src/triagedesk/demo/run.py)" -ge 2</automated>
  </verify>
  <acceptance_criteria>
    - `uv run mypy scripts/record_demo.py` error count [HEAD=3 EXPECT==0]
    - `grep -v '^\s*#' scripts/record_demo.py | grep -c '16 cases\|DEFERS'` [HEAD=2 EXPECT==0]
    - `grep -c 'idle-time-limit 60' docs/render-demo.sh` [HEAD=1 EXPECT==0]
    - `grep -c 'TOOL_PREFIX' src/triagedesk/demo/run.py` [HEAD=0 EXPECT>=2]
  </acceptance_criteria>
  <done>
    tests/test_record_demo.py passes (including the real-pty answer round-trip) with no Ollama; tests/test_demo.py and tests/test_demo_runbook.py stay green; ruff and mypy clean. Committed as one commit staging exactly the four files listed (never `git add -A`).
  </done>
</task>

<task type="auto">
  <name>Task 2: Render the video on the warm local model and visually QA every cue</name>
  <files>docs/assets/triagedesk-demo.mp4, docs/assets/demo-captions.ass</files>
  <precondition>`ollama list` shows qwen2.5:1.5b and `agg` (~/.cargo/bin), `ffmpeg`, `ffprobe` are on PATH.</precondition>
  <action>
Prepare: `uv sync --frozen` (so no resolve/install lines can appear inside the recording), then warm the model with `ollama run qwen2.5:1.5b "ok"` immediately before rendering (default keep-alive outlasts the ~3-minute render).

Render: `bash docs/render-demo.sh`. Capture its stdout — keep the recorder's summary (total seconds, cue count, `tools on screen: N (names)`) and the final duration line for Task 3 and the SUMMARY.

If the render aborts (a recorder guard: the model did not ask in the clarify beat, a cue marker or the online mode line did not appear, a warning/traceback on screen, a segment timeout) or the duration guard fails (≥ 180 s from model latency): re-warm and re-render, up to 3 attempts total. If still over 180 s after 3 attempts, shorten only the reading holds of the OFFLINE segments (refusal, projection, failure) in `segments()` — never the online beats, never a caption's truth — re-run Task 1's test command, and render again. NEVER pass `--answer`, never edit a cast or a caption by hand, never fake a question the model did not ask: if the model will not ask in 3 attempts, stop and report it in the SUMMARY as a blocker. Record every attempt and its outcome honestly in the SUMMARY.

Visual QA (frames go to a scratch directory outside the repo, e.g. from `mktemp -d`): for every `Dialogue:` line in docs/assets/demo-captions.ass, extract one frame ~1.5 s after its start with `ffmpeg -ss <t> -i docs/assets/triagedesk-demo.mp4 -frames:v 1`, then view at least these frames with the Read tool: the escalation commit cue, the clarify `[elicit]` cue (question visible), a frame just after the answer is typed (`[nurse] q1> low glucose, 2.1 mmol/L` visible), the clarify `accepted` cue (RED visible), the refusal, the projection (table + measured-source line readable), the failure, and the close. Confirm in each: the caption matches what the terminal shows, it sits inside the bottom band in at most two lines (not over the terminal), and the online beats show the online mode line. If a caption overflows the band, shorten that caption text, re-run Task 1's tests, and re-render.

Cleanup: render-demo.sh removes a spans.jsonl it created; a pre-existing gitignored spans.jsonl at the repo root is left alone and never staged. Commit ONLY docs/assets/triagedesk-demo.mp4 and docs/assets/demo-captions.ass (plus scripts/record_demo.py if a hold/caption had to change, with its test re-run). Never stage the user's untracked docs/assets/*.png, *.svg, or architecture-technical* files, and never `git add -A` / `git add docs/assets`.
  </action>
  <verify>
    <automated>ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 docs/assets/triagedesk-demo.mp4 | python3 -c "import sys; d=float(sys.stdin.read()); assert d < 180, d; print(f'{d:.1f}s')" && test "$(grep -c '^Dialogue:' docs/assets/demo-captions.ass)" -ge 10 && test "$(grep -c 'request_clarification' docs/assets/demo-captions.ass)" -ge 1 && test "$(grep -c '24 cases x 3 runs' docs/assets/demo-captions.ass)" -eq 1 && test "$(grep -c '16 cases' docs/assets/demo-captions.ass)" -eq 0 && test -z "$(git status --porcelain docs/assets/triagedesk-demo.mp4 docs/assets/demo-captions.ass)"</automated>
  </verify>
  <acceptance_criteria>
    - video duration from ffprobe: HEAD is the 148.2 s offline-only render; the new render must be < 180 s
    - `grep -c '^Dialogue:' docs/assets/demo-captions.ass` [HEAD=8 EXPECT>=10]
    - `grep -c 'request_clarification' docs/assets/demo-captions.ass` [HEAD=0 EXPECT>=1]
    - `grep -c '24 cases x 3 runs' docs/assets/demo-captions.ass` [HEAD=0 EXPECT==1] (24 and 3 are what `evals/results/report.json` holds at HEAD; this plan does not touch the report)
    - `grep -c '16 cases' docs/assets/demo-captions.ass` [HEAD=1 EXPECT==0]
  </acceptance_criteria>
  <done>
    `bash docs/render-demo.sh` exited 0 (all recorder guards passed, under the 3-minute limit). Frames confirm caption/screen agreement and band fit; the mp4 and .ass are committed; no untracked user asset was staged. The SUMMARY records the attempts, the measured duration, and the recorder's `tools on screen` line.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update the docs to the measured re-recording, keeping the upload history honest</name>
  <files>docs/DEMO.md, README.md, STATUS.md, docs/REQUIREMENTS.md</files>
  <action>
Compute the measured duration as M:SS (floor to whole seconds) from `ffprobe` on docs/assets/triagedesk-demo.mp4, and take N + names from the recorder's `tools on screen` summary captured in Task 2. Never guess either.

Edit only the lines that cite the video (Read each region first):
- docs/DEMO.md ~5 (opening blockquote: the file is now an M:SS re-recording, 2026-11-15, on `qwen2.5:1.5b`; online escalation + live MCP elicitation `clarify`, then refusal and the declared E-09 failure on the offline fixture — each run's mode line says which — and the measured evaluation; N distinct owned tools' calls on screen); ~10-14 *Upload status* (the Google Drive submission upload was the earlier 2:28 v1.0 recording; this re-recording is not yet uploaded — re-hosting on YouTube/Vimeo remains the G1/G-9 step); ~19 (the 2:28 sentence becomes explicitly about the Drive-uploaded v1.0 recording); ~92-98 *Rendering the video* bullets (online beats on the real model, the recorder waits for each run to finish, types the nurse's answer at the real `[nurse] q1>` prompt, times each caption from — and refuses to burn one without — the output it narrates; agg never compresses idle time); ~196 (the Drive-uploaded 2:28 v1.0 video shows the earlier deferral; the re-recording does not play the routine beat); ~418.
- README.md ~91 (demo-video row) and ~104-106 (paragraph): the repo file is the M:SS re-recording on the local model with live elicitation; the 2:28 v1.0 recording is what was uploaded to Google Drive during submission (keep the folder link).
- STATUS.md ~71 (row: M:SS measured, real unedited recording, N owned tools on screen, online beats + live elicitation; Drive upload = 2:28 v1.0; replace the "seven … recorded before v1.3" caveat with the measured N), ~88 (Demo score row), ~110 (G1: re-hosting the NEW re-recording on YouTube/Vimeo closes it), ~238 (action list). Leave lines ~28/~40 unless they become false.
- docs/REQUIREMENTS.md SB-4 (M:SS re-recording; the Drive upload was the 2:28 v1.0 recording; YouTube upload pending, user action), SB-5 (online + offline beats, N owned tool calls on screen, live MCP elicitation, the declared E-09 failure), JC-6 (one M:SS recording: tool calls, live elicitation, the measured eval, the declared failure).

Rules: link rather than restate (DRY) — figures stay in EVALS.md; do not invent an upload; keep docs/DEMO.md's honesty clauses (HUMAN action, unedited, screen recording, E-09) that tests/test_demo_runbook.py asserts. Commit the four doc files only.
  </action>
  <verify>
    <automated>DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 docs/assets/triagedesk-demo.mp4 | python3 -c "import sys; d=int(float(sys.stdin.read())); print(f'{d//60}:{d%60:02d}')"); for f in docs/DEMO.md README.md STATUS.md docs/REQUIREMENTS.md; do grep -q "$DUR" "$f" || { echo "MISSING $DUR in $f"; exit 1; }; done; test "$(grep -h '2:28' docs/DEMO.md README.md STATUS.md docs/REQUIREMENTS.md | grep -vc 'Drive\|v1\.0')" -eq 0 && uv run pytest tests/test_demo_runbook.py tests/test_docs_final.py tests/test_readme_runbook.py tests/test_record_demo.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -h '2:28' docs/DEMO.md README.md STATUS.md docs/REQUIREMENTS.md | grep -vc 'Drive\|v1\.0'` [HEAD=6 EXPECT==0]
    - the measured M:SS string appears in each of docs/DEMO.md, README.md, STATUS.md, docs/REQUIREMENTS.md (HEAD: the new duration does not exist yet; EXPECT: present in all four)
  </acceptance_criteria>
  <done>
    Every file cites the measured M:SS; the tool count in STATUS/REQUIREMENTS equals the recorder's measured N; doc tests pass; the four doc files are committed (nothing else staged).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local model → screen/captions | non-deterministic model output is what the video shows; captions make claims about it |
| recorder → pty shell | the recorder types commands and the nurse answer into a real shell |
| working tree → git | untracked user assets sit beside the tracked render outputs |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-lgd-01 | Repudiation | caption track vs screen | high | mitigate | Every cue is timed by, and requires, a regex match in the segment's own output; `expect` patterns guard non-captioned claims (the RED commit); a beat must show its `mode_line(...)`; any miss raises SystemExit before agg/ffmpeg run. Tests cover each guard. |
| T-lgd-02 | Spoofing | clarify beat (faked elicitation) | high | mitigate | The answer is typed only after a real `[nurse] <field>> ` prompt appears; `--answer` is never in any built command (tested); a clarify segment with zero prompts aborts the recording; no hand edits of cast or captions. |
| T-lgd-03 | Information disclosure | recorded terminal | low | accept | Only bundled synthetic fixtures run; the child shell has a fixed PS1 and runs no command that prints env or paths beyond the repo. |
| T-lgd-04 | Tampering | git staging | medium | mitigate | Explicit-path staging only (never `git add -A` / `git add docs/assets`); Task 2 verify checks the two tracked outputs are committed; untracked user assets stay unstaged. |
| T-lgd-05 | Denial of service | hung model call | low | mitigate | Per-segment SEGMENT_TIMEOUT raises SystemExit; render-demo.sh's trap removes the temp work dir. |
| T-lgd-SC | Tampering | npm/pip/cargo installs | low | accept | No package is installed or added in this plan (`uv sync --frozen` only reproduces the committed lock). |
</threat_model>

<verification>
- `uv run pytest tests/test_record_demo.py tests/test_demo.py tests/test_demo_runbook.py tests/test_docs_final.py tests/test_readme_runbook.py -q` passes.
- `uv run ruff check scripts/record_demo.py tests/test_record_demo.py src/triagedesk/demo/run.py` and `uv run mypy scripts/record_demo.py` are clean.
- docs/assets/triagedesk-demo.mp4 is < 180 s, rendered by `bash docs/render-demo.sh` (exit 0) on the warm local model, with the online mode line visible in the escalation and clarify beats and the typed answer visible at the real prompt.
- `git status --porcelain` shows no staged untracked user assets; spans.jsonl is not staged.
</verification>

<success_criteria>
- The repository's submission video shows the current system on the real local model, including the live MCP elicitation, in one unedited recording under 3:00, with every caption backed by the output it narrates.
- The recorder can never again burn a caption the screen contradicts or a figure that drifted from the report.
- Docs cite the measured duration and tool count, and the upload history is stated truthfully.
</success_criteria>

<output>
Create `.planning/quick/261115-lgd-re-record-the-submission-demo-video-on-t/261115-lgd-SUMMARY.md` when done
</output>
