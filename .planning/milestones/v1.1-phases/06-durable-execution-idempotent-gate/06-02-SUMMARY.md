---
phase: 06-durable-execution-idempotent-gate
plan: 02
subsystem: orchestration
tags: [langgraph, sqlite, checkpointing, interrupt, idempotency, cli]

# Dependency graph
requires:
  - phase: 06-durable-execution-idempotent-gate
    provides: "the immutable-CaseInput queue key + supersede-in-place commit_to_queue (plan 06-01)"
  - phase: 03-mcp-gated-commit-and-audit
    provides: "checkpointed_graph, the approval_gate interrupt, the @audited interceptor, the injectable store seam"
provides:
  - "src/triagedesk/durable.py — the ONE durable pause/resume helper (derive_thread_id, invoke_graph, run_to_gate, resume_paused, resume_thread, approval_decision, PausedRun, DurableError)"
  - "triagedesk resume subcommand (--thread-id/--decision/--approver/--role/--colour/--db)"
  - "demo --durable / --db — one beat to the approval gate, prints thread_id + the exact resume command, no auto-resume"
  - "restart + per-tool exactly-once proof over two checkpointed_graph instances"
affects: [07-replay-read-only, docs-demo]

# Actuals (#2632) — chars/4 over the realized tracked diff, same scale as the plan estimate.
actuals:
  tokens: 9751
  tasks: 3
  commits: 4
commits: 4
plan_head_before: 08cd60ea04de05873f6b8515eeb4934748b12d63
plan_head_after: a8781814fb3b45ac049a36a62a7d4202066cce87

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One shared invoke→interrupt→resume primitive (durable.invoke_graph) so the eval runner and the demo cannot drift"
    - "Lazy import to break the evals <-> durable import cycle (matches the existing store/adapter lazy-import precedent)"
    - "Content-addressed durable thread_id reusing the ONE case_id_for derivation (stripped note)"
    - "A durable path that reuses the ONE existing store-resolution seam (mcp.server._resolve_store) — no second resolver"

key-files:
  created:
    - src/triagedesk/durable.py
    - tests/test_graph_durable.py
    - tests/test_durable_cli.py
  modified:
    - src/triagedesk/demo/run.py
    - src/triagedesk/evals/runner.py
    - src/triagedesk/cli.py
    - docs/DEMO.md

key-decisions:
  - "The durable lifecycle lives in ONE helper (durable.py) so `demo --durable` and `resume` cannot drift (D6-08…D6-11)."
  - "`resume` builds its tools in-process from a placeholder CaseSpec and injects NO store of its own — it reuses `mcp.server._resolve_store`, so there is exactly one store-resolution path."
  - "The absent-thread check runs BEFORE the graph is invoked, so `resume --thread-id <absent>` touches no store and launches no borrowed `npx mcp-sqlite` subprocess."
  - "`--durable` runs exactly ONE beat per invocation (content-addressed thread_id would collide on two beats sharing a case) and never auto-resumes (a single in-process pause proves nothing)."
  - "`evals/runner._run_once` keeps its per-run thread_id and shares only the invoke primitive — the eval's deliberate per-run isolation must not adopt the durable id (Pitfall 3)."
  - "`--approver`/`--role` are required only for approve/edit (enforced in durable.approval_decision), so `resume --decision dismiss` demonstrates the gate refusal without a fabricated identity (Open Q4)."

patterns-established:
  - "One invoke primitive, per-caller thread-id policy (SOLID: S) — the eval runner and demo share the mechanism but own their identity rules."
  - "Lazy import inside a function to break a package import cycle, mirroring graph.build.load_graph_tools / store.default_store."

