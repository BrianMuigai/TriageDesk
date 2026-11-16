---
phase: quick-261115-jlr
verified: 2026-11-15T12:30:00Z
status: human_needed
score: 7/7 must-haves verified
covered_files:
  - ".planning/quick/261115-jlr-live-mcp-elicitation-in-the-demo-and-des/261115-jlr-PLAN.md"
  - ".planning/quick/261115-jlr-live-mcp-elicitation-in-the-demo-and-des/261115-jlr-SUMMARY.md"
  - "README.md"
  - "STATUS.md"
  - "demo/storyboard.yaml"
  - "docs/DEMO.md"
  - "docs/DESK.md"
  - "docs/MCP.md"
  - "src/triagedesk/cli.py"
  - "src/triagedesk/demo/run.py"
  - "src/triagedesk/desk/pipeline.py"
  - "src/triagedesk/durable.py"
  - "src/triagedesk/mcp/adapter.py"
  - "src/triagedesk/mcp/elicitation.py"
  - "tests/test_demo.py"
  - "tests/test_desk.py"
  - "tests/test_live_clarification.py"
covered_digest: "v4:sha256:62da41ca076850c6466b89ae67cb812a6243ca5c470212a7c3ef8957eaaf311c"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "In a real terminal: `uv run triagedesk demo --online --beat clarify`, type an answer naming the finding (e.g. `low glucose, 2.1 mmol/L`) at the `[nurse] q1>` prompt and press Enter on the rest."
    expected: "The live model chooses ask_question, the run pauses inside request_clarification, re-matches hypoglycaemia, scores RED via score_priority and commits under the demo nurse. `rm -f spans.jsonl` afterwards."
    why_human: "Needs a real TTY and the live qwen2.5:1.5b model choosing to ask; offline tests stub the model and simulate the TTY. (Harvested from the PLAN's Task 3 <human-check>.)"
  - test: "`uv run triagedesk desk --online`, submit the E-09 vitals with complaint `known diabetic, feeling unwell`, answer the question panel."
    expected: "The question panel renders (no decision controls); after Send answer the SAME case shows the approval gate; nothing is committed until a named nurse decides."
    why_human: "Browser + live model; the offline HTTP test proves the same flow with the model stubbed. (Harvested from the PLAN's Task 3 <human-check>.)"
---

# Quick 261115-jlr: Live MCP elicitation in the demo and the desk. Verification report

**Goal:** Make MCP elicitation work live on the CLI demo (new `clarify` beat) and the online desk through ONE opt-in seam that routes `request_clarification` via the real in-process MCPAdapter. Fix resume (desk /clarify, CLI `resume --answer`) so answers reach the real tool. Keep the batch eval unchanged and keep the safety invariants. DRY+SOLID.
**Verified:** 2026-11-15
**Status:** human_needed. All automated checks pass. The two live/interactive checks the PLAN deferred to a human remain.
**Re-verification:** No. This is the initial verification.

## Goal achievement

