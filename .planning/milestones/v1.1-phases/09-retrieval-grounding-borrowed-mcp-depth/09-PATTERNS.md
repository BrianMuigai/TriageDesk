# Phase 9: Retrieval Grounding & Borrowed-MCP Depth - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 16 (3 new, 13 modified)
**Analogs found:** 16 / 16 (every file has a direct in-repo precedent — this phase is *wiring + one small pure module*)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/triagedesk/core/retrieval.py` (NEW) | core module (pure) | transform | `src/triagedesk/core/confidence.py` | exact (purity + loader-read + named constants) |
| `src/triagedesk/core/matcher.py` (MOD) | core module (pure) | transform | itself (`_tokens`, :27-35) | exact |
| `src/triagedesk/core/schema.py` (MOD) | model / schema | declaration | `src/triagedesk/core/schema.py::ConfidenceResult` (:136-152) | exact |
| `src/triagedesk/graph/state.py` (MOD) | store / state channel | declaration | `confidence` channel (:55-57) | exact |
| `src/triagedesk/graph/nodes.py` (MOD) | hook (node factory) | request-response | `_make_assess` (:196-216) | exact |
| `src/triagedesk/graph/build.py` (MOD) | config (composition root) | event-driven (topology) | itself (allowlist/TRACER_NODES/edges) | exact |
| `src/triagedesk/mcp/server.py` (MOD) | controller (MCP tool) | request-response | `assess_confidence` (:207-223) | exact |
| `src/triagedesk/evals/tools.py` (MOD) | factory / config | request-response | `build_tools` (:77-138) | exact |
| `tests/conftest.py` (MOD) | test fixture | request-response | `build_graph_tools` (:134-216) | exact |
| `tests/test_safety_spine.py` (MOD) | test (guard) | n/a | itself (:187-215) | exact |
| `src/triagedesk/store/borrowed.py` (MOD) | service (adapter) | CRUD / request-response | itself (`_rows`, `_call`, `read_queue_row`, `ensure_schema`) | exact |
| `docs/DECISIONS.md` (MOD) | docs / config | n/a | D19 / D20 rows (tail) | role-match |
| `tests/test_retrieval.py` (NEW) | test | batch | `tests/test_confidence.py` | role-match |
| `tests/test_graph_grounding.py` (NEW) | test | event-driven | `tests/test_graph_confidence.py` | exact |
| `tests/test_borrowed_store.py` (MOD) | test | request-response | itself (`_FakeBorrowedTools`) | exact |
| `tests/test_observability.py` (MOD) | test (fake) | request-response | `_SqliteBorrowedTools` (:66-128) | exact |

**Tracked-source gate:** every analog above was verified `git ls-files --error-unmatch`-TRACKED this session. No gitignored install/mirror path is named anywhere in this document.

## The four set-equality sites (MOVE IN ONE WAVE — Pitfall 1)

Adding `"retrieve_evidence"` to any ONE of these without the other three makes `build_graph` raise
`RuntimeError: owned tool surface drifted from the allowlist (SAFE-03)` — the **whole suite fails at
composition**, not one test. All four edits belong to a single execution wave/plan.

| # | Site | Exact symbol | Line |
|---|------|--------------|------|
| 1 | `src/triagedesk/graph/build.py` | `OWNED_TOOL_ALLOWLIST` | :66-73 |
| 2 | `src/triagedesk/evals/tools.py` | `build_tools` return dict | :131-138 |
| 3 | `tests/conftest.py` | `build_graph_tools` return dict | :209-216 |
| 4 | `tests/test_safety_spine.py` | `test_graph_startup_asserts_the_tool_allowlist` exact-set literal | :190-197 |

---

## Pattern Assignments

### `src/triagedesk/core/retrieval.py` (NEW — core module, pure, transform)

**Analogs:** `src/triagedesk/core/confidence.py` (purity/loader/named-constant shape) + `src/triagedesk/core/matcher.py` (the tokeniser) + `src/triagedesk/core/citations.py` (the citation helper).

**Module docstring + imports pattern** (`core/confidence.py`, :1-26) — copy the *contract statement* shape: name the decisions, state that the module imports nothing from `llm`/`mcp`/`store`, state that every value is read via the ONE loader and nothing is inlined:

```python
# Source: src/triagedesk/core/confidence.py:1-26 (VERIFIED)
"""Pure deterministic coverage/deferral signal (D8-01, D8-02, D8-03).
...
This module imports nothing from ``llm`` / ``mcp`` / ``store`` (enforced by
``tests/test_purity.py``); every band and category is read from ``data/*.yaml``
through the one loader (``core/rules.py``) — no SATS value is inlined here
(CONVENTIONS §1). ...
"""

from __future__ import annotations

