---
phase: 09-retrieval-grounding-borrowed-mcp-depth
plan: 03
subsystem: graph / retrieval-grounding
tags: [retrieval, grounding, graph-node, state-channel, routing-neutral, dry, solid, decisions]

requires:
  - phase: 09-retrieval-grounding-borrowed-mcp-depth
    plan: 01
    provides: the colour-free EvidenceResult contract and the retrieve_evidence owned tool (the seventh)
  - phase: 08-calibrated-confidence-abstention
    provides: the pure-core -> thin-tool -> thin-node -> channel pattern (assess/confidence) and the D8-12 one-way safety posture
  - phase: 01-05 (v1.0)
    provides: graph/build.py composition root, graph/state.py channel inventory, the four route functions
provides:
  - "the `ground` node (graph/nodes.py::_make_ground) that surfaces attributed evidence and writes only the `evidence` channel"
  - "the `evidence: EvidenceResult | None` state channel (graph/state.py) — advisory, read by nothing that routes"
  - "the routing-neutral `score -> ground -> verify` wiring (graph/build.py): `ground` in TRACER_NODES and a plain `ground -> verify` edge"
  - "tests/test_graph_grounding.py — channel-isolation + routing-neutrality proofs and an optional `retrieve_impl` seam on the ONE shared fake"
  - "docs/DECISIONS.md D21 (retrieval grounding) and D22 (read-only borrowed MCP on the agent path)"
affects: [10 UX adapter (renders the evidence channel)]

actuals:
  tokens: 5758
  tasks: 3
  commits: 3
  plan_head_before: 45f0b084c4b34ef6b27deb2eb3f1196907a6d264
  plan_head_after: 5b120a4e88401c518b47d2b59dae149a6ec4daaa

tech-stack:
  added: []   # intentionally zero new dependencies (no rank-bm25, numpy, embeddings or vector store)
  patterns:
    - "Advisory node: a new node wired by a plain edge that writes its own channel and is read by nothing that routes"
    - "Channel isolation proof: two runs (with/without retrieval) over the SAME note, asserting the routed channels are byte-identical while the advisory channel differs, plus a direct-scorer colour equality"
    - "Routing neutrality by structure: an edge-set assertion plus a source scan of all four route functions for the channel token"
    - "Reuse the ONE shared fake with an optional impl seam rather than adding a second builder (DRY)"

key-files:
  created:
    - tests/test_graph_grounding.py
  modified:
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/state.py
    - src/triagedesk/graph/build.py
    - tests/conftest.py
    - docs/DECISIONS.md

key-decisions:
  - "`ground` is placed `score -> ground -> verify` by plain edges only: `route_after_score`'s LABEL stays `verify` (the decision) while its destination is the advisory node, and a plain `ground -> verify` edge follows — no router reads `evidence` (D9-08)"
  - "`_make_ground` returns exactly `{\"evidence\": result}` — never `priority`, `citations`, `matched_ids` or `no_match` — so retrieval is structurally unable to touch the scored colour (D9-07)"
  - "A4 accepted and declared: when `route_after_verify` loops a failed check back to `score`, `ground` re-runs deterministically on the unchanged complaint; the only cost is a second node span and a second `retrieve_evidence` audit record on a retried case (E-12 slices)"
  - "The `evidence` channel needs no reducer — `ground` is the only writer and its value is a pure function of the complaint (last-write-wins is correct)"
  - "The four route functions must not name the evidence channel in body or docstring, so the neutrality proof is a real structural check rather than a tautology"

patterns-established:
  - "Advisory-channel node: place it between two existing nodes with a plain edge, prove isolation channel-by-channel, prove neutrality by edge set + router source scan"
  - "An optional `*_impl` seam on the ONE `build_graph_tools` fake is the DRY way to vary a single tool in a proof"

requirements-completed: [AGENT-03]