### Observable truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `demo --online --beat clarify --answer …` pauses inside the real `request_clarification` MCP call, prints `[elicit]`/`[nurse]` lines and the `[tool] request_clarification` result after the resume, re-matches, scores through `score_priority`, and commits only after the named approval | VERIFIED (code path); live model run is a human item | `demo/run.py::_run_beat` wraps `build_tools` with `with_live_clarification` only when `not offline`. `_answer_question` prints from the adapter payload. `_respond_for` returns `_resume_for(beat)` (named approval) only for non-elicitation payloads. Tests `test_the_cli_answer_flag_drives_the_online_clarify_beat` and `test_the_online_clarify_beat_asks_and_acts_on_the_answer` drive the real adapter + real server with only the model stubbed, and they pass. |
| 2 | An answer is an observation only: it goes to `nurse_answers`, is re-matched deterministically, the colour equals `score_priority(case, matched_ids)`, it never answers the gate, and a decline/empty/all-blank answer appends nothing | VERIFIED | `resume_with_answers` declines unless at least one paired value is non-blank. Passing tests: `test_an_accepted_answer_is_rematched_scored_and_committed_only_by_approval` (colour == `server_module.score_priority(...)`), `test_an_answer_never_answers_the_approval_gate`, `test_a_decline_records_nothing`, `test_resume_with_answers_declines_when_nothing_was_answered[[]/blank]`. Graph, core and `mcp/server.py` are unchanged since 2028403. |
| 3 | No demo run blocks on stdin unless online AND TTY AND no `--answer`; the bare offline demo runs all six beats non-interactively; the offline planner never asks | VERIFIED | `_collect_answers`: explicit answers win, and `offline or not sys.stdin.isatty()` returns `[]`. I ran `uv run triagedesk demo < /dev/null`: rc=0, 6 `BEAT` lines, 0 `[elicit]`/`[nurse]` lines. Passing tests: `test_a_non_interactive_run_without_answers_declines_and_never_waits`, `test_an_interactive_terminal_is_asked`, `test_the_offline_clarify_beat_never_asks`. |
| 4 | Online desk: a planner that asks renders the question panel; POST /clarify resumes the SAME run to the gate (answer) or to its no-gate terminal (decline) with no queue row; the offline desk is unchanged | VERIFIED | `desk/pipeline.py::_tools_for` wraps only the `extraction is not None` (online) branch. Passing tests: `test_the_online_desk_answer_resumes_the_same_run_to_the_gate` and `test_the_online_desk_decline_reaches_no_gate_and_writes_nothing` (real HTTP server, `injected_store.rows == []`). |
| 5 | `resume --answer` and desk `/clarify` reach the real tool when the paused node re-executes | VERIFIED | `durable.resume_thread(wrap_tools=…)` applies the decorator to the resume map. `cli.py` and `answer_clarification` both pass `with_live_clarification`. Passing tests: `test_cli_resume_answers_a_paused_question_through_the_real_tool` (checkpoint state `nurse_answers == [ANSWER]`), `test_resume_thread_applies_the_injected_tool_decorator`, and the `test_desk.py` assertion that `wrap_tools is with_live_clarification`. |
| 6 | The eval harness never uses the seam; `emit_evals.py --check` exits 0 | VERIFIED | `grep with_live_clarification\|mcp.adapter src/triagedesk/evals/` returns nothing. `git diff 2028403..HEAD -- src/triagedesk/evals evals/` is empty. `emit_evals.py --check` prints `EVALS.md is up to date (report 0ae3dde6ca3f3615)`. |
| 7 | `MCPAdapter` is named only in `mcp/adapter.py`; importing it prints no beta warning | VERIFIED | `grep -rn MCPAdapter src/` matches only adapter.py. `uv run python -c 'from triagedesk.mcp import adapter' 2>&1 \| grep -c LangChainBetaWarning` returns 0. |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

### Deviation #1: can an elicitation answer be treated as an approval?

**Finding: no.** I traced every path.

- **CLI `_resume_policy` (cli.py:76-91).** It returns `resume_with_answers(...)` only when `is_elicitation(payload)`. That value is `{"responses": {key: {action, content?}}}` and never carries `decision` or `approved_by`. For an approval payload with no `--decision`:
  - If this resume answered a question, it returns `None`. `durable._drive` / `resume_paused` treat `None` as "stop, leave paused", so `main` prints "paused again at the approval gate; nothing has been committed".
  - Otherwise it raises `DurableError` naming `--decision`. The pending-approval + `--answer`-only case still raises; `test_resume_policy_names_the_missing_decision_for_an_approval` covers it unchanged.
  - The `answered_a_question` flag is per-invocation (closure state) and is set only after an elicitation payload has actually been answered, so a run that was already at the gate cannot reach the `None` branch.
- **Approval is synthesised only from `--decision`.** The approval value is always `approval_decision(args.decision, approver, role, colour)`, validated eagerly. It is never built from `--answer`.
- **Defence in depth.** Suppose an elicitation-shaped value did reach `approval_gate`. The only way would be desk `/clarify` posted against a thread pending at approval, which is pre-existing and unchanged. `_build_token` would copy it verbatim, and `commit_priority` would refuse it: `ApprovalToken.decision` is a required `Literal`, and `ValidationError` leads to `refused=True` before any store call.
- **Tests.** `test_cli_resume_answers_a_paused_question_through_the_real_tool` asserts the stderr "paused again at the approval gate" and `injected_store.rows == []`.

### Required artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/triagedesk/mcp/adapter.py` | VERIFIED | `with_live_clarification` replaces only `request_clarification`, returns a new dict, and loads lazily via `MCPAdapter(server_module.server)`. It has no try/except, so the interrupt propagates. |
| `src/triagedesk/mcp/elicitation.py` | VERIFIED | `resume_with_answers` is the single answers-to-resume rule, used by `cli.py` and `demo/run.py`. |
| `src/triagedesk/demo/run.py` | VERIFIED | `[elicit]`/`[nurse]` prefixes, `--answer`/TTY/decline handling, and the approval payload recorded separately (`record["approval"]`) and passed to `_print_outcome`. |
| `demo/storyboard.yaml` | VERIFIED | The `clarify` beat on E-09 is appended. `failure` is unchanged. |
| `src/triagedesk/durable.py` | VERIFIED | `wrap_tools` parameter added. The module still imports no `triagedesk.mcp` module (grep is empty). |
| `src/triagedesk/desk/pipeline.py` | VERIFIED | The online submit and `answer_clarification` both go through the seam. |
| `tests/test_live_clarification.py` | VERIFIED | 19 tests covering seam, rule, graph, demo, CLI, durable and desk. Only the model is stubbed. All pass. |
| `docs/DEMO.md`, `DESK.md`, `MCP.md`, `STATUS.md`, `README.md` | VERIFIED | The live runbook, the alias caveat (cites the YAML, no alias list restated) and the "batch eval still `unavailable`" note are present. The stale MCP.md "no shipped graph node calls it" note is replaced. STATUS/README drop elicitation from future work and claim no new figure. |

