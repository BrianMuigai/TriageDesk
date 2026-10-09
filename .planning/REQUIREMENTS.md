# Requirements: TriageDesk

**Defined:** 2026-10-09
**Core Value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.

> Iron-clad engineering rule: **DRY + SOLID** (`CONVENTIONS.md`) — every requirement below must be met
> without duplicating logic or violating the single-source-of-truth rule.

## v1 Requirements

### Intake & Data

- [ ] **INTAKE-01**: Nurse can enter a case as structured vitals plus a free-text presenting complaint
- [ ] **INTAKE-02**: System normalizes a case into one validated typed schema (defined once, imported everywhere)
- [ ] **INTAKE-03**: Missing critical vitals are detected and the nurse is asked to re-measure — no imputation
- [x] **INTAKE-04**: Adult TEWS bands + colour thresholds live **only** in `data/sats_tews.yaml`
- [x] **INTAKE-05**: Discriminators + categories live **only** in `data/sats_discriminators.yaml`

### Scoring (deterministic)

- [ ] **SCORE-01**: TEWS is computed deterministically from typed vitals (no LLM arithmetic)
- [ ] **SCORE-02**: Discriminator overrides apply (most-urgent wins) → a colour + target time
- [ ] **SCORE-03**: Every priority cites the exact rule/vital(s) that produced it (citation invariant)
- [ ] **SCORE-04**: Paediatric / out-of-scope input is detected, then **abstains + escalates** (predicate fails closed)
- [ ] **SCORE-05**: Band-edge, boundary, and unit cases are covered by tests

### MCP tools

- [ ] **TOOL-01**: Own MCP server exposes `normalize_case`
- [ ] **TOOL-02**: Own MCP server exposes `match_discriminators`
- [ ] **TOOL-03**: Own MCP server exposes `score_priority` (acting)
- [ ] **TOOL-04**: Own MCP server exposes `raise_recheck_flag` (acting)
- [ ] **TOOL-05**: Own MCP server exposes `commit_priority` (acting + gated + idempotent)
- [ ] **TOOL-06**: A **borrowed**, maintained SQLite MCP server provides case/queue storage + audit

### Orchestration

- [ ] **ORCH-01**: LangGraph graph runs `ingest → normalize → retrieve → score → verify → (recheck) → gate → commit → handover`
- [ ] **ORCH-02**: The whole task runs on a **local open-weights** model; no frontier model in the required path
- [ ] **ORCH-03**: Model is used only to extract/explain; the score path never imports the model or an MCP client (enforced by a guard test)
- [ ] **ORCH-04**: Extraction uses structured JSON output; invalid output retries once, then falls back deterministically
- [ ] **ORCH-05**: Missing-vital recovery and safe abstention are conditional edges that never guess

### Gate & commit (safety milestone)

- [ ] **GATE-01**: A LangGraph `interrupt()` pauses for a **named** clinician before any queue-affecting write
- [ ] **GATE-02**: `commit_priority` cannot run without a valid approval token (approve/edit/dismiss + name + role + timestamp)
- [ ] **GATE-03**: The write is **idempotent** (keyed by `case_id` + content hash) — a retry cannot double-place a patient
- [ ] **GATE-04**: A deterioration re-check raises a second-look flag **without** reordering the queue on its own

### Audit

- [ ] **AUDIT-01**: Every tool call appends a hash-chained record (inputs, outputs, timestamp, actor)
- [ ] **AUDIT-02**: Approval records capture the named approver + role
- [ ] **AUDIT-03**: Audit record shape is defined once (one helper) and written to one authoritative store

### Safety & hardening

- [ ] **SAFE-01**: Free-text complaint is treated as untrusted data — prompt injection cannot set a priority (tested by E-13)
- [ ] **SAFE-02**: No diagnosis/prescription output exists and no dx/rx tool is defined
- [ ] **SAFE-03**: Least privilege — tools are allowlisted; no network/credentials in the agent path
- [ ] **SAFE-04**: Version pinning + hashing for prompts, model, scale data, and tool schemas
- [ ] **SAFE-05**: Suppression-direction injection is tested (injection that tries to *hide* a finding)

### Evaluation

- [ ] **EVAL-01**: 14 eval cases with expected outcomes, including one unfixed failure (E-09)
- [ ] **EVAL-02**: Each case runs 3×; run-to-run variation is measured and reported
- [ ] **EVAL-03**: Safety invariants INV-1…INV-4 are executable assertions on every run
- [ ] **EVAL-04**: Under-triage and over-triage are reported separately (not hidden behind symmetric accuracy)
- [ ] **EVAL-05**: Report includes latency + token cost per run and is reproducible via recorded hashes

