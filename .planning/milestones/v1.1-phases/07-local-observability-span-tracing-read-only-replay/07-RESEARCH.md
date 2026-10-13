# Phase 7: Local Observability — Span Tracing & Read-Only Replay - Research

**Researched:** 2026-10-12
**Domain:** Local append-only span tracing (stdlib JSONL) + content-addressed trace linkage + read-only LangGraph checkpoint reconstruction
**Confidence:** HIGH (every load-bearing claim verified against the installed source in `.venv` and by running the project's own code; two probe scripts and the project's own test suite)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Span emission surface & local sink**
- **D7-01:** Spans originate from the **existing** seams, not from a new framework integration: tool
  spans from the `@audited` interceptor (one span per owned tool call), node spans from a thin wrapper
  around the graph's node callables, model spans from the `llm/client` boundary. No LangChain callback
  handler machinery, no LangSmith exporter.
- **D7-02:** The sink is ONE append-only **JSONL** file written by ONE small module
  (`src/triagedesk/observability/spans.py`), one JSON object per line, no new dependency. The path is
  named in exactly one place and is overridable for tests.
- **D7-03:** Cloud tracing is explicitly disabled and asserted at startup — `LANGSMITH_TRACING` /
  `LANGCHAIN_TRACING_V2` / any OTLP endpoint unset or forced off — so the default LangChain/LangSmith
  transitive packages already present cannot export anything. The agent path stays offline.
- **D7-04:** There is exactly ONE span writer (`emit_span`); the three emit sites call it and never
  format a span themselves (DRY — the same rule as the one audit helper).

**trace_id linkage**
- **D7-05:** The `trace_id` is **content-derived**, reusing the existing `case_id_for(raw_note)`
  derivation as the trace root, so one case has exactly one trace across a restart and across replay —
  never a random uuid.
- **D7-06:** `trace_id` is a **first-class field on `AuditRecord`** (the record shape has exactly one
  owner, `store/audit.py`), not a key buried in `inputs`/`outputs`. Adding a field is additive; the
  record's canonical digest covers it because the digest hashes every field but `hash`.
- **D7-07:** Every span in the stream carries `trace_id` + `span_id` + `parent_id` + `kind`
  (`tool` | `node` | `model`) + start/end timestamps, so the stream is a reconstructable tree rather
  than an undifferentiated log.
- **D7-08:** Model spans are emitted through the same writer with **minimal** content — no prompt or
  completion echo beyond what the audit record already stores — so the local sink never becomes a second,
  uncontrolled copy of clinical text.

**Read-only replay**
- **D7-09:** Replay's input is the **checkpoint** (LangGraph state) plus the **audit/span stream**. It
  reconstructs the recorded outcome; it never re-runs the model and never re-invokes the graph.
- **D7-10:** Read-only is **structural, not conventional**: `replay.py` builds a view from stored data
  only and never constructs a tool mapping that contains `commit_priority` (or any write-capable tool),
  so no code path in replay can reach the gated commit.
- **D7-11:** Replay renders a reconstructed case view — suggested colour, target, citations, matched
  discriminators, the human decision and approver, and the span timeline — to stdout as text.
- **D7-12:** Replay is exposed as `triagedesk replay --thread-id <id> [--db PATH]`, reusing the durable
  helper to locate the checkpoint and the audit/span readers to rebuild the stream.

**Proof & guards**
- **D7-13:** The zero-write property is proven by a test that replays a **committed, gated** case and
  asserts zero new queue rows and zero new commits (the audit record count is unchanged).
- **D7-14:** The no-egress property is proven by a test asserting the local sink is written for a run and
  that no cloud tracer is active (the disabling from D7-03 holds) — the run stays hermetic.
- **D7-15:** Replay lives in `src/triagedesk/replay.py` — ONE home above `durable`/`store`, consuming
  their published seams rather than duplicating them.
- **D7-16:** A test asserts replay never calls the model (no Ollama call), by construction and by a
  spy/absence assertion.

### the agent's Discretion
- The exact span JSON keys and timestamp format; the file name of the sink.
- Whether the node-span wrapper is a decorator in `graph/nodes.py` or a wrapper applied in
  `graph/build.py` — either is acceptable as long as the node bodies stay single-purpose and the
  topology is unchanged.
- The precise stdout layout of the replay view.
- How tests inject a sink path (an argument, a module-level override, or an env var).

### Deferred Ideas (OUT OF SCOPE)
- Multi-agent / cross-service trace propagation (not needed for a single-process, local tool).
- Online eval, drift monitoring, or dashboards (AGENT-06).
- A vector MCP server for retrieval (MCP-02) — belongs to Phase 9's family.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-04 | Tool, node, and model spans are emitted from the **existing** audit interceptor and wrappers to a **local** exporter (no cloud/egress), a `trace_id` links spans to the audit record, and **replay is read-only** — it reconstructs from the checkpoint + audit/span stream and structurally cannot re-run the gated commit. | (1) The three exact intercept points are confirmed by reading the source: `mcp/server.py::audited` (`record()` closure at :105-138, `wrapper` at :140-152), the `graph/build.py` node loop (:170-171), and `llm/client.py::extract` (`ollama.generate` at :96). All three extensions are additive. (2) `AuditRecord` gains `trace_id: str = ""` additively, but the **borrowed store enumerates audit columns explicitly** (`store/borrowed.py:288-305`, `:316-318`) so a DB column + INSERT/SELECT change is required. (3) Tracing is enabled only when `LANGSMITH_TRACING(_V2)`/`LANGCHAIN_TRACING(_V2)` == `"true"`, and `get_env_var` is **lru_cached** — the hardening must clear that cache. (4) A finished thread's full state (incl. `approval`/`commit_result`/`handover`) is readable **directly from the checkpointer** via `aget_tuple` with the existing serde allowlist — no graph compile, no tool map, so replay is read-only by construction. |
</phase_requirements>

## Summary

Phase 7 is **instrumentation of existing seams plus one read-only projection**, not a new subsystem. Every
mechanism it needs already exists: the ONE audit interceptor (`mcp/server.py::audited`), the ONE
content-hash derivation (`graph/nodes.case_id_for`), the ONE durable saver
(`graph/build.checkpointed_graph`), and the ONE store seam (`mcp.server._resolve_store`). The phase
adds a single span writer, one trace context, one `trace_id` field, and one replay reader.

Four facts drive the plan, each verified against the installed source and by running the project's code:

1. **The three emit sites are exactly as CONTEXT states, and all three extensions are additive.** Tool
   spans attach inside `audited().decorate()`; node spans attach in the `build_graph` wiring loop
   (`graph/build.py:170-171`) without touching node bodies or the topology; model spans attach in
   `llm/client.py::extract` around the one `ollama.generate` call. None of the three edits changes the
   scorer, the citation helper, or the interceptor's audit behaviour.

