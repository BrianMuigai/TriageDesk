# Requirements: TriageDesk

**Defined:** 2026-11-13 (milestone **v1.3 Adaptive Triage**)
**Core Value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.

> Iron-clad engineering rule: **DRY + SOLID** (`docs/CONVENTIONS.md`). Every requirement below must be
> met without duplicating logic or violating the single-source-of-truth rule. The scorer, the citation
> helper and the audit interceptor are not edited. The planner may only choose **read-only investigation**
> actions; the colour is still produced in exactly one place.

---

## Milestone v1.3 Requirements

### Architecture documentation (reviewer-requested)

- [ ] **DIAG-01**: Two diagrams ship as separately readable assets with different audiences: **A** —
  adaptive clinical workflow (judge / clinician / product reviewer, understandable in under a minute);
  **B** — component and infrastructure architecture (engineer, traceable model call → MCP → DB →
  checkpoint → audit). The comprehensive reference diagram is retained.

- [ ] **DIAG-02**: Diagram A shows intake and observations, the deterministic emergency check, normalisation,
  discriminator retrieval and coverage, the four planner actions, the guard between proposal and execution,
  the iteration / clarification / evidence budgets, all four elicitation outcomes, the frozen kernel, the
  clinician decision, and the safe exits — and makes it visually unmistakable that the planner cannot
  score, approve or commit.

- [ ] **DIAG-03**: Diagram B shows the nurse-facing app, the LangGraph engine with planner and checkpoint
  persistence, the local model (measured default and documented fallback), the MCP client over stdio, the
  owned server's nine tools with `plan_next_step`, `request_clarification` and `commit_priority`
  distinguished, the guard as a separate control, the borrowed server's read-only paths, the Store-seam
  write, the three rule sources, the three persistence/observability stores, and the offline boundary.

- [ ] **DIAG-04**: Both diagrams share one vocabulary (labels match source names), one legend (human /
  deterministic / model proposal / persistence / safe exit), and one honesty rule: every element is marked
  implemented, tested, proposed or outstanding. No proposed feature is drawn as shipped.

- [ ] **DIAG-05**: One renderer produces every diagram asset from source
  (`docs/render-architecture.sh [stem]`); no diagram is hand-edited binary output.

- [ ] **DIAG-06**: `ARCHITECTURE.md` links both diagrams; `README.md` stays high-level; `SECURITY.md` states
  the real tool inventory and marks proposed tools as proposed; `STATUS.md` separates implemented /
  tested / proposed / outstanding.

### Adaptive investigation

- [ ] **ADAPT-01**: The graph has a `plan` node that, before scoring, chooses exactly one next action from
  a **closed, typed** set — `gather_evidence`, `ask_question`, `re_extract`, `finish_investigation`. The
  action set and its admissibility rules are declared once; no node inlines a second copy.

- [ ] **ADAPT-02**: The local model **proposes** the action with structured output over the closed set; a
  deterministic admissibility guard **validates** it against the current typed state and the remaining
  step budget, and substitutes the default (`finish_investigation`) when the proposal is inadmissible,
  malformed, unparseable, or the budget is spent. The model is never the authority, and a bad proposal can
  never widen what the graph is able to do.

- [ ] **ADAPT-03**: The safety kernel is a **non-skippable suffix**: `finish_investigation` is the only edge
  into `score`, and `score → ground → verify → recheck → assess → approval_gate → commit → handover` is
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
  a no-repeat guard on an identical `(action, input)` pair, and a monotonically decreasing budget. Budget
  exhaustion concludes the investigation; it never raises, loops, or falls through to the gate. An
  unresolved case that exhausts its budget still cannot deliver on a guess — the deterministic `assess`
  decides, and an ambiguous case defers.

- [ ] **ADAPT-07**: `re_extract` is **monotone**: it may fill a field that is missing, and it never
  overwrites a recorded vital, the original note, or a nurse's answer. A stated value always wins over a
  re-read value.

- [ ] **ADAPT-08**: The fourth action is named `finish_investigation` in code, contracts, tests and docs —
  one name, no synonym drift.

### MCP elicitation

- [ ] **ELICIT-01**: A new owned tool `request_clarification` elicits a typed answer **mid-tool-call** via
  `ctx.elicit()` for at most three targeted questions. It is read-only, takes no approval token, and
  writes no queue row.

- [ ] **ELICIT-02**: The elicitation round-trip works end-to-end through the **shipped adapter**, not a
  stub: tool call → `interrupt()` → resume with the nurse's answer → the tool returns the answer and
  the call completes. Proven by a test that drives `langchain.mcp.MCPAdapter` against the real owned
  server.

- [ ] **ELICIT-03**: Elicitation has **four distinct outcomes** — `accepted`, `declined`, `cancelled`,
  `unavailable` (the client cannot elicit). Only `accepted` carries an answer. A decline, cancel or
  unavailable client is **not** a negative clinical response and is never converted into a value.

- [ ] **ELICIT-04**: The owned-tool allowlist fan-out (server, discovery, graph allowlist, test fake,
  exact-set assertion) moves in **one atomic change**, and the exact-set assertion still fails closed on a
  missing or unexpected tool.

- [ ] **ELICIT-05**: The desk and CLI surfaces present an elicitation interrupt **distinctly** from the
  approval gate — a question, not a decision — and neither surface can commit from it.

- [ ] **ELICIT-06**: Every question is drawn from the loaded discriminator definitions (the closed set plus
  `data/*.yaml`), never authored freely by the model. A question that does not trace to a definition is
  not asked.

