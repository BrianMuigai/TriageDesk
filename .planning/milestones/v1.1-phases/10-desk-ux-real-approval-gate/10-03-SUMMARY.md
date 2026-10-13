---
phase: 10-desk-ux-real-approval-gate
plan: 03
subsystem: docs
tags: [quickstart, runbook, drift-guard, decision-record, adr, cli, stdlib, http-server]

# Dependency graph
requires:
  - phase: 10-desk-ux-real-approval-gate
    plan: 01
    provides: "the desk bridge, its static assets and the `desk` CLI subcommand (the surface the quickstart documents)"
  - phase: 10-desk-ux-real-approval-gate
    plan: 02
    provides: "the banner, the read-only deferred terminal and the fail-safe gate (the routes/copy the quickstart documents)"
provides:
  - "docs/DESK.md: the one-screen desk quickstart — the literal one-command path, the local URL, the UI-SPEC copy a nurse sees, and the plain-language fail-safe clauses, with no graph internals named"
  - "tests/test_desk_runbook.py: the runbook-vs-CLI drift guard (drives the public triagedesk.cli.main surface, serve spied)"
  - "docs/DECISIONS.md D23: the desk-surface design recorded in the ADR-lite log"
affects: [verification, ship]

# Actuals (#2632) — pairs with the plan's estimate (30000 tokens / 2 tasks / low confidence).
# Same estimateTokens scale: chars/4 over the realized diff, never a harness token count.
actuals:
  tokens: 2665
  tasks: 2
  commits: 2
  plan_head_before: e7236598871754d1253dcb3ac7a32ad9d9ff9ae1
  plan_head_after: 667f4ed4e0ee149ba53058822dc2fa51dfc418d2

# Tech tracking
tech-stack:
  added: []  # no new dependency (D10-16)
  patterns:
    - "a runbook is pinned to the shipped CLI by driving the public main surface with the lazy handler seam spied — the documented invocation is the command a nurse runs, never a private parser helper"
    - "the internal identifiers a doc must not name are imported (TRACER_NODES), never restated, so the guard tracks the code"
    - "a new runbook lives in its own document so it cannot perturb the already-guarded submission docs (one concern per document — SOLID: S)"

key-files:
  created:
    - docs/DESK.md
    - tests/test_desk_runbook.py
  modified:
    - docs/DECISIONS.md

key-decisions:
  - "The quickstart lives in a NEW docs/DESK.md: the existing doc guards constrain specific files (ARCHITECTURE/DESCRIPTION/README/EVALS via test_docs_final.py, docs/DEMO.md via test_demo_runbook.py), so a new document is unconstrained and cannot break a guard (A5, RESEARCH Pattern 6)."
  - "The drift guard drives triagedesk.cli.main with triagedesk.desk.server.serve spied (the lazy-import target), so no server is started and the runbook cannot document a flag the shipped CLI rejects."
  - "The internal-identifier check set is derived from triagedesk.graph.build.TRACER_NODES (imported, filtered to underscore-bearing names) — never restated — so the guard tracks the code as nodes are added."
  - "docs/DECISIONS.md gains exactly ONE new row (D23) recording the surface design and its two owner-confirmed resolutions, linking to the reasoning rather than restating any colour list, target time or copy string (CONVENTIONS §1)."

patterns-established:
  - "A quickstart proves its commands by driving the shipped entry point with the side-effecting seam spied, so the doc is grounded in the CLI rather than asserted."
  - "A doc-guard's forbidden-token set is imported from the code that owns it, keeping the guard non-vacuous and drift-proof."

requirements-completed: [UX-04]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "docs/DESK.md is a one-screen desk quickstart: the literal `uv run triagedesk desk` path with its host/port/db overrides, the local URL to open, the UI-SPEC copy a nurse sees, and the fail-safe clauses (timeout = no approve, dismiss commits nothing, never commits on its own) — naming no graph node, thread id or internal identifier (D10-14)."
    requirement: "UX-04"
    verification:
      - kind: unit
        ref: "tests/test_desk_runbook.py#test_documented_invocations_are_accepted_by_the_cli"
        status: pass
      - kind: unit
        ref: "tests/test_desk_runbook.py#test_runbook_documents_the_one_command_path_and_url"
        status: pass
      - kind: unit
        ref: "tests/test_desk_runbook.py#test_runbook_states_the_fail_safe_clauses"
        status: pass
      - kind: unit
        ref: "tests/test_desk_runbook.py#test_runbook_names_no_graph_internal_identifier"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/DECISIONS.md carries exactly one new D23 row recording the desk-surface design — the stdlib http.server presentation bridge, the ONE pause/resume plumbing with no surface commit path, the banner-on-the-terminal resolution, and the gate-derived editable colour set — without restating any colour list, target time or copy string."
    requirement: "UX-04"
    verification:
      - kind: other
        ref: "grep -c '^### D23 ' docs/DECISIONS.md == 1; uv run pytest tests/test_docs_final.py tests/test_demo_runbook.py -q"
        status: pass
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-10-13
status: complete
---

# Phase 10 Plan 03: The One-Screen Desk Quickstart, Its Drift Guard & the D23 Decision Row Summary

