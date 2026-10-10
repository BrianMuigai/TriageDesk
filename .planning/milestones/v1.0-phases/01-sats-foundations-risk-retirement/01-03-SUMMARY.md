---
phase: 01-sats-foundations-risk-retirement
plan: 03
subsystem: mcp
tags: [mcp, langchain, adapter, dip, spike, purity-guard, dry-guard, ast, ruff, world-a]

# Dependency graph
requires:
  - plan: "01-01"
    provides: "uv/Python-3.12 scaffold, core/schema.py, mcp/server.py stub, mcp/adapter.py load_tools(), langchain[mcp] pins"
  - plan: "01-02"
    provides: "data/*.yaml single source of truth, core/rules.py loaders (TEWS + discriminators)"
provides:
  - "mcp/adapter.py — the ONE MCP wiring module: load_tools() (graph DIP seam) + load_borrowed_tools() in a SEPARATE adapter context (no era collapse)"
  - "evidence/mcp-spike.json — D-07 retirement: owned + borrowed tool lists and one real call each; World A adopted explicitly"
  - "scripts/spike_mcp.py — repeatable MCP handshake spike (exit non-zero on either failure)"
  - "tests/test_mcp_server.py — owned tool contract regression via the in-memory MCP client"
  - "tests/test_purity.py — executable AST purity guard for core/ (D-13, one-way)"
  - "tests/test_no_duplicated_sats.py — executable DRY guard for the scoring substrate"
  - "pyproject.toml — ruff TID251 banned-api scoped to core/ (belt-and-braces)"
affects: [01-04, phase-2, phase-3]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 52000, raw_tokens: 40000).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 6751         # chars/4 over the full realized diff (27005 chars)
  raw_tokens: 6222     # chars/4 over authored files only (24889 chars, excl. generated evidence/mcp-spike.json)
  tasks: 3             # 1 blocking-human checkpoint (approved) + 2 auto tasks
  commits: 2           # MEASURED: git rev-list --count plan_head_before..HEAD
  plan_head_before: 4d09b819fdd51251fbeb2e34fc6c092dc0b45b24
  plan_head_after: ff657355030880ce362d4491d0c13c2d80515054

tech-stack:
  added: []
  patterns:
    - "One MCP wiring module names MCPAdapter; every server is reached through its OWN adapter context (era-safe)"
    - "DIP seam: the graph depends on load_tools() -> list[BaseTool], never on the concrete adapter (D-04)"
    - "Guards are executable: core/ purity (AST) and single-source SATS (AST + ruff TID251)"

key-files:
  created:
    - scripts/spike_mcp.py
    - tests/test_mcp_server.py
    - tests/test_purity.py
    - tests/test_no_duplicated_sats.py
    - evidence/mcp-spike.json
  modified:
    - src/triagedesk/mcp/adapter.py
    - src/triagedesk/mcp/server.py
    - pyproject.toml

key-decisions:
  - "World A adopted (D-04): langchain.mcp.MCPAdapter listed and called a tool on BOTH the owned SDK-v2 server and the borrowed legacy SQLite server, each in a separate adapter context — no era collapse."
  - "The borrowed server is reached through load_borrowed_tools() in adapter.py (a SEPARATE context), keeping mcp/adapter.py the only module that names MCPAdapter while load_tools() remains the graph-facing seam."
  - "The DRY guard covers the scoring substrate (discriminating numeric band edges + all clinical strings); input-domain enums (mobility/avpu) and plausible-range bounds in core/schema.py are exempt by design."
  - "ruff TID251 is scoped to core/ via per-file-ignores, because a global ban on triagedesk.llm|mcp|store would flag legitimate mcp->llm imports."

patterns-established:
  - "Two adapter contexts, never one merged MCPConfig — the modern owned server and the legacy borrowed server keep their own protocol eras"
  - "Guards prove their own non-vacuity (a synthetic violation is asserted to fail the guard)"

requirements-completed: [QUAL-01]