requirements-completed: [AGENT-01]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "The durable lifecycle lives in ONE helper: derive_thread_id (the ONE content derivation), invoke_graph, run_to_gate, resume_paused, resume_thread, approval_decision, PausedRun and DurableError are importable from triagedesk.durable."
    requirement: AGENT-01
    verification:
      - kind: unit
        ref: "python -c \"from triagedesk.durable import derive_thread_id, run_to_gate, resume_paused, resume_thread, invoke_graph, approval_decision, DurableError, PausedRun\""
        status: pass
      - kind: unit
        ref: "tests/test_graph_durable.py#test_thread_id_is_the_stripped_note_hash"
        status: pass
    human_judgment: false
  - id: D2
    description: "A case paused in one process resumes to a committed handover in a fresh process over the same checkpoint file, with one queue row and one audit record per owned tool (no pre-gate replay)."
    requirement: AGENT-01
    verification:
      - kind: integration
        ref: "tests/test_graph_durable.py#test_restart_resumes_to_one_row_and_one_commit_audit"
        status: pass
    human_judgment: false
  - id: D3
    description: "An edit resumed on the durable path supersedes the row in place: one row, edited colour, unchanged position, colour-independent content_hash."
    requirement: AGENT-01
    verification:
      - kind: integration
        ref: "tests/test_graph_durable.py#test_edit_resume_supersedes_on_the_durable_path"
        status: pass
    human_judgment: false
  - id: D4
    description: "triagedesk resume parses and dispatches through the shared helper, exits non-zero naming an absent thread, requires --approver for approve, and never touches a store on the absent path."
    requirement: AGENT-01
    verification:
      - kind: unit
        ref: "tests/test_durable_cli.py#test_resume_absent_thread_never_touches_a_store"
        status: pass
      - kind: unit
        ref: "tests/test_durable_cli.py#test_resume_approve_without_approver_names_the_flag"
        status: pass
      - kind: other
        ref: "uv run triagedesk resume --thread-id absent --decision dismiss --db /tmp/opencode/none.db (exit=1, names thread + db)"
        status: pass
    human_judgment: false
  - id: D5
    description: "demo --durable runs one beat to the gate, prints exactly one thread_id line and the exact resume command, and does not auto-resume (no outcome block, no queue row)."
    requirement: AGENT-01
    verification:
      - kind: unit
        ref: "tests/test_durable_cli.py#test_durable_demo_pauses_and_prints_one_thread_id_line"
        status: pass
      - kind: other
        ref: "uv run triagedesk demo --durable --beat escalation --db /tmp/opencode/durable_demo.db (one thread_id= line, one resume line)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The bare uv run triagedesk demo is unchanged: the five-beat offline storyboard still runs hermetically (no model, no borrowed subprocess)."
    requirement: AGENT-01
    verification:
      - kind: integration
        ref: "tests/test_demo.py (five beats, no queue row on the refusal beat)"
        status: pass
      - kind: other
        ref: "uv run triagedesk demo (exit=0, no thread_id lines, no borrowed subprocess)"
        status: pass
    human_judgment: false
  - id: D7
    description: "docs/DEMO.md documents the two-command durability story (pause → resume), the gate refusal on a pending thread, the borrowed-store caveat and the checkpoints.db reset — with the one-command path and honesty clauses intact."
    requirement: AGENT-01
    verification:
      - kind: unit
        ref: "tests/test_demo_runbook.py (runbook matches the shipped CLI; beats documented)"
        status: pass
    human_judgment: false

# Metrics
duration: 16min
completed: 2026-10-12
status: complete
---

# Phase 6 Plan 02: Durable Execution & Idempotent Gate Summary

**The durable `checkpointed_graph` is now the real path: `demo --durable` runs one case to the approval gate over `checkpoints.db`, prints the content-derived `thread_id` and the exact `resume` command, and `triagedesk resume` reopens the same file in a fresh process and drives the gate to a committed handover — one shared pause/resume helper, no auto-resume.**

## Performance

- **Duration:** 16 min (commit span 13:36:55 → 13:51:47 +0300)
- **Started:** 2026-10-12T10:35:59Z
- **Completed:** 2026-10-12T10:52:20Z
- **Tasks:** 3
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- **ROADMAP Phase 6 criterion 1 is TRUE:** a case paused at the gate resumes to a committed handover
  after a full process restart, on a `thread_id` equal to `case_id_for(note.strip())` from any entry
  point (`tests/test_graph_durable.py`).
