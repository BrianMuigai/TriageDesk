# Phase 6: Durable Execution & Idempotent Gate - Research

**Researched:** 2026-10-12
**Domain:** LangGraph 1.2.14 durable checkpoints (`AsyncSqliteSaver`) + idempotent queue-key breadth
**Confidence:** HIGH (every load-bearing claim was verified against the installed source and by
running the project's own code in `.venv`)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**thread_id derivation & stability**
- Derive the `thread_id` from the **existing** `case_id_for(raw_note)` content hash
  (`core.hashing.hash_value`) — never a random uuid, never a per-entry-point prefix. The same case
  content therefore yields the same `thread_id` from any entry point and after a restart.
- Hash input is the **raw note only**, through the one canonical hashing path — no second hash
  function and no ad-hoc string concatenation.
- The derivation lives in exactly ONE place (`graph/nodes.py`, the existing `case_id_for` helper); the
  demo, the CLI and any durable runner **import** it. No caller re-derives or inlines a hash.

**Idempotency key breadth & edit-supersedes (the core bug)**
- The queue idempotency key becomes `case_id` + a hash over the **immutable case input** (the
  normalized `CaseInput` payload), NOT the scored outputs. An `approve` and an `edit` of the same case
  therefore re-derive the SAME key, so exactly one queue row exists per case.
- The immutable-field set is **derived from the `CaseInput` schema** (DRY), not a hand-maintained tuple
  — a future case field is covered automatically and cannot drift from the schema.
- An `edit` **supersedes in place**: the same key updates the existing row's mutable `colour` (and
  `target`), preserving `position` and `created_at`. No second row is inserted and the queue position
  does not move.
- The v1.0 test that asserted "a different scored field produces a different key" (`RED != ORANGE`) is
  **rewritten** to assert the new contract: an edit supersedes (one row, updated colour, unchanged
  position). The old assertion is now wrong by design; the intent (one row per case) is preserved.

**Durable CLI / demo surface**
- `triagedesk demo --durable` swaps the in-memory saver for `checkpointed_graph` over `checkpoints.db`;
  the default (no flag) stays hermetic in-memory so the clean-clone demo needs no file state or model.
- A new `triagedesk resume` subcommand drives the second half of the lifecycle:
  `resume --thread-id <id> --decision approve|edit|dismiss --approver NAME --role ROLE [--colour C]
  [--db PATH]`.
- `checkpoints.db` lives at the repo root — the path already named ONCE in `graph/build.py`
  (`CHECKPOINTS_DB_PATH`) — overridable with `--db`; tests use a `tmp_path` file, never the repo copy.
- On reaching the gate, `demo --durable` prints the derived `thread_id` and the exact `resume` command,
  then exits — a two-step storyboard whose second invocation proves the restart. It does NOT
  auto-resume in-process (that would not demonstrate persistence).

**Interrupt re-entry & exactly-once proof**
- "Exactly one audit record and one queue row" is proven by a test that runs the case through **two
  separate `checkpointed_graph` instances** over one temp checkpoint file (a real restart boundary),
  then asserts exactly one queue row and one `commit_priority` audit record.
- The proof asserts the **audit count**, not the design's good intentions: `approval_gate` stays
  side-effect-free before `interrupt()` (D-04) and the checkpoint short-circuits already-completed
  nodes, so pre-gate tool calls are not replayed. No de-dup guard is added to the interceptor.
- `--durable` resolves the real store seam (`store.default_store`) so the queue row survives the
  restart; tests inject the in-memory double or a tmp-file store.
- Output stays **text only**; the `thread_id` is printed on one stable, greppable line. No `--json`.

### the agent's Discretion
- The exact `CaseInput` field list used for the key (read from the schema at runtime, not hard-coded).
- Whether the supersede is implemented as an `UPDATE` inside `upsert_queue_row` or as an explicit
  `read → mutate → write` in `commit_to_queue`; either is acceptable as long as `Store` stays the one
  seam and `position`/`created_at` are preserved.
- The precise text/format of the printed `thread_id` line and the resume-command hint.
- How the restart is staged in the test (two `asynccontextmanager` entries vs. two saver opens).

### Deferred Ideas (OUT OF SCOPE)
- Model routing / caching / budgets to attack the 14–17 s latency (AGENT-05) — later milestone.
- A `--json` machine-readable output mode for the CLI — not needed by AGENT-01.
- Online eval / drift monitoring (AGENT-06) — later milestone.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-01 | The demo and CLI run through the durable `checkpointed_graph` (SQLite `checkpoints.db`), a case paused at the approval gate resumes after a process restart on a stable `thread_id`, and an **edit** decision supersedes rather than duplicates the queue row (idempotency key covers the immutable case content, not `colour` alone). | (1) Restart+resume semantics proven against installed LangGraph 1.2.14 (probe below). (2) `checkpointed_graph` already exists and works — only the demo/CLI/store must adopt it. (3) Key-breadth fix: derive `IMMUTABLE_FIELDS` from `CaseInput.model_fields` + pass the `CaseInput` as the keyed content (probe proves one key). (4) Supersede-in-place write must be added to `commit_to_queue` + both `Store` impls. (5) `case_id_for` is the ONE thread_id derivation. |
</phase_requirements>

## Summary

Phase 6 is **not** a greenfield build. Every mechanism it needs already exists in the frozen v1.0
spine; the phase *wires them together* and fixes one real bug. Three facts drive the plan:

1. **Durable restart+resume already works.** `graph.build.checkpointed_graph(tools, db_path)` (an
   `asynccontextmanager` over `AsyncSqliteSaver.from_conn_string`) already yields a compiled graph whose
   paused state survives reopening the same SQLite file. I ran the project's own code across **two
   separate `checkpointed_graph` instances over one temp file**: process 2 sees
   `snapshot.next == ('approval_gate',)` with 1 pending interrupt and completes on
   `ainvoke(Command(resume=...), config)` with the **same `thread_id`**.

