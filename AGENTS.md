<!-- IRON-CLAD: do not remove. Placed outside GSD markers so it survives regeneration. -->
> ## IRON-CLAD RULE — DRY + SOLID
>
> **All code, tests, configuration, and documentation MUST adhere to DRY and SOLID.** A change that
> violates either is rejected at review and **blocks the phase**. No exceptions.
>
> Authoritative standard: [`CONVENTIONS.md`](./CONVENTIONS.md) — mandatory reading before any
> `Edit`, `Write`, or code generation.
>
> In short: SATS rules live only in `data/*.yaml`; citations come from one helper; tools are narrow and
> single-purpose; the graph depends on the tool *interface*, not concrete implementations; extend by
> data/config — not by editing working code.

<!-- GSD:project-start source:PROJECT.md -->

## Project

**TriageDesk**

TriageDesk is an agentic triage-support tool for the outpatient (OPD) triage desk of a busy public
hospital in Africa. It turns the vitals and presenting complaint a nurse already has in front of her
into a **sourced, SATS-grounded priority level in seconds** — and it never diagnoses, prescribes, or
moves a patient without a named clinician's approval. It is an entry in the *Agentic AI for Africa*
challenge (Health & Wellbeing track, **Symptom-based priority scoring**).

> Note: the repository-root `PROJECT.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `EVALS.md`,
> `DECISIONS.md`, `SECURITY.md` are the **public submission artifacts**. This `.planning/PROJECT.md`
> is GSD's internal working memory. Keep them consistent, but do not treat them as the same file.

**Core Value:** **A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches
the queue without her approval.** If everything else fails, this must work.

### Constraints

- **Team**: solo — scope discipline is a scored skill.
- **Timeline**: ~6 days (today 2026-10-09 → deadline 2026-10-15); repos are cloned at the deadline and
  post-deadline commits disqualify.
- **Compute**: local CPU only; small quantised open-weights model.
- **Stack**: required MCP + open-source orchestration; no closed no-code builders.
- **Data**: synthetic only; no health data leaves the machine.
- **Compliance**: every challenge requirement is tracked in `../REQUIREMENTS.md`.
- **Engineering standards**: **DRY + SOLID are iron-clad** (`../CONVENTIONS.md`); a violation blocks the phase.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## TL;DR — the one decision that shapes everything

| | **World A — Modern (recommended)** | **World B — Adapter (fallback only)** |
|---|---|---|
| MCP SDK | `mcp` **2.3.0** (`from mcp.server import MCPServer`) | `mcp` **1.30.0** (`from mcp.server.fastmcp import FastMCP`) |
| Protocol | **2026-07-28** (current) | 2025-06-18 / 2025-11-25 |
| Tool ingestion into LangGraph | `langchain.mcp.MCPAdapter` (**beta**, on FastMCP 4) | `langchain-mcp-adapters` 0.3.2 (**deprecated**) |
| Status | All components maintained, on current spec | Adapter unmaintained; SDK in maintenance-only mode |

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python (uv-managed) | **3.12.x** (`requires-python = ">=3.12,<3.13"`) | Runtime | Host system Python is 3.14; every pinned dependency declares `>=3.10`, so 3.12 is safe and reproducible. Pin via `.python-version` so the deadline-cloned repo rebuilds identically. |
| uv | **>=0.12** (host has 0.5.26 → upgrade) | Env + dependency manager | Single tool for `pyproject.toml`, `uv.lock`, venv and `uv run`; the project's own constraint (avoid host Python 3.14). `uv.lock` (committed) is what makes the "cloned at the deadline" reproducible. |
| **MCP Python SDK** (`mcp`) | **2.3.0** | Author the *owned* MCP server | Official SDK, current stable line. v2 exposes `MCPServer` (the v1 `FastMCP` name is **gone**, not deprecated). Speaks the current **2026-07-28** revision and serves legacy 2025-era clients from the same server. |
| MCP protocol revision | **2026-07-28** | Wire contract to target | The **current** revision per `modelcontextprotocol.io/specification/versioning`. v2 SDK implements it and negotiates down to 2025-11-25 automatically. |
| **LangGraph** | **1.2.14** | Agent orchestration + approval gate | Already a fixed project decision. `interrupt(payload)` + `Command(resume=...)` is exactly the human-approval gate the challenge requires; state is checkpointed so a paused triage survives. |
| **langchain** (`langchain[mcp]`) | **1.4.4** | Ingest MCP tools as LangChain tools | The current, maintained home of MCP support (`langchain.mcp.MCPAdapter`). Replaces the deprecated `langchain-mcp-adapters`. Beta — see flags. |
| **FastMCP** | **4.1.0** | MCP client engine (transitive) | Pulled in by `langchain[mcp]` (`fastmcp>=4.0.11,<5`). FastMCP 4 targets the modern sessionless protocol era and does transport inference/negotiation for `MCPAdapter`. **Do not add directly** — let `langchain[mcp]` pin it. |
| **Ollama** (server) | **0.30.6** (installed) | Local open-weights inference | CPU-only, no data egress. Supports structured outputs (JSON Schema via `format`) and tool calling. |
| **ollama** (Python client) | **0.6.3** | Call the local model | Thin client; `format=PydanticModel.model_json_schema()` drives constrained decoding. |
| Qwen2.5 **1.5B-Instruct** (`qwen2.5:1.5b`) | Q4_K_M, **986 MB**, 32K ctx | **Primary** local model | Apache-2.0, and it actually fits the host's ~2.3 GB *available* RAM (see sizing below). |
| Qwen2.5 **3B-Instruct** (`qwen2.5:3b`) | Q4_K_M, **1.9 GB**, 32K ctx | **Aspirational** model | Better reasoning, but ~2.4-3 GB needed — only viable when background RAM is freed. **License caveat: 3B (and 72B) ship under the Qwen licence, not Apache-2.0.** |
| SQLite (stdlib `sqlite3`) | 3.x (bundled, WAL mode) | Domain store + audit log | Zero-dependency, local, file-based; the challenge's "borrowed MCP server" target. |
| LangGraph SQLite checkpointer (`langgraph-checkpoint-sqlite`) | **3.1.1** | Persist paused graph state for `interrupt()`/resume | Official checkpointer. `AsyncSqliteSaver.from_conn_string(...)`. **Separate file from the domain DB** — runtime state vs clinical record are different concerns. |
| Pydantic | **2.14.0** | Schemas everywhere | One schema source for Ollama structured output, MCP tool contracts, and typed state. Satisfies the DRY "one schema module" rule. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyyaml` | `>=6.0,<7` | Load `data/sats_tews.yaml`, `data/sats_discriminators.yaml` | The DRY single source for SATS rules — load once at startup, never inline thresholds. |
| `aiosqlite` | `>=0.20` (transitive) | Async SQLite for the checkpointer | Pulled in by `langgraph-checkpoint-sqlite`; not added manually. |
| `sqlite-vec` | `>=0.1.6` (transitive) | Checkpointer dependency | Transitive only; unused by us. |
| `rich` | (transitive via `mcp[cli]`) | Readable tool-call/CLI output for the demo | Demo legibility. |
| `pytest` + `pytest-asyncio` | latest | Test suite incl. the 14 eval cases | Dev-only. One test per tool contract (SOLID Liskov check on return shapes). |
| `ruff` | latest | Lint + format | Enforce the DRY rule mechanically (flagting duplicated literals outside `data/`). |
| `mypy` | latest | Static typing | Typed tool contracts; catches return-shape drift (SOLID L). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Project lifecycle | `uv init --python 3.12` → `uv python pin 3.12` → `uv add …` → `uv lock` → `uv run`. Upgrade the host's 0.5.26 first. |
| Ollama CLI | Model pull/run | `ollama pull qwen2.5:1.5b` (and optionally `qwen2.5:3b`). |
| `npx` (Node 22 present) | Launch the borrowed SQLite MCP server | `npx -y mcp-sqlite <db>` — **pin the package version**, do not rely on `latest`. |
| MCP Inspector | Debug the owned server | `uv run mcp dev server.py` (the CLI needs `npx` on PATH). |

