---
phase: 09-retrieval-grounding-borrowed-mcp-depth
plan: 01
subsystem: core / mcp / graph-composition
tags: [retrieval, lexical-scoring, mcp, pydantic, dry, solid, colour-free-contract]

requires:
  - phase: 08-calibrated-confidence-abstention
    provides: the colour-free / no-float contract posture (ConfidenceResult) and the absolute no_match deferral
  - phase: 01-05 (v1.0)
    provides: core/rules.py (the ONE loader), core/citations.py (the ONE citation helper), core/matcher.py (the tokeniser)
provides:
  - "core/retrieval.py — one pure, deterministic integer lexical scorer returning attributed closed-set passages"
  - "EvidencePassage / EvidenceResult contracts with no colour/target/priority/float field, extra='forbid'"
  - "matcher.tokenize — the ONE public normalisation owner (retrieval.tokenize is matcher.tokenize)"
  - "the seventh owned MCP tool retrieve_evidence and the four-site allowlist fan-out (all seven names)"
affects: [09-03 graph grounding, 10 UX adapter]

actuals:
  tokens: 5949
  tasks: 2
  commits: 2
  plan_head_before: 7a2974bfa74b8162e1f9bfd198f54ff2542f3b6e
  plan_head_after: 3db929ec0f53166910b2725a3558cd26647aaffe

tech-stack:
  added: []   # intentionally zero new dependencies (no rank-bm25, numpy, embeddings or vector store)
  patterns:
    - "Colour-free contract: the absence of a colour/target/priority field makes a colour unrepresentable, not merely unused"
    - "One normalisation owner: a public tokenize() reused by matcher and retrieval; no second regex"
    - "Pure core module read through the ONE loader; every label/id/citation sourced from data/*.yaml"
    - "Deterministic integer ranking with an explicit (-score, id) tie-break"
    - "Set-equality allowlist fanned out to four sites in one atomic wave"

key-files:
  created:
    - src/triagedesk/core/retrieval.py
    - tests/test_retrieval.py
  modified:
    - src/triagedesk/core/matcher.py
    - src/triagedesk/core/schema.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/evals/tools.py
    - tests/conftest.py
    - tests/test_safety_spine.py
    - tests/test_mcp_tools.py

key-decisions:
  - "Promoted matcher._tokens to a public tokenize() with _tokens = tokenize, so there is exactly ONE normalisation owner and all three existing call sites stay byte-identical (A3, D9 discretion)"
  - "The evidence contract carries no colour/target/priority field and an integer score (no float), so a colour is unrepresentable — mirrors ConfidenceResult's no-float posture (D9-03)"
  - "Ranking is an in-house integer lexical scorer with an explicit (-score, discriminator_id asc) tie-break; no rank-bm25, numpy or embedding dependency (D9-02)"
  - "E-09's 'feeling unwell' is an honest no_match read from the substrate warning — no alias, fixture or threshold was added (D9-09)"

patterns-established:
  - "Colour-free retrieval contract: five closed-set passage fields + an explicit substrate-sourced no_match"
  - "Four-site allowlist fan-out must move in one atomic edit or build_graph raises at composition (D9-05)"

requirements-completed: [AGENT-03]

coverage:
  - id: D1
    description: "EvidencePassage/EvidenceResult contract with no colour/target/priority/float field and extra='forbid'"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_retrieval.py#test_contract_carries_no_float_or_colour_field"
        status: pass
      - kind: unit
        ref: "tests/test_retrieval.py#test_contract_rejects_an_undeclared_field"
        status: pass
    human_judgment: false
  - id: D2
    description: "ONE public normalisation owner: retrieval.tokenize is matcher.tokenize, no second regex"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_retrieval.py#test_there_is_one_normalisation_owner"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pure deterministic lexical retrieval returning attributed, closed-set, ranked passages"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_retrieval.py#test_retrieve_is_deterministic"
        status: pass
      - kind: unit
        ref: "tests/test_retrieval.py#test_returned_ids_are_members_of_the_closed_set"
        status: pass
      - kind: unit
        ref: "tests/test_retrieval.py#test_rank_is_one_based_and_ordered_by_score_desc_then_id"
        status: pass
    human_judgment: false
  - id: D4
    description: "Seventh owned MCP tool retrieve_evidence registered behind the ONE @audited interceptor; four-site allowlist agrees on seven names"
    requirement: AGENT-03
    verification:
      - kind: integration
        ref: "tests/test_mcp_tools.py#test_retrieve_evidence_returns_closed_set_passages"
        status: pass
      - kind: unit
        ref: "tests/test_safety_spine.py#test_graph_startup_asserts_the_tool_allowlist"
        status: pass
    human_judgment: false
  - id: D5
    description: "E-09 vague complaint returns an explicit no_match — never tuned green with an alias"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_retrieval.py#test_e09_vague_complaint_is_an_honest_no_match"
        status: pass
      - kind: unit
        ref: "tests/test_retrieval.py#test_no_match_reason_is_read_from_the_substrate"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-12
status: complete
---

# Phase 9 Plan 01: Retrieval Grounding — Pure Core & Seventh Owned Tool Summary