coverage:
  - id: D1
    description: "The `ground` node writes only its own `evidence` channel (no routed channel touched)"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_graph_grounding.py#test_ground_writes_only_its_own_channel"
        status: pass
    human_judgment: false
  - id: D2
    description: "`priority`/`citations`/`matched_ids`/`no_match` are identical with and without retrieval; each run's colour equals a direct scorer call"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_graph_grounding.py#test_evidence_channel_is_isolated_from_every_routed_channel"
        status: pass
      - kind: unit
        ref: "tests/test_graph_grounding.py#test_ground_does_not_change_the_delivered_colour"
        status: pass
    human_judgment: false
  - id: D3
    description: "`ground` is routing-neutral: `score -> ground -> verify` by plain edges, no router reads `evidence`, no `ground` edge reaches `commit`"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_graph_grounding.py#test_ground_is_wired_by_plain_edges_and_routes_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "The node reaches the injected `retrieve_evidence` tool with the case's complaint"
    requirement: AGENT-03
    verification:
      - kind: integration
        ref: "tests/test_graph_grounding.py#test_ground_reaches_the_retrieve_evidence_tool"
        status: pass
    human_judgment: false
  - id: D5
    description: "E-09 stays an honest no_match defer with no queue write — never tuned green with an alias"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_graph_grounding.py#test_e09_grounding_is_an_honest_no_match_defer_with_no_write"
        status: pass
    human_judgment: false
  - id: D6
    description: "The retrieval/grounding and borrowed read-only decisions are recorded (D21, D22)"
    requirement: AGENT-03
    verification:
      - kind: unit
        ref: "tests/test_docs_final.py"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-12
status: complete
---

# Phase 9 Plan 03: Retrieval Grounding — The Advisory `ground` Node & Decision Records Summary

**Retrieval is wired into the graph as an advisory, routing-neutral `ground` node (`score -> ground -> verify`) that writes its own `evidence` channel and is structurally unable to set a colour — proven channel-by-channel — with the phase's two design decisions recorded as D21/D22.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-10-12
- **Tasks:** 3
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `graph/state.py` — a NEW `evidence: EvidenceResult | None` channel whose comment states it is written by `ground`, consulted by nothing that routes, and advisory display/provenance only; the module docstring's channel inventory now names `ground` adding `evidence`.
- `graph/nodes.py` — `_make_ground` mirrors the `_make_assess` thin-factory shape: an async node whose payload is exactly `{"complaint": state["case"].complaint}`, decoded with `parse_tool_result(EvidenceResult, ...)`, returning exactly `{"evidence": result}`. Its docstring declares the retry consequence (the `verify -> score` loop re-runs `ground` deterministically; a second span/audit record on a retried case only) and that it touches no model and writes no store.
- `graph/build.py` — `ground` added to `TRACER_NODES` immediately after `score` (so the composition-root `_spanned` wrapper gives it a node span for free); the `score` conditional-edge mapping's `verify` route now targets `ground`; a plain `ground -> verify` edge follows. No conditional edge leaves `ground` and no router reads the channel (D9-08). The `build_graph` docstring reads `score -> ground -> verify` and states the neutrality.
- `tests/test_graph_grounding.py` — six offline proofs: node-writes-only-its-channel; the strongest channel-isolation proof (two runs over the same note with real vs no-match retrieval — routed channels byte-identical, `evidence` differs, each colour equals a direct scorer call); routing neutrality (edge set + a source scan of all four route functions); the tool is reached with the case's complaint; E-09 stays an honest `no_match` defer with no write; the delivered colour is unchanged.
- `tests/conftest.py` — the ONE shared `build_graph_tools` fake gained an optional `retrieve_impl` seam (mirroring `normalize_impl`); no second builder was added (DRY).
- `docs/DECISIONS.md` — D21 (retrieval grounding over the SATS discriminator KB) and D22 (read-only borrowed MCP on the agent path), above the disclosed-components table, in the existing ADR-lite shape. The table is unchanged (no component added).

## Task Commits

Each task was committed atomically:

1. **Task 1: the `ground` node, the `evidence` channel, and the routing-neutral wiring** — `10cce51` (feat)
2. **Task 2: the channel-isolation and routing-neutrality proofs** — `402769c` (test)
3. **Task 3: record the retrieval/grounding and borrowed read-only decisions (D21, D22)** — `5b120a4` (docs)

