---
phase: 02-deterministic-scorer-own-mcp-server
verified: 2026-10-09T18:20:00Z
status: passed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
covered_files:
  - .planning/phases/02-deterministic-scorer-own-mcp-server/02-01-PLAN.md
  - .planning/phases/02-deterministic-scorer-own-mcp-server/02-01-SUMMARY.md
  - .planning/phases/02-deterministic-scorer-own-mcp-server/02-02-PLAN.md
  - .planning/phases/02-deterministic-scorer-own-mcp-server/02-02-SUMMARY.md
  - .planning/phases/02-deterministic-scorer-own-mcp-server/02-03-PLAN.md
  - .planning/phases/02-deterministic-scorer-own-mcp-server/02-03-SUMMARY.md
  - scripts/spike_score.py
  - src/triagedesk/core/matcher.py
  - src/triagedesk/core/recheck.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/core/scorer.py
  - src/triagedesk/mcp/server.py
  - tests/test_matcher.py
  - tests/test_matcher_determinism.py
  - tests/test_mcp_server.py
  - tests/test_mcp_tools.py
  - tests/test_recheck.py
  - tests/test_scorer.py
  - tests/test_scorer_edges.py
  - tests/test_scorer_override.py
  - tests/test_scorer_safety.py
covered_digest: "v3:sha256:78a4d49ee271eeb6683ca03b74ab7524d88e8d24672ea3750ae836bdb87668e4"
---

# Phase 2: Deterministic Scorer & Own MCP Server Verification Report

