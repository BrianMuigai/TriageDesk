# 24-02 — SUMMARY

**Status:** complete · **Commit:** `1b8cf76`

## Measured arms (real mode, full 24-case suite, 1 run each)

> **Post-close update:** the phase initially published a declared 4-case subset because the host was
> measuring ~90 s per model call. The host recovered; the comparison below is the **full suite**, and it
> replaces the subset figures. The subset reports are removed.

| Metric | Adaptive | Baseline | Delta |
| --- | --- | --- | --- |
| Colour correctness | 16/16 | 16/16 | +0.0 pp |
| Coverage (delivered/reached) | 16/20 | 16/20 | +0 runs |
| Clarified | 3 | 3 | 0 |
| Deferred | 0 | 0 | 0 |
| Mean steps | 2.1 | 0.0 | +2.10 |
| Guard overrides | 3/23 | 0/0 | +13.0 pp |
| Latency p50 (s) | 25.99 | 18.26 | +7.73 |
| Latency p95 (s) | 50.47 | 24.06 | +26.41 |

Adaptive actions: `gather_evidence` ×23, `ask_question` ×3, `finish_investigation` ×23. The three
elicitation outcomes were `unavailable` (the eval harness is in-process and has no MCP client), so the
planner asked and then finished. Both arms fired the deterministic emergency bypass on the same case
(E-16). Under-triage and over-triage are empty in both arms; the gate passes in both.

The honest reading: on the full suite the envelope changes **behaviour** and costs **latency**
(+7.73 s p50, +26.41 s p95) without changing a single clinical outcome. It does not make the system more
accurate on these cases; it makes it able to ask, gather and re-read.

## Publishing

`scripts/emit_evals.py` generates §3.3 from both sealed reports; the pair is resolved from fixed paths
(`report.adaptive.json`, `report.baseline.json`) so the documented one-liner still passes `--check`
(exit 0). A missing baseline fails with a named remedy, not a traceback.
