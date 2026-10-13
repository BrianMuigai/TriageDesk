---
phase: 10-desk-ux-real-approval-gate
plan: 02
subsystem: ui
tags: [http.server, langgraph, human-in-the-loop, approval-gate, uncertainty-banner, stdlib, html, css]

# Dependency graph
requires:
  - phase: 10-desk-ux-real-approval-gate
    plan: 01
    provides: "the desk bridge (render_state, the template placeholders, the committable card+gate) and its test suite"
  - phase: 08-calibrated-confidence-abstention
    provides: "the typed confidence / no_match deferral signal (the banner trigger)"
  - phase: 09-retrieval-grounding-borrowed-mcp-depth
    provides: "the evidence channel (the evidence list)"
  - phase: 06-durable-execution-idempotent-gate
    provides: "durable.run_to_gate / approval_decision / resume_thread / DurableError (the ONE pause/resume plumbing)"
provides:
  - "the loud uncertainty banner driven by the typed signal (no_match OR confidence.deferral), on the terminal"
  - "the read-only deferred terminal (banner + read-only card + no gate) vs the committable gate (card + gate, no banner)"
  - "the attributed evidence list read from the paused state snapshot"
  - "the fail-safe gate: editable_colours() = the gate's own accepted set, dismiss/timeout commit nothing, the schema's own rejection, and explicit existed=True handling"
affects: [10-03, verification, ship]

# Actuals (#2632) — pairs with the plan's estimate (80000 tokens / 3 tasks / low confidence).
# Same estimateTokens scale: chars/4 over the realized diff, never a harness token count.
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
  plan_head_before: fe7d393e5ec62b4b943195c14cbf26e70e666ad6
  plan_head_after: e7236598871754d1253dcb3ac7a32ad9d9ff9ae1

# Tech tracking
tech-stack:
  added: []  # no new dependency (D10-16)
  patterns:
    - "a presentation bridge reads the graph's TYPED channels for the uncertainty trigger and terminal kind — never a free-text reason, evidence.no_match, or missing_vitals alone"
    - "the interrupt payload and the paused state snapshot are read together (the payload omits evidence/confidence)"
    - "the edit control is derived from the SAME expression the gate's token validator uses, so the surface cannot offer a decision the gate refuses"

key-files:
  created: []
  modified:
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - tests/test_desk.py

key-decisions:
  - "The deferred read-only card carries a dedicated framing line ('Not confirmed and not queued — this is what the system computed from the vitals alone.') because the UI-SPEC state contract requires the framing while its Copywriting Contract omits a row for it (documented deviation)."
  - "A non-DurableError server/graph failure renders the UI-SPEC _FAILURE_COPY; a DurableError (the gate's own refusal: blank identity, missing colour, no pending gate) renders its own message — the surface restates no gate logic."
  - "terminal_kind checks the deferral channel FIRST, so a deferred repeat submission stays a deferred terminal (never a gate); existed=True re-renders card+gate only when a pending gate remains, and a committed thread shows the gate's own outcome."
  - "The timeout panel is rendered inside the gate markup so it exists only where a timeout can apply; the bridge holds no server-side deadline (a timeout is simply 'no decision POST ever arrives')."

patterns-established:
  - "The banner body is trigger-conditional: one banner rule, two bodies, so the banner never asserts a fact its trigger did not establish."
  - "Colour is never the only signal: the colour name is rendered as text beside the swatch and the generic colour-{name} class."

