---
phase: 01-sats-foundations-risk-retirement
plan: 01
subsystem: infra
tags: [python, uv, pydantic, ollama, mcp, langchain, sats, schema-validation, local-model]

# Dependency graph
requires: []
provides:
  - "Reproducible uv/Python-3.12 scaffold with exact pins + committed uv.lock"
  - "data/sats_tews.yaml — adult TEWS bands, colour thresholds, out_of_scope (single source of truth)"
  - "core/schema.py — the ONE typed schema module (CaseInput / ExtractionResult), range-validated"
  - "core/rules.py — the ONE YAML loader returning typed models"
  - "core/citations.py — the ONE citation helper (D-15)"
  - "llm/prompts.py + llm/client.py — Ollama extraction with format=schema and mandatory think=False"
  - "mcp/server.py — owned SDK-v2 MCPServer exposing normalize_case over stdio"
  - "mcp/adapter.py — the ONE DIP seam, load_tools() -> list[BaseTool]"
  - "evidence/model-spike.json — measured model-fit evidence selecting the default model"
affects: [01-02, 01-03, 01-04, phase-2, phase-3]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 60000, raw_tokens: 45000).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 57458       # chars/4 over the full realized diff, incl. generated uv.lock (229832 chars)
  raw_tokens: 8879    # chars/4 over authored source/tests/data/scripts only (35518 chars, excl. uv.lock)
  tasks: 3
  commits: 3

tech-stack:
  added:
    - "mcp==2.3.0 (SDK v2, MCPServer) + langchain[mcp]==1.4.4 (langchain.mcp.MCPAdapter, beta)"
    - "langgraph==1.2.14 + langgraph-checkpoint-sqlite==3.1.1 (pinned now, used in Phase 3)"
    - "ollama==0.6.3 (local client) + pydantic==2.14.0 + pyyaml>=6.0,<7"
    - "uv 0.12.24 + Python 3.12.15 (uv-managed)"
  patterns:
    - "One schema module imported everywhere (D-14)"
    - "Purity boundary: core/ imports nothing from llm/mcp/store (D-13)"
    - "Schema-constrained extraction with format=<schema> AND think=False"
    - "DIP seam: callers depend on load_tools(), not MCPAdapter (D-04)"

key-files:
  created:
    - pyproject.toml
    - .python-version
    - .gitignore
    - uv.lock
    - data/sats_tews.yaml
    - src/triagedesk/__init__.py
    - src/triagedesk/core/schema.py
    - src/triagedesk/core/rules.py
    - src/triagedesk/core/citations.py
    - src/triagedesk/llm/prompts.py
    - src/triagedesk/llm/client.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/mcp/adapter.py
    - scripts/spike_e2e.py
    - scripts/spike_model.py
    - evidence/model-spike.json
    - tests/test_schema_rejects.py
  modified: []

key-decisions:
  - "Selected qwen2.5:1.5b as the default model on measured evidence: with qwen3.5:4b loaded, available RAM fell to ~600 MB (< 1024 MB budget) and warm latency was 43s vs 14.8s; the 4B is the documented fallback and both ran end-to-end (SC3)."
  - "The MCP adapter target must be a Path, not a bare string — a bare string is parsed as a URL (adapter refused to launch the owned server)."
  - "Model tags are config values in llm/client.py (PRIMARY_MODEL / FALLBACK_MODEL / DEFAULT_MODEL); a swap is a config change behind the wrapper (SOLID: D)."
  - "Plausible physiological bounds live in the schema; SATS TEWS bands live only in data/sats_tews.yaml — the two never overlap (CONVENTIONS §1)."

patterns-established:
  - "Schema honesty: unit-carrying, range-validated nullable fields; a missing vital stays None and is never imputed"
  - "Tracer-first: one real path through data -> core -> llm -> mcp before any expansion"

requirements-completed: [INTAKE-01, INTAKE-02]

coverage:
  - id: D1
    description: "A free-text note becomes one validated typed case (INTAKE-01) via a real local-model call, and the owned MCP tool is listed and called through the adapter seam."
    requirement: "INTAKE-01"
    verification:
      - kind: e2e
        ref: "uv run python scripts/spike_e2e.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "One schema module represents a case (INTAKE-02); it rejects implausible/wrong-unit values and never imputes a missing vital (Roadmap SC2)."
    requirement: "INTAKE-02"
    verification:
      - kind: unit
        ref: "tests/test_schema_rejects.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Model-fit evidence retires Day-1 unknown (a): measured RAM/latency for the primary model, and the smaller-Qwen fallback run end-to-end (Roadmap SC3)."
    verification:
      - kind: automated
        ref: "uv run python scripts/spike_model.py -> evidence/model-spike.json"
        status: pass
    human_judgment: false
  - id: D4
    description: "DRY/SOLID seams exist: one citation helper (D-15), one prompt module, one YAML loader, and the core/ purity boundary."
    verification:
      - kind: other
        ref: "grep: CaseInput/ExtractionResult only in core/schema.py; format_citation only in core/citations.py; core/ imports no llm/mcp/store"
        status: pass
    human_judgment: false

