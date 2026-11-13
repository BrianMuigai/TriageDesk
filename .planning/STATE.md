---
gsd_state_version: "1.0"
milestone: v1.3
milestone_name: Adaptive Triage
current_phase: 21
current_phase_name: MCP elicitation end-to-end — `request_clarification` asks mid-call
status: executing
stopped_at: Phase 21 complete (3/3 plans), ready to plan Phase 22
last_updated: "2026-11-14T00:58:26.000Z"
last_activity: 2026-11-14
last_activity_desc: Phase 21 complete — MCP elicitation end-to-end
state_head: 9c512ac
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-13)

**Core value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.
**Current focus:** Milestone v1.3 Adaptive Triage — bounded planner over a frozen safety kernel, plus real MCP elicitation

## Current Position

Phase: 21 — MCP elicitation end-to-end — `request_clarification` asks mid-call
Plan: 3/3 complete (21-01, 21-02, 21-03)
Status: Complete — ready to plan Phase 22
Last activity: 2026-11-14 — Phase 21 complete: the ninth owned tool, the real-adapter round trip,
the ONE respond loop, and the CLI/desk question surfaces

## Reviewer Challenge (drives this milestone)

> "Is this genuinely an agentic system, or a deterministic clinical rules engine with an LLM
> extraction step and an MCP integration?"

`STATUS.md` §3/§5/§7 conceded two named limitations: **fixed routing rather than dynamic planning**
and **no MCP elicitation (G7)**. v1.3 answers with behaviour + a structural proof:

- a bounded `plan` node that chooses the next read-only investigation action (model proposes, guard disposes);
- `finish_investigation` as the only edge into `score`, so the safety kernel is a non-skippable suffix;
- `request_clarification` eliciting mid-tool-call → LangGraph `interrupt()`, with
  accepted / declined / cancelled / unavailable distinguished (the 2026-07-28 transport carries the
  question inside an `InputRequiredResult`; `ctx.elicit` remains the legacy-era path);
- a deterministic emergency bypass so a critical structured case never waits for the model or the planner;
- two diagrams split by audience (clinical workflow; components and infrastructure), honestly labelled;
- an adaptive-vs-baseline measurement published from `report.json`, never hand-typed.


## Performance Metrics

**Velocity:**

- v1.0 shipped: 5 phases, 21 plans (archived in `.planning/milestones/v1.0-phases/`)
- v1.1 plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase (v1.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 6 | 2 | - | - |
| 7 | 2 | - | - |
| 8 | 3 | - | - |
| 9 | 3 | - | - |
| 10 | 3 | - | - |
| 11 | 3 | - | - |
| 12 | 3 | - | - |
| 13 | 3 | - | - |
| 14 | 3 | - | - |
| 19 | 1 | - | - |
| 20 | 4 | - | - |
| 21 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 06 P01 | 8min | 2 tasks | 14 files |
| Phase 06 P02 | 16min | 3 tasks | 7 files |
| Phase 7 P01 | 8min | 3 tasks | 13 files |
| Phase 07 P02 | 15min | 2 tasks | 8 files |
| Phase 08 P01 | 19min | 2 tasks | 13 files |
| Phase 08 P02 | 25min | 3 tasks | 9 files |
| Phase 08 P03 | 30min | 2 tasks | 5 files |
| Phase 09 P01 | 6min | 2 tasks | 10 files |
| Phase 09 P02 | 10min | 2 tasks | 3 files |
| Phase 09 P03 | 12min | 3 tasks | 6 files |
| Phase 10 P01 | 13min | 2 tasks | 7 files |
| Phase 10 P02 | 22min | 3 tasks | 4 files |
| Phase 10 P03 | 3min | 2 tasks | 3 files |
| Phase 11 P01 | 56 | 3 tasks | 7 files |
| Phase 11 P03 | 3 | 2 tasks | 3 files |
| Phase 11 P02 | 19min | 3 tasks | 4 files |
| Phase 12 P01 | 20min | 2 tasks | 3 files |
| Phase 12 P02 | 4min | 3 tasks | 3 files |
| Phase 12 P03 | 18min | 3 tasks | 6 files |
| Phase 21 P01 | 35min | 6 tasks | 12 files |
| Phase 21 P02 | 30min | 4 tasks | 4 files |
| Phase 21 P03 | 40min | 6 tasks | 15 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.1 Roadmap]: 7 coarse phases derived from the research build order (8 capability phases grouped); phase numbering continues from v1.0 at Phase 6.
- [v1.1 Roadmap]: Phase 6 front-loads the milestone's first HIGH blocker — the durable approval-gate lifecycle and the idempotency-key breadth bug (an edit supersedes, not duplicates).
- [v1.1 Roadmap]: Phase 7 retires the second HIGH blocker — replay must be read-only by construction (commit structurally unreachable), riding on Phase 6's checkpoint.
- [v1.1 Roadmap]: Phases 7/8/9 depend only on Phase 6 and are independent/parallelisable; Phase 10 (UX adapter) consumes Phases 8 and 9; DOCS-06 lands in the final Phase 12.
- [v1.0, carried]: Nothing edits the scorer, the citation helper, or the audit interceptor — every v1.1 change attaches at a published seam (new node / new tool / new contract / adapter behind an existing protocol) (D-18).
- [v1.3 Phase 21]: The installed SDK's 2026-07-28 revision forbids a server-initiated request, so
  `request_clarification` asks over the input-required round trip and keeps `ctx.elicit` for an older
  connection; both share one question derivation and one outcome mapper.
