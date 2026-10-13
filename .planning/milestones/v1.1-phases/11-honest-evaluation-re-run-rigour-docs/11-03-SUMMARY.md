---
phase: 11-honest-evaluation-re-run-rigour-docs
plan: 03
subsystem: docs
tags: [readme, quickstart, cli-drift-guard, uv, docs-04]

# Dependency graph
requires:
  - phase: 11-honest-evaluation-re-run-rigour-docs
    provides: the extraction-contract fix and re-run pipeline (11-01; unchanged here)
  - phase: 10-desk-ux-real-approval-gate
    provides: the shipped `triagedesk` CLI + desk surface (the guard drives them)
provides:
  - "README §Quickstart as the literal one-command path `uv run triagedesk demo` (no separate install step)"
  - "the optional second command named: `uv run triagedesk desk`"
  - "tests/test_readme_runbook.py — the CLI-driving README-vs-CLI drift guard"
  - "the corrected `test_readme_has_the_one_command_quickstart` guard (forbids the two-step install)"
affects: [12 (final doc refresh + live review)]

# Actuals (#2632) — chars/4 over the realized diff, not a harness token count.
actuals:
  tokens: 1653
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []            # no new dependency (the phase installs nothing)
  patterns:
    - "A documented invocation is proven against the shipped `triagedesk.cli.main`, never a private parser helper"
    - "The side-effectful seams (`run_demo`, `serve`) are spied so the guard proves the invocation shape without running anything"

key-files:
  created:
    - tests/test_readme_runbook.py
  modified:
    - README.md
    - tests/test_docs_final.py

key-decisions:
  - "The README's quickstart is the literal `uv run triagedesk demo`; `uv run` auto-syncs the locked environment from the committed uv.lock, so the `uv sync --locked` two-step is unnecessary and removed (D11-09/D11-11)"
  - "The one-command claim is guarded by driving the documented invocation through the public `triagedesk.cli.main`, with the lazy `run_demo`/`serve` seams spied (D11-10)"
  - "The README keeps the `uv.lock` rationale explicit so a future change to uv's sync default is visible to a reader (the honest boundary of assumption A2)"

patterns-established:
  - "README quickstart drift guard: mirror tests/test_desk_runbook.py — read fenced blocks, extract `uv run triagedesk <cmd>` invocations, drive the public `main`, spy the seams"

requirements-completed: [DOCS-04]

coverage:
  - id: D1
    description: "The README quickstart is the literal one-command path `uv run triagedesk demo`, with no separate install step, and names the optional second command `uv run triagedesk desk`"
    requirement: DOCS-04
    verification:
      - kind: unit
        ref: "tests/test_docs_final.py#test_readme_has_the_one_command_quickstart"
        status: pass
      - kind: unit
        ref: "tests/test_readme_runbook.py#test_readme_documents_the_bare_one_command_path"
        status: pass
      - kind: unit
        ref: "tests/test_readme_runbook.py#test_readme_documents_the_optional_second_command"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every `uv run triagedesk <cmd>` invocation the README documents is accepted by the shipped CLI (exit 0) and reaches its spied seam, so the documented invocation cannot drift from the shipped one"
    requirement: DOCS-04
    verification:
      - kind: integration
        ref: "tests/test_readme_runbook.py#test_documented_invocations_are_accepted_by_the_cli"
        status: pass
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-10-13
status: complete
---

# Phase 11 Plan 03: The Literal One-Command Quickstart Summary

**README quickstart is now the literal `uv run triagedesk demo` — no separate install step — and the claim is proven against the shipped `triagedesk.cli.main` by a CLI-driving drift guard.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-10-13T07:37:36Z
- **Completed:** 2026-10-13T07:39:58Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Replaced the README's two-step install (`uv sync --locked` then `uv run triagedesk demo`) with the
  literal one-liner `uv run triagedesk demo`, stating on a comment line above the invocation that
  `uv run` syncs the locked environment from the committed `uv.lock` — so a stranger needs no separate
  install step.
- Named the optional second command, `uv run triagedesk desk` (the local desk surface), in the same
  fenced block.
- Corrected `tests/test_docs_final.py::test_readme_has_the_one_command_quickstart`, which previously
  *required* the two-step install: it now asserts the one-liner is present **and** `uv sync --locked`
  is absent.
