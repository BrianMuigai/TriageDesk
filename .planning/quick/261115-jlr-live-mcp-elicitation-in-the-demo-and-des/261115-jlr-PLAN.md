---
quick_id: 261115-jlr
slug: live-mcp-elicitation-in-the-demo-and-des
phase: quick-261115-jlr
plan: 01
type: execute
wave: 1
depends_on: []
branch: feat/v1.3-adaptive-triage
files_modified:
  - src/triagedesk/mcp/adapter.py
  - src/triagedesk/mcp/elicitation.py
  - src/triagedesk/demo/run.py
  - demo/storyboard.yaml
  - src/triagedesk/cli.py
  - src/triagedesk/durable.py
  - src/triagedesk/desk/pipeline.py
  - tests/test_live_clarification.py
  - tests/test_demo.py
  - tests/test_desk.py
  - docs/DEMO.md
  - docs/DESK.md
  - docs/MCP.md
  - STATUS.md
  - README.md
autonomous: true
requirements: [ELICIT-01, ELICIT-02, ELICIT-03, ELICIT-05, ELICIT-08, JC-1]

estimate:
  tokens: 115000
  raw_tokens: 115000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`uv run triagedesk demo --online --beat clarify --answer <alias-bearing answer>` pauses INSIDE the real `request_clarification` MCP call (an `mcp_elicitation` interrupt), prints the server's own questions as `[elicit] ...` lines and the answer as `[nurse] ...` lines, prints the `[tool] request_clarification` result after the resume, re-matches, scores a colour through `score_priority`, and commits only after the beat's named approval"
    - "A nurse answer is an observation only: it is appended to `nurse_answers` and re-matched by the deterministic matcher; the colour equals `score_priority(case, matched_ids)`; an answer never answers the approval gate; a decline, an empty input or an all-blank answer appends nothing and declines"
    - "No demo run blocks on stdin unless it is online AND stdin is a TTY AND no `--answer` was given; the bare offline `uv run triagedesk demo` runs all six beats non-interactively and the offline planner never asks"
    - "`uv run triagedesk desk --online`: a submission whose planner chooses to ask renders the existing question panel, and POST /clarify resumes the SAME run to the approval gate (answer) or to its no-gate terminal (decline) with no queue row written; the offline desk path is unchanged"
    - "`triagedesk resume --answer` and the desk's /clarify reach the real tool when the paused node re-executes, so a resumed question no longer silently becomes `unavailable`"
    - "The eval harness never uses the live seam: nothing under `src/triagedesk/evals/` references it and `uv run python scripts/emit_evals.py --check` exits 0 (sealed reports unchanged)"
    - "`MCPAdapter` is still named in exactly one module (`src/triagedesk/mcp/adapter.py`), and importing that module prints no beta warning on the presenter's screen"
  artifacts:
    - path: src/triagedesk/mcp/adapter.py
      provides: "with_live_clarification(tools) — the ONE opt-in seam: returns a new tool map whose request_clarification is the adapter-loaded owned tool, loaded in process"
    - path: src/triagedesk/mcp/elicitation.py
      provides: "resume_with_answers(payload, supplied) — the ONE rule turning surface answers into an accept/decline resume value (CLI resume + demo share it)"
    - path: src/triagedesk/demo/run.py
      provides: "the demo respond policy: [elicit]/[nurse] lines, --answer / TTY / decline handling, approval payload kept separate from the question payload"
    - path: demo/storyboard.yaml
      provides: "the additive `clarify` beat on E-09"
    - path: src/triagedesk/durable.py
      provides: "resume_thread(..., wrap_tools=None) — an injected tool-map decorator; durable names no MCP module"
    - path: src/triagedesk/desk/pipeline.py
      provides: "online submit and /clarify answer both built through the seam"
    - path: tests/test_live_clarification.py
      provides: "the ONE offline (no Ollama) proof module for live clarification on every surface: real guard + real adapter + real elicitation. Task 1 adds the seam/demo-runner tests (accept / decline / non-alias / gate-not-answered / never-blocks / interactive / offline beat); Task 2 appends the CLI demo-flag, CLI resume-over-a-checkpoint, wrap_tools hook and online-desk HTTP tests"
    - path: docs/DEMO.md
      provides: "the live `clarify` runbook section, alias-matching caveat, eval-still-unavailable note"
  key_links:
    - from: src/triagedesk/demo/run.py
      to: src/triagedesk/mcp/adapter.py
      via: "_run_beat wraps build_tools(...) with with_live_clarification ONLY when not offline (lazy import); _run_durable is untouched"
    - from: src/triagedesk/mcp/adapter.py
      to: src/triagedesk/mcp/server.py
      via: "MCPAdapter(server_module.server).list_tools() in process — a real 2026-07-28 session over the in-memory transport, so the tool returns InputRequiredResult and the adapter raises interrupt(mcp_elicitation)"
    - from: src/triagedesk/desk/pipeline.py
      to: src/triagedesk/durable.py
      via: "_tools_for wraps online_tools with the seam; answer_clarification passes wrap_tools=with_live_clarification to resume_thread"
    - from: src/triagedesk/cli.py
      to: src/triagedesk/mcp/elicitation.py
      via: "_resume_policy and the demo policy both call resume_with_answers; resume passes wrap_tools=with_live_clarification (lazy import after harden_offline)"
    - from: src/triagedesk/demo/run.py
      to: src/triagedesk/evals/outcome.py
      via: "_print_outcome receives the APPROVAL payload the policy answered, never the elicitation payload (capture_outcome reads colour/citations from the payload it is given)"
---

# Quick task 261115-jlr — live MCP elicitation on the CLI demo and the desk

<objective>
Make MCP elicitation actually happen, live, on the two interactive surfaces, so a judge at the live
final sees the agent ask the nurse a question mid-tool-call and act on her answer.

Today every shipped surface (demo, desk, eval) builds its tool map through `evals/tools.py::_tool_map`,
whose `request_clarification` calls the server function in process with `ctx=None` and therefore
always answers `unavailable`. The shipped adapter path DOES work (proved in process by
`tests/test_elicitation_roundtrip.py`), but nothing on a demo surface uses it.

This plan adds ONE opt-in seam in the one module that names the adapter, wires it into the online
demo (a new additive `clarify` beat on E-09) and the online desk (whose question panel already
exists but is never reached), fixes the resume path so a re-executed question node reaches the real
tool, and documents the behaviour honestly — including that the batch eval still records
`unavailable` because no human answers in a batch run.

Purpose: the strongest answer to "is this genuinely agentic?" is the agent visibly asking a human,
pausing, and acting on the answer — through MCP, live, in front of the judges.
Output: the seam + surface wiring with offline tests, docs, and a recorded live online run.

**DRY/SOLID (CONVENTIONS §1–2, iron-clad):**
- **D/O:** the seam is a pure tool-map decorator injected by each surface; the graph, the planner
  guard and `evals/tools.py` are not edited. `durable.resume_thread` gains an injected decorator
  parameter instead of importing the MCP layer (durable.py is TID251-banned from it anyway).
