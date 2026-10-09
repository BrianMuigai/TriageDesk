---
phase: 03-approval-gate-gated-commit-safety-spine
plan: 04
subsystem: agent-orchestration
tags: [langgraph, recovery, abstention, recheck, safety, pydantic, dry]

# Dependency graph
requires:
  - phase: 03-approval-gate-gated-commit-safety-spine
    provides: "graph/ (TriageState, thin nodes over an injected tool mapping, build_graph/run_case), the approval gate interrupt, the gated commit, the durable checkpointer, the owned raise_recheck_flag tool and core.recheck.compare_vitals"
  - phase: 02-deterministic-scorer-owned-tools
    provides: "core.scorer.score_priority (missing_vitals + out_of_scope signals), core.recheck.compare_vitals (RecheckFlag, no colour)"
provides:
  - "RecoveryRequest + Escalation typed terminals; route_after_score branches a missing-vital case to recovery and an out-of-scope case to escalation — neither has an edge to commit (ORCH-05, D-03)"
  - "Bounded extraction retry (_EXTRACTION_MAX_ATTEMPTS = 2) then a deterministic, model-free fallback (ORCH-04)"
  - "A non-mutating recheck node between verify and approval_gate: a visible before/after second-look flag, queue position unchanged (GATE-04, D-07, M-4)"
  - "run_case(raw_note, tools, config, previous_case=None): the serial-vitals input path"
affects: [04-evaluation, 05-demo]

# Actuals (#2632) — pairs with the plan's estimate (56000 tokens, low confidence).
# Same estimateTokens scale (chars/4 over the realized diff), never a harness count.
actuals:
  tokens: 11216
  tasks: 3
  commits: 3
  plan_head_before: ce3def9a19b410289bcc02bfa8ab7ff109cf6089
  plan_head_after: 186ba9d0f0d15245af53fc00e1aa3702a22ef0a8

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-closed safe terminals: a missing/out-of-scope case stops at a typed terminal with no colour and no edge to commit"
    - "Bounded recovery: one retry, then a deterministic model-free fallback over already-parsed fields"
    - "Non-mutating second look: the recheck writes only a flag, never a colour or a queue reorder"

key-files:
  created:
    - tests/test_graph_recovery.py
    - tests/test_graph_recheck.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/graph/state.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - src/triagedesk/graph/__init__.py
    - tests/conftest.py
    - tests/test_graph_tracer.py

key-decisions:
  - "The recovery/abstention branch is placed after score, on the PriorityResult signals, so the graph never duplicates the scorer's scope/missing logic (DRY) and stays bound to the tool interface (SOLID: D)"
  - "The extraction retry is an in-node loop bounded by the named constant _EXTRACTION_MAX_ATTEMPTS; the state attempt field remains the verify retry budget (no cross-coupling)"
  - "The deterministic fallback reads already-parsed structured fields (a caller-supplied case, or a structured JSON note) and otherwise routes to the escalation terminal — never fabricating a value (ORCH-04)"
  - "RecoveryRequest/Escalation carry no colour; the recovery/escalation terminals have no edge to commit (ORCH-05, D-03)"
  - "The recheck node stores RecheckFlag in state['second_look'] and HandoverCard.second_look only; it never touches the colour, the priority or the queue (D-07, M-4)"
  - "One shared offline graph tool fake lives in tests/conftest.py so the three graph proof suites define it once (DRY)"

patterns-established:
  - "route_after_score: a pure read of the scored PriorityResult that fails closed to a typed terminal"
  - "Deterministic, model-free fallback: the model may only structure; a failed extraction recovers from typed fields or abstains"

requirements-completed: [ORCH-04, ORCH-05, GATE-04]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Invalid extraction retries once, then falls back deterministically — never emitting an uncited or partial priority"
    requirement: "ORCH-04"
    verification:
      - kind: unit
        ref: "tests/test_graph_recovery.py#test_bounded_extraction_retries_exactly_once"
        status: pass
      - kind: unit
        ref: "tests/test_graph_recovery.py#test_second_invalid_result_uses_the_fallback"
        status: pass
      - kind: unit
        ref: "tests/test_graph_recovery.py#test_exhausted_retry_without_a_fallback_escalates"
        status: pass
    human_judgment: false
  - id: D2
    description: "A missing vital routes to a re-measure terminal and an out-of-scope case to an abstention terminal; neither guesses and neither commits"
    requirement: "ORCH-05"
    verification:
      - kind: unit
        ref: "tests/test_graph_recovery.py#test_missing_vital_routes_to_the_recovery_terminal"
        status: pass
      - kind: unit
        ref: "tests/test_graph_recovery.py#test_out_of_scope_case_routes_to_the_abstention_terminal"
        status: pass
      - kind: unit
        ref: "tests/test_graph_recovery.py#test_neither_terminal_calls_commit_priority"
        status: pass
    human_judgment: false
  - id: D3
    description: "A deterioration raises a visible before/after second-look flag with the queue position unchanged; no colour and no reorder"
    requirement: "GATE-04"
    verification:
      - kind: unit
        ref: "tests/test_graph_recheck.py#test_deterioration_sets_the_flag_in_state_and_handover_card"
        status: pass
      - kind: unit
        ref: "tests/test_graph_recheck.py#test_recheck_does_not_change_the_queue_position"
        status: pass
      - kind: unit
        ref: "tests/test_graph_recheck.py#test_recheck_never_commits_and_never_sets_a_colour"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-10-09
