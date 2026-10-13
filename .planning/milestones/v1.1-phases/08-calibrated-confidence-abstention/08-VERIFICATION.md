---
phase: 08-calibrated-confidence-abstention
verified: 2026-10-13T13:19:16Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - .planning/phases/08-calibrated-confidence-abstention/08-01-PLAN.md
  - .planning/phases/08-calibrated-confidence-abstention/08-01-SUMMARY.md
  - .planning/phases/08-calibrated-confidence-abstention/08-02-PLAN.md
  - .planning/phases/08-calibrated-confidence-abstention/08-02-SUMMARY.md
  - .planning/phases/08-calibrated-confidence-abstention/08-03-PLAN.md
  - .planning/phases/08-calibrated-confidence-abstention/08-03-SUMMARY.md
  - EVALS.md
  - docs/DECISIONS.md
  - evals/results/report.json
  - scripts/emit_evals.py
  - src/triagedesk/core/confidence.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/evals/analysis.py
  - src/triagedesk/evals/report.py
  - src/triagedesk/evals/runner.py
  - src/triagedesk/evals/tools.py
  - src/triagedesk/graph/build.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/graph/state.py
  - src/triagedesk/mcp/server.py
  - tests/conftest.py
  - tests/test_confidence.py
  - tests/test_demo.py
  - tests/test_eval_honest_terminal.py
  - tests/test_eval_invariants.py
  - tests/test_eval_report.py
  - tests/test_eval_suite.py
  - tests/test_graph_confidence.py
  - tests/test_mcp_server.py
  - tests/test_safety_spine.py
  - tests/test_scorer_baseline.py
covered_digest: "v3:sha256:9d69520fb3896a01b5c34b5f5687059ca10d4bc33ae4dd4068d6c8d8a12f9ded"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed: []
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "A stray repo-root spans.jsonl (a gitignored artifact, timestamped after this phase) transiently poisoned the Phase-7 hermeticity guard tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root, so an unclean tree reported 1 failed / 453 passed."
    category: other
    reason: "Environmental, not a Phase-8 regression: the artifact is untracked and gitignored (.gitignore:22), no Phase-8 file is involved, and in a clean tree the full suite is 454 passed across three consecutive runs with the file absent. No deterministic failure reproduces; no action required for Phase 8."
    evidence_status: "no reproducible failure in a clean tree — 454 passed x3"
human_verification: []
---

# Phase 8: Calibrated Confidence & Abstention Verification Report

