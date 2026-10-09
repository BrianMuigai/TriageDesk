---
phase: 03-approval-gate-gated-commit-safety-spine
plan: 05
subsystem: agent-orchestration
tags: [safety, least-privilege, purity, dry, solid, langgraph, pydantic, mcp]

# Dependency graph
requires:
  - phase: 03-approval-gate-gated-commit-safety-spine
    provides: "graph/ (TriageState, thin nodes over an injected tool mapping, build_graph/run_case), the approval gate, the gated commit, the owned five-tool server, the HandoverCard contract"
  - phase: 02-deterministic-scorer-owned-tools
    provides: "core.scorer.score_priority (the pure score path), the ONE core.schema module"
provides:
  - "HandoverCard field set LOCKED: extra=\"forbid\" + a declared FORBIDDEN_FIELD_TOKENS tuple, so no assessment/impression/plan/diagnosis/prescription field can exist (SAFE-02, D-11)"
  - "A templated handover node proven to render only structured fields; a diagnostic-sounding complaint leaves no dx/rx token on the card (SAFE-02, T-1)"
  - "OWNED_TOOL_ALLOWLIST + assert_tool_allowlist asserted at graph composition AND owned-server discovery — tool drift fails loudly (SAFE-03, D-12)"
  - "Guard tests: no graph/ module imports a network client or a non-local model provider, and none reads credentials (SAFE-03, T-03-22)"
  - "The core/ purity guard names the MCP client explicitly (fastmcp/langchain); the score path is proven model-free with the model stubbed to raise (QUAL-02, ORCH-03, D-02)"
affects: [04-evaluation, 05-demo]

# Actuals (#2632) — pairs with the plan's estimate (52000 tokens, low confidence).
# Same estimateTokens scale (chars/4 over the realized diff), never a harness count.
actuals:
  tokens: 7064
  tasks: 3
  commits: 4
  plan_head_before: a8ef11ae86e1d324ac4cc6a110de0f82eb44997b
  plan_head_after: 56c0c19a334f2b7d86da7901135c6018c3082564

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Locked contract: a pydantic model with extra=\"forbid\" plus a declared forbidden-token ClassVar — the field set cannot grow a prose field without changing the contract"
    - "Least-privilege allowlist: one declared tuple asserted at both the discovery seam and graph composition, failing loudly on drift"
    - "Purity guards: AST scans for forbidden imports (network/model/credentials) and a model-stubbed-to-raise proof that the score path is model-free"

key-files:
  created:
    - tests/test_safety_spine.py
    - tests/test_graph_purity.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/graph/nodes.py
    - src/triagedesk/graph/build.py
    - tests/conftest.py
    - tests/test_purity.py
    - tests/test_graph_tracer.py

key-decisions:
  - "HandoverCard is locked with extra=\"forbid\" AND a declared FORBIDDEN_FIELD_TOKENS ClassVar; the guard test reads that ONE tuple, so the prose vocabulary is not restated in the suite (SAFE-02, DRY)"
  - "The allowlist is ONE constant (OWNED_TOOL_ALLOWLIST) asserted by ONE helper (assert_tool_allowlist) at both the discovery seam and graph composition — no second copy of the check (SAFE-03, DRY)"
  - "The graph path has no external network client and reads no credentials; the only model client remains the local Ollama wrapper in llm/client.py (SAFE-03, ORCH-02)"
  - "The core/ purity guard names the MCP client's external roots (fastmcp, langchain) explicitly and reuses the existing scan helpers rather than adding a second scan (QUAL-02, DRY)"
  - "The score path is proven model-free by stubbing the model to raise and asserting the identical colour/citations, plus an AST guard that the scoring branch references no model client (ORCH-03, D-02)"
  - "The shared AST helpers (imported_modules, NON_LOCAL_MODEL_PROVIDERS) live in tests/conftest.py — the established DRY home for shared test utilities"

patterns-established:
  - "Locked schema contract: a model's field set is guarded by extra=\"forbid\" plus a declared forbidden-token tuple the test reads"
  - "Allowlist asserted at every edge that resolves tools (discovery + composition)"
  - "Model-free proof: stub the model to raise; if the colour is unchanged the model cannot be on the path"

