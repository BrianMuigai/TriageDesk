# DECISIONS — TriageDesk

> ADR-lite. Each decision: **context · decision · why · consequence**. Rationale is preserved so the
> live technical review can be answered from the record, and so third-party components are **disclosed**
> (instant-disqualifier DQ-8).

---

### D1 — Hybrid: deterministic scorer + LLM orchestration
**Decision:** the model orchestrates, extracts, and explains; a **deterministic tool** computes the
SATS/TEWS score and citations. No number ever comes from the LLM.
**Why:** defensibility (a priority must survive a clinical-audit question) and evaluation honesty
(deterministic cases with known expected outputs). An LLM computing arithmetic is neither auditable nor
reproducible.
**Consequence:** more code in the scoring tool; far stronger JC-4 and JC-5.

### D2 — Use the South African Triage Scale (SATS)
**Decision:** build on SATS (EMSSA), not an invented scale or the Manchester Triage System.
**Why:** the brief explicitly requires an existing triage scale; SATS is openly published, designed for
resource-limited African settings, and is a two-part algorithm (TEWS + clinical discriminators) that is
straightforward to encode. MTS is licensed (proprietary), which conflicts with an open-source repo.
**Consequence:** adult SATS in scope; paediatric SATS de-scoped (see D6). Source: SATS Training Manual
2012 (EMSSA), <https://emssa.org.za>.

### D3 — Local open-weights model: qwen3.5:4b, RAM-constrained
**Decision:** run the agent loop on the locally installed **`qwen3.5:4b`** (3.3 GB) via Ollama; a
**smaller Qwen is the documented fallback** if Phase 1's RAM measurement shows the 4B cannot run within
budget. Frontier models optional and never required to run. Extraction uses **structured JSON output**
(`format=<schema>`), not native tool-calling.
**Why:** eligibility requires a full task on an open-weights model, and patient data must not leave the
country; the 4B is already installed and gives better extraction than a 1.5B.
**Constraint discovered:** the host has **~6.9 GB RAM total and as little as ~0.8 GB free** — the 4B
needs ~3.3 GB, so the demo machine must free memory; the fallback keeps the demo runnable otherwise.
**Consequence:** possible latency/swap pressure (documented in `REQUIREMENTS.md` G-2); measured in
Phase 1 and recorded honestly. Record the `qwen3.5:4b` licence in the NOTICE.

### D4 — LangGraph for orchestration
**Decision:** LangGraph.
**Why:** open source; its `interrupt()` + checkpointer model maps directly onto "gate every irreversible
action on a named approver"; the explicit graph is easy to walk a judge through; node boundaries are
reusable. Alternatives (CrewAI, Pydantic AI, smolagents) were viable but had a weaker story for the
approval gate.
**Consequence:** slightly more boilerplate; much clearer agent shape for JC-1 and ST-1.

### D5 — Borrow the SQLite MCP server
**Decision:** use a pre-existing, **maintained** SQLite MCP server for the case/queue store and audit
table (candidates: `jparkerweb/mcp-sqlite`, `rusq/mcp-sqlite`). The official reference server is
archived and is not used.
**Why (one line):** *persistence, schema and query safety are solved — hand-rolling a database layer
adds zero triage value and adds auditable surface area we would have to defend.*
**Considered and declined:** a vector-store MCP for discriminator retrieval (stronger citation story,
more setup time). Its absence is exactly what makes case **E-09** fail — recorded as the honest
unfixed failure.
**Consequence:** satisfies BW-3; the "boring but correct" storage choice is deliberate. Because the
graph depends on the tool interface, swapping the server is a one-module change.

### D6 — Safe abstention on paediatric / out-of-scope input
**Decision:** the agent **detects** paediatric (age <12) or otherwise out-of-scope input and **abstains
+ escalates** to a human, instead of scoring with the adult chart.
**Why:** mis-scoring a child is dangerous. A deliberate, visible safe-failure is a stronger and more
honest story than a silent wrong answer.
**Consequence:** paediatric triage is out of scope (declared in `PROJECT.md`); tested as case E-06.

### D7 — Apache-2.0 licence
**Decision:** Apache-2.0 (OSI-approved).
**Why:** includes an explicit patent grant, which is appropriate for a health-adjacent project, while
remaining permissive.
**Consequence:** satisfies EL-3 and SB-2.

### D8 — English-only build
**Decision:** English input/output only; multilingual support is architecture-aware but out of scope.
**Why:** solo build under a ~6-day deadline; keeps prompt and eval surface small.
**Consequence:** the agent's multilingual potential is documented but not demonstrated.

