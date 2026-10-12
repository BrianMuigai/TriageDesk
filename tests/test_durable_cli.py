"""The durable CLI surface proof suite (Plan 06-02, AGENT-01, D6-08…D6-15).

Proves the two-command durability story's CLI wiring through the PUBLIC ``main`` surface:

* the ``demo`` parser accepts ``--durable`` and the ``resume`` parser parses its flags;
* ``resume`` on an absent thread exits non-zero, names the thread id and the checkpoint
  file, and touches NO store — it launches no borrowed ``npx mcp-sqlite`` subprocess
  (the absent-thread check runs before the graph is invoked);
* ``resume --decision approve`` without ``--approver`` exits non-zero naming the flag;
* ``demo --durable`` runs one case to the gate, prints exactly one ``thread_id=`` line and
  one ``resume`` command line, and does NOT auto-resume (no outcome block, no queue row);
* ``demo --durable`` without ``store=`` resolves the INJECTED store seam, so it uses an
  injected double rather than launching the borrowed ``npx mcp-sqlite`` subprocess (WR-01).

The store double is the shared ``triagedesk.store.memory.InMemoryStore`` and the absent
thread is patched through the ONE borrowed-store factory seam, so the suite launches no
subprocess (CONVENTIONS §1).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from triagedesk.cli import _build_parser, main
from triagedesk.demo.run import run_demo
from triagedesk.durable import run_to_gate
from triagedesk.evals.case import load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.store.memory import InMemoryStore

# The bundled synthetic fixtures, resolved from the repo root (the same cases the demo runs).
CASES_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"


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


@pytest.mark.parametrize(
    ("approver", "role", "named"),
    [
        ("   ", "triage nurse", "--approver"),
        ("Nurse Demo", "   ", "--role"),
    ],
)
def test_resume_rejects_a_whitespace_only_identity(
    tmp_path: Path,
    injected_store,
    capsys: pytest.CaptureFixture[str],
    approver: str,
    role: str,
    named: str,
) -> None:
    """A whitespace-only ``--approver``/``--role`` is rejected before any commit (WR-06).

    ``if not approver`` treats ``"   "`` as present, and ``ApprovalToken``'s field check
    counted spaces, so a fabricated blank identity could approve a real queue row. The ONE
    decision builder now strips before validating, so a blank identity exits non-zero naming
    the offending flag and writes nothing.
    """
    code = main(
        [
            "resume",
            "--thread-id",
            "x",
            "--decision",
            "approve",
            "--approver",
            approver,
            "--role",
            role,
            "--db",
            str(tmp_path / "checkpoints.db"),
        ]
    )

    assert code != 0
    assert named in capsys.readouterr().err
    assert injected_store.rows == [], "a blank identity committed a queue row"


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


async def test_durable_demo_resolves_the_injected_store_seam(
    tmp_path: Path,
    injected_store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``demo --durable`` (no ``store=``) uses the INJECTED seam, not the borrowed default (WR-01).

    The durable path must resolve its store through the ONE seam
    (``mcp.server._resolve_store``); running with no explicit ``store=`` must still honour a
    store injected via ``set_store`` so the suite never launches ``npx mcp-sqlite``. Before the
    fix this test fails: ``_run_durable`` called the borrowed factory directly, launching the
    subprocess and leaving the injected store untouched.
    """
    launched: list[object] = []

    def spy(*args: object, **kwargs: object) -> object:
        launched.append((args, kwargs))
        raise AssertionError("the durable demo launched the borrowed store")

    monkeypatch.setattr("triagedesk.store.borrowed.open_borrowed_store", spy)

    code = await run_demo(
        beats=["escalation"],
        durable=True,
        db_path=tmp_path / "checkpoints.db",
    )

    assert code == 0
    assert launched == [], "the durable demo bypassed the injected store seam"
    assert (
        injected_store.audit_records
    ), "the injected store was not used by the durable demo"


def test_resume_refused_edit_prints_reason_and_exits_nonzero(
    tmp_path: Path, injected_store, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gate that REFUSES an ``edit`` prints the gate's reason and exits non-zero (WR-02).

    An undeclared ``--colour`` (``PURPLE``) makes the approval token malformed, so the gate
    refuses and leaves the queue untouched; the CLI must not report success by silence.
    """
    case = next(case for case in load_cases(CASES_DIR) if case.id == "E-02")
    db_path = tmp_path / "checkpoints.db"
    tools = build_tools(case, offline=True, recorder=UsageRecorder())
    paused = asyncio.run(
        run_to_gate(tools, raw_note=case.note, case=case.case, db_path=db_path)
    )
    assert paused.paused, "the E-02 case did not pause at the approval gate"

    code = main(
        [
            "resume",
            "--thread-id",
            paused.thread_id,
            "--decision",
            "edit",
            "--approver",
            "Nurse Demo",
            "--role",
            "triage nurse",
            "--colour",
            "PURPLE",
            "--db",
            str(db_path),
        ]
    )

    assert code != 0, "a refused edit reported success"
    err = capsys.readouterr().err
    assert "refusing to commit" in err, "the gate's refusal reason was not printed"
    assert injected_store.rows == [], "a refused edit wrote a queue row"


def test_resume_reports_an_unexpected_failure_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A non-``DurableError`` failure is reported cleanly with exit 1, not a traceback (WR-04).

    The resume path lazily opens the borrowed store (or reads the checkpointer) and can fail
    with a ``RuntimeError``/``sqlite3.Error`` rather than a ``DurableError``; the CLI must
    report that message with a non-zero exit instead of propagating a stack trace.
    """

    async def boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("Client failed to connect")

    monkeypatch.setattr("triagedesk.cli.resume_thread", boom)

    code = main(
        [
            "resume",
            "--thread-id",
            "x",
            "--decision",
            "dismiss",
            "--db",
            str(tmp_path / "checkpoints.db"),
        ]
    )

    assert code == 1
    err = capsys.readouterr().err
    assert "Client failed to connect" in err
    assert "Traceback" not in err