**Phase Goal:** A pure deterministic scorer converts typed vitals plus matched discriminators into a cited SATS colour and target time, and the owned MCP server exposes the intake and scoring capability as five contracted tools.
**Verified:** 2026-10-09T18:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | TEWS is computed deterministically from typed vitals with no model involvement (SCORE-01) | ✓ VERIFIED | `core/scorer.py` reads only `CaseInput` + `data/sats_tews.yaml` via `rules.get_tews()`; no `llm|mcp|store` import (AST purity guard + independent scan). Spike: RR24/HR118/SBP108/T38.9/alert/no-trauma → `ORANGE tews=6`, matching an independently hand-derived total. |
| 2   | Every priority's citations correspond 1:1 with its triggered rules (`citations == triggered_rules`) (SCORE-03) | ✓ VERIFIED | `scorer.py:260` derives `citations=[rule.citation for rule in triggered_rules]` by construction. Independent probe: list equality + length equality hold on 20 runs and after a discriminator override. |
| 3   | Discriminator overrides apply most-urgent-wins → a colour + target time (SCORE-02) | ✓ VERIFIED | `_most_urgent_category` picks the most urgent present category via data-derived urgency (`tews_to_colour` lower bound). Independent probe: `chest_pain` raises GREEN→ORANGE with ORANGE target; `[chest_pain, obstructed_airway]` → RED regardless of order. |
| 4   | Paediatric / out-of-scope input abstains and escalates; missing, months-expressed, and ambiguous age all abstain and never receive an adult colour (SCORE-04, Roadmap SC2) | ✓ VERIFIED | `_out_of_scope` reads the predicate from `out_of_scope` data. Independent probe: age 4, age 12, missing age, `age_months=18`, `age_ambiguous=True`, height=150-with-no-age all return `out_of_scope=True, abstained=True, colour=None, tews=None` with a reason. |
| 5   | A missing scored vital is detected and never imputed; score inputs ⊆ nurse-provided fields (INTAKE-03) | ✓ VERIFIED | `scorer.py:220` appends to `missing_vitals` and `continue`s (no 0-point default). Independent probe: dropping `temperature_c` removes exactly its 2 points (6→4), lists `temperature` in `missing_vitals` and not in `used_vitals`. |
| 6   | Identical inputs produce an identical colour and an identical citation set on every run (determinism) | ✓ VERIFIED | Independent probe: 20 consecutive `score_priority` calls → 1 distinct colour, 1 distinct citation tuple. `test_scorer_edges`/`test_matcher_determinism` lock it. |
| 7   | Every TEWS band edge on both sides, the colour boundaries, and unit/boundary cases are covered by tests (SCORE-05) | ✓ VERIFIED | Independent reproduction of all numeric edges: RR 8/9/14/15/20/21/29/30; HR 40/41/50/51/100/101/110/111/129/130; SBP 70/71/80/81/100/101/199/200; TEMP 34.9/34.95/35.0/38.4/38.5 — each matches the YAML band; TEWS→colour 0-2 GREEN, 3-4 YELLOW, 5-6 ORANGE, 7+ RED. Gap value 34.95 resolves to the fail-closed higher-points band. |
| 8   | Discriminator matching is a deterministic data lookup over YAML aliases with an explicit `no_match`, returning closed-set ids only (SAFE-01, TOOL-02, Roadmap SC5) | ✓ VERIFIED | `core/matcher.py` tokenises via one regex and matches contiguous token sequences; unmatched → `no_match=True` with the declared warning. Independent probe: "chest pain" → `chest_pain`; unrelated text → `no_match`, empty ids. |
| 9   | Short aliases match only on word/token boundaries — no substring false positives | ✓ VERIFIED | Independent probe: "hypothermia" does NOT fire `hypo` (hypoglycaemia) and "sobbing" does NOT fire `sob` (acute shortness of breath); the sentence yields no match. `test_matcher.py` locks it. |
| 10  | Injected or omitted complaint text cannot change the colour; the colour is never read from the complaint (SAFE-01, E-13 direction) | ✓ VERIFIED | Independent probe: an injection string matching nothing leaves the colour unchanged (GREEN); the scorer consumes only vitals + closed-set ids. `test_matcher_determinism.py` proves injection, complaint-prose isolation, and omission. |
| 11  | The owned MCP server exposes all five contracted tools — `normalize_case`, `match_discriminators`, `score_priority`, `raise_recheck_flag`, `commit_priority` — each validated against the one shared schema (TOOL-01..05, Roadmap SC3) | ✓ VERIFIED | In-memory MCP client `list_tools()` returns exactly those five names; each tool returns a Pydantic contract from the one `core/schema.py`. `test_mcp_server.py` asserts the five-tool superset. |
| 12  | `commit_priority` refuses without a well-formed approval token and performs no queue/store write (TOOL-05) | ✓ VERIFIED | Independent in-memory calls: no token → `refused=True, committed=False`; malformed token → `refused=True, committed=False`; well-formed token → `refused=False, committed=False` (never fakes a write). `server.py` imports no `store`; a source-regex guard confirms it. |
| 13  | `raise_recheck_flag` returns a second-look flag with before/after vitals and never re-classifies or reorders (TOOL-04) | ✓ VERIFIED | `core/recheck.py` compares per-vital band points; `RecheckFlag` has no `colour`/`target`/`destination` field. Independent probe: SBP118→96, RR16→26, HR80→122 flags exactly those three deteriorations; improvement is not reported as deterioration. |
| 14  | `normalize_case` returns the shared `ExtractionResult` with discriminator ids constrained to the closed set and missing vitals left `None` (TOOL-01) | ✓ VERIFIED | `server.py:46` filters model ids through `matcher.validate_discriminator_ids` (the one closed-set authority) and derives `no_discriminator_matched = not ids`; `test_mcp_tools.py` covers unknown-dropped / valid-kept / missing-None / all-unknown cases. |

