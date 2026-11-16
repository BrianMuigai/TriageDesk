# 20-01 — SUMMARY

**Status:** complete · **Commit:** `0d87633`

- `core/schema.py`: `PlanAction` (exactly `gather_evidence`, `ask_question`, `re_extract`,
  `finish_investigation`), `InvestigationState`, `PlanProposal`, `PlanDecision`.
- `core/planner.py`: `MAX_INVESTIGATION_STEPS = 3`, `admissible_actions`, `default_plan`,
  `validate_proposal`, `FINISH_ONLY` — pure, no `llm`/`mcp`/`store` import.
- `tests/test_planner.py`: closed-set, admissibility and validation unit tests.
- Verified: `uv run pytest -q` green; `ruff` clean.
