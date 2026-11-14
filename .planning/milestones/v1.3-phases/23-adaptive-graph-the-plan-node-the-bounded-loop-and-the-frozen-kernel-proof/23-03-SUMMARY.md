# 23-03 — SUMMARY

**Status:** complete · **Commit:** `056c1a4`

- The `plan` node emits a decision span carrying the structural facts only (action, step, budget,
  overridden) and the `plan_next_step` audit record carries the full `PlanDecision` — the durable
  "why next?" record (ADAPT-05).
- `tests/test_plan_audit.py`: one audit record per decision with the whole decision; the span carries the
  structural facts and belongs to the case trace.
- `docs/MCP.md` and the packaged `triagedesk-triage` skill describe the planner round-trip.
