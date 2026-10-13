---
phase: 09-retrieval-grounding-borrowed-mcp-depth
fixed_at: 2026-10-12T19:07:09Z
review_path: /home/brian/Desktop/brij/ai/TriageDesk/.planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-REVIEW.md
iteration: 2
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 09: Code Review Fix Report

**Fixed at:** 2026-10-12T19:07:09Z
**Source review:** /home/brian/Desktop/brij/ai/TriageDesk/.planning/phases/09-retrieval-grounding-borrowed-mcp-depth/09-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

Scope note: the review's frontmatter counts 1 critical + 0 warning + 3 info. The orchestrator's
iteration-2 instruction was to close the critical blocker **and** the three cheap info items while
in scope, so all 4 findings were attempted and fixed. (IN-03 is documentation only; CR-01, IN-01 and
IN-02 are in the phase's declared safety surface — the fail-closed statement guard.)

## Fixed Issues

### CR-01: The statement guard still admits an `EXPLAIN`-prefixed `PRAGMA` write

**Files modified:** `src/triagedesk/store/borrowed.py`, `tests/test_borrowed_store.py`
**Commit:** `6530b98`
**Applied fix:** Dropped `EXPLAIN` from `_READ_PREFIXES` outright (now `("SELECT", "VALUES")`) — the
minimal, provably-safe route, since no caller issues `EXPLAIN` (the store's own reads are `SELECT`
and `PRAGMA table_info`; verified by repo-wide search). `EXPLAIN` only suppresses the VDBE program,
while SQLite executes `PRAGMA` at COMPILE time, so `EXPLAIN PRAGMA writable_schema = 1` mutated state
and was admitted by the prefix test. The `_READ_PREFIXES` comment and the `is_read_only_statement`
docstring now state the reason. Tests: removed `"EXPLAIN SELECT 1"` from `_READ_ONLY_STATEMENTS` and
added `"EXPLAIN SELECT 1"`, `"EXPLAIN PRAGMA writable_schema = 1"` and
`"EXPLAIN QUERY PLAN PRAGMA cache_size = 100"` to `_NOT_READ_STATEMENTS`.
**Verification:** syntax OK; targeted suite green; guard empirically refuses all three `EXPLAIN`
bypasses (`is_read_only_statement` → `False`).

### IN-01: `SELECT` with a side-effecting function is admitted

**Files modified:** `src/triagedesk/store/borrowed.py`, `tests/test_borrowed_store.py`
**Commit:** `8c442d9`
**Applied fix:** Added a one-source deny-list regex
`_SIDE_EFFECTING_FUNCTION = re.compile(r"\bLOAD_EXTENSION\b")` and a check that refuses a statement
whose token stream names a side-effecting SQL function, applied before the head test so even a
`SELECT` head cannot carry `load_extension` (the only built-in that can act beyond the current
database). Extension loading is default-off in both Python's `sqlite3` and `mcp-sqlite@1.0.9`, so the
guard does not rely on that behaviour. Test added: `"SELECT load_extension('evil')"` →
`_NOT_READ_STATEMENTS`.

### IN-02: The `PRAGMA` read-subset test over-accepts by prefix

**Files modified:** `src/triagedesk/store/borrowed.py`, `tests/test_borrowed_store.py`
**Commit:** `f8ee51b`
**Applied fix:** Replaced the bare `startswith(_PRAGMA_READ_PREFIXES)` with a single-purpose
`_is_read_pragma(upper)` helper that requires a name boundary after the admitted pragma name —
`(`, whitespace, or end of string — so an unknown pragma sharing a prefix (`PRAGMA table_infox`) is
refused while `PRAGMA table_info(audit)` / `PRAGMA table_info (audit)` still pass. Tests: added
`"PRAGMA table_infox(queue)"` to `_NOT_READ_STATEMENTS` and `"PRAGMA table_info (audit)"` to
`_READ_ONLY_STATEMENTS` to pin the boundary positively.

### IN-03: `retrieve_evidence`'s docstring claimed "no store access"

**Files modified:** `src/triagedesk/mcp/server.py`
**Commit:** `bb19fc1`
**Applied fix:** Reworded the docstring to the truth — the tool's own logic touches no store and sets
no queue row / approval token, while the uniform `@audited` interceptor *does* record the call
(AUDIT-01). The interceptor itself was not changed. Summary line now reads "read-only, no queue
effect" rather than "no store".

## Skipped Issues

None — all in-scope findings were fixed.

---

## Verification

- Baseline before this pass: `uv run pytest -q` → **348 passed**.
- After this pass: `uv run pytest -q` → **353 passed** (+5 net new parametrised classifier cases:
  +1 positive boundary case, +5 negative cases, −1 removed `EXPLAIN` positive case). `uv run ruff
  check .` → **clean**.
- An explicit adversarial re-check confirmed the guard now returns `False` for
  `EXPLAIN PRAGMA writable_schema=1`, `EXPLAIN QUERY PLAN PRAGMA cache_size=100`, `EXPLAIN SELECT 1`,
  `PRAGMA writable_schema=1`, `PRAGMA table_infox(queue)`, `SELECT load_extension('evil')`,
  `WITH x AS (SELECT 1) DELETE FROM queue`, and `SELECT 1; DELETE FROM queue`; and `True` for
  `SELECT 1`, `PRAGMA table_info(audit)`, `PRAGMA table_info (audit)`, `PRAGMA index_list(queue)`,
  `VALUES (1)`.
- **Where the gates ran:** `workflow.use_worktrees` is `false` in `.planning/config.json`, so no
  worktree was created and all edits, commits and gate runs happened in the **main checkout** — the
  numbers above are reproducible from this tree.
- **Not touched (per instruction):** `core/scorer.py` arithmetic, the citation helper, the `@audited`
  interceptor's behaviour, graph topology, the `Store` protocol shape, `data/*.yaml`. No new
  dependency. Retrieval stays colour-free; the `ground` channel stays isolated.

---

_Fixed: 2026-10-12T19:07:09Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 2_
