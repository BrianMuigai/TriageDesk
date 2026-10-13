---
phase: 09-retrieval-grounding-borrowed-mcp-depth
verified: 2026-10-13T13:10:30Z
status: passed
score: 15/15 must-haves verified
covered_files: [".planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-01-PLAN.md", ".planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-01-SUMMARY.md", ".planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-02-PLAN.md", ".planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-02-SUMMARY.md", ".planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-03-PLAN.md", ".planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-03-SUMMARY.md", "docs/DECISIONS.md", "src/triagedesk/core/matcher.py", "src/triagedesk/core/retrieval.py", "src/triagedesk/core/schema.py", "src/triagedesk/evals/tools.py", "src/triagedesk/graph/build.py", "src/triagedesk/graph/nodes.py", "src/triagedesk/graph/state.py", "src/triagedesk/mcp/server.py", "src/triagedesk/store/borrowed.py", "tests/conftest.py", "tests/test_borrowed_store.py", "tests/test_graph_grounding.py", "tests/test_mcp_tools.py", "tests/test_observability.py", "tests/test_retrieval.py", "tests/test_safety_spine.py"]
covered_digest: "v3:sha256:b88ff4fbb0180557590d67b2305466ea594fab03afb32334abf38f8cee5720bb"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 15/15
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 9: Retrieval Grounding & Borrowed-MCP Depth — Verification Report

**Phase Goal:** A read-only `retrieve_evidence` tool plus a `ground` node placed after `score` surface
attributed SATS KB excerpts under a closed-set contract that cannot set a colour, and the borrowed SQLite
MCP server is exercised through its read paths behind the unchanged `Store` protocol — read-only in the
agent path.
**Verified:** 2026-10-13T13:10:30Z
**Status:** passed
**Re-verification:** Yes — stale re-verification. Later phases (10–12) additively edited shared source
files covered by the prior report, so the fingerprint was regenerated and all four ROADMAP success
criteria were re-confirmed against the CURRENT codebase. The prior report was `passed` with no `gaps:`
section; the fifteen merged must-have truths are preserved verbatim and re-checked.

## Goal Achievement

