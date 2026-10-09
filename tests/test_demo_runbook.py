"""The runbook-vs-CLI grounding proof (DEMO-01, D-07, T-05-06).

Keeps ``docs/DEMO.md`` honest against the shipped entry point, so the runbook cannot drift
from what a presenter will actually run:

* every ``--beat`` the runbook documents exists in ``uv run triagedesk demo --list``;
* every beat the CLI exposes is documented (no exposed beat the runbook omits);
* the honesty clauses are present — the recording is declared a **HUMAN** action, and the
  **E-09** declared failure is shown.

The CLI is driven through its public ``main`` surface (the same entry point the console
script calls), never by importing a private helper — the test proves the runbook matches
what a presenter runs.
"""

from __future__ import annotations

import re
from pathlib import Path

from pytest import CaptureFixture

from triagedesk.cli import main

# The runbook and the ONE command it must match (DRY: the doc links, the CLI is the source).
RUNBOOK_PATH = Path("docs/DEMO.md")
_LIST_ARGS = ["demo", "--list"]

# Fenced command blocks (```...```) and a ``--beat <name>`` invocation inside one.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_BEAT_RE = re.compile(r"--beat\s+([A-Za-z0-9_-]+)")


def _runbook_text() -> str:
    """Read the runbook as text."""
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def _documented_beats(text: str) -> set[str]:
    """Every beat named by a ``--beat`` invocation inside a fenced command block."""
    fenced = "\n".join(_FENCE_RE.findall(text))
    return set(_BEAT_RE.findall(fenced))


def _cli_beats(capsys: CaptureFixture[str]) -> set[str]:
    """The beats the shipped CLI exposes via ``triagedesk demo --list``."""
    assert main(_LIST_ARGS) == 0
    out = capsys.readouterr().out
    return {line.split("\t", 1)[0] for line in out.splitlines() if line.strip()}


def test_documented_beats_exist_in_the_cli(capsys: CaptureFixture[str]) -> None:
    """No documented beat the CLI does not expose (the runbook cannot invent a beat)."""
    assert _documented_beats(_runbook_text()) <= _cli_beats(capsys)


def test_no_cli_beat_is_omitted(capsys: CaptureFixture[str]) -> None:
    """No exposed beat the runbook omits (every CLI beat is documented)."""
    assert _cli_beats(capsys) <= _documented_beats(_runbook_text())


def test_runbook_documents_the_bare_one_command_path() -> None:
    """The runbook documents the bare one-command path a stranger runs."""
    assert "uv run triagedesk demo" in _runbook_text()


def test_runbook_declares_the_recording_a_human_action() -> None:
    """The recording is declared an unedited HUMAN screen recording (DEMO-01)."""
    text = _runbook_text().lower()
    assert "human" in text
    assert "screen recording" in text
    assert "unedited" in text


def test_runbook_shows_the_e09_failure() -> None:
    """The runbook documents the E-09 declared failure (shown, not hidden)."""
    assert "E-09" in _runbook_text()
