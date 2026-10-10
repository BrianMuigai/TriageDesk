# Project Research Summary

**Project:** TriageDesk — milestone **v1.1 "Score Uplift"**
**Domain:** Agentic clinical triage-support tool (SATS-grounded, MCP + LangGraph, human-gated queue write, offline, synthetic-only)
**Researched:** 2026-10-10
**Confidence:** HIGH (stack, architecture, pitfalls — read from the frozen v1.0 tree and cross-checked against the installed `.venv`); MEDIUM (external clinical/agent-engineering best-practice claims)

## Executive Summary

This milestone is **additive engineering onto a frozen, already-shipped safety spine** (tag `v1.0-submission`), not a greenfield build. v1.0's colour is produced in exactly one pure, data-driven place (`core/scorer.py::score_priority`, `citations == triggered_rules`), the human gate is structural (`approval_gate` is side-effect-free before `interrupt()`; `commit` is the only queue-writing node reachable solely through the resumed interrupt), and there is one audit path (`mcp/server.py::audited` → `store/audit.py`). The seven new capabilities (RAG grounding, calibrated confidence + abstention, durable checkpoints E2E, span tracing + replay, desk UX + real approve/edit/dismiss gate, deeper borrowed-SQLite-MCP use, live rule-extensibility, plus docs/eval reconciliation) must all attach **at a published seam** — a new node, a new tool, a new schema contract, or a new adapter *behind an existing protocol* — and must never edit the scorer, the citation helper, or the audit interceptor. The research is emphatic and consistent across all four files: **the milestone's entire risk is a new path that bypasses an existing invariant.**

The strongest practical finding is that **most of what v1.1 needs is already in the venv**. Capabilities 3 (durable checkpoints) and 6 (borrowed MCP depth) add **ZERO new dependencies** — `langgraph-checkpoint-sqlite==3.1.1` + `AsyncSqliteSaver` and all 8 borrowed tool names are already present, only the *callers* need swapping. Capability 5 needs only `rich==15.0.0` **promoted from transitive to a direct pin** (no resolved version change). Capability 4 tracing adds the minimal `opentelemetry-sdk==1.45.1` (its `opentelemetry-api==1.45.1` is already pulled in by `mcp==2.3.0`). RAG should be **lexical-first (in-house BM25/TF-IDF + `snowballstemmer`)** with optional local Ollama embeddings — a 41-doc KB does not warrant a vector platform. Calibration runtime adds **nothing** (a pure `core/confidence.py` + a frozen `data/calibration.json`), with `scikit-learn` as a **dev-only** fitter. Tracing must be **local-only** (OTLP-JSON-file exporter or a ~40-line in-house JSONL exporter); LangSmith cloud is a hard **do-not-enable** (egress).

Two cross-cutting blockers dominate the milestone and both are pre-existing v1.0 warnings that v1.1 makes *reachable*. **First, the idempotency-key breadth bug:** the commit key covers **`colour` only**, so once a real **edit** decision is live, a same-`case_id` edit writes a *second queue row* — the exact corruption the gate exists to prevent. It must be widened to the immutable case content it was always meant to cover (`IMMUTABLE_FIELDS`) or keyed on `(case_id, decision_id)`. **Second, replay must be read-only:** if "replay" feeds recorded inputs back through the live graph it **re-executes `commit_priority`** — a second queue write and second audit record disguised as observability. Replay must reconstruct from the checkpoint + audit/span event stream, or run with the commit tool structurally unreachable (an injected tool map with no `commit_priority`). Both blockers are HIGH-severity and must be retired early.

## Key Findings

### Recommended Stack

The stack is **mostly already installed**. Add nothing for durable checkpoints or borrowed-MCP depth; promote `rich`; add `opentelemetry-sdk`, one local span exporter, and `snowballstemmer`; keep `scikit-learn` dev-only. **Do not** add vector platforms (chromadb/faiss/qdrant/lancedb/LlamaIndex/txtai), `sentence-transformers`/`torch`, LangSmith cloud tracing, `langgraph-checkpoint-postgres`, a runtime ML stack, or a web UI. The v1.0 World A/B MCP decision, LangGraph, Ollama/Qwen, Pydantic, the borrowed `mcp-sqlite@1.0.9`, and the hash-chained audit are all frozen and unchanged.

