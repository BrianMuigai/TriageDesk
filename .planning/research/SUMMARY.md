# Project Research Summary

**Project:** TriageDesk
**Domain:** Local-first, MCP-based agentic clinical triage-support tool (SATS priority scoring, Python)
**Researched:** 2026-10-09
**Confidence:** MEDIUM-HIGH (project-derived design = HIGH; ecosystem/mechanics = MEDIUM-HIGH; agent-engineering generalities = MEDIUM)

## Executive Summary

TriageDesk is a **safety-critical clinical decision-support agent**, not a chatbot and not a
general-purpose assistant. It turns the vitals and free-text complaint a nurse already has at the OPD
triage desk into a **sourced, SATS-grounded priority colour in seconds** — and it never diagnoses,
prescribes, or moves a patient without a named clinician's approval. The research converges on one
architecture that experts use for regulated decisioning: **the graph plans, the tools compute, the model
talks, the clinician authorises, the store persists.** Determinism is a property of the *tool layer*
(pure functions over data), never of the graph and never of the model. The score path must never cross
the LLM boundary; the model is confined to normalising prose and explaining, and the only irreversible
action (the queue write) is idempotent, approval-keyed, and structurally reachable only through an
`interrupt()` gate.

The single most consequential technical finding is an **MCP ecosystem fork**: `langchain-mcp-adapters`
is deprecated/archived and pins `mcp<2`, so it physically cannot coexist with the current MCP SDK. The
recommended **"World A"** stack is `mcp` 2.3.0 (`MCPServer`) + `langchain[mcp]` 1.4.4
(`langchain.mcp.MCPAdapter`, **beta**) + FastMCP 4, on Python 3.12 via `uv`, LangGraph 1.2.14 with a
SQLite checkpointer, and a local Qwen2.5 model via Ollama. The one real risk is the **beta adapter**;
this is contained by exact-pinning and retiring it in a **half-day Phase-1 spike**, after which the
fallback ("World B": `mcp<2` + `FastMCP` v1 API) is a one-module wiring swap because the graph binds to
the MCP *tool interface*, not the adapter.

The dominant risks are **clinical, not technical**. The dangerous error is *under-triage*: a
citation-backed but wrong colour (E-09), a silently imputed missing vital, a discriminator that is never
matched, or prompt injection that *suppresses* a finding rather than inflating it. Mitigations are
consistent across the research: deterministic scoring and deterministic discriminator matching, a
citation invariant that checks *applicability* (`citations == triggered_rules`) not just presence, a
fail-closed out-of-scope detector, governed recovery paths, and an **honest, enforced** evaluation that
reports under- vs over-triage separately and treats *any* run-to-run variation as a failure. On a 6-day
solo deadline the greatest non-clinical risk is **over-building** — three working tools beat nine
half-working ones, and the shipped E-09 honest failure outscores a hastily-added feature.

## Key Findings

### Recommended Stack

The stack is **World A of the forked MCP ecosystem** (`STACK.md`): `mcp==2.3.0` with the v2 `MCPServer`
API (the v1 `FastMCP` import path was *removed*, not deprecated), protocol revision **2026-07-28**,
ingested into LangGraph via `langchain[mcp]==1.4.4` (`langchain.mcp.MCPAdapter`, **beta**). Everything
is pinned and locked (`uv.lock`, `.python-version`) so the deadline-cloned repo rebuilds identically.
The model is **Qwen2.5-1.5B-Instruct** (Q4_K_M, 986 MB, Apache-2.0) as the primary — it actually fits
the host's ~2.3 GB available RAM; **3B** (1.9 GB, better reasoning but the **Qwen licence**, not
Apache-2.0) is aspirational/opt-in. Two SQLite files are deliberate: `triage.db` (domain + audit via the
borrowed MCP) and `checkpoints.db` (LangGraph pause state) — an immutable clinical record and disposable
runtime state are different concerns.

