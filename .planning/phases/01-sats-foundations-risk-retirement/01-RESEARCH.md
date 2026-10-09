# Phase 1: SATS Foundations & Risk Retirement - Research

**Researched:** 2026-10-09
**Domain:** Local-first Python agent scaffold — SATS rule substrate (YAML), one typed Pydantic schema, Ollama schema-constrained extraction, MCP v2 server/client wiring
**Confidence:** HIGH for the two Day-1 risks (both retired by live probe this session); MEDIUM for exact package versions (registry-confirmed but flagged SUS by the legitimacy seam); HIGH for domain data shape (source files read directly)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Primary local model = **`qwen3.5:4b`** (already installed, 3.3 GB). Phase 1 must **measure**
  that it runs within the demo machine's RAM budget; a **smaller Qwen fallback is documented and used if
  it cannot**. Record the model licence. — **Reversibility:** reversible — a model swap is a config
  change behind the `llm/` wrapper (SOLID: D), not a code change.
- **D-02:** Extraction contract = **strict JSON schema** via Ollama `format=` + Pydantic validation, from
  the one shared schema module. Not free-form parsing, not native tool-calling.
- **D-03:** Model authority = structure the note, **select discriminators from a closed set**, draft the
  rationale. It **never** does arithmetic, routing, or the colour.
- **D-04:** Adopt **World A** (`langchain.mcp.MCPAdapter`) behind the Phase-1 spike; keep **World B**
  (pinned `langchain-mcp-adapters` + `mcp<2`) as a documented **one-module** fallback. — **Reversibility:**
  costly — swapping worlds touches the MCP wiring module and dependency pins, but is contained by the
  tool-interface boundary.
- **D-05:** Borrowed server = **`jparkerweb/mcp-sqlite`** (npm, **pinned version**); `rusq/mcp-sqlite`
  (Go) is the read-only-posture alternative.
- **D-06:** The gated write goes through **our** `commit_priority`; the borrowed server is **storage**,
  the gate is ours.
- **D-07:** "Retired" evidence bar = committed spike evidence showing **tool-list + one tool call on
  BOTH the owned and borrowed servers**, plus a **RAM measurement** that selects the model.
- **D-08:** Two files — `data/sats_tews.yaml` + `data/sats_discriminators.yaml` — the single source of truth.
- **D-09:** Encode the **adult chart only**; paediatric = **fail-closed abstain stub**.
- **D-10:** Verification = **dual independent transcription diff** + **band-edge unit tests**; residual
  uncertainty flagged in `docs/SATS.md`.
- **D-11:** Discriminator matching = **deterministic alias lookup in YAML with an explicit "no match"**;
  no embeddings in v1.
- **D-12:** Layout: `core/` (pure: schema, scorer, citations) · `llm/` · `mcp/` · `store/` · `graph/`.
- **D-13:** **Guard test**: `core/` must not import `llm|mcp|store` — enforced by an AST test + ruff; CI
  fails on violation (QUAL-02). — **Reversibility:** one-way — the purity boundary is a published
  contract other phases build on; breaking it silently would let the score path depend on the model.
- **D-14:** One Pydantic schema module, imported by MCP contracts, the Ollama `format=`, and graph state.
- **D-15:** Citation helper lives in `core/`, used by every priority.

### the agent's Discretion
- YAML key naming/shape; test framework specifics; spike transcript format; exact pinned versions.

### Deferred Ideas (OUT OF SCOPE)
- Discriminator confidence field + clarifying-question loop (the E-09 fix) — v2.
- Embedding-based discriminator retrieval — v2.
- Referral / department routing tool — v2.
- "Additional investigations" column + SHCP discretion — v2.
- Multilingual clinical lexicon — v2.
- Paediatric SATS charts — v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTAKE-01 | Nurse can enter a case as structured vitals plus a free-text presenting complaint | Typed schema (§Standard Stack, §Code Examples `CaseInput`); the Ollama probe shows free-text → typed fields works with `think:false` + `format=<schema>` |
| INTAKE-02 | System normalizes a case into one validated typed schema (defined once, imported everywhere) | One `core/schema.py` module (D-14); Pydantic 2.14; imported by MCP contracts, Ollama `format=`, and graph state |
| INTAKE-04 | Adult TEWS bands + colour thresholds live **only** in `data/sats_tews.yaml` | Concrete YAML schema (§Pattern 4); DRY guard test + verifier gate; verbatim re-verify (D-10) |
| INTAKE-05 | Discriminators + categories live **only** in `data/sats_discriminators.yaml` | Concrete YAML schema with alias lists + explicit `no_match` (§Pattern 4) |
| SAFE-04 | Version pinning + hashing for prompts, model, scale data, and tool schemas | `uv.lock` + `.python-version`; `core/hashing.py` `sha256` over canonicalised YAML/prompt/schema bytes (§Pattern 6) |
| QUAL-01 | DRY + SOLID enforced — no duplicated SATS values/citations; graph depends on the tool interface | AST purity guard + `grep`-style "no SATS literal outside `data/`" test (§Pattern 6); CONVENTIONS §1/§2 read verbatim |
</phase_requirements>

## Architectural Responsibility Map

This is a **single-process local Python application**. There is no browser/client tier and no network
server tier. The tiers that matter are *process boundaries* (pure core vs model vs MCP subprocess) and
*storage*.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SATS rule substrate (bands, thresholds, discriminators) | Data/Config (file-backed) | — | Single source of truth is `data/*.yaml`; read via one loader, never inlined (`CONVENTIONS.md:10-18`) |
| Case schema + validation (one typed module) | Backend / pure core (`core/`) | — | Zero I/O, zero model/MCP deps — the purity boundary D-13 protects |
| Model extraction (prose → typed fields) | Backend / model edge (`llm/`) | — | Untrusted, stochastic, behind a wrapper; may not be imported by `core/` |
| Owned MCP server (stdio process) | Backend / MCP boundary (`mcp/`) | — | Separate process; exposes tools over stdio; depends on `core/` but not vice-versa |
| MCP tool ingestion into LangGraph | Backend / MCP boundary (`mcp/adapter.py`) | — | One wiring module; the DIP seam for the World A↔B swap |
| Borrowed persistence (case/queue/audit) | Database/Storage | Backend (`store/`) | SQLite via a borrowed MCP server; the gate stays ours (D-06) |
| Purity + DRY guard (tests) | Backend / tests | — | Executable enforcement of QUAL-01/QUAL-02 |

## Summary

Phase 1 builds the rule substrate, the one typed case schema, a reproducible `uv`/Python 3.12 scaffold,
and — most importantly — **retires the two Day-1 unknowns on evidence**. Both unknowns were probed
directly on this machine this session, and one of them produced a non-obvious, load-bearing finding:

