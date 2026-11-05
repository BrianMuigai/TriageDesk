---
phase: 13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn
plan: 01
subsystem: llm, mcp, desk
tags: [async, event-loop, mcp-tool, desk-surface, jc-1]
requires:
  - "triagedesk.llm.client.extract (the sync transport)"
  - "triagedesk.mcp.server.normalize_case (the owned read-only tool)"
  - "triagedesk.desk.pipeline.submit_case/decide"
provides:
  - "triagedesk.llm.client.extract_async (one core, two transports)"
  - "triagedesk.desk.loop.DeskLoop (one loop per desk server)"
  - "DeskServer.serialised (the one in-loop write lock)"
affects:
  - "13-02 precompute (uses DeskLoop.submit while a submit awaits)"
  - "13-03 waiting-room read (runs on the same free loop)"
tech-stack:
  added: []
  patterns:
    - "one core / two transports (sync + async share prompt, parser, grounding and span)"
    - "one owned event loop on a dedicated daemon thread"
key-files:
  created:
    - src/triagedesk/desk/loop.py
    - tests/test_llm_client_async.py
  modified:
    - src/triagedesk/llm/client.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/evals/usage.py
    - src/triagedesk/evals/tools.py
    - src/triagedesk/evals/__init__.py
    - src/triagedesk/desk/server.py
    - tests/conftest.py
    - tests/test_desk.py
    - tests/test_mcp_server.py
    - tests/test_mcp_tools.py
    - tests/test_audit_chain.py
    - tests/test_replay_read_only.py
    - tests/test_graph_durable.py
    - tests/test_graph_purity.py
    - tests/test_observability.py
decisions:
  - "extract_async shares _prompt_for/_usage_attrs/_parsed with extract; only the transport differs"
  - "the async Ollama client is built lazily, never at import, so desk imports prime no network"
  - "normalize_case awaits extract_async; its contract, audit record and closed-set filter are unchanged"
  - "the desk owns one DeskLoop and one asyncio.Lock; both handlers run through DeskServer.serialised"
  - "the purity guard poisons both transport seams (sync and async raising stubs)"
metrics:
  duration: "~13m"
  completed: "2026-11-05T06:05:06Z"
status: complete
actuals:
  tokens: 12449
  tasks: 3
  commits: 3
plan_head_before: 8c41d540ea23c8068e83197e36153d21e79f5c07
plan_head_after: 577a37150fea3c440e6481f5c82f485d194b76cc
---

# Phase 13 Plan 01: Non-blocking async extraction and one desk event loop Summary

One async extraction core behind the existing client interface, an owned `normalize_case`
tool that awaits it, and a desk server that owns ONE long-lived event loop for its whole
lifetime instead of building and destroying a loop per POST.

## What changed

### Task 1 — one core, two transports

`src/triagedesk/llm/client.py` now factors the extraction into three helpers that both
transports use:

- `_prompt_for(note, discriminator_ids)` — the ONE schema + prompt builder;
- `_usage_attrs(response, attrs)` — the ONE token-count placement inside the span;
- `_parsed(response, note)` — the ONE empty-check / validation / grounding step.

`extract` keeps its signature, docstring, span order and `ExtractionError` contract.
`extract_async` has the same body shape, awaiting `_async_generate`, which uses a lazily
built `ollama.AsyncClient` (never constructed at import). Both emit the same minimal
`model` span (`model`, `tokens_in`, `tokens_out`; no note, prompt or completion).

`tests/test_llm_client_async.py` proves equal results across transports, one model span
per call with identical attributes, measured overlap of two concurrent calls (peak 2,
elapsed < 0.09 s), fail-closed parsing on empty/invalid JSON, one forwarded usage pair,
and lazy client reuse.

### Task 2 — the owned tool awaits the async path

- `mcp/server.py`: `normalize_case` is `async` and awaits `extract_async`; the closed-set
  filter and `no_discriminator_matched` derivation are byte-for-byte the same. `@audited`
  already awaits an awaitable, so exactly one audit record per call is preserved.
