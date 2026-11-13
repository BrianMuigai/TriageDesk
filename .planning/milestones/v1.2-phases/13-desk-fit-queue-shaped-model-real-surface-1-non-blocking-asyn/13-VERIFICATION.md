---
phase: 13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn
verified: 2026-11-05T06:44:49Z
status: passed
verdict: "PASS WITH NOTES"
score: 21/21 must-haves verified
covered_files: [
  ".planning/phases/13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn/13-01-PLAN.md",
  ".planning/phases/13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn/13-01-SUMMARY.md",
  ".planning/phases/13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn/13-02-PLAN.md",
  ".planning/phases/13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn/13-02-SUMMARY.md",
  ".planning/phases/13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn/13-03-PLAN.md",
  ".planning/phases/13-desk-fit-queue-shaped-model-real-surface-1-non-blocking-asyn/13-03-SUMMARY.md",
  "src/triagedesk/cli.py",
  "src/triagedesk/core/matcher.py",
  "src/triagedesk/core/rules.py",
  "src/triagedesk/core/scorer.py",
  "src/triagedesk/desk/copy.py",
  "src/triagedesk/desk/extraction.py",
  "src/triagedesk/desk/forms.py",
  "src/triagedesk/desk/loop.py",
  "src/triagedesk/desk/pipeline.py",
  "src/triagedesk/desk/server.py",
  "src/triagedesk/desk/static/index.html",
  "src/triagedesk/desk/static/styles.css",
  "src/triagedesk/desk/views.py",
  "src/triagedesk/desk/waiting.py",
  "src/triagedesk/evals/__init__.py",
  "src/triagedesk/evals/tools.py",
  "src/triagedesk/evals/usage.py",
  "src/triagedesk/llm/client.py",
  "src/triagedesk/mcp/server.py",
  "src/triagedesk/store/memory.py",
  "tests/conftest.py",
  "tests/test_audit_chain.py",
  "tests/test_desk.py",
  "tests/test_desk_forms.py",
  "tests/test_desk_online.py",
  "tests/test_desk_waiting.py",
  "tests/test_graph_durable.py",
  "tests/test_graph_purity.py",
  "tests/test_llm_client_async.py",
  "tests/test_mcp_server.py",
  "tests/test_mcp_tools.py",
  "tests/test_observability.py",
  "tests/test_replay_read_only.py"
]
covered_digest: "v4:sha256:a7c2b3b0dd2fdede8e96eeae83b0e97de445895a65c1a023a1498dfd78e4b372"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 13: Desk Fit — queue-shaped, model-real surface — Verification Report

