# 20-03 — SUMMARY

**Status:** complete · **Commit:** `bf207ec`

- `tests/test_planner_guard.py`: every degradation cause (inadmissible, `None`, malformed action,
  malformed shape, unparseable, exhausted budget) lands on `finish_investigation` with
  `overridden=True`; the boundary matrix of `admissible_actions`; a state × proposal cross-product
  proving no proposal can widen the action set.
- `tests/test_purity.py`: a named test that `core/planner.py` imports nothing from `llm`/`mcp`/`store`.
- Verified: `uv run pytest -q` → 794 passed; `ruff` clean; `mypy` unchanged from baseline.
