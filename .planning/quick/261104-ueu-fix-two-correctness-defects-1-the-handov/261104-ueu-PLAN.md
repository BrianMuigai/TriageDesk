---
quick_id: 261104-ueu
slug: fix-two-correctness-defects-1-the-handov
status: planned
branch: post-submission/hardening
autonomous: true
depends_on: []
files_modified:
  - src/triagedesk/core/approval.py
  - src/triagedesk/core/schema.py
  - src/triagedesk/core/confidence.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/graph/build.py
  - src/triagedesk/graph/state.py
  - tests/conftest.py
  - tests/test_commit_idempotent.py
  - tests/test_safety_spine.py
  - tests/test_graph_durable.py
  - tests/test_graph_tracer.py
---

# Quick task 261104-ueu — two correctness defects (handover colour, dead retry edge)

## Goal

Make two shipped behaviours truthful without widening the blast radius:

1. **The handover card shows the colour that was actually committed.** An `edit`
   (e.g. scored ORANGE → clinician RED) currently writes a RED queue row but renders an
   ORANGE card, because `handover()` re-reads the pre-approval scored priority.
2. **The `verify` failure path stops pretending it can recover.** `route_after_verify()`
   loops a failed check back to `score`, but `score` is deterministic over unchanged state,
   so the loop re-produces the identical failure until the attempt budget runs out.

Both are fixed with the smallest change that removes the falsehood, and both get a
regression test that fails today.

## Evidence (read before editing)

| Fact | Location |
| --- | --- |
| `handover()` builds the card from `priority.colour` (pre-approval) | `src/triagedesk/graph/nodes.py:392-421` (`colour=priority.colour` at ~409) |
| The gate computes the committed colour but discards it | `src/triagedesk/mcp/server.py:334-347` |
| `CommitResult` carries `committed`/`refused`/`reason`/`position` — no colour | `src/triagedesk/core/schema.py:339-357` |
| `route_after_verify()` retries to `"score"` while `attempt < _MAX_ATTEMPTS` | `src/triagedesk/graph/build.py:118-120, 181-192, 267-271` |
| `score` re-scores the *same* `case` + `matched_ids` | `src/triagedesk/graph/nodes.py:182-194` |
| Extraction is deterministic: `temperature: 0`, `seed: 42` | `src/triagedesk/llm/client.py:45-46` |
| Citations are derived 1:1 from `triggered_rules` by construction | `src/triagedesk/core/scorer.py:194-205, 256-270` |
| `route_after_score` diverts every `missing_vitals` case before `verify` | `src/triagedesk/graph/build.py:136-149` |
| `handover.colour` is also what the eval projection records as the delivered colour | `src/triagedesk/evals/invariants.py:234-235`, `src/triagedesk/evals/runner.py:66` |

## Decisions

**D1 — the committed colour becomes part of the tool contract.** `CommitResult` gains an
optional `colour`; the gate populates it from the row it just wrote; `handover()` prefers it
when `committed` is true. Rationale: the card must show what the queue holds, and the gate is
the only component that knows it. The alternative (re-reading `state["approval"]["final_colour"]`
in `handover`) would trust the untrusted resume value a second time and duplicate the
`decision == "edit"` rule — a second source of truth, rejected by CONVENTIONS §1.

**D2 — the token→colour rule moves to one helper.** `committed_colour(token, scored_colour)`
lands in a new pure `core/approval.py` (the same one-helper-per-concern shape as
`core/citations.py`). `mcp/server.py` and the graph fake in `tests/conftest.py` both call it,
so the fake cannot drift from the shipped gate (SOLID: L) and the rule is never restated.

**D3 — the `verify` retry edge is removed; a failed check is terminal.** Chosen over routing
the retry to `normalize`, because that would only look like recovery: re-extraction runs the
same model with `temperature=0, seed=42` on the same note, so it re-derives the same case, the
same `matched_ids` and the same score — a slower no-op loop, not a recovery. Fail-closed is the
honest terminal and is already a supported, tested outcome (`ABORT`, exit non-zero).