- [ ] **ELICIT-07**: Resuming an elicitation is **idempotent**: a resumed thread cannot duplicate a queue
  commit, and an already-answered question is not asked twice.

- [ ] **ELICIT-08**: A clarification answer is an **observation, not an approval**: it is appended to the
  case facts only, it never advances the case past the approval gate, and it never becomes a colour.

### Emergency bypass

- [ ] **EMERG-01**: A pure, deterministic pre-check runs on a structured case **before any model call**. When
  it fires, the graph skips extraction and the planner and enters the kernel at `retrieve → score`.

- [ ] **EMERG-02**: The pre-check reuses the ONE scorer and the loaded bands; it cannot disagree with the
  kernel's colour, and it never produces a colour itself.

- [ ] **EMERG-03**: The emergency arm still passes `verify → recheck → assess → approval_gate → commit`; it
  cannot write a queue row and cannot bypass the clinician.

- [ ] **EMERG-04**: An incomplete or unstructured case never fires the check (no imputation); it takes the
  normal path.

- [ ] **EMERG-05**: The bypass is recorded as a provenance fact and an audit/span event, so a reader can see
  that the case skipped the model and why.

### Measurement

- [ ] **MEAS-01**: The eval harness records per-case investigation facts: steps taken, the action
  sequence, whether an elicitation occurred, whether the guard overrode a proposal, and whether the
  emergency bypass fired.

- [ ] **MEAS-02**: The report publishes an **adaptive-vs-baseline** comparison on the same suite (planner
  enabled vs default-finish), with colour correctness, coverage, steps and latency side by side. The
  delta is stated even when it is zero or negative.

- [ ] **MEAS-03**: All four safety invariants (INV-1..INV-4) hold on **every** adaptive run; no
  under-triage is introduced; the declared failure E-09 stays visible and is never tuned green.

- [ ] **MEAS-04**: `EVALS.md` is regenerated only by `scripts/emit_evals.py` from `report.json`, and
  `--check` exits 0.

### Documentation

- [ ] **DOC-01**: `ARCHITECTURE.md` states the two-layer shape and why free-form ReAct is still rejected.

- [ ] **DOC-02**: A reviewer-facing answer to *"is this a rules engine?"* ships in the docs, grounded in
  the measured adaptive-vs-baseline delta and the structural safety proof, not in adjectives.

- [ ] **DOC-03**: `STATUS.md` closes **G7** (elicitation) and moves *dynamic planning* from partial to
  present, while naming the honest residual limits (bounded action set, no free-form planning,
  CPU-model proposals).

- [ ] **DOC-04**: `docs/DECISIONS.md` records D31 (bounded autonomy over a frozen kernel), D32 (model
  proposes / guard disposes), D33 (server-side elicitation), D34 (deterministic emergency bypass), and the
  narrow revision to D1.

- [ ] **DOC-05**: `docs/MCP.md` and the packaged `triagedesk-triage` skill document the elicitation
  round-trip and the fail-closed stop rules.

- [ ] **DOC-06**: The docs state which artefact is authoritative for queue handover (the committed queue row,
  not the printed card), that answering a clarification is not approval, that the approver's identity is
  recorded but not authenticated (G4), and that structured observations are currently two-state
  (stated / missing) with text-level negation handled — a four-state observation model is declared as an
  outstanding limitation, not drawn as if it existed.

---

## Future Requirements (deferred)

- **G6 — Online evaluation and drift monitoring** — the report stays an offline measurement.
- **G10 — Runtime model routing and automatic fallback** — `qwen2.5:1.5b` remains the measured default.
- **G4 — Authenticated approver identity** — recorded, not authenticated; a production requirement.
- **G8 — Multimodal intake** (voice, chart/cuff photo) — the real desk interface, absent by choice.
- **Four-state observation model** — stated / missing / not assessed / explicitly negative as first-class
  structured states. Text-level negation is handled today; a per-field provenance model is deferred.
- **MCP sampling** — deliberately out of scope: the server must not borrow the client's model.

## Out of Scope (explicit)

- **Free-form ReAct / LLM-authored plan DAG** — makes the safety kernel skippable and is unevaluable on a
  1.5B CPU model. The planner's action set is closed for this reason.
- **Multi-agent planner/executor/critic** — the `verify` node plus the admissibility guard cover the
  critic role structurally; a second autonomous agent adds risk without evidence.
- **Allergy history and acute allergic-reaction support** — explicitly outside v1.3.
- **Runtime self-learning / long-term memory** — unsafe at the point of care.
- **Autonomous queue movement** — forbidden by the challenge; `commit_priority` remains the only
  queue-mutating tool and stays gated.

## Traceability

| Requirement | Phase |
| --- | --- |
| DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05, DIAG-06 | Phase 19 |
| ADAPT-02, ADAPT-04, ADAPT-06, ADAPT-08 | Phase 20 |
| ELICIT-01, ELICIT-02, ELICIT-03, ELICIT-04, ELICIT-05, ELICIT-06, ELICIT-07, ELICIT-08 | Phase 21 |
| EMERG-01, EMERG-02, EMERG-03, EMERG-04, EMERG-05 | Phase 22 |
| ADAPT-01, ADAPT-03, ADAPT-05, ADAPT-07 | Phase 23 |
| MEAS-01, MEAS-02, MEAS-03, MEAS-04, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06 | Phase 24 |
