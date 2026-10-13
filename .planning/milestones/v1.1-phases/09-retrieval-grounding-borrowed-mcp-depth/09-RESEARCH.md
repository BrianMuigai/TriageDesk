# Phase 9: Retrieval Grounding & Borrowed-MCP Depth - Research

**Researched:** 2026-10-13
**Domain:** In-house deterministic lexical retrieval over a closed SATS KB + borrowed-MCP read-path depth behind an unchanged protocol (Python 3.12, LangGraph, MCP SDK v2)
**Confidence:** HIGH (codebase seams read this session) / MEDIUM (borrowed `read_records`/`get_table_schema` wire shapes are unverified — see Assumptions)

## Summary

All the machinery this phase attaches to was read directly this session, so the seams are
known, not guessed. The phase adds **four additive things** — a pure `core/retrieval.py`, a
`retrieve_evidence` owned tool (the 7th), a `ground` node + `evidence` state channel, and
read-path usage inside `store/borrowed.py` — plus the **one-wave allowlist edit** that the
project's set-equality contract makes mandatory.

The retrieval is advisory only. It runs *after* `score` and writes a channel the scorer never
reads, so it is structurally incapable of changing a colour (`citations == triggered_rules`
stays scorer-produced). The corpus is the *existing* `data/sats_discriminators.yaml` read
through the ONE loader (`core/rules.py`); nothing is re-authored and no SATS value is inlined,
so the `test_no_duplicated_sats.py` guard stays green.

The single highest-risk item is not the retrieval — it is the **set-equality fan-out**: the
owned-tool allowlist is asserted as an *exact set* at four sites, and the graph refuses to
compose when any site lags. All four must move in one wave. Everything else adds nodes/channels
that existing tests check as *supersets*, so it is safe.

**Primary recommendation:** Build a dependency-free integer-weight lexical scorer that reuses
`core/matcher.py`'s tokeniser (promoted to a public `tokenize()`), expose it as a read-only
`retrieve_evidence` tool over a new colour-free `EvidenceResult` contract, wire `ground` at
`score → ground → verify`, and deepen `store/borrowed.py` reads behind the unchanged `Store`
protocol with a tool allowlist + a fail-closed statement guard.

## Project Constraints (from AGENTS.md)

- **IRON-CLAD DRY + SOLID.** Authoritative standard: `docs/CONVENTIONS.md` — mandatory before any
  `Edit`/`Write`. A violation is rejected at review and **blocks the phase**.
- SATS thresholds/discriminators live **only** in `data/*.yaml`; code reads them via the ONE loader.
- One schema module (`core/schema.py`); one citation helper (`core/citations.py::format_citation`);
  one audit append (`store/audit.append`); one place a colour is produced (`core/scorer.py`).
- Extend by **data/config**, and by a **new node + new tool** — never by editing working code.
- The graph depends on the **MCP tool interface**, not a concrete implementation (SOLID: D/L).
- Work must run through a GSD command (`/gsd-execute-phase`), not direct edits.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D9-01:** The corpus is derived from the existing **`data/*.yaml`** substrate through the ONE rules loader
  (`core/rules.py`): the discriminator catalogue and its categories, and the TEWS band structure. Nothing is
  re-authored and no colour/band/tag literal is inlined in code (the no-duplicated-SATS guard stays green).
- **D9-02:** The ranking is an **in-house, deterministic lexical scorer** — no embeddings, no vector
  database, no `rank-bm25` (its numpy-2 alias risk). The same input always yields the same ranking, so the
  retrieval is reproducible and offline.
- **D9-03:** The retrieval contract returns **only**: the closed-set discriminator ids it matched, a
  rank/score ordering, and an explicit `no_match` when nothing clears the bar — plus the attributed excerpt
  text needed to *show* the grounding. It has **no colour field**, so it structurally cannot set a priority.
- **D9-04:** The pure computation lives in a NEW `core/retrieval.py` mirroring `core/scorer.py`'s purity
  (no model, no MCP client, no I/O); the tool is a thin audited wrapper over it.
- **D9-05:** A new owned MCP tool `retrieve_evidence` (the 7th) joins the ONE `@audited` interceptor.
  Because the owned-tool allowlist is **set-equality across three sites** (`graph/build.py::OWNED_TOOL_ALLOWLIST`,
  `evals/tools.py::build_tools`, `tests/conftest.py::build_graph_tools`) plus the exact-set assertion in
  `tests/test_safety_spine.py`, all four move in the SAME wave or composition raises for the whole suite.
- **D9-06:** The tool is **read-only and side-effect-free**: no store access, no queue row, no approval
  token. It reads only the loaded `data/*.yaml` substrate.
- **D9-07:** A new `ground` node sits **after `score`** and writes a NEW `evidence` state channel. It must
  NOT write `priority`, `citations`, `matched_ids` or `no_match` — proven by a test that those channels are
  byte-identical with and without `ground` running.
- **D9-08:** `ground` is **routing-neutral**: it never changes the path taken (no conditional edge depends on
  `evidence`). Its purpose is attributable display and provenance, not a decision.
- **D9-09:** The declared failure **E-09** is addressed by **real retrieval or an honest clean defer** —
  never by adding a literal discriminator alias to make it pass. With the absolute `no_match` deferral
  (D8-11), E-09's honest outcome is a deferral; retrieval must surface the coverage gap rather than paper over
  it. No fixture, threshold, or alias is tuned.