1. **The local model works for schema-constrained extraction — but only with `think: false`.** `qwen3.5:4b`
   (family `qwen35`, 4.2B, Q4_K_M, 3.3 GB) is a **reasoning/thinking model**. A plain
   `format=<jsonschema>` request emits the constrained JSON into the `thinking` field and returns an
   **empty `response`** — every tutorial snippet and the Ollama docs' own example will appear to fail.
   Passing `"think": false` returns clean, Pydantic-valid JSON. This is the single most important
   implementation detail in the phase. `[VERIFIED: live probe 2026-10-09 — response empty without
   think:false; valid JSON with think:false]`

2. **The 4B model is RAM-marginal on this host.** With the model loaded, available RAM fell to
   **~428–498 MB**; the Ollama *server itself crashed* mid-probe under a slightly heavier request
   (connection dropped). `ollama ps` shows 3.1 GB resident at `num_ctx=2048`. Warm per-case latency is
   **~21 s** (cold ~40 s) — an order of magnitude above the "seconds" promise (M-7). The roadmap's
   success criterion 3 ("within this machine's RAM budget (measured)") is therefore a **live decision
   point**, not a formality. No smaller Qwen is installed, so the fallback must be pulled.

The MCP side is well-documented in the v2 SDK: `from mcp.server import MCPServer` with `@mcp.tool()`
decorators and `mcp.run(transport="stdio")`. The client path is `langchain.mcp.MCPAdapter` (beta), whose
critical trap is that an `MCPConfig` fleet shares **one protocol era** across all backends — mixing our
modern owned server with the legacy TS borrowed server in one config drops the whole fleet to legacy; a
`ClientGroup` (or two adapters) keeps each on its own era.

**Primary recommendation:** Build the `core/` schema + `data/*.yaml` + `uv` scaffold first (fully
testable offline), then run **one** structured spike that (a) proves `think:false` extraction on
`qwen3.5:4b`, (b) measures RAM/latency and pulls a smaller Qwen if the budget fails, and (c) proves
`MCPAdapter` lists + calls a tool on **both** the owned stdio server and the borrowed `mcp-sqlite@1.0.9`
server — committing the transcript as the D-07 evidence.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python (uv-managed) | `3.12.x` (`requires-python = ">=3.12,<3.13"`) | Runtime | Host is 3.14; every pinned dep declares `>=3.10`; pin via `.python-version` so the deadline clone rebuilds identically (`STACK.md:39`) |
| uv | `>=0.12` (host has **0.5.26 → must upgrade**) | Env + dependency manager | One tool for `pyproject.toml`, `uv.lock`, venv, `uv run`; committed `uv.lock` is the reproducibility guarantee |
| `mcp` | **2.3.0** | Author the *owned* MCP server | Official SDK v2; `from mcp.server import MCPServer` (the v1 `FastMCP` import path is **removed**); speaks 2026-07-28 and serves legacy clients (`STACK.md:41`) |
| `pydantic` | **2.14.0** | One schema module (DRY) | The single source imported by MCP contracts, Ollama `format=`, and graph state (`STACK.md:52`) |
| `pyyaml` | `>=6.0,<7` | Load `data/*.yaml` | The DRY single source for SATS rules; load once, never inline (`STACK.md:58`) |
| `ollama` (Python client) | **0.6.3** | Call the local model | `format=Model.model_json_schema()` drives constrained decoding; **must also pass `think=False`** (see Pitfall 1) |

### Supporting (installed now, consumed by later phases — Phase 1 only *pins* them)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain[mcp]` | **1.4.4** | Ingest MCP tools (`langchain.mcp.MCPAdapter`, **beta**) | Phase-1 spike only; pulls `fastmcp>=4.0.11,<5` transitively |
| `langgraph` | **1.2.14** | Orchestration + approval gate | Phase 3; Phase 1 pins it so `uv.lock` is complete |
| `langgraph-checkpoint-sqlite` | **3.1.1** | Persist paused graph state | Phase 3; separate file from the domain DB |
| `pytest`, `pytest-asyncio` | latest | Test suite incl. band-edge + guard tests | Phase 1 owns the guard tests |
| `ruff`, `mypy` | latest | Lint/format + static typing | Enforce the DRY rule and typed contracts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langchain.mcp.MCPAdapter` (beta) | `langchain-mcp-adapters==0.3.2` (deprecated, pins `mcp<2`) | Only via World B; hard conflict with `mcp==2.3.0` (`STACK.md:122,191`) |
| `qwen3.5:4b` (installed) | smaller Qwen (`qwen3:1.7b` / `qwen2.5:1.5b`) | Forced if the RAM measurement fails; **not installed today — must `ollama pull`** |
| `jparkerweb/mcp-sqlite` (npm) | `rusq/mcp-sqlite` (Go, BSD-2, read-only default) | Read-only posture / single binary; write path then needs a separate surface (`STACK.md:127`) |
| stdlib `hashlib` hash-chain (Phase 3) | `auditchain` (PyPI, MIT) | Built-in checkpoints/HMAC; in-house preferred for a ~40-line module (`STACK.md:128`) |

**Installation (host `uv` must be upgraded first — it is 0.5.26):**
```bash
uv self update                                   # host has 0.5.26; current line is ~0.12
uv init --python 3.12
uv python pin 3.12                               # writes .python-version
uv add "mcp[cli]==2.3.0" "langgraph==1.2.14" "langchain[mcp]==1.4.4" \
       "langgraph-checkpoint-sqlite==3.1.1" "ollama==0.6.3" "pydantic==2.14.0" \
       "pyyaml>=6.0,<7"