status: complete
---

# Phase 3 Plan 4: Safe Branches — Recovery, Abstention & Deterioration Re-check Summary

**The graph's safe branches are complete: a failing extraction recovers within one bounded retry, a missing-vital or out-of-scope case stops at a typed terminal that never guesses or commits, and a deterioration raises a visible before/after second look with the queue position unchanged.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-10-09T16:34:48Z
- **Completed:** 2026-10-09T16:50:25Z
- **Tasks:** 3
- **Files modified:** 9 (2 created, 7 modified)

## Accomplishments

- **Bounded recovery (ORCH-04):** `normalize` retries a raised or schema-invalid extraction exactly once (`_EXTRACTION_MAX_ATTEMPTS = 2`), then takes the deterministic, model-free path — the caller's already-parsed structured fields (a state `case`, or a structured JSON note), else the escalation terminal. No path fabricates a value or emits an uncited priority (D-02/D-03).
- **Safe terminals (ORCH-05):** `RecoveryRequest` and `Escalation` typed terminals in the ONE schema module. `route_after_score` reads the scored `PriorityResult`: out-of-scope → `escalate`, a missing scored vital → `request_missing_info`, else `verify`. Neither terminal has an edge to `commit`, so a non-scored case is never written.
- **Non-mutating second look (GATE-04, M-4):** a `recheck` node between `verify` and `approval_gate` calls the owned `raise_recheck_flag` tool and stores the `RecheckFlag` in `state["second_look"]`, the gate payload and `HandoverCard.second_look`. The flag carries before/after values and no colour; the node never re-scores, reorders or writes.
- **The serial-vitals input path:** `run_case(raw_note, tools, config, previous_case=None)` seeds `previous_case` into the initial state so a second look has a defined entry point.
- **DRY:** one shared offline graph tool fake in `tests/conftest.py` now backs all three graph proof suites (the tracer was refactored onto it).

## Task Commits

Each task was committed atomically:

1. **Task 1: Missing-vital recovery and out-of-scope abstention edges** — `94ddfb6` (feat)
2. **Task 2: Bounded extraction retry, then deterministic fallback** — `39a01dc` (feat)
3. **Task 3: Deterioration re-check — visible second look, queue unchanged** — `186ba9d` (feat)

## Files Created/Modified

- `src/triagedesk/core/schema.py` — `RecoveryRequest` + `Escalation` typed terminals (no colour field).
- `src/triagedesk/graph/state.py` — `recovery`, `escalation`, `previous_case`, `second_look` channels.
- `src/triagedesk/graph/nodes.py` — bounded `normalize` retry + `_structured_case` fallback; `request_missing_info`, `escalate`, `recheck` nodes; `handover`/`approval_gate` carry the second look.
- `src/triagedesk/graph/build.py` — `route_after_normalize`, `route_after_score`, the recheck edge, the terminal edges, `run_case(..., previous_case=...)`.
- `src/triagedesk/graph/__init__.py` — export the new route functions.
- `tests/conftest.py` — the ONE shared offline graph tool fake (`build_graph_tools`, `COMPLETE_CASE`).
- `tests/test_graph_recovery.py` — the recovery/abstention + bounded-retry proofs.
- `tests/test_graph_recheck.py` — the second-look proofs (flag, unchanged queue, no commit/colour).
- `tests/test_graph_tracer.py` — node-set superset assertion (incl. recheck/request_missing_info/escalate), the `verify → recheck` route assertion, and refactor onto the shared fake.

## Decisions Made

