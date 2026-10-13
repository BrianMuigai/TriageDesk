---
phase: 06-durable-execution-idempotent-gate
fixed_at: 2026-10-12T12:08:10Z
review_path: .planning/phases/06-durable-execution-idempotent-gate/06-REVIEW.md
iteration: 2
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report (iteration 2)

**Fixed at:** 2026-10-12T12:08:10Z
**Source review:** `.planning/phases/06-durable-execution-idempotent-gate/06-REVIEW.md`
**Iteration:** 2

**Summary:**

- Findings in scope: 2 (WR-05, WR-06 — both warnings; 0 critical)
- Fixed: 2
- Skipped: 0

**Verification location:** the project sets `workflow.use_worktrees=false`, so no git
worktree was created (#2825); every edit, test run, and commit was made in the **main
checkout**. The numbers below are reproducible from the tree as it stands.

## Fixed Issues

### WR-05: `DEMO.md` documented a dismissal reason the CLI never emitted (WR-03 regression)

**Files modified:** `src/triagedesk/core/schema.py`, `src/triagedesk/durable.py`,
`src/triagedesk/demo/run.py`, `src/triagedesk/evals/runner.py`, `docs/DEMO.md`,
`tests/conftest.py`, `tests/test_demo_runbook.py`, `tests/test_commit_idempotent.py`
**Commit:** `f95210b`
**Status:** `fixed: requires human verification`

**Applied fix (root cause, not the doc string):** `approval_decision("dismiss")` now emits
`{"decision": "dismiss", "approved_at": <iso>}` — a **well-formed** `ApprovalToken` — instead
of the partial `{"decision": "dismiss"}` that `ApprovalToken.model_validate` rejected before
`commit_priority`'s `decision == "dismiss"` branch could run. `ApprovalToken`'s identity/colour
requirements moved from field-level `min_length=1` to a single
`model_validator(mode="after")` (`_identity_and_colour_required`) that enforces a named
clinician and a declared `final_colour` for `approve`/`edit` only; a `dismiss` short-circuits
(no approver, no colour — the gate refuses it and writes nothing). The gate's dismissal branch
is now reachable from every in-tree caller, so the CLI genuinely prints
`clinician dismissed the priority; refusing to commit`.

Concurrently (cheap DRY root of WR-05 / IN-05): `demo/run.py` and `evals/runner.py` dropped
their private `_UNAPPROVED_RESUME = {"decision": "dismiss"}` literals and both route their
dismiss resume value through the ONE builder, `durable.approval_decision("dismiss")`, so the
token shape and the reason string cannot drift again. The eval runner keeps the lazy import
(no `evals` ↔ `durable` cycle). `tests/conftest.py`'s graph fake now mirrors the real gate's
refusal **order** (a well-formed `dismiss` is refused before any store access), so the eval's
unapproved resume is still observably refused.

Docs and guard: `docs/DEMO.md`'s refusal-beat block now records the string the CLI prints
(`clinician dismissed the priority; refusing to commit`, previously
`approval token is malformed; refusing to commit`); the durable-dismissal section already
matched and is now truthful. New tests:
`tests/test_demo_runbook.py::test_runbook_documents_the_dismissal_refusal_the_cli_prints`
(drives the real `resume --decision dismiss` path over a paused E-02 thread and asserts the
gate's reason lands on stderr **and** appears verbatim in `docs/DEMO.md` — coupling CLI output
to the doc so this drift cannot recur silently) and
`tests/test_commit_idempotent.py::test_approval_decision_dismiss_reaches_the_dismiss_branch`
(the builder's token reaches the dismiss branch, not the malformed branch, and writes nothing).

**Flagged for human verification:** this fix changes the gate's token-validation semantics
(identity/colour are no longer required for a `dismiss`), so the logic change should be
confirmed by a human, even though the new tests exercise it end-to-end.

### WR-06: the approval gate accepted a whitespace-only approver/role (blank identity commits a row)

**Files modified:** `src/triagedesk/durable.py`, `tests/test_durable_cli.py`
**Commit:** `b70277e`
**Applied fix:** `approval_decision` now validates the identity with
`if not (approver or "").strip():` / `if not (role or "").strip():` (and `--colour` likewise for
an `edit`), so a whitespace-only value counts as absent and raises `DurableError` naming the
offending flag — which the CLI surfaces on stderr with a non-zero exit. This closes the gap where
`if not approver:` was `False` for `"   "` and `ApprovalToken`'s `min_length=1` counted spaces, so
a fabricated blank identity could approve a real queue row (T-06-05). The schema-side
`_identity_and_colour_required` validator also strips, giving defence in depth. New test:
`tests/test_durable_cli.py::test_resume_rejects_a_whitespace_only_identity` (parametrized over a
whitespace `--approver` and a whitespace `--role`) asserts a non-zero exit, the named-flag
error, and that no queue row is written.

## Skipped Issues

None — both in-scope findings were fixed.

## Verification

- `uv run pytest -q` → **255 passed** (251 before this pass + 4 new regression cases: 1 runbook
  printed-string test, 2 parametrized whitespace-identity cases, 1 dismiss-branch test).
- Reproduced the dismissal path directly: `uv run triagedesk demo --beat refusal` prints
  `commit : clinician dismissed the priority; refusing to commit` — the exact string now in
  `docs/DEMO.md`.
- `uv run ruff check` on every changed file → **All checks passed**.
- `uv run mypy` on the changed source files → only **pre-existing** errors, unchanged by these
  fixes: `Library stubs not installed for "yaml"` (`demo/run.py:25`) and
  `Returning Any ...` (`durable.py:175`, an untouched line in `resume_paused`).
- No `*.db` artifact is created by the offline suite (hermetic; no npx / no network).
- Untouched by design: `core/scorer.py`, `core/citations.py`, the `@audited` interceptor body,
  and the graph topology.

---

_Fixed: 2026-10-12T12:08:10Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 2_