- **D9-10:** The retrieval must never invent a rule id: every returned id is a member of the closed
  discriminator set read from `data/sats_discriminators.yaml`, and an unknown id cannot be produced.
- **D9-11:** The borrowed store adapter (`store/borrowed.py`) actually **uses** the borrowed server's read
  paths — `db_info`, `list_tables`, `get_table_schema`, `read_records` — not only `query`. The usage is
  **behind the unchanged `Store` protocol** (its method signatures do not change), so the graph keeps
  depending on the interface, not the borrowed implementation (SOLID: D).
- **D9-12:** The borrowed server stays **read-only in the agent path** via a **tool allowlist** (only the
  read tools are permitted) and a **statement guard** (any write/mutation statement is refused before it
  reaches the borrowed server). The guard fails closed and is provable by test.
- **D9-13:** The write path (the queue/audit writes) remains reachable **only** through the existing gated
  commit route; the agent path cannot issue a mutation through the borrowed server.
- **D9-14:** The read-path usage is exercised by a test that drives the adapter against the borrowed server
  (or its stdlib stand-in) and observes the read tools being called, so MCP-01 is demonstrated rather than
  asserted.

### the agent's Discretion
- The exact lexical scoring function (tokenisation, weighting, the match bar) provided D9-02/D9-03 hold.
- The `evidence` channel's element shape and the excerpt-attribution format.
- The `ground` node's position among the `score → … → verify` edges, provided it is after `score` and
  routing-neutral (D9-07/D9-08).
- Whether retrieval reuses the matcher's normalisation or a sibling helper, provided DRY holds (one
  normalisation owner).
- How the read-path depth is surfaced (a startup probe, an explicit call, or a diagnostic command).

### Deferred Ideas (OUT OF SCOPE)
- Generative RAG that writes clinical prose — forbidden (hallucination risk).
- A second borrowed **vector** MCP server (MCP-02) — future requirements.
- Multimodal intake and the desk UX (UX-05 / Phase 10).
- The desk-facing rendering of the evidence (Phase 10 consumes it).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-03 | A `retrieve_evidence` tool and a `ground` node placed after `score` fetch attributed SATS KB excerpts (derived from `data/*.yaml`, not re-authored); retrieval returns only closed-set discriminator ids, a rank, and an explicit `no_match`; E-09 addressed by real retrieval or a clean defer, never an alias. | §1 (corpus + lexical scorer), §2 (colour-free contract), §3 (tool + node + allowlist wave), §4 (`evidence` channel), §6 (E-09 honesty) |
| MCP-01 | The borrowed SQLite MCP server is exercised beyond `query` — `list_tables`, schema, `read_records`, `db_info` used behind the unchanged `Store` protocol, server stays read-only in the agent path with a tool allowlist and statement guard. | §5 (read-path depth, allowlist, statement guard, proof-by-test) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lexical retrieval scoring (deterministic rank) | Pure core module (`core/retrieval.py`) | — | Mirrors `core/scorer.py`/`core/confidence.py`: no model, no MCP, no I/O; enforced by `tests/test_purity.py`. |
| Attributed evidence contract | Schema module (`core/schema.py`) | — | The ONE schema module; the checkpointer msgpack allowlist is derived from it. |
| `retrieve_evidence` tool | Owned MCP server (`mcp/server.py`) | Pure core (delegates) | Thin `@audited()` wrapper; read-only; SRP. |
| `ground` node + `evidence` channel | Graph (`graph/nodes.py`, `graph/state.py`, `graph/build.py`) | — | Thin node; routing-neutral; node span emitted by the composition-root wrapper. |
| Borrowed read-path depth | Storage adapter (`store/borrowed.py`) | — | The ONLY layer that reaches the borrowed server; behind the unchanged `Store` protocol. |
| Borrowed read-only enforcement (allowlist + statement guard) | Storage adapter (`store/borrowed.py`) | — | Read-only-by-construction (the Phase-7 replay precedent), provable by test. |
| E-09 outcome reporting | Eval harness (`evals/`) | — | Consumes the existing `deferrals` fact; no new report field. |

## Standard Stack

**No new dependency.** This phase adds zero packages. That is a hard constraint (`09-CONTEXT`
domain note; `REQUIREMENTS.md` Out of Scope "Vector platform / heavy embedding stack";
`.planning/research/SUMMARY.md` "Capabilities 3 and 6 add ZERO new dependencies").