**Score:** 14/14 truths verified (0 present, behavior-unverified)

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Real LangGraph `interrupt()` approval gate, idempotent content-hash commit, and queue write behind `commit_priority` | Phase 3 | Roadmap Phase 3 SC1–SC2 (GATE-01..04); the Phase-2 stub is the locked deliverable (`02-03-PLAN.md` D-07) |
| 2 | Borrowed maintained SQLite MCP server for case/queue storage + audit | Phase 3 | TOOL-06 mapped to Phase 3 (REQUIREMENTS traceability) |
| 3 | Recheck flag surfaced as a visible second-look with queue position unchanged in the full graph | Phase 3 | Roadmap Phase 3 SC5 |

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/triagedesk/core/scorer.py` | Pure deterministic `score_priority` (TEWS + override + citations) | ✓ VERIFIED | 266 lines; imports only `math`, `core.citations`, `core.rules`, `core.schema`. Substantive band selection, gap totality, out-of-scope, missing-vital, override. Wired: imported by `mcp/server.py` and `core/recheck.py`. |
| `src/triagedesk/core/matcher.py` | Deterministic boundary-respecting alias matcher + closed-set validator | ✓ VERIFIED | 89 lines; one token regex; `match_discriminators` + `validate_discriminator_ids`. Wired into `mcp/server.py`. |
| `src/triagedesk/core/recheck.py` | Pure serial-vitals comparison, no colour | ✓ VERIFIED | 59 lines; reuses `scorer.band_points` (single band authority). Wired into `mcp/server.py`. |
| `src/triagedesk/core/schema.py` | One shared contract module (TriggeredRule, PriorityResult, MatchResult, VitalChange, RecheckFlag, ApprovalToken, CommitResult, CaseInput) | ✓ VERIFIED | All contracts present and imported by the server + tools. |
| `src/triagedesk/mcp/server.py` | Five contracted `@server.tool()` adapters | ✓ VERIFIED | All five registered; each thin over a pure `core/` function; no store on any path. |
| `scripts/spike_score.py` | End-to-end typed case → cited score → owned tool | ✓ VERIFIED | `uv run python scripts/spike_score.py` exits 0, prints ORANGE/tews 6, lists all five tools. |
| `tests/test_scorer*.py`, `test_matcher*.py`, `test_recheck.py`, `test_mcp_tools.py`, `test_mcp_server.py` | Phase proof suite | ✓ VERIFIED | All present; 116 tests pass. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `mcp/server.py score_priority` | `core/scorer.py score_priority` | direct call, no model | WIRED | Tool payload equals the pure result (spike + `test_scorer.py`). |
| `mcp/server.py match_discriminators` | `core/matcher.py` | direct call | WIRED | In-memory tool call returns the same ids as the pure function. |
| `mcp/server.py raise_recheck_flag` | `core/recheck.py compare_vitals` | direct call | WIRED | Tool returns `RecheckFlag` with matching deteriorations. |
| `mcp/server.py commit_priority` | `ApprovalToken.model_validate` | shape validation, no store | WIRED | Refuses missing/malformed; never writes; no `store` import. |
| `mcp/server.py normalize_case` | `core/matcher.validate_discriminator_ids` | closed-set filter | WIRED | Unknown model ids dropped; `no_discriminator_matched` derived. |
| `core/scorer.py` | `core/rules.py get_tews()/get_discriminators()` | data loader | WIRED | Every band/threshold/colour/target read from YAML. |
| `core/scorer.py` | `core/citations.py format_citation` | one citation helper | WIRED | No citation string inlined. |
| `core/recheck.py` | `core/scorer.band_points` | single band authority | WIRED | No duplicated band-selection logic. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `core/scorer.py score_priority` | `tews`, `colour`, `target`, `triggered_rules`, `citations` | `CaseInput` fields + `data/sats_tews.yaml` via `rules.get_tews()` | Yes — computed from live typed input and the loaded rule substrate; no static return | ✓ FLOWING |
| `core/matcher.py match_discriminators` | `matched_ids`, `no_match` | `data/sats_discriminators.yaml` aliases | Yes — real lookup over the loaded closed set | ✓ FLOWING |
| `core/recheck.py compare_vitals` | `deteriorations`, `changes` | previous/current `CaseInput` + `scorer.band_points` | Yes — real per-vital band-point comparison | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full phase suite | `uv run pytest -q` | 116 passed in 1.00s | ✓ PASS |
| End-to-end tracer | `uv run python scripts/spike_score.py` | `[ok] end-to-end path works…`, exit 0 | ✓ PASS |
| Determinism / citations / fail-closed / boundaries / word-boundary / override / injection / recheck (independent probe) | `uv run python /tmp/opencode/verify_p2.py` | all 25 checks PASS, exit 0 | ✓ PASS |
| MCP five-tool surface + commit no-write + purity (independent probe) | `uv run python /tmp/opencode/verify_p2b.py` | all 7 checks PASS, exit 0 | ✓ PASS |
| Band edges reproduced independently | `uv run python /tmp/opencode/edges.py` | every edge matches YAML; colour boundaries exact | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| (none declared) | — | No `probe-*.sh` files exist in the repo; the phase's runnable check is `scripts/spike_score.py`, exercised above (exit 0) | N/A |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| INTAKE-03 | 02-01 | Missing critical vitals detected, no imputation | ✓ SATISFIED | Truth 5; `missing_vitals`/`used_vitals`, independent probe. |
| SCORE-01 | 02-01 | TEWS computed deterministically from typed vitals (no LLM arithmetic) | ✓ SATISFIED | Truth 1; purity guard; spike. |
| SCORE-02 | 02-02 | Discriminator overrides apply (most-urgent wins) → colour + target time | ✓ SATISFIED | Truth 3; `test_scorer_override.py`; independent probe. |
| SCORE-03 | 02-01 | Every priority cites the exact rule/vital(s) that produced it | ✓ SATISFIED | Truth 2; citations derived 1:1 by construction. |
| SCORE-04 | 02-01 | Paediatric / out-of-scope input abstains + escalates | ✓ SATISFIED | Truth 4; `test_scorer_safety.py`; independent probe. |
| SCORE-05 | 02-01 | Band-edge, boundary, and unit cases covered by tests | ✓ SATISFIED | Truth 7; `test_scorer_edges.py`; independent edge reproduction. |
| SAFE-01 | 02-02 | Free-text complaint is untrusted; injection cannot set a priority | ✓ SATISFIED | Truths 8–10; `test_matcher.py`, `test_matcher_determinism.py`. |
| TOOL-01 | 02-03 | Own MCP server exposes `normalize_case` | ✓ SATISFIED | Truth 14; tool listed; closed-set filter verified. |
| TOOL-02 | 02-02 | Own MCP server exposes `match_discriminators` | ✓ SATISFIED | Truth 8; tool listed and callable. |
| TOOL-03 | 02-01 | Own MCP server exposes `score_priority` | ✓ SATISFIED | Truth 11; tool listed and callable. |
| TOOL-04 | 02-03 | Own MCP server exposes `raise_recheck_flag` | ✓ SATISFIED | Truth 13; tool listed and callable. |
| TOOL-05 | 02-03 | Own MCP server exposes `commit_priority` (gated) | ✓ SATISFIED | Truth 12; gated stub refuses without a token and writes nothing (real gate deferred to Phase 3). |

No orphaned requirements: every REQUIREMENTS.md id mapped to Phase 2 (INTAKE-03, SCORE-01…05, SAFE-01, TOOL-01…05) is claimed by a plan's `requirements` field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`, no `TODO`/`HACK`/`PLACEHOLDER`, no empty-return / not-implemented stubs in phase-2 source files | — | None |