**Safety argument (D3).**
- `verify` fails only on a *structural contract violation*: `citations` are derived 1:1 from
  `triggered_rules` in `score_priority`, and a rule-less in-scope priority gains exactly one
  data-driven baseline rule. `verify` is reachable only with every scored vital present
  (`route_after_score` diverts `missing_vitals` first), so at least one citation exists.
  A failure therefore means the scorer contract was broken — no re-run of the same
  deterministic function can repair that.
- Removing the edge can only *reduce* reachability. The single path to `commit` remains
  `verify(ok) → recheck → assess → approval_gate → commit`; a failed check ends at `END`
  with no card, no gate and no write.
- No retry could ever have produced an uncited colour: `score` is the only writer of
  `priority`, it is deterministic, and it never emits a colour without its citations.

## Tasks

### Task 1 — `CommitResult` carries the committed colour (schema + one helper + gate)

**Files:** `src/triagedesk/core/approval.py` (new), `src/triagedesk/core/schema.py`,
`src/triagedesk/mcp/server.py`, `tests/test_commit_idempotent.py`

1. **New `src/triagedesk/core/approval.py`** — pure module (no I/O; imports only
   `triagedesk.core.schema`). Module docstring states it is the ONE home of the
   approval-token→committed-colour rule (CONVENTIONS §1, D-05). One function:
   `committed_colour(token: ApprovalToken, scored_colour: str) -> str` returning
   `token.final_colour` for an `edit` decision and `scored_colour` otherwise. Docstring
   names why: `final_colour` is the one place an edit records the clinician's colour
   (`ApprovalToken` docstring, `schema.py:285-336`).
2. **`src/triagedesk/core/schema.py`** — add `colour: str | None = None` to `CommitResult`
   (after `position`). Extend the class docstring: `colour` is the colour the gated write
   actually persisted (`final_colour` for an `edit`, the scored colour for an `approve`) and
   is `None` on a refusal; it exists so a reader presents the committed colour instead of
   re-deriving it. Do **not** add `extra="forbid"` here — the model is deliberately additive
   (its docstring says so) and this change must not tighten it.
3. **`src/triagedesk/mcp/server.py`** — import `committed_colour` from
   `triagedesk.core.approval`; replace the inline ternary at line 334 with a call to it;
   pass that value to `commit_to_queue` as today; return `CommitResult(..., colour=row.colour,
   position=row.position)`. Use `row.colour` (the persisted truth) rather than the local, so
   the field always reports what the queue holds — including on the idempotent
   "already committed" path. Refusal branches stay untouched (they leave `colour=None`).
   Update the tool docstring's last paragraph to name the returned field.
4. **Tests — `tests/test_commit_idempotent.py`:**
   - In `test_commit_priority_edit_commits_the_tokens_final_colour` (~line 205): parse the
     call result once and assert `parsed.committed is True` and
     `parsed.colour == "GREEN"` alongside the existing row assertion.
   - In `test_an_edit_supersedes_the_same_case_keeping_the_same_position` (~line 219):
     assert `approve_result.colour == "RED"` and `edit_result.colour == "GREEN"` — the two
     decisions report different committed colours for the same case.
   - In `tests/test_mcp_tools.py::test_commit_priority_refuses_without_a_token`: assert
     `parsed.colour is None` (a refusal never names a colour).

### Task 2 — the handover card reads the committed colour

**Files:** `src/triagedesk/graph/nodes.py`, `tests/conftest.py`,
`tests/test_safety_spine.py`, `tests/test_graph_durable.py`

1. **`src/triagedesk/graph/nodes.py::handover`** — read `commit_result = state.get("commit_result")`
   and compute the card's colour as: `commit_result.colour` when the result exists, is
   `committed`, and carries a non-empty colour; otherwise `priority.colour` (dismiss, refusal,
   or a direct render with no commit). Pass that value as `colour=`. One local + one
   conditional expression — no new helper, no new field on `HandoverCard`, no other line of the
   node changes. Extend the docstring with one sentence: the card shows the committed colour so
   an `edit` can never leave the card disagreeing with the queue row (D-05, D-11), falling back
   to the scored colour when nothing was committed.