coverage:
  - id: D1
    description: "The adapter lists and calls a tool on BOTH the owned and borrowed servers, with the World A/B decision recorded (D-07, Roadmap SC4)."
    verification:
      - kind: e2e
        ref: "uv run python scripts/spike_mcp.py --report evidence/mcp-spike.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "The owned tool contract is regression-tested without the borrowed server (in-memory MCP client)."
    verification:
      - kind: unit
        ref: "tests/test_mcp_server.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "core/ provably imports nothing from llm|mcp|store — enforced by an executable AST test, with a ruff belt-and-braces (D-13, QUAL-01/02)."
    verification:
      - kind: unit
        ref: "tests/test_purity.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "No SATS scoring value (band edge, colour threshold, discriminator label/alias) appears outside data/ — enforced by an executable test (QUAL-01, CONVENTIONS §1)."
    verification:
      - kind: unit
        ref: "tests/test_no_duplicated_sats.py"
        status: pass
    human_judgment: false

duration: 23min
completed: 2026-10-09
status: complete
---

# Phase 1 Plan 03: MCP Beta-Adapter Retirement & Executable DRY/SOLID Guards Summary

**The MCP unknown is retired on committed evidence — `langchain.mcp.MCPAdapter` listed and called a tool on both the owned SDK-v2 server and the borrowed legacy SQLite server, each in its own adapter context (World A adopted) — and the iron-clad DRY + SOLID rules are now executable: an AST purity guard proves `core/` imports no `llm`/`mcp`/`store`, and a DRY guard proves no SATS scoring value escapes `data/`.**

## Performance

- **Duration:** ~23 min (12:29Z → 12:52Z)
- **Started:** 2026-10-09T12:29:26Z
- **Completed:** 2026-10-09T12:52:19Z
- **Tasks:** 3/3 (1 blocking-human checkpoint approved + 2 auto)
- **Files modified:** 8 (5 created, 3 modified)

## Accomplishments

- **Day-1 unknown (b) is retired with committed evidence (D-07, Roadmap SC4).** `scripts/spike_mcp.py` lists tools and invokes one tool on **both** servers and writes `evidence/mcp-spike.json` (exit 0). The owned server exposes `normalize_case`; the borrowed `jparkerweb/mcp-sqlite@1.0.9` exposes its 8 storage tools (`db_info`, `query`, `list_tables`, `get_table_schema`, `create_record`, `read_records`, `update_records`, `delete_records`) and answered a real `db_info` call.
- **The era-collapse trap is avoided by construction.** Each server is reached through its **own** `MCPAdapter` context — the modern owned server and the legacy borrowed server never share one `MCPConfig`, so the fleet is not dropped to a single (legacy) protocol era (01-RESEARCH Pattern 3).
- **The World A↔B swap is contained to one module (D-04, SOLID: D).** `mcp/adapter.py` is the **only** module that names `MCPAdapter`; the graph-facing surface is exactly `load_tools() -> list[BaseTool]`, and the borrowed storage server is reached via a sibling `load_borrowed_tools()` in a separate context.
- **The owned tool contract is regression-tested offline.** `tests/test_mcp_server.py` drives the owned server through the SDK's **in-memory** client and asserts the payload validates back to the one shared `ExtractionResult` schema (D-14) — so server and model contracts cannot drift.
- **QUAL-01 / D-13 are now executable, not advisory.** `tests/test_purity.py` parses every `core/**.py` with `ast` and fails if any imports `llm`/`mcp`/`store` in **any** form (absolute or relative); a non-vacuity self-test proves the guard flags each forbidden form. `tests/test_no_duplicated_sats.py` loads every leaf of `data/*.yaml` **through the one loader** and fails if a discriminating scoring value reappears under `src/`. A ruff `TID251` banned-api (scoped to `core/`) is the belt-and-braces lint-time guard.
- **The package-legitimacy gate was honoured, not bypassed.** The borrowed-server install was gated by a `blocking-human` checkpoint; fresh read-only npm metadata confirmed the pinned `mcp-sqlite@1.0.9` (repo `github.com/jparkerweb/mcp-sqlite`; benign `console.log` postinstall) and the human approved it before any install (T-01-SC).