**Core technologies (new/changed only):**
- **`opentelemetry-sdk==1.45.1`** — tracing engine (cap 4); pairs with the already-installed `opentelemetry-api==1.45.1`, zero additional API surface
- **`opentelemetry-exporter-otlp-json-file==0.66b1`** (or ~40-line in-house JSONL `SpanExporter`) — writes spans to a local file, **no collector, no network** (*beta — spike*)
- **`rich==15.0.0`** — promote transitive → direct pin for the priority card + vitals entry (cap 5); no version change
- **`snowballstemmer==3.1.1`** — deterministic stemming for the in-house lexical retriever (cap 1)
- **In-house BM25/TF-IDF scorer** — primary retriever over ~41 discriminators; zero new runtime dep; deterministic/offline (*optional* semantic rerank via existing Ollama `nomic-embed-text`, 274 MB, or `all-minilm`, 46 MB)
- **`scikit-learn==1.9.1`** (**dev-only**) — fit/measure calibration offline; runtime ships only the frozen `data/calibration.json`
- **Runtime unchanged for cap 2/3/6** — pure `core/confidence.py`; `langgraph-checkpoint-sqlite==3.1.1` + `AsyncSqliteSaver`; borrowed tools already declared in `store/borrowed.py`

### Expected Features

The eight feature sections map almost one-to-one onto the five things a trustworthy 2026 triage agent is expected to do: ground every claim in an attributable source (a); know and *say* when it does not know (b); keep the human the actor (c); survive audit (d); fit the workflow (e).

**Must have (P1 — the milestone minimum):**
- **Real approve/edit/dismiss prompt** with a named approver — closes the hardcoded-approval gap (U2); no new deps
- **Human-readable priority card** — colour + target time + "why" vitals + adjacent citations, framed **"SUGGESTED" not a verdict**; the biggest "fit to desk" mover (U1)
- **Loud "no discriminator matched / low confidence — nurse to confirm" banner** + a typed uncertainty field that **drives routing** (U4) — turns the E-09 class into a visible flag
- **Durable checkpoints wired E2E** — already ~80% built; exercise `checkpointed_graph` in the demo/CLI path
- **Live YAML rule + re-score rehearsal** — cheapest, most directly-scored Stage-2 item (ST-1)

**Should have (P2 — capability upgrades):**
- **Retrieval-grounded RAG (hybrid, thresholded)** — the honest fix to declared failure E-09; must be a real retrieval gain, not a keyword patch; re-run the suite and either pass or cleanly defer
- **Selective-prediction reporting** — coverage vs under-triage on the eval set (not just point accuracy)
- **Span tracing + replay** — local spans, replay from checkpoint (never re-running the model)

**Defer (P3):**
- Second borrowed MCP server (vector KB) for retrieval; online eval/drift monitoring; model routing/caching for the 14–17 s latency (U3); multimodal intake (voice/cuff photo)

**Anti-features (do NOT build):** generative RAG that writes guidance prose; any pseudo-probability shown as clinical risk ("87% sure this is ORANGE"); decorative confidence that never changes routing; default-yes/single-OK gate or auto-commit on timeout; auto-low-acuity colour when nothing matches (this *is* E-09); cloud tracing or replay that re-runs the model; one DB for checkpoints + audit; editing code (or `docs/SATS.md`) to add a rule; adding a literal alias to "pass" E-09.

### Architecture Approach

The architecture is a **frozen spine plus additive seams**. The single-line thesis: every capability is a **new node, new tool, new contract, or adapter behind an existing protocol** — none edits the scorer, the citation helper, or the audit interceptor, and none adds an edge to `commit`. Exactly **two new owned tools** (`retrieve_evidence`, `assess_confidence`), **one new advisory `ground` node** (placed *after* `score`, so retrieval structurally cannot set a colour), **one pure KB module** (`core/grounding.py`), **one pure confidence module** (`core/confidence.py`), and **one new `desk/` package** (a *peer* of `demo/run.py`, not inside the graph).