- **Branch after `score`, not before.** The plan's prose mentions routing "after normalize"; the deterministic signals (`PriorityResult.missing_vitals` / `.out_of_scope`) live on the scored result. Routing pre-score would either duplicate the scorer's scope/missing logic (a DRY violation) or import `core` into the graph (a SOLID: D violation). The terminals therefore branch after `score`; `route_after_normalize` handles only the unparseable-extraction escalation. See Deviations.
- **Extraction retry is an in-node loop** bounded by the named constant, so the state `attempt` field stays the verify retry budget and the two bounds never interfere.
- **The fallback is model-free** (D-02): it reads typed structured fields only.
- **The recheck flag has no colour** and the node writes only `second_look` — the second look can never become a second classification (M-4).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Extracted the shared offline graph tool fake into `tests/conftest.py`**
- **Found during:** Task 1
- **Issue:** The plan lists three graph proof suites (`test_graph_tracer`, `test_graph_recovery`, `test_graph_recheck`), each needing the same injected `name -> async callable` fake. Copying it per module would triple a non-trivial fake and violate the iron-clad DRY rule (and the established conftest precedent: "one fake, not one per test module").
- **Fix:** Added `COMPLETE_CASE` and `build_graph_tools(...)` to `tests/conftest.py`; all three suites import them (the tracer's private `_fake_tools` was removed).
- **Files modified:** `tests/conftest.py`, `tests/test_graph_tracer.py`, `tests/test_graph_recovery.py`, `tests/test_graph_recheck.py`
- **Verification:** `uv run pytest -q` → 156 passed.
- **Committed in:** `94ddfb6` (Task 1), `186ba9d` (Task 3, tracer refactor)

### Design adaptations (documented, not scope creep)

**2. Recovery/abstention terminals branch after `score`.**
- **Why:** `PriorityResult.missing_vitals` and `.out_of_scope` are THE deterministic signals (the plan's own prior-context note). Branching before `score` would require re-deriving the scorer's out-of-scope/missing logic outside the ONE authority (DRY) or reaching `core.scorer` from the graph (SOLID: D — the graph depends on the injected tool interface). `route_after_normalize` still routes an unparseable case (a Task-2 concern) straight to `escalate`.
- **Impact:** Behaviour and the plan's three Task-1 `<behavior>` tests are satisfied; the graph never falls through to `commit` on a missing/out-of-scope case.

---

**Total deviations:** 1 auto-fixed (missing critical / DRY) + 1 documented design adaptation. No scope creep.

## Issues Encountered

- The three tasks' work is tightly coupled (all in the recovery/recheck region of `nodes.py` and `build.py`, and Tasks 1–2 share `test_graph_recovery.py`). Commits were split back into three atomic task commits after an initial combined commit, so each task maps to exactly one commit.

## Known Stubs

None. The 03-01 stub "`handover.second_look` is always `None` in the tracer" is now resolved — the recheck node wires the flag through to the card (WINDOWS entry #2 marked fixed).

## Threat Flags

None — the plan's threat register (T-03-16…T-03-20) covers the new surface; no unlisted surface was introduced.

## Threat Model Coverage

| Threat ID | Disposition | Mitigation shipped |
|-----------|-------------|--------------------|
| T-03-16 (Tampering — retry/fallback) | mitigate | Bounded retry once, then a deterministic model-free fallback; no path emits an uncited/partial priority. |
| T-03-17 (Spoofing — recovery edge) | mitigate | A missing vital routes to a re-measure terminal; the graph never imputes a value. |
| T-03-18 (Elevation — out-of-scope edge) | mitigate | Out-of-scope input routes to abstention/escalation and never receives an adult colour. |
| T-03-19 (Tampering — recheck node) | mitigate | The recheck surfaces a before/after flag with no colour and no reorder; the queue position is asserted unchanged. |
| T-03-20 (DoS — recovery terminals) | accept | A safe terminal ends the run; the nurse re-runs after re-measuring. |
| T-03-SC (Tampering — installs) | mitigate | No package install occurred in this plan. |

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The graph's full safety spine is now wired: `ingest → normalize → retrieve → score → (recovery | abstention | verify → recheck → approval_gate → commit → handover) → END`, with the gate unchanged and no terminal reaching `commit`.
- Ready for Phase 4 (evaluation): the recovery, abstention and recheck branches are proven offline and can be exercised end-to-end by the eval harness.

---

*Phase: 03-approval-gate-gated-commit-safety-spine*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All created/modified artifacts exist on disk (two proof suites, schema/state/nodes/build changes, SUMMARY).
- All 3 task commits are ancestors of HEAD: `94ddfb6`, `39a01dc`, `186ba9d`.
