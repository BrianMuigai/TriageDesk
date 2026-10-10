# Stack Research — v1.1 "Score Uplift" additions

**Domain:** Local-first, MCP-based agentic clinical triage-support tool (Python) — **additions for the six new v1.1 capabilities**
**Researched:** 2026-10-10
**Confidence:** **HIGH** on every version (PyPI registry JSON cross-checked against the *installed* `.venv`, i.e. the versions are literally present). **MEDIUM** on two beta/optional items — the OTLP JSON file exporter (beta) and LangChain auto-instrumentation — both flagged as *retire in a spike*.

> **Scope note (DRY).** The v1.0 stack is **frozen** at tag `v1.0-submission` and is not re-derived here.
> The MCP World A/B decision, LangGraph, Ollama/Qwen, `langchain.mcp.MCPAdapter`, Pydantic, the borrowed
> `mcp-sqlite` and the hash-chained audit are settled (see the prior `.planning/research/STACK.md` history
> and `docs/DECISIONS.md`). This document adds **only** what the six new capabilities need, names the
> exact integration seam for each, and says explicitly what **not** to add.

---

## TL;DR — most of what v1.1 needs is **already in the venv**

The single most useful finding: three of the six capabilities need **no new dependency at all**, and two
of the rest need only a package that is *already installed transitively* and merely needs to be promoted
to a **direct** pin.

| # | Capability | New runtime dep? | What to add (exact pin) |
|---|------------|------------------|--------------------------|
| 1 | **RAG over the SATS KB** | Optional | **None** (in-house lexical, recommended) — or `rank-bm25==0.2.2` + `snowballstemmer==3.1.1`; semantic lift via existing Ollama `nomic-embed-text` + already-present `sqlite-vec==0.1.9` |
| 2 | **Calibrated confidence + abstention** | No (runtime) | Runtime = a deterministic scorer + a frozen `data/calibration.json`; **dev-only** `scikit-learn==1.9.1` to fit it |
| 3 | **Durable checkpoints E2E** | **No** | Nothing — `langgraph-checkpoint-sqlite==3.1.1` + `AsyncSqliteSaver` are already pinned and wired in `graph/build.py`; only the *callers* need swapping |
| 4 | **Span tracing + replay** | Yes (small) | `opentelemetry-sdk==1.45.1` (the `opentelemetry-api==1.45.1` is **already present** via `mcp==2.3.0`); offline export via `opentelemetry-exporter-otlp-json-file==0.66b1` **or** a ~40-line in-house JSONL exporter |
| 5 | **Desk-facing UX** | Promote existing | `rich==15.0.0` — **already installed** (transitive via `typer` / `mcp[cli]`); declare it directly. Optional `textual==8.2.8` |
| 6 | **Deeper borrowed SQLite MCP use** | **No** | Nothing — the 8 tools are already declared in `store/borrowed.py`; wire the ones you don't call yet |

**Already in `.venv` today (verified on disk):** `rich-15.0.0`, `opentelemetry_api-1.45.1`,
`sqlite_vec-0.1.9`, `langgraph_checkpoint_sqlite-3.1.1` (`langgraph_checkpoint-4.2.0`),
`langsmith-0.14.5`, `langchain_core-1.6.9`, `mcp-2.3.0`, `fastmcp-4.1.0`.

---

## Recommended Stack

### Core Technologies (new)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12.x (unchanged) | Runtime | `requires-python = ">=3.12,<3.13"` already pinned; every new package below supports 3.12 (`numpy==2.5.3` requires `>=3.12` exactly). |
| **`opentelemetry-sdk`** | **1.45.1** | Tracing engine for capability 4 | The `opentelemetry-api` is **already a dependency of `mcp==2.3.0`** (`opentelemetry-api>=1.28.0`, resolved to 1.45.1), so adding the SDK is a one-package change that keeps the whole trace stack on one version line and adds **zero** API surface. |
| **`rich`** | **15.0.0** (promote transitive → direct) | Desk-facing priority card + vitals entry (capability 5) | It is *already installed* (pulled by `typer` ← `mcp[cli]`), so promoting it changes no resolved version — it just makes the real dependency explicit and DRY-pinned instead of incidental. Panels/Tables/prompts cover both the card and the vitals entry with no second UI stack. |
| **Ollama embeddings** (`nomic-embed-text` / `all-minilm`) | model pull; `ollama==0.6.3` client already pinned | Optional semantic half of RAG (capability 1) | Reuses the **existing** Ollama server and client (`ollama.embeddings(...)`), so no new Python dependency and no second model server. `nomic-embed-text` is 274 MB / 768-dim; `all-minilm` is 46 MB / 384-dim — both fit the CPU-only, low-headroom budget when loaded *sequentially* with the extractor. |