duration: 64min
completed: 2026-10-09
status: complete
---

# Phase 1 Plan 01: End-to-End Tracer & Model-Fit Retirement Summary

**The thinnest real path works end-to-end — a triage note becomes one range-validated typed case and is exposed as an owned MCP tool listed and called through the adapter — and the local model is selected on measured evidence (qwen2.5:1.5b default; qwen3.5:4b the measured fallback).**

## Performance

- **Duration:** ~64 min (10:55Z → 12:00Z)
- **Started:** 2026-10-09T10:55:42Z
- **Completed:** 2026-10-09T12:00:01Z
- **Tasks:** 3/3
- **Files modified:** 20 created (0 modified)

## Accomplishments

- **The phase's tracer bullet works end-to-end.** `scripts/spike_e2e.py` loads the rule substrate, extracts a validated `ExtractionResult` from a fixed synthetic note via a real local-model call, then lists and calls the owned `normalize_case` tool through `load_tools()` — exiting 0.
- **The single most important implementation detail is captured in code:** schema-constrained extraction requires `think=False` on `qwen3.5:4b`, and the wrapper raises on empty/unparsable output rather than returning unvalidated data.
- **The model unknown is retired on measured evidence.** `evidence/model-spike.json` records RAM (`free -m`), `ollama ps` size, cold/warm latency, licence and a validated extraction for BOTH models. The budget gate selected `qwen2.5:1.5b` (available RAM with the 4B loaded fell to ~600 MB < 1024 MB; warm 14.8s vs 43.0s), and the fallback ran end-to-end unconditionally (Roadmap SC3).
- **Schema honesty is executable (Roadmap SC2).** `CaseInput` carries plausible physiological ranges; a Fahrenheit-magnitude temperature on the Celsius field and out-of-range vitals raise `ValidationError`, and omitted vitals stay `None`.
- **DRY/SOLID seams are real:** one schema module, one YAML loader, one citation helper (`core/citations.py`, D-15), one prompt module, and the `core/` purity boundary.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end note → typed case → owned MCP tool (tracer)** - `e3f8c27` (feat)
2. **Task 2: Retire the model unknown (RAM/latency + fallback run)** - `5362b5e` (feat)
3. **Task 3: Schema honesty tests (reject implausible, never impute)** - `205c7ea` (feat)

**Plan metadata:** committed together with this SUMMARY and STATE.md (docs: complete plan)

## Files Created/Modified

- `pyproject.toml` — exact pins (mcp 2.3.0, langchain[mcp] 1.4.4, langgraph 1.2.14, langgraph-checkpoint-sqlite 3.1.1, ollama 0.6.3, pydantic 2.14.0, pyyaml) + dev deps + pytest/ruff/mypy config
- `.python-version` — `3.12` (host is 3.14; pinned for the deadline clone)
- `uv.lock` — committed resolution (reproducibility artifact; formally owned by Plan 01-04)
- `.gitignore` — Python/tooling artefacts (Rule 2 addition — see Deviations)
- `data/sats_tews.yaml` — adult TEWS bands, TEWS→colour thresholds, target times, `out_of_scope` (single source of truth; re-verified verbatim in Plan 01-02)
- `src/triagedesk/core/schema.py` — the ONE schema module (`CaseInput`, `ExtractionResult`) with plausible-range validators (D-14)
- `src/triagedesk/core/rules.py` — the ONE loader for `data/sats_tews.yaml`, returning typed Pydantic models
- `src/triagedesk/core/citations.py` — the ONE citation helper (D-15)
- `src/triagedesk/llm/prompts.py` — the single home for the extraction prompt template (hashed by SAFE-04 in Plan 01-04)
- `src/triagedesk/llm/client.py` — Ollama wrapper (`format=schema`, `think=False`, validate-or-raise); model tags are config values
- `src/triagedesk/mcp/server.py` — owned SDK-v2 `MCPServer` exposing `normalize_case` over stdio
- `src/triagedesk/mcp/adapter.py` — the ONE DIP seam, `load_tools() -> list[BaseTool]`
- `scripts/spike_e2e.py` — the tracer verification
- `scripts/spike_model.py` — the D-07 model evidence generator (both models, budget gate)
- `evidence/model-spike.json` — committed measured model-fit evidence
- `tests/test_schema_rejects.py` — schema honesty tests (run offline)

