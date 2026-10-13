---
phase: 09
review: 09-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "the borrowed statement guard was not fail-closed (WITH-prefixed DML, PRAGMA writes, multi-statement, then EXPLAIN+PRAGMA)"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "retrieval matched token sets rather than the matcher's contiguous rule, surfacing discriminators absent from matched_ids"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "stale line references in the matcher comment"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "the read-path probe docstring documented an unreachable degradation branch"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "SELECT load_extension(...) was admitted by the guard (iteration 2)"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "PRAGMA prefix matching over-accepted PRAGMA table_infox (iteration 2)"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "retrieve_evidence's docstring claimed 'no store access' while the @audited interceptor records the call (iteration 2)"
open: 0
total: 7
recorded: 2026-10-13T02:10:00.000Z
---

# Phase 09: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fixed across `2d97aa3` (WITH head refused, read-only PRAGMA subset, non-trailing `;` refused) and `6530b98` (`EXPLAIN` dropped from the admitted prefixes — SQLite executes `PRAGMA` at compile time, so `EXPLAIN PRAGMA writable_schema=1` mutated state). Re-verified over 33 adversarial vectors. |
| WR-01 | warning | fixed | fixed in a716651 — the matcher's contiguous helper promoted to public `contains_sequence` and reused in `retrieval._score`; two false-positive phrases are regression cases; 0 divergences vs `match_discriminators` over 35 complaints |
| IN-01 | info | fixed | fixed in b5b9421 — stale line refs corrected *(iteration 1)* |
| IN-02 | info | fixed | fixed in 36104e0 — the probe docstring now matches the reachable behaviour *(iteration 1)* |
| IN-01 | info | fixed | fixed in 8c442d9 — `load_extension` refused by a deny-list check *(iteration 2)* |
| IN-02 | info | fixed | fixed in f8ee51b — the `PRAGMA` name-boundary check rejects `PRAGMA table_infox` *(iteration 2)* |
| IN-03 | info | fixed | fixed in bb19fc1 — the docstring corrected: the tool's own logic touches no store; the interceptor audits every owned call *(iteration 2)* |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently.

> **Note on id reuse during the `--auto` loop.** `gsd-code-reviewer` numbers `WR-NN`/`IN-NN` per review pass, so
> an id is only stable within one iteration. Each row above carries a free-text Source cell naming the commit
> that fixed it, so a reused id is unambiguous; every row is fixed, so no decision is lost.