### Supporting Libraries (new)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rank-bm25` | **0.2.2** | Off-the-shelf BM25 lexical retrieval | **Only if** you prefer a library over in-house code. Pure Python + numpy; 8.7M downloads/month. See the flag: unmaintained since 2022 with a numpy-2 alias risk. |
| `snowballstemmer` | **3.1.1** | Deterministic English stemming for the lexical index/query | With the in-house scorer, so a query token *"diabetic"* matches the KB stem *"diabet"* (the E-09 mechanism). Zero dependencies, pure Python. |
| `rapidfuzz` | **3.14.6** | Fuzzy typo tolerance on the complaint | Optional retrieval hardening (misspellings); wheels only, no build step. |
| `numpy` | **2.5.3** | Cosine similarity over ≤~50 vectors; calibration maths | **Only if** you compute vectors directly (brute-force is simpler than `sqlite-vec` at this KB size) or want numpy-only calibration. Pin it if you import it directly. |
| `sqlite-vec` | **0.1.9** | Vector store *if the KB grows* | Already installed transitively via `langgraph-checkpoint-sqlite`. Overkill for a 41-row KB; keep as the scale path, not the MVP path. |
| `opentelemetry-exporter-otlp-json-file` | **0.66b1** | Writes spans as compact JSON-Lines to a file — **no collector, no network** | Use this (or an in-house exporter) so capability 4 stays offline. **Beta** — flagged. |
| `scikit-learn` | **1.9.1** | **Dev-only.** Fits + evaluates the confidence calibration | `isotonic_regression` / `CalibratedClassifierCV`, `brier_score_loss`, `calibration_curve`. Keeps the runtime free of the ML stack. |
| `textual` | **8.2.8** | Optional richer TUI for the vitals form | Only if `rich` prompts feel too thin for the demo. Heavier (adds `platformdirs`, `mdit-py-plugins`). |

### Development Tools (unchanged)

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Project lifecycle | Host is already on **uv 0.12.24** — the v1.0 "upgrade uv" flag is **stale**; do not re-flag it. |
| Ollama CLI | Pull the embedding model once | `ollama pull nomic-embed-text` (274 MB) — pulled at build time, offline at run time, exactly like `qwen2.5:1.5b`. |
| `pytest` / `pytest-asyncio` | New contract tests | Checkpoint restart test; retrieval determinism test; confidence-monotonicity test; span-tree replay test. |

---

## Capability detail & integration seams

### 1. Retrieval-grounded knowledge (RAG) over the SATS manual / discriminator KB

**The KB is tiny and already structured**: 41 discriminators in `data/sats_discriminators.yaml`
(208 lines) plus `docs/SATS.md` (146 lines). Do **not** build a vector platform for 41 documents.

**Recommendation — lexical-first, semantic-optional (hybrid):**

1. **Primary retriever: an in-house BM25/TF-IDF scorer** over `snowballstemmer==3.1.1`-normalised
   tokens of each discriminator's `label` + `aliases` and each SATS.md section. ~40 lines, zero new
   runtime dependency, fully deterministic and offline. This respects the project's determinism ethos
   (D-01/D-02): retrieval cannot inject a colour and the offline demo/eval stays reproducible.
2. **Query = the whole note, not the short `complaint` field.** This is the actual E-09 fix: the E-09
   note literally contains *"known diabetic"*, and the discriminator alias *"diabetic glucose high"*
   stems to the same `diabet` token — so a stemmed lexical query **surfaces** `diabetic_hyperglycaemia_*`
   as a candidate, which the exact alias table (which deliberately excludes "feeling unwell") missed.
   Retrieval surfaces candidates; the model still only *selects* from the closed set (D-06 unchanged).
