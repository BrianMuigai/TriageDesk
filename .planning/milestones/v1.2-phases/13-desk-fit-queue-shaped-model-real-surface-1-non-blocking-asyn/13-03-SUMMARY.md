---
phase: 13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn
plan: 03
subsystem: desk, core, store
tags: [waiting-room, acuity-order, queue-projection, keyboard, desk-surface, jc-3]
requires:
  - "triagedesk.core.rules.get_tews (the SATS band substrate)"
  - "triagedesk.desk.card._colour_class (the ONE colour -> CSS class mapping)"
  - "triagedesk.desk.markup._escaped (the ONE escaping rule)"
  - "triagedesk.store.QueueRow / Store / default_store (the queue read seam)"
  - "triagedesk.desk.loop.DeskLoop (the Plan-13-01 owned loop)"
provides:
  - "triagedesk.core.rules.colour_urgency (the ONE data-derived acuity rank)"
  - "triagedesk.desk.waiting.order_rows / wait_minutes / waiting_html / read_rows"
  - "DeskServer.store (the injectable read seam) and GET /waiting"
  - "keyboard-first vitals form (autofocus, enterkeyhint, clinical tab order)"
affects:
  - "the desk surface's navigation and queue legibility (JC-3)"
tech-stack:
  added: []
  patterns:
    - "one acuity rank in core.rules; the scorer delegates, the waiting room reads it"
    - "a read-only projection over read_queue_rows: no write call, guarded by AST + recorded calls"
    - "presentation-only keyboard attributes; DOM order is the tab order"
key-files:
  created:
    - src/triagedesk/desk/waiting.py
    - tests/test_desk_waiting.py
    - tests/test_desk_forms.py
  modified:
    - src/triagedesk/core/rules.py
    - src/triagedesk/core/scorer.py
    - src/triagedesk/desk/copy.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/views.py
    - src/triagedesk/desk/forms.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - src/triagedesk/store/memory.py
    - tests/test_desk.py
    - tests/test_replay_read_only.py
decisions:
  - "the acuity rank has ONE home (core.rules.colour_urgency); core.scorer._colour_urgency is a one-line delegate"
  - "the waiting room is a projection over read_queue_rows only; position and the idempotency key are untouched"
  - "an unbanded colour (BLUE) sorts last rather than raising, and naive datetimes are treated as UTC in one helper"
  - "GET /waiting resolves the store seam on the desk loop and renders the failure panel on any store error"
  - "keyboard attributes are presentation only: no field name, bound, value or submission changed"
metrics:
  duration: "~15m"
  completed: "2026-11-05T06:35:02Z"
status: complete
actuals:
  tokens: 10930
  tasks: 3
  commits: 3
  plan_head_before: 06a9d6bb16b2da75a8a79b1a59e571a3d68ca51b
  plan_head_after: abee2242049724e8600a835542bde827dca74096
---

# Phase 13 Plan 03: Acuity-ordered waiting room and keyboard-first vitals entry Summary

The desk is now queue-shaped: `GET /waiting` reads the committed queue once and renders it in
acuity order (then wait time, then the stable `position`), each row showing its committed
colour as a swatch and as text plus a wait timer, while the vitals form autofocuses the first
control and tabs through the clinical reading order. The stored position, the idempotency key
and the approval gate are untouched.

## What changed

### Task 1 — rows in, acuity order and wait timers out, with no write

- `core/rules.py`: new `colour_urgency(rules=None)` — `{band.colour: float(band.min)}` from
  `data/sats_tews.yaml`. This is the ONE acuity rank; no colour token is inlined.
- `core/scorer.py`: `_colour_urgency(rules)` is now a one-line delegate to it (the private name
  is kept so its callers and tests are untouched). No behaviour change.
- `desk/waiting.py` (new): `order_rows` sorts by
  `(-urgency.get(colour, -1.0), _epoch(created_at), position)` — acuity, then age, then the
  stable id; an unbanded colour sorts last. `_as_utc`/`_epoch` normalise a naive datetime to
  UTC so an older row cannot raise. `wait_minutes` floors at 0. `waiting_html` renders the
  panel (heading, caption, Position/Priority/Waiting/Target table, labelled colour swatch via
  the ONE `_colour_class`, `<time datetime=...>Waiting N min</time>`), the empty copy, or the
  failure panel and nothing else. `read_rows` makes the ONE store call.
- `desk/copy.py`: `_WAITING_HEADING`, `_WAITING_EMPTY`, `_WAITING_FAILED` (no prohibited token,
  no percentage).
- `store/memory.py`: `read_queue_rows` records `_note("read_queue_rows")`, so the read-only
  proof can observe the read; it is a no-op in production.
- `tests/test_desk_waiting.py` (new, 9 tests): data-derived order, one-home equality, wait
  arithmetic, labelled rendering, escaping, empty/error states, exactly-one-read, the AST
  no-write guard, and an in-place edit keeping its position while moving in the order.

### Task 2 — `GET /waiting` over an injectable store

