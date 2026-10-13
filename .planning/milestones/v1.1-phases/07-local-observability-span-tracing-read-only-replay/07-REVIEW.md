---
phase: 07-local-observability-span-tracing-read-only-replay
reviewed: 2026-10-12T14:45:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - .gitignore
  - SECURITY.md
  - docs/DECISIONS.md
  - pyproject.toml
  - src/triagedesk/cli.py
  - src/triagedesk/graph/build.py
  - src/triagedesk/llm/client.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/observability/__init__.py
  - src/triagedesk/observability/context.py
  - src/triagedesk/observability/offline.py
  - src/triagedesk/observability/spans.py
  - src/triagedesk/replay.py
  - src/triagedesk/store/audit.py
  - src/triagedesk/store/borrowed.py
  - tests/conftest.py
  - tests/test_observability.py
  - tests/test_replay_read_only.py
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
status: clean
---

# Phase 07: Code Review Report (iteration 3 — final)

**Reviewed:** 2026-10-12T14:45:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** clean (0 critical, 0 warning, 4 info)

## Summary

Iteration 3 (final) re-reviewed the phase at standard depth, verified each of the four iteration-2
fixes against the **current** source, and hunted for regressions those fixes may have introduced. No
critical or warning findings remain — the status is **clean**; the four Info items are non-blocking
notes (one new doc-accuracy drift, one reader-robustness asymmetry, two carry-over nits).

**Iteration-2 fixes verified against current source**

- **WR-01 → `79532da` verified.** `spans.read_spans` now decodes each line under
  `except json.JSONDecodeError`, skips the bad line and reports it via `_report_skipped_line`
  (`spans.py:158-163`, `spans.py:72-86`); the docstring documents the skip (`spans.py:143-147`). The
  replay CLI's `except` tuple now includes `ValueError` (`cli.py:216`), so a decode failure can never
  traceback — `json.JSONDecodeError` subclasses `ValueError` (verified at runtime). The three new
  proofs are meaningful and non-vacuous: `test_read_spans_skips_a_truncated_line_and_keeps_the_valid_ones`
  (asserts the surviving row *and* the stderr report), `test_replay_cli_survives_a_corrupt_span_sink`
  (a truncated sink still exits 0 with the valid timeline), and
  `test_replay_cli_reports_a_decode_failure_cleanly` (a forced `ValueError` exits 1 without a traceback).
  I confirmed `monkeypatch.setattr("triagedesk.replay.read_spans", ...)` is effective because
  `replay_case` resolves `read_spans` from its own module global.
- **IN-01 → `0782d30` verified.** `offline.py:59` carries the narrow `# type: ignore[attr-defined]` on
  the `lru_cache` `cache_clear`; `replay.py:44,70` annotates `config` as `RunnableConfig`.
  `uv run mypy src/triagedesk/observability src/triagedesk/replay.py` → **clean** (the two previous
  strict errors are gone).
- **IN-03 → `d0a7a60` verified.** `cli.py`'s two `except` clauses (`cli.py:191`, `cli.py:216`) no longer
  list `DurableError`/`ReplayError` alongside `RuntimeError`; the now-unused imports were dropped. I
  grepped the whole tree — no remaining `DurableError`/`ReplayError` reference in `cli.py` — so no
  `NameError`; the base `RuntimeError` still covers both (they subclass it).
- **IN-05 → `be09595` verified.** `SECURITY.md` §10 and D19 now say `case_id_for_note(raw_note)` and
  qualify the digest seal with "when non-empty" (`SECURITY.md:105-106`, `DECISIONS.md:153-155`); the
  `AuditRecord` docstring's primitive reference was renamed (`audit.py:48`). One clause of that same
  docstring was missed — see IN-01 below.

**Regression checks the brief called out — all pass**

- `uv run pytest -q` → **279 passed** in 8.37s. `uv run ruff check .` → **All checks passed!**
- `graph/*.py` is free of `os.environ` / `getenv` / `import os` / network clients (grep → none), so the
  safety-spine AST guards hold.
