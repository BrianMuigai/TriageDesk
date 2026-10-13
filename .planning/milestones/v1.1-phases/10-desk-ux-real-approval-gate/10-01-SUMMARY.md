---
phase: 10-desk-ux-real-approval-gate
plan: 01
subsystem: ui
tags: [http.server, langgraph, human-in-the-loop, approval-gate, stdlib, html, css]

# Dependency graph
requires:
  - phase: 06-durable-execution-idempotent-gate
    provides: "durable.run_to_gate / approval_decision / resume_thread (the ONE pause/resume plumbing)"
  - phase: 08-calibrated-confidence-abstention
    provides: "the typed confidence / no_match signal (the banner trigger, consumed by 10-02)"
  - phase: 09-retrieval-grounding-borrowed-mcp-depth
    provides: "the evidence channel (consumed by 10-02)"
provides:
  - "the triagedesk.desk presentation bridge: form -> graph -> suggestion card -> real gate -> exactly one queue row"
  - "the 'desk' CLI subcommand (loopback-only, harden-first, lazy handler import)"
  - "the desk/static/index.html + styles.css hand-authored assets"
affects: [10-02, 10-03, verification]

# Actuals (#2632) — pairs with the plan's estimate (70000 tokens / 2 tasks / low confidence).
# Same estimateTokens scale: chars/4 over the realized diff, never a harness token count.
actuals:
  tokens: 11590
  tasks: 2
  commits: 2
  plan_head_before: bb19fc17652ecc9577b69f9f23acd9d503bfb759
  plan_head_after: fe7d393e5ec62b4b943195c14cbf26e70e666ad6

# Tech tracking
tech-stack:
  added: []  # no new dependency (D10-16)
  patterns:
    - "presentation bridge over the ONE pause/resume plumbing — no second checkpointer lifecycle, no commit path"
    - "static markup as served assets, not Python string literals (keeps the no-duplicated-SATS guard green)"
    - "loopback-only stdlib http.server with a fixed two-name asset allowlist and escaped output"

key-files:
  created:
    - src/triagedesk/desk/__init__.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - tests/test_desk.py
  modified:
    - src/triagedesk/cli.py
    - pyproject.toml

key-decisions:
  - "The bridge reuses durable.run_to_gate / approval_decision / resume_thread; it adds no second checkpointer lifecycle and no commit path (D10-11/D10-12)."
  - "GET / renders the empty state through the ONE template rather than serving the raw file, so no unsubstituted placeholder is ever exposed."
  - "Colour names live only in styles.css; the Python emits the generic colour-{name} class, keeping a SATS literal out of src/**/*.py (CONVENTIONS §1)."
  - "serve() takes keyword-only host/port/db_path; the CLI imports the handler lazily inside main, after harden_offline() (WR-06)."

patterns-established:
  - "A presentation layer imports the shipped seams and re-derives nothing; its only mapping is a substrate colour string -> a CSS class."
  - "A stdlib HTTP surface proves its safety structurally (AST import scan, ordered-event hardening test, asset scan) — never by assertion."

requirements-completed: [UX-02, UX-03, UX-04]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "A vitals form validates through the ONE CaseInput schema, renders the empty state, then the graph's suggested priority card framed as a suggestion (colour + name, target time, why-vitals beside adjacent citations)."
    requirement: "UX-02"
    verification:
      - kind: e2e
        ref: "tests/test_desk.py#test_form_to_card_to_gate_to_commit"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_out_of_range_vital_renders_the_schema_message"
        status: pass
    human_judgment: false
  - id: D2
    description: "A named-human approve resumes the paused thread and lands EXACTLY one queue row through the gated tool; the response carries the committed copy."
    requirement: "UX-03"
    verification:
      - kind: e2e
        ref: "tests/test_desk.py#test_form_to_card_to_gate_to_commit"
        status: pass
    human_judgment: false
  - id: D3
    description: "The desk package cannot commit on its own, binds loopback only, hardens offline before its handler, makes no external request, and escapes untrusted input."
    requirement: "UX-04"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_no_self_commit_path_in_the_desk_package"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_make_server_binds_localhost_only"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_desk_entry_point_hardens_offline_before_serve"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_served_assets_make_no_external_request"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_untrusted_complaint_escapes_markup"
        status: pass
    human_judgment: false
  - id: D4
    description: "The visual paint: the card layout, the CTA label swap while a submit is in flight, and the gate button labels at 1024px/1280px."
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_index_html_loading_swap_on_submit"
        status: pass
    human_judgment: true
    rationale: "The loading-row copy swap is machine-checked in markup, but the painted state and the no-clip check at the two declared widths need a human/visual backstop (UI-SPEC backstop rows)."

duration: 13min
completed: 2026-10-12
status: complete
---

# Phase 10 Plan 01: Desk Surface — Suggestion Card & Real Approval Gate Summary

