# ARCHITECTURE — TriageDesk

> **One page.** Agent shape, MCP servers built vs borrowed, and why.
> Challenge brief: <https://agentic-africa-challenge.lovable.app/tracks/healthcare>

## 1. Shape in one line

A **deterministic SATS scorer** wrapped in an **explicit LangGraph plan** driven by a **local
open-weights model**, with a **human approval gate before anything reaches a queue**.

The LLM handles language and judgement; **no number is ever produced by the model**. That split is
what makes a priority defensible under audit and an evaluation honest.

The **whole** task — raw input to sourced priority and handover — runs on the **open-weights model**.
No frontier model sits in the required path (a frontier comparison is optional, synthetic-only, and
never needed to run the demo).

## 2. Context

```
 nurse ──vitals + complaint──▶ [ TriageDesk ]
                                   │
                     ┌─────────────┴──────────────┐
                     ▼                             ▼
        our MCP server (triage)          borrowed SQLite MCP
        normalize · match · score        case cards · queue · audit log
        recheck · commit(gated)
                     │
                     ▼
        local Qwen2.5 via Ollama  (no egress)
                     │
                     ▼
     sourced priority + second-look flag  ──▶  named clinician approves ──▶ queue
```

## 3. Agent graph (LangGraph)

| Node | Kind | Responsibility |
| --- | --- | --- |
| `ingest` | deterministic | Validate raw case (age, vitals, free-text complaint). |
| `normalize` | LLM + tool | Parse prose → structured fields; list `missing[]`; detect `out_of_scope`. |
| `retrieve` | tool | `match_discriminators` — candidate SATS discriminators for the complaint. |
| `score` | tool | `score_priority` — deterministic TEWS + discriminator override → colour + citations + target time. |
| `verify` | LLM critic + deterministic | Reject any priority lacking a source; retry once, else fail safe. |
| `recheck` | tool | `raise_recheck_flag` — comparison of serial vitals → second-look flag. |
| `approval_gate` | LangGraph `interrupt()` | Pause for a **named** clinician; approve / edit / dismiss. |
| `commit` | tool (gated) | `commit_priority` — write case card + queue position + audit entry. |
| `handover` | deterministic | Render the sourced case card for the nurse. |

