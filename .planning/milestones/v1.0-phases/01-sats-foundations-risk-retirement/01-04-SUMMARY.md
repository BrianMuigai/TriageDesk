---
phase: 01-sats-foundations-risk-retirement
plan: 04
subsystem: infra
tags: [hashing, sha256, reproducibility, uv-lock, notice, licensing, sats, safe-04, d-17]

# Dependency graph
requires:
  - plan: "01-01"
    provides: "uv/Python-3.12 scaffold, core/schema.py (CaseInput/ExtractionResult), llm/prompts.py (EXTRACTION_PROMPT), committed uv.lock, evidence/model-spike.json"
  - plan: "01-02"
    provides: "data/sats_tews.yaml + data/sats_discriminators.yaml single source of truth, core/rules.py loaders"
provides:
  - "core/hashing.py — the ONE canonical sha256 helper over normalised (sorted-key JSON) inputs (SAFE-04, D-17)"
  - "tests/test_hashing.py — normalisation contract: key reorder / comment+whitespace edits do not churn; real edits do"
  - "scripts/hash_data.py — hashes data/*.yaml, the prompt template and the tool schemas; exits non-zero on a missing input"
  - "evidence/hashes.json — the version manifest (model tag + data/prompts/schemas digests) every Phase-3 audit record names"
  - "NOTICE — every third-party licence (Python deps, both Qwen model tags, borrowed mcp-sqlite, SATS/EMSSA attribution)"
  - "uv.lock — re-verified current from the pinned pyproject.toml (reproducibility artifact, Roadmap SC5)"
affects: [phase-2, phase-3, phase-4]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 36000, raw_tokens: 28000, tasks: 2).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 4228         # chars/4 over the full realized diff (16,912 chars)
  raw_tokens: 3739     # chars/4 over the 4 authored files (14,959 chars, excl. generated evidence/hashes.json)
  tasks: 2
  commits: 2           # MEASURED: git rev-list --count plan_head_before..HEAD
  plan_head_before: e5e265f86ea872b99b2ed9122f946ef0db4c8b73
  plan_head_after: 06f6a1fe634220b82164cd2f608ff57be185204e

tech-stack:
  added: []
  patterns:
    - "One canonical hashing path: every value (rule object, prompt string, tool schema) funnels through hash_value"
    - "Hash the NORMALISED structure, never raw file bytes — comments/whitespace do not churn; only real content changes do"
    - "Version manifest as an artefact (evidence/hashes.json) that later audit records name (D-17)"

key-files:
  created:
    - src/triagedesk/core/hashing.py
    - tests/test_hashing.py
    - scripts/hash_data.py
    - evidence/hashes.json
    - NOTICE
  modified: []

key-decisions:
  - "Canonical form = sorted-key, compact-separator JSON encoded UTF-8 then sha256: the digest is independent of dict insertion order and of YAML comments/whitespace (01-RESEARCH Open Question #4)."
  - "Three typed entry points (hash_rule_object / hash_prompt / hash_tool_schema) all delegate to the single hash_value path, so no caller hashes by hand (DRY)."
  - "The script hashes data/*.yaml through the one loader where a loader exists (core/rules.py), falling back to a normalised YAML load for a future data file, so 'every data/*.yaml' stays true."
  - "The prompt is hashed as its declared template constant (EXTRACTION_PROMPT), not the module's raw bytes — a comment edit in prompts.py does not churn the digest (matches the key_link)."
  - "uv.lock was already committed by Plan 01-01; Task 2's deliverable was to regenerate/verify it — `uv lock` resolved 115 packages with zero diff, so the lockfile is current (no spurious churn)."
  - "NOTICE licence facts were read from installed package metadata (importlib.metadata) and npm metadata, not recalled — mcp-sqlite@1.0.9 is ISC; qwen2.5:1.5b/qwen3.5:4b recorded as Apache-2.0 per evidence/model-spike.json."

patterns-established:
  - "Reproducibility as an artefact: evidence/hashes.json + uv.lock together pin the clinical substrate and the dependency graph"
  - "Tamper-evidence: a silent edit to data/ or a prompt is now detectable by re-running scripts/hash_data.py"

requirements-completed: [SAFE-04]

