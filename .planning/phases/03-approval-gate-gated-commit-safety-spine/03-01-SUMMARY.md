---
phase: 03-approval-gate-gated-commit-safety-spine
plan: 01
subsystem: agent-orchestration
tags: [langgraph, interrupt, approval-gate, checkpointer, sqlite, ollama, pydantic]

# Dependency graph
requires:
  - phase: 02-deterministic-scorer-owned-tools
    provides: "core.scorer.score_priority (pure), core.matcher.match_discriminators, the owned MCP tools (normalize_case, match_discriminators, score_priority, commit_priority stub), and the ONE schema module"
  - phase: 01-foundation-local-model-mcp-spike
    provides: "llm.client.extract (local Ollama), mcp.adapter.load_tools (the DIP seam), core.hashing.hash_value"
provides:
  - "graph/ package: TriageState, thin nodes over an injected tool mapping, and build_graph/run_case"
  - "The approval gate as a LangGraph interrupt() with NO side effect before it (D-04)"
  - "The gated commit node: an ApprovalToken built from the resumed value, refused without a named clinician (D-05)"
  - "checkpointed_graph(tools, db_path): durable AsyncSqliteSaver over checkpoints.db, separate from triage.db (D-09)"
  - "HandoverCard contract (no dx/rx field) and ApprovalToken.final_colour in core/schema.py"
affects: [03-approval-gate-gated-commit-safety-spine, 04-evaluation, 05-demo]

# Actuals (#2632) — pairs with the plan's estimate (62000 tokens, low confidence).
# Same estimateTokens scale (chars/4 over the realized diff), never a harness count.
actuals:
  tokens: 9066
  tasks: 3
  commits: 3
  plan_head_before: 16df47b3b70dfd62af05ef24423fa2df29d703e8
  plan_head_after: f7ef1a1c9d64c8d51025329c5931ce5f2fff4a7b

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injected tool mapping (name -> async callable) as the graph's only outside-world dependency (SOLID: D)"
    - "Interrupt-before-write: a side-effect-free gate node; the write/audit belongs in the next node (D-04)"
    - "Untrusted resume value validated into an ApprovalToken before any queue-affecting call (GATE-02)"

key-files:
  created:
    - src/triagedesk/graph/__init__.py
    - src/triagedesk/graph/state.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - scripts/spike_graph.py
    - tests/test_graph_tracer.py
  modified:
    - src/triagedesk/core/schema.py
    - tests/test_mcp_tools.py

key-decisions:
  - "The graph depends on an injected tool mapping (name -> async callable), never on MCPAdapter; build.py is the only composition point (D-13, SOLID: D)"
  - "approval_gate builds the evidence payload then calls interrupt() with no side effect before it, so a resumed node re-runs cleanly (D-04, T-03-02)"
  - "commit builds an ApprovalToken from the resumed value verbatim; an approve decision defaults final_colour to the scored colour, an edit must carry its own; malformed/absent tokens are refused by the gated tool (D-05, T-03-01)"
  - "ApprovalToken.final_colour is validated against the colour set read from data/sats_tews.yaml, never a hard-coded literal (CONVENTIONS §1)"
  - "checkpoints.db (runtime state) is deliberately a different file from triage.db (clinical record + audit) (D-09)"
  - "The verify retry edge is bounded (attempt < 2); an exhausted retry stops at END, never reaching the gate or commit (T-03-05)"
  - "The SQLite saver gets an explicit allowlist of the state schema types (derived from core.schema), avoiding the future strict-msgpack block without a blanket allow"

patterns-established:
  - "Side-effect-free gate node: a resumed interrupt node re-runs from its top, so no non-idempotent action may precede interrupt()"
  - "parse_tool_result: the ONE decoder for MCP tool output (typed model | content blocks | mapping | JSON text)"
  - "The graph reaches only the local Ollama client; a guard test AST-scans graph/ for any non-local model provider"

