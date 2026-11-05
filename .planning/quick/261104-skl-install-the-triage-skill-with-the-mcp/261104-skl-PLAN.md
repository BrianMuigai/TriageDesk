---
quick_id: 261104-skl
slug: install-the-triage-skill-with-the-mcp
status: planned
branch: post-submission/hardening
autonomous: true
depends_on: []
files_modified:
  - src/triagedesk/skills/__init__.py
  - src/triagedesk/skills/triagedesk-triage/SKILL.md
  - src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md
  - scripts/install_mcp.py
  - tests/test_install_mcp.py
  - tests/test_triage_skill.py
  - docs/MCP.md
  - README.md
---

# Quick task 261104-skl — install the TriageDesk usage skill with the MCP

## Goal

Ship ONE agent skill that teaches a harness how to use the TriageDesk MCP server safely, and
make `scripts/install_mcp.py --write` install it alongside the MCP config. The skill is package
data (`src/triagedesk/skills/`) so a wheel carries it; the installer copies the whole skill
directory into the harness's own skills directory.

## Why

The MCP server is usable only if the calling agent knows the safe sequence: normalize → match →
score → evidence → confidence → clinician approval → commit, and knows that a missing vital,
an out-of-scope case, a `no_match`, or a deferral must never reach the queue. Today that
knowledge lives in `docs/MCP.md` (human runbook) and the nurse stress-test skill (QA only),
not in a skill installed with the server. A harness that installs the MCP alone can call
`score_priority` directly and present a colour for a case with no age — the raw-MCP trap.

## Deliverables

1. `src/triagedesk/skills/triagedesk-triage/SKILL.md` — trigger-rich frontmatter, the canonical
   workflow, the seven-tool table, the hard safety rules, the approval-token shape, refusal
   handling, one worked example, and troubleshooting.
2. `src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md` — exact `CaseInput`
   fields and per-tool argument/return shapes, self-contained for an installed harness.
3. `src/triagedesk/skills/__init__.py` — the ONE package-resource locator (`SKILL_NAME`,
   `skill_root()`) so the installer reads the skill from an installed wheel, not a repo path.
4. `scripts/install_mcp.py` — per-harness skill directories, recursive skill copy, idempotent
   write, `--no-skill`, `--skill-path`, and a printed skill target in print/list mode.
5. Tests: the skill's declared tool surface equals the registered server tools; `CaseInput` and
   `ApprovalToken` fields are covered; the package resource exists; every skill-capable harness
   has an absolute in-home/in-repo path; `--write` installs config + skill idempotently and
   never clobbers a differing skill without `--force`; `--no-skill` and `--skill-path` behave.
6. Docs: `docs/MCP.md` §1/§3 and the README install snippet name the skill and its directories.

## DRY / SOLID notes

- The skill is the ONE agent-facing usage contract; it links to `data/*.yaml` as the SATS
  authority and does not restate TEWS bands. `docs/MCP.md` stays the human runbook.
- The installer already owns every harness spelling; skill paths join that registry instead of a
  second mapping. One recursive copy function serves every harness.
- The package locator is the only place the skill's package path is named.

## Verification

- `uv run pytest tests/test_install_mcp.py tests/test_triage_skill.py`
- `uv run ruff check src scripts tests`
- `uv run mypy src scripts`
- `uv run python scripts/install_mcp.py --list` and a print-mode run for OpenCode.
- Build a wheel and confirm the skill files are inside it (`uv build --wheel` + `unzip -l`).