**Major components (new/changed):**
1. **`ground` node + `retrieve_evidence` tool** — fetch attributed KB excerpts for already-scored ids; writes a separate `evidence` channel; never touches `priority`/`citations`
2. **`core/confidence.py` + `assess_confidence` tool + `verify`-node signal + one conditional edge** — deterministic features (vitals coverage, discriminator coverage, override-vs-TEWS path, TEWS distance from band edge) → score via `data/confidence.yaml`; abstention is **routing to `escalate`, never to `commit`**
3. **Durable checkpoints** — swap entry points to `checkpointed_graph`; stable `thread_id == case_id_for(raw_note)`; keep `checkpoints.db` separate from `triage.db`
4. **`Tracer`** — emitted from the **existing** `audited()` interceptor + node wrapper + `llm/client.extract`; local OTLP/JSONL only; `trace_id` added to `AuditRecord`
5. **`desk/` adapter** — consumes only the typed interrupt payload + terminal channels; renders from the locked `HandoverCard`; real approve/edit/dismiss via `Command(resume=...)`
6. **`store/borrowed.py`** (MOD) — exercise `list_tables`/`get_table_schema`/`read_records`/`db_info` behind the unchanged `Store` protocol; **keep raw `query` for idempotent upserts** until duplicate-key semantics are proven
7. **`core/rules.py::reload()`** — clears the one lru_cache so a live YAML edit takes effect

### Critical Pitfalls

The dangerous class in an additive milestone is **a new path that bypasses an existing invariant**. Top pitfalls (of 15) and their guards:

1. **The idempotency-key breadth bug becomes reachable** — the commit key covers `colour` only, so a live **edit** writes a *second queue row*. Widen the key to `IMMUTABLE_FIELDS` / `(case_id, decision_id)`; test an edit-resume yields **one updated row, not two**; assert approved artefact == committed artefact. *(HIGH — pre-existing warning, now reachable)*
2. **Replay re-executes the gated commit** — feeding recorded inputs back through the live graph re-runs `commit_priority`; a duplicate record *verifies* (append-only) and an edit-replay adds a genuinely different row. Make replay read-only by construction (reconstruct from checkpoint + audit/span stream, or inject a no-op commit tool with no `commit_priority`); assert zero rows/zero commits and replayed colour == original. *(HIGH)*
3. **RAG becomes a second colour path** — retrieval must return **only** closed-set ids + a rank + explicit `no_match` (the `MatchResult` contract); the scorer remains the sole colour producer; guard test: no retrieved value may be a colour token or a non-declared id. *(HIGH)*
4. **Durable resume re-runs side effects** — `interrupt()` **replays the node from the top**, so any pre-interrupt log/append fires twice. Keep `approval_gate` side-effect-free before `interrupt()` (make it a test, not a comment); validate the resume payload with a typed schema; E2E test asserts exactly one `commit_priority` record + one queue row. *(HIGH)*
5. **Confidence hides the dangerous case** — a high-confidence value on a no-match case is worse than no confidence; and a percentage invites over-trust. Confidence is a **deterministic coverage/deferral signal that can only make the system more cautious**, never a model logit, never a percentage, never a colour downgrade. Calibrate offline on a held-out split; report ECE + risk–coverage; also guard against **abstain-too-often** (alert fatigue) by tuning the threshold to a stated asymmetric cost and reporting the deferral rate. *(MEDIUM–HIGH)*
6. **Un-gated borrowed-MCP write** — keep the borrowed server **read-only in the agent path**; exercise it beyond `query` with its read tools only; add a tool allowlist + statement guard. *(MEDIUM–HIGH)*
7. **DRY/SOLID erosion** (all phases) — hold the OCP test: *"added as data or new tool+node, working code untouched?"* Keep `test_purity` / `test_no_duplicated_sats` / `test_graph_purity` green.

## Implications for Roadmap

Based on the combined research (and directly mirroring ARCHITECTURE.md §7's build order and PITFALLS.md's phase map), the milestone should be structured to **front-load the two spirit-level risks** — the durable-gate lifecycle and the idempotency breadth — then land the pure/additive capabilities, and consume them last in the UX surface. Capability labels are stable; the roadmapper re-maps to its own phase numbers.

### Phase 1: Durable checkpoints E2E + interactivity prerequisite (P-Ckpt)
**Rationale:** The durable gate is the capability most entangled with the safety spine and changes *where the gate lives in time*; everything on the resume/replay path builds on it. The two HIGH blockers (idempotency breadth, resume side-effects) live here.
**Delivers:** demo/CLI routed through `checkpointed_graph`; stable `thread_id == case_id_for(raw_note)`; `--durable` mode; a documented resume CLI subcommand; **widened idempotency key** (edit supersedes, not duplicates); E2E restart-between-pause-and-resume test.
**Addresses:** cap 3; enables the real gate (cap 5) and replay (cap 4).
**Avoids:** Pitfall 8 (duplicate side effects on resume), Pitfall 9 (wrong-thread / key-breadth edit duplicate).

