---
phase: 01-sats-foundations-risk-retirement
verified: 2026-10-09T13:29:26Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - .gitignore
  - .planning/phases/01-sats-foundations-risk-retirement/01-01-PLAN.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-01-SUMMARY.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-02-PLAN.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-02-SUMMARY.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-03-PLAN.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-03-SUMMARY.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-04-PLAN.md
  - .planning/phases/01-sats-foundations-risk-retirement/01-04-SUMMARY.md
  - .python-version
  - NOTICE
  - data/sats_discriminators.yaml
  - data/sats_tews.yaml
  - docs/SATS.md
  - evidence/hashes.json
  - evidence/mcp-spike.json
  - evidence/model-spike.json
  - evidence/sats-verification.md
  - evidence/sats_transcription_b.yaml
  - pyproject.toml
  - scripts/hash_data.py
  - scripts/spike_e2e.py
  - scripts/spike_mcp.py
  - scripts/spike_model.py
  - scripts/transcribe_diff.py
  - src/triagedesk/__init__.py
  - src/triagedesk/core/__init__.py
  - src/triagedesk/core/citations.py
  - src/triagedesk/core/hashing.py
  - src/triagedesk/core/rules.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/llm/__init__.py
  - src/triagedesk/llm/client.py
  - src/triagedesk/llm/prompts.py
  - src/triagedesk/mcp/__init__.py
  - src/triagedesk/mcp/adapter.py
  - src/triagedesk/mcp/server.py
  - tests/test_hashing.py
  - tests/test_mcp_server.py
  - tests/test_no_duplicated_sats.py
  - tests/test_purity.py
  - tests/test_sats_bands.py
  - tests/test_sats_discriminators.py
  - tests/test_schema_rejects.py
  - uv.lock
covered_digest: "v3:sha256:d5121939d3441a35338e777d31a25b8d205d231bc50c83d037f812e2e675a728"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 1: SATS Foundations & Risk Retirement — Verification Report

**Phase Goal:** The published SATS rule substrate and the one typed case schema exist as the single source of truth, the project builds reproducibly, and both Day-1 unknowns are retired on evidence — the local model's schema-constrained output and the MCP beta-adapter / borrowed-server handshake.
**Verified:** 2026-10-09T13:29:26Z
**Status:** passed
**Re-verification:** No — initial verification (no prior VERIFICATION.md existed).

## Goal Achievement

### Observable Truths