Every must-have was re-verified against the live codebase, not against SUMMARY.md claims. The four ROADMAP
success criteria are the contract; the plan-level truths that refine them are listed below and deduplicated.

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | **SC1a** — A `retrieve_evidence` owned tool returns attributed SATS KB excerpts derived from `data/*.yaml` | ✓ VERIFIED | `src/triagedesk/mcp/server.py:240-253` registers the tool behind `@audited()`; `retrieval.retrieve()` reads the corpus only through `core/rules.get_discriminators()`. Live: `retrieve('central chest pain')` → `[('chest_pain', rank 1, score 3)]`. `tests/test_mcp_tools.py` drives it over the SDK in-memory `Client`. |
| 2   | **SC1b** — A `ground` node placed after `score` surfaces those excerpts | ✓ VERIFIED | `graph/build.py:252-264`: the `score` conditional edge's `verify` route targets `ground`; plain `ground -> verify` edge follows. `ground` is in `TRACER_NODES` (`build.py:100-114`) and in `make_nodes` (`nodes.py:436`). Live edge set: `("score","ground")` and `("ground","verify")` present; `ground`'s only outgoing edge is `verify`. Asserted by `tests/test_graph_grounding.py:118-127`. |
| 3   | **SC2a** — Retrieval returns only closed-set discriminator ids, a rank, and an explicit `no_match` — it can never emit a colour or an uncited rule | ✓ VERIFIED | `retrieval.py:62-111`: passages built FROM `substrate.discriminators` (ids unconstructible outside the closed set); `citation=format_citation(...)` from the ONE helper (`retrieval.py:25,98`). `EvidencePassage`/`EvidenceResult` carry no colour/target/priority/float field and `extra="forbid"`. Tests: `test_retrieval.py:47,57,67,100`. Live `model_fields` = `{discriminator_id,label,citation,score,rank}` / `{passages,no_match,reason}`. |
| 4   | **SC2b** — The `ground` node writes a separate `evidence` channel without touching `priority`/`citations` | ✓ VERIFIED | `nodes.py:197-224` returns exactly `{"evidence": result}`. `state.py:60-65` declares the channel. `tests/test_graph_grounding.py:64-71` asserts the key set is exactly `{evidence}`; `:82-112` runs the graph twice (real vs no-match retrieval) and asserts `priority.colour`/`citations`/`matched_ids`/`no_match` are identical while `evidence` differs, and each colour equals a direct `scorer.score_priority` call. |
| 5   | **SC3** — E-09 is addressed by real retrieval / reported as a clean defer, never by a literal alias | ✓ VERIFIED | Live: E-09 complaint `'feeling unwell'` → `no_match=True`, `passages=[]`, `declared_failure=True`. `tests/test_retrieval.py:112` and `tests/test_graph_grounding.py:155-176` (asserts a safe terminal reached, no `commit_priority` call, `memory_store.rows == []`). `git log -- evals/cases/E-09.yaml` shows the fixture untouched since phase 04-02 (`f11e4a6`) — no alias/fixture/threshold added by phase 9 or later. |
| 6   | **SC4** — The borrowed SQLite MCP server's read paths (`list_tables`, schema, `read_records`, `db_info`) are used behind the unchanged `Store` protocol, with a tool allowlist and statement guard keeping it read-only | ✓ VERIFIED | `store/borrowed.py:315-373` `_probe_read_paths` calls all four read tools through the guarded seam; `ensure_schema` sets `read_path_report` (`:313`). `git log -1 -- src/triagedesk/store/__init__.py` = phase 06-01 (`9af1d3c`) — protocol shape unchanged by phase 9 or later. `READ_TOOLS` (`:63-69`) + `is_read_only_statement` (`:182-223`) enforced at the ONE `_call` seam (`:277-298`). `tests/test_borrowed_store.py:230` observes the read tools called. |
| 7   | Retrieval is one pure, deterministic function — no model, no MCP client, no I/O | ✓ VERIFIED | `retrieval.py` imports only `citations`/`matcher`/`rules`/`schema`; covered by `tests/test_purity.py` (auto-parametrised). `test_retrieval.py:41` proves determinism; `:57` proves the explicit `(-score, id)` tie-break. |
| 8   | The evidence contract has no colour/target/priority/float field, so a colour is unrepresentable | ✓ VERIFIED | `schema.py:182-226`; both models `ConfigDict(extra="forbid")` (live-confirmed). `tests/test_retrieval.py:67-97` iterates `model_fields`, rejects a smuggled `colour`/`target` at construction (`:100`), and asserts no substrate colour appears as a JSON key or scalar value. |
| 9   | Every returned `discriminator_id` ∈ the loader-derived closed set; every citation from the ONE helper | ✓ VERIFIED | `test_retrieval.py:47-54` asserts membership against the non-vacuously non-empty loader-derived set; `retrieval.py:98` uses `format_citation`. `_score` (`retrieval.py:41-59`) now applies the matcher's contiguous-phrase rule (`contains_sequence`), so retrieval and the matcher agree on which discriminators a complaint names (`test_retrieval.py:144-169`). |
| 10  | The owned server registers a seventh read-only tool and the allowlist equals the seven-name surface at all four assertion sites | ✓ VERIFIED | Live `server.list_tools()` = 7 names including `retrieve_evidence`; `OWNED_TOOL_ALLOWLIST` = the same 7. All four sites agree: `graph/build.py:68-76`, `evals/tools.py:140`, `tests/conftest.py`, `tests/test_safety_spine.py`. `build_graph` composes without raising (suite green). |
| 11  | A mutation on the read path is refused before the borrowed tool is invoked; an off-allowlist tool name is refused fail-closed | ✓ VERIFIED | `borrowed.py:289-297` raises before `self._tools` is dereferenced. Live guard check (hardened after review): `EXPLAIN PRAGMA writable_schema=1` → False; `WITH … DELETE` → False; `SELECT 1; DELETE` → False; `PRAGMA writable_schema=1` → False; `PRAGMA table_infox(queue)` → False; `SELECT load_extension(1)` → False; `SELECT 1`/`PRAGMA table_info(audit)`/`VALUES (1)` → True. `_READ_PREFIXES = ("SELECT","VALUES")` (EXPLAIN/WITH dropped), PRAGMA read-subset with name boundary, `_SIDE_EFFECTING_FUNCTION` deny-list, multi-statement refusal. Tests `test_borrowed_store.py:252,270,328`. |
| 12  | A read-path shape mismatch degrades — recorded, never crashes the store-open path | ✓ VERIFIED | `borrowed.py:341-353` wraps each probe; `tests/test_borrowed_store.py:334-365` drives a raising `db_info` and a scalar `read_records` and asserts `ensure_schema()` completes with a `degraded:` report and the store still usable. |
| 13  | The gated write path still works (bootstrap DDL, queue upsert, chain-head write, audit insert) | ✓ VERIFIED | `write=True` at `borrowed.py:302-305,312,415-435,481-490,492-518`. `tests/test_commit_idempotent.py`, `tests/test_audit_chain.py`, `tests/test_durable_cli.py` all pass in the 454-test suite. |
| 14  | No conditional edge or router reads `evidence`; the path taken is unchanged; no `ground`→`commit` edge | ✓ VERIFIED | `ground`'s only outgoing edge is `verify` (`build.py:264`); live scan: none of the four route functions' sources contain the token `evidence`. `tests/test_graph_grounding.py:118-134` asserts the edge set and scans the route sources. `route_after_score` returns the label `verify` (`build.py:147`) — the decision is unchanged. |
| 15  | The retrieval/grounding design and the borrowed read-only guard are recorded as D21/D22 in `docs/DECISIONS.md` | ✓ VERIFIED | `docs/DECISIONS.md` D21/D22 rows above the disclosed-components table. `tests/test_docs_final.py` passes. |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Deferred Items

