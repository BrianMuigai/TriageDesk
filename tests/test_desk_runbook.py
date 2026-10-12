"""The desk-quickstart-vs-CLI grounding proof (UX-04, D10-14, T-10-10).

Keeps ``docs/DESK.md`` honest against the shipped entry point, so the one-screen quickstart
cannot drift from what a nurse actually runs:

* every ``triagedesk desk`` invocation the quickstart documents is accepted by the shipped CLI
  when driven through its **public ``main`` surface** (the same entry point the console script
  calls), with ``triagedesk.desk.server.serve`` spied so no server is ever started;
* the quickstart names the literal one-command path and the local URL to open;
* the fail-safe clauses are present — a timeout is no approve, a dismiss commits nothing, and
  the surface never commits on its own;
* the quickstart names no graph-internal identifier: no underscore-bearing tracer-node name and
  no thread-id token (D10-14).

The CLI is driven through its public ``main`` surface, never by importing a private parser
helper — the test proves the quickstart matches what a nurse runs.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest

from triagedesk.cli import main
from triagedesk.desk import server as desk_server
from triagedesk.graph.build import TRACER_NODES

# The quickstart and the ONE command it must match (DRY: the doc links, the CLI is the source).
RUNBOOK_PATH = Path("docs/DESK.md")

# Fenced blocks (```...```) and a ``uv run triagedesk desk ...`` invocation inside one. The
# captured group is the argv the console script receives (the ``uv run triagedesk `` prefix
# stripped), so the guard drives exactly the invocation the document names.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION_RE = re.compile(r"uv run triagedesk (desk[^\n`]*)")


def _runbook_text() -> str:
    """Read the quickstart as text."""
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def _documented_invocations(text: str) -> list[list[str]]:
    """Every ``triagedesk desk`` invocation in the fenced blocks, as the argv ``main`` receives."""
    fenced = "\n".join(_FENCE_RE.findall(text))
    return [shlex.split(match) for match in _INVOCATION_RE.findall(fenced)]


def test_documented_invocations_are_accepted_by_the_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No documented ``desk`` invocation the shipped CLI rejects (the runbook cannot invent a flag).

    The documented invocations are driven through the shipped ``main`` surface with the lazy
    ``serve`` seam spied, so the runbook cannot document a flag the parser rejects and no server
    is actually started.
    """
    invocations = _documented_invocations(_runbook_text())
    assert invocations, "docs/DESK.md documents no triagedesk desk invocation"

    calls: list[dict[str, Any]] = []

    def _spy(*args: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(desk_server, "serve", _spy)

    for argv in invocations:
        before = len(calls)
        assert main(argv) == 0, f"the shipped CLI rejected a documented invocation: {argv}"
        assert len(calls) == before + 1, f"the documented invocation never reached serve(): {argv}"


def test_runbook_documents_the_one_command_path_and_url() -> None:
    """The quickstart documents the literal one-command path and the local URL to open."""
    text = _runbook_text()
    assert "uv run triagedesk desk" in text
    assert "http://127.0.0.1:8765" in text


def test_runbook_states_the_fail_safe_clauses() -> None:
    """The fail-safe clauses are present, so the quickstart cannot drift into over-claiming."""
    text = _runbook_text().lower()
    assert "timeout" in text and "no approve" in text
    assert "dismiss" in text and "commits nothing" in text
    assert "never commits on its own" in text


def test_runbook_names_no_graph_internal_identifier() -> None:
    """The quickstart names no graph-internal identifier (D10-14).

    The check set is derived from ``TRACER_NODES`` — imported, never restated — and filtered to
    the underscore-bearing names no runbook should ever name. The set is asserted non-empty so
    the absence check cannot pass vacuously.
    """
    text = _runbook_text()
    internal = [name for name in TRACER_NODES if "_" in name]
    assert internal, "the tracer-node set exposed no underscore-bearing identifier to check"
    for name in internal:
        assert name not in text, f"docs/DESK.md names the internal identifier {name!r}"
    for token in ("thread_id", "thread-id"):
        assert token not in text, f"docs/DESK.md names the thread-id token {token!r}"