2. **`tests/conftest.py`** — the graph fake `commit_priority` must honour the contract it
   stands in for (SOLID: L): import `committed_colour` from `triagedesk.core.approval` and
   return `CommitResult(committed=store is not None, colour=committed_colour(parsed, inp["colour"]),
   reason="accepted")`. No other fake changes.
3. **Tests — `tests/test_safety_spine.py`:** give `_render_card` an optional
   `commit_result: CommitResult | None = None` parameter that it puts on the state (the ONE
   card-rendering helper, reused — no second renderer). Add
   `test_handover_card_shows_the_committed_colour_after_an_edit`:
   - with `CommitResult(committed=True, colour="RED")` and a priority whose scored colour is
     ORANGE → `card.colour == "RED"`;
   - with `CommitResult(refused=True, reason="dismissed")` → `card.colour == priority.colour`;
   - with no `commit_result` → `card.colour == priority.colour`.
   Use the existing chest-pain case for the ORANGE priority and assert the precondition
   (`priority.colour != "RED"`) so the test cannot pass vacuously.
   `_EXPECTED_CARD_FIELDS` must stay unchanged — this task adds no card field.
4. **Test — `tests/test_graph_durable.py::test_edit_resume_supersedes_on_the_durable_path`**
   (~line 133): capture the resume results. Assert the `approve` resume's
   `result["handover"].colour == scored_colour` and the `edit` resume's
   `result["handover"].colour == EDITED_COLOUR == rows[0].colour`. This is the end-to-end
   regression: real gate, real store, real handover — card colour equals queue colour.

### Task 3 — remove the dead `verify` retry edge

**Files:** `src/triagedesk/graph/build.py`, `src/triagedesk/graph/nodes.py`,
`src/triagedesk/graph/state.py`, `src/triagedesk/core/confidence.py`,
`tests/test_graph_tracer.py`

1. **`src/triagedesk/graph/build.py`:**
   - Delete `_MAX_ATTEMPTS` and its comment (lines ~118-120) — it has no remaining reader.
   - `route_after_verify(state)` becomes: `"recheck"` when `route == "ok"`, else `END`.
     Rewrite the docstring: `ok` → second look → gate; a failed check stops at `END` because
     the check is a structural invariant the deterministic scorer upholds by construction, so
     re-running the same deterministic `score` on the same case cannot change the outcome; the
     terminal is fail-closed (no gate, no commit, no card).
   - Change the conditional-edge map at ~line 270 from
     `{"recheck": "recheck", "score": "score", END: END}` to `{"recheck": "recheck", END: END}`.
   - Update the `build_graph` docstring's edge summary only if it names the retry (it currently
     reads `(verify -> recheck)`; leave it if accurate).
2. **`src/triagedesk/graph/nodes.py`:**
   - `verify` docstring: replace "bumps `attempt` so the retry edge is bounded" with the
     truthful statement — it records the failed check in `attempt` (the honest abort record the
     eval projection reads) and the failure is terminal. Body unchanged: it still returns
     `route="retry"` (the label is the declared failed-check marker consumed by
     `evals/outcome.py`; renaming it would touch the eval harness, which is out of scope).
   - `_make_ground` docstring: delete the "Retry consequence" paragraph (it describes a loop
     that no longer exists) and replace it with one sentence — `ground` runs once per scored
     case because `verify` has no retry edge; it still writes only `evidence`.
3. **`src/triagedesk/graph/state.py`** — docstring: "`verify` sets `route` (and bumps
   `attempt` on a retry)" → "`verify` sets `route` and records a failed check in `attempt`; a
   failure is terminal".
4. **`src/triagedesk/core/confidence.py`** (~line 165) — the sentence "the retry from `score`
   recomputes the same `PriorityResult` from the same case" is now false; replace with "the
   scored `PriorityResult` already carries every fact the signal reads".
