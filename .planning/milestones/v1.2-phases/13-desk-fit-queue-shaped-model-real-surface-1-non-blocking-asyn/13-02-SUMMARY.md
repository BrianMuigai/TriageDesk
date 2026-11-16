---
phase: 13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn
plan: 02
subsystem: desk, llm, evals
tags: [online-mode, extraction, precompute, cache, desk-surface, jc-1, jc-3]
requires:
  - "triagedesk.llm.client.extract_async (the Plan-13-01 async transport)"
  - "triagedesk.core.matcher.validate_discriminator_ids (the closed set)"
  - "triagedesk.core.hashing.hash_value (the ONE hashing path)"
  - "triagedesk.desk.loop.DeskLoop (the Plan-13-01 owned loop)"
provides:
  - "triagedesk.desk.extraction.extract_complaint / merge_case / complaint_key / PrecomputeCache"
  - "triagedesk.evals.tools.online_tools (harness-free, pre-computed extraction)"
  - "DeskServer.online / DeskServer.extraction"
  - "POST /precompute (guarded, 204, fire-and-forget)"
  - "triagedesk desk --online"
affects:
  - "13-03 waiting-room read (the desk now has a labelled online mode and a precompute seam)"
tech-stack:
  added: []
  patterns:
    - "one extraction seam: model -> closed-set filter -> merge under the form"
    - "precompute keyed by a content hash, bounded FIFO, fail-safe take"
    - "one tool map, three ways to supply normalize (offline / harness / online)"
key-files:
  created:
    - src/triagedesk/desk/extraction.py
    - tests/test_desk_online.py
  modified:
    - src/triagedesk/core/matcher.py
    - src/triagedesk/mcp/server.py
    - src/triagedesk/evals/tools.py
    - src/triagedesk/desk/pipeline.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/views.py
    - src/triagedesk/desk/copy.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/cli.py
decisions:
  - "the closed-set discriminator filter has one home (matcher.filter_discriminator_ids); the owned tool and the desk both call it"
  - "merge_case overlays every non-None form field, so the nurse's case is the scored case by construction"
  - "the cache key is hash_value({'complaint': text}) — no hash(), no second digest"
  - "PrecomputeCache is loop-local and lock-free; start never awaits the model, take is the only observer"
  - "the precompute calls extract_async directly, never the audited tool, so it appends no audit record"
  - "offline stays the default everywhere: serve/make_server/DeskServer default to online=False"
metrics:
  duration: "~20m"
  completed: "2026-11-05T06:23:10Z"
status: complete
actuals:
  tokens: 11620
  tasks: 3
  commits: 3
  plan_head_before: 577a37150fea3c440e6481f5c82f485d194b76cc
  plan_head_after: 06a9d6bb16b2da75a8a79b1a59e571a3d68ca51b
---

# Phase 13 Plan 02: Online desk extraction with background precompute Summary

The desk can now run the REAL local extraction on the free-text complaint — precomputed in
the background while the nurse finishes the vitals — while the default stays offline, the
nurse's typed vitals always win, and the deterministic scorer still decides the colour.

## What changed

### Task 1 — a complaint becomes a real extraction, merged under the form

- `core/matcher.py`: new `filter_discriminator_ids(result)` — the ONE home for "the model may
  not choose an id outside the closed set". It delegates to the existing
  `validate_discriminator_ids` and sets `no_discriminator_matched` from what survives.
- `mcp/server.py`: `normalize_case` now calls that one function instead of restating the
  three filtering lines. Behaviour is byte-identical.
- `evals/tools.py`: `_tool_map` gained a keyword-only `extraction` parameter, checked before
  the `offline` branch, and the public `online_tools(case, extraction, recorder)` delegates to
  it. The seven tools and their order are unchanged; `__all__` and the module docstring say so.
- `desk/extraction.py` (new): `extract_complaint` (awaits `llm.client.extract_async`, then the
  closed-set filter) and `merge_case` (every non-`None` form field over the extracted case).
  No store, no queue, no second prompt, no number.
- `desk/pipeline.py`: `_tools_for(case, extraction)` and
  `submit_case(..., *, extraction=None)` — one code path, `raw_note` unchanged, so the
  content-derived thread id is identical in both modes.

Proofs in `tests/test_desk_online.py`: online and offline produce the same colour and the same
non-empty citations; a stub extraction claiming RR 60 / HR 200 cannot overwrite the form's
RR 24 / HR 118; the closed-set filter drops unknown ids and sets the coverage signal; the
offline submit never calls the model even when the seam raises.

### Task 2 — the precompute cache

- `complaint_key(complaint)` = `hash_value({"complaint": complaint})` — the ONE hashing helper,
  never `hash()` and never a second digest.