2. **Adding `trace_id` to `AuditRecord` is additive for the chain but needs a DB column for the borrowed
   store.** `record_digest` hashes every field except `hash` (`store/audit.py:72`), so `verify`/`reconcile`
   stay internally consistent. But `store/borrowed.py` writes and reads the audit table with an
   **explicit 11-column list** — without a `trace_id` column, the field is silently dropped on the
   production store round-trip. No test asserts the audit record's field set or the audit DDL, so the
   schema widening is safe (the borrowed-store test only asserts the queue/cases DDL).

3. **Cloud tracing is one lru-cached env read away from egress — and this was observed.** `langsmith`
   enables tracing iff `get_env_var("TRACING_V2", default=get_env_var("TRACING"))` == `"true"` across the
   `LANGSMITH_`/`LANGCHAIN_` namespaces (`langsmith/utils.py:141-142`), and `get_env_var` is
   `@functools.lru_cache(maxsize=100)` (:420-421). During probing, setting `LANGCHAIN_TRACING_V2=true`
   made the graph attempt a real HTTPS POST to `api.smith.langchain.com/runs/multipart`. Because the
   read is cached, disabling must **pop the vars AND clear the cache**, and the assertion must call
   `tracing_is_enabled()` after both. The `opentelemetry` **SDK is not installed** (API only), so OTLP is
   inert; the langsmith vars are the whole exposure.

4. **Replay can be read-only by construction, more strongly than D7-10 requires.** A finished/committed
   thread's complete state — including `approval`, `commit_result` and `handover` — is returned by
   `AsyncSqliteSaver.aget_tuple(config)` (with the existing `JsonPlusSerializer` allowlist) **without
   compiling the graph at all**. Replay therefore constructs **no tool mapping whatsoever**, so it cannot
   call `commit_priority` (or any tool) even by future mistake. A paused thread returns
   `snapshot.next == ('approval_gate',)`; a finished thread has `pending_writes == 0` and the resumed-only
   channels present.

**Primary recommendation:** Add `observability/` (one span writer + one trace context + one offline
hardener, stdlib only), widen `AuditRecord` with `trace_id: str = ""` (+ the borrowed-store column),
thread the trace id from a contextvar into the interceptor's `append(...)`, wrap the tool call and the
model call in the one span context manager, wrap the graph nodes in `build_graph`, and build
`replay.py` on `AsyncSqliteSaver.aget_tuple` + the store's audit reader + the span reader — never on a
compiled graph.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Span capture at the tool boundary | **Existing audit seam (`mcp/server.py::audited`)** | Local observability writer | The interceptor already runs exactly once per owned tool call; emitting there keeps one event source (PITFALLS Pitfall 10). |
| Span capture at the node boundary | **Composition root (`graph/build.py`)** | Local observability writer | `build_graph` is the ONLY wiring point; wrapping in its node loop leaves node bodies and topology untouched. |
| Span capture at the model boundary | **Model wrapper (`llm/client.py::extract`)** | Local observability writer | `extract` is the ONE model boundary; the one `ollama.generate` call is the only thing to time. |
| Span sink + trace context | **Local observability module (`observability/`)** | — | One writer (`emit_span`) and one context (contextvars); stdlib only, so it sits below graph/llm/store and cannot create a cycle. |
| `trace_id` derivation | **Graph (`graph/nodes.case_id_for`)** | `durable.derive_thread_id`, replay | One content-addressed hash; the trace id equals the thread id so one case has one trace across restart/replay (D7-05). |
| `trace_id` on the audit record | **Audit shape owner (`store/audit.py`)** | `store/borrowed.py` column, interceptor | One record shape; the borrowed store must persist the new field to avoid a silent drop. |
| Read-only replay | **Application CLI layer (`replay.py`)** | Checkpointer reader (`aget_tuple`) + store audit reader | A projection over stored data; constructing no tool map makes the gated commit structurally unreachable (D7-10). |
| Offline hardening (no egress) | **Local observability module** | CLI startup | Neutralise the transitive tracer's env, clear its cached read, then assert inert. |

## Standard Stack

