# Phase 20 — SUMMARY

**Status:** complete · **Commits:** `e215f68` (plans), `0d87633`, `a7f385a`, `bf207ec`

## What shipped

- **`core/planner.py`** (new, pure): the closed action set policy — `MAX_INVESTIGATION_STEPS = 3`,
  `admissible_actions`, `default_plan`, `validate_proposal`, `FINISH_ONLY`. No `llm`/`mcp`/`store` import.
- **`core/schema.py`**: `PlanAction` (exactly four members, none of them `score`/`approval_gate`/`commit`),
  `InvestigationState`, `PlanProposal`, `PlanDecision` (carries `proposed_action`, `overridden`,
  `override_reason` for audit).
- **`llm/client.py` + `llm/prompts.py`**: `propose_plan_async` — structured output over `PlanProposal`,
  reusing the ONE client construction; a transport/schema failure returns `None`.
- **`mcp/server.py`**: the eighth owned tool `plan_next_step(investigation) -> PlanDecision`, thin and
  audited. Fast path: when only `finish_investigation` is admissible the model is **not called**.
- **Allowlist 7 → 8** in one atomic change across the server, the discovery assertion, the graph
  allowlist, the eval tool fake and `tests/conftest.py`.
- **Docs touched honestly**: `docs/MCP.md` and the packaged `triagedesk-triage` skill document the new
  contract; README/ARCHITECTURE/SECURITY/STATUS still say 7 shipped + 2 proposed (the tool exists but no
  graph node calls it yet — topology is Phase 23).

## Verification

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| ADAPT-02 | Model proposes via structured output; guard degrades every inadmissible/malformed/unparseable/exhausted proposal to `finish_investigation` with `overridden=True` (`tests/test_planner_guard.py`) | PASS |
| ADAPT-04 | The decision contract cannot express a colour, priority or queue effect; the action is always a member of `admissible_actions(state)` over the full state × proposal cross-product | PASS |
| ADAPT-06 | Budget matrix pinned: budget 0 offers only the exit; history suppresses repeats; `MAX_INVESTIGATION_STEPS` declared once | PASS |
| ADAPT-08 | `finish_investigation` is the only name in code, contracts, tests and docs | PASS |

- `uv run pytest -q` → **794 passed** (647 baseline + 147 new).
- `uv run ruff check src tests` → clean.
- `uv run mypy src` → 30 pre-existing errors in 7 files, identical to the pre-phase baseline; none in the
  new or modified modules.

## Honest gaps

- The graph topology is unchanged by design: `plan_next_step` is allowlisted but unreferenced until
  Phase 23. A reader could mistake "tool exists" for "agent decides" — the summary and the allowlist
  comment both say so explicitly.
- No latency measurement yet; the fast path exists but its effect is measured in Phase 24.
