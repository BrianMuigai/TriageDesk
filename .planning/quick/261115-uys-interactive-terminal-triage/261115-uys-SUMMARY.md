---
quick_id: 261115-uys
slug: interactive-terminal-triage
status: complete
date: 2026-11-15
files_modified:
  - src/triagedesk/desk/interactive.py
  - src/triagedesk/cli.py
  - src/triagedesk/desk/extraction.py
  - src/triagedesk/llm/client.py
  - src/triagedesk/mcp/server.py
  - tests/test_interactive.py
  - tests/test_readme_runbook.py
  - README.md
  - docs/DESK.md
---

# Summary — interactive terminal triage

## What shipped

`uv run triagedesk triage [--online] [--note TEXT|-]`.

- **Raw note first.** Paste the nurse's note; the ONE grounded composition reads it into the typed
  case, prints the extracted fields and the ones the note did *not* state, and asks for
  confirmation. Declining falls back to field-by-field entry.
- **Field entry.** Blank skips a vital (never imputed); the complaint is required; an impossible
  value is re-prompted before the scorer sees it.
- **The graph, unchanged.** `desk.pipeline.submit_case` → the durable gate; an elicitation pause is
  answered in the terminal and the gate still pauses afterwards; `decide` commits only on a named
  approval.
- **Honest terminals.** An escalation / recovery / clarification prints what happened, not an empty
  card.
- **`--note`** is the non-interactive path (`-` reads stdin); it requires `--online` and says so.

## DRY / SOLID

- One note→case composition: `llm.client.extract_grounded(note, *, extract=...)`, used by both the
  owned `normalize_case` tool and the terminal intake. The model call is injectable, so the server
  keeps its existing patchable `extract_async` seam.
- The surface is presentation only: no scoring, no gate logic, no queue write, no second elicitation
  vocabulary. The desk-package guard (`test_no_self_commit_path_in_the_desk_package`) still passes —
  the terminal module imports no commit path.
- `mcp/server.py` lost a now-redundant grounding call; `core/scorer.py`, `core/citations.py` and the
  `@audited` interceptor are untouched.

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest -q` | **967 passed** |
| `uv run ruff check src tests` | clean |
| Real `--online --note` run | extracted a pasted note, scored ORANGE with three citations, committed one queue row on approval |
| Desk commit-path guard | passes (no `triagedesk.mcp.server` import in the desk package) |

## Honest notes

- The eval harness still has no MCP client, so an `ask_question` there records `unavailable`; the
  terminal is the surface that actually answers it.
- Raw notes need the local model. Offline they are refused with a named reason rather than silently
  parsed by a second extractor.
- Three untracked `.planning/quick/` directories from earlier subagent runs (`261114-io6`,
  `261115-jlr`, `261115-lgd`) were left untouched — they are not this task's record.