**One pure integer lexical scorer turns a free-text complaint into attributed, closed-set SATS discriminator passages under a contract where a colour is unrepresentable — plus the `retrieve_evidence` tool and its four-site allowlist fan-out.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-10-12T21:19Z (approx)
- **Completed:** 2026-10-12T21:22Z
- **Tasks:** 2
- **Files modified:** 10 (2 created, 8 modified)

## Accomplishments

- `core/retrieval.py` — a NEW pure module that ranks a complaint into attributed, closed-set discriminator passages via an in-house integer lexical scorer. It imports nothing from `llm`/`mcp`/`store` (auto-covered by the parametrised purity guard), reads the corpus only through `core/rules.py`, builds every citation with the ONE citation helper, and returns the substrate's own `no_match.warning` on a coverage gap.
- The colour-free contract: `EvidencePassage{discriminator_id,label,citation,score:int,rank:int}` and `EvidenceResult{passages,no_match,reason}` with `extra="forbid"` and **no** colour/target/priority/float field. Proven unrepresentable by iterating `model_fields` and by asserting no substrate colour appears as a serialised key or value.
- ONE normalisation owner: promoted `matcher._tokens` to a public `tokenize()` with `_tokens = tokenize`; `retrieval.tokenize is matcher.tokenize` holds and no second regex exists.
- The seventh owned tool `retrieve_evidence` (thin `@audited()` wrapper, no store/approval token/model) and the four-site allowlist fan-out moved in one atomic commit, so `build_graph` composes over the seven-name surface without drift.
- E-09 stays an honest `no_match` with empty passages — no alias, fixture, threshold or YAML file was touched.

## Task Commits

Each task was committed atomically:

1. **Task 1: colour-free evidence contract, ONE public tokeniser, pure lexical retrieval** — `a0f1766` (feat)
2. **Task 2: the seventh owned tool + the four-site allowlist fan-out in one wave** — `3db929e` (feat)

**Plan metadata:** skipped (commit_docs disabled — see Deviations/Notes)

## Files Created/Modified

- `src/triagedesk/core/matcher.py` — promoted `_tokens` to the public `tokenize()` (one owner; three call sites unchanged via alias)
- `src/triagedesk/core/schema.py` — added `EvidencePassage` / `EvidenceResult` (colour-free, no-float, `extra="forbid"`)
- `src/triagedesk/core/retrieval.py` — NEW pure lexical retrieval (`retrieve`, `_score`, `MATCH_MIN_SCORE`, `MAX_PASSAGES`)
- `src/triagedesk/mcp/server.py` — registered `retrieve_evidence`; docstring and imports updated (six -> seven)
- `src/triagedesk/graph/build.py` — appended `retrieve_evidence` to `OWNED_TOOL_ALLOWLIST` (+comment)
- `src/triagedesk/evals/tools.py` — real in-process `retrieve_evidence` closure in `build_tools`
- `tests/conftest.py` — `retrieve_evidence` fake added to the ONE `build_graph_tools` builder
- `tests/test_safety_spine.py` — exact-set assertion now the owned seven
- `tests/test_mcp_tools.py` — SDK in-memory `Client` call validating to `EvidenceResult`
- `tests/test_retrieval.py` — NEW: determinism, closed-set membership, unrepresentability, E-09 honesty, substrate reason, DRY owner

## Decisions Made

- **Promote `matcher._tokens` in place** (A3): `core/matcher.py` is not a frozen seam; a public `tokenize` plus the `_tokens = tokenize` alias keeps the matcher's behaviour bit-identical and gives exactly ONE normalisation owner.
- **Read, but do not turn into passages, the TEWS band structure**: band data is colour-bearing and complaint-addressable text-free, so a band passage would emit a colour or re-author prose — both forbidden. The passage family is the discriminator catalogue only.
- **No new dependency**: the ranking is the in-house integer scorer (`MATCH_MIN_SCORE`, `MAX_PASSAGES`), no `rank-bm25`/numpy/embeddings.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Full suite green at **315 passed** (304 baseline + 9 retrieval + 1 MCP-tool test + 1 auto-parametrised purity case for the new `core/retrieval.py`).

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change at a trust boundary was introduced beyond the plan's threat model. `retrieve_evidence` is read-only, side-effect-free and carries no colour field.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 09-02 (borrowed read paths + tool allowlist + statement guard) and Plan 09-03 (the `ground` node, the `evidence` state channel, `score -> ground -> verify`) can now consume `EvidenceResult` — a type with no colour field to write.
- The seven-name owned-tool surface is stable across all four set-equality sites; adding an eighth tool later must again move all four in one wave.
- No blockers. `data/*.yaml`, `evals/cases/`, `pyproject.toml`, the scorer's arithmetic, `core/citations.py` and the `@audited` interceptor are untouched (verified by `git diff --stat`).

---
*Phase: 09-retrieval-grounding-borrowed-mcp-depth*
*Completed: 2026-10-12*

## Self-Check: PASSED

- FOUND: `src/triagedesk/core/retrieval.py`
- FOUND: `tests/test_retrieval.py`
- FOUND: `.planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-01-SUMMARY.md`
- FOUND: commit `a0f1766` (Task 1)
- FOUND: commit `3db929e` (Task 2)
- `retrieve_evidence` present at all four set-equality sites (`graph/build.py`, `evals/tools.py`, `tests/conftest.py`, `tests/test_safety_spine.py`) plus the tool registration (`mcp/server.py`).
