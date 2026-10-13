---
phase: 06-durable-execution-idempotent-gate
reviewed: 2026-10-12T12:18:17Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - docs/DECISIONS.md
  - docs/DEMO.md
  - src/triagedesk/cli.py
  - src/triagedesk/demo/run.py
  - src/triagedesk/durable.py
  - src/triagedesk/evals/runner.py
  - src/triagedesk/evals/tools.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/store/__init__.py
  - src/triagedesk/store/borrowed.py
  - src/triagedesk/store/memory.py
  - src/triagedesk/store/queue.py
  - tests/conftest.py
  - tests/test_audit_chain.py
  - tests/test_borrowed_store.py
  - tests/test_commit_idempotent.py
  - tests/test_durable_cli.py
  - tests/test_eval_invariants.py
  - tests/test_graph_durable.py
  - tests/test_mcp_tools.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 06: Code Review Report (iteration 3)

**Reviewed:** 2026-10-12T12:18:17Z
**Depth:** standard
**Files Reviewed:** 21
**Status:** clean

## Summary

This is the iteration-3 (final) re-review of the durable-execution / idempotent-gate phase
after the iteration-2 fix loop (`f95210b`, `b70277e`). I verified both iteration-2 warnings
against the **current** source and executed the affected paths rather than trusting the fix
report. **No critical and no warning findings remain.** The three Info items below are
carried over from iterations 1–2, are outside the default `critical_warning` fix scope, and
are non-blocking.

**WR-05 — genuinely resolved (verified by execution).** `durable.approval_decision("dismiss")`
(`src/triagedesk/durable.py:198-199`) now returns `{"decision": "dismiss", "approved_at": <iso>}`
— a **well-formed** `ApprovalToken` (the `model_validator` short-circuits for `dismiss`), so
`mcp/server.py::commit_priority` reaches its own `token.decision == "dismiss"` branch instead of
classifying the token as malformed. I ran the real offline refusal beat:

```text
[tool] commit_priority {..., "approval_token": {"approved_at": "...", "decision": "dismiss"}} ->
  {"committed": false, "reason": "clinician dismissed the priority; refusing to commit", "refused": true}
  commit       : clinician dismissed the priority; refusing to commit
  GATE REFUSED : no queue row written (rows added this beat: 0)
```

That string is exactly what `docs/DEMO.md:82` and `docs/DEMO.md:165` document, and the graph
built exactly one row-less refusal. `tests/test_demo_runbook.py::test_runbook_documents_the_dismissal_refusal_the_cli_prints`
couples the live `resume --decision dismiss` stderr output to the doc, so the two cannot drift
silently again.

**WR-06 — genuinely resolved (verified by direct invocation).** `approval_decision` now strips
before validating (`durable.py:204-216`). Directly invoking the builder:

- `approve` with `approver="   "` → `DurableError: --approver is required for a 'approve' decision`
- `approve` with `role="   "` → `DurableError: --role is required for a 'approve' decision`
- `edit` with `colour="  "` → `DurableError: --colour is required for an 'edit' decision`

and `tests/test_durable_cli.py::test_resume_rejects_a_whitespace_only_identity` proves the CLI
exits non-zero naming the offending flag and writes no queue row. A blank identity can no longer
approve a queue row.

**Regression checks on the two changed mechanisms — clean:**

1. **A valid `approve`/`edit` still commits exactly one row.** `approval_decision("approve", …)`
   omits `final_colour`, and the graph's `_build_token` (`graph/nodes.py:293-294`) still fills it
   from the scored colour, so the token validates. Driving the real graph, the `routine` and
   `failure` beats each returned `{"committed": true, …, "refused": false}` and wrote one row;
   `tests/test_graph_durable.py::test_edit_resume_supersedes_on_the_durable_path` still shows an
   `edit` superseding the same keyed row in place (one row, new colour, same position).
2. **A `dismiss` still writes nothing.** Verified above (0 rows, `refused=true`), and
   `tests/test_commit_idempotent.py::test_approval_decision_dismiss_reaches_the_dismiss_branch`.
3. **No previously-refused *malformed* token is now accepted for a commit.** Sweeping the
   `ApprovalToken` contract: `approve` with missing/whitespace identity, an undeclared colour
   (`PURPLE`), or an `edit` with no colour all still raise `ValidationError`. The only tokens the
   validator newly admits are `dismiss` tokens (identity/colour irrelevant); the gate refuses
   **every** `dismiss` before touching the store, so no newly-admitted token can write. The
   `dismiss`-acceptance relaxation therefore carries no commit-path risk.
4. **No side effects on the required-unchanged surfaces.** `core/scorer.py` and
   `core/citations.py` have **no** phase-6 diff; the `@audited` interceptor body is unchanged
   (only `commit_priority`'s signature/body changed). The suite is green and hermetic:
   `uv run pytest -q` → **255 passed**, and no `*.db` file is created by the offline paths.

DRY/SOLID: the duplicated `_UNAPPROVED_RESUME` literal is gone from both `demo/run.py` and
`evals/runner.py` (both now route through `durable.approval_decision`), and the `dismiss` token
shape has one home. No SATS value or citation is inlined outside `data/*.yaml`.

## Info

### IN-06: `DEMO.md` per-beat expected-output blocks still omit lines the CLI prints

**File:** `docs/DEMO.md:110-181`
**Issue:** The doc claims "Every line below is real output from the shipped CLI (not a
hand-written mock)", but running the beats shows an extra `handover card: …` line on every
committing beat (and on the refusal beat) that the blocks omit. Pre-existing (carried from
iteration 1 IN-02); the claim is inaccurate, not the behaviour.
**Fix:** either add the `handover card: …` line to each block or soften the claim (e.g. "the
`--- outcome ---` block is real output; the card JSON is elided for width").

### IN-07: the supersede unconditionally overwrites the stored `target`

**File:** `src/triagedesk/store/queue.py:75`
**Issue:** `updated = existing.model_copy(update={"colour": colour, "target": target})` writes
the caller's `target` (always `None` on the real path, since `commit_priority` never passes one)
over any stored value. Harmless today; a future caller that sets a target on insert then edits
without one would silently clear it. Carried from iteration 1 IN-03.
**Fix:** `target=target if target is not None else existing.target`.

### IN-08: the borrowed UPSERT semantics are only string-asserted, never executed

**File:** `tests/test_borrowed_store.py:124-145`
**Issue:** The suite asserts the SQL text (`ON CONFLICT(case_id, content_hash) DO UPDATE`) but
never executes it against the real borrowed server, so a regression in the supersede SQL or its
parameter binding would not be caught (the real handshake is Phase-1 evidence only, per the
module docstring). Coverage gap, not a defect. Carried from iteration 1 IN-04.
**Fix:** add an integration test (skipped when `npx` is unavailable) that round-trips insert +
supersede through `open_borrowed_store`.

---

_Reviewed: 2026-10-12T12:18:17Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