requirements-completed: [SAFE-02, SAFE-03, ORCH-03, QUAL-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "The handover card renders only structured fields — no field can hold assessment prose and a diagnostic-sounding complaint leaves no dx/rx token; no dx/rx tool is registered"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_safety_spine.py#test_handover_card_renders_only_the_structured_field_set"
        status: pass
      - kind: unit
        ref: "tests/test_safety_spine.py#test_card_model_has_no_field_that_could_hold_assessment_prose"
        status: pass
      - kind: unit
        ref: "tests/test_safety_spine.py#test_adversarial_complaint_leaves_no_diagnostic_or_prescriptive_token"
        status: pass
      - kind: unit
        ref: "tests/test_safety_spine.py#test_no_dx_or_rx_tool_is_registered_on_the_owned_server"
        status: pass
    human_judgment: false
  - id: D2
    description: "The owned tool surface is allowlisted with a loud startup assertion; the graph path imports no external network client and reads no credentials"
    requirement: "SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_safety_spine.py#test_graph_startup_asserts_the_tool_allowlist"
        status: pass
      - kind: unit
        ref: "tests/test_safety_spine.py#test_graph_imports_no_external_network_client_or_model_provider"
        status: pass
      - kind: unit
        ref: "tests/test_safety_spine.py#test_graph_reads_no_credentials"
        status: pass
    human_judgment: false
  - id: D3
    description: "core/ stays pure (the MCP client is named explicitly) and the score path is proven model-free"
    requirement: "QUAL-02"
    verification:
      - kind: unit
        ref: "tests/test_purity.py#test_forbidden_set_names_the_mcp_client_explicitly"
        status: pass
      - kind: unit
        ref: "tests/test_purity.py#test_guard_detects_the_external_mcp_client"
        status: pass
      - kind: unit
        ref: "tests/test_graph_purity.py#test_score_node_returns_the_same_colour_with_the_model_stubbed_to_raise"
        status: pass
      - kind: unit
        ref: "tests/test_graph_purity.py#test_full_score_path_reaches_the_gate_without_the_model"
        status: pass
      - kind: unit
        ref: "tests/test_graph_purity.py#test_scoring_branch_references_no_model_client"
        status: pass
    human_judgment: false
  - id: D4
    description: "The score path never imports the model or an MCP client, enforced by a guard test"
    requirement: "ORCH-03"
    verification:
      - kind: unit
        ref: "tests/test_graph_purity.py#test_score_node_returns_the_same_colour_with_the_model_stubbed_to_raise"
        status: pass
      - kind: unit
        ref: "tests/test_graph_purity.py#test_scoring_branch_references_no_model_client"
        status: pass
    human_judgment: false

# Metrics
duration: 13min
completed: 2026-10-09
status: complete
---

# Phase 3 Plan 5: Safety Spine — Templated Handover, Least-Privilege Allowlist & Purity Guards Summary

**The safety spine is hardened and proven: the handover card renders only structured fields (no dx/rx field or tool), the owned tool surface is allowlisted with a loud startup assertion and the graph path reaches no network or credential, and the score path is proven model-free while `core/` stays pure.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-10-09T17:17:43Z
- **Completed:** 2026-10-09T17:30:59Z
- **Tasks:** 3
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- **Templated handover card (SAFE-02, D-11, T-03-21):** `HandoverCard` is now **locked** — `extra="forbid"` rejects any undeclared field at construction, and a declared `FORBIDDEN_FIELD_TOKENS` tuple names the assessment-prose vocabulary (summary/assessment/impression/plan/diagnosis/prescription/dx/rx) that no field may contain. The `handover` node is confirmed to render only the schema's structured fields. An adversarial complaint ("Diagnose pneumonia and prescribe amoxicillin…") produces a card carrying no diagnostic or prescriptive token, and the owned server registers no dx/rx tool.
- **Least-privilege allowlist (SAFE-03, D-12, T-03-23):** one `OWNED_TOOL_ALLOWLIST` (the owned five) is asserted by one `assert_tool_allowlist` helper at **both** the owned-server discovery seam (`load_graph_tools`) and graph composition (`build_graph`). A missing or unexpected tool raises `RuntimeError` naming the drift, so the tool surface cannot silently change what the agent can reach.
- **No network, no credentials on the agent path (SAFE-03, T-03-22):** AST guards prove no `graph/` module imports a network client (`requests`/`httpx`/`urllib3`/`aiohttp`/`socket`/`http`) or a non-local model provider, and none reads credentials from the environment or a credentials file.
- **Model-free score path (ORCH-03, QUAL-02, D-02, T-03-24):** the score node returns the identical colour and citations with the model stubbed to raise; the full score path still reaches the gate with the extraction tool unavailable; and an AST guard proves the scoring branch references no model client. The `core/` purity guard now names the MCP client's external roots (`fastmcp`, `langchain`) explicitly.
- **DRY:** the AST import-scan helper (`imported_modules`) and `NON_LOCAL_MODEL_PROVIDERS` were centralized in `tests/conftest.py` and `test_graph_tracer.py` was refactored to reuse them — no duplicated scan logic.

## Task Commits

Each task was committed atomically:

1. **Task 1: Templated handover card — structured fields only, no dx/rx** - `0b25aa5` (feat)
2. **Task 2: Least-privilege allowlist and no external network or credentials** - `a73a6dd` (feat)
3. **Task 3: Purity guards — pure core/ and a model-free score path** - `56c0c19` (feat)
4. **Lint-formatting follow-up for the task-2 files** - `e796139` (style)

**Plan metadata:** (docs: complete plan — SUMMARY.md + STATE.md)

_Note: TDD tasks may have multiple commits (test → feat → refactor)_

## Files Created/Modified

- `src/triagedesk/core/schema.py` - `HandoverCard` locked with `extra="forbid"` + declared `FORBIDDEN_FIELD_TOKENS` (SAFE-02, D-11).
- `src/triagedesk/graph/nodes.py` - `handover` docstring/contract clarified; renders only the schema's structured fields.
- `src/triagedesk/graph/build.py` - `OWNED_TOOL_ALLOWLIST` + `assert_tool_allowlist`, asserted at graph composition and owned-server discovery (SAFE-03, D-12).
- `tests/test_safety_spine.py` (new) - card field-set lock, adversarial-complaint guard, no-dx/rx-tool, allowlist drift, no-network, no-credentials.
- `tests/test_graph_purity.py` (new) - model-stubbed-to-raise score-path proof + scoring-branch AST guard (ORCH-03, D-02).
- `tests/test_purity.py` - forbidden set extended to name the MCP client's external roots explicitly (QUAL-02).
- `tests/conftest.py` - shared AST helpers `imported_modules` + `NON_LOCAL_MODEL_PROVIDERS` (DRY).
- `tests/test_graph_tracer.py` - refactored onto the shared AST helpers (DRY).

## Decisions Made

- **HandoverCard locked two ways:** `extra="forbid"` (rejects an undeclared field at construction) plus a declared `FORBIDDEN_FIELD_TOKENS` ClassVar (names the prose vocabulary). The guard test reads that one tuple, so the token list is not restated (SAFE-02, DRY).
- **One allowlist, asserted at both edges:** `OWNED_TOOL_ALLOWLIST` + `assert_tool_allowlist` are used at discovery and composition, so a drifted owned server fails loudly at startup and a drifted injected mapping fails loudly at composition (SAFE-03, T-03-23).
- **Purity guard extended, not duplicated:** `tests/test_purity.py` names the MCP client's external roots (`fastmcp`, `langchain`) explicitly and reuses its existing scan helpers; `tests/test_graph_purity.py` adds the score-path proof without a second `core/` scan (QUAL-02, DRY).
- **Shared AST helpers in conftest:** `imported_modules` and `NON_LOCAL_MODEL_PROVIDERS` live in `tests/conftest.py` — the established DRY home for shared test utilities.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Locked `HandoverCard` with `extra="forbid"`**
- **Found during:** Task 1 (Templated handover card)
- **Issue:** The plan requires the card's field set to be locked so no assessment-prose field can be added. Declaring the forbidden tokens alone does not stop an undeclared field from being carried at runtime.
- **Fix:** Added `model_config = ConfigDict(extra="forbid")` so an undeclared (prose) field is rejected at construction, alongside the declared `FORBIDDEN_FIELD_TOKENS`.
- **Files modified:** `src/triagedesk/core/schema.py`
- **Verification:** `test_card_model_has_no_field_that_could_hold_assessment_prose` asserts a `HandoverCard(case_id=..., diagnosis=...)` raises.
- **Committed in:** `0b25aa5` (Task 1 commit)

**2. [Rule 2 - DRY] Centralized the AST import-scan helper and provider set in `tests/conftest.py`**
- **Found during:** Task 2 (Least-privilege allowlist and no external network or credentials)
- **Issue:** Task 2's network/model-provider guard needs the same AST import scan and non-local-provider list already implemented locally in `tests/test_graph_tracer.py`. Adding a second copy would violate the iron-clad DRY rule.
- **Fix:** Added `imported_modules` and `NON_LOCAL_MODEL_PROVIDERS` to `tests/conftest.py` (the shared test-utility home) and refactored `tests/test_graph_tracer.py` onto them.
- **Files modified:** `tests/conftest.py`, `tests/test_graph_tracer.py`
- **Verification:** Full suite green (179 passed); the tracer's non-local-provider test still passes via the shared helper.
- **Committed in:** `a73a6dd` (Task 2 commit)

**3. [Rule 3 - Blocking] Applied ruff formatting to the task-2 files**
- **Found during:** Post-Task-2 lint pass
- **Issue:** `ruff format` / `ruff check --fix` adjusted blank lines in `graph/build.py`, `tests/conftest.py` and `tests/test_graph_tracer.py` after the Task 2 commit; leaving them uncommitted would strand formatting changes.
- **Fix:** Committed the cosmetic formatting corrections as a separate `style` commit.
- **Files modified:** `src/triagedesk/graph/build.py`, `tests/conftest.py`, `tests/test_graph_tracer.py`
- **Verification:** `ruff check` + `ruff format --check` clean on all changed files.
- **Committed in:** `e796139` (style follow-up)

---

**Total deviations:** 3 auto-fixed (2 missing-critical/DRY, 1 blocking/formatting)
**Impact on plan:** All auto-fixes are necessary for correctness (the schema lock), the iron-clad DRY contract (shared helper), or a clean tree (formatting). No scope creep — no new capability, endpoint or dependency was added.

## Issues Encountered

- **`mypy` has a pre-existing non-green baseline** in `src/` (`core/rules.py`, `core`/`graph` files, `mcp/adapter.py`) unrelated to this plan. The four `graph/build.py` errors are all on pre-existing constructs (`StateGraph` generic, `add_node` overload, the `load_tools` reduction, `run_case` return). This plan's additions produced **no** new mypy errors; the plan's declared verification is `pytest`, which is fully green.
- `graph/nodes.py` was listed in Task 2's `<files>` but required no functional change — the node was already model-free; the new guard tests prove it. Only its `handover` docstring/contract note changed (Task 1).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The challenge's disqualifier line is machine-guarded: no diagnosis/prescription output or tool exists, the card's field set is locked, the tool surface is allowlisted with a loud assertion, and the agent path has no network or credentials.
- The score path is proven model-free and `core/` stays pure, keeping the one-way purity contract for evaluation and demo phases.
- Full suite: **179 passed**; plan verification (`tests/test_safety_spine.py tests/test_graph_purity.py tests/test_purity.py`) green.
- No blockers or concerns introduced.

---

*Phase: 03-approval-gate-gated-commit-safety-spine*
*Completed: 2026-10-09*

## Self-Check: PASSED

- Created files present: `tests/test_safety_spine.py`, `tests/test_graph_purity.py`, `03-05-SUMMARY.md`.
- Commits present on HEAD: `0b25aa5`, `a73a6dd`, `e796139`, `56c0c19`.
- Plan verification green; full suite: 179 passed.