**Core technologies:**
- **Python 3.12 via `uv`** — reproducible runtime; host 3.14 is pinned away for the deadline clone.
- **`mcp==2.3.0` (`MCPServer`)** — author the *owned* MCP server; current spec; serves legacy clients.
- **`langchain[mcp]==1.4.4` (beta) + FastMCP 4.1.0** — ingest MCP tools as LangChain tools; beta risk retired in a Phase-1 spike.
- **LangGraph 1.2.14 + `langgraph-checkpoint-sqlite==3.1.1`** — explicit graph; `interrupt()`/`Command(resume=)` is exactly the approval gate; durable pause.
- **Ollama 0.30.6 + `ollama==0.6.3` + Qwen2.5-1.5B** — local CPU inference, no egress; structured outputs (`format=<JSON schema>`).
- **Pydantic 2.14.0** — one schema source for Ollama output, MCP contracts, and typed state (DRY).
- **`pyyaml`** — `data/sats_tews.yaml` + `data/sats_discriminators.yaml`; the single source of SATS truth.

**Hard avoid:** `from mcp.server.fastmcp import FastMCP`; `langchain-mcp-adapters`; the archived official
SQLite MCP server; Qwen2.5 7B (won't fit); free-form ReAct; Ollama tool-calling as the primary
extraction path; unpinned `npx`; one file for audit + checkpoints.

### Expected Features

The feature landscape (`FEATURES.md`) is derived from SATS reliability literature and the CDS "Five
Rights" — the tool competes on **defensibility and fit, not raw accuracy**. The MVP is the *safety
spine* plus honest evidence, ruthlessly scoped for 6 days.

**Must have (table stakes):**
- **Sourced priority** — every colour cites the rule/vital that produced it; unsourced is disqualifying.
- **Deterministic scoring** — TEWS + discriminator override computed in code; the model never emits a number.
- **Human confirmation gate** — `interrupt()` before any queue write; write refuses without an approval token.
- **Named-approver audit trail** — one logging helper; actor/approver/role/timestamp per call.
- **Published-scale grounding** — SATS/TEWS + discriminators in `data/*.yaml`, never hard-coded.
- **Structured intake + missing-vital recovery** — parse prose → typed fields; ask, don't fabricate.
- **Actionable output + handover card** — colour + target time + citations.
- **Local-only, one-command run + 13 honest eval cases.**

**Should have (competitive differentiators):**
- **Safe abstention** on out-of-scope/paediatric input — fail closed, escalate.
- **Discriminator-override correctness** ("most urgent wins") — proves understanding of SATS, not just TEWS.
- **Calibration / discriminator-confidence signal** — tells the nurse *when the match was weak* (fix path for E-09).
- **Deterioration re-check flag** — second look, non-mutating, no auto re-classification.
- **Bounded failure recovery** — retry once → deterministic fallback or escalate; never uncited output.
- **Prompt-injection resistance**, **hash-chained audit**, **idempotent gated write**, **version pinning/hashing**, **extend-by-data**, **honest evaluation incl. a declared failure**.

**Defer (v1.x / v2+):**
- Discriminator confidence field, clarifying-question loop, embedding retrieval over the KB, referral routing, multilingual (v1.x).
- Live hospital integration, approver authentication, full paediatric SATS, offline rule-review pipeline (v2+).

**Anti-features (deliberately excluded):** autonomous queue movement, diagnosis/differential generation,
prescribing, runtime self-learning, free-form ReAct, LLM-computed numbers, chatbot-wrapper, real patient
data, over-alerting, and any "confidence score" shown as a clinical probability.

### Architecture Approach

The architecture (`ARCHITECTURE.md`) is an explicit LangGraph `StateGraph` over a **pure deterministic
core** with the model at the edges. Thesis: *the graph plans; the tools compute; the model talks; the
clinician authorises; the store persists.* Every component has one responsibility; the boundary rule is
"answers a question → tool; controls flow → node; remembers → checkpointer/store". The HITL gate sits at
the **proposal→persistence** boundary — everything up to `score`/`verify` is reversible; the only
irreversible action is `commit_priority`, reachable only through the resumed `interrupt()`.

**Major components:**
1. **Ingestion/normalisation** — validate + type; emit `missing[]` / `out_of_scope`; LLM extraction + deterministic fallback.
2. **Deterministic SATS scorer** (`score_priority`) — pure, I/O-free; TEWS + override → colour + `triggered_rules[]` + `citations[]`.
3. **Discriminator retrieval** (`match_discriminators`) — deterministic alias/synonym lookup over the KB.
4. **Deterioration re-check** (`raise_recheck_flag`) — pure serial-vitals comparison → flag only.
5. **Approval gate** (`interrupt()`) + **gated commit** (`commit_priority`) — idempotent, approval-keyed, transactional.
6. **Audit log** — one hash-chained interceptor every tool call routes through.
7. **Evaluation harness** — same graph interface with an injected stub model + fault injection.

**Key patterns:** deterministic operator behind an MCP tool; explicit graph (not free-form ReAct);
HITL gate as an interrupt node (no non-idempotent side effect before `interrupt()`); idempotent
approval-keyed write boundary; data-driven rule substrate (new rule = a YAML edit, OCP); audit as a
cross-cutting interceptor; checkpointer ≠ system of record. Two cheap guardrails are worth building
early: a test that fails if `core/` imports `llm/` or an MCP client, and a test that fails if any TEWS
band/discriminator/citation string appears outside `data/`.

### Critical Pitfalls

The pitfalls research (`PITFALLS.md`) is the highest-value input for sequencing — 17 critical + 15
moderate, each mapped to the phase that must own it. Top five:

1. **"Cited" ≠ "correctly cited"** (Pitfall 1) — a real citation can hide under-triage (E-09). Treat
   discriminator recall as a first-class safety metric; make `verify` reject `citations ≠ triggered_rules`;
   emit a "no discriminator matched" coverage signal.
2. **Automation bias turns the gate into a rubber stamp** (Pitfall 2) — show *evidence*, not a verdict;
   make edit/dismiss as easy as approve; record and report the override rate (0% is a warning, not a win).
3. **Prompt injection that *suppresses* a finding** (Pitfall 3) — the deterministic scorer defends the
   *computation*, not the *perception*; keep `match_discriminators` deterministic, schema-constrain
   `normalize`, and add a negation/suppression eval case.
4. **The LLM silently imputes a missing vital** (Pitfall 4) — make the schema nullable, derive `missing[]`
   from raw input, never default a missing param to its 0-point band, and assert score inputs ⊆ nurse-provided fields.
5. **A 3B CPU model cannot reliably drive multi-step tool calls** (Pitfall 13) — the plan's biggest
   technical risk; use schema-constrained decoding + Pydantic on every result, keep `verify`
   deterministic-first, benchmark 3B vs 1.5B **on Day 1**, and exercise the deterministic fallback.

Also phase-critical: band-edge/unit ambiguity (Pitfall 5, P1/P2); "deterministic" while the pipeline is
stochastic (Pitfall 6, P3/P4); non-deterministic discriminator selection (Pitfall 7); over-triage masking
danger (Pitfall 8); diagnosis/prescription creep through the handover prose (Pitfall 9); paediatric
detector failing open (Pitfall 10); the eval set curated to pass (Pitfall 11); variation reported but not
enforced (Pitfall 12); non-atomic write/hash drift (Pitfall 14); licensing/attribution (Pitfall 15);
"never-ran results" or a post-deadline commit (Pitfall 16, both disqualifying); and over-building
(Pitfall 17).

## Implications for Roadmap

The research independently converges on the **same six capability phases** (the pitfalls file maps to
them explicitly; the architecture build order nests cleanly inside them). This is the recommended
starting structure.

### Phase 1: SATS Data & Foundations
**Rationale:** Everything depends on the rule substrate and on retiring the two riskiest unknowns first
(model reliability, MCP wiring). Front-loading risk is the single most important scheduling decision.
**Delivers:** `data/sats_tews.yaml` + `data/sats_discriminators.yaml` (verbatim re-verified against the
SATS manual), the typed `schema/` case model, `rules/loader` + the one citation helper; project scaffold
(`uv`/3.12/`uv.lock`); a proven local-model structured-output round-trip (pick 1.5B vs 3B on evidence);
**the MCP spike** (beta `MCPAdapter` against the owned + borrowed servers); `NOTICE`/attribution +
third-party licence disclosure.
**Addresses:** published-scale grounding, deterministic scoring (schema side), local model, DRY single-source.
**Avoids:** Pitfall 5 (data/verbatim, unit-carrying schema), Pitfall 13 (model selection on Day 1),
Pitfall 15 (licence hygiene), plus the Stack's open flags — retire the beta-adapter and legacy-handshake
risks here.

### Phase 2: Deterministic Scorer & Own MCP Server
**Rationale:** The scorer is the load-bearing correctness component and is pure, so it can be tested in
isolation before any graph exists. The owned server wraps it as the challenge-required tools.
**Delivers:** `core/*` (TEWS, discriminator match + override resolution, scorer, recheck) with
hand-computed unit tests; `mcp_server/` exposing 5 tools incl. the gated `commit_priority` stub, with
`contracts.py` shared with the graph.
**Uses:** `mcp==2.3.0` (`MCPServer`), Pydantic schemas, `pyyaml`.
**Implements:** deterministic scorer, discriminator retrieval, audit/tool contracts.
**Avoids:** Pitfall 1 (citation applicability), Pitfall 4 (no imputation idiom), Pitfall 5 (table-test
every band edge both sides), Pitfall 7 (deterministic alias matcher), Pitfall 10 (out-of-scope predicate
as data, fail closed), Pitfall 13 (schema-validation on every result).

### Phase 3: Graph, Gate, Audit & Borrowed Server
**Rationale:** With pure tools proven, wire them into the explicit graph and add the safety spine —
the gate, the hash-chained audit, and the borrowed persistence. Step 6 of the architecture build order
("the gate refuses to commit without approval") is the single most important behavioural milestone;
protect it over polish if schedules slip.
**Delivers:** `graph/` nodes + conditional edges (missing / out_of_scope / retry / recheck);
checkpointer + `approval_gate` (`interrupt()`/`Command(resume=)`); borrowed SQLite MCP adapter +
transactional, idempotent `commit_priority`; hash-chained audit (one interceptor); the two cheap
DRY/DIP guardrail tests.
**Uses:** LangGraph 1.2.14, `langgraph-checkpoint-sqlite`, `langchain[mcp]`, borrowed SQLite MCP.
**Implements:** approval gate, gated commit, audit interceptor, checkpointer.
**Avoids:** Pitfall 2 (evidence-rich gate; edit/dismiss first-class), Pitfall 3 (colour path prose-free,
deterministic matcher), Pitfall 9 (templated handover, no clinical fields), Pitfall 12 (INV-1…4 as
executable assertions), Pitfall 14 (one transaction, immutable hash key), M-4/M-6/M-14.

### Phase 4: Evals, Recovery & Honest Failure
**Rationale:** Credibility is scored; the harness must be honest and *enforcing*, not decorative, and the
recovery/abstention/calibration paths are what make the tool defensible. Expected colours must have been
frozen in Phase 1 (before the scorer existed).
**Delivers:** `evals/` harness running 13 cases × 3 runs through the same graph interface with fault
injection; per-case coverage/confidence; missing-vital recovery, abstention, deterioration, retry-once +
deterministic fallback; under- vs over-triage reported separately; ≥2 held-out cases; E-09 as the declared
failure; `report.json` as the sole source of `EVALS.md` numbers.
**Addresses:** honest evaluation, bounded failure recovery, calibrated confidence.
**Avoids:** Pitfall 1 (coverage field + `discriminator_matched`), Pitfall 8 (error-direction report),
Pitfall 11 (frozen expectations, held-out cases), Pitfall 12 (any-variation = fail; invariants gate CI),
Pitfall 13 (E-12 extended to wrong-tool injection).

### Phase 5: Demo & Minimal Surface
**Rationale:** The demo gates every criterion; it must be recorded on schedule regardless of polish, and
it must show a human *judging* with evidence on screen — not a single "approve" keystroke.
**Delivers:** a minimal terminal/CLI surface; an unedited ≤3-minute live demo against the frozen commit;
latency measured on the demo machine (cold start included); model pre-warmed; an OOM/latency dry run the
day before.
**Avoids:** Pitfall 2 (visible reasoning + override), Pitfall 16 (live run, no mocked calls),
Pitfall 17 (hard scope stop — ship the terminal surface, cut anything untraceable to a REQUIREMENTS ID),
M-7/M-8 (latency & RAM).

### Phase 6: Docs, Freeze & Submit
**Rationale:** Two silent disqualifiers live here (never-ran results; a post-deadline commit), so the
freeze is a designed procedure, not an afterthought.
**Delivers:** finalised ARCHITECTURE/EVALS/DESCRIPTION (numbers only from `report.json`); a clean-clone,
one-command run against the frozen tag; a licence/attribution audit; **freeze on Day 6 morning** — tag,
then stop; disable `commit_docs`/CI/hooks and audit the remote for post-freeze commits.
**Avoids:** Pitfall 15 (licence audit), Pitfall 16 (report from harness; `git log -1` predates deadline;
automation paused), M-15 (`.planning/` vs public docs consistency).

### Phase Ordering Rationale

- **Follows the dependency DAG from data outward** (architecture build order): `data` → `schema`/loader
  → pure `core` → MCP server → graph → gate → store → evals → demo → docs. Nothing downstream is
  buildable before its inputs, and each layer is testable in isolation because the boundary between them
  is an interface (DIP), not a call chain.
- **Retires both Day-1 risks early:** model reliability and MCP wiring are the two unknowns that could
  force a rewrite; Phase 1 spikes them.
- **Splits pure-tool correctness (P2) from graph/safety wiring (P3)** so the scorer can be proven against
  hand-computed colours before it is called by anything.
- **Every pitfall maps to an owning phase** with an observable verification (see `PITFALLS.md`
  §"Pitfall-to-Phase Mapping"), so prevention is scheduled rather than hoped for.
- **Demo (P5) and freeze (P6) are protected phases**, because they gate scoring and carry disqualifiers,
  not because they are the largest.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** the MCP beta-adapter spike and the legacy-server handshake are explicitly OPEN — plan the
  half-day spike, exact-pin the versions, and define the World-B fallback trigger up front.
- **Phase 3:** LangGraph `interrupt()` + durable checkpointer semantics have non-obvious rules (no
  try/except around `interrupt()`; no side effects before it; typed resume values). Worth a focused
  research pass before planning the node graph.

Phases with well-understood patterns (skip `--research-phase`):
- **Phase 2:** pure functions + Pydantic + FastMCP decorators — standard, well-documented patterns.
- **Phase 4:** pytest harness + fault injection — standard test engineering, guided by `EVALS.md`.
- **Phase 5 / Phase 6:** CLI surface, demo recording, and a freeze/tag procedure — process, not research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Versions cross-checked against official docs + PyPI registry (HIGH); two contested items — beta `langchain.mcp.MCPAdapter` and the borrowed-server handshake — flagged OPEN, retired in a Phase-1 spike. |
| Features | MEDIUM | Internal design docs + SATS primary sources are HIGH; external literature gathered via web search is LOW per provider tier (though mostly peer-reviewed). |
| Architecture | HIGH (design) / MEDIUM (mechanics) | The project's own design docs are authoritative requirements (HIGH); LangGraph/MCP mechanics rest on official docs (MEDIUM); the hybrid-orchestration consensus is cross-checked web (MEDIUM). |
| Pitfalls | HIGH (project-specific) / MEDIUM (generalities) | Pitfalls 1–17 + M-1…M-15 derive directly from the artifacts and challenge brief (HIGH); clinical/agent-engineering generalities are directional (MEDIUM); small-model numeric thresholds are LOW and must be measured on this machine. |

**Overall confidence:** MEDIUM-HIGH. The *what to build* is high-confidence and internally consistent;
the *exact stack wiring* and *model reliability* are the two areas carrying real, scheduled uncertainty.

### Gaps to Address

- **No guaranteed clinician/nurse access during the build** (`PROJECT.md`) — expected colours are
  guideline-derived, not clinician-adjudicated (`G-1`). Keep that claim honest; do not upgrade it later
  without adjudication.
- **Beta MCP adapter + legacy borrowed-server handshake** — the highest stack uncertainty; must be
  resolved by the Phase-1 spike, with the World-B one-module swap defined in advance.
- **Model tool-calling reliability at 1.5B/3B on CPU is unmeasured here** — treat community "70%"
  figures as LOW confidence and benchmark on the actual machine (Pitfall 13, Day 1).
- **RAM headroom (~1.4–2.3 GB) is tight** — measure with `ollama ps`; default to 1.5B, keep 3B opt-in,
  and have the 1.5B fallback run end-to-end before relying on 3B.
- **3B licence is the Qwen licence, not Apache-2.0** — default to 1.5B for the recorded demo and
  document any 3B use; confirm the exact Ollama tag's licence before shipping.
- **Two SQLite files** may invite a "why two?" question — document the audit-record-vs-runtime-state
  rationale in `ARCHITECTURE` (already the plan).
- **Test-set honesty** — expected colours must be frozen before the scorer exists, with held-out cases and
  logged rationale for any YAML change that flips a colour.

## Sources

### Primary (HIGH confidence)
- Project design docs — `PROJECT.md`, `CONVENTIONS.md`, `ARCHITECTURE.md`, `REQUIREMENTS.md`, `EVALS.md`, `DECISIONS.md`, `SECURITY.md`, `docs/SATS.md`.
- `modelcontextprotocol.io/specification/versioning` — protocol revision 2026-07-28.
- `py.sdk.modelcontextprotocol.io` + `python-sdk` whats-new — SDK v2, `FastMCP`→`MCPServer`, transports.
- PyPI registry metadata — `mcp` 2.3.0, `langchain` 1.4.4, `fastmcp` 4.1.0, `langgraph` 1.2.14, `langgraph-checkpoint-sqlite` 3.1.1, `ollama` 0.6.3, `pydantic` 2.14.0, `langchain-mcp-adapters` 0.3.2.
- LangChain docs — `langchain.mcp.MCPAdapter`, migration off `langchain-mcp-adapters`, LangGraph interrupts/persistence.
- Ollama docs — structured outputs, tool calling; archived `modelcontextprotocol/servers-archived` (SQLite server).

### Secondary (MEDIUM confidence)
- SATS validity/reliability literature (Mould-Millman 2021; Twomey 2012; Dalwai 2017; Meyer 2018; Conti 2022) — under-triage as the dangerous direction.
- CDS "Five Rights" (Osheroff/AHRQ); Fernandes 2020 triage-CDS review; automation-bias reviews (Goddard; Khera, JAMA 2024).
- Maintained borrowed-server candidates — `jparkerweb/mcp-sqlite` (npm 1.0.9), `rusq/mcp-sqlite` (Go, BSD-2).
- Hash-chain audit patterns (`auditchain` and peers) — `SHA256(prev_hash‖payload)`, HMAC seal, append-only.
- Manchester Triage System licensing (ALSG) — the licensing trap avoided by choosing SATS.
- OWASP LLM Prompt Injection Prevention Cheat Sheet; AWS Bedrock agent-security guidance — dual-LLM/quarantined-parser shape.
- Challenge brief — Healthcare track, *The Triage Desk* (`agentic-africa-challenge.lovable.app`), fetched 2026-10-09.

### Tertiary (LOW confidence)
- Small-model tool-calling failure-rate benchmarks (community posts; single-source thresholds) — use as a warning signal, measure on this machine (Pitfall 13).
- Selective-prediction/abstention findings (arXiv preprints) — directionally supportive, not predictive for this prototype.

---
*Research completed: 2026-10-09*
*Ready for roadmap: yes*
