"""Installer-vs-harness proof for ``scripts/install_mcp.py`` (DOCS-05, D-04).

Every harness block the installer can emit is checked against the harness's own
documented shape (a JSON object, or a TOML table), and against the ONE launch
command (:func:`install_mcp.launch`). So ``docs/MCP.md``'s promise — "the same
server, installed the way your harness spells it" — cannot drift from the script
that actually writes the files.

The ``--write`` paths are exercised against ``tmp_path`` only. No test touches a
real client configuration, and no test launches the server or the borrowed
SQLite subprocess.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_mcp.py"

# Every harness the installer knows, as the keys a user passes to --harness.
EXPECTED_HARNESSES = {
    "opencode",
    "claude-desktop",
    "claude-code",
    "cursor",
    "vscode",
    "codex",
    "gemini",
    "zed",
    "windsurf",
}


def _installer() -> ModuleType:
    """Load ``scripts/install_mcp.py`` by path (``scripts/`` is not a package).

    The module is registered in ``sys.modules`` before execution: ``dataclasses``
    resolves a class's defining module through that mapping, so a path-loaded
    module that skips it cannot build its frozen dataclasses.
    """
    spec = importlib.util.spec_from_file_location("_install_mcp", INSTALLER_PATH)
    assert spec is not None and spec.loader is not None, f"could not load {INSTALLER_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def install_mcp() -> ModuleType:
    """The installer module, loaded once for the module's tests."""
    return _installer()


def test_the_documented_harnesses_are_the_installed_ones(install_mcp: ModuleType) -> None:
    """The registry covers exactly the harnesses the docs promise (no silent drop)."""
    assert set(install_mcp.HARNESSES) == EXPECTED_HARNESSES


@pytest.mark.parametrize("harness_key", sorted(EXPECTED_HARNESSES))
def test_every_harness_renders_a_parsable_config(install_mcp: ModuleType, harness_key: str) -> None:
    """Each rendered block parses in its native format and launches the one module."""
    harness = install_mcp.HARNESSES[harness_key]
    rendered = install_mcp.render(harness)

    if harness.fmt == "json":
        document = json.loads(rendered)
        assert list(document) == [harness.container]
        entry = document[harness.container]["triagedesk"]
        assert "triagedesk.mcp.server" in json.dumps(entry)
    else:
        document = tomllib.loads(rendered)
        entry = document["mcp_servers"]["triagedesk"]
        assert "triagedesk.mcp.server" in json.dumps(entry)

    command, args = install_mcp.launch()
    assert command == "uv"
    assert args[-2:] == ["-m", install_mcp.SERVER_MODULE]
    assert str(install_mcp.REPO_ROOT) in args


def test_opencode_entry_is_local_with_a_cwd_and_a_timeout(install_mcp: ModuleType) -> None:
    """OpenCode's non-negotiable fields are present (local type, cwd, timeout)."""
    entry = install_mcp.HARNESSES["opencode"].entry()
    assert entry["type"] == "local"
    assert isinstance(entry["command"], list)
    assert entry["command"][0] == "uv"
    assert entry["cwd"] == str(REPO_ROOT)
    assert entry["timeout"] >= 60_000


def test_claude_code_entry_carries_a_per_server_timeout(install_mcp: ModuleType) -> None:
    """Claude Code accepts a millisecond per-server timeout; we set one."""
    entry = install_mcp.HARNESSES["claude-code"].entry()
    assert entry["type"] == "stdio"
    assert entry["timeout"] >= 60_000


def test_every_default_path_is_absolute_and_inside_home_or_repo(
    install_mcp: ModuleType,
) -> None:
    """A written path is absolute, and never outside the repo or the user's home."""
    allowed_roots = (Path.home(), REPO_ROOT)
    for harness in install_mcp.HARNESSES.values():
        for scope in harness.paths:
            path = install_mcp.path_for(harness, scope)
            assert path.is_absolute(), f"{harness.key}/{scope} is not absolute"
            assert path.is_relative_to(allowed_roots[0]) or path.is_relative_to(allowed_roots[1]), (
                f"{harness.key}/{scope} escapes home and repo: {path}"
            )