### Core (already pinned — do not change)
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pydantic` | 2.14.0 `[VERIFIED: pyproject.toml:13]` | The new `EvidenceResult`/`EvidencePassage` contracts | ONE schema module; reused by the tool, the node, and the checkpointer. |
| `pyyaml` | `>=6.0,<7` `[VERIFIED: pyproject.toml:14]` | Reads the corpus indirectly via `core/rules.py` | Never imported by `core/retrieval.py` (it reads through the loader, not YAML directly). |
| `langgraph` | 1.2.14 `[VERIFIED: pyproject.toml:9]` | The new `evidence` channel + `ground` node | No reducer needed (last-write-wins). |
| `mcp[cli]` | 2.3.0 `[VERIFIED: pyproject.toml:8]` | Registers the 7th owned tool | `MCPServer` v2, unchanged. |

### Explicitly NOT used (verified this session)
- `rank-bm25` — not in `pyproject.toml`; no `rank.?bm25|BM25` reference in `src/` `[VERIFIED: grep src/]`.
- `numpy`, `faiss`, `chromadb`, `sentence-transformers`, `torch`, embeddings — none in `pyproject.toml`
  `[VERIFIED: pyproject.toml:7-15]`; no non-comment reference in `src/`.
- `snowballstemmer` (suggested by earlier project research but **not** adopted) — would be a new
  dependency, forbidden here. Use the matcher's tokeniser; no stemming.

**Installation:** none. If any plan task proposes `uv add`, that task is wrong — stop it.

## Package Legitimacy Audit

> **Not applicable — this phase installs no external packages.** It adds code that reads existing
> data files and uses already-pinned libraries. The borrowed server (`mcp-sqlite@1.0.9`) is already
> pinned and unchanged `[VERIFIED: src/triagedesk/mcp/adapter.py:39 — BORROWED_SERVER_PACKAGE = "mcp-sqlite@1.0.9"]`.

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
 nurse note ──▶ ingest ──▶ normalize ──▶ retrieve ──▶ score ──┐
   (raw text)     │   (model: owned tool)  │  (matcher)  │  (scorer: ONLY colour) │
                  │                        └─ escalate   └─ request_missing_info │
                  │                                                              ▼
                  │                                                     ┌────────────────┐
                  │                                                     │  ground (NEW)  │  reads state.case.complaint
                  │                                                     │  → retrieve_   │  ──▶ retrieve_evidence tool
                  │                                                     │    evidence    │        │  (7th owned tool, read-only)
                  │                                                     └────────────────┘        ▼
                  │                                                              │        core/retrieval.py  (pure)
                  │                                                              ▼        corpus = data/*.yaml via
                  │                                                          verify ◀──┐   core/rules.py (ONE loader)
                  │                                                             │      │        │
                  │                                        (retry, bounded) ────┘      │        ▼ returns ONLY:
                  │                                                             │      │  EvidenceResult{ passages[
                  │                                                             ▼      │    {discriminator_id, label,
                  │                                                          recheck   │     citation, score, rank}],
                  │                                                             │      │    no_match, reason }  ← NO colour
                  │                                                          assess    │
                  │                                                             │      │   writes state.evidence
                  │                                                             ▼      │   (never priority/citations/
                  │                                       escalate ◀─ deferral ─ approval_gate ─▶ commit ─▶ handover
                  │                                                             │
                  ▼                                                             ▼
              END (terminals)                                        END / handover card
```

The `evidence` channel is a **sink**: written by `ground`, read by nothing that routes. The
scorer is still the only colour source; `citations == triggered_rules` is untouched.

### Recommended Project Structure (new/changed files)
```
src/triagedesk/
├── core/
│   ├── retrieval.py      # NEW — pure deterministic lexical retrieval over the closed KB
│   ├── schema.py         # MOD — EvidencePassage + EvidenceResult contracts
│   └── matcher.py        # MOD — promote the ONE tokeniser to a public `tokenize()`
├── graph/
│   ├── nodes.py          # MOD — the `ground` node factory
│   ├── state.py          # MOD — the `evidence` channel
│   └── build.py          # MOD — allowlist +1, TRACER_NODES +1, `score→ground→verify`
├── mcp/
│   └── server.py         # MOD — the 7th tool `retrieve_evidence`
└── store/
    └── borrowed.py       # MOD — read-path depth + tool allowlist + statement guard

tests/
├── test_retrieval.py         # NEW  — pure scorer: determinism, closed set, no-colour
├── test_graph_grounding.py   # NEW  — ground writes only `evidence`; routing-neutral
├── test_borrowed_store.py    # MOD  — read tools observed; mutation refused
├── test_observability.py     # MOD  — stdlib fake: real get_table_schema/read_records
├── conftest.py               # MOD  — build_graph_tools +1 fake
└── test_safety_spine.py      # MOD  — exact allowlist set 6 → 7
```

### Pattern 1: The ONE owned-tool allowlist — set equality at FOUR sites, ONE wave

**Source:** `src/triagedesk/graph/build.py::OWNED_TOOL_ALLOWLIST` and `assert_tool_allowlist`
`[VERIFIED: src/triagedesk/graph/build.py:66-91]`:

```python
OWNED_TOOL_ALLOWLIST: tuple[str, ...] = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "raise_recheck_flag",
    "assess_confidence",
    "commit_priority",
)
```
```python
def assert_tool_allowlist(tool_names: Iterable[str]) -> None:
    discovered = set(tool_names)
    expected = set(OWNED_TOOL_ALLOWLIST)
    missing = expected - discovered
    unexpected = discovered - expected
    if missing or unexpected:
        raise RuntimeError(...)
```