- **Criterion 3 is TRUE:** the restart produces exactly one queue row and one audit record per owned
  tool (`normalize_case`, `match_discriminators`, `score_priority`, `commit_priority` all exactly 1) —
  no pre-gate tool is replayed, and no de-dup guard was added to the interceptor.
- **Criterion 4 is TRUE:** `uv run triagedesk demo` still runs its five-beat storyboard offline and
  hermetically; its `--durable` mode executes through the checkpointed graph and documents the `resume`
  subcommand.
- **All pause/resume plumbing is in ONE place** (`src/triagedesk/durable.py`) so `demo --durable` and
  `resume` cannot drift; the eval runner and the demo now share one `invoke_graph` primitive.
- **`resume` adds no second store resolver:** it delegates to the existing `mcp.server._resolve_store`
  seam, and its pending-gate check runs before the graph is invoked — so an absent thread touches no
  store and launches no borrowed `npx mcp-sqlite` subprocess (proven by test).
- **D-18 holds:** `core/scorer.py`, `core/citations.py` and the `@audited` interceptor body are
  untouched, and the graph topology is unchanged (no new nodes). The whole suite is green (248 passed).

## Task Commits

Each task was committed atomically (Task 1 is a `tdd="true"` tracer → RED then GREEN):

1. **Task 1 (RED): failing durable restart + exactly-once proof** - `6208518` (test)
2. **Task 1 (GREEN): durable.py + demo/evals wiring** - `e548c19` (feat)
3. **Task 2: resume subcommand + demo --durable flag** - `9c87be6` (feat)
4. **Task 3: durable edit-supersede proof + runbook** - `a878181` (test)

**Plan metadata:** skipped (`commit_docs: false`).

_Note: TDD task 1 produced a RED (`test`) then GREEN (`feat`) commit; no REFACTOR commit was needed._

## Files Created/Modified

- `src/triagedesk/durable.py` - **NEW**: `DurableError`, `derive_thread_id`, `PausedRun`, `invoke_graph`,
  `run_to_gate`, `resume_paused`, `resume_thread`, `approval_decision`, `_RESUME_PLACEHOLDER`
- `src/triagedesk/demo/run.py` - `_run_beat`/`_named_approval` delegate to `durable`; added the
  `durable`/`db_path` keywords and `_run_durable` (one beat → gate → print resume command → exit)
- `src/triagedesk/evals/runner.py` - `_run_once` delegates the invoke→interrupt→resume step to
  `durable.invoke_graph` (lazy import to break the `evals`↔`durable` cycle), keeping its per-run id
- `src/triagedesk/cli.py` - demo `--durable`/`--db`; a `resume` subcommand
  (`--thread-id`/`--decision`/`--approver`/`--role`/`--colour`/`--db`) dispatching through `durable`
- `tests/test_graph_durable.py` - **NEW**: restart + per-tool exactly-once, thread_id derivability,
  no-pending-gate `DurableError`, durable edit-supersede
- `tests/test_durable_cli.py` - **NEW**: `resume` parse + dispatch, absent-thread store isolation,
  missing-`--approver`, durable-demo output
- `docs/DEMO.md` - the "Durable mode (two-command durability story)" section

## Decisions Made

- **One helper, per-caller identity policy:** the shared `invoke_graph` primitive is used by both the
  eval runner (per-run id, isolation) and the demo (positional id); only the *durable* entry points
  adopt the content-derived id. Chosen to satisfy SOLID: S without adopting Pitfall 3.
- **`resume` reuses the ONE store seam:** `resume_thread` builds its tools in-process from a placeholder
  `CaseSpec` and injects no store — the gate's commit and the audit interceptor resolve the store
  through `mcp.server._resolve_store`, so there is exactly one resolution path.