- **S/I:** the seam replaces exactly ONE key (`request_clarification`); every other callable in
  the map is passed through by identity. The adapter-loaded tool list is never exposed.
- **DRY:** `MCPAdapter` stays named only in `src/triagedesk/mcp/adapter.py`; the answers→resume rule
  lives once in `mcp/elicitation.py` and both the CLI resume policy and the demo policy call it;
  question text is read from the payload via the existing `mcp.elicitation` helpers (it was minted
  by `core.coverage.question_for`), never re-authored; no SATS alias string is added under `src/`.
- **Eval untouched:** the harness keeps `build_tools` without the seam (no human → it must not
  pause); the sealed reports and `emit_evals.py --check` are unchanged.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md
@docs/CONVENTIONS.md
@tests/test_elicitation_roundtrip.py

<!-- planner-discipline-allow: low glucose -->
<!-- planner-discipline-allow: with_live_clarification -->
<!-- planner-discipline-allow: LangChainBetaWarning -->

## Grounded facts (verified at planning time — do not re-derive, but trust live output if it differs)

| Fact | Evidence |
| --- | --- |
| `request_clarification` (`src/triagedesk/mcp/server.py` ~585) returns `unavailable` when `ctx is None`; through `MCPAdapter(server_module.server)` in process it returns `InputRequiredResult` and the adapter raises `interrupt()` of type `mcp_elicitation` (payload keys `type`, `tool_name`, `requests[]` with `key`, `message`, `mode`, `requested_schema`). | `tests/test_elicitation_roundtrip.py` |
| Each adapter-loaded LangChain tool opens its own client per call (`.venv/.../langchain/mcp/tools.py` `call_tool`: `async with client:`), and `MCPAdapter.list_tools()` enters its own context. So loading the tools and invoking later outside any `async with` is safe — `adapter.load_tools()` already does exactly this. | read |
| An in-process adapter call prints NO INFO log lines (measured with the root RichHandler installed). | probe |
| Importing `langchain.mcp` prints a `LangChainBetaWarning` on stderr: `uv run python -c "from triagedesk.mcp import adapter" 2>&1 \| grep -c LangChainBetaWarning` → 1. `langchain_core` installs its own warning filter when it is imported, so an ignore filter only wins if installed AFTER `langchain_core` is imported. Verified silent: import `LangChainBetaWarning` from `langchain_core._api.beta_decorator` first, then wrap the `MCPAdapter` import in `warnings.catch_warnings()` + `warnings.simplefilter("ignore", category=LangChainBetaWarning)`. | probe |
| E-09 offline (`uv run triagedesk demo --beat failure`): `match_discriminators` → `retrieval_status: ambiguous`, three candidates (the hypoglycaemia id + two diabetic-hyperglycaemia ids); offline `plan_next_step` = `planner.default_plan` → finish; outcome GREEN with `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)`; no gate (bounded-clarification terminal), no commit line. | run |
| The three derived questions for E-09 are `coverage.question_for(id)` (`Ask about: …`), form fields `q1..q3`. An accept carrying only `q1` is valid (the roundtrip test accepts `{"q1": "yes"}` against two questions). `_CLARIFICATION_MESSAGE` is the request's `message`. | `mcp/server.py:421-440`, roundtrip test |
| The matcher on `low glucose, 2.1 mmol/L` alone → the hypoglycaemia id; `score_priority(E-09 case, [that id])` → **RED / Immediate** (an emergency discriminator; clinically right — SATS adult glucose < 3). Matching is alias text (`data/sats_discriminators.yaml` aliases include `low glucose`, `low blood sugar`, `glucose below 3`, `hypo`); a bare number does not match. | measured |
| `retrieve` re-matches `_rematch_text(complaint, nurse_answers)` (`graph/nodes.py:215-251`). `route_after_retrieve` bypasses the planner only on a fired VITALS emergency verdict, so after an accepted answer on E-09 the run returns to `plan` (one more model call online); the guard refuses a second `ask_question` (round 1 / already taken). | read |
| On resume LangGraph RE-EXECUTES the interrupted node from its start: `ask_question` calls `tools["request_clarification"]` again and only the adapter-backed tool consumes the resume value. `durable.resume_thread` builds `offline_tools(CaseInput(), …)` whose in-process tool answers `unavailable` — so today any durable resume of a question silently drops the answer (latent: unreachable until a surface pauses at a question; the online desk will). | `durable.py:296-326`, `evals/tools.py:173-179` |
| `invoke_graph` returns the FIRST interrupt payload; `capture_outcome` / `_print_outcome` read colour, citations and target from the payload they are given — handing them the elicitation payload would print `colour: None`. | `durable.py:80-102`, `evals/outcome.py:46-50`, `demo/run.py:143-177` |
| Desk: `views` checks `is_elicitation(paused.payload)` FIRST and renders `_question_html` (form `action="/clarify"`, hidden `thread_id` + `request_key`, inputs `answer.q1..`); `/clarify` → `pipeline.answer_clarification` → `resume_thread(..., respond=lambda _: None)` → the gate is rendered as itself (`class="approval-gate"`). Desk online: `_handle_case` → `_online_extraction` (calls `desk.extraction.extract_complaint` through the module, monkeypatchable) → `submit_case(..., extraction=…)` → `_tools_for` → `online_tools`. | `desk/server.py:359-458`, `desk/views.py:173-192` |
| Desk ambiguity: complaint `known diabetic, feeling unwell` → `ambiguous` with the two diabetic-hyperglycaemia candidates; `feeling unwell` alone → `no_candidate` (never asks). | measured |
| Layering guards: `src/triagedesk/durable.py` is NOT in the TID251 per-file-ignores (it may not import the MCP package); `desk/**` may not import `triagedesk.mcp.server` / `store.queue` directly (`tests/test_desk.py:760`) — `triagedesk.mcp.adapter` is allowed; importing `triagedesk.cli` must load no langchain/mcp (`tests/test_observability.py::test_importing_the_cli_pulls_no_tracer_capable_stack`) → every new CLI import is lazy inside `main`; `docs/DESK.md` must name no underscore-bearing graph node and no thread-id token (`tests/test_desk_runbook.py:116`). | read |
| Test seams: the autouse `_model_seam_is_stubbed` fixture makes `server_module.extract_async` / `propose_plan_async` raise; tests monkeypatch them (a test may stub the MODEL, never the guard). `_always_proposes(action)` exists in `tests/test_plan_audit.py`; test modules import helpers from sibling test modules (`tests/test_desk_online.py` imports from `test_desk`). The autouse `injected_store` is a `RecordingStore` with `.rows`. pytest's stdin `isatty()` returns False. | `tests/conftest.py:185-250` |
| `tests/test_desk.py` `_resume` stubs at ~2026 and ~2062 use a STRICT keyword signature `(*, thread_id, decision, db_path, respond)` — a new kwarg from `answer_clarification` raises TypeError there. `tests/test_demo.py:49-51` pins the storyboard names list. `tests/test_demo_runbook.py::test_no_cli_beat_is_omitted` requires every CLI beat to appear as `--beat <name>` inside a fenced block of `docs/DEMO.md`. | read |
| Model calls are `temperature 0, seed 42` (`llm/client.py:48`); the orchestrator observed the online model proposing `ask_question` on E-09. | read |
| **Measured post-answer routing, DEMO path** (in-process graph, `build_tools(E-09, offline=False)` + an adapter-backed `request_clarification`, model stubbed to always propose `ask_question`, real guard): accept the alias-bearing answer → payloads `[mcp_elicitation, approval]`, `nurse_answers` = [answer], `matched_ids` = [hypoglycaemia id], second plan step = the stub's question OVERRIDDEN by the guard to `finish_investigation`, colour RED, committed at position 1 (one row). Decline → payloads `[mcp_elicitation]` only, no answers, ids `[]`, GREEN, no commit, 0 rows. Non-alias `glucose 2.1` accepted → answers recorded, ids `[]`, GREEN, no gate, 0 rows. | scratchpad probe @2028403 |
| **Measured post-answer routing, DESK path** (`run_to_gate` over a temp checkpoint with `online_tools(case, extraction)` + seam, complaint `known diabetic, feeling unwell`, E-09 vitals; then `resume_paused` with `offline_tools(CaseInput())` + seam and `respond=lambda _: None`, exactly what `answer_clarification` will do): first pause `mcp_elicitation`. Accept → re-match `matched` with the hypoglycaemia id; the post-answer plan step is the OFFLINE `planner.default_plan` → `finish_investigation` (not overridden; no model on the resume path); colour RED; confidence `deliver` → the run pauses at the **approval** interrupt; 0 rows. Decline → `elicitation_outcome: declined`, ids `[]`, `ambiguous`, GREEN, confidence `clarify` → the v1.2 bounded-clarification terminal (no approval interrupt); 0 rows. Non-alias accept → answers recorded, ids `[]`, confidence `defer` → no approval interrupt; 0 rows. The resume path is deterministic (no model call), so a missing gate after an alias-bearing answer is a regression, not flakiness. | scratchpad probe @2028403 |
| CLI runs from the repo root write `spans.jsonl` there and break `tests/test_observability.py` — `rm -f spans.jsonl` after EVERY manual CLI run. Never stage untracked `docs/assets/*`. | prior quick task |
| Baselines @2028403: `uv run pytest --co -q` → 904 tests; `uv run ruff check` clean; `uv run mypy` over the six touched src files → 2 pre-existing errors (`demo/run.py` import-untyped yaml; `mcp/adapter.py` type-arg). | measured |

