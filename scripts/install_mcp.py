"""Install the owned triage MCP server and its usage skill into a client harness.

The owned server (``triagedesk.mcp.server``, SDK v2, stdio) is the same process a
harness launches with ``uv run … python -m triagedesk.mcp.server``. Every harness
spells that launch differently — a JSON ``mcpServers`` entry, OpenCode's
``mcp``/``type: local`` object, VS Code's ``servers``, Zed's ``context_servers``,
or Codex's ``[mcp_servers.x]`` TOML table — so those spellings live here ONCE and
``docs/MCP.md`` links to this script instead of restating nine near-identical
blocks (CONVENTIONS §1, DRY).

The launch command is ONE function (:func:`launch`): no harness builder invents
its own command, and a change to the launch path is a one-line edit.

The usage skill (:data:`triagedesk.skills.SKILL_NAME`) is package data. ``--write``
copies it into the harness's own skills directory — native where the harness has
one, else the portable ``.agents/skills`` convention — so a harness that installs
the MCP also learns the safe call sequence. ``--no-skill`` skips it and
``--skill-path`` overrides the skills directory.

Usage:
    uv run python scripts/install_mcp.py --list
    uv run python scripts/install_mcp.py --harness opencode            # print
    uv run python scripts/install_mcp.py --harness cursor --write      # merge
    uv run python scripts/install_mcp.py --harness opencode --scope user
    uv run python scripts/install_mcp.py --harness opencode --write --no-skill

``--write`` merges a JSON harness without touching any other key and is
idempotent; a TOML harness (Codex) is only ever *appended* when its table is
absent, because rewriting a user's ``config.toml`` is not worth the risk. Every
other case prints the block and the target path for a human to paste.

The script never writes outside the harness's declared configuration path unless
``--path`` is passed explicitly (tests use that for a throwaway file). The skill
target is printed in every mode, so a user can see exactly which directory it
will touch before passing ``--write``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from triagedesk.skills import SKILL_NAME, install_skill

REPO_ROOT = Path(__file__).resolve().parents[1]

# The ONE launch command. ``--project`` makes the checkout's locked environment
# resolve even when a harness starts the server from another directory; the
# server's own ``data/`` lookup is file-relative, so it needs no cwd.
SERVER_MODULE = "triagedesk.mcp.server"
SERVER_PATH = "src/triagedesk/mcp/server.py"

# A tool call can outlive a harness's default request timeout when
# ``normalize_case`` drives the local model, so every harness that accepts a
# timeout gets this one.
TIMEOUT_MS = 120_000

# The portable Agent Skills convention. It is the fallback for a harness with no
# native skill directory, so ``--write`` still installs the skill somewhere a
# compatible harness reads (OpenCode and the ``.agents`` convention both do).
PORTABLE_SKILL_PATHS: dict[str, str] = {
    "project": "{repo}/.agents/skills",
    "user": "{home}/.agents/skills",
}

Scope = Literal["project", "user"]
Format = Literal["json", "toml"]


def launch() -> tuple[str, list[str]]:
    """Return the ONE ``(command, args)`` pair that starts the owned server."""
    return "uv", ["run", "--frozen", "--project", str(REPO_ROOT), "python", "-m", SERVER_MODULE]


def _stdio_entry() -> dict[str, Any]:
    """The portable ``command``/``args`` shape most harnesses share."""
    command, args = launch()
    return {"command": command, "args": list(args)}


def _opencode_entry() -> dict[str, Any]:
    """OpenCode's local-server object (command is one argv array, not split)."""
    command, args = launch()
    return {
        "type": "local",
        "command": [command, *args],
        "cwd": str(REPO_ROOT),
        "enabled": True,
        "timeout": TIMEOUT_MS,
    }


def _claude_code_entry() -> dict[str, Any]:
    """Claude Code's ``.mcp.json`` entry: stdio plus a per-server timeout."""
    return {"type": "stdio", **_stdio_entry(), "timeout": TIMEOUT_MS}