## Task Commits

Each task was committed atomically:

1. **Task 1: Approve the borrowed SQLite MCP server package before install** — `checkpoint:human-verify` (blocking-human) — **approved** (`mcp-sqlite@1.0.9`); no commit (no code).
2. **Task 2: Owned-server contract, DIP seam, and the borrowed-server handshake spike** — `97ec0da` (feat)
3. **Task 3: Executable DRY and purity guards** — `ff65735` (test)

**Plan metadata:** committed together with this SUMMARY and STATE.md (docs: complete plan)

## Files Created/Modified

- `src/triagedesk/mcp/adapter.py` — the ONE wiring module: `load_tools()` (graph DIP seam) + `load_borrowed_tools()`/`borrowed_server_config()` (separate borrowed context, pinned `mcp-sqlite@1.0.9`)
- `src/triagedesk/mcp/server.py` — owned SDK-v2 `MCPServer` versioned; single contract-typed `normalize_case` tool
- `scripts/spike_mcp.py` — D-07 MCP handshake spike (lists + calls on both servers; writes the report; exits non-zero on failure)
- `tests/test_mcp_server.py` — owned tool contract regression via the in-memory MCP client (offline; model stubbed)
- `tests/test_purity.py` — AST purity guard for `core/` (D-13) + non-vacuity self-test
- `tests/test_no_duplicated_sats.py` — DRY guard for the SATS scoring substrate (one leaf-collection helper) + non-vacuity self-test
- `pyproject.toml` — ruff `TID251` banned-api for `triagedesk.llm|mcp|store`, scoped to `core/` via per-file-ignores
- `evidence/mcp-spike.json` — committed D-07 evidence: both tool lists, one real call each, World A decision

## Decisions Made

- **World A adopted (D-04).** Both handshakes succeeded through separate `MCPAdapter` contexts, so the modern `langchain.mcp.MCPAdapter` + `mcp==2.3.0` stack is retained; World B remains the documented one-module fallback.
- **The borrowed loader lives in `adapter.py`.** The plan requires the spike to reach the borrowed server through a separate adapter context *and* requires `adapter.py` to be the only module naming `MCPAdapter`; a sibling `load_borrowed_tools()` satisfies both while `load_tools()` stays the graph seam.
- **DRY guard scope: scoring substrate only.** The guard exempts `core/schema.py`'s input-domain `Literal` enums (`mobility`, `avpu`) and its plausible-range bounds — these are input-domain constraints, not scoring bands (a distinct concern; the guard docstring warns a future reader not to "fix" it by moving the enums into the YAML).
- **Numeric guard targets *discriminating* values.** Single-digit band points (0–3) are ubiquitous in ordinary code, so the numeric guard scans band edges with a fractional part or ≥ 2 significant digits (minus plausible-range bounds); single-digit band integrity is covered by the data-driven band-edge tests.
- **ruff `TID251` scoped to `core/`.** A global ban on `triagedesk.llm|mcp|store` would flag legitimate `mcp → llm` imports, so the ban is disabled outside `core/` via per-file-ignores; the AST test remains authoritative.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added the borrowed-server loader to `mcp/adapter.py`**
- **Found during:** Task 2
- **Issue:** The plan requires the spike to reach the borrowed server through a *separate adapter context*, and its `key_link` requires `mcp/adapter.py` to be the ONLY module that names `MCPAdapter`. Without a loader there, the spike would have to name `MCPAdapter` directly — violating the containment contract.
- **Fix:** Added `load_borrowed_tools()` + `borrowed_server_config()` to `adapter.py` (each in its own context); `load_tools()` remains the graph-facing DIP seam.
- **Files modified:** `src/triagedesk/mcp/adapter.py`
- **Verification:** `grep -rn "MCPAdapter" src/ --include="*.py"` returns only `adapter.py`; the spike lists/calls both servers.
- **Committed in:** `97ec0da`

