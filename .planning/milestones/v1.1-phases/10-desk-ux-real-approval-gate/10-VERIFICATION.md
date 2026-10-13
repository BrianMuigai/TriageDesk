---
phase: 10-desk-ux-real-approval-gate
verified: 2026-10-13T13:19:00Z
status: passed
score: 33/33 must-haves verified
covered_files: [".planning/phases/10-desk-ux-real-approval-gate/10-01-PLAN.md", ".planning/phases/10-desk-ux-real-approval-gate/10-01-SUMMARY.md", ".planning/phases/10-desk-ux-real-approval-gate/10-02-PLAN.md", ".planning/phases/10-desk-ux-real-approval-gate/10-02-SUMMARY.md", ".planning/phases/10-desk-ux-real-approval-gate/10-03-PLAN.md", ".planning/phases/10-desk-ux-real-approval-gate/10-03-SUMMARY.md", "docs/DECISIONS.md", "docs/DESK.md", "pyproject.toml", "src/triagedesk/cli.py", "src/triagedesk/desk/__init__.py", "src/triagedesk/desk/server.py", "src/triagedesk/desk/static/index.html", "src/triagedesk/desk/static/styles.css", "tests/conftest.py", "tests/test_desk.py", "tests/test_desk_runbook.py"]
covered_digest: "v3:sha256:f8fe975a3363edd1b91f4d2dede837548f713c8ee43fd83c0b909262ccf668aa"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 33/33
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 10: Desk UX & Real Approval Gate Verification Report

