---
quick_id: 261104-skl
slug: install-the-triage-skill-with-the-mcp
status: complete
completed: 2026-11-04
---

# Quick task 261104-skl — summary

## What shipped

**One packaged usage skill, installed with the MCP, and usable from a wheel.**

- `src/triagedesk/skills/triagedesk-triage/SKILL.md` — the agent-facing contract:
  trigger-rich frontmatter, seven-tool table, canonical workflow, fail-closed stop rules,
  approval-token rules, a worked example, and troubleshooting.
- `src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md` — exact `CaseInput`
  fields and every tool's arguments/returns, self-contained for a harness that does not have
  the checkout on its path.
- `src/triagedesk/skills/__init__.py` — `SKILL_NAME`, `skill_root()`, and the ONE recursive
  `install_skill()` copy. Both the installer and the CLI use it.
- `scripts/install_mcp.py` — `--write` installs the config **and** the skill; `--no-skill` and
  `--skill-path DIR` are the escape hatches; the skill target is printed in list/print mode.
  Native skill directories are declared per harness; harnesses without one fall back to the
  portable `.agents/skills` convention.
- `triagedesk skill path` / `triagedesk skill install --path DIR` — the package-level command,
  so a wheel-only install can locate and install the skill without the checkout. The heavy
  command handlers now load *after* this lightweight branch.
- `opencode.json` points the checkout's own OpenCode at `./src/triagedesk/skills`, so this
  repo's harness discovers the packaged skill without a duplicate copy.

## Documentation updated

- `docs/MCP.md` — the "what gets installed" table, installer flags, skill directories,
  verification, and troubleshooting now cover the skill.
- `README.md` — the install snippet names the skill and `--no-skill`.
- `AGENTS.md` — the MCP installer row and the Project Skills section list the packaged skill.
- `docs/CONVENTIONS.md` — the single-source table names `src/triagedesk/skills/` as the
  agent-facing skill's one home.
- `docs/DECISIONS.md` — D27 records why the skill is package data installed with the MCP.
- `ARCHITECTURE.md` was left unchanged: the one-page bound has no room for an install detail,
  and `docs/MCP.md` already owns it.

## Harness skill directories

| Harness | Native project dir | Native user dir |
| --- | --- | --- |
| OpenCode | `.opencode/skills` | `~/.config/opencode/skills` |
| Claude Code | `.claude/skills` | `~/.claude/skills` |
| Cursor | `.cursor/skills` | `~/.cursor/skills` |
| VS Code | `.github/skills` | — |
| Codex | `.codex/skills` | `~/.codex/skills` |
| Others | `.agents/skills` (portable) | `~/.agents/skills` (portable) |

## Why this shape

- The skill is **package data**, so a wheel carries it. The installer reads it through
  `importlib.resources`, not a repo-relative path, and copies the whole directory.
- The installer already owns every harness spelling; skill paths join that ONE registry.
- The skill links to `data/*.yaml` as the SATS authority and deliberately does not restate
  TEWS bands (DRY). `docs/MCP.md` remains the human runbook.
- The fail-closed stop rules are explicit because a raw MCP caller can otherwise present a
  colour for a case with no age or missing vitals — the raw-MCP trap the nurse stress test
  already documents.

## Tests

- `tests/test_triage_skill.py` keeps the skill honest against the server and the schema:
  declared tools == registered tools; every `CaseInput`/`ApprovalToken` field documented;
  documented tokens validate; fail-closed vocabulary present; SATS authority linked; the
  package and CLI can install the skill.
- `tests/test_install_mcp.py` covers the packaged resource, every harness's absolute skill
  target, config+skill `--write`, idempotency, no-clobber unless `--force`, `--no-skill`, and
  `--skill-path` for a user-only harness.

## Verification

- `uv run pytest tests/test_install_mcp.py tests/test_triage_skill.py` → **37 passed**.
- `uv run ruff check src scripts tests` → clean.
- `uv run mypy src/triagedesk/cli.py src/triagedesk/skills/__init__.py scripts/install_mcp.py`
  → clean.
- `uv build --wheel` → the wheel contains the skill and its reference.
- A throwaway venv installed from that wheel with `--no-deps` ran
  `triagedesk skill path` and `triagedesk skill install --path …` successfully.
- `uv run pytest -q` excluding the two files touched by concurrent 261104-nst work → **514
  passed**.

## Notes / follow-ups

- Concurrent uncommitted work (`261104-nst`) landed in `matcher.py`, `llm/client.py`,
  `llm/notes.py`, `mcp/server.py`, `desk/*`, and `tests/test_matcher.py` while this task ran.
  Its in-progress negation change currently makes `tests/test_no_duplicated_sats.py` and
  `tests/test_retrieval.py` fail; neither file is part of this task, and I did not edit or
  revert them.
- The installer remains a `scripts/` entry point (the documented checkout flow); the
  `triagedesk skill` command is the wheel-only path for the skill itself.
