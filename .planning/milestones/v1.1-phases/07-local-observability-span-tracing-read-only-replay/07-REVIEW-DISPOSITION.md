---
phase: 07
review: 07-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "the @audited span wrapper could fail a successful tool call and fabricate a failed-tool audit record"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "replay was not read-only at the SQLite level (WAL pragma + schema ensure) — scope corrected and asserted (iteration 1)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "the contextvars trace binding does not cross the stdio-subprocess boundary — declared and pinned"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "the ALTER TABLE migration made pre-phase-7 audit rows fail verify()"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "replay reached private _resolve_store/_allowed_msgpack_modules and duplicated the saver wiring"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "the strip-then-derive case id was duplicated across _spanned and derive_thread_id"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "harden_offline ran after heavy imports could already prime a tracer"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "read_spans hit an unguarded json.loads, so a corrupt sink produced a raw traceback (iteration 2)"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "two mypy-strict errors introduced by the phase (lru_cache attr, RunnableConfig arg)"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "redundant CLI exception subclasses already covered by RuntimeError"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "doc drift from the WR-03/WR-05 renames"
  - id: IN-02
    severity: info
    disposition: open
    title: "read_spans guards malformed JSON but not a valid-JSON non-object line or a sink I/O fault (not reachable via realistic truncation)"
  - id: IN-04
    severity: info
    disposition: open
    title: "test_observability.py 'exactly one span' over-claims for a resumed run (test-only)"
open: 2
total: 13
recorded: 2026-10-12T14:30:00.000Z
---

# Phase 07: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fixed in ed97c05 — `emit_span` swallows its own `OSError` and `span()`'s `finally` guards the emit independently, so observability can never fail a tool call or fabricate a failed-tool audit record; regression test makes the sink a directory |
| WR-01 | warning | fixed | fixed in 81a110b — the read-only scope is now stated at the row level and asserted (zero queue rows / zero commits, with the necessary WAL/DDL declared) *(iteration 1)* |
| WR-02 | warning | fixed | fixed in 99e903f — the `contextvars` subprocess boundary is declared in SECURITY §10 + D19 and pinned by a test |
| WR-03 | warning | fixed | fixed in 68d1e5c — `record_digest` omits an empty `trace_id`, so pre-migration rows still verify while real traces stay sealed; test seeds a legacy-shaped row |
| WR-04 | warning | fixed | fixed in 3b35d72 — new `graph.build.open_checkpointer` + published `mcp.server.resolve_store`; replay no longer reaches private symbols |
| WR-05 | warning | fixed | fixed in f2ee83a — one `case_id_for_note` normaliser owns "strip then derive" for `_spanned`, `derive_thread_id` and the node bodies |
| WR-06 | warning | fixed | fixed in de13948 — `main()` hardens offline first, then lazily imports handlers |
| WR-01 | warning | fixed | fixed in 79532da — `read_spans` skips an unparsable line and reports it on stderr; the CLI also catches `ValueError`; 3 regression tests *(iteration 2, id reused)* |
| IN-01 | info | fixed | fixed in 0782d30 — the two phase-introduced mypy-strict errors cleared |
| IN-03 | info | fixed | fixed in d0a7a60 — redundant CLI exception subclasses dropped |
| IN-05 | info | fixed | fixed in be09595 — SECURITY §10 / D19 / the `AuditRecord` docstring aligned with the renames |
| IN-02 | info | open | out of `critical_warning` fix scope — not reachable via realistic truncation; see 07-REVIEW.md |
| IN-04 | info | open | out of `critical_warning` fix scope — a test-only over-claim; see 07-REVIEW.md |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.

> **Note on id reuse during the `--auto` loop.** `gsd-code-reviewer` numbers `WR-NN`/`IN-NN` per review
> pass, so an id is only stable within one iteration. This ledger records each row with a free-text Source
> cell naming its iteration and commit, so a reused id (WR-01 above) is unambiguous. Both `WR-01` rows are
> distinct defects and both are fixed.
