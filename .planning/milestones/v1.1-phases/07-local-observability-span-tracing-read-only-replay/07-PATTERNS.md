# Phase 7: Local Observability — Span Tracing & Read-Only Replay - Pattern Map

**Mapped:** 2026-10-12
**Files analyzed:** 17 (9 production NEW/MOD · 2 tests NEW · 3 infra/docs MOD · 3 observability pkg files)
**Analogs found:** 15 / 17 (2 partial — see "No Analog Found")

> **DRY + SOLID are iron-clad** (`docs/CONVENTIONS.md`). This phase is *wiring + one projection*: it
> adds exactly ONE span writer and ONE replay reader, and edits no working behaviour of the scorer,
> the citation helper, or the audit interceptor. Every analog below is the already-published seam the
> new code copies, so no concern gets a second source of truth.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/triagedesk/observability/__init__.py` | config (package barrel) | transform | `src/triagedesk/store/__init__.py` | role-match |
| `src/triagedesk/observability/spans.py` | utility (the ONE writer) | file-I/O (append-only) | `src/triagedesk/store/audit.py` (`append`, one helper) | role+flow (partial: JSONL vs chained DB) |
| `src/triagedesk/observability/context.py` | state/context utility | transform | `src/triagedesk/mcp/server.py` (`_store` seam) / `src/triagedesk/llm/client.py` (`usage_sink` seam) | role-match |
| `src/triagedesk/observability/offline.py` | config (guard/assertion) | transform | `src/triagedesk/graph/build.py` (`assert_tool_allowlist`) + `store/__init__.py::default_store` (lazy import) | partial (no env-guard analog) |
| `src/triagedesk/store/audit.py` (MOD) | model | CRUD | itself — `AuditRecord` field list | exact |
| `src/triagedesk/store/borrowed.py` (MOD) | store adapter | CRUD (SQL) | itself — `ensure_schema` / `append_audit_record` / `read_audit_records` | exact |
| `src/triagedesk/store/memory.py` (MOD) | store double | CRUD | itself | exact |
| `src/triagedesk/mcp/server.py` (MOD) | middleware (interceptor) | request-response | itself — `audited()` `record()`/`wrapper()` | exact |
| `src/triagedesk/graph/build.py` (MOD) | composition root (wiring) | event-driven | itself — `for name in TRACER_NODES` loop (:170-171) | exact |
| `src/triagedesk/llm/client.py` (MOD) | service (model boundary) | request-response | itself — `extract()` / `usage_sink` | exact |
| `src/triagedesk/replay.py` (NEW) | CLI/service (read-only projection) | batch (read + render) | `src/triagedesk/durable.py` + `evals/runner.py::_capture` | role-match |
| `src/triagedesk/cli.py` (MOD) | route (CLI) | request-response | itself — `resume` subparser + dispatch | exact |
| `tests/conftest.py` (MOD) | test infra | — | itself — autouse `injected_store` fixture | exact |
| `.gitignore` (MOD) | config | — | its own `*.db` runtime-artefacts block | exact |
| `tests/test_spans.py` (NEW) | test | — | `tests/test_audit_chain.py` (+ `test_graph_durable.py`) | role-match |
| `tests/test_replay.py` (NEW) | test | — | `tests/test_durable_cli.py` (+ `test_graph_durable.py`) | role-match |
| `docs/DECISIONS.md`, `ARCHITECTURE.md`, `SECURITY.md` (MOD) | docs | — | `docs/DECISIONS.md` D17/D18 entry shape | exact |

> **Naming note (discretion — D7 span keys/file name are free):** the task prompt names the test files
> `tests/test_spans.py` and `tests/test_replay.py`; `07-RESEARCH.md` names them
> `tests/test_observability.py` and `tests/test_replay_read_only.py`. The planner picks one pair.
> Likewise the task prompt expects `observability/__init__.py` + `spans.py`; RESEARCH proposes a
> slightly wider package (`spans.py` + `context.py` + `offline.py`). Both satisfy D7-02/D7-04 (one
> writer); the plan should pick one structure and say why.

---

## Pattern Assignments

### `src/triagedesk/observability/spans.py` (utility, file-I/O) — the ONE span writer

**Analog:** `src/triagedesk/store/audit.py` — the "one helper per concern" shape (CONVENTIONS §1: *one
logging function; every tool call routes through it*). The new writer is the exact analogue for spans.

**The one-writer contract to copy** (`store/audit.py:134-158`) — one public function, everything else
private, docstring names it as the single path:

```python
async def append(store: AuditStore, fields: Mapping[str, Any]) -> AuditRecord:
    """Append ONE canonical record, chained to the persisted head (AUDIT-01, D-08).
    ...
    Nothing else writes an audit record, so no tool call escapes the audit (AUDIT-03, DRY).
    """
