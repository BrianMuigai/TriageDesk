---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 4
current_phase_name: Evaluation, Recovery & Honest Failure
status: verifying
stopped_at: Completed 04-05-PLAN.md
last_updated: "2026-10-09T20:52:08.657Z"
last_activity: 2026-10-09
last_activity_desc: Completed 04-03-PLAN.md
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 18
  completed_plans: 17
state_head: bad675a53c01366530f0aea27e61b72b45c1f88b
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.
**Current focus:** Phase 4 — Evaluation, Recovery & Honest Failure

## Current Position

Phase: 4 (Evaluation, Recovery & Honest Failure) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
Last activity: 2026-10-09 — Completed 04-03-PLAN.md

Progress: [█████████░] 94%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P1 | 64 | 3 tasks | 20 files |
| Phase 1 P2 | 13 | 3 tasks | 8 files |
| Phase 1 P3 | 23 | 3 tasks | 8 files |
| Phase 1 P4 | 4 | 2 tasks | 5 files |
| Phase 02 P01 | 16 | 3 tasks | 8 files |
| Phase 02 P02 | 6 | 3 tasks | 7 files |
| Phase 02 P03 | 10 | 3 tasks | 8 files |
| Phase 3 P01 | 11 | 3 tasks | 8 files |
| Phase 3 P02 | 9 | 3 tasks | 10 files |
| Phase 3 P04 | 15 | 3 tasks | 9 files |
| Phase 03 P03 | 13 | 3 tasks | 6 files |
| Phase 03 P05 | 13 | 3 tasks | 8 files |
| Phase 04 P01 | 23 | 3 tasks | 13 files |
| Phase 04 P02 | 7 | 3 tasks | 21 files |
| Phase 04 P03 | 19 | 3 tasks | 8 files |
| Phase 04 P04 | 24 | 4 tasks | 8 files |
| Phase 04 P05 | 5 | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 5-phase coarse structure derived from the research build order; research P5 (demo) and P6 (freeze) merged into Phase 5.
- [Roadmap]: The approval gate is protected as Phase 3's phase goal — not a sub-task of graph wiring.
- [Roadmap]: Phase 1 owns retirement of both Day-1 risks (local-model structured output; MCP beta-adapter / borrowed-server handshake).
- [Roadmap]: Deterministic scorer/owned tools (Phase 2) split from graph + safety wiring (Phase 3) so the scorer is proven before anything calls it.
- [Phase 1]: Model default: qwen2.5:1.5b selected on measured evidence (qwen3.5:4b left ~600MB available RAM, warm 43.0s vs 14.8s); qwen3.5:4b is the verified fallback and both ran end-to-end (SC3).
- [Phase 1]: MCP adapter target must be a Path, not a bare string (a string is parsed as a URL and refuses to launch the owned stdio server).
- [Phase 1]: Schema plausible-range bounds are distinct from SATS TEWS bands; the latter live only in data/sats_tews.yaml (CONVENTIONS 1).
- [Phase 1]: Adult SATS discriminators are consumed through the one loader (core/rules.py) — data/*.yaml are read only there (D-08; DRY/DIP).
- [Phase 1]: data/sats_tews.yaml + data/sats_discriminators.yaml re-verified by a dual independent transcription diff (scripts/transcribe_diff.py: zero disagreements); residual uncertainty (blank temperature 1-point column; original manual unavailable) flagged in docs/SATS.md and evidence/sats-verification.md (D-10).
- [Phase 1]: 'feeling unwell' is deliberately NOT a discriminator alias — eval case E-09 stays the declared coverage-gap failure; the KB is not tuned green (Pitfall 11).
- [Phase 1]: World A adopted (D-04): langchain.mcp.MCPAdapter listed and called a tool on BOTH the owned SDK-v2 server and the borrowed legacy mcp-sqlite@1.0.9, each in a SEPARATE adapter context (no era collapse); evidence/mcp-spike.json committed.
- [Phase 1]: DRY guard covers the scoring substrate only; core/schema.py's input-domain enums (mobility/avpu) and plausible-range bounds are exempt by design (input-domain vs scoring-band boundary).
- [Phase 1]: ruff TID251 banned-api scoped to core/ via per-file-ignores (a global ban would flag legitimate mcp->llm imports); the AST purity test is authoritative.
- [Phase 1]: Canonical hash = sorted-key compact JSON (UTF-8) then sha256 — the digest is independent of dict insertion order and of YAML comments/whitespace, so only a real content change churns it (SAFE-04, D-17).
- [Phase 1]: One hashing path: hash_rule_object/hash_prompt/hash_tool_schema all delegate to hash_value; scripts/hash_data.py writes evidence/hashes.json (model tag + data/prompts/schemas digests) and exits non-zero on a missing required input.
- [Phase 1]: uv.lock was already current (Plan 01-01); uv lock resolved 115 packages with zero diff — no spurious churn. NOTICE licence facts read from installed metadata + npm (mcp-sqlite@1.0.9 = ISC; Qwen tags Apache-2.0 per evidence/model-spike.json).
- [Phase 02]: score_priority is a thin MCP tool over the pure core function; no model touches the score path (D-02, T-02-01).
- [Phase 02]: The scorer binds each loaded parameter key to its schema field structurally (temperature -> temperature_c), so a new YAML parameter auto-scores without editing the scorer (SOLID: O).
- [Phase 02]: Boolean parameters (trauma) map to their highest/lowest-points band by data, so the yes/no tokens are never inlined (DRY guard).
- [Phase 02]: Gap distances compare with a relative tolerance and resolve ties to the fail-closed higher-points band (temperature 34.95 no longer under-triages).
- [Phase 02]: Fail-closed safety branches (out-of-scope abstention, missing-vital detection) shipped with the Task-1 tracer as a Rule-2 fix; Task 2 added the proving tests and its TDD RED collapsed to GREEN.
- [Phase 02]: Discriminator matching is token-boundary based, not substring: a short alias never fires inside an unrelated word (hypothermia !-> hypo; sobbing !-> sob) (SAFE-01, D-05).
- [Phase 02]: The override's urgency order is data-derived from the TEWS colour bands' lower bounds, so no colour token is hard-coded in core/ (T-02-08).
- [Phase 02]: Unknown matched ids are ignored by the scorer, so a caller can never inject a category or colour; an unmatched complaint returns the declared no_match, never a guessed id (D-06).
- [Phase 02]: The firing discriminator category is recorded as one TriggeredRule (points 0) so citations == triggered_rules holds after the override.
- [Phase 02]: normalize_case constrains model-returned ids through core.matcher.validate_discriminator_ids (the one closed-set authority); unknown ids dropped, missing vitals stay None (TOOL-01, D-09).
- [Phase 02]: Deterioration direction is data-derived: the serial-vitals recheck compares TEWS band points, reusing core.scorer.band_points() so no threshold is duplicated; RecheckFlag has no colour and never re-classifies (TOOL-04, D-08).
- [Phase 02]: commit_priority is a gated Phase-2 stub: it validates an ApprovalToken (approver+role+decision+timestamp), refuses without one, and writes nothing; the real LangGraph gate is Phase 3 (TOOL-05, D-07).
- [Phase 3]: Graph depends on an injected tools mapping (name -> async callable), never MCPAdapter; graph/build.py is the only composition point (D-13, SOLID: D).
- [Phase 3]: approval_gate builds a pure evidence payload then interrupt(); NO side effect before the gate so a resumed node re-runs cleanly (D-04, T-03-02).
- [Phase 3]: commit builds an ApprovalToken from the resumed value verbatim (approve defaults final_colour to the scored colour; edit must carry its own); the gated tool refuses malformed/absent tokens (D-05, T-03-01).
- [Phase 3]: ApprovalToken.final_colour is validated against the colour set read from data/sats_tews.yaml, never a literal (CONVENTIONS 1).
- [Phase 3]: checkpoints.db (runtime state) is a different file from triage.db (clinical record + audit) (D-09); the SQLite saver registers an explicit per-type msgpack allowlist derived from core.schema.
- [Phase 3]: The verify retry edge is bounded (attempt < 2); an exhausted retry stops at END, never reaching the gate or commit (T-03-05).
- [Phase 3]: The graph and the server depend on the Store protocol, not the borrowed tool set; a World-B store swap touches store/borrowed.py alone (D-13, SOLID: D/L)
- [Phase 3]: content_hash reads ONLY immutable case content (colour, target, triggered_rules, citations, used_vitals); the approval timestamp and volatile fields are structurally excluded (D-06, Pitfall 14)
- [Phase 3]: commit_to_queue is the ONE idempotent write: an existing (case_id, content_hash) key is returned unchanged and no second row is inserted; crash-safety IS the idempotency key
- [Phase 3]: commit_priority is async; the refusal path returns BEFORE any store call, so no path reaches the store without a valid named approval (GATE-02, T-03-09)
- [Phase 3]: The committed colour is token.final_colour for an edit and the scored colour for an approve (D-05)
- [Phase 3]: DOMAIN_DB_PATH is owned by the store package (single source); graph/build.py imports it (DRY)
- [Phase 3]: The recovery/abstention branch is placed after score on the PriorityResult signals, so the graph never duplicates the scorer's scope/missing logic (DRY) and stays bound to the injected tool interface (SOLID: D)
- [Phase 3]: The extraction retry is an in-node loop bounded by _EXTRACTION_MAX_ATTEMPTS; the state attempt field remains the verify retry budget (no cross-coupling)
- [Phase 3]: The deterministic extraction fallback reads already-parsed structured fields (a state case or a structured JSON note) and otherwise escalates — never fabricating a value (ORCH-04, D-02)
- [Phase 3]: RecoveryRequest/Escalation carry no colour and the recovery/escalation terminals have no edge to commit (ORCH-05, D-03)
- [Phase 3]: The recheck node stores RecheckFlag in state second_look and HandoverCard.second_look only — never the colour, the priority or the queue (D-07, M-4)
- [Phase 3]: One shared offline graph tool fake in tests/conftest.py backs all three graph proof suites (DRY)
- [Phase 03]: One audit-record shape (AuditRecord) and one canonical seal (record_digest) are shared by append and verify, so the writer and the verifier cannot drift (AUDIT-03, DRY)
- [Phase 03]: The chain head is persisted in the authoritative store (audit_head); verify recomputes the chain and cross-checks the persisted head, so verification survives a restart (M-6)
- [Phase 03]: append is the only audit write; verify/reconcile are read-only. reconcile reports any queue row lacking its approval audit record, closed by re-issuing the idempotent commit (D-09, no claimed transaction primitive)
- [Phase 03]: ONE uniform @audited interceptor wraps every @server.tool(); the record tool name is the wrapped function's name, the append follows the tool's logic so refused/raising calls are recorded honestly (AUDIT-01/03, T-03-15)
- [Phase 03]: HandoverCard is locked with extra="forbid" + a declared FORBIDDEN_FIELD_TOKENS tuple; the guard test reads that ONE tuple (SAFE-02, DRY)
- [Phase 03]: ONE OWNED_TOOL_ALLOWLIST asserted by ONE assert_tool_allowlist at both owned-server discovery and graph composition; tool drift fails loudly (SAFE-03, D-12)
- [Phase 03]: The graph path imports no network client and reads no credentials; the core/ purity guard names the MCP client (fastmcp/langchain) explicitly (SAFE-03, QUAL-02)
- [Phase 03]: The score path is proven model-free by stubbing the model to raise (identical colour) + an AST guard on the scoring branch (ORCH-03, D-02)
- [Phase 04]: The eval harness consumes the ONE graph interface (TriageState + interrupt); no bespoke code path (D-01, EVAL-02)
- [Phase 04]: Colour, matched-set and field stability are three SEPARATE flags; an unstable colour/matched-set is a recorded failure, never averaged (D-02, Pitfall 12)
- [Phase 04]: Token cost is read from the SAME ollama response via an injected usage_sink on llm.client.extract; never a second model call (D-08, Pitfall 16)
- [Phase 04]: The report carries a report_digest over non-volatile content (ids, outcomes, stability flags, provenance), excluding latency/tokens/timestamps (D-08, Pitfall 18)
- [Phase 04]: Terminal outcomes RECOVER/ABSTAIN/RECHECK are read from the graph's own channels (escalation/recovery/second_look), never a re-derived colour (ORCH-05)
- [Phase 04]: A case passes only when every run's outcome equals expected AND colour + matched-set are stable; the declared failure (E-09) is an allowed miss, recorded passed=false (D-04, T-04-08)
- [Phase 04]: The E-12 fault is declared as fixture data and wrapped onto the injected normalize callable per case per run, so it exercises the real bounded retry and cannot leak (Pitfall 13, T-04-09)
- [Phase 04]: Every expected value is frozen from EVALS.md §4 through the substrate; E-04 earns RED from the declared emergency-AVPU alias wording with no data/*.yaml edit (D-05, Pitfall 11)
- [Phase 04]: INV-2 reuses store/audit.reconcile and asserts the run added zero queue rows and the unapproved resume left CommitResult.refused true — the write-without-approval path is closed at both levels (AUDIT-01, GATE-02)
- [Phase 04]: INV-3 imports HandoverCard.FORBIDDEN_FIELD_TOKENS and appends a disjoint domain deny-list, matching on token boundaries; the schema token list is never restated (DRY, SAFE-02)
- [Phase 04]: The exit code is the gate: non-zero on ANY invariant violation on ANY run OR any non-declared accuracy miss; the declared failure E-09 excuses an accuracy miss only, never a safety break (D-06, Pitfall 12)
- [Phase 04]: The invariant verdicts and the gate are sealed in report_digest, so a hand-edited verdict is detectable while the offline digest stays reproducible (D-08, Pitfall 18)
- [Phase 04]: INV-1 is scoped to the shipped citation contract (citations==triggered_rules; fired rules must be cited); a TEWS-0 priority fired no rule and has nothing to cite — a pre-existing scorer/verify interaction logged out of scope
- [Phase 04]: Under-triage and over-triage are reported SEPARATELY with case ids + run counts; terminal outcomes are excluded from the direction split and counted on their own (D-03, Pitfall 8)
- [Phase 04]: The colour urgency rank is the band's lower TEWS bound from data/sats_tews.yaml; the most-urgent (RED) colour is derived (max rank), never a literal (CONVENTIONS 1)
- [Phase 04]: evals/results/report.json is a REAL measured run (mode: real, non-zero tokens); the offline report.ci.json stays the CI gate artefact only; the analysis block is excluded from report_digest (volatile cost)
- [Phase 04]: scripts/emit_evals.py is the ONE writer of EVALS.md result cells, rendered strictly from the report and idempotent; it refuses a report whose digest does not recompute (T-04-16/18)
- [Phase 04]: The measured run failed the gate honestly (E-04 unstable, E-07 RECHECK->RECOVER, E-13 injection->ABSTAIN beyond the declared E-09); recorded, not tuned (D-04/D-05)
- [Phase 04]: The TEWS-0 baseline citation is data-driven (data/sats_tews.yaml baseline_citation) and formatted through the ONE citation helper; the baseline rule is emitted only when no rule/override fired and a parameter was used, so a real finding is never displaced (G-1, T-04-22)
- [Phase 04]: INV-1 now fails a scored priority carrying zero citations; graph/nodes.verify is unchanged, so a genuinely uncited priority still fail-closes (T-04-23, EVAL-03)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Beta `langchain.mcp.MCPAdapter` + legacy borrowed-server handshake are OPEN — half-day spike required; define the World-B one-module swap in advance.
- [Phase 1]: RAM headroom ~1.4–2.3 GB — default to Qwen2.5-1.5B, keep 3B opt-in (Qwen licence), measure with `ollama ps`.
- [Phase 3]: LangGraph `interrupt()` + durable checkpointer semantics have non-obvious rules (no side effects before the interrupt; typed resume values) — focused research pass advised before planning.
- [All]: DRY + SOLID are iron-clad (CONVENTIONS.md) — a violation blocks the phase at plan-check, code-review, and verifier gates.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-09T20:52:08.643Z
Stopped at: Completed 04-05-PLAN.md
Resume file: None