None. All phase must-haves are met; nothing is deferred to a later phase.

### Advisory (New Scope, Unevidenced)

None. The stale re-verification surfaced no new-scope findings: no Step 7 blocker was raised, so there is
nothing to downgrade to advisory. (Section included because a re-verification pass ran.)

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/triagedesk/core/retrieval.py` | NEW pure lexical retrieval | ✓ VERIFIED | 114 lines; `retrieve`, `_score`, `MATCH_MIN_SCORE`, `MAX_PASSAGES`; imports no `llm`/`mcp`/`store`. |
| `src/triagedesk/core/schema.py` | `EvidencePassage`/`EvidenceResult` contracts | ✓ VERIFIED | `:182-226`; colour-free, no-float, `extra="forbid"`. Evidence region untouched by later phases (schema.py's 3 post-phase-9 commits changed unrelated extraction regions). |
| `src/triagedesk/core/matcher.py` | public `tokenize` (ONE owner) + `contains_sequence` | ✓ VERIFIED | `:33-41`; `_tokens = tokenize` alias (`:47`); `contains_sequence` (`:50-62`). Unchanged since phase 9. |
| `src/triagedesk/mcp/server.py` | `retrieve_evidence` tool | ✓ VERIFIED | `:240-253`; thin `@audited()` wrapper, no approval token. |
| `src/triagedesk/evals/tools.py` | `retrieve_evidence` closure | ✓ VERIFIED | `:125-126,140`; calls the REAL owned tool in-process. |
| `tests/test_retrieval.py` | NEW retrieval proofs | ✓ VERIFIED | 170 lines; determinism, closed-set, unrepresentability, E-09, DRY, negated-phrase regression. |
| `src/triagedesk/store/borrowed.py` | `READ_TOOLS`, `is_read_only_statement`, guarded `_call`, read-path probe | ✓ VERIFIED | `:63-69,166-223,277-298,315-373`. Guard hardened after review (EXPLAIN/WITH dropped, PRAGMA boundary, side-effecting function, multi-statement). |
| `tests/test_borrowed_store.py` | read-tool observation, refusal, degradation proofs | ✓ VERIFIED | `:218-365`; observes reads, refuses mutations on the fake's call log. |
| `tests/test_observability.py` | stdlib stand-in returns real columns/rows | ✓ VERIFIED | `get_table_schema`/`read_records` read the live `sqlite3` connection. |
| `src/triagedesk/graph/nodes.py` | `_make_ground` | ✓ VERIFIED | `:197-224`; returns exactly `{"evidence": result}`. |
| `src/triagedesk/graph/state.py` | `evidence` channel | ✓ VERIFIED | `:60-65`; advisory, read by nothing that routes. |
| `src/triagedesk/graph/build.py` | `ground` in `TRACER_NODES` + `score → ground → verify` | ✓ VERIFIED | `:100-114,252-264`. |
| `tests/test_graph_grounding.py` | NEW channel-isolation + neutrality proofs | ✓ VERIFIED | 192 lines; six proofs. |
| `docs/DECISIONS.md` | D21, D22 rows | ✓ VERIFIED | Present above the disclosed-components table (D23–D25 added later by phases 10–12). |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `retrieve_evidence` tool | `core.retrieval.retrieve` | `@audited()` wrapper body | ✓ WIRED | `server.py:253`. |
| `OWNED_TOOL_ALLOWLIST` | `evals/tools.build_tools` → `tests/conftest.build_graph_tools` → `tests/test_safety_spine` | seven-name set-equality | ✓ WIRED | All four sites carry the identical 7 names (live-confirmed). |
| `EvidencePassage.discriminator_id` | `get_discriminators().discriminators` ids | built FROM the loader | ✓ WIRED | `retrieval.py:84-105`. |
| `EvidencePassage.citation` | `core.citations.format_citation` | imported helper | ✓ WIRED | `retrieval.py:25,98`. |
| `EvidenceResult.no_match` reason | `get_discriminators().no_match.warning` | read, never restated | ✓ WIRED | `retrieval.py:92`. |
| `BorrowedStore._call` | `READ_TOOLS` + `is_read_only_statement` | the ONE guarded seam | ✓ WIRED | `borrowed.py:289-297`. |
| `ensure_schema` | `_probe_read_paths` → `read_path_report` | additive probe | ✓ WIRED | `borrowed.py:313-373`. |
| `commit_priority` | `store/queue.commit_to_queue` → `BorrowedStore.upsert_queue_row` (`write=True`) | the ONLY mutation route | ✓ WIRED | `borrowed.py:407-435`; idempotency suite green. |
| `Store` protocol (`store/__init__.py`) | `BorrowedStore` / `InMemoryStore` | shape unchanged | ✓ WIRED | Last commit touching `store/__init__.py` = phase 06-01 (`9af1d3c`). |
| `score` | `ground` → `verify` | plain edge | ✓ WIRED | `build.py:258,264`; edge set asserted. |
| `ground` | `tools["retrieve_evidence"]` | injected mapping | ✓ WIRED | `nodes.py:220`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `core/retrieval.retrieve` | `passages[].discriminator_id/label/citation` | `get_discriminators()` (`data/sats_discriminators.yaml`) | Yes — live call returns real `chest_pain` passage | ✓ FLOWING |
| `core/retrieval.retrieve` | `reason` (no_match) | `substrate.no_match.warning` | Yes — E-09 live returns the substrate warning | ✓ FLOWING |
| `graph/nodes._make_ground` | `evidence` | `tools["retrieve_evidence"]({"complaint": case.complaint})` | Yes — asserted by `test_ground_reaches_the_retrieve_evidence_tool` | ✓ FLOWING |
| `store/borrowed._probe_read_paths` | `read_path_report` | `db_info`/`list_tables`/`get_table_schema`/`read_records` through `_call` | Yes — `test_ensure_schema_observes_the_borrowed_read_tools` records all four `ok` | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite | `uv run pytest -q` | `454 passed in 34.92s` | ✓ PASS |
| Focused phase gate | `uv run pytest tests/test_retrieval.py tests/test_graph_grounding.py tests/test_borrowed_store.py -q` | `54 passed in 0.68s` | ✓ PASS |
| Statement guard fail-closed | `python -c "is_read_only_statement(...)"` | `EXPLAIN PRAGMA writable_schema=1`/`WITH…DELETE`/`SELECT 1; DELETE`/`PRAGMA writable_schema=1`/`PRAGMA table_infox(queue)`/`SELECT load_extension('evil')` → False; `SELECT 1`/`PRAGMA table_info(audit)`/`PRAGMA table_info (audit)`/`VALUES (1)`/`PRAGMA index_list(queue)` → True | ✓ PASS |
| One tokeniser / one phrase rule | `python -c "retrieval.tokenize is matcher.tokenize"` | `True` (and `contains_sequence is contains_sequence` → `True`) | ✓ PASS |
| Colour-free contract | `python -c "EvidencePassage.model_fields"` | `{rank,citation,score,label,discriminator_id}` / `{no_match,passages,reason}`; `extra=forbid` both | ✓ PASS |
| E-09 honest defer | `python -c "retrieval.retrieve('feeling unwell')"` | `no_match=True`, `passages=[]` | ✓ PASS |
| Owned tool surface | `python -c "await server.list_tools()"` / `OWNED_TOOL_ALLOWLIST` | both exactly the same 7 names | ✓ PASS |
| Ground edge set | `python -c "build_graph(...).get_graph().edges"` | `("score","ground")` and `("ground","verify")` present; `ground` outgoing = `{verify}`; no `("ground","commit")` | ✓ PASS |

**Note (non-blocking, environmental):** the first full-suite run reported `1 failed, 453 passed` on
`tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`, because a stray
gitignored `spans.jsonl` (74 spans, timestamps `2026-10-13T12:10:29Z`) had been left in the repo root by a
manual/demo run — NOT by the pytest suite, whose autouse `_spans_sink` fixture redirects the sink to
`tmp_path` (`tests/conftest.py:200-212`). Removing the artifact and re-running produced the clean
`454 passed` baseline above. This is not a phase-9 regression; no phase-9 file writes the repo-root sink.

### Probe Execution

Not applicable — this phase declares no `probe-*.sh` scripts and is not a migration/tooling phase. The
phase's executable evidence is the pytest suite and the direct guard/tokeniser checks above.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/test_retrieval.py` | AGENT-03 | 10 | 0 | 0 | Value + Behavioral (closed-set membership, unrepresentability, E-09 defer, phrase-rule regression) | PASS |
| `tests/test_graph_grounding.py` | AGENT-03 | 6 | 0 | 0 | Behavioral (two-run channel isolation, router source scan, E-09 no-write) | PASS |
| `tests/test_borrowed_store.py` | MCP-01 | 13 | 0 | 0 | Behavioral (read tools observed, refusal before the fake, degradation) | PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| **AGENT-03** | 09-01, 09-03 | A `retrieve_evidence` tool and a `ground` node after `score` fetch attributed SATS KB excerpts (from `data/*.yaml`, not re-authored); retrieval returns only closed-set ids, a rank, explicit `no_match`; E-09 addressed by real retrieval or a clean defer, never an alias | ✓ SATISFIED | Truths 1–5, 7–10, 14; `server.py:240`, `build.py:252-264`, `nodes.py:197-224`, `retrieval.py`, `schema.py:182-226`; E-09 live `no_match`. `REQUIREMENTS.md:25,92` marks it Complete. |
| **MCP-01** | 09-02 | The borrowed SQLite MCP server is exercised beyond `query` — read paths used behind the unchanged `Store` protocol, read-only with a tool allowlist and statement guard | ✓ SATISFIED | Truths 6, 11–13; `borrowed.py:63-69,166-223,277-298,315-373`; protocol unchanged (last touched phase 06-01); guard fail-closed verified. `REQUIREMENTS.md:40,98` marks it Complete. |