@src/triagedesk/mcp/adapter.py
@src/triagedesk/mcp/elicitation.py
@src/triagedesk/demo/run.py
@src/triagedesk/durable.py
@src/triagedesk/desk/pipeline.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): the opt-in seam, wired end-to-end through the online demo's new `clarify` beat</name>
  <files>src/triagedesk/mcp/adapter.py, src/triagedesk/mcp/elicitation.py, src/triagedesk/demo/run.py, demo/storyboard.yaml, tests/test_live_clarification.py, tests/test_demo.py, docs/DEMO.md</files>
  <read_first>src/triagedesk/mcp/adapter.py (whole), src/triagedesk/mcp/elicitation.py (whole), src/triagedesk/demo/run.py (whole), demo/storyboard.yaml, src/triagedesk/durable.py lines 80-160 (invoke_graph, _drive), src/triagedesk/graph/planning.py lines 157-198 (ask_question), tests/test_elicitation_roundtrip.py, tests/test_plan_audit.py lines 60-70 (_always_proposes), tests/test_demo.py lines 40-60, docs/DEMO.md lines 42-62</read_first>
  <behavior>
    Constants in the new test module: ANSWER = "low glucose, 2.1 mmol/L" (alias-bearing); NON_ALIAS = "glucose 2.1". E-09 is loaded with `load_cases` from `evals/cases` (never re-typed). Model stub helper: monkeypatch `server_module.extract_async` → `async_return(ExtractionResult(case=e09.case, matched_discriminator_ids=[]))` and `server_module.propose_plan_async` → `_always_proposes(PlanAction.ASK_QUESTION)` (imported from test_plan_audit) — the model is stubbed, the shipped guard in `server_module.plan_next_step` is real. Module-level `pytestmark` filters the LangChain beta warning exactly as `tests/test_elicitation_roundtrip.py` does.
    - Seam narrowness (sync): `with_live_clarification(tools)` returns a NEW dict with identical keys; every value except `request_clarification` is the SAME object (`is`); the input mapping is not mutated.
    - `resume_with_answers` unit: answers pair with the form fields in question order → accept with those fields; all-blank or empty supplied → decline; a payload with no form request → decline (key falls back to `CLARIFICATION_REQUEST_KEY`).
    - Accept, state level (async): `build_tools(e09, offline=False, recorder=UsageRecorder())` → `with_live_clarification` → `build_graph(..., checkpointer=in_memory_checkpointer())` → `invoke_graph(..., respond=policy)` where the policy records every payload, answers a question with `resume_with_answers(payload, [ANSWER])` and an approval with `approval_decision("approve", approver=..., role=...)`. Assert: the first payload's type is `InterruptType.ELICITATION`; every prompt from `answer_prompts(form_requests(payload)[0])` is in `{coverage.question_for(i) for i in match.candidates}` where `match = await server_module.match_discriminators(e09.case.complaint, e09.note)`, and there is at least one; a later payload is an approval; `state["nurse_answers"] == [ANSWER]`; the matcher's ids for ANSWER alone are a non-empty subset of `state["matched_ids"]`; `state["priority"].colour == (await server_module.score_priority(e09.case, list(state["matched_ids"]))).colour`; the commit is committed and `injected_store.rows` has exactly one row.
    - An answer never answers the gate: same run but the policy returns None at the approval → the final state is paused at an approval interrupt and `injected_store.rows == []`.
    - Decline: the policy declines (`resume_with_answers(payload, [])`) → `state["elicitation_outcome"] == "declined"`, no `nurse_answers`, `matched_ids == []`, `injected_store.rows == []`.
    - Alias caveat pinned honestly: precondition `(await server_module.match_discriminators(NON_ALIAS, "")).matched_ids == []`; accept NON_ALIAS → `nurse_answers == [NON_ALIAS]`, `matched_ids == []`, no queue row.
    - Runner end-to-end (async): `await run_demo(beats=["clarify"], offline=False, answers=[ANSWER], store=store)` with `store = InMemoryStore()` returns 0; captured stdout has an `[elicit]` line carrying `coverage.question_for` text, the `[nurse] q1: ` line with ANSWER (field name via `answer_field(1)`), a `[tool] request_clarification` line, and a `commit` line containing `committed`; `SHOWN MISMATCH` is NOT printed; `await store.read_queue_rows()` has one row.
    - Never blocks (async): `await run_demo(beats=["clarify"], offline=False, store=InMemoryStore())` with no answers (pytest stdin is not a TTY) returns 0, prints the decline line, prints no `committed`.
    - (The CLI `--answer` flag and its `main(...)`-level tests belong to Task 2.)
    - Interactive (async): monkeypatch `sys.stdin` with a `io.StringIO` subclass whose `isatty()` returns True, holding ANSWER then two empty lines; `await run_demo(beats=["clarify"], offline=False, store=store)` with `store = InMemoryStore()` returns 0 and `await store.read_queue_rows()` has one row.
    - Offline beat (async): `await run_demo(beats=["clarify"], store=InMemoryStore())` returns 0 and prints no `[elicit]` line (the offline planner never asks).
    - tests/test_demo.py: the storyboard-names test now expects `[..., "failure", "clarify"]` and its docstring says six beats.
  </behavior>
  <action>
