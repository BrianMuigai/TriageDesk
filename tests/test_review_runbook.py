"""The live-review-runbook-vs-CLI grounding proof (REV-01, D12-01, D12-03, T-12-01).

Keeps ``docs/REVIEW.md`` honest against the shipped entry point, so the 10-minute Stage-2
walkthrough cannot drift from what the CLI actually accepts:

* every ``uv run triagedesk <cmd>`` invocation the runbook's fenced blocks document is
  accepted by the shipped CLI when driven through its **public ``main`` surface** (the same
  entry point the console script calls), with EVERY side-effectful seam spied so nothing
  runs — no model, no server, no demo, no eval and no durable resume;
* each documented invocation reaches exactly one of those seams (so a documented command is
  proven to dispatch, not merely to parse);
* the documented durable dismissal (Beat 3) is a pause-then-resume pair on ONE checkpoint
  file, and the pair is driven **end-to-end** over a ``tmp_path`` file (a real pause, then a
  real dismissal resume) — so a documented SEQUENCE that parses but cannot run (a lone
  ``resume`` with nothing paused, which raises ``DurableError`` and exits non-zero) is caught,
  not merely a documented invocation the parser rejects (CR-01);
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
from triagedesk.mcp import server as server_module

# The runbook and the ONE command surface it must match (DRY: the doc links, the CLI is the
# source of truth).
RUNBOOK_PATH = Path("docs/REVIEW.md")

# Fenced blocks (```...```) and a ``uv run triagedesk <cmd>`` invocation inside one. The
# captured group is the argv the console script receives (the ``uv run triagedesk `` prefix
# stripped), so the guard drives exactly the invocation the document names.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION_RE = re.compile(r"uv run triagedesk ([^\n`#]+)")

# The exact dismissal refusal the gate emits (``mcp/server.py::commit_priority``) — the same
# literal ``docs/DEMO.md`` is guarded against, so both runbooks name the string a presenter
# actually sees rather than a hand-written mock (CR-01).
DISMISSAL_REFUSAL = "clinician dismissed the priority; refusing to commit"

# The content-derived ``thread_id`` a durable pause prints, which the runbook's ``resume``
# line shows as the ``<content-id>`` placeholder the presenter pastes back.
_THREAD_ID_RE = re.compile(r"\[durable\] thread_id=(\S+) paused")


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


def _flag_value(argv: list[str], flag: str) -> str | None:
    """The value following *flag* in *argv*, or ``None`` when the flag is absent."""
    for index, token in enumerate(argv):
        if token == flag:
            return argv[index + 1] if index + 1 < len(argv) else None
    return None


def _replace_flag(argv: list[str], flag: str, value: str) -> list[str]:
    """A copy of *argv* with the value following *flag* replaced by *value*."""
    out = list(argv)
    for index, token in enumerate(out):
        if token == flag and index + 1 < len(out):
            out[index + 1] = value
            return out
    raise AssertionError(f"{flag} is absent from the documented invocation: {argv}")


def _documented_durable_dismissal(text: str) -> tuple[list[str], list[str]]:
    """The documented Beat-3 pair: a durable PAUSE and a dismissal RESUME on ONE checkpoint file.

    A dismissal resumes a *paused* thread, so the runbook MUST document the pause before the
    resume — the CR-01 regression is a lone ``resume`` whose thread was never paused (which
    raises ``DurableError`` and exits non-zero). The pair is matched on a SHARED ``--db`` value,
    so the resume provably targets the file the pause wrote.
    """
    invocations = _documented_invocations(text)
    pauses = [argv for argv in invocations if "--durable" in argv]
    dismissals = [
        argv for argv in invocations if _flag_value(argv, "--decision") == "dismiss"
    ]
    for pause in pauses:
        db = _flag_value(pause, "--db")
        if db is None:
            continue
        for resume in dismissals:
            if _flag_value(resume, "--db") == db:
                return pause, resume
    raise AssertionError(
        "docs/REVIEW.md does not document the durable dismissal as a pause-then-resume pair "
        "on ONE checkpoint file (CR-01)"
    )


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


def test_documented_durable_dismissal_runs_end_to_end(
    tmp_path: Path, injected_store: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """The documented Beat-3 pause→resume sequence is RUNNABLE, not merely accepted (CR-01).

    The acceptance guard above proves each documented invocation PARSES and dispatches; it does
    NOT prove a documented multi-command SEQUENCE runs. Beat 3 is two commands — a durable pause
    into a checkpoint file, then a dismissal resume of the SAME thread/db — so this test extracts
    that pair, drives the real pause and then the real resume over a ``tmp_path`` checkpoint file
    through the shipped ``main`` surface, and asserts the dismissal exits 0 with the gate's own
    refusal. A re-drift to a lone ``resume`` (nothing paused) raises ``DurableError`` and exits
    non-zero, which this test catches — the runnability gap CR-01 named.
    """
    pause, resume = _documented_durable_dismissal(_runbook_text())

    # The runbook uses a throwaway /tmp path; redirect BOTH commands to one hermetic tmp file
    # (the only substitution) so the suite leaves nothing behind.
    db_path = tmp_path / "checkpoints.db"
    pause = _replace_flag(pause, "--db", str(db_path))

    assert main(pause) == 0, "the documented durable pause did not run"
    match = _THREAD_ID_RE.search(capsys.readouterr().out)
    assert match is not None, "the durable pause printed no thread_id to resume"
    thread_id = match.group(1)

    # ``demo --durable`` restores the store seam in its ``finally``; a real terminal re-resolves
    # the borrowed store on the resume. Re-inject the in-memory double so the suite stays hermetic
    # (no ``npx mcp-sqlite`` subprocess) while the dismissal still reaches the gate.
    server_module.set_store(injected_store)

    resume = _replace_flag(resume, "--db", str(db_path))
    resume = _replace_flag(resume, "--thread-id", thread_id)
    code = main(resume)
    err = capsys.readouterr().err

    assert code == 0, "the documented dismissal did not exit 0"
    assert DISMISSAL_REFUSAL in err, f"the CLI did not print the dismissal reason: {err!r}"


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
