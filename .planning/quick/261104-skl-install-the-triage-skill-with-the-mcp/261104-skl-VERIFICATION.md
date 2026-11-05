# Verification — quick task 261104-skl

## Commands run

```bash
uv run pytest tests/test_install_mcp.py tests/test_triage_skill.py -q
# 37 passed

uv run ruff check src scripts tests
# All checks passed!

uv run mypy src/triagedesk/cli.py src/triagedesk/skills/__init__.py scripts/install_mcp.py
# Success: no issues found in 3 source files

uv build --wheel --out-dir /tmp/opencode/triagedesk-dist
# Successfully built triagedesk-0.1.0-py3-none-any.whl
# wheel contains:
#   triagedesk/skills/__init__.py
#   triagedesk/skills/triagedesk-triage/SKILL.md
#   triagedesk/skills/triagedesk-triage/references/tool-contracts.md

# wheel-only, no-deps smoke:
uv venv --python 3.12 /tmp/opencode/skill-venv2
uv pip install --python /tmp/opencode/skill-venv2/bin/python --no-deps \
  /tmp/opencode/triagedesk-dist/triagedesk-0.1.0-py3-none-any.whl
/tmp/opencode/skill-venv2/bin/triagedesk skill path
# /tmp/opencode/skill-venv2/lib/python3.12/site-packages/triagedesk/skills/triagedesk-triage
/tmp/opencode/skill-venv2/bin/triagedesk skill install --path /tmp/opencode/skill-out2
# wrote /tmp/opencode/skill-out2/triagedesk-triage
```

## Behaviour checks

- `uv run python scripts/install_mcp.py --list` prints every harness plus a resolved skill
  target.
- `--harness opencode` (print mode) prints the config and the skill target without writing.
- `--write --path <tmp> --skill-path <tmp>` writes the config and `<tmp>/triagedesk-triage/`
  including `references/tool-contracts.md`; a second run is a no-op.
- A locally edited skill is not overwritten without `--force`.
- `--no-skill` writes only the config.
- `--skill-path` works for a user-only harness (Zed).
- The harness discovered the new skill in-session after `opencode.json` added
  `"skills": ["./src/triagedesk/skills"]`.

## Concurrent-work note

A separate uncommitted task (`261104-nst`) modified `core/matcher.py`, `llm/client.py`,
`llm/notes.py`, `mcp/server.py`, `desk/*`, and their tests while this task ran. The full
suite currently shows two failures from that in-progress work:

- `tests/test_no_duplicated_sats.py` — new `'no'` literal in `matcher.py`;
- `tests/test_retrieval.py` — the matcher now applies negation but retrieval does not yet.

Neither file is part of this task, and neither was edited or reverted here. Excluding those
two files, `uv run pytest -q` passed **514 tests**.
