"""The demo-path regression proof (DOCS-01, T-05-01, T-05-03).

Proves the one-command demo runs the REAL graph through the shipped seams, and that the
gated commit behaves honestly on screen:

* the full offline storyboard returns 0 (the exact path CI runs);
* each beat run in ISOLATION against a FRESH store: the named-approval escalation beat
  writes EXACTLY ONE queue row, while the refusal beat writes NONE (the demo never shows
  a write without a named nurse);
* the tracer emits the owned tool names each beat actually reaches — the escalation
  beat's FOUR (``raise_recheck_flag`` is NOT reached: E-02 carries no ``previous_case``)
  and the deterioration beat's ``raise_recheck_flag``.

The store double is the shared ``triagedesk.store.memory.InMemoryStore`` (CONVENTIONS §1:
one double, not a new one per test module).
"""

from __future__ import annotations

from pytest import CaptureFixture

from triagedesk.demo.run import load_storyboard, run_demo
from triagedesk.store.memory import InMemoryStore

# The four owned tools the escalation beat (E-02) actually reaches, in call order.
_ESCALATION_TOOLS = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
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


async def test_escalation_beat_reaches_four_owned_tools(
    capsys: CaptureFixture[str],
) -> None:
    """The tracer shows the four tools the escalation beat reaches — no recheck tool."""
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
