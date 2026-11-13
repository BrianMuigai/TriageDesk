# Requirements: TriageDesk

**Defined:** 2026-11-13 (milestone **v1.3 Adaptive Triage**)
**Core Value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.

> Iron-clad engineering rule: **DRY + SOLID** (`docs/CONVENTIONS.md`). Every requirement below must be
> met without duplicating logic or violating the single-source-of-truth rule. The scorer, the citation
> helper and the audit interceptor are not edited. The planner may only choose **read-only investigation**
> actions; the colour is still produced in exactly one place.

---

## Milestone v1.3 Requirements

### Adaptive investigation

- [ ] **ADAPT-01**: The graph has a `plan` node that, before scoring, chooses exactly one next action from
      a **closed, typed** set — `gather_evidence`, `ask_question`, `re_extract`, `conclude`. The action set
      and its admissibility rules are declared once; no node inlines a second copy.

- [ ] **ADAPT-02**: The local model **proposes** the action with structured output over the closed set; a
      deterministic admissibility guard **validates** it against the current typed state and the remaining
      step budget, and substitutes the default (`conclude`) when the proposal is inadmissible, malformed,
      unparseable, or the budget is spent. The model is never the authority, and a bad proposal can never
      widen what the graph is able to do.

- [ ] **ADAPT-03**: The safety kernel is a **non-skippable suffix**: `conclude` is the only edge into
      `score`, and `score → ground → verify → recheck → assess → approval_gate → commit → handover` is
      unchanged. A structural test proves by graph inspection that no investigation node reaches `score`,
      `approval_gate` or `commit`, and that `commit` still has exactly one inbound edge.

- [ ] **ADAPT-04**: Every investigation action is read-only with respect to the queue, the colour and the
      clinical facts: it may add investigation facts only (evidence passages, candidate ids, an appended
      nurse answer, a re-extraction hint). No investigation action writes `priority`, `commit_result`, or a
      queue row, and none may emit a colour.

- [ ] **ADAPT-05**: Each planner decision is a typed contract recorded in the audit trail and the span
      stream — action, rationale, the signals it used, and the step index — so an auditor can answer
      "why did it do that next?" from the record alone, without re-running the case.

- [ ] **ADAPT-06**: The investigation loop is **bounded**: a declared maximum number of steps (default 3),
      a no-repeat guard on an identical `(action, input)` pair, and a monotonically decreasing budget.
      Budget exhaustion concludes the investigation; it never raises, loops, or falls through to the gate.

### MCP elicitation

- [ ] **ELICIT-01**: A new owned tool `request_clarification` elicits a typed answer **mid-tool-call** via
      `ctx.elicit()` for at most three targeted questions. It is read-only, takes no approval token, and
      writes no queue row.

- [ ] **ELICIT-02**: The elicitation round-trip works end-to-end through the **shipped adapter**, not a
      stub: tool call → `interrupt()` → resume with the nurse's answer → the tool returns the answer and
      the call completes. Proven by a test that drives `langchain.mcp.MCPAdapter` against the real owned
      server.

- [ ] **ELICIT-03**: `decline` and `cancel` are **refusals, not answers**: the graph concludes or defers,
      and never fabricates, infers or defaults a value from a refusal.

- [ ] **ELICIT-04**: The owned-tool allowlist fan-out (server, adapter/discovery, graph allowlist, test
      fake, exact-set assertion) moves in **one atomic change**, and the exact-set assertion still fails
      closed on a missing or unexpected tool.

- [ ] **ELICIT-05**: The desk and CLI surfaces present an elicitation interrupt **distinctly** from the
      approval gate — a question, not a decision — and neither surface can commit from it.

### Measurement

- [ ] **MEAS-01**: The eval harness records per-case investigation facts: steps taken, the action
      sequence, whether an elicitation occurred, and whether the guard overrode a proposal.

- [ ] **MEAS-02**: The report publishes an **adaptive-vs-baseline** comparison on the same suite (planner
      enabled vs default-conclude), with colour correctness, coverage, steps and latency side by side. The
      delta is stated even when it is zero or negative.

- [ ] **MEAS-03**: All four safety invariants (INV-1..INV-4) hold on **every** adaptive run; no
      under-triage is introduced; the declared failure E-09 stays visible and is never tuned green.

- [ ] **MEAS-04**: `EVALS.md` is regenerated only by `scripts/emit_evals.py` from `report.json`, and
      `--check` exits 0.

### Documentation

- [ ] **DOC-01**: `ARCHITECTURE.md` states the two-layer shape — bounded adaptive investigation over a
      frozen safety kernel — and states why free-form ReAct is still rejected.

- [ ] **DOC-02**: A reviewer-facing answer to *"is this a rules engine?"* ships in the docs, grounded in
      the measured adaptive-vs-baseline delta and the structural safety proof, not in adjectives.

- [ ] **DOC-03**: `STATUS.md` closes **G7** (elicitation) and moves *dynamic planning* from partial to
      present, while naming the honest residual limits (bounded action set, no free-form planning,
      CPU-model proposals).

- [ ] **DOC-04**: `docs/DECISIONS.md` records D31 (bounded autonomy over a frozen kernel), D32 (model
      proposes / guard disposes) and D33 (server-side elicitation), plus the narrow revision to D1.

- [ ] **DOC-05**: `docs/MCP.md` and the packaged `triagedesk-triage` skill document the elicitation
      round-trip and the fail-closed stop rules.

---

## Future Requirements (deferred)

- **G6 — Online evaluation and drift monitoring** — the report stays an offline measurement.
- **G10 — Runtime model routing and automatic fallback** — `qwen2.5:1.5b` remains the measured default.
- **G4 — Authenticated approver identity** — recorded, not authenticated; a production requirement.
- **G8 — Multimodal intake** (voice, chart/cuff photo) — the real desk interface, absent by choice.
- **MCP sampling** — deliberately out of scope: the server must not borrow the client's model, and the
  local model is the only inference path we can defend.

## Out of Scope (explicit)

- **Free-form ReAct / LLM-authored plan DAG** — makes the safety kernel skippable and is unevaluable on a
  1.5B CPU model. The planner's action set is closed for this reason.
- **Multi-agent planner/executor/critic** — the `verify` node plus the admissibility guard cover the
  critic role structurally; a second autonomous agent adds risk without evidence.
- **Runtime self-learning / long-term memory** — unsafe at the point of care.
- **Autonomous queue movement** — forbidden by the challenge; `commit_priority` remains the only
  queue-mutating tool and stays gated.

## Traceability

| Requirement | Phase |
| --- | --- |
| ADAPT-02, ADAPT-04, ADAPT-06 | Phase 19 |
| ELICIT-01, ELICIT-02, ELICIT-03, ELICIT-04, ELICIT-05 | Phase 20 |
| ADAPT-01, ADAPT-03, ADAPT-05 | Phase 21 |
| MEAS-01, MEAS-02, MEAS-03, MEAS-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05 | Phase 22 |
