---
phase: 07-local-observability-span-tracing-read-only-replay
fixed_at: 2026-10-12T14:16:43Z
review_path: .planning/phases/07-local-observability-span-tracing-read-only-replay/07-REVIEW.md
iteration: 2
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-10-12T14:16:43Z
**Source review:** `.planning/phases/07-local-observability-span-tracing-read-only-replay/07-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 4 — WR-01 (the iteration-2 `critical_warning` finding) plus the three cheap INFO
  items the fix brief named explicitly (IN-01, IN-03, IN-05). IN-02, IN-04 and IN-06 were not requested
  and were left untouched.
- Fixed: 4
- Skipped: 0

**Verification environment:** all fixes were applied and verified in the **main checkout** (project
config `workflow.use_worktrees=false` — no isolated worktree was created), as iteration 1 did. Every
finding is an atomic one-finding commit on branch `main`. The full suite (`uv run pytest -q`,
**279 passed** — the 276 baseline plus the 3 new WR-01 regression tests) and `uv run ruff check .`
(clean) were run in the main checkout and are reproducible from it. `uv run mypy src` reports **29**
errors (down from 31 — the two phase-introduced errors are gone; the remaining 29 are the repo's
pre-existing backlog).

**Commit note:** `workflow.commit_docs` is `false` in `.planning/config.json`, so the
`gsd_run query commit` helper returns `{skipped: true, reason: "skipped_commit_docs_false"}` and
commits nothing. Each fix was therefore committed atomically with plain `git commit` (no git hooks are
installed), listing only the finding's own files — the pre-existing dirty `.planning/` and
`docs/assets/` changes were left unstaged and untouched.

## Fixed Issues

### WR-01: `read_spans` raises on a malformed/truncated JSONL line, and the replay CLI does not catch it

**Files modified:** `src/triagedesk/observability/spans.py`, `src/triagedesk/cli.py`, `tests/test_replay_read_only.py`
**Commit:** `79532da`
**Applied fix:** Chose the reviewer's preferred root-cause fix (skip + clearly report) and added the
suggested CLI coverage as defence-in-depth:
- `read_spans` now wraps each non-empty line's `json.loads` in `try/except json.JSONDecodeError` and
  **skips** an unparsable (truncated/corrupt) line instead of raising. A new `_report_skipped_line`
  helper surfaces the skip on `stderr` with its 1-based line number (so corruption is visible, never
  silent) and, like `_report_sink_failure`, can never itself raise. The one reader still owns the
  format and the recovery (DRY; a JSONL sink is best-effort, mirroring CR-01's "observability never
  fails the path it observes"). The docstring was extended to document the corrupt-line behaviour
  alongside the existing "a missing file is an empty stream" promise.
- The `replay` (and symmetrically the `resume`) handler's `except` tuple now also catches `ValueError`
  — `json.JSONDecodeError` is a `ValueError` — so even a residual decode/deserialisation failure is
  reported cleanly with a non-zero exit and never a raw traceback. (IN-03 then removed the redundant
  `ReplayError`/`DurableError` subclasses from the same tuples; see below.)
- Added three regression tests in `tests/test_replay_read_only.py`:
  - `test_read_spans_skips_a_truncated_line_and_keeps_the_valid_ones` — writes one valid + one
    truncated line, asserts `read_spans` returns only the valid row and reports `corrupt span line 2`
    on `stderr`.
  - `test_replay_cli_survives_a_corrupt_span_sink` — commits a real case, appends a truncated line to
    the sink, runs the real `replay` CLI and asserts **no traceback**, a clean exit, the thread id in
    the rendered view, and the valid span lines still readable. This is the actual pre-fix failure
    (an unguarded decode traced back out of `main`).
  - `test_replay_cli_reports_a_decode_failure_cleanly` — makes the reader raise a `JSONDecodeError`
    and asserts the CLI reports it with a **clean non-zero exit and no traceback**, pinning the
    `ValueError` coverage the brief asked for.

**Design note (why skip, and why the test asserts both exit codes):** the review offered two options —
skip (best-effort, valid lines readable, replay succeeds) or keep the parse strict and catch
`ValueError` (clean non-zero exit). A single corrupt line cannot both be skipped *and* fail replay, so
both behaviours were implemented together and each is pinned by its own test: the reader degrades
gracefully (valid lines readable, exit 0 on the real path), and the CLI guarantees a clean **non-zero**
exit for any decode error that does reach it. This is the reviewer's "and/or" satisfied in full rather
than a compromise.

**Verification note:** a control-flow fix (an exception no longer escapes the reader); covered by the
three dedicated behavioural tests above. Flagged for human confirmation.

### IN-01: Two mypy-strict errors remain in the phase's touch points

**Files modified:** `src/triagedesk/observability/offline.py`, `src/triagedesk/replay.py`
**Commit:** `0782d30`
**Applied fix:**
- `offline.py`: `langsmith_utils.get_env_var.cache_clear()` now carries a narrow
  `# type: ignore[attr-defined]` (mypy only sees the two `@overload` signatures, which omit the
  `lru_cache` wrapper attribute) with a comment explaining why. The review's literal
  `getattr(..., "cache_clear")()` suggestion was tried first but rejected: ruff's `B009` (enabled in
  this repo) flags a constant-attribute `getattr` as no safer than direct access, so it would have
  traded one gate for another. The repo already uses `# type: ignore[...]` for third-party stub gaps
  (`evals/case.py`, `core/scorer.py`), so this matches the established convention.