from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import (
    ConfidenceComponent, ConfidenceLevel, ConfidenceResult, PriorityResult,
)
```

**Named-constant single-source pattern** (`core/confidence.py`, :28-59) — the match bar / weights must be named module constants with a rationale comment, never bare literals; the `COMPONENT_NAMES`/`COMPONENT_COUNT` precedent is the model for anything retrieval publishes (e.g. its token-weight table):

```python
# Source: src/triagedesk/core/confidence.py:33, 43-59 (VERIFIED)
DEFERRAL_MIN_SATISFIED_COMPONENTS = 2   # named, derived from stated cost — never tuned green
...
COMPONENT_NAMES: tuple[str, ...] = (...)
# The signal's arity — the ONE source for the offline ECE normaliser, never a bare literal.
COMPONENT_COUNT = len(COMPONENT_NAMES)
```

**The corpus source — read through the ONE loader** (`core/rules.py`, :86-135) — build every passage *from* `get_discriminators()`; the id is closed by construction (D9-10):

```python
# Source: src/triagedesk/core/rules.py:86-99, 132-135 (VERIFIED)
class Discriminator(BaseModel):
    id: str
    category: str
    label: str
    aliases: list[str]

class DiscriminatorCategory(BaseModel):
    colour: str
    citation_ref: str
...
@lru_cache(maxsize=1)
def get_discriminators() -> DiscriminatorRules:
    return load_discriminators()
```

`get_discriminators()` also exposes `substrate.citation` and `substrate.no_match.warning` — the honest `no_match` text (E-09's deferral, D9-09) comes from there, never from a literal.

**Tokeniser — import the (promoted) public owner, do NOT re-implement** (`core/matcher.py`, :27-35):

```python
# Source: src/triagedesk/core/matcher.py:27-35 (VERIFIED) — after this phase, call the public form
from triagedesk.core.matcher import tokenize   # the ONE normalisation owner (D9 discretion)

tokens = tokenize(complaint)                   # never a second regex in retrieval.py
```

**Citation — call the ONE helper, never inline a string** (`core/citations.py`, :28-38):

```python
# Source: src/triagedesk/core/citations.py:28-38 (VERIFIED)
from triagedesk.core.citations import format_citation

citation = format_citation(category.citation_ref, substrate.citation)
```

**Deterministic ranking + public entry point** — mirror `assess(...)`'s shape (`core/confidence.py`, :148-196): a single public function returning the typed contract, with a module-level `__all__`:

```python
# Source: src/triagedesk/core/confidence.py:148-196 (VERIFIED, shape only)
def assess(matched_ids, no_match, priority) -> ConfidenceResult:
    ...
    return ConfidenceResult(...)

__all__ = ["COMPONENT_COUNT", "COMPONENT_NAMES", "DEFERRAL_MIN_SATISFIED_COMPONENTS", "assess"]
```

Retrieval's scorer must tie-break explicitly on `(score desc, id asc)` (Pitfall 2) so the ranking is reproducible; score is an **int**, never a float (mirrors the D8-04 no-float posture).

**Purity guard auto-covers it** (`tests/test_purity.py`, :89-97) — the parametrisation is `sorted(CORE_DIR.rglob("*.py"))`, so `core/retrieval.py` is scanned automatically the moment it exists (no test edit needed):

```python
# Source: tests/test_purity.py:89-97 (VERIFIED)
@pytest.mark.parametrize(
    "path", sorted(CORE_DIR.rglob("*.py")), ids=lambda p: p.relative_to(REPO_ROOT).as_posix()
)
def test_core_imports_nothing_from_llm_mcp_or_store(path: Path) -> None:
    offenders = _forbidden_in_file(path)
    assert not offenders, ...
```

**DRY/no-inlined-SATS guard also auto-covers it** (`tests/test_no_duplicated_sats.py`, :147-162) — it rglob-scans all of `src/`, so any label/alias/colour literal in `retrieval.py` fails the build. Every label/alias/citation must come from `get_discriminators()`.

---

### `src/triagedesk/core/matcher.py` (MOD — promote the ONE tokeniser)

**Analog:** itself. This is the ONLY module-level edit that changes a name; it must be **purely additive and behaviour-preserving**.

**Current state** (`core/matcher.py`, :27-35) — the private owner and its 3 call sites:

```python
# Source: src/triagedesk/core/matcher.py:27-35 (VERIFIED)
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

def _tokens(text: str) -> list[str]:
    """Tokenise *text* into lower-case alphanumeric runs (the shared boundary rule)."""
    return _TOKEN_PATTERN.findall(text.lower())
```

**The three internal callers** (verified this session — the *only* callers in the repo):

| Call site | Line | Use |
|-----------|------|-----|
| `_tokens(complaint)` | :60 | tokenise the complaint |
| `_tokens(alias)` | :65 | tokenise each alias |

**The additive change:** rename the public seam to `tokenize` (and keep `_tokens` delegating / aliasing so nothing else moves), then export it:

```python
# Recommended shape (discretion D9): one owner, two names — behaviour identical.
def tokenize(text: str) -> list[str]:
    """Tokenise *text* into lower-case alphanumeric runs (the ONE boundary rule)."""
    return _TOKEN_PATTERN.findall(text.lower())

