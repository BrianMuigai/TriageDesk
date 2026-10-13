---
phase: quick
plan: "261013-tqi"
subsystem: ui
tags: [refactor, srp, dry, solid, desk, http, pydantic, facade, python]

# Dependency graph
requires: []
provides:
  - "8 single-responsibility `triagedesk/desk/` modules: copy, markup, assets, pipeline, forms, card, gate, views"
  - "`desk/server.py` reduced to the HTTP layer + the public facade that re-exports every moved name"
  - "README `## Running the demos` section covering the storyboard demo and the desk surface"
affects: [desk, README]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# chars/4 over the realized diff (NOT a harness token count).
actuals:
  tokens: 20682    # chars/4 over the realized diff (82728 diff chars)
  tasks: 3
  commits: 3
  plan_head_before: f4df184babdf6fe5231d316ad9f45df4ea2399b8
  plan_head_after: 39e9cc862e7ecfe8496e5e889c88235971e9ff68

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "God-module split by SRP with a facade: `server.py` keeps the HTTP layer and re-imports every moved public name so `triagedesk.desk.server` stays the one seam the CLI, package `__init__` and the suite reach"
    - "Monkeypatch seam preserved by bare-name lookup through the defining module's globals (`server.decide`/`server.serve`)"

key-files:
  created:
    - src/triagedesk/desk/copy.py
    - src/triagedesk/desk/markup.py
    - src/triagedesk/desk/assets.py
    - src/triagedesk/desk/pipeline.py
    - src/triagedesk/desk/forms.py
    - src/triagedesk/desk/card.py
    - src/triagedesk/desk/gate.py
    - src/triagedesk/desk/views.py
  modified:
    - src/triagedesk/desk/server.py
    - README.md

key-decisions:
  - "Two leaf modules (`markup.py`, `assets.py`) were added beyond the agreed six so `_escaped` and `STATIC_DIR`/`_ASSETS` each have ONE home importable by the render modules without an import cycle back through `server.py` (the plan's justification)."
  - "`DeskHandler._handle_decision`/`_handle_case` stay in `server.py` and call the bare names `decide`/`submit_case`, so a function's defining-module global lookup keeps the `triagedesk.desk.server.decide` monkeypatch seam live."
  - "`_CSRF_FIELD` + `_csrf_field` live in `forms.py` (the lowest render module) because both the gate and the vitals form render the field; `gate` and `views` import it with no cycle."
  - "No test was edited — a pure move that required a test change would have meant a broken seam."

patterns-established:
  - "SRP split + facade: each desktop concern (copy, escaping, assets, runner, form, card, gate, views) has exactly one module; the former god-module becomes the HTTP layer and the re-export surface."

requirements-completed: [QUICK-261013]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Eight SRP `desk/` modules own copy, escaping, assets, the graph runner, the vitals form, the card, the gate and the view assembly; `server.py` is the HTTP layer + facade"
    requirement: QUICK-261013
    verification:
      - kind: integration
        ref: "tests/test_desk.py (full, incl. structural import guards) — 84 passed"
        status: pass
      - kind: other
        ref: "grep: `__file__).parent` matches assets.py only; `def _escaped` matches markup.py only; no `store.queue`/`mcp.server` import under desk/"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every name the suite reaches or patches is still a `triagedesk.desk.server` attribute; the `decide`/`serve` monkeypatch seams hold with zero test edits"
    requirement: QUICK-261013
    verification:
      - kind: unit
        ref: "tests/test_desk.py::test_a_failure_is_never_an_approve + ::test_desk_entry_point_hardens_offline_before_serve — 2 passed"
        status: pass
      - kind: other
        ref: "import smoke: getattr(server, n) for all 13 facade names — OK"
        status: pass
    human_judgment: false
  - id: D3
    description: "README gains a `## Running the demos` section whose every fenced invocation is CLI-accepted and reaches its seam; the two required command substrings remain"
    requirement: QUICK-261013
    verification:
      - kind: unit
        ref: "tests/test_readme_runbook.py + tests/test_docs_final.py — passed"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-10-13
status: complete
---

# Quick Task 261013-tqi: Split the desk server module by SRP Summary

**The 1169-line `desk/server.py` god-module split into eight single-responsibility modules behind a facade `server.py`, with the full desk suite and every runbook guard green and zero test edits.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-10-13T21:24:30+03:00
- **Completed:** 2026-10-13T21:42:29+03:00
- **Tasks:** 3
- **Files modified:** 10 (9 source/doc, 1 net new modules count 8)

## Accomplishments
- Split `desk/server.py` into `copy`, `markup`, `assets`, `pipeline`, `forms`, `card`, `gate`, `views` — each owning exactly one responsibility — leaving `server.py` as the HTTP layer plus the public facade.
- Preserved the monkeypatch seams: `_handle_decision` calls the bare name `decide` (a `server` global imported from `pipeline`), so `monkeypatch.setattr("triagedesk.desk.server.decide", …)` is still observed; `serve` remains a `server` attribute.
- DRY honoured: `_escaped` has ONE home (`markup.py`), `STATIC_DIR`/`_ASSETS` have ONE home (`assets.py`), and every user-facing string has ONE home (`copy.py`) — all imported, none restated.
- Added the README `## Running the demos` section documenting the storyboard demo (offline default, `--online`, `--beat`, `--durable` + the exact `resume` follow-up) and the desk surface (command, URL, Ctrl-C, loopback-only, walkthrough link), folding the Quickstart's duplicated drive prose into it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract the shared leaves and the graph runner** - `c55b08f` (refactor)
2. **Task 2: Extract the render modules; finish server.py as the HTTP layer + facade** - `28404dc` (refactor)
3. **Task 3: Document how to run the demos in the README** - `39e9cc8` (docs)