2. **The checkpoint short-circuits already-completed nodes — pre-gate tool calls are NOT replayed.** In
   the same probe, `normalize_case` (the model call) was invoked **exactly once** and `commit_priority`
   **exactly once** across both processes; only the `approval_gate` node re-ran from its top (twice).
   This is the mechanism behind success criterion 3, and it is confirmed by the LangGraph source
   (`types.py:906-912`: "The graph resumes from the start of the node, **re-executing** all logic").

3. **The key-breadth bug is real and reproducible.** `commit_priority` calls
   `commit_to_queue(..., content={"colour": committed_colour})` (`mcp/server.py:253`) and
   `IMMUTABLE_FIELDS` is the scored-output tuple (`store/queue.py:28-34`). Committing the same case as
   `ORANGE` then `GREEN` writes **two rows** (probe output below). Deriving `IMMUTABLE_FIELDS` from
   `CaseInput.model_fields` and passing the `CaseInput` as `content` makes both derive the *same* key →
   one row. What is still missing is the **supersede write**: today the second commit returns the
   existing row **unchanged** (`colour` stays `ORANGE`) because `commit_to_queue` returns early on an
   existing key and both `Store` impls only ever insert.

**Primary recommendation:** Make `commit_priority` take the typed `case: CaseInput`, derive
`IMMUTABLE_FIELDS = tuple(CaseInput.model_fields)` in `store/queue.py`, and change
`commit_to_queue` to `read → mutate → write` (update `colour`/`target` in place, preserve
`position`/`created_at`) with both `Store` impls upserting by key. Then have `demo --durable` use
`checkpointed_graph` + `case_id_for`, and add a `resume` subcommand that reopens the same file, rebuilds
the same config, and re-invokes with `Command(resume=...)`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Durable pause/resume of a triage run | **Graph runtime (LangGraph checkpointer)** | — | LangGraph owns step scheduling, the interrupt, and the checkpoint; the app must not reimplement it. |
| `thread_id` derivation | **Graph (`graph/nodes.case_id_for`)** | CLI/demo (import only) | One content-addressed derivation, shared by every entry point (D-06, DRY). |
| Idempotency key breadth | **Store seam (`store/queue.py` + `Store` protocol)** | MCP tool (`commit_priority`) supplies the case input | The key is a persistence concern; the tool only *supplies* the immutable content. |
| Supersede-in-place write | **Store implementations (`memory.py`, `borrowed.py`)** | `commit_to_queue` orchestrates read→mutate→write | The write primitive belongs at the storage boundary; the protocol stays the one seam (D-13). |
| Durable CLI surface (`--durable`, `resume`) | **CLI + demo runner (`cli.py`, `demo/run.py`)** | `graph/build.checkpointed_graph`, `store.default_store` | Presentation only; no scoring/gate logic may live here. |
| Exactly-once proof | **Test suite (pytest-asyncio)** | — | A property, not a runtime guard; no de-dup is added to the interceptor (CONTEXT). |

## Standard Stack

No new dependencies. Every library this phase needs is already pinned and installed; the phase is
in-repo wiring only.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LangGraph | **1.2.14** (installed) | `interrupt()` + `Command(resume=...)` + checkpointing | Project decision (D-04); install verified in `.venv`. |
| `langgraph-checkpoint-sqlite` | **3.1.1** (installed) | `AsyncSqliteSaver.from_conn_string` | The durable saver behind `checkpointed_graph`. |
| `langgraph-checkpoint` | **4.2.0** (installed, transitive) | `JsonPlusSerializer`, `InMemorySaver` | Supplies the serde allowlist and the test saver. |
| Pydantic | **2.14.0** | `CaseInput` field derivation + tool contracts | The one schema source (D-14). |
| Python | **3.12.15** (`.venv`) | Runtime | Pinned via uv. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiosqlite` | transitive | Async SQLite for `AsyncSqliteSaver` | Pulled in by the checkpointer; not added manually. |
| pytest + pytest-asyncio | installed | The exactly-once + supersede proofs | `asyncio_mode = "auto"` per `pyproject.toml`. |
| `mcp` | 2.3.0 | In-memory `Client` used by tool-level tests | `from mcp import Client` — already used throughout the suite. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `AsyncSqliteSaver` (`checkpointed_graph`) | `InMemorySaver` | In-memory loses the pause on restart — fails AGENT-01. Keep in-memory only for the hermetic default demo and tests. |
| True upsert in `upsert_queue_row` | A new `Store.update_queue_row(row)` method | New method is more explicit but widens the protocol; the method name `upsert` already implies insert-or-update. Prefer the true upsert (fewer methods, ISP). |
| `Command(resume=dict)` (next interrupt) | `Command(resume={interrupt_id: value})` | The id form is only needed for multiple interrupts; the gate raises exactly one, so the bare form is correct and simpler. |

**Installation:** none — no new packages.

**Version verification:** `langgraph 1.2.14` and `langgraph-checkpoint-sqlite 3.1.1` confirmed present in
`.venv/lib/python3.12/site-packages/` (dist-info directories). Python 3.12.15 confirmed via
`.venv/bin/python --version`.

## Package Legitimacy Audit

**No external packages are installed by this phase.** Every dependency it uses is already pinned in
`uv.lock` and present in `.venv`. No legitimacy check is required; none is emitted.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────── durable lifecycle (this phase) ────────────────┐
                    │                                                                │
  nurse note  ──►  ingest ──► normalize ──► retrieve ──► score ──► verify ──► recheck │
  (raw text)          │          │(model)      │(matcher)  │(scorer)    │(pure)     │
                      │          │             │           │            │           │
                      │          ▼             ▼           ▼            ▼           │
                      │      [escalate]  [request_missing] [END]                    │
                      │                                                             │
                      │                                       ┌─────────────────────┴──┐
                      │                                       │   approval_gate        │
                      │                                       │  (side-effect-free;    │
                      │                                       │   interrupt(payload)   │◄──┐
                      │                                       └───────────┬────────────┘   │
                      │                                                   │               │
                      │             ┌─────────────────────────────────────┘               │
                      │             │  Command(resume=decision)  ◄── triagedesk resume ────┘
                      │             ▼                                                      │
                      │          commit ──► handover ──► END                               │
                      │             │                                                       │
                      └─────────────┼───────────────────────────────────────────────────────┘
                                    │  commit_priority(case_id, colour, case, approval_token)
                                    ▼
                    ┌──────────────── MCP owned server (@audited → 1 audit record/call) ────┐
                    │  refusal path (no token / malformed / dismiss) returns BEFORE store   │
                    │  validated path ─► commit_to_queue(store, case_id, colour, case)      │
                    └───────────────────────────────┬──────────────────────────────────────┘
                                                     │
                                        ┌────────────▼─────────────┐
                                        │  Store protocol (one seam)│
                                        │  read_queue_row /         │
                                        │  upsert_queue_row (NEW:   │
                                        │  insert OR update colour) │
                                        └────────────┬──────────────┘
                                                     │
                        ┌────────────────────────────┴───────────────────────────┐
                        ▼                                                         ▼
              InMemoryStore (tests/demo)                          BorrowedStore (mcp-sqlite,
                                                                   triage.db: queue + audit)
        ── separate file ──►  checkpoints.db (LangGraph runtime state, AsyncSqliteSaver)
                             opened by checkpointed_graph(); the ONLY restart boundary
```