Write tests/test_live_clarification.py and the tests/test_demo.py names change FIRST and run them RED, then implement (GREEN).

1. src/triagedesk/mcp/adapter.py — the ONE opt-in seam (per the description's required behaviour 1).
   - Silence the beta warning at its single source: import `LangChainBetaWarning` from `langchain_core._api.beta_decorator`, then move the module-level MCPAdapter import inside `warnings.catch_warnings()` with `warnings.simplefilter("ignore", category=LangChainBetaWarning)` — after every other import (langchain_core must already be imported so its own filter is in place; the grounded-facts probe proves this order is silent). Comment WHY: the beta API is a recorded, exact-pinned decision (STACK flag) and the warning would otherwise print on the live demo screen. If ruff reports E402 on a line, add a targeted `# noqa: E402` on that line only.
   - Add a private `async def _owned_tool(name: str) -> BaseTool` that imports `triagedesk.mcp.server` LAZILY inside the function (server → store → borrowed lazily imports this module; keep the import graph acyclic), loads `MCPAdapter(server_module.server).list_tools()` IN PROCESS, and returns the tool with that name, raising `LookupError` if absent (a transport/discovery failure must never become a clinical answer).
   - Add public `with_live_clarification(tools: Mapping[str, Any]) -> dict[str, Any]` (sync): returns `{**tools, "request_clarification": <async callable>}` where the callable takes the graph's single input mapping, loads the tool via `_owned_tool` at call time (no adapter cost unless the planner actually asks), and returns `await tool.ainvoke({"candidates": list(inp.get("candidates") or [])})` unchanged — the graph's `parse_tool_result` already decodes content blocks. No try/except: the `mcp_elicitation` interrupt must propagate to LangGraph exactly as `ask_question`'s docstring requires. Docstring states: in process = a real 2026-07-28 MCP session over the in-memory transport (not a direct function call), so the store seam and the audit interceptor apply and no stdio subprocess or borrowed store is launched; opt-in because a human must be present to answer — the eval harness has none and must keep `unavailable`; only this one key is replaced (SOLID I) and the adapter's tool list is never exposed. Update the module docstring's loader list to name the seam. Add it to nothing else; the module still names `MCPAdapter` alone.

2. src/triagedesk/mcp/elicitation.py — add `resume_with_answers(payload: Mapping[str, Any], supplied: Sequence[str]) -> dict[str, Any]`, the ONE answers→resume rule: take the first `form_requests(payload)` entry, key = its `key` or `CLARIFICATION_REQUEST_KEY`; pair `answers_in_order(answer_fields(request), supplied)`; if a request exists AND at least one paired value is non-blank → `accept_responses(key, paired)`, else `decline_responses(key)` (an all-blank answer is the absence of an observation — ELICIT-03/08). Add to `__all__`. Keep the module free of `langchain.mcp` and `mcp.server` imports. (Task 2 moves the CLI's `_resume_policy` onto this same helper, so it ends the plan with two callers.)

3. (no step — the CLI is untouched in this task; `run_demo`'s new `answers` keyword is exercised directly by the tests and wired to a CLI flag in Task 2.)

4. demo/storyboard.yaml — append (after `failure`) a beat `name: clarify`, `case: E-09`, label `"Online: the agent asks the nurse mid-call and acts on the answer"`. Extend the header comment: the beat is ADDITIVE — `failure` stays the declared, unanswered E-09; `clarify` runs the same case and, online, the planner may ask through `request_clarification`; offline the deterministic planner never asks, so the beat honestly shows the E-09 terminal.

5. src/triagedesk/demo/run.py
   - `run_demo` gains keyword `answers: Sequence[str] | None = None` (docstring: online-only; with none an interactive TTY is asked, otherwise the question is declined) and forwards it to `_run_beat`. `_run_durable` is NOT changed — the durable two-command story keeps the in-process tool and its "paused at approval gate" wording.
   - In `_run_beat`, after `build_tools(...)`: when `not offline`, lazily import the seam and wrap the map with it BEFORE `_traced_tools`, so the `[tool] request_clarification` line prints the real tool's result after the resume (on the first, interrupted execution the wrapper prints nothing — the interrupt propagates through it).
   - Replace the bare decision with a respond policy built by a new private `_respond_for(beat, *, offline, answers)` and pass it as `respond=` to `invoke_graph`. The policy keeps a small closure record of the APPROVAL payload it answered: for an approval it records the payload and returns `_resume_for(beat)` (unchanged decisions); for `is_elicitation(payload)` it calls `_answer_question(payload, offline=offline, answers=answers)`. `_run_beat` then passes the recorded approval payload (or None) — never `invoke_graph`'s first payload — to `_print_outcome`, because `capture_outcome` reads colour/citations/target from the payload it is given. Existing beats are unaffected (their only payload is the approval).
   - `_answer_question`: read everything from the payload through the `mcp.elicitation` helpers (`form_requests`, `answer_fields`, `answer_prompts`) and the payload's own `tool_name` — never re-type the tool name or a question. Print one `[elicit] {tool_name}: {message}` line (the request's `message`), then one `[elicit] {tool_name} asks {field}: {prompt}` line per question. Answers: explicit `answers` win; else if `not offline and sys.stdin.isatty()` read one line per question with `input(f"[nurse] {field}> ")` (catch `EOFError` → blank); else none. If at least one non-blank answer: print `[nurse] {field}: {answer}` for each field (`(no answer)` when blank — skip this echo for the interactive path where the terminal already shows the typed text); otherwise print exactly one `[nurse] declined — no answer given; nothing is recorded` line. Return `resume_with_answers(payload, collected)` — the decline/accept decision is the shared rule, not restated here. Keep the two screen prefixes as module constants (named once).
   - `_print_outcome`: after `matched ids`, print `  answers      : {list}` when `result.get("nurse_answers")` is non-empty and `  elicitation  : {value}` when `result.get("elicitation_outcome")` is set (13-char labels, matching the existing column). For `case.declared_failure`: when answers were accepted, print only `  DECLARED     : {case.expected} (the eval expectation for the note alone — not compared: this run added a nurse answer)`; otherwise keep the existing DECLARED/MEASURED pair byte-for-byte (the `failure` beat's documented output must not change).
   - Update the module docstring (one sentence: the online `clarify` beat runs the real elicitation through the seam).

6. docs/DEMO.md — minimal drift-guard edit only (Task 3 writes the section): in the one-command fenced block (lines ~48-53), after the `failure` line, add `uv run triagedesk demo --online --beat clarify   # live: the agent asks the nurse (see below)` so `tests/test_demo_runbook.py::test_no_cli_beat_is_omitted` stays green.

Do not edit `src/triagedesk/evals/**`, `src/triagedesk/graph/**`, `src/triagedesk/core/**` or the server. Do not put any SATS alias or example answer text in `src/` (docstrings included). After any manual CLI run, `rm -f spans.jsonl`.
  </action>
  <verify>
    <automated>rm -f spans.jsonl && uv run pytest -q tests/test_live_clarification.py tests/test_demo.py tests/test_demo_runbook.py tests/test_elicitation_roundtrip.py tests/test_elicitation_tool.py tests/test_observability.py tests/test_purity.py tests/test_no_duplicated_sats.py && uv run ruff check</automated>
    <automated>test "$(grep -c 'def with_live_clarification' src/triagedesk/mcp/adapter.py)" -eq 1   # [HEAD=0 EXPECT==1 @2028403]</automated>
    <automated>test "$(grep -c 'def resume_with_answers' src/triagedesk/mcp/elicitation.py)" -eq 1   # [HEAD=0 EXPECT==1 @2028403]</automated>
    <automated>test "$(grep -c 'resume_with_answers' src/triagedesk/demo/run.py)" -ge 1   # [HEAD=0 EXPECT>=1 @2028403 GUARD MUTATION: a second answers->resume rule hand-rolled in the demo]</automated>
    <automated>test "$(grep -rn 'import.*MCPAdapter' src/ | grep -v '^src/triagedesk/mcp/adapter.py:' | wc -l)" -eq 0 && test "$(grep -c 'import MCPAdapter' src/triagedesk/mcp/adapter.py)" -eq 1   # [HEAD=0,1 EXPECT==0,==1 @2028403 GUARD MUTATION: importing the adapter class outside mcp/adapter.py]</automated>
    <automated>test "$(grep -rn 'with_live_clarification' src/triagedesk/evals/ | wc -l)" -eq 0   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: wiring the seam into the eval harness, which has no human and would hang]</automated>
    <automated>test "$(uv run python -c 'from triagedesk.mcp import adapter' 2>&1 | grep -c 'LangChainBetaWarning')" -eq 0   # [HEAD=1 EXPECT==0 @2028403]</automated>
    <automated>test "$(grep -c 'name: clarify' demo/storyboard.yaml)" -eq 1   # [HEAD=0 EXPECT==1 @2028403]</automated>
    <automated>test "$(grep -rni 'low glucose' src/ | wc -l)" -eq 0   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: baking an alias-bearing default answer into src]</automated>
    <automated>test "$(uv run mypy src/triagedesk/mcp/adapter.py src/triagedesk/mcp/elicitation.py src/triagedesk/demo/run.py 2>&1 | grep -cE '^src/triagedesk/(mcp/adapter|mcp/elicitation|demo/run)\.py:[0-9]+: error')" -le 2   # [HEAD=2 EXPECT<=2 @2028403 GUARD MUTATION: a new type error in the seam, the resume helper or the demo policy]</automated>
    <automated>out=$(mktemp) && uv run triagedesk demo > "$out" 2>&1 < /dev/null; rc=$?; grep -c '^BEAT ' "$out" | grep -qx 6; b=$?; rm -f "$out" spans.jsonl; test $rc -eq 0 -a $b -eq 0   # bare offline demo: six beats, no stdin wait</automated>
  </verify>
  <done>`with_live_clarification` and `resume_with_answers` exist once each (the CLI is untouched in this task); the online `clarify` beat pauses inside the real MCP tool, prints `[elicit]`/`[nurse]` lines and acts on the answer (proved offline with a stubbed model and the real guard/adapter); decline, blank and non-alias answers add nothing that changes the colour; an answer never answers the gate; no run blocks on stdin; the bare offline demo runs six beats; importing the adapter prints no beta warning; ruff clean; no new mypy errors; no `spans.jsonl` left.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: The CLI and the online desk ask through the seam, and every resume of a question reaches the real tool</name>
  <files>src/triagedesk/durable.py, src/triagedesk/desk/pipeline.py, src/triagedesk/cli.py, tests/test_live_clarification.py, tests/test_desk.py</files>
  <read_first>src/triagedesk/durable.py lines 212-326 (resume_paused, resume_thread), src/triagedesk/desk/pipeline.py (whole), src/triagedesk/desk/server.py lines 359-458 (_handle_case, _handle_clarify), src/triagedesk/desk/clarification.py lines 43-86, src/triagedesk/cli.py lines 53-108 (_resume_policy), 148-182 (demo parser), 324-375 (demo dispatch + resume branch), tests/test_desk_online.py lines 20-60 and 237-262 (the `_running_server` helper and imports to reuse), tests/test_desk.py lines 120-221 (`_base`, `_post`, `_form_from_case`, `_section`) and 2020-2080 (the strict `_resume` stubs), tests/test_durable_cli.py lines 297-410 (existing `_resume_policy` tests this refactor must keep green)</read_first>
  <behavior>
    All new tests are APPENDED to tests/test_live_clarification.py (the one module for live clarification; it reuses Task 1's constants, E-09 loader and model-stub helper, imports `_running_server` from test_desk_online and `_base`, `_post`, `_form_from_case` from test_desk — the same cross-module helper reuse tests/test_desk_online.py already does). No other test module gains tests; tests/test_desk_online.py and tests/test_durable_cli.py are run, not edited.
    - CLI demo flag (sync `def`): with the model stubbed, `main(["demo", "--online", "--beat", "clarify", "--answer", ANSWER])` returns 0; stdout has an `[elicit]` line, the `[nurse] q1: ` line with ANSWER, a `[tool] request_clarification` line and a `commit` line containing `committed`.
    - CLI never blocks (sync `def`): `main(["demo", "--online", "--beat", "clarify"])` (pytest stdin is not a TTY) returns 0, prints the decline line and no `committed`.
    - `_resume_policy` refactor: the existing tests in tests/test_durable_cli.py (answers in question order → accept; no answer → decline; approval → decision; missing decision named) stay green unchanged.
    - CLI resume reaches the real tool (sync): with the same model stubs, `asyncio.run(run_to_gate(with_live_clarification(build_tools(e09, offline=False, recorder=UsageRecorder())), raw_note=e09.note, case=e09.case, db_path=db))` pauses with an elicitation payload; then `main(["resume", "--thread-id", paused.thread_id, "--answer", ANSWER, "--db", str(db)])` returns 0 and stderr says it paused again at the approval gate; reading the checkpoint state (via `graph.build.checkpointed_graph` + `aget_state`) shows `nurse_answers == [ANSWER]` and `injected_store.rows == []`. Without the hook (pre-change) this test fails because the re-executed node answers `unavailable`.
    - Hook unit: `resume_thread(..., wrap_tools=spy)` on a db with no such thread raises `DurableError` AFTER `spy` was called exactly once with a mapping that contains `request_clarification`.
    - Desk online, accept (sync, real HTTP via `_running_server(db, online=True)`): case = the E-09 fixture vitals with complaint `known diabetic, feeling unwell`; PRECONDITIONS asserted in the test before any POST: `(await server_module.match_discriminators(complaint, "")).retrieval_status == "ambiguous"` and the matcher's ids for ANSWER alone are non-empty. Stub `extraction_module.extract_complaint` to return an `ExtractionResult` of that case with no ids, and `server_module.propose_plan_async` with `_always_proposes(PlanAction.ASK_QUESTION)`. POST /case → body has `class="clarification-panel"` and `action="/clarify"` and NO `class="approval-gate"`; read the hidden `thread_id` and `request_key` values from the body with a regex; POST /clarify with `action=accept` and `answer.q1=ANSWER` → body HAS `class="approval-gate"` and no `action="/clarify"`; `injected_store.rows == []` (answering is not approving). Why the gate is the expected next screen (grounded fact "Measured post-answer routing, DESK path"): the resume path runs no model — the re-match returns `matched` with the hypoglycaemia id, the offline `default_plan` finishes, the scorer gives RED and confidence `deliver`, so the run pauses at the approval interrupt. The assertion stays exact (gate required): the path is deterministic, so a missing gate is a regression to investigate, not flakiness to tolerate.
    - Desk online, decline: same submission, POST /clarify with `action=decline` → no `class="approval-gate"` in the body (measured: confidence `clarify` → the v1.2 bounded-clarification terminal) and `injected_store.rows == []`.
    - tests/test_desk.py: both strict `_resume` stubs accept `wrap_tools: Any = None`; the accept test additionally asserts the recorded `wrap_tools is with_live_clarification`.
  </behavior>
  <action>
Write the tests first (RED), then implement.

1. src/triagedesk/durable.py — `resume_thread` gains keyword `wrap_tools: Callable[[dict[str, Any]], dict[str, Any]] | None = None`. After building `offline_tools(CaseInput(), UsageRecorder())`, apply `wrap_tools` when given, then call `resume_paused` as today. Docstring: an injected tool-map decorator (SOLID D) — a surface that may have paused at a question passes the adapter seam so the re-executed question node reaches the real tool (LangGraph re-runs the interrupted node on resume; the in-process tool would answer `unavailable` and silently drop the answer). durable.py gains no import of the MCP package (TID251 bans it here; the seam is injected). `resume_paused` and every other function are unchanged.

2. src/triagedesk/desk/pipeline.py
   - `_tools_for`: when `extraction is not None` (online — the model planner may ask), lazily import the seam and return it applied to `online_tools(case, extraction, recorder)`; the offline branch is byte-for-byte unchanged (offline_tools; the deterministic planner never asks). Update its docstring and fix the stale "six other tools" wording to eight.
   - `answer_clarification`: pass `wrap_tools=` the seam (lazy import) to `resume_thread`. Docstring: /clarify is reachable only for a paused question, and only the adapter-backed tool consumes the answer when the node re-executes; the seam loads nothing unless that tool is called. `decide` is unchanged (resuming at the gate re-executes no question).
   - The desk package still imports no commit path (`tests/test_desk.py::test_no_self_commit_path_in_the_desk_package`).

3. src/triagedesk/cli.py (moved here from Task 1 — this task owns every CLI edit). Every new import stays lazy inside `main`/`_resume_policy`, after `harden_offline()`; never at module level (`tests/test_observability.py` forbids the CLI module pulling langchain/mcp).
   - Refactor `_resume_policy`'s elicitation branch to `return resume_with_answers(payload, args.answer or [])` (Task 1's shared helper). Behaviour for the existing tests is identical; an all-blank `--answer` now declines instead of sending an empty accept.
   - Demo parser: add `--answer` (`dest="answers"`, `action="append"`, `default=None`, `metavar="ANSWER"`), help: one answer per question of the agent, in question order (repeatable); online only; with none, an interactive terminal is asked and anything else declines. Dispatch passes `answers=args.answers` to `run_demo`.
   - `resume` branch: lazily import the seam and pass `wrap_tools=` it to `resume_thread`, so `triagedesk resume --answer` answers a question paused by the online desk through the real tool. Update the module docstring's resume sentence.

4. Tests: append the tests from `<behavior>` to tests/test_live_clarification.py; update the two strict stubs in tests/test_desk.py. Do not edit tests/test_desk_online.py or tests/test_durable_cli.py.

Ground it once by hand if Ollama is up (optional, not a gate): `uv run triagedesk desk --online`, submit the E-09 vitals with complaint `known diabetic, feeling unwell`, see the question panel, answer, see the gate; Ctrl-C; `rm -f spans.jsonl checkpoints.db` only if this run created them (check `git status` first — never delete a pre-existing tracked/ignored checkpoint file you did not create).
  </action>
  <verify>
    <automated>rm -f spans.jsonl && uv run pytest -q tests/test_live_clarification.py tests/test_desk_online.py tests/test_desk.py tests/test_durable_cli.py tests/test_graph_durable.py tests/test_review_runbook.py tests/test_readme_runbook.py tests/test_observability.py tests/test_demo.py && uv run ruff check</automated>
    <automated>test "$(grep -c 'wrap_tools' src/triagedesk/durable.py)" -ge 2   # [HEAD=0 EXPECT>=2 @2028403]</automated>
    <automated>test "$(grep -c 'from triagedesk.mcp' src/triagedesk/durable.py)" -eq 0   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: importing the seam into durable instead of injecting it]</automated>
    <automated>test "$(grep -c 'with_live_clarification' src/triagedesk/desk/pipeline.py)" -ge 2   # [HEAD=0 EXPECT>=2 @2028403]</automated>
    <automated>test "$(grep -c 'wrap_tools' src/triagedesk/cli.py)" -ge 1   # [HEAD=0 EXPECT>=1 @2028403]</automated>
    <automated>test "$(grep -c 'resume_with_answers' src/triagedesk/cli.py)" -ge 1   # [HEAD=0 EXPECT>=1 @2028403]</automated>
    <automated>test "$(grep -c 'dest="answers"' src/triagedesk/cli.py)" -eq 1   # [HEAD=0 EXPECT==1 @2028403]</automated>
    <automated>d=$(git diff --name-only -- tests/test_desk_online.py tests/test_durable_cli.py) && test -z "$d"   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: spreading the new tests back across extra test modules]</automated>
    <automated>test "$(grep -rn 'with_live_clarification' src/triagedesk/evals/ | wc -l)" -eq 0   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: passing the seam to the eval runner's build_tools]</automated>
    <automated>test "$(uv run mypy src/triagedesk/durable.py src/triagedesk/desk/pipeline.py src/triagedesk/cli.py 2>&1 | grep -cE '^src/triagedesk/(durable|desk/pipeline|cli)\.py:[0-9]+: error')" -eq 0   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: an untyped wrap_tools parameter or seam call]</automated>
  </verify>
  <done>`demo --answer` drives the online `clarify` beat and a non-TTY run without it declines; `_resume_policy` shares `resume_with_answers` with the demo; an online desk submission that the planner asks about renders the existing question panel; /clarify accept resumes the same run to the approval gate and decline to a no-gate terminal, writing no row either way; `triagedesk resume --answer` and /clarify both reach the real tool on node re-execution (proved end-to-end over a real checkpoint file); durable.py injects rather than imports the seam; offline desk and eval paths unchanged; ruff clean; no new mypy errors.</done>
