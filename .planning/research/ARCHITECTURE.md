# Architecture Research

**Domain:** Agentic clinical triage-support tool (MCP + LangGraph, deterministic-SATS scorer, human-gated queue write)
**Researched:** 2026-10-09
**Confidence:** HIGH for the project-derived design (TriageDesk's own design docs are the authoritative requirements); MEDIUM for the LangGraph/MCP mechanics (official docs); MEDIUM for the domain/orchestration consensus (cross-checked web sources)

> **One-line thesis.** The graph **plans**; the tools **compute**; the model **talks**; the clinician
> **authorises**; the store **persists**. Determinism is a property of the **tool layer**, not the graph
> and never the model. The HITL gate is a structural break between *proposal* and *persistence*, and the
> only irreversible action is idempotent and approval-keyed.

---

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│ PRESENTATION / DESK SURFACE   (nurse + named clinician)                │
│  case card · citations · approve/edit/dismiss · second-look prompt     │
└───────────────▲───────────────────────────────────┬───────────────────┘
                │ handover (sourced card)            │ approval decision
┌───────────────┴───────────────────────────────────▼───────────────────┐
│ ORCHESTRATION  (LangGraph StateGraph + checkpointer)                   │
│  ingest → normalize → retrieve → score → verify → recheck              │
│                                            │                           │
│                                    approval_gate  ◀── interrupt()  ══╗  │
│                                            │                        ║  │
│                                         commit ──▶ handover         ║  │
│  state saved/resumed by checkpointer (thread_id = case_id) ──────── ╝  │
└──────┬───────────────────────────────┬───────────────────┬────────────┘
       │ MCP tool interface            │ MCP tool interface│ model (LLM)
┌──────▼───────────────┐   ┌───────────▼────────────┐  ┌───▼─────────────┐
│ OUR MCP SERVER       │   │ BORROWED SQLITE MCP    │  │ LOCAL LLM       │
│ "triagedesk" (5 tools)│   │ (persistence)          │  │ Qwen2.5 (Ollama)│
│ ─ normalize_case     │   │ case cards · queue ·   │  │ extract prose,  │
│ ─ match_discriminators│  │ audit table            │  │ rank candidates,│
│ ─ score_priority PURE│   │                        │  │ explain only    │
│ ─ raise_recheck_flag │   └────────────────────────┘  └─────────────────┘
│ ─ commit_priority ⚿  │
└──────────┬───────────┘
           │ reads (no network)
┌──────────▼───────────────────────────────────────────┐
│ DATA SUBSTRATE — single source of truth (DRY)        │
│ data/sats_tews.yaml · data/sats_discriminators.yaml  │
│ schema module (typed case) · citation helper ·       │
│ audit-record shape · tool-contract declarations      │
└──────────────────────────────────────────────────────┘
```

Legend: `⚿` = gated tool (requires an approval token); `PURE` = no I/O, no model, deterministic.

### Component Responsibilities

Each row is a **single responsibility** (SOLID-S). Nothing here both scores and writes; nothing here
both normalises and gates.

| Component | Owns | Does **not** do | Typical implementation |
|-----------|------|-----------------|------------------------|
| **Ingestion / normalisation** (`ingest` node, `normalize_case` tool) | Validate raw case (age, vitals, free-text complaint); parse prose → typed fields; emit `missing[]` and `out_of_scope` | Score, persist, decide colour | LangGraph node + MCP tool; LLM extraction constrained to a JSON schema, with a deterministic fallback parser |
| **Deterministic SATS scorer** (`score` node, `score_priority` tool) | TEWS arithmetic, discriminator override, `colour`, `tews`, `triggered_rules[]`, `citations[]`, `target_time` | Persist, notify, call the model | **Pure function** over typed fields, reading `data/*.yaml` via one loader; no model, no network |
| **Discriminator retrieval** (`retrieve` node, `match_discriminators` tool) | Rank candidate SATS discriminators for a complaint → IDs | Score or decide the colour | Keyword/alias match over `data/sats_discriminators.yaml` (embedding retrieval is the known de-scoped upgrade — E-09) |
| **Deterioration re-check** (`recheck` node, `raise_recheck_flag` tool) | Compare serial vitals → a flag | Re-classify or reorder the queue | Pure function over two vitals snapshots; returns a flag only |
| **Approval gate** (`approval_gate` node) | Pause for a **named** clinician; capture approve / edit / dismiss | Write, score, or hold state itself | LangGraph `interrupt()` + checkpointer; no side effects before `interrupt()` |
| **Gated commit** (`commit` node, `commit_priority` tool) | Idempotent queue write + audit entry, **only** with a valid approval token | Score, decide, or run without approval | MCP tool keyed by `case_id` (+ content hash); refunds/refuses without `approved_by` |
| **Audit log** (cross-cutting interceptor + `log/audit.jsonl`) | One appended, hash-chained record per tool call | Contain business logic | A single logging function every tool routes through (DRY); hash = H(prev_hash ‖ record) |
| **Evaluation harness** (`evals/` CLI) | Run cases N× through the **same graph interface**, record colour/citations/invariants/latency/tokens | Live in the request path | Injects a stub/deterministic model via the same interface (DIP); writes `report.json` |
| **Presentation / desk surface** (`handover` node) | Render the sourced case card; surface the gate | Decide anything | Local terminal/CLI streaming tool calls + citations |

### Boundary rule of thumb

> If a component answers a **question** (what is this? what colour? has it changed?), it is a **tool**.
> If it **controls flow** (what next? ask whom?), it is a **node**.
> If it **remembers**, it is the **checkpointer** or the **SQLite store**, never the graph state alone.

---

## Recommended Project Structure

```
triagedesk/
├── data/                     # SATS rules — the ONLY place clinical numbers live (DRY)
│   ├── sats_tews.yaml        #   parameter → band → points; TEWS → colour thresholds
│   └── sats_discriminators.yaml  # discriminator → category → citation
├── schema/                   # one typed case model (pydantic); imported everywhere (DRY)
│   └── case.py               #   vitals, complaint, missing[], out_of_scope, score result
├── rules/                    # data loader + validator (no business logic beyond parsing rules)
│   ├── loader.py
│   └── citation.py           # the single citation formatter (no inline strings anywhere)
├── core/                     # PURE deterministic functions — no I/O, no model, no MCP
│   ├── tews.py               #   TEWS arithmetic over the loaded bands
│   ├── discriminators.py     #   match + override resolution
│   ├── scorer.py             #   score_priority(): combines TEWS + overrides → colour + citations
│   └── recheck.py            #   serial-vitals comparison → flag
├── mcp_server/               # our MCP server: thin @mcp.tool() wrappers over core/*
│   ├── server.py             #   FastMCP("triagedesk"); exposes 5 tools
│   └── contracts.py          #   one declaration per tool (shared with the graph — DRY)
├── graph/                    # LangGraph: nodes route, they do not compute
│   ├── state.py              #   typed graph state
│   ├── nodes.py              #   ingest, normalize, retrieve, score, verify, recheck, gate, commit, handover
│   ├── edges.py              #   conditional edges (missing / out_of_scope / retry / recheck)
│   └── build.py              #   compiles graph with injected tools + checkpointer
├── llm/                      # the model boundary — the ONLY place the model is called
│   ├── client.py             #   Ollama/Qwen2.5 wrapper + structured-output contract
│   └── prompts/              #   pinned + hashed prompt templates
├── store/                    # thin adapter onto the borrowed SQLite MCP (interface, not impl)
│   └── case_store.py         #   save_case(), enqueue(), write_audit()
├── audit/                    # hash-chained logging — one function, used by every tool call
│   └── log.py
├── gate/                     # approval token shape + validation (idempotency key)
│   └── approval.py
├── evals/                    # harness + synthetic cases + report
│   ├── cases/                #   E-01…E-13 YAML fixtures
│   └── run.py                #   injections: model stub, tool timeout, malformed JSON
├── cli.py                    # one-command entry: `uv run triagedesk demo | eval`
└── tests/                    # unit tests for core/* against hand-computed colours
```

### Structure Rationale

- **`data/` vs `core/` vs `rules/`:** the clinical content (bands, discriminators, citations) is *data*;
  the arithmetic is *code*; the loader is the *one* seam between them. A new SATS rule is a YAML edit —
  no code touched (OCP). This is also what makes the live "add a requirement" review a one-liner.
- **`core/` is pure and I/O-free:** it can be unit-tested against hand-computed expected colours with no
  model, no MCP, no database. The scorer is the load-bearing correctness component; keeping it pure is
  what makes the evaluation honest.
- **`mcp_server/contracts.py` is shared with `graph/`:** the tool contract is declared once and imported
  by both sides, so the MCP server and the graph cannot drift (DRY). This is the DIP seam — the graph
  binds to the *interface*, so the owned server can be swapped for the borrowed store adapter.
- **`llm/` is the only module that calls the model:** one boundary to constrain, hash, stub (in evals),
  and swap. Nothing else imports a model client.
- **`gate/` is separate from `commit`:** the approval record and its validation are not colocated with
  the write, which keeps "who may authorise" distinct from "how we persist".

---

## Architectural Patterns

### Pattern 1: Deterministic operator behind an MCP tool (the orchestrator/operator split)

**What:** The LLM orchestrates, extracts, and explains; a deterministic tool computes the auditable
decision. No number (TEWS, colour, target time) is ever produced by the model.
**When to use:** Any regulated decision where the answer must survive a clinical/regulatory audit and be
reproducible run-to-run.
**Trade-offs:** More code in the scoring tool and a serialisation boundary; in exchange you get
reproducible cases with known expected outputs, a citation invariant the model cannot fabricate away, and
prompt-injection resistance (an injected "mark RED" has no rule citation and is rejected).

**Backing:** Multiple independent 2026 sources converge on the same claim — "LLMs make better
orchestrators than operators; the deterministic substrate is what gets audited" (HackerNoon; Adnan
Masood; Simplai; Elementum; AWS Prescriptive Guidance). This is not a TriageDesk idiosyncrasy; it is the
current consensus pattern for regulated agentic decisioning.

**Example:**
```python
# core/scorer.py — pure, deterministic, no model, no I/O
def score_priority(case: Case, rules: SatsRules) -> ScoreResult:
    tews = sum(band.points for band in rules.tews_bands(case.vitals))   # arithmetic
    tvs_colour = rules.colour_for_tews(tews)                            # data-driven
    overrides = [
        d.category for d in rules.match_discriminators(case.complaint)
        if d.category.urgency > tvs_colour.urgency                      # most-urgent wins
    ]
    final = max([tvs_colour, *overrides], key=lambda c: c.urgency)
    return ScoreResult(colour=final, tews=tews,
                       triggered_rules=[...], citations=[ ... ])        # every rule cites
```

### Pattern 2: LLM-as-orchestrator with an explicit graph (not free-form ReAct)

**What:** The control flow is fixed in the LangGraph graph; the model only makes bounded decisions at
named nodes (normalise, rank discriminators, explain).
**When to use:** Small CPU model (Qwen2.5-3B), reproducibility required, latency budgeted.
**Trade-offs:** Less "emergent" behaviour, more boilerplate — but far fewer random failures, which is what
the reliability criterion rewards. Free-form ReAct on a 3B CPU model is an unreliable free agent.

### Pattern 3: Human-in-the-loop gate as a node that interrupts (LangGraph `interrupt()` + checkpointer)

**What:** `approval_gate` calls `interrupt(payload)`; the checkpointer saves state; execution waits until
resumed with `Command(resume=<decision>)`. The resume value becomes the return value of `interrupt()`. The
node then routes to `commit` (approve) or `handover`/`cancel` (dismiss).
**When to use:** Before every irreversible action (queue write, referral, deterioration-driven reorder).
**Trade-offs:** Requires a checkpointer and a stable `thread_id`; the node **restarts from the beginning
on resume**, so *any side effect before `interrupt()` must be idempotent* — put side effects after the
interrupt or in a separate node.

**Critical rules (from LangGraph docs — MEDIUM confidence, official):**
- Never wrap `interrupt()` in a bare `try/except` — it pauses by raising; a catch swallows the pause.
- Do not conditionally skip or loop `interrupt()` in one node (index- and invocation-based matching cause
  exponential re-execution); loop back via a **conditional edge** instead.
- Only JSON-serializable payloads; typed resume values via `response_schema` need `langgraph>=1.2.12`.
- `Command(resume=...)` is the only `Command` you pass *into* the graph as input.

**Example:**
```python
# graph/nodes.py — no side effect before interrupt(); the write is in a LATER node
def approval_gate(state: CaseState) -> Command[Literal["commit", "handover"]]:
    decision = interrupt({
        "question": "Approve this priority for the queue?",
        "case_id": state.case_id,
        "proposed": state.score.colour,
        "citations": state.score.citations,
    })                                   # resume value: ApprovalDecision
    if decision.action == "approve":
        return Command(goto="commit", update={"approval": decision})
    return Command(goto="handover", update={"approval": decision, "committed": False})
```

### Pattern 4: Idempotent, approval-keyed write boundary

**What:** `commit_priority` refuses without an `approved_by` token and is keyed by `case_id` (+ content
hash), so a retried or replayed call cannot place a patient twice.
**When to use:** The one irreversible/queue-affecting action.
**Trade-offs:** A little bookkeeping; the payoff is safety under retry/replay and a hash-chainable audit.
This is also where DIP pays off: the graph calls the tool *interface*; the tool's persistence goes through
the borrowed SQLite MCP adapter, so swapping the store does not touch the graph.

### Pattern 5: Data-driven rule substrate (OCP in practice)

**What:** TEWS bands, colour thresholds, discriminators, and citations live in YAML. A loader validates
and exposes them; the scorer reads them.
**When to use:** When clinical content will be reviewed/extended by non-authors (the live review).
**Trade-offs:** A small loader/validator to build and test; worth it, because "add a rule" becomes a
one-line edit and clinical review is separated from code review.

### Pattern 6: Audit as a cross-cutting interceptor, not scattered calls

**What:** Every tool call routes through one logging function that appends a hash-chained record
(`prev_hash`, `hash`, inputs, outputs, actor, approver). A `@wrap_tool_call` middleware (LangChain) can
wrap every tool call agent-side, which is exactly the "one place" DRY wants.
**When to use:** Tamper-evidence is a scored requirement and a defensibility property.
**Trade-offs:** Negligible overhead; one more shared function that must stay single-sourced.

### Pattern 7: Checkpointer as the pause store, SQLite store as the system of record

**What:** Two distinct persistence roles — the **checkpointer** holds LangGraph thread state for
pause/resume; the **SQLite store** holds case cards, queue positions, and the audit table.
**When to use:** Always, once the gate exists. Do not conflate them.
**Trade-offs:** Two stores to reason about; keep `thread_id == case_id` so a case and its in-flight graph
state share one pointer. Use `InMemorySaver` for tests, `SqliteSaver` locally, Postgres only if it ever
leaves a single machine.

---

## Data Flow

### Request Flow (raw input → sourced priority → gated write)

```
Raw case (vitals + free-text complaint)   ── untrusted input
    │
    ▼
[ ingest ]  validate + type fields; missing[] / out_of_scope
    │
    ▼
[ normalize ]  LLM(extract to schema) ▶ normalize_case           ── LLM boundary
    │            (deterministic fallback parser on failure)
    │
    ├─ missing critical vitals ─▶ [ request_missing_info ] ─▶ back to nurse (recover, don't guess)
    ├─ out_of_scope (paediatric) ─▶ [ escalate ] ─▶ handover (safe abstention; no adult score)
    ▼
[ retrieve ]  match_discriminators(complaint) ▶ ranked IDs       ── deterministic
    │
    ▼
[ score ]   score_priority(typed case) ▶ colour + tews + triggered_rules + citations + target_time
    │                                                             ── DETERMINISM LIVES HERE
    ▼
[ verify ]  citation invariant: every priority cites a rule?
    │         no ▶ retry once ▶ still no ▶ deterministic fallback or escalate (never uncited)
    ▼
[ recheck ]  raise_recheck_flag(serial vitals) ▶ second-look flag ── deterministic; never re-classifies
    │
    ▼
[ approval_gate ]  interrupt({proposed colour, citations, case_id})  ═══ PAUSE ═══
    │                 state saved by checkpointer; nurse/clinician sees the sourced card
    │
    ├─ dismiss ─────────────▶ handover (nothing written)
    ├─ edit (new colour) ───▶ handover (recorded as a clinician override; nothing auto-written)
    └─ approve ──▶ [ commit ]  commit_priority(approval token) ▶ queue + audit entry (IDEMPOTENT)
    │
    ▼
[ handover ]  render sourced case card + tool-call trace + citations
```

### State Management

```
LangGraph state (thread-scoped)                 SQLite store (system of record)
  case_id (= thread_id)                            case_cards
  raw_input, normalised fields                     queue_positions
  score: colour/tews/rules/citations               audit table (hash chain)
  recheck_flag                                     │
  approval: {approved_by, role, ts, decision}      │
  missing[], out_of_scope, committed               │
        │                                          │
        ▼  checkpointer.put / put_writes            ▼  borrowed MCP tool calls
   SqliteSaver(checkpoint.db)                  MultiServerMCPClient (SQLite MCP)
        ▲
        │  Command(resume=decision)  ── same thread_id ──▶ node re-runs → routes
```

### Key Data Flows

1. **Happy path:** raw case → typed fields → discriminator match → deterministic score (+citations) →
   verify → approval gate (pause) → resume "approve" → idempotent `commit_priority` → queue + audit.
2. **Missing vital (E-05):** `normalize` emits `missing=[temperature]`; the `missing` conditional edge
   routes to a recovery node that asks the nurse to re-measure — the system **never fabricates** a value
   and **never commits**.
3. **Out-of-scope / paediatric (E-06):** `out_of_scope=true` routes to escalate; no adult SATS colour is
   produced; nothing commits. (Safety invariant INV-4.)
4. **Deterioration (E-07):** serial vitals trigger `raise_recheck_flag`; the flag routes to the gate as a
   *second-look request*; queue position is **unchanged** unless the clinician acts. (SN-5.)
5. **Failure recovery (E-12):** malformed model JSON or a tool timeout → `verify` retries once → on a
   second failure the graph takes the **deterministic path** (score from already-parsed fields) or
   escalates; never emits an uncited/partial priority. (JC-1.)
6. **Prompt injection (E-13):** instructions inside the complaint are parsed as data; the deterministic
   scorer means no sentence can set a colour; uncited "RED" is rejected by `verify`.
7. **Audit:** every tool call appends one hash-chained record to `log/audit.jsonl` and the SQLite audit
   table; the commit record carries `approved_by` + `role`. (BW-8/10, JC-5.)

---

## The Human-in-the-Loop Gate and the Write Boundary

**Where the boundary sits:** at the *transition from proposal to persistence*. Everything up to and
including `score` and `verify` is **advisory and reversible** (it computes and remembers). The only
irreversible action is `commit_priority`, and the graph can only reach it through `approval_gate`.

Why this placement matters:
- **It is structural, not procedural.** A prompt cannot bypass a `Command(goto=...)` that only the
  resumed `interrupt()` value can produce. The model has no edge to `commit`.
- **It is idempotent.** `commit_priority` keys on `case_id` (+ content hash) and refuses without an
  approval token, so retries/replays/reconnects cannot double-place a patient (D16, SW-3).
- **The approver is named.** `approved_by`, `role`, `approved_at`, `decision`, `final_colour` are recorded
  and audited (SW-4). Authenticated identity is a declared production requirement, not a demo feature.
- **The pause is durable.** The checkpointer writes the exact graph state at the interrupt, so the gate
  can be held across a process restart — the realistic case at a busy desk.

**Design consequence (non-obvious):** because a resumed node re-runs from its top, the `approval_gate`
node must contain **no non-idempotent side effect before `interrupt()`**. Keep the audit "approval
requested" entry out of the pre-interrupt path, or make it an upsert keyed by `case_id`. The commit (and
its audit entry) live in the *next* node, which runs once.

---

## Where the LLM Sits — and Where Determinism Must Sit

| Concern | Owner | Rationale |
|---------|-------|-----------|
| Parse free-text complaint → typed fields | **LLM** (constrained JSON) | Language/ambiguity is the LLM's job |
| Detect `missing[]`, `out_of_scope` | LLM proposes, **deterministic validator confirms** | Safety-critical flags must not be model-discretionary |
| Rank candidate discriminators | **LLM may assist; deterministic matcher decides** | Retrieval is the known weak link (E-09); keep it inspectable |
| **TEWS arithmetic** | **Deterministic** | A number from an LLM is neither auditable nor reproducible |
| **Colour / target time** | **Deterministic** | Must survive a clinical-audit question; most-urgent-wins is a rule |
| **Citations** | **Deterministic** (one helper) | "Unsourced is worse than none" (SN-6) |
| Deterioration flag | **Deterministic** | Comparison of serial vitals; never a verdict |
| Explanation / handover prose | **LLM** | Presentation only; cannot change the colour |
| Approval | **Human** | Authoritative |
| Persistence | **Borrowed store via tool** | Not the model's, not the graph's |

**The invariant:** *the score path never crosses the model boundary.* Once the complaint is in typed
fields, the colour is a pure function of `data/*.yaml` + those fields. That single rule simultaneously
delivers defensibility (JC-5), evaluation honesty (JC-4), and injection resistance (SW-1).

**Boundary discipline:** `llm/` is the only module that calls the model. `core/` must not import it. A
lint/test that fails if `core/` imports `llm/` or any MCP client is a cheap, high-value guardrail.

---

## Build Order and Dependency Graph

The dependency graph is a **DAG from data outward**; nothing downstream can be built before its inputs.

```
data/*.yaml ──▶ schema + loader/validator ──▶ core/* (pure scorer, discriminator match, recheck)
                                                   │
                                                   ├──▶ mcp_server (wrap core as 5 tools + contracts)
                                                   │
        llm/client (structured output) ────────────┼──▶ graph (nodes + edges, injected tools)
                                                   │            │
                                                   │            ├──▶ checkpointer + approval_gate (interrupt)
                                                   │            │
                                                   │            └──▶ borrowed SQLite MCP (store adapter)
                                                   │                       │
                                                   └──▶ audit logger (hash chain) ──▶ commit_priority
                                                                              │
        evals harness (injects stub model + fault injection) ◀────────────────┘
```

### Suggested Build Order

| Step | Build | Depends on | Exit criteria | Front-loads risk? |
|------|-------|-----------|---------------|-------------------|
| 1 | `data/*.yaml` + `schema/` + `rules/loader` + citation helper | — | Loader validates the SATS tables; one case parses | — |
| 2 | `core/*` pure scorer / discriminator match / recheck | 1 | Scorer unit tests green vs hand-computed colours (E-01/02/04/10/11) | **Correctness risk retired** |
| 3 | `llm/client` — prove Qwen2.5 emits valid structured output; pick 3B vs 1.5B | — | One case parsed into typed JSON on this machine | **Model/RAM risk retired first** |
| 4 | `mcp_server` — 5 tools incl. gated `commit_priority` stub + `contracts.py` | 2 | MCP server lists 5 tools; acting tools behave | — |
| 5 | `graph/` — nodes + conditional edges (missing / out_of_scope / retry / recheck) | 3, 4 | End-to-end run to the gate (no commit yet) | — |
| 6 | Checkpointer + `approval_gate` (`interrupt`) + `Command(resume)` | 5 | Run **refuses to commit without approval** | **Safety-gate risk retired** |
| 7 | Borrowed SQLite MCP adapter + `commit_priority` idempotent write + audit hash chain | 6 | Commit writes once; replay does not duplicate | — |
| 8 | Recovery paths: retry-once, deterministic fallback, abstention, missing-vital recovery | 5,6 | E-05/06/12 behave; invariants hold | — |
| 9 | `evals/` harness + 13 synthetic cases × 3 runs | 4–8 | `report.json` populated; E-09 captured as the honest failure | — |
| 10 | CLI surface + demo recording + docs | 9 | One-command run on a clean clone; <3-min video | — |

**Critical path:** 1 → 2 → 4 → 5 → 6 → 7. Steps 2 and 3 are parallelizable and are the two riskiest —
retire both on Day 1–2. Step 6 (the gate refusing a commit) is the single most important behavioural
milestone; if schedules slip, protect it over polish.

**Why this order (not by feature):** every step's inputs are already typed, pure, or persisted by the
step before it. You can *test each layer in isolation* precisely because the boundary between them is an
interface (DIP) rather than a call chain into a monolith.

---

## How SOLID Shapes the Boundaries (OCP + DIP in particular)

| Principle | Concrete rule in this codebase | What it buys |
|-----------|-------------------------------|--------------|
| **S** — single responsibility | One job per module/tool/node; `score_priority` scores, `commit_priority` persists, `approval_gate` pauses. A node routes; it does not compute. | No god-node; every component is explainable line-by-line (live review). |
| **O** — open/closed | **New SATS rule = a `data/*.yaml` edit.** **New capability = a new tool + a new node** (e.g. referral routing = `referral` node + `route_referral` tool + one edge). Existing modules untouched. | "Add a requirement live" is a one-line data change; the codebase never grows by editing working code. |
| **L** — Liskov substitution | Every MCP tool honours its declared contract; no tool silently changes its return shape. The owned store adapter and the borrowed SQLite MCP are interchangeable behind the same interface. | Swapping storage cannot break the graph or a caller. |
| **I** — interface segregation | Narrow tools, no "fat" tool. A node depends only on the tools it uses (`score` node does not see `commit_priority`). | No accidental privilege; the gate's reachability is controlled by edges, not by capability. |
| **D** — dependency inversion | The graph depends on the **MCP tool interface**, not concrete implementations. Scorer rules, store, and model are **injectable**. | Isolated unit tests (inject a stub scorer/store), the owned↔borrowed swap, and the eval harness's model stub all fall out for free. |

**The decisive test for any change:** *"Can I do this by adding data, or by adding a tool+node — without
editing existing working code?"* If yes, it is OCP-compliant. If a change edits the scorer to add a rule,
or edits a node to add a capability, it violates OCP and is rejected at review.

Two cheap guardrails that enforce the above mechanically (worth building early):
1. a test that fails if `core/` imports `llm/` or any MCP client (protects the determinism boundary + DIP);
2. a test that fails if any TEWS band / colour / discriminator / citation string appears outside `data/`
   and `rules/citation.py` (protects DRY).

---

## Scaling Considerations

TriageDesk is a **single-desk decision aid**, not a multi-tenant SaaS. Scale means "more desks", not
"millions of users".

| Scale | Architecture adjustments |
|-------|--------------------------|
| 1 desk (this build) | Monolith: one process, LangGraph + SqliteSaver + borrowed SQLite MCP, local Ollama. The right choice — least auditable surface. |
| A few desks / one department | Keep one graph per case; move the system-of-record to a shared SQLite/Postgres; keep the checkpointer per process. Batch is not needed — cases are independent and latency-bounded (seconds). |
| Many facilities | Split the deterministic scorer (stateless) from the model runtime (GPU/CPU pool); promote the checkpointer to Postgres; the borrowed store becomes a real service. The tool interface is already network-capable (MCP transports), so the split is a transport change, not a rewrite. |

### Scaling Priorities

1. **First bottleneck: model latency on CPU.** A 3B Qwen2.5 on ~6.9 GB RAM is the throughput ceiling.
   Fix: keep the model out of the score path (already true), cap the model to normalise/explain, and pin a
   small context. This is why the deterministic core matters *even for performance*.
2. **Second bottleneck: the model being in the loop at all for easy cases.** When the complaint already
   matches a discriminator or the vitals already yield RED, the LLM adds latency without value — the
   graph can shortcut. A "no-model fast path" is a natural, OCP-friendly extension (a new edge, no edits).
3. **Do not pre-optimize:** no queues, no sharding, no vector store until a real desk demands it.

---

## Anti-Patterns

### Anti-Pattern 1: The god-node that normalises, scores, gates, and writes
**What people do:** collapse the pipeline into one "handle_case" node for speed.
**Why it's wrong:** it leaks responsibility (SRP), hides the determinism boundary, makes the gate
bypassable, and cannot be unit-tested. It also fails the live code walkthrough.
**Do this instead:** keep the small named nodes; let them route, not compute.

### Anti-Pattern 2: A tool that both scores and writes
**What people do:** `score_and_enqueue()` to save a round-trip.
**Why it's wrong:** it fuses the reversible (compute) with the irreversible (persist) across the safety
gate; the only irreversible action must be narrowly reachable and approvable.
**Do this instead:** `score_priority` (pure) + `commit_priority` (gated, idempotent), reached only through
`approval_gate`.

### Anti-Pattern 3: Non-idempotent work before `interrupt()`
**What people do:** write an audit entry / call an API before the interrupt.
**Why it's wrong:** the node re-runs from the top on resume, so the side effect fires repeatedly.
**Do this instead:** put side effects after `interrupt()` or in the following node; make any pre-interrupt
effect an upsert keyed by `case_id`.

### Anti-Pattern 4: Duplicated clinical constants
**What people do:** hard-code a TEWS band or a citation string in a node.
**Why it's wrong:** DRY violation and — worse — a correctness *and* audit risk: two numbers can disagree.
**Do this instead:** rules live only in `data/`; citations come from one helper.

### Anti-Pattern 5: Letting the model compute or override the colour
**What people do:** ask the LLM for the priority, or let it "adjust" the deterministic result.
**Why it's wrong:** unauditable, non-reproducible, injectable.
**Do this instead:** the model normalises and explains; the tool scores. `verify` rejects any uncited
priority and any output that disagrees with the tool's score.

### Anti-Pattern 6: Conflating the checkpointer with the system of record
**What people do:** treat LangGraph checkpoint state as the case database.
**Why it's wrong:** checkpoint state is thread-scoped, internal, and can be pruned; case cards and the
queue need a stable schema and its own audit.
**Do this instead:** checkpointer pauses the graph; SQLite/borrowed MCP holds cases, queue, and audit.

---

## Integration Points

### External Services

| Service | Integration pattern | Notes |
|---------|---------------------|-------|
| **Local LLM (Ollama + Qwen2.5-3B Q4_K_M)** | HTTP to `localhost` only; structured/constrained JSON output | Pin + hash model + prompts. 1.5B fallback for RAM ceiling. No egress. |
| **Our MCP server (`triagedesk`)** | In-process / stdio FastMCP; 5 tools | `@mcp.tool()` over pure `core/*`. stdio keeps the tool surface off the network. |
| **Borrowed SQLite MCP** | LangChain MCP client → tool calls | **Currency note below.** Verify a maintained server before Day 2 (G-4). |
| **SQLite checkpointer** | `langgraph-checkpoint-sqlite` compiled into the graph | Separate DB from the case store; `thread_id = case_id`. |

> **Currency alert (MEDIUM confidence, official docs).** `langchain-mcp-adapters` is **archived** (Sep 2026).
> MCP support now ships in the built-in `langchain.mcp` namespace via `langchain[mcp]>=1.4.0` (currently
> **beta**): `MultiServerMCPClient` → `MCPAdapter` (async context manager, `list_tools()`, `mcpServers`
> config, transport inferred). *Recommendation:* pin the archived `langchain-mcp-adapters` if you need a
> stable, well-documented surface for a 6-day build, and record the migration as a deliberate, disclosed
> choice — or adopt `langchain.mcp` and accept the beta warning. Do not do both. Either way, keep the MCP
> client behind the `store/` adapter so the choice is swappable (DIP).

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| graph ↔ MCP tools | tool interface (injected) | The DIP seam; enables stub injection + owned↔borrowed swap |
| core ↔ data | loader read-only | Rules are data; a rule change never edits `core/` (OCP) |
| graph ↔ checkpointer | `put`/`put_writes`/`get_tuple` at super-steps | Holds pause state; `thread_id = case_id` |
| commit ↔ store | borrowed MCP tool call | Only queue-mutating path; approval-token gated + idempotent |
| every tool ↔ audit | one logging function (interceptor) | Hash-chained; single source of the record shape (DRY) |
| evals ↔ graph | same graph interface, stub model injected | Honest evaluation; fault injection for E-12 |

---

## Sources

- **Project design docs (HIGH confidence — authoritative requirements):** `PROJECT.md`,
  `ARCHITECTURE.md` (repo root), `DECISIONS.md`, `REQUIREMENTS.md`, `SECURITY.md`, `EVALS.md`,
  `docs/SATS.md`, `CONVENTIONS.md`.
- **LangGraph interrupts — human-in-the-loop** (official docs, MEDIUM):
  <https://docs.langchain.com/oss/python/langgraph/interrupts>
- **LangGraph persistence / checkpointers** (official docs, MEDIUM):
  <https://docs.langchain.com/oss/python/langgraph/persistence> and
  <https://docs.langchain.com/oss/python/langgraph/checkpointers>
- **langchain-mcp-adapters archive + `langchain.mcp` migration** (official docs, MEDIUM):
  <https://github.com/langchain-ai/langchain-mcp-adapters> (archived Sep 2026) and
  <https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters>
- **Agentic clinical CDS / human-in-the-loop consensus** (web, MEDIUM — cross-checked):
  MDPI *Future Internet* survey; Momentum *AI Agents for Healthcare*; Pariveda *Responsible Agentic AI*;
  Innovaccer evaluation guide.
- **Hybrid deterministic-rules + LLM orchestration** (web, MEDIUM — cross-checked):
  HackerNoon *Rule Engine + LLM Hybrid Architectures*; Adnan Masood, *Rule Engines in the Age of Agents*;
  Simplai *Hybrid AI Orchestration*; Elementum *Enterprise AI Orchestration*; AWS Prescriptive Guidance
  *Orchestration models*.

---

*Architecture research for: TriageDesk — MCP-based, LangGraph-orchestrated triage-support agent*
*Researched: 2026-10-09*