3. **Optional semantic rerank** (only if a spike shows lexical still misses): embed the query with the
   local Ollama embedding model (`nomic-embed-text`, 274 MB) and rank by cosine. With ≤50 vectors,
   brute-force `numpy` cosine beats adding a vector store; keep `sqlite-vec==0.1.9` for the day the KB
   grows. Load the embedding model **after** unloading the extractor (`keep_alive=0`) to stay inside RAM.
4. **Offline golden path:** the offline demo/eval must not need the embedding model. The lexical retriever
   is deterministic, so `--offline` uses it directly; a golden retrieval fixture is unnecessary.

**Integration seam:** new pure module `src/triagedesk/core/kb.py` (index build from `data/*.yaml` +
`docs/SATS.md` — one loader, CONVENTIONS §1) and `src/triagedesk/core/retrieval.py` (pure scorer; imports
nothing from `llm`/`mcp`/`store`, D-13); a new owned MCP tool `retrieve_discriminators` in
`src/triagedesk/mcp/server.py` (add to `OWNED_TOOL_ALLOWLIST` in `graph/build.py`); a new `retrieve_kb`
graph node wired **before** `score`, feeding candidates into `normalize`. Because a new capability is
"one tool + one node" (D-18), existing code is untouched.

**What NOT to add:** `chromadb`, `faiss-cpu`, `qdrant-client`, `lancedb`, `LlamaIndex`, `txtai` — all far
heavier than a 41-doc corpus warrants and several add a server or a native build. `sentence-transformers`
/ `torch` — pull a multi-hundred-MB runtime that will not fit the CPU/RAM budget.

### 2. Calibrated confidence + abstention (selective prediction)

**Runtime adds no dependency.** A pure `src/triagedesk/core/confidence.py` maps the deterministic signals
already in the system — TEWS distance from the band edge, whether the colour came from a TEWS band vs a
discriminator override, exact-alias vs retrieved-candidate provenance, `missing_vitals`, `no_match`, and
the retrieved candidate's score — to a calibrated probability plus an **abstain** decision. The mapping
constants are a **frozen `data/calibration.json`** table (the DRY single source, mirroring how SATS rules
live in `data/*.yaml`).

**Offline fit + reporting: `scikit-learn==1.9.1` as a *dev-only* dependency** — fit isotonic / Platt
scaling on the eval suite, compute `brier_score_loss` and `calibration_curve`, and write the frozen table.
The runtime never imports it (keeps the frozen app light and the loader pure). It pulls `numpy==2.5.3`
and `scipy` at dev time only.

**Integration seam:** additive fields on `PriorityResult` (`confidence`, `abstain_reason`) in
`core/schema.py`; a reliability/Brier block in `evals/report.py` + `evals/analysis.py`; the U4 "no
match — nurse to confirm" banner (capability 5) reads `confidence`.

**Lean alternative:** skip scikit-learn entirely — numpy-only PAVA isotonic (~30 lines) and a
hand-computed Brier score. Choose this if you want the dev environment free of `scipy` too.

**What NOT to add:** `netcal` / `torchmetrics` (extra calibration frameworks — overkill on a 14-case
set); any *runtime* ML library; online/self-learning calibration (out of scope by project decision).

### 3. Durable LangGraph checkpoints wired E2E

**Nothing to add — the stack is already correct; only the wiring is missing.**

- `langgraph-checkpoint-sqlite==3.1.1` (resolving `langgraph-checkpoint==4.2.0`, `aiosqlite>=0.20`) is
  pinned, and `graph/build.py:checkpointed_graph` already opens `AsyncSqliteSaver.from_conn_string(...)`
  over a dedicated `checkpoints.db` with the msgpack allowlist.
- The gap is that `demo/run.py`, `cli.py` and `evals/runner._checkpointer()` still compile over
  `InMemorySaver`. **Swap the E2E path to `checkpointed_graph`** and add one test that reopens
  `checkpoints.db` with a *fresh* saver and observes the pending `interrupt()`.