Data flow for the headline property: **run once to the gate → process exits → process 2 reopens the
same `checkpoints.db` with the same `thread_id` → `Command(resume=...)` → `commit` runs once → one
queue row + one `commit_priority` audit record.**

### Recommended Project Structure (unchanged; edits at published seams only)

```
src/triagedesk/
├── graph/
│   ├── build.py        # checkpointed_graph, _allowed_msgpack_modules  (reused, unchanged)
│   ├── nodes.py        # case_id_for (ONE derivation); _make_commit passes `case`
│   └── state.py        # TriageState                                     (unchanged)
├── store/
│   ├── __init__.py     # Store protocol + QueueRow — upsert semantics widen
│   ├── queue.py        # IMMUTABLE_FIELDS (derived) + commit_to_queue (supersede)
│   ├── memory.py       # InMemoryStore.upsert_queue_row → replace by key
│   └── borrowed.py     # BorrowedStore.upsert_queue_row → INSERT ... ON CONFLICT DO UPDATE
├── mcp/server.py       # commit_priority: take `case`, key on it
├── evals/tools.py      # build_tools.commit_priority: forward `case`
├── demo/run.py         # --durable: checkpointed_graph + case_id_for + print resume hint
└── cli.py              # register `resume`; add demo `--durable`
tests/
├── conftest.py         # build_graph_tools.commit_priority forwards `case`
└── test_graph_durable.py  # NEW: restart + exactly-once proof (Wave 0)
```

### Pattern 1: Resume a paused thread from a fresh process over the same file
**What:** Reopen the same SQLite file with a fresh `AsyncSqliteSaver`, rebuild the identical graph, then
`ainvoke(Command(resume=<value>), config)` with the same `thread_id`.
**When to use:** any second process (`triagedesk resume`) or a staged "restart" in a test.
**Example:**
```python
# Source: graph/build.py:243-260 (checkpointed_graph) + langgraph types.py:906-908
async with checkpointed_graph(tools, db_path) as graph:      # fresh saver over the same file
    config = {"configurable": {"thread_id": thread_id}}      # stable, content-derived
    snapshot = await graph.aget_state(config)
    # snapshot.next -> ('approval_gate',); snapshot.interrupts -> 1 pending Interrupt
    result = await graph.ainvoke(Command(resume=decision), config)
```
Proven: `[VERIFIED: probe /tmp/opencode/td_probe.py]` — process 2 sees the pending gate and completes.

### Pattern 2: Enumerate a pending interrupt without resuming
**What:** `aget_state(config)` returns a `StateSnapshot`; `.next` names the node to run and `.interrupts`
holds the still-unanswered interrupts.
**When to use:** the `resume` command should confirm the thread is actually paused before driving it; the
test asserts the persisted interrupt.
**Example:**
```python
# Source: langgraph/pregel/main.py:1217-1332 (StateSnapshot assembly), types.py:711-735
snapshot = await graph.aget_state(config)
assert snapshot.next == ("approval_gate",)
assert snapshot.tasks[0].interrupts          # the persisted interrupt
payload = snapshot.interrupts[0].value       # == the dict passed to interrupt() in approval_gate
```
Proven: `[VERIFIED: probe /tmp/opencode/lg_restart_probe.py]` (`.next`, `.interrupts`, `.tasks[i].interrupts`).

### Pattern 3: Content-derived idempotency key over the immutable case input
**What:** the key = `hash_value({"case_id": case_id, **{f: case[f] for f in CaseInput.model_fields}})`.
**When to use:** every queue write (`approve` and `edit` alike).
**Example:**
```python
# Source: store/queue.py:37-48 (content_hash) with IMMUTABLE_FIELDS derived from the schema
IMMUTABLE_FIELDS: tuple[str, ...] = tuple(CaseInput.model_fields)   # DRY, cannot drift
```
Proven: `[VERIFIED: probe /tmp/opencode/td_keyfix_probe.py]` — an `ORANGE` approve and a `GREEN` edit of
the same case derive the **same** key; today the row is returned unchanged (supersede write absent).

