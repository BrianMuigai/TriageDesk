# Phase 1: SATS Foundations & Risk Retirement - Context

**Gathered:** 2026-10-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the **SATS rule substrate** (data), **one typed case schema**, a **reproducible `uv` scaffold**,
and **evidence** retiring the two Day-1 unknowns — the local model's schema-constrained output and the
MCP beta-adapter / borrowed-server handshake.

Explicitly NOT in this phase: the deterministic scorer and owned tools (Phase 2), the graph / gate /
audit (Phase 3), evaluation (Phase 4), demo & freeze (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Model & extraction contract
- **D-01:** Primary local model = **`qwen3.5:4b`** (already installed, 3.3 GB). Phase 1 must **measure**
  that it runs within the demo machine's RAM budget; a **smaller Qwen fallback is documented and used if
  it cannot**. Record the model licence. — **Reversibility:** reversible — a model swap is a config
  change behind the `llm/` wrapper (SOLID: D), not a code change.
- **D-02:** Extraction contract = **strict JSON schema** via Ollama `format=` + Pydantic validation, from
  the one shared schema module. Not free-form parsing, not native tool-calling.
- **D-03:** Model authority = structure the note, **select discriminators from a closed set**, draft the
  rationale. It **never** does arithmetic, routing, or the colour.

### MCP strategy & borrowed server
- **D-04:** Adopt **World A** (`langchain.mcp.MCPAdapter`) behind the Phase-1 spike; keep **World B**
  (pinned `langchain-mcp-adapters` + `mcp<2`) as a documented **one-module** fallback. — **Reversibility:**
  costly — swapping worlds touches the MCP wiring module and dependency pins, but is contained by the
  tool-interface boundary.
- **D-05:** Borrowed server = **`jparkerweb/mcp-sqlite`** (npm, **pinned version**); `rusq/mcp-sqlite`
  (Go) is the read-only-posture alternative.
- **D-06:** The gated write goes through **our** `commit_priority`; the borrowed server is **storage**,
  the gate is ours.
- **D-07:** "Retired" evidence bar = committed spike evidence showing **tool-list + one tool call on
  BOTH the owned and borrowed servers**, plus a **RAM measurement** that selects the model.

### SATS data encoding
- **D-08:** Two files — `data/sats_tews.yaml` + `data/sats_discriminators.yaml` — the single source of truth.
- **D-09:** Encode the **adult chart only**; paediatric = **fail-closed abstain stub**.
- **D-10:** Verification = **dual independent transcription diff** + **band-edge unit tests**; residual
  uncertainty flagged in `docs/SATS.md`.
- **D-11:** Discriminator matching = **deterministic alias lookup in YAML with an explicit "no match"**;
  no embeddings in v1.

### Module boundaries & DRY/SOLID
- **D-12:** Layout: `core/` (pure: schema, scorer, citations) · `llm/` · `mcp/` · `store/` · `graph/`.
- **D-13:** **Guard test**: `core/` must not import `llm|mcp|store` — enforced by an AST test + ruff; CI
  fails on violation (QUAL-02). — **Reversibility:** one-way — the purity boundary is a published
  contract other phases build on; breaking it silently would let the score path depend on the model.
- **D-14:** One Pydantic schema module, imported by MCP contracts, the Ollama `format=`, and graph state.
- **D-15:** Citation helper lives in `core/`, used by every priority.

### the agent's Discretion
- YAML key naming/shape; test framework specifics; spike transcript format; exact pinned versions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engineering standard (iron-clad)
- `CONVENTIONS.md` — DRY + SOLID; single-source-of-truth table; enforcement gates.
- `AGENTS.md` — iron-clad rule (top block) + full stack research.

### Domain
- `docs/SATS.md` — SATS process, adult TEWS bands, colours, discriminators (verify-flagged).
- `.planning/research/PITFALLS.md` — pitfall→phase map (P1–P17); Phase 1 owns P5, P11, P13, P15.
- `.planning/research/STACK.md` — pinned versions, World A/B, model sizing.
- `.planning/research/SUMMARY.md` — phase structure rationale.

### Challenge compliance
- `REQUIREMENTS.md` — challenge compliance & traceability (BW-3, BW-5, DC-1, EL-3).
- `.planning/REQUIREMENTS.md` — INTAKE-01/02/04/05, SAFE-04, QUAL-01.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — greenfield. The repository currently holds design and planning documents only.

### Established Patterns
- The design docs + `CONVENTIONS.md` establish the intended layering; Phase 1 is where it becomes real.

### Integration Points
- `data/*.yaml` and the schema module are the interfaces every later phase consumes.

</code_context>

<specifics>
## Specific Ideas

- **Reuse the installed `qwen3.5:4b`**; do not pull a new model unless the RAM measurement fails.
- DRY + SOLID is iron-clad; the purity guard (`core/` ↛ `llm`/`mcp`) is a first-class deliverable, not a nicety.

</specifics>

<deferred>
## Deferred Ideas

- Discriminator confidence field + clarifying-question loop (the E-09 fix) — v2.
- Embedding-based discriminator retrieval — v2.
- Referral / department routing tool — v2.
- "Additional investigations" column + SHCP discretion — v2.
- Multilingual clinical lexicon — v2.
- Paediatric SATS charts — v2.

</deferred>

---

*Phase: 1-SATS Foundations & Risk Retirement*
*Context gathered: 2026-10-09*