def _cursor_entry() -> dict[str, Any]:
    """Cursor declares the transport explicitly and supports no timeout field."""
    return {"type": "stdio", **_stdio_entry()}


def _vscode_entry() -> dict[str, Any]:
    """VS Code's native ``servers`` entry (portable ``mcpServers`` also accepted)."""
    return {"type": "stdio", **_stdio_entry()}


def _gemini_entry() -> dict[str, Any]:
    """Gemini CLI: stdio plus ``cwd`` and a millisecond ``timeout``."""
    return {**_stdio_entry(), "cwd": str(REPO_ROOT), "timeout": TIMEOUT_MS}


def _zed_entry() -> dict[str, Any]:
    """Zed's ``context_servers`` entry: flat command/args/env, no transport key."""
    return {**_stdio_entry(), "env": {}}


@dataclass(frozen=True)
class Harness:
    """One client harness: where its config lives and how it spells the server.

    ``paths`` maps each scope the harness actually supports to a path template;
    ``{home}`` is expanded per-OS by :func:`path_for`. ``entry`` builds the
    harness-native entry, and ``container`` names the JSON key it sits under
    (``None`` for TOML, which is rendered by :func:`render_toml`).
    """

    key: str
    label: str
    fmt: Format
    paths: dict[str, str]
    container: str | None
    entry: Callable[[], dict[str, Any]] | None
    note: str
    # The harness's native skills root, per scope. ``None`` falls back to the
    # portable ``.agents/skills`` convention in :func:`skills_dir_for`.
    skill_paths: dict[str, str] | None = None


HARNESSES: dict[str, Harness] = {
    h.key: h
    for h in (
        Harness(
            key="opencode",
            label="OpenCode",
            fmt="json",
            paths={
                "project": "{repo}/opencode.json",
                "user": "{home}/.config/opencode/opencode.json",
            },
            container="mcp",
            entry=_opencode_entry,
            note="Local servers need type=local, one argv array, cwd and a timeout.",
            skill_paths={
                "project": "{repo}/.opencode/skills",
                "user": "{home}/.config/opencode/skills",
            },
        ),
        Harness(
            key="claude-desktop",
            label="Claude Desktop",
            fmt="json",
            paths={
                "user": "{config}/Claude/claude_desktop_config.json",
            },
            container="mcpServers",
            entry=_stdio_entry,
            note="Restart the app after editing; the Developer tab opens this file.",
        ),
        Harness(
            key="claude-code",
            label="Claude Code",
            fmt="json",
            paths={
                "project": "{repo}/.mcp.json",
                "user": "{home}/.claude.json",
            },
            container="mcpServers",
            entry=_claude_code_entry,
            note=(
                "Or: claude mcp add --transport stdio triagedesk -- uv run --frozen "
                f"--project {REPO_ROOT} python -m {SERVER_MODULE}"
            ),
            skill_paths={
                "project": "{repo}/.claude/skills",
                "user": "{home}/.claude/skills",
            },
        ),
        Harness(
            key="cursor",
            label="Cursor",
            fmt="json",
            paths={
                "project": "{repo}/.cursor/mcp.json",
                "user": "{home}/.cursor/mcp.json",
            },
            container="mcpServers",
            entry=_cursor_entry,
            note=("Supports ${workspaceFolder} in command/args if you commit the file."),
            skill_paths={
                "project": "{repo}/.cursor/skills",
                "user": "{home}/.cursor/skills",
            },
        ),
        Harness(
            key="vscode",
            label="VS Code (Copilot)",
            fmt="json",
            paths={"project": "{repo}/.vscode/mcp.json"},
            container="servers",
            entry=_vscode_entry,
            note="The portable .mcp.json form uses mcpServers instead of servers.",
            skill_paths={"project": "{repo}/.github/skills"},
        ),
        Harness(
            key="codex",
            label="Codex CLI / ChatGPT desktop",
            fmt="toml",
            paths={
                "project": "{repo}/.codex/config.toml",
                "user": "{home}/.codex/config.toml",
            },
            container=None,
            entry=None,
            note="Trusted projects only; --write appends when the table is absent.",
            skill_paths={
                "project": "{repo}/.codex/skills",
                "user": "{home}/.codex/skills",
            },
        ),
        Harness(
            key="gemini",
            label="Gemini CLI",
            fmt="json",
            paths={
                "project": "{repo}/.gemini/settings.json",
                "user": "{home}/.gemini/settings.json",
            },
            container="mcpServers",
            entry=_gemini_entry,
            note="Untrusted folders show stdio servers as disconnected; run gemini trust.",
        ),
        Harness(
            key="zed",
            label="Zed",
            fmt="json",
            paths={"user": "{home}/.config/zed/settings.json"},
            container="context_servers",
            entry=_zed_entry,
            note="Settings → AI → MCP Servers also writes this file.",
        ),
        Harness(
            key="windsurf",
            label="Windsurf / Devin Desktop",
            fmt="json",
            paths={
                "project": "{repo}/.devin/mcp_config.json",
                "user": "{home}/.config/devin/mcp_config.json",
            },
            container="mcpServers",
            entry=_stdio_entry,
            note="Legacy Windsurf builds read ~/.codeium/windsurf/mcp_config.json.",
        ),
    )
}