### Anti-Patterns to Avoid
- **A second hash/identifier scheme for `thread_id`.** Use `case_id_for` only. A per-entry-point prefix
  (`f"demo-{beat}-{i}"`) breaks reproducibility across entry points and restarts (CONTEXT locks this).
- **Deriving the key from scored outputs.** `colour` is mutable (an `edit` changes it) — keying on it
  duplicates the row. Key on the immutable input.
- **A de-dup guard in the audit interceptor.** The interceptor must keep appending one record per call
  (AUDIT-01); the no-replay property comes from the checkpoint, not from suppressing writes.
- **Auto-resuming inside `demo --durable`.** A single in-process pause+resume proves nothing about
  persistence (CONTEXT).
- **Editing the scorer / citation helper / `audited` wrapper.** Forbidden (D-18).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pausing/resuming a run across restarts | A JSON "state file" + manual re-entry | `checkpointed_graph` (`AsyncSqliteSaver`) | LangGraph already short-circuits completed nodes and persists pending writes; a hand-rolled one would replay side effects. |
| Enumerating a pending interrupt | Parse the SQLite `checkpoints`/`writes` tables by hand | `graph.aget_state(config).next/.interrupts/.tasks` | The snapshot API is the supported, versioned surface. |
| Stable identity for a case | `uuid4()` / random / positional id | `case_id_for(raw_note)` | Content-addressed → same id from any entry point and after restart. |
| Idempotent insert-or-update | A Python read-modify-write loop with an in-process lock | `INSERT ... ON CONFLICT(case_id, content_hash) DO UPDATE` (SQLite ≥ 3.24) | The PRIMARY KEY + UPSERT is atomic and survives the borrowed server's lack of transactions (D-06, Pitfall 14). |
| Serialisation allowlist for the checkpoint | `allowed_msgpack_modules=True` (dangerous) | The existing `_allowed_msgpack_modules()` from `core.schema` | One derived allowlist (DRY); a second process reuses it unchanged — no new modules needed. |

**Key insight:** the whole phase is *wiring at published seams*. The durable saver, the interrupt gate,
the content hash, the audit interceptor and the two-file split already exist; the only genuinely new
behaviour is the supersede write and the CLI surface.

## Runtime State Inventory

> This is **not** a rename/refactor phase, but it *does* change an idempotency-key scheme, which has a
> stored-data dimension. The inventory below covers that dimension; other categories are explicitly
> answered "none".

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | A `triage.db` written by a v1.0 demo carries queue rows keyed under the **old colour-based** `content_hash`. A post-fix run of the same case computes a **new** key and would treat the old row as absent → a second row. | **No migration.** Data is synthetic; v1.0 is frozen at tag `v1.0-submission`; the demo/tests use in-memory or `tmp_path` stores, never the repo `triage.db`. Document the key-scheme change in `ARCHITECTURE.md`/`DECISIONS.md` (D-06 note); delete any stale local `triage.db`/`checkpoints.db` before a durable demo. |
| Live service config | None — verified: the queue lives in a local SQLite file reached through the borrowed MCP; no external service holds the key. | None. |
| OS-registered state | None — verified: no scheduler/pm2/systemd/launchd registrations reference the queue or `thread_id`. | None. |
| Secrets/env vars | None — verified: the idempotency key and `thread_id` are derived, never configured; no env var names the key. | None. |
| Build artifacts | The `.pyc` caches under `src/triagedesk/**/__pycache__/` will be stale after the edits; uv/pytest regenerate them automatically. `checkpoints.db` (if present at the repo root from a prior manual run) is **gitignored runtime state**, not a build artifact. | None (regenerated). Confirm `checkpoints.db` is gitignored so the deadline clone starts clean. |

**Canonical question — after every file is updated, what runtime system still holds the old key?**
Answer: only a *pre-existing local* `triage.db` (synthetic, disposable). The `checkpoints.db` runtime
state is orthogonal to the key (it stores graph state, not queue keys) and needs no migration.

## Common Pitfalls

### Pitfall 1: Assuming `commit_priority` can keep its old signature
**What goes wrong:** adding the required `case: CaseInput` parameter breaks every call site that passes
only `{case_id, colour, approval_token}` — the tool cannot compute the new key without the case input.
**Why it happens:** the key needs the immutable input, and the tool is the only place the write is
keyed.
**How to avoid:** change the signature and forward `case` everywhere in the same change: graph
`_make_commit`, `evals/tools.build_tools`, `tests/conftest.build_graph_tools`, and the tool-level tests
(see the enumerated list below).
**Warning signs:** `ValidationError`/missing-argument errors in `test_mcp_tools.py`, `test_audit_chain.py`,
`test_commit_idempotent.py`.

### Pitfall 2: Supersede updates `position`/`created_at`
**What goes wrong:** an `INSERT OR REPLACE` (or rebuilding a `QueueRow` with a fresh `next_position()`)
moves the case in the queue or resets its creation time on an edit.
**Why it happens:** `INSERT OR REPLACE` deletes then re-inserts the row.
**How to avoid:** `INSERT ... ON CONFLICT(case_id, content_hash) DO UPDATE SET colour=excluded.colour,
target=excluded.target` (SQLite) and a same-key replace in `InMemoryStore`; never call `next_position()`
on the update path. Assert `position` and `created_at` are unchanged in the test.
**Warning signs:** the queue position changes after an edit; two rows exist.

### Pitfall 3: Treating the eval runner's `thread_id` as durable
**What goes wrong:** applying the content-derived `thread_id` to `evals/runner.py` makes the three
repeat runs of a case share one thread → runs 2/3 resume run 1's completed checkpoint instead of
running fresh.
**Why it happens:** `evals/runner.py:154` uses `f"{case.id}-{run_index}"` deliberately for **per-run
isolation**, not durability.
**How to avoid:** change only the **durable** entry points (`demo --durable`, `resume`); leave the eval
runner's per-run ids alone.
**Warning signs:** eval stability flags flip; a case appears to run only once.