**Confirmed current API (docs, 2026):**
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as saver:
    graph = builder.compile(checkpointer=saver)
    await graph.ainvoke(initial, {"configurable": {"thread_id": case_id}})
```

**What NOT to add:** `langgraph-checkpoint-postgres` (requires a server; violates the offline/no-service
posture). Do not re-add `sqlite-vec`/`aiosqlite` — they are transitive. Keep `checkpoints.db` **separate**
from `triage.db` (D-09: runtime state vs clinical record — the two-file rationale stands).

### 4. Span-based tracing + replay on top of the JSONL audit

**Add `opentelemetry-sdk==1.45.1`.** The `opentelemetry-api` is already installed (via `mcp==2.3.0`), so
this is the minimal additive change.

**Offline export — two acceptable options, no collector, no egress:**
- **`opentelemetry-exporter-otlp-json-file==0.66b1`** *(beta, flagged)* — official "OTLP JSON File
  Exporter"; writes compact JSON-Lines spans to a file (`FileSpanExporter(path)` paired with
  `SimpleSpanProcessor`/`BatchSpanProcessor`). This is the cleanest "spans on disk, replay later" path.
- **In-house ~40-line `SpanExporter`** writing to `log/spans.jsonl` — the leaner, dependency-free option;
  reuse the existing audit writer's JSONL pattern so there is one serialisation idiom (DRY).

**Instrumentation:** explicit, manual `tracer.start_as_current_span("node:score")` around each graph node
(`graph/nodes.py`) and the tool wrapper (`demo/run.py:_traced_tools`). `trace_id`/`span_id`/`parent_id`
give the replay tree; a `triagedesk replay` command reads `log/spans.jsonl` + the existing `log/audit.jsonl`
and re-renders with `rich`, and can re-run deterministically from recorded inputs (the deterministic
scorer makes replay faithful).

**Alternatives & what NOT to add:**
- **LangSmith cloud tracing — do NOT enable.** `langsmith==0.14.5` is already installed transitively, but
  the default endpoint is SaaS → **network egress**, which violates the no-data-leaves-the-machine
  guarantee. Keep `LANGSMITH_TRACING`/`LANGCHAIN_TRACING_V2` unset (or `local`) and confirm with
  `strace` in the no-egress test.
- `openinference-instrumentation-langchain==0.1.79` (auto-instrumentation) — convenient, but it type-checks
  against `langchain-core==1.3.3` while the project resolves `1.6.9`; treat as an **optional spike**, not a
  default. Manual spans are safer and match the "small, named components" principle (D-14).
- `arize-phoenix` / `opentelemetry-exporter-otlp-proto-http` + a local Jaeger/Tempo — only if you want a
  graphical trace UI; heavier (Docker/server) and unnecessary when a JSONL replay tool suffices.

### 5. Minimal desk-facing UX surface (vitals entry + priority card)

**Add `rich==15.0.0` as a *direct* dependency** (already installed transitively). Build:
- the **priority card** as a `rich.Panel`/`Table` rendering `HandoverCard`: colour-coded, with citations
  next to the colour (the existing automation-bias mitigation), stated target time, and the loud
  **"LOW CONFIDENCE / NO DISCRIMINATOR MATCHED — nurse to confirm"** banner (U4, reads capability 2);
- the **vitals-entry** surface with `rich.prompt` (numeric-keypad-friendly, units, missing-vital prompts —
  U5), which also makes the approve/edit/dismiss gate a **real interaction** instead of a hardcoded value
  (U2).

**Integration seam:** new `src/triagedesk/ui/` package (pure renderers of `HandoverCard`/`PriorityResult`);
a `triagedesk desk` (and/or `triagedesk card`) subcommand in `cli.py` (stdlib `argparse` stays).

**Optional:** `textual==8.2.8` for a proper form/TUI if `rich` prompts are too thin for the recording.

**What NOT to add:** Streamlit / Gradio / NiceGUI / a web UI — out of scope for a 6-day solo build, heavier,
and the brief asks for a *desk surface*, which a terminal delivers without a browser or a server.

### 6. Deeper use of the borrowed SQLite MCP server

**Nothing to add.** `store/borrowed.py` already declares all 8 borrowed tools in `EXPECTED_TOOLS`
(`db_info`, `query`, `list_tables`, `get_table_schema`, `create_record`, `read_records`,
`update_records`, `delete_records`); only `query` is invoked today (STATUS.md G7). Wire the others:
- `list_tables` + `get_table_schema` → a startup schema check / introspection tool (proves the borrowed
  server is actually exercised, not merely connected);
- `read_records` → read the queue/case rows instead of raw `SELECT` (narrower, safer SQL surface);
- `create_record` → the queue/case insert path.

**Integration seam:** `store/borrowed.py` (add the calls) behind the unchanged `Store` protocol in
`store/__init__.py` (SOLID: L — the protocol does not change; only the concrete server calls do). Consider
one new *owned* read tool (`queue_status`) that surfaces borrowed-server facts to the graph.

**What NOT to add:** the **archived** official `modelcontextprotocol/sqlite` / PyPI `mcp-server-sqlite`
(no security guarantees); an unpinned `npx -y mcp-sqlite` (breaks deadline reproducibility — keep
`mcp-sqlite@1.0.9`).

---

## Installation

```bash
# 0. uv is already current (0.12.24) — no self-update needed.