## Installation

# 0. Modernise uv (host has 0.5.26; current line is ~0.12)

# 1. Project on Python 3.12 (uv downloads a managed 3.12; host 3.14 untouched)

# 2. Core dependencies (exact pins; commit uv.lock)

# 3. Dev dependencies

# 4. Deterministic install for the deadline clone

# 5. Open-weights model (no egress during the demo)

# 6. Borrowed SQLite MCP server (fetched on demand, stdio, pinned)

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `langchain.mcp.MCPAdapter` (1.4.4, beta) | `langchain-mcp-adapters` `MultiServerMCPClient` (0.3.2, **deprecated**) | Only if a spike proves `MCPAdapter` unusable **and** you accept pinning `mcp<2` + the v1 `FastMCP` server API. It is the lower-risk *known* path but a dead-end dependency. |
| `mcp` 2.3.0 + `MCPServer` | Direct low-level `Server` (v2) | Only for JSON-RPC-level control (custom middleware). Not needed — decorator tools cover the ≥3 required tools. |
| `qwen2.5:1.5b` (986 MB, Apache-2.0) | `qwen2.5:3b` (1.9 GB, Qwen licence) | When the demo machine has ≥4 GB free RAM and licence terms are acceptable. |
| `qwen2.5:1.5b` | Llama-3.2-3B / Gemma-2-2B / Qwen3 small | If Qwen's JSON discipline disappoints; Llama-3.1/3.2 has the strongest *native* tool-call template. Extra evaluation cost. |
| `langgraph-checkpoint-sqlite` `AsyncSqliteSaver` | `InMemorySaver` | Tests only. The approval gate must persist across the pause — in-memory loses it on restart. |
| `jparkerweb/mcp-sqlite` (npm, 128★) | `rusq/mcp-sqlite` (Go, BSD-2) | When you want a read-only-by-default posture and row caps for token safety, or prefer a compiled single binary. |
| In-house ~40-line hash-chain module | `auditchain` (PyPI, MIT) | If you want built-in checkpoints, HMAC seal-key rotation and a `verify` CLI for free. See *What NOT to Use* for why in-house is preferred here. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `from mcp.server.fastmcp import FastMCP` | The v1 import path was **removed** in SDK v2 (not deprecated). Every copy-pasted tutorial snippet uses it and will fail on install. | `from mcp.server import MCPServer` (v2). |
| `langchain-mcp-adapters` | Repo states it is "no longer actively maintained"; current release pins `mcp<2.0.0`, so it **conflicts** with `mcp` 2.3.0. | `langchain.mcp.MCPAdapter` via `langchain[mcp]`. |
| `langchain-mcp-adapters` **and** `mcp` 2.x in one env | Hard dependency conflict (`mcp<2` vs `mcp>=2`) — will not resolve. | Pick one world; do not mix. |
| Official `modelcontextprotocol/sqlite` / PyPI `mcp-server-sqlite` | **Archived** (moved to `servers-archived`; "NO SECURITY GUARANTEES … no updates"). PyPI release `2025.4.25` is archived too. | A maintained community server (`jparkerweb/mcp-sqlite` or `rusq/mcp-sqlite`). |
| Qwen2.5 **7B** (any quant) | Needs ≥3 GB free even at Q2_K; host has ~2.3 GB available. Will swap / stall on CPU. | `qwen2.5:3b` (only with freed RAM) or `qwen2.5:1.5b`. |
| Free-form ReAct agent driving tools on a 1.5B model | Small models pick the wrong tool, loop, and mis-format arguments — catastrophic for a safety-critical path. | **Explicit graph** with deterministic nodes; LLM only for extraction/structure, never arithmetic or routing (already a project decision). |
| Relying on Ollama **tool calling** as the primary extraction path | Native tool-call templates for Qwen2.5 exist, but reliability at 1.5B-3B on CPU is poor. | Ollama **structured outputs** (`format=<JSON schema>` + Pydantic validation) for every extraction; treat tool-calling as a secondary experiment. |
| WebSocket MCP transport | Removed from the SDK in v2 and never part of the spec. | stdio (local) or Streamable HTTP. |
| `npx --yes <unpinned-pkg>` at runtime | Fetches whatever `latest` is at clone time — breaks the deadline-reproducibility guarantee and executes unverified code. | Pin the version (`mcp-sqlite@1.0.9`) and, for the demo, vendor/install it once. |
| Storing the audit log and the LangGraph checkpoints in one file | Conflates an immutable clinical record with disposable runtime state; a checkpointer write could be mistaken for an audit event (DRY ambiguity). | Two files: `triage.db` (domain + audit, via MCP) and `checkpoints.db` (LangGraph). |

