---
phase: 09-retrieval-grounding-borrowed-mcp-depth
reviewed: 2026-10-12T19:11:47Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - docs/DECISIONS.md
  - src/triagedesk/core/matcher.py
  - src/triagedesk/core/retrieval.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/evals/tools.py
  - src/triagedesk/graph/build.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/graph/state.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/store/borrowed.py
  - tests/conftest.py
  - tests/test_borrowed_store.py
  - tests/test_graph_grounding.py
  - tests/test_mcp_tools.py
  - tests/test_observability.py
  - tests/test_retrieval.py
  - tests/test_safety_spine.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 09: Code Review Report

**Reviewed:** 2026-10-12T19:11:47Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** clean

## Summary

Iteration-3 (FINAL) adversarial re-review of phase 9. I read every changed file in the current tree,
re-derived each prior finding against the live source (not the fix reports), ran the suite
(`uv run pytest -q` → **353 passed**) and `uv run ruff check .` (**clean**), and then made my own focused
attempt to defeat the hardened statement guard.

**Prior findings — all verified fixed against the current source:**

- **CR-01 (`6530b98`) — FIXED.** `EXPLAIN` is genuinely gone from the admitted heads:
  `_READ_PREFIXES = ("SELECT", "VALUES")` (`store/borrowed.py:82`); `"EXPLAIN" in _READ_PREFIXES` is
  `False`. Every `EXPLAIN`-headed form is now refused (see the bypass table below). No caller issues
  `EXPLAIN` — a repo-wide grep finds it only in comments/docstrings and the negative test list — and every
  read-path `_call(TOOL_QUERY, …)` site uses `SELECT` or `PRAGMA table_info(...)`, all still admitted.
- **IN-01 (`8c442d9`) — FIXED.** `_SIDE_EFFECTING_FUNCTION = re.compile(r"\bLOAD_EXTENSION\b")` is applied
  to the upper-cased statement *before* the head test (`:216`), so `SELECT load_extension('evil')`,
  `select LOAD_EXTENSION('x')` and schema-qualified/quote-wrapped spellings are all refused.
- **IN-02 (`f8ee51b`) — FIXED.** `_is_read_pragma` now requires a name boundary (`(`, whitespace, or end of
  string) after the admitted pragma name (`:166-179`), so `PRAGMA table_infox(queue)` is refused while
  `PRAGMA table_info(audit)` / `PRAGMA table_info (audit)` / `PRAGMA index_list(queue)` are admitted.
- **IN-03 (`bb19fc1`) — FIXED.** `retrieve_evidence`'s docstring no longer claims "no store access"; it now
  states its own logic touches no store and the uniform `@audited` interceptor records the call (AUDIT-01).

**My own bypass attempt (fresh, against the current source).** I ran the guard over 33 vectors — `EXPLAIN`,
`EXPLAIN QUERY PLAN`, mixed case, leading whitespace, leading `/*…*/` and `--` comments, `WITH`,
`PRAGMA writable_schema=1`, `PRAGMA main.writable_schema=1`, `PRAGMA_table_info(x)`, `PRAGMA index_list(q);
DROP TABLE q`, `SELECT load_extension(...)`, quoted/qualified `load_extension`, `ATTACH`, `REPLACE`,
`SELECT 1; DELETE …`, `SELECT 1; -- trailing`, `SELECT 1;-- c`, `SELECT 1 --;\nDELETE …`, and
`SELECT * FROM pragma_writable_schema`. Every mutation-bearing vector is refused; the only admitted
statements are genuine reads (`SELECT …`, `VALUES (…)`, the three read `PRAGMA`s). Two admitted edge forms
are noted as non-blocking info below — neither can mutate (both are SQLite syntax errors at execution).

**No regression in the rest of the phase (all confirmed):**

- Colour-free contract intact: `EvidencePassage`/`EvidenceResult` keep `extra="forbid"` and no
  colour/target/priority/float field (`core/schema.py:155-199`); the serialised result carries no colour
  key or value (`test_retrieval.py::test_contract_carries_no_float_or_colour_field`).
