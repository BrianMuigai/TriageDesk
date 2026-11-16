# Quick Task SUMMARY — one default store per loop, not one per call

- **Task:** `261116-hut-open-the-borrowed-audit-store-once-per-p`
- **Branch:** `fix/nurse-stress-test-batch`
- **Commit:** `1f4a5c1` — `fix(quick-261116-hut): open the default store once per loop`
- **Status:** complete, no incomplete work.

## The defect, measured

Every audited tool call re-resolved the store: `mcp/server.py::resolve_store` → `store.default_store()`
→ `open_borrowed_store(db)`. That launched a fresh `npx mcp-sqlite@1.0.9` and ensured the schema
**per call**, so even `score_priority` (integer arithmetic) and `match_discriminators` (a dict
lookup) carried the open cost. Nurse stress test 2026-11-16, S4: 3.12 s average over 41
`match_discriminators` calls (`128 s` total).

## What changed

`src/triagedesk/store/__init__.py`

- `default_store(db_path=None)` now returns **one** store per `(db_path, running event loop)`.
  The cache is a single `(path, loop, store)` triple, read first; a miss opens and stores.
- `reset_default_store()` — the ONE invalidation path, exported in `__all__`.
- Loop-keyed for the reason already recorded for `llm.client._async_client` (commit `4a24c8f`):
  the borrowed store owns async subprocess transports bound to the loop that created them, so a
  second `asyncio.run(...)` (the desk runs two loops) must get a **new** store while one loop
  reuses one. A closed loop's store is dropped, never closed — its loop is already gone.
- Single-entry cache, documented: alternating db paths rebuild (a test-only pattern; production
  names one domain db, `DOMAIN_DB_PATH`).
- The open is unchanged: still lazy-imported (`open_borrowed_store`), still in its own adapter
  context, schema ensured **once per open** instead of once per call.

`src/triagedesk/mcp/server.py`

- `resolve_store` docstring records the new contract. The code is untouched: an injected store
  (`set_store`) is returned first and is **never cached**, so the seam's precedence (D-13) and
  the offline/test path are exactly as before.

Nothing else moved: no change to `core/scorer.py`, the citation helper, the `@audited`
interceptor, `store/audit.py`, `store/borrowed.py`, or `data/*.yaml` (D-18).

Because a loop now holds exactly one store, the audit chain keeps its **single writer** — this
change removes store instances, it does not add any.

## Measured before → after

Local store (`/tmp/opencode/measure-triage.db`), same process, in-process `match_discriminators`
(the audited tool function, so the audit append and its span are included), 20 calls:

| Measurement | Before (open per call) | After (cached) |
| --- | --- | --- |
| 20 `default_store()` resolutions | **45.2 s** (2.26 s each) | **0.00 s** (one open, reused) |
| 20 `match_discriminators` calls | **45.6 s** (2.28 s each) | **0.20 s** (10 ms each) |

The residual ~10 ms per call is the audit append round-trip through the one borrowed server — no
subprocess launch. (The fix is measured by resetting the cache between calls for the "before"
column, i.e. reproducing the old per-call open on the same code path.)

## Tests added — `tests/test_default_store_cache.py`

All patch `triagedesk.store.borrowed.open_borrowed_store` (or use the autouse injected store), so
**no test launches a subprocess or touches the network**.

| Test | Proves |
| --- | --- |
| `test_one_loop_resolves_the_same_store_twice` | same object on one loop; factory called once |
| `test_a_different_db_path_gets_a_new_store` | the path is part of the key |
| `test_a_second_event_loop_gets_a_new_store` | two `asyncio.run(...)` calls get distinct stores (the `4a24c8f` failure mode) |
| `test_an_injected_store_wins_and_is_never_cached` | `set_store` wins twice with no factory call; clearing the seam resolves the borrowed default, not the injected store; that default is then cached |
| `test_reset_drops_the_cached_store` | `reset_default_store()` forces a fresh open |

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest tests/test_default_store_cache.py -q` | **5 passed** |
| targeted: `test_default_store_cache`, `test_store_seam`, `test_borrowed_store`, `test_audit_chain`, `test_durable_cli`, `test_replay_read_only`, `test_desk`, `test_mcp_tools` | **181 passed** |
| `uv run pytest -q` | **982 passed** |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src/triagedesk/store/__init__.py` | Success: no issues found |

## Deviations / judgement calls

- **Cache placed in `store.default_store`, not in `mcp/server.resolve_store`.** The default
  factory is already the ONE owner of "the default store" (`desk/waiting.py` calls it directly),
  so caching there fixes the desk's per-request open too and keeps one source of truth (DRY).
  `resolve_store`'s behaviour is unchanged; the injected seam still short-circuits it.
- **Single-entry cache rather than a dict keyed on loop.** Matches the existing `_ASYNC_CLIENT`
  pattern and cannot leak strong references to dead loops. Two different db paths alternating in
  one loop would thrash — acceptable, since no production path names more than one domain db.
- **No close on eviction.** A superseded store's transports belong to a loop that has either gone
  away (a closed loop cannot be awaited on to close cleanly) or still owns them. Same choice as
  `_async_client`.
- **Accepted risk — concurrent first resolve.** Two coroutines racing the *first* resolve on one
  loop can both open a store; the last write wins the cache and the loser is dropped. That race
  exists today on **every** call, so this is strictly narrower, and the shipped flows (a single
  desk loop, a one-shot CLI) do not issue overlapping first calls. Serialising the open would
  need a loop-bound lock and was not required by the plan.
- Only the three files above were staged; `.planning/`, `spans.jsonl`, `checkpoints.db`,
  `triage.db` and untracked `docs/assets/*` were left alone. (`spans.jsonl` created by the
  measurement run was gitignored and removed — the observability guard test requires it absent.)
