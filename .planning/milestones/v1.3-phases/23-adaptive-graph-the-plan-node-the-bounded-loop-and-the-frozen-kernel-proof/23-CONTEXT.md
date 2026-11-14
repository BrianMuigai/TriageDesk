# Phase 23 — Adaptive graph: CONTEXT

**Phase:** 23 · **Requirements:** ADAPT-01, ADAPT-03, ADAPT-05, ADAPT-07

## Goal

The graph investigates adaptively before it scores — `plan → action → plan … → finish_investigation`
inside a hard budget — and a structural test proves no investigation node can reach `score`, the gate or
the commit, with every decision audited and re-extraction monotone.

## Topology (exact)

```
START → ingest → emergency_check ─┬─(fast)──────────────→ retrieve
                                 └─(normal)→ normalize → retrieve
retrieve ─┬─(emergency_verdict.fired)──────────────→ finish_investigation
          └─(otherwise)────────────────────────────→ plan
plan ─┬→ gather_evidence → plan
      ├→ ask_question   → retrieve
      ├→ re_extract     → retrieve
      └→ finish_investigation → score
score → ground → verify → recheck → assess → approval_gate → commit → handover → END
```

**Critical property:** `predecessors("score") == {"finish_investigation"}`. The emergency arm also enters
the kernel **through** `finish_investigation` (it just skips `plan`), so the structural claim stays exact.

## State (extend `graph/state.py`)

- `plan: PlanDecision | None` — the current decision.
- `investigation: InvestigationFacts` — typed accumulator (`steps`, `history: list[PlanAction]`,
  `answers: list[str]`, `guard_overrides: int`), declared in `core/schema.py`.
- `nurse_answers: list[str]` — appended observations only (never an approval).

## Nodes (new `graph/planning.py`, re-exported through `make_nodes`)

- **`plan`**: builds `InvestigationState` from typed state (complaint, retrieval status, candidates,
  questions, missing vitals, has-evidence, step, budget, clarification round, history), calls the
  `plan_next_step` tool, stores `plan` + the updated `investigation`. On the fast path the tool does not
  call the model (already proven in Phase 20).
- **`gather_evidence`**: calls `retrieve_evidence`, writes `evidence` only, records the action, → `plan`.
- **`ask_question`**: calls `request_clarification(candidates=state["candidates"])`. On `accepted`,
  appends the answers to `nurse_answers` and the note-derived text used for re-matching, and increments
  `clarification_round`. On `declined`/`cancelled`/`unavailable`, records the refusal and appends nothing.
  → `retrieve` in both cases.
- **`re_extract`**: calls `normalize_case` with a hint and merges **monotonically** (ADAPT-07) — a field is
  filled only when it is `None`; a recorded vital, the original note and a nurse answer are never
  overwritten. → `retrieve`.
- **`finish_investigation`**: a pure no-op that records the final decision; → `score`.

## `core/merge.py` (new, pure)

`merge_monotone(current: CaseInput, extracted: CaseInput) -> CaseInput` — fills only `None` fields; every
stated value wins. No model, no store. Unit-tested field by field, including "extracted contradicts a
recorded vital → recorded wins".

## Decision audit + spans (ADAPT-05)

- The `plan_next_step` tool call is already audited (one record per call) and carries the `PlanDecision` as
  its output — that is the durable "why next?" record.
- The `plan` node additionally emits a decision span/fact that names the action, the step and whether the
  guard overrode the proposal. Do **not** edit the `@audited` interceptor; use the existing
  `observability.span` helper inside the node if needed.
- A test must prove the decision (action, rationale, step, overridden) is recoverable from the audit
  record and/or the span stream for one adaptive run.

## Structural proof (ADAPT-03)

1. `predecessors("score") == {"finish_investigation"}` on the compiled graph.
2. `predecessors("commit") == {"approval_gate"}` (unchanged).
3. No investigation node's partial update contains `priority`, `commit_result` or `handover` — assert the
   returned keys directly with fake tools.
4. `PlanAction` still has no `score`/`approval_gate`/`commit` member.
5. Budget: a run never exceeds `MAX_INVESTIGATION_STEPS` plan decisions; a repeated `(action, focus)` is
   never selected; budget exhaustion reaches `finish_investigation`.

## Tests

- Adaptive happy path with fake tools: ambiguous case → `ask_question` → answer → re-retrieve → matched →
  `finish_investigation` → kernel → gate.
- Guard override path: the fake `plan_next_step` returns an inadmissible action → graph still runs
  `finish_investigation`.
- `gather_evidence` path writes `evidence` and returns to `plan`.
- `re_extract` path fills a missing vital and never overwrites a stated one.
- Structural proof suite above.
- Emergency arm reaches `finish_investigation` without calling `plan_next_step`.
- The existing eval suite must stay green (24 cases); no colour changes.

## Definition of done

`uv run pytest -q` green; `ruff` clean; `mypy` no new errors; atomic commits; `ARCHITECTURE.md` §3 already
describes this shape; `STATUS.md` moves dynamic planning to ✅ only with test evidence.
