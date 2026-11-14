# Phase 20 — Planner substrate: CONTEXT

**Phase:** 20 · **Milestone:** v1.3 Adaptive Triage · **Requirements:** ADAPT-02, ADAPT-04, ADAPT-06, ADAPT-08

## Goal

A planner decision is a typed contract over a closed action set, proposed by the local model and validated
by a deterministic guard that can only narrow what happens next — with the bounded-step policy implemented
and tested **before any graph edge moves**.

## Hard constraints (iron-clad)

- **DRY + SOLID** (`docs/CONVENTIONS.md`). SATS values live only in `data/*.yaml`.
- Do **not** edit `core/scorer.py`, `core/citations.py`, or the `@audited` interceptor.
- No graph wiring in this phase: `graph/build.py` topology is untouched. The only graph-adjacent change is
  the owned-tool allowlist growing 7 → 8 (one atomic fan-out across server, discovery, graph allowlist,
  test fake and the exact-set assertion).
- New modules import no network client and no model provider except through the ONE `llm` wrapper.

## Design (approved 2026-11-13)

### Contracts — extend `core/schema.py` (the one schema module)

```python
class PlanAction(StrEnum):
    GATHER_EVIDENCE = "gather_evidence"
    ASK_QUESTION = "ask_question"
    RE_EXTRACT = "re_extract"
    FINISH_INVESTIGATION = "finish_investigation"   # the ONLY exit to the kernel

class InvestigationState(BaseModel):   # the tool's narrow input (ISP)
    complaint: str
    retrieval_status: str              # matched | ambiguous | no_candidate
    candidates: list[str] = []
    questions: list[str] = []
    missing_vitals: list[str] = []
    has_evidence: bool = False
    step: int = 0
    budget_left: int = 3
    clarification_round: int = 0
    history: list[PlanAction] = []

class PlanProposal(BaseModel):         # what the MODEL returns
    action: PlanAction
    rationale: str = ""
    focus: str | None = None
    signals: list[str] = []

class PlanDecision(BaseModel):         # what the TOOL returns (validated)
    action: PlanAction
    rationale: str = ""
    signals: list[str] = []
    step: int
    budget_left: int
    proposed_action: PlanAction | None = None   # audit: what the model said
    overridden: bool = False
    override_reason: str | None = None
```

### `core/planner.py` — pure, the whole policy

- `MAX_INVESTIGATION_STEPS: int = 3` — declared ONCE, with a docstring deriving it from cost/latency, not
  tuned to a test.
- `admissible_actions(state) -> frozenset[PlanAction]`:
  - `finish_investigation` always admissible;
  - `gather_evidence` when `not has_evidence` and not already in history;
  - `ask_question` when `retrieval_status == "ambiguous"`, `candidates` non-empty, `clarification_round < 1`,
    and not already in history;
  - `re_extract` when `missing_vitals` non-empty and not already in history;
  - nothing else admissible when `budget_left <= 0`.
- `default_plan(state) -> PlanDecision` — always `finish_investigation` (this is exactly today's behaviour,
  and it is the baseline arm for the Phase 24 measurement).
- `validate_proposal(proposal, state) -> PlanDecision` — an inadmissible / `None` / malformed proposal
  becomes `finish_investigation` with `overridden=True` and a reason naming why.
- Purity is enforced by the existing `tests/test_purity.py` style guard (no `llm`, `mcp`, `store` imports).

### `llm/client.py` — the ONE model-access wrapper

Add `propose_plan_async(state) -> PlanProposal | None` using structured output
(`format=PlanProposal.model_json_schema()`), mirroring the existing extraction call. A transport/schema
failure returns `None` (the guard then defaults). Do not duplicate the Ollama client construction.

### `mcp/server.py` — the eighth owned tool

```python
@server.tool()
@audited()
async def plan_next_step(investigation: InvestigationState) -> PlanDecision
```

Thin adapter: `core.planner.admissible_actions` fast path → if the only admissible action is
`finish_investigation`, **do not call the model** (routine case costs what it costs today); otherwise
propose via the llm wrapper and return `validate_proposal(...)`. Read-only: no store, no approval token.
The tool's contract cannot return an inadmissible action.

Allowlist fan-out (8 names now): `graph/build.py:OWNED_TOOL_ALLOWLIST`, the discovery assertion, the test
fake tool map, and any exact-set test. One atomic commit.

## Tests that must exist

1. Closed set: `PlanAction` has exactly four members and none is `score`/`approval_gate`/`commit`.
2. Guard degradation: inadmissible, `None`, malformed, unparseable and exhausted-budget proposals all
   return `finish_investigation` with `overridden=True` (except the fast path, where `overridden=False`).
3. `admissible_actions` boundary cases: ambiguous+round 0 offers `ask_question`; round 1 does not;
   no_candidate offers no ask; missing vitals offer `re_extract`; history suppresses repeats; budget 0
   offers only `finish_investigation`.
4. Fast path: when only `finish_investigation` is admissible the model wrapper is never called
   (assert with a spy).
5. Purity: `core/planner.py` imports nothing from `llm`, `mcp`, `store`.

## Definition of done

`uv run pytest -q` green (647 + new tests); `uv run ruff check src tests` clean; `uv run mypy src` no new
errors; one atomic commit per plan.
