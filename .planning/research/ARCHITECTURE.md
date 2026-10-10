# Architecture Research — v1.1 Score Uplift

**Domain:** Agentic clinical triage-support tool (MCP + LangGraph, deterministic-SATS scorer, human-gated queue write)
**Researched:** 2026-10-10
**Confidence:** HIGH for the integration design (it is derived from the frozen v1.0 source tree, read line-by-line); MEDIUM for the LangGraph checkpointer / OTel mechanics (official docs); MEDIUM for the RAG choices (multiple community sources agree, no single authority).

> **Scope of this document.** This is **not** a greenfield architecture. v1.0 is shipped and frozen at
> `v1.0-submission`. This document answers one question: *how do the seven new v1.1 capabilities attach to
> the existing safety spine without duplicating the citation helper, the audit interceptor, or the
> scorer's monopoly on the colour?*
>
> **One-line thesis.** Every new capability is **additive at a published seam** — a new node, a new tool, a
> new schema contract, or a new adapter *behind an existing protocol*. None of them edits the scorer, the
> citation helper, or the audit interceptor; none of them adds an edge to `commit`.

---

## 1. The frozen spine (what must not move)

These five single-sources-of-truth are the invariants every v1.1 change is measured against. They are read
from the live tree; the line references are the actual seams.

| Single source | Lives at | Contract | v1.1 rule |
|---|---|---|---|
| **Colour authority** | `core/scorer.py::score_priority` (pure; imports no `llm`/`mcp`/`store`, enforced by `tests/test_purity.py`) | consumes `CaseInput` + matched ids → `PriorityResult` with `citations` 1:1 with `triggered_rules` | **No new code may produce a colour.** New code may compute a *signal*; only the scorer maps a signal to a colour. |
| **Citation helper** | `core/citations.py::format_citation` (the `Citation` dataclass) | `format_citation(reference, source) -> str` | **One helper.** Evidence/RAG/confidence text that needs attribution must call this (or a sibling that reuses `Citation`) — never an inline string. |
| **Schema module** | `core/schema.py` (`CaseInput`, `PriorityResult`, `HandoverCard`, …) | the one typed contract set | **Any new state channel or tool contract is added here.** The checkpoint serializer allowlist is *derived from this module* (`graph/build.py::_allowed_msgpack_modules`), so a contract placed here is serialisable automatically. |
| **Audit interceptor** | `mcp/server.py::audited()` → `store/audit.py::append` | one hash-chained record per owned-tool call (`AuditRecord`) | **One writer.** Any span/observability must be emitted *through* this interceptor, not beside it. |
| **Rule substrate** | `data/sats_tews.yaml`, `data/sats_discriminators.yaml` via `core/rules.py` (lru-cached) | SATS bands, colours, discriminators, citations | **Data-only extension.** New rules/weights/citations are YAML edits; no SATS value appears in code. |

The **safety spine** is the chain `score → verify → (recheck) → approval_gate (interrupt) → commit`, where
`commit_priority` is the **only** queue-affecting tool and is structurally reachable only through the
resumed `interrupt()` value (`graph/build.py` wires `approval_gate → commit` as the sole inbound edge).
`graph/build.py::OWNED_TOOL_ALLOWLIST` + `assert_tool_allowlist` pin the reachable tool surface at both the
discovery and composition edges, so any new tool is a *loud, single* edit.

---

## 2. Standard Architecture — target state after v1.1

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ DESK SURFACE  (new `desk/` package)  — a PEER of demo/run.py, not inside the graph
│  priority card · evidence excerpts · LOW-CONFIDENCE banner · vitals entry ·
│  approve / edit / dismiss ── consumed from the interrupt payload + terminal state only
└──────────────▲──────────────────────────────────────────┬─────────────────────┘
               │ handover / terminal channels              │ Command(resume=decision)
┌──────────────┴──────────────────────────────────────────▼─────────────────────┐
│ ORCHESTRATION  LangGraph StateGraph  (graph/build.py + graph/nodes.py)          │
│  ingest → normalize → retrieve → score → GROUND(new, advisory) → verify(+conf) │
│      → recheck → approval_gate(interrupt) → commit → handover                   │
│  durable state:  AsyncSqliteSaver(checkpoints.db)   ← wired E2E (was InMemory)   │
│  tracing:        ONE Tracer callback (new)  ← spans on nodes + tools + model     │
└───┬───────────────────────────┬────────────────────────┬───────────┬───────────┘
    │ MCP tool interface (DIP)  │ MCP tool interface     │ model     │ spans (local OTLP)
