# Quick Task: open the borrowed audit store once per process and event loop

## Goal
Remove the ~2.6–3.1 s floor on every audited tool call caused by resolving a brand-new borrowed
store per call.

## Measured defect (nurse stress test 2026-11-16, S4)
`match_discriminators` averaged 3.12 s over 41 calls; `score_priority` 2.5–2.6 s for pure integer
arithmetic. `mcp/server.py::resolve_store` calls `store.default_store()` →
`open_borrowed_store(db)` on EVERY call, launching a fresh `npx mcp-sqlite@1.0.9` and ensuring
the schema each time.

## Change
Cache the DEFAULT store, keyed on `(db_path, running event loop)`.

- An **injected** store (`set_store`) still wins and is never cached.
- The borrowed store holds async subprocess transports, which are bound to the event loop that
  created them — the same failure mode as `llm/client._async_client` (commit `4a24c8f`). A new
  loop must therefore get a NEW store; reuse within one loop.
- Provide a small module-level reset (e.g. `reset_default_store()`) for tests and document the
  lifetime (one store per process per loop, closed/dropped with it).
- Keep the audit chain single-writer: the cached instance is the same single store per loop, so
  no new concurrency is introduced.

## Acceptance
- Tests: two `resolve_store()` calls on one loop return the SAME object; a different loop gets a
  different object; an injected store wins and is not cached; reset drops the cached one. Patch
  `open_borrowed_store` (or inject a fake) so tests launch no subprocess and no network.
- Full suite green.
- Record in SUMMARY a measured before/after for 20 `match_discriminators` calls (local store is
  fine here).

## Operating constraints

- Work only in the git worktree `/tmp/opencode/triage-batch` (branch `fix/nurse-stress-test-batch`).
- Stage ONLY the files this plan names. Never stage `.planning/`, `spans.jsonl`, `checkpoints.db`,
  `triage.db`, or any untracked `docs/assets/*` file.
- Commit atomically with a conventional message.
- Follow `docs/CONVENTIONS.md` (DRY + SOLID). Do not edit the scorer's arithmetic (`core/scorer.py`),
  the citation helper or the `@audited` interceptor unless this plan explicitly says so (D-18).
- Run the targeted tests you add/update, plus `uv run ruff check src tests`.

## Report back

Commit hash, files changed, test names, targeted + full-suite counts, ruff result, any deviation.