- Added `tests/test_readme_runbook.py`, which reads the README's fenced blocks, extracts every
  `uv run triagedesk <cmd>` invocation, and drives each through the shipped `triagedesk.cli.main` with
  the `run_demo`/`serve` seams spied — so the documented invocation cannot drift from the shipped CLI.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace the two-step quickstart with the literal one-liner and correct its guard** - `bfbb184` (docs)
2. **Task 2: Guard the README's claim by driving the documented invocation through the shipped CLI** - `11c8b54` (test)

**Plan metadata:** skipped (`.planning/` docs commit disabled — `commit_docs: false`)

## Files Created/Modified

- `README.md` — §Quickstart is the literal one-command path plus the optional desk command; the
  offline/`--online` sentence, the `--beat` sentence and the `docs/DEMO.md` link are preserved (no
  demo beat is restated — DRY).
- `tests/test_docs_final.py` — `test_readme_has_the_one_command_quickstart` now requires the one-liner
  and forbids the two-step install; every other guard in the file is unchanged.
- `tests/test_readme_runbook.py` (new) — the README-vs-CLI drift guard, mirroring
  `tests/test_desk_runbook.py`.

## The exact README quickstart text

````markdown
## Quickstart

From a clean clone, one command:

```bash
# The whole demo, offline, on the bundled synthetic fixture. `uv run` syncs the locked
# environment from the committed uv.lock before it runs — there is no separate install step.
uv run triagedesk demo

# The optional second command: serve the local desk surface (loopback only, no external request).
uv run triagedesk desk
```
````

## The documented invocations the new guard drives

`tests/test_readme_runbook.py` extracts these argv lists from the README's fenced blocks and drives
each through `triagedesk.cli.main`:

| Documented line | argv driven through `main` | Seam spied | Assertion |
|---|---|---|---|
| `uv run triagedesk demo` | `["demo"]` | `triagedesk.demo.run.run_demo` (async stub → 0) | exit 0, `run_demo` reached |
| `uv run triagedesk desk` | `["desk"]` | `triagedesk.desk.server.serve` (sync spy) | exit 0, `serve` reached |

The guard derives no flag list from a private parser helper — it drives the public `main` surface
only, exactly as `tests/test_desk_runbook.py` does. No model, server or demo is started.

## Decisions Made

- The README quickstart is the literal one-liner `uv run triagedesk demo`; `uv run` auto-syncs from
  the committed lock, so the two-step install is removed (D11-09, D11-11).
- The one-command claim is guarded by a CLI-driving test (D11-10) rather than a weaker
  string-presence check, so the documented invocation is the shipped one.
- The README keeps the `uv.lock` rationale explicit, so a future change to uv's sync default is
  visible to a reader — the honest disclosure of the boundary of assumption A2 (the guard proves the
  invocation, not the clean-clone sync itself).

## Deviations from Plan

None - plan executed exactly as written.

## Scope Note (D11-11 blast radius)

D11-11 / the orchestrator's constraint say to correct any other documented quick-start command that
no longer holds. The only documented command that **no longer holds** is the README's required
two-step install (the README claimed "one command" while showing two) — that is corrected here. The
runbooks `docs/DEMO.md` and `docs/DESK.md` present `uv sync --locked` under a separate
**"One-time setup"** heading, not as part of a one-command quickstart, and it remains a valid
(optional) deterministic-install step, so nothing there is now false and the plan's declared
`files_modified` was not exceeded. The stale "two commands" framing in `STATUS.md` (G3) and
`docs/REQUIREMENTS.md` (SB-3) is tracking-doc refresh scope for Phase 12 (per `11-RESEARCH.md`,
STATUS.md is refreshed in Phase 12), not this plan.

## Threat Flags

None - the change is documentation plus a test that reuses existing patterns; no new surface (the
plan's T-11-09/T-11-10/T-11-11 mitigations are the corrected guard and the CLI-driving guard; T-11-SC
holds — no package was added).

## Self-Check

- FOUND: README.md
- FOUND: tests/test_docs_final.py
- FOUND: tests/test_readme_runbook.py
- FOUND: bfbb184
- FOUND: 11c8b54