## Decisions Made

- **Default model = `qwen2.5:1.5b`.** The budget gate is a designed decision point, not a formality: with `qwen3.5:4b` loaded, available RAM fell to ~600 MB (below the 1024 MB budget) and warm latency was 43.0s (cold 128.2s). `qwen2.5:1.5b` used 1.1 GB resident, left 797 MB available, and ran warm at 14.8s. Both models returned valid schema-constrained JSON; `qwen3.5:4b` is the documented, verified fallback.
- **Both models are Apache-2.0** (recorded in the evidence for the Plan 01-04 NOTICE).
- **The adapter target is a `Path`.** `langchain.mcp.MCPAdapter` parses a bare string as a URL and refuses to launch a subprocess; `Path(server.py)` is the correct local-stdio target.
- **Plausible physiological bounds vs SATS bands are kept separate** — the schema bounds (e.g. temperature 20–45 °C) reject wrong-unit/impossible values; the SATS TEWS bands (35.0/38.4) live only in `data/sats_tews.yaml`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MCP adapter target must be a `Path`, not a string**
- **Found during:** Task 1 (tracer)
- **Issue:** `MCPAdapter(str(SERVER_PATH))` raised `ValueError: MCP target '...' is not a valid URL` — a bare string is parsed as a URL and the owned server was never launched.
- **Fix:** Pass `SERVER_PATH` (a `Path`) so the adapter launches the owned server as a stdio subprocess.
- **Files modified:** `src/triagedesk/mcp/adapter.py`
- **Verification:** `uv run python scripts/spike_e2e.py` lists `['normalize_case']` and calls it, exit 0.
- **Committed in:** `e3f8c27` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added `.gitignore`**
- **Found during:** Task 1 (scaffold)
- **Issue:** The plan listed no `.gitignore`; a Python project without one risks committing `__pycache__/`, tooling caches and runtime DBs. (`.venv/` is auto-ignored by uv's own `.venv/.gitignore`.)
- **Fix:** Added a `.gitignore` covering `__pycache__/`, caches, build artefacts and runtime `*.db` files.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` shows no stray artefacts; the plan's files stage cleanly.
- **Committed in:** `e3f8c27` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both necessary for correctness and a clean scaffold. No scope creep. The model-default outcome is the plan's designed budget gate, not a deviation.

## Issues Encountered

- **Ollama pull of `qwen2.5:1.5b` was network-bound** (~986 MB at ~100–950 KB/s, ~20 min). Resolved by pulling in the background and waiting; the model is now installed and the spike runs offline from here.
- **Cold latency is high on this host** (4B cold 128s / warm 43s; 1.5B cold 41s / warm 15s) — recorded honestly in the evidence (Pitfall 6 / M-7). The "seconds" promise needs the pre-warm strategy documented for the demo.

## User Setup Required

None beyond the plan's declared `user_setup`: the Ollama service must be running with `qwen3.5:4b` and `qwen2.5:1.5b` pulled. Both are now present on this machine.

## Next Phase Readiness

- The scaffold, the one schema module, the rules loader and the citation helper are ready for Plan 01-02 (SATS rule substrate + dual-transcription band tests) and Plan 01-03 (MCP adapter/borrowed-server handshake + purity guards).
- `core/` purity, the citation helper and the prompt module are in place; the executable AST purity guard is Plan 01-03's deliverable.
- **Open (carried forward):** the borrowed `mcp-sqlite` handshake (Plan 01-03) and the verbatim SATS re-verification (Plan 01-02) are still outstanding.
- **Note for Phase 2:** `matched_discriminator_ids` is unconstrained (`list[str]`) until the discriminator data lands in Plan 01-02; the closed set will then be sourced from `data/sats_discriminators.yaml`, never from code.

---
*Phase: 01-sats-foundations-risk-retirement*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 14 key files exist on disk (scaffold, data, core/llm/mcp modules, scripts, evidence, tests).
- All 3 task commits are ancestors of HEAD: `e3f8c27`, `5362b5e`, `205c7ea`.
- Working tree clean (no untracked files).

