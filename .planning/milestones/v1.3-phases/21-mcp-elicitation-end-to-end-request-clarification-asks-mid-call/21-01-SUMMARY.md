---
phase: 21
plan: "01"
subsystem: mcp
tags: [mcp, elicitation, schema, allowlist, dry, solid]
requires:
  - "core.coverage.question_for (the ONE owner of question text)"
  - "core.schema (the ONE contract module)"
  - "graph/build.OWNED_TOOL_ALLOWLIST (the ONE allowlist)"
provides:
  - "core.schema.InterruptType / ElicitationOutcome / ClarificationAnswer"
  - "mcp.elicitation (the ONE elicitation wire vocabulary)"
  - "mcp.server.request_clarification (the ninth owned tool)"
affects:
  - "Phase 23 (the plan node will call request_clarification)"
tech-stack:
  added: []
  patterns:
    - "a data-driven pydantic create_model form rendered through render_elicitation_schema"
    - "one private transport branch: input-required round trip (2026-07-28) | legacy ctx.elicit"
key-files:
  created:
    - src/triagedesk/mcp/elicitation.py
    - tests/test_elicitation_tool.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/evals/tools.py
    - tests/conftest.py
    - tests/test_safety_spine.py
    - docs/MCP.md
    - src/triagedesk/skills/triagedesk-triage/SKILL.md
    - src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md
decisions:
  - "InterruptType is declared in core.schema (not mcp/) so the graph never imports mcp and the literal has one home"
  - "the tool asks over the input-required round trip on 2026-07-28 and ctx.elicit on an older connection; one outcome mapper serves both"
  - "zero known candidates returns `unavailable` (nothing was elicited), never an answer"
  - "a blank answer field is dropped: an empty string is not an observation"
metrics:
  duration: "~35 min"
  completed: "2026-11-14"
  tasks: 6
  commits: 1
  files: 12
status: complete
---

# Phase 21 Plan 01: The ninth owned tool — `request_clarification` Summary

One narrow, read-only owned tool asks the nurse at most three questions **inside** a tool call and
returns a typed four-outcome answer, with the owned surface grown 8 → 9 in a single atomic change.

## What was built

**Contracts (`core/schema.py`).** `InterruptType` names the two interrupt discriminators
(`approval` / `mcp_elicitation`) once, in the pure contract module — so `graph/nodes.py`, `durable`,
the CLI and the desk compare against a member instead of repeating a literal, and the graph never
imports `triagedesk.mcp`. `ElicitationOutcome` is the closed four-way answer. `ClarificationAnswer`
carries `outcome`, `answers` and `reason`, declares `extra="forbid"`, and a `model_validator` rejects
answers on any outcome other than `accepted` — a decline can never be constructed as a clinical fact.

**Wire vocabulary (`mcp/elicitation.py`, new).** The one home for the request key
(`clarification`), the answer field names (`q1..qN`), the `{"responses": …}` resume-value builders,
and `is_elicitation`. Dependency-light by design: no `server`, `store` or `llm` import, so the desk's
no-commit-path guard still holds and the CLI path emits no `langchain.mcp` beta warning.

**The tool (`mcp/server.py`).** `request_clarification(candidates, ctx)` derives at most
`coverage.MAX_CLARIFICATION_QUESTIONS` questions from `coverage.question_for` — the ONE owner of
question text — skipping an id outside the closed set, builds a spec-valid `create_model` form
rendered through `render_elicitation_schema`, and maps the four outcomes. One private `_ask` picks the
transport: the 2026-07-28 **input-required round trip** (the transport forbids a server-initiated
request there) or the legacy `ctx.elicit` back-channel; both feed one mapper. A missing capability or
a connection with no back-channel is `unavailable`; **any other exception propagates**.

**The allowlist fan-out, atomically.** `graph/build.OWNED_TOOL_ALLOWLIST` (nine names), the eval
`_tool_map`, the conftest graph fake (which calls the real tool with `ctx=None`, honestly
`unavailable`) and the exact-set assertion all moved together. No node calls the tool yet.

**Docs.** `docs/MCP.md` gains a `### request_clarification` section and a "How the round-trip works"
subsection; the packaged skill declares the ninth tool, names it in the table and adds the
"answering is not approval" rule.

## Deviations from Plan

### 1. [Rule 1 - Bug] `ctx.elicit()` cannot carry a question on the installed SDK's modern era

- **Found during:** Task 3 (before writing the tool, by probing the installed SDK).
- **Issue:** the plan (from `21-CONTEXT.md`) specified `await ctx.elicit(message, Form)`. On the
  negotiated 2026-07-28 revision the SDK's per-request dispatch context has **no back-channel**, so
  `ctx.elicit` raises `MCPError: Cannot send 'elicitation/create': this transport context has no
  back-channel`. A spike confirmed it, and confirmed that the shipped `langchain.mcp` driver only
  answers `InputRequiredResult` rounds. Implementing `ctx.elicit` alone would have made every call
  `unavailable` and left ELICIT-02 unprovable.
- **Fix:** the tool returns an `InputRequiredResult` carrying one form request on its first round and
  reads `ctx.input_responses` on the retry — the spec-valid modern flow — and keeps `ctx.elicit` for
  an older connection, which does have a back-channel. Both paths share one question derivation and
  one outcome mapper.
- **Files modified:** `src/triagedesk/mcp/server.py`
- **Commit:** 5c9f961

### 2. [Rule 2 - Missing critical functionality] a blank answer was reaching the contract

- **Found during:** Task 3.
- **Issue:** the legacy path hands back a validated form model, and the modern path a mapping; a
  naive read would either miss the model or carry `""` as an observation.
- **Fix:** `_answers` accepts both shapes and drops blank/whitespace values — an untouched input is
  an unanswered question, not a finding.
- **Files modified:** `src/triagedesk/mcp/server.py`
- **Commit:** 5c9f961

### 3. [Rule 3 - Blocking] mypy `no-any-return` on `create_model`

- **Found during:** the plan's verification step.
- **Issue:** `create_model` returns `Any`, so the helper's `type[BaseModel]` return tripped
  `no-any-return` — a 31st mypy error against the 30-error baseline.
- **Fix:** bind to a typed local and return it. mypy is back to the baseline.
- **Files modified:** `src/triagedesk/mcp/server.py`
- **Commit:** 5c9f961

## Known Stubs

None. The tool is fully implemented and tested; it is *unwired* (no node calls it), which is the
declared scope of Phase 21, not a stub — and it is documented as unwired in the server docstring,
`docs/MCP.md` and the skill.

## Self-Check: PASSED

- `src/triagedesk/mcp/elicitation.py` exists; `request_clarification` is the ninth registered tool.
- Commit `5c9f961` is an ancestor of HEAD.
- `uv run pytest tests/test_elicitation_tool.py -q` → 18 passed.
