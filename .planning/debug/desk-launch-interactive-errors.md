---
status: resolved
trigger: "lets gsd-debug fix the interractive error and the launch failure of the desk"
created: 2026-11-17
updated: 2026-11-17
---

# Debug Session: desk-launch-interactive-errors

## Symptoms

- **Launch:** `uv run triagedesk desk` (default `127.0.0.1:8765`) exits with
  `OSError: [Errno 98] Address already in use` and a full traceback. Stale desk processes from
  earlier UI checks are listening on 8765, 8766, 8767, and 8768.
- **Interactive:** `uv run mypy src/triagedesk/desk` reports four errors in
  `src/triagedesk/desk/interactive.py`:
  - `mobility` (str | None) is passed to `CaseInput.mobility` (Literal[...] | None);
  - `avpu` (str | None) is passed to `CaseInput.avpu` (Literal[...] | None);
  - `intake = collect_case(...)` assigns `Intake | None` to a variable inferred as `Intake`;
  - `state` is redefined in `main` (the `--note` branch and the interactive loop).
- A scripted interactive run with a complete case reaches the gate and commits without a
  runtime traceback, so the interactive failure is currently static typing, not a broken flow.

## Expected behavior

- `uv run triagedesk desk` starts on the default port, or reports a clean, actionable
  "port in use / choose --port" message with exit 1 — never a raw traceback.
- `uv run mypy src/triagedesk/desk` has no errors in `interactive.py`.
- Neither fix changes the clinical decision path.

## Actual behavior

- The desk command does not catch `OSError`, so a bind failure escapes as a traceback even
  though the surrounding comment claims a bind failure is reported cleanly.
- The four mypy errors above.

## Timeline

Detected during Phase 25 UI verification on 2026-11-16/17. The stale processes were started by
the agent's own browser checks; the missing `OSError` handling predates Phase 25.

## Reproduction

```bash
# Launch failure (with a desk already listening on 8765)
uv run triagedesk desk

# Static interactive errors
uv run mypy src/triagedesk/desk

# Runtime interactive smoke (currently exits 0)
printf '\n34\n1\n24\n94\n118\n108\n70\n38.9\n1\nn\ncoughing and fast breathing since last night\n1\nNurse Demo\ntriage nurse\nn\n' \
  | uv run triagedesk triage --db /tmp/opencode/interactive-debug.db
```

## Current Focus

hypothesis: CONFIRMED — the launch failure was a stale listener plus a missing `OSError` branch in
the `desk` CLI handler; the interactive errors were untyped `_ask_choice` returns and variable
reuse in `interactive.main`, not a runtime fault.
test: "Run the desk on an occupied port with `serve` spied/real, assert exit 1 and clean stderr;
run mypy on the desk package and assert zero errors."
expecting: "A clean CLI error with `--port` guidance, and mypy-clean interactive.py." — both met.
next_action: none — fixed, verified and committed as `06c3b0f`.
reasoning_checkpoint: "Do not change the graph, scorer, gate, or commit path; both fixes are
presentation/CLI and typing only."
tdd_checkpoint: "Failing CLI test first (confirmed red), then the fix; type-check after."

## Evidence

- 2026-11-17: `ps`/`ss` show four `triagedesk desk` processes on 8765-8768 plus a sketch
  `python3 -m http.server 8899`, all started during the agent's UI checks.
- 2026-11-17: `timeout 8 uv run triagedesk desk` exits 1 with `OSError: [Errno 98] Address
  already in use` and a traceback through `server_bind`.
- 2026-11-17: `uv run mypy src/triagedesk/desk` reports exactly four errors, all in
  `interactive.py` (lines 238, 239, 415, 419 at the time of the run).
- 2026-11-17: a complete scripted `triagedesk triage` run reaches the card, gate, and handover;
  exit 0. The interactive flow itself is not broken.
- 2026-11-17: stopped only the agent's own stale listeners — the four `triagedesk desk`
  processes whose argv names `/tmp/opencode/desk-ui-*.db` (8765-8768) and the sketch
  `python3 -m http.server 8899` — plus their `uv run` wrappers; `ss` then showed all five ports
  clear. No other process was touched.
- 2026-11-17: the new regression test (`test_desk_command_reports_an_occupied_port_cleanly`,
  a real socket holding a real loopback port) fails on the pre-fix handler with the exact
  `OSError: [Errno 98] Address already in use` traceback through `socketserver.server_bind`,
  and passes with the `OSError` branch. Red → green on the same test.