- `PrecomputeCache` holds `dict[str, asyncio.Task[ExtractionResult]]`, bounded to
  `_MAX_ENTRIES = 32` with FIFO eviction (cancel + drop). `start` is a no-op for a blank
  complaint or an existing key; `take` pops and awaits, returning `None` on a miss or a
  failure and re-raising `asyncio.CancelledError`. Every method runs on the desk loop, so no
  lock is needed; `__len__` exists for the bound proof.

Proofs: one model call per hit and the second take is a miss; a never-started key costs no
call; a failing extraction returns `None` and the normal path still yields a cited colour;
`_MAX_ENTRIES + 1` distinct complaints leave exactly 32 with the oldest cancelled; the key is
content-derived and equals the one hashing helper's output.

### Task 3 — the online surface

- `desk/copy.py`: `_MODE_OFFLINE` / `_MODE_ONLINE`, one sentence each, naming the live mode and
  stating the deterministic scorer decides the colour. Both are free of every
  `prohibited_tokens()` entry and of any percentage.
- `desk/views.py`: `mode_label` threaded through `_render` and `render_state` (default
  `_MODE_OFFLINE`) into the new `$mode_label` region; every `_render` call inside
  `render_state` passes it, so a direct render labels the offline default.
- `desk/static/index.html`: `<p class="mode-label">$mode_label</p>` after the `<h1>`, and an
  inline `change` listener on `#complaint` that POSTs the form's own fields (CSRF included) to
  the relative `/precompute` and ignores failures. No `<script src>`, no absolute URL, no
  `url(`.
- `desk/server.py`: `DeskServer.online` / `DeskServer.extraction` (default offline + a fresh
  cache); `make_server(..., online=False)` and `serve(..., online=False)` forward it; `_page`
  labels the live mode; `do_POST` dispatches `/precompute` behind the unchanged
  Host/Origin/CSRF/Content-Length preamble; `_handle_precompute` no-ops offline or blank and
  otherwise starts the extraction on the loop and returns 204; `_handle_case` resolves the
  extraction on the loop before the write lock, reuses a hit, makes one in-path call on a
  miss, and degrades to `None` on failure; offline mode passes nothing.
- `cli.py`: `desk --online` (`store_true`) forwarded as `online=args.online`.

Proofs: both page labels (and the offline default on a direct render); the CLI forwards
`True`/`False`; two `/precompute` POSTs for one complaint start exactly one extraction; an
offline `/precompute` is a 204 no-op with no model call; a warmed cache makes a `/case` submit
cost exactly one model call in total and still render a card with a colour name and a citation.

## Safety argument — as executed

1. **The model cannot move a vital.** `merge_case` overlays every non-`None` `CaseInput` field
   of the form; asserted field-by-field in `test_the_model_cannot_overwrite_a_nurse_value`.
2. **The model cannot move the colour.** Two `submit_case` runs over separate checkpoint files
   (one offline, one with a stubbed extraction) produce equal, non-empty `citations` and equal
   `colour`.
3. **No uncited priority.** The extraction never produces a `PriorityResult`; the colour and
   citations come only from `core.scorer.score_priority`.
4. **No new commit path.** `desk/` still imports neither `triagedesk.store.queue` nor
   `triagedesk.mcp.server` (the package-wide AST guard passed), and the gate is untouched.
5. **Precompute cannot corrupt the audit chain.** It calls `llm.client.extract_async`
   directly, never the audited owned tool, so it appends no audit record.
6. **Offline is unchanged.** `uv run triagedesk demo` still runs offline from the fixtures
   (exit 0, no model span) and the offline submit path calls no model.

## Deviations from Plan

None — the plan executed as written. Two implementation notes, neither a behaviour change:

- The new `tests/test_desk_online.py` reuses the loopback request helpers (`_base`,
  `_csrf_token`, `_get`, `_post`, `_request_status`, `_section`, `_form_from_case`) by
  importing them from `tests/test_desk.py` rather than restating them, honouring the DRY rule.
  It defines only the one helper the shared suite lacks: a `_running_server(..., online=...)`
  wrapper.
- A `spans.jsonl` produced by the manual `triagedesk demo` verification (the production
  default sink) was removed before the final suite run; it is a generated, gitignored artifact,
  not part of the change.

## Authentication gates

None.

## Known Stubs

None.

## Threat Flags

None — no new network surface, no new route to the queue, no new colour source, and no package
installed. `POST /precompute` reuses the existing guard preamble and returns 204 with no body.

## Self-Check

- `src/triagedesk/desk/extraction.py` exists — FOUND
- `tests/test_desk_online.py` exists — FOUND
- commit `346b0ec` is an ancestor of HEAD — FOUND
- commit `203044d` is an ancestor of HEAD — FOUND
- commit `06a9d6b` is an ancestor of HEAD — FOUND
- `uv run pytest -q --ignore=tests/test_triage_skill.py` — 568 passed (baseline 553, +15)
- `uv run ruff check src tests` — All checks passed

## Self-Check: PASSED
