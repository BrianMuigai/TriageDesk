# Requirements: TriageDesk

**Defined:** 2026-10-09
**Core Value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.

> Iron-clad engineering rule: **DRY + SOLID** (`CONVENTIONS.md`) — every requirement below must be met
> without duplicating logic or violating the single-source-of-truth rule.

## v1 Requirements

### Intake & Data

- [ ] **INTAKE-01**: Nurse can enter a case as structured vitals plus a free-text presenting complaint
- [ ] **INTAKE-02**: System normalizes a case into one validated typed schema (defined once, imported everywhere)
- [x] **INTAKE-03**: Missing critical vitals are detected and the nurse is asked to re-measure — no imputation
- [x] **INTAKE-04**: Adult TEWS bands + colour thresholds live **only** in `data/sats_tews.yaml`
- [x] **INTAKE-05**: Discriminators + categories live **only** in `data/sats_discriminators.yaml`

### Scoring (deterministic)

- [x] **SCORE-01**: TEWS is computed deterministically from typed vitals (no LLM arithmetic)
- [x] **SCORE-02**: Discriminator overrides apply (most-urgent wins) → a colour + target time
- [x] **SCORE-03**: Every priority cites the exact rule/vital(s) that produced it (citation invariant)
- [x] **SCORE-04**: Paediatric / out-of-scope input is detected, then **abstains + escalates** (predicate fails closed)
- [x] **SCORE-05**: Band-edge, boundary, and unit cases are covered by tests

### MCP tools

- [x] **TOOL-01**: Own MCP server exposes `normalize_case`
- [x] **TOOL-02**: Own MCP server exposes `match_discriminators`
- [x] **TOOL-03**: Own MCP server exposes `score_priority` (acting)
- [x] **TOOL-04**: Own MCP server exposes `raise_recheck_flag` (acting)
- [x] **TOOL-05**: Own MCP server exposes `commit_priority` (acting + gated + idempotent)
- [x] **TOOL-06**: A **borrowed**, maintained SQLite MCP server provides case/queue storage + audit

### Orchestration

- [x] **ORCH-01**: LangGraph graph runs `ingest → normalize → retrieve → score → verify → (recheck) → gate → commit → handover`
- [x] **ORCH-02**: The whole task runs on a **local open-weights** model; no frontier model in the required path
- [x] **ORCH-03**: Model is used only to extract/explain; the score path never imports the model or an MCP client (enforced by a guard test)
- [x] **ORCH-04**: Extraction uses structured JSON output; invalid output retries once, then falls back deterministically
- [x] **ORCH-05**: Missing-vital recovery and safe abstention are conditional edges that never guess

### Gate & commit (safety milestone)

- [x] **GATE-01**: A LangGraph `interrupt()` pauses for a **named** clinician before any queue-affecting write
- [x] **GATE-02**: `commit_priority` cannot run without a valid approval token (approve/edit/dismiss + name + role + timestamp)
- [x] **GATE-03**: The write is **idempotent** (keyed by `case_id` + content hash) — a retry cannot double-place a patient
- [x] **GATE-04**: A deterioration re-check raises a second-look flag **without** reordering the queue on its own

### Audit

- [x] **AUDIT-01**: Every tool call appends a hash-chained record (inputs, outputs, timestamp, actor)
- [x] **AUDIT-02**: Approval records capture the named approver + role
- [x] **AUDIT-03**: Audit record shape is defined once (one helper) and written to one authoritative store

### Safety & hardening

- [x] **SAFE-01**: Free-text complaint is treated as untrusted data — prompt injection cannot set a priority (tested by E-13)
- [x] **SAFE-02**: No diagnosis/prescription output exists and no dx/rx tool is defined
- [x] **SAFE-03**: Least privilege — tools are allowlisted; no network/credentials in the agent path
- [x] **SAFE-04**: Version pinning + hashing for prompts, model, scale data, and tool schemas
- [x] **SAFE-05**: Suppression-direction injection is tested (injection that tries to *hide* a finding)

### Evaluation

- [x] **EVAL-01**: 14 eval cases with expected outcomes, including one unfixed failure (E-09)
- [x] **EVAL-02**: Each case runs 3×; run-to-run variation is measured and reported
- [x] **EVAL-03**: Safety invariants INV-1…INV-4 are executable assertions on every run
- [ ] **EVAL-04**: Under-triage and over-triage are reported separately (not hidden behind symmetric accuracy)
- [ ] **EVAL-05**: Report includes latency + token cost per run and is reproducible via recorded hashes

### Docs & demo

- [ ] **DOCS-01**: README gets a stranger running in **one command**
- [ ] **DOCS-02**: `ARCHITECTURE.md` (one page), `EVALS.md`, and `DESCRIPTION.md` (~300 words) are finalised
- [ ] **DOCS-03**: CI smoke test runs the demo on the synthetic fixture
- [ ] **DEMO-01**: 3-minute unedited demo video with tool calls on screen, including a failure

### Engineering standards

- [x] **QUAL-01**: DRY + SOLID enforced — no duplicated SATS values/citations; graph depends on the tool interface
- [x] **QUAL-02**: A guard test proves `core/` does not import `llm/` or any MCP client

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
| INTAKE-03 | Phase 2 | Complete |
| INTAKE-04 | Phase 1 | Complete |
| INTAKE-05 | Phase 1 | Complete |
| SCORE-01 | Phase 2 | Complete |
| SCORE-02 | Phase 2 | Complete |
| SCORE-03 | Phase 2 | Complete |
| SCORE-04 | Phase 2 | Complete |
| SCORE-05 | Phase 2 | Complete |
| TOOL-01 | Phase 2 | Complete |
| TOOL-02 | Phase 2 | Complete |
| TOOL-03 | Phase 2 | Complete |
| TOOL-04 | Phase 2 | Complete |
| TOOL-05 | Phase 2 | Complete |
| TOOL-06 | Phase 3 | Complete |
| ORCH-01 | Phase 3 | Complete |
| ORCH-02 | Phase 3 | Complete |
| ORCH-03 | Phase 3 | Complete |
| ORCH-04 | Phase 3 | Complete |
| ORCH-05 | Phase 3 | Complete |
| GATE-01 | Phase 3 | Complete |
| GATE-02 | Phase 3 | Complete |
| GATE-03 | Phase 3 | Complete |
| GATE-04 | Phase 3 | Complete |
| AUDIT-01 | Phase 3 | Complete |
| AUDIT-02 | Phase 3 | Complete |
| AUDIT-03 | Phase 3 | Complete |
| SAFE-01 | Phase 2 | Complete |
| SAFE-02 | Phase 3 | Complete |
| SAFE-03 | Phase 3 | Complete |
| SAFE-04 | Phase 1 | Complete |
| SAFE-05 | Phase 4 | Complete |
| EVAL-01 | Phase 4 | Complete |
| EVAL-02 | Phase 4 | Complete |
| EVAL-03 | Phase 4 | Complete |
| EVAL-04 | Phase 4 | Pending |
| EVAL-05 | Phase 4 | Pending |
| DOCS-01 | Phase 5 | Pending |
| DOCS-02 | Phase 5 | Pending |
| DOCS-03 | Phase 5 | Pending |
| DEMO-01 | Phase 5 | Pending |
| QUAL-01 | Phase 1 | Complete |
| QUAL-02 | Phase 3 | Complete |

**Coverage:**

- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-10-09*
*Last updated: 2026-10-09 after roadmap traceability*