**Phase Goal:** The system computes a deterministic coverage/deferral signal — never a model probability — exposed by an `assess_confidence` tool and wired to routing, so low confidence can only make the system more cautious (escalate or request-missing-info), never `commit` and never downgrade a scored colour.
**Verified:** 2026-10-13T13:19:16Z
**Status:** passed
**Re-verification:** Yes — STALE re-verification (later phases 9–12 additively edited shared source files that Phase 8's report covered). Not a gap-closure pass: previous status was already `passed`.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `assess_confidence` returns a deterministic coverage/deferral signal derived from exactly four components (vitals coverage, discriminator coverage, override-vs-TEWS path, TEWS distance from the band edge) — never a model probability/percentage (SC1, D8-01). | ✓ VERIFIED | `core/confidence.py::assess()` computes `COMPONENT_NAMES` = (vitals_coverage, discriminator_coverage, override_path, tews_band_distance), `COMPONENT_COUNT == 4`; `assess` signature is `(matched_ids, no_match, priority) -> ConfidenceResult` (unchanged since the prior pass — no commit touches `core/confidence.py`). `tests/test_confidence.py::test_assess_is_deterministic` and `::test_assess_reports_the_declared_components` pass. |
| 2 | The contract carries no float and nothing readable as a clinical probability — only a `deferral` bool, a closed-set `level`, a per-component breakdown and a `reason`; no percentage on the contract, the tool output, or the CLI (SC1, D8-02/D8-04). | ✓ VERIFIED | `ConfidenceResult.model_fields == ['deferral','level','components','reason']`, `ConfidenceComponent.model_fields == ['name','satisfied','detail']`; runtime probe: zero `float`-annotated fields, `'%' not in ConfidenceResult(...).model_dump_json()` → True. `tests/test_confidence.py::test_contract_carries_no_float_or_probability_field` passes. |
| 3 | `no_match` forces `deferral = True` (`level == "low"`) regardless of the other components — a no-match case is never high confidence (SC3, D8-11). | ✓ VERIFIED | `assess()` short-circuits on `no_match` before the satisfied-count branch; runtime probe `assess([], True, PriorityResult(...))` → `deferral=True, level='low'`. `tests/test_confidence.py::test_no_match_forces_a_deferral_never_high_confidence` and `tests/test_graph_confidence.py::test_no_match_e09_defers_to_a_terminal_without_a_queue_row` pass. |
| 4 | A deferral routes only to `escalate` / `request_missing_info` and never reaches `commit`; no queue row is written; the deterministic `recheck` still runs before `assess` (SC2, D8-08/D8-12). | ✓ VERIFIED | `graph/build.py`: `recheck → assess` edge (line 270); `route_after_assess` returns only `escalate`/`request_missing_info`/`approval_gate` (runtime probe: deferral→escalate, deferral+missing_vitals→request_missing_info, neutral→approval_gate); `escalate`/`request_missing_info` end at `END` with no edge to `commit`. `tests/test_graph_confidence.py::test_a_deferral_cannot_reach_the_commit` and `::test_a_forced_deferral_ends_at_a_terminal_with_no_write` pass. |
| 5 | The signal never downgrades a scored colour: `assess` never assigns `priority`, and `core/scorer.py` takes no confidence input and is untouched by this phase (SC2, D8-12, D-18). | ✓ VERIFIED | `graph/nodes.py::_make_assess` returns only `{"confidence": signal}`. `git diff 45fd1dd..HEAD -- src/triagedesk/core/scorer.py src/triagedesk/core/citations.py src/triagedesk/mcp/audit.py` is EMPTY (scorer/citations/audit untouched across phases 9–12). `tests/test_graph_confidence.py::test_assess_does_not_change_the_scored_colour` and `tests/test_confidence.py::test_scorer_has_no_confidence_input_and_does_not_import_confidence` pass. |
| 6 | The deferral threshold is derived from a stated asymmetric cost and is a named constant — never tuned to make a test green (SC3, D8-09). | ✓ VERIFIED | `core/confidence.py: DEFERRAL_MIN_SATISFIED_COMPONENTS = 2` (module-level int, runtime-confirmed); `docs/DECISIONS.md` D20 (line 177) records the two named costs (a missed emergency vastly outweighs a needless deferral) and cites the constant; `tests/test_confidence.py::test_deferral_threshold_is_a_named_constant_and_flips_on_the_count` passes. |
| 7 | The deferral rate is reported next to the outcome breakdown, from `report.json` only (SC3, D8-10/D8-16). | ✓ VERIFIED | `evals/report.py::ReportCase.deferrals`/`Analysis.deferral_rate`; current `report.json` `analysis.deferral_count/runs/rate` = 15/34/0.4412, `deferral_cases` = [E-01,E-07,E-08,E-09,E-14] (moved from the Phase-8-time 12/32 after Phase 11's E-04/E-07 fidelity fix — owner-confirmed, see Non-Gaps below); `EVALS.md` §3 `Deferral rate` cell = `15/34` and §6.1 record derived from the report. |
| 8 | Calibration (ECE + risk–coverage) is measured offline on a declared split, both sample sizes named, declared a small-sample measure (SC4, D8-13/D8-15). | ✓ VERIFIED | `evals/analysis.py::_calibration` partitions by `held_out`; current `report.json` `analysis.calibration`: `ece=0.2053…`, `ece_bins=4`, `n_calibration=14`, `n_held_out=2`, `held_out_ids=[H-01,H-02]`, `risk_coverage` = 3 points, `small_sample_caveat` names both n's ("not a validated calibrated probability"). `EVALS.md` §3 `Calibration (small-sample)` cell = `ECE 0.205 · n_calibration=14 · n_held_out=2` + §3.2 declaration. |
| 9 | `EVALS.md` is a pure projection of `evals/results/report.json` — no hand-typed number; the generator's `--check` gate passes (D8-14). | ✓ VERIFIED | `uv run python scripts/emit_evals.py --check` → exit 0 ("EVALS.md is up to date (report 12d6d1b909d33872)"). Runtime probe `compute_report_digest(Report.model_validate_json(...)) == report.report_digest` → True. |
| 10 | The owned-tool allowlist is declared once and `build_graph` composes over it; `assess_confidence` is registered, audited exactly once and pure (no store, no token, no queue row) (D8-05/06/07). | ✓ VERIFIED | `OWNED_TOOL_ALLOWLIST` (graph/build.py) contains `assess_confidence`; the live server lists 7 owned tools incl. `assess_confidence`. NOTE (expected additive evolution): the allowlist is now **seven** names, not six — Phase 9 added `retrieve_evidence` in the same wave (`3db929e feat(09-01): add the seventh owned tool and fan out the allowlist in one wave`). The Phase-8 property this truth asserts still holds: `assess_confidence` is in the allowlist, the exact set is asserted at both seams, and the tool is registered/audited once/pure. `tests/test_safety_spine.py::test_graph_startup_asserts_the_tool_allowlist` and `tests/test_graph_confidence.py::test_assess_confidence_is_pure_and_audited_exactly_once` pass. |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

### Deferred Items

None outstanding. The single Phase-8-time deferred item (the real-mode `gate.passed == false` for the pre-existing extraction failures) was owned by Phase 11, which is now complete — see Non-Gaps below.

### Advisory (New Scope, Unevidenced)

Re-verification ran; one environmental observation recorded, no deterministic failure reproduces.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | A stray gitignored repo-root `spans.jsonl` (timestamped after this phase) transiently tripped the Phase-7 hermeticity guard `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`, so an unclean tree showed `1 failed / 453 passed`. | other | New-scope and not Phase-8-related: the artifact is untracked/gitignored, no Phase-8 file is involved, and in a clean tree the suite is `454 passed` across three consecutive runs with the file absent. No reproducible failure → advisory, not a blocker. |

### Non-Gaps (owner-confirmed; recorded so a future pass does not re-flag them)

1. **D8-11 is an ABSOLUTE `no_match` deferral.** A case where no discriminator matched always defers (`level == "low"`) regardless of the other components — this is the intended one-way-caution property, not an over-deferral defect.
2. **The published report is `mode: real` and shows the residual honest misses.** After Phase 11's fidelity fix, `report.json` `gate` = `{passed: false, unexpected_failures: ['E-11','E-13'], violations: []}`, and `E-09` carries `declared_failure: true`. This honest measured state (owner-reviewed) is NOT a Phase-8 gap. The Phase-8-time deferred item (E-04/E-07/E-13) is resolved: E-04 and E-07 now pass (E-07 defers as a RECHECK terminal), and the residual failures are E-11/E-13, which post-date this phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/triagedesk/core/confidence.py` | Pure four-component signal + named threshold | ✓ VERIFIED | 196 lines; imports only `core.rules` + `core.schema`; `assess(...)`, `DEFERRAL_MIN_SATISFIED_COMPONENTS`, `COMPONENT_NAMES`/`COMPONENT_COUNT`. Untouched since the prior pass. |
| `src/triagedesk/core/schema.py` | `ConfidenceLevel`/`ConfidenceComponent`/`ConfidenceResult` (no float) | ✓ VERIFIED | Lines 145–179; no float/probability field; `HandoverCard` field set unchanged. Phase 9 appended `EvidencePassage` (additive). |
| `src/triagedesk/graph/state.py` | `confidence` channel | ✓ VERIFIED | `confidence: ConfidenceResult | None`. |
| `src/triagedesk/graph/nodes.py` | `_make_assess` node factory | ✓ VERIFIED | `_make_assess` (line 227) + `"assess"` in `make_nodes` (line 437); returns only `{"confidence": signal}`. |
| `src/triagedesk/graph/build.py` | allowlist (contains `assess_confidence`), `assess` node, `route_after_assess`, `recheck→assess` | ✓ VERIFIED | Allowlist now 7 (Phase 9 additive); `TRACER_NODES` includes `assess`; `route_after_assess`; edges wired (`recheck→assess`, `assess→{escalate,request_missing_info,approval_gate}`). |
| `src/triagedesk/mcp/server.py` | owned tool `assess_confidence` | ✓ VERIFIED | `@server.tool()` + `@audited()`, delegating to `confidence.assess`; no store/token. Live server lists it. |
| `src/triagedesk/evals/report.py` | deferral/held-out fields, `RiskCoveragePoint`, `Calibration`, digest sealing | ✓ VERIFIED | Fields present; `_digest_payload` seals `held_out`/`confidence_levels`/`deferrals`/`confidence_satisfied` (runtime: `'deferrals' in cases[0]`). |
| `src/triagedesk/evals/analysis.py` | deferral tally + declared-split calibration | ✓ VERIFIED | `deferral_*` separate from the direction split; `_calibration`, `_risk_coverage`, `_expected_calibration_error`. |
| `src/triagedesk/evals/runner.py` | confidence capture + recheck precedence + deferral-aware gate | ✓ VERIFIED | `_capture` reads the graph's `confidence` channel; `_outcome` RECHECK precedence; `_build_gate` excludes only all-`True`-deferred cases. |
| `scripts/emit_evals.py` | deferral-rate + calibration §3 rows, §4 deferral marker, derived §6.1 record | ✓ VERIFIED | `_measured_metrics` rows; `_shows_deferral_marker`; `_render_deferral_block` derived from report. |
| `EVALS.md` | §3 rows, §3.2 small-sample declaration, §6/§6.1 record | ✓ VERIFIED | Measured cells generated from report.json (`Deferral rate 15/34`, `ECE 0.205 · n_calibration=14 · n_held_out=2`); `--check` exits 0. |
| `evals/results/report.json` | real-mode report, recomputing digest | ✓ VERIFIED | `mode: real`, digest `12d6d1b909d33872…` recomputes; per-case deferrals recorded. |
| `tests/test_confidence.py` | one-way + contract-shape proofs | ✓ VERIFIED | 6 tests; all pass. |
| `tests/test_graph_confidence.py` | deferral routing / no-write integration proofs | ✓ VERIFIED | 7 tests incl. 4 async end-to-end; all pass. |
| `docs/DECISIONS.md` | D20 asymmetric-cost rationale | ✓ VERIFIED | D20 at line 177. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `assess` node | `assess_confidence` tool | `tools["assess_confidence"](payload)` | ✓ WIRED | `graph/nodes.py:243`; payload validated via `parse_tool_result(ConfidenceResult, …)`. |
| `assess_confidence` tool | `confidence.assess` | delegation | ✓ WIRED | `mcp/server.py`; also on both tool factories (`evals/tools.py`, `tests/conftest.py`). |
| `assess` node | `confidence` state channel | return `{"confidence": signal}` | ✓ WIRED | `graph/state.py`; read by `route_after_assess`. |
| `confidence` channel | `route_after_assess` | gate on `signal.deferral` | ✓ WIRED | `graph/build.py:150-176`; conditional edges to escalate/request_missing_info/approval_gate (runtime probe confirmed all three arms). |
| `recheck` | `assess` | `graph.add_edge("recheck","assess")` | ✓ WIRED | `graph/build.py:270`; asserted by `test_a_deferral_cannot_reach_the_commit`. |
| graph `confidence` channel | `ReportCase.deferrals` | `runner._capture` → `_run_case` | ✓ WIRED | Never re-derived; report carries per-case `deferrals`. |
| `Analysis.deferral_rate`/`calibration` | `EVALS.md` §3 `Measured` cells | `emit_evals._measured_metrics` | ✓ WIRED | `--check` exits 0. |
| allowlist | `mcp/server.py` ↔ `evals/tools.py::build_tools` ↔ `tests/conftest.py::build_graph_tools` | set-equality via `assert_tool_allowlist` | ✓ WIRED | Exact set asserted (7 names incl. `assess_confidence`); server listing confirmed at runtime. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `graph/nodes.py::_make_assess` | `signal` | `confidence.assess(matched_ids, no_match, priority)` over the graph's own typed state | Yes | ✓ FLOWING |
| `runner._capture`/`_run_case` | `confidence`/`deferrals`/`confidence_satisfied` | `result.get("confidence")` (graph channel) | Yes | ✓ FLOWING |
| `report.json` | `analysis.deferral_*`/`calibration` | `analyse(report)` over the measured per-case facts | Yes | ✓ FLOWING |
| `EVALS.md` §3/§4/§6.1 | `Measured` cells / marker / record | `render_evals(EVALS.md, report)` | Yes | ✓ FLOWING |

No static returns, hardcoded literals, or mocks stand in for the signal: the published report carries real measured deferrals (15/34) and calibration (n=14/n=2).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Whole suite green, hermetic | `uv run pytest -q` (clean tree, x3) | `454 passed`, exit 0; no repo-root `spans.jsonl`/`*.db` created | ✓ PASS |
| Phase-8 proof suite | `uv run pytest tests/test_confidence.py tests/test_graph_confidence.py -q` | `13 passed` | ✓ PASS |
| Safety spine + purity | `uv run pytest tests/test_safety_spine.py tests/test_purity.py -q` | `20 passed` | ✓ PASS |
| Deferral never reaches `commit` (end-to-end) | `uv run pytest "tests/test_graph_confidence.py::test_a_forced_deferral_ends_at_a_terminal_with_no_write" "::test_a_deferral_cannot_reach_the_commit" "::test_assess_does_not_change_the_scored_colour" "::test_assess_confidence_is_pure_and_audited_exactly_once" "::test_no_match_e09_defers_to_a_terminal_without_a_queue_row" -q` | `5 passed` | ✓ PASS |
| EVALS.md is a pure projection | `uv run python scripts/emit_evals.py --check` | `EVALS.md is up to date (report 12d6d1b909d33872)`, exit 0 | ✓ PASS |
| Report digest recomputes | `compute_report_digest(Report.model_validate_json(...)) == report.report_digest` | `True` | ✓ PASS |
| Owned server exposes `assess_confidence` | `server.list_tools()` | 7 tools incl. `assess_confidence` | ✓ PASS |
| Routing arms are one-way | `route_after_assess(...)` runtime probe | deferral→escalate; deferral+missing→request_missing_info; neutral→approval_gate | ✓ PASS |
| Published state matches owner declaration | inspect `report.json` | `mode: real`; deferrals [E-01,E-07,E-08,E-09,E-14]; gate failures E-11/E-13; E-09 declared | ✓ PASS |

### Probe Execution

No probes declared (`scripts/*/tests/probe-*.sh` absent) — Step 7c not applicable.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/test_confidence.py` | AGENT-02 | 6 | 0 | none | Value + Behavioral (determinism, component set, no-float contract) | PASS |
| `tests/test_graph_confidence.py` | AGENT-02 | 7 | 0 | none | Behavioral (graph invocation: no `__interrupt__`, no `commit_priority` call, `memory_store.rows == []`) | PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0. The deferral proof tests invoke the compiled graph and assert the absence of a queue row and the terminal reached — value/behavioral level, not existence-only.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| AGENT-02 | 08-01, 08-02, 08-03 | Deterministic coverage/deferral signal (never a model probability / percentage as clinical risk), an `assess_confidence` tool exposing it, low confidence routing to escalate / request-missing-info and never to `commit`, never downgrading a scored colour. | ✓ SATISFIED | Truths 1–10 above; REQUIREMENTS.md maps AGENT-02 → Phase 8 (Complete, line 91); all three plans declare `requirements: [AGENT-02]`. |

No orphaned requirements: Phase 8's only mapped requirement id (AGENT-02) appears in every plan's `requirements` field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | None | — | No `TBD`/`FIXME`/`XXX`, placeholder text, empty-implementation return, or hardcoded-empty data found in the phase's implementation files. The two `return None`/sentinel paths reviewed (`route_after_assess` defensive arm, `_band_distance` fallback) are documented, unreachable-by-construction, and covered by direct tests — not stubs. No debt marker blocks this pass. |

### Human Verification Required

None. All four ROADMAP success criteria resolve to machine-verified evidence (deterministic unit tests, graph-invoking integration tests, and the report/generator gates). No visual, real-time, or external-service behaviour is asserted by this phase's goal, and no truth was left present-but-behavior-unverified.

### Gaps Summary

No gaps. The four ROADMAP success criteria still hold against the current (post-Phase-12) codebase:

- **SC1** — `core/confidence.py::assess` returns a four-component deterministic signal (`COMPONENT_NAMES`/`COMPONENT_COUNT == 4`); the contract (`ConfidenceResult`/`ConfidenceComponent`) has no float/probability/percentage field, so a model-derived number is unrepresentable.
- **SC2** — `recheck → assess → approval_gate` with `route_after_assess` reaching only `escalate`/`request_missing_info` (both terminal, no edge to `commit`); a deferred case provably writes no queue row and never reaches the gate, and `assess` never assigns `priority` (the scorer/citations/audit are byte-identical across phases 9–12), so no scored colour can be downgraded.
- **SC3** — `DEFERRAL_MIN_SATISFIED_COMPONENTS` is a named constant with its asymmetric-cost rationale in D20; `no_match` forces a deferral; the deferral rate is reported from `report.json` (15/34).
- **SC4** — ECE + risk–coverage are measured on a declared split (calibration n=14 / held-out n=2), both sizes named, with an explicit small-sample caveat, published only via the generator.

Two points checked and explicitly **not** gaps (owner-confirmed):
1. The real-mode `gate.passed == false` (E-11/E-13, with E-09 declared) is the owner-reviewed honest measured state after Phase 11's fidelity fix; it post-dates this phase.
2. The ECE is computed over the **calibration** split (`held_out=false`, n=14) and the held-out split (`held_out=true`, H-01/H-02, n=2) is named to bound the declared failure — an explicitly declared, owner-reviewed interpretation (`EVALS.md` §3.2), with both `n`s published so the split is auditable rather than chosen after seeing the result.

**Additive evolution noted (not a regression):** the owned-tool allowlist grew from six to seven names when Phase 9 added `retrieve_evidence`; `assess_confidence` remains in the allowlist and the Phase-8 property (declared-once allowlist, exact-set assertion at both seams, tool registered/audited-once/pure) is intact.

---

_Verified: 2026-10-13T13:19:16Z_
_Verifier: the agent (gsd-verifier)_