**Plan metadata:** (docs commit handled separately by the orchestrator — `commit_docs: false`)

## Files Created/Modified
- `src/triagedesk/desk/copy.py` - the ONE home for every user-facing string (`_BANNER_*`, `_EMPTY_*`, `_CARD_FRAMING`, `_FAILURE_COPY`, …)
- `src/triagedesk/desk/markup.py` - the ONE escaping rule `_escaped` (ASVS V5)
- `src/triagedesk/desk/assets.py` - the ONE `STATIC_DIR` + the fixed `_ASSETS` allowlist
- `src/triagedesk/desk/pipeline.py` - the graph-runner seam (`_tools_for`, `submit_case`, `decide`)
- `src/triagedesk/desk/forms.py` - `form_to_case` + the schema-derived controls + `_TRUTHY`/`_VITALS_LAYOUT`/`_CSRF_FIELD`/`_csrf_field`
- `src/triagedesk/desk/card.py` - `_colour_class`, `_why_vitals_rows`, `_evidence_rows`, `_card_html`, `_card_payload_from_state`
- `src/triagedesk/desk/gate.py` - `editable_colours`, `_gate_html`
- `src/triagedesk/desk/views.py` - `banner_trigger`, `terminal_kind`, the view builders, `render_state`
- `src/triagedesk/desk/server.py` - the HTTP layer (`DeskServer`, `DeskHandler`, `make_server`, `serve`, guards) + the facade re-exports
- `README.md` - the new `## Running the demos` section; Quickstart drive prose folded in (DRY)

## Decisions Made
- Added the two leaf modules (`markup.py`, `assets.py`) the plan justified: they are the only way to give `_escaped` and `STATIC_DIR`/`_ASSETS` one home each without an import cycle back through `server.py` (which imports `views` for the facade). The render graph is acyclic: nothing imports `server`.
- Kept `_handle_decision`/`_handle_case` in `server.py` and left them calling the bare names `decide`/`submit_case` — not `pipeline.decide(...)` — because the bare name is what makes the `triagedesk.desk.server.decide` patch hold at the call site.
- `_CSRF_FIELD`/`_csrf_field` placed in `forms.py` (the lowest render module), so both `gate.py` and `views.py` import it without a cycle.
- Did NOT add `_escaped` to `server.py` after the split — nothing there uses it, so importing it would be an F401.

## Deviations from Plan

### Plan-checker advisories applied (both required, strengthening the verify to match the plan's assertions)

**1. [Verification] Appended `uv run mypy src/triagedesk/desk` to Tasks 1 and 2**
- **Found during:** Tasks 1 and 2 verify.
- **Issue:** The plan's tasks assert mypy stays clean but the `<automated>` chains only ran `pytest … && ruff check`.
- **Fix:** Ran `uv run mypy src/triagedesk/desk` as part of each task's verification — both clean (`Success: no issues found in N source files`).
- **Files modified:** none (verification only).

**2. [Verification] Included `tests/test_docs_final.py` in Task 3's pytest run**
- **Found during:** Task 3 verify.
- **Issue:** `tests/test_docs_final.py` is also a README-content guard (one-command quickstart, no `uv sync --locked`, no stale pre-build rows, `EVALS.md`/`E-09` present) but was absent from Task 3's invocation.
- **Fix:** Ran `tests/test_docs_final.py` alongside the three runbook suites — all green.
- **Files modified:** none (verification only).

**Total deviations:** 0 code deviations; 2 verification-chain strengthenings (both mandated by the plan-checker advisories).
**Impact on plan:** None on scope. The move executed exactly as written; no behaviour, string, route, header, guard or docstring-of-a-moved-function changed.

## Issues Encountered
None. Every task's focused verification passed on the first run after the edit; the only in-flight correction was removing the now-duplicate `_escaped` definition from `server.py` during Task 1 (expected, and caught by ruff F811/F821 before commit).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The desk package is now readable module-by-module; each concern has one home.
- `server.py` remains the single seam (`desk/__init__.py`, `cli.py` and the suite are untouched).
- No new dependency; `pyproject.toml`/`uv.lock` untouched. `demo/`'s private imports, the `desk`/`demo` folder split, `docs/assets/desk-demo.mp4`, and the two pre-existing working-tree changes (`docs/assets/architecture.pdf`, `docs/render-architecture.sh`) were left alone.

## Self-Check

- [x] `src/triagedesk/desk/{copy,markup,assets,pipeline,forms,card,gate,views}.py` exist
- [x] Commits `c55b08f`, `28404dc`, `39e9cc8` exist
- [x] Zero `tests/` churn (`git diff --name-only c55b08f~1..HEAD -- tests/` → empty)
- [x] Focused suite + `test_docs_final.py` green (93 passed); `ruff check` clean; `mypy src/triagedesk/desk` clean
- [x] Structural greps: `__file__).parent` → `assets.py` only; `def _escaped` → `markup.py` only; no `store.queue`/`mcp.server` under `desk/`
- [x] Facade smoke: all 13 reached/patched names present on `triagedesk.desk.server`

**Self-Check: PASSED**