def test_list_mode_lists_every_harness(
    install_mcp: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--list`` is the discoverable entry point and names every harness."""
    assert install_mcp.main(["--list"]) == 0
    printed = capsys.readouterr().out
    for key in EXPECTED_HARNESSES:
        assert key in printed


def test_print_mode_does_not_touch_the_filesystem(
    install_mcp: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default action prints; it writes nothing even when a path is supplied."""
    target = tmp_path / "opencode.json"
    assert install_mcp.main(["--harness", "opencode", "--path", str(target)]) == 0
    assert "triagedesk.mcp.server" in capsys.readouterr().out
    assert not target.exists()


def test_write_merges_without_clobbering_and_is_idempotent(
    install_mcp: ModuleType, tmp_path: Path
) -> None:
    """An existing config keeps its keys; a second write is a no-op."""
    target = tmp_path / "opencode.json"
    target.write_text(json.dumps({"theme": "dark", "mcp": {"other": {"type": "local"}}}), "utf-8")

    assert install_mcp.main(["--harness", "opencode", "--write", "--path", str(target)]) == 0
    document = json.loads(target.read_text("utf-8"))
    assert document["theme"] == "dark"
    assert "other" in document["mcp"]
    assert document["mcp"]["triagedesk"]["type"] == "local"

    first = target.read_text("utf-8")
    assert install_mcp.main(["--harness", "opencode", "--write", "--path", str(target)]) == 0
    assert target.read_text("utf-8") == first


def test_write_refuses_a_conflicting_entry_unless_forced(
    install_mcp: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A different existing 'triagedesk' entry is never replaced silently."""
    target = tmp_path / "config.json"
    conflicting = {"mcpServers": {"triagedesk": {"command": "something-else"}}}
    target.write_text(json.dumps(conflicting), "utf-8")

    assert install_mcp.main(["--harness", "claude-code", "--write", "--path", str(target)]) == 1
    assert "already defines a different" in capsys.readouterr().err
    assert json.loads(target.read_text("utf-8")) == conflicting

    assert (
        install_mcp.main(["--harness", "claude-code", "--write", "--force", "--path", str(target)])
        == 0
    )
    assert json.loads(target.read_text("utf-8"))["mcpServers"]["triagedesk"]["type"] == "stdio"


def test_toml_write_appends_once_and_never_rewrites(
    install_mcp: ModuleType, tmp_path: Path
) -> None:
    """Codex's config.toml gains the table once; an existing table is left alone."""
    target = tmp_path / "config.toml"
    target.write_text('model = "gpt-5"\n', "utf-8")

    assert install_mcp.main(["--harness", "codex", "--write", "--path", str(target)]) == 0
    document = tomllib.loads(target.read_text("utf-8"))
    assert document["model"] == "gpt-5"
    assert document["mcp_servers"]["triagedesk"]["command"] == "uv"
    assert document["mcp_servers"]["triagedesk"]["tool_timeout_sec"] >= 60

    first = target.read_text("utf-8")
    assert install_mcp.main(["--harness", "codex", "--write", "--path", str(target)]) == 0
    assert target.read_text("utf-8") == first


def test_scope_selection_prefers_project_then_user(install_mcp: ModuleType) -> None:
    """A harness with a project path defaults to it; a user-only one falls back."""
    assert install_mcp.scope_for(install_mcp.HARNESSES["opencode"], None) == "project"
    assert install_mcp.scope_for(install_mcp.HARNESSES["claude-desktop"], None) == "user"
    assert install_mcp.scope_for(install_mcp.HARNESSES["opencode"], "user") == "user"


def test_unsupported_scope_is_rejected(
    install_mcp: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """Asking for a scope a harness does not have is an error, not a silent fallback."""
    assert install_mcp.main(["--harness", "claude-desktop", "--scope", "project"]) == 2
    assert "has no project scope" in capsys.readouterr().err