**A dependency-free local desk page turns a vitals form into the graph's sourced priority suggestion and lets a named human approve it through the real gate — landing exactly one queue row — with the whole surface provably unable to commit, escape, or egress.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-10-12T20:39:41Z
- **Completed:** 2026-10-12T20:52:42Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- The `triagedesk.desk` package: the ONE presentation bridge (`form_to_case`, `submit_case`, `decide`, `render_state`, `make_server`, `serve`, `DeskHandler`), which validates the vitals form through the ONE `CaseInput` schema, runs the case to the gate over `durable.run_to_gate`, renders the graph's own interrupt payload as a **suggestion** card (colour + its name as text, target time, each fired rule's `detail` beside its adjacent citation, not-recorded vitals, case id), and resumes a paused thread with a named human decision through `durable.approval_decision` + `durable.resume_thread`.
- The real gate carries the paused thread identity as a hidden `thread_id` field rendered from the interrupt payload's `case_id` (the ONE content-derived thread id); the `/decision` POST returns it and lands exactly one queue row through the gated tool.
- Two hand-authored assets (`desk/static/index.html`, `desk/static/styles.css`) built to the UI-SPEC Copywriting Contract and token tables — no CDN, no webfont, no build step, no new dependency; the colour names live only in the CSS, so no SATS literal enters Python.
- The `desk` CLI subcommand (`--host`/`--port`/`--db`) whose handler is imported lazily inside `main` after `harden_offline()`.
- A hermetic end-to-end and structural proof suite: the surface is proven incapable of committing (AST import scan), bound to loopback only, hardened before its handler, external-request-free, and escaping the untrusted complaint.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end — a vitals form becomes a rendered suggestion and a real approve commits one row** — `e973635` (feat)
2. **Task 2: The structural proofs — no self-commit path, localhost-only bind, harden-first entry point, escaped output** — `fe7d393` (test)

**Plan metadata:** committed separately (docs) — see the phase directory.

## Files Created/Modified

- `src/triagedesk/desk/__init__.py` — the package seam, re-exporting the public names (the `demo/__init__.py` shape).
- `src/triagedesk/desk/server.py` — the ONE presentation bridge (the phase's core file).
- `src/triagedesk/desk/static/index.html` — the hand-authored page (UI-SPEC copy, verbatim).
- `src/triagedesk/desk/static/styles.css` — the UI-SPEC token set + the five per-colour swatch classes.
- `src/triagedesk/cli.py` — the `desk` subcommand (lazy handler import after `harden_offline()`).
- `pyproject.toml` — the `"src/triagedesk/desk/**" = ["TID251"]` per-file ignore (mirrors `replay.py`).
- `tests/test_desk.py` — the hermetic end-to-end and structural proofs.

## Decisions Made

- **`GET /` renders the empty state through the ONE template** rather than serving the raw `index.html` file — so no unsubstituted `$placeholder` is ever exposed, and the empty state (`No case yet`) is what a first visit shows. Only `styles.css` is served as raw bytes, and only by allowlist.
- **`harden_offline` patch target is `triagedesk.cli.harden_offline`** (not the `observability.offline` attribute) because `cli.py` binds the name into its own namespace at import time; the ordered-event proof (`["harden", "serve"]`) therefore tests the *effective* call.
- **The structural proofs were split into a second commit** so each task is atomic, matching the plan's two-task file lists (both name `tests/test_desk.py`).
- **Requirement completion follows the established per-plan convention** (09-01/09-03 both recorded the shared `AGENT-03`): UX-02/UX-03/UX-04 are recorded as this plan's declared requirements, delivered incrementally (10-01 ships the committable half; 10-02/10-03 ship the banner/deferred/evidence and the quickstart halves).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `GET /` served the raw template, so the empty state never rendered**
- **Found during:** Task 1 (end-to-end proof)
- **Issue:** The plan's `do_GET` wording ("serve `index.html` for `/`") served the raw file bytes, which left the `$state_panel`/`$card`/`$gate` placeholders unsubstituted and rendered no `No case yet` heading — failing the plan's own empty-state acceptance criterion.
- **Fix:** `/` (and `/index.html`) now render the empty state through `render_state()`; only the CSS is served as raw bytes by allowlist. No path is built from `self.path`.
- **Files modified:** `src/triagedesk/desk/server.py`
- **Verification:** `test_form_to_card_to_gate_to_commit` asserts the empty-state copy is present and no card/gate region renders.
- **Committed in:** `e973635` (Task 1 commit)

**2. [Rule 1 - Bug] The CSS header comment tripped the offline-asset proof**
- **Found during:** Task 2 (offline-asset proof)
- **Issue:** The comment literally contained the substrings `@import` and `url(`, which the asset scan asserts are absent.
- **Fix:** Reworded the comment to describe the same intent without the literal substrings.
- **Files modified:** `src/triagedesk/desk/static/styles.css`
- **Verification:** `test_served_assets_make_no_external_request` passes.
- **Committed in:** `e973635` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs).
**Impact on plan:** Both fixes were required for the plan's own acceptance criteria to hold. No scope creep; no frozen-spine change.

## Issues Encountered

- A leftover `spans.jsonl` at the repository root (created by an out-of-band probe script, not by the suite) failed `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`. It is a gitignored generated artefact; removing it restored the full suite to green. The suite itself writes spans only to `tmp_path` via the autouse conftest seam.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The committable path (form → graph → card → gate → approve) is proven end-to-end and hermetic; the `desk` entry point resolves and exits 0 on `--help`.
- Full suite green at 353 baseline + 9 new desk tests = **362 passed**.
- Ready for plan 10-02 (the uncertainty banner on the deferred terminal, the read-only card, the evidence list, the edit/dismiss/fail-safe branches) and plan 10-03 (the `docs/DESK.md` quickstart + the `D23` decision row).
- The frozen spine is byte-identical: no change under `src/triagedesk/core/`, `graph/`, `mcp/`, `store/`, `evals/` or `data/`.

---
*Phase: 10-desk-ux-real-approval-gate*
*Completed: 2026-10-12*

## Self-Check: PASSED

- All created files exist (desk package, both assets, test suite, this SUMMARY).
- Both task commits exist and are ancestors of HEAD: `e973635`, `fe7d393`.
