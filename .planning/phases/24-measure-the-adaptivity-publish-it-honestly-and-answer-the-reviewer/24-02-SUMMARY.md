# 24-02 — SUMMARY

**Status:** complete · **Commit:** `1b8cf76`

## Measured arms (real mode, 1 run each)

The comparison uses the four cases where an investigation action is admissible at all — E-09 (ambiguous),
E-12 (missing vitals), E-15 and H-03 (clarify). A routine matched case admits only
`finish_investigation`, so it cannot distinguish the arms.

| Metric | Adaptive | Baseline | Delta |
| --- | --- | --- | --- |
| Colour correctness | 0/0 | 0/0 | +0.0 pp (no colour-expected case in the subset) |
| Clarified | 3 | 3 | 0 |
| Deferred | 0 | 0 | 0 |
| Mean steps | 2.8 | 0.0 | +2.80 |
| Guard overrides | 1/4 | 0/0 | +25.0 pp |
| Latency p50 (s) | 38.06 | 14.32 | +23.74 |
| Latency p95 (s) | 48.56 | 17.53 | +31.03 |

The adaptive actions were `gather_evidence` ×4, `ask_question` ×3, `finish_investigation` ×4; the three
elicitation outcomes were `unavailable` (the eval harness is in-process and has no MCP client), so the
planner asked and then finished. That is the honest result: on these cases the envelope changes
**behaviour** and costs **latency**, and it does not change the clinical outcome.

## Why the full suite is not re-run in real mode

The host measured ~90 s per local model call at the time of writing; a two-arm 24 × 3 re-run was not
practical. `EVALS.md` §3 remains the last full-suite real measurement (v1.2 code, 3 runs, digest
`0ae3dde6`); §3.3 states this explicitly rather than implying a fresh full-suite number.

## Publishing

`scripts/emit_evals.py` generates §3.3 from both sealed reports; the pair is resolved from fixed paths
(`report.adaptive.json`, `report.baseline.json`) so the documented one-liner still passes `--check`
(exit 0). A missing baseline fails with a named remedy, not a traceback.