_tokens = tokenize   # internal callers (:33, :60, :65) unchanged
```

Add `"tokenize"` to `matcher.py`'s `__all__` if/when one is declared. No other module in `src/` or `tests/` references `_tokens` (grep verified), so this is safe. See Pitfall/A3: if a reviewer treats `core/matcher.py` as frozen, move `tokenize` to a neutral core module — either way there must be **exactly one** owner.

---

### `src/triagedesk/core/schema.py` (MOD — the colour-free contract)

**Analog:** `ConfidenceResult` / `ConfidenceComponent` (:121-152) + `MatchResult` (:103-115) + the "deliberately no colour field" posture in `RecheckFlag` (:170-183) and `RecoveryRequest` (:186-196).

**The no-colour/no-float posture to copy** (`core/schema.py`, :136-152):

```python
# Source: src/triagedesk/core/schema.py:136-152 (VERIFIED)
class ConfidenceResult(BaseModel):
    """...There is deliberately no percentage and no float ``score``/``probability`` field:
    a model-derived number is *unrepresentable* rather than merely discouraged (D8-04). ..."""

    deferral: bool = False
    level: ConfidenceLevel = "high"
    components: list[ConfidenceComponent] = Field(default_factory=list)
    reason: str = ""
```

**Apply as** the `EvidencePassage` / `EvidenceResult` contract from 09-RESEARCH "The colour-free contract" (§Code Examples, :390-406): `EvidencePassage{discriminator_id, label, citation, score:int, rank:int}` and `EvidenceResult{passages, no_match, reason}` — with **no** `colour`/`target`/`priority`/`citations` field, so a colour is structurally unrepresentable (D9-03).

**The guard test pattern to mirror** (`tests/test_confidence.py`, :88-101):

```python
# Source: tests/test_confidence.py:88-101 (VERIFIED)
def test_contract_carries_no_float_or_probability_field() -> None:
    for model in (ConfidenceResult, ConfidenceComponent):
        for name, field in model.model_fields.items():
            assert field.annotation is not float, f"{model.__name__}.{name} is a float"
            ...
    # There is deliberately no colour field: the signal can never downgrade one (D8-12).
    assert "colour" not in ConfidenceResult.model_fields
```

Note: adding these models to `core/schema.py` **automatically** extends the checkpointer allowlist (`graph/build.py::_allowed_msgpack_modules`, :346-359, derives from `vars(schema_module)`), so no edit is needed there — but the new models must live in `schema.py`, not in `retrieval.py`.

---

### `src/triagedesk/graph/state.py` (MOD — the `evidence` channel)

**Analog:** the `confidence` channel (:55-57) and the import block (:14-23).

```python
# Source: src/triagedesk/graph/state.py:14-23, 55-57 (VERIFIED)
from triagedesk.core.schema import (
    CaseInput, CommitResult, ConfidenceResult, Escalation, HandoverCard,
    PriorityResult, RecheckFlag, RecoveryRequest,
)
...
    # Deterministic coverage/deferral signal (AGENT-02, D8-08): written by ``assess`` and
    # consulted by ``route_after_assess``. It never reaches ``commit`` (D8-12).
    confidence: ConfidenceResult | None
```

**Apply:** add `from triagedesk.core.schema import EvidenceResult` and a `evidence: EvidenceResult | None` channel, with a comment stating it is written by `ground` and read by **nothing that routes** (D9-07/D9-08). No reducer is needed (last-write-wins, per 09-RESEARCH Standard Stack). Also extend the module docstring's channel inventory (:26-36) to name `ground` → `evidence`.

---

### `src/triagedesk/graph/nodes.py` (MOD — the `ground` factory)

**Analog:** `_make_assess` (:196-216) — a thin factory returning an async node that writes **exactly one** channel; plus `_make_retrieve` (:166-178) for the `state["case"].complaint` read; plus `parse_tool_result` (:64-81) for decoding.

```python
# Source: src/triagedesk/graph/nodes.py:196-216 (VERIFIED) — the exact shape to mirror
def _make_assess(tools: ToolMap) -> NodeFn:
    """Build the ``assess`` node over the injected tool mapping (D8-08)."""

    async def assess(state: TriageState) -> dict[str, Any]:
        """...It never assigns to ``priority``, so the scored colour is unchanged..."""
        payload = {...}
        signal = parse_tool_result(ConfidenceResult, await tools["assess_confidence"](payload))
        return {"confidence": signal}          # the ONLY key

    return assess
```

```python
# Source: src/triagedesk/graph/nodes.py:166-178 (VERIFIED) — reading the complaint
async def retrieve(state: TriageState) -> dict[str, Any]:
    case = state["case"]
    match = parse_tool_result(MatchResult, await tools["match_discriminators"]({"complaint": case.complaint}))
    return {"matched_ids": list(match.matched_ids), "no_match": match.no_match}