### Phase 2: Calibrated confidence + abstention (P-Eval)
**Rationale:** Pure and independent; retires the honesty gap and provides the signal the UX banner and gate consume. Low spine risk (pure function). Pairs with fixing E-04/E-07 and re-running the suite.
**Delivers:** `core/confidence.py` + `data/calibration.json` (frozen) + `assess_confidence` tool + `verify`-node signal + abstention edge (routes to `escalate`/`request_missing_info`, **never `commit`**); offline fit with dev-only `scikit-learn`; ECE/reliability + risk–coverage reporting; deferral-rate reporting.
**Uses:** `scikit-learn==1.9.1` (dev-only), pure core pattern.
**Avoids:** Pitfall 5 (overconfident/hidden dangerous case), Pitfall 6 (abstain-too-often).

### Phase 3: Span tracing + replay (P-Trace)
**Rationale:** Rides on Phase 1 for state replay; read-only observability, off the critical path, can be retied early without touching the scored path.
**Delivers:** one `Tracer` emitted from the existing `audited()` interceptor + node wrapper + `llm/extract`; `trace_id` on `AuditRecord`; local OTLP-JSON-file or in-house JSONL exporter; **read-only replay** with commit structurally unreachable.
**Uses:** `opentelemetry-sdk==1.45.1`; keep LANGCHAIN_TRACING/LANGSMITH unset.
**Avoids:** Pitfall 10 (second/divergent/leaking/bloating log), Pitfall 14 (replay re-commits).

### Phase 4: RAG grounding over the SATS KB (P-RAG)
**Rationale:** The honest E-09 fix; pure/additive and placed *after* `score` so it structurally cannot set a colour. Engine choice is the risk (lexical vs local embedding under the RAM budget).
**Delivers:** `core/grounding.py` (KB index from existing `data/*.yaml`, not a copy) + `retrieve_evidence` tool + `ground` node + `evidence` channel; in-house lexical BM25 with `snowballstemmer`; optional local Ollama semantic rerank (pinned/hashed).
**Uses:** `snowballstemmer==3.1.1`; optional existing Ollama embeddings.
**Avoids:** Pitfall 1 (second colour path), Pitfall 2 (deceptive grounding), Pitfall 3 (E-09 tuned green), Pitfall 4 (non-deterministic retrieval).

### Phase 5: Desk UX + real gate (P-Gate / P-UX)
**Rationale:** Consumes the pull of Phases 1, 2, 4 (payload, confidence, evidence); it is an adapter, so it lands last among the builders. Wraps the milestone's two human surfaces — both automation-bias surfaces.
**Delivers:** `desk/` package; typed `ApprovalRequest` (frozen view model); priority card rendering from the locked `HandoverCard`; confidence/no-match banner; evidence excerpts; real approve/edit/dismiss interaction (no default approve; edit/dismiss one action away); vitals entry validating through the same schema; override-rate reporting.
**Addresses:** cap 5 / U1–U5.
**Avoids:** Pitfall 7 (rubber-stamp gate), Pitfall 11 (colour without citations / diagnosis creep / over-trust).

### Phase 6: Deeper borrowed-SQLite-MCP usage (P-MCP)
**Rationale:** Confined to one module behind the unchanged `Store` protocol; independent and parallelisable; only threatens idempotency, so **spike duplicate-key semantics first**.
**Delivers:** read paths via `read_records`/`list_tables`/`get_table_schema` + `db_info` startup health-check; borrowed-tool allowlist + statement guard; read-only borrowed posture in the agent path.
**Avoids:** Pitfall 15 (un-gated borrowed write).

### Phase 7: Live rule-extensibility rehearsal (P-Live)
**Rationale:** A rehearsal, not a build; cheapest, highest value-per-effort for ST-1; data-only and independent.
**Delivers:** `core/rules.py::reload()`; loader validator (fails closed on duplicate ids / alias collision / undeclared category / a rule producing no citation); versioned + hashed ruleset recorded in the audit; a documented one-line edit + post-edit safety-suite re-run.
**Avoids:** Pitfall 12 (live edit silently breaks an invariant), Pitfall 3 (live edit must not tune E-09 green).

### Phase 8: Docs & rigour reconciliation (P-Docs)
**Rationale:** Close the honesty loop — regenerate `EVALS.md` **only** from `report.json` (never hand-edit the 14-vs-16 count), one-command README, re-declare E-09 honestly. Runs alongside/concluding the suite re-run.
**Delivers:** reconciled EVALS.md + README; E-09 result + held-out vague-case results reported together; commit/demo refresh + freeze discipline.

### Phase Ordering Rationale

