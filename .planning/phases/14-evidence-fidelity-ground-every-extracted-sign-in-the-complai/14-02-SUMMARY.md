---
phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai
plan: 02
subsystem: core/approval + mcp/server + graph/nodes
tags: [sats, commit-gate, handover-card, target-time, dry, solid]

requires:
  - phase: 14-01
    provides: grounded extracted signs (no bearing on the commit path, shared suite)

provides:
  - "CommitResult.target: the target the queue row holds on a commit, None on a refusal"
  - "core.approval.target_for_colour: substrate-derived target from the committed colour"
  - "core.approval.committed_or_scored: the ONE home for 'the committed field wins'"
  - "handover card shows the committed colour AND target, or the scored pair on fallback"
  - "test stand-in gate mirrors the shipped gate's committed colour and target (SOLID: L)"

affects: [phase-15, verify-work, any reader of CommitResult or HandoverCard]

actuals:
  tokens: 4890
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "One helper owns 'the committed field wins'; render sites call it, never restate it"
    - "Derived clinical fields (target) are lookups of the committed colour in data/*.yaml"

key-files:
  created: []
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/core/approval.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/graph/nodes.py
    - tests/conftest.py
    - tests/test_safety_spine.py
    - tests/test_commit_idempotent.py
    - tests/test_mcp_tools.py
    - tests/test_graph_durable.py

key-decisions:
  - "CommitResult.target is additive (the model has no extra='forbid') so no caller shape changes"
  - "target_for_colour returns None for an undeclared colour instead of raising (T-14-05)"
  - "ApprovalToken carries no target: the target is a function of the committed colour, so a clinician cannot set a target that disagrees with the colour they approved"
  - "The test stand-in now persists AND reports the committed colour and target, closing a latent Liskov divergence"

patterns-established:
  - "committed_or_scored: one call returns the (colour, target) pair a reader should present"

requirements-completed: [JC-1, JC-5]

coverage:
  - id: D1
    description: "An edit that changes colour and target yields a handover card whose colour AND target equal the persisted queue row."
    requirement: JC-5
    verification:
      - kind: unit
        ref: "tests/test_graph_durable.py#test_edit_resume_supersedes_on_the_durable_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "CommitResult.target reports the persisted row target on approve/edit and None on a refusal."
    requirement: JC-1
    verification:
      - kind: unit
        ref: "tests/test_commit_idempotent.py#test_commit_priority_edit_commits_the_tokens_final_colour"
        status: pass
      - kind: unit
        ref: "tests/test_mcp_tools.py#test_commit_priority_commits_once_through_the_injected_store"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dismissal, refusal and no-commit paths render the scored colour and target."
    requirement: JC-5
    verification:
      - kind: unit
        ref: "tests/test_safety_spine.py#test_handover_card_shows_the_committed_colour_and_target_after_an_edit"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-11-05
status: complete
plan_head_before: 0e7357cce78b87abeeec0fe8e6f5cf67e5b3bc93
plan_head_after: 6e32a93cdc13913bb8d646383ad84fa70bd5ec51
---

# Phase 14 Plan 02: Carry the committed target through an approval edit

**`CommitResult.target` now reports the queue row's target, `commit_priority` derives it from the committed colour through `data/sats_tews.yaml`, and `handover` renders colour and target from one shared helper — so an edit can no longer show a scored target beside a committed colour.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2
- **Files modified:** 9
- **Commits:** 2

## Accomplishments

- `CommitResult` gained an additive `target` field populated from the persisted row; refusals carry `None`.
- `core.approval` gained `target_for_colour` (substrate lookup, `None` when undeclared) and `committed_or_scored` (the single home for "the committed field wins"), leaving `committed_colour` unchanged.
- `commit_priority` computes the committed colour once, derives its target, persists both, and returns the row's values.
- `handover` calls `committed_or_scored` and passes both values to `HandoverCard`; the duplicated conditional is gone.
- The test stand-in gate now persists and reports the committed colour and target via the same helpers, closing a latent divergence where it wrote the scored colour while reporting the committed one.
- Durable edit regression asserts card colour **and** target equal the queue row, with the expected target read from the substrate.

## Task Commits

1. **Task 1: End-to-end — an edited commit's target reaches the card from the queue row** - `6d3624e` (feat)
2. **Task 2: Fallbacks and stand-in parity** - `6e32a93` (test)

## Files Created/Modified

- `src/triagedesk/core/schema.py` — `CommitResult.target` plus docstring.
- `src/triagedesk/core/approval.py` — `target_for_colour`, `committed_or_scored`.
- `src/triagedesk/mcp/server.py` — persists and reports the row's colour and target.
- `src/triagedesk/graph/nodes.py` — `handover` uses the one helper; no inline conditional.
- `tests/conftest.py` — stand-in gate mirrors the shipped gate.
- `tests/test_graph_durable.py` — durable edit regression covers colour and target.
- `tests/test_safety_spine.py` — committed/refused/no-commit target fallbacks.
- `tests/test_commit_idempotent.py` — approve/edit target contract, refusal target is `None`.
- `tests/test_mcp_tools.py` — tool-contract target assertions.

## Decisions Made

- `target` is additive on `CommitResult` because that model does not declare `extra="forbid"`; no caller shape changes.
- `target_for_colour` degrades to `None` for an undeclared colour rather than raising (T-14-05); `ApprovalToken` already rejects undeclared edit colours.
- No target on `ApprovalToken`: the target is a pure function of the committed colour, so a clinician cannot set a target that disagrees with the colour they approved.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first full-suite run failed `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root` because a stale, gitignored `spans.jsonl` was present in the repo root. Removed it; two subsequent full runs passed with the artifact absent. Not caused by this plan's changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The card and the queue row can no longer disagree about colour or target for the same patient.
- Gate, audit, topology, allowlist, deferral and idempotency key are unchanged.

---
*Phase: 14-evidence-fidelity-ground-every-extracted-sign-in-the-complai*
*Completed: 2026-11-05*

## Self-Check: PASSED

- All nine declared files exist.
- Both task commits (`6d3624e`, `6e32a93`) are ancestors of HEAD.
- `handover` contains no unconditional `priority.target` render (the only match is the commit node's scored payload).
- Full suite: 596 passed; `ruff check src tests`: clean.