- `core/scorer.py` and `core/citations.py` carry **no** phase diff (`git diff 658269e~1..HEAD -- src/triagedesk/core/` empty).
- The `@audited` decorator's audit behaviour is unchanged: the diff is purely additive — a `trace_id`
  field on the record and a `span(...)` wrapper — and `record()` still appends exactly one chained
  record per call, on both the success and the exception path (`mcp/server.py:114-162`). The CR-01
  hardening still holds: `span()`'s `finally` catches every `Exception` from `emit_span`
  (`spans.py:189-204`), so a sink failure cannot enter the wrapper's `except` and fabricate a
  failed-tool record.
- `open_checkpointer` remains the ONE saver factory, used by both `checkpointed_graph`
  (`build.py:299`) and `replay.read_recorded` (`replay.py:71`); `resolve_store` is the ONE public
  resolver (no stale `_resolve_store` anywhere — grep clean).
- No repo-root `spans.jsonl`, `checkpoints.db` or `triage.db` exists, and none is git-tracked; the
  autouse `_spans_sink` fixture keeps the suite hermetic.

## Info

### IN-01: `AuditRecord` docstring still claims `trace_id` is sealed unconditionally

**File:** `src/triagedesk/store/audit.py:50-51`

**Issue:** The IN-05 fix updated the `case_id_for_note` reference in this docstring but left the
adjacent clause "it is sealed by :func:`record_digest` like every other field." After WR-03, an
**empty** `trace_id` is deliberately *omitted* from the digest (`audit.py:84-87`), so "like every other
field" is now inaccurate. Doc-only; no code impact. (This is the residual of IN-05, whose scope named
SECURITY §10/D19 but not this clause.)
**Fix:** Qualify it, e.g. "and, when non-empty, it is sealed by `record_digest` (an empty value is
omitted so pre-migration rows still verify)".

### IN-02: `read_spans` is less robust than the writer it sits beside

**File:** `src/triagedesk/observability/spans.py:149-165`

**Issue:** The reader guards a malformed *JSON* line but not two sibling failure modes the hardened
writer already tolerates: (a) a **valid-JSON-but-not-an-object** line (`json.loads("[]")`) makes
`row.get(...)` raise `AttributeError` at `spans.py:164`; and (b) an I/O error reading the sink —
`resolved.exists()` is `True` for a directory, then `resolved.read_text()` raises
`IsADirectoryError`/`OSError` (`spans.py:154`), which the replay CLI's `except` tuple does **not**
catch. Neither is reachable via the realistic truncation path the WR-01 fix targets (a truncated
object prefix is always invalid JSON, so it degrades to the handled `JSONDecodeError`), and a
directory/permission fault at `spans.jsonl` is a contrived environment — hence Info, not a Warning.
**Fix:** For symmetry with `emit_span`'s `except OSError`, either skip a non-`Mapping` decoded row and
wrap the `read_text` in `except OSError`, or add `OSError` to the replay CLI's `except` tuple.

### IN-03: Observability barrel re-exports symbols no caller uses *via the barrel* (carry-over)

**File:** `src/triagedesk/observability/__init__.py:11-20`

**Issue:** The barrel docstring says the three emit sites import from ONE place, but they only use
`bind_trace`, `current_trace_id`, `span`. `emit_span`, `read_spans`, `set_sink` and `SPANS_PATH` are
re-exported yet consumed through the `observability.spans` submodule (`replay.py:48`,
`conftest.py:28`, the tests), so the barrel's surface is broader than its stated purpose. Minor: two
import paths for the same module.
**Fix:** Trim `__all__` to the symbols actually imported from the barrel, or route the
`replay`/`conftest` imports through it so there is one import path.

### IN-04: The "exactly one span" test assertion over-claims for a resumed run (carry-over)

**File:** `tests/test_observability.py:283`

**Issue:** The assertion `len(names) == len(set(names))` (and its message "a node must emit exactly one
span") holds only because the test runs to the gate; in a real durable run `approval_gate`
re-executes on resume and legitimately emits a second `node` span. Test-only and still passing, so no
reliability impact.
**Fix:** Reword to "each node emits exactly one span *per execution*", asserting the second
`approval_gate` span explicitly rather than uniqueness.

---

_Reviewed: 2026-10-12T14:45:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
