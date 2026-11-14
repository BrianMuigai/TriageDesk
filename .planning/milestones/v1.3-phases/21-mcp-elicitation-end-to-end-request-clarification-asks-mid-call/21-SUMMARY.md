---
phase: 21
phase_name: "MCP elicitation end-to-end — request_clarification asks mid-call"
subsystem: mcp
tags: [elicitation, mcp, langgraph, interrupt, cli, desk, dry, solid]
requires:
  - "Phase 20 (the planner substrate: allowlist fan-out pattern, the ninth-tool precedent)"
  - "the shipped adapter langchain.mcp.MCPAdapter (World A)"
provides:
  - "the ninth owned tool request_clarification (read-only, question-derived, four outcomes)"
  - "core.schema.InterruptType / ElicitationOutcome / ClarificationAnswer"
  - "mcp.elicitation — the ONE elicitation wire vocabulary"
  - "durable.RespondPolicy + the ONE interrupt loop"
  - "triagedesk resume --answer and the desk question panel"
affects:
  - "Phase 23: the plan node will call request_clarification and make the surfaces reachable in a real run"
tech-stack:
  added: []
  patterns:
    - "input-required round trip (2026-07-28) with a legacy ctx.elicit fallback behind one outcome mapper"
    - "one interrupt loop behind an injectable policy; None means 'leave it paused for a human'"
key-files:
  created:
    - src/triagedesk/mcp/elicitation.py
    - src/triagedesk/desk/clarification.py
    - tests/test_elicitation_tool.py
    - tests/test_elicitation_roundtrip.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/durable.py
    - src/triagedesk/cli.py
    - src/triagedesk/evals/tools.py
    - src/triagedesk/desk/views.py
    - src/triagedesk/desk/pipeline.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/copy.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - tests/conftest.py
    - tests/test_safety_spine.py
    - tests/test_graph_durable.py
    - tests/test_durable_cli.py
    - tests/test_desk.py
    - docs/MCP.md
    - src/triagedesk/skills/triagedesk-triage/SKILL.md
    - src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md
    - pyproject.toml
decisions:
  - "the 2026-07-28 transport forbids a server-initiated request, so the tool asks over the input-required round trip and keeps ctx.elicit for an older connection"
  - "InterruptType lives in core.schema so the graph never imports mcp and the discriminator has one home"
  - "the default respond policy answers an approval and stops at a question — no existing caller changes"
  - "only `accepted` can carry an answer, structurally: the contract rejects answers on a refusal"
  - "the surfaces cannot commit from an answer: the desk's /clarify resumes with a stop policy and the panel has no decision control"
metrics:
  duration: "~2 h"
  completed: "2026-11-14"
  tasks: 16
  files: 26
commits: 3
plan_head_before: 1cea0b4c26063395489ccad878a13189281f6215
plan_head_after: 9c512ac
actuals:
  tokens: 30869
  tasks: 16
  commits: 3
status: complete
---

# Phase 21: MCP elicitation end-to-end — `request_clarification` asks mid-call — Summary

**One-liner:** the owned server genuinely asks the nurse a bounded, data-sourced question *inside* a
tool call, the shipped adapter turns it into a LangGraph `interrupt()`, and all four outcomes are
distinguished with a refusal never treated as an answer.

## What shipped

### The tool (ELICIT-01, ELICIT-06, ELICIT-08)

`request_clarification(candidates, ctx)` is the ninth owned tool. Read-only — no store, no queue row,
no approval token — and its contract has no colour/priority/target field, so an answer is
*unrepresentable* as a clinical decision. It takes **closed-set discriminator ids only** and derives
at most three questions from `core.coverage.question_for`, the ONE owner of question text, so a caller
cannot author a question and a question that does not trace to a loaded definition is not asked. The
form is a dynamically built, spec-valid `create_model` rendered through
`render_elicitation_schema` — one flat `string` property per question.

### The round trip (ELICIT-02, ELICIT-03)

Proved through the **real shipped adapter** (`langchain.mcp.MCPAdapter`) against the real owned
`MCPServer`, in process, over a real LangGraph checkpointer: tool call → `interrupt(type:
"mcp_elicitation")` → resume with `{"responses": …}` → the tool returns the answer. Four outcomes —
`accepted` (the only one carrying answers), `declined`, `cancelled`, `unavailable` — with a refusal
returning `answers == []` and writing no queue row. A transport failure that is not a capability or
back-channel problem **propagates** rather than becoming an answer.