```

**Apply:** add `_make_ground(tools)` returning `{"evidence": result}` — the **only** key (never `priority`/`citations`/`matched_ids`/`no_match`, D9-07). Then register it in `make_nodes` (:393-413):

```python
# Source: src/triagedesk/graph/nodes.py:400-413 (VERIFIED) — add one line
return {
    "ingest": ingest,
    "normalize": _make_normalize(tools),
    "retrieve": _make_retrieve(tools),
    "score": _make_score(tools),
    "ground": _make_ground(tools),      # NEW
    "assess": _make_assess(tools),
    ...
}
```

Extend the module docstring (:1-18) note that `ground` touches no model.

---

### `src/triagedesk/graph/build.py` (MOD — the composition root)

**Analog:** itself. Four distinct edits, all in the ONE composition root.

**(a) The allowlist** (:66-73) — append `"retrieve_evidence"`:

```python
# Source: src/triagedesk/graph/build.py:66-73 (VERIFIED)
OWNED_TOOL_ALLOWLIST: tuple[str, ...] = (
    "normalize_case", "match_discriminators", "score_priority",
    "raise_recheck_flag", "assess_confidence", "commit_priority",
)
```

**(b) `TRACER_NODES`** (:97-110) — add `"ground"`. The tracer test asserts a **superset** (`tests/test_graph_tracer.py`, :42-48, `missing = expected - node_names`), so adding is safe.

**(c) The wiring** (:238-275) — insert `ground` at `score → ground → verify`:

```python
# Source: src/triagedesk/graph/build.py:245-259 (VERIFIED) — current, then the insertion
graph.add_edge("retrieve", "score")
graph.add_conditional_edges(
    "score", route_after_score,
    {"escalate": "escalate", "request_missing_info": "request_missing_info", "verify": "verify"},
)
graph.add_conditional_edges(
    "verify", route_after_verify,
    {"recheck": "recheck", "score": "score", END: END},
)
```

Insert as a plain edge (routing-neutral, D9-08) — **do not** add a conditional edge or a router that reads `evidence`:

```python
# The insertion: replace {"verify": "verify"} above with {"verify": "ground"},
# then add the plain edges. Both are legal "after score" placements:
graph.add_edge("ground", "verify")        # option A: score → ground → verify
# OR (single-run; avoids the retry re-running ground — see below):
# graph.add_conditional_edges("verify", route_after_verify, {"recheck": "recheck", "score": "score", END: END})
# graph.add_edge("ground", "recheck")     # option B: verify --ok--> ground --> recheck
```

**The retry hazard** (`route_after_verify`, :175-186): `"score"` is returned on a failed check, so option A runs `ground` twice on a sliced case (E-12 slices; deterministic and harmless per 09-RESEARCH Blast Radius E). Option B runs it once. Either is "after `score`" and routing-neutral — the plan must pick one and note it.

**(d) `_spanned`** (:189-213) — no change; the `add_node` loop (:235-236) wraps every `TRACER_NODES` entry automatically, so `ground` gets its node span for free.

The `add_node` loop:

```python
# Source: src/triagedesk/graph/build.py:234-236 (VERIFIED)
graph: StateGraph = StateGraph(TriageState)
for name in TRACER_NODES:
    graph.add_node(name, _spanned(name, nodes[name]))
```

---

### `src/triagedesk/mcp/server.py` (MOD — the 7th tool)

**Analog:** `assess_confidence` (:207-223) — the closest thin `@audited()` wrapper; `match_discriminators` (:226-236) for a single-string input + read-only docstring.

```python
# Source: src/triagedesk/mcp/server.py:207-223 (VERIFIED)
@server.tool()
@audited()
def assess_confidence(
    matched_ids: list[str], no_match: bool, priority: PriorityResult,
) -> ConfidenceResult:
    """Return the deterministic coverage/deferral signal — no model, no store (D8-07).
    A thin, contract-typed adapter over the pure ``core.confidence.assess`` function
    (SOLID: S/D)... It touches no store, writes no queue row and takes no approval token...
    """
    return confidence.assess(matched_ids, no_match, priority)
```

```python
# Source: src/triagedesk/mcp/server.py:226-236 (VERIFIED)
@server.tool()
@audited()
def match_discriminators(complaint: str) -> MatchResult:
    """...A thin, contract-typed adapter over the pure ``core.matcher`` function..."""
    return matcher.match_discriminators(complaint)
```

**Apply:** the read-only tool from 09-RESEARCH §Code Examples (:408-416) — `@server.tool()` + `@audited()` + `def retrieve_evidence(complaint: str) -> EvidenceResult: return retrieval.retrieve(complaint)`. Add `retrieval` to the core import line (:30) and `EvidenceResult` to the schema import block (:31-40). Update the module docstring's "six tools" → "seven" (:1) and the `@audited` docstring if it enumerates.

---

### `src/triagedesk/evals/tools.py` (MOD — set-equality site #2)

**Analog:** `build_tools` (:77-138); the `assess_confidence` closure (:118-123) is the exact shape for a thin pass-through closure.

```python
# Source: src/triagedesk/evals/tools.py:118-138 (VERIFIED)
    async def assess_confidence(inp: Mapping[str, Any]) -> Any:
        return await server_module.assess_confidence(
            list(inp.get("matched_ids") or []),
            bool(inp.get("no_match")),
            PriorityResult.model_validate(inp["priority"]),
        )
    ...
    return {
        "normalize_case": normalize,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "assess_confidence": assess_confidence,
        "commit_priority": commit_priority,
    }
