---
phase: quick
plan: "261104-ueu"
subsystem: graph
tags: [handover, approval-gate, commit, verify, quick]

# Dependency graph
requires: []
provides:
  - "CommitResult.colour: str | None — the colour the gated write actually persisted (additive; None on refusal)"
  - "core/approval.py::committed_colour(token, scored_colour) — the ONE edit-vs-approve colour rule"
  - "mcp/server.py::commit_priority returns colour=row.colour on a committed write"
  - "graph/nodes.py::handover renders the committed colour when committed, else the scored colour"
  - "route_after_verify fails closed to END; the dead verify->score retry edge is gone"
affects: [graph, mcp, evals]

actuals:
  tokens: 5371
  tasks: 3
  commits: 3

key-files:
  created:
    - src/triagedesk/core/approval.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/graph/state.py
    - src/triagedesk/core/confidence.py
    - tests/conftest.py
    - tests/test_commit_idempotent.py
    - tests/test_mcp_tools.py
    - tests/test_safety_spine.py
    - tests/test_graph_durable.py
    - tests/test_graph_tracer.py

key-decisions:
  - "The committed colour is part of the tool contract: the gate returns the persisted row colour, so the card never re-derives it."
  - "The token->colour rule lives only in core/approval.py; the shipped gate and the graph fake both call it (SOLID: L)."
  - "A failed verify is terminal: re-running the deterministic scorer on unchanged state cannot repair a structural contract violation."

status: complete
completed: 2026-11-04
---

# Quick Task 261104-ueu: two correctness defects Summary

**The handover card now shows the colour the queue actually holds (an edit's committed colour), and a failed evidence check fails closed instead of looping a deterministic scorer that can never change its answer.**

## Task Commits

1. **Task 1: `CommitResult` carries the committed colour** — `e9261e4` (feat)
2. **Task 2: handover card reads the committed colour** — `dfb8394` (fix)
3. **Task 3: remove the dead verify retry edge** — `119890c` (fix)

## Files Created/Modified

- `src/triagedesk/core/approval.py` (new) — pure `committed_colour(token, scored_colour)`; the ONE home of the edit-vs-approve rule.
- `src/triagedesk/core/schema.py` — additive `CommitResult.colour: str | None = None`; docstring names the persisted-colour contract.
- `src/triagedesk/mcp/server.py` — gate calls the helper and returns `colour=row.colour` (the persisted truth, including the idempotent path); refusal branches untouched.
- `src/triagedesk/graph/nodes.py` — `handover()` prefers `commit_result.colour` when committed and non-empty, else `priority.colour`; `verify`/`_make_ground` docstrings made truthful.
- `src/triagedesk/graph/build.py` — `_MAX_ATTEMPTS` deleted; `route_after_verify` returns `recheck` or `END`; edge map narrowed to `{"recheck", END}`.
- `src/triagedesk/graph/state.py`, `src/triagedesk/core/confidence.py` — stale retry wording corrected.
- `tests/conftest.py` — graph fake returns `committed_colour(parsed, inp["colour"])` via the shared helper.
- `tests/test_commit_idempotent.py`, `tests/test_mcp_tools.py`, `tests/test_safety_spine.py`, `tests/test_graph_durable.py`, `tests/test_graph_tracer.py` — regression coverage per plan, including the end-to-end durable edit asserting card colour == queue row colour.

## Verification

- Focused subset: `uv run pytest -q tests/test_graph_tracer.py tests/test_commit_idempotent.py tests/test_safety_spine.py tests/test_graph_durable.py tests/test_mcp_tools.py tests/test_eval_honest_terminal.py` → **51 passed**.
- Full suite: `uv run pytest -q` → **510 passed** (baseline 492 + 3 new tests from this plan = 495 attributable; the remainder comes from a concurrent, uncommitted quick task in the same worktree — `test_triage_skill.py` and `src/triagedesk/skills/`, not part of this change set).
- Lint: `uv run ruff check src tests` → **All checks passed!**
- The plan's stray gitignored `spans.jsonl` was removed before the runs; the final full run leaves none.

## Deviations from Plan

None — plan executed exactly as written.

## Plan-Left-Undone (deliberately out of scope)

- The card's `target` still comes from the scored priority, so an edit that changes the colour keeps the scored target time (the plan's documented residual; needs a committed `target` on `CommitResult`).
- `ARCHITECTURE.md:26,34` and `docs/REQUIREMENTS.md` (JC-1) still describe a "retry once" / verify-retry loop; the plan flags this as doc drift to correct separately.

## Self-Check

- FOUND: src/triagedesk/core/approval.py
- FOUND: e9261e4
- FOUND: dfb8394
- FOUND: 119890c

## Self-Check: PASSED

---
*Quick task: 261104-ueu*
*Completed: 2026-11-04*