# 1. Runtime additions (capabilities 1, 4, 5). rich is already installed transitively;
#    declaring it makes the pin explicit (no resolved version changes).
uv add \
  "opentelemetry-sdk==1.45.1" \
  "opentelemetry-exporter-otlp-json-file==0.66b1" \
  "rich==15.0.0" \
  "snowballstemmer==3.1.1"          # RAG lexical normalisation (in-house scorer)

#    Optional RAG library instead of / in addition to the in-house scorer:
#    uv add "rank-bm25==0.2.2" "rapidfuzz==3.14.6" "numpy==2.5.3"
#    Optional richer TUI: uv add "textual==8.2.8"

# 2. Dev-only additions (capability 2 calibration fit + metrics)
uv add --dev "scikit-learn==1.9.1"

# 3. Re-lock for the deadline clone (offline, reproducible)
uv lock && uv sync --locked

# 4. Embedding model for the OPTIONAL semantic retrieval half (pulled once, then offline)
ollama pull nomic-embed-text        # 274 MB, 768-dim (all-minilm = 46 MB, 384-dim fallback)

# Capability 3 (durable checkpoints) and 6 (borrowed MCP) add NOTHING to install.
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| In-house lexical BM25 (zero dep) | `rank-bm25==0.2.2` | If you prefer a library to ~40 lines of code and accept the numpy-2 risk. |
| In-house lexical BM25 | `bm25s==0.3.13` | If the KB grows and you want speed — but it pulls `scipy` (479 MB env), so not for 41 docs. |
| Ollama embeddings (+ numpy cosine) | `sqlite-vec==0.1.9` (already present) | When the KB outgrows brute-force (hundreds of rows) and you want ANN. |
| Ollama embeddings | `fastembed==0.9.0` (ONNX) | If you must avoid the Ollama embedding model — but it adds `onnxruntime` + `tokenizers` + a HF download. |
| `opentelemetry-exporter-otlp-json-file==0.66b1` | In-house JSONL `SpanExporter` | If you want no beta dependency; ~40 lines, same result. |
| Manual OTel spans | `openinference-instrumentation-langchain==0.1.79` | Optional auto-instrumentation spike; flagged for `langchain-core` drift. |
| `scikit-learn` (dev-only) | numpy-only PAVA isotonic | If you want the dev env free of `scipy`. |
| `rich` prompts | `textual==8.2.8` | If the demo wants a full-screen form. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `chromadb`, `faiss-cpu`, `qdrant-client`, `lancedb`, `LlamaIndex`, `txtai` | Massively over-provisioned for a 41-doc KB; add native builds, servers or large transitive trees. | In-house lexical BM25 (+ optional Ollama embeddings). |
| `sentence-transformers`, `torch`, `transformers` (for embeddings) | Multi-hundred-MB CPU runtimes; will not fit the low-headroom budget and add no value over Ollama's embeddings. | `nomic-embed-text` / `all-minilm` via the existing Ollama server. |
| **LangSmith cloud tracing** (`LANGSMITH_TRACING=true`, `LANGCHAIN_TRACING_V2=true`) | SaaS endpoint = **network egress** of case data; instant-disqualifier risk. | `opentelemetry-sdk` with a file exporter; keep LangSmith env unset. |
| `arize-phoenix`, OTLP-HTTP + a collector, for the MVP | Adds a local server/Docker; the JSONL file exporter already gives replay. | OTLP **JSON file** exporter or in-house JSONL exporter. |
| `langgraph-checkpoint-postgres` | Requires a Postgres server; not offline. | `langgraph-checkpoint-sqlite` (`AsyncSqliteSaver`) — already pinned. |
| Runtime `scikit-learn` / `torch` on the safety path | Pulls the ML stack into a frozen, RAM-tight app for a 14-case calibration; undermines determinism/defensibility. | Dev-only `scikit-learn` → frozen `data/calibration.json`. |
| `rank-bm25==0.2.2` under `numpy>=2` **without a spike** | Unmaintained since 2022; numpy 2.0 removed aliases (`np.float_`, …) that old libs use. | Verify in the capability-1 spike; else use the in-house scorer or `bm25s`. |
| The archived official `mcp-server-sqlite` / unpinned `npx mcp-sqlite@latest` | No security guarantees; unpinned fetch breaks deadline reproducibility. | The pinned `mcp-sqlite@1.0.9` already wired in `mcp/adapter.py`. |
| A web UI (Streamlit/Gradio/NiceGUI) | Scope/time cost; a browser+server is not a *desk terminal* surface. | `rich` (+ optional `textual`). |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `opentelemetry-sdk==1.45.1` | `opentelemetry-api==1.45.1` (already installed via `mcp==2.3.0`) | SDK pins the API **at the exact same version**; the existing transitive API is 1.45.1, so this is a clean, conflict-free add. |
| `opentelemetry-exporter-otlp-json-file==0.66b1` | `opentelemetry-sdk~=1.45.1` | Beta line aligned to SDK 1.45.1. Flagged. |
| `rich==15.0.0` | `typer==0.27.3` ← `mcp[cli]` | Already the resolved version; promoting it to a direct pin changes nothing. |
| `scikit-learn==1.9.1` | `numpy==2.5.3`, `scipy>=1.10.0` | Dev-only. `requires-python>=3.11`; 3.12 ✓. |
| `numpy==2.5.3` | Python `>=3.12` | Matches the project's `>=3.12,<3.13`. Pin it only if imported directly. |
| `sqlite-vec==0.1.9` | `langgraph-checkpoint-sqlite==3.1.1` | Already installed transitively; re-adding is a no-op. |
| Ollama `nomic-embed-text` | Ollama server `0.30.6` | Embeddings API has been stable for years; `ollama==0.6.3` client supports `embeddings()`. |
| `rank-bm25==0.2.2` | `numpy==2.5.3` | **Unverified** — numpy 2.x removed legacy aliases; spike before adopting. |