uv add --dev pytest pytest-asyncio ruff mypy
uv sync
```

**Version verification (run this session):**
```bash
npm view mcp-sqlite version          # 1.0.9   (latest; modified 2026-04-04)
pip index versions mcp               # mcp (2.3.0); v1 line max = 1.30.0
ollama list                          # qwen3.5:4b (3.3 GB, Q4_K_M, family qwen35, 4.2B)
ollama --version                     # 0.30.6
```
`mcp` 2.3.0 and the v1 ceiling 1.30.0 both match `STACK.md` exactly. `mcp-sqlite` 1.0.9 matches the
pinned version in `STACK.md:107`.

## Package Legitimacy Audit

> Run via `gsd_run query package-legitimacy check`. The seam **cannot read PyPI download counts**
> (`weeklyDownloads: null`), so it flags every PyPI package `SUS` on `too-new` + `unknown-downloads`.
> These are false positives for the official packages (`mcp` = modelcontextprotocol, `langchain`/`langgraph`
> = langchain-ai, `pydantic` = pydantic), all of which are **verified HIGH against official docs** in
> `STACK.md`. The one verdict with a real signal is the borrowed npm server.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `mcp` | PyPI | current | n/a (seam) | modelcontextprotocol.io | SUS | Approved — seam false positive; official SDK, docs-verified |
| `langchain` | PyPI | current | n/a (seam) | docs.langchain.com | SUS | Approved — seam false positive; docs-verified |
| `langgraph` | PyPI | current | n/a (seam) | github.com/langchain-ai/langgraph | SUS | Approved — seam false positive; docs-verified |
| `pydantic` | PyPI | current | n/a (seam) | github.com/pydantic/pydantic | SUS | Approved — seam false positive; docs-verified |
| `ollama` (py) | PyPI | current | n/a (seam) | none (seam) | SUS | Approved — seam false positive; official Ollama client |
| `pyyaml` | PyPI | mature | n/a (seam) | yaml/pyyaml | SUS | Approved — seam false positive; ubiquitous |
| `mcp-sqlite` | npm | ~6 mo | **662/wk** | github.com/jparkerweb/mcp-sqlite | **SLOP** | **Flagged — locked by D-05.** See note. |

**Packages removed due to [SLOP] verdict:** none removed — see reconciliation below.
**Packages flagged as suspicious [SUS]:** `mcp-sqlite` (seam SLOP; locked by D-05).

**Reconciliation for `mcp-sqlite` (honest, do not skip):** the seam returns `SLOP` on two reasons —
`low-downloads` (662/wk) and `suspicious-postinstall`. I read the npm metadata: the postinstall is
`node -e "console.log('…')"` — a **benign console message, not a network call or out-of-tree write**.
The repo (`jparkerweb/mcp-sqlite`) is real and maintained; the package is ~6 months old. The genuine
signal is modest download volume. Because **D-05 locks this server** and a named alternative exists, the
correct action is not silent removal: the planner MUST insert a `checkpoint:human-verify` before the
install, **pin `mcp-sqlite@1.0.9`** (never `npx -y mcp-sqlite`), and record `rusq/mcp-sqlite` (Go,
BSD-2) as the pre-approved fallback if the handshake fails. `[VERIFIED: npm registry metadata 2026-10-09]`

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────────────────────────────────────┐
                │  TriageDesk (single local Python process, no egress)       │
                │                                                           │
  nurse note ──▶│  llm/  (model edge, untrusted output)                     │
  (vitals +     │    OllamaClient.extract(note) ──format=schema, think=false │
   free text)   │        │  Pydantic-validated typed fields (or fallback)    │
                │        ▼                                                   │
                │  core/ (PURE — no llm/mcp/store imports; D-13 guard)       │
                │    schema.py ── rules/loader.py ── citation.py            │
                │        │            ▲                                     │
                │        │            │ reads once at startup               │
                │        │       data/sats_tews.yaml                        │
                │        │       data/sats_discriminators.yaml              │
                │        ▼                                                   │
                │  mcp/  (process boundary)                                  │
                │    server.py  ──stdio──▶  owned tools (normalize/match/…)  │
                │    adapter.py ──MCPAdapter──▶ LangChain tools (Phase 3)    │
                │        │                                                   │
                │        └──stdio──▶ borrowed mcp-sqlite (storage: queue+audit)│
                └──────────────────────────────────────────────────────────┘
```

Phase 1 delivers the **left two blocks** (`core/` + `data/`) fully, a **stub** of `mcp/server.py`, and the
**spike transcript** proving `adapter.py` can list + call tools on both servers. The model edge is proven
but not wired into a graph yet.

### Recommended Project Structure
```
TriageDesk/
├── pyproject.toml          # exact pins (uv-managed)
├── uv.lock                 # committed — the deadline-reproducibility artifact
├── .python-version         # "3.12"
├── NOTICE                  # third-party licences incl. qwen3.5:4b + SATS attribution (SAFE-04/P15)
├── data/
│   ├── sats_tews.yaml              # parameter→bands→points + TEWS→colour thresholds
│   └── sats_discriminators.yaml    # discriminator→category→citation (+ alias lists)
├── docs/SATS.md            # human-readable reference (re-verify flags)
├── src/triagedesk/
│   ├── __init__.py
│   ├── core/               # PURE: schema, rules loader, citation, hashing — no llm/mcp/store imports
│   │   ├── schema.py       # the ONE Pydantic module (D-14)
│   │   ├── rules.py        # YAML loader + typed rule model
│   │   ├── citations.py    # the ONE citation helper (D-15)
│   │   └── hashing.py      # canonical sha256 over data/prompts/schemas (SAFE-04)
│   ├── llm/
│   │   └── client.py       # OllamaClient wrapper (format=schema, think=False, validate, fallback)
│   ├── mcp/
│   │   ├── server.py       # owned MCPServer stub (≥1 tool now; 5 by Phase 2)
│   │   └── adapter.py      # ONE wiring module: load_tools() → list[BaseTool] (World A↔B seam)
│   ├── store/              # Phase 3 (borrowed mcp-sqlite wiring)
│   └── graph/              # Phase 3 (LangGraph)
├── scripts/
│   ├── spike_model.py      # D-07 model evidence (RAM + schema round-trip + timing)
│   └── spike_mcp.py        # D-07 MCP evidence (list + call on owned AND borrowed)
└── tests/
    ├── test_purity.py      # AST guard: core/ must not import llm|mcp|store (QUAL-02)
    ├── test_no_duplicated_sats.py  # no TEWS/discriminator/citation literal outside data/ (QUAL-01)
    └── test_sats_bands.py  # band-edge tests on both sides of every boundary (P5)
```

### Pattern 1: Schema-constrained extraction — `format=<schema>` **and** `think=False`
**What:** Bind the model to a JSON schema and force it to answer *directly* (not to "think" first).
**When to use:** Every model call in the system (D-02); the model never computes a number (D-03).
**Why the `think` flag is mandatory here:** `qwen3.5:4b` is a reasoning model. Without `think:false`, the
constrained JSON is emitted as *reasoning* and `response` is empty.

