---
phase: 11
review: 11-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "the 'general' serial-vitals contract omitted temperature_c and its field set coincided exactly with E-07's fixture"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "the §4 case-table reconciliation guard was one-directional (a stale row passed --check)"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "STATUS.md restated figures that contradicted the corrected README and the regenerated EVALS.md"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "STATUS.md:56 still said '4 failures' after the WR-03 correction (iteration 2)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "the report's harness_commit named a commit whose schema differed from the run's, so the bare SHA could not reproduce it (iteration 2)"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "docs/REQUIREMENTS.md and docs/ROADMAP.md still restated the stale 14-cases / two-commands figures (iteration 2)"
  - id: WR-01
    severity: warning
    disposition: deferred
    title: "docs/DEMO.md's recorded output blocks drift from the shipped CLI since Phases 8/9/10 (iteration 3)"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "cheap doc-accuracy items: the stale tool count (5 vs 7), the eval-case count, and a ROADMAP cross-reference"
open: 0
total: 8
recorded: 2026-10-13T09:30:00.000Z
---

# Phase 11: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | fixed in ae980c5 + 9e18462 — the serial-reading description now covers every scored numeric vital, derived from the scored-vitals source of truth; a guard asserts the described set equals the scored set. This changed the model input, so the report was regenerated through the pipeline (owner-confirmed: publish as measured). |
| WR-02 | warning | fixed | fixed in 967a4a5 + 273eb38 — the §4 case-table guard now enforces set equality (a stale row fails closed); both directions pinned |
| WR-03 | warning | fixed | fixed in 47bd4a1 — STATUS.md's contradicting figures corrected |
| WR-01 | warning | fixed | fixed in 08fc622 — the STATUS.md:56 row now agrees with its own §5 G4 and the regenerated report *(iteration 2)* |
| WR-02 | warning | fixed | fixed in 14974a0 — a non-clean tree is now marked `-dirty`; `EVALS.md` §8 names the sealed `extraction_schema_hash` as what reproduces the run, not the bare commit. NO eval re-run, so no measured number moved *(iteration 2)* |
| WR-03 | warning | fixed | fixed in 1ff1872 — only the contradicting restatements updated in docs/REQUIREMENTS.md and docs/ROADMAP.md *(iteration 2)* |
| WR-01 | warning | **deferred** | **Deferred to Phase 12 (DOCS-06) with a recorded reason.** `docs/DEMO.md`'s recorded output blocks predate Phases 8/9/10 (the `routine`/E-01 and `deterioration`/E-07 beats defer with no `commit` line; `escalation` commits at queue position 1). A faithful refresh requires re-running the demo and re-transcribing it — exactly DOCS-06's "every submission document refreshed to the v1.1 state". A dated **"Known drift — refreshed in Phase 12 (DOCS-06)"** note was added at the affected section, the original blocks kept (no wrong output transcribed as right), and the "every line is real output" claim softened so it no longer asserts byte-exact currency. Recorded in STATE.md's Blockers/Concerns as a `[Phase 12, DOCS-06]` item. |
| IN-01 | info | fixed | fixed in b1c3d14 (the tool count 5 → 7, derived from `OWNED_TOOL_ALLOWLIST`), d4e44d1 (AGENTS.md 14 → 16 eval cases), 951a632 (the ROADMAP cross-reference §10 → §11); the E-09 framing was verified already correct across the non-planning docs |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently.

> **Note on id reuse during the `--auto` loop.** `gsd-code-reviewer` numbers `WR-NN`/`IN-NN` per review pass, so
> an id is only stable within one iteration. Each row above carries a free-text Source cell naming the commit
> that fixed it and its iteration. Three ids are reused (`WR-01` ×3, `WR-02` ×2, `WR-03` ×2) — each names a
> DIFFERENT defect. Every row is `fixed` except the one explicitly `deferred` to Phase 12.