### Pitfall 4: A shared `thread_id` collides in the durable demo
**What goes wrong:** the storyboard has two beats on the **same case** (`escalation` and `refusal`, both
`E-02`). With a content-derived `thread_id` and one shared `checkpoints.db`, the second beat finds a
thread already past the gate.
**Why it happens:** `case_id_for` is a function of the note only — two beats, one note, one id.
**How to avoid:** resolve this explicitly in the plan (see Open Question 2): either the durable demo runs
one case per invocation, or the refusal path is demonstrated through
`triagedesk resume --decision dismiss` rather than a second in-process run.
**Warning signs:** the refusal beat does not pause (no `__interrupt__`); the demo's durable storyboard
exits without printing a resume hint for the second beat.

### Pitfall 5: Whitespace desynchronises the printed `thread_id`
**What goes wrong:** the demo computes `thread_id` from the unstripped fixture note while the graph's
`ingest` strips it before `approval_gate`/`commit` call `case_id_for({**state["raw_note"]**)}`, so the
printed id does not match the one the gate used.
**Why it happens:** `ingest` writes the stripped note back into `raw_note` (`graph/nodes.py:99-102`).
**How to avoid:** derive the demo's `thread_id` from the **same stripped value** the graph uses (e.g.
`case_id_for(case.note.strip())`), and assert in a test that the printed id equals
`case_id_for(<stripped note>)`.
**Warning signs:** `resume --thread-id <printed>` reports no pending interrupt.

### Pitfall 6: A second process needing new allowlist entries
**What goes wrong:** fear that a resumed run deserialises a type the second process did not allowlist.
**Why it happens:** the checkpoint holds `CaseInput`, `PriorityResult`, `TriggeredRule`, `RecheckFlag`,
`VitalChange`, etc.
**How to avoid:** nothing — `_allowed_msgpack_modules()` (`graph/build.py:263-276`) derives from
`core.schema`, and `checkpointed_graph` installs it on the saver, so the second process gets the same
allowlist automatically. The resume value is a plain `dict`. **No new allowlist entries are required.**
**Warning signs:** (would be) an `InvalidModuleError` on `loads_typed` — not expected here.

## Code Examples

### Derive the key from the schema and make an edit supersede
```python
# Source: store/queue.py (current) — the change in shape, not a copy
from triagedesk.core.schema import CaseInput

# DRY: derived from the schema, so a new CaseInput field is covered automatically.
IMMUTABLE_FIELDS: tuple[str, ...] = tuple(CaseInput.model_fields)

async def commit_to_queue(store, *, case_id, colour, content, target=None):
    key = content_hash(case_id, content)
    existing = await store.read_queue_row(case_id, key)
    if existing is not None:
        if existing.colour != colour or existing.target != target:
            # Supersede IN PLACE: preserve position/created_at, update only mutable fields.
            updated = existing.model_copy(update={"colour": colour, "target": target})
            await store.upsert_queue_row(updated)
            return updated, False
        return existing, False
    row = QueueRow(case_id=case_id, content_hash=key, colour=colour, target=target,
                   position=await store.next_position(), created_at=datetime.now(UTC))
    await store.upsert_queue_row(row)
    return row, True
```

### The durable demo pause + the resume command
```python
# Source: demo/run.py (current) + graph/nodes.py:83-90 (case_id_for)
from triagedesk.graph.nodes import case_id_for
from triagedesk.graph.build import checkpointed_graph

thread_id = case_id_for(case.note.strip())          # ONE derivation, same as the gate
config = {"configurable": {"thread_id": thread_id}}
async with checkpointed_graph(tools, db_path) as graph:   # durable saver over checkpoints.db
    result = await graph.ainvoke(initial, config)
    if result.get("__interrupt__"):
        # print ONE stable, greppable line + the exact resume command, then exit (no auto-resume)
        print(f"[durable] paused at approval gate; thread_id={thread_id}")
        print(f"[durable] resume: uv run triagedesk resume --thread-id {thread_id} "
              f"--decision approve --approver NAME --role ROLE [--db {db_path}]")
```

### Assert exactly-once after a restart (test sketch)
```python
# Source: tests/test_graph_tracer.py:108-122 (the existing restart pattern) + test_eval_tracer.py:206
async def test_restart_resumes_to_one_row_and_one_commit_audit(tmp_path, injected_store):
    db = tmp_path / "checkpoints.db"
    tools = build_tools(case, offline=True, recorder=UsageRecorder())  # REAL audited tools
    cfg = {"configurable": {"thread_id": case_id_for(case.note.strip())}}

    async with checkpointed_graph(tools, db) as first:            # process 1
        r1 = await first.ainvoke({"raw_note": case.note, "case": case.case}, cfg)
        assert r1.get("__interrupt__")

    async with checkpointed_graph(tools, db) as second:           # process 2 (same file)
        assert (await second.aget_state(cfg)).next == ("approval_gate",)
        await second.ainvoke(Command(resume=_named_approval()), cfg)

    assert len(await injected_store.read_queue_rows()) == 1
    commits = [r for r in injected_store.audit_records if r.tool == "commit_priority"]
    assert len(commits) == 1
    # No pre-gate tool was replayed either:
    tools_seen = [r.tool for r in injected_store.audit_records]
    assert tools_seen.count("normalize_case") == 1 and tools_seen.count("score_priority") == 1
```

## Test Churn — the Exact Blast Radius

The signature change (adding `case: CaseInput` to `commit_priority`) and the key change reach these
files. This is the exhaustive list, gathered by grep.