### Key link verification

| From | To | Via | Status |
|------|----|-----|--------|
| demo/run.py | mcp/adapter.py | lazy import in `_run_beat` when `not offline`; `_run_durable` untouched | WIRED |
| mcp/adapter.py | mcp/server.py | `MCPAdapter(server_module.server).list_tools()` in process | WIRED (the roundtrip is exercised by the passing graph tests) |
| desk/pipeline.py | durable.py | `_tools_for` online wrap; `answer_clarification(..., wrap_tools=with_live_clarification)` | WIRED |
| cli.py | mcp/elicitation.py | `_resume_policy` calls `resume_with_answers`; `resume` passes `wrap_tools` (lazy import after `harden_offline`) | WIRED |
| demo/run.py | evals/outcome.py | `_print_outcome(case, record.get("approval"), ...)`, never the first (question) payload | WIRED |

### Behavioral spot-checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full offline suite | `uv run pytest -q` | 923 passed in 57.75s | PASS |
| Bare offline demo never waits | `uv run triagedesk demo < /dev/null` | rc=0, 6 BEAT lines, no `[elicit]` | PASS |
| Eval seal unchanged | `uv run python scripts/emit_evals.py --check` | up to date (0ae3dde6ca3f3615), rc=0 | PASS |
| Lint | `uv run ruff check` | All checks passed | PASS |
| Types on touched modules | `mypy durable.py desk/pipeline.py cli.py mcp/elicitation.py` | no issues | PASS |
| No beta warning | `python -c 'from triagedesk.mcp import adapter'` | 0 warnings | PASS |

Note: my first suite run (with `-x`) failed `test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`. A `spans.jsonl` had appeared at the repo root mid-run, because my offline demo spot-check (or the orchestrator's concurrent live run) ran at the same time. With nothing else running, the clean re-run passed 923/923. `spans.jsonl` was removed before and after.

### Probe execution

Not applicable. The PLAN declares no `probe-*.sh`.

### Requirements coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ELICIT-01/02 (elicitation inside the tool call, server-derived questions) | SATISFIED | Real adapter interrupt; the prompts are a subset of `coverage.question_for(candidates)` (tested) |
| ELICIT-03/08 (refusal never becomes a value; blank = no observation) | SATISFIED | `resume_with_answers` decline rule + tests |
| ELICIT-05 (a question is not a decision) | SATISFIED | See the deviation #1 analysis above |
| JC-1 (judge-visible agentic behaviour) | NEEDS HUMAN | The live TTY/browser run (human items) |

### Anti-patterns found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (all modified src/tests) | — | TBD/FIXME/XXX/TODO/HACK | none found | — |
| src/triagedesk/cli.py | 85-91 | `resume --answer X --decision approve` answers the question and then approves the post-answer colour, which the operator never saw (e.g. GREEN to RED). It is still an explicit, named, validated approval, the combination predates this task, and the docs advertise the two-step flow only. | Info | Consider documenting that `--decision` together with `--answer` approves an unseen re-scored colour, or refusing that combination. Not a gap. |
| src/triagedesk/demo/run.py | `_collect_answers` | `demo --answer` offline is silently ignored, because the offline planner never asks | Info | Documented as online-only in the `--help` text |

### Human verification required

#### 1. Live TTY clarify beat
**Test:** `uv run triagedesk demo --online --beat clarify`, then type `low glucose, 2.1 mmol/L` at `[nurse] q1>` and press Enter on the rest.
**Expected:** The model asks, the answer is re-matched to hypoglycaemia, the case scores RED and commits under the demo nurse.
**Why human:** This needs a real terminal and the live model choosing `ask_question`.

#### 2. Online desk question panel
**Test:** `uv run triagedesk desk --online`, submit the E-09 vitals with complaint `known diabetic, feeling unwell`, then answer the panel.
**Expected:** The panel appears without decision controls, the approval gate follows on the same case, and nothing is committed until a named decision.
**Why human:** This needs a browser and the live model.

### Gaps summary

No gaps. Every must-have is implemented and wired, and passing offline tests exercise each one through the real adapter, the real server tool and the real planner guard (only the model is stubbed). The safety invariants hold, including the scrutinised deviation #1. The status is `human_needed` only because the PLAN's Task 3 `<human-check>` (live TTY demo + online desk in a browser) cannot be verified programmatically.

---

_Verified: 2026-11-15_
_Verifier: Claude (gsd-verifier)_