5. **Tests — `tests/test_graph_tracer.py`:**
   - Replace `test_route_after_verify_is_bounded` with
     `test_route_after_verify_fails_closed`: parametrized over `attempt` in `(0, 1, 2)`,
     `route_after_verify({"route": "retry", "attempt": attempt}) == END` for every value, and
     `route_after_verify({"route": "ok"}) == "recheck"`. Import `END` from `langgraph.graph`
     instead of the deleted private constant.
   - Add `test_graph_has_no_verify_retry_edge`: build the graph with `build_graph_tools()` and
     assert `("verify", "score")` is absent from
     `{(e.source, e.target) for e in graph.get_graph().edges}`, while `("verify", "recheck")`
     and `("verify", "__end__")` are present. (The drawn graph enumerates every conditional
     target, so this is a real topology assertion; it fails on today's code.)
   - Add `test_verify_failure_is_terminal_and_scores_exactly_once`: take
     `tools = build_graph_tools(calls=calls)`, wrap `tools["score_priority"]` so the returned
     `PriorityResult` is copied with `citations=[]` (the same corruption the eval suite uses),
     run `build_graph(tools).ainvoke({"raw_note": NOTE})`, then assert: `result.get("handover")
     is None`, `result.get("route") == "retry"`, `result.get("attempt") == 1`,
     `[n for n, _ in calls].count("score_priority") == 1`, and `"commit_priority"` is not in the
     called tool names. This is the defect-2 regression: the old code scores twice and still
     ends identically.

## Verification

```bash
# 1. A stray runtime artefact from an earlier manual run breaks one unrelated guard;
#    it is gitignored, so remove it first to restore the stated green baseline.
rm -f spans.jsonl

# 2. Full suite (baseline: 492 passed; expect >= 495 after the three new tests)
uv run pytest -q

# 3. The touched suites, for a fast loop
uv run pytest -q tests/test_graph_tracer.py tests/test_commit_idempotent.py \
  tests/test_safety_spine.py tests/test_graph_durable.py tests/test_mcp_tools.py \
  tests/test_eval_honest_terminal.py

# 4. Lint (currently clean; must stay clean)
uv run ruff check src tests
```

Expected: every test passes. `tests/test_eval_honest_terminal.py` must stay green untouched —
it asserts `routes == ["retry"] * 3` and `attempts >= 1` for a fail-closed run, which the new
terminal still produces (one failed check, no retry).

Manual confirmation of the headline defect (optional, no model needed): the durable test
`test_edit_resume_supersedes_on_the_durable_path` now asserts the card colour equals the queue
row colour on the same resume.

## Risk / rollback

| Risk | Mitigation |
| --- | --- |
| `CommitResult.colour` is a new field on a contract that also travels through the checkpointer | Additive with a `None` default; the msgpack allowlist is derived from the schema module (`build.py::_allowed_msgpack_modules`), so old and new checkpoint states both deserialize |
| A reader could mistake `colour` for the scored colour | Field docstring + it is only populated on a committed write; `handover` guards on `committed` |
| Removing the retry lowers resilience if the scorer ever regresses | A `verify` failure is a contract violation no re-run can repair; the honest terminal is already recorded as `ABORT` and exits non-zero, so a regression is loud, not silent |
| Fake/real gate divergence in tests | The `decision == "edit"` rule lives only in `core/approval.py`; `mcp/server.py` and `tests/conftest.py` both call it |
| DB / audit / allowlist side effects | None: no queue-schema change (the row already stores `colour`), no audit change, no tool added or removed, no eval-harness change |

**Rollback:** one revert of the change set. No data migration, no store or checkpoint format
change, no persisted state to unwind.

**Known residual (deliberately out of scope).** The card's `target` still comes from the scored
priority, so an edit ORANGE→RED shows the committed colour with the scored target time. Fixing
that needs a committed `target` on `CommitResult` (derived from the substrate's
`target_times[row.colour]` in the gate) — a separate, equally small change, but it widens the
gate's imports and the tool contract beyond this task's stated defect.

**Doc drift to flag, not fix here.** `ARCHITECTURE.md:26,34` and `docs/REQUIREMENTS.md` (JC-1)
still describe "retry once" / a "verify/retry loop". Task 3 makes those claims stale; the
correction is a two-line wording change and is left out because this task is scoped to code and
tests.