**2. [Rule 1 - Bug] `CallToolResult.is_error`, not `isError`**
- **Found during:** Task 2 (test)
- **Issue:** The SDK v2 `CallToolResult` field is `is_error` (snake_case); the test used `isError`, raising `AttributeError`.
- **Fix:** Asserted `not result.is_error`.
- **Files modified:** `tests/test_mcp_server.py`
- **Verification:** `uv run pytest tests/test_mcp_server.py` passes.
- **Committed in:** `97ec0da`

**3. [Rule 3 - Blocking] ruff banned-api needed per-file-ignores to scope `TID251` to `core/`**
- **Found during:** Task 3
- **Issue:** The plan's ruff config bans `triagedesk.llm|mcp|store` globally, but `mcp/server.py` legitimately imports `triagedesk.llm.client` — a global ban would fail the lint on correct code.
- **Fix:** Added `[tool.ruff.lint.per-file-ignores]` disabling `TID251` outside `core/`, so the lint enforces the same boundary the AST test enforces.
- **Files modified:** `pyproject.toml`
- **Verification:** A synthetic `from triagedesk.llm import client` under `core/` raises `TID251`; the real tree lints without new errors.
- **Committed in:** `ff65735`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 bug, 1 blocking)
**Impact on plan:** All three are necessary for correctness and for the plan's own containment/guard contracts. No scope creep.

## Issues Encountered

- **Pre-existing lint findings (out of scope).** `ruff check .` reports `F841` in `scripts/spike_model.py` and `E501` in `src/triagedesk/llm/prompts.py` — all from Plan 01-01, already logged in `deferred-items.md`. Per the scope boundary they were **not** fixed; every file touched by this plan lints clean.
- **First-run npm fetch latency.** The borrowed server's first `npx -y mcp-sqlite@1.0.9` invocation downloaded the package (~1 min); subsequent runs are cached. The spike's `read_timeout_seconds` is not exceeded.

## User Setup Required

- **Blocking package-legitimacy checkpoint (Task 1) — APPROVED.** The human confirmed the pinned `mcp-sqlite@1.0.9` (source repo `github.com/jparkerweb/mcp-sqlite`; `postinstall` is a benign `console.log` message) before any install. `rusq/mcp-sqlite` remains the pre-approved fallback (not needed).
- **Runtime:** `npm`/`npx` must be on PATH to fetch the borrowed server; the local Ollama server must be running for the owned tool's real extraction (the pytest uses a stub, so the suite stays offline).

## Known Stubs

None. The `tests/test_mcp_server.py` model stub is a deliberate test double (the real end-to-end call is covered by `scripts/spike_mcp.py`), not a product stub.

## Threat Flags

None — no new trust-boundary surface beyond the plan's `<threat_model>` (the borrowed subprocess is already T-01-03-01; the purity/DRY boundaries are T-01-03-02/03).

## Next Phase Readiness

- **D-04/D-07 are retired:** `mcp/adapter.py` is the single swap point and World A is proven on both servers. Phase 3 can consume `load_tools()` as the graph's tool seam.
- **QUAL-01 is executable:** the purity and DRY guards are wired into `pytest` (47 tests pass), so a forbidden import or a duplicated SATS value now fails CI.
- **Carried forward:** Plan 01-04 (pins/`uv.lock` ownership, `core/hashing.py`, `NOTICE`) and the residual SATS transcription uncertainty flagged in `evidence/sats-verification.md`.
- **Note for Phase 3:** `load_borrowed_tools()` is storage-facing; the gated write stays in the owned `commit_priority` tool (D-06).

---

*Phase: 01-sats-foundations-risk-retirement*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 5 created key files exist on disk (`scripts/spike_mcp.py`, `tests/test_mcp_server.py`, `tests/test_purity.py`, `tests/test_no_duplicated_sats.py`, `evidence/mcp-spike.json`).
- Both task commits are ancestors of HEAD: `97ec0da`, `ff65735`.
- `uv run pytest -q` → 47 passed; `scripts/spike_mcp.py` exits 0; `grep MCPAdapter src/` → only `adapter.py`.
- Working tree clean (no untracked files; `triage.db` is gitignored).