- `evals/usage.py`: `recorded_extract` became `recorded_extract_async`; the dead sync
  wrapper was removed. `evals/__init__.py` re-exports the new name.
- `evals/tools.py`: `recorded_extract_seam` now swaps `server_module.extract_async`.
- `tests/conftest.py`: added the shared `async_return(value)` stub helper and an autouse
  `_model_seam_is_stubbed` fixture that raises on an unpatched model call.
- Every patch site moved to `extract_async` with `async_return(...)`; the replay "never
  calls the model" test now patches `triagedesk.llm.client.extract_async`, and the purity
  guard poisons both `extract` and `extract_async`.

### Task 3 — one event loop for the desk's lifetime

- `src/triagedesk/desk/loop.py` (new): `DeskLoop` runs one private loop on a dedicated
  daemon thread; `start()` blocks until the loop is running; `run(coro)` returns the
  result; `submit(coro)` returns the future; `stop()` stops, joins and closes the loop and
  is idempotent; `run`/`submit` after `stop()` raise `RuntimeError` (fail-closed).
- `desk/server.py`: `DeskServer` owns `self.loop` and one `asyncio.Lock`; `serialised(coro)`
  is the ONE in-loop serialisation of checkpoint-touching work; both handlers call
  `self.server.loop.run(self.server.serialised(...))`; `server_close()` stops the loop;
  `serve()` always tears down in a `finally`; `asyncio.run` is gone and `threading` is no
  longer imported.
- `tests/test_desk.py` proves one distinct loop id across two POSTs, a slow submit leaves
  the loop free, teardown joins the thread and fails closed, and the structural guard
  rejects `asyncio.run(` in the desk server.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `evals/__init__.py` still imported the removed `recorded_extract`**
- **Found during:** Task 2
- **Issue:** Renaming the usage seam in `evals/usage.py` left the package re-export broken.
- **Fix:** Updated the import and `__all__` to `recorded_extract_async`.
- **Files modified:** `src/triagedesk/evals/__init__.py`
- **Commit:** `5e5199a`

**2. [Rule 1 - Bug] `server_close` is called by `TCPServer.__init__` before the loop exists**
- **Found during:** Task 3
- **Issue:** A bind failure makes `socketserver.TCPServer.__init__` call `server_close()`
  before `DeskServer` has created `self.loop`, so the override would raise `AttributeError`
  and mask the real bind error.
- **Fix:** Stop the loop only when it exists (`getattr(self, "loop", None)`), then always
  call `super().server_close()`.
- **Files modified:** `src/triagedesk/desk/server.py`
- **Commit:** `577a371`

**3. [Rule 1 - Bug] The purity guard would have been vacuous for the async transport**
- **Found during:** Task 2
- **Issue:** Patching only the sync `extract` name leaves the new awaited seam unpoisoned.
- **Fix:** Added `_model_must_not_run_async` and patched both `extract` and `extract_async`.
- **Files modified:** `tests/test_graph_purity.py`
- **Commit:** `5e5199a`

### Note on the plan's stated baseline

The plan's verification section says "Baseline to preserve: 502 passed". The pre-plan tree
on this branch actually collects **543** tests (the branch had moved on since that number
was written). The plan adds 6 tests in `tests/test_llm_client_async.py` and 4 in
`tests/test_desk.py`, giving **553 passed** at HEAD. No pre-existing test was removed or
skipped.

## Authentication gates

None.

## Known Stubs

None.

## Threat Flags

None — no new network surface, no new route to the queue, no new colour source, and no
package installed.

## Self-Check

- `src/triagedesk/desk/loop.py` exists — FOUND
- `tests/test_llm_client_async.py` exists — FOUND
- commit `9d891cc` is an ancestor of HEAD — FOUND
- commit `5e5199a` is an ancestor of HEAD — FOUND
- commit `577a371` is an ancestor of HEAD — FOUND
- `uv run pytest -q --ignore=tests/test_triage_skill.py` — 553 passed
- `uv run ruff check src tests` — All checks passed

## Self-Check: PASSED