**Conditional edges:** missing critical vitals → `request_missing_info` (recover, don't guess) ·
`out_of_scope` (e.g. paediatric) → `escalate` (safe abstention) · uncited score → `score` retry ·
deterioration detected → `recheck` loop.

**Why not free-form ReAct:** a small CPU model is an unreliable free agent. Fixing the *plan* in the
graph and giving the model only bounded decisions keeps behaviour reproducible — which is exactly what
JC-1 (agentic depth) and JC-4 (reliability) reward.

**Recovery from failure (bounded).** If the model emits invalid structured output, or a tool errors,
`verify` retries **once**. On a second failure the graph falls back to the **deterministic path**
(score directly from the already-parsed structured fields) or **escalates to the nurse**. It never
emits an uncited or partially-parsed priority. This is the "recovers from failure" behaviour the
challenge's *agentic* definition asks for.

## 4. MCP servers

### Built by us — `triage` server (5 tools)

| Tool | Read/Act | Contract (in → out) |
| --- | --- | --- |
| `normalize_case` | read | prose + vitals → structured JSON, `missing[]`, `out_of_scope` |
| `match_discriminators` | read | complaint → ranked discriminator IDs from the SATS KB |
| `score_priority` | **act** | structured case → `colour`, `tews`, `triggered_rules[]`, `citations[]`, `target_time` |
| `raise_recheck_flag` | **act** | serial vitals → deterioration flag (**never** a verdict) |
| `commit_priority` | **act + gated** | approved case → queue write + audit entry; **refuses without an approval token** |

Three of the five tools *do something* (BW-2). The queue-mutating tool is the gated one (BW-9).

> `normalize_case` captures the **full** vitals set (including SpO₂ and diastolic BP) for the case card
> and audit trail, but `score_priority` scores **only the SATS-defined parameters** — see
> `docs/SATS.md` §4.1 for why SpO₂ is captured-but-not-scored.

### Borrowed — SQLite MCP

**Why it beats writing our own:** persistence, schema management, and query safety are solved
problems; hand-rolling a database layer adds zero triage value and adds auditable surface area we
would have to defend. Consumed through an MCP client adapter — `langchain.mcp.MCPAdapter`
(`langchain[mcp]>=1.4.0`, current) rather than the archived `langchain-mcp-adapters`.

> **Maintained server + fallback.** The official reference SQLite server is archived; use a maintained
> community server (e.g. `jparkerweb/mcp-sqlite` or `rusq/mcp-sqlite`). The graph binds to the **tool
> interface** (SOLID/DIP), so a "World B" swap of the adapter is a one-module change if the current
> adapter proves unstable (see `.planning/research/SUMMARY.md`).

## 5. The gate (irreversible actions)

Three kinds of output could move a patient's queue position: a **priority level**, a **referral**
(stretch tool, if built), and a **deterioration flag**. All three are gated. A deterioration alert is
surfaced to the nurse as a **second-look request** and does **not** reorder the queue on its own;
`commit_priority` is the **only** tool that changes a queue position, and it requires a signed
approval record:

```json
{ "case_id": "0417", "approved_by": "<named clinician>", "approved_at": "<ts>",
  "decision": "approve|edit|dismiss", "final_colour": "ORANGE" }
```

The LangGraph `interrupt()` in `approval_gate` halts before `commit`. Nothing a model says can place a
patient in a queue on its own (SN-3, SN-4, DQ-3). The write is **idempotent** (keyed by `case_id`), and
the approval record carries the approver's **name and role** — authentication of that identity is a
documented production requirement (`SECURITY.md` §6).

## 6. Logging & audit

Every tool call appends one record (BW-8, BW-10):

```json
{ "ts": "...", "case_id": "0417", "tool": "score_priority", "actor": "agent|clinician",
  "inputs": { "...": "..." }, "outputs": { "...": "..." },
  "approved_by": null, "prev_hash": "...", "hash": "..." }
```

Written to `log/audit.jsonl` **and** the SQLite audit table. Hash-chained so the log is readable and
tamper-evident (JC-5).

## 7. Data flow & no-egress guarantee

Input (synthetic) → local model → local tools → local SQLite. No network calls in the agent path. The
model is pulled once; inference is offline. This satisfies BW-6 (data does not leave the country)
even though the data is synthetic.

## 8. Extensibility (built for the live review — ST-1)

SATS rules live in **data**, not code:

```
data/sats_tews.yaml            # parameter → band → points
data/sats_discriminators.yaml  # discriminator → category → citation
```

Adding a rule, a band, or a new discriminator is a **one-line YAML edit**. Adding a wholly new
capability (e.g. referral routing) means adding one node + one tool, because nodes and tools are
independent.

## 9. Model & runtime

| Choice | Value | Note |
| --- | --- | --- |
| Orchestration | **LangGraph** | Open source; `interrupt()` maps to the gate |
| Model | **Qwen2.5-1.5B-Instruct (Q4)** via Ollama | Primary (fits ~6.9 GB RAM); 3B opt-in only if measured to fit |
| Runner | `uv`, Python 3.12 | Avoids host Python 3.14 wheel gaps |
| Output contract | structured JSON via Ollama `format=<schema>` | More reliable than native tool-calling at 1.5B–3B on CPU |

See `DECISIONS.md` for rationale on every choice above.

## 10. Security & hardening

The presenting complaint is **untrusted input**: it is treated as data, never instructions, and the
deterministic scorer means no sentence a note can contain can set a colour. Tools are **allowlisted**
with no network or credentials; `commit_priority` is **idempotent** (keyed by `case_id`); and prompts,
model version, and scale data are **pinned and hashed** for reproducibility. Full threat model:
[`SECURITY.md`](SECURITY.md).

## 11. Design principles (iron-clad)

All code adheres to **DRY + SOLID** — see [`CONVENTIONS.md`](CONVENTIONS.md). In practice: SATS rules
live only in `data/*.yaml`; citations come from one helper; tools are narrow and single-purpose; and the
graph depends on the **tool interface**, not implementations (so the owned/borrowed server swap is safe).
Extend by data/config, not by editing working code.
