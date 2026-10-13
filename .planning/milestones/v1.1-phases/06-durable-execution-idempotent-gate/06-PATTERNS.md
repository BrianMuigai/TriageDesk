# Phase 6: Durable Execution & Idempotent Gate - Pattern Map

**Mapped:** 2026-10-12
**Files analyzed:** 16 (9 production/modify, 1 new production helper, 6 tests)
**Analogs found:** 16 / 16

> Every analog below was verified **git-tracked** (`git ls-files -- <path>` non-empty). No
> gitignored mirror paths (`checkpoints.db`, `triage.db` are `*.db`, ignored — but they are
> runtime artefacts, never analogs). All excerpts are real, current source.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/triagedesk/store/queue.py` | store / key-derivation | CRUD | itself + `graph/build.py::_allowed_msgpack_modules` (schema-derived tuple) | exact (self-edit) |
| `src/triagedesk/store/__init__.py` | protocol / interface | request-response | itself (`Store` protocol docstrings) | exact (self-edit) |
| `src/triagedesk/store/memory.py` | store impl | CRUD | itself (`read_queue_row` + `upsert_queue_row`) | exact (self-edit) |
| `src/triagedesk/store/borrowed.py` | store impl | file-I/O (SQL) | itself (`upsert_queue_row` + `write_chain_head` upsert) | exact (self-edit) |
| `src/triagedesk/mcp/server.py` | controller (MCP tool) | request-response | itself (`score_priority` already takes `case: CaseInput`) | exact (self-edit) |
| `src/triagedesk/graph/nodes.py` | graph node factory | request-response | itself (`_make_score` forwards `case.model_dump()`) | exact (self-edit) |
| `src/triagedesk/evals/tools.py` | adapter | request-response | itself (`score_priority` / `raise_recheck_flag` forwarding) | exact (self-edit) |
| `src/triagedesk/cli.py` | CLI / controller | request-response | itself (`demo` subcommand registration) | exact (self-edit) |
| `src/triagedesk/demo/run.py` | runner | streaming / durable | itself (`_run_beat`) + `evals/runner.py::_run_once` | exact (self-edit) |
| NEW shared pause/resume helper (decide home) | utility | request-response (durable) | `evals/runner.py::_run_once` + `demo/run.py::_run_beat` | role-match |
| `tests/test_graph_durable.py` | test | durable/restart | `tests/test_graph_tracer.py::test_checkpoint_survives_a_fresh_saver` | exact |
| `tests/test_commit_idempotent.py` | test | CRUD | itself (rewrite the `RED != ORANGE` test) | exact (self-edit) |
| `tests/test_mcp_tools.py` | test | request-response | itself (`commit_priority` call sites) | exact (self-edit) |
| `tests/test_audit_chain.py` | test | event-driven | itself (`commit_to_queue` + tool calls) | exact (self-edit) |
| `tests/test_borrowed_store.py` | test | file-I/O (SQL) | itself (`test_upsert_queue_row_inserts...`) | exact (self-edit) |
| `tests/conftest.py` | test fixture | request-response | itself (`build_graph_tools.commit_priority`) | exact (self-edit) |

---

## Pattern Assignments

### `src/triagedesk/store/queue.py` (store, CRUD) — MODIFY

**Analog:** itself (`store/queue.py:28-79`) + **schema-derivation pattern** from
`graph/build.py::_allowed_msgpack_modules` (lines 263-276).

**The schema-derived tuple pattern** (imitate this DRY shape; currently a hand-maintained tuple) —
`graph/build.py:263-276`:
```python
def _allowed_msgpack_modules() -> list[tuple[str, str]]:
    """Derived from the schema module rather than hand-listed, so a new state contract
    is covered automatically (DRY)."""
    return [
        (schema_module.__name__, name)
        for name, obj in vars(schema_module).items()
        if isinstance(obj, type)
        and issubclass(obj, BaseModel)
        and obj.__module__ == schema_module.__name__
    ]
```

**Current code being replaced** — `store/queue.py:28-34` (the bug) and `51-79`:
```python
IMMUTABLE_FIELDS: tuple[str, ...] = (
    "colour", "target", "triggered_rules", "citations", "used_vitals",
)

