"""The durable CLI surface proof suite (Plan 06-02, AGENT-01, D6-08…D6-15).

Proves the two-command durability story's CLI wiring through the PUBLIC ``main`` surface:

* the ``demo`` parser accepts ``--durable`` and the ``resume`` parser parses its flags;
* ``resume`` on an absent thread exits non-zero, names the thread id and the checkpoint
  file, and touches NO store — it launches no borrowed ``npx mcp-sqlite`` subprocess
  (the absent-thread check runs before the graph is invoked);
* ``resume --decision approve`` without ``--approver`` exits non-zero naming the flag;
* ``demo --durable`` runs one case to the gate, prints exactly one ``thread_id=`` line and
  one ``resume`` command line, and does NOT auto-resume (no outcome block, no queue row).

The store double is the shared ``triagedesk.store.memory.InMemoryStore`` and the absent
thread is patched through the ONE borrowed-store factory seam, so the suite launches no
subprocess (CONVENTIONS §1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from triagedesk.cli import _build_parser, main
from triagedesk.demo.run import run_demo
from triagedesk.store.memory import InMemoryStore


def test_demo_parser_accepts_the_durable_flag() -> None:
    """``demo --durable`` parses to ``durable=True`` and defaults ``--db`` to None."""
    args = _build_parser().parse_args(["demo", "--durable"])
    assert args.durable is True
    assert args.db is None


def test_resume_parser_parses_its_flags() -> None:
    """``resume`` parses the thread id, decision, approver and role."""
    args = _build_parser().parse_args(
        [
            "resume",
            "--thread-id",
            "abc",
            "--decision",
            "approve",
            "--approver",
            "N",
            "--role",
            "R",
        ]
    )
    assert args.thread_id == "abc"
    assert args.decision == "approve"
    assert args.approver == "N"
    assert args.role == "R"


def test_resume_absent_thread_never_touches_a_store(
    tmp_path: Path,
    injected_store,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An absent-thread resume exits non-zero and launches no borrowed store (T-06-05)."""
    launched: list[object] = []

    def spy(*args: object, **kwargs: object) -> object:
        launched.append((args, kwargs))
        raise AssertionError("the absent-thread resume launched the borrowed store")

    monkeypatch.setattr("triagedesk.store.borrowed.open_borrowed_store", spy)

    code = main(
        [
            "resume",
            "--thread-id",
            "absent",
            "--decision",
            "approve",
            "--approver",
            "N",
            "--role",
            "R",
            "--db",
            str(tmp_path / "checkpoints.db"),
        ]
    )

    assert code != 0
    assert "no pending approval gate" in capsys.readouterr().err
    assert injected_store.calls == []
    assert launched == []


def test_resume_approve_without_approver_names_the_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An approve decision with no approver exits non-zero naming ``--approver`` (T-06-05)."""
    code = main(
        [
            "resume",
            "--thread-id",
            "x",
            "--decision",
            "approve",
            "--db",
            str(tmp_path / "checkpoints.db"),
        ]
    )

    assert code != 0
    assert "--approver" in capsys.readouterr().err


async def test_durable_demo_pauses_and_prints_one_thread_id_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``demo --durable`` pauses, prints one thread_id line, and never auto-resumes (D6-11)."""
    store = InMemoryStore()
    code = await run_demo(
        beats=["escalation"],
        durable=True,
        db_path=tmp_path / "checkpoints.db",
        store=store,
    )

    assert code == 0
    out = capsys.readouterr().out
    assert len([line for line in out.splitlines() if "thread_id=" in line]) == 1
    assert len([line for line in out.splitlines() if "uv run triagedesk resume" in line]) == 1
    assert "--- outcome ---" not in out
    assert store.rows == [], "the durable demo auto-resumed and wrote a queue row"