## Stack Patterns by Variant

- Pin `mcp>=1.24,<2` and `langchain-mcp-adapters==0.3.2`; author the owned server with `FastMCP`.
- Because the graph depends on the **MCP tool interface**, not the adapter (SOLID: D), the swap is confined to one wiring module — budget ~1 day, not a re-architecture.
- Use `qwen2.5:3b` as primary for better extraction quality; keep `1.5b` as the documented fallback for the recording.
- Use `qwen2.5:1.5b` or `qwen2.5:0.5b` (Apache-2.0). Note 3B/72B are under the Qwen licence (still open-weights, but with usage conditions).
- Prefer `rusq/mcp-sqlite` (Go) with its read-only default, and route **writes** (queue + audit) through a separate write-capable surface. (The challenge's gated write needs a write path, so choose deliberately.)

## Recommended Dependency Boundaries (honours the iron-clad DRY + SOLID rule)

| Concern | Single source of truth | Everyone else |
|---|---|---|
| SATS thresholds / discriminators | `data/*.yaml` | Loaded once; never inlined (CONVENTIONS §1). |
| Vitals / case / audit **schemas** | one typed `pydantic` module | MCP tool contracts, Ollama `format=`, and graph state all import it. This is why `pydantic` is a **core** dep, not a supporting one. |
| Audit record shape + hash chain | one logging function (stdlib `hashlib`/`hmac`/`sqlite3`) | Every tool call routes through it. |
| MCP tool ingestion | one wiring module (`MCPAdapter` ↔ LangChain tools) | The graph sees only LangChain tool objects — swapping World A → B touches this module alone (SOLID: D, L). |
| Model access | one `OllamaClient` wrapper bound to a Pydantic schema | Nodes call the wrapper; no node builds its own prompt/JSON parsing. |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `mcp==2.3.0` | `mcp-types==2.3.0` | `mcp` depends on `mcp-types` at an **exact** version. Never pin `mcp-types` separately. |
| `mcp==2.3.0` | Python 3.10-3.14 | `requires-python>=3.10`; 3.14 branches exist (`anyio>=4.10`, `starlette>=0.48`). 3.12 is squarely supported. |
| `fastmcp==4.1.0` | `mcp>=2.0.0,<3.0.0` | Via `fastmcp-slim==4.1.0` (also `mcp-types>=2.0.0`). Confirms FastMCP 4 is on the v2/modern era. |
| `langchain[mcp]==1.4.4` | `fastmcp>=4.0.11,<5` | The `[mcp]` extra. `langchain` needs `>=1.4.0` for the `langchain.mcp` namespace (beta). |
| `langgraph==1.2.14` | `langchain-core>=1.4.7,<2` | Check `langchain==1.4.4` resolves the same `langchain-core`; both are in the 1.x line so this is expected to resolve cleanly. |
| `langgraph-checkpoint-sqlite==3.1.1` | `langgraph-checkpoint>=4.1.0,<5`, `aiosqlite>=0.20` | Pulls `sqlite-vec`. |
| `langchain-mcp-adapters==0.3.2` | **`mcp>=1.24,<2` (CONFLICT)** | Cannot coexist with `mcp==2.3.0`. This is the fork. |
| `ollama==0.6.3` | `httpx>=0.27`, `pydantic>=2.9` | Note: `ollama` uses classic `httpx`; `mcp`/`fastmcp` use the new `httpx2`. Both will be installed — different packages, no conflict. |
| Ollama server `0.30.6` | `qwen2.5:3b` / `qwen2.5:1.5b` | Both require well below 0.30; structured outputs need a recent Ollama (0.5+). |

## Open Questions / Flags

| Flag | Risk | Retire by |
|------|------|-----------|
| `langchain.mcp.MCPAdapter` is **beta** (`LangChainBetaWarning`, "API may change") | Depends on a beta API for the core tool path. | **Phase 1 spike (half a day):** connect `MCPAdapter` to the owned server + the borrowed server, call a tool, run a `create_agent` round-trip. Exact-pin `langchain==1.4.4` so an upstream release cannot shift under you. If it fails → World B. |
| FastMCP 4 client ↔ **legacy TS v1** borrowed server (`@modelcontextprotocol/sdk ^1.12.1`) | FastMCP 4 targets 2026-07-28 and claims legacy fallback; unverified against this specific old server. | Same Phase-1 spike — if the handshake fails, use `rusq/mcp-sqlite` (Go, actively maintained) or World B. |
| 3B RAM fit on this host | ~2.3 GB available now vs ~2.4-3 GB needed. | Measure with `ollama ps` during the spike; make 1.5B the default and 3B opt-in. |
| Qwen2.5 3B licence (not Apache-2.0) | Challenge may read "open-weights" strictly. | Default to **1.5B (Apache-2.0)** for the recorded demo; document any 3B use. |
| Two SQLite files (`triage.db` + `checkpoints.db`) | Reviewers may ask "why two?". | Document the rationale in ARCHITECTURE (audit record vs runtime state), per DRY "distinct concerns" table. |
| `uv` on host is 0.5.26 | Old CLI; some documented flows assume ~0.12. | `uv self update` before `uv init`. |

## Sources

- `https://modelcontextprotocol.io/specification/versioning` — current protocol revision **2026-07-28** (HIGH — official).
- `https://py.sdk.modelcontextprotocol.io/` + `.../whats-new/` + `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/docs/whats-new.md` — SDK v2, `FastMCP`→`MCPServer`, both-era serving, stdio/streamable-HTTP transports (HIGH — official).
- `https://pypi.org/pypi/mcp/json` — `mcp` **2.3.0**; v1 line max **1.30.0** (HIGH — registry).
- `https://pypi.org/pypi/langchain-mcp-adapters/json` — 0.3.2 pins `mcp<2.0.0,>=1.24.0` (HIGH — registry).
- `https://docs.langchain.com/oss/python/langchain/mcp` + `.../migrate/langchain-mcp-adapters` — `MCPAdapter`, `MCPConfig`, elicitation→interrupt (HIGH — official docs); `langchain.mcp` is **beta** (flagged).
- `https://pypi.org/pypi/langchain/json` — **1.4.4**, `[mcp]` → `fastmcp>=4.0.11,<5` (HIGH — registry).
- `https://pypi.org/pypi/fastmcp/json` + `.../fastmcp-slim/json` — **4.1.0**, `mcp>=2.0.0,<3.0.0` (HIGH — registry).
- `https://pypi.org/pypi/langgraph/json` + `.../langgraph-checkpoint-sqlite/json` — **1.2.14** and **3.1.1** (HIGH — registry).
- `https://pypi.org/pypi/ollama/json` + `.../pydantic/json` — **0.6.3**, **2.14.0** (HIGH — registry).
- `https://docs.langchain.com/oss/python/langgraph/interrupts` — `interrupt()` + `Command(resume=...)` (HIGH — official).
- `https://docs.ollama.com/capabilities/structured-outputs` + `.../tool-calling` — `format=<schema>`, Pydantic `model_json_schema()`, Qwen tool-call template (HIGH — official).
- `https://github.com/modelcontextprotocol/servers-archived` — SQLite reference server **archived, no security guarantees** (HIGH — official repo).
- `https://github.com/jparkerweb/mcp-sqlite` (npm `mcp-sqlite` 1.0.9, ~500 wk downloads) and `https://raw.githubusercontent.com/rusq/mcp-sqlite/master/README.md` (Go, BSD-2) — maintained borrow candidates (MEDIUM — community repos).
- Ollama registry pages for `qwen2.5:3b` (1.9 GB) and `qwen2.5:1.5b` (986 MB); Qwen2.5 licence carve-out for 3B/72B (MEDIUM — registry + model card).
- Hash-chain audit patterns: `https://pypi.org/project/auditchain/` (+ sealog, nexuscone, sovereign-sdk-ledger) — `SHA256(prev_hash||payload)`, HMAC seal, checkpoints, append-only triggers (MEDIUM — multiple community sources agree).

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

# CONVENTIONS (pointer)

Authoritative engineering standards: **[`../../CONVENTIONS.md`](../../CONVENTIONS.md)**.

**IRON-CLAD RULE: DRY + SOLID.** See that file for the single-source-of-truth table, the SOLID
application, the enforcement gates, and the rejected anti-patterns.

> This file is intentionally a pointer. The standards live in exactly one place (root
> `CONVENTIONS.md`); do not restate them here (that would violate DRY).
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