### Production call sites (must change together)
| File | Change |
|------|--------|
| `src/triagedesk/mcp/server.py:221-259` | `commit_priority` takes `case: CaseInput`; pass `content=case` (not `{"colour": ...}`) to `commit_to_queue`. |
| `src/triagedesk/graph/nodes.py:311-317` | `_make_commit` payload adds `"case": state["case"].model_dump()` (or the model). |
| `src/triagedesk/evals/tools.py:118-121` | `build_tools.commit_priority` forwards `inp["case"]` to `server_module.commit_priority`. |
| `src/triagedesk/store/queue.py:28-34, 51-79` | `IMMUTABLE_FIELDS` derived from `CaseInput.model_fields`; `commit_to_queue` does read→mutate→write. |
| `src/triagedesk/store/memory.py:84-88` | `upsert_queue_row` replaces the row with the same key (insert-or-update). |
| `src/triagedesk/store/borrowed.py:199-218` | `upsert_queue_row` → `INSERT ... ON CONFLICT(case_id, content_hash) DO UPDATE SET colour=..., target=...`. |
| `src/triagedesk/store/__init__.py:85-87` | `Store.upsert_queue_row` docstring: "insert, ignoring a duplicate key" → "insert or update the mutable fields by key". |

### Tests that MUST be rewritten or updated
| File / test | Why it breaks | Disposition |
|-------------|---------------|-------------|
| `tests/test_commit_idempotent.py::test_changing_a_scored_field_changes_the_content_hash` (lines 57-61) | Asserts `RED != ORANGE` for colour-only content; with `IMMUTABLE_FIELDS` derived from `CaseInput`, both hashes collapse to the same value → the old assertion is now **wrong by design**. | **REWRITE** to the supersede contract: same `case_id` + same `CaseInput`, different colour → one row, colour updated, `position`/`created_at` preserved. (CONTEXT explicitly sanctions this rewrite.) |
| `tests/test_commit_idempotent.py` store-level tests (lines 40-95) | Pass `content={"colour": ...}` maps; under the new field set the key becomes `case_id`-only (vacuously passes but tests nothing). | UPDATE to pass a `CaseInput` as `content` so the key is meaningful. |
| `tests/test_commit_idempotent.py` tool-level tests (lines 101-175) | Call `commit_priority` without `case`. | UPDATE every call to include `"case": <CaseInput payload>`. |
| `tests/test_mcp_tools.py` (lines 87-164) | Four `commit_priority` call sites omit `case`. | UPDATE to include `case`. |
| `tests/test_audit_chain.py` (lines 133-155, 185-236) | `commit_to_queue(content={"colour": ...})` and `commit_priority` calls without `case`. | UPDATE `content` to a `CaseInput`; add `case` to the tool calls. |
| `tests/test_borrowed_store.py::test_upsert_queue_row_inserts_through_the_query_tool` (lines 124-143) | Asserts `"INSERT OR IGNORE INTO queue" in sql`. | UPDATE to the new `ON CONFLICT ... DO UPDATE` SQL assertion. |
| `tests/conftest.py::build_graph_tools.commit_priority` (lines 157-174) | Fake calls `commit_to_queue(content={"colour": inp["colour"]})`. | UPDATE to forward `inp["case"]` as `content`. |

### Tests likely to still pass (verify, don't assume)
| File | Note |
|------|------|
| `tests/test_graph_recheck.py::test_recheck_does_not_change_the_queue_position` (line 98) | Asserts `[row.position] == [1]` after one approve commit — unaffected, but it *is* the position-preservation analogue; mirror its style in the new supersede test. |
| `tests/test_demo.py` (lines 45-56) | Uses `read_queue_rows()` counts on `InMemoryStore`; unaffected by the key change (fresh store per beat). |
| `tests/test_graph_tracer.py::test_checkpoint_survives_a_fresh_saver` (lines 108-122) | Already the restart proof; the new durable test extends it. |
| `tests/test_safety_spine.py`, `tests/test_mcp_server.py` | Reference `commit_priority` by **name only** (allowlist / tool list), not by signature — unaffected. |

### New tests required (Wave 0)
- `tests/test_graph_durable.py::test_restart_resumes_to_one_row_and_one_commit_audit` —
  the AGENT-01 headline proof (sketch above).
- A store-level supersede test — the rewritten `test_changing_a_scored_field_...` (or a new
  `test_an_edit_supersedes_the_row_in_place`): commit `ORANGE`, then `GREEN` with the same
  `case_id`+`CaseInput`; assert `len(rows) == 1`, `rows[0].colour == "GREEN"`,
  `rows[0].position == 1`, and `created_at` unchanged.
- A `thread_id` derivability test — assert the demo/resume `thread_id` equals
  `case_id_for(<stripped note>)` so a reviewer can recompute it by hand (CONTEXT "Specific Ideas").
- A CLI test for the `resume` subcommand (parse + dispatch) and for `demo --durable` printing one
  greppable `thread_id` line.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Key the queue on `colour`/scored outputs | Key on the immutable `CaseInput` | This phase (v1.1) | An `edit` no longer duplicates the row; the key cannot drift from the schema. |
| Demo uses a positional `thread_id` (`demo-{beat}-{index}`) | Content-derived `case_id_for(note)` | This phase | The same case is resumable from any entry point and after a restart. |
| Durable saver exists but is not the demo/CLI path | `checkpointed_graph` is exercised by `demo --durable` + `resume` | This phase | The headline property (survives a restart) becomes demonstrable, not just unit-tested. |

**Deprecated/outdated:**
- `IMMUTABLE_FIELDS` as a hand-maintained tuple of scored outputs — replaced by a schema-derived tuple
  (CONTEXT "idempotency key breadth").