### Docs & demo

- [ ] **DOCS-01**: README gets a stranger running in **one command**
- [ ] **DOCS-02**: `ARCHITECTURE.md` (one page), `EVALS.md`, and `DESCRIPTION.md` (~300 words) are finalised
- [ ] **DOCS-03**: CI smoke test runs the demo on the synthetic fixture
- [ ] **DEMO-01**: 3-minute unedited demo video with tool calls on screen, including a failure

### Engineering standards

- [ ] **QUAL-01**: DRY + SOLID enforced — no duplicated SATS values/citations; graph depends on the tool interface
- [ ] **QUAL-02**: A guard test proves `core/` does not import `llm/` or any MCP client

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

- **DISC-01**: Discriminator confidence field + clarifying-question loop (the honest E-09 fix)
- **ROUTE-01**: Referral / department routing tool (gated like the queue write)
- **INV-01**: "Additional investigations" column (glucose, ketones, urine) + SHCP discretion
- **CAL-01**: Calibration metrics (Brier score / reliability curves)
- **LANG-01**: Multilingual clinical lexicon
- **PAED-01**: Paediatric SATS age-banded charts
- **RETR-01**: Embedding-based discriminator retrieval

## Out of Scope

| Feature | Reason |
|---------|--------|
| Autonomous queue movement | Challenge disqualifier; safety boundary |
| Diagnosis / prescribing | Challenge disqualifier; no dx/rx tool |
| Runtime self-learning / long-term memory | Unsafe at the point of care; non-reproducible priorities |
| Real patient data / hospital EMR integration | Data conduct; synthetic only |
| Frontier model in the required path | Eligibility; data residency |
| Closed no-code builders | Explicitly disallowed by the brief |
| Multilingual input (v1) | Scope; English only for the deadline |
| Full paediatric scoring | Replaced by safe abstention + escalation |

## Traceability

Which phases cover which requirements.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTAKE-01 | Phase 1 | Pending |
| INTAKE-02 | Phase 1 | Pending |
| INTAKE-03 | Phase 2 | Pending |
| INTAKE-04 | Phase 1 | Complete |
| INTAKE-05 | Phase 1 | Complete |
| SCORE-01 | Phase 2 | Pending |
| SCORE-02 | Phase 2 | Pending |
| SCORE-03 | Phase 2 | Pending |
| SCORE-04 | Phase 2 | Pending |
| SCORE-05 | Phase 2 | Pending |
| TOOL-01 | Phase 2 | Pending |
| TOOL-02 | Phase 2 | Pending |
| TOOL-03 | Phase 2 | Pending |
| TOOL-04 | Phase 2 | Pending |
| TOOL-05 | Phase 2 | Pending |
| TOOL-06 | Phase 3 | Pending |
| ORCH-01 | Phase 3 | Pending |
| ORCH-02 | Phase 3 | Pending |
| ORCH-03 | Phase 3 | Pending |
| ORCH-04 | Phase 3 | Pending |
| ORCH-05 | Phase 3 | Pending |
| GATE-01 | Phase 3 | Pending |
| GATE-02 | Phase 3 | Pending |
| GATE-03 | Phase 3 | Pending |
| GATE-04 | Phase 3 | Pending |
| AUDIT-01 | Phase 3 | Pending |
| AUDIT-02 | Phase 3 | Pending |
| AUDIT-03 | Phase 3 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 3 | Pending |
| SAFE-03 | Phase 3 | Pending |
| SAFE-04 | Phase 1 | Pending |
| SAFE-05 | Phase 4 | Pending |
| EVAL-01 | Phase 4 | Pending |
| EVAL-02 | Phase 4 | Pending |
| EVAL-03 | Phase 4 | Pending |
| EVAL-04 | Phase 4 | Pending |
| EVAL-05 | Phase 4 | Pending |
| DOCS-01 | Phase 5 | Pending |
| DOCS-02 | Phase 5 | Pending |
| DOCS-03 | Phase 5 | Pending |
| DEMO-01 | Phase 5 | Pending |
| QUAL-01 | Phase 1 | Pending |
| QUAL-02 | Phase 3 | Pending |

**Coverage:**

- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-10-09*
*Last updated: 2026-10-09 after roadmap traceability*