coverage:
  - id: D1
    description: "One canonical hashing helper produces a stable sha256 digest over normalised data/prompt/schema inputs; key reordering and comment/whitespace edits do not change it, a real value change does (SAFE-04, D-17)."
    requirement: "SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_hashing.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/hash_data.py writes evidence/hashes.json recording the model tag plus the digests of the data substrate, the prompt template and the tool schemas, and exits non-zero when a required input is missing (SAFE-04, D-17)."
    requirement: "SAFE-04"
    verification:
      - kind: automated
        ref: "uv run python scripts/hash_data.py --out evidence/hashes.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "NOTICE records every third-party licence — the Python dependencies, the selected and fallback model tags, the borrowed SQLite MCP server, and the SATS/EMSSA attribution with the explicit 'cited, not redistributed wholesale' line (Roadmap SC5, Pitfall 5, DQ-8)."
    requirement: "SAFE-04"
    verification:
      - kind: other
        ref: "grep -q 'qwen2.5:1.5b' NOTICE && grep -q 'EMSSA' NOTICE && grep -q 'cited, not redistributed' NOTICE"
        status: pass
    human_judgment: true
    rationale: "Completeness and accuracy of the licence disclosure is a challenge-compliance judgment (instant-disqualifier DQ-8); automation can prove the model licence and SATS attribution are present, but a human should confirm no third-party component was missed."
  - id: D4
    description: "The build is reproducible from the committed uv.lock on pinned Python 3.12: `uv lock`/`uv sync` resolve the same 115-package graph (Roadmap SC5)."
    verification:
      - kind: automated
        ref: "uv lock && uv sync"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-09
status: complete
---

# Phase 1 Plan 04: Canonical Hashing, Reproducible Build & Licence NOTICE Summary

**The clinical substrate is now tamper-evident and the build is reproducible: one canonical `sha256` helper hashes the loaded rule objects, the prompt template and the tool schemas into `evidence/hashes.json` (with the `qwen2.5:1.5b` model tag), a committed `uv.lock` pins the 115-package graph on Python 3.12, and a `NOTICE` records every third-party licence plus the SATS/EMSSA attribution.**

## Performance

- **Duration:** ~4 min (12:59Z → 13:04Z)
- **Started:** 2026-10-09T12:59:42Z
- **Completed:** 2026-10-09T13:03:57Z
- **Tasks:** 2/2
- **Files modified:** 5 created (0 modified)

## Accomplishments

