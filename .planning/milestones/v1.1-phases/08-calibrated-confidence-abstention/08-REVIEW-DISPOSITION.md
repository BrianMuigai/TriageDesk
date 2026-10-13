---
phase: 08
review: 08-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "the missing_vitals branch in route_after_assess was dead (route_after_score diverts those cases first)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "_COMPONENT_COUNT = 4 duplicated the component arity owned by core.confidence, so a component change could silently mis-normalise the published ECE"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "the assess tool/node validated and passed a full case the core signal discarded"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "evals/runner.py had no per-run error handling, so an errored run and a legitimate short-circuit both surfaced as None"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "_digest_payload omitted confidence_satisfied, so tampering with it changed the published ECE undetected"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "component names restated in a test rather than read from the ONE owner (folded into WR-02)"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "the band-distance fallback was unreachable and unremarked"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "the colour-accuracy cell read 100.0% beside a failing gate without naming the failures"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "an errored run injected latency = 0.0 into the p50/p95 sample"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "EVALS.md said the ECE was computed over the held-out split rather than the calibration split"
open: 0
total: 10
recorded: 2026-10-13T00:20:00.000Z
---

# Phase 08: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | fixed in 186b6de — the arm is now an explicitly-labelled defensive guard with the code and comment agreeing, covered by two direct route tests |
| WR-02 | warning | fixed | fixed in 02fa979 — `COMPONENT_NAMES`/`COMPONENT_COUNT` declared once in `core/confidence.py`; `evals/analysis.py` imports `COMPONENT_COUNT` for the ECE divisor |
| WR-03 | warning | fixed | fixed in f95d972 — the unused `case` removed from `assess`, the MCP tool, the node payload, the eval wrapper and the test fake |
| WR-04 | warning | fixed | fixed in 6fa6b92 — per-run try/except; a new index-aligned `ReportCase.run_errors` surfaces an errored run (fail-closed ABORT, invariants not-held); the deferral denominator counts only evaluated runs |
| WR-05 | warning | fixed | fixed in 7a2974b — `confidence_satisfied` sealed in `report_digest` and the report + EVALS.md regenerated through the shipped real pipeline; a digest-mutation test pins it |
| IN-01 | info | fixed | folded into WR-02 |
| IN-02 | info | fixed | fixed in d59916d — the fallback is documented as unreachable |
| IN-03 | info | fixed | fixed in b7e1661 — the cell now reads "…correct (100.0%); 3 case(s) failing the gate" |
| IN-04 | info | fixed | fixed in 7352967 — an errored run records a `None` latency and is excluded from the p50/p95 sample |
| IN-05 | info | fixed | fixed in 3e6d0ef — the ECE wording now names the calibration split (`held_out=false`) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently.

> **Note on id reuse during the `--auto` loop.** `gsd-code-reviewer` numbers `WR-NN`/`IN-NN` per review pass.
> This ledger's rows are unambiguous: each carries a free-text Source cell naming the commit that fixed it,
> and every row here is fixed, so no id-reuse collision can lose a decision.
