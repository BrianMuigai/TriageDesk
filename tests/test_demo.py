"""The demo-path regression proof (DOCS-01, T-05-01, T-05-03).

Proves the one-command demo runs the REAL graph through the shipped seams, and that the
gated commit behaves honestly on screen:

* the full offline storyboard returns 0 (the exact path CI runs);
* each beat run in ISOLATION against a FRESH store: the named-approval escalation beat
  writes EXACTLY ONE queue row, while the refusal beat writes NONE (the demo never shows
  a write without a named nurse);
* the tracer emits the owned tool names each beat actually reaches — the escalation
  beat's FIVE (``raise_recheck_flag`` is NOT reached: E-02 carries no ``previous_case``)
  and the deterioration beat's ``raise_recheck_flag``;
* every run opens with exactly ONE ``mode:`` line (the ONE ``mode_line`` text), and the
  online line names the model tag the client actually uses (``DEFAULT_MODEL``, imported);
* the CLI raises the ``httpx`` logger to WARNING, so an online run prints no
  ``HTTP Request`` INFO lines between the ``[tool]`` lines.

The store double is the shared ``triagedesk.store.memory.InMemoryStore`` (CONVENTIONS §1:
one double, not a new one per test module).
"""

from __future__ import annotations

import logging

from pytest import CaptureFixture

from triagedesk.cli import main
from triagedesk.demo.run import load_storyboard, mode_line, run_demo
from triagedesk.llm.client import DEFAULT_MODEL
from triagedesk.store.memory import InMemoryStore

# The five owned tools the escalation beat (E-02) actually reaches, in call order.
_ESCALATION_TOOLS = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "assess_confidence",
    "commit_priority",
)


async def test_full_storyboard_returns_zero() -> None:
    """The whole offline storyboard runs to completion (the CI smoke path)."""
    assert await run_demo() == 0


async def test_manifest_names_every_declared_beat() -> None:
    """The storyboard declares the five demo beats (D-07)."""
    names = [beat.name for beat in load_storyboard()]
    assert names == ["routine", "escalation", "deterioration", "refusal", "failure"]


async def test_named_approval_commits_exactly_one_row() -> None:
    """The escalation beat (named approval) writes exactly one queue row."""
    store = InMemoryStore()
    assert await run_demo(beats=["escalation"], store=store) == 0
    assert len(await store.read_queue_rows()) == 1


async def test_refusal_writes_no_queue_row() -> None:
    """The refusal beat (dismiss, no approver) writes no queue row (T-05-03)."""
    store = InMemoryStore()
    assert await run_demo(beats=["refusal"], store=store) == 0
    assert await store.read_queue_rows() == []


async def test_escalation_beat_reaches_five_owned_tools(
    capsys: CaptureFixture[str],
) -> None:
    """The tracer shows the five tools the escalation beat reaches — no recheck tool."""
    assert await run_demo(beats=["escalation"], store=InMemoryStore()) == 0
    out = capsys.readouterr().out
    for name in _ESCALATION_TOOLS:
        assert f"[tool] {name} " in out
    assert "[tool] raise_recheck_flag " not in out


async def test_deterioration_beat_reaches_raise_recheck_flag(
    capsys: CaptureFixture[str],
) -> None:
    """The deterioration beat (E-07, with previous_case) reaches raise_recheck_flag."""
    assert await run_demo(beats=["deterioration"], store=InMemoryStore()) == 0
    out = capsys.readouterr().out
    assert "[tool] raise_recheck_flag " in out


def test_cli_demo_opens_with_offline_mode_line_and_quiets_httpx(
    capsys: CaptureFixture[str],
) -> None:
    """The bare CLI demo prints the offline mode line first and leaves httpx at WARNING."""
    httpx_logger = logging.getLogger("httpx")
    saved = httpx_logger.level
    httpx_logger.setLevel(logging.NOTSET)
    try:
        assert main(["demo", "--beat", "routine"]) == 0
        first = capsys.readouterr().out.splitlines()[0]
        assert first == mode_line(offline=True)
        assert first.startswith("mode: offline")
        assert httpx_logger.level == logging.WARNING
        assert not httpx_logger.isEnabledFor(logging.INFO)
    finally:
        httpx_logger.setLevel(saved)


def test_online_mode_line_names_the_client_model_tag() -> None:
    """The online header names the tag the model client defaults to — never a re-typed one."""
    line = mode_line(offline=False)
    assert line.startswith("mode: online")
    assert DEFAULT_MODEL in line


async def test_run_prints_exactly_one_mode_line_first(
    capsys: CaptureFixture[str],
) -> None:
    """A multi-beat run prints ONE mode header, and it is the first stdout line."""
    assert await run_demo(beats=["routine", "escalation"], store=InMemoryStore()) == 0
    lines = capsys.readouterr().out.splitlines()
    modes = [line for line in lines if line.startswith("mode:")]
    assert modes == [lines[0]]