- [v1.3 Phase 21]: The interrupt discriminator (`approval` | `mcp_elicitation`) lives once in
  `core.schema.InterruptType`, so the graph never imports `mcp` and no surface repeats a literal.
- [v1.3 Phase 21]: One interrupt loop behind an injectable `RespondPolicy`; the default answers an
  approval and STOPS at a question, so no existing caller changed and an approval never answers one.
- [v1.3 Phase 21]: `request_clarification` is the ninth owned tool but is unwired — no graph node
  calls it until Phase 23 wires the `plan` node. The nine-tool count stays "7 shipped + 2 substrate"
  in README/ARCHITECTURE/SECURITY/STATUS.
- [v1.0, carried]: `checkpoints.db` (runtime state) is a separate file from `triage.db` (clinical record + audit); the queue write is the ONE idempotent write keyed on immutable case content.
- [v1.0, carried]: Colour is produced in exactly one place (`core/scorer.score_priority`, `citations == triggered_rules`); the agent path stays offline and model-free on the score path.
- [v1.0, carried]: `approval_gate` is side-effect-free before `interrupt()`, and `commit` is reachable only through the resumed interrupt.
- [v1.0, carried]: `EVALS.md` is generated only by `scripts/emit_evals.py` from `report.json`; the declared failure E-09 and honest misses stay visible (never tuned green).
- [v1.0, carried]: SATS rules live only in `data/*.yaml`; a rule is added as data, never by editing code (extend by config, not working code).
- [Phase 06]: The queue idempotency key covers the immutable CaseInput payload (schema-derived, D6-05), not the scored colour — an approve and an edit re-derive the SAME key (D6-04).
- [Phase 06]: An edit supersedes the queue row in place: colour/target updated, position/created_at preserved, so exactly one row exists per case (D6-06).
- [Phase 06]: commit_priority gained a required typed case: CaseInput; the signature change moved across every call site in one wave (Pitfall 1), with no migration for frozen v1.0 data.
- [Phase 06]: Durable pause/resume plumbing lives in ONE helper (durable.py): demo --durable and resume share durable.invoke_graph and durable.approval_decision; resume reuses the ONE mcp.server._resolve_store seam and never auto-resumes.
- [Phase 7]: Local span tracing: ONE JSONL writer (tool/node/model spans) + a content-derived trace_id first-class on AuditRecord, persisted through the borrowed audit table; spans need all four SQL edits or the field is silently dropped
- [Phase 7]: No-egress guard: harden_offline pops the four tracer vars + clears langsmith's cached env read + asserts tracing_is_enabled() is False at CLI startup; all env logic stays outside graph/
- [Phase 07]: Read-only replay is structural: replay.py reads the checkpoint via aget_tuple with the ONE msgpack allowlist, builds no tool map and no graph, and never calls the model, so the gated commit is unreachable by construction (D7-10)
- [Phase 07]: replay_case reads the checkpoint BEFORE resolving the audit store (mcp.server._resolve_store), so an absent thread never launches the borrowed store or runs its schema DDL; read_spans is the ONE JSONL reader colocated with emit_span
- [Phase 8]: Phase 08: The coverage/deferral signal is a pure four-component function of already-typed objects; the contract has no float/percentage field, so a model probability is unrepresentable (D8-01/02/04).
- [Phase 8]: Phase 08: no_match forces a deferral; a deferral routes only to escalate/request_missing_info (no edge to commit), and assess sits immediately before approval_gate so the deterministic recheck still runs (D8-08/11/12).
- [Phase 8]: Phase 08: DEFERRAL_MIN_SATISFIED_COMPONENTS=2 is a named constant derived from the D20 asymmetric cost (a missed emergency vastly outweighs a needless deferral); never tuned to make a test green (D8-09).
- [Phase 08]: Phase 08-02: The deferral rate is derived from the report's per-run deferrals (count/reached-assess runs) and reported separately from the under/over direction split (D8-10/D8-16).
- [Phase 08]: Phase 08-02: Calibration is declared by the existing held_out flag (E-01..E-14 calibration n=14 vs H-01/H-02 held-out n=2) with both n's named and an explicit small-sample caveat (D8-13/D8-15).
- [Phase 08]: Phase 08-02: The confidence ordinal scalar lives only in evals/; the deferral-aware gate excludes a case from unexpected_failures ONLY when every run deferred, so a wrong colour is never hidden (D8-04/T-08-07).
- [Phase 08]: Phase 08-03: REAL mode kept (owner decision 2026-10-12); the committed report is mode real and stably diverges on pre-existing E-04/E-07/E-13 — no fixture, threshold or mode tuned, not flipped to --offline
- [Phase 08]: Phase 08-03: E-13 short-circuits before assess so it carries null deferrals and stays at its abstain terminal (correct, not a defect); E-07 reaches RECOVER in real mode so it also carries null; a terminal before assess cannot carry a deferral fact
- [Phase 08]: Phase 08-03: The §6.1 coverage-deferral record is DERIVED from the report (moved cases via the §4 predicate, fraction via the analyser, gate failures via report.gate) so the published narrative cannot drift; the pre-existing real-mode gate failures are honest and belong to Phase 11
- [Phase 09]: Phase 09-01: retrieval is a pure integer lexical scorer over data/*.yaml through the ONE loader; the EvidencePassage/EvidenceResult contract has no colour/target/priority/float field, so a colour is unrepresentable rather than merely unused (D9-03).
- [Phase 09]: Phase 09-01: one normalisation owner — matcher._tokens was promoted to a public tokenize() (with _tokens = tokenize keeping the three call sites byte-identical); retrieval.tokenize is matcher.tokenize and no second regex exists (A3, D9 discretion).
- [Phase 09]: Phase 09-01: the seventh owned tool retrieve_evidence is a thin @audited read-only wrapper (no store/approval token/model), and the seven-name owned-tool allowlist moved across all four set-equality sites in ONE atomic commit (D9-05/D9-06).
- [Phase 09]: Phase 09-01: E-09's vague complaint stays an honest no_match read from the substrate warning — no alias, fixture, threshold or YAML file was added or tuned (D9-09).
- [Phase 09]: MCP-01: READ_TOOLS allowlist + fail-closed is_read_only_statement applied at the ONE _call seam; write=True is the sole privileged route (D9-12/D9-13)
- [Phase 09]: The trace_id column check stays on the verified PRAGMA table_info read; get_table_schema is used additively by ensure_schema's read-path probe (RESEARCH Pitfall 3)
- [Phase 09]: The borrowed read-path probe degrades: every probe wrapped, shape surprises RECORDED in read_path_report and never raised (D9-14/T-09-22)
- [Phase 09]: ground is placed score -> ground -> verify by plain edges only; route_after_score's LABEL stays verify while its destination is the advisory node, so no router reads evidence (D9-08)
- [Phase 09]: The ground node returns exactly {evidence} and the evidence channel is proven byte-isolated from priority/citations/matched_ids/no_match, with each colour equal to a direct scorer call
- [Phase 09]: A4 accepted and declared: the verify -> score retry re-runs ground deterministically on the unchanged complaint; only a second span/audit record on a retried case (E-12 slices)
- [Phase 10]: The desk bridge is presentation-only: it reuses durable.run_to_gate / approval_decision / resume_thread and adds no commit path; GET / renders the empty state through the ONE template.
- [Phase 10]: The deferred read-only card carries a dedicated framing line because the UI-SPEC state contract requires the not-confirmed-not-queued framing while its Copywriting Contract omits a row for it.
- [Phase 10]: A non-DurableError server/graph failure renders the UI-SPEC _FAILURE_COPY; a DurableError (the gate's own refusal) renders its own message.
- [Phase 10]: existed=True is terminal-aware: a deferred repeat stays a deferred terminal (never a gate); a committed thread shows the gate's own outcome.
- [Phase 10]: The desk quickstart lives in a NEW docs/DESK.md (unconstrained by the existing doc guards); the desk runbook stays separate from the demo-video runbook (one concern per document).
- [Phase 10]: The runbook-vs-CLI drift guard drives the public triagedesk.cli.main surface with triagedesk.desk.server.serve spied, so the documented invocation is the shipped command and no server starts.
- [Phase 10]: The internal-identifier check set is derived from triagedesk.graph.build.TRACER_NODES (imported, never restated), so the guard tracks the code.
- [Phase 10]: docs/DECISIONS.md gains exactly one D23 row recording the desk-surface design; it links to the reasoning rather than restating any colour list, target time or copy string (CONVENTIONS §1).
- [Phase 11]: E-04 is an age-fidelity failure (not discriminator retrieval): fix the age_years contract at the extraction seam, never the matcher (D11-01)
- [Phase 11]: Extraction fidelity is fixed at the CONTRACT the model fills: a general schema description on age_years and on the scored vitals (serial before/after resolves to the AFTER value); the 1.5B model is schema-sensitive so the age description must be emphatic (D11-01)
- [Phase 11]: E-07's fixture note is repaired to state its golden temperature (D11-14); expectation unchanged; the serial-vitals contract resolves the arrow notation
- [Phase 11]: Provenance.extraction_schema_hash seals the model INPUT and is covered by report_digest; defaulted + excluded-when-unset so the committed report stays valid until 11-02 regenerates it (T-11-03)
- [Phase 11]: README quickstart is the literal one-liner 'uv run triagedesk demo' (uv auto-syncs from uv.lock; no separate install step); the optional desk command is named (D11-09/D11-11)
- [Phase 11]: The one-command claim is guarded by driving the documented invocation through the public triagedesk.cli.main with the run_demo/serve seams spied (D11-10)
- [Phase 11]: The §4 row-set guard lives in render_evals, so both --check and --write fail closed (ValueError) when a report case has no published row
- [Phase 11]: The regenerated real report measures E-04 RED×3 and E-07 RECHECK×3 (both now pass); E-09 stays the declared failure; E-08/E-13 stay visible honest misses (null-age ABSTAIN)
- [Phase 11]: Research A4 did not hold: E-13 stayed a null-age ABSTAIN (not a coverage deferral) — recorded as measured, never tuned (D11-03)
- [Phase 12]: D12-01/02/03: docs/REVIEW.md runbook + tests/test_review_runbook.py CLI-drift guard + tests/test_data_extension.py hermetic data-only-extension proof (REV-01)
- [Phase 12]: D12-04: a 2–3 minute narrated demo script with a one-line narration cue pinned per beat
- [Phase 12]: D12-05: the recording and the public upload are flagged human_needed and never claimed
- [Phase 12]: D12-06: the clinical-fit gap is re-declared honestly with a marked, attributed, empty slot
- [Phase 12]: D12-10: the Phase-11 docs/DEMO.md output drift is closed by re-transcription from the shipped runner
- [Phase 12]: Q2: the committed EVALS.md projection plus the live failure beat is the on-screen measured artefact; the ~10-min silent real run is NOT streamed
- [Phase 12]: D25: the milestone close is demonstrated-not-claimed — data-only live extension (fresh process, no hot reload); the demo shows the committed EVALS.md projection + live failure beat, not the ~10-min run; the clinical-fit gap stays declared with an empty attributed slot; the upload and clinician review stay human flags
- [Phase 14]: G2 is declared and now bounded, not closed: the eight-question clinician interview, its drafted responses, and the module each answer depends on ship in docs/CLINICIAN-INTERVIEW.md; no clinician has attested it, so every gap statement keeps 'none obtained' and no quote is claimed. — The fit-to-desk criterion asks 'did you talk to one?'. Inventing or paraphrasing a review would breach the project's flag-never-claim rule. Preparing the instrument converts an open-ended gap into one bounded fifteen-minute conversation and makes every drafted answer falsifiable against the code.
- [Phase ?]: Coverage is three-way (matched / ambiguous / no_candidate). A no_candidate complaint with complete vitals is delivered on the TEWS band; only an ambiguous complaint holds a case back. The classifier reads data/text_terms.yaml and never adds a scored id. — One no_match boolean conflated 'no alias matched' with 'no discriminator applies', deferring routine presentations the vitals already answered. Splitting the fact raises coverage without weakening a safety invariant.
- [Phase ?]: A clarification is bounded to one answer round and at most three targeted questions; it emits no colour, no gate and no commit. A second ambiguity defers. — A dead-end deferral was the only safe response to a vague complaint. Asking the one measurement a nurse would ask (capillary glucose) makes the case resolvable without guessing, while the bound keeps it an ask rather than a loop.
- [Phase ?]: A stated RR/HR/systolic/diastolic BP/SpO2 is recovered deterministically when the model drops it; only a None field is filled and a stated AFTER value is never overwritten. — E-11 reached RECOVER on 2/3 runs because the model dropped a vital the note stated. Recovery is monotone completion from the note, never imputation, so the deterministic path is stable and an incomplete note still recovers.

### Pending Todos

None yet.

### Blockers/Concerns

- [All]: DRY + SOLID are iron-clad (`docs/CONVENTIONS.md`) — a violation blocks the phase at plan-check, code-review, and verifier gates.
- [All]: The v1.0 spine is frozen (tag `v1.0-submission`); every v1.1 change attached at a published seam and never edited the scorer's arithmetic, the citation helper, or the `@audited` interceptor.
- [Next milestone, carried]: The two human SUBMISSION steps remain open (the demo video upload; a clinician review) — see `## Deferred Verification` below. They are submission actions, not milestone gaps.
- [Next milestone, tech debt]: Nine sub-threshold review advisories across Phases 6/7/10/12 plus one integration wording nuance; the material ones are `store/queue.py`'s supersede unconditionally overwriting `target`, the borrowed UPSERT being string-asserted rather than suite-executed, and the desk docstring's transitive-import wording. Full list in `.planning/milestones/v1.1-MILESTONE-AUDIT.md`.
- [Next milestone, process]: `commit_docs` is `false`, so GSD's commit helper skips `.planning/`. The v1.1 archive was committed manually (matching the v1.0 precedent). Decide the convention for the next milestone.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 1 | desk panel shows the queue position the gated commit assigned | 2026-10-13 | ae611b4 | complete | [261013-sbd-desk-panel-shows-the-queue-position-the-](./quick/261013-sbd-desk-panel-shows-the-queue-position-the/) |
| 2 | collapse the duplicated store-seam ceremony and give the tool map a CaseInput entry point | 2026-10-13 | ab58bbd | Verified | [261013-taj-collapse-the-duplicated-store-seam-cerem](./quick/261013-taj-collapse-the-duplicated-store-seam-cerem/) |
| 3 | split the desk server module by SRP and document how to run the demos in the README | 2026-10-13 | 39e9cc8 | Verified | [261013-tqi-split-the-desk-server-module-by-srp-and-](./quick/261013-tqi-split-the-desk-server-module-by-srp-and-/) |
| 4 | give the outcome projection and the in-memory checkpointer one public home instead of private cross-module imports | 2026-10-13 | c15b500 | Verified | [261013-wjd-give-the-outcome-projection-and-the-in-m](./quick/261013-wjd-give-the-outcome-projection-and-the-in-m/) |
| 5 | refresh STATUS.md with the post-v1.1 desk hardening, the queue-position payoff and the two recorded walkthroughs | 2026-10-14 | 0991141 | complete | [261014-ad2-refresh-status-md-with-the-post-v1-1-des](./quick/261014-ad2-refresh-status-md-with-the-post-v1-1-des/) |
| 6 | overhaul STATUS.md into a current-state gap analysis | 2026-10-14 | a7eba9e | Verified | [261014-asx-overhaul-status-md-into-a-current-state-](./quick/261014-asx-overhaul-status-md-into-a-current-state-/) |
| 7 | record ONE reproducible <3 min submission video with the tool calls on screen (G5) | 2026-10-14 | 88b02ab | complete | [261014-f37-single-tool-call-demo-video](./quick/261014-f37-single-tool-call-demo-video/) |
| 8 | fix two correctness defects: handover card shows the committed colour after an edit; the dead verify retry edge fails closed | 2026-11-04 | 119890c | complete | [261104-ueu-fix-two-correctness-defects-1-the-handov](./quick/261104-ueu-fix-two-correctness-defects-1-the-handov/) |
| 9 | add safe lay/OPD phrasing aliases to existing discriminators and show DEFERRED (not GREEN) on the read-only card | 2026-11-04 | bb73945 | complete | [261104-w53-expand-safe-lay-phrasing-aliases-only-fo](./quick/261104-w53-expand-safe-lay-phrasing-aliases-only-fo/) |
| 10 | close the three nurse stress-test defects (negation, incomplete-case refusal, extraction grounding) plus the named recovery copy | 2026-11-04 | 8c41d54 | complete | [261104-nst-nurse-stress-test-fixes](./quick/261104-nst-nurse-stress-test-fixes/) |

## Deferred Verification

| Phase | State | Resume |
|-------|-------|--------|
| 12 | verification_deferred_human (submission-time, out-of-band) | `/gsd-verify-work 12` |

Two human SUBMISSION actions remain for Phase 12 (the phase itself is verified `passed`, 13/13):

1. **Publicly upload the demo video** — the one submission blocker (`STATUS` G1/G9). The video is
   now recorded (`docs/assets/triagedesk-demo.mp4`, 2:28 — ONE complete candidate with the tool calls
   on screen, the measured eval and the declared failure; G5 closed, reproducible via
   `docs/render-demo.sh`); only the public upload to YouTube/Vimeo remains.

2. **Obtain a triage nurse/clinician review** (FIT-01) — the sanctioned fallback is shipped (an
   honest re-declaration with a marked, empty, attributed slot in `README.md`/`EVALS.md` §7).

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-13T18:30:00.000Z
Stopped at: Phase 20 complete, ready to plan Phase 21
Resume file: None

## Operator Next Steps

- Branch is `feat/v1.3-adaptive-triage` (never work on `main`); open a PR to `main` when the milestone lands.
- `/gsd-plan-phase 19` — the two diagrams, the shared legend and the honest-labelling pass.
- Phases 19 → 24 are strictly sequential: docs contract → guard → tool → emergency bypass → graph → measurement.
- The emergency bypass and the diagrams came from the owner's architecture review on 2026-11-13; both are
  now requirements (EMERG-01..05, DIAG-01..06), not side notes.
