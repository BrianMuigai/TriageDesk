---
phase: 06
review: 06-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "demo --durable bypassed the injectable store seam and launched the borrowed subprocess"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "resume printed nothing and returned 0 even when the gate REFUSED the commit"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "DEMO.md said the durable dismissal refusal 'is shown', but the CLI emitted nothing"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "resume caught only DurableError; every other failure escaped as a raw traceback"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "the dismiss token was malformed, so commit_priority's dismiss branch was unreachable and the runbook contradicted the CLI"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "a whitespace-only approver/role passed the gate's identity check"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "approval_decision accepted a whitespace-only approver/role (reclassified WR-06 in iteration 2; fixed in b70277e)"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "the dismiss-token literal was duplicated in demo/run.py and evals/runner.py (fixed in f95210b)"
  - id: IN-06
    severity: info
    disposition: open
    title: "DEMO.md per-beat expected-output blocks omit the printed handover card:/commit: lines"
  - id: IN-07
    severity: info
    disposition: open
    title: "the supersede unconditionally overwrites the stored target (store/queue.py)"
  - id: IN-08
    severity: info
    disposition: open
    title: "the borrowed UPSERT semantics are only string-asserted, never executed"
open: 3
total: 11
recorded: 2026-10-12T12:05:00.000Z
---

# Phase 06: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | fixed in 9a24f8c — `demo --durable` resolves its store through the one `mcp.server._resolve_store` seam; regression test asserts the borrowed factory is never invoked |
| WR-02 | warning | fixed | fixed in c97a4df — `resume` surfaces the commit outcome and exits non-zero on a refused approve/edit |
| WR-03 | warning | fixed | fixed in b2f5cae — runbook aligned to the CLI's refusal string; superseded by WR-05 (f95210b) which fixed the root cause |
| WR-04 | warning | fixed | fixed in f5d2a45 — `resume` catches `DurableError`, `RuntimeError`, `sqlite3.Error`, `ExceptionGroup` and reports cleanly |
| WR-05 | warning | fixed | fixed in f95210b — `approval_decision("dismiss")` now emits a well-formed token, so `commit_priority`'s dismiss branch runs; DEMO.md corrected and coupled by a test |
| WR-06 | warning | fixed | fixed in b70277e — whitespace-only approver/role/colour rejected with a named-flag error and a non-zero exit |
| IN-01 | info | fixed | reclassified as WR-06 in iteration 2; fixed in b70277e |
| IN-05 | info | fixed | fixed in f95210b — the duplicated `_UNAPPROVED_RESUME` literal consolidated through `durable.approval_decision` |
| IN-06 | info | open | out of `critical_warning` fix scope — carried to a later phase (or a docs sweep) |
| IN-07 | info | open | out of `critical_warning` fix scope — latent; see 06-REVIEW.md |
| IN-08 | info | open | out of `critical_warning` fix scope — coverage gap; the UPSERT was validated manually |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.

> **Note on `info` ids during the `--auto` loop.** `gsd-code-reviewer` numbers `IN-NN` per review pass, so an
> `IN-NN` id is only stable within one iteration. This ledger records the ids as they appeared in the review
> pass that surfaced them, with a free-text Source cell making each row self-describing. The `warning` ids
> (`WR-NN`) are stable across the loop because the re-review reports them until they are fixed.
