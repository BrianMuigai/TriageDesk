"""The README-quickstart-vs-CLI grounding proof (DOCS-04, D11-09, D11-10, T-11-09/10/11).

Keeps ``README.md`` honest against the shipped entry point, so the one-command quickstart a
stranger runs cannot drift from what the CLI actually accepts:

* every ``uv run triagedesk <cmd>`` invocation the README's fenced blocks document is accepted
  by the shipped CLI when driven through its **public ``main`` surface** (the same entry point
  the console script calls), with the side-effectful seams spied so nothing runs — no model,
  no server and no demo is ever started;
* the README documents the bare ``uv run triagedesk demo`` one-command path.

The CLI is driven through its public ``main`` surface, never by importing a private parser
helper — the test proves the documented invocation is the shipped one (D11-10). The demo seam
(``triagedesk.demo.run.run_demo``) is an async stub because the CLI hands it to ``asyncio.run``;
the desk seam (``triagedesk.desk.server.serve``) is a sync spy recording its kwargs, mirroring
``tests/test_desk_runbook.py``.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest

from triagedesk.cli import main
from triagedesk.demo import run as demo_run
from triagedesk.desk import server as desk_server

# The README and the ONE command it must match (DRY: the doc links, the CLI is the source).
README_PATH = Path("README.md")

# Fenced blocks (```...```) and a ``uv run triagedesk <cmd>`` invocation inside one. The
# captured group is the argv the console script receives (the ``uv run triagedesk `` prefix
# stripped), so the guard drives exactly the invocation the document names.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION_RE = re.compile(r"uv run triagedesk ([^\n`]+)")


def _readme_text() -> str:
    """Read the README as text."""
    return README_PATH.read_text(encoding="utf-8")


def _documented_invocations(text: str) -> list[list[str]]:
    """Every ``uv run triagedesk`` invocation in the fenced blocks, as the argv ``main`` receives.

    Any inline ``# …`` trailing comment is stripped so the argv is exactly the invocation the
    console script receives, then ``shlex.split`` recovers the argument list.
    """
    fenced = "\n".join(_FENCE_RE.findall(text))
    invocations: list[list[str]] = []
    for match in _INVOCATION_RE.findall(fenced):
        command = match.split("#", 1)[0].strip()
        if command:
            invocations.append(shlex.split(command))
    return invocations


def test_documented_invocations_are_accepted_by_the_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No documented invocation the shipped CLI rejects (the README cannot invent a flag).

    Each documented invocation is driven through the shipped ``main`` surface with the lazy
    ``run_demo`` and ``serve`` seams spied, so the README cannot document a flag the parser
    rejects and nothing (model, server, demo) is actually started (T-11-11).
    """
    invocations = _documented_invocations(_readme_text())
    assert invocations, "README.md documents no uv run triagedesk invocation"

    demo_calls: list[dict[str, Any]] = []
    desk_calls: list[dict[str, Any]] = []

    async def _run_demo_spy(*args: Any, **kwargs: Any) -> int:
        demo_calls.append(kwargs)
        return 0

    def _serve_spy(*args: Any, **kwargs: Any) -> None:
        desk_calls.append(kwargs)

    monkeypatch.setattr(demo_run, "run_demo", _run_demo_spy)
    monkeypatch.setattr(desk_server, "serve", _serve_spy)

    for argv in invocations:
        demo_before = len(demo_calls)
        desk_before = len(desk_calls)
        assert main(argv) == 0, f"the shipped CLI rejected a documented invocation: {argv}"
        reached = (
            len(demo_calls) == demo_before + 1 or len(desk_calls) == desk_before + 1
        )
        assert reached, f"the documented invocation never reached its seam: {argv}"


def test_readme_documents_the_bare_one_command_path() -> None:
    """The README documents the bare one-command path a stranger runs (D11-09)."""
    assert "uv run triagedesk demo" in _readme_text()


def test_readme_documents_the_optional_second_command() -> None:
    """The README names the optional second command (the desk surface) (D11-09)."""
    assert "uv run triagedesk desk" in _readme_text()