`build_graph` calls `assert_tool_allowlist(tools.keys())` first `[VERIFIED: src/triagedesk/graph/build.py:232]`,
and `load_graph_tools` asserts the *discovered* names at startup `[VERIFIED: src/triagedesk/graph/build.py:291]`.
**All four sites must change in the SAME wave:**
1. `src/triagedesk/graph/build.py::OWNED_TOOL_ALLOWLIST` (+`"retrieve_evidence"`).
2. `src/triagedesk/evals/tools.py::build_tools` return dict `[VERIFIED: src/triagedesk/evals/tools.py:131-138]`.
3. `tests/conftest.py::build_graph_tools` return dict `[VERIFIED: tests/conftest.py:209-216]`.
4. `tests/test_safety_spine.py::test_graph_startup_asserts_the_tool_allowlist` exact-set assertion
   `[VERIFIED: tests/test_safety_spine.py:190-197]`.

### Pattern 2: Extend the corpus and the score from the ONE loader (no re-authoring)

**Source:** `core/rules.py` `[VERIFIED: src/triagedesk/core/rules.py:86-135]` — `load_discriminators`/
`get_discriminators` (lru-cached) return `DiscriminatorRules{version, citation, categories, discriminators, no_match}`;
each `Discriminator{id, category, label, aliases}`; each `DiscriminatorCategory{colour, citation_ref}`.

The corpus is therefore: every `discriminator.id`, `.label`, `.aliases`, its `.category` string, and
the substrate `citation` + `no_match.warning` — all read through `get_discriminators()`.

### Pattern 3: The colour-free contract (prove unrepresentability, don't discourage)

Model on `ConfidenceResult` `[VERIFIED: src/triagedesk/core/schema.py:136-152]` — "There is deliberately
no percentage and no float `score`/`probability` field: a model-derived number is *unrepresentable*
rather than merely discouraged". The Phase-8 test proves this by iterating `model_fields`
`[VERIFIED: tests/test_confidence.py:88-101]`. Do the same for evidence: no `colour`, no `target`.

### Pattern 4: Pure core module + thin audited tool + thin node (the Phase-8 triple)

Exact mirror: `core/confidence.py` (pure) → `mcp/server.py::assess_confidence` (thin `@audited()` wrapper)
→ `graph/nodes.py::_make_assess` (thin node) → `graph/state.py` `confidence` channel → route.
`retrieve_evidence`/`ground`/`evidence` is the identical shape with **no** routing edge.

### Pattern 5: The ONE tokeniser (reuse, do not duplicate the normalisation)

**Source:** `core/matcher.py` `[VERIFIED: src/triagedesk/core/matcher.py:30-35]`:

```python
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    """Tokenise *text* into lower-case alphanumeric runs (the shared boundary rule)."""
    return _TOKEN_PATTERN.findall(text.lower())
```

D9 says "one normalisation owner". **Recommended (discretion):** promote this to a public
`tokenize(text) -> list[str]` in `core/matcher.py` (keep `_tokens` delegating to it, or make
`_tokens = tokenize`), then `core/retrieval.py` imports `tokenize`. This is a minimal, purely
additive, non-behavioural change to a **non-frozen** module (the frozen seams are the scorer
arithmetic, `core/citations.py`, and `@audited`'s behaviour). The alternative (a second tokeniser in
`retrieval.py`) is a DRY violation and will be caught at review.

### Anti-Patterns to Avoid
- **A second copy of discriminator text** (labels/aliases/citations) in code or a new YAML. The corpus
  is derived, not re-authored (D9-01). The `tests/test_no_duplicated_sats.py` gate scans every string
  literal under `src/` against the loaded data leaves `[VERIFIED: tests/test_no_duplicated_sats.py:147-162]`.
- **A colour field anywhere on the evidence contract** — it must be unrepresentable, not unused (D9-03).
- **Reusing retrieval to widen `matched_ids`.** That would move the scored colour and could flap
  `matched_set_stable`. Retrieval is post-score and writes only `evidence`.
- **Tuning E-09 green** by adding `"feeling unwell"` (or any) alias to the YAML, or lowering the match bar.
- **Sending a mutation through the borrowed `query` tool from a read path.** The guard fails closed.
- **Adding a `ground` conditional edge.** It is a plain edge; no router reads `evidence`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tokenisation / normalisation | A new regex/tokeniser in `retrieval.py` | `core/matcher.py::tokenize` (the ONE owner) | DRY: one normalisation owner (D9 discretion). |
| Citation string for an excerpt | Inline f-string / a new helper | `core.citations.format_citation(reference, source)` | The ONE citation helper; frozen — call it, never edit it. |
| Closed-set id constraint | A new id validator | Build passages *from* `get_discriminators().discriminators`; test membership | The matcher already owns id constraining `[VERIFIED: src/triagedesk/core/matcher.py:78-89]`; retrieval is closed by construction. |
| Schema/state types | New ad-hoc dicts | `core/schema.py` models | ONE schema module; checkpointer allowlist derives from it. |
| Ranking library (BM25) | `rank-bm25`/`bm25s` | Integer-weight overlap + deterministic tie-break | numpy-2 alias risk; new-dep ban (D9-02). |
| SQL statement safety | String-concatenated SQL | Parameterised `values` (existing) + statement guard | `upsert_queue_row` already parameterises `[VERIFIED: src/triagedesk/store/borrowed.py:221-240]`. |

**Key insight:** every hard part here already has a single owner in the repo. The phase is
*wiring + one small pure module*, not new infrastructure.

## Runtime State Inventory

> Not a rename/refactor/migration phase — omitted by design (greenfield additive code).

## Common Pitfalls

