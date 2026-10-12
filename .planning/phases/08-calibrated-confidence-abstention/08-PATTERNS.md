# Phase 8: Calibrated Confidence & Abstention - Pattern Map

**Mapped:** 2026-10-12
**Files analyzed:** 20 (new + modified)
**Analogs found:** 18 / 20 (2 are pure regenerated artefacts with a generator as their analog)

> **Greenfield confirmation.** `grep -rn "confidence|deferral|assess_confidence|ConfidenceResult" src tests`
> returns **nothing** — every symbol this phase adds is new. The seams are additive.
>
> **Iron-clad rule (AGENTS.md / `docs/CONVENTIONS.md`):** DRY + SOLID. One schema module; one place a
> colour is produced; one audit interceptor; extend by a **new node + a new tool**, never by editing a
> working one. All excerpts below are from git-tracked source (`git ls-files` verified).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/triagedesk/core/confidence.py` (NEW) | core / pure domain fn | transform | `src/triagedesk/core/scorer.py` | exact |
| `src/triagedesk/core/schema.py` (MODIFY) | model (schema) | transform | existing models in the SAME file (`RecheckFlag`, `MatchResult`) | exact |
| `src/triagedesk/graph/state.py` (MODIFY) | state / config | event-driven (channel) | existing channels in the SAME file (`second_look`, `priority`) | exact |
| `src/triagedesk/graph/nodes.py` (MODIFY) | graph node | request-response | `_make_score` / `_make_recheck` (SAME file) | exact |
| `src/triagedesk/graph/build.py` (MODIFY) | composition / config | event-driven (routing) | `route_after_score` + the SAME file's conditional-edge wiring | exact |
| `src/triagedesk/mcp/server.py` (MODIFY) | MCP tool | request-response | `score_priority` / `match_discriminators` (SAME file) | exact |
| `src/triagedesk/evals/tools.py` (MODIFY) | tool adapter (eval) | request-response | `score_priority` closure (SAME file) | exact |
| `tests/conftest.py` (MODIFY) | test fixture | request-response | `score_priority` fake (SAME file) | exact |
| `tests/test_safety_spine.py` (MODIFY) | test (contract) | transform (AST/set) | `test_graph_startup_asserts_the_tool_allowlist` (SAME file) | exact |
| `src/triagedesk/evals/report.py` (MODIFY) | model + digest | transform | `ReportCase` / `Analysis` / `_digest_payload` (SAME file) | exact |
| `src/triagedesk/evals/analysis.py` (MODIFY) | service (analyser) | batch / transform | `analyse` accumulation loop (SAME file) | exact |
| `src/triagedesk/evals/runner.py` (MODIFY, implied) | service (runner) | batch | `_capture` (SAME file) | exact |
| `scripts/emit_evals.py` (MODIFY) | generator / projection | transform | `_measured_metrics` (SAME file) | exact |
| `evals/results/report.json` (REGENERATE) | data artefact | batch | its own generator pipeline (`uv run triagedesk eval`) | n/a — regenerate |
| `EVALS.md` (REGENERATE §3 cell) | doc (projection) | transform | `scripts/emit_evals.py --write` (SAME generator) | n/a — regenerate |
| `docs/DECISIONS.md` (MODIFY) | doc (ADR) | — | `D16` / `D19` entries (SAME file) | exact |
| `tests/test_confidence.py` (NEW) | test (unit + shape) | transform | `tests/test_purity.py` + `tests/test_safety_spine.py` | exact |
| `tests/test_graph_confidence.py` (NEW) | test (integration) | request-response | `tests/test_graph_recovery.py` | exact |
| `tests/test_eval_report.py` (MODIFY) | test (projection) | transform | `test_generator_is_idempotent_and_the_report_is_the_sole_source` (SAME file) | exact |
| `tests/test_eval_suite.py` (MODIFY) | test (E-09 outcome) | batch | `test_terminal_outcomes_are_first_class_and_write_no_queue_row` (SAME file) | exact |

---

## Pattern Assignments

### `src/triagedesk/core/confidence.py` (core / pure fn, transform) — NEW

**Analog:** `src/triagedesk/core/scorer.py`

This is the single most important analog: copy its **purity posture and its data-driven band reads**, not
its arithmetic. `tests/test_purity.py` is parametrized over `CORE_DIR.rglob("*.py")`, so the new module is
**automatically** covered by the purity guard — it must import no `llm`/`mcp`/`store`/`fastmcp`/`langchain`
(`tests/test_purity.py:89-97`).

**Module docstring + import discipline** (`core/scorer.py:1-29`):
```python
"""Pure deterministic TEWS scorer (D-01, D-02, D-03, D-04).

No number ever comes from the model (D-02): this module imports nothing from
``llm`` / ``mcp`` / ``store`` (enforced by ``tests/test_purity.py``). Every band,
threshold, colour and target time is read from ``data/sats_tews.yaml`` through the
one loader (``core/rules.py``) — no SATS value is inlined here (CONVENTIONS §1).
"""
from __future__ import annotations