</task>

<task type="auto">
  <name>Task 3: Live verification with the local model, then honest docs from the real output</name>
  <files>docs/DEMO.md, docs/DESK.md, docs/MCP.md, STATUS.md, README.md</files>
  <read_first>docs/DEMO.md lines 1-62 and 149-176 and 250-276, docs/DESK.md lines 60-93, docs/MCP.md lines 296-385, STATUS.md lines 120-128 and 244-250 and 266-271, README.md lines 274-284, tests/test_demo_runbook.py, tests/test_desk_runbook.py lines 116-130</read_first>
  <action>
1. LIVE RUN FIRST (Ollama is up; the default model is pulled). Run, with a 600 s timeout: `uv run triagedesk demo --online --beat clarify --answer "low glucose, 2.1 mmol/L" 2>&1 | tee <scratchpad file>`, then `rm -f spans.jsonl`. Keep the full output for the SUMMARY. Confirm on screen: the mode line, `[tool] plan_next_step` proposing the question, the `[elicit]` message + question lines, the `[nurse] q1:` line, `[tool] request_clarification` with an accepted outcome, a second `[tool] match_discriminators` whose complaint carries the answer and whose matched ids are non-empty, the colour, and `commit : committed …`. If the model does NOT propose the question (no `[elicit]` line), rerun up to two more times and record every attempt verbatim in the SUMMARY — never edit output, never fake an elicitation, and report it if it never asks. Also run `uv run triagedesk demo --online --beat clarify < /dev/null` once to show the non-interactive decline path, then `rm -f spans.jsonl`.