def _config_dir() -> Path:
    """Return the per-OS user configuration root (``~/.config`` on Linux)."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def path_for(harness: Harness, scope: Scope) -> Path:
    """Resolve one harness's config path for ``scope``, expanding placeholders."""
    template = harness.paths[scope]
    expanded = template.format(home=Path.home(), repo=REPO_ROOT, config=_config_dir())
    return Path(expanded)


def skills_dir_for(harness: Harness, scope: Scope) -> Path:
    """Resolve the skills root the usage skill is installed under.

    A harness's native skills directory wins; a harness with none falls back to the
    portable ``.agents/skills`` convention (``PORTABLE_SKILL_PATHS``), so every
    harness gets the skill with the MCP rather than a silent gap.
    """
    templates = harness.skill_paths or PORTABLE_SKILL_PATHS
    template = templates.get(scope) or templates.get("project") or templates.get("user")
    if template is None:  # pragma: no cover - the portable map always has both scopes
        raise ValueError(f"{harness.key} declares no skills directory")
    expanded = template.format(home=Path.home(), repo=REPO_ROOT, config=_config_dir())
    return Path(expanded)


def scope_for(harness: Harness, requested: str | None) -> Scope:
    """Pick the scope: the requested one when supported, else project-then-user."""
    if requested is not None:
        if requested not in harness.paths:
            raise ValueError(f"{harness.key} has no {requested} scope")
        return cast(Scope, requested)
    return "project" if "project" in harness.paths else "user"


def render_json(harness: Harness) -> str:
    """Render the harness's snippet as the JSON document it belongs in."""
    assert harness.container is not None, "TOML harnesses render through render_toml"
    assert harness.entry is not None, "JSON harnesses declare an entry builder"
    document = {harness.container: {"triagedesk": harness.entry()}}
    return json.dumps(document, indent=2) + "\n"


def render_toml(harness: Harness) -> str:
    """Render Codex's ``[mcp_servers.triagedesk]`` table."""
    command, args = launch()
    rendered_args = ", ".join(json.dumps(arg) for arg in args)
    return (
        "[mcp_servers.triagedesk]\n"
        f"command = {json.dumps(command)}\n"
        f"args = [{rendered_args}]\n"
        f"cwd = {json.dumps(str(REPO_ROOT))}\n"
        f"tool_timeout_sec = {TIMEOUT_MS // 1000}\n"
        "startup_timeout_sec = 30\n"
    )