from triagedesk.core.rules import (
    Band, DiscriminatorCategory, Parameter, TewsRules,
    get_discriminators, get_tews,
)
from triagedesk.core.schema import CaseInput, PriorityResult, TriggeredRule
```
Mirror exactly: import `get_tews` / `get_discriminators` from `core.rules` (the ONE loader) and the typed
contracts from `core.schema`. No `math` needed unless you compute a distance (scorer imports it at line 18).

**Data-driven band read — DO NOT inline a band edge** (`core/scorer.py:127-133`); the "distance from the
band edge" component must reuse this shape, reading `rules.tews_to_colour` (a `list[ColourBand]` with
`min: int`, `max: int | None` — `core/rules.py:44-49`):
```python
def _colour_for(rules: TewsRules, total: int) -> str:
    """Map a TEWS *total* to its colour token (data-driven, inclusive bands)."""
    for band in rules.tews_to_colour:
        high = band.max if band.max is not None else math.inf
        if band.min <= total <= high:
            return band.colour
    raise ValueError(f"no colour band covers TEWS total {total}")
```
The confidence component must find the band containing `priority.tews` and compute a distance — but it
**must not map `tews`→colour** (Pitfall 2). Use the same inclusive `min ≤ tews ≤ max` scan, then
`min(tews - band.min, band.max - tews)` with a missing `max` treated as open.

**Purity/derivation note — the data authorities the four components read** (all verified):
- (a) vitals coverage: `priority.used_vitals` / `priority.missing_vitals`, denominator
  `len(get_tews().parameters)` (scorer partitions in `score_priority`, `core/scorer.py:221-226`).
- (b) discriminator coverage: `matched_ids` / `no_match`, denominator
  `len(get_discriminators().discriminators)`; `no_match is True` forces a deferral (D8-11).
- (c) override-vs-TEWS: `any(rule.rule_id in get_discriminators().categories for rule in priority.triggered_rules)`.
  The override `TriggeredRule.rule_id` is the category name (`core/scorer.py:243-255`), disjoint from
  TEWS parameter keys and `"tews_baseline"` — so this is DRY-safe and re-derives no colour.
- (d) TEWS band distance: `priority.tews` vs `get_tews().tews_to_colour` bounds.

**Public function signature** (mirror `score_priority`'s typed-in/typed-out shape, `core/scorer.py:194-197`):
```python
def assess(
    case: CaseInput,
    matched_ids: list[str],
    no_match: bool,
    priority: PriorityResult,
) -> ConfidenceResult: ...
```

**DRY guard warning:** `tests/test_no_duplicated_sats.py` scans every `src/**.py` literal against the data
leaves. Band edges `0-6` are single-digit and slip the *numeric* scan, but the **string** leaves (colours
`GREEN`/`YELLOW`/`ORANGE`/`RED`, `tews_baseline`) are caught **exactly**. Never name a colour or
`"tews_baseline"` in `core/confidence.py` — read them through the loader.

---

### `src/triagedesk/core/schema.py` (model, transform) — MODIFY

**Analog:** the models already in this file.

Add **one** new contract, `ConfidenceResult`, beside the existing results. Copy this docstring-and-fields
convention (note how `RecheckFlag` and `Escalation` document "there is deliberately no colour field" — the
*absence* of a field is the guard, `core/schema.py:133-172`):

```python
class RecheckFlag(BaseModel):
    """Second-look flag from serial vitals — never a colour, never a reorder (D-08).

    ``flag`` is ``True`` when at least one scored vital moved to a higher-points
    TEWS band; ... There is deliberately no colour field: this result never
    re-classifies and never touches the queue (TOOL-04, T-02-10).
    """

    flag: bool = False
    deteriorations: list[str] = Field(default_factory=list)
    changes: list[VitalChange] = Field(default_factory=list)
    reason: str | None = None
```

Contract rules (D8-02/D8-04 — make a percentage **unrepresentable**, not merely discouraged):
- `deferral: bool`
- a small **closed-set** level: `Literal[...]` (e.g. `"high" | "moderate" | "low"`) — no float field exists.
- a per-component breakdown of **counts/booleans** (a small sub-model, e.g. `ConfidenceComponent` with
  `satisfied: bool`, `detail: str`) — or plain bool fields.
- `reason: str`
- **NO** `float`, `score`, `probability`, `percent` field. (A `tests/test_confidence.py` shape test rejects one.)

Use plain `str` fields for the level only with a declared `Literal`; the file already uses
`Literal` via `Mobility`/`AVPU` (`core/schema.py:20-21`). If you add a second small model, declare it in
**this file** so `graph/build.py::_allowed_msgpack_modules` auto-covers it (see Shared Patterns).

**Do NOT add a confidence field to `HandoverCard`** (`core/schema.py:243-287`) — that breaks the exact
card field-set assertion (`tests/test_safety_spine.py:44-59`) and is Phase 10's job (Assumption A3).

---

### `src/triagedesk/graph/state.py` (state/config, channel) — MODIFY

**Analog:** the SAME file. Add one channel to `TriageState` and its import.

**Import block** (`graph/state.py:14-22`):
```python
from triagedesk.core.schema import (
    CaseInput, CommitResult, Escalation, HandoverCard,
    PriorityResult, RecheckFlag, RecoveryRequest,
)
```
Add `ConfidenceResult` to this import.

**Channel declaration** (`graph/state.py:40-52`) — copy the `second_look:` shape exactly:
```python
    priority: PriorityResult | None
    ...
    # Serial-vitals second look (GATE-04, D-07): the previous case and the flag it raises.
    previous_case: CaseInput | None
    second_look: RecheckFlag | None
```
Add `confidence: ConfidenceResult | None`. `total=False` means it is optional (no default needed). Update
the class docstring's node→channel map to name `assess` (the docstring already enumerates which node adds
which channel, `graph/state.py:29-34`).

---

### `src/triagedesk/graph/nodes.py` (node, request-response) — MODIFY

**Analog:** `_make_score` (`graph/nodes.py:180-192`) and `_make_recheck` (`graph/nodes.py:240-264`).

The node is a thin `_make_*` factory returning an `async def` that calls one tool via `parse_tool_result`
(the ONE parser, `graph/nodes.py:63-80`) and returns a partial state update.

**`_make_score` — the exact shape to copy** (`graph/nodes.py:180-192`):
```python
def _make_score(tools: ToolMap) -> NodeFn:
    """Build the ``score`` node over the injected tool mapping (D-02)."""

    async def score(state: TriageState) -> dict[str, Any]:
        """Score the typed case deterministically — no model on this path (D-02)."""
        payload = {
            "case": state["case"].model_dump(),
            "matched_discriminator_ids": list(state.get("matched_ids") or []),
        }
        priority = parse_tool_result(PriorityResult, await tools["score_priority"](payload))
        return {"priority": priority}

    return score
```
Mirror it as `_make_assess(tools)` → `async def assess(state)` calling `tools["assess_confidence"]` with a
payload of `{case, matched_ids, no_match, priority}` (typed dump), then
`parse_tool_result(ConfidenceResult, ...)` and `return {"confidence": signal}`. Keep it **side-effect free**
(read the priority, write the new channel only — never assign to `priority`).

**Register in the factory** (`graph/nodes.py:376-388`) — add one entry; import `ConfidenceResult` into the
`core.schema` block at `graph/nodes.py:29-39`:
```python
    return {
        "ingest": ingest,
        "normalize": _make_normalize(tools),
        "retrieve": _make_retrieve(tools),
        "score": _make_score(tools),
        "verify": verify,
        ...
        "escalate": escalate,
    }
```

---

### `src/triagedesk/graph/build.py` (composition, routing) — MODIFY

**Analog:** the SAME file — `route_after_score` (`:127-140`) and the conditional-edge wiring (`:204-232`).

This is the **whole-suite hazard** file. Four edits, all in the same wave.

**(1) Allowlist +1** (`graph/build.py:65-71`):
```python
OWNED_TOOL_ALLOWLIST: tuple[str, ...] = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "raise_recheck_flag",
    "commit_priority",
)
```
Add `"assess_confidence",`. `assert_tool_allowlist` is **set-equality** (`:74-89`): `missing`/`unexpected`
both raise `RuntimeError`. The two tool factories (sites below) must add the callable in the same commit.

**(2) `TRACER_NODES` +1** (`graph/build.py:95-107`): add `"assess"` (the tracer proof checks a
**superset**, so this is safe — `tests/test_graph_tracer.py`).

**(3) Re-point `score`'s neutral target + add the new router.** Change the mapping at `:212-220` so
`"verify": "verify"` becomes `"verify": "assess"`, and add a `route_after_assess` modelled on
`route_after_score` (`:127-140`):
```python
def route_after_score(state: TriageState) -> str:
    """Choose the next node after ``score`` — safe terminals vs ``verify`` (ORCH-05)."""
    priority = state.get("priority")
    if priority is not None and priority.out_of_scope:
        return "escalate"
    if priority is not None and priority.missing_vitals:
        return "request_missing_info"
    return "verify"
```
New router reads the `confidence` channel; a deferral routes to a terminal, else `verify`:
```python
def route_after_assess(state: TriageState) -> str:
    signal = state.get("confidence")
    if signal is not None and signal.deferral:
        return "request_missing_info" if <missing-info reason> else "escalate"
    return "verify"
```
(Research recommends: missing-vitals-driven deferral → `request_missing_info`; all other deferrals
(no_match, band-edge, override-ambiguity) → `escalate`, so terminal semantics stay single-purpose.)

**(4) Register the node + its conditional edges** (`graph/build.py:221-231`). Neither terminal has an edge
to `commit` (`:230-231`), so "never commit" is **structural**:
```python
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {"recheck": "recheck", "score": "score", END: END},
    )
    graph.add_edge("recheck", "approval_gate")
    ...
    graph.add_edge("request_missing_info", END)
    graph.add_edge("escalate", END)
```
Add, alongside the above:
```python
    graph.add_conditional_edges(
        "assess",
        route_after_assess,
        {"escalate": "escalate", "request_missing_info": "request_missing_info", "verify": "verify"},
    )
```
The node itself is added by the existing loop `for name in TRACER_NODES: graph.add_node(name, _spanned(...))`
(`:201-202`) once `nodes["assess"]` exists — no extra wiring.

**Also** add `"route_after_assess"` to `__all__` (`:45-59`). `_allowed_msgpack_modules` (`:303-316`)
derives BaseModel classes from `core.schema.py` by `__module__`, so a new `ConfidenceResult` declared in
`core.schema` is auto-included — **provided it lives in that module**.

---

### `src/triagedesk/mcp/server.py` (MCP tool, request-response) — MODIFY

**Analog:** `score_priority` (`mcp/server.py:190-203`) and `match_discriminators` (`:206-216`).

Every tool is `@server.tool()` + `@audited()` over a thin adapter to the pure `core` function. Add a 6th in
the identical shape; import `assess_confidence`'s core fn and `ConfidenceResult` from `core.schema`
(add to the block at `mcp/server.py:31-39`, and add `confidence` to the `from triagedesk.core import ...`
line at `:30`):

```python
@server.tool()
@audited()
def score_priority(
    case: CaseInput,
    matched_discriminator_ids: list[str] | None = None,
) -> PriorityResult:
    """Score a typed case deterministically — no model on this path (D-02).

    A thin, contract-typed adapter over the pure ``core.scorer.score_priority``
    function (SOLID: S/D): it touches no model and cannot inject a colour. ...
    """
    return scorer.score_priority(case, matched_discriminator_ids)
```
New tool (D8-06/07): take the typed inputs (`CaseInput`, `list[str]`, `bool`, `PriorityResult`), return
`ConfidenceResult`, **no** store/queue/token, `@audited()` only (not `@audited(approval=True)`):
```python
@server.tool()
@audited()
def assess_confidence(
    case: CaseInput,
    matched_ids: list[str],
    no_match: bool,
    priority: PriorityResult,
) -> ConfidenceResult:
    """Return the deterministic coverage/deferral signal — no model, no store (D8-07)."""
    return confidence.assess(case, matched_ids, no_match, priority)
```
Update the module docstring's "the five triage tools" (`:1`) and the `tests/test_mcp_server.py` superset
comment — no behaviour change there (its check is `>=`).

---

### `src/triagedesk/evals/tools.py` (eval tool adapter, request-response) — MODIFY

**Analog:** the `score_priority` closure (`evals/tools.py:107-111`) inside `build_tools`.

**CRITICAL — set-equality break.** `build_graph` asserts `assert_tool_allowlist`, and this factory returns
exactly five names. Add a 6th closure and key **in the same commit** as the allowlist, or every
graph/eval/demo/durable test raises at composition.

Copy the closure shape (`evals/tools.py:107-111`) and the returned dict (`:124-130`):
```python
    async def score_priority(inp: Mapping[str, Any]) -> Any:
        parsed = CaseInput.model_validate(inp["case"])
        return await server_module.score_priority(
            parsed, inp.get("matched_discriminator_ids")
        )
    ...
    return {
        "normalize_case": normalize,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "commit_priority": commit_priority,
    }
```
Add:
```python
    async def assess_confidence(inp: Mapping[str, Any]) -> Any:
        case = CaseInput.model_validate(inp["case"])
        return await server_module.assess_confidence(
            case, list(inp.get("matched_ids") or []), bool(inp.get("no_match")),
            PriorityResult.model_validate(inp["priority"]),
        )
```
and the `"assess_confidence": assess_confidence` key. Import `PriorityResult` at the `core.schema` line
(`:21`). This factory also feeds `durable.resume_thread` (`durable.py:239`) and `demo/run.py` (`:177,:224`),
so all three consumers inherit the fix.

---

### `tests/conftest.py` (test fixture, request-response) — MODIFY

**Analog:** the `score_priority` fake (`tests/conftest.py:163-166`) inside `build_graph_tools`.

**CRITICAL — the second set-equality break.** Same wave as the allowlist. Copy the fake shape (`:163-166`)
and the returned dict (`:200-206`):
```python
    async def score_priority(inp: dict[str, Any]) -> Any:
        calls.append(("score_priority", inp))
        parsed = CaseInput.model_validate(inp["case"])
        return scorer.score_priority(parsed, inp.get("matched_discriminator_ids"))
    ...
    return {
        "normalize_case": normalize_case,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "commit_priority": commit_priority,
    }
```
Add an `assess_confidence` fake that calls the **real** `confidence.assess` (so the proof runs the shipped
logic, mirroring how the `score_priority` fake calls the real `scorer`) and records its call:
```python
    async def assess_confidence(inp: dict[str, Any]) -> Any:
        calls.append(("assess_confidence", inp))
        return confidence.assess(
            CaseInput.model_validate(inp["case"]),
            list(inp.get("matched_ids") or []),
            bool(inp.get("no_match")),
            PriorityResult.model_validate(inp["priority"]),
        )
```
Add `from triagedesk.core import confidence, matcher, recheck, scorer` (extend the `:20` import) and
`PriorityResult` to the `core.schema` import (`:21-26`). Add the `"assess_confidence"` key.

---

### `tests/test_safety_spine.py` (contract test, transform) — MODIFY

**Analog:** `test_graph_startup_asserts_the_tool_allowlist` (`tests/test_safety_spine.py:187-214`).

The exact-set assertion must go from five to six names (`:190-196`):
```python
def test_graph_startup_asserts_the_tool_allowlist() -> None:
    """The graph composes only over the allowlisted tool set, failing loudly on drift (SAFE-03)."""
    # The allowlist is the owned five, declared as ONE constant.
    assert set(build_module.OWNED_TOOL_ALLOWLIST) == {
        "normalize_case",
        "match_discriminators",
        "score_priority",
        "raise_recheck_flag",
        "commit_priority",
    }
    # The allowlisted surface composes cleanly.
    build_graph(build_graph_tools())
```
Add `"assess_confidence"` to the set and update the "owned five" comment to "six". The missing/unexpected
sub-assertions (`:200-214`) keep working unchanged.

---

### `src/triagedesk/evals/report.py` (model + digest, transform) — MODIFY

**Analogs:** `ReportCase` (`:48-85`), `Analysis` (`:114-157`), `_digest_payload` (`:227-260`) — all SAME file.

**Per-case deferral facts (additive, defaulted).** Copy `ReportCase`'s defaulted-list convention
(`:65-85`); the models are built by keyword in tests (`tests/test_eval_report.py:103-118`), so a defaulted
field is additive and breaks nothing:
```python
    case_id: str
    expected: str
    runs: int
    colours: list[str | None] = Field(default_factory=list)
    outcomes: list[str | None] = Field(default_factory=list)
    ...
    latency_s: list[float] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    declared_failure: bool = False
```
Add e.g. `confidence_levels: list[str] = Field(default_factory=list)` and
`deferrals: list[bool] = Field(default_factory=list)`.

**Aggregate deferral + calibration.** Add a `deferral_rate` / `deferral_count` / `deferral_cases` tuple and
a `calibration` sub-block to `Analysis`, following the existing under/over asymmetry block (`:134-157`).
Keep ECE/bin scalar figures **inside `Analysis` only** (never in `core/schema.py`, never in the tool
output) — that separation is what keeps D8-04 intact (Assumption A2).

**Digest — deliberate choice.** `_digest_payload` enumerates an explicit key list (`:235-260`); a new
`ReportCase`/`Report` field is **not** sealed automatically. Per research: add the per-case **deferral**
fields to `_digest_payload` (the decision is deterministic, so sealing strengthens tamper-detection), but
keep the **calibration aggregates in `Analysis`**, which is deliberately excluded from the digest
(`Report` docstring, `:160-179`):
```python
        "cases": [
            {
                "case_id": case.case_id,
                "expected": case.expected,
                ...
                "invariants_pass": case.invariants_pass,
                "declared_failure": case.declared_failure,
            }
            for case in report.cases
        ],
```
`compute_report_digest` (`:263-265`) is the ONE sealing path — no second digest.

---

### `src/triagedesk/evals/analysis.py` (analyser, batch) — MODIFY

**Analog:** the `analyse` accumulation loop (`analysis.py:60-188`).

The analyser is **pure over the report** and never re-runs the graph (`:60-76`). It reads the per-case
facts and derives the urgency ordering from the substrate (`colour_urgency`, `:33-43`). Add a deferral
aggregation alongside the under/over counts (`:83-161`) and return it in the `Analysis(...)` construction
(`:163-188`):
```python
    return Analysis(
        colour_runs=colour_runs,
        colour_correct=colour_correct,
        ...
        red_miss_cases=red_miss_cases,
    )
```
**E-09 behavioural note:** under D8-11 the deferred no-match case leaves `under_triage` — the branch at
`:123-133` **excludes a terminal outcome on a colour-expected case** from the direction split and does not
count it as a terminal miss. This is an intended, published change: regenerate, do not tune the fixture.

---

### `src/triagedesk/evals/runner.py` (runner, batch) — MODIFY (implied)

**Analog:** `_capture` (`runner.py:60-105`).

To populate the new per-case fields, `_capture` must read the graph's **own** `confidence` channel — never
re-derive the signal (the same principle by which it reads `recovery`/`escalation`/`second_look`):
```python
    return {
        "colour": colour,
        "citations": citations,
        "triggered_rules": triggered,
        "matched_ids": matched,
        "recovery": recovery is not None,
        "escalation": escalation is not None,
        "second_look": (
            second_look.model_dump(mode="json") if second_look is not None else None
        ),
        "delivered": result.get("handover") is not None,
        "route": result.get("route"),
        "attempt": int(result.get("attempt") or 0),
    }
```
Add a `confidence` capture from `result.get("confidence")`, then thread it through `_run_case` (`:246-320`)
into the new `ReportCase` fields. (Whether this is runner-side or derived in `analysis` is the agent's
discretion, but the source of truth must be the graph's channel.)

---

### `scripts/emit_evals.py` (generator, transform) — MODIFY

**Analog:** `_measured_metrics` (`scripts/emit_evals.py:84-105`).

`EVALS.md` is a **projection** of `report.json` only — every number is generated here (`:1-22`). Add one
key to `_measured_metrics` for the new deferral-rate / calibration §3 row:
```python
    return {
        "Colour accuracy": f"{analysis.colour_correct}/{analysis.colour_runs} ({accuracy})",
        "Error direction": (
            f"under-triage {analysis.under_triage_count} · "
            f"over-triage {analysis.over_triage_count}"
        ),
        "Citation completeness": f"{citation_ok}/{total} cases",
        "Gate delivery": f"{total - len(analysis.aborted_cases)}/{total} cases",
        "Safety invariants": f"{invariants_ok}/{len(INVARIANT_IDS)}",
        ...
    }
```
The corresponding **row label + definition** in `EVALS.md` §3 is hand-written (allowed, structural); the
**measured cell** is generated (a number typed by hand is not). The generator is idempotent and refuses a
report whose digest does not recompute (`validate_report`, `:206-212`).

---

### `evals/results/report.json` + `EVALS.md` (regenerated artefacts) — REGENERATE

**Analog/generator:** `uv run triagedesk eval` → `scripts/emit_evals.py --write`.

Never hand-edit either. The regeneration pipeline:
1. `uv run triagedesk eval` (offline mode) re-runs the suite and rewrites `evals/results/report.json`.
2. `uv run python scripts/emit_evals.py --write` projects the report into `EVALS.md`.
3. `tests/test_docs_final.py::test_evals_is_a_projection_of_the_report` (`:98-105`) runs `emit_evals.py
   --check` and fails if `EVALS.md` ≠ the generator's output.

Because E-09's outcome changes (D8-11), `analysis.under_triage*` and the §3 direction split change — this
is expected and must be re-read honestly (E-09 stays `passed=False`, the sole declared failure).

---

### `docs/DECISIONS.md` (ADR doc) — MODIFY

**Analog:** `D16` (`:124-130`) / `D19` (`:149-174`) — context · decision · why · consequence, ADR-lite.

Add a numbered decision (D20) recording D8-09's asymmetric cost with **both costs named** (a missed
emergency ≫ a needless deferral) and the named constant derived from it. Keep it to the established
four-line shape:
```markdown
### D16 — Idempotent, approval-keyed queue writes
**Decision:** `commit_priority` is keyed by `case_id` (+ content hash) and requires an approval token.
**Why:** the queue write is the one irreversible action; retries must not place a patient twice.
**Consequence:** safe under retry/replay; complements the LangGraph `interrupt()` gate.
```
Do not restate SATS values or the threshold at multiple sites (DRY) — the named constant lives once in
`core/confidence.py`; `DECISIONS.md` records the *rationale*. `docs/CONVENTIONS.md` is linked, never copied.

---

### `tests/test_confidence.py` (unit + shape test) — NEW

**Analogs:** `tests/test_purity.py` (AST/contract-shape guards) + `tests/test_safety_spine.py`
(field-set equality & forbidden-token).

- **Pure-signal unit tests** for the four components + determinism + `no_match` forces deferral (mirror
  the parametrized/`ast` style of `tests/test_purity.py:89-97`).
- **"No percentage" shape guard** — assert `ConfidenceResult.model_fields` has **no `float` annotation**
  and the serialised output contains no `%`/`"probability"`/`"confidence"`-as-scalar token. Mirror the
  forbidden-token field-set check (`tests/test_safety_spine.py:123-133`):
  ```python
  def test_card_model_has_no_field_that_could_hold_assessment_prose() -> None:
      tokens = HandoverCard.FORBIDDEN_FIELD_TOKENS
      assert tokens, "the forbidden-token contract must be declared on the card"
      for field_name in HandoverCard.model_fields:
          lowered = field_name.lower()
          assert not any(token in lowered for token in tokens), field_name
      with pytest.raises(ValueError):
          HandoverCard(case_id="c-1", diagnosis="community-acquired pneumonia")
  ```
- **One-way downgrade guard** — assert `core/scorer.py`'s source contains no `confidence` import/symbol
  and `score_priority`'s signature has no confidence parameter. Use the AST helper
  `imported_modules` from `tests/conftest.py:50-63` (imported in tests as `from conftest import ...`,
  `tests/test_safety_spine.py:25`).
- **Purity** is already auto-covered for the new module by `tests/test_purity.py` (parametrized over
  `core/**.py`); add a focused assertion only if useful.

---

### `tests/test_graph_confidence.py` (integration test, request-response) — NEW

**Analog:** `tests/test_graph_recovery.py` (the whole file — `:40-179`).

Copy the invoke-and-assert-terminal pattern verbatim. Note the existing assertions you will re-use for the
"no commit on a deferral" proof:
```python
async def test_missing_vital_routes_to_the_recovery_terminal() -> None:
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=MISSING_VITAL_CASE, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())
    result = await app.ainvoke({"raw_note": NOTE}, _config("recovery"))
    recovery = result.get("recovery")
    assert isinstance(recovery, RecoveryRequest), "did not reach the recovery terminal"
    ...
    assert result.get("commit_result") is None
    assert not result.get("__interrupt__"), "a missing-vital case must not reach the gate"
    assert "commit_priority" not in [name for name, _ in calls]
```
Proofs to add (research §Proving the One-Way Safety Property):
1. A deferral on an otherwise-committing case (`COMPLETE_CASE`, `tests/conftest.py:120-130`) ends at
   `escalation`/`recovery`, interrupt never fired, store empty (`memory_store.rows == []`), no
   `commit_priority` call.
2. `no_match is True` ⇒ `confidence.deferral is True`; end-to-end on the E-09 complaint → terminal, no row.
3. `assess` never assigns `priority` (colour survives unchanged; AST/signature guard in `test_confidence.py`).
4. `assess_confidence` is pure — call it, assert one `assess_confidence` audit record, `memory_store.rows == []`.

`memory_store` fixture and `injected_store` autouse are in `tests/conftest.py:82-99`.

---

### `tests/test_eval_report.py` (projection test, transform) — MODIFY

**Analog:** `test_generator_is_idempotent_and_the_report_is_the_sole_source` (`:238-266`) and
`_report_case` (`:89-118`).

Add a test that the deferral rate / calibration figures are rendered from the report and that rendering is
still idempotent. Reuse `_report_case` (builds `ReportCase` by keyword — the additive fields need no change
here) and `_EMIT.render_evals`:
```python
    first = _EMIT.render_evals(_TEMPLATE, sealed)
    second = _EMIT.render_evals(first, sealed)
    assert first == second, "the generator is not idempotent"
```

---

### `tests/test_eval_suite.py` (E-09 outcome test, batch) — MODIFY

**Analog:** `test_terminal_outcomes_are_first_class_and_write_no_queue_row` (`:138-151`).

Extend to assert the E-09 deferral loudly (research §E-09 change):
```python
    assert _report_case(report, "E-05").outcomes == ["RECOVER"] * 3
    ...
    assert store.rows == [], "a recovery/abstention/recheck case wrote a queue row"
```
Add: E-09's measured outcome is a terminal (not a GREEN colour), `store.rows == []`, and E-09 remains
`passed=False` and the sole `declared_failure` (existing assertions at `:88-100` still hold).

---

## Shared Patterns

### The ONE schema module
**Source:** `src/triagedesk/core/schema.py` (docstring `:1-9`)
**Apply to:** the new `ConfidenceResult` (and any sub-model)
- Every typed contract lives here; MCP tool contracts, the Ollama `format=` schema and graph state import it.
- `graph/build.py::_allowed_msgpack_modules` (`:303-316`) derives the checkpointer allowlist from
  `core/schema.py` **by `__module__`** — a `ConfidenceResult` declared here is auto-covered; declared
  elsewhere it is not.

### The ONE audit interceptor
**Source:** `src/triagedesk/mcp/server.py::audited` (`:91-166`)
**Apply to:** `assess_confidence`
- `@audited()` appends exactly one chained record and opens one `tool` span. The new tool uses
  `@audited()` (not `@audited(approval=True)`): it is pure and takes no token.

### The ONE owned-tool allowlist — set-equality, THREE sites, ONE wave
**Source:** `src/triagedesk/graph/build.py::OWNED_TOOL_ALLOWLIST` (`:65-71`) + `assert_tool_allowlist` (`:74-89`)
**Apply to:** `mcp/server.py`, `evals/tools.py::build_tools`, `tests/conftest.py::build_graph_tools`,
`tests/test_safety_spine.py`
- `assert_tool_allowlist` is **set equality** (`missing`/`unexpected` both raise). Both tool factories must
  add the callable in the SAME commit or **every** graph/eval/demo/durable test raises `RuntimeError` at
  `build_graph` (`:198`). This is the whole-suite hazard (Research Pitfall 1).

### Purity guard — automatic for the new core module
**Source:** `tests/test_purity.py` (`:89-97`)
**Apply to:** `core/confidence.py`
- Parametrized over `CORE_DIR.rglob("*.py")`; forbids `llm`/`mcp`/`store` (siblings) and
  `fastmcp`/`langchain` (MCP-client roots). Read-only data via `core.rules` is the sanctioned path.

### DRY data guard — no inlined SATS value
**Source:** `tests/test_no_duplicated_sats.py` (`:147-162`)
**Apply to:** `core/confidence.py`, `graph/nodes.py`, `graph/build.py`
- Scans every `src/**.py` literal against `data/*.yaml` leaves. String leaves (colours, `tews_baseline`)
  are caught **exactly**; discriminating numbers (`≥10` or non-integer) are caught. Read bands through
  `get_tews()`; derive the threshold as a named constant (D8-09), never a bare literal sprinkled at call sites.

### Node superset check — adding a node is safe
**Source:** `tests/test_graph_tracer.py::test_...` (`:42-48`) and `tests/test_observability.py` (`:279-296`)
**Apply to:** the new `assess` node
- The tracer checks a **superset** of `TRACER_NODES`, so `+1` node is safe. The observability test asserts
  each node emits exactly one span (uniqueness), not a node count — the new node adds one `node` + one `tool`
  span, no break.

### Card field-set equality — do NOT touch `HandoverCard`
**Source:** `tests/test_safety_spine.py::_EXPECTED_CARD_FIELDS` (`:44-59`)
**Apply to:** Phase 8 scope boundary
- An exact-set assertion; adding a confidence field to the card breaks it and is Phase 10's banner work
  (Assumption A3). `assess` writes a **new state channel**, not the card.

### The ONE projection invariant
**Source:** `tests/test_docs_final.py::test_evals_is_a_projection_of_the_report` (`:98-105`)
**Apply to:** `report.json` + `EVALS.md`
- Runs `emit_evals.py --check`; fails if `EVALS.md` ≠ the generator's output. Every report change forces a
  `--write` regeneration (D8-14). No hand-typed number.

### One colour, one producer
**Source:** `src/triagedesk/core/scorer.py::_colour_for` (`:127-133`), `_colour_urgency` (`:136-144`)
**Apply to:** `core/confidence.py`
- The confidence signal **reads** `priority.triggered_rules` and the substrate `categories`; it never maps
  `tews`→colour or parses the `"discriminator override:"` detail string (Research Pitfalls 2/3).

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | Every new/modified file has a same-role, same-flow analog — the phase is deliberately additive onto frozen seams. |

The two regenerated artefacts (`evals/results/report.json`, `EVALS.md`) have no hand-written analog by
design: their "pattern" is the generator pipeline (`uv run triagedesk eval` → `emit_evals.py --write`),
and they must never be edited directly.

---

## Metadata

**Analog search scope:** `src/triagedesk/{core,graph,mcp,evals}`, `scripts/`, `tests/`, `docs/`, `evals/`.
**Files scanned:** ~30 (12 read in full, remainder via targeted grep).
**Tracked-source check:** every named analog verified with `git ls-files -- <path>` (all non-empty).
**Pattern extraction date:** 2026-10-12
**Confidence:** HIGH on the codebase seams (allowlist set-equality, tool-factory break, node superset
safety, purity/DRY guards, regeneration pipeline all confirmed by reading the files).

## PATTERN MAPPING COMPLETE