### The discriminator and the loop (ELICIT-05, ELICIT-07)

`core.schema.InterruptType` declares `approval` and `mcp_elicitation` once; `approval_gate`'s payload
now carries `type: "approval"` (additive). `durable` owns ONE interrupt loop behind an injectable
`RespondPolicy`; the default answers an approval and **stops** at a question, so every pre-existing
caller is unchanged and an approval token can never answer a question. Resuming is idempotent: an
answered question is not asked twice, and the queue write stays keyed on the case content hash.

### The surfaces (ELICIT-05, ELICIT-08)

`triagedesk resume` takes repeatable `--answer` and declines by default; `--decision` is required only
when an approval is actually pending, and a still-paused resume says "nothing has been committed". The
desk renders a **question panel** — the derived questions, one free-text field each, a decline
control — instead of the approval gate, with no decision field, no colour control and no commit path;
`POST /clarify` resumes through the same gated plumbing and then shows whatever comes next as itself.

### The allowlist (ELICIT-04)

The nine-name surface moved in one atomic change across the server, the graph allowlist, the eval fake,
the conftest graph fake and the exact-set assertion. The assertion still fails closed on a missing or
unexpected tool.

## Requirements coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| ELICIT-01 | met | `request_clarification` registered as the ninth tool; read-only contract; `tests/test_elicitation_tool.py` |
| ELICIT-02 | met | real `MCPAdapter` round trip in `tests/test_elicitation_roundtrip.py` |
| ELICIT-03 | met | four outcomes, only `accepted` carries answers, structurally enforced in `core.schema`; tool + round-trip tests |
| ELICIT-04 | met | allowlist 8 → 9 atomically; `tests/test_safety_spine.py` exact-set assertion |
| ELICIT-05 | met | `InterruptType` + distinct payloads; CLI policy tests and desk panel tests |
| ELICIT-06 | met | questions derived from `coverage.question_for`, asserted verbatim against the form schema |
| ELICIT-07 | met | idempotent resume test; content-hash queue write unchanged |
| ELICIT-08 | met | `extra="forbid"`, no clinical field, refusal-cannot-carry-answers validator; desk no-commit-path module test |

## Deviations (phase level)

1. **`ctx.elicit` is not usable on the installed SDK's modern era.** The context document specified
   `await ctx.elicit(...)`; on 2026-07-28 the transport has no back-channel for a server-initiated
   request. The tool therefore uses the spec-valid input-required round trip on that revision and
   keeps `ctx.elicit` for an older connection. Both share one derivation and one outcome mapper.
2. **`durable.resume_paused` semantics.** An explicit `decision` answers the *pending* payload; the
   policy answers whatever follows — required so a surface can answer a question and leave the gate
   pending. Documented in the helper and covered by tests.
3. **`pyproject.toml` gained a TID251 exception for `cli.py`** — the outermost layer legitimately
   reaches the seams, exactly as `replay.py`, `desk/**` and `demo/**` already do.

## Honest gaps

- **No shipped graph node calls the tool yet.** Phase 23 wires the `plan` node. The adapter round-trip
  is proved against a two-node harness around the real tool, and the CLI/desk elicitation paths are
  proved at the policy and surface layer. The docs and the tool docstring say so.
- **The legacy `ctx.elicit` branch is unit-tested with a fake context, not a legacy client.** The
  shipped adapter negotiates 2026-07-28, so the back-channel branch has no end-to-end harness; its
  four outcomes are proved through the fake.
- **`@audited` records every interrupt round.** The interceptor is out of scope to edit, so an
  elicitation that pauses produces audit records for the interrupted attempt as well as the completed
  call. Honest, but noisier than one record per logical call.
- **The audit record carries the injected `ctx`** as `{}` (the production `Context` dumps to an empty
  mapping). Harmless, but it is not information a reviewer needs.

## Commits

| Hash | Plan | Subject |
| --- | --- | --- |
| `5c9f961` | 21-01 | feat(21-01): add the ninth owned tool request_clarification |
| `7bb7f68` | 21-02 | feat(21-02): prove the elicitation round-trip through the shipped adapter |
| `9c512ac` | 21-03 | feat(21-03): present the mid-call question as a question, never a gate |

`commits: 3` is measured: `git rev-list --count 1cea0b4..HEAD`.