```

**Apply:** add a `retrieve_evidence` closure (`return await server_module.retrieve_evidence(str(inp["complaint"]))`) and its dict entry. The harness calls the **real owned tool in-process** (SOLID: L) — no stub.

---

### `tests/conftest.py` (MOD — set-equality site #3)

**Analog:** `build_graph_tools` (:134-216); the `assess_confidence` closure (:175-181) is the model.

```python
# Source: tests/conftest.py:175-181, 209-216 (VERIFIED)
    async def assess_confidence(inp: dict[str, Any]) -> Any:
        calls.append(("assess_confidence", inp))
        return confidence.assess(
            list(inp.get("matched_ids") or []),
            bool(inp.get("no_match")),
            PriorityResult.model_validate(inp["priority"]),
        )
    ...
    return {
        "normalize_case": normalize_case,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "assess_confidence": assess_confidence,
        "commit_priority": commit_priority,
    }
```

**Apply:** add a `retrieve_evidence` closure that `calls.append(("retrieve_evidence", inp))` then returns `retrieval.retrieve(str(inp["complaint"]))` (import `retrieval` alongside `confidence, matcher, recheck, scorer` at :20). Add the dict entry. This is the fake the graph proof suites use — the `calls` log is what `test_graph_grounding.py` will assert on.

---

### `tests/test_safety_spine.py` (MOD — set-equality site #4)

**Analog:** itself (:187-215). This is the assertion that also proves the fan-out is not vacuous.

```python
# Source: tests/test_safety_spine.py:187-215 (VERIFIED)
def test_graph_startup_asserts_the_tool_allowlist() -> None:
    """The graph composes only over the allowlisted tool set, failing loudly on drift (SAFE-03)."""
    # The allowlist is the owned six, declared as ONE constant.
    assert set(build_module.OWNED_TOOL_ALLOWLIST) == {
        "normalize_case", "match_discriminators", "score_priority",
        "raise_recheck_flag", "assess_confidence", "commit_priority",
    }
    # The allowlisted surface composes cleanly.
    build_graph(build_graph_tools())
    ...
```

**Apply:** add `"retrieve_evidence"` to the literal set (comment → "owned seven"). The MISSING/UNEXPECTED sub-cases below it keep working unchanged.

---

### `src/triagedesk/store/borrowed.py` (MOD — read-path depth + allowlist + guard)

**Analog:** itself. Three additive pieces; the `Store` protocol shape (`store/__init__.py`, :64-119) does **not** change (D9-11) — no method signature may move.

**(a) The read-path constants already exist and are under-used** (:29-47) — use them, don't add new strings:

```python
# Source: src/triagedesk/store/borrowed.py:29-47 (VERIFIED)
TOOL_DB_INFO = "db_info"
TOOL_QUERY = "query"
TOOL_LIST_TABLES = "list_tables"
TOOL_GET_TABLE_SCHEMA = "get_table_schema"
TOOL_CREATE_RECORD = "create_record"
TOOL_READ_RECORDS = "read_records"
TOOL_UPDATE_RECORDS = "update_records"
TOOL_DELETE_RECORDS = "delete_records"

EXPECTED_TOOLS: tuple[str, ...] = ( TOOL_DB_INFO, TOOL_QUERY, TOOL_LIST_TABLES, TOOL_GET_TABLE_SCHEMA,
    TOOL_CREATE_RECORD, TOOL_READ_RECORDS, TOOL_UPDATE_RECORDS, TOOL_DELETE_RECORDS, )
```

Add a `READ_TOOLS: tuple[str, ...] = (TOOL_DB_INFO, TOOL_QUERY, TOOL_LIST_TABLES, TOOL_GET_TABLE_SCHEMA, TOOL_READ_RECORDS)` allowlist (D9-12) and enforce it in `_call`.

**(b) The one dispatch seam** (:165-167) — the single place the allowlist is applied:

```python
# Source: src/triagedesk/store/borrowed.py:165-167 (VERIFIED)
    async def _call(self, name: str, arguments: Mapping[str, Any]) -> Any:
        """Invoke one borrowed tool through the injected mapping (D-13)."""
        return await self._tools[name](dict(arguments))
```

**Apply:** before dispatch, refuse a tool not in `READ_TOOLS` (fail closed) and, for `TOOL_QUERY`, refuse a non-read statement. The statement guard from 09-RESEARCH §Code Examples (:419-427) is **new** (no repo analog — classifier is in-house):

```python
# NEW — fail-closed leading-keyword classifier (D9-12)
_READ_PREFIXES = ("SELECT", "PRAGMA", "EXPLAIN", "WITH", "VALUES")

def is_read_only_statement(sql: str) -> bool:
    """True only for a statement whose leading keyword is read-only (fails closed)."""
    head = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    return head in _READ_PREFIXES
