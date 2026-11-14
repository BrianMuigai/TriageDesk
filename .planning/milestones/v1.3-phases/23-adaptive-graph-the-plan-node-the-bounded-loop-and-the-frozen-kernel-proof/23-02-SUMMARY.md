# 23-02 — SUMMARY

**Status:** complete · **Commit:** `056c1a4`

`tests/test_frozen_kernel.py` proves, on the compiled graph and with fake tools:

1. `score` has exactly one inbound edge (`finish_investigation`).
2. `commit` has exactly one inbound edge (`approval_gate`).
3. No investigation node's partial update contains `priority`, `commit_result` or `handover`.
4. `PlanAction` cannot express a kernel effect (no `score`/`approval_gate`/`commit` member).
5. The loop is bounded (never more than `MAX_INVESTIGATION_STEPS` decisions, never a repeated action) and a
   spent budget reaches `finish_investigation`.
6. The emergency arm reaches `finish_investigation` without ever calling `plan_next_step`.
