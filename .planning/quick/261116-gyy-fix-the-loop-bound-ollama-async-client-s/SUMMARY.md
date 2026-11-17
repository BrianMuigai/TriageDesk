# Quick Task 261116-gyy — loop-scoped async Ollama client

**Status:** complete
**Commit:** `4a24c8f` — `fix(llm): scope the async ollama client to its event loop`
**Branch:** `fix/planner-event-loop`
**Files changed:** `src/triagedesk/llm/client.py`, `tests/test_llm_client_async.py` (only)

## Root cause (as measured before the fix)

`llm/client._ASYNC_CLIENT` was a single module-level `ollama.AsyncClient`. That client owns an
`httpx.AsyncClient` bound to the event loop that constructed it.
`desk/interactive.main` calls `asyncio.run(...)` twice — once for note extraction, again for
`run_one` — so the planner's model call on the second loop raised instantly. `propose_plan_async`
swallows every transport exception and returns `None`, and `plan_next_step`'s guard then substituted
`finish_investigation`. The user's `spans.jsonl` recorded the consequence exactly:
`{"action":"finish_investigation","overridden":true,"proposed_action":null}` with a 1.5 ms `model`
child span and no token counts — no generation ever happened, which is how E-09 stopped asking its
glucose question.

## What changed

`src/triagedesk/llm/client.py`

- Cache is now `_ASYNC_CLIENT: tuple[asyncio.AbstractEventLoop, ollama.AsyncClient] | None`.
- `_async_client()` keys the cache on `asyncio.get_running_loop()`: same loop → same client;
  different loop → new client. Still built lazily on first use — nothing is constructed at import
  time (the offline/harden ordering still holds).
- A closed loop's client is dropped rather than closed (its loop is already gone; there is nothing
  to await on).
- The module comment and the `_async_client` docstring record why: loop-bound `httpx` client reused
  across `asyncio.run` calls raises instantly and the planner degrades to `finish_investigation`
  (the E-09 symptom above).
- No change to `_async_generate`, `extract`, `extract_async`, `propose_plan_async`, the planner, the
  guard, the graph, or the terminal — the async transport seam and every contract are untouched.

`tests/test_llm_client_async.py`

- `test_async_client_is_built_lazily_and_reused` (now `async def`, runs inside a loop): asserts no
  client exists before first use and the SAME client is returned twice within one loop.
- `test_async_client_is_rebuilt_for_a_new_event_loop` (new, sync): three consecutive
  `asyncio.run(...)` calls each inside their own loop return three distinct client objects.
  Identity only — no network, no `generate` call.
- Small helper `_client_from_this_loop()` returns the module's client for whichever loop is running.
- `import ollama` added for the helper's return annotation.

## Verification

| Gate | Command | Result |
| --- | --- | --- |
| Targeted tests | `uv run pytest -q tests/test_llm_client_async.py` | **7 passed** |
| Full suite | `uv run pytest -q` | **968 passed**, 0 failed |
| Lint | `uv run ruff check src tests` | **All checks passed** |

Test names in the targeted file (all passing):

- `test_extract_and_extract_async_share_one_core`
- `test_extract_async_overlaps_two_calls`
- `test_extract_async_raises_on_empty_and_on_invalid_json[empty|invalid-json]`
- `test_extract_async_forwards_usage_from_the_one_response`
- `test_async_client_is_built_lazily_and_reused` *(updated — now runs in a loop)*
- `test_async_client_is_rebuilt_for_a_new_event_loop` *(new regression)*

## Deviations

1. **Full-suite gate blocked by a pre-existing untracked artifact (out of scope, not committed).**
   The first `uv run pytest -q` failed one test,
   `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`, because the
   user's debug file `spans.jsonl` (gitignored, untracked, 9 637 bytes, dated before this task) sat
   at the repo root. That test asserts the artifact is *absent*; the failure is entirely
   environmental and independent of this change (the diff touches no observability code). To prove
   the suite is green, the artifact was temporarily moved to `/tmp/opencode/spans.jsonl.bak`, the
   suite re-run (968 passed), and the file restored — sha256 verified identical before and after
   (`7659ceda…9a44`). It remains untracked, unmodified and unstaged.
2. **Plan's baseline test count (">= the current 969") is inaccurate.** Measured baseline is **967**
   collected tests; this file held 6 before the change. With one test updated and one added, the
   file has 7 and the suite collects **968** — a net **+1**, which is the plan's intent ("+2
   new/updated tests" counts the updated test as new work, not as an added test). No test was
   dropped.
3. **Pre-existing mypy finding, untouched.** `uv run mypy` on the two files reports
   `Module "triagedesk.llm.client" does not explicitly export attribute "ollama"` at
   `tests/test_llm_client_async.py:58` — the pre-existing `monkeypatch.setattr(client.ollama, …)`
   line (line 52 at `HEAD`, shifted by this task's insertions). Out of scope; the mandated gates are
   pytest and ruff, both green.
4. **Worktree-side effect:** none. The commit stages only the two intended files; `.planning/`,
   `spans.jsonl`, `checkpoints.db`, `triage.db` and the untracked `docs/assets/*` files were left
   out (this SUMMARY itself is written after the commit and is not part of it).

## Notes for the reviewer

- The fix does not change the planner's degradable contract: a genuine transport failure still
  returns `None` and the guard still substitutes `finish_investigation`. What changes is that a
  healthy second loop is no longer *mistaken* for a failure.
- `_async_client()` now requires a running loop by design (it is only reached through
  `_async_generate`, which is always awaited); calling it outside a loop raises `RuntimeError`
  rather than silently creating an unusable client.