def render(harness: Harness) -> str:
    """Render the harness's install snippet in its native format."""
    return render_toml(harness) if harness.fmt == "toml" else render_json(harness)


def _merge_json(path: Path, harness: Harness, force: bool) -> str:
    """Merge the entry into a JSON config, preserving every other key."""
    document: dict[str, Any] = {}
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            loaded = json.loads(raw)
            if not isinstance(loaded, dict):
                raise ValueError(f"{path} is not a JSON object")
            document = loaded
    assert harness.container is not None, "TOML harnesses never reach this merge"
    assert harness.entry is not None, "JSON harnesses declare an entry builder"
    section = document.setdefault(harness.container, {})
    if not isinstance(section, dict):
        raise ValueError(f"{path}: {harness.container!r} is not an object")

    entry = harness.entry()
    existing = section.get("triagedesk")
    if existing == entry:
        return f"already installed: {path}"
    if existing is not None and not force:
        raise ValueError(
            f"{path} already defines a different 'triagedesk' entry; "
            "re-run with --force to replace it"
        )
    section["triagedesk"] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return f"wrote {path}"


def _append_toml(path: Path, harness: Harness) -> str:
    """Append the Codex table when absent; never rewrite an existing one."""
    block = render_toml(harness)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if "triagedesk" in tomllib.loads(text or "").get("mcp_servers", {}):
        return f"already installed: {path} (left unchanged)"
    # Keep exactly one blank line between the existing content and the new table.
    separator = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + separator + block, encoding="utf-8")
    return f"wrote {path}"


def _describe(harness: Harness) -> str:
    """One line for ``--list``: key, label, config paths, and the skill target."""
    scopes = ", ".join(
        f"{scope}: {path_for(harness, cast(Scope, scope))}" for scope in harness.paths
    )
    skill_scope: Scope = "project" if "project" in harness.paths else "user"
    skill = skills_dir_for(harness, skill_scope) / SKILL_NAME
    return f"{harness.key:<16} {harness.label:<30} {scopes} | skill: {skill}"


def main(argv: list[str] | None = None) -> int:
    """Entry point: list harnesses, or print/merge one harness's configuration."""
    parser = argparse.ArgumentParser(
        prog="install_mcp",
        description="Install the TriageDesk MCP server into a client harness.",
    )
    parser.add_argument("--harness", choices=sorted(HARNESSES), help="target harness")
    parser.add_argument("--list", action="store_true", help="list known harnesses")
    parser.add_argument("--write", action="store_true", help="merge into the config file")
    parser.add_argument("--scope", choices=["project", "user"], default=None)
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="override the config file (pair with --skill-path or --no-skill)",
    )
    parser.add_argument(
        "--skill-path",
        type=Path,
        default=None,
        help=f"skills directory to install {SKILL_NAME} into (default: the harness's own)",
    )
    parser.add_argument(
        "--no-skill",
        action="store_true",
        help="install only the MCP config, not the usage skill",
    )
    parser.add_argument("--force", action="store_true", help="replace a differing entry")
    args = parser.parse_args(argv)

    if args.list or args.harness is None:
        for harness in HARNESSES.values():
            print(_describe(harness))
        return 0

    harness = HARNESSES[args.harness]
    try:
        scope = scope_for(harness, args.scope)
        target = args.path or path_for(harness, scope)
        skill_dir = args.skill_path or skills_dir_for(harness, scope)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"# {harness.label}: {target}")
    print(f"# {harness.note}")
    if args.no_skill:
        print("# skill: skipped (--no-skill)")
    else:
        print(f"# skill: {skill_dir / SKILL_NAME}")
    if not args.write:
        print(render(harness))
        return 0

    try:
        if harness.fmt == "toml":
            print(_append_toml(target, harness))
        else:
            print(_merge_json(target, harness, args.force))
        if not args.no_skill:
            print(install_skill(skill_dir, force=args.force))
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