2. docs/DEMO.md (transcribe from the real output above; never hand-write a model line)
   - Line ~56: update the beat count in the sentence that opens the paragraph after the one-command block to six beats, and add one sentence: offline, the `clarify` beat shows the same E-09 terminal as `failure` because the deterministic planner never asks — the question appears only `--online`.
   - Lines ~171-172: replace the sentence that says no beat reaches `request_clarification` with: offline the run shows eight of the nine owned tools; `request_clarification` appears when the online planner chooses to ask — the `clarify` beat (see the new section).
   - Add a new section `## Live final: the agent asks the nurse (online clarify beat)` (before `## The desk surface`). Contents: a fenced block with the interactive command (`uv run triagedesk demo --online --beat clarify`, presenter types the answer at each `[nurse] q1>` prompt; Enter on every prompt = decline) and the rehearsal command with `--answer "low glucose, 2.1 mmol/L"` (repeatable, question order); an excerpt of the real run's `[elicit]` / `[nurse]` / `[tool] request_clarification` / second `match_discriminators` / outcome lines, labelled with the date and model tag and "the model decides whether to ask; temperature 0, so runs repeat, but it is a model"; how it works in one paragraph (the run pauses INSIDE the MCP tool call — a real `mcp_elicitation` interrupt from the shipped adapter, in process — the answer resumes the same run); the safety rules (the answer is an observation re-matched by the deterministic matcher; the colour is `score_priority`'s; the commit still needs the named approval — the demo's synthetic nurse; a decline or blank answer records nothing; a non-interactive run without `--answer` declines and never waits); the alias-matching caveat stated plainly (matching is alias text from `data/sats_discriminators.yaml` — an answer naming the finding, like "low glucose", resolves it; a bare number such as "glucose 2.1" is recorded but matches nothing, so the case stays unresolved and defers; there is no number parsing); why `DECLARED` is printed without a verdict on an answered run (the eval expectation is for the note alone); and that the batch eval (`triagedesk eval`) has no human to answer, so it keeps the in-process tool, records `unavailable` whenever its planner asks, and its sealed reports are unchanged by this beat — no new eval numbers are claimed. Note `--durable` does not ask (the two-command story keeps the in-process tool).
   - Do not change the recorded-video statements (they are historical) or the `failure` beat's transcribed block.