- **Dependencies drive order:** durable checkpoints (1) → confidence (2) → tracing (3, replay rides on 1) → RAG (4) → UX (5, consumes 1/2/4). Steps 2/3/4 are pure or additive and can be retired without touching the scored path; step 6 is confined to one module; step 7 is a rehearsal.
- **Critical path:** **1 → 2 → 4 → 5.** Phase 3 and Phase 6 are independent and parallelisable. Phase 1 is the must-not-slip item.
- **Front-loads the HIGH blockers:** the durable-gate lifecycle (Pitfall 8/9/14) and the borrowed idempotency unknown (Pitfall 15) — both can invalidate the whole milestone if deferred.
- **Grouping mirrors the architecture:** pure-core additions (`confidence.py`, `grounding.py`) ship before the adapter that renders them; data-only extensibility ships independently; docs honesty closes the loop.
- **Anti-pattern guardrails are structural, not conditional:** research explicitly warns against conditional branches *inside* nodes (e.g. a `commit`-skip flag); the correct form is an injected tool map that structurally cannot reach the side-effect.

### Research Flags

Phases likely needing deeper research during planning (`--research-phase`):
- **Phase 1 (Durable checkpoints):** HIGH-risk interaction of `AsyncSqliteSaver` + `interrupt()` across process restarts, `thread_id` stability, resume-payload schema validation (LangGraph `>=1.2.12`), and checkpoint-file versioning on schema drift.
- **Phase 3 (Tracing):** OTel-without-egress mechanics; the OTLP-JSON-file exporter is **beta** (in-house JSONL fallback); auto-instrumentation (`openinference`) has a `langchain-core` drift risk — default to manual spans.
- **Phase 4 (RAG):** retrieval-engine spike — in-house lexical BM25 sufficiency for E-09, `rank-bm25==0.2.2` numpy-2 alias risk, and RAM measurement (`ollama ps`) if the embedding model is used alongside the extractor.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Confidence):** pure function + frozen data table; the pattern mirrors existing SATS rules; only calibration *quality* needs tuning, not research.
- **Phase 6 (Borrowed MCP):** tools already declared as data; the change is behind an unchanged protocol (just spike duplicate-key semantics).
- **Phase 7 (Live rule edit):** already the design; one cache-clear function (+ a loader validator).
- **Phase 8 (Docs):** mechanical reconciliation from `report.json`.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Every version is PyPI-registry JSON cross-checked against the *installed* `.venv` (the versions are literally present). MEDIUM only on two beta/optional items — the OTLP-JSON-file exporter (beta) and LangChain auto-instrumentation — both flagged "retire in a spike". `uv` is already 0.12.24 (the v1.0 "upgrade uv" flag is stale). |
| Features | **MEDIUM–HIGH** | The frozen v1.0 implementation + docs were read directly (HIGH); external best-practice claims are web-search (LOW→MEDIUM where official/peer-reviewed agree). Prioritisation (P1/P2/P3) is well-supported and mapped to JC/ST/U criteria. |
| Architecture | **HIGH** for integration design | Derived from the frozen v1.0 source tree read line-by-line (the seams are actual file locations); MEDIUM for LangGraph checkpointer / OTel mechanics (official docs) and for RAG engine choice (community consensus). |
| Pitfalls | **HIGH** for project-specific | Derived from the frozen source, the v1.0 milestone audit, and root design docs; MEDIUM for clinical/agent-engineering generalities (peer-reviewed + official docs). The two cross-cutting blockers are pre-existing v1.0 warnings, now reachable. |

**Overall confidence:** **HIGH**

### Gaps to Address

