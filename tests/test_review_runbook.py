"""The live-review-runbook-vs-CLI grounding proof (REV-01, D12-01, D12-03, T-12-01).

Keeps ``docs/REVIEW.md`` honest against the shipped entry point, so the 10-minute Stage-2
walkthrough cannot drift from what the CLI actually accepts:

* every ``uv run triagedesk <cmd>`` invocation the runbook's fenced blocks document is
  accepted by the shipped CLI when driven through its **public ``main`` surface** (the same
  entry point the console script calls), with EVERY side-effectful seam spied so nothing
  runs — no model, no server, no demo, no eval and no durable resume;
* each documented invocation reaches exactly one of those seams (so a documented command is
  proven to dispatch, not merely to parse);
* the honesty clauses are present — the recording/upload are declared **HUMAN** actions, the
  live extension is named as a **data edit** with **no code** change, the **E-09** declared
  failure is shown, and **"reload" is stated as a fresh process**.

The CLI is driven through its public ``main`` surface, never by importing a private parser
helper. ``main`` imports each handler lazily inside itself
(``from triagedesk.evals.runner import run_eval``, ``from triagedesk.demo.run import run_demo``,
…), so monkeypatching the **module attribute** rebinds the handler on each ``main()`` call.

Spy return shapes (each MUST match what ``main``'s branch expects, or ``main(argv) == 0``
fails): ``run_demo`` -> an ``int`` (``0``); ``run_eval`` -> an ``int`` (``0``);
``resume_thread`` -> a **mapping** (``{}``), because the ``resume`` branch calls
``result.get("commit_result")`` on the return (a bare ``0``/``None`` would raise
``AttributeError``); ``replay_case`` -> a printable value (a ``str``); ``serve`` -> unused
(the sync ``desk`` branch ignores its return).
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest

import triagedesk.durable as durable
import triagedesk.replay as replay
from triagedesk.cli import main
from triagedesk.demo import run as demo_run
from triagedesk.desk import server as desk_server
from triagedesk.evals import runner as eval_runner

# The runbook and the ONE command surface it must match (DRY: the doc links, the CLI is the
# source of truth).
RUNBOOK_PATH = Path("docs/REVIEW.md")

# Fenced blocks (```...```) and a ``uv run triagedesk <cmd>`` invocation inside one. The
# captured group is the argv the console script receives (the ``uv run triagedesk `` prefix
# stripped), so the guard drives exactly the invocation the document names.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION_RE = re.compile(r"uv run triagedesk ([^\n`#]+)")


def _runbook_text() -> str:
    """Read the runbook as text."""
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def _documented_invocations(text: str) -> list[list[str]]:
    """Every ``uv run triagedesk`` invocation in the fenced blocks, as the argv ``main`` receives.

    Any inline ``# …`` trailing comment is stripped so the argv is exactly the invocation the
    console script receives, then ``shlex.split`` recovers the argument list (mirrors
    ``tests/test_readme_runbook.py``).
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
    """No documented invocation the shipped CLI rejects (the runbook cannot invent a flag).

    Each documented invocation is driven through the shipped ``main`` surface with EVERY
    side-effectful seam spied, so the runbook cannot document a flag the parser rejects and
    nothing (model, server, demo, eval, resume) is actually started. Each invocation must
    reach exactly one seam, proving it dispatches (T-12-01).
    """
    invocations = _documented_invocations(_runbook_text())
    assert invocations, "docs/REVIEW.md documents no uv run triagedesk invocation"

    demo_calls: list[dict[str, Any]] = []
    desk_calls: list[dict[str, Any]] = []
    eval_calls: list[dict[str, Any]] = []
    resume_calls: list[dict[str, Any]] = []
    replay_calls: list[dict[str, Any]] = []

    async def _run_demo_spy(*args: Any, **kwargs: Any) -> int:
        demo_calls.append(kwargs)
        return 0

    async def _run_eval_spy(*args: Any, **kwargs: Any) -> int:
        eval_calls.append(kwargs)
        return 0

    async def _resume_spy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        # A MAPPING: the ``resume`` branch calls ``result.get("commit_result")`` on it.
        resume_calls.append(kwargs)
        return {}

    async def _replay_spy(*args: Any, **kwargs: Any) -> str:
        # A printable value: the ``replay`` branch only prints it.
        replay_calls.append(kwargs)
        return ""

    def _serve_spy(*args: Any, **kwargs: Any) -> None:
        desk_calls.append(kwargs)

    monkeypatch.setattr(demo_run, "run_demo", _run_demo_spy)
    monkeypatch.setattr(eval_runner, "run_eval", _run_eval_spy)
    monkeypatch.setattr(durable, "resume_thread", _resume_spy)
    monkeypatch.setattr(replay, "replay_case", _replay_spy)
    monkeypatch.setattr(desk_server, "serve", _serve_spy)

    def _seam_total() -> int:
        return (
            len(demo_calls)
            + len(desk_calls)
            + len(eval_calls)
            + len(resume_calls)
            + len(replay_calls)
        )

    for argv in invocations:
        before = _seam_total()
        assert main(argv) == 0, f"the shipped CLI rejected a documented invocation: {argv}"
        assert _seam_total() == before + 1, (
            f"the documented invocation did not reach exactly one seam: {argv}"
        )


def test_runbook_declares_the_human_actions() -> None:
    """The recording and the public upload are declared HUMAN actions (D12-05, T-12-04)."""
    text = _runbook_text().lower()
    assert "human" in text
    assert "upload" in text


def test_runbook_names_the_data_only_extension() -> None:
    """The live extension is named as a data edit with no code change (D12-02, T-12-02)."""
    text = _runbook_text()
    assert "data/sats_discriminators.yaml" in text
    assert "no code" in text.lower()


def test_runbook_states_reload_is_a_fresh_process() -> None:
    """'Reload' is stated as a fresh process — no hot reload, no cache-clear flag (Pitfall 1)."""
    assert "fresh process" in _runbook_text()


def test_runbook_shows_the_e09_failure() -> None:
    """The runbook documents the E-09 declared failure (shown, not hidden) (T-12-03)."""
    assert "E-09" in _runbook_text()