### D9 — Synthetic data only
**Decision:** all fixtures are self-constructed synthetic patient records; a published scale is the
only external reference.
**Why:** the brief makes synthetic the default; no real patient data, consenting or not, avoids the
gravest instant-disqualifier entirely.
**Consequence:** no egress, no consent risk (DC-1…DC-3, DQ-5).

### D10 — Explicit graph over free-form ReAct
**Decision:** fix the control flow in the LangGraph graph; the model only makes bounded decisions at
named nodes.
**Why:** a small CPU model is an unreliable free agent. This keeps runs reproducible, which is what the
reliability criterion rewards.
**Consequence:** less "emergent" behaviour; far fewer random failures.

### D11 — SATS rules live in YAML data, not code
**Decision:** `data/sats_tews.yaml` and `data/sats_discriminators.yaml` hold the scoring logic.
**Why:** the live review (ST-1) adds a requirement on the spot; a one-line data edit makes that look
effortless. It also separates clinical content review from code.
**Consequence:** a small loader/validator is needed; worth it.

### D12 — Hash-chained audit log
**Decision:** every tool call is appended to `log/audit.jsonl` and the SQLite audit table, with a hash
chained to the previous entry.
**Why:** "readable log" is a scored, defensibility criterion; a tamper-evident chain is cheap and
credible.
**Consequence:** negligible overhead; strong JC-5 story.

### D13 — Single-theme entry; deterioration is a capability, not a second theme
**Decision:** enter under **Symptom-based priority scoring only**. The deterioration re-check is a tool
of the same agent, not a separate "Deterioration watch" submission.
**Why:** the rules forbid entering one project under more than one theme; the re-check exists to protect
the scoring workflow, not to be a second product.
**Consequence:** unambiguous one-theme compliance.

### D14 — Build with AI coding tools, ship only what we can explain
**Decision:** use AI coding assistants freely (explicitly allowed), but nothing ships that the author
cannot explain line-by-line in the live review.
**Why:** the brief says the live review is where they separate "directing a coding agent" from
"accepting output you cannot explain."
**Consequence:** a preference for explicit, small, named components over clever code — which also
happens to be the best shape for the live "add a requirement" test.

### D15 — Treat the presenting complaint as untrusted data, never instructions
**Decision:** free-text input is parsed into **typed fields**; instructions embedded in prose are never
executed. The colour is computed deterministically from the typed fields.
**Why:** a SOTA agent treats untrusted input as data. The deterministic scorer means prompt injection
cannot set a priority — an injected "mark this red" has no rule citation and is rejected.
**Consequence:** strong, cheap resistance to the most relevant injection vector; tested by E-13.

### D16 — Idempotent, approval-keyed queue writes
**Decision:** `commit_priority` is keyed by `case_id` (+ content hash) and requires an approval token.
**Why:** the queue write is the one irreversible action; retries must not place a patient twice.
**Consequence:** safe under retry/replay; complements the LangGraph `interrupt()` gate.
**v1.1 note:** the idempotency key now covers the **immutable case input** (the normalized `CaseInput`
payload), not `colour` alone — so an `edit` supersedes the queue row in place (one row, updated
colour, unchanged position) rather than inserting a second one.

### D17 — Pin and hash prompts, model, and scale versions
**Decision:** prompt templates, model version, SATS data, and tool schemas are pinned and hashed; every
audit record names the versions that produced it.
**Why:** reproducibility is a defensibility requirement — a priority must be explainable and
re-derivable.
**Consequence:** small config overhead; directly serves JC-5.

### D18 — DRY + SOLID are iron-clad engineering standards
**Decision:** all code, tests, configuration, and documentation adhere to **DRY** and **SOLID**. The
authoritative standard is [`CONVENTIONS.md`](CONVENTIONS.md), enforced at the **plan-check**,
**code-review**, and **verifier** gates.
**Why:** duplicated SATS values are simultaneously a correctness risk and a defensibility risk, and
responsibility leaks break the safety gate. Maintainability is how a solo builder keeps a 6-day sprint
auditable.
**Consequence:** a violation blocks a phase. Rules live once (YAML data / a single helper); a new
capability means a **new** tool + **new** node, leaving existing code untouched.

---

## Disclosed third-party components (DQ-8)

| Component | Origin | Licence/notes |
| --- | --- | --- |
| LangGraph | LangChain (open source) | MIT |
| MCP client adapter | `langchain.mcp` namespace | current; replaces archived `langchain-mcp-adapters` |
| Ollama | Ollama (open source) | MIT; runtime only |
| qwen3.5:4b | Alibaba (open weights) | record licence in NOTICE; installed locally |
| SQLite MCP server | maintained community (`jparkerweb/mcp-sqlite` / `rusq/mcp-sqlite`) | official reference server is archived |
| SATS manual | EMSSA | clinical content; cited, not redistributed wholesale |