**Note (not a gap):** `commit_priority` is an intentional gated stub, recorded as an open entry in `.planning/WINDOWS.md` (kind `stub`) and mandated by `02-03-PLAN.md` D-07 / Roadmap SC3. It is in-scope Phase-2 behaviour, not an incomplete implementation or an unresolved debt marker; `/gsd-ship` will expect this window to be resolved when Phase 3 replaces the stub.

### Human Verification Required

None. The phase delivers pure, deterministic functions with no visual, real-time, or external-service surface; every must-have is exercised by automated tests and independently reproduced.

### Gaps Summary

None. All five Roadmap success criteria and all twelve phase requirements are satisfied with codebase evidence. The scorer is pure (no `llm|mcp|store` import), deterministic (identical inputs → identical colour + citation set), and fail-closed (paediatric/missing/months/ambiguous age abstain; missing vitals are reported, never imputed). Discriminator matching is a boundary-respecting alias lookup over `data/*.yaml` with an explicit `no_match`, and the owned server exposes exactly the five contracted tools — the queue-affecting one gated and inert. Every band edge and colour boundary was independently reproduced against the YAML substrate and matches. The full suite (116 tests) and the end-to-end spike pass.

---

_Verified: 2026-10-09T18:20:00Z_
_Verifier: the agent (gsd-verifier)_