**Orphaned requirements:** none. `REQUIREMENTS.md` maps only AGENT-03 and MCP-01 to Phase 9, and both are
claimed by the plans' `requirements` frontmatter (09-01/09-03 → AGENT-03; 09-02 → MCP-01).

### Decision Coverage

All 14 trackable `09-CONTEXT.md` decisions are honored by shipped artifacts (handler: `{total: 14,
honored: 14, not_honored: []}`). D9-01..D9-14 are reflected across `retrieval.py`, `schema.py`,
`store/borrowed.py`, `graph/nodes.py`, `graph/state.py`, `graph/build.py` and `docs/DECISIONS.md`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` in any phase-modified source or test file | — | Clean. No unresolved debt markers; no blockers. |
| — | — | No `return null`/empty-literal/console-only stub in `retrieval.py`, `borrowed.py`, `nodes.py`, `build.py` | — | No stubs found. |

**Info note (non-blocking):** the real `mcp-sqlite@1.0.9` wire shapes for `read_records`/`get_table_schema`
are unverified in-repo (RESEARCH A1). The plan deliberately decided to **degrade, not probe live** — the
probe records a `degraded:` string on `read_path_report` rather than raising, and no human-verify checkpoint
was added. This is an explicitly accepted, documented risk (D22), not a must-have failure: the phase's claim
is that the read paths are *exercised behind the unchanged protocol with a read-only guard*, which is proven
hermetically against the stdlib stand-in. Inspect `store.read_path_report` during the pre-demo real run.

**Info note (non-blocking, carried from 09-REVIEW.md):** two cosmetic guard notes were recorded by the
clean review — the `head == "WITH"` branch is dead code (unreachable-as-a-decision; `WITH` is already absent
from `_READ_PREFIXES`), and multi-statement detection is `;`-only so a newline-separated tail is admitted by
the classifier but rejected by SQLite itself (not exploitable; no live path issues such a string). Neither
is a must-have failure.

### Human Verification Required

None. Every phase must-have truth is verified with explicit codebase evidence, including all behavior-dependent
truths (channel isolation, refusal-before-touch, graceful degradation, gated-write reachability, E-09 defer),
each backed by a passing behavioral test. No `verification: backstop` truth is declared in any phase plan.
This is an infrastructure/backend phase with no user-facing elements.

### Gaps Summary

No gaps. All four ROADMAP success criteria and all fifteen merged must-have truths are VERIFIED against the
live codebase; all artifacts exist, are substantive and wired; all key links are connected; no debt markers
or blockers were found; both requirement IDs are satisfied with no orphans; all 14 CONTEXT decisions are
honored. The full suite is green at **454 passed**, matching the expected count, and the phase's focused gate
is **54 passed**. The stale re-verification confirmed the phase-9 source files are unchanged since the prior
pass except `schema.py`, whose `EvidencePassage`/`EvidenceResult` region was untouched by the later-phase
additive edits — no regression.

---

_Verified: 2026-10-13T13:10:30Z_
_Verifier: the agent (gsd-verifier)_