- The `RED != ORANGE` content-hash assertion — wrong by design after this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The two-beat shared-case (`E-02`) `thread_id` collision is resolvable by scoping the durable demo to one case per invocation, or by demonstrating the refusal through `resume --decision dismiss`. | Common Pitfalls 4, Open Q2 | The durable storyboard would not pause on the second E-02 beat; the plan would need a different beat layout. |
| A2 | `commit_priority`'s `case` parameter is **required** (not optional-with-fallback), matching the locked "key covers the immutable case input" decision. | Standard Stack / Test Churn | A larger test blast radius than an optional param would give — but an optional param would diverge from the locked decision. |
| A3 | The durable demo/resume may invoke `store.default_store()` (the borrowed `npx mcp-sqlite` subprocess), which needs npx + a first-run package fetch. | Environment Availability | If the deadline machine is offline on first run, `--durable` fails where the default demo does not; document the fallback. |
| A4 | `CaseInput.model_fields` yields the complete immutable input set (including `complaint`); no field is deliberately excluded. | Code Examples | If a future field is volatile, the key would churn — but all current fields are nurse-provided input. |
| A5 | The "exactly one audit record" phrasing means exactly one `commit_priority` record (a full run legitimately writes one per tool — 4 records). | Summary / Code Examples | If it means *one record total*, the assertion is unimplementable with the uniform interceptor; see Open Q1. |

**If this table is empty:** N/A — five assumptions above need confirmation.

## Open Questions (RESOLVED)

1. **Does "exactly one audit record" mean one total, or one `commit_priority` record?**
   - What we know: the uniform interceptor appends one record **per tool call**, so a clean run writes
     one record each for `normalize_case`, `match_discriminators`, `score_priority`, `commit_priority`.
     CONTEXT's own wording is "one `commit_priority` audit record".
   - What's unclear: the ROADMAP criterion says "exactly one audit record".
   - Recommendation: assert **per-tool counts are all 1** (i.e. no tool was replayed), which is the
     strongest and unambiguous form and subsumes both readings.
   - **RESOLVED:** the plans assert per-tool audit counts all `== 1` (no tool replayed) — see 06-02-PLAN.md
     Task 1 Test A.

2. **How does the durable demo handle two beats on the same case?**
   - What we know: `escalation` and `refusal` both run `E-02`; a content-derived `thread_id` makes them
     collide in one `checkpoints.db`. CONTEXT says the durable demo pauses and exits (no auto-resume).
   - What's unclear: whether the durable storyboard plays all five beats or a single-case subset, and
     how the refusal is shown in durable mode.
   - Recommendation: have the durable path either (a) run one case per invocation, or (b) keep the
     default (in-memory) storyboard for the multi-beat narrative and use `--durable` + `resume` for the
     single-case two-command durability story. Confirm with the user in discuss-phase.
   - **RESOLVED:** the durable path runs exactly one selected beat per invocation (selecting more than one
     prints a clear message and returns 2); the refusal is shown via `resume --decision dismiss` — see
     06-02-PLAN.md Task 1.

3. **How does `resume` obtain the graph tool mapping?**
   - What we know: on resume only `approval_gate` (side-effect-free), `commit` and `handover` re-run;
     `commit` needs `tools["commit_priority"]`, and `build_graph` asserts all five allowlist keys.
   - What's unclear: whether `resume` should build tools in-process like the demo
     (`evals.tools.build_tools`) or launch the real owned MCP server (`load_graph_tools`).
   - Recommendation: reuse the demo's in-process tool construction (DRY, offline-friendly) with a
     placeholder case, since the case-dependent `normalize_case` is short-circuited on resume; factor
     the shared pause/resume plumbing into one helper so `demo --durable` and `resume` cannot drift.
   - **RESOLVED:** `resume` builds its tool mapping in-process from a placeholder `CaseSpec` via
     `evals.tools.build_tools` (it never launches the owned MCP server), and the shared pause/resume
     plumbing lives once in `durable.py` — see 06-02-PLAN.md Task 1.

4. **Should `resume` require `--approver`/`--role` for `dismiss`?**
   - What we know: `ApprovalToken` requires non-empty `approved_by`/`role`, but `commit_priority`
     refuses a `dismiss` before validating the token.
   - Recommendation: make `--approver`/`--role` optional and required only for `approve`/`edit`, so
     `resume --decision dismiss` demonstrates the gate's refusal path (the demo's climax) without a
     fabricated approver.
   - **RESOLVED:** `--approver`/`--role` are optional at the CLI and required only for `approve`/`edit`
     (enforced in `durable.approval_decision`); `dismiss` needs neither — see 06-02-PLAN.md Tasks 1–2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python (`.venv`) | All | ✓ | 3.12.15 | — (pinned via uv). |
| uv | `uv run …`, tests | ✓ | 0.12.24 | — |
| Node / npx | borrowed SQLite MCP for `--durable` | ✓ | node 22.14.0 | In-memory store (default demo), `tmp_path` store (tests). |
| Ollama | `normalize` in real mode | ✓ | 0.30.6 | `--durable`/demo default is offline (golden fixture); no model needed for AGENT-01. |
| `checkpoints.db` at repo root | `demo --durable` | optional | — | A fresh temp file for tests; delete stale repo copy before a durable demo. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** the borrowed `npx mcp-sqlite` (network on first fetch) — the
default hermetic demo and all tests avoid it; only production `--durable` uses it (A3).

## Security Domain