requirements-completed: [UX-01, UX-02, UX-03]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "The loud uncertainty banner fires from the typed signal only — no_match OR confidence.deferral — with a trigger-conditional body, verbatim headline, and aria-live region."
    requirement: "UX-01"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_banner_trigger_reads_only_the_typed_signal"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_banner_body_is_trigger_conditional"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_no_banner_for_evidence_no_match_or_missing_vitals"
        status: pass
      - kind: e2e
        ref: "tests/test_desk.py#test_deferred_case_renders_the_banner_read_only_card_and_no_gate"
        status: pass
    human_judgment: false
  - id: D2
    description: "A deferred case renders the banner + a READ-ONLY card + the deferred copy and NO gate; a committable case renders the card + the real gate and no banner (D10-17)."
    requirement: "UX-01"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_terminal_kind_prefers_the_deferral_channel"
        status: pass
      - kind: e2e
        ref: "tests/test_desk.py#test_deferred_end_to_end_is_read_only"
        status: pass
    human_judgment: false
  - id: D3
    description: "The evidence list renders the ranked evidence.passages (label + citation) read from the paused state snapshot, or the verbatim no-evidence line when zero matched (UX-02)."
    requirement: "UX-02"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_evidence_list_renders_each_passage_in_rank_order"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_evidence_list_renders_the_no_evidence_line"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_baseline_why_vitals_row_is_never_an_empty_list"
        status: pass
    human_judgment: false
  - id: D4
    description: "The fail-safe gate: dismiss commits nothing, a timeout approves nothing, the edit control offers exactly the gate's accepted set, an invalid field surfaces the ONE schema's rejection, and a repeat submission reuses its thread (UX-03)."
    requirement: "UX-03"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_dismiss_commits_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_timeout_is_no_approve"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_edit_set_equals_the_gate_set"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_schema_rejection_renders_the_message_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_existed_repeat_submission_reuses_the_thread"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_a_failure_is_never_an_approve"
        status: pass
    human_judgment: false
  - id: D5
    description: "The rendered copy is provably clean (no prohibited token, no percentage), every colour is labelled, and the suite launches no borrowed subprocess (D10-05, D10-15)."
    requirement: "UX-02"
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_rendered_copy_carries_no_forbidden_token"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_no_rendered_string_shows_a_percentage"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_colour_label_accompanies_every_rendered_colour"
        status: pass
      - kind: unit
        ref: "tests/test_desk.py#test_submit_path_launches_no_borrowed_store"
        status: pass
    human_judgment: false
  - id: D6
    description: "The visual paint: the banner's caution-tint treatment, the long-citation/evidence wrap inside the card column with no horizontal scroll at 1280px/1024px, and the 'Dismiss (commit nothing)' label not clipping at 1024px."
    verification:
      - kind: unit
        ref: "tests/test_desk.py#test_served_css_declares_wrapping_rules"
        status: pass
    human_judgment: true
    rationale: "The wrap/clip rules are machine-checked as CSS declarations (a proxy), but the painted banner and the no-clip check at the two declared widths need a human/visual backstop (UI-SPEC backstop rows)."

# Metrics
duration: 22min
completed: 2026-10-13
status: complete
---

# Phase 10 Plan 02: The Uncertainty Banner, the Read-Only Deferred Terminal & the Fail-Safe Gate Summary

**The E-09 class becomes a loud typed-signal banner on a read-only deferred terminal with no gate, the evidence grounding the colour is read from the paused state, and every gate branch — dismiss, timeout, edit set, schema rejection, repeat submission — is proven incapable of committing without a named human.**

## Performance

- **Duration:** 22 min (the measured span from the first to the last task commit)
- **Started:** 2026-10-12T20:51:58Z
- **Completed:** 2026-10-12T21:14:01Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- The loud uncertainty banner: `banner_trigger` reads the graph's typed channels only (`no_match` OR `confidence.deferral`), with a trigger-conditional body so the banner never asserts a fact its trigger did not establish; `terminal_kind` selects the terminal copy from the typed `confidence`/`escalation`/`recovery` channels (never a free-text reason).
- The honest deferred terminal (D10-17): a deferred case renders the banner plus a **read-only** suggestion card and the deferred copy with **no** approve/edit/dismiss control — the deferral routes to a terminal, so there is nothing to approve and nothing can be queued. A committable case renders the card plus the real gate and no banner.
- The attributed evidence list: read from the paused state snapshot (`evidence.passages` — the interrupt payload omits it), one ranked row per passage with its label and citation, or the verbatim no-evidence line; the baseline why-vitals row is the scorer's own `tews_baseline` entry.
- The fail-safe gate (UX-03): `editable_colours()` is the SAME expression `ApprovalToken` validates against (four colours today; no BLUE), the radio group preselects nothing, dismiss returns `refused=True`/`committed=False` and writes no row, a timeout is "no decision POST ever arrives" (no row, no preselection), an invalid field surfaces the ONE schema's own message, and `existed=True` reuses the content-addressed thread instead of forking one.
- 26 new hermetic tests (9 → 35 in `tests/test_desk.py`); the full suite is green at **388 passed** (362 baseline + 26).

