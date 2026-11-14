# ARCHITECTURE — TriageDesk

> **One page.** Agent shape; MCP built vs borrowed; why.
> Challenge brief: <https://agentic-africa-challenge.lovable.app/tracks/healthcare>

## 1. Shape in one line

A **deterministic SATS scorer** in an **explicit LangGraph plan** on a **local open-weights
model**, gated by **human approval before anything reaches a queue**. The LLM handles language;
**no number comes from the model**.

## 2. Context

Vitals + complaint → `triage` MCP (score/flag) + borrowed SQLite MCP (persist) + local Qwen2.5,
offline, gated by a clinician.

## 3. Agent shape — two layers

**Adaptive envelope** (`ingest → normalize → retrieve → plan`): the planner chooses one read-only
action — `gather_evidence`, `ask_question`, `re_extract`, `finish_investigation` — from a closed set,
inside a 3-step budget. The model proposes; a deterministic guard disposes.

**Frozen safety kernel** (`score → ground → verify → recheck → assess → approval_gate → commit →
handover`): non-skippable. `finish_investigation` is its only entry, `commit` keeps one inbound edge,
and the planner's vocabulary contains no score, gate or commit.

A **deterministic emergency check** runs before any model call: a critical structured case skips the
model and the planner, never the kernel or the clinician.

**Why not ReAct:** a small CPU model is an unreliable free agent; a bounded plan is reproducible (JC-1).
The planner is bounded for the same reason (D31). The reviewer-facing answer — what the system
decides, what it structurally cannot, and the measured adaptive-vs-baseline delta — is
[`docs/AGENTIC.md`](docs/AGENTIC.md).

**Diagrams:** canonical shipped render [reference](docs/assets/architecture.pdf) (source `.mmd`
beside it) · [clinical workflow](docs/assets/architecture-workflow.pdf) ·
[components](docs/assets/architecture-components.pdf) — all **shipped** in v1.3, one renderer.

## 4. MCP servers

### Built by us — `triage` server (seven tools)

| Tool | Read/Act | Contract |
| --- | --- | --- |
| `normalize_case` | read | prose + vitals → structured JSON, `missing[]`, `out_of_scope` |
| `match_discriminators` | read | complaint → discriminator ids + coverage status |
| `retrieve_evidence` · `assess_confidence` | read | cited passages · deliver / clarify / defer |
| `score_priority` | **act** | case → `colour`, `tews`, `citations[]`, `target_time` |
| `raise_recheck_flag` | **act** | serial vitals → deterioration flag (**never** a verdict) |
| `commit_priority` | **act + gated** | approved case → queue write + audit; **refuses without a token** |

Three of seven act (BW-2); only the gated tool mutates the queue (BW-9).

### Borrowed — SQLite MCP

**Why not write our own:** persistence, schema and query safety are solved; a hand-rolled DB
adds zero triage value. Consumed via `langchain.mcp.MCPAdapter`; the reference server is archived.
The graph binds to the **tool interface** (SOLID/DIP); a "World B" swap is one module.

## 5. The gate (irreversible actions)

A priority and a deterioration flag could each move a queue, so both are gated; a deterioration alert
is a **second-look request** that does **not** reorder the queue. `commit_priority` is the **only**
queue-changing tool and needs a signed approval record:

```json
{ "decision": "approve|edit|dismiss", "approved_at": "<ts>", "approved_by": "<clinician>", "role": "<role>", "final_colour": "ORANGE" }
```

The `interrupt()` in `approval_gate` halts before `commit` — nothing a model says places a patient in a
queue (SN-3, SN-4). The write is **idempotent** (keyed by `case_id`); approver identity is recorded,
and its authentication is declared in `SECURITY.md` §6.

## 6. Logging & audit

One chained record per tool call (BW-8, BW-10):

```json
{ "ts": "...", "case_id": "0417", "tool": "score_priority", "actor": "agent|clinician", "inputs": {}, "outputs": {}, "approved_by": null, "prev_hash": "...", "hash": "..." }
```

Written to SQLite; each call emits a `tool` span in `spans.jsonl` — readable and tamper-evident (JC-5).

## 7. Data flow & no-egress guarantee

Synthetic input → local model → tools → SQLite. No network in the agent path; inference offline (BW-6).

## 8. Extensibility, model & runtime (ST-1)

SATS rules live in **data**, not code (`data/*.yaml`), so a rule, band or discriminator is a
**one-line YAML edit**; a new capability is one node + one tool. Runtime: **`qwen2.5:1.5b`** via
Ollama — the measured default — on LangGraph, `uv`/Python 3.12, structured JSON (`format=<schema>`).
Code adheres to **DRY + SOLID** ([`docs/CONVENTIONS.md`](docs/CONVENTIONS.md)).
