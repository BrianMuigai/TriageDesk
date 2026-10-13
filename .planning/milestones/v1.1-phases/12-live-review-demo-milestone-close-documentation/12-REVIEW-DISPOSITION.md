---
phase: 12
review: 12-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "docs/REVIEW.md Beat 3 documented only the resume half, so the beat failed live; the guard proved acceptance, not runnability"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "STATUS.md §5 G6 still said 'we have not rehearsed it' while its own §8 and REQUIREMENTS ST-1 said 'G6 resolved'"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "a stale '302 words' for DESCRIPTION.md survived the v1.1 sweep"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "docs/DEMO.md's header pointed at v1.0-submission while its body documented v1.1-only behaviour"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "STATUS.md said '453 tests pass' after the suite reached 454 (iteration 2)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "docs/DECISIONS.md D3 and the DQ-8 table named qwen3.5:4b while the shipped default is qwen2.5:1.5b (iteration 2)"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "docs/DEMO.md asserted it 'maps those timing bands' of the ROADMAP storyboard, but the bands had diverged (iteration 3)"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "advisories: the runbook header's coverage claim; a vacuous src/ guard; the README repo map; PROJECT.md's compute row; client.py's RAM figure + model naming; STATUS §0's band and confirmation count"
open: 0
total: 8
recorded: 2026-10-13T12:40:00.000Z
---

# Phase 12: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fixed in e418ced — Beat 3 corrected to the two-command pause→resume form AND the guard strengthened to prove RUNNABILITY (a compose assertion that the documented pause+resume share one `--db`, plus driving the real pause→resume through the shipped `main` over a `tmp_path` checkpoint; verified non-vacuous) |
| WR-01 | warning | fixed | fixed in 3143e79 — G6 now states what remains human (performing it live) rather than "not rehearsed" |
| WR-02 | warning | fixed | fixed in 161e81c — the stale "302 words" dropped in favour of a link |
| WR-03 | warning | fixed | fixed in 7ca9f62 — the DEMO header now points at the v1.1 state |
| WR-01 | warning | fixed | fixed in 56de010 — the hard test count dropped in favour of the suite, so the doc cannot re-stale *(iteration 2)* |
| WR-02 | warning | fixed | fixed in 9b92e54 — D3 + the DQ-8 table now name the shipped/measured default `qwen2.5:1.5b` (with the 4B as the verified fallback), reconciled with BW-5 *(iteration 2)* |
| WR-01 | warning | fixed | fixed in 8c4e081 — ROADMAP's canonical storyboard bands updated to the runbook's, so DEMO's "maps those timing bands" claim is now TRUE *(iteration 3)* |
| IN-01 | info | fixed | fixed across 6aad338, 4797939, 99a9e73 (iteration 1); 9490e2a (iteration 2); 014299e, 5eb12aa, c8fe673, fa9e257 (iteration 3) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently.

> **Note on id reuse during the `--auto` loop.** `gsd-code-reviewer` numbers `WR-NN`/`IN-NN` per review pass, so
> an id is only stable within one iteration. Each row above carries a free-text Source cell naming the commit
> that fixed it and its iteration. `WR-01` and `WR-02` are reused across iterations — each names a DIFFERENT
> defect. Every row is `fixed`; the final review reported `status: clean` with only two sub-threshold
> advisories (a `spike_model.py` evidence-key naming nit and a missing `check=True` in a spike script).