```

**Core pattern — copy the shape, keep stdlib-only** (`07-RESEARCH.md` "Pattern 1", lines 266-308).
Path named ONCE (D7-02); JSON encoding + ids/timestamps live only here (D7-04):

```python
import contextvars, json, time, uuid
from datetime import UTC, datetime
from pathlib import Path

SPANS_PATH = Path("spans.jsonl")          # named ONCE (D7-02)
_sink: contextvars.ContextVar[Path | None] = contextvars.ContextVar("spans_sink", default=None)
_trace: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_stack: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar("span_stack", default=())

def set_sink(path: Path | None) -> None: ...      # test override (discretion)
def bind_trace(trace_id: str) -> None: ...
def current_trace_id() -> str: ...

def emit_span(*, trace_id, span_id, parent_id, kind, name, started, ended,
              duration_ms, attributes=None) -> None:
    line = {"trace_id": trace_id, "span_id": span_id, "parent_id": parent_id,
            "kind": kind, "name": name, "started": started, "ended": ended,
            "duration_ms": duration_ms, "attributes": attributes or {}}
    path = _sink.get() or SPANS_PATH
    with path.open("a", encoding="utf-8") as fh:       # append-only; local; no network
        fh.write(json.dumps(line, default=str, sort_keys=True) + "\n")
```

**Model boundary attribute privacy (D7-08 / Pitfall 6)** — copy from `llm/client.py::_response_usage`
(:58-70): the ONLY fields a model span may carry are the model tag plus
`(prompt_eval_count, eval_count)`. Never the note/prompt/completion.

**Exports to mirror** (`store/audit.py:229-241` `__all__`): declare `SPANS_PATH`, `emit_span`,
`span`, `set_sink`, `bind_trace`, `current_trace_id` in `__all__` so the surface is explicit.

---

### `src/triagedesk/observability/context.py` (state/context utility) — trace + span-stack contextvars

**Analog:** `src/triagedesk/mcp/server.py:52-73` — the injectable module-level seam (`_store` +
`set_store`/`_resolve_store`). Same posture: a tiny module holding process-wide-but-injectable state,
read through one resolver, overridable by tests.

**Injectable-seam pattern to copy** (`mcp/server.py:52-73`):

```python
_store: Store | None = None

def set_store(store: Store | None) -> None:
    """Inject (or clear) the store seam ... passing ``None`` restores the borrowed default."""
    global _store
    _store = store

async def _resolve_store() -> Store:
    if _store is not None:
        return _store
    return await default_store()
```

**What changes:** the state is `contextvars`, not a module global (so pytest-asyncio and concurrent
runs are safe) — see `07-RESEARCH.md` Pattern 1 (:310-312). Keep `bind_trace`/`current_trace_id`/
`set_sink` in ONE place; `spans.py` and the three emit sites import them from here (or from `spans.py`
if the writer owns them — the plan picks one home, not two).

**Second analog — the usage-sink injection precedent** (`llm/client.py:23-28, 73-85`): an optional
callable threaded through a boundary, default `None`, so existing callers are untouched (Liskov).

---

### `src/triagedesk/observability/offline.py` (config, guard) — `harden_offline()`

**Analog (partial):** `src/triagedesk/graph/build.py::assert_tool_allowlist` (:70-85) — the project's
"fail loudly at startup" guard, and `store/__init__.py::default_store` (:122-131) — the lazy-import
pattern for a heavy/optional dependency.

**Guard shape to copy** (`graph/build.py:70-85`):

```python
def assert_tool_allowlist(tool_names: Iterable[str]) -> None:
    """Fail loudly unless *tool_names* equals the declared allowlist (SAFE-03, D-12)."""
    ...
    if missing or unexpected:
        raise RuntimeError("owned tool surface drifted from the allowlist (SAFE-03): ...")