- **Placeholder `expected` uses declared harness vocabulary:** `_RESUME_PLACEHOLDER.expected =
  TERMINAL_OUTCOMES[0]` (not a SATS colour literal), because the DRY guard
  (`tests/test_no_duplicated_sats.py`) forbids SATS colour strings under `src/` — the placeholder's
  expectation is never read, so a terminal token is the honest choice.
- **Lazy import to break a real cycle:** `durable` imports `evals.case` (for `CaseSpec`) at module
  level, which triggers `evals/__init__` → `evals.runner`; `evals.runner` therefore imports
  `durable.invoke_graph` lazily inside `_run_once`. A top-level import there is a genuine circular
  import (verified), and the lazy form matches the existing `graph.build.load_graph_tools` precedent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Avoided a SATS colour literal in the resume placeholder**
- **Found during:** Task 1 (`uv run pytest -q`)
- **Issue:** `_RESUME_PLACEHOLDER.expected = "GREEN"` tripped the DRY guard
  `tests/test_no_duplicated_sats.py` (SATS scoring values must live only in `data/*.yaml`).
- **Fix:** use `TERMINAL_OUTCOMES[0]` (declared harness vocabulary, never a SATS value); the
  placeholder's expectation is never evaluated.
- **Files modified:** `src/triagedesk/durable.py`
- **Verification:** `uv run pytest -q` → 242 passed (then 248).
- **Committed in:** `e548c19` (Task 1 GREEN commit)

**2. [Rule 3 - Blocking] Broke the `evals` ↔ `durable` import cycle**
- **Found during:** Task 1 (first `pytest` collection after adding the import)
- **Issue:** a top-level `from triagedesk.durable import invoke_graph` in `evals/runner.py` cycles
  (`durable` → `evals.case` → `evals/__init__` → `evals.runner` → `durable`, partially initialised).
- **Fix:** import `durable.invoke_graph` lazily inside `_run_once` (matches the existing lazy-import
  precedent in `store.default_store` / `graph.build.load_graph_tools`).
- **Files modified:** `src/triagedesk/evals/runner.py`
- **Verification:** import + full suite green; `derive_thread_id` import works standalone.
- **Committed in:** `e548c19` (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both auto-fixes were necessary for correctness/import health. No scope creep — no
new symbol, file, or behaviour beyond the plan.

## Issues Encountered

None beyond the two auto-fixes above. The plan's call-site list matched reality exactly; the `--durable`
path was additionally exercised end-to-end against the real borrowed store (npx `mcp-sqlite@1.0.9` was
already cached), confirming pause → resume-command → fresh-process resume → dismiss-refusal → non-zero
on a completed thread.

## User Setup Required

None - no external service configuration required. (`--durable` may launch the borrowed
`npx mcp-sqlite` on its first write; the bare demo and the whole test suite do not.)

## Known Stubs

None.

## Threat Flags

None — the change stays within the plan's `<threat_model>`. No new network/file/trust surface: the
resume value is a plain `dict` validated by `ApprovalToken`, the deserialiser allowlist is unchanged
(no new entry, never `True`), the borrowed write stays parameterised, and `--approver`/`--role` are
required at runtime for approve/edit (no fabricated identity).

## Next Phase Readiness

- Ready for **Phase 7** (replay read-only): the queue now has exactly one row per case and the durable
  thread is content-addressed, so replay assertions (zero rows / zero commits) have a stable identity to
  assert against (06-01 already established the same persistence contract).
- Ready for the **DOCS** phase: `docs/DEMO.md` documents the durable two-command story; the CLI is the
  source of the command text and `EVALS.md` remains the sole owner of the numbers.
- No blockers.

---

*Phase: 06-durable-execution-idempotent-gate*
*Completed: 2026-10-12*

## Self-Check: PASSED

All 7 changed files present; commits `6208518`, `e548c19`, `9c87be6`, `a878181` are ancestors of HEAD.
