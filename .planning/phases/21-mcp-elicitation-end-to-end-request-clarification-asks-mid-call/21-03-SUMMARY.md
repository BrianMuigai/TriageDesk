---
phase: 21
plan: "03"
subsystem: desk
tags: [cli, desk, elicitation, ux, dry, solid]
requires:
  - "durable.RespondPolicy (21-02)"
  - "mcp.elicitation resume-value builders (21-01)"
provides:
  - "triagedesk resume --answer (repeatable) + a default decline"
  - "desk question panel + POST /clarify"
affects:
  - "Phase 23 (the plan node will make the panel reachable in a real run)"
tech-stack:
  added: []
  patterns:
    - "one surface policy built from the ONE wire module; no surface restates the resume shape"
    - "the desk's /clarify route reuses the gated plumbing and a stop policy"
key-files:
  created:
    - src/triagedesk/desk/clarification.py
  modified:
    - src/triagedesk/cli.py
    - src/triagedesk/durable.py
    - src/triagedesk/desk/pipeline.py
    - src/triagedesk/desk/views.py
    - src/triagedesk/desk/copy.py
    - src/triagedesk/desk/server.py
    - src/triagedesk/desk/static/index.html
    - src/triagedesk/desk/static/styles.css
    - tests/test_durable_cli.py
    - tests/test_desk.py
    - docs/MCP.md
    - src/triagedesk/skills/triagedesk-triage/SKILL.md
    - src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md
decisions:
  - "the CLI's whole answer logic is one _resume_policy, built with lazy imports so nothing primes a tracer before harden_offline"
  - "a decision is validated eagerly when supplied, so a blank identity is refused before the checkpoint is opened (the pre-existing contract)"
  - "the desk's question panel renders the FIRST form request only (the tool mints exactly one) and offers accept + decline, nothing else"
metrics:
  duration: "~40 min"
  completed: "2026-11-14"
  tasks: 6
  commits: 1
  files: 15
status: complete
---

# Phase 21 Plan 03: A question is not a decision — the CLI and desk surfaces Summary

Both shipped surfaces now present an elicitation as a **question**: answerable, declinable, and
structurally incapable of approving anything.

## What was built

**CLI.** `triagedesk resume` gained repeatable `--answer` and made `--decision` optional. One
`_resume_policy` is the CLI's whole answer logic: an elicitation is answered with the `--answer`
values paired to the questions in order, or **declined** when none was given; an approval goes
through the ONE `durable.approval_decision` (which still rejects a blank identity or a missing edit
colour, eagerly, before the checkpoint is opened). A missing `--decision` when an approval is pending
names the flag instead of inventing a decision. If the resume leaves the run paused (the gate appeared
after the answer), the CLI says so and exits 0 — "nothing has been committed" is stated, never
inferred. Imports stay lazy, after `harden_offline()`.

**Desk.** `desk/clarification.py` renders the question panel: the derived questions with one free-text
field each, a hidden `thread_id`/`request_key`, the CSRF field, and exactly two buttons — "Send
answer" and "Decline to answer". There is no `decision` field, no approve/edit/dismiss control, no
colour control and no hidden commit input; a module test asserts the file imports neither the queue
writer nor the commit host. `_paused_view` checks `is_elicitation(payload)` **first**, so an
elicitation can never fall through to the gate branch. `POST /clarify` sits behind the same preamble
as `/case` and `/decision` (loopback Host, same-origin, CSRF, body cap), runs under the one serialised
write lock, and resumes through `answer_clarification` → the ONE `durable.resume_thread` with a
`None`-returning policy: whatever comes next (the gate) is left paused and rendered as itself.

**Docs.** `docs/MCP.md` now tells the CLI and desk story, the four outcomes, the fail-closed rules and
the honest scope note (no shipped node calls the tool yet); the packaged skill adds the stop rule that
a refusal is never a finding and answering is never approval. Both skill copies in the checkout are
byte-identical to the packaged source.

## Deviations from Plan

### 1. [Rule 3 - Blocking] `ruff` TID251 banned the CLI's `triagedesk.mcp` import

- **Found during:** Task 1.
- **Issue:** `cli.py` is the outermost layer and legitimately reaches the seams (it already imports
  `durable`, `evals.runner`, `demo.run`, `replay`), but it was not on the per-file allowlist, so the
  elicitation wire import was rejected.
- **Fix:** added `"src/triagedesk/cli.py" = ["TID251"]` with a comment naming the layer — the same
  treatment `replay.py`, `desk/**` and `demo/**` already have.
- **Files modified:** `pyproject.toml`
- **Commit:** 9c512ac

### 2. [Rule 1 - Bug] a grouped CSS selector broke the served-CSS proxy test

- **Found during:** Task 4 verification.
- **Issue:** folding `.gate-actions` into a selector group made `_css_block(css, ".gate-actions")`
  (which matches `selector {`) fail, so the "no fixed width" proxy silently stopped covering the gate.
- **Fix:** kept the gate rule intact and declared `.clarification-actions` as its own rule with the
  same wrapping declarations.
- **Files modified:** `src/triagedesk/desk/static/styles.css`
- **Commit:** 9c512ac

### 3. [Rule 2 - Missing critical functionality] the desk's "next state" was not rendered

- **Found during:** Task 4.
- **Issue:** after answering a question the graph re-pauses at the gate; returning only the mapping
  would have dropped the clinician's gate from the page.
- **Fix:** the handler builds a `PausedRun` from the returned state and renders it through the
  ordinary paused view, so the gate (or a terminal) appears as itself.
- **Files modified:** `src/triagedesk/desk/server.py`
- **Commit:** 9c512ac

## Known Stubs

None. Note the declared scope: **no shipped graph node calls `request_clarification` yet** (Phase 23
wires the `plan` node), so the CLI/desk elicitation path is proved at the policy and surface layer,
with the tool → adapter → interrupt → answer path proved in `tests/test_elicitation_roundtrip.py`.

## Self-Check: PASSED

- `src/triagedesk/desk/clarification.py` exists; commit `9c512ac` is HEAD.
- `uv run pytest tests/test_durable_cli.py tests/test_desk.py -q` → 105 passed.