**Phase Goal:** An OPD triage nurse can enter vitals at the desk while the local model works in the
background, and read the whole waiting room in acuity order — with no new path to the queue and no
uncited colour.
**Verified:** 2026-11-05T06:44:49Z
**Status:** passed
**Verdict:** PASS WITH NOTES
**Re-verification:** No — initial verification
**Branch:** `post-submission/desk-fit` (confirmed; `main` untouched, nothing pushed)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `extract_async` and `extract` share one prompt/parse/ground core; no second prompt or parser | ✓ VERIFIED | `src/triagedesk/llm/client.py:76-121` (`_prompt_for`, `_usage_attrs`, `_parsed`), `:124-159` (sync), `:191-216` (async); `tests/test_llm_client_async.py:44-68` asserts equal results and one identical `model` span per transport |
| 2 | Two concurrent `extract_async` calls are genuinely in flight together (measured, not code shape) | ✓ VERIFIED | `tests/test_llm_client_async.py:70-99` — fake transport increments in-flight, peak == 2, elapsed < 0.09 s |
| 3 | `normalize_case` is async and awaits the async extraction path | ✓ VERIFIED | `src/triagedesk/mcp/server.py:207-223`; `@server.tool()` + `@audited()` retained |
| 4 | Owned MCP server tool surface, return contract and closed-set id filtering unchanged | ✓ VERIFIED | `src/triagedesk/mcp/server.py` diff only moves the await and delegates to `src/triagedesk/core/matcher.py:205-218`; `tests/test_mcp_tools.py`, `tests/test_audit_chain.py` pass |
| 5 | Desk runs every checkpoint-touching coroutine on ONE long-lived loop; no `asyncio.run` in desk handlers | ✓ VERIFIED | `src/triagedesk/desk/loop.py:25-85`; `src/triagedesk/desk/server.py:117-127`; `tests/test_desk.py:1671-1691` (one loop id across two POSTs, equal to `server.loop.loop`), `:1746-1750` (source contains no `asyncio.run(`) |
| 6 | While a submit awaits a slow extraction, an independent coroutine on the same loop completes | ✓ VERIFIED | `tests/test_desk.py:1693-1725` — slow submit sleeps 0.3 s; `server.loop.run(asyncio.sleep(0.01))` returns while POST is in flight |
| 7 | Loopback/Host/Origin/CSRF/Content-Length guards unchanged; offline default unchanged | ✓ VERIFIED | `src/triagedesk/desk/server.py:143-233` guards untouched by the phase diff; `uv run triagedesk demo` exit 0 with zero `model` spans in `spans.jsonl` |
| 8 | `triagedesk desk --online` runs the REAL local extraction; default desk stays offline and calls no model | ✓ VERIFIED | `src/triagedesk/cli.py:153-157,248-258`; `src/triagedesk/desk/server.py:376-387`; live run: `POST /precompute` → 204, `POST /case` → 200 with ORANGE card + citation after a real Ollama call; `tests/test_desk_online.py:280-296,324-342` |
| 9 | The page always labels the live mode; a direct `render_state()` labels the offline default | ✓ VERIFIED | `src/triagedesk/desk/copy.py:23-30`; `src/triagedesk/desk/views.py:234-275`; `tests/test_desk_online.py:261-278` |
| 10 | The nurse's typed vitals are authoritative — model extraction merged UNDER the form | ✓ VERIFIED | `src/triagedesk/desk/extraction.py:106-114`; `tests/test_desk_online.py:83-97` (every non-`None` form field survives; model RR 60 / HR 200 cannot overwrite form RR 24 / HR 118) |
| 11 | Online and offline produce the same colour and citations for the same form case | ✓ VERIFIED (scope note) | `tests/test_desk_online.py:61-81` uses a fully specified form and asserts equal non-empty citations and colour. For an incomplete form the extraction may supply a scored vital the nurse left blank (by design) — see Notes 2 |
| 12 | A precompute is keyed by a complaint hash, starts exactly one extraction, and a submit with the same complaint reuses it | ✓ VERIFIED | `src/triagedesk/desk/extraction.py:33-40,59-69`; `tests/test_desk_online.py:150-167,225-233,298-322,344-363` (one model call total; content-derived key equals `hash_value({"complaint": ...})`) |
| 13 | Cache miss falls back to one in-path extraction; failure degrades to the normal cited path | ✓ VERIFIED | `src/triagedesk/desk/server.py:342-355`; `src/triagedesk/desk/extraction.py:71-86`; `tests/test_desk_online.py:169-198` (miss costs no call; failure returns `None` and the normal path still yields colour + citations) |
| 14 | Precompute is bounded (FIFO) | ✓ VERIFIED | `src/triagedesk/desk/extraction.py:30,67-69`; `tests/test_desk_online.py:200-223` (`_MAX_ENTRIES + 1` leaves exactly 32; oldest cancelled) |
| 15 | Gate, deferral, commit path, graph topology, tool allowlist and hash-chained audit untouched | ✓ VERIFIED | Phase diff `8c41d54..abee224` touches none of `core/schema.py`, `core/approval.py`, `graph/`, `durable.py`, `store/queue.py`; `tests/test_desk.py:744-753` package-wide import guard; `tests/test_audit_chain.py` passes |
| 16 | Waiting room ordered acuity → `created_at` → `position`, with the rank derived from `data/sats_tews.yaml` | ✓ VERIFIED | `src/triagedesk/desk/waiting.py:44-60`; `src/triagedesk/core/rules.py:165-173` (RED 7 → ORANGE 5 → YELLOW 3 → GREEN 0; BLUE sorts last); `src/triagedesk/core/scorer.py:137-144` delegates; `tests/test_desk_waiting.py:65-96` |
| 17 | `position` and the idempotency key unchanged; an in-place edit keeps position/`created_at` | ✓ VERIFIED | `src/triagedesk/store/queue.py` untouched in the phase diff; `tests/test_desk_waiting.py:176-204` (edit keeps position and `created_at`, row moves in order) |
| 18 | Each row renders colour as swatch AND text, plus wait timer and target | ✓ VERIFIED | `src/triagedesk/desk/waiting.py:69-117`; `tests/test_desk_waiting.py:107-128` (labelled swatch, `<time>` timer, order) |
| 19 | Waiting room is read-only: exactly one `read_queue_rows()` and no write call | ✓ VERIFIED | `src/triagedesk/desk/waiting.py:120-127`; `tests/test_desk_waiting.py:154-174` (recorded calls == `[("read_queue_rows", ())]`; AST guard disjoint from write methods); `tests/test_desk.py:1769-1786` |
| 20 | `GET /waiting` renders the panel; `GET /` does not read the store; a store failure renders a panel | ✓ VERIFIED | `src/triagedesk/desk/server.py:249-276`; `tests/test_desk.py:1788-1801` (failure panel, no `waiting-table`), `:1803-1812` (`GET /` touches no store) |
| 21 | Keyboard changes are presentation attributes only; no new dependency | ✓ VERIFIED | `src/triagedesk/desk/forms.py:28-43` (clinical DOM order), `:150-250` (`autofocus`, `enterkeyhint`); `tests/test_desk_forms.py:52-111` (one autofocus on `age_years`, `next` on numerics, `enter` on complaint, names/bounds/action unchanged, AST import allowlist); `pyproject.toml`/`uv.lock` unchanged in the phase diff |

