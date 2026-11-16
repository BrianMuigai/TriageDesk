# 20-02 — SUMMARY

**Status:** complete · **Commit:** `a7f385a`

- `llm/prompts.py` + `llm/client.py`: `propose_plan_async` — structured output over `PlanProposal`,
  reusing the ONE Ollama client construction; failure returns `None`.
- `mcp/server.py`: eighth owned tool `plan_next_step` (`@server.tool()` + `@audited()`), thin, read-only,
  no store and no approval token; the no-model fast path lives in the tool.
- Allowlist 7 → 8 in one atomic change: `graph/build.py`, discovery assertion, `evals/tools.py`,
  `tests/conftest.py`.
- `docs/MCP.md` + packaged `triagedesk-triage` skill document the contract.
- `tests/test_planner_tool.py`: tool contract, fast-path spy (model never called), audit record.
- Verified: `uv run pytest -q` green; `ruff` clean.