```

> **Caution:** `ensure_schema` (:169-179) issues `CREATE TABLE` / `ALTER TABLE` through `TOOL_QUERY`. The guard must permit schema bootstrap on the **adapter-init** path while refusing mutations on the **agent read path** (D9-13). Either scope the guard to read methods only, or route the DDL through a separate internal call that bypasses the guard — decide once and name it. Do NOT break `ensure_schema`.

**(c) Apply the read tools, additively** — reuse `_rows` (:117-147) to decode any read shape:

```python
# Source: src/triagedesk/store/borrowed.py:169-195 (VERIFIED) — read-path + parameterised-values pattern
    async def ensure_schema(self) -> None:
        await self._call(TOOL_QUERY, {"sql": _QUEUE_DDL})
        ...
        columns = _rows(await self._call(TOOL_QUERY, {"sql": f"PRAGMA table_info({AUDIT_TABLE})"}))
        if not any(str(column.get("name")) == "trace_id" for column in columns):
            await self._call(TOOL_QUERY, {"sql": _AUDIT_TRACE_ID_MIGRATION})

    async def read_queue_row(self, case_id: str, content_hash: str) -> QueueRow | None:
        rows = _rows(await self._call(TOOL_QUERY, {
            "sql": ("SELECT ... FROM {QUEUE_TABLE} WHERE case_id = ? AND content_hash = ? LIMIT 1"),
            "values": [case_id, content_hash],           # parameterised — never interpolated (T-06-01)
        }))
```

Per 09-RESEARCH Open Question 2 (recommendation): surface read-path depth as a **startup probe inside `ensure_schema`** — call `db_info` + `list_tables`, and use `get_table_schema` for the `trace_id` column check. Keep `read_records` usage minimal (its arg shape is ASSUMED — A1) and behind a human-verify checkpoint. Update `__all__` (:364-372) if new public helpers are added.

---

### `docs/DECISIONS.md` (MOD — the retrieval design row)

**Analog:** the D19/D20 row format (tail of the file) — `### Dn — Title` then **Decision:** / **Why:** / **Consequence:**, ADR-lite, "never tuned to make a test green".

```markdown
# Source: docs/DECISIONS.md:176-188 (D20, VERIFIED) — the row shape to copy
### D20 — Asymmetric-cost deferral threshold for the coverage signal
**Decision:** ...
**Why:** ...
**Consequence:** the signal can only ever make the system *more* cautious ... The named constant
lives once in `core/confidence.py`; this record is its rationale and it is never tuned to make a test green.
```

**Apply:** add the next-numbered row (D21) recording: the corpus is derived from `data/*.yaml` via the ONE loader; the ranking is an in-house deterministic integer lexical scorer (no `rank-bm25`, no embeddings); the contract has **no colour field** (unrepresentable, not merely unused); `evidence` is written by `ground` and read by nothing that routes; E-09 stays an honest deferral (never an alias). Keep the disclosed-components table (bottom of file) unchanged — this phase adds no dependency.

Note the docs guard (`tests/test_docs_final.py`) does **not** bound `docs/DECISIONS.md`, so length is free — but keep the ADR-lite shape for the live review (DQ-8).

---

### `tests/test_retrieval.py` (NEW — pure-scorer proofs)

**Analog:** `tests/test_confidence.py` (the pure-signal contract suite) for shape; `tests/test_matcher_determinism.py` for determinism; `tests/test_no_duplicated_sats.py` for the literal guard.

**The no-colour/no-float field-iteration proof** (`tests/test_confidence.py`, :88-101) — iterate `EvidenceResult`/`EvidencePassage.model_fields`, assert no field annotation is `float`, assert `"colour" not in EvidenceResult.model_fields`, and assert the serialised JSON carries no substrate colour token.

**Determinism proof** — mirror the matcher determinism suite: same complaint → identical ranked passage list on repeat calls.

**Closed-set proof (D9-10)** — every returned `discriminator_id` is a member of `{d.id for d in get_discriminators().discriminators}` (derive the set from the loader — never a literal, per the DRY gate). Add the E-09 case: `retrieve("feeling unwell")` returns `no_match=True` (D9-09/Pitfall 5) — do not tune it green.

**Expected commands** (09-RESEARCH Validation Architecture): `uv run pytest tests/test_retrieval.py -x`.

---

### `tests/test_graph_grounding.py` (NEW — ground writes only `evidence`; routing-neutral)

**Analog:** `tests/test_graph_confidence.py` — the offline graph-proof suite: builds the graph over `build_graph_tools()` fakes, uses `InMemorySaver`, asserts routing.

```python
# Source: tests/test_graph_confidence.py:1-40 (VERIFIED) — the offline proof harness shape
from langgraph.checkpoint.memory import InMemorySaver
from conftest import COMPLETE_CASE, build_graph_tools
from triagedesk.graph.build import build_graph, route_after_assess
```

**Proof 1 — channel isolation (D9-07):** run the graph with and without the `ground` node's output and assert `priority`, `citations`, `matched_ids`, `no_match` are byte-identical; the `ground` return dict keys == `{"evidence"}`. The `calls` log from `build_graph_tools` is how you observe `retrieve_evidence` was called.