> `security_enforcement` is enabled (ASVS level 1) in `.planning/config.json`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CLI, no user authn; the "approver" is a named field, not a credential. |
| V3 Session Management | no | Each invocation is stateless apart from `checkpoints.db`. |
| V4 Access Control | yes | The gate: `commit` is reachable only through a resumed interrupt with a validated `ApprovalToken`; refusal path touches no store (D-05). |
| V5 Input Validation | yes | Untrusted note → typed `CaseInput`; the resume value is untrusted → `ApprovalToken.model_validate`; `final_colour` validated against the loaded substrate (`core/schema.py:195-204`). |
| V6 Cryptography | yes | sha256 via the one `core.hashing.hash_value` — never hand-roll (this phase adds no new crypto). |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered `checkpoints.db` injection (arbitrary object deserialisation) | Tampering / Elevation | `JsonPlusSerializer(allowed_msgpack_modules=<explicit list>)` — an allowlist, **never `True`** (`graph/build.py:263-276`). |
| Crafted resume value setting a colour | Tampering | `ApprovalToken` validation + `final_colour` checked against `data/sats_tews.yaml` bands; a malformed token is refused (`mcp/server.py:236-245`). |
| SQL injection via case content | Tampering | Parameterised `values` in `BorrowedStore`; the queue write is the only write and carries no free text. |
| Replay/retry duplicating a queue row | Repudiation / Integrity | The content-derived idempotency key + the `PRIMARY KEY` upsert; asserted by the exactly-once test. |
| Unaudited write | Repudiation | Every owned tool call routes through the ONE `audited` interceptor (must not be edited, D-18). |

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: .venv/lib/python3.12/site-packages/langgraph/types.py:906-912]` — "The graph resumes from
  the start of the node, **re-executing** all logic"; `Command(resume=...)` (types.py:833-857).
- `[VERIFIED: .venv/.../langgraph/types.py:711-735]` — `StateSnapshot` fields `values/next/config/
  tasks/interrupts`; "When reading the latest state (`get_state` …), this contains only interrupts
  still waiting for an answer."
- `[VERIFIED: .venv/.../langgraph/pregel/main.py:1217-1332, 1460-1508]` — snapshot assembly and
  `get_state`/`aget_state`.
- `[VERIFIED: .venv/.../langgraph/pregel/_algo.py:232-345, 597-639]` — `apply_writes`/`_triggers`:
  a PULL task runs only if a channel it reads was updated since `versions_seen` (why completed nodes
  are short-circuited).
- `[VERIFIED: .venv/.../langgraph/checkpoint/sqlite/aio.py:118-145, 305-344]` — `AsyncSqliteSaver`
  constructor, `from_conn_string` (`aiosqlite.connect`), `setup()` DDL + WAL.
- `[VERIFIED: .venv/.../langgraph/checkpoint/serde/jsonplus.py:97-158, 223-290]` —
  `allowed_msgpack_modules` normalisation, `_check_allowed_json_modules`, `dumps_typed`/`loads_typed`.
- `[VERIFIED: probe /tmp/opencode/lg_restart_probe.py]` — fresh saver over one file sees
  `next=('gate',)`, 1 interrupt; resume works; `ingest` count 1, `commit` count 1, gate-node count 2.
- `[VERIFIED: probe /tmp/opencode/td_probe.py]` — same result through the project's
  `checkpointed_graph`; and the colour-only key produces **two** rows for one case.
- `[VERIFIED: probe /tmp/opencode/td_keyfix_probe.py]` — `IMMUTABLE_FIELDS = tuple(CaseInput.model_fields)`
  + `content=CaseInput(...)` → approve/edit share one key, one row; colour stays `ORANGE` today (the
  supersede write is still missing).
- `[VERIFIED: src/triagedesk/store/queue.py:28-34]` — `IMMUTABLE_FIELDS: tuple[str, ...] = ("colour",
  "target", "triggered_rules", "citations", "used_vitals")`.
- `[VERIFIED: src/triagedesk/mcp/server.py:249-254]` — `commit_to_queue(store, case_id=case_id,
  colour=committed_colour, content={"colour": committed_colour})`.
- `[VERIFIED: src/triagedesk/graph/nodes.py:83-90]` — `return hash_value({"raw_note": raw_note})[:16]`.
- `[VERIFIED: src/triagedesk/graph/build.py:40, 243-276]` — `CHECKPOINTS_DB_PATH = Path("checkpoints.db")`,
  `checkpointed_graph`, `_allowed_msgpack_modules`.
- `[VERIFIED: src/triagedesk/store/__init__.py:37, 40-54, 85-87]` — `DOMAIN_DB_PATH = Path("triage.db")`,
  `QueueRow`, `upsert_queue_row` docstring.
- `[VERIFIED: src/triagedesk/store/borrowed.py:64-73, 199-218]` — `PRIMARY KEY (case_id, content_hash)`;
  `INSERT OR IGNORE INTO queue`.
- `[VERIFIED: src/triagedesk/store/memory.py:84-88]` — in-memory `upsert_queue_row` appends only when
  the key is absent.
- `[VERIFIED: src/triagedesk/core/schema.py:36-51, 174-204]` — `CaseInput` field set; `ApprovalToken`
  `final_colour` validator.
- `[VERIFIED: src/triagedesk/evals/runner.py:154, src/triagedesk/demo/run.py:183]` — the current
  per-run / positional `thread_id`s.

### Secondary (MEDIUM confidence)
- SQLite UPSERT (`INSERT ... ON CONFLICT ... DO UPDATE`) is available since SQLite 3.24 (2018); the
  bundled `sqlite3` on Python 3.12 is far newer. `[ASSUMED]` for the exact bundled patch level — verify
  with `python -c "import sqlite3; print(sqlite3.sqlite_version)"` during Wave 0.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; installed versions read from `.venv`.
- Architecture / restart semantics: HIGH — verified against the installed LangGraph source *and* by
  running the project's own code byte-for-byte.
- Idempotency fix: HIGH — the key mechanism was executed; the missing supersede write was observed.
- Pitfalls / test churn: HIGH — every file was read; the call-site list is grep-complete.
- CLI surface design: MEDIUM — the shape is locked by CONTEXT, but the durable-demo beat handling and
  the `resume` tool-source are open (Open Q2/Q3).

**Research date:** 2026-10-12
**Valid until:** ~2026-11-11 (30 days; stable pinned deps). Re-verify if `langgraph` is upgraded.

## RESEARCH COMPLETE