┌───▼──────────────────┐  ┌─────▼──────────────────┐  ┌──▼────────┐ ┌▼──────────────┐
│ OWNED MCP SERVER     │  │ BORROWED SQLITE MCP    │  │ LOCAL LLM │ │ TRACING (local│
│ 5 tools + 2 NEW:     │  │ (store/borrowed.py)    │  │ Qwen      │ │ file/OTLP;    │
│  · retrieve_evidence │  │ CRUD + read + query    │  │ extract   │ │ NO LangSmith) │
│  · assess_confidence │  │ + db_info/list_tables  │  │ only      │ │               │
│ (each @audited)      │  │ behind unchanged Store │  └───────────┘ └───────────────┘
└───┬──────────────────┘  └───────────┬────────────┘
    │ reads                            │ reads
┌───▼──────────────────────────────────▼────────────────────────────────────────┐
│ DATA + PURE CORE (unchanged spine, extended additively)                        │
│  data/sats_tews.yaml · data/sats_discriminators.yaml · data/confidence.yaml(new)│
│  core/scorer.py (COLOUR AUTHORITY) · core/citations.py (ONE HELPER)            │
│  core/confidence.py(new, pure) · core/grounding.py(new, pure KB index)         │
│  core/rules.py (ONE loader, + reload() for the live review) · core/schema.py    │
│  store/audit.py (ONE audit writer)                                             │
└────────────────────────────────────────────────────────────────────────────────┘
```

Legend: **bold = v1.1 change**; everything unmarked is frozen v1.0. There are exactly **two new owned
tools**, **one new advisory node**, **one new pure-KB module**, **one new pure-confidence module**, and
**one new UI package**; every other change is an additive field, edge, or wiring line at an existing seam.

### Component responsibilities (new/changed only)

| Component | New/Mod | Owns | Does **not** do | Implementation |
|---|---|---|---|---|
| `ground` node | NEW | fetch attributed KB excerpts for the *already-scored* matched ids | score, re-order, or set a colour | thin node in `graph/nodes.py`; calls `retrieve_evidence`; writes `evidence` channel |
| `retrieve_evidence` tool | NEW | return closed-set-keyed, `format_citation`-attributed excerpts from `data/*.yaml` | return a colour, or an id outside the closed set | owned `@server.tool() @audited()` in `mcp/server.py`; wraps pure `core/grounding.py` |
| `assess_confidence` tool | NEW | map deterministic features → a calibration score | touch the model, a colour, or a citation | owned tool wrapping pure `core/confidence.py` |
| `core/confidence.py` | NEW | the ONE calibration mapping (weights from `data/confidence.yaml`) | decide routing, call the store | pure; imports only `core/rules` + `core/schema` |
| `core/grounding.py` | NEW | build/query the KB index **from the existing YAML** | own a second copy of discriminator text | pure (lexical/BM25 over the closed set); no model |
| `Tracer` | NEW | emit node/tool/model spans with a shared trace id | be a second tool-call log | injected once in `graph/build.py`; the `audited()` interceptor calls it |
| `desk/` | NEW | render the card/banner, collect vitals + the decision | import `graph.nodes`, re-derive a colour | peer adapter over `build_graph`/`Command(resume=…)` |
| `BorrowedStore` | MOD | exercise the borrowed server's CRUD/read tools behind `Store` | change the `Store` protocol or caller surface | `store/borrowed.py` implementation only |
| `core/rules.py` | MOD | add `reload()` (clear the one lru_cache) | introduce a second loader | one function on the existing loader |
| `core/schema.py` | MOD | add `Confidence`, `GroundingPassage`, `ApprovalRequest`; extend `PriorityResult` | add a clinical-opinion field | contracts only |
| `mcp/server.py::audited` | MOD | also emit a span via the injected tracer | add a second logging path | the existing interceptor gains one call |

---

## 3. Integration map — the seven capabilities

Each row: **where it lives**, the **exact seam** it attaches to, and its **risk to the spine**.

| # Capability | Placement | Seam (file) | Spine risk |
|---|---|---|---|
| 1 RAG grounding | new owned tool + new advisory node | `mcp/server.py`, `graph/nodes.py`, `graph/state.py` | **None** if post-score & advisory; the colour is already fixed and citations stay scorer-only |
| 2 Calibrated confidence + abstention | pure helper + owned tool + `verify`-node signal + one conditional edge | `core/confidence.py`, `graph/nodes.py::verify`, `graph/build.py::route_after_verify` | Low — adds a *signal*, never a colour; abstention routes to `escalate`, never `commit` |
| 3 Durable checkpoints E2E | swap the injected checkpointer in the production/demo path | `graph/build.py::checkpointed_graph` (exists), `demo/run.py`, `cli.py` | Medium — changes the gate's pause lifecycle; must keep `thread_id` stable per case |
| 4 Span tracing + replay | one `Tracer` invoked from the **existing** interceptor + node/model wrappers | `mcp/server.py::audited`, `llm/client.py::extract`, `graph/build.py` | Low — read-only observability; must stay local (no egress) |
| 5 Desk UX | new `desk/` adapter over the graph's public interface | consumes the `approval_gate` payload + terminal channels | Low — a peer of `demo/run.py`; must not import graph internals |
| 6 Deeper borrowed-MCP usage | implementation change inside the store | `store/borrowed.py` only | Low — behind the `Store` protocol (Liskov); **watch idempotency** |
| 7 Live "add a rule" extensibility | loader cache reset + rehearsal | `core/rules.py::reload` | None — data-only; already the design |

---

## 4. Capability detail

### 4.1 RAG grounding over the SATS discriminator KB

**Where it lives → a new owned tool `retrieve_evidence` wrapped by a thin new `ground` node, placed
*after* `score`.** Rationale (the boundary rule from v1.0: *if it answers a question it is a tool; if it
controls flow it is a node*): retrieval answers "what does the manual say about this?" → **tool**; the node
only routes → **thin node**.

**Why post-score, not in the score path.** Running grounding *after* the colour is fixed makes it
structurally impossible for retrieval (lexical or embedding) to influence the priority. The node writes a
**separate** `evidence: list[GroundingPassage]` channel; it never touches `priority`, `triggered_rules`, or
`citations`. The deterministic scorer stays the **only** source of colour.

**The KB is derived, not re-authored (DRY).** Build the index from the *existing* `data/sats_discriminators.yaml`
(labels + aliases + category) — not from a second copy of discriminator text. If prose grounding is wanted,
index the transcribed sections of `docs/SATS.md` **as an evidence source only** (it is already the
human-readable reference and is excluded from the DRY gate by design), with the explicit rule that a prose
excerpt can never be read as a colour. The colour mapping remains `discriminators.yaml` categories →
`tews_to_colour` via the scorer.

**Attribution stays one helper.** Passages carry `(source, reference)` and are formatted through
`core/citations.py`. Extend the module with an `evidence_citation(...)` that **reuses the existing
`Citation` dataclass**, so no second citation string is ever built inline. Keep the priority's `citations`
strictly scorer-produced (`citations == triggered_rules`); evidence passages live in their own channel and
are rendered under a distinct "Reference excerpt" heading so a reader can never confuse them with the rule
citations.

**Recall widening (optional, guarded).** If RAG is also wanted as a *recall* aid for paraphrased complaints,
it must feed candidate ids through the existing gate `core/matcher.py::validate_discriminator_ids` (the ONE
authority that constrains ids to the closed set) and the scorer's own closed-set guard
(`_most_urgent_category` already ignores ids not in `category_of`). A model or embedding may *propose* ids;
only the scorer maps a surviving id to a colour. Prefer to ship the advisory (post-score) form first; add
recall widening only if the eval proves a real gain.

**Retrieval engine.** Default to a **lexical/BM25 index** over ~40 discriminators: zero new model, zero
egress, negligible RAM — this matters because the host's free RAM is the documented ceiling (`DEFAULT_MODEL`
is the 1.5B fallback precisely for this reason). An embedding variant is acceptable only via **local
Ollama** embeddings; a hosted vector MCP would violate the no-egress guarantee (BW-6). If embeddings are
used, the embedding client lives **outside `core/`** (in the server/`retrieval` layer) so `core/` stays pure
(`tests/test_purity.py` forbids `core/` importing `langchain`/`fastmcp`/`llm`).

**Purity boundary.** `core/grounding.py` (index build + query over YAML) stays pure and import-free of
`llm|mcp|store`. Any embedding/HTTP client is a separate, non-pure adapter.

### 4.2 Calibrated confidence + abstention

**Where it lives → a pure `core/confidence.py`, a thin owned tool `assess_confidence`, a signal set by the
`verify` node, and one conditional edge.** Confidence is a **signal on the priority**, computed from
deterministic features the pipeline already has — **not** an LLM logit (the model only ever extracts; its
confidence is not the priority's confidence).

**The features (all already in state/payload):** vitals coverage (`used_vitals` vs `missing_vitals` on
`PriorityResult`), discriminator coverage (`no_match`, `matched_ids`), override vs TEWS-only path, distance
of the TEWS total from its colour-band boundary, and extraction attempts (`attempt`). Map these to a score
via **weights/thresholds in `data/confidence.yaml`** — the same DRY/OCP pattern as the SATS rules: a
calibration tweak is a data edit, never a code edit. The pure function is the ONE mapping; the tool is a
thin wrapper (mirroring `score_priority` → `core.scorer`.

**No second citation path.** `Confidence` carries a `reason` (a short structural explanation such as
"2 of 5 scored vitals missing") that is *not* a citation. It never enters `PriorityResult.citations`.

**Abstention is routing, not computing.** Extend `graph/build.py::route_after_verify` (or add a sibling
route) so a below-threshold confidence routes to `escalate` (or `request_missing_info`) — **never to
`commit`**. The routing decision lives in the graph (a node/edge routes; it does not compute), the score
lives in the pure helper. This preserves the invariant "no code path reaches `commit` without a token".

**Schema.** Add `Confidence` to `core/schema.py` and attach it to the state (e.g. a `confidence` channel and
optionally a `confidence` field on `PriorityResult`). Because `_allowed_msgpack_modules()` derives from the
schema module, the durable checkpointer serialises it automatically — no second allowlist to maintain.

The desk banner (U4) and the gate payload read this one signal; nothing re-derives it.

### 4.3 Durable LangGraph checkpoints wired E2E

**What already exists:** `graph/build.py::checkpointed_graph(...)` compiles the graph over
`AsyncSqliteSaver` at `CHECKPOINTS_DB_PATH` (`checkpoints.db`), with the serializer allowlist derived from
the schema module. **What is missing:** the production/demo path never uses it — `run_case` builds the graph
with `checkpointer=None`, and `demo/run.py` + `evals/runner.py` both inject `InMemorySaver`.

**The change is confined to entry points, not the graph.**
- Route the real path through `checkpointed_graph`; keep `InMemorySaver` for the offline/test path (a clean
  clone must still run with no filesystem side effects — the `triagedesk demo` offline guarantee).
- Add a durable mode (`triagedesk demo --durable` / a `desk` session) that opens the file-backed saver.
- **Stable `thread_id` is the crux.** The durable resume only works if the thread id is deterministic from
  the case: use `case_id_for(raw_note)` (`graph/nodes.py`) as the real `thread_id`, replacing the
  throwaway `demo-{beat}-{index}` / `{case.id}-{run_index}` ids. Today's ids are fine for in-memory evals;
  they would make a durable gate unresumable after a restart.
- **Lifespan.** `AsyncSqliteSaver.from_conn_string` is an async context manager; the CLI/desk must own the
  open→invoke→(pause)→resume→close lifecycle so a paused gate survives a *process* restart. `run_case`
  should accept a checkpointer (or callers should use `checkpointed_graph`).

**Consequences for the interrupt/resume gate (the important part).**
- The pause becomes durable: a nurse can be interrupted, the process dies, and a fresh process reopens
  `checkpoints.db` and still reports the pending interrupt for the same `thread_id` — the realistic desk
  case. This is the headline behavioural upgrade.
- The `approval_gate` node stays **side-effect-free before `interrupt()`** (unchanged rule): a resumed node
  re-runs from its top, so the durable saver makes a pre-interrupt non-idempotent write *persistently*
  duplicated across restarts, not merely in-process. No new code may add such a write.
- **`triage.db` and `checkpoints.db` stay separate files** (clinical record vs disposable runtime state) —
  reaffirm the v1.0 rationale; do not collapse them.
- **Schema/format drift:** a stale `checkpoints.db` written under an older state shape can fail to
  deserialise. Version the checkpoint file (or delete on schema change) and document it; the allowlist being
  derived from the schema module means *adding* a contract is safe, but *changing* one is not.
- Single-process SQLite locking is fine for one desk; note it as the scale boundary.

### 4.4 Span-based tracing + replay

**The DRY rule: one event, one writer.** Do **not** introduce a second tool-call log. Instead:
- Add a single **`Tracer`** (one implementation, one source) and have the **existing**
  `mcp/server.py::audited()` interceptor emit a tool span as part of its single `record()` path — the audit
  record remains the canonical durable tool-call event; the span adds timing/parent context.
- Emit **node spans** once, via the graph callback/`make_nodes` wrapper (the v1.0 `demo/_traced_tools`
  wrapper is the shape to generalise — but as a real tracer, not a print).
- Emit **model spans** at the one model boundary, `llm/client.py::extract` (the only place the model is
  called).
- Correlate with a shared `trace_id` on the case: add a `trace_id` field to `AuditRecord` (schema change in
  `store/audit.py`) and as a span attribute, so an audit record and its span reference the same event
  **without duplicating inputs/outputs**. The span carries timing + a reference to the audit `seq`; the audit
  keeps the payload.

**No egress.** `LangSmith` is a cloud SaaS — using it would violate the no-egress guarantee (BW-6). Use
**OpenTelemetry with a local exporter** (file/JSONL or a local collector). This is a hard architectural
constraint, not a preference.

**Replay.** Two levels, both reading existing artefacts:
1. **State replay** — resume from `checkpoints.db` for a thread id (needs 4.3). Free once durable
   checkpoints land.
2. **Trace replay** — render a recorded case's spans + audit chain from the local trace file; the audit
   chain is already the deterministic record of every tool call, so replay needs no new log format.

Keep spans **derived/observational**: nothing in the scoring path depends on a span.

### 4.5 Desk UX surface

**Where it sits → a new `desk/` package that is a PEER of `demo/run.py` and `evals/runner.py`, not inside
the graph.** It depends only on the graph's **public interface**:
- the **interrupt payload** from `approval_gate` (the view model), and
- the **terminal channels** (`handover`, `recovery`, `escalation`, `priority`, and the new `confidence` /
  `evidence`).

It must **not** import `graph.nodes`, re-derive a colour, or re-score. Like `demo/run.py`, it renders only
values returned by the real graph ("no value is hard-coded").

**Freeze the payload as a typed contract.** `approval_gate` currently builds an untyped dict. Promote it to
a typed `ApprovalRequest` in `core/schema.py` (single schema source) and have the node return it — this
(a) gives the UI a stable view model, (b) lets the durable checkpointer serialise it via the derived
allowlist, and (c) removes an untyped dict from the interrupt path (a DRY/SOLID improvement, not just UX).

**Make the gate a real interaction (U2).** The UI collects `{approved_by, role, decision, final_colour,
approved_at}` and resumes with `Command(resume=...)`, replacing the demo's hardcoded value. The gate stays
machine-enforced (the tool still refuses a malformed token); the UI only supplies the human decision. This
directly addresses the automation-bias pitfall (a real approve/edit/dismiss affordance, not a rubber stamp).

**Surface the two new signals (U4).** A loud "LOW CONFIDENCE / NO DISCRIMINATOR MATCHED — nurse to
confirm" banner from `confidence` + `no_match`, and the attributed evidence excerpts from `evidence`. Both
read-only renderings of graph output.

**Tech.** Terminal TUI: `rich` (already transitive via `mcp[cli]`) for the card/banner; optionally `textual`
for the vitals-entry form. No browser surface, no new network dependency; a local TUI keeps the no-egress and
"runs from a clean clone" guarantees. Vitals entry (U5) is a form over `CaseInput` — it validates through the
**same** schema (single source), never a parallel validator.

### 4.6 Deeper borrowed-SQLite-MCP usage

**What exists:** `store/borrowed.py` already declares the borrowed tool names **as data**
(`TOOL_QUERY`, `TOOL_CREATE_RECORD`, `TOOL_READ_RECORDS`, `TOOL_LIST_TABLES`, `TOOL_GET_TABLE_SCHEMA`,
`TOOL_DB_INFO`, …) and `EXPECTED_TOOLS`, but every operation currently goes through `TOOL_QUERY`; the other
seven are asserted-but-unused (gap G7).

**The change is confined to `store/borrowed.py` (Liskov).** Route the read paths through `read_records` /
`list_tables` / `get_table_schema` and add a `db_info` startup health-check, all behind the **unchanged**
`Store` protocol, so no caller changes.

**The idempotency trap (must verify first).** `commit_to_queue` relies on `INSERT OR IGNORE` semantics
(`queue.py`) and the audit table relies on `INSERT OR IGNORE` on `seq` for replay-safety. A borrowed
`create_record` that **errors on a duplicate primary key** would break idempotency. **Keep raw `query` for
the idempotent upserts** (queue row, chain head, audit append) unless the borrowed tool's duplicate
behaviour is proven equivalent; use the CRUD/read tools for the genuinely read/DDL paths. This is a
spike-before-use item, not an assumption.

The single audit writer (`store/audit.append`) and the single idempotent write (`queue.commit_to_queue`) are
unchanged — only the store *implementation* behind them changes. This keeps DRY and gives the borrowed-MCP
story real teeth (G7) without touching the gate.

### 4.7 Live-review "add a rule in one line" extensibility

**Already the design:** a new discriminator is a YAML edit (`data/sats_discriminators.yaml`); the matcher and
scorer read it through the ONE loader (`core/rules.py`). **One missing affordance:** the loader is
`lru_cache`d (`get_tews`/`get_discriminators`), so a live edit needs a cache reset to take effect.

**The change:** add `core/rules.py::reload()` that clears the one cache — a small, single-source addition.
The CLI/desk calls it (e.g. a `rules reload` verb, or `demo --reload`) before re-scoring. A new *category* or
*colour* remains a data edit too (`categories`, `tews_to_colour`, `target_times` — all YAML), so the
"one-line" claim holds for a rule, a band, or a discriminator.

**Do not build a rule editor** (scope discipline). The rehearsal is a documented one-line edit + reload; the
live review is a *demonstration that the code was never edited*.

---

## 5. Data-flow changes

Only two flows change; both are additive.

**Flow A — grounded, confidence-scored, durable gate (new happy path):**
```
raw → ingest → normalize → retrieve → score ──(colour FIXED here)──►
     ground (advisory excerpts; cannot change colour) →
     verify (+ confidence signal from core/confidence.py) →
     [low confidence] → escalate            (new conditional, never → commit)
     [ok] → recheck → approval_gate(interrupt; payload = typed ApprovalRequest)
           │  state persisted to checkpoints.db (thread_id = case_id_for(raw_note))
           └─ resume(decision) → commit (gated, idempotent) → handover
```

**Flow B — observability/replay:**
```
every owned-tool call → audited() record() ─┬─► store/audit.append   (canonical, hash-chained)
                                            └─► Tracer.span(tool)     (timing, trace_id, ref=seq)
every node super-step  → Tracer.span(node)
llm/client.extract()   → Tracer.span(model)
   → local trace file (OTLP/JSONL) ── replay reads trace + audit chain + checkpoints.db
```

**State-channel additions (all in `core/schema.py` + `graph/state.py`):** `evidence: list[GroundingPassage]`,
`confidence: Confidence`, and the typed `ApprovalRequest` (interrupt payload). `PriorityResult` may gain a
`confidence` field. Nothing else in the state shape changes.

---

## 6. DRY / SOLID compliance — how each capability avoids duplication

| Capability | The single source it **reuses** | It must **not** create |
|---|---|---|
| RAG grounding | `data/sats_discriminators.yaml` (indexed, not copied); `core/citations.py` for attribution; `validate_discriminator_ids` for closed-set ids | a second discriminator KB, a second citation formatter, a second colour source |
| Confidence | `core/schema.py` for the contract; `data/confidence.yaml` for weights; the `verify` node for placement | an LLM confidence, a second evidence path, a second abstention mechanism outside routing |
| Durable checkpoints | `graph/build.py::checkpointed_graph` (exists); the schema-derived serializer allowlist | a second persistence layer, a merged `triage.db`/`checkpoints.db` |
| Tracing | the existing `audited()` interceptor; `store/audit.py` record shape; the one model boundary | a second tool-call log, a cloud tracer, a duplicate inputs/outputs store |
| Desk UX | the graph's public interface (payload + terminal channels); `CaseInput` for vitals | graph-internal imports, a re-derived colour, a parallel validator |
| Borrowed MCP depth | the existing `Store` protocol + declared tool constants | a new caller surface, a broken idempotency key |
| Rule extensibility | `data/*.yaml` + the one loader | a code path per rule, a rule editor |

**The OCP test for every change:** *"Is this a new node, a new tool, a new contract, or a data edit — without
editing the scorer, the citation helper, or the audit interceptor?"* If a change edits `core/scorer.py` to
add a colour source, edits `core/citations.py` to add a second formatter, or adds a second `append()` path,
it violates the iron-clad rule and is rejected at review.

---

## 7. Suggested build order (dependencies + risk retirement)

The ordering front-loads the two risks that could invalidate the whole milestone: the durable-gate
lifecycle and the borrowed-tool idempotency. Capabilities that are independent run in parallel.

| Step | Build | Depends on | Retires | Risk front-loaded |
|---|---|---|---|---|
| **1** | Durable checkpoints E2E (#3): route demo/desk through `checkpointed_graph`, stable `thread_id`, `--durable`, prove pause survives a *process restart* | — (prebuilt `checkpointed_graph`) | the gate's durable lifecycle | **HIGH** — the interaction of `AsyncSqliteSaver` + `interrupt()` across restarts, and the `thread_id` stability requirement |
| **2** | Tracing seam (#4): one `Tracer`, emitted from the existing `audited()` + node wrapper + `llm/extract`; local OTLP/JSONL; `trace_id` on `AuditRecord` | 1 (for state replay) | observability, no-egress tracer | MEDIUM — OTel without egress; keeping it off the critical path |
| **3** | Calibrated confidence + abstention (#2): `core/confidence.py` + `data/confidence.yaml` + `assess_confidence` tool + `verify` signal + abstention edge | — | the honesty gap (E-09 class) | LOW — pure function; the risk is calibration *quality*, tuned against the eval labels |
| **4** | RAG grounding (#1): `core/grounding.py` KB from YAML + `retrieve_evidence` tool + `ground` node after `score` + evidence channel | 3 (schema/contracts land with it) | knowledge-grounding gap | MEDIUM — engine choice (lexical vs local-embedding) under the RAM budget |
| **5** | Borrowed-MCP depth (#6): CRUD/read/`db_info` behind the unchanged `Store`; **spike the duplicate-key idempotency first** | — | gap G7; the idempotency unknown | MEDIUM — a borrowed `create_record` that breaks `INSERT OR IGNORE` semantics |
| **6** | Desk UX (#5): `desk/` adapter + typed `ApprovalRequest` + priority card + confidence banner + evidence excerpts + real approve/edit/dismiss + vitals entry | 1, 3, 4 | fit-to-desk gap (U1–U5) | LOW — it is an adapter, but it must not reach into graph internals |
| **7** | Rule-extensibility rehearsal (#7): `core/rules.py::reload()` + a documented one-line edit + rehearse the live walkthrough | — | gap G6 | LOW |

**Critical path:** 1 → 3 → 4 → 6. Steps 2 and 5 are independent and parallelisable; step 1 is the must-not-slip
item because the durable gate is the capability most entangled with the safety spine.

**Why this order:** #3 (durable checkpoints) changes *where the gate lives in time*, so it is resolved before
anything builds on the resume path. #2 (tracing) rides on #3 for replay. #2/#4 are pure/additive and can be
retired early without touching the scored path. #5 (borrowed depth) is confined to one module and only
threatens idempotency — spike it in parallel. #6 (UX) consumes #1/#3/#4, so it lands last among the builders.
#7 is a rehearsal, not a build.

---

## 8. Anti-patterns (milestone-specific)

### Anti-Pattern 1: RAG in the score path
**What:** feed retrieval candidates (or model output) into the colour decision.
**Why wrong:** reintroduces a non-deterministic colour source; breaks the audit story and injection
resistance.
**Instead:** ground *after* `score` (advisory), or feed candidates only through `validate_discriminator_ids`
and let the scorer's closed-set guard + colour mapping remain the sole authority.

### Anti-Pattern 2: an LLM confidence
**What:** ask the model how sure it is, or read a logit from extraction.
**Why wrong:** the model only extracts; its confidence is neither calibrated nor about the *priority*.
**Instead:** compute confidence from deterministic features in `core/confidence.py`, weights in `data/`.

### Anti-Pattern 3: a second logging path for traces
**What:** a tracing decorator beside `audited()` that logs tool calls again.
**Why wrong:** two tool-call records that can disagree (DRY violation) and a duplicated audit surface.
**Instead:** the existing interceptor emits the span; the audit record stays canonical.

### Anti-Pattern 4: a cloud tracer
**What:** wire `LangSmith`/hosted OTel for convenience.
**Why wrong:** egress — violates BW-6 and the data-residency guarantee.
**Instead:** local OTLP/JSONL exporter.

### Anti-Pattern 5: UX coupled to graph internals
**What:** the desk form imports `graph.nodes` or re-derives the colour from the priority.
**Why wrong:** couples the surface to internals; risks a second colour/citation path.
**Instead:** consume only the interrupt payload + terminal channels; render what the graph returns.

### Anti-Pattern 6: breaking idempotency to "use more borrowed tools"
**What:** swap the `INSERT OR IGNORE` upserts for a borrowed `create_record` that errors on duplicates.
**Why wrong:** a crash-retry would then create a second queue row — the exact failure the idempotency key
exists to prevent.
**Instead:** verify duplicate behaviour; keep raw `query` for idempotent writes, use CRUD/read tools elsewhere.

### Anti-Pattern 7: collapsing the two databases
**What:** reuse `checkpoints.db` as the case/queue/audit store, or vice versa.
**Why wrong:** conflates disposable runtime state with the immutable clinical record.
**Instead:** keep `triage.db` (clinical + audit) and `checkpoints.db` (runtime) separate.

---

## 9. Integration points

### External services

| Service | Integration pattern | Notes |
|---|---|---|
| Local LLM (Ollama, Qwen2.5-1.5b default) | `llm/client.py::extract` only; structured JSON (`format=<schema>`) | unchanged; model span emitted here. No egress. |
| Owned MCP server (`triagedesk`) | stdio; 5 existing tools + 2 new (`retrieve_evidence`, `assess_confidence`), each `@audited()` | adding a tool touches the allowlist + `evals/tools.py` map + server |
| Borrowed SQLite MCP (`mcp-sqlite@1.0.9`) | separate adapter context (`load_borrowed_tools`); more of its tools used behind `Store` | do not merge contexts (era collapse); verify duplicate-key semantics |
| Local trace sink (OTLP/JSONL) | local file/collector only | **no** LangSmith/hosted tracer (egress) |
| Durable checkpoints (`checkpoints.db`) | `AsyncSqliteSaver` via `checkpointed_graph` | separate file from `triage.db`; stable `thread_id` |

### Internal boundaries

| Boundary | Communication | v1.1 notes |
|---|---|---|
| graph ↔ MCP tools | injected `ToolMap` (DIP) | two new owned tools added to the allowlist + every injected map |
| ground node ↔ scorer | **none** (ground runs after score) | the structural guarantee RAG cannot set a colour |
| verify ↔ confidence | pure function call (`core/confidence.py`) | a node delegates computation to pure core; the node only sets a channel |
| approval_gate ↔ UI | typed `ApprovalRequest` (interrupt payload) | the one view-model seam; serialised via the derived allowlist |
| approval_gate ↔ checkpointer | `interrupt()` + `Command(resume=…)`, durable | the pause survives a process restart; no pre-interrupt side effect |
| every owned tool ↔ audit | `audited()` (ONE interceptor) | the same interceptor also emits the tool span |
| store callers ↔ borrowed tools | `Store` protocol | expanded borrowed usage stays behind the protocol |
| core ↔ data | loader (+ `reload()`) | confidence weights join the data authority; a rule is still a one-line edit |

---

## 10. Sources

- **Project source tree (HIGH — read directly, authoritative):** `src/triagedesk/graph/{build,nodes,state}.py`,
  `src/triagedesk/mcp/{server,adapter}.py`, `src/triagedesk/core/{scorer,citations,rules,matcher,schema}.py`,
  `src/triagedesk/store/{audit,borrowed,queue,__init__}.py`, `src/triagedesk/{demo/run,evals/runner,evals/tools,llm/client,cli}.py`,
  `tests/test_purity.py`, `data/sats_discriminators.yaml`, `pyproject.toml`.
- **Project docs (HIGH — authoritative requirements):** `.planning/PROJECT.md`, `ARCHITECTURE.md`,
  `STATUS.md`, `docs/DECISIONS.md`, `docs/CONVENTIONS.md`, `docs/ROADMAP.md`.
- **LangGraph persistence & checkpointers** (official docs, MEDIUM):
  <https://docs.langchain.com/oss/python/langgraph/persistence> and `.../interrupts`.
- **OpenTelemetry Python SDK** (official docs, MEDIUM): local OTLP/console exporters, no hosted backend.
- **RAG lexical vs embedding retrieval over small curated corpora** (web, MEDIUM — multiple community
  sources agree BM25 is competitive and dependency-free for ~40 short documents; embeddings add a model +
  RAM cost).

---

*Architecture research for: TriageDesk v1.1 Score Uplift — integrating seven new capabilities into a frozen, safety-critical MCP + LangGraph agent.*
*Researched: 2026-10-10*