**Proof 2 — routing neutrality (D9-08):** assert no conditional edge/router reads `evidence`; assert `score → ground → verify` (or option B) is present in `graph.get_graph().edges`. Mirror the superset node assertion in `tests/test_graph_tracer.py`, :42-48.

**Proof 3 (existing, must stay green):** E-09 → clean defer (already in `tests/test_eval_suite.py` :96-104, `deferrals == [True]*3`).

**Expected command:** `uv run pytest tests/test_graph_grounding.py -x`.

---

### `tests/test_borrowed_store.py` (MOD — read tools observed; mutation refused)

**Analog:** itself — `_FakeBorrowedTools` (:41-93) already records every call in `self.calls` and already implements all eight borrowed tools.

```python
# Source: tests/test_borrowed_store.py:41-93 (VERIFIED)
class _FakeBorrowedTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any]]] = []
        self.response: Any = []
    def _record(self, name, arguments) -> None:
        self.calls.append((name, dict(arguments)))
    def tools(self) -> dict[str, Any]:
        async def db_info(arguments): self._record("db_info", arguments); return {"tableCount": 2}
        ...
```

**Apply (per D9-14 / MCP-01):**
- Assert the read tools were **observed called**: after `await store.ensure_schema()` (or the chosen probe), `[name for name, _ in fake.calls]` contains `db_info` / `list_tables` / `get_table_schema` (and `read_records` if used).
- Assert a **mutation through the read path is refused and the fake is never reached**: call the guarded path with an `INSERT`/`DELETE` and assert `pytest.raises(...)` **and** that no `TOOL_QUERY` write call was recorded (mirror the refuse-before-touch posture of `commit_priority`).
- Assert an **unpermitted tool name raises** (fail closed).
- Keep the existing test `test_expected_tools_match_the_phase_1_handshake` (:101-103) green — `EXPECTED_TOOLS` is unchanged.

**Expected command:** `uv run pytest tests/test_borrowed_store.py -x`.

---

### `tests/test_observability.py` (MOD — the stdlib fake; Pitfall 3)

**Analog:** `_SqliteBorrowedTools` (:66-128) — it keeps a **live `sqlite3` connection** and runs real SQL, so its read tools can return real columns/rows.

```python
# Source: tests/test_observability.py:99-101 (VERIFIED) — the stale stub to fix
        async def get_table_schema(arguments: Any) -> Any:
            self._record("get_table_schema", arguments)
            return {"tableName": arguments.get("tableName")}     # NO columns → Pitfall 3
```

**The hazard (Pitfall 3):** if `ensure_schema` switches its `trace_id` check from `PRAGMA table_info` (via `query`) to `get_table_schema`, this fake returns no columns → the check thinks `trace_id` is absent → issues `ALTER TABLE` → "duplicate column name". **Fix in the same wave:** make `get_table_schema` (and `read_records`, :107-109) query the live `self.conn` and return real columns/rows, e.g. `[dict(r) for r in self.conn.execute("PRAGMA table_info(...)")]`. Keep `test_expected_tools_match_the_phase_1_handshake` (:131-133) green.

---

## Shared Patterns

### Pure-core boundary (one-way contract)
**Source:** `tests/test_purity.py:89-97` (auto-covers `core/retrieval.py`) + module docstrings in `core/confidence.py:1-16`, `core/matcher.py:15-18`, `core/citations.py:7-9`.
**Apply to:** `core/retrieval.py`. It must import nothing from `llm`/`mcp`/`store`; read all substrate via `core/rules.py`; import the citation helper, never inline a citation.

### Extend by a new node + a new tool, never by editing working code (SOLID: O)
**Source:** `docs/CONVENTIONS.md:28-32` (S/O) + the Phase-8 precedent (`core/confidence.py` → `assess_confidence` → `_make_assess` → `confidence` channel).
**Apply to:** all six source edits. Nothing edits the scorer's arithmetic, `core/citations.py`, or `@audited`'s behaviour.

### The ONE dispatcher for tool calls (audit + span)
**Source:** `src/triagedesk/mcp/server.py:92-167` (`@audited()`).
**Apply to:** `retrieve_evidence` — it joins the SAME interceptor; the tool body carries no audit code. It gets its `tool` span and audit record for free.

### The ONE tool mapping shape (DIP seam)
**Source:** `graph/nodes.py:45` (`ToolMap`), `graph/build.py:278-292` (`load_graph_tools`), `evals/tools.py:28`.
**Apply to:** `ground` depends on `tools["retrieve_evidence"]` (the mapping), never on a concrete server import.

### Parameterised values + a fail-closed guard for the borrowed store
**Source:** `store/borrowed.py:213-240` (`upsert_queue_row` — `values`, never interpolation).
**Apply to:** every borrowed read/write; the statement guard wraps it, failing closed.