## Recommended Dependency Boundaries (DRY + SOLID)

| Concern | Single source of truth | Everyone else |
|---------|------------------------|---------------|
| KB index + retrieval scoring | one pure `core/kb.py` + `core/retrieval.py` (D-13: no `llm`/`mcp`/`store` imports) | The MCP tool and graph node call these; no alias/label is inlined. |
| Retrieval candidates → model | the owned `retrieve_discriminators` tool + one node | The model still only *selects* from the closed set; the colour is never retrieved. |
| Confidence + abstention policy | one pure `core/confidence.py` + frozen `data/calibration.json` | The eval report and the UX banner read the same value. |
| Span shape / export | one observability module (tracer + one exporter) | Nodes/tool wrapper emit spans; replay reads one file. |
| Durable runtime state | `checkpoints.db` via `checkpointed_graph` (the ONE compile-with-checkpointer seam) | Callers request it; they never open a saver themselves. |
| Borrowed-server tool names | the ONE `EXPECTED_TOOLS` tuple in `store/borrowed.py` | Wiring reads names; nothing inlines them. |
| Desk rendering | one `ui/` package rendering `HandoverCard` | CLI/UX call it; no card field is reformatted elsewhere. |

## Open Questions / Flags

| Flag | Risk | Retire by |
|------|------|-----------|
| `rank-bm25==0.2.2` under numpy 2.x | Legacy numpy aliases removed in 2.0; lib unmaintained since 2022. | Capability-1 spike: import + index + query; if it breaks, use the in-house scorer. |
| `opentelemetry-exporter-otlp-json-file==0.66b1` is **beta** | Beta API may change. | Capability-4 spike; in-house JSONL `SpanExporter` is the zero-risk fallback. |
| `openinference-instrumentation-langchain==0.1.79` vs `langchain-core==1.6.9` | Its type-check pin is `langchain-core==1.3.3`. | Optional spike only; default to manual spans. |
| Lexical retrieval insufficient for E-09 | BM25 + stemming should surface `diabetic_*` from "known diabetic", but not guaranteed. | Measure E-09 in the capability-1 spike; if it still misses, add the Ollama semantic rerank. |
| Embedding model alongside the extractor on ~6.9 GB RAM | Two models resident could pressure RAM. | Measure with `ollama ps`; load embeddings *after* the extractor unloads (`keep_alive=0`); `all-minilm` (46 MB) is the escape hatch. |
| `rich` currently transitive | A `typer` upgrade could drop it. | Promote to a direct pin now (already the plan). |