**No new dependencies.** Every library this phase needs is already pinned in `uv.lock` and installed in
`.venv`; the phase is in-repo wiring only (CONTEXT D7-02: "no new dependency").

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LangGraph | **1.2.14** (installed) | `AsyncSqliteSaver` checkpoint read for replay; `StateSnapshot` semantics | Project decision; the durable saver already exists (`graph/build.checkpointed_graph`). |
| `langgraph-checkpoint-sqlite` | **3.1.1** (installed) | `AsyncSqliteSaver.aget_tuple` / `alist` (replay's read path) | The same saver Phase 6 uses; no second persistence mechanism. |
| `langgraph-checkpoint` | **4.2.0** (installed, transitive) | `JsonPlusSerializer`, `allowed_msgpack_modules` | The serde allowlist the state read must reuse (`graph/build._allowed_msgpack_modules`). |
| Pydantic | **2.14.0** | `AuditRecord` field widening; span record validation if desired | The ONE schema source. |
| Python stdlib | **3.12.x** | `json`, `contextvars`, `datetime`, `pathlib`, `uuid` — the whole span writer/context/hardener | No third-party tracing library (D7-01/D7-02). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langsmith` | **0.14.5** (transitive) | Read-only introspected for the offline hardening (`get_env_var`, `tracing_is_enabled`) | Only in `observability/offline.py`, lazily imported, to disable and assert — never to export. |
| `opentelemetry-api` | **1.45.1** (transitive) | Present but **inert**: the SDK is NOT installed | Nothing to do; note in the security section that no exporter can be constructed. |
| pytest + pytest-asyncio | installed | The span/no-egress/zero-write proofs | `asyncio_mode = "auto"` per `pyproject.toml`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Node spans via a thin wrapper in `build_graph` | LangGraph `astream(stream_mode="updates")` / `GraphCallbackHandler` | These are supported local mechanisms that emit per-step events, but D7-01/D7-02 **lock the existing-seam approach** and forbid callback-handler machinery. Using `astream` would also change the invoke shape across every entry point. Do not. |
| Direct `aget_tuple` checkpoint read for replay | Compile a graph with a reduced tool map and use `aget_state` | `build_graph` calls `assert_tool_allowlist(tools.keys())`, which **requires** `commit_priority`; any reduced map raises. Compiling also constructs write-capable tools, which D7-10 forbids. Do not. |
| New `Store`/`AuditRecord` trace columns via a migration framework | An idempotent `ALTER TABLE ... ADD COLUMN` in `ensure_schema` | No migration framework exists and v1.0 data is synthetic/disposable; an idempotent ALTER (or deleting a stale `triage.db`) is the project-consistent choice. |
| A span `trace_id` derived from a random uuid | `case_id_for(raw_note)` | D7-05 forbids random; a random id would not survive a restart or join replay. |

**Installation:** none — no new packages.

**Version verification:** `langgraph 1.2.14`, `langgraph-checkpoint-sqlite 3.1.1`,
`langgraph-checkpoint 4.2.0`, `langsmith 0.14.5`, `opentelemetry-api 1.45.1` confirmed present under
`.venv/lib/python3.12/site-packages/`; `opentelemetry-sdk` confirmed **absent** (`ls | grep -i
opentelemetry` → only `opentelemetry` (API) and `opentelemetry_api-1.45.1.dist-info`).

## Package Legitimacy Audit

**No external packages are installed by this phase.** Every dependency it uses is already pinned in
`uv.lock` and present in `.venv`; no registry lookup or legitimacy check is required. None emitted.

## Architecture Patterns

### System Architecture Diagram

Data flow through the instrumentation (one trace per case), and the separate read-only replay path:

```
   nurse note ──► ingest ──► normalize ──► retrieve ──► score ──► verify ──► recheck
                    │           │            │           │          │          │
   ┌────────────────┴───────────┴────────────┴───────────┴──────────┴──────────┴──────────────┐
   │ node-span wrapper (graph/build.py: wraps each entry in TRACER_NODES)                     │
   │   on entry: trace_id := case_id_for(state.raw_note.strip())   (== thread_id, D7-05)      │
   │             bind_trace(trace_id); open node span; push span_id on the context stack       │
   │   on exit : close node span (duration)                                                   │
   └───────────────┬─────────────────────────────────────────────────────────────────────────┘
                   │ tools[...](...)  (in-process call to the audited owned tools)
                   ▼
   ┌────────────────────────────────────── mcp/server.py::audited ────────────────────────────┐
   │ wrapper():  with span(kind="tool", name=<tool>):  result = await fn(...)                  │
   │ record():   append(store, {..., "trace_id": current_trace_id()})   ← audit gains trace_id │
   │             → store/audit.py::append → AuditRecord(trace_id=...)  (D7-06)                 │
   └───────────────┬───────────────────────────────────────────────────────────────────────────┘
                   │ normalize_case → llm/client.py::extract
                   ▼
   ┌───────────────── llm/client.py::extract (the ONE model boundary) ────────────────────────┐
   │ with span(kind="model", name=DEFAULT_MODEL, attrs={tokens_in, tokens_out}):               │
   │     response = ollama.generate(...)      # local only; NO prompt/complaint in the span     │
   └───────────────┬───────────────────────────────────────────────────────────────────────────┘
                   │ every emit site calls the ONE writer
                   ▼
   ┌──────────────────────────── observability/spans.py ──────────────────────────────────────┐
   │ emit_span(...)  → one JSON object per line → SPANS_PATH ("spans.jsonl", append-only)       │
   │ trace_id + span_id + parent_id(-stack) + kind + name + started/ended + duration_ms + attrs │
   └───────────────────────────────────────────────────────────────────────────────────────────┘

   read-only replay (a SEPARATE process path; never touches the graph or any tool):
   checkpoints.db ──aget_tuple(config)──► checkpoint["channel_values"]  (approval/commit_result/
                                          handover/priority — no graph compiled)
   triage.db (audit) ──store.read_audit_records()──► records filtered by trace_id
   spans.jsonl ───────spans reader──► span timeline filtered by trace_id
                    │
                    ▼
            replay.py builds a VIEW (no tool mapping) ──► stdout text (D7-11)
```

The primary use case traces left-to-right: a note enters, every node/tool/model call appends one span to
one local file, and each audit record carries the same `trace_id`. Replay is a **different arrow** that
reads only stored data.

### Recommended Project Structure

```
src/triagedesk/
├── observability/                 # NEW package (stdlib only)
│   ├── __init__.py
│   ├── spans.py                   # the ONE writer: emit_span + SPANS_PATH + the span() ctx mgr
│   ├── context.py                 # trace_id + span-stack contextvars (bind_trace/current_trace_id)
│   └── offline.py                 # harden_offline(): neutralise the tracer env + assert inert
├── replay.py                      # NEW: read-only reconstruction (checkpoint + audit + spans)
├── store/
│   ├── audit.py                   # MOD: AuditRecord gains `trace_id: str = ""`
│   └── borrowed.py                # MOD: audit DDL column + INSERT/SELECT + idempotent ALTER
├── mcp/server.py                  # MOD: audited wrapper opens a tool span; record() adds trace_id
├── graph/build.py                 # MOD: wrap each node in the span wrapper at add_node
├── llm/client.py                  # MOD: extract() opens a model span around ollama.generate
└── cli.py                         # MOD: register the `replay` subcommand
tests/
├── conftest.py                    # MOD: autouse fixture redirects SPANS_PATH to tmp_path
├── test_observability.py          # NEW: 3 span kinds + no-egress proof (Wave 0)
└── test_replay_read_only.py       # NEW: zero rows / zero commits / no model / outcome equals (Wave 0)
.gitignore                         # MOD: ignore spans.jsonl
```

### Pattern 1: The ONE span writer + the ONE span context manager

**What:** `observability/spans.py` owns the file path, the JSON encoding, and the ids/timestamps.
Emit sites call a context manager (`span(kind, name, attributes=...)`) that times the block, resolves the
parent from a contextvar stack, and calls `emit_span(...)` once on exit.

**When to use:** at every one of the three seams — never inline a span dict at a call site (D7-04).

**Example (shape, not a copy):**
```python
# Source: design derived from graph/nodes.py:83-90 (case_id_for) + mcp/server.py:105-152
import contextvars, json, time, uuid
from datetime import UTC, datetime
from pathlib import Path

SPANS_PATH = Path("spans.jsonl")          # named ONCE (D7-02)
_sink: contextvars.ContextVar[Path | None] = contextvars.ContextVar("spans_sink", default=None)
_trace: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_stack: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar("span_stack", default=())

def set_sink(path: Path | None) -> None:   # test override (discretion)
    _sink.set(path)

def bind_trace(trace_id: str) -> None:
    _trace.set(trace_id)

def current_trace_id() -> str:
    return _trace.get()

def emit_span(*, trace_id, span_id, parent_id, kind, name, started, ended,
              duration_ms, attributes=None) -> None:
    line = {"trace_id": trace_id, "span_id": span_id, "parent_id": parent_id,
            "kind": kind, "name": name, "started": started, "ended": ended,
            "duration_ms": duration_ms, "attributes": attributes or {}}
    path = _sink.get() or SPANS_PATH
    with path.open("a", encoding="utf-8") as fh:      # append-only; local; no network
        fh.write(json.dumps(line, default=str, sort_keys=True) + "\n")

@contextlib.contextmanager
def span(kind: str, name: str, attributes: dict | None = None):
    parent = _stack.get()[-1] if _stack.get() else None
    span_id = uuid.uuid4().hex
    started, t0 = datetime.now(UTC).isoformat(), time.perf_counter()
    token = _stack.set(_stack.get() + (span_id,))
    try:
        yield
    finally:
        _stack.reset(token)
        emit_span(trace_id=current_trace_id(), span_id=span_id, parent_id=parent,
                  kind=kind, name=name, started=started, ended=datetime.now(UTC).isoformat(),
                  duration_ms=(time.perf_counter() - t0) * 1000.0, attributes=attributes)
```

`contextvars` work correctly under `asyncio` tasks and are set per-task, so a span opened inside a node
does not leak into a concurrent run. The `_sink` contextvar (rather than only a module global) makes the
test override safe under pytest-asyncio; a module-global default remains for production.

### Pattern 2: Node spans without touching node bodies or the topology

**What:** wrap the callable at the composition root, in the existing node loop:
```python
# Source: graph/build.py:170-171 (the current loop)
for name in TRACER_NODES:
    graph.add_node(name, _spanned(name, nodes[name]))
```
**When to use:** the single place graph nodes are registered. `_spanned` returns a
`functools.wraps` wrapper that derives the trace id from the state and opens a `kind="node"` span:
```python
def _spanned(name: str, fn: NodeFn) -> NodeFn:
    @functools.wraps(fn)
    async def wrapped(state: TriageState) -> Any:
        trace_id = case_id_for(str(state.get("raw_note") or "").strip())  # == durable.derive_thread_id
        bind_trace(trace_id)
        with span("node", name):
            result = fn(state)
            return await result if inspect.isawaitable(result) else result
    return wrapped
```
`add_node(name, action)` passes the node name explicitly, so replacing the callable is transparent to
LangGraph; `functools.wraps` preserves `__name__` for tracebacks. The node bodies and the edges are
unchanged.

### Pattern 3: Read-only replay from the checkpointer, with no graph compiled

**What:** read the latest checkpoint for the thread via the saver, deserialize with the SAME allowlist the
durable path uses, and render a view. No `build_graph`, no tool map, no `ainvoke`.
**When to use:** `triagedesk replay` and its test.
**Example:**
```python
# Source: langgraph/checkpoint/sqlite/aio.py:346-... (aget_tuple) + graph/build.py:263-276
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from triagedesk.graph.build import _allowed_msgpack_modules

async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
    saver.serde = JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
    tup = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
    if tup is None:
        raise ReplayError(f"no checkpoint for thread_id {thread_id} in {db_path}")
    values = tup.checkpoint["channel_values"]      # approval / commit_result / handover / priority / case
    history = [t async for t in saver.alist({"configurable": {"thread_id": thread_id}})]
```
Verified: a **finished** thread returns `channel_values` including `approval`, `commit_result`,
`handover`, `priority`, `case`, `raw_note`, `matched_ids`, `second_look`, and `pending_writes == 0`,
with **11** checkpoints in `alist` history; an **absent** thread returns `None`. A paused thread read
through a compiled graph showed `next == ('approval_gate',)`.

### Anti-Patterns to Avoid
- **Emitting spans from a second path beside the audit.** PITFALLS Pitfall 10: the trace must be a
  *derived view* of the one interceptor, not a parallel log with its own truth.
- **Putting the complaint text / prompt / completion into span attributes.** D7-08 + Pitfall 10(b):
  keeps the sink from becoming an uncontrolled second copy of clinical text (and the egress risk if a
  future change ever routes it off-machine).
- **Reading the checkpoint by compiling the graph.** Fails `assert_tool_allowlist` without a
  `commit_priority` tool, and constructs write-capable tools — both forbid the read-only construction.
- **A conditional "if replay: skip commit" branch inside `commit`.** PITFALLS Pitfall 14: the OCP rule
  rejects editing the gate; read-only must come from the *absence* of a tool map, not a flag.
- **A random `trace_id` or a span-only id.** D7-05: one case, one trace, across restart and replay.
- **Relying on env vars alone to disable tracing without clearing `get_env_var`'s lru_cache.** A stale
  cached `"true"` re-enables the tracer within the same process (observed).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content-addressed case/trace identity | A new hash or uuid scheme | `graph/nodes.case_id_for` (`core.hashing.hash_value`) | One derivation; deterministic; recomputable by hand (D7-05). |
| Locating a past run's state | Parsing the SQLite `checkpoints` blob by hand | `AsyncSqliteSaver.aget_tuple` + `JsonPlusSerializer(allowed_msgpack_modules=...)` | Versioned, deserializes typed contracts; the allowlist is the same ONE list Phase 6 uses. |
| Deserializing custom state contracts | `allowed_msgpack_modules=True` | `graph/build._allowed_msgpack_modules()` | One derived allowlist; `True` would deserialize arbitrary types from a tampered checkpoint. |
| Enabling/disabling the transitive tracer | A hand-rolled network guard or monkeypatching `LangChainTracer` | Neutralise the documented env + `get_env_var.cache_clear()` + assert `langsmith.utils.tracing_is_enabled()` | Matches how the library actually decides to trace; the assertion is the proof. |
| Append-only structured local logging | `logging`/`json.dumps` per call site | The one `emit_span` writer | D7-04 DRY; one file, one format, one path constant. |
| Reading the audit stream | A second query path or file | `store.read_audit_records()` (the published audit seam) | One audit source (D7-15). |

**Key insight:** the entire phase is *wiring + one projection*. The only genuinely new runtime behaviour
is "append a JSON line and read a checkpoint back" — both stdlib/library primitives, no framework.

## Runtime State Inventory

> This is **not** a rename/refactor phase, but it **widens a persisted schema** and **adds a runtime
> file**, both of which have a stored-state dimension. Categories with nothing are stated explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | The borrowed audit table (`audit`) has no `trace_id` column; records already written by a v1.0/Phase-6 run carry an 11-column row and a `hash` sealed over 11 fields. After the change, `AuditRecord` carries 12 fields, so `record_digest` of an old row (read back with `trace_id=""`) no longer matches its stored `hash` → `verify()` reports a break on legacy rows. | **Schema widening + no data migration.** Add the column + an idempotent `ALTER TABLE ... ADD COLUMN` in `ensure_schema`; document that a stale local `triage.db` must be deleted before a durable demo (synthetic, disposable — same posture Phase 6 took for the key-scheme change). |
| Live service config | None — verified: the audit and queue live in the local `triage.db` reached through the borrowed MCP; no external service holds the record. | None. |
| OS-registered state | None — verified: no scheduler/pm2/systemd/launchd registration references the audit, spans, or `thread_id`. | None. |
| Secrets/env vars | The **transitive tracer env** (`LANGSMITH_TRACING`, `LANGSMITH_TRACING_V2`, `LANGCHAIN_TRACING`, `LANGCHAIN_TRACING_V2`, and the OTLP/`OTEL_ENABLED` family). These are *not* project-owned secrets but they decide whether the process egresses. | Neutralise at startup (`harden_offline`) + clear `get_env_var`'s cache; assert `tracing_is_enabled() is False`. |
| Build artifacts | A new runtime artefact `spans.jsonl` at the repo root (append-only). Set `*.jsonl`/`spans.jsonl` in `.gitignore`. `checkpoints.db` / `triage.db` are already gitignored (`*.db`). | Add the `.gitignore` entry; tests redirect the sink to `tmp_path`. |

**Canonical question — after every file is updated, what runtime system still holds the old shape?**
Answer: only a *pre-existing local* `triage.db` audit table (synthetic, disposable) and a *pre-existing*
`spans.jsonl` (none today). Neither needs a migration; both are deleted or regenerated.

## Common Pitfalls

### Pitfall 1: `trace_id` silently dropped by the borrowed store
**What goes wrong:** `AuditRecord` gains the field, the interceptor passes it, but the borrowed store's
`append_audit_record` writes an explicit 11-column list and `read_audit_records` selects those same 11
columns — so `trace_id` is written nowhere and read back as the default `""`. Every audit record appears
to carry an empty trace id, and criterion 2 fails on the production store (not on the in-memory double).
**Why it happens:** the record shape and the SQL column list are separate sources of truth; widening one
does not widen the other.
**How to avoid:** add `trace_id` to `_AUDIT_DDL`, to the `INSERT` column list + values, and to the
`SELECT`; add an idempotent `ALTER TABLE audit ADD COLUMN trace_id TEXT NOT NULL DEFAULT ''` in
`ensure_schema` for pre-existing files. Assert the round-trip on the **borrowed** store (via the fake
tool set), not only on `InMemoryStore`.
**Warning signs:** `read_audit_records()` returns records whose `trace_id == ""` while the span stream has
spans for that case; the SQL string still contains exactly eleven placeholders.

### Pitfall 2: Cloud tracing re-enabled by a cached env read
**What goes wrong:** the hardener pops the env vars, but `langsmith.utils.get_env_var` is
`@functools.lru_cache(maxsize=100)` and already returned `"true"` earlier in the process, so
`tracing_is_enabled()` stays `True` and the tracer POSTs to `api.smith.langchain.com`.
**Why it happens:** env reads are cached process-wide; a pop after the first read is invisible.
**How to avoid:** `harden_offline()` must pop **and** call `get_env_var.cache_clear()` (lazily imported,
guarded by `try/except ImportError`), then assert `tracing_is_enabled() is False`. Belt-and-braces: set
`langsmith._internal._context._GLOBAL_TRACING_ENABLED = False` (the process-wide override `tracing_is_enabled`
checks before the env) — note it is private, so treat it as optional hardening.
**Warning signs:** a network attempt to `api.smith.langchain.com` in a test (observed in probing when
`LANGCHAIN_TRACING_V2=true`); `tracing_is_enabled()` returning `True`/`"local"`.

### Pitfall 3: Node wrapper breaks LangGraph node identity or the purity guards
**What goes wrong:** a wrapper that does not `functools.wraps` the node, or that reads env/credentials, or
that is applied by editing node bodies, trips a guard or changes graph behaviour.
**Why it happens:** `graph/` has an AST guard (`tests/test_safety_spine.py::test_graph_reads_no_credentials`,
`test_graph_imports_no_external_network_client_or_model_provider`) and cannot import `langsmith`/`httpx`;
the purity suite scans `_make_score` for model refs.
**How to avoid:** keep the env logic in `observability/`, not `graph/`; import only the observability
context/writer into `graph/build.py`; use `functools.wraps`; do not touch `_make_score`. Importing
`triagedesk.observability` is fine (its root is `triagedesk`, not a flagged network/model provider).
**Warning signs:** `test_graph_reads_no_credentials` or `test_graph_imports_no_external_network_client_or_model_provider`
fails; `snapshot.next` changes; a node appears under a different name.

### Pitfall 4: Replay re-runs work by calling the graph entry point
**What goes wrong:** replay calls `durable.resume_paused`/`graph.ainvoke` "to get the state", which requeues
the gated commit and (with any future key change) writes a second queue row — the exact PITFALLS Pitfall 14
failure.
**How to avoid:** read `aget_tuple` (no graph) and render from stored channels; construct **no** tool map.
Assert zero new rows and zero `commit_priority` records after replay.
**Warning signs:** `replay.py` imports `build_graph`/`checkpointed_graph`/`resume_paused`; the test's row
count grows.

### Pitfall 5: The span sink pollutes the repo and the test run
**What goes wrong:** with a default `SPANS_PATH = Path("spans.jsonl")`, every test and every demo run
appends to a repo-root file, and it becomes an untracked artefact that appears during the deadline clone.
**How to avoid:** an autouse fixture in `conftest.py` that `set_sink(tmp_path / "spans.jsonl")` for each
test; add `spans.jsonl` to `.gitignore`. Production/CLI keeps the repo-root default.
**Warning signs:** a `spans.jsonl` appears at the repo root after `uv run pytest`.

### Pitfall 6: Model span emitted when no model ran (or containing the note)
**What goes wrong:** a model span is emitted unconditionally, or it includes the note/prompt text.
**Why it happens:** `extract` is the model boundary, but in offline mode the tool is stubbed and never
calls it; and the note is right there in scope.
**How to avoid:** emit the model span **inside** `extract` around the one `ollama.generate` call, with
attributes limited to the model tag and token counts (from `_response_usage`). A hermetic model-span test
monkeypatches `triagedesk.llm.client.ollama.generate` (as `scripts/spike_model.py` does) so no model is
launched.
**Warning signs:** a span whose attributes contain the complaint string; a model span in an offline run.

### Pitfall 7: The durable demo's two-beat shared case collides on `trace_id`
**What goes wrong:** because `trace_id == case_id_for(note)` and the `escalation`/`refusal` beats share
E-02, both land on one trace id (and one durable thread).
**Why it happens:** content-addressed identity by design (D7-05).
**How to avoid:** this is already resolved for the durable path (one beat per invocation, CONTEXT D6-08);
for spans, the consequence is only that the two beats share one trace — acceptable and documented, not a
bug. The zero-write/outcome tests must therefore assert **per-run** row/commit deltas, not absolute counts
across the whole storyboard.
**Warning signs:** a test asserting `len(trace_spans) == N` across a multi-beat run.

## Code Examples

### Reuse the ONE content derivation for the trace root
```python
# Source: src/triagedesk/graph/nodes.py:83-90 (verbatim body)
def case_id_for(raw_note: str) -> str:
    """Derive a stable, content-addressed case id from the note (D-06). ..."""
    return hash_value({"raw_note": raw_note})[:16]
```
The trace root is `case_id_for(raw_note.strip())` — the identical value
`durable.derive_thread_id` produces (`src/triagedesk/durable.py:80-88`). Replay derives the same value
from the thread id it is given (they are the same string), so no second scheme is introduced.

### Add the field additively (the record shape owner)
```python
# Source: src/triagedesk/store/audit.py:50-60 (current field order) — add ONE line after `role`
    seq: int
    ts: datetime
    case_id: str = ""
    tool: str
    actor: Actor
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    role: str | None = None
    trace_id: str = ""            # NEW — additive; digest covers it (:72)
    prev_hash: str
    hash: str = ""
```
`record_digest` is unchanged — `hash_value(record.model_dump(mode="json", exclude={"hash"}))`
(`src/triagedesk/store/audit.py:72`) hashes every field, so `trace_id` is sealed automatically and
`verify`/`reconcile` stay correct because they recompute from the same field set.

### The interceptor extension (additive; audit behaviour preserved)
```python
# Source: src/triagedesk/mcp/server.py:105-152 (current structure) — two additive edits
async def record(args, kwargs, result, error):
    ...
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

@functools.wraps(fn)
async def wrapper(*args, **kwargs):
    trace_id = current_trace_id()
    try:
        with span("tool", tool_name, attributes={"trace_id": trace_id}):  # NEW — timing + one span
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
    except Exception as exc:
        await record(args, kwargs, None, f"{type(exc).__name__}: {exc}")
        raise
    await record(args, kwargs, result, None)
    return result
```
The `record()` closure still appends exactly one chained record per call with unchanged fields plus
`trace_id`; the refusal path is untouched (the span closes on the exception, then `record` runs).

### Read-only replay: the state source and the assertions
```python
# Source: probe /tmp/opencode/p7_probe4.py (verified) + langgraph/checkpoint/sqlite/aio.py:346
async def read_recorded(thread_id: str, db_path: Path) -> dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        saver.serde = JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
        tup = await saver.aget_tuple(config)
        if tup is None:
            raise ReplayError(f"no checkpoint for thread_id {thread_id} in {db_path}")
        return dict(tup.checkpoint["channel_values"])   # approval/commit_result/handover/priority/case

# The zero-write proof (test shape):
rows_before = len(await store.read_queue_rows())
commits_before = sum(r.tool == "commit_priority" for r in await store.read_audit_records())
out = replay_render(thread_id, db_path)                 # pure read; no graph, no tools
assert await store.read_queue_rows() == rows_before     # zero new rows
assert sum(r.tool == "commit_priority" for r in await store.read_audit_records()) == commits_before
assert recorded_colour in out                            # outcome equals the original
```
`commit_priority` is never *called* because replay builds no tool mapping — there is no code path from
`replay.py` to any tool.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSONL audit only; no spans (`STATUS.md`: "genuine gap") | One local spans JSONL linked to the audit by a first-class `trace_id` | This phase (v1.1) | The agent path becomes inspectable without any egress. |
| Replay = "run it again to watch" (the PITFALLS P14 trap) | Replay = a projection over the checkpoint + audit/span stream | This phase | The gated commit is structurally unreachable from replay. |
| Blanket "unset LANGCHAIN_TRACING_V2" hygiene | Explicit, asserted, cache-cleared neutralisation of the tracer env | This phase | The no-egress property is provable, not assumed. |

**Deprecated/outdated:**
- Treating `langsmith`/`opentelemetry` as "installed but unused" — they are enabled by an env read, so
  "inert" must be *asserted*, not assumed.
- Compiling the graph merely to read a checkpoint — `aget_tuple` is the supported, read-only surface.

## Test Churn — the Exact Blast Radius

Baseline confirmed: **`uv run pytest -q` → 255 passed in 7.35s** (`.venv`, Python 3.12). The changes below
are the exhaustive set gathered by reading every test that touches audit, graph, store, demo or CLI.

### Production changes (must land together)
| File | Change |
|------|--------|
| `src/triagedesk/observability/__init__.py`, `spans.py`, `context.py`, `offline.py` | NEW package: one writer, one context, one hardener (stdlib only). |
| `src/triagedesk/store/audit.py:50-60` | Add `trace_id: str = ""` to `AuditRecord` (after `role`). |
| `src/triagedesk/store/borrowed.py:85-98, 288-305, 316-318` | Audit DDL + INSERT columns/values + SELECT gain `trace_id`; idempotent `ALTER TABLE` in `ensure_schema` (:161-166). |
| `src/triagedesk/mcp/server.py:105-152` | `record()` adds `"trace_id": current_trace_id()`; `wrapper()` opens a `tool` span around `fn(...)`. |
| `src/triagedesk/graph/build.py:170-171` | `graph.add_node(name, _spanned(name, nodes[name]))` (node spans). |
| `src/triagedesk/llm/client.py:96-104` | Wrap `ollama.generate` in a `model` span (minimal attributes). |
| `src/triagedesk/replay.py` | NEW: read-only reconstruction (no graph compile). |
| `src/triagedesk/cli.py:32-122, 125-182` | Register the `replay` subcommand + dispatch; optionally call `harden_offline()`. |
| `.gitignore` | Ignore `spans.jsonl` (or `*.jsonl`). |

### Existing tests — expected disposition
| File / test | Why it is touched | Disposition |
|-------------|-------------------|-------------|
| `tests/conftest.py` | Every graph/tool test now emits spans; the sink must not land at the repo root. | **ADD** an autouse `set_sink(tmp_path/"spans.jsonl")` fixture. No existing fixture changes. |
| `tests/test_audit_chain.py:83-84` (`AuditRecord(**common, ...)`) | Constructs a record directly; a defaulted field keeps it valid. | **UNAFFECTED** (passes as-is). Optionally **ADD** an assertion that the interceptor carries `trace_id` (`test_every_tool_call_appends_exactly_one_chained_record`, :226-260). |
| `tests/test_borrowed_store.py` | Asserts only the queue/cases DDL (`:120-121`), never the audit DDL or the audit INSERT SQL. | **UNAFFECTED**. Optionally **ADD** an audit round-trip test (borrowed fake → `trace_id` survives). |
| `tests/test_graph_durable.py` | Runs real tools/graph; now also writes spans (redirected). | **UNAFFECTED** (asserts per-tool audit counts == 1; the `trace_id` field does not change counts). |
| `tests/test_durable_cli.py`, `test_demo.py`, `test_demo_runbook.py`, `test_graph_tracer.py`, `test_graph_purity.py`, `test_graph_recheck.py`, `test_graph_recovery.py`, `test_safety_spine.py`, `test_purity.py` | Run the graph or scan `graph/`; the wrapper and span imports must stay within the guards. | **UNAFFECTED** if the wrapper uses `functools.wraps` and no env/credential read lands in `graph/`. |
| `tests/test_mcp_tools.py`, `test_mcp_server.py` | Call owned tools in-process; spans are emitted (redirected). | **UNAFFECTED**. |
| `tests/test_eval_*.py` | Run the harness; spans emitted (redirected); report shape unchanged (provenance does not capture env — `evals/report.py:37-45`). | **UNAFFECTED**. |

### New tests required (Wave 0)
- `tests/test_observability.py`
  - all three span kinds land in one sink for one run (`{tool, node, model}` ⊆ kinds);
  - each span carries `trace_id` + `span_id` + `parent_id` + `kind` + start/end;
  - the audit record for a real owned call carries the same `trace_id` as its tool span (the join);
  - **no-egress**: after `harden_offline()`, `langsmith.utils.tracing_is_enabled()` is `False`, with the
    tracing env vars popped and `get_env_var.cache_clear()` applied;
  - a model span is emitted with **no** complaint/prompt text in its attributes.
- `tests/test_replay_read_only.py`
  - replay a committed, gated case adds **zero** queue rows and **zero** `commit_priority` records;
  - replay never calls the model (monkeypatch `triagedesk.llm.client.extract` to raise; assert no raise
    and no new model spans);
  - the replayed colour/target/citations equal the recorded ones (outcome equality);
  - an absent thread raises a typed `ReplayError` naming the thread and the db.
- A CLI test that `replay` parses and dispatches (mirroring `test_durable_cli.py`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The four langsmith vars (`LANGSMITH_TRACING`, `LANGSMITH_TRACING_V2`, `LANGCHAIN_TRACING`, `LANGCHAIN_TRACING_V2`) plus `get_env_var.cache_clear()` fully neutralise tracing; no other env var re-enables it. | Summary 3, Pitfalls 2 | A residual egress path could survive the hardening; mitigate by asserting `tracing_is_enabled() is False` (the assertion is the proof) and optionally the `_GLOBAL_TRACING_ENABLED=False` override. |
| A2 | OTLP is inert because only `opentelemetry-api` is installed (no SDK). | Standard Stack, Security | If a future phase adds the SDK, OTLP could become constructible; currently no exporter can be built. |
| A3 | Widening `AuditRecord` requires a borrowed-store column; pre-existing `triage.db` is disposable (delete, no migration). | Pitfalls 1, Runtime State Inventory | A stale `triage.db` would fail `verify` after the change; the plan must document deleting it (or the idempotent ALTER covers it structurally). |
| A4 | Reading the checkpoint with `aget_tuple` (no graph compile) is an acceptable reading of D7-10 — it is *stronger* than "no `commit_priority` in a tool map". | Summary 4, Pattern 3 | If a reviewer insists on a compiled-but-reduced graph, it raises `assert_tool_allowlist`; direct read is the only viable read-only construction. |
| A5 | The default sink path being `spans.jsonl` at the repo root is acceptable; tests always redirect it. | Pitfall 5, Discretion | A repo-root artefact appears in a manual run — gitignored, and consistent with `checkpoints.db`. |
| A6 | `_spanned` computed over `state["raw_note"]` (stripped) equals `durable.derive_thread_id` for every node, including `ingest`. | Pattern 2 | If a node runs with no `raw_note` in state, the trace id would be `case_id_for("")`; assert in a test that the node span's `trace_id` equals the thread id. |

**If this table is empty:** N/A — six assumptions above need confirmation (A1/A3/A5 are the material ones).

## Open Questions

1. **Where does the `trace_id` context get bound — the node wrapper, or each entry point?**
   - What we know: the node wrapper is the only place that always sees `state["raw_note"]` and re-runs on
     resume; it covers every entry point (CLI, demo, eval, resume) with one edit.
   - What's unclear: whether the planner prefers the entry points to bind it explicitly (touching four
     call sites) instead.
   - Recommendation: bind in the node wrapper (one place, cannot be forgotten); the entry points need no
     change. Flag as the plan's DRY rationale.

2. **Does replay read audit records from the store (launching the borrowed server) or only the spans?**
   - What we know: D7-09 says checkpoint **plus** audit/span stream, so the audit reader is required; the
     store seam defaults to the borrowed `npx mcp-sqlite` (as `resume` already does).
   - What's unclear: whether `--db` should also name the domain store, or default to `DOMAIN_DB_PATH`.
   - Recommendation: resolve the audit store through the ONE seam (`server_module._resolve_store()`,
     exactly like `_run_durable`), default `triage.db`; tests inject the in-memory store. No new flag
     unless a reviewer asks (discretion).

3. **Exact span JSON keys, timestamp format and stdout layout** (explicit discretion).
   - Recommendation: ISO-8601 UTC `started`/`ended`, `duration_ms` float, `attributes` object; replay
     prints the colour, target, citations, matched ids, decision/approver and a one-line-per-span
     timeline. Keep it text-only (D6-15 posture: no `--json`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (`.venv`) | All | ✓ | 3.12.x | — (pinned via uv). |
| `langgraph` / `langgraph-checkpoint-sqlite` | Durable checkpoint read for replay | ✓ | 1.2.14 / 3.1.1 | — |
| `langsmith` (transitive) | Offline hardening (introspection only) | ✓ | 0.14.5 | Guard the import; if absent, popping the env is still a no-op-safe hardening. |
| `opentelemetry-api` (transitive) | None (inert) | ✓ (API only) | 1.45.1 | SDK not installed → no exporter constructible. |
| Node / npx | borrowed SQLite MCP for the replay CLI / durable demo | ✓ | node 22.14.0 | In-memory store in tests; spans/checkpoint reads do not need it. |
| Ollama | a real model span | ✓ | 0.30.6 | Hermetic tests monkeypatch `ollama.generate`; no model needed. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** the borrowed `npx mcp-sqlite` (first-run network fetch) — the
default hermetic demo, all tests, and the checkpoint/span reads avoid it.

## Validation Architecture

> `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` → Nyquist validation is disabled, so no `*-VALIDATION.md` is expected for this phase.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio (`asyncio_mode = "auto"`, `pyproject.toml:35-37`) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `uv run pytest tests/test_observability.py tests/test_replay_read_only.py -q` |
| Full suite command | `uv run pytest -q` (baseline 255 passing) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| AGENT-04 (SC1) | tool+node+model spans written locally, no egress | unit | `uv run pytest tests/test_observability.py -q` | ❌ Wave 0 |
| AGENT-04 (SC2) | audit record carries `trace_id` linking to its spans | unit/integration | `uv run pytest tests/test_observability.py::test_audit_trace_id_links_to_spans -q` | ❌ Wave 0 |
| AGENT-04 (SC3) | past case reconstructed from checkpoint + streams, no model | integration | `uv run pytest tests/test_replay_read_only.py -q` | ❌ Wave 0 |
| AGENT-04 (SC4) | replay adds zero rows/commits; outcome equals original | integration | `uv run pytest tests/test_replay_read_only.py::test_replay_writes_nothing -q` | ❌ Wave 0 |
| carried (AUDIT-01) | the 255-suite stays green (interceptor audit behaviour unchanged) | regression | `uv run pytest -q` | ✅ |

### Sampling Rate
- **Per task commit:** `uv run pytest -q` (the suite is 7.35s — always affordable).
- **Per wave merge:** `uv run pytest -q` + `uv run ruff check .` + `uv run mypy src`.
- **Phase gate:** full suite green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_observability.py` — span kinds + no-egress + redaction (REQ AGENT-04 SC1/SC2).
- [ ] `tests/test_replay_read_only.py` — zero-write/no-model/outcome-equality (REQ AGENT-04 SC3/SC4).
- [ ] `tests/conftest.py` autouse `set_sink(tmp_path)` fixture.
- [ ] Framework install: none — pytest/pytest-asyncio already installed.

## Security Domain

> `security_enforcement` is enabled (ASVS level 1) in `.planning/config.json`.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CLI; the "approver" is a named field, not a credential. |
| V3 Session Management | no | Stateless per invocation apart from `checkpoints.db`/`spans.jsonl`. |
| V4 Access Control | yes | Read-only replay constructs **no tool mapping**, so the gated commit is structurally unreachable; `commit` remains reachable only through a resumed interrupt with a validated token. |
| V5 Input Validation | yes | The span writer must not echo untrusted complaint/prompt text (D7-08); replay validates nothing new but reads typed state (Pydantic contracts). |
| V6 Cryptography | yes | sha256 via the ONE `core.hashing.hash_value` for the trace id; this phase adds no new crypto. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cloud tracing egress (data residency breach) | **Information Disclosure** | Neutralise `LANGSMITH_*`/`LANGCHAIN_TRACING*` + clear the cached env read + assert `tracing_is_enabled() is False`; OTLP inert (no SDK). |
| Clinical text leaked into the span sink | Information Disclosure | Minimal span attributes (ids, counts, colour, rule ids, timings only — D7-08); never the note/prompt/completion. |
| Replay re-executing the gated commit | Tampering / Repudiation | Read-only by construction: no tool map, `aget_tuple` only; zero-write test. |
| Tampered `checkpoints.db` (arbitrary deserialization) | Tampering / Elevation | `JsonPlusSerializer(allowed_msgpack_modules=<explicit list>)`, never `True` (reuse `_allowed_msgpack_modules`). |
| `trace_id` forged to mis-join a record to spans | Tampering | `trace_id` is content-derived from the note (not free input) and sealed inside the audit digest. |
| Unaudited tool call | Repudiation | Every owned tool still routes through the ONE `audited` interceptor (unchanged, D-18). |

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: src/triagedesk/store/audit.py:50-60,72]` — `AuditRecord` field list; `record_digest` → `hash_value(record.model_dump(mode="json", exclude={"hash"}))`.
- `[VERIFIED: src/triagedesk/mcp/server.py:105-152]` — the `record()` closure (`await append(` :127) and the `wrapper` (`@functools.wraps(fn)` :140, `result = fn(*args, **kwargs)` :143).
- `[VERIFIED: src/triagedesk/store/borrowed.py:85-98,288-305,316-318]` — `_AUDIT_DDL` (no `trace_id`); the explicit 11-column `INSERT OR IGNORE INTO {AUDIT_TABLE}` and the `SELECT seq, ts, ...` read.
- `[VERIFIED: src/triagedesk/graph/nodes.py:83-90]` — `case_id_for` → `hash_value({"raw_note": raw_note})[:16]`.
- `[VERIFIED: src/triagedesk/graph/build.py:170-171]` — `for name in TRACER_NODES: graph.add_node(name, nodes[name])`.
- `[VERIFIED: src/triagedesk/llm/client.py:73,96-104]` — `def extract(` and the one `ollama.generate(` call + `usage_sink`.
- `[VERIFIED: src/triagedesk/durable.py:80-88]` — `derive_thread_id` → `case_id_for(raw_note.strip())`.
- `[VERIFIED: .venv/.../langsmith/utils.py:121-142,420-445]` — `tracing_is_enabled` returns `var_result == "true"` from `get_env_var("TRACING_V2", default=get_env_var("TRACING", default=""))`; `@functools.lru_cache(maxsize=100)` on `get_env_var` (namespaces `("LANGSMITH","LANGCHAIN")`).
- `[VERIFIED: .venv/.../langchain_core/callbacks/manager.py:2492,2497]` — `env_var_is_set("LANGCHAIN_TRACING")` (v1) and `tracing_v2_enabled_ = _tracing_v2_is_enabled()`.
- `[VERIFIED: .venv/.../langchain_core/utils/env.py:9-21]` — `env_var_is_set` treats `""`/`"0"`/`"false"`/`"False"` as unset.
- `[VERIFIED: .venv/.../langgraph/types.py:711-735]` — `StateSnapshot` fields; "reading the latest state … contains only interrupts still waiting for an answer".
- `[VERIFIED: .venv/.../langgraph/checkpoint/sqlite/aio.py:346-...]` — `aget_tuple` returns a `CheckpointTuple` and deserializes via `self.serde.loads_typed`.
- `[VERIFIED: probe /tmp/opencode/p7_probe4.py]` — finished thread `channel_values` include `approval`/`commit_result`/`handover`; `pending_writes == 0`; `alist` history 11; absent thread → `None`; paused thread `next == ('approval_gate',)`.
- `[VERIFIED: probe /tmp/opencode/p7_probe3.py + env_check.py]` — `get_env_var` is lru-cached: a fresh process with `LANGCHAIN_TRACING_V2=true` before the first read → `tracing_is_enabled() is True`; the same process after an unset first read → stuck `False`.
- `[VERIFIED: probe observation, p7_probe2.py]` — with a tracing var truthy, the langgraph run attempted a real HTTPS POST to `api.smith.langchain.com/runs/multipart` (401), i.e. egress is live unless neutralised.
- `[VERIFIED: uv run pytest -q]` — 255 passed in 7.35s (baseline).
- `[VERIFIED: requirements.txt:178-181, 314-315]` — `opentelemetry-api==1.45.1` present; no SDK in the lock.

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` Pitfall 10 (tracing as a derived view; redaction; no egress) and Pitfall 14 (replay must not re-execute the gated commit) — the project's own pre-build research; consistent with the verified seams.
- `.planning/research/ARCHITECTURE.md:92,105` — "`mcp/server.py::audited` … also emit a span via the injected tracer; add a second logging path → the existing interceptor gains one call" and "one `Tracer` invoked from the existing interceptor + node/model wrappers".

### Tertiary (LOW confidence)
- None material. (The OTEL-inert claim rests on the *absence* of the SDK in the lock — a present-install fact read directly, not an inferred absence.)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; versions read from `.venv`/`requirements.txt`.
- Architecture / intercept points: HIGH — every seam was read line-by-line; the extensions are additive and the node loop is confirmed.
- Env disabling semantics: HIGH — verified by probe, including the lru_cache subtlety and an observed egress attempt.
- Read-only replay mechanics: HIGH — verified by probe (`aget_tuple` on a finished thread; absent → None).
- Test churn: HIGH — the full suite was read; no test asserts the audit field set or the audit DDL (only the queue/cases DDL).
- Pitfalls: HIGH — grounded in the codebase's own guard suites plus the probe findings.
- Live-review narration and exact stdout layout: MEDIUM — intentionally left to the planner (discretion).

**Research date:** 2026-10-12
**Valid until:** ~2026-11-11 (30 days; stable pinned deps). Re-verify if `langgraph`, `langsmith` or `langchain-core` is upgraded.

## RESEARCH COMPLETE