### Refuse-before-touch (no side effect without a validated token)
**Source:** `mcp/server.py:273-282` (`commit_priority` refuses before any store call).
**Apply to:** the borrowed statement guard — a non-read statement is refused **before** reaching the borrowed server (D9-12), with the fake/connection provably untouched (D9-14).

### InTest fakes are shared, one per concern (DRY)
**Source:** `tests/conftest.py:67-86` (`RecordingStore` subclasses the ONE `InMemoryStore`; one fake, not one per module).
**Apply to:** the new `retrieve_evidence` fake closure is added to the EXISTING `build_graph_tools`, not a new builder.

## Blast Radius (baseline: 304 passing — 09-RESEARCH §Blast Radius)

**Safe as-is (superset / membership checks — no edit):** `tests/test_graph_tracer.py:42-48`, `tests/test_observability.py:282-292` (node-span uniqueness — `ground` adds exactly one name on E-02, no retry), `tests/test_mcp_server.py:33-39` (`>=` five), `tests/test_mcp_tools.py` (membership), `tests/test_graph_durable.py:51-56` (`ONCE_PER_TOOL` is a subset; `retrieve_evidence` not listed), `tests/test_graph_durable.py:89` / `test_graph_tracer.py:121` (`snapshot.next == ("approval_gate",)` — unaffected by a node before `verify`), `tests/test_replay_read_only.py` (`_render` ignores the extra channel), `tests/test_no_duplicated_sats.py`, `tests/test_purity.py`.

**Optional hygiene:** `tests/test_demo.py:26-32` `_ESCALATION_TOOLS` — `retrieve_evidence` now appears; the assertion (`those five appear`, `raise_recheck_flag` does not) is not broken, but the tuple/docstring could note the escalation beat reaches six tools.

**Must move together (Pitfall 1):** the four set-equality sites above.

## No Analog Found

| File | Role | Data Flow | Reason / mitigation |
|------|------|-----------|---------------------|
| `is_read_only_statement()` (inside `store/borrowed.py`) | utility (pure) | transform | No SQL statement classifier exists in the repo. In-house by design (09-RESEARCH §Code Examples). Keep it pure + fail-closed and unit-test it directly (assert `False` for `INSERT/UPDATE/DELETE/CREATE/DROP/ALTER`, `True` for `SELECT/PRAGMA/EXPLAIN/WITH/VALUES`). |

Everything else has a direct in-repo analog; no new dependency, no new pattern.

## Metadata

**Analog search scope:** `src/triagedesk/{core,graph,mcp,store,evals}/`, `tests/`, `docs/`, `data/`, `evals/cases/`.
**Files scanned (read this session):** 20 source + test + docs files; all named analogs verified git-tracked.
**Tokeniser call sites verified:** `matcher.py` :33, :60, :65 only — no other repo caller.
**Read-tool constants verified:** declared and referenced only inside `store/borrowed.py` (no read-path user yet — exactly what MCP-01 closes).
**Pattern extraction date:** 2026-10-13.

## PATTERN MAPPING COMPLETE

**Phase:** 9 - Retrieval Grounding & Borrowed-MCP Depth
**Files classified:** 16 (3 new, 13 modified)
**Analogs found:** 16 / 16

### Coverage
- Files with exact analog: 14
- Files with role-match analog: 2 (`tests/test_retrieval.py` ← `test_confidence.py`; `docs/DECISIONS.md` ← D19/D20 rows)
- Files/units with no analog: 1 unit (`is_read_only_statement`, in-house by design)

### Key Patterns Identified
- **The four set-equality sites must move in ONE wave** (`graph/build.py::OWNED_TOOL_ALLOWLIST`, `evals/tools.py::build_tools`, `tests/conftest.py::build_graph_tools`, `tests/test_safety_spine.py`), or `build_graph` raises at composition and the whole suite fails.
- **Pure-core triple** (`core/confidence.py` → `assess_confidence` → `_make_assess` → `confidence` channel) is the exact mirror for `core/retrieval.py` → `retrieve_evidence` → `ground` → `evidence` — with **no** routing edge.
- **One normalisation owner**: promote `matcher._tokens` → public `tokenize()`; `retrieval.py` imports it; never a second regex. Verified only 3 internal callers.
- **Colour is unrepresentable, not merely unused**: the `EvidenceResult` contract carries no `colour`/`target`/`priority` field (mirrors `ConfidenceResult`'s no-float posture; proven by iterating `model_fields`).
- **Attribution reuses `core.citations.format_citation`** and the closed discriminator set from `get_discriminators()` — no inlined citation, no invented id (auto-guarded by `test_no_duplicated_sats.py` + `test_purity.py`).
- **Borrowed read-path depth behind the unchanged `Store` protocol**: apply the already-declared `TOOL_DB_INFO`/`TOOL_LIST_TABLES`/`TOOL_GET_TABLE_SCHEMA`/`TOOL_READ_RECORDS` at the single `_call` seam, with a tool allowlist + a fail-closed statement guard; the `ensure_schema` DDL path must keep working, and the stdlib fake's `get_table_schema` must return real columns (Pitfall 3).

### File Created
`.planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