async def commit_to_queue(store, *, case_id, colour, content, target=None):
    key = content_hash(case_id, content)
    existing = await store.read_queue_row(case_id, key)
    if existing is not None:
        return existing, False          # <-- returns UNCHANGED: no supersede today
    row = QueueRow(case_id=case_id, content_hash=key, colour=colour, target=target,
                   position=await store.next_position(), created_at=datetime.now(UTC))
    await store.upsert_queue_row(row)
    return row, True
```

**Target shape** (from 06-RESEARCH "Code Examples"; `IMMUTABLE_FIELDS` derived from the schema so
it cannot drift, and the existing-key branch **supersedes in place** preserving
`position`/`created_at`):
```python
from triagedesk.core.schema import CaseInput

IMMUTABLE_FIELDS: tuple[str, ...] = tuple(CaseInput.model_fields)  # DRY, cannot drift

async def commit_to_queue(store, *, case_id, colour, content, target=None):
    key = content_hash(case_id, content)
    existing = await store.read_queue_row(case_id, key)
    if existing is not None:
        if existing.colour != colour or existing.target != target:
            updated = existing.model_copy(update={"colour": colour, "target": target})
            await store.upsert_queue_row(updated)   # preserve position/created_at
            return updated, False
        return existing, False
    row = QueueRow(case_id=case_id, content_hash=key, colour=colour, target=target,
                   position=await store.next_position(), created_at=datetime.now(UTC))
    await store.upsert_queue_row(row)
    return row, True
```

> NOTE: `store/queue.py` currently imports `core.hashing.hash_value` only. Importing
> `core.schema.CaseInput` here stays within the layering (store → core is allowed; `core/` never
> imports `store/`). `content_hash` (lines 37-48) is unchanged — it already reads only
> `IMMUTABLE_FIELDS`.

---

### `src/triagedesk/store/__init__.py` (protocol, request-response) — MODIFY

**Analog:** itself — the `Store` protocol + `QueueRow` docstrings (`store/__init__.py:40-54, 85-87`).

**Current contract docstring to widen** (lines 85-87):
```python
    async def upsert_queue_row(self, row: QueueRow) -> None:
        """Insert the row, ignoring a duplicate idempotency key (belt-and-braces)."""
        ...
```

**Target:** change the docstring to state the new semantics — *"insert, or update the mutable
fields (`colour`/`target`) by key, preserving `position`/`created_at`."* No signature change; the
protocol stays the one narrow seam (SOLID: ISP/D). `QueueRow` (lines 40-54) is unchanged.

---

### `src/triagedesk/store/memory.py` (store impl, CRUD) — MODIFY

**Analog:** itself — `read_queue_row` (lines 73-78) shows the two-column key comparison the upsert
must match; `upsert_queue_row` (lines 84-88) is append-only today.

**Current append-only impl** (lines 84-88):
```python
    async def upsert_queue_row(self, row: QueueRow) -> None:
        self._note("upsert_queue_row", row.case_id, row.content_hash)
        key = (row.case_id, row.content_hash)
        if all((existing.case_id, existing.content_hash) != key for existing in self.rows):
            self.rows.append(row)
```

**Target:** replace-by-key (insert-or-update) — same key updates the existing element **in place**;
never `append` a second row:
```python
    async def upsert_queue_row(self, row: QueueRow) -> None:
        self._note("upsert_queue_row", row.case_id, row.content_hash)
        key = (row.case_id, row.content_hash)
        for index, existing in enumerate(self.rows):
            if (existing.case_id, existing.content_hash) == key:
                self.rows[index] = row     # supersede in place (keeps list order == position)
                return
        self.rows.append(row)
```

> The `new_position()`/`next_position()` method (lines 80-82, `len(self.rows) + 1`) is untouched —
> the update path must never call it (Pitfall 2).

---

### `src/triagedesk/store/borrowed.py` (store impl, file-I/O/SQL) — MODIFY

**Analog:** itself — the existing `INSERT OR IGNORE` upsert (lines 199-218) and the
**`INSERT OR REPLACE`** precedent in `write_chain_head` (lines 262-272). Use the SQLite UPSERT form
(`ON CONFLICT ... DO UPDATE`), NOT `INSERT OR REPLACE` (which deletes+reinserts and would reset
`position`).

**Current impl** (lines 199-218):
```python
    async def upsert_queue_row(self, row: QueueRow) -> None:
        """Insert the row, ignoring a duplicate idempotency key (belt-and-braces)."""
        await self._call(
            TOOL_QUERY,
            {
                "sql": (
                    f"INSERT OR IGNORE INTO {QUEUE_TABLE} "
                    "(case_id, content_hash, colour, target, position, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                "values": [row.case_id, row.content_hash, row.colour, row.target,
                           row.position, row.created_at.isoformat()],
            },
        )