- `ground` isolation and routing-neutrality intact: `ground` returns exactly `{"evidence": …}`
  (`graph/nodes.py:217-222`); it is wired by a plain edge `ground -> verify` (`graph/build.py:264`) and no
  router's source names the channel (`test_graph_grounding.py::test_ground_is_wired_by_plain_edges_and_routes_nothing`).
- One tokeniser / one contiguous helper: `retrieval` imports `tokenize` and `contains_sequence` from
  `matcher`; `retrieval.tokenize is matcher.tokenize` and `retrieval.contains_sequence is matcher.contains_sequence`;
  `re.compile` does not appear in `retrieval.py` (`test_retrieval.py:135-146`).
- `Store` protocol unchanged: `git diff 7a2974b..HEAD -- src/triagedesk/store/__init__.py` is empty.
- `core/scorer.py` and the citation helper untouched (`git diff 7a2974b..HEAD` lists neither); `@audited`
  behaviour unchanged (the only `mcp/server.py` change in the fix loop is the `retrieve_evidence` docstring).
- `graph/*.py` free of env/network access (safety-spine AST guards green); tests hermetic
  (in-memory store + `tmp_path` span sink); no new dependency (`pyproject.toml`/`uv.lock` not in the diff).

Two non-blocking info notes follow. **No critical or warning findings remain.**

## Narrative Findings (AI reviewer)

### Critical Issues

None. CR-01 is verified fixed: `EXPLAIN` is absent from `_READ_PREFIXES`, and my independent bypass sweep
confirms no mutation-bearing statement is admitted (the previous iteration's `EXPLAIN PRAGMA
writable_schema = 1` / `EXPLAIN QUERY PLAN …` bypasses now return `False`).

### Warnings

None.

### Info

#### IN-01: `head == "WITH"` branch is redundant (dead code)

**File:** `src/triagedesk/store/borrowed.py:221`
**Issue:** `is_read_only_statement` contains `if head == "WITH": return False`, but `WITH` is not in
`_READ_PREFIXES` (`("SELECT", "VALUES")`), so the final `return head in _READ_PREFIXES` already returns
`False` for a `WITH` head. The branch is unreachable-as-a-decision: removing it changes no behaviour. It is
harmless and self-documenting (the rationale is also in the `_READ_PREFIXES` comment above), so this is a
cosmetic dead-code note only.
**Fix:** either delete the branch and rely on the fall-through, or add a one-line comment marking it as an
explicit belt-and-braces assertion (e.g. `# defensive: WITH is already excluded by _READ_PREFIXES`). No
functional change either way.

#### IN-02: Multi-statement detection is `;`-only — a newline-separated second statement is admitted (and then rejected by SQLite, so not exploitable)

**File:** `src/triagedesk/store/borrowed.py:211`
**Issue:** The single-statement check is `if ";" in stripped.rstrip(";"): return False`. A statement whose
second statement is separated by a newline rather than a `;` is therefore admitted, e.g.
`is_read_only_statement("SELECT 1\nDELETE FROM queue")` → `True`. This is **not exploitable**: I confirmed
against the shipped SQLite (3.53.1) that `SELECT 1\nDELETE FROM queue` raises
`OperationalError: near "DELETE": syntax error` and executes **no** mutation (queue row count unchanged);
the same holds for `SELECT 1\nDROP TABLE queue`, and the real borrowed server (`mcp-sqlite@1.0.9` on
`better-sqlite3`) rejects a non-empty statement tail outright. It is noted only because the guard's
docstring claims it is a "string-level barrier" that "must not rely on the executor's behaviour" — for
newline-separated forms it does defer to the SQL parser. Today the sole enforcement point is a constant
`SELECT`/`PRAGMA table_info` string, so this is defense-in-depth, not a live path.
**Fix (optional):** if you want the guard to be provably self-sufficient, reject a statement whose token
stream contains a statement-terminating keyword (`INSERT`/`UPDATE`/`DELETE`/`DROP`/`CREATE`/`ALTER`/`ATTACH`/
`PRAGMA`/…) after the head, or simply leave it as-is and rely on SQLite's mandatory `;` separator.

---

_Reviewed: 2026-10-12T19:11:47Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