**Phase Goal:** The desk-facing surface renders the suggestion plus its evidence and requires a named human to approve, edit, or dismiss — nothing commits without that interaction.
**Verified:** 2026-10-13T13:19:00Z
**Status:** passed
**Re-verification:** Yes — stale re-verification (later phases 11–12 additively edited shared files Phase 10's report covered)

## Re-verification Note

This pass re-checks the same 33 truths from the previous `passed` report against the **current**
codebase (HEAD `fa9e257`). Later phases (11–12) touched the phase's shared documents, so the
report is regenerated with a freshly computed covered-input fingerprint.

**What changed since the prior verification (`verified: 2026-10-13T00:11:23Z`):**

- Of every Phase-10 covered file, **only `docs/DECISIONS.md` was modified** — 4 later-phase commits
  (`9474aea`, `9e18462` add/repair **D24**; `bba6473` adds **D25**; `9b92e54` corrects D3/DQ-8). Each
  diff touches no D23 line; the Phase-10 decision row is intact (`grep -c '^### D23 ' == 1`). The
  changes are **purely additive** to the decision record.
- **No Phase-10 implementation file changed**: `git log --since=<prior verified> -- <server.py,
  index.html, styles.css, cli.py, pyproject.toml, test_desk.py, test_desk_runbook.py, DESK.md>`
  returns **0 commits** for each.
- The suite grew 424 → **454 passed** because Phases 11–12 added tests; the desk suites stay at
  **71 passed**.
- Consequently the `covered_digest` moved from `64b6b6e2…` to `f8fe975a…` (driven by the additive
  `docs/DECISIONS.md` rows), while every Phase-10 implementation input is byte-identical.

**Regression check:** none. The 33 truths are re-verified against the current tree below.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | **SC1** — a priority card renders the *suggested* colour with its text label, the target time, and each fired rule's `detail` beside its adjacent citation, framed as a suggestion (never a diagnosis) | ✓ VERIFIED | `test_form_to_card_to_gate_to_commit` asserts the card copy (`Suggested priority`, `This is a suggestion, not a decision…`, `Suggested colour:`, `Target time:`, `Why these vitals:`) and the colour name as text; `_card_html` (server.py:514-568) renders every value from the payload |
| 2 | The card is rendered from the graph's own typed outputs (interrupt payload + `PausedRun.result`); the bridge re-derives no colour, citation, target or confidence value | ✓ VERIFIED | `_card_html`/`_why_vitals_rows`/`_evidence_rows` read `payload["…"]`/`state["evidence"]`; `_colour_class` is a string→class lookup (server.py:293-299); no scorer/citation call in `desk/` |
| 3 | The evidence list renders the ranked `evidence.passages` (label + citation) from the paused state snapshot, or the verbatim no-evidence line | ✓ VERIFIED | `test_evidence_list_renders_each_passage_in_rank_order` (rank order + label + citation), `test_evidence_list_renders_the_no_evidence_line`; `_evidence_rows` (server.py:495-511) |
| 4 | A routine all-normal-vitals case still renders a why-vitals row (the scorer's `tews_baseline` entry), never an empty list | ✓ VERIFIED | `test_baseline_why_vitals_row_is_never_an_empty_list` asserts the baseline `detail`+`citation` render |
| 5 | The why-vitals list covers zero / one / many rules | ✓ VERIFIED | zero → the `tews_baseline` row (#4); one/many → `test_form_to_card_to_gate_to_commit` + `_why_vitals_rows` emitting one row per `triggered_rules` entry |
| 6 | The evidence list covers zero / one / many (capped by the substrate's own passage limit) | ✓ VERIFIED | zero → #3 no-evidence line; many → #3 (`len(expected) >= 2`, capped by `retrieval.MAX_PASSAGES`, not the surface) |
| 7 | The complaint renders in a wrapping block with no truncation and a citation is never ellipsised | ✓ VERIFIED | `.citation`/`.why-vitals-list li`/`.evidence-list li` declare `overflow-wrap: anywhere; word-break: break-word` (styles.css:106-107, 289-301); `test_served_css_declares_wrapping_rules` |
| 8 | No rendered card/banner string or surface copy carries a `HandoverCard.FORBIDDEN_FIELD_TOKENS` token, and no rendered string carries a percentage | ✓ VERIFIED | `test_rendered_copy_carries_no_forbidden_token` (imports `prohibited_tokens()`, non-vacuous subject), `test_no_rendered_string_shows_a_percentage`; grep of served assets = clean |
| 9 | **SC2** — a loud banner whose headline is exactly `No discriminator matched / low confidence — nurse to confirm` renders whenever the typed uncertainty signal fires (`no_match` OR `confidence.deferral`) | ✓ VERIFIED | `test_banner_trigger_reads_only_the_typed_signal`, `test_deferred_case_renders_the_banner_read_only_card_and_no_gate`; `_BANNER_HEADLINE` (server.py:117) verbatim; `banner_trigger` (server.py:247-260) |
| 10 | The banner body is trigger-conditional (never asserts a fact its trigger did not establish) | ✓ VERIFIED | `test_banner_body_is_trigger_conditional`; `_banner_html` (server.py:320-331) selects no-match vs low-confidence body |
| 11 | The banner never fires on `evidence.no_match` or `missing_vitals` alone | ✓ VERIFIED | `test_no_banner_for_evidence_no_match_or_missing_vitals` |
| 12 | The banner headline wraps to at most three lines and stays fully visible at 1024px | ✓ VERIFIED | `.banner-headline` declares `overflow-wrap`/`word-break`, no fixed height (`test_served_css_declares_wrapping_rules`); UI-REVIEW measured the headline at 2 lines / fully visible at 1024px |
| 13 | Missing scored vitals are named under `Not recorded:` and the banner does not fire for missing vitals alone | ✓ VERIFIED | `_card_html` renders `Not recorded:` from `payload["missing_vitals"]`; #11 proves the banner does not fire on missing vitals |
| 14 | **SC3** — an approve decision resumes the paused thread through `durable.approval_decision` + `durable.resume_thread` and lands exactly one queue row, recording the named approver and role | ✓ VERIFIED | `test_form_to_card_to_gate_to_commit` asserts `len(injected_store.rows) == 1` and the committed copy; `decide` (server.py:226-244) calls the ONE plumbing; behavioural row-delta |
| 15 | A dismiss decision commits no artefact | ✓ VERIFIED | `test_dismiss_commits_nothing` asserts `refused=True`/`committed=False` and `injected_store.rows == []`; behavioural row-delta |
| 16 | A timeout — no decision POST at all — produces no decision, no resume and no queue row (no default approve) | ✓ VERIFIED | `test_timeout_is_no_approve` asserts zero rows and no preselected decision/colour; the bridge holds no server-side deadline (server.py:1133-1146) |
| 17 | The edit control offers exactly the colours the gate's validator accepts | ✓ VERIFIED | `test_edit_set_equals_the_gate_set` asserts `editable_colours() == {band.colour for band in get_tews().tews_to_colour}`, equals the rendered radio set, and every offered colour validates an `ApprovalToken`; `editable_colours()` (server.py:282-290) |
| 18 | The bridge has no commit path — no `desk/` module imports the queue writer or the gated-commit host module | ✓ VERIFIED | `test_no_self_commit_path_in_the_desk_package` (recursive AST/relative-import scan, non-vacuous), `test_commit_path_guard_resolves_relative_and_symbol_imports`, `test_commit_path_guard_catches_literal_dynamic_imports`; grep of `desk/*.py` for `store.queue`/`mcp.server`/commit symbols = only a docstring mention (server.py:14); behavioural half = zero-row delta on dismiss/timeout/deferred |
| 19 | A server/graph failure renders the error panel copy and leaves the gate unresolved — a failure is never an approve | ✓ VERIFIED | `test_a_failure_is_never_an_approve` asserts the `_FAILURE_COPY` panel and zero rows; `_handle_decision` catches and never resumes |
| 20 | A blank name/role or a missing edit colour surfaces the ONE decision builder's error and writes nothing | ✓ VERIFIED | `test_blank_identity_surfaces_the_builder_error`, `test_missing_edit_colour_surfaces_the_builder_error`; `durable.approval_decision` owns the check |
| 21 | A repeat submission (`existed=True`) reuses the content-addressed thread instead of forking one | ✓ VERIFIED | `test_existed_repeat_submission_reuses_the_thread` (same thread id, no row), `test_repeat_submission_after_commit_adds_no_row` |
| 22 | **SC4** — the vitals form validates through the ONE `CaseInput` schema and an invalid field surfaces the schema's own message beside that field, scoring nothing | ✓ VERIFIED | `test_out_of_range_vital_renders_the_schema_message`, `test_schema_rejection_renders_beside_the_offending_field` (field carries `field-error` + `aria-invalid` + message, no separate panel), `test_form_to_case_routes_a_bad_numeric_through_the_schema`; `form_to_case` (server.py:145-189) |
| 23 | A browser-realistic submission — including an unchecked Trauma box — reaches the card + gate | ✓ VERIFIED | `test_unchecked_trauma_reaches_the_card_and_gate`, `test_checked_trauma_duplicate_key_reaches_the_card_and_gate`, `test_trauma_checkbox_is_paired_with_a_hidden_false`; the hidden `false` companion (server.py:431-434) |
| 24 | `docs/DESK.md` is a one-screen quickstart: the literal `uv run triagedesk desk` path with `--host`/`--port`/`--db`, the local URL, and the expected on-screen states, naming no graph node/thread id/internal identifier | ✓ VERIFIED | docs/DESK.md (75 lines, one screen); `test_runbook_documents_the_one_command_path_and_url`, `test_runbook_names_no_graph_internal_identifier` (imports `TRACER_NODES`, non-vacuous) |
| 25 | The quickstart's commands are guarded by a test that drives the shipped CLI's own parser | ✓ VERIFIED | `test_documented_invocations_are_accepted_by_the_cli` drives public `triagedesk.cli.main` with `serve` spied; `uv run triagedesk desk --help` exits 0 and lists `--host`/`--port`/`--db` |
| 26 | The quickstart states the surface's fail-safe rules in plain language (timeout = no approve, dismiss commits nothing, never commits on its own) | ✓ VERIFIED | `test_runbook_states_the_fail_safe_clauses`; docs/DESK.md "What the surface never does" |
| 27 | The bridge binds `127.0.0.1` only; a non-loopback/wildcard bind is refused; `serve`'s declared default host is loopback | ✓ VERIFIED | `test_make_server_binds_localhost_only`, `test_serve_declares_a_localhost_default`, `test_non_loopback_bind_is_refused`, `test_non_loopback_bind_requires_explicit_opt_in`, `test_desk_server_refuses_a_non_loopback_bind_by_construction`, `test_desk_command_refuses_a_non_loopback_host`; `_refuse_non_loopback` (server.py:1092-1109) |
| 28 | The `desk` entry point runs `harden_offline()` before the handler is imported (offline, no CDN/webfont/external request) | ✓ VERIFIED | `test_desk_entry_point_hardens_offline_before_serve` asserts the ordered events `["harden", "serve"]`; cli.py:161 `harden_offline()` then lazy `from triagedesk.desk.server import serve` at cli.py:245 |
| 29 | Every rendered string is HTML-escaped (untrusted complaint, approver name/role, colour class), and the served assets make no external request | ✓ VERIFIED | `test_untrusted_complaint_escapes_markup`, `test_state_panel_escapes_its_copy`, `test_colour_label_accompanies_every_rendered_colour` (hostile colour class escaped); `test_served_assets_make_no_external_request` (no `http(s)://`, `@import`, `url(`, off-host `<script src=`); grep of `index.html`/`styles.css` = clean |
| 30 | Hermeticity — no model, no borrowed subprocess, no repo-root artefact — and the frozen spine is unchanged by the phase | ✓ VERIFIED | `test_submit_path_launches_no_borrowed_store`; `uv run pytest -q` → **454 passed**; the 30 Phase-10 commits touch **no** file under `src/triagedesk/{core,graph,mcp,store,evals}/` or `data/` (verified per-commit); no committed repo-root artefact (`spans.jsonl`/`*.db` are gitignored — see Anti-Patterns ℹ️) |
| 31 | `docs/DECISIONS.md` carries exactly one new D23 row and no already-guarded document is edited | ✓ VERIFIED | `grep -c '^### D23 ' == 1` (still true after Phases 11–12 appended D24/D25); Phase-10 commits touch only `docs/DECISIONS.md` + `docs/DESK.md` under `docs/`; `tests/test_docs_final.py` + `tests/test_demo_runbook.py` pass |
| 32 | **(backstop)** Long citation/evidence strings wrap within the card column; the page never scrolls horizontally at 1280px or 1024px | ✓ VERIFIED | UI-REVIEW browser measurement: no horizontal overflow at 1280px or 1024px (committable + deferred); `test_served_css_declares_wrapping_rules` (the machine-checkable CSS proxy) |
| 33 | **(backstop)** The label `Dismiss (commit nothing)` never clips at 1024px | ✓ VERIFIED | UI-REVIEW browser measurement: `scrollWidth == clientWidth` on the dismiss button at 1024px; `test_served_css_declares_wrapping_rules` (no fixed width / `nowrap`) |

**Score:** 33/33 truths verified (0 present, behavior-unverified)

The two `backstop` truths (#32, #33) are the UI-SPEC's declared browser backstops. They are carried as VERIFIED on **explicit evidence**: the `10-UI-REVIEW.md` audit drove the real surface in headless Chromium and measured the layout at 1280px and 1024px (no horizontal overflow; no button clipping). The UI review is ADVISORY (non-blocking) and adds no gap; the machine-checkable CSS wrap-rule proxy in `tests/test_desk.py` is the in-repo half.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/triagedesk/desk/__init__.py` | package seam, re-exports the public names | ✓ VERIFIED | 26 lines; re-exports the bridge |
| `src/triagedesk/desk/server.py` | the ONE presentation bridge (1162 lines) | ✓ VERIFIED | `form_to_case`/`submit_case`/`decide`/`render_state`/`make_server`/`serve`/`DeskHandler`/`DeskServer`; presentation-only |
| `src/triagedesk/desk/static/index.html` | hand-authored page (UI-SPEC copy) | ✓ VERIFIED | 75 lines; verbatim copy; one inline script with no `$` |
| `src/triagedesk/desk/static/styles.css` | UI-SPEC token set + swatch classes | ✓ VERIFIED | 391 lines; five colour tokens incl. `--colour-blue`, all state tokens, wrap rules |
| `src/triagedesk/cli.py` | the `desk` subcommand | ✓ VERIFIED | `--host`/`--port`/`--db`; lazy handler import after `harden_offline()` |
| `pyproject.toml` | `desk/**` TID251 ignore | ✓ VERIFIED | `"src/triagedesk/desk/**" = ["TID251"]` (mirrors `replay.py`) |
| `tests/test_desk.py` | end-to-end + structural + fail-safe proofs | ✓ VERIFIED | 1511 lines, 66 tests, all passing |
| `tests/test_desk_runbook.py` | quickstart-vs-CLI drift guard | ✓ VERIFIED | 129 lines, 5 tests, all passing |
| `docs/DESK.md` | one-screen desk quickstart | ✓ VERIFIED | 75 lines; literal command + URL + transcript + fail-safe clauses |
| `docs/DECISIONS.md` | the D23 row | ✓ VERIFIED | exactly one `### D23` row recording the surface design; D24/D25 appended additively by later phases |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| cli.py `desk` handler | `triagedesk.desk.server.serve` | lazy import AFTER `harden_offline()` | ✓ WIRED | cli.py:161 then :245; ordered-event test `["harden","serve"]` |
| `desk/server.submit_case` | `durable.run_to_gate` | the ONE pause path | ✓ WIRED | server.py:218-223 |
| `desk/server.decide` | `durable.approval_decision` + `durable.resume_thread` | the ONE decision builder + resume entry | ✓ WIRED | server.py:238-244 |
| gate hidden `thread_id` | interrupt payload `case_id` | `/decision` POST → `decide(thread_id,…)` | ✓ WIRED | `_gate_html` (server.py:625); `test_gate_carries_the_paused_thread_id` |
| `desk/server.form_to_case` | `core.schema.CaseInput.model_validate` | the ONE schema | ✓ WIRED | server.py:189; `test_form_to_case_routes_a_bad_numeric_through_the_schema` |
| `render_state` | `PausedRun.result` channels (priority/evidence/confidence/matched_ids/no_match/second_look) | paused state snapshot | ✓ WIRED | `_paused_view` (server.py:669-736) |
| colour class | styles.css `colour-{name}` class | presentation lookup | ✓ WIRED | `_colour_class` (server.py:299) + styles.css:250-273; `test_css_declares_every_substrate_colour_token` |
| assets | UI-SPEC Copywriting Contract + token tables | approved design contract | ✓ WIRED | copy/tokens verified verbatim by tests + UI-REVIEW |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `priority-card` colour/target/why-vitals | `payload["colour"|"target"|"triggered_rules"]` | `approval_gate` interrupt payload (graph) | Yes | ✓ FLOWING |
| `priority-card` evidence | `state["evidence"].passages` | `ground` node / retrieval (graph) | Yes | ✓ FLOWING |
| `uncertainty-banner` | `banner_trigger(state)` | typed `no_match` / `confidence.deferral` channels | Yes | ✓ FLOWING |
| `approval-gate` thread id | `payload["case_id"]` | `durable` content-derived thread id | Yes | ✓ FLOWING |
| gate edit colours | `editable_colours()` | `get_tews().tews_to_colour` substrate | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite green | `uv run pytest -q` | **454 passed** | ✓ PASS |
| Desk + runbook suites | `uv run pytest tests/test_desk.py tests/test_desk_runbook.py -q` | **71 passed** | ✓ PASS |
| Entry point resolves | `uv run triagedesk desk --help` | exits 0; lists `--host`/`--port`/`--db` | ✓ PASS |
| Doc/guard suites | `uv run pytest tests/test_no_duplicated_sats.py tests/test_docs_final.py tests/test_demo_runbook.py -q` | green (within the 454) | ✓ PASS |
| Banner/gate disjointness + no preselection (independent render probe) | `render_state(...)` on a committable and a deferred `PausedRun` | committable: banner empty, card+gate, hidden `thread_id`, no preselection, colour name as text; deferred: banner + read-only card, no gate | ✓ PASS |
| Edit set == gate accepted set (independent probe) | `editable_colours()` vs substrate | `['GREEN','ORANGE','RED','YELLOW']` == substrate (no BLUE) | ✓ PASS |

### Probe Execution

No phase-declared or conventional `scripts/*/tests/probe-*.sh` probes exist for this phase (it is a presentation-layer phase, not a migration/tooling phase). Step 7c: not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| UX-01 | 10-02 | Loud banner backed by a typed uncertainty field that drives routing | ✓ SATISFIED | Truths #9-#13; `banner_trigger` reads only the typed signal |
| UX-02 | 10-01, 10-02 | Priority card: suggested colour, target time, why-vitals + adjacent citations; evidence | ✓ SATISFIED | Truths #1-#8; card + evidence list |
| UX-03 | 10-01, 10-02 | Real approve/edit/dismiss; named approver; no artefact on dismiss/timeout | ✓ SATISFIED | Truths #14-#21 |
| UX-04 | 10-01, 10-03 | Minimal vitals-entry surface (one shared schema) + one-screen quickstart | ✓ SATISFIED | Truths #22-#26 |

All four requirement IDs declared in the plans are accounted for. `REQUIREMENTS.md` maps exactly UX-01…UX-04 to Phase 10; no orphaned requirements (no other ID maps to this phase).

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts. (`check.decision-coverage-verify`: 19/19 honored, `not_honored: []`, non-blocking.)

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/test_desk.py` | UX-01…UX-04 | 66 | 0 | none | Behavioural (row deltas, render assertions, AST import scan) | ✓ OK |
| `tests/test_desk_runbook.py` | UX-04 | 5 | 0 | none | Value/Behavioural (CLI-driven) | ✓ OK |

**Disabled tests on requirements:** 0 → no BLOCKER. **Circular patterns detected:** 0 → no BLOCKER. **Insufficient assertions:** 0 → no WARNING.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder debt markers in any phase file | — | none |
| `src/triagedesk/desk/server.py` | 135, 142 | `_UNREACHED_COPY` / `_NO_THREAD_COPY` render beyond the UI-SPEC Copywriting Contract | ℹ️ Info | Plain, non-clinical fallbacks (the UI-REVIEW noted them as a mild divergence, not a defect); the read-only framing `_READ_ONLY_FRAMING` is sanctioned by D10-17 |
| repo root | — | Gitignored test byproducts `triage.db` / `spans.jsonl` observed **intermittently** at repo root during test runs | ℹ️ Info | Observed twice across ~8 runs and **not reproducible on demand** (3× full-suite and 3× desk-suite reruns each left the root clean); not created by the desk path (hermeticity test #30 passes); both are gitignored. Not a Phase-10 regression — no Phase-10 file changed since the prior pass |

The three `open` sub-threshold advisories in `10-REVIEW-DISPOSITION.md` (IN-01 bracket-suffixed `Host`, IN-02 over-refusal of `127.1`/`localhost.`, IN-03 no per-connection read timeout) are raw-client-only, not browser-reachable, never touch a commit path, and were recorded as non-blocking by the code review. They are informational, not gaps.

### Advisory (New Scope, Unevidenced)

None. No Step-7 blocker was downgraded for lack of evidence on this pass.

### Human Verification Required

None. The two UI-SPEC `backstop` rows (layout wrap / button no-clip at 1024px-1280px) were cleared by explicit browser measurement in `10-UI-REVIEW.md` and are carried as VERIFIED above; the advisory UI review is non-blocking and adds no gap. All functional success criteria are covered by passing behavioural tests.

### Gaps Summary

No gaps. The phase goal is achieved in the codebase:

- The desk surface (`src/triagedesk/desk/`) is a dependency-free stdlib `http.server` bridge that renders the graph's own typed outputs as a **suggestion** card with its adjacent citations and attributed evidence (SC1/UX-02), fires a loud trigger-driven banner from the typed uncertainty signal (SC2/UX-01), and gates the queue behind a real approve/edit/dismiss interaction that records a named approver and commits nothing on dismiss or timeout (SC3/UX-03).
- The vitals form validates through the ONE `CaseInput` schema — including the browser-realistic unchecked-Trauma path — and a one-screen `docs/DESK.md` quickstart gives the first interaction in literal steps pinned to the shipped CLI (SC4/UX-04).
- All four roadmap success criteria are verified with behavioural evidence (row deltas, render assertions, ordered-event proof, AST import scan), plus independent render probes for the banner/gate disjointness and the gate's no-preselection.
- The frozen v1.0 spine is untouched by the phase (per-commit diff over the 30 Phase-10 commits); no new dependency; `uv run pytest -q` is green at **454 passed**.

**Owner-confirmed, NOT a gap:** D10-17 — the banner and the gate apply to **different cases**: a deferred case shows the banner + a read-only card and **no** gate. This is the intended reachable design, not a defect.

This is a stale re-verification: every Phase-10 implementation input is byte-identical to the prior `passed` pass; only `docs/DECISIONS.md` changed (additive D24/D25 rows, D23 intact). The fingerprint is refreshed and the four success criteria still hold.

---

_Verified: 2026-10-13T13:19:00Z_
_Verifier: the agent (gsd-verifier)_
