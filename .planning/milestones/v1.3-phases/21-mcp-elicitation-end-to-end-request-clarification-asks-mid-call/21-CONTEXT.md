# Phase 21 — MCP elicitation: CONTEXT

**Phase:** 21 · **Requirements:** ELICIT-01..08

## Goal

The owned server genuinely asks the human for the missing measurement **inside a tool call**, the shipped
adapter turns that into a LangGraph `interrupt()`, and all four outcomes are distinguished — with a refusal
never treated as an answer.

## Hard constraints

- DRY + SOLID. Do not edit `core/scorer.py`, `core/citations.py`, or the `@audited` interceptor.
- Questions are **derived**, never passed in: the tool takes candidate discriminator ids and calls the ONE
  owner `core.coverage.question_for` (already used by the classifier). A caller cannot supply question
  text — ELICIT-06 holds by construction.
- The tool is read-only: no store, no approval token, no queue row.
- The allowlist grows 8 → 9 in ONE atomic change (server, discovery, graph allowlist, eval fake, conftest,
  exact-set assertion).

## Contracts (extend `core/schema.py`)

```python
class ElicitationOutcome(StrEnum):
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"      # the client cannot elicit — NOT a decline

class ClarificationAnswer(BaseModel):
    outcome: ElicitationOutcome
    answers: list[str] = []
    reason: str | None = None
```

## Tool — `mcp/server.py`

```python
@server.tool()
@audited()
async def request_clarification(candidates: list[str], ctx: Context) -> ClarificationAnswer
```

- Derive at most `MAX_CLARIFICATION_QUESTIONS` (3) questions via `coverage.question_for(id_)`, skipping an
  unknown id.
- Build a **spec-valid** form schema dynamically (`pydantic.create_model`) with one `str` field per
  question (`q1..qN`, description = the question text). MCP elicitation admits primitive properties only.
- `await ctx.elicit(message, Form)` and map:
  - `AcceptedElicitation` → `accepted` + answers in field order;
  - `DeclinedElicitation` → `declined`;
  - `CancelledElicitation` → `cancelled`;
  - a missing client capability (`mcp` raises `McpError` with `MISSING_REQUIRED_CLIENT_CAPABILITY`, or the
    transport reports no elicitation support) → `unavailable`;
  - any other exception propagates (do not swallow a transport failure as a clinical answer).
- Never log or echo the raw form beyond the answers list.

## Interrupt discrimination (ELICIT-05)

- `approval_gate`'s payload gains `"type": "approval"` (additive; existing readers keep working).
- An elicitation interrupt already carries `"type": "mcp_elicitation"` (from `langchain.mcp`).
- `durable.invoke_graph` gains an optional `respond: Callable[[Mapping], Mapping]` policy and **loops**
  while `__interrupt__` is present: each payload is passed to `respond`, whose return value resumes the
  graph. Default policy = the existing approval decision, so every current caller is unchanged.
- `durable.resume_paused` uses the same loop.
- CLI: `resume` gains repeatable `--answer`; when an elicitation arrives and no answer is supplied, respond
  with `{"responses": {key: {"action": "decline"}}}`. An approval still needs `--decision`.
- Desk: when the paused payload is an elicitation, render a **question panel** (the questions, one free-text
  field each, a "decline" button) instead of the approval gate; POST resumes with the answers. The panel has
  no approve/edit/dismiss control and cannot commit.

## Tests

1. **Server unit**: with a fake `Context` whose `elicit` returns each of the four outcomes, the tool maps
   correctly; questions come from `coverage.question_for`; an unknown candidate is skipped; >3 candidates
   are trimmed.
2. **Adapter round-trip (ELICIT-02)**: build a two-node LangGraph graph whose node calls the
   `request_clarification` tool through the real `MCPAdapter`-loaded tool; assert the run pauses with an
   `mcp_elicitation` interrupt, resume with an accepted response, assert the tool returned the answer.
   If the adapter cannot be driven headlessly, prove the same path with `fastmcp.Client` + the
   `langchain.mcp.elicitation` driver and say so in the summary — do not weaken the assertion silently.
3. **Refusal is not an answer**: declined / cancelled / unavailable each return `answers == []`, and no
   colour or priority channel is written.
4. **Allowlist**: 9 names, exact-set assertion still fails closed.
5. **Desk/CLI**: an elicitation payload renders the question surface, not the gate; no commit path.

## Definition of done

`uv run pytest -q` green; `ruff` clean; `mypy` no new errors; atomic commits; `docs/MCP.md` and the
packaged skill document the round-trip and the four outcomes.