requirements-completed: [ORCH-01, ORCH-02, GATE-01, GATE-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "A raw triage note runs the full graph on the local model and pauses at the gate with a sourced, cited priority"
    requirement: "ORCH-01"
    verification:
      - kind: e2e
        ref: "uv run python scripts/spike_graph.py"
        status: pass
      - kind: unit
        ref: "tests/test_graph_tracer.py#test_run_reaches_the_gate_without_committing"
        status: pass
    human_judgment: false
  - id: D2
    description: "No queue-affecting write happens before the interrupt (the gate node is side-effect-free)"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "tests/test_graph_tracer.py#test_run_reaches_the_gate_without_committing"
        status: pass
    human_judgment: false
  - id: D3
    description: "Resuming without a valid approval token leaves the commit refused and writes nothing"
    requirement: "GATE-02"
    verification:
      - kind: unit
        ref: "tests/test_graph_tracer.py#test_unapproved_resume_is_refused_and_writes_nothing"
        status: pass
      - kind: e2e
        ref: "uv run python scripts/spike_graph.py (dismiss resume -> refused)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The whole path runs on the local open-weights model; no frontier provider is reachable from graph/"
    requirement: "ORCH-02"
    verification:
      - kind: unit
        ref: "tests/test_graph_tracer.py#test_graph_imports_no_non_local_model_provider"
        status: pass
    human_judgment: false
  - id: D5
    description: "A paused triage survives a process restart via the SQLite checkpointer in checkpoints.db, separate from triage.db"
    verification:
      - kind: unit
        ref: "tests/test_graph_tracer.py#test_checkpoint_survives_a_fresh_saver"
        status: pass
    human_judgment: false

# Metrics
duration: 11min
completed: 2026-10-09
status: complete
---

# Phase 3 Plan 1: End-to-end Tracer — Raw Note → Sourced Priority → Gate Interrupt Summary

**The full triage graph runs a raw note through the local model to a cited SATS priority, pauses at a LangGraph `interrupt()` for a named clinician, and physically refuses to commit when resumed without a valid approval token.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-10-09T15:56:45Z
- **Completed:** 2026-10-09T16:08:20Z
- **Tasks:** 3
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments
- The `graph/` package: one typed `TriageState`, thin single-purpose nodes over an **injected tool mapping**, and a builder wiring `ingest → normalize → retrieve → score → verify → approval_gate → commit → handover` with a bounded `verify` retry.
- The **approval gate is the protected headline**: `approval_gate` performs no side effect before `interrupt()`, and `commit` reaches the gated `commit_priority` tool only via the resumed value — an absent/malformed approval is refused and nothing is written (D-04, D-05).
- A real local-model spike (`scripts/spike_graph.py`) proved the end-to-end path: the raw note scored **ORANGE with 3 citations**, the graph paused at the gate, and a `dismiss` resume (no named approver) was **refused**.
- Durable persistence: `checkpointed_graph` backs the graph with `AsyncSqliteSaver` over `checkpoints.db` — deliberately separate from the domain store `triage.db` (D-09) — and a paused thread survives a fresh saver.
- `HandoverCard` (no diagnosis/assessment/impression/plan/prescription field) and `ApprovalToken.final_colour` added to the ONE schema module.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end raw note → sourced priority → gate interrupt** - `c5220f8` (feat)
2. **Task 2: Persist the paused graph in a separate checkpointer file** - `fec1b08` (feat)
3. **Task 3: Tracer proof suite** - `f7ef1a1` (test)

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified
- `src/triagedesk/graph/state.py` - The ONE typed `TriageState` (imports only `core.schema`)
- `src/triagedesk/graph/nodes.py` - Thin nodes over an injected `tools` mapping; the side-effect-free gate; the gated commit; the deterministic handover
- `src/triagedesk/graph/build.py` - `build_graph`, `run_case`, `checkpointed_graph`, the bounded verify route, and the two named DB paths
- `src/triagedesk/graph/__init__.py` - Public exports for the graph package
- `src/triagedesk/core/schema.py` - `ApprovalToken.final_colour` (substrate-validated) + `HandoverCard`
- `scripts/spike_graph.py` - The real local-model end-to-end tracer (pause + refusal)
- `tests/test_graph_tracer.py` - The four offline proof behaviours + checkpoint durability + bounded retry
- `tests/test_mcp_tools.py` - Added `final_colour` to the well-formed-token case (schema change)

## Decisions Made
- The graph depends on a `tools` mapping (name → async callable), never on `MCPAdapter`; `build.py` is the only composition point (D-13, SOLID: D).
- `approval_gate` builds a pure evidence payload then calls `interrupt()`; the write + audit belong in the next node (D-04).
- `commit` builds an `ApprovalToken` from the resumed value verbatim (approve defaults `final_colour` to the scored colour; edit must carry its own); the gated tool refuses anything malformed (D-05).
- `final_colour` is validated against the colours read from `data/sats_tews.yaml`, never a literal (CONVENTIONS §1).
- The verify retry is bounded (`attempt < 2`); an exhausted retry stops at `END` — fail-closed, never reaching the gate.
- The SQLite saver's serializer gets an explicit allowlist of the state schema types (derived from `core.schema`), avoiding the future strict-msgpack block without a blanket allow.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated the pre-existing `commit_priority` token test for the new `final_colour` field**
- **Found during:** Task 1 (schema change)
- **Issue:** The plan mandates extending `ApprovalToken` with a required `final_colour: str = Field(min_length=1)`. The existing `tests/test_mcp_tools.py::test_commit_priority_accepts_a_well_formed_token_without_committing` supplied a token without `final_colour`, so the token became malformed and the test failed — breaking the "full suite stays green" verification.
- **Fix:** Added `"final_colour": "RED"` to that well-formed token (its intent — a valid token is accepted but never commits — is unchanged).
- **Files modified:** tests/test_mcp_tools.py
- **Verification:** `uv run pytest -q` → 125 passed.
- **Committed in:** `c5220f8` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Registered the state schema types with the checkpointer serializer**
- **Found during:** Task 2 (durable checkpointer)
- **Issue:** LangGraph's default serde warned that custom state types (`CaseInput`, `PriorityResult`, `CommitResult`, `HandoverCard`, …) were "unregistered" and "will be blocked in a future version" — a latent break of the pause-and-resume guarantee.
- **Fix:** `checkpointed_graph` sets an explicit `JsonPlusSerializer(allowed_msgpack_modules=...)` allowlist derived from `core.schema` (never a blanket `True`).
- **Files modified:** src/triagedesk/graph/build.py
- **Verification:** `uv run python scripts/spike_graph.py` — the msgpack warning is gone; the spike still passes.
- **Committed in:** `fec1b08` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both are consequences of the plan's own schema/checkpointer requirements. No scope creep.

## Issues Encountered
- The plan's Task 2 verify (`pytest ... -k checkpoint`) references the proof suite authored in Task 3. The checkpoint test was authored alongside the suite and used to verify Task 2 against the working tree; its commit lands with Task 3, consistent with the plan's file ownership.

## Known Stubs
- `src/triagedesk/graph/nodes.py` (`handover`): `HandoverCard.second_look` is always `None` in the tracer — the serial-vitals recheck node is wired in a later Phase-3 plan (D-07). It does not affect this plan's goal (the gate); it is recorded in `.planning/WINDOWS.md`.
- `src/triagedesk/mcp/server.py`: `commit_priority` remains the Phase-2 gated stub (refuses without a token, writes nothing). The real idempotent queue write is a later Phase-3 plan — the existing WINDOWS.md entry stays open by design.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: deserialization | src/triagedesk/graph/build.py | The checkpointer now deserialises custom state types; mitigated by an explicit per-type allowlist (never a blanket allow), so a tampered checkpoint cannot instantiate an arbitrary type. |

## User Setup Required
None - no external service configuration required. (The local Ollama server with `qwen2.5:1.5b` was already running and pulled.)

## Next Phase Readiness
- The graph shape, the interrupt-before-write ordering, and the checkpointer choice are now fixed and proven on one real path — later Phase-3 plans can expand (idempotent commit, audit interceptor, recheck/recovery edges) without re-opening the architecture.
- `build_graph` takes an injected tool mapping, so the borrowed-SQLite wiring and the real commit slot in behind the same interface (D-13).
- Blocker carried forward: the real idempotent commit and the borrowed SQLite store are not yet wired (by design — later plans).

---
*Phase: 03-approval-gate-gated-commit-safety-spine*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 7 created/modified artifacts exist on disk (graph package, spike, proof suite, SUMMARY).
- All 3 task commits are ancestors of HEAD: `c5220f8`, `fec1b08`, `f7ef1a1`.