- **Idempotency-key breadth (HIGH, blocking):** the shipped key covers `colour` only — widen to `IMMUTABLE_FIELDS` / `(case_id, decision_id)` and prove edit-supersede-not-duplicate in Phase 1 before the real gate is live.
- **Replay read-only guarantee (HIGH, blocking):** enforce by construction (no-op commit injection / event-stream reconstruction); assert zero rows + zero commits in Phase 3.
- **RAG engine sufficiency for E-09:** lexical BM25 + stemming should surface `diabetic_*` from "known diabetic", but is **not guaranteed** — measure in a Phase-4 spike; escalate to a local Ollama semantic rerank only if it still misses. Author **held-out vague cases** that are never iterated against, so the E-09 fix proves generalisation, not tuning.
- **`rank-bm25==0.2.2` under numpy 2.x:** unmaintained since 2022; numpy 2.0 removed legacy aliases. Spike import+index+query, or use the in-house scorer (recommended, zero-dep).
- **OTLP-JSON-file exporter is beta (0.66b1):** have the ~40-line in-house JSONL `SpanExporter` ready as the zero-risk fallback.
- **Embedding model RAM fit:** two models resident could pressure the ~2.3 GB headroom; load embeddings *after* the extractor unloads (`keep_alive=0`); `all-minilm` (46 MB) is the escape hatch. Default to lexical (no model) for the offline golden path.
- **Calibration at 14 cases:** ECE/reliability is a declared, small-sample measure — report it as such rather than claiming precision; the threshold must derive from a stated asymmetric cost, not a hand-picked 0.5.
- **Clinician interview (G2) and the still-terminal surface:** cannot be fixed by these capabilities; the honest fit-to-desk estimate should rise from ~7–12/20 toward the low-to-mid teens but remains capped. Declare these gaps rather than over-claim.
- **Docs honesty:** `EVALS.md` must be regenerated from `report.json` (sole writer); never hand-edit the 14-vs-16 count.

## Sources

### Primary (HIGH confidence)
- **PyPI registry JSON** (`https://pypi.org/pypi/<pkg>/json`) cross-checked against the installed `.venv` — exact versions for `opentelemetry-sdk` 1.45.1, `opentelemetry-api` 1.45.1, `opentelemetry-exporter-otlp-json-file` 0.66b1, `rich` 15.0.0, `textual` 8.2.8, `scikit-learn` 1.9.1, `numpy` 2.5.3, `rapidfuzz` 3.14.6, `rank-bm25` 0.2.2, `bm25s` 0.3.13, `snowballstemmer` 3.1.1, `sqlite-vec` 0.1.9, `langgraph-checkpoint-sqlite` 3.1.1, `mcp` 2.3.0.
- **Frozen v1.0 source tree read directly** — `src/triagedesk/graph/{build,nodes,state}.py`, `mcp/{server,adapter}.py`, `core/{scorer,citations,rules,matcher,schema}.py`, `store/{audit,borrowed,queue,__init__}.py`, `{demo/run,evals/runner,evals/tools,llm/client,cli}.py`, `tests/test_purity.py`, `data/sats_discriminators.yaml`, `pyproject.toml`.
- **Project docs read directly** — `.planning/PROJECT.md`, `ARCHITECTURE.md`, `STATUS.md`, `EVALS.md`, `docs/{DECISIONS,CONVENTIONS,REQUIREMENTS,ROADMAP,SATS}.md`.
- **LangChain/LangGraph official docs** — persistence, interrupts, `AsyncSqliteSaver`, HITL/`Command(resume=...)`.
- **OpenTelemetry official docs** — Python SDK local exporters, file exporter (JSON-Lines), sensitive-data minimisation.
- **arXiv/peer-reviewed (verified this session)** — "Deceptive Grounding" (arXiv:2607.09349); "Conformal selective prediction with cost-aware deferral for safe clinical triage" (*Sci. Rep.* 2026); "Empirical Analysis of Calibration and Selective Prediction" (arXiv:2603.02719); Goddard et al., "Automation bias" (*JAMIA* 2011); "ICAN-Deploy" (arXiv:2605.28097); numpy 2.0 release notes (alias removal).

### Secondary (MEDIUM confidence)
- `https://reference.langchain.com/python/langgraph.checkpoint.sqlite` — `AsyncSqliteSaver.from_conn_string(...)` context manager + `graph.compile(checkpointer=saver)`.
- `https://opentelemetry.io/docs/specs/otel/protocol/file-exporter` — spans as JSON-Lines to a file, no collector.
- LangSmith docs on egress / `enabled='local'` — cloud sends spans to `api.smith.langchain.com` by default.
- Ollama library pages — `nomic-embed-text` (274 MB), `all-minilm` (46 MB) sizing; Qwen2.5 1.5B/3B licenses.
- Community repos — `jparkerweb/mcp-sqlite` (npm `mcp-sqlite@1.0.9`) and `rusq/mcp-sqlite` (Go, BSD-2); hash-chain audit patterns.

### Tertiary (LOW confidence)
- Web-search best-practice claims on RAG in clinical settings and agent observability 2026 — directional only; MEDIUM where corroborated by official/peer-reviewed sources above.
- Community analyses of LangGraph durable execution ("checkpoints are not durable execution") — flagged for validation during planning.

---

*Research completed: 2026-10-10*
*Ready for roadmap: yes*
