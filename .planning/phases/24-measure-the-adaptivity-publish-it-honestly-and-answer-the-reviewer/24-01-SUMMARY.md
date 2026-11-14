# 24-01 — SUMMARY

**Status:** complete · **Commit:** `ed4a095`

- `build_graph(..., planner=True)` and `run_eval(..., planner=True)`; `triagedesk eval --no-planner`
  selects the baseline arm (`retrieve → finish_investigation`).
- `Report.planner` records the arm; `ReportCase` gains index-aligned, default-empty investigation facts
  (`investigation_steps`, `plan_actions`, `guard_overrides`, `elicitation_outcomes`, `emergency_bypass`);
  the `Analysis.adaptive` block derives them through the ONE analyser.
- The new facts are volatile (not sealed in `report_digest`), following the latency/token precedent, so
  the published digest contract does not move.
- `tests/test_eval_adaptive.py` proves the two arms, the unchanged kernel on both, the recorded facts and
  the all-zero baseline block.