### Pitfall 1: The allowlist fan-out (HIGHEST RISK)
**What goes wrong:** adding `retrieve_evidence` to `OWNED_TOOL_ALLOWLIST` but lagging any of the other
three sites makes `build_graph` raise `RuntimeError` — the **whole suite** fails at composition, not one test.
**Why:** `assert_tool_allowlist` is set-equality over `missing`/`unexpected` `[VERIFIED: src/triagedesk/graph/build.py:76-91]`.
**How to avoid:** edit all four sites in ONE wave (allowlist, `evals/tools.py::build_tools`,
`tests/conftest.py::build_graph_tools`, `tests/test_safety_spine.py`).
**Warning signs:** `RuntimeError: owned tool surface drifted from the allowlist`.

### Pitfall 2: Retrieval non-determinism flapping `matched_set_stable`
**What goes wrong:** an embedding/ANN retriever returns a different top-k run-to-run; because the eval
treats any `matched_ids` variation as a hard failure, the suite becomes impossible to pass honestly
(`.planning/research/PITFALLS.md` Pitfall 4).
**How to avoid:** deterministic integer scoring with an explicit tie-break **on `(score desc, id asc)`**;
retrieval writes only `evidence`, never `matched_ids`. `matched_set_stable` is unaffected by construction.

### Pitfall 3: A stale `get_table_schema` fake breaks `ensure_schema`
**What goes wrong:** if `ensure_schema`'s `trace_id` migration check switches from `PRAGMA table_info`
(via `query`) to `get_table_schema`, the stdlib fake in `tests/test_observability.py` currently returns
`{"tableName": ...}` with **no columns** `[VERIFIED: tests/test_observability.py:99-101]`; the check would
then think `trace_id` is absent and issue the `ALTER TABLE`, which raises "duplicate column name".
**How to avoid:** update the stdlib fake's `get_table_schema` to return the real table's columns (it
already keeps a live `sqlite3` connection `[VERIFIED: tests/test_observability.py:75-93]`), or keep the
`PRAGMA` check and use `get_table_schema` only additively. Do both edits in the same wave.

### Pitfall 4: `read_records`/`get_table_schema` real wire shapes are unverified
**What goes wrong:** the hermetic fakes accept any args, so a wrong arg shape passes every test but
fails against the real `mcp-sqlite@1.0.9` server at demo time.
**Why:** the Phase-1 spike evidence only exercised `db_info` with `{}` `[VERIFIED: evidence/mcp-spike.json:37-47]`.
**How to avoid:** keep the read tools whose shapes *are* evidenced (`db_info{}`, `list_tables`, and the
`get_table_schema{tableName}` shape the fakes already assert) central, and treat a `read_records` call as
ASSUMED — surface it behind a human-verify checkpoint or a one-shot spike that dumps the borrowed server's
tool input schemas before relying on it in the recorded demo.

### Pitfall 5: E-09 "fixed" with an alias
**What goes wrong:** a well-meaning task adds `"feeling unwell"` (or similar) to the YAML to make E-09
pass. That tunes a declared failure green and hides a real coverage gap.
**How to avoid:** E-09's honest outcome is the existing absolute `no_match` deferral (D8-11); retrieval
on "feeling unwell" must return `no_match`. No fixture, threshold, or alias changes. `tests/test_eval_suite.py`
already asserts `E-09` = `["ABSTAIN"]*3` with `deferrals == [True]*3` `[VERIFIED: tests/test_eval_suite.py:96-104]`.

### Pitfall 6: Inlining a SATS literal
**What goes wrong:** a reason string or a test expectation hard-codes a colour/label/alias; the DRY guard
`tests/test_no_duplicated_sats.py` fails the build.
**How to avoid:** read every label/alias/colour/citation from `get_discriminators()`/`get_tews()`; in tests,
derive expectations from the loaders (as the existing suites do).

## Code Examples

### The grounded node (thin, writes ONLY `evidence`) — mirrors `_make_assess`
```python
# Source: shape copied from src/triagedesk/graph/nodes.py::_make_assess (VERIFIED: 196-216)
def _make_ground(tools: ToolMap) -> NodeFn:
    """Build the ``ground`` node over the injected tool mapping (D9-07)."""

    async def ground(state: TriageState) -> dict[str, Any]:
        """Fetch attributed KB excerpts for the complaint — no model, no write (D9-07)."""
        case = state["case"]
        result = parse_tool_result(
            EvidenceResult,
            await tools["retrieve_evidence"]({"complaint": case.complaint}),
        )
        return {"evidence": result}          # the ONLY key — never priority/citations/matched_ids/no_match

    return ground
```

### The colour-free contract (in `core/schema.py`)
```python
# Source: pattern mirrored from ConfidenceResult (VERIFIED: src/triagedesk/core/schema.py:136-152)
class EvidencePassage(BaseModel):
    discriminator_id: str          # ALWAYS a member of get_discriminators()
    label: str                     # the excerpt text, read from data — never inlined
    citation: str                  # format_citation(category.citation_ref, substrate.citation)
    score: int                     # deterministic lexical score (integer — no float/probability)
    rank: int                      # 1-based ordering position


class EvidenceResult(BaseModel):
    passages: list[EvidencePassage] = Field(default_factory=list)
    no_match: bool = False
    reason: str = ""
    # NO colour, target, priority, or citations field exists — a colour is unrepresentable.
```