- 2026-11-17: end-to-end launch check — `uv run triagedesk desk --port 8770` stays up on a free
  port (killed by `timeout`, exit 124), and with a real listener on 8771 the same command prints
  `port 8771 on 127.0.0.1 is already in use. Stop the other process, or choose a free port
  with --port.` and exits 1, no traceback.
- 2026-11-17: the scripted interactive reproduction still reaches the gate and the handover card
  (ORANGE, position 9) after the typing change — exit 0.
- 2026-11-17: verification gates — `uv run mypy src/triagedesk/desk` → Success (0 errors);
  `uv run ruff check src tests` → All checks passed; `uv run pytest -q` → 1003 passed.
- 2026-11-17: one unrelated suite failure was a stray untracked `spans.jsonl` at the repo root
  (written by a real CLI graph run, not by the suite); removed it, and the suite is clean.

## Eliminated

- hypothesis: "The desk server code regressed and cannot bind at all." — eliminated: the server
  binds and serves on fresh ports (8768) and the executor tests pass; the failure is port
  contention plus missing OSError handling.
- hypothesis: "The interactive runtime path crashes on a complete case." — eliminated: the
  scripted run reaches the gate and commits (exit 0).

## Resolution

root_cause: >
  Two independent defects with one shared shape — a boundary that swallowed the wrong exception
  type list. (1) `cli.main`'s `desk` branch caught
  `(ValueError, RuntimeError, sqlite3.Error, ExceptionGroup)` but not `OSError`, so the
  `EADDRINUSE` raised by `socketserver.server_bind` inside `make_server` escaped `main` as a raw
  traceback even though the branch's own comment claimed a bind failure was reported cleanly.
  (2) `interactive._ask_choice` returned `str | None` wholesale, so `collect_case` passed a bare
  `str` into `CaseInput.mobility`/`avpu` (both `Literal[...]`), and `interactive.main` reused the
  names `intake` and `state` across the `--note` branch and the interactive loop — four mypy
  errors, no runtime fault.

fix: >
  `cli.main` now catches `OSError` ahead of the generic tuple: `errno.EADDRINUSE` prints
  `port <port> on <host> is already in use. Stop the other process, or choose a free port with
  --port.` and exits 1; any other `OSError` still prints its own text cleanly. No `--port`
  advice is offered for a non-port failure, so the message never misdirects. `_ask_choice` is now
  generic over the choice type (PEP 695 `def _ask_choice[ChoiceT: str](...)-> ChoiceT | None`)
  and resolves a by-name answer by returning the matching member (never the raw `str`);
  `collect_case` prompts from `_AVPU_OPTIONS`/`_MOBILITY_OPTIONS`, which are
  `get_args(AVPU)`/`get_args(Mobility)` annotated with the schema's own Literal types — the values
  still come from the ONE schema, so no clinical value is restated and no cast is needed.
  `interactive.main` uses `noted` for the `--note` intake and `outcome` for the loop's result,
  removing both redefinitions. Presentation/CLI and typing only: the scorer, matcher, retrieval,
  confidence, graph topology, approval gate, commit tool and audit chain are untouched.

verification: >
  Regression test `tests/test_desk.py::test_desk_command_reports_an_occupied_port_cleanly`
  occupies a real loopback port and drives the public `cli.main` surface; it reproduced the bug
  (pre-fix: the exact `OSError` traceback through `socketserver.server_bind`) and now asserts exit
  1, the port number, `--port` guidance, and no `Traceback` on stderr. End-to-end: the desk stays
  up on a free port (8770) and prints the actionable message with exit 1 on an occupied one
  (8771); the scripted interactive reproduction reaches the gate and handover (exit 0).
  `uv run mypy src/triagedesk/desk` → Success (0 errors), `uv run ruff check src tests` → all
  checks passed, `uv run pytest -q` → 1003 passed.

files_changed:
  - src/triagedesk/cli.py
  - src/triagedesk/desk/interactive.py
  - tests/test_desk.py

commit: 06c3b0f (fix(25-debug): report an occupied desk port cleanly and type the interactive prompts)

## Prevention

why not caught: no gate covered the `desk` launch path on an occupied port — the CLI-level tests
either spied `serve` (so nothing ever bound) or used a schema refusal, and mypy was not run over
`src/triagedesk/desk` in the phase gates, so four static errors sat in `interactive.py`.
guard: the new real-socket CLI regression test pins the occupied-port contract (message, exit
code, no traceback), and `uv run mypy src/triagedesk/desk` is now a clean baseline to keep in the
gate set.