## Sources

- **PyPI registry JSON** (`https://pypi.org/pypi/<pkg>/json`) — exact versions for `opentelemetry-sdk` 1.45.1, `opentelemetry-api` 1.45.1, `opentelemetry-exporter-otlp-json-file` 0.66b1, `rich` 15.0.0, `textual` 8.2.8, `scikit-learn` 1.9.1, `numpy` 2.5.3, `rapidfuzz` 3.14.6, `rank-bm25` 0.2.2, `bm25s` 0.3.13, `snowballstemmer` 3.1.1, `sqlite-vec` 0.1.9, `langgraph-checkpoint-sqlite` 3.1.1, `mcp` 2.3.0 — **HIGH** (authoritative registry; cross-checked against the installed `.venv`, which contains these exact versions).
- **`.venv` on-disk inspection** (`site-packages`) — proves `rich-15.0.0`, `opentelemetry_api-1.45.1`, `sqlite_vec-0.1.9`, `langgraph_checkpoint_sqlite-3.1.1`, `langsmith-0.14.5`, `langchain_core-1.6.9` are already present — **HIGH**.
- `https://reference.langchain.com/python/langgraph.checkpoint.sqlite` + `.../aio/AsyncSqliteSaver` — `AsyncSqliteSaver.from_conn_string(...)` context-manager + `graph.compile(checkpointer=saver)` — **MEDIUM** (official LangChain reference; verified via search).
- `https://opentelemetry-python.readthedocs.io/.../exporter/otlp/otlp.html` + `https://opentelemetry.io/docs/specs/otel/protocol/file-exporter` — `FileSpanExporter` writes spans as JSON-Lines to a file, no collector — **MEDIUM** (official OTel docs).
- `https://docs.langchain.com/langsmith/self-host-egress` + `https://reference.langchain.com/python/langsmith/run_trees/configure` — LangSmith is SaaS by default; `enabled='local'` exists but cloud sends spans to `api.smith.langchain.com` — **MEDIUM** (official docs).
- `https://huggingface.co/blog/xhluca/bm25s` + `https://bm25s.github.io` + `https://pypistats.org/packages/rank-bm25` — rank-bm25 is pure-Python+numpy (8.7M downloads/month, unmaintained), bm25s is faster but pulls scipy — **MEDIUM** (vendor blog + stats).
- `https://numpy.org/doc/stable/release/2.0.0-notes.html` — numpy 2.0 removed `np.float_`/`np.complex_` aliases (basis of the rank-bm25 flag) — **HIGH** (official release notes).
- Ollama library pages (`nomic-embed-text` 274 MB, `all-minilm` 46 MB, `mxbai-embed-large` 670 MB, `bge-m3` 1.2 GB) — **MEDIUM** (vendor registry).

---
*Stack research for: TriageDesk v1.1 "Score Uplift" capability additions*
*Researched: 2026-10-10*