## Task Commits

Each task was committed atomically:

1. **Task 1: The uncertainty banner, the read-only deferred terminal, and the evidence list** - `96e9552` (feat)
2. **Task 2: The fail-safe gate — dismiss, timeout, the gate's own editable set, the schema's rejection, the `existed` re-submit** - `0ad1a27` (test)
3. **Task 3: The copy and hermeticity proofs — no forbidden token, no percentage, no borrowed subprocess, the deferred end-to-end** - `e723659` (test)

**Plan metadata:** the SUMMARY/STATE/ROADMAP are written but **not committed** — `.planning/config.json` sets `commit_docs: false` (the SDK `commit` verb returns `skipped_commit_docs_false`).

_Note: the surface implementation (the banner, the deferred render, the gate) landed in the Task 1 commit because the three changed files carry one cohesive edit; the fail-safe and copy proofs are the separate Task 2/3 commits (mirroring 10-01's split of code-then-proofs)._

## Files Created/Modified

- `src/triagedesk/desk/server.py` - `banner_trigger`/`terminal_kind`/`editable_colours`; the banner, the read-only card framing, the evidence list, the card/evidence row helpers, the gate radio group + hidden thread id + timeout panel, the deferred/escalated/recovery/existed/committed branches, and the DurableError-vs-failure error split.
- `src/triagedesk/desk/static/index.html` - the gate loading/timeout client script (a decision in flight disables the controls; the deadline reveals the timeout panel without submitting).
- `src/triagedesk/desk/static/styles.css` - the `.banner-headline`/`.banner-body` caution treatment, the `.evidence-list`, the `.colour-choices`/`.colour-choice` gate control, and the wrapping rules (`overflow-wrap`/`word-break`) on the card rows, the banner headline and the complaint block.
- `tests/test_desk.py` - the banner, deferred, evidence, fail-safe, schema-rejection, `existed` and copy proofs (26 new tests).

## Decisions Made

- **The read-only deferred card's framing line is new copy.** The UI-SPEC state contract requires the card to be "explicitly framed as not confirmed and not queued", but its Copywriting Contract carries no row for it; a dedicated line was added (documented as a deviation).
- **`_FAILURE_COPY` for a non-DurableError failure.** The handlers now render the UI-SPEC server/graph-failure copy for an unexpected exception, while a `DurableError` (the gate's own refusal) still shows its own message — the surface restates no gate logic.
- **`existed=True` is terminal-aware.** `terminal_kind` is checked first, so a deferred repeat submission renders the deferred terminal (never a gate); a committed thread renders the gate's own outcome. This is the explicit D10-19 handling over the session checkpoint file.
- **The timeout panel is gate-scoped.** It is rendered inside the gate markup so it exists only where a timeout can apply, and the bridge holds no server-side deadline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] The read-only deferred card needed a framing line the UI-SPEC Copywriting Contract omits**
- **Found during:** Task 1 (the deferred render)
- **Issue:** The plan requires the read-only card to be "explicitly framed as not confirmed and not queued" (the UI-SPEC state contract's Deferred row), but the UI-SPEC Copywriting Contract carries no row for a read-only card framing — the only relevant string is the deferred terminal copy, which is rendered separately as the state panel.
- **Fix:** Added the dedicated constant `_READ_ONLY_FRAMING` ("Not confirmed and not queued — this is what the system computed from the vitals alone.") and used it as the read-only card's framing line, keeping the deferred terminal copy as the state panel.
- **Files modified:** `src/triagedesk/desk/server.py`
- **Verification:** `test_deferred_case_renders_the_banner_read_only_card_and_no_gate` asserts the framing and the deferred copy render with no gate.
- **Committed in:** `96e9552` (Task 1 commit)

**2. [Rule 2 - Missing Critical] A server/graph failure showed the raw exception string instead of the UI-SPEC error copy**
- **Found during:** Task 2 (the fail-safe gate)
- **Issue:** The 10-01 handlers caught every exception and rendered `str(exc)`. The UI-SPEC error/approval-gate row requires the fixed server/graph-failure copy for such a failure, while the plan requires a `DurableError` (a blank identity, a missing colour, no pending gate) to surface its own message.
- **Fix:** `_handle_decision` now distinguishes `DurableError` (its message) from any other exception (`_FAILURE_COPY`); `_handle_case`'s graph-failure catch renders `_FAILURE_COPY`.
- **Files modified:** `src/triagedesk/desk/server.py`
- **Verification:** `test_a_failure_is_never_an_approve` asserts the failure copy; `test_absent_thread_renders_an_error_panel` asserts the plumbing's own message.
- **Committed in:** `96e9552` (Task 1 commit)

**3. [Rule 2 - Missing Critical] A committed repeat submission would have re-rendered a fresh gate**
- **Found during:** Task 2 (the `existed` handling)
- **Issue:** The plan's `existed=True` rule re-renders the card and gate from the snapshot. For a thread that already committed, that would show a gate the plumbing would refuse — misleading, though fail-safe (no second row).
- **Fix:** When the snapshot carries a `commit_result`, the surface renders the gate's own outcome (its `reason`) instead of a fresh gate.
- **Files modified:** `src/triagedesk/desk/server.py`
- **Verification:** `test_repeat_submission_after_commit_adds_no_row` asserts the committed outcome renders and no second row appears.
- **Committed in:** `96e9552` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (3 Rule 2 missing-critical).
**Impact on plan:** All three make the surface more honest and match the UI-SPEC's own copy requirements; no scope creep, no frozen-spine change, no new dependency.

## Issues Encountered

- The out-of-band probe scripts (run outside pytest, so without the autouse span-sink fixture) wrote a gitignored `spans.jsonl` into the repository root, which failed `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`. Removing the generated artefact restored the suite to green. (The same artefact was noted in 10-01.) The suite itself writes spans only to `tmp_path`.

## Known Stubs

None. Every rendered value is wired to a graph-owned field; no placeholder, hardcoded-empty or mock data flows to the surface.

## Threat Flags

None new. This plan adds no network endpoint, auth path, file-access pattern or schema change at a trust boundary beyond the surface already declared in the plan's `<threat_model>` (T-10-05…T-10-09, T-10-SC); the fail-safe, editable-colour and banner-trigger mitigations are implemented and proven by the tests above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The banner, the read-only deferred terminal, the evidence list and every gate branch are proven end-to-end and hermetic; the frozen spine is byte-identical (no change under `src/triagedesk/core/`, `graph/`, `mcp/`, `store/`, `evals/` or `data/`).
- Full suite green at **388 passed**; `ruff check` clean on `src/triagedesk/desk` and `tests/test_desk.py`; the no-duplicated-SATS and doc guards stay green.
- Ready for plan 10-03 (the `docs/DESK.md` quickstart + the `D23` decision row), which documents the routes and form-field names this plan froze.
- The one human backstop: the painted banner and the no-clip check at 1280px/1024px (D6, `human_judgment: true`).

---
*Phase: 10-desk-ux-real-approval-gate*
*Completed: 2026-10-13*

## Self-Check: PASSED

- All created/modified files exist (server.py, both assets, the test suite, this SUMMARY).
- All three task commits exist and are ancestors of HEAD: `96e9552`, `0ad1a27`, `e723659`.
- Full suite green at 388 passed (362 baseline + 26 new desk tests).

