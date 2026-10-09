"""Executable purity guard for ``core/`` (D-13, QUAL-01/QUAL-02).

``core/`` is a **pure** boundary: it may not import ``llm``, ``mcp`` or ``store``
in any form — absolute (``import triagedesk.llm`` / ``from triagedesk.llm import
...``) or relative (``from ..llm import ...`` / ``from .. import mcp``). It also may
not import the **MCP client's** external package roots (``fastmcp`` / ``langchain``),
which are named explicitly so a stray client import is caught even outside the
``triagedesk`` namespace (QUAL-02). This is a **one-way, published contract** (D-13):
later phases depend on it, and silently letting the score path depend on the model /
MCP client / storage would break the design.

The AST test below is authoritative; a ruff ``flake8-tidy-imports`` banned-api
rule (``pyproject.toml``, scoped to ``core/``) is the belt-and-braces secondary
guard at lint time.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
CORE_DIR = SRC_ROOT / "triagedesk" / "core"
PACKAGE = "triagedesk"
# Sibling packages under the ``triagedesk`` namespace that ``core/`` must never reach.
_FORBIDDEN_SIBLINGS = ("llm", "mcp", "store")
# The MCP client's external package roots, named explicitly (QUAL-02): the client
# engine (``fastmcp``) and the adapter host (``langchain``). The ``mcp`` SDK root is
# already covered as a sibling, and ``_is_forbidden`` treats a bare root uniformly.
_FORBIDDEN_MCP_CLIENT = ("fastmcp", "langchain")
FORBIDDEN = _FORBIDDEN_SIBLINGS + _FORBIDDEN_MCP_CLIENT


def _module_parts(path: Path) -> list[str]:
    """Return the dotted-module parts for a file under ``src/``."""
    rel = path.resolve().relative_to(SRC_ROOT)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return parts


def _is_forbidden(parts: list[str]) -> bool:
    """True if *parts* names a forbidden sibling of the ``triagedesk`` package."""
    if parts and parts[0] == PACKAGE:
        parts = parts[1:]
    return bool(parts) and parts[0] in FORBIDDEN


def _forbidden_in_source(source: str, module_parts: list[str]) -> list[str]:
    """Return the forbidden imports found in *source* (empty list when pure).

    *module_parts* is the dotted module of the file being parsed, used to resolve
    relative imports (``from ..llm import x``) back to an absolute form.
    """
    tree = ast.parse(source)
    package = module_parts[:-1]
    hits: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden(alias.name.split(".")):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base: list[str] = []
            else:
                keep = len(package) - (node.level - 1)
                base = package[:keep]
            if node.module:
                target = base + node.module.split(".")
                if _is_forbidden(target):
                    hits.append("." * node.level + node.module)
            for alias in node.names:
                target = base + [alias.name]
                if _is_forbidden(target):
                    hits.append("." * node.level + alias.name)
    return sorted(set(hits))


def _forbidden_in_file(path: Path) -> list[str]:
    return _forbidden_in_source(path.read_text(encoding="utf-8"), _module_parts(path))


@pytest.mark.parametrize(
    "path", sorted(CORE_DIR.rglob("*.py")), ids=lambda p: p.relative_to(REPO_ROOT).as_posix()
)
def test_core_imports_nothing_from_llm_mcp_or_store(path: Path) -> None:
    offenders = _forbidden_in_file(path)
    assert not offenders, (
        f"{path.relative_to(REPO_ROOT)} imports forbidden package(s) {offenders}; "
        f"core/ must not depend on {FORBIDDEN} (D-13, one-way contract)"
    )


def test_guard_detects_absolute_and_relative_forbidden_imports() -> None:
    """The guard is not vacuous: it flags every forbidden import form."""
    source = (
        "import triagedesk.llm\n"
        "from triagedesk.mcp import adapter\n"
        "from .. import store\n"
        "from ..llm import client\n"
        "from . import schema\n"  # allowed: a core-internal submodule
    )
    hits = _forbidden_in_source(source, ["triagedesk", "core", "sample"])
    assert "triagedesk.llm" in hits
    assert "triagedesk.mcp" in hits
    assert "..store" in hits
    assert "..llm" in hits
    assert not any("schema" in hit for hit in hits)


def test_forbidden_set_names_the_mcp_client_explicitly() -> None:
    """The forbidden set names the MCP client's roots, not only the sibling (QUAL-02)."""
    assert "mcp" in FORBIDDEN
    for root in _FORBIDDEN_MCP_CLIENT:
        assert root in FORBIDDEN


def test_guard_detects_the_external_mcp_client() -> None:
    """The guard is not vacuous for the external MCP client imports (QUAL-02)."""
    source = "import fastmcp\nfrom langchain.mcp import MCPAdapter\nimport mcp\n"
    hits = _forbidden_in_source(source, ["triagedesk", "core", "sample"])
    assert "fastmcp" in hits
    assert "langchain.mcp" in hits
    assert "mcp" in hits
