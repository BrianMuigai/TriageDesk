# ARCHITECTURE — TriageDesk

> **One page.** Agent shape; MCP built vs borrowed; why.
> Challenge brief: <https://agentic-africa-challenge.lovable.app/tracks/healthcare>

## 1. Shape in one line

A **deterministic SATS scorer** in an **explicit LangGraph plan** on a **local open-weights
model**, gated by **human approval before anything reaches a queue**. The LLM handles language;
**no number comes from the model**, so a priority is defensible under audit.

## 2. Context

Vitals + complaint → `triage` MCP (score/flag) + borrowed SQLite MCP (persist) + local Qwen2.5,
offline, gated by a clinician.

## 3. Agent graph (LangGraph)

| Node | Kind | Responsibility |
| --- | --- | --- |
| `ingest` | deterministic | Validate raw case. |
| `normalize` | LLM + tool | Parse prose → fields; `missing[]`; `out_of_scope`. |
| `retrieve` | tool | `match_discriminators`. |
| `score` | tool | `score_priority` — TEWS + override → colour + citations. |
| `ground` | tool | `retrieve_evidence` (no colour). |
| `verify` | critic + deterministic | Reject uncited; retry once, else fail safe. |
| `recheck` | tool | `raise_recheck_flag` — serial vitals → second-look. |
| `assess` | deterministic | Coverage/deferral → a terminal. |
| `approval_gate` | `interrupt()` | Pause for a **named** clinician. |
| `commit` | tool (gated) | Gated write: case card + queue + audit. |
| `handover` | deterministic | Render the sourced case card. |
| `request_missing_info` · `escalate` | terminal | Abstain / escalate. |

**Edges:** missing vitals → recover · `out_of_scope` → abstain · uncited → retry · deterioration →
`recheck`. **Why not ReAct:** a small CPU model is an unreliable free agent; a bounded plan is
reproducible (JC-1).

## 4. MCP servers

### Built by us — `triage` server (seven tools)

| Tool | Read/Act | Contract |
| --- | --- | --- |
| `normalize_case` | read | prose + vitals → structured JSON, `missing[]`, `out_of_scope` |
| `match_discriminators` | read | complaint → ranked discriminator IDs |
| `retrieve_evidence` · `assess_confidence` | read | cited passages · confidence/deferral |
| `score_priority` | **act** | case → `colour`, `tews`, `citations[]`, `target_time` |
| `raise_recheck_flag` | **act** | serial vitals → deterioration flag (**never** a verdict) |
| `commit_priority` | **act + gated** | approved case → queue write + audit; **refuses without a token** |

Three of seven act (BW-2); only the gated tool mutates the queue (BW-9).

### Borrowed — SQLite MCP

**Why not write our own:** persistence, schema and query safety are solved; a hand-rolled DB
adds zero triage value. Consumed via `langchain.mcp.MCPAdapter`; the reference server is archived; use
a maintained one. The graph binds to the **tool interface** (SOLID/DIP); a "World B" swap is
one-module.

## 5. The gate (irreversible actions)

A **priority** and a **deterioration flag** could each move a queue position, so all are gated; a
deterioration alert is a **second-look request** that does **not** reorder the queue. `commit_priority` is the **only** queue-changing tool and needs a signed approval record:

```json
{ "case_id": "0417", "approved_by": "<clinician>", "approved_at": "<ts>", "decision": "approve|edit|dismiss", "final_colour": "ORANGE" }
```

The `interrupt()` in `approval_gate` halts before `commit` — nothing a model says places a patient in a
queue (SN-3, SN-4). The write is **idempotent** (keyed by `case_id`); approver identity is recorded,
and its authentication is a declared production requirement (`SECURITY.md` §6).

## 6. Logging & audit

Every tool call appends one hash-chained record (BW-8, BW-10):

```json
{ "ts": "...", "case_id": "0417", "tool": "score_priority", "actor": "agent|clinician", "inputs": {}, "outputs": {}, "approved_by": null, "prev_hash": "...", "hash": "..." }
```

Written to `log/audit.jsonl` **and** the SQLite audit table — readable and tamper-evident (JC-5).

## 7. Data flow & no-egress guarantee

Synthetic input → local model → tools → SQLite. No network in the agent path; inference offline (BW-6).

## 8. Extensibility, model & runtime (ST-1)

SATS rules live in **data**, not code (`data/sats_tews.yaml`, `data/sats_discriminators.yaml`), so
adding a rule, band or discriminator is a **one-line YAML edit**; a new capability is one node + one
tool. Runtime: **`qwen2.5:1.5b`** via Ollama — the measured default —
orchestrated by LangGraph on `uv` / Python 3.12 with structured JSON output (`format=<schema>`).
Code adheres to **DRY + SOLID** ([`docs/CONVENTIONS.md`](docs/CONVENTIONS.md)).
