---
phase: 21
phase_name: "MCP elicitation end-to-end — request_clarification asks mid-call"
verified_at: "2026-11-14"
verifier: gsd-executor
status: passed
covered_files:
  - src/triagedesk/core/schema.py
  - src/triagedesk/mcp/elicitation.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/durable.py
  - src/triagedesk/cli.py
  - src/triagedesk/desk/clarification.py
  - src/triagedesk/desk/views.py
  - src/triagedesk/desk/pipeline.py
  - src/triagedesk/desk/server.py
  - src/triagedesk/desk/copy.py
covered_digest: "v4:sha256:b5a26c44c6ef67c8445611952fab8e25d4f29c966dbd4397b10640b9ac21d00a"
commands:
  - "uv run pytest -q -> 836 passed"
  - "uv run ruff check src tests -> All checks passed"
  - "uv run mypy src -> 29 errors in 6 files (baseline 30; no new errors, none in a phase file)"
---

# Phase 21 Verification

## Gate results

| Gate | Command | Result |
| --- | --- | --- |
| Tests | `uv run pytest -q` | **836 passed** (Phase 20 left 812; +24) |
| Lint | `uv run ruff check src tests` | clean |
| Types | `uv run mypy src` | 29 errors, all pre-existing (baseline 30) — none in a file this phase touched |

The mypy error set is confined to `core/rules.py`, `demo/run.py`, `graph/build.py`,
`graph/nodes.py`, `graph/state.py` and `mcp/adapter.py`; the phase's own modules
(`mcp/server.py`, `mcp/elicitation.py`, `durable.py`, `cli.py`, `desk/**`) contribute zero.

## Requirement → evidence

| Requirement | Verdict | Evidence |
| --- | --- | --- |
| **ELICIT-01** — a new owned tool `request_clarification` elicits a typed answer mid-call for at most three targeted questions; read-only, no token, no queue row | met | `mcp/server.py::request_clarification` registered ninth; `tests/test_elicitation_tool.py::test_the_first_round_returns_a_spec_valid_form_of_derived_questions`, `::test_more_than_three_candidates_are_trimmed_to_the_one_bound`; `tests/test_safety_spine.py::test_graph_startup_asserts_the_tool_allowlist` (nine names) |
| **ELICIT-02** — the round trip works through the shipped adapter, not a stub: call → `interrupt()` → resume → the tool returns the answer | met | `tests/test_elicitation_roundtrip.py::test_the_real_adapter_pauses_then_returns_the_accepted_answer` — the real `langchain.mcp.MCPAdapter` over the real `MCPServer`, in process, over a real checkpointer |
| **ELICIT-03** — four distinct outcomes; only `accepted` carries an answer; a refusal is never a value | met | `core/schema.py::ClarificationAnswer._only_an_acceptance_carries_answers` (structural); `tests/test_elicitation_tool.py` accepted/declined/cancelled/unavailable cases; `tests/test_elicitation_roundtrip.py::test_a_refusal_returns_no_answers_and_writes_no_queue_row` |
| **ELICIT-04** — the allowlist fan-out moves in one atomic change and still fails closed | met | `graph/build.py::OWNED_TOOL_ALLOWLIST` (9) + `evals/tools.py` + `tests/conftest.py` + `tests/test_safety_spine.py`, all in commit `5c9f961`; the missing/unexpected assertions still raise |
| **ELICIT-05** — the desk and CLI present an elicitation distinctly from the gate, and neither can commit from it | met | `core/schema.py::InterruptType`; `graph/nodes.py` payload `type=approval`; `tests/test_durable_cli.py::test_resume_policy_*`; `tests/test_desk.py::test_elicitation_payload_renders_the_question_panel_not_the_gate`, `::test_the_clarification_module_reaches_no_commit_path`; `durable.py` default policy stops at a question |
| **ELICIT-06** — every question traces to a loaded definition, never authored | met | `mcp/server.py::_clarification_questions` calls `coverage.question_for` only; the round-trip test asserts each schema `description` equals `coverage.question_for(id)` verbatim; an unknown id is skipped (`tests/test_elicitation_tool.py`) |
| **ELICIT-07** — resuming is idempotent: no duplicate queue commit, an answered question is not asked twice | met | `tests/test_elicitation_roundtrip.py::test_resuming_an_answered_thread_does_not_re_ask_or_re_write`; the content-hash queue key is unchanged (`tests/test_commit_idempotent.py` still green) |
| **ELICIT-08** — an answer is an observation, never an approval: appended to facts only, never past the gate, never a colour | met | `ClarificationAnswer` has `extra="forbid"` and no clinical field; the desk `/clarify` resumes with a `None` policy so the gate stays pending (`tests/test_desk.py::test_answering_a_clarification_never_sends_a_decision`); `durable.resume_paused` returns the still-paused state |

## Invariants re-checked (unchanged by this phase)

| Invariant | Evidence |
| --- | --- |
| `commit_priority` remains the only queue-affecting tool | `tests/test_safety_spine.py`, `tests/test_commit_idempotent.py` green; no new write path added |
| The approval gate still needs a named clinician | `tests/test_graph_durable.py` approve/edit/dismiss suites green |
| The colour is still produced in exactly one place | `core/scorer.py` and `core/citations.py` untouched (`git diff 1cea0b4..HEAD --name-only` excludes them) |
| The `@audited` interceptor is untouched | same check; `mcp/server.py` only adds a tool, never edits `audited` |
| SATS values only from `data/*.yaml` | `tests/test_no_duplicated_sats.py` green |
| The nine-tool count stays honest | README/ARCHITECTURE/SECURITY/STATUS still say 7 shipped + 2 proposed; `docs/MCP.md` and the skill name all nine and mark the two substrate tools unwired |

## Known gaps (carried forward, not regressions)

1. No shipped graph node calls `request_clarification` yet — Phase 23 wires the `plan` node. The
   adapter round trip is proved around a two-node harness containing the real tool.
2. The legacy `ctx.elicit` branch is proved with a fake `Context`, not a legacy client: the shipped
   adapter negotiates 2026-07-28.
3. `@audited` writes one record per interrupt round (the interceptor is out of scope to edit), and the
   record carries the injected `ctx` as `{}`.