- `replay.py`: `read_recorded`'s `config` is now annotated `RunnableConfig` (imported from
  `langchain_core.runnables`) instead of `dict[str, Any]`, so `saver.aget_tuple(config)` type-checks
  against the expected `RunnableConfig`.
- Result: `uv run mypy src` drops from 31 to 29 errors; the two phase-introduced errors are gone.

### IN-03: Redundant exception classes in the CLI handlers

**Files modified:** `src/triagedesk/cli.py`
**Commit:** `d0a7a60`
**Applied fix:** `durable.DurableError` and `replay.ReplayError` are `RuntimeError` subclasses already
covered by the base in the handlers' `except` tuples, so the subclasses were dropped
(`(ValueError, RuntimeError, sqlite3.Error, ExceptionGroup)` on both the `resume` and `replay`
handlers). The now-unused `DurableError`/`ReplayError` imports were removed and the comments updated to
name the classes as `RuntimeError` subclasses so the intent stays explicit. No test references those
names through `triagedesk.cli`, so nothing else changed; `test_resume_reports_an_unexpected_failure_cleanly`
(a raw `RuntimeError`) still passes.

### IN-05: Docs still name the pre-WR-05 helper and overstate the digest seal

**Files modified:** `SECURITY.md`, `docs/DECISIONS.md`, `src/triagedesk/store/audit.py`
**Commit:** `be09595`
**Applied fix:** Aligned the design-source docs with the shipped code:
- `SECURITY.md` §10 and `docs/DECISIONS.md` D19 now reference `case_id_for_note(raw_note)` (the WR-05
  "strip then derive" helper) rather than the raw `case_id_for(raw_note)` primitive.
- The §10 seal sentence and D19's "(additive; sealed in the canonical digest)" now read "when
  non-empty", matching WR-03's rule that an empty `trace_id` is omitted from `canonical digest` while a
  non-empty one stays sealed and tamper-evident.
- The `AuditRecord` docstring in `store/audit.py` now names `graph.nodes.case_id_for_note`.
- Verified no `case_id_for(raw_note)` reference remains in `SECURITY.md`, `docs/DECISIONS.md` or
  `src/`. Historical `.planning/` planning artefacts (07-PLAN/07-RESEARCH/06-*) were left as-is —
  they are dated records, not the design single source CONVENTIONS §1 governs.

## Not in scope (Info findings)

IN-02 (the "one span per node" assertion wording), IN-04 (the observability barrel's broader-than-stated
`__all__`) and IN-06 (the pre-existing `evals/runner.py` private allowlist reach) were not requested for
this pass and were not addressed.

---

**Constraint compliance:** `core/scorer.py` and `core/citations.py` were untouched; the `@audited`
interceptor's audit behaviour (exactly one record per call, refusal path, actor/approver logic) is
unchanged; the graph topology is unchanged. All new tests are hermetic (real owned tools in-process,
model stubbed at its one seam, span sink redirected to `tmp_path`, no subprocess to `npx`, no network,
no repo-root artefact).

_Fixed: 2026-10-12T14:16:43Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 2_