3. docs/DESK.md — after the "one bounded question" paragraph (~line 78-81) add one paragraph: with `--online`, the agent itself may ask mid-run — the page pauses on a question panel showing the questions the server derived, one field each, and a "Decline to answer" control, with no decision controls; answering resumes the same case and the next screen is the approval gate (or, if the answer resolves nothing, the case stays unresolved); declining adds nothing; answers are matched as text (name the finding, e.g. "low glucose" — a bare number is not matched); offline never asks. Name NO underscore-bearing graph identifier and no thread-id token (tests/test_desk_runbook.py enforces this).

4. docs/MCP.md — replace the stale "Honest scope" blockquote at ~381-384 (it says the graph does not call the tool yet) with a "Where it runs live" blockquote: the graph's question node calls `request_clarification` when the planner chooses it; the online demo `clarify` beat ([`DEMO.md`](DEMO.md)) and the online desk question panel ([`DESK.md`](DESK.md)) load the tool through the shipped adapter in process (`mcp/adapter.py`'s seam), so a real `mcp_elicitation` interrupt pauses the run; `triagedesk resume --answer` and the desk's /clarify answer it; the batch eval has no human and records `unavailable`. Keep the test-file references.

5. STATUS.md — §7 G7 (lines ~123-127): append one sentence: exercised live on the online `demo --beat clarify` and the online desk question panel; the batch eval has no human to answer, so it records `unavailable` (no new measurement claimed). Lines ~248 and ~269: drop elicitation from the slash-joined "sampling and elicitation" pairs so each names only sampling (G7 already says elicitation is closed). README.md line ~282: the future-work bullet that pairs sampling with elicitation becomes MCP sampling only, with a parenthetical that elicitation ships (link docs/DEMO.md). Touch nothing else in README/STATUS; quote no eval figure.