- **SAFE-04 / D-17 are satisfied by one helper.** `core/hashing.py` normalises a value (Pydantic model → JSON dump; sorted keys; compact separators; UTF-8) and returns a stable `sha256` hex digest. `hash_rule_object`, `hash_prompt` and `hash_tool_schema` all funnel through the single `hash_value` path — no caller hashes by hand.
- **The digest is stable under normalisation, and only under normalisation.** `tests/test_hashing.py` (10 tests) proves key reordering does not change the digest, that two YAML fixtures differing only by comments/blank lines/spacing load to the same digest, and that a single changed value **does** change it (01-RESEARCH Open Question #4).
- **The version manifest exists for every later audit record to name (D-17).** `scripts/hash_data.py` hashes every `data/*.yaml` (through the one loader), the `EXTRACTION_PROMPT` template, and the `CaseInput`/`ExtractionResult` tool schemas, then writes `evidence/hashes.json` with the selected model tag and its licence. It **exits non-zero** when a required input is missing (verified by temporarily removing a data file → exit 1).
- **The build is reproducible (Roadmap SC5).** `uv lock` resolves 115 packages from the pinned `pyproject.toml` with zero diff against the committed `uv.lock`; `uv sync` is clean on the pinned Python 3.12.
- **The licensing control is in place (Pitfall 5, DQ-8).** `NOTICE` lists every third-party licence — Python runtime/transitive/dev dependencies, both Qwen model tags, the borrowed `mcp-sqlite@1.0.9` — and the SATS/EMSSA attribution with the explicit statement that clinical content is **cited, not redistributed wholesale**.

## Task Commits

Each task was committed atomically:

1. **Task 1: Canonical hashing helper for data, prompts and schemas** - `d1a2797` (feat)
2. **Task 2: Lock the build, hash the substrate, and record the NOTICE** - `06f6a1f` (feat)

**Plan metadata:** committed together with this SUMMARY and STATE.md (docs: complete plan)

## Files Created/Modified

- `src/triagedesk/core/hashing.py` — the ONE canonical `sha256` helper: `canonical_json` + `hash_value` + three typed entry points; pure (stdlib + pydantic only, D-13)
- `tests/test_hashing.py` — 10 offline tests: digest shape, key-reorder invariance, YAML comment/whitespace invariance, real-change sensitivity, loaded-rule and tool-schema hashing, shared-path equality
- `scripts/hash_data.py` — builds and writes the manifest; loads `data/*.yaml` through `core/rules.py`, hashes the prompt module's declared templates and the schema module's `model_json_schema()`; exits non-zero on a missing required input
- `evidence/hashes.json` — the committed version manifest: `model_tag` = `qwen2.5:1.5b`, `model_licence` = Apache-2.0, plus the two data, one prompt and two schema digests
- `NOTICE` — third-party licence disclosure + SATS/EMSSA attribution + synthetic-data/local-only posture
- `uv.lock` — **unchanged** (already committed by Plan 01-01); re-verified current by `uv lock`

## Decisions Made

- **Canonical form = sorted-key compact JSON, then sha256.** This makes the digest independent of dict insertion order and of YAML comments/whitespace, while a real content change still churns it — exactly the normalisation contract the plan's key_link requires.
- **Three entry points, one path.** `hash_rule_object`/`hash_prompt`/`hash_tool_schema` all delegate to `hash_value`, keeping the hashing concern in exactly one place (DRY/SOLID: S).
- **Prompts are hashed as their declared template constant**, not the module's raw bytes, so a comment edit in `llm/prompts.py` does not churn the digest (consistent with the "normalised output, not raw file bytes" key_link).
- **`uv.lock` was already current.** Plan 01-01 committed it; Task 2 regenerated/verified it with zero diff. Forcing a rewrite would have been spurious churn, so the lockfile was left byte-identical and its currency is the verified outcome.
- **NOTICE licence facts were read from installed metadata** (`importlib.metadata`) and npm metadata rather than recalled — e.g. `mcp-sqlite@1.0.9` is **ISC**; `pytest-asyncio` is Apache-2.0; the Qwen tags are recorded as Apache-2.0 per `evidence/model-spike.json`.

## Deviations from Plan

None — plan executed exactly as written.

The plan's Task 2 listed `uv.lock` as a deliverable "to generate and commit"; it was already generated and committed by Plan 01-01 (which the 01-01 SUMMARY explicitly notes: "uv.lock — committed resolution (reproducibility artifact; formally owned by Plan 01-04)"). Task 2 regenerated it with `uv lock` (zero diff) and confirmed `uv sync` reproducibility — so the deliverable is met without a spurious change.

## Issues Encountered

- **Branching context (not a deviation).** `.planning/config.json` sets `git.branching_strategy: "none"` and `workflow.use_worktrees: false`, and the orchestrator directed execution in the main working tree. Commits were therefore made on the default branch, consistent with the three prior Plan 01-0x commits on the same branch.
- **Pre-existing lint findings (out of scope).** The repo's known `F841`/`E501` findings from Plan 01-01 remain untouched (logged in `deferred-items.md`); every file created by this plan lints clean (`ruff check` passes on `hashing.py`, `test_hashing.py`, `hash_data.py`).

## User Setup Required

None — stdlib + already-installed dependencies only; no new installs, no external services. The manifest and lockfile are produced offline.

## Next Phase Readiness

- **SAFE-04 / D-17 are executable:** `evidence/hashes.json` is the version manifest Phase 3's audit records will name; re-running `scripts/hash_data.py` detects any silent edit to `data/` or a prompt (T-01-04-01 mitigated).
- **Roadmap SC5 is satisfied:** a clean clone rebuilds identically from the committed `uv.lock` on Python 3.12, and `NOTICE` discloses every third-party licence (T-01-04-02/T-01-SC mitigated).
- **Carried forward:** the residual SATS transcription uncertainty flagged in `evidence/sats-verification.md` and `docs/SATS.md`; the NOTICE's licence-list completeness is flagged for human confirmation in the D3 coverage entry.
- Phase 1 is complete after this plan — all four plans (tracer + model fit, rule substrate, MCP/purity guards, hashing/reproducibility) are done.

---

*Phase: 01-sats-foundations-risk-retirement*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 5 created key files exist on disk (`core/hashing.py`, `tests/test_hashing.py`, `scripts/hash_data.py`, `evidence/hashes.json`, `NOTICE`).
- Both task commits are ancestors of HEAD: `d1a2797`, `06f6a1f`.
- `uv run pytest -q` → 58 passed; `scripts/hash_data.py` exits 0; missing-input path exits 1; `uv sync` clean.
- Working tree clean after the metadata commit.
