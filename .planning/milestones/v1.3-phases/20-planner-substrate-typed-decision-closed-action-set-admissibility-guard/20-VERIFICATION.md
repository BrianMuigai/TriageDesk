---
phase: 20
verified: "2026-11-14"
status: passed
score: "4/4 requirements"
covered_files: ["docs/MCP.md", "src/triagedesk/core/planner.py", "src/triagedesk/core/schema.py", "src/triagedesk/evals/tools.py", "src/triagedesk/graph/build.py", "src/triagedesk/llm/client.py", "src/triagedesk/llm/prompts.py", "src/triagedesk/mcp/server.py", "src/triagedesk/skills/triagedesk-triage/SKILL.md", "src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md", "tests/conftest.py", "tests/test_planner.py", "tests/test_planner_guard.py", "tests/test_planner_tool.py", "tests/test_purity.py", "tests/test_safety_spine.py", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-01-PLAN.md", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-01-SUMMARY.md", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-02-PLAN.md", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-02-SUMMARY.md", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-03-PLAN.md", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-03-SUMMARY.md", ".planning/phases/20-planner-substrate-typed-decision-closed-action-set-admissibility-guard/20-SUMMARY.md"]
covered_digest: "v4:sha256:e87db2ec9ba94e5d786400c0ab4443fcab16a0b98aefe9ff744ae15f66f79082"
---

# Phase 20 — VERIFICATION

## Requirement coverage

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| ADAPT-02 | `core/planner.validate_proposal` returns `finish_investigation` + `overridden=True` for inadmissible, `None`, malformed and unparseable proposals; `tests/test_planner_guard.py` pins each cause with a named reason | PASS |
| ADAPT-04 | `PlanDecision` has no colour/priority/queue field; the guard test asserts the action is always a member of `admissible_actions(state)` across the state × proposal cross-product | PASS |
| ADAPT-06 | `MAX_INVESTIGATION_STEPS = 3` declared once; budget 0 admits only `finish_investigation`; history suppresses a repeated action; the guard never raises on exhaustion | PASS |
| ADAPT-08 | `finish_investigation` is the single name in `PlanAction`, the guard, the tool contract, the tests and the docs | PASS |

## Measured checks

- `uv run pytest -q` → **794 passed**.
- `uv run ruff check src tests` → All checks passed.
- `uv run mypy src` → 30 errors in 7 files, **identical to the pre-phase baseline**; zero in
  `core/planner.py`, `core/schema.py`, `llm/client.py`, `mcp/server.py`.
- The owned-tool allowlist is 8 and the exact-set assertion still fails closed (its existing test passes).

## Honest gaps

- No graph node calls `plan_next_step` yet (by design; Phase 23 wires it). The tool is allowlisted and
  tested in isolation only.
- The fast path is asserted with a spy but not yet measured end-to-end; Phase 24 publishes the delta.