6. Finish: `rm -f spans.jsonl`, then the full suite, ruff, and `scripts/emit_evals.py --check`. Never stage untracked `docs/assets/*` files.
  </action>
  <verify>
    <automated>if curl -s -m 3 http://127.0.0.1:11434/api/tags >/dev/null; then out=$(mktemp); timeout 600 uv run triagedesk demo --online --beat clarify --answer "low glucose, 2.1 mmol/L" > "$out" 2>&1; grep -q '^\[elicit\]' "$out" && grep -q '^\[nurse\] q1: ' "$out" && grep -q '^\[tool\] request_clarification' "$out" && grep -q 'commit       : committed' "$out"; rc=$?; cat "$out"; rm -f "$out" spans.jsonl; test $rc -eq 0; else echo "SKIP: Ollama not running"; fi</automated>
    <automated>rm -f spans.jsonl && uv run pytest -q tests/test_demo_runbook.py tests/test_desk_runbook.py tests/test_mcp_runbook.py tests/test_docs_final.py tests/test_readme_runbook.py && uv run python scripts/emit_evals.py --check</automated>
    <automated>test "$(grep -c -- '--beat clarify' docs/DEMO.md)" -ge 2   # [HEAD=0 EXPECT>=2 @2028403 (Task 1 adds 1)]</automated>
    <automated>test "$(grep -c 'unavailable' docs/DEMO.md)" -ge 1   # [HEAD=0 EXPECT>=1 @2028403]</automated>
    <automated>test "$(grep -c 'all five beats' docs/DEMO.md)" -eq 0   # [HEAD=1 EXPECT==0 @2028403]</automated>
    <automated>test "$(grep -c 'no storyboard beat does' docs/DEMO.md)" -eq 0   # [HEAD=1 EXPECT==0 @2028403]</automated>
    <automated>test "$(grep -ci 'question panel' docs/DESK.md)" -ge 1   # [HEAD=0 EXPECT>=1 @2028403]</automated>
    <automated>test "$(grep -c 'no shipped graph node calls' docs/MCP.md)" -eq 0   # [HEAD=1 EXPECT==0 @2028403]</automated>
    <automated>test "$(grep -c 'MCP sampling / elicitation' README.md)" -eq 0   # [HEAD=1 EXPECT==0 @2028403]</automated>
    <automated>test "$(grep -c 'sampling/elicitation' STATUS.md)" -eq 0   # [HEAD=2 EXPECT==0 @2028403]</automated>
    <automated>d=$(git diff --name-only -- evals/results/) && test -z "$d"   # [HEAD=0 EXPECT==0 @2028403 GUARD MUTATION: re-running or editing the sealed eval reports]</automated>
    <automated>rm -f spans.jsonl && uv run pytest -q && uv run ruff check && test ! -e spans.jsonl</automated>
    <human-check>In a real terminal: `uv run triagedesk demo --online --beat clarify`, type an answer naming the finding at the `[nurse] q1>` prompt and press Enter on the rest; the run re-matches, shows a colour and commits under the demo nurse. Then `uv run triagedesk desk --online`, submit the E-09 vitals with complaint `known diabetic, feeling unwell`, answer the question panel, and confirm the approval gate appears. `rm -f spans.jsonl` afterwards.</human-check>
  </verify>
  <done>A real online run shows the agent asking through MCP, the nurse's answer, the re-match, a colour and the gated commit — its output is recorded verbatim in the SUMMARY (or, if the model never asks, every attempt is recorded and reported). DEMO.md documents the live beat, the alias caveat and that the batch eval still records `unavailable`; DESK.md says the question panel is reached online; MCP.md's stale scope note is replaced; STATUS/README no longer list elicitation as future work and quote no new figure; the full suite, ruff and `emit_evals.py --check` are green; `evals/results/` untouched; no `spans.jsonl` at the root.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| presenter / nurse free text → graph state | a typed answer enters `nurse_answers` and the matcher's complaint text; it must never become a colour, a decision or a queue write |
| in-process MCP client ↔ owned server | the adapter session (in-memory transport) carries the question out and the answer back; failures must surface, never become answers |
| desk POST /clarify (loopback) → durable resume | an HTTP form resumes a paused question; the existing CSRF / same-origin / body-cap preamble applies |
| CLI stdin → demo | a TTY read during a live run; a non-interactive run must not hang |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-jlr-01 | Elevation of privilege | demo/desk answer → colour / gate | high | mitigate | The answer reaches the graph only through `ask_question` (appends to `nurse_answers`) and the deterministic matcher; the colour is `score_priority(case, matched_ids)`; the approval is a separate interrupt answered only by the beat's named decision. Tests: colour equals score_priority over the final ids; a run whose policy declines to answer the gate stays paused with no row; desk /clarify writes no row. |
| T-jlr-02 | Repudiation | decline / blank input | medium | mitigate | `resume_with_answers` declines when no non-blank answer exists; Enter-only, EOF and non-TTY-without-`--answer` all decline and print one explicit "nothing is recorded" line. Tests: decline → no `nurse_answers`, ids unchanged, no row. |
| T-jlr-03 | Denial of service | demo stdin read | medium | mitigate | `input()` only when online AND `sys.stdin.isatty()` AND no `--answer`; EOF → blank. Tests: CLI run under non-TTY stdin returns 0 without waiting; bare offline demo with `< /dev/null` runs six beats. |
| T-jlr-04 | Information disclosure / Tampering | seam scope | medium | mitigate | `with_live_clarification` replaces exactly one key and never exposes the adapter's full tool list (which includes the gated commit); test asserts every other value is the same object. |
| T-jlr-05 | Tampering | eval harness / sealed reports | high | mitigate | The seam is opt-in per surface; `evals/` never references it (grep gate); `emit_evals.py --check` exits 0; `evals/results/` diff is empty. |
| T-jlr-06 | Tampering | durable resume of a question | high | mitigate | `resume_thread(wrap_tools=…)` lets the desk and CLI inject the seam, so the re-executed question node consumes the answer instead of answering `unavailable`; proved end-to-end over a real checkpoint file. durable.py imports no MCP module (TID251 + grep gate). |
| T-jlr-07 | Spoofing | on-screen elicitation lines | low | mitigate | Question text, message and tool name are read from the payload the adapter minted (question text from `core.coverage.question_for`); the demo authors no question and no tool name. |
| T-jlr-08 | Denial of service | in-process adapter failure | low | accept | A discovery/transport failure raises (no try/except around the tool call), so the run fails loudly rather than inventing an answer — a demo crash is preferable to a fabricated clinical fact. |
| T-jlr-SC | Tampering | npm/pip/cargo installs | high | accept | No package is installed or upgraded: `langchain[mcp]`, `fastmcp` and `mcp` are already exact-pinned in `uv.lock`; the plan adds no dependency. |
</threat_model>

<verification>
- `uv run pytest -q` green (baseline 904 collected, plus the new tests); `uv run ruff check` clean; no new mypy errors in touched src files.
- `uv run python scripts/emit_evals.py --check` exits 0 and `git diff --name-only -- evals/results/` is empty.
- `MCPAdapter` still imported only in `src/triagedesk/mcp/adapter.py`; `src/triagedesk/evals/` never references the seam; durable.py imports no MCP module.
- Live: `uv run triagedesk demo --online --beat clarify --answer "low glucose, 2.1 mmol/L"` shows `[elicit]`, `[nurse] q1:`, `[tool] request_clarification`, the re-match, a colour and the gated commit — output recorded in the SUMMARY.
- No `spans.jsonl` at the repo root; no untracked `docs/assets/*` staged.
</verification>

<success_criteria>
- A judge watching `uv run triagedesk demo --online --beat clarify` sees the agent pause inside an MCP tool call, ask the nurse the server's own question, take her answer, re-match, score and commit only under the named approval.
- The online desk reaches its existing question panel and /clarify resumes to the gate; offline desk and demo behaviour (other than the additive beat) are unchanged.
- Every safety invariant (answer = observation, decline = nothing, gate needs a named approval, guard unchanged, eval untouched) is enforced by an offline test that needs no Ollama.
- Docs describe exactly what runs, state the alias-matching caveat and the eval's `unavailable`, and claim no new numbers.
</success_criteria>

<output>
Create `.planning/quick/261115-jlr-live-mcp-elicitation-in-the-demo-and-des/261115-jlr-SUMMARY.md` when done, including the verbatim live `--online --beat clarify` output (every attempt) and the non-interactive decline run.
</output>