### The read-only tool (thin `@audited()` wrapper)
```python
# Source: shape copied from server.assess_confidence (VERIFIED: src/triagedesk/mcp/server.py:207-223)
@server.tool()
@audited()
def retrieve_evidence(complaint: str) -> EvidenceResult:
    """Return attributed SATS KB excerpts for a complaint — read-only, no store (D9-06)."""
    return retrieval.retrieve(complaint)
```

### The statement guard (pure, fail-closed)
```python
# NEW in src/triagedesk/store/borrowed.py — no repo analog; classifier is in-house
_READ_PREFIXES = ("SELECT", "PRAGMA", "EXPLAIN", "WITH", "VALUES")

def is_read_only_statement(sql: str) -> bool:
    """True only for a statement whose leading keyword is read-only (fails closed)."""
    head = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    return head in _READ_PREFIXES     # anything else (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/...) → False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `FastMCP` (mcp v1) | `MCPServer` (mcp v2) | SDK v2 | Owned server import path; unchanged this phase. |
| `rank-bm25` lexical library | In-house integer scoring | this milestone | Zero new dep; no numpy-2 alias risk. |
| `sqlite3`-via-`query` for reads | Native borrowed read tools | this phase | MCP-01 depth; read-only allowlist. |
| Float "score" on a signal contract | Integer rank/score, no probability field | v1.1 (D8-04) | Evidence follows the same no-float posture. |

**Deprecated/outdated:**
- `langchain-mcp-adapters` (deprecated) — not used; World A `MCPAdapter` is the adapter.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The real `mcp-sqlite@1.0.9` `read_records` and `get_table_schema` input/return shapes match what the hermetic fakes tolerate (`get_table_schema` takes `{tableName}`; `read_records` takes a table + filters). | §5, Pitfall 4 | MCP-01 read-path calls fail against the real server at demo time; tests still pass (hermetic). Mitigate with a spike or a human-verify checkpoint. |
| A2 | Retrieval on E-09's complaint "feeling unwell" returns `no_match` under any reasonable lexical bar. | §6 | If a scorer is too loose, E-09 might spuriously "retrieve" something; the bar must be named and tested. Not a colour-setting risk (evidence is advisory), but an honesty risk if claimed as a fix. |
| A3 | Promoting `matcher._tokens` to a public `tokenize()` is acceptable (non-frozen module). | §1, Pattern 5 | If a reviewer treats `core/matcher.py` as frozen, the tokeniser must move to a neutral module; either way there is ONE owner. |
| A4 | The `ground` node re-running on the bounded `verify→score` retry is harmless (deterministic; same `evidence`). | §3 | If a test asserts node-span multiplicity across a retry, ground could emit two node spans; the slicing case is E-02, which does not retry. |

**If this table is empty:** not empty — A1 is the one that needs confirmation before the recorded demo.

## Open Questions (RESOLVED)

1. **Exact borrowed `read_records` argument shape.**
   - What we know: `db_info` takes `{}` and returns `{dbPath, exists, size, lastModified, tableCount}`
     `[VERIFIED: evidence/mcp-spike.json:37-47]`; the suite's fakes take `{tableName}` for `get_table_schema`.
   - What's unclear: `read_records`' required args (table? limit? where?) on `mcp-sqlite@1.0.9`.
   - Recommendation: dump the borrowed tools' input schemas once (the `MCPAdapter` exposes them) in a
     spike task, or keep `read_records` usage minimal and behind a human-verify checkpoint.

2. **Where to surface read-path depth.**
   - What we know: the discretion allows a startup probe, an explicit call, or a diagnostic command.
   - Recommendation: a **startup probe inside `ensure_schema`** (call `db_info` + `list_tables`; use
     `get_table_schema` for the `trace_id` column check). Fewest new surfaces; no new CLI command; keeps scope tight.

3. **Whether to render `evidence` in replay.**
   - Recommendation: no — Phase 10 renders it. `read_recorded` will include the channel automatically;
     `replay._render` can ignore it.

## Validation Architecture

> `workflow.nyquist_validation` is absent in `.planning/config.json` → treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode=auto) `[VERIFIED: pyproject.toml:18-22, 35-37]` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]}) |
| Quick run command | `uv run pytest tests/test_retrieval.py tests/test_graph_grounding.py tests/test_borrowed_store.py -x` |
| Full suite command | `uv run pytest` (baseline: **304 passing**) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-03 | Same complaint → identical ranked passages (determinism) | unit | `uv run pytest tests/test_retrieval.py -x` | ❌ Wave 0 |
| AGENT-03 | Every returned id ∈ `get_discriminators()`; no invented id | unit | `uv run pytest tests/test_retrieval.py -x` | ❌ Wave 0 |
| AGENT-03 | `EvidenceResult`/`EvidencePassage` have no colour/target field; serialised JSON carries no substrate colour token | unit | `uv run pytest tests/test_retrieval.py -x` | ❌ Wave 0 |
| AGENT-03 | `ground` return dict keys == `{"evidence"}`; priority/citations/matched_ids/no_match byte-identical with/without ground | unit + integration | `uv run pytest tests/test_graph_grounding.py -x` | ❌ Wave 0 |
| AGENT-03 | No conditional edge reads `evidence`; `score→ground→verify` present | structural | `uv run pytest tests/test_graph_grounding.py -x` | ❌ Wave 0 |
| AGENT-03 | E-09 → clean defer, queue untouched, no alias | integration | `uv run pytest tests/test_eval_suite.py tests/test_graph_confidence.py -x` | ✅ (existing, must stay green) |
| MCP-01 | Read tools (`db_info`/`list_tables`/`get_table_schema`/`read_records`) observed called | unit | `uv run pytest tests/test_borrowed_store.py -x` | ✅ (extend) |
| MCP-01 | A mutation via the read path is refused, fake never reached | unit | `uv run pytest tests/test_borrowed_store.py -x` | ✅ (extend) |
| MCP-01 | Unpermitted tool name raises (fail closed) | unit | `uv run pytest tests/test_borrowed_store.py -x` | ✅ (extend) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_retrieval.py tests/test_graph_grounding.py tests/test_borrowed_store.py tests/test_safety_spine.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** full suite green (≥ 304 + new) before `/gsd-verify-work`; the eval gate (`uv run triagedesk eval`) must still exit 0.

### Wave 0 Gaps
- [ ] `tests/test_retrieval.py` — covers AGENT-03 (determinism, closed set, no-colour contract).
- [ ] `tests/test_graph_grounding.py` — covers AGENT-03 (ground writes only `evidence`; routing-neutral).
- [ ] Extend `tests/test_borrowed_store.py` + update `tests/test_observability.py`'s stdlib fake — covers MCP-01.
- [ ] Framework install: none (pytest present).

## Security Domain

> `security_enforcement` is not `false` → included.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (unchanged; the gate is the auth boundary). |
| V3 Session Management | no | N/A. |
| V4 Access Control | yes | The owned-tool allowlist (set-equality) + the borrowed **tool allowlist** and **statement guard** (D9-12). Least privilege. |
| V5 Input Validation | yes | The complaint is untrusted free text `[VERIFIED: src/triagedesk/core/schema.py:51]`; retrieval tokenises it and never executes it. `EvidencePassage.discriminator_id` is closed-set by construction. |
| V6 Cryptography | no | N/A (no new crypto; the audit hash chain is untouched). |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection / unauthorised mutation through the borrowed `query` tool | Tampering / Elevation | Statement guard refuses any non-read statement on the read path, fail-closed; the write path stays behind the gated commit (D9-12/D9-13). |
| Prompt injection in the complaint steering retrieval | Tampering | Retrieval only tokenises and ranks closed-set ids; it never interprets text as instructions and never sets a colour. |
| Untrusted text leaking into a citation | Information disclosure | The citation is built from `data/*.yaml` (`citation_ref` + substrate `citation`), never from the complaint. |
| A fabricated discriminator id entering evidence | Spoofing | Passages are built *from* `get_discriminators()`; a membership test proves no id outside the set is produced (D9-10). |
| Non-deterministic retrieval destabilising a safety figure | Tampering | Integer scoring + `(score desc, id asc)` tie-break; `matched_ids` untouched (Pitfall 2). |

## Blast Radius (baseline 304 passing)

### A. Breaks if the allowlist grows to 7 but a site lags (all four move together — Pitfall 1)
- `src/triagedesk/graph/build.py::OWNED_TOOL_ALLOWLIST` `[VERIFIED: 66-73]`
- `src/triagedesk/evals/tools.py::build_tools` `[VERIFIED: 131-138]`
- `tests/conftest.py::build_graph_tools` `[VERIFIED: 209-216]`
- `tests/test_safety_spine.py::test_graph_startup_asserts_the_tool_allowlist` `[VERIFIED: 190-197]`

### B. Superset / membership enumerations — SAFE, no edit required
- `tests/test_graph_tracer.py::test_graph_compiles_with_the_tracer_node_set` — `missing = expected - node_names`
  `[VERIFIED: tests/test_graph_tracer.py:42-48]` (superset) → adding `ground` is safe.
- `tests/test_observability.py::test_node_spans_carry_the_content_trace_id` — `{...} <= set(names)` plus a
  uniqueness check `[VERIFIED: tests/test_observability.py:282-292]`. Adding `ground` adds exactly one more
  node name on E-02 (no retry); uniqueness holds.
- `tests/test_mcp_server.py` — `names >= {five}` `[VERIFIED: tests/test_mcp_server.py:33-39]` → safe.
- `tests/test_mcp_tools.py::test_commit_priority_is_listed_by_the_owned_server` — membership → safe.
- `tests/test_graph_durable.py::ONCE_PER_TOOL` `[VERIFIED: tests/test_graph_durable.py:51-56]` — asserts each
  *listed* tool ran exactly once (subset); `retrieve_evidence` is not listed → safe.
- `tests/test_demo.py::_ESCALATION_TOOLS` `[VERIFIED: tests/test_demo.py:26-32]` — asserts those five appear and
  `raise_recheck_flag` does not; `retrieve_evidence` now appearing does **not** break it. *Optional hygiene:*
  update the tuple/docstring (the escalation beat reaches six tools, not five).
- `tests/test_graph_durable.py::test_restart_...` / `test_graph_tracer.py::test_checkpoint_survives_...` —
  `snapshot.next == ("approval_gate",)` `[VERIFIED: tests/test_graph_durable.py:89, tests/test_graph_tracer.py:121]`
  — unaffected by a node inserted before `verify`.

### C. Breaks / needs edit when the read paths change
- `tests/test_observability.py::_SqliteBorrowedTools.get_table_schema`/`read_records` (currently stubs)
  `[VERIFIED: tests/test_observability.py:99-109]` — must return real columns / rows if `ensure_schema`
  or a read method switches to them (Pitfall 3).
- `tests/test_borrowed_store.py::_FakeBorrowedTools` `[VERIFIED: tests/test_borrowed_store.py:41-93]` — extend
  with assertions that read tools were called; ensure its `query` still executes DDL (used by `ensure_schema`).

### D. Not affected
- `tests/test_no_duplicated_sats.py` — stays green **iff** no SATS literal is inlined.
- `tests/test_purity.py` — auto-covers the new `core/retrieval.py` (parametrised over `core/*.py`
  `[VERIFIED: tests/test_purity.py:89-92]`).
- `tests/test_eval_suite.py` / `test_graph_confidence.py` — E-09's deferral behaviour is unchanged
  (retrieval is advisory; no routing edge reads `evidence`).
- `tests/test_replay_read_only.py` — replay reads `channel_values` generically; an extra `evidence`
  channel is inert to `_render` `[VERIFIED: src/triagedesk/replay.py:78-124]`.

### E. New risk: the `verify→score` retry re-runs `ground`
`route_after_verify` returns `"score"` on a failed check `[VERIFIED: src/triagedesk/graph/build.py:175-186]`,
so a sliced case would run `ground` twice (two node spans, two `retrieve_evidence` audit records). Deterministic
and harmless; only E-12 slices, and no test asserts `retrieve_evidence` multiplicity. Note it in the plan.
If a plan prefers a single run, place `ground` on the success arm (`verify --ok--> ground --> recheck`) instead —
still "after `score`" and still routing-neutral.

## Sources

### Primary (HIGH confidence — read this session)
- `src/triagedesk/graph/build.py` — `OWNED_TOOL_ALLOWLIST` (:66-73), `assert_tool_allowlist` (:76-91),
  `TRACER_NODES` (:97-110), `build_graph` edges (:238-275), `_allowed_msgpack_modules` (:346-359).
- `src/triagedesk/graph/nodes.py` — `make_nodes` (:393-413), `parse_tool_result` (:64-81), `_make_assess` (:196-216).
- `src/triagedesk/graph/state.py` — `TriageState` channels (:26-57).
- `src/triagedesk/core/schema.py` — `ConfidenceResult` no-float contract (:136-152), `CaseInput.complaint` (:51).
- `src/triagedesk/core/rules.py` — the ONE loader (:86-135).
- `src/triagedesk/core/matcher.py` — the ONE tokeniser (:30-35), `validate_discriminator_ids` (:78-89).
- `src/triagedesk/core/confidence.py` — the pure-core pattern (:1-196).
- `src/triagedesk/core/citations.py` — `format_citation(reference, source)` (:28-38).
- `src/triagedesk/mcp/server.py` — `@audited` (:92-167), tools (:170-296).
- `src/triagedesk/store/borrowed.py` — read-tool constants (:29-36), `EXPECTED_TOOLS` (:38-47), `BorrowedStore` (:150-344).
- `src/triagedesk/store/__init__.py` — the `Store` protocol (:64-119).
- `data/sats_discriminators.yaml` — corpus shape (:1-208).
- `evals/cases/E-09.yaml` — the declared failure (:1-27).
- `tests/test_safety_spine.py`, `tests/conftest.py`, `tests/test_borrowed_store.py`, `tests/test_observability.py`,
  `tests/test_graph_tracer.py`, `tests/test_graph_confidence.py`, `tests/test_eval_suite.py`, `tests/test_purity.py`,
  `tests/test_no_duplicated_sats.py`, `tests/test_graph_durable.py`, `tests/test_demo.py` — the blast-radius evidence.
- `.planning/phases/08-calibrated-confidence-abstention/08-CONTEXT.md`, `08-PATTERNS.md` — the node/tool/allowlist precedent.

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` §4.1, `.planning/research/PITFALLS.md` Pitfall 4, `.planning/research/SUMMARY.md` — prior design context (note: prior research proposed `core/grounding.py`; CONTEXT D9-04 overrides to `core/retrieval.py`).
- `evidence/mcp-spike.json` — the borrowed handshake (`db_info` shape only).

### Tertiary (LOW confidence)
- The real `read_records`/`get_table_schema` wire shapes for `mcp-sqlite@1.0.9` — **ASSUMED** (A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against `pyproject.toml`; zero new deps confirmed.
- Architecture: HIGH — every seam read this session; the additive node/tool/channel pattern has a direct precedent (Phase 8).
- Borrowed-MCP wire shapes: MEDIUM/LOW — hermetic fakes mask the real arg shapes (A1).
- Pitfalls: HIGH — the allowlist fan-out and the DRY gate are mechanically enforced by existing tests.

**Research date:** 2026-10-13
**Valid until:** 2026-10-15 (deadline; repo frozen at `v1.0-submission` + v1.1 phases 6–8).