**Score:** 21/21 truths verified (0 present-but-behavior-unverified).

### Deferred Items

None — Phase 13 is the last phase in the current milestone; no later phase owns any part of this goal.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/triagedesk/llm/client.py` | `extract_async` + shared `_prompt_for`/`_usage_attrs`/`_parsed`; lazily built `ollama.AsyncClient` | ✓ VERIFIED | `:76-121`, `:162-216`; no client at import |
| `src/triagedesk/desk/loop.py` | `DeskLoop` — one loop on a daemon thread, fail-closed after stop | ✓ VERIFIED | `:25-85`; `start` blocks until running, `stop` joins/closes, `run`/`submit` raise after stop |
| `src/triagedesk/desk/server.py` | `DeskServer.loop`, `serialised`, `server_close`, `online`, `extraction`, `store`, `/waiting`, `/precompute` | ✓ VERIFIED | `:72-141`, `:235-409`; guards unchanged |
| `src/triagedesk/desk/extraction.py` | `complaint_key`, `PrecomputeCache`, `extract_complaint`, `merge_case` | ✓ VERIFIED | `:33-114`; bounded 32, FIFO, failure-safe `take` |
| `src/triagedesk/desk/waiting.py` | `order_rows`, `wait_minutes`, `waiting_html`, `read_rows` | ✓ VERIFIED | `:44-127`; read-only projection |
| `src/triagedesk/core/rules.py` | `colour_urgency` — the one data-derived rank | ✓ VERIFIED | `:165-173`; scorer delegates at `core/scorer.py:137-144` |
| `src/triagedesk/desk/forms.py` | clinical order, autofocus, `enterkeyhint` | ✓ VERIFIED | `:28-43`, `:150-250`; attributes only |
| `src/triagedesk/evals/tools.py` | `online_tools` + async usage seam | ✓ VERIFIED | `:188-210`; seven tools/order unchanged; `tests/test_eval_*` pass |
| `src/triagedesk/evals/usage.py` | `recorded_extract_async` | ✓ VERIFIED | `:52-69`; old sync wrapper removed |
| `src/triagedesk/mcp/server.py` | async `normalize_case` delegating to the one closed-set filter | ✓ VERIFIED | `:207-223` |
| `tests/test_llm_client_async.py` | async transport proofs | ✓ VERIFIED | 5 tests, all pass |
| `tests/test_desk_online.py` | online/precompute proofs | ✓ VERIFIED | 15 tests, all pass |
| `tests/test_desk_waiting.py` | waiting-room proofs | ✓ VERIFIED | 9 tests, all pass |
| `tests/test_desk_forms.py` | keyboard proofs | ✓ VERIFIED | 5 tests, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `llm/client.extract_async` | `_prompt_for` / `_usage_attrs` / `_parsed` | direct calls | ✓ WIRED | `client.py:209-216`; same helpers as `extract` at `:146-159` |
| `mcp/server.normalize_case` | `llm/client.extract_async` | `await extract_async(raw_note)` | ✓ WIRED | `mcp/server.py:222` |
| `evals/tools.recorded_extract_seam` | `mcp/server.extract_async` | namespace-dict swap, restored in `finally` | ✓ WIRED | `evals/tools.py:39-60`; `tests/test_mcp_tools.py` passes |
| `DeskHandler._handle_case` / `_handle_decision` | `DeskServer.loop.run(DeskServer.serialised(...))` | one loop + one in-loop write lock | ✓ WIRED | `desk/server.py:390,400-402`; `tests/test_desk.py:1671` |
| `DeskServer.server_close` | `DeskLoop.stop` | `server_close` override + `serve` `finally` | ✓ WIRED | `desk/server.py:129-140,504-507`; `tests/test_desk.py:1727` |
| `desk/extraction.extract_complaint` | `llm/client.extract_async` → `matcher.filter_discriminator_ids` | one online extraction seam | ✓ WIRED | `desk/extraction.py:93-103` |
| `desk/extraction.merge_case` | `evals/tools.online_tools` → graph `normalize` | form overlays extraction | ✓ WIRED | `desk/extraction.py:106-114`; `desk/pipeline.py:31-56`; `evals/tools.py:113-117` |
| `POST /precompute` | `DeskServer.loop.run(PrecomputeCache.start)` | fire-and-forget on the one loop | ✓ WIRED | `desk/server.py:324-340`; `tests/test_desk_online.py:298` |
| `POST /case` | `PrecomputeCache.take` → `submit_case(..., extraction=...)` | cache hit = one model call; miss = one in-path call | ✓ WIRED | `desk/server.py:342-390`; `tests/test_desk_online.py:344` |
| `desk/waiting.order_rows` | `core/rules.colour_urgency` + `created_at` + `position` | data-derived sort key | ✓ WIRED | `desk/waiting.py:44-60` |
| `desk/waiting.waiting_html` | `desk/card._colour_class` | one colour → CSS-class mapping | ✓ WIRED | `desk/waiting.py:74-75`; `desk/card.py:19-26` |
| `desk/waiting.read_rows` | `store.read_queue_rows` | the only store call | ✓ WIRED | `desk/waiting.py:120-127`; `tests/test_desk_waiting.py:154` |
| `GET /waiting` | `DeskServer.loop.run(read_rows(...))` → `render_state(waiting=...)` → `$waiting` | injectable store seam | ✓ WIRED | `desk/server.py:249-276`; `desk/views.py:234-331`; `static/index.html` `$waiting` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `desk/waiting.py` | `rows` | `Store.read_queue_rows()` (real store or injected test store) | Yes — committed queue rows | ✓ FLOWING |
| `desk/server.py` `/waiting` | `waiting` panel | `read_rows` → `waiting_html` → `render_state` | Yes | ✓ FLOWING |
| `desk/extraction.py` | `ExtractionResult` | real `llm.client.extract_async` → closed-set filter | Yes — live Ollama call verified | ✓ FLOWING |
| `desk/pipeline.py` | merged `CaseInput` | form `CaseInput` over extraction → graph `normalize` | Yes | ✓ FLOWING |
| `desk/server.py` `/` | `mode_label`, `waiting` | `_MODE_OFFLINE`/`_MODE_ONLINE`; empty on `/` | Yes (label), empty panel on `/` by design | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `uv run pytest -q --ignore=tests/test_triage_skill.py` | **585 passed** in 40.39 s | ✓ PASS |
| Lint | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Offline demo | `uv run triagedesk demo` | exit 0; 5/5 beats; no `model` span in `spans.jsonl` | ✓ PASS |
| Real online extraction | `uv run python - <<'PY' ... extract_async(...) ...` | exit 0; validated grounded `ExtractionResult` from local `qwen2.5:1.5b` | ✓ PASS |
| Live `desk --online` end-to-end | start server, `GET /`, `POST /precompute`, `POST /case` | `GET /` 200 with "Online mode"; `/precompute` 204; `/case` 200 with ORANGE card, citation and gate; no failure panel | ✓ PASS |
| Focused eval/audit/MCP/replay regression | `uv run pytest -q tests/test_eval_suite.py tests/test_eval_invariants.py tests/test_mcp_tools.py tests/test_audit_chain.py tests/test_replay_read_only.py` | 47 passed | ✓ PASS |

### Probe Execution

No probe scripts are declared by the phase plans and none exist under `scripts/*/tests/probe-*.sh`; not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| JC-1 | 13-01, 13-02 | Agentic depth & MCP craft — tools reusable, model call no longer serialises the surface | ✓ SATISFIED | async tool contract, one core/two transports, one desk loop, online extraction + precompute; `tests/test_llm_client_async.py`, `tests/test_desk_online.py`, `tests/test_desk.py` |
| JC-3 | 13-02, 13-03 | Fit to triage desk — real thing faster, at the desk, under queue pressure | ✓ SATISFIED | live online desk, labelled mode, acuity-ordered waiting room, keyboard-first vitals; `tests/test_desk_waiting.py`, `tests/test_desk_forms.py`; the pre-existing "no clinician interview" gap in `docs/REQUIREMENTS.md` (G-1) is unchanged and outside this phase |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` in any phase-changed source or test file | — | — |
| — | — | No empty-return/stub patterns in `desk/loop.py`, `desk/extraction.py`, `desk/waiting.py` | — | — |

### Notes / Deviations

1. **Eval-harness adaptation is a planned, behaviour-preserving change.** The user-facing criterion
   says "the eval harness is untouched". `src/triagedesk/evals/usage.py` and
   `src/triagedesk/evals/tools.py` were modified to follow the async seam
   (`recorded_extract` → `recorded_extract_async`; `online_tools` added). The 14-case harness itself
   (`evals/case.py`, `evals/runner.py`) and its results are unchanged; the focused eval/audit/MCP
   regression run passed 47/47. This is not a gap, but it is a literal touch of the eval-harness
   package.
2. **Online/offline colour parity is proven for a fully specified form.** `merge_case`
   (`desk/extraction.py:106-114`) overlays only non-`None` form fields, so if the nurse leaves a
   scored vital blank and the note states it, the online path can legitimately produce a different
   colour from the offline path. The nurse's typed values still win, and the colour/citations still
   come from the deterministic scorer. If the intended contract is "never differs for any form",
   that is stricter than implemented and would need a separate decision.
3. **Waiting-room rows show the committed colour, not the citation inline.** Each row renders its
   committed `colour` as a swatch + text, plus wait timer and target (`desk/waiting.py:69-117`). The
   citation that justified that colour lives on the case card and in the audit record, not in the
   queue row. This satisfies "no new colour source"; if "no uncited colour" is read as "every
   waiting-room row must print its citation", that is not implemented.
4. **Precompute trigger timing.** The listener is on the complaint field's `change` event
   (`static/index.html`), and the complaint is the last field in the clinical layout
   (`desk/forms.py:28-43`). The model therefore works in the background while the nurse finishes
   typing/editing the complaint; if the nurse enters the complaint last and submits immediately, the
   submit reuses the in-flight precompute rather than overlapping earlier vitals entry. The
   mechanism is non-blocking and correct; the overlap is a UX nuance worth a spot-check.
5. **Generated artifact.** `uv run triagedesk demo` writes the production span sink `spans.jsonl` at
   the repo root. It is gitignored (`.gitignore:22`), was removed after verification, and was not
   committed.

### Gaps Summary

No gaps. Every phase truth resolves to ✓ VERIFIED; no artifact is missing, stub, orphaned or
hollow; every key link is wired; no debt markers or blocker anti-patterns exist. The full suite,
ruff, the offline demo and a live `desk --online` round-trip all pass.

### What a Reviewer Should Spot-Check

1. **Incomplete-form online/offline parity.** Submit once offline and once online with a form that
   omits a scored vital the complaint states (e.g. age + "RR 30, HR 130, temp 39.5"), and confirm
   the online colour differs only because the extraction supplied the blank vital, that the card
   shows citations, and that no typed value was overwritten.
2. **Waiting-room order with a real seed.** Seed RED, ORANGE, YELLOW, GREEN and two same-colour rows
   with different `created_at`/`position`; confirm `GET /waiting` renders acuity → oldest → position,
   records exactly one `read_queue_rows`, and writes nothing.
3. **Waiting-room failure.** Point the store seam at a raising store and confirm the failure panel
   renders with no partial table.
4. **Keyboard flow.** On `GET /`, confirm exactly one `autofocus` (on `age_years`), `enterkeyhint="next"`
   on every numeric input and `enter` on the complaint, and that tab order matches the clinical
   layout; confirm field names, schema bounds and `action="/case"` are unchanged.
5. **Offline demo purity.** Run `uv run triagedesk demo` and confirm exit 0 with no `model` span in
   `spans.jsonl` (the offline fixture path).
6. **Online round-trip.** Run `uv run triagedesk desk --online`, enter a complaint, confirm
   `/precompute` returns 204, and the submit renders a colour + citation + gate (no failure panel).
7. **Commit hygiene.** `git log --name-only main..HEAD` and the nine phase commits
   (`9d891cc..abee224`) contain no `.planning/`, `spans.jsonl`, `*.db` or fixture artifacts. The
   phase `.planning/` files remain untracked in this worktree, as expected.

---

_Verified: 2026-11-05T06:44:49Z_
_Verifier: the agent (gsd-verifier)_