```

**Target SQL** (the PK is `(case_id, content_hash)` — `_QUEUE_DDL` lines 64-73):
```sql
INSERT INTO queue (case_id, content_hash, colour, target, position, created_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(case_id, content_hash) DO UPDATE SET
  colour = excluded.colour,
  target = excluded.target
```
Parameterised `values` exactly as today (lines 209-216) — no string interpolation of case content
(Security Domain: SQL injection mitigation).

---

### `src/triagedesk/mcp/server.py` (controller/MCP tool, request-response) — MODIFY

**Analog:** itself — `score_priority(case: CaseInput, ...)` (lines 178-191) is the **exact**
typed-`case` parameter precedent; `_jsonable` (lines 76-85) is the ONE serialiser the audit
interceptor already uses.

**Typed-parameter precedent** (`score_priority`, lines 178-182):
```python
@server.tool()
@audited()
def score_priority(
    case: CaseInput,
    matched_discriminator_ids: list[str] | None = None,
) -> PriorityResult:
```

**Current `commit_priority`** (lines 219-259) — signature at 221-223 and the buggy `content=` at
249-254:
```python
async def commit_priority(
    case_id: str, colour: str, approval_token: dict[str, object] | None = None
) -> CommitResult:
    ...
    row, created = await commit_to_queue(
        store,
        case_id=case_id,
        colour=committed_colour,
        content={"colour": committed_colour},   # <-- key-breadth bug
    )
```

**Target:** add `case: CaseInput` to the signature (required) and pass `content=case`:
```python
async def commit_priority(
    case_id: str,
    colour: str,
    case: CaseInput,
    approval_token: dict[str, object] | None = None,
) -> CommitResult:
    ...
    row, created = await commit_to_queue(
        store, case_id=case_id, colour=committed_colour, content=case,
    )
```
`CaseInput` is **already imported** at `server.py:31-39`. The refusal path (lines 236-245) stays
**before** the store call (D-05). The `@audited(approval=True)` decorator (line 220) is untouched —
the audit interceptor must not be edited (D-18); it serialises `case` via `_jsonable` automatically.

---

### `src/triagedesk/graph/nodes.py` (graph node factory, request-response) — MODIFY

**Analog:** itself — `_make_score` (lines 168-180) is the **exact** pattern: build a payload
mapping and forward `state["case"].model_dump()` to the tool.

**Precedent** (`_make_score`, lines 171-178):
```python
    async def score(state: TriageState) -> dict[str, Any]:
        payload = {
            "case": state["case"].model_dump(),
            "matched_discriminator_ids": list(state.get("matched_ids") or []),
        }
        priority = parse_tool_result(PriorityResult, await tools["score_priority"](payload))
        return {"priority": priority}
```

**Current `_make_commit` payload** (lines 301-319):
```python
    async def commit(state: TriageState) -> dict[str, Any]:
        priority = state["priority"]
        result = parse_tool_result(
            CommitResult,
            await tools["commit_priority"](
                {
                    "case_id": case_id_for(state["raw_note"]),
                    "colour": priority.colour or "",
                    "approval_token": _build_token(state.get("approval"), priority),
                }
            ),
        )
        return {"commit_result": result}
```

**Target:** add `"case": state["case"].model_dump()` to the payload. `case_id_for` (lines 83-90) is
the **ONE** thread_id derivation and must not change:
```python
def case_id_for(raw_note: str) -> str:
    return hash_value({"raw_note": raw_note})[:16]
```

---

### `src/triagedesk/evals/tools.py` (adapter, request-response) — MODIFY

**Analog:** itself — `score_priority` (lines 107-111) and `raise_recheck_flag` (lines 113-116) both
`model_validate` the incoming dict and forward to `server_module`.

**Precedent** (lines 107-111, 113-116):
```python
    async def score_priority(inp: Mapping[str, Any]) -> Any:
        parsed = CaseInput.model_validate(inp["case"])
        return await server_module.score_priority(parsed, inp.get("matched_discriminator_ids"))

    async def raise_recheck_flag(inp: Mapping[str, Any]) -> Any:
        previous = CaseInput.model_validate(inp["previous"])
        current = CaseInput.model_validate(inp["current"])
        return await server_module.raise_recheck_flag(previous, current)
```

**Current `commit_priority` adapter** (lines 118-121) — omits `case`:
```python
    async def commit_priority(inp: Mapping[str, Any]) -> Any:
        return await server_module.commit_priority(
            str(inp["case_id"]), str(inp["colour"]), inp.get("approval_token")
        )
```

**Target:** validate and forward `case`, matching the sibling adapters:
```python
    async def commit_priority(inp: Mapping[str, Any]) -> Any:
        return await server_module.commit_priority(
            str(inp["case_id"]),
            str(inp["colour"]),
            CaseInput.model_validate(inp["case"]),
            inp.get("approval_token"),
        )
```
`CaseInput` is already imported (`evals/tools.py:21`).

---

### `src/triagedesk/cli.py` (CLI/controller, request-response) — MODIFY

**Analog:** itself — the `demo` subcommand registration (lines 51-74) and dispatch (lines 91-100).

**Subcommand registration pattern** (lines 51-74):
```python
    demo_parser = subcommands.add_parser(
        "demo", help="run the scripted demo storyboard (offline by default)"
    )
    demo_parser.add_argument("--online", action="store_true", help="...")
    ...
```

**Dispatch pattern** (lines 91-100):
```python
    if args.command == "demo":
        if args.list_beats:
            return list_beats()
        return asyncio.run(
            run_demo(beats=args.beats, offline=not args.online, fixture_dir=args.fixture)
        )
    return 2
```

**Target:**
1. Add `--durable` flag to the `demo` parser and thread it into `run_demo(..., durable=args.durable)`.
2. Register a `resume` subcommand:
   `resume --thread-id <id> --decision approve|edit|dismiss --approver NAME --role ROLE [--colour C] [--db PATH]`
   (per CONTEXT lines 52-54); dispatch to the new resume runner (via the shared helper).
3. Keep the CLI "the thinnest possible shell" (module docstring, lines 1-8) — import runner
   functions, never inline async logic. `--approver`/`--role` optional (required only for
   `approve`/`edit`, Open Q4).

The CLI test analog (`tests/test_demo_runbook.py:23,47`) drives the public `main([...])` surface —
the new resume test must do the same.

---

### `src/triagedesk/demo/run.py` (runner, durable) — MODIFY

**Analog:** itself — `_run_beat` (lines 171-196) already builds tools, compiles a graph with a
checkpointer, invokes, reads `__interrupt__`, and resumes. The durable path mirrors this but uses
`checkpointed_graph` over a file and a **content-derived** `thread_id`.

**Current in-memory per-beat path** (lines 180-195):
```python
    recorder = UsageRecorder()
    tools = build_tools(case, offline=offline, recorder=recorder)
    graph = build_graph(_traced_tools(tools, _print_tool_call), checkpointer=_checkpointer())
    config = {"configurable": {"thread_id": f"demo-{beat.name}-{index}"}}   # positional id
    initial: dict[str, Any] = {"raw_note": case.note, "case": case.case}
    ...
    result = await graph.ainvoke(initial, config)
    payload: dict[str, Any] | None = None
    if result.get("__interrupt__"):
        payload = dict(result["__interrupt__"][0].value)
        result = await graph.ainvoke(Command(resume=_resume_for(beat)), config)
```

**Cross-module private-helper import precedent** (lines 31-34) — already imports `_capture` and
`_checkpointer` from `evals.runner`. A new shared pause/resume helper follows the same established
convention:
```python
from triagedesk.evals.runner import _capture, _checkpointer
```

**Target (durable mode, CONTEXT lines 50-59 + RESEARCH "Code Examples"):**
```python
from triagedesk.graph.nodes import case_id_for
from triagedesk.graph.build import checkpointed_graph, CHECKPOINTS_DB_PATH

thread_id = case_id_for(case.note.strip())            # SAME stripped value the graph uses
config = {"configurable": {"thread_id": thread_id}}
async with checkpointed_graph(tools, db_path) as graph:
    result = await graph.ainvoke(initial, config)
    if result.get("__interrupt__"):
        print(f"[durable] paused at approval gate; thread_id={thread_id}")
        print(f"[durable] resume: uv run triagedesk resume --thread-id {thread_id} "
              f"--decision approve --approver NAME --role ROLE [--db {db_path}]")
        return 0                                       # NO auto-resume (CONTEXT line 59)
```
Key constraints: default (no `--durable`) stays hermetic in-memory (lines 234-247 unchanged);
`--durable` resolves the real store seam (`store.default_store`) so the row survives the restart
(CONTEXT line 68); derive `thread_id` from the **stripped** note (Pitfall 5).

---

### NEW shared pause/resume helper (utility, durable) — CREATE

**Analog:** `evals/runner.py::_run_once` (lines 149-167) and `demo/run.py::_run_beat` (lines
171-196). Both do the same three steps — *invoke → read `__interrupt__` → `ainvoke(Command(resume=...))`*.

**`_run_once` precedent** (lines 149-167):
```python
async def _run_once(case, run_index, tools):
    graph = build_graph(tools, checkpointer=_checkpointer())
    config = {"configurable": {"thread_id": f"{case.id}-{run_index}"}}
    initial: dict[str, Any] = {"raw_note": case.note, "case": case.case}
    ...
    result = await graph.ainvoke(initial, config)
    payload: dict[str, Any] | None = None
    if result.get("__interrupt__"):
        payload = dict(result["__interrupt__"][0].value)
        result = await graph.ainvoke(Command(resume=dict(_UNAPPROVED_RESUME)), config)
    ...
    return _capture(result, payload), latency, result
```

**Recommended home (Open Q3, CONTEXT line 61-64):** a single helper co-located with the durable
seams so `demo --durable` and `resume` **cannot drift**. Two DRY-compliant options:
- **Preferred:** add to `graph/build.py` (the composition root that already owns
  `checkpointed_graph`, `CHECKPOINTS_DB_PATH`, `run_case`) — e.g.
  `async def resume_thread(graph, config, decision: Mapping) -> Mapping` and a
  `derive_thread_id(note) -> str` that delegates to `nodes.case_id_for`.
- Alternative: a new `graph/durable.py` module. Do **not** duplicate the
  `case_id_for(case.note.strip())` derivation in both `demo/run.py` and the `resume` command —
  import it from ONE place (CONTEXT lines 32-34; DRY).

The helper must reuse `_allowed_msgpack_modules` (already installed by `checkpointed_graph`,
`graph/build.py:259`) — no new allowlist entries (Pitfall 6).

---

### `tests/test_graph_durable.py` (test, durable/restart) — CREATE (Wave 0)

**Analog:** `tests/test_graph_tracer.py::test_checkpoint_survives_a_fresh_saver` (lines 108-122) —
the exact two-`async with checkpointed_graph` restart pattern; extended with the resume + count
assertions.

**Restart precedent** (lines 108-122):
```python
async def test_checkpoint_survives_a_fresh_saver(tmp_path: Path) -> None:
    db_path = tmp_path / "checkpoints.db"
    tools = build_graph_tools()
    config = {"configurable": {"thread_id": "case-checkpoint"}}

    async with checkpointed_graph(tools, db_path) as graph:
        result = await graph.ainvoke({"raw_note": NOTE}, config)
        assert result.get("__interrupt__"), "the first pass did not pause"

    # A fresh saver over the SAME file — simulating a process restart.
    async with checkpointed_graph(tools, db_path) as reopened:
        snapshot = await reopened.aget_state(config)
        assert snapshot.next == ("approval_gate",), f"pending node drifted: {snapshot.next}"
        assert snapshot.tasks and snapshot.tasks[0].interrupts, "the interrupt was not persisted"
```

**Header/imports analog** (lines 1-30 of `test_graph_tracer.py`) — reuse its module-level
`build_graph_tools` import from `conftest` and `checkpointed_graph` from `graph.build`.

**Target test body** (RESEARCH "Assert exactly-once after a restart (test sketch)", lines 426-448):
run case through two `checkpointed_graph` instances over one `tmp_path` file; assert one queue row
and per-tool audit counts all == 1 (Open Q1 recommendation). Set the config `thread_id` with
`case_id_for(case.note.strip())` so the durable derivation is exercised end-to-end.

**Also add in this file (or a sibling):**
- **supersede test** — mirror `test_graph_recheck.py:83-98` style: commit `ORANGE`, then `GREEN`
  with the same `case_id`+`CaseInput`; assert `len(rows) == 1`, `rows[0].colour == "GREEN"`,
  `rows[0].position == 1`, `created_at` unchanged.
- **thread_id derivability test** — assert the demo/resume `thread_id` equals
  `case_id_for(<stripped note>)` (CONTEXT "Specific Ideas").
- **CLI test** — drive `triagedesk.cli.main([...])` for `resume` parse+dispatch and `demo --durable`
  printing one greppable `thread_id` line, in the style of `tests/test_demo_runbook.py:45-49`.

---

### `tests/test_commit_idempotent.py` (test, CRUD) — REWRITE

**Analog:** itself. The test to **rewrite** is `test_changing_a_scored_field_changes_the_content_hash`
(lines 57-61):
```python
async def test_changing_a_scored_field_changes_the_content_hash() -> None:
    """A different scored field produces a different key (and so a distinct row)."""
    red = content_hash("c-1", {"colour": "RED", "target": "now"})
    orange = content_hash("c-1", {"colour": "ORANGE", "target": "now"})
    assert red != orange
```
This is **wrong by design** after the fix (both collapse to the same key). Rewrite to the supersede
contract: same `case_id` + same `CaseInput`, different colour → one row, colour updated,
`position`/`created_at` preserved (CONTEXT lines 45-47).

**Existing passing test to keep as a shape reference** (`test_commit_twice_yields_one_row`, lines
40-54) and `test_crash_then_retry_yields_one_row` (lines 74-95, uses `retried.position == 1` —
the position-preservation analogue).

**Store-level tests (lines 40-95):** pass a real `CaseInput` as `content` (not
`{"colour": ...}`) so the key is meaningful (`test_volatile_timestamp_...` lines 64-71 keeps
asserting `approved_at not in IMMUTABLE_FIELDS`).

**Tool-level tests (lines 101-175):** add `"case": <CaseInput payload>` to every
`client.call_tool("commit_priority", {...})` call. `CaseInput` import: add to line 19.

---

### `tests/test_mcp_tools.py` (test, request-response) — MODIFY

**Analog:** itself — four `commit_priority` call sites omit `case`.

Call sites: lines 89, 106-108, 124-132, 156-160. Add a `case` field to each dict, e.g.:
```python
_case = {"respiratory_rate": 24, "heart_rate": 118, "avpu": "alert", "complaint": "central chest pain"}
call = await client.call_tool("commit_priority", {"case_id": "c-1", "colour": "RED", "case": _case})
```
Use the same case-shape already used for `score_priority` at lines 223-228
(`test_audit_chain.py`).

---

### `tests/test_audit_chain.py` (test, event-driven) — MODIFY

**Analog:** itself.

- Line 135: `commit_to_queue(memory_store, case_id="c-1", colour="RED", content={"colour": "RED"})`
  → `content=CaseInput(...)`.
- Lines 187, 199-202, 234-237: `commit_priority` tool calls → add `"case"` to the dict. The
  multi-tool test at 229-237 already builds a `case` dict for `score_priority` — reuse it for the
  commit call too.

---

### `tests/test_borrowed_store.py` (test, file-I/O/SQL) — MODIFY

**Analog:** itself — `test_upsert_queue_row_inserts_through_the_query_tool` (lines 124-143).

**Current assertion** (lines 139-143) — the SQL string:
```python
    name, arguments = fake.calls[-1]
    assert name == TOOL_QUERY
    assert f"INSERT OR IGNORE INTO {QUEUE_TABLE}" in arguments["sql"]
    assert arguments["values"][0] == "c-1"
    assert arguments["values"][1] == "abc123"
```

**Target:** assert the new upsert SQL:
```python
    assert f"INSERT INTO {QUEUE_TABLE}" in arguments["sql"]
    assert "ON CONFLICT(case_id, content_hash) DO UPDATE" in arguments["sql"]
```
Keep the `_FakeBorrowedTools` shape (lines 1-100) — add a case for the update path (colour change
with same key) if a value assertion is wanted. `QueueRow` construction (lines 128-135) unchanged.

---

### `tests/conftest.py` (test fixture, request-response) — MODIFY

**Analog:** itself — `build_graph_tools.commit_priority` (lines 157-174).

**Current fake** (lines 157-174) — passes `content={"colour": inp["colour"]}`:
```python
    async def commit_priority(inp: dict[str, Any]) -> CommitResult:
        calls.append(("commit_priority", inp))
        token = inp.get("approval_token")
        ...
        writes.append(inp)
        if store is not None:
            await commit_to_queue(
                store,
                case_id=inp["case_id"],
                colour=inp["colour"],
                content={"colour": inp["colour"]},
            )
        return CommitResult(committed=store is not None, reason="accepted")
```

**Target:** forward the case input as the keyed content (mirrors the real adapter change):
```python
        if store is not None:
            await commit_to_queue(
                store,
                case_id=inp["case_id"],
                colour=inp["colour"],
                content=CaseInput.model_validate(inp["case"]),
            )
```
`CaseInput` is already imported (`conftest.py:20-25`). The shared `RecordingStore` double
(lines 64-77) is unchanged.

---

## Shared Patterns

### Content-addressed identity (the ONE derivation)
**Source:** `src/triagedesk/graph/nodes.py:83-90` (`case_id_for`)
```python
def case_id_for(raw_note: str) -> str:
    return hash_value({"raw_note": raw_note})[:16]
```
**Apply to:** `demo/run.py` (durable `thread_id`), the new resume helper, tests. **Never** invent a
second hash scheme or a per-entry-point prefix (CONTEXT lines 27-34).

### Schema-derived tuples (DRY, cannot drift)
**Source:** `src/triagedesk/graph/build.py:263-276` (`_allowed_msgpack_modules`)
**Apply to:** `store/queue.py::IMMUTABLE_FIELDS` — derive from `CaseInput.model_fields`, never a
hand-maintained list (CONTEXT lines 40-42).

### One hashing path
**Source:** `src/triagedesk/core/hashing.py::hash_value`
**Apply to:** every key/identity derivation. `content_hash` (`store/queue.py:37-48`) and
`case_id_for` both delegate to it. No new hash function (Security Domain: sha256 via the ONE path).

### Injectable store seam
**Source:** `src/triagedesk/mcp/server.py::set_store` / `_resolve_store` (lines 55-73)
```python
def set_store(store: Store | None) -> None:
    global _store
    _store = store
```
**Apply to:** `--durable` (inject `store.default_store` or a tmp-file store) and every test (the
autouse `injected_store` fixture, `conftest.py:86-97`). Tests never launch the borrowed subprocess.

### Uniform audit interceptor — DO NOT EDIT (D-18)
**Source:** `src/triagedesk/mcp/server.py::audited` (lines 88-154)
**Apply to:** `commit_priority` keeps its `@audited(approval=True)` decorator unchanged. The
interceptor records `case` automatically via `_jsonable`. **No de-dup guard** is added — the
no-replay property comes from the checkpoint (CONTEXT line 67).

### Upsert-by-key at the storage boundary
**Source:** `src/triagedesk/store/borrowed.py::write_chain_head` (lines 262-272) — an existing
`INSERT ... OR REPLACE` precedent (but see the DO-UPDATE-not-REPLACE caveat above).
```python
    async def write_chain_head(self, head: str) -> None:
        await self._call(TOOL_QUERY, {"sql": (
            f"INSERT OR REPLACE INTO {AUDIT_HEAD_TABLE} (id, head) VALUES (1, ?)"),
            "values": [head]})
```
**Apply to:** `upsert_queue_row` in both `borrowed.py` and `memory.py`, plus `commit_to_queue`'s
read→mutate→write orchestration. `position`/`created_at` are preserved, never recomputed.

### Two-file split (runtime state vs clinical record) — unchanged
**Source:** `graph/build.py:40` (`CHECKPOINTS_DB_PATH`) + `store/__init__.py:37` (`DOMAIN_DB_PATH`).
`checkpoints.db` and `triage.db` are both `*.db`-gitignored (verified). Tests use `tmp_path`, never
the repo copies (CONTEXT line 56).

---

## No Analog Found

None. Every file to create/modify has a strong same-role, same-data-flow analog in the existing
frozen v1.0 spine. The phase is **wiring at published seams** — no genuinely new pattern is
introduced.

> The one file with only a **role-match** (not exact) is the NEW shared pause/resume helper, because
> it consolidates the invoke→interrupt→resume logic currently duplicated/adjacent in
> `evals/runner.py::_run_once` and `demo/run.py::_run_beat`. The planner should decide its home
> (recommended: `graph/build.py`, which already owns `checkpointed_graph`).

## Metadata

**Analog search scope:** `src/triagedesk/**/*.py` (34 modules), `tests/**/*.py` (35 files).
**Files scanned:** 20 read in full/targeted (all git-tracked).
**Tracked-source gate:** PASS — every analog verified via `git ls-files -- <path>`; no gitignored
mirror paths emitted.
**Pattern extraction date:** 2026-10-12

## PATTERN MAPPING COMPLETE