**A one-screen desk quickstart gives a first desk-facing interaction in literal steps — pinned to the shipped CLI's own parser so it cannot drift — and the surface's design is recorded as the single decision row D23, with every guarded submission document untouched.**

## Performance

- **Duration:** ~3 min (the measured span from the first to the last task commit)
- **Started:** 2026-10-12T21:22:02Z
- **Completed:** 2026-10-12T21:25:22Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- **`docs/DESK.md`** — a one-screen desk quickstart: a short intro blockquote (single local page, loopback only, no external request, no build step, no dependency), a one-time `uv sync --locked` block, the literal `uv run triagedesk desk` command with its `--host`/`--port`/`--db` overrides and the `http://127.0.0.1:8765` URL, a fenced `text` block of the expected on-screen states using the UI-SPEC Copywriting Contract strings verbatim, and a plain-language "what the surface never does" block stating the fail-safe rules. It names no graph node, no thread id and no internal identifier (D10-14).
- **`tests/test_desk_runbook.py`** — the runbook-vs-CLI drift guard (the `tests/test_demo_runbook.py` shape). It extracts every `triagedesk desk` invocation from the document's fenced blocks and drives each through the **public `triagedesk.cli.main`** surface with `triagedesk.desk.server.serve` spied, asserting a `0` return and that the spy recorded the call (so no server starts and the runbook cannot document a flag the CLI rejects). It also pins the literal one-command path + URL, the three fail-safe clauses, and the absence of any underscore-bearing `TRACER_NODES` name or `thread_id`/`thread-id` token — with both check sets asserted non-empty so the guard cannot pass vacuously.
- **`docs/DECISIONS.md`** — exactly one new **D23** row recording the desk-surface design: the stdlib-`http.server` presentation bridge bound to loopback with no build step/CDN/dependency; the thin presentation-only rendering of the graph's typed outputs (no re-derived colour/citation/target/confidence); the ONE pause/resume plumbing with no surface commit path (timeout = no approve, dismiss commits nothing); the banner-on-the-terminal resolution (a deferred case = a read-only card and no gate); and the gate-derived editable colour set. It restates no colour list, target time or copy string.

## Task Commits

Each task was committed atomically:

1. **Task 1: The one-screen desk quickstart and its runbook-vs-CLI drift guard** — `9862fcb` (docs)
2. **Task 2: The desk-surface decision row in `docs/DECISIONS.md`** — `667f4ed` (docs)

**Plan metadata:** the SUMMARY/STATE/ROADMAP are written but **not committed** — `.planning/config.json` sets `commit_docs: false` (the SDK `commit` verb returns `skipped_commit_docs_false`).

## Files Created/Modified

- `docs/DESK.md` (NEW) — the one-screen desk quickstart, deliberately outside every existing doc guard.
- `tests/test_desk_runbook.py` (NEW) — the runbook-vs-CLI drift guard (drives the public `main` surface, `serve` spied).
- `docs/DECISIONS.md` — the D23 row (the surface design and its two owner-confirmed resolutions).

## Decisions Made

- **The quickstart's home is a new `docs/DESK.md`.** `tests/test_docs_final.py` constrains `ARCHITECTURE.md`/`DESCRIPTION.md`/`README.md`/`EVALS.md` and `tests/test_demo_runbook.py` constrains `docs/DEMO.md`; a new document is unconstrained, so the quickstart cannot break an existing guard, and the desk runbook stays separate from the demo-video runbook (one concern per document — SOLID: S).
- **The drift guard spies the lazy-import target.** `main` imports `from triagedesk.desk.server import serve` *inside* its `desk` branch, so the monkeypatch is applied to the module attribute `triagedesk.desk.server.serve` (not a name in `cli`'s namespace) — the documented invocation is driven through the shipped entry point and no server is started.
- **One decision row, not several.** D10-01…D10-19 are the phase's working decisions in CONTEXT.md; `docs/DECISIONS.md` is the durable ADR-lite record, so it gains exactly one row that links to the reasoning instead of restating the token/colour lists or copy (CONVENTIONS §1).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The suite ran clean at the 388-test baseline; no `spans.jsonl` artefact was present (the out-of-band-probe issue noted in 10-01/10-02 did not recur).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10's documentation half is complete: the quickstart is provably the shipped CLI's own commands, and the surface design is answerable from the decision record.
- Full suite green at **392 passed** (388 baseline + 4 new runbook tests); `ruff check` clean on `tests/test_desk_runbook.py`.
- No guarded submission document was edited; the frozen spine is byte-identical (no change under `src/triagedesk/core/`, `graph/`, `mcp/`, `store/`, `evals/` or `data/`).
- Phase 10 is ready for verification; the one standing human backstop remains the painted banner/no-clip visual check declared in 10-01/10-02 (D4/D6, `human_judgment: true`).

---

*Phase: 10-desk-ux-real-approval-gate*
*Completed: 2026-10-13*

## Self-Check: PASSED

- All created/modified files exist (`docs/DESK.md`, `tests/test_desk_runbook.py`, `docs/DECISIONS.md`).
- Both task commits exist and are ancestors of HEAD: `9862fcb`, `667f4ed`.
- `docs/DECISIONS.md` carries exactly one `### D23 ` row.
- Full suite green at 392 passed (388 baseline + 4 new runbook tests).