```python
# Source: docs.ollama.com/capabilities/structured-outputs (format usage) +
#         live probe on this host (the think=False requirement). VERIFIED 2026-10-09.
import ollama
from triagedesk.core.schema import ExtractionResult   # the ONE schema module (D-14)

def extract(note: str) -> ExtractionResult:
    resp = ollama.generate(
        model="qwen3.5:4b",
        prompt=EXTRACTION_PROMPT.format(note=note, schema=ExtractionResult.model_json_schema()),
        format=ExtractionResult.model_json_schema(),   # grammar-constrained decoding
        think=False,                                   # REQUIRED for qwen3.5:4b — else response == ""
        options={"temperature": 0, "seed": 42, "num_ctx": 2048},
    )
    return ExtractionResult.model_validate_json(resp.response)   # never trust unvalidated output
```
> The docs also advise passing the schema string **in the prompt** to ground the model, and using
> `temperature=0`. `[CITED: docs.ollama.com/capabilities/structured-outputs]`

### Pattern 2: Owned MCP server (SDK v2, stdio)
**What:** A decorator-built `MCPServer` exposing tools over stdio.
**When to use:** The challenge-required owned tools (TOOL-01…05, full set in Phase 2; a stub here).

```python
# Source: python-sdk docs — whats-new.md + migration.md (v2). VERIFIED via official docs 2026-10-09.
from mcp.server import MCPServer               # v1: from mcp.server.fastmcp import FastMCP (REMOVED)
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from triagedesk.core.schema import CaseInput, ExtractionResult

mcp = MCPServer("triagedesk-triage", version="0.1.0")   # keep name positional; pass rest by keyword

@mcp.tool()
async def normalize_case(raw_note: str, ctx: Context) -> ExtractionResult:
    """Parse a triage note into the typed case schema. Read-only."""
    try:
        return _extract(raw_note)
    except ValueError as exc:
        raise ToolError(str(exc))              # ToolError text reaches the model; other exc → -32603

if __name__ == "__main__":
    mcp.run(transport="stdio")                 # transport config lives on run(), not the constructor
```
**v2 gotchas (all docs-verified):** the input schema comes from type hints; `get_context()` is gone —
declare `ctx: Context`; transport kwargs moved to `run()` (`MCPServer("x", port=…)` is a `TypeError`);
a sync `def` handler runs on a worker thread; a bare `list`/`dict` return is fine on `MCPServer` (only the
low-level `Server` requires full result types). `[CITED: python-sdk whats-new.md]`

### Pattern 3: MCP client into LangGraph — one wiring module, era-aware
**What:** `MCPAdapter` discovers and adapts MCP tools into LangChain tools.
**When to use:** Phase-1 spike now; the graph in Phase 3.

```python
# Source: docs.langchain.com/oss/python/langchain/mcp + .../connections. VERIFIED via official docs.
from pathlib import Path
from langchain.mcp import MCPAdapter           # beta — LangChainBetaWarning once per process

async def load_tools():
    async with MCPAdapter(Path("src/triagedesk/mcp/server.py")) as owned:
        owned_tools = await owned.list_tools()          # our v2 server over stdio
    async with MCPAdapter(
        {"mcpServers": {"sqlite": {"command": "npx",
                                   "args": ["-y", "mcp-sqlite@1.0.9", "/abs/triage.db"]}}}
    ) as borrowed:
        borrowed_tools = await borrowed.list_tools()    # legacy TS server — namespaced `sqlite_*`
    return owned_tools + borrowed_tools
```
**Critical failure mode (docs-verified):** an `MCPConfig` fleet negotiates **one protocol era for every
backend** — adding the legacy borrowed server drops the *whole fleet* (including our modern owned server)
to the legacy era. If the owned/borrowed servers must keep different eras, use a `fastmcp.client.ClientGroup`
with a per-server `Client(mode="legacy"|"auto")`, or two separate `MCPAdapter` contexts (as above).
`[CITED: docs.langchain.com/oss/python/langchain/mcp/connections]`

**Two more traps:**
- `MCPAdapter(server_object)` (in-process) expects a **`fastmcp`** server, not the `mcp.server.MCPServer`.
  Launch our owned server as a **stdio subprocess** via `Path("…/server.py")` — the realistic spike path.
- `create_agent(...)` needs a LangChain **chat model**. The stack pins the raw `ollama` client, **not**
  `langchain-ollama`; a full `create_agent` round-trip on the local model therefore needs an extra dep.
  **Recommendation:** scope the Phase-1 spike to `list_tools()` + direct tool invocation; defer
  `create_agent` to Phase 3 (or add `langchain-ollama` then). Flagged in Open Questions.

### Pattern 4: SATS rule substrate as YAML (single source of truth)
**What:** Bands and discriminators live only in `data/*.yaml` (`INTAKE-04/05`, `CONVENTIONS.md:12-13`).
**When to use:** Always — the scorer (Phase 2) reads it; nothing else may hard-code a threshold.