```

**Lazy-import shape to copy** (`store/__init__.py:122-131`) — import `langsmith` *inside* the
function, guarded, so naming the module does not pull the transitive tracer:

```python
async def default_store(db_path: Path | None = None) -> Store:
    """... Imported lazily so naming the interface does not pull the adapter/langchain stack."""
    from triagedesk.store.borrowed import open_borrowed_store
    return await open_borrowed_store(db_path or DOMAIN_DB_PATH)
```

**The hardening body** is dictated by `07-RESEARCH.md` Pitfall 2 (:425-435) and Summary 3 (:106-113):
pop `LANGSMITH_TRACING(_V2)`/`LANGCHAIN_TRACING(_V2)` + OTLP vars, call
`langsmith.utils.get_env_var.cache_clear()` (it is `@functools.lru_cache`), then assert
`langsmith.utils.tracing_is_enabled() is False`. `try/except ImportError` so it is safe if langsmith
is ever absent.

> **HARD CONSTRAINT (Pitfall 3, `test_safety_spine.py:157-184,228-232`):** the AST guard
> `test_graph_reads_no_credentials` scans **every** `graph/*.py` for `os.environ` / `getenv` /
> `.netrc`. Therefore the env logic MUST live in `observability/offline.py` (outside `graph/`), and
> `graph/build.py` may only import the span *context/writer* (root `triagedesk.observability`, which
> the network/credential guards do not flag). Do not put `harden_offline` in `graph/`.

---

### `src/triagedesk/store/audit.py` (MOD, model) — add `trace_id` to `AuditRecord`

**Analog:** itself — the ONE record shape (D7-06). **Additive only.**

**Current field list** (`store/audit.py:50-60`):

```python
    seq: int
    ts: datetime
    case_id: str = ""
    tool: str
    actor: Actor
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    role: str | None = None
    prev_hash: str
    hash: str = ""
```

**Add ONE defaulted line after `role`** (default → every existing constructor stays valid; D7-06):

```python
    role: str | None = None
    trace_id: str = ""            # NEW — additive; digest covers it (:72)
    prev_hash: str
```

**Do NOT touch `record_digest`** (`store/audit.py:63-72`) — it already hashes *every* field except
`hash`, so the new field is sealed automatically and `verify`/`reconcile` stay internally consistent:

```python
    return hash_value(record.model_dump(mode="json", exclude={"hash"}))
```

**`append` signatures that carry the new field** (`store/audit.py:134-158`): `fields` is a
`Mapping`, so no signature change is needed — the interceptor simply passes `"trace_id"` in `fields`.
The `**fields` splat at :153 already threads it through.

**Test that stays valid as-is** (`tests/test_audit_chain.py:72-86`): `AuditRecord(**common, ...)`
constructs directly; a defaulted field keeps it passing. The plan may *add* (not modify) an assertion
that `trace_id` survives the round-trip.

---

### `src/triagedesk/store/borrowed.py` (MOD, store adapter) — ⚠ THE 11-COLUMN PITFALL

**Analog:** itself — `ensure_schema` (:161-166), `append_audit_record` (:283-307),
`read_audit_records` (:309-330). This is the SINGLE highest-risk edit in the phase
(`07-RESEARCH.md` Pitfall 1, :411-423): the record shape and the SQL column list are **separate
sources of truth**, so widening one silently drops the field on the production store while the
in-memory double keeps passing.

**Four coordinated edits — all required:**

**(1) DDL** (`borrowed.py:85-98`) — add the column:

```python
_AUDIT_DDL = (
    f"CREATE TABLE IF NOT EXISTS {AUDIT_TABLE} ("
    "seq INTEGER PRIMARY KEY, "
    "ts TEXT NOT NULL, "
    "case_id TEXT NOT NULL, "
    "tool TEXT NOT NULL, "
    "actor TEXT NOT NULL, "
    "inputs TEXT NOT NULL, "
    "outputs TEXT NOT NULL, "
    "approved_by TEXT, "
    "role TEXT, "
    "trace_id TEXT NOT NULL DEFAULT '', "   # NEW
    "prev_hash TEXT NOT NULL, "
    "hash TEXT NOT NULL)"
)
```

**(2) Idempotent ALTER for pre-existing files** — copy the `ensure_schema` pattern (:161-166) and add
one statement (no migration framework exists; synthetic DBs are disposable, A3):

```python
    async def ensure_schema(self) -> None:
        """Create the case/queue and audit tables if absent, via the borrowed ``query`` tool."""
        await self._call(TOOL_QUERY, {"sql": _QUEUE_DDL})
        await self._call(TOOL_QUERY, {"sql": _CASES_DDL})
        await self._call(TOOL_QUERY, {"sql": _AUDIT_DDL})
        await self._call(TOOL_QUERY, {"sql": _AUDIT_HEAD_DDL})
        # NEW — widen a pre-existing audit table (idempotent; ignore "duplicate column").
        await self._call(TOOL_QUERY, {"sql": _AUDIT_TRACE_ID_MIGRATION})
```

**(3) INSERT column list + placeholders + values** (`borrowed.py:283-307`) — 11 → 12:

```python
                "sql": (
                    f"INSERT OR IGNORE INTO {AUDIT_TABLE} "
                    "(seq, ts, case_id, tool, actor, inputs, outputs, approved_by, role, "
                    "trace_id, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                "values": [
                    record.seq,
                    record.ts.isoformat(),
                    record.case_id,
                    record.tool,
                    record.actor,
                    json.dumps(record.inputs),
                    json.dumps(record.outputs),
                    record.approved_by,
                    record.role,
                    record.trace_id,          # NEW
                    record.prev_hash,
                    record.hash,
                ],
```

**(4) SELECT column list** (`borrowed.py:309-330`) — must read the new column or it comes back `""`:

```python
                    "sql": (
                        "SELECT seq, ts, case_id, tool, actor, inputs, outputs, "
                        "approved_by, role, trace_id, prev_hash, hash "
                        f"FROM {AUDIT_TABLE} ORDER BY seq"
                    )
```

**Warning sign to test for** (`07-RESEARCH.md` Pitfall 1): `read_audit_records()` returns records
whose `trace_id == ""` while the span stream has spans for that case; the SQL string still contains
exactly eleven placeholders. The plan MUST add a **borrowed-store** round-trip assertion (via the
`_FakeBorrowedTools` fake in `tests/test_borrowed_store.py:41-98`), not only `InMemoryStore`.

`tests/test_borrowed_store.py` only asserts the queue/cases DDL (:120-121), never the audit DDL or the
audit INSERT SQL → this change is safe.

---

### `src/triagedesk/store/memory.py` (MOD, store double) — mirror the column change

**Analog:** itself (`store/memory.py:100-110`). Because `AuditRecord` now carries `trace_id`, the
double needs **no code change** — it stores whole `AuditRecord` objects. This is the trap: the double
passes even when `borrowed.py` is broken, which is exactly why the borrowed round-trip test is
mandatory. Confirm the double is untouched (SRP), and use it as the fast inline test store.

---

### `src/triagedesk/mcp/server.py` (MOD, interceptor) — tool span + `trace_id` in the record

**Analog:** itself — `audited()` at `:88-154`. **Two additive edits; audit behaviour preserved
(D-18).**

**Edit A — `record()` gains the trace field** (`server.py:126-138`); the `append` call is the ONE
audit path and its `fields` mapping is where `trace_id` rides:

```python
            store = await _resolve_store()
            await append(
                store,
                {
                    "case_id": str(inputs.get("case_id") or ""),
                    "tool": tool_name,
                    "actor": "clinician" if approval else "agent",
                    "inputs": inputs,
                    "outputs": outputs,
                    "approved_by": approved_by,
                    "role": role,
                    "trace_id": current_trace_id(),     # NEW — additive field, D7-06
                },
            )
```

**Edit B — `wrapper()` opens a tool span around the call** (`server.py:140-152`). Note the span closes
on the exception path *before* `record(...)` runs, so a refused/failed commit is still both spanned
and audited exactly as today:

```python
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            trace_id = current_trace_id()
            try:
                with span("tool", tool_name, attributes={"trace_id": trace_id}):  # NEW
                    result = fn(*args, **kwargs)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as exc:  # noqa: BLE001 — the tool boundary is external
                await record(args, kwargs, None, f"{type(exc).__name__}: {exc}")
                raise
            await record(args, kwargs, result, None)
            return result
```

**Do NOT change** the refusal path or the actor/approver logic (`:119-125`); the interceptor's audit
behaviour is carried AUDIT-01 and must stay byte-equivalent apart from the new field.

---

### `src/triagedesk/graph/build.py` (MOD, composition root) — node spans via the add_node loop

**Analog:** itself — the node loop at `:170-171` (the ONLY wiring point):

```python
    assert_tool_allowlist(tools.keys())
    nodes = make_nodes(tools)
    graph: StateGraph = StateGraph(TriageState)
    for name in TRACER_NODES:
        graph.add_node(name, nodes[name])
```

**Replace only the loop body** with the wrapped callable (`07-RESEARCH.md` Pattern 2, :316-337):

```python
    for name in TRACER_NODES:
        graph.add_node(name, _spanned(name, nodes[name]))
```

**`_spanned` wrapper shape** — `functools.wraps` is mandatory (Pitfall 3: preserves `__name__`
for tracebacks and keeps LangGraph node identity); derive the trace id from the state so one case =
one trace across restart/replay (D7-05):

```python
def _spanned(name: str, fn: NodeFn) -> NodeFn:
    @functools.wraps(fn)
    async def wrapped(state: TriageState) -> Any:
        trace_id = case_id_for(str(state.get("raw_note") or "").strip())  # == derive_thread_id
        bind_trace(trace_id)
        with span("node", name):
            result = fn(state)
            return await result if inspect.isawaitable(result) else result
    return wrapped
```

**Imports allowed here:** `functools`, `inspect`, `graph.nodes.case_id_for`, and the span helpers from
`triagedesk.observability`. **Forbidden here** (AST guard, Pitfall 3): `os.environ`/`getenv`,
`.netrc`, any network client or non-local model provider, `langsmith`. Node bodies, edges, and the
topology are untouched. The trace-id import reuses the ONE derivation (`graph/nodes.py:83-90`) — never
a second hash.

---

### `src/triagedesk/llm/client.py` (MOD, model boundary) — model span around the one call

**Analog:** itself — `extract()` at `:73-113`, the `usage_sink` injection at `:23-28, 103-104`.

**Wrap the ONE `ollama.generate` call** (`client.py:96-102`) in a model span; attributes limited to
the model tag + token counts from `_response_usage` (`:58-70`). **No prompt/complaint text (D7-08,
Pitfall 6):**

```python
    with span("model", model, attributes={"tokens_in": tokens_in, "tokens_out": tokens_out}):
        response = ollama.generate(
            model=model,
            prompt=prompt,
            format=schema,   # grammar-constrained decoding
            think=False,     # REQUIRED for qwen3.5:4b — else `response` is empty
            options=OPTIONS,
        )
```

The span must be emitted **inside** `extract` so an offline run (model stubbed) emits **no** model
span. Hermetic test: monkeypatch `triagedesk.llm.client.ollama.generate` (the same seam
`tests/test_graph_durable.py:71-75` uses to stub `server_module.extract`).

---

### `src/triagedesk/replay.py` (NEW, read-only projection)

**Analogs:** `src/triagedesk/durable.py` (Phase 6) for saver/state handling + `evals/runner.py::_capture`
for reading graph channels. **No graph compile, no tool map (D7-10).**

**Saver handling to copy** (`durable.py:221-242` `resume_thread` + `graph/build.py:258-260`): open the
saver the same way, but read with `aget_tuple` instead of invoking:

```python
# Source: 07-RESEARCH Pattern 3 (:345-358) + graph/build.py:263-276 (_allowed_msgpack_modules)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from triagedesk.graph.build import _allowed_msgpack_modules

async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
    saver.serde = JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
    tup = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
    if tup is None:
        raise ReplayError(f"no checkpoint for thread_id {thread_id} in {db_path}")
    values = tup.checkpoint["channel_values"]   # approval / commit_result / handover / priority / case
```

**Channel-reading shape to copy** (`evals/runner.py::_capture:60-105`): read the graph's OWN channels
(`priority`, `commit_result`, `handover`, `escalation`, `recovery`, `second_look`) — never re-derive a
colour or re-score.

**Typed error to copy** (`durable.py:58-59`): `class DurableError(RuntimeError)` → create
`class ReplayError(RuntimeError)` with the same one-line docstring posture, raising naming the thread
id and the db file.

**Audit reader** — use the published seam `store.read_audit_records()` (D7-15), filtered by
`trace_id`. Resolve the store through the ONE seam like `demo/run.py::_run_durable` (:223-225):

```python
    resolved_store = store if store is not None else await server_module._resolve_store()
```

**What replay must NOT import** (Pitfall 4): `build_graph`, `checkpointed_graph`, `resume_paused`,
`load_graph_tools`, or anything that constructs a tool mapping. Both `await store.read_queue_rows()`
and `await store.read_audit_records()` are read-only projections (mirror `evals/runner.py` row-count
deltas at :173-190).

---

### `src/triagedesk/cli.py` (MOD, CLI) — `replay` subcommand

**Analog:** itself — the `resume` subparser (`cli.py:94-122`) and its dispatch branch
(`:150-181`). Copy the parser shape one-for-one (D7-12):

```python
    replay_parser = subcommands.add_parser(
        "replay", help="read-only reconstruction of a past case from checkpoint + stream"
    )
    replay_parser.add_argument("--thread-id", required=True, help="the content-derived thread id")
    replay_parser.add_argument("--db", default=None, help="checkpoint file (default: checkpoints.db)")
```

**Dispatch shape to copy** (`cli.py:150-181`): wrap in `try/except (DurableError, RuntimeError,
sqlite3.Error, ExceptionGroup)`, `print(str(exc), file=sys.stderr)`, `return 1`, and return `0` on
success. Register the `replay` branch exactly like the `resume` branch. Optionally call
`harden_offline()` at startup (D7-03).

---

### `tests/conftest.py` (MOD, test infra) — autouse sink redirect

**Analog:** itself — the autouse `injected_store` fixture (`conftest.py:86-97`):

```python
@pytest.fixture(autouse=True)
def injected_store(memory_store: RecordingStore) -> Iterator[RecordingStore]:
    server_module.set_store(memory_store)
    try:
        yield memory_store
    finally:
        server_module.set_store(None)
```

**Add ONE autouse sibling** that redirects the sink so no test writes `spans.jsonl` to the repo root
(Pitfall 5):

```python
@pytest.fixture(autouse=True)
def _spans_sink(tmp_path: Path) -> Iterator[None]:
    set_sink(tmp_path / "spans.jsonl")
    try:
        yield
    finally:
        set_sink(None)
```

No existing fixture changes. Reuse the shared `RecordingStore`/`InMemoryStore` (DRY).

---

### `.gitignore` (MOD, config) — ignore the sink

**Analog:** its own runtime-artefacts block:

```
# Runtime artefacts (kept out of history)
*.db
*.db-wal
*.db-shm
```

**Add** `spans.jsonl` (or `*.jsonl`) to that same block — do not create a second section.

---

### `tests/test_spans.py` (NEW, test) — span kinds + linkage + no-egress

**Analog:** `tests/test_audit_chain.py` (uses `memory_store`, `append`, asserts linkage) +
`tests/test_graph_durable.py` (stubs the model via `server_module.extract`).

**Setup pattern to copy** (`test_graph_durable.py:64-97`): monkeypatch the model seam, build real
tools, run the graph, assert on the store.

**Assertions to write** (`07-RESEARCH.md` Validation Map, :620-634):
- all three kinds land in one sink: `{tool, node, model} ⊆ {s["kind"] for s in spans}`;
- each span carries `trace_id` + `span_id` + `parent_id` + `kind` + start/end;
- the audit record for a real owned call carries the same `trace_id` as its tool span (the join);
- **no-egress:** after `harden_offline()`, `langsmith.utils.tracing_is_enabled() is False`;
- a model span carries **no** complaint/prompt text.

---

### `tests/test_replay.py` (NEW, test) — zero-write + no-model + outcome equality

**Analog:** `tests/test_durable_cli.py` (CLI dispatch + `injected_store` + spy pattern) +
`tests/test_graph_durable.py` (run a real case to a commit).

**Zero-write proof to copy** (`07-RESEARCH.md` :567-573; spy pattern from `test_durable_cli.py:74-101`):

```python
rows_before = len(await store.read_queue_rows())
commits_before = sum(r.tool == "commit_priority" for r in await store.read_audit_records())
out = replay_render(thread_id, db_path)                 # pure read; no graph, no tools
assert await store.read_queue_rows() == rows_before     # zero new rows
assert sum(r.tool == "commit_priority" for r in await store.read_audit_records()) == commits_before
assert recorded_colour in out                            # outcome equals the original
```

- **No-model:** monkeypatch `triagedesk.llm.client.extract` to raise; assert no raise + no new model
  spans (D7-16).
- **Read-only spy:** the `monkeypatch.setattr(..., spy)` pattern from `test_durable_cli.py:80` can
  assert no write-capable path is reached.
- **Absent thread:** assert a typed `ReplayError` naming the thread and db.
- **Per-run deltas, not absolute counts** (Pitfall 7): the shared-case beats share one trace id, so
  assert deltas.

---

## Shared Patterns

### One helper per concern (DRY, CONVENTIONS §1)
**Source:** `store/audit.py::append` (:134-158) · **Apply to:** `observability/spans.py` (`emit_span`),
`replay.py` (one projection)
The existing "one logging function; every tool call routes through it" rule is the template: the phase
adds exactly ONE span writer and ONE replay reader. Emit sites call `span(...)` and never build a span
dict inline (D7-04).

### One content-hash derivation (D7-05)
**Source:** `graph/nodes.py::case_id_for` (:83-90) → `hash_value`, re-exported as
`durable.derive_thread_id` (`durable.py:80-88`) · **Apply to:** `replay.py`, `graph/build.py`,
`mcp/server.py`
```python
def case_id_for(raw_note: str) -> str:
    """Derive a stable, content-addressed case id from the note (D-06)."""
    return hash_value({"raw_note": raw_note})[:16]
```
The trace id is `case_id_for(raw_note.strip())` — never a random uuid, never a second scheme.

### Injectable seam, default `None` (SOLID: D)
**Source:** `mcp/server.py:52-73` (`_store`/`set_store`/`_resolve_store`), `llm/client.py:23-28`
(`usage_sink`), `store/__init__.py:122-131` (lazy `default_store`) · **Apply to:** the sink path, the
trace context, `replay.py`'s store resolution
Every new external touchpoint is injected and defaulted so tests never launch a subprocess or a model.

### Typed error naming the offender
**Source:** `durable.py::DurableError` (:58-59) + its raise sites (:172-174, :201-207) · **Apply to:**
`replay.py::ReplayError`
Errors name the thread id and the db file so the failure is actionable in the CLI.

### Assert-at-startup (fail loudly)
**Source:** `graph/build.py::assert_tool_allowlist` (:70-85) · **Apply to:**
`observability/offline.py::harden_offline`
The no-egress property is *asserted* (`tracing_is_enabled() is False`), not assumed — the assertion is
the proof (D7-14).

### Lazy import of a heavy/optional dependency
**Source:** `store/__init__.py:129` (`from triagedesk.store.borrowed import open_borrowed_store`) ·
**Apply to:** `offline.py`'s `langsmith` import (guarded `try/except ImportError`)

---

## No Analog Found

Files with no close match in the codebase (planner should use `07-RESEARCH.md` patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/triagedesk/observability/offline.py` | config (guard) | transform | No env-hardening or tracer-neutralisation code exists; the *shape* borrows `assert_tool_allowlist` + lazy import, but the body comes entirely from RESEARCH Pitfall 2 / Summary 3. |
| `src/triagedesk/observability/context.py` | state/context utility | transform | No `contextvars` usage exists anywhere yet; only the *injectable-seam posture* maps to `mcp/server.py`'s `_store`. The contextvar mechanics come from RESEARCH Pattern 1. |

**Partial-match files (analog exists but only for part of the concern):**
- `observability/spans.py` — the "one writer" *shape* matches `store/audit.py`, but the *format* is
  append-only JSONL (no chained-in-DB analogue); use RESEARCH Pattern 1 for the encoding.
- `replay.py` — `durable.py` gives the saver handling and `evals/runner._capture` gives the channel
  reading, but no existing module does a *read-only checkpoint reconstruction*; use RESEARCH Pattern 3.

---

## Metadata

**Analog search scope:** `src/triagedesk/**` (store, mcp, graph, llm, evals, demo, durable, cli),
`tests/**` (audit, borrowed, durable, graph, safety-spine), `docs/**`, `.gitignore`, `scripts/**`.
**Files scanned:** ~20 read in full; grep-swept for emit sites, contextvars, env reads, and channel
reads.
**Git-tracked gate:** every analog path named above was verified with `git ls-files -- <path>` (all
non-empty → all tracked). No gitignored install/runtime mirror is referenced.
**Key constraints carried forward:** DRY + SOLID iron-clad (CONVENTIONS §1/§2); one writer per concern;
graph depends on the tool interface not implementations; `graph/` must stay free of env/credential
reads and network imports (safety-spine AST guard); the borrowed-store audit column list is the
11-column pitfall.
**Pattern extraction date:** 2026-10-12