| # | Truth (Roadmap success criterion) | Status | Evidence |
|---|-----------------------------------|--------|----------|
| 1 | Every TEWS band, colour threshold, discriminator and category lives in exactly one `data/*.yaml` and appears nowhere else in code/runtime | ✓ VERIFIED | `data/sats_tews.yaml` (7 parameters, both colour thresholds, `target_times`, fail-closed `out_of_scope`) and `data/sats_discriminators.yaml` (41 discriminators, 3 categories, explicit `no_match`) are the only definitions; `grep` over `src/` for band edges, temperature thresholds, colour tokens (`GREEN/YELLOW/ORANGE/RED/BLUE`) and discriminator strings returns nothing. `tests/test_no_duplicated_sats.py` enforces this executably (non-vacuity self-test included) and `tests/test_sats_bands.py` derives every edge from the data. Dual-transcription diff (`scripts/transcribe_diff.py`) reproduced: **PASS, 0 disagreements**. |
| 2 | A case (structured vitals + free-text complaint) is represented by one validated typed schema that rejects implausible values instead of imputing them | ✓ VERIFIED | `src/triagedesk/core/schema.py` is the single `CaseInput`/`ExtractionResult` definition (grep: class names appear only here). `tests/test_schema_rejects.py` proves: out-of-range values raise, a Fahrenheit-magnitude temperature (98.6 on the Celsius field) is rejected, omitted vitals stay `None`, and out-of-enum values raise. Ran `uv run pytest -q` → **58 passed**. |
| 3 | The local model returns valid schema-constrained JSON within the RAM budget (measured), and a smaller-Qwen fallback has been run end-to-end | ✓ VERIFIED | `evidence/model-spike.json` records RAM (`free -m`), `ollama ps`, cold/warm latency, licence and a validated extraction for both models; budget gate selected `qwen2.5:1.5b` (641 MB available with `qwen3.5:4b` loaded < 1024 MB budget). Independently reproduced both halves: a real `extract()` call with `qwen3.5:4b` returned a valid `ExtractionResult` (rr=24, hr=118, avpu=alert), and `scripts/spike_mcp.py` drove the default model (`qwen2.5:1.5b`) through the owned tool returning valid schema JSON. |
| 4 | The MCP adapter lists and calls tools on both the owned server and the borrowed SQLite server, with a documented World A/B decision | ✓ VERIFIED | Independently re-ran `uv run python scripts/spike_mcp.py` (exit 0): owned server lists `["normalize_case"]` and answers a real call; borrowed `mcp-sqlite@1.0.9` lists its 8 storage tools and answers `db_info`; `world_decision.world == "A"` with reason. `grep MCPAdapter src/` → only `mcp/adapter.py` (single swap point). `tests/test_mcp_server.py` regression-tests the owned contract offline. |
| 5 | A `uv`-pinned Python 3.12 rebuild is reproducible; deps, model tag, prompts, tool schemas and scale data are pinned and hashed; a NOTICE records every third-party licence | ✓ VERIFIED | `.python-version` = `3.12`; `uv.lock` committed; `uv lock --check` and `uv sync --locked` both clean (115 packages). Re-ran `scripts/hash_data.py` → byte-identical to committed `evidence/hashes.json` (2 data + 1 prompt + 2 schema digests + model tag `qwen2.5:1.5b`). `NOTICE` records runtime/transitive/dev deps, both model tags, borrowed `mcp-sqlite@1.0.9` (ISC) and the SATS/EMSSA attribution with the "cited, not redistributed wholesale" line. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/sats_tews.yaml` | Complete adult TEWS chart + thresholds + out_of_scope | ✓ VERIFIED | 7 parameters, inclusive bands, 4 colour bands, 5 target times, fail-closed predicate; loaded via `core/rules.py` |
| `data/sats_discriminators.yaml` | 41 discriminators + categories + no_match | ✓ VERIFIED | 7 emergency / 24 very-urgent / 10 urgent, unique ids, unambiguous aliases, explicit `no_match` |
| `src/triagedesk/core/schema.py` | The ONE typed schema module | ✓ VERIFIED | `CaseInput` (nullable, range-validated, `Literal` enums) + `ExtractionResult`; pure |
| `src/triagedesk/core/rules.py` | The ONE YAML loader (TEWS + discriminators) | ✓ VERIFIED | Typed pydantic models; no other module parses the YAML |
| `src/triagedesk/core/citations.py` | The ONE citation helper (D-15) | ✓ VERIFIED | `format_citation` is the only citation formatter; source supplied by caller |
| `src/triagedesk/core/hashing.py` | Canonical sha256 helper (SAFE-04) | ✓ VERIFIED | Sorted-key JSON → sha256; three typed entry points share one path; pure |
| `src/triagedesk/llm/prompts.py` | Single prompt home | ✓ VERIFIED | `EXTRACTION_PROMPT` imported by `client.py`; no inline prompt |
| `src/triagedesk/llm/client.py` | Ollama wrapper, validate-or-raise, `think=False` | ✓ VERIFIED | `format=ExtractionResult.model_json_schema()`, `think=False`, raises `ExtractionError` on empty/unparsable |
| `src/triagedesk/mcp/server.py` | Owned SDK-v2 server, one contract-typed tool | ✓ VERIFIED | `MCPServer("triagedesk-triage")` exposing `normalize_case` returning `ExtractionResult` |
| `src/triagedesk/mcp/adapter.py` | ONE DIP seam; separate borrowed context | ✓ VERIFIED | `load_tools()` + `load_borrowed_tools()`; only module naming `MCPAdapter` |
| `evidence/model-spike.json` | Measured model-fit evidence | ✓ VERIFIED | Both models, RAM/latency/licence/parsed output, selection rationale |
| `evidence/mcp-spike.json` | D-07 retirement on both servers | ✓ VERIFIED | Both tool lists, one real call each, World A decision; reproduced |
| `evidence/hashes.json` | Version manifest | ✓ VERIFIED | Reproduced byte-identical |
| `evidence/sats-verification.md` + `sats_transcription_b.yaml` | Dual-transcription evidence | ✓ VERIFIED | Independent transcription B (range-string route); diff PASS |
| `uv.lock`, `NOTICE`, `.python-version`, `pyproject.toml` | Reproducibility + licence | ✓ VERIFIED | Lock current; NOTICE complete; Python pinned 3.12 |
| `tests/test_purity.py`, `tests/test_no_duplicated_sats.py` | Executable DRY + purity guards | ✓ VERIFIED | AST guards with non-vacuity self-tests |

**Artifacts:** 16/16 verified

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `llm/client.py` | `core/schema.py` | imports `ExtractionResult` | ✓ WIRED | `from triagedesk.core.schema import ExtractionResult` |
| `llm/client.py` | `llm/prompts.py` | imports `EXTRACTION_PROMPT` | ✓ WIRED | prompt never inlined at call site |
| `mcp/server.py` | `core/schema.py` + `llm/client.py` | tool returns shared schema | ✓ WIRED | `normalize_case` returns `ExtractionResult`; regression-tested in-memory |
| `mcp/adapter.py` | owned `server.py` | `MCPAdapter(SERVER_PATH)` (Path) | ✓ WIRED | stdio subprocess launched; `load_tools()` lists/calls it (reproduced) |
| `mcp/adapter.py` | borrowed `mcp-sqlite@1.0.9` | `load_borrowed_tools()` separate context | ✓ WIRED | 8 tools listed, `db_info` answered (reproduced) |
| `scripts/hash_data.py` | `core/hashing.py` | one hashing path | ✓ WIRED | no ad-hoc hashing |
| `scripts/transcribe_diff.py` | `core/rules.py` | loads A through the one loader | ✓ WIRED | diff exits non-zero on disagreement |
| `core/` | `llm`/`mcp`/`store` | forbidden | ✓ WIRED (absent by design) | AST purity test + ruff TID251 |

**Wiring:** 8/8 connections verified

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `llm/client.py` → owned `normalize_case` | `ExtractionResult` | Real local Ollama call (`format=schema`, `think=False`) | Yes — reproduced live (rr=24, hr=118, avpu=alert, complaint preserved) | ✓ FLOWING |
| `mcp/adapter.py` borrowed tools | `db_info` result | Real `npx -y mcp-sqlite@1.0.9 <db>` subprocess | Yes — real DB metadata returned | ✓ FLOWING |
| `core/rules.py` | `TewsRules` / `DiscriminatorRules` | `data/*.yaml` on disk | Yes — 7 params / 41 discriminators loaded | ✓ FLOWING |

No static/hardcoded return paths found; no mock in the product path (the model stub lives only in the offline regression test).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `uv run pytest -q` | 58 passed in 0.95s | ✓ PASS |
| Dual-transcription diff | `uv run python scripts/transcribe_diff.py` | PASS — 7 params, 4 thresholds, 41 discriminators, 0 disagreements; exit 0 | ✓ PASS |
| Hash manifest reproducibility | `uv run python scripts/hash_data.py --out /tmp/...` + diff | byte-identical to `evidence/hashes.json`; exit 0 | ✓ PASS |
| MCP handshake (both servers) | `uv run python scripts/spike_mcp.py` | owned + borrowed tool lists and one call each; World A; exit 0 | ✓ PASS |
| Tracer end-to-end | `uv run python scripts/spike_e2e.py` | note → typed case → owned MCP tool; exit 0 | ✓ PASS |
| Primary model schema-constrained output | `extract(note, model="qwen3.5:4b")` | valid `ExtractionResult` (rr=24, hr=118, avpu=alert) | ✓ PASS |
| Reproducible build | `uv lock --check` / `uv sync --locked` | 115 packages, clean; exit 0 | ✓ PASS |

### Probe Execution

No `probe-*.sh` scripts are declared by this phase and none exist under `scripts/*/tests/`. The phase's runnable checks are the `scripts/spike_*.py` and `scripts/transcribe_diff.py` executables exercised above. **N/A.**

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INTAKE-01 | 01-01 | Case entered as structured vitals + free-text complaint | ✓ SATISFIED | `CaseInput` (vitals + `complaint`); `spike_e2e.py` extracts a typed case from a note |
| INTAKE-02 | 01-01 | One validated typed schema, defined once, imported everywhere | ✓ SATISFIED | `core/schema.py` is the only definition; imported by client + server; `test_schema_rejects.py` |
| INTAKE-04 | 01-02 | Adult TEWS bands + colour thresholds only in `data/sats_tews.yaml` | ✓ SATISFIED | File is the sole source; guard + grep clean; dual-transcription PASS |
| INTAKE-05 | 01-02 | Discriminators + categories only in `data/sats_discriminators.yaml` | ✓ SATISFIED | File is the sole source; `test_sats_discriminators.py`; dual-transcription PASS |
| SAFE-04 | 01-04 | Version pinning + hashing for prompts, model, scale data, tool schemas | ✓ SATISFIED | `core/hashing.py` + `evidence/hashes.json` (data/prompts/schemas + model tag); `uv.lock` |
| QUAL-01 | 01-03 | DRY + SOLID enforced — no duplicated SATS values/citations; graph depends on the tool interface | ✓ SATISFIED | `test_no_duplicated_sats.py` + `test_purity.py`; `load_tools()` DIP seam; `MCPAdapter` confined to `adapter.py` |

**Coverage:** 6/6 phase requirements satisfied. No orphaned requirements mapped to Phase 1.

### Decision Coverage

All 15 trackable CONTEXT.md `<decisions>` (D-01…D-15) are honored by shipped artifacts — gate result: `{total: 15, honored: 15, not_honored: []}`.

### Anti-Patterns / Warnings

| # | File / Area | Pattern | Severity | Impact |
|---|-------------|---------|----------|--------|
| 1 | `docs/SATS.md`, `evidence/sats-verification.md` | SC1's "(re-verified verbatim against the SATS manual)" was met by a dual transcription of `docs/SATS.md`, not a read of the original EMSSA manual (unavailable in the build window). Honestly flagged as residual uncertainty. | ⚠️ Warning | The substrate is internally consistent and the transcription diff caught a real slip, but clinical accuracy vs the published manual remains unconfirmed. A human should accept this residual uncertainty before the demo/evaluation. |
| 2 | `src/triagedesk/llm/client.py`, `evidence/model-spike.json` | The installed `qwen3.5:4b` does **not** fit the RAM budget (641 MB available < 1024 MB) and is the *fallback*; `qwen2.5:1.5b` is the default. SC3's literal "qwen3.5:4b … within the RAM budget" is therefore inverted. | ⚠️ Warning | Plan 01-01's designed budget gate explicitly anticipated this; both models returned valid schema JSON (reproduced). Reviewers should note the default is 1.5B, not the 4B named in the SC. |
| 3 | `tests/test_no_duplicated_sats.py` | Numeric DRY guard only flags values with a fractional part or ≥ 2 significant digits — single-digit band edges (8/9) and colour thresholds (2–7) are not scanned. | ⚠️ Warning | No current violation exists (manual `grep` clean), but the guard is weaker than "no scoring value anywhere" implies. Harden by deriving colour-threshold/edge literals from data. |
| 4 | `src/triagedesk/core/schema.py` | `ExtractionResult.matched_discriminator_ids` is `list[str]`, unconstrained against the closed discriminator set (explicitly deferred to Phase 2). | ⚠️ Warning | The closed set now exists in `data/sats_discriminators.yaml`; Phase 2 (`match_discriminators`) should validate against it. Not an SC2 failure (SC2 concerns the case schema). |
| 5 | `scripts/spike_model.py:87`, `src/triagedesk/llm/prompts.py:10,13,17` | Pre-existing ruff `F841` / `E501` (not debt markers) | ℹ️ Info | Logged in `deferred-items.md`; no `TBD`/`FIXME`/`XXX` anywhere in phase files. |
| 6 | `01-01-SUMMARY.md` vs `evidence/model-spike.json` | Narrative latency figures (43.0 s / 128.2 s) differ from the committed evidence (50.9 s / 144.1 s). | ℹ️ Info | Cosmetic inconsistency in prose only; the artifact is authoritative. |

**Anti-patterns:** 6 found (0 blockers, 3 warnings, 2 info) + 1 SC-wording caveat.

### Human Verification Required

N/A — Infrastructure/foundation phase (scaffold, schema, data substrate, tooling, guards) with no user-facing elements. All acceptance criteria were verified programmatically, and there are no ⚠️ PRESENT_BEHAVIOR_UNVERIFIED truths (every behavior-dependent claim was exercised by a test or independently reproduced). The clinical residual uncertainty (Warning #1) and the model-default inversion (Warning #2) are recorded as non-blocking warnings for human awareness, not as UAT items.

### Gaps Summary

**No gaps found.** Phase goal achieved on independently reproduced evidence.

- The SATS rule substrate and the one typed case schema exist as the single source of truth; the DRY and purity invariants are executable, not advisory, and are non-vacuous.
- The project rebuilds reproducibly from a committed `uv.lock` on pinned Python 3.12 (verified with `uv lock --check` / `uv sync --locked`), and the substrate/prompt/schema digests reproduce byte-for-byte.
- Both Day-1 unknowns are retired on evidence and were re-verified live during this audit: the local model returns valid schema-constrained JSON (both `qwen2.5:1.5b` and `qwen3.5:4b`), and `langchain.mcp.MCPAdapter` lists and calls a tool on both the owned SDK-v2 server and the borrowed legacy `mcp-sqlite@1.0.9` server (World A adopted, separate adapter contexts).

**Caveats (non-blocking, for human awareness):** the clinical transcription was verified against `docs/SATS.md` rather than the original manual (Warning #1), and the RAM budget gate inverted the SC's primary/fallback roles (Warning #2). Neither blocks goal achievement.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | `matched_discriminator_ids` validated against the closed discriminator set | Phase 2 | Phase 2 SC3/SC5: owned `match_discriminators` + deterministic alias lookup |
| 2 | Pre-existing ruff `F841`/`E501` cleanup | later cleanup | `.planning/phases/01-.../deferred-items.md` |

---

*Verified: 2026-10-09T13:29:26Z*
*Verifier: the agent (gsd-verifier)*
