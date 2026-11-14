---
phase: 22
plan: "01"
subsystem: graph
tags: [emergency, bypass, pre-check, langgraph, safety]
requires:
  - core.scorer.score_priority
  - core.rules.colour_urgency
provides:
  - core.emergency.EmergencyVerdict
  - core.emergency.assess_emergency
  - graph.nodes.emergency_check
  - graph.build.route_after_emergency
affects:
  - graph.build.TRACER_NODES
  - graph.state.TriageState
  - graph.nodes.approval_gate
tech-stack:
  added: []
  patterns:
    - "pure pre-check reads the ONE scorer; never a second colour producer"
    - "conditional arm selection before normalize"
key-files:
  created:
    - src/triagedesk/core/emergency.py
    - tests/test_emergency.py
  modified:
    - src/triagedesk/graph/state.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/graph/__init__.py
    - tests/conftest.py
    - tests/test_no_duplicated_sats.py
decisions:
  - "The pre-check scores with score_priority(case, []) and derives the most urgent band from colour_urgency; it emits no colour."
  - "The internal route tokens are fast/normal, not the word 'emergency', because that word is a loaded discriminator category and the SATS DRY guard forbids repeating it under src/."
  - "The DRY guard gains ONE exact STRUCTURAL_CHANNEL_KEYS exemption for the CONTEXT-fixed 'emergency' state/payload key, pinned narrow by its own test."
  - "The checkpointer msgpack allowlist now derives from core.schema + core.emergency so a resumed verdict stays typed."
metrics:
  duration: "~35 min"
  completed: "2026-11-14"
  tasks: 4
  commits: 2
  plan_head_before: "3b0daa2f395f2db43993d05902c315065187f3d8"
  plan_head_after: "955da91"
status: complete
---

# Phase 22 Plan 01: Deterministic emergency pre-check and fast arm Summary

## One-liner

A pure `EmergencyVerdict` pre-check fires on a complete case whose derived TEWS is the most
urgent band, and a new `emergency_check` node routes it to `retrieve` — skipping `normalize`
only, while the normal arm keeps today's exact node order plus the one pre-check node.

## What was built

- `core/emergency.py` — `EmergencyVerdict` (no colour/priority/target field) and
  `assess_emergency(case)`, which calls `scorer.score_priority(case, [])` and derives the most
  urgent band from `rules.colour_urgency()`. It fires only when the score is non-abstained,
  in scope, has no missing scored vital, and equals the most urgent colour.
- `TriageState.emergency: EmergencyVerdict | None` and the `emergency_check` node, which writes
  the verdict and the fast/normal `route`.
- Topology: `ingest → emergency_check → (fast: retrieve | normal: normalize → retrieve) →
  score → ground → verify → recheck → assess → approval_gate → commit → handover`.
  `TRACER_NODES` gains `emergency_check`; every downstream edge is unchanged.
- `approval_gate` payload gains `emergency`, populated only when the bypass fired.
- The durable checkpointer's msgpack allowlist now covers `core.emergency`.

## Tests

- `tests/test_emergency.py` (13 tests): fires on the most urgent band; not on a lower band,
  a missing vital, an out-of-scope case or an unstructured case; verdict field-set proof;
  data-derived predicate across all 24 bundled eval cases; fast arm skips `normalize_case`;
  normal arm still extracts; payload fact vs `None`; router; topology.
- `tests/test_no_duplicated_sats.py`: the structural-key exemption is pinned to exactly
  `{"emergency"}`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] The durable checkpointer would downgrade the verdict**
- **Found during:** Task 2 (state wiring)
- **Issue:** `_allowed_msgpack_modules()` scanned only `core.schema`. A blocked Pydantic type
  is silently deserialised as a plain dict, so a paused/resumed run would lose
  `EmergencyVerdict` (EMERG-05 provenance).
- **Fix:** the allowlist now derives from `(core.schema, core.emergency)`.
- **Files modified:** `src/triagedesk/graph/build.py`
- **Commit:** `955da91`

**2. [Rule 1 - Bug] The SATS DRY guard flagged the CONTEXT-fixed channel key**
- **Found during:** full-suite run after Task 4
- **Issue:** the state/payload key `"emergency"` is also a loaded discriminator category, so
  `test_no_duplicated_sats` rejected it as a duplicated SATS string.
- **Fix:** extended the guard's existing, documented scope boundary with ONE exact
  `STRUCTURAL_CHANNEL_KEYS` exemption (a structural channel key is not a scoring value) and a
  test pinning the set to that single key. The guard was not weakened generally.
- **Files modified:** `tests/test_no_duplicated_sats.py`
- **Commit:** `955da91`

## Known Stubs

None.

## Threat Flags

None — no new endpoint, auth path, file-access pattern or trust boundary. The pre-check reads
the pure scorer and writes two state channels.

## Self-Check: PASSED

- `src/triagedesk/core/emergency.py` exists; `tests/test_emergency.py` exists.
- Commit `955da91` is an ancestor of HEAD.
- `core/scorer.py`, `core/citations.py` and the `@audited` interceptor are untouched.