- `desk/server.py`: `DeskServer.store` (default `None` = resolve the ONE store factory on
  demand); `make_server(..., store=None)` / `serve(..., store=None)` forward it; `do_GET`
  handles `/waiting` after the loopback Host check and after `name` is derived, before the
  asset allowlist (no path is built from `self.path`). `_waiting_page` runs `read_rows` on the
  server's ONE loop and catches any failure into the failure panel (200, no partial table).
- `desk/views.py`: `waiting: str = ""` threaded through `_render`/`render_state` into the new
  `$waiting` region; every `_render` call inside `render_state` passes it.
- `desk/static/index.html`: a static `<nav>` (Waiting room / New case) after the `<h1>`, and
  `$waiting` between the banner and `$card`.
- `desk/static/styles.css`: `.desk-nav`, `.waiting-room`, `.waiting-table` (+ th/td),
  `.waiting-caption`, `.waiting-empty`, and a compact `.waiting-room .colour-block` swatch —
  existing tokens only, no `url(`, no `@import`, no new colour literal.
- `tests/test_desk.py` (+3 tests): `_running_server(db_path, store=None)`; the route renders
  `order_rows` order and records only `read_queue_rows`; a failing store renders the panel;
  `GET /` never reads the store.

### Task 3 — keyboard-first vitals entry

- `desk/forms.py`: `_VITALS_LAYOUT` reordered into the clinical reading order (context block,
  AVPU, breathing, SpO2, heart rate, systolic, diastolic, temperature, mobility, trauma,
  complaint) with every label and field name unchanged; `_vitals_field(..., autofocus=False)`
  adds ` autofocus` to the numeric/select/text control only, `enterkeyhint="next"` to numeric
  inputs and `enterkeyhint="enter"` to the complaint; `_vitals_fields` passes
  `autofocus=(index == 0)`.
- `tests/test_desk_forms.py` (new, 5 tests): exactly one autofocus on `age_years`, every
  numeric control hints `next` and the complaint hints `enter`, DOM id order equals the layout,
  names/bounds/submit path unchanged, and an AST guard proves no new import.

## Safety argument — as executed

1. **Read-only by construction.** `desk/waiting.py` calls only `read_queue_rows`; the AST guard
   proves no write method is called, and the route test records exactly
   `[("read_queue_rows", ())]`. A store failure renders a panel, never a partial table.
2. **No identity change.** `store/queue.py` and the UPSERT are untouched; an in-place edit keeps
   `position` and `created_at`, and the idempotency key is unchanged. The order is a projection.
3. **No new colour source.** Each row renders its committed `colour` with its name through the
   ONE `_colour_class`; the module computes no colour and no rank literal.
4. **No new commit path.** The package-wide desk import guard still passes; `GET /waiting` is a
   read route behind the unchanged loopback Host guard and the asset allowlist.
5. **Keyboard attributes cannot change a submission.** Names, values, schema bounds and
   `action="/case"` are asserted unchanged; no dependency was added.
6. **`GET /` stays read-free.** No store read on the main page, so the offline desk launches no
   borrowed subprocess on a page load.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The new read-recording hook broke a replay assertion**

- **Found during:** Task 2 (full-suite verification)
- **Issue:** The plan predicted `tests/test_replay_read_only.py::test_replay_writes_nothing`
  would be unaffected because it "compares before/after lengths". In fact its comparison
  counts every recorded queue-protocol call, so the newly recorded `read_queue_rows` made it
  fail (5 vs 4). The plan's claim was wrong; the waiting-room design is sound.
- **Fix:** The assertion now compares the call lists with `read_queue_rows` filtered out on
  both sides, so it still proves "replay adds no write" (and the row/commit/audit assertions
  are unchanged).
- **Files modified:** `tests/test_replay_read_only.py`
- **Commit:** `00a4c0c`

**2. [Rule 1 - Bug] The waiting-room CSS comment tripped the prohibited-token scan**

- **Found during:** Task 2 (full-suite verification)
- **Issue:** A CSS comment naming "Plan 13-03" contained the prohibited token `plan`, which the
  rendered-copy guard scans in `styles.css`.
- **Fix:** Removed the plan reference from the comment; no rule changed.
- **Files modified:** `src/triagedesk/desk/static/styles.css`
- **Commit:** `00a4c0c`

### Implementation notes (not behaviour changes)

- The manual `uv run triagedesk demo` verification (exit 0) writes the production default span
  sink `spans.jsonl` at the repo root; the generated, gitignored file was removed before the
  final suite run so the "no repo-root spans artifact" guard stays green.

## Authentication gates

None.

## Known Stubs

None.

## Threat Flags

None — no new network surface, no new write route, no new colour source, and no package
installed (ZERO installs; stdlib + existing deps only).

## Self-Check

- `src/triagedesk/desk/waiting.py` exists — FOUND
- `tests/test_desk_waiting.py` exists — FOUND
- `tests/test_desk_forms.py` exists — FOUND
- commit `da1bb08` is an ancestor of HEAD — FOUND
- commit `00a4c0c` is an ancestor of HEAD — FOUND
- commit `abee224` is an ancestor of HEAD — FOUND
- `uv run pytest -q --ignore=tests/test_triage_skill.py` — 585 passed (plan baseline 568)
- `uv run ruff check src tests` — All checks passed
- `uv run triagedesk demo` — exit 0

## Self-Check: PASSED