`data/sats_tews.yaml` (proposed shape — key naming is the agent's discretion):
```yaml
# Adult TEWS. Source: SATS Training Manual 2012 (EMSSA). Bands are INCLUSIVE [min, max].
# Re-verified verbatim 2026-10-09 — see docs/SATS.md verification flag.
version: 1
citation: "SATS Training Manual 2012 (EMSSA), adult TEWS"
parameters:
  respiratory_rate:
    unit: breaths/min
    bands:
      - {points: 0, min: 9,  max: 14}
      - {points: 1, min: 15, max: 20}
      - {points: 2, min: 21, max: 29}
      - {points: 3, max: 8}     # <9
      - {points: 3, min: 30}    # >=30
  heart_rate:
    unit: bpm
    bands:
      - {points: 0, min: 51, max: 100}
      - {points: 1, min: 41, max: 50}
      - {points: 1, min: 101, max: 110}
      - {points: 2, min: 111, max: 129}
      - {points: 3, max: 40}
      - {points: 3, min: 130}
  systolic_bp:
    unit: mmHg
    bands:
      - {points: 0, min: 101, max: 199}
      - {points: 1, min: 81,  max: 100}
      - {points: 2, min: 71,  max: 80}
      - {points: 3, max: 70}
      - {points: 3, min: 200}
  temperature:
    unit: celsius
    bands:
      - {points: 0, min: 35.0, max: 38.4}   # NOTE: 1-point band is EMPTY in the manual — re-verify (P5)
      - {points: 2, max: 34.9}
      - {points: 2, min: 38.5}
  mobility: {bands: [{points: 0, value: walking}, {points: 1, value: with_help}, {points: 2, value: stretcher}]}
  avpu:     {bands: [{points: 0, value: alert}, {points: 1, value: voice}, {points: 2, value: pain}, {points: 3, value: unresponsive}]}
  trauma:   {bands: [{points: 0, value: no}, {points: 1, value: yes}]}
tews_to_colour:                     # docs/SATS.md:58-63
  - {colour: GREEN,  min: 0, max: 2}
  - {colour: YELLOW, min: 3, max: 4}
  - {colour: ORANGE, min: 5, max: 6}
  - {colour: RED,    min: 7}
target_times:                       # docs/SATS.md:34-40
  RED: {target: "Immediate", destination: "Resuscitation room"}
  ORANGE: {target: "< 10 min", destination: "Majors"}
  YELLOW: {target: "< 1 hour", destination: "Majors"}
  GREEN: {target: "< 4 hours", destination: "Designated area"}
  BLUE: {target: "< 2 hours", destination: "Doctor for certification"}
out_of_scope:                       # fail-closed predicate AS DATA (P10; D-09)
  adult_min_age_years: 12
  adult_min_height_cm: 150          # adult = age > 12 OR height > 150 cm
  on_missing_age: abstain           # never default to adult
```
> Bands above are transcribed from `docs/SATS.md:46-54` and `:58-63` (read this session). They are the
> **design transcription** and MUST be re-verified verbatim against the manual (D-10) — do not treat this
> block as the verified artefact. `[VERIFIED: docs/SATS.md:46-54,58-63 — verbatim quote below]`

Verbatim source (read this session):
```
docs/SATS.md:48-54
| Respiratory rate | 9–14 | 15–20 | 21–29 | < 9 or ≥ 30 |
| Heart rate | 51–100 | 41–50 or 101–110 | 111–129 | < 41 or ≥ 130 |
| Systolic BP | 101–199 | 81–100 | 71–80 | < 71 or ≥ 200 |
| Temperature | 35.0–38.4 °C | — | < 35 or > 38.4 | — |
docs/SATS.md:58-63
| **0, 1, 2** | 🟢 Green (routine) |
| **3 or 4** | 🟡 Yellow (urgent) |
| **5 or 6** | 🟠 Orange (very urgent) |
| **7 or more** | 🔴 Red (emergency) |
```

`data/sats_discriminators.yaml` (proposed shape):
```yaml
version: 1
citation: "SATS Training Manual 2012 (EMSSA), adult clinical discriminators"
categories:
  emergency:   {colour: RED,    citation_ref: "SATS Table: Emergency discriminators"}
  very_urgent: {colour: ORANGE, citation_ref: "SATS Table: Very urgent discriminators"}
  urgent:      {colour: YELLOW, citation_ref: "SATS Table: Urgent discriminators"}
discriminators:
  - id: acute_shortness_of_breath
    category: very_urgent
    label: "Acute shortness of breath"
    aliases: ["short of breath", "sob", "breathless", "can't breathe", "difficulty breathing"]
  - id: chest_pain
    category: very_urgent
    label: "Chest pain"
    aliases: ["chest pain", "pain in chest", "chest tightness"]
  # ... all adult discriminators from docs/SATS.md:83-103, one entry each
no_match: {result: none, warning: "no discriminator matched — coverage gap (E-09)"}
```
> Discriminator strings and categories come from `docs/SATS.md:83-103` (read this session); alias lists
> are authored (the agent's discretion) and must be broad enough to cover the eval complaints.
> Matching is a **deterministic alias lookup with an explicit `no_match`** (D-11) — never an LLM call.

### Anti-Patterns to Avoid
- **Calling the model without `think:false`.** Silent empty `response`; looks like a broken schema. (Pitfall 1)
- **Hard-coding any TEWS band / discriminator / citation outside `data/`.** A defect per `CONVENTIONS.md:20`
  ("Any TEWS threshold, discriminator string, or citation that appears in more than one place is a defect.")
- **`from mcp.server.fastmcp import FastMCP`.** Import path removed in v2 — fails at import.
- **One `MCPConfig` for both servers.** Collapses the fleet to one protocol era (see Pattern 3).
- **`npx -y mcp-sqlite` unpinned.** Fetches `latest` at clone time — breaks deadline reproducibility.
- **Making `match_discriminators` an LLM call.** Non-deterministic colours (P7); the matcher is a data lookup.
- **Importing `llm`/`mcp`/`store` from `core/`.** Breaks the D-13 purity contract; caught by the AST guard.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-schema-constrained decoding | Prompt-only "please return JSON" + regex repair | Ollama `format=<schema>` + Pydantic validation | Grammar-constrained decoding makes malformed JSON structurally impossible (`STACK.md:142`) |
| MCP server plumbing | Custom JSON-RPC / stdio framing | `mcp==2.3.0` `MCPServer` decorators | Handshake, transport, schema generation are solved |
| MCP tool ingestion | Custom MCP client | `langchain.mcp.MCPAdapter` | Transport inference, protocol negotiation, lifecycle |
| SQLite persistence + schema | A hand-rolled DB layer | borrowed `mcp-sqlite@1.0.9` | "Persistence, schema and query safety are solved" (`DECISIONS.md` D5) |
| YAML→typed rule model | Hand-parsing dicts everywhere | One `core/rules.py` loader returning typed Pydantic models | DRY: one parse, one validation, one place to add a rule |
| Canonical hashing of data/prompts/schemas | Ad-hoc `hash(str(dict))` | One `core/hashing.py` with sorted keys + fixed encoding | Dict key order must not change the hash (PITFALLS §Integration Gotchas) |
| Import-purity enforcement | Eyeballing imports at review | AST test + ruff | QUAL-01/02 must be **executable**, not advisory |

**Key insight:** In this domain the expensive mistakes are *not* code you didn't write — they are values
duplicated in two places and stochastic steps that look deterministic. Every "don't hand-roll" here is
really "keep the single source of truth single".

## Common Pitfalls

### Pitfall 1 (P13/P5-adjacent, phase-critical): the thinking model swallows `format=` output
**What goes wrong:** `format=<schema>` returns `response: ""`; the JSON appears in the `thinking` field.
A developer concludes the schema is wrong or the model is broken.
**Why it happens:** `qwen3.5:4b` is a reasoning model; its chat template routes generated tokens into a
reasoning channel unless told not to.
**How to avoid:** Pass `think: false` (HTTP) / `think=False` (Python client) on **every** call. Assert in
the wrapper that `response` is non-empty and `json.loads`-able before returning.
**Warning signs:** empty `response` with a non-zero `eval_count`; valid-looking JSON in `thinking`.
`[VERIFIED: live probe 2026-10-09]`

### Pitfall 2 (P13): RAM fit is marginal and unmeasured
**What goes wrong:** the demo machine OOMs or the Ollama server disconnects mid-run.
**Why it happens:** the box has 6.9 GB total; the 4B model is 3.1 GB resident; available RAM dropped to
~428–498 MB with the model loaded, and the server **actually dropped a connection** under a heavier
request this session.
**How to avoid:** Run the `scripts/spike_model.py` measurement (`ollama ps` SIZE, `free -m` available,
`ps -o rss` of the ollama runner, cold + warm latency) **before** committing to the 4B. If available RAM
< ~1 GB with the model loaded, `ollama pull` a smaller Qwen and run it end-to-end (roadmap SC3 requires
the fallback to be *run*, not just named).
**Warning signs:** `available` < 1 GB in `free -m` with the model loaded; swap in active use; a dropped
`/api/generate` connection. `[VERIFIED: live probe 2026-10-09]`

### Pitfall 3 (P5): band-edge and unit ambiguity
**What goes wrong:** an inclusive/exclusive slip moves a patient one colour; a Fahrenheit temperature
(`98.6`) scored as Celsius sits in the 0-point band while the patient is febrile.
**Why it happens:** bands transcribed by hand; the `docs/SATS.md` temperature row itself has a **blank**
in the 1-point column (`docs/SATS.md:52`) — a transcription risk that must actually be checked.
**How to avoid:** table-test **every boundary on both sides** (RR 8/9/14/15/20/21/29/30; HR 40/41/50/51/
100/101/110/111/129/130; SBP 70/71/80/81/100/101/199/200; T 34.9/35.0/38.4/38.5). Make the schema
**unit-carrying** and **reject** implausible values (T `98.6` with unit `C` → re-measure, not score).
Store boundaries once, in `data/` (DRY).
**Warning signs:** tests cluster mid-band; no unit field on temperature. `[VERIFIED: docs/SATS.md:46-54]`

### Pitfall 4 (P11): the test set is curated to pass
**What goes wrong:** the YAML is tuned until cases go green — overfitting to the author's own mental model.
**Why it happens:** one author writes the rules and the cases; expected colours are guideline-derived, not
clinician-adjudicated (`EVALS.md:114-122`).
**How to avoid:** **freeze the expected colours from `docs/SATS.md` before the scorer exists** (this
phase), and treat any later change to an expected colour as a reviewable event with a written reason.
Plan ≥2 held-out cases. Keep E-09 (`EVALS.md:77`, expected ORANGE) as the declared failure — do not tune
the YAML to fix it.
**Warning signs:** every case's expected colour matches the scorer output; `git log` on `data/*.yaml`
shows post-eval edits with no rationale. `[VERIFIED: EVALS.md:69-82]`

### Pitfall 5 (P15): SATS / MTS licensing and attribution
**What goes wrong:** wholesale reproduction of the manual's tables/prose into an Apache-2.0 repo raises a
copyright question; MTS would be a clear breach.
**Why it happens:** "openly published" ≠ "free to redistribute".
**How to avoid:** keep the YAML to **functional facts** (bands, discriminator labels → category, short
citations) — no manual prose, figures, or layout. Add a `NOTICE` with the EMSSA URL, the "clinical content
cited, not redistributed" line, and the **`qwen3.5:4b` licence** (record it; the STACK's Apache-2.0 note
applies to Qwen2.5 1.5B/0.5B, *not* to 3B/72B — confirm the exact tag's licence before shipping).
**Warning signs:** YAML contains sentences copied from the manual; no `NOTICE`; a model tag shipped
without a licence line. `[CITED: DECISIONS.md:148-157]`

### Pitfall 6 (M-7/M-8): latency blows the "seconds" promise
**What goes wrong:** the brief promises *seconds*; measured warm latency is **~21 s/case** (cold ~40 s) on
CPU, and RAM headroom is ~0.5 GB.
**Why it happens:** 4B model on CPU with a reasoning-capable template; no pre-warm.
**How to avoid:** pre-warm the model before the demo; keep `num_ctx` small (2048); route structured input
through the deterministic path by default; measure on the demo machine (this phase's spike captures the
number honestly). `[VERIFIED: live probe 2026-10-09]`

## Code Examples

### The one schema module (`core/schema.py`) — D-14
```python
# Source: project D-14 + Ollama structured-outputs docs. This module is imported by
# mcp contracts, the Ollama format=, and graph state — the DRY single source.
from typing import Literal
from pydantic import BaseModel, Field

class CaseInput(BaseModel):
    """What the nurse provides (INTAKE-01). Every vital nullable — never impute (P4)."""
    age_years: int | None = None
    height_cm: float | None = None
    respiratory_rate: int | None = None
    heart_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None          # captured, not scored (docs/SATS.md:73)
    temperature_c: float | None = None
    spo2: int | None = None                  # captured, not scored (docs/SATS.md:71)
    mobility: Literal["walking", "with_help", "stretcher"] | None = None
    avpu: Literal["alert", "voice", "pain", "unresponsive"] | None = None
    trauma: bool | None = None
    complaint: str = ""                      # UNTRUSTED free text (SECURITY.md T-1)

class ExtractionResult(BaseModel):
    """What the model may return — schema-constrained, then validated. No numbers computed here."""
    case: CaseInput
    matched_discriminator_ids: list[str] = Field(default_factory=list)
    no_discriminator_matched: bool = False   # coverage signal (P1) — v1 field, cheap
```
> The model **fills enum fields and selects discriminator ids from the closed set**; it never computes
> TEWS or a colour (D-03). `Literal`/enum constraints become JSON-schema `enum`s and are enforced by
> `format=`. `[VERIFIED: live probe — enum `avpu` returned "A"; schema `["integer","null"]` accepted null]`

### AST purity guard (`tests/test_purity.py`) — QUAL-01/QUAL-02, D-13
```python
# Source: project D-13. stdlib only — no extra dependency needed.
import ast, pathlib

FORBIDDEN = {"llm", "mcp", "store"}

def _imports(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots

def test_core_is_pure():
    offenders = {}
    for py in pathlib.Path("src/triagedesk/core").rglob("*.py"):
        bad = _imports(py) & FORBIDDEN
        if bad:
            offenders[str(py)] = sorted(bad)
    assert not offenders, f"core/ must not import {FORBIDDEN}: {offenders}"
```
Pair this with a ruff rule so the failure is caught at lint time too, e.g. in `pyproject.toml`:
```toml
[tool.ruff.lint]
select = ["TID"]
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"triagedesk.llm".msg = "core/ must not depend on the model (D-13)"
"triagedesk.mcp".msg = "core/ must not depend on MCP (D-13)"
"triagedesk.store".msg = "core/ must not depend on storage (D-13)"
```
> A **second** guard test should assert no TEWS band/discriminator/citation literal appears outside
> `data/` (the CONVENTIONS verifier gate, `CONVENTIONS.md:44`). Implementation: load every string leaf
> from `data/*.yaml` and assert none of the discriminating ones occur in `src/**.py`.

### Model spike (`scripts/spike_model.py`) — D-07 evidence
```python
# Records RAM fit + a schema round-trip; the artefact that selects 4B vs fallback.
import json, subprocess, time, ollama
from triagedesk.core.schema import ExtractionResult

def _ram() -> dict:
    free = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
    ps   = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout
    return {"free_m": free, "ollama_ps": ps}

NOTE = "RR 24, HR 118, BP 108/70, temp 38.9, alert, cough and fast breathing"
out = {"ram_before": _ram()}
t0 = time.time()
resp = ollama.generate(model="qwen3.5:4b", prompt=..., think=False,
                       format=ExtractionResult.model_json_schema(),
                       options={"temperature": 0, "seed": 42, "num_ctx": 2048})
out["elapsed_s"] = round(time.time() - t0, 1)
out["response_empty"] = resp.response == ""                 # MUST be False
out["parsed"] = ExtractionResult.model_validate_json(resp.response).model_dump()
out["ram_after"] = _ram()
print(json.dumps(out, indent=2))
```
Commit the JSON output as the D-07 model evidence.

### MCP spike (`scripts/spike_mcp.py`) — D-07 evidence
```python
# Lists + calls one tool on BOTH servers; commit the transcript.
import asyncio
from pathlib import Path
from langchain.mcp import MCPAdapter

async def main():
    async with MCPAdapter(Path("src/triagedesk/mcp/server.py")) as owned:
        tools = await owned.list_tools()
        print("OWNED TOOLS:", [t.name for t in tools])
        # call one tool by name and print the result
    async with MCPAdapter({"mcpServers": {"sqlite": {
            "command": "npx", "args": ["-y", "mcp-sqlite@1.0.9", "/abs/path/triage.db"]}}}) as borrowed:
        tools = await borrowed.list_tools()
        print("BORROWED TOOLS:", [t.name for t in tools])   # expect db_info, list_tables, query, …
    # If either handshake fails → World B trigger (see below).

asyncio.run(main())
```

### World-B fallback wiring module (`mcp/adapter.py`) — D-04, one-module swap
```python
# The graph depends only on load_tools() -> list[BaseTool]; the world swap is contained here.
# World A (current): langchain.mcp.MCPAdapter + mcp==2.3.0
# World B (fallback): langchain-mcp-adapters.MultiServerMCPClient + mcp>=1.24,<2 + FastMCP v1 server
```
The World-B trigger is explicit: if `MCPAdapter` raises on import, `list_tools()` returns nothing, or the
borrowed handshake fails after the `rusq` alternative is tried, swap **this one file** and the two pins
(`mcp<2`, `langchain-mcp-adapters==0.3.2`) and re-author the owned server with the v1 `FastMCP` API.
Budget ~1 day (`STACK.md:153`).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` | SDK v2 | v1 import path **removed** — every tutorial snippet fails |
| `langchain-mcp-adapters` | `langchain.mcp.MCPAdapter` | LangChain 1.4.0 | Adapter is beta; the old package pins `mcp<2` (hard conflict) |
| `initialize` handshake | `server/discover` + per-request `_meta` (2026-07-28) | Protocol 2026-07-28 | No session; both eras served from one server |
| `httpx` / `httpx-sse` | `httpx2` | SDK v2 | `except httpx.*` blocks silently stop matching; TLS via OS trust store |
| WebSocket MCP transport | stdio / Streamable HTTP | SDK v2 | WS removed, never in spec |

**Deprecated/outdated:**
- Ollama **tool-calling** as the primary extraction path — unreliable at 4B on CPU; use structured outputs.
- Free-form ReAct agent — the project uses an explicit graph (`DECISIONS.md` D10).
- Official `modelcontextprotocol/sqlite` server — archived; use `jparkerweb/mcp-sqlite` or `rusq/mcp-sqlite`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A smaller Qwen suitable as fallback (e.g. `qwen3:1.7b`, `qwen2.5:1.5b`) is pullable from the Ollama registry and fits the RAM budget | Standard Stack / Pitfall 2 | Cannot satisfy roadmap SC3 ("fallback run end-to-end"); demo left with a marginal 4B |
| A2 | The exact `qwen3.5:4b` licence permits redistribution/use; it will be recorded in `NOTICE` | Pitfall 5 / SAFE-04 | Challenge eligibility / DQ-8 disclosure risk |
| A3 | `jparkerweb/mcp-sqlite@1.0.9` speaks a protocol era the FastMCP-4 client can negotiate | Pattern 3 | Borrowed-server handshake fails → World B or `rusq/mcp-sqlite` |
| A4 | The borrowed server's tool names are `db_info, list_tables, get_table_schema, create_record, read_records, update_records, delete_records, query` | Pattern 3 | Startup tool-set assertion would fail; adjust expected list |
| A5 | `create_agent` is not required for the Phase-1 spike (direct tool calls suffice) | Pattern 3 | If required, add `langchain-ollama` (not currently pinned) |

**Note:** A4 is `[CITED: github.com/jparkerweb/mcp-sqlite README]` but not confirmed against the running
server this session — verify in the spike.

## Open Questions (RESOLVED)

All four questions below are resolved by the Phase-1 plans; each carries its resolution and the plan/task
that implements it.

1. **Is the 4B within budget, or must the fallback be pulled?** — **RESOLVED (Plan 01, task 2).** The plan
   implements this as an **in-plan measurement gate**: `scripts/spike_model.py` measures RAM/latency on
   `qwen3.5:4b`, and the smaller-Qwen fallback is pulled and run end-to-end **unconditionally** as Plan-B
   evidence, so Roadmap SC3 is satisfied regardless of the gate's outcome. The gate only decides which model
   is the *default*.
   - What we know: warm ~21 s, ~0.5 GB available with the model loaded, server dropped a connection under load.
   - Recommendation adopted: run `scripts/spike_model.py` first; treat the result as a **gate**; the fallback
     is run end-to-end either way.

2. **Which protocol era does the borrowed server speak, and does one `MCPConfig` work?** — **RESOLVED
   (Plan 03, spike task).** The plan spikes **two separate adapter contexts** (never one merged `MCPConfig`),
   which keeps the modern owned server and the legacy borrowed server on their own protocol eras and avoids
   era collapse. If the borrowed handshake still fails after the `rusq/mcp-sqlite` alternative, the documented
   one-module World-B fallback is triggered.
   - What we know: `MCPConfig` collapses the fleet to one era; `ClientGroup` keeps them separate.
   - Recommendation adopted: two adapters; prefer **two adapters / `ClientGroup`** to avoid era collapse.

3. **Does the Phase-1 spike need `create_agent`, or only `list_tools` + a tool call?** — **RESOLVED
   (Plans 01 + 03).** The plans scope the spike to `list_tools` + direct tool invocation; `create_agent` and
   `langchain-ollama` are deferred to Phase 3, matching D-07 ("tool-list + one tool call").
   - Recommendation adopted: scope to `list_tools` + direct tool call.

4. **What is the canonical key order for the SATS `data/*.yaml` hashes (SAFE-04)?** — **RESOLVED (Plan 04,
   task 1).** `core/hashing.py` serialises the loader's *normalised* output with `sort_keys=True` + a fixed
   UTF-8 encoding before `sha256`; raw file bytes are never hashed, so comment/whitespace edits do not churn
   the hash.
   - Recommendation adopted: one `core/hashing.py` using `json.dumps(..., sort_keys=True)` + UTF-8 bytes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Ollama server | Local model inference | ✓ | 0.30.6 (systemd `ollama.service`) | — |
| `qwen3.5:4b` | Primary extraction (D-01) | ✓ | 3.3 GB, Q4_K_M, 4.2B, ctx 256K | smaller Qwen (must pull — see A1) |
| uv | Env/deps | ✓ | **0.5.26 (too old)** | `uv self update` → ~0.12 |
| Python (host) | Runtime | ✓ | 3.14.4 | pin 3.12 via `uv` (host 3.14 avoided) |
| Node / npx | Borrowed stdio server | ✓ | 22.14.0 / 11.8.0 | — |
| `mcp-sqlite` | Borrowed storage | not installed | — | `rusq/mcp-sqlite` (Go, BSD-2) |
| RAM | Model + app | ⚠ marginal | 6.9 GB total; **~0.4–3.3 GB available** | smaller model; free background apps |
| gsd-tools in repo | GSD seams | ✗ (global only) | global `@opengsd/gsd-core` 1.16.0 | use global `gsd_run` |

**Missing dependencies with no fallback:**
- A **smaller Qwen fallback** is not installed. Roadmap SC3 requires it be run end-to-end → the plan must
  include an `ollama pull <small-qwen>` task (and confirm the tag exists).

**Missing dependencies with fallback:**
- `mcp-sqlite` not yet fetched — pinned `npx mcp-sqlite@1.0.9` fetches on demand; `rusq/mcp-sqlite` is the
  pre-approved alternative.
- Host `uv` 0.5.26 — upgrade with `uv self update` before `uv init`.

## Security Domain

`security_enforcement: true` (`config.json:48`), ASVS level 1. Phase 1 is mostly data + scaffold, but it
establishes the trust boundaries the later phases depend on.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Phase 3) | Approver auth is a declared production gap (`SECURITY.md:77-78`) |
| V3 Session Management | no | — |
| V4 Access Control | no (Phase 3) | Tool allowlist + gated write (`SECURITY.md:62-66`) |
| V5 Input Validation | **yes** | Pydantic schema; untrusted complaint parsed to typed fields; reject implausible units |
| V6 Cryptography | **yes** | `hashlib.sha256` for data/prompt/schema hashing — never hand-roll a primitive |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via free-text complaint (T-1) | Tampering | Complaint is **data**; parsed to typed fields; colour computed deterministically; schema-constrained extraction (`SECURITY.md:40`) |
| Untrusted model/tool output (T-2, T-7) | Tampering | Pydantic-validate every model and tool result; reject on failure |
| Supply-chain (model/tool provenance) (T-10) | Tampering | Pin + hash model tag, prompts, SATS YAML, tool schemas (`SAFE-04`); `uv.lock` committed |
| Data exfiltration (T-5) | Information Disclosure | No network egress; local model + tools; synthetic data only |
| Malicious borrowed MCP server (T-6) | Elevation | Least privilege; no credentials; **pinned source** (`mcp-sqlite@1.0.9`); not OS-sandboxed (`SECURITY.md:100`) |

## Sources

### Primary (HIGH confidence)
- `docs/SATS.md:46-63,83-103` — adult TEWS bands, TEWS→colour thresholds, discriminator lists (read this session; verbatim quotes above).
- `CONVENTIONS.md:10-20,44` — the single-source-of-truth table and verifier gate (read this session).
- `.planning/REQUIREMENTS.md:13-17,82-83` + `.planning/ROADMAP.md:30-40` — phase requirements and success criteria.
- `EVALS.md:62-82,114-122` — eval cases (incl. E-09), frozen-expectation guidance.
- `DECISIONS.md` D1–D18; `SECURITY.md` T-1…T-10; `ARCHITECTURE.md` §4/§8/§9.
- `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/docs/whats-new.md` — SDK v2 `MCPServer`, protocol 2026-07-28, transport/`run()` changes.
- `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/docs/migration.md` — v1→v2 renames, `ToolError`, `mcp-types`.
- `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/docs/get-started/testing.md` — in-memory `Client(mcp)` smoke test.
- `https://docs.ollama.com/capabilities/structured-outputs` — `format=<schema>`, Pydantic `model_json_schema()`.
- `https://docs.langchain.com/oss/python/langchain/mcp` + `.../connections` — `MCPAdapter`, targets, `MCPConfig`, `ClientGroup`, protocol-era collapse.
- **Live probes this session** — `qwen3.5:4b` `think:false` extraction (valid JSON); default `format=` (empty `response`); RAM/latency measurement; npm/PyPI registry versions.

### Secondary (MEDIUM confidence)
- `https://github.com/jparkerweb/mcp-sqlite` README — borrowed server tool surface (A4).
- `.planning/research/STACK.md` / `SUMMARY.md` / `PITFALLS.md` — prior research, consistent with this session's findings.
- `gsd_run query package-legitimacy check` — verdicts (with the false-positive caveat documented above).

### Tertiary (LOW confidence)
- Smaller-Qwen fallback tag availability (A1) — not verified by pull this session; confirm before planning the fallback task.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM-HIGH — registry-confirmed versions + official docs; seam flags SUS (false positives) documented.
- Architecture: HIGH — the two Day-1 risks were retired by live probe; MCP patterns are docs-verified.
- Pitfalls: HIGH — P5/P11/P13/P15 are project-derived and now reinforced by direct measurement.
- Code examples: HIGH — schema/MCP/adapter shapes are from official docs; the `think:false` requirement is probe-verified.

**Research date:** 2026-10-09
**Valid until:** 2026-10-16 (short — fast-moving MCP/LangChain beta surface, and the model/RAM decision is live)

---

*Phase: 01-sats-foundations-risk-retirement*
*Research completed: 2026-10-09*
*Ready for planning: yes — with the model-fit measurement as an explicit in-plan gate*
