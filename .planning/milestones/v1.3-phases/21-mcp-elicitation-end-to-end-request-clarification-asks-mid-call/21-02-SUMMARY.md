---
phase: 21
plan: "02"
subsystem: graph
tags: [elicitation, interrupt, langgraph, adapter, dry, solid]
requires:
  - "mcp.server.request_clarification (21-01)"
  - "core.schema.InterruptType (21-01)"
provides:
  - "graph.nodes.approval_gate payload type=approval"
  - "durable.RespondPolicy / pending_interrupt / _drive (the ONE interrupt loop)"
affects:
  - "Phase 21-03 (the CLI and desk consume the loop)"
  - "Phase 23 (the plan node will elicit before the gate)"
tech-stack:
  added: []
  patterns:
    - "one interrupt loop behind an injectable respond policy; None means 'leave it paused'"
    - "the default policy answers an approval and stops at a question"
key-files:
  created:
    - tests/test_elicitation_roundtrip.py
  modified:
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/durable.py
    - tests/test_graph_durable.py
decisions:
  - "the default respond policy answers an approval and returns None for an elicitation, so no current caller changes and an approval never answers a question"
  - "an explicit `decision` answers the PENDING payload; the policy answers whatever follows — that is what lets a surface answer a question and leave the gate pending"
  - "durable reads InterruptType from core.schema rather than importing triagedesk.mcp (layering + the ruff core-import ban)"
metrics:
  duration: "~30 min"
  completed: "2026-11-14"
  tasks: 4
  commits: 1
  files: 4
status: complete
---

# Phase 21 Plan 02: The interrupt round-trip and the ONE respond loop Summary

The tool's mid-call question becomes a real LangGraph `interrupt()`, one injected policy answers it,
and the whole path is proved through the **shipped adapter** rather than a stub.

## What was built

**A distinguishable approval payload.** `approval_gate` now puts `type: "approval"` first in its
payload, taken from `core.schema.InterruptType`. Additive — every existing reader keeps working — and
it is what lets a surface tell a decision from a question without sniffing keys (ELICIT-05).

**One interrupt loop.** `durable` gained `RespondPolicy` (a payload → resume value, or `None` to leave
the run paused), `pending_interrupt(snapshot)` (the one reader of LangGraph's pending-interrupt shape),
`_approval_only(decision)` (the default policy), and `_drive(...)` (the one loop). `invoke_graph` and
`resume_paused` both drive through it, so the pause/resume mechanics exist once. The default policy
answers an approval and **stops** at an elicitation, so every current caller is byte-for-byte
unchanged and an approval token can never be used to answer a question.

**The end-to-end proof (`tests/test_elicitation_roundtrip.py`).** The real `langchain.mcp.MCPAdapter`
loads the real owned `MCPServer` **in process** (FastMCP accepts an in-process server, so no stdio
subprocess and no borrowed store), and a real two-node LangGraph graph over a real `MemorySaver`
pauses, resumes and completes:

1. the run pauses with `type: "mcp_elicitation"`, `tool_name: "request_clarification"`, one form
   request keyed `clarification`, and a schema whose `q1..qN` descriptions **are**
   `coverage.question_for(id)` verbatim;
2. resuming with `{"responses": {"clarification": {"action": "accept", …}}}` returns
   `ClarificationAnswer(outcome="accepted", answers=[…])` in question order;
3. a decline and a cancel each return `answers == []` and write **no queue row**;
4. a further resume on a settled thread neither re-asks nor re-writes (ELICIT-07);
5. the shipped graph's gate payload is `type: "approval"` — the two types never mix.

**The loop's own contract (`tests/test_graph_durable.py`).** The default policy leaves an elicitation
paused; a policy answers the question then stops at the gate (with the gate still pending); a policy
that answers both reaches the terminal; `pending_interrupt` reads the payload; a `None` policy leaves
the thread paused and writes nothing.

## Deviations from Plan

### 1. [Rule 1 - Bug] the plan's `resume_paused` ordering ignored an explicit decision

- **Found during:** Task 2, while wiring 21-03's desk resume.
- **Issue:** with `respond` given, the first resume went through the policy and the pre-built
  `decision` was ignored — so "answer the question, then present the gate" could not be expressed.
- **Fix:** an explicit `decision` now answers the pending payload; the policy answers any *further*
  payload. Both behaviours are covered by tests.
- **Files modified:** `src/triagedesk/durable.py`
- **Commit:** 9c512ac (the fix landed with the surface that needed it)

### 2. [Rule 3 - Blocking] the core-import ban (TID251) rejected `durable → triagedesk.mcp`

- **Found during:** Task 2 verification.
- **Issue:** `ruff` bans `triagedesk.mcp` outside an explicit per-file allowlist, and `durable.py` is
  not on it. Adding the exception would have widened the layering rule for a single constant.
- **Fix:** `durable` compares `payload.get("type")` against `core.schema.InterruptType.ELICITATION`
  — the same single declaration — so no new import edge and no config exception.
- **Files modified:** `src/triagedesk/durable.py`
- **Commit:** 7bb7f68

## Known Stubs

None.

## Self-Check: PASSED

- `tests/test_elicitation_roundtrip.py` exists; commit `7bb7f68` is an ancestor of HEAD.
- `uv run pytest tests/test_elicitation_roundtrip.py tests/test_graph_durable.py -q` → 15 passed.