**Plan metadata:** skipped (commit_docs disabled — see Deviations/Notes)

## Files Created/Modified

- `src/triagedesk/graph/state.py` — `EvidenceResult` import + the `evidence` channel (comment: written by `ground`, read by nothing that routes, no reducer needed) + docstring inventory
- `src/triagedesk/graph/nodes.py` — `_make_ground` (returns exactly `{evidence}`), registered in `make_nodes` after `score`; module docstring "no model" inventory now names `ground`
- `src/triagedesk/graph/build.py` — `ground` in `TRACER_NODES`; `score`'s `verify` route -> `ground`; plain `ground -> verify` edge; `build_graph` docstring updated
- `tests/test_graph_grounding.py` — NEW: six advisory-grounding proofs (isolation + neutrality + tool-reached + E-09 + colour)
- `tests/conftest.py` — optional `retrieve_impl` seam on the ONE `build_graph_tools` fake
- `docs/DECISIONS.md` — D21 and D22 rows

## Decisions Made

- **Place `ground` on plain edges** (`score -> ground -> verify`): the conditional edge's route LABEL stays `verify` (the decision is unchanged) while its destination is the advisory node, and a plain edge carries `ground` onward. This keeps the path taken identical whether or not retrieval runs.
- **Accept and declare A4** (the `verify -> score` retry re-runs `ground`): harmless and deterministic — the complaint is unchanged, so the same `EvidenceResult` is produced, and `ground` writes only `evidence`. The alternative (placing `ground` on the success arm) was rejected because it would leave a never-verified case without evidence.
- **No reducer for `evidence`**: `ground` is the only writer and its output is a pure function of the complaint, so last-write-wins is correct.
- **Routers must not name the channel**: the four route functions' bodies and docstrings stay free of the evidence token, which is what makes the neutrality proof a real structural check.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Full suite green at **340 passed** (334 baseline + 6 new grounding tests). The phase gate (`test_graph_grounding.py`, `test_retrieval.py`, `test_graph_confidence.py`, `test_eval_suite.py`, `test_borrowed_store.py`, `test_safety_spine.py`, `test_purity.py`, `test_no_duplicated_sats.py`) is **79 passed**. `git diff --stat` shows no change to `data/`, `evals/cases/`, `src/triagedesk/core/scorer.py`, `src/triagedesk/core/citations.py`, or `src/triagedesk/mcp/server.py` (the `@audited` interceptor's behaviour).

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change at a trust boundary beyond the plan's threat model. The `ground` node is read-only, side-effect-free, carries no colour field and is wired by plain edges.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 (the desk UX adapter) can consume the `evidence` channel to render the attributed excerpts; the channel is advisory and its shape (`EvidenceResult`) is fixed.
- The `ground` node carries no routing power and cannot influence the scored colour or the path taken, so any later change that made retrieval decision-bearing would fail the neutrality proof in `tests/test_graph_grounding.py`.
- No blockers. `data/*.yaml`, `evals/cases/`, `pyproject.toml`, the scorer's arithmetic, `core/citations.py` and the `@audited` interceptor are untouched.

---
*Phase: 09-retrieval-grounding-borrowed-mcp-depth*
*Completed: 2026-10-12*

## Self-Check: PASSED

- FOUND: `src/triagedesk/graph/nodes.py` (`_make_ground`)
- FOUND: `src/triagedesk/graph/state.py` (`evidence` channel)
- FOUND: `src/triagedesk/graph/build.py` (`ground` in TRACER_NODES, plain `ground -> verify` edge)
- FOUND: `tests/test_graph_grounding.py`
- FOUND: `docs/DECISIONS.md` (D21, D22)
- FOUND: commit `10cce51` (Task 1)
- FOUND: commit `402769c` (Task 2)
- FOUND: commit `5b120a4` (Task 3)
- `evidence` channel isolated (two-run byte-identical routed channels) and `ground` routing-neutral (edge set + four-router source scan) — both proven green.
