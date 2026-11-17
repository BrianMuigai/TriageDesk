# Quick Task: loop-scoped async Ollama client

**Goal:** the interactive terminal's planner must actually run on the second event loop, so an
ambiguous case (E-09) asks its bounded clarification question instead of silently finishing.

## Grounded facts

- `src/triagedesk/llm/client.py` caches ONE `ollama.AsyncClient` in the module global
  `_ASYNC_CLIENT`, built lazily by `_async_client()` and used by `_async_generate()`.
  An `ollama.AsyncClient` owns an `httpx.AsyncClient` bound to the event loop that created it.
- `desk/interactive.py::main` calls `asyncio.run(...)` more than once: once for the raw-note
  extraction (`_intake_from_note` / `collect_case`) and again for `run_one`. The second loop
  reuses the first loop's client, so the call raises immediately.
- `llm/client.py::propose_plan_async` catches every transport exception and returns `None`;
  `mcp/server.py::plan_next_step` then hands that `None` to the guard, which substitutes
  `finish_investigation` (`overridden=true, proposed_action=null`).
- Measured in the user's run: the plan `decision` span is `{"action":"finish_investigation",
  "overridden":true,"proposed_action":null,"step":1}` and its child `model` span lasts 1.5 ms
  with no token counts — no generation happened.
- Demo and desk use a single event loop, so they are unaffected; any caller that invokes
  `asyncio.run` twice (the terminal, tests) is affected.
- `tests/test_llm_client_async.py::test_async_client_is_built_lazily_and_reused` currently
  asserts one process-wide client and resets the global.

## Change

1. Make the cache **per running event loop** in `llm/client.py`:
   - keep laziness (nothing constructed at import time);
   - reuse the SAME client for repeated calls on one loop;
   - build a NEW client when the running loop changes (the old loop is closed).
   Suggested shape: `_ASYNC_CLIENT: tuple[asyncio.AbstractEventLoop, ollama.AsyncClient] | None`,
   `_async_client()` keyed on `asyncio.get_running_loop()`.
2. Document in the `_async_client` docstring why: a loop-bound `httpx` client reused across
   `asyncio.run` calls raises instantly and the planner degrades to `finish_investigation`,
   which is how E-09 stopped asking its glucose question.
3. Update `test_async_client_is_built_lazily_and_reused` to run inside loops and add a
   regression test: a second `asyncio.run` gets a NEW client (not the first loop's), proving
   the failure mode is gone. No network: do not call `generate`; assert on identity.
4. No other module changes. Do not change the planner contract, the guard, the graph or the
   terminal's `asyncio.run` structure.

## Acceptance criteria

- `uv run pytest -q` passes (>= the current 969; +2 new/updated tests).
- `uv run ruff check src tests` clean.
- The two tests prove: lazy build; same client within one loop; DIFFERENT client on a new loop.
- Only `src/triagedesk/llm/client.py` and `tests/test_llm_client_async.py` change.
- Commit (conventional) on the current branch; do not commit `.planning/` or any untracked
  `docs/assets/*` file.

## Verification

`uv run pytest -q tests/test_llm_client_async.py`, then the full suite and ruff.
