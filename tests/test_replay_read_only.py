"""Read-only replay proof suite (Plan 07-02, AGENT-04, D7-09…D7-16).

Proves the headline replay properties against a REAL committed case over a REAL SQLite
checkpointer and the shared in-memory store double:

* **Test A** — replaying a committed, gated case reconstructs the recorded outcome (colour,
  target, citations) and adds ZERO queue rows and ZERO ``commit_priority`` audit records;
* **Test B** — replay never calls the model (the model seam is patched to raise) and emits no
  new ``model`` span;
* **Test C** — an absent thread raises a typed :class:`ReplayError` naming the thread id and
  the checkpoint file;
* **Test D** — the ``replay`` CLI parses its flags and reports an absent thread cleanly with a
  non-zero exit.

The tools are the real owned tools called in-process (only the model is stubbed, via the one
``server_module.extract`` seam), so the suite launches no borrowed ``npx mcp-sqlite``
subprocess and no model. Row/commit counts are asserted as PER-RUN deltas (07-RESEARCH
Pitfall 7: content-addressed cases may share a trace across beats, so absolute counts are
never asserted).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from triagedesk.cli import _build_parser, main
from triagedesk.core.schema import ExtractionResult
from triagedesk.durable import approval_decision, resume_paused, run_to_gate
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.mcp import server as server_module
from triagedesk.observability.spans import SPANS_PATH, read_spans
from triagedesk.replay import ReplayError, replay_case
from triagedesk.store.audit import verify

# The bundled synthetic fixtures, resolved from the repo root (the same cases the demo runs).
CASES_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"

# The synthetic, named approver this suite approves with — a demo identity, no credential.
APPROVER = "Dr A. Nurse"
ROLE = "triage clinician"


def _case(case_id: str) -> CaseSpec:
    """Load one bundled eval case by id (the fixture is the declared input)."""
    return next(case for case in load_cases(CASES_DIR) if case.id == case_id)


async def _run_to_commit(
    case_id: str, *, db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[CaseSpec, str, dict]:
    """Run one case to a committed handover over the durable saver (D6-12 replay input).

    The model is stubbed through the ONE owned ``extract`` seam, so ``normalize_case`` runs
    as the real audited owned tool with no model call. The case pauses at the gate and is
    resumed with a named ``approve`` through the ONE decision builder, so the checkpoint
    carries ``approval``/``commit_result``/``handover`` for replay to read back.
    """
    case = _case(case_id)
    monkeypatch.setattr(
        server_module,
        "extract",
        lambda note: ExtractionResult(case=case.case, matched_discriminator_ids=[]),
    )
    tools = build_tools(case, offline=False, recorder=UsageRecorder())
    paused = await run_to_gate(tools, raw_note=case.note, case=case.case, db_path=db_path)
    assert paused.paused, "the case did not pause at the approval gate"
    final = await resume_paused(
        tools,
        thread_id=paused.thread_id,
        decision=approval_decision("approve", approver=APPROVER, role=ROLE),
        db_path=db_path,
    )
    return case, paused.thread_id, dict(final)


async def test_replay_writes_nothing(
    tmp_path: Path, injected_store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay reconstructs the outcome and adds zero rows / zero commits (D7-13, T-07-05)."""
    db_path = tmp_path / "checkpoints.db"
    case, thread_id, final = await _run_to_commit("E-02", db_path=db_path, monkeypatch=monkeypatch)

    rows_before = len(await injected_store.read_queue_rows())
    commits_before = sum(
        record.tool == "commit_priority"
        for record in await injected_store.read_audit_records()
    )
    records_before = len(await injected_store.read_audit_records())
    calls_before = len(injected_store.calls)

    out = await replay_case(thread_id, db_path=db_path)

    # Zero writes: no queue row, no commit record, no new audit record, no store call.
    assert len(await injected_store.read_queue_rows()) == rows_before
    assert (
        sum(
            record.tool == "commit_priority"
            for record in await injected_store.read_audit_records()
        )
        == commits_before
    )
    assert len(await injected_store.read_audit_records()) == records_before
    assert len(injected_store.calls) == calls_before

    # Outcome equality: the rendered view carries the recorded colour, target and citations.
    priority = final["priority"]
    assert thread_id in out
    assert priority.colour in out
    assert priority.target in out
    for citation in priority.citations:
        assert citation in out
    rows = await injected_store.read_queue_rows()
    assert len(rows) == 1, "the run did not commit exactly one queue row"
    assert rows[0].colour == priority.colour


async def test_replay_leaves_the_queue_and_audit_chain_unchanged(
    tmp_path: Path, injected_store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay adds no queue row and no commit/audit record, and the chain still verifies (WR-01).

    The replay SQLite open is not file-level read-only (the checkpointer runs its idempotent
    ``setup()`` DDL), so the guarantee proven here is the *row-level* one the roadmap requires:
    the queue, the audit record count and the chain head are byte-for-byte unchanged, and the
    chain still verifies.
    """
    db_path = tmp_path / "checkpoints.db"
    _case_spec, thread_id, _final = await _run_to_commit(
        case_id="E-02", db_path=db_path, monkeypatch=monkeypatch
    )

    rows_before = len(await injected_store.read_queue_rows())
    records_before = len(await injected_store.read_audit_records())
    chain_head_before = injected_store.chain_head

    await replay_case(thread_id, db_path=db_path)

    assert len(await injected_store.read_queue_rows()) == rows_before
    assert len(await injected_store.read_audit_records()) == records_before
    assert injected_store.chain_head == chain_head_before
    assert (await verify(injected_store)).valid is True


async def test_replay_never_calls_the_model(
    tmp_path: Path, injected_store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay does not call the model and emits no new ``model`` span (D7-09, D7-16)."""
    db_path = tmp_path / "checkpoints.db"
    _case_spec, thread_id, _final = await _run_to_commit(
        case_id="E-02", db_path=db_path, monkeypatch=monkeypatch
    )

    def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("replay called the model")

    monkeypatch.setattr("triagedesk.llm.client.extract", _boom)
    model_spans_before = sum(1 for row in read_spans() if row["kind"] == "model")

    # Must not raise: the model seam is never reached by a read-only projection.
    out = await replay_case(thread_id, db_path=db_path)

    model_spans_after = sum(1 for row in read_spans() if row["kind"] == "model")
    assert model_spans_after == model_spans_before
    assert thread_id in out


async def test_replay_absent_thread_raises_replay_error(tmp_path: Path) -> None:
    """An absent thread raises ``ReplayError`` naming the thread id and the db (D7-15)."""
    db_path = tmp_path / "checkpoints.db"

    with pytest.raises(ReplayError) as excinfo:
        await replay_case("absent-thread", db_path=db_path)

    message = str(excinfo.value)
    assert "absent-thread" in message
    assert str(db_path) in message


def test_replay_parser_parses_its_flags() -> None:
    """``replay`` parses the thread id and defaults ``--db`` to None (D7-12)."""
    args = _build_parser().parse_args(["replay", "--thread-id", "x"])
    assert args.thread_id == "x"
    assert args.db is None


def test_replay_cli_reports_an_absent_thread_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An absent-thread replay exits non-zero, names the thread, and launches no store (D7-12).

    The checkpoint is read before the store is resolved, so the absent-thread path never
    opens the borrowed SQLite MCP server — mirroring ``triagedesk resume`` (WR-01): the
    spy would raise (and the message would change) if the borrowed store were launched.
    """
    launched: list[object] = []

    def spy(*args: object, **kwargs: object) -> object:
        launched.append((args, kwargs))
        raise AssertionError("the absent-thread replay launched the borrowed store")

    monkeypatch.setattr("triagedesk.store.borrowed.open_borrowed_store", spy)

    code = main(["replay", "--thread-id", "absent", "--db", str(tmp_path / "checkpoints.db")])

    assert code == 1
    err = capsys.readouterr().err
    assert "absent" in err
    assert "Traceback" not in err
    assert launched == []


def test_read_spans_skips_a_truncated_line_and_keeps_the_valid_ones(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A corrupt/truncated span line is skipped (and reported); valid lines survive (WR-01).

    The sink is append-only, so a crash between the write's ``open`` and ``write`` (or any
    external truncation) can leave a partial final line. One bad line must not make the whole
    stream unreadable: the reader returns the valid rows and reports the skip on ``stderr``.
    """
    sink = tmp_path / SPANS_PATH.name
    valid = {"trace_id": "tr-1", "kind": "tool", "name": "normalize_case"}
    sink.write_text(
        json.dumps(valid) + "\n" + '{"trace_id": "tr-1", "kind": "tool"',
        encoding="utf-8",
    )

    rows = read_spans()

    assert rows == [valid], "the valid line was lost to a neighbouring corrupt one"
    err = capsys.readouterr().err
    assert "corrupt span line 2" in err, "the skipped line was not reported"


def test_replay_cli_survives_a_corrupt_span_sink(
    tmp_path: Path,
    injected_store,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A corrupt/truncated span line no longer turns ``triagedesk replay`` into a traceback (WR-01).

    Before the fix the reader's unguarded ``json.loads`` raised ``JSONDecodeError`` — a
    ``ValueError`` the CLI did not catch — so a truncated sink produced a raw traceback. The
    corrupt line is now skipped, the valid timeline stays readable, and the CLI exits cleanly.
    """
    db_path = tmp_path / "checkpoints.db"
    _case_spec, thread_id, _final = asyncio.run(
        _run_to_commit(case_id="E-02", db_path=db_path, monkeypatch=monkeypatch)
    )
    sink = tmp_path / SPANS_PATH.name
    assert sink.exists(), "the run emitted no spans to corrupt"
    sink.write_text(
        sink.read_text(encoding="utf-8") + '{"trace_id": "tr-1", "kind": ',
        encoding="utf-8",
    )

    code = main(["replay", "--thread-id", thread_id, "--db", str(db_path)])

    assert code == 0
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert thread_id in captured.out
    assert read_spans(), "the valid span lines are no longer readable"


def test_replay_cli_reports_a_decode_failure_cleanly(
    tmp_path: Path,
    injected_store,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A decode ``ValueError`` from the replay path exits non-zero with no traceback (WR-01).

    The reader now skips corrupt lines, but the CLI still catches ``ValueError`` so the
    promised clean error can never regress into a raw traceback.
    """
    db_path = tmp_path / "checkpoints.db"
    _case_spec, thread_id, _final = asyncio.run(
        _run_to_commit(case_id="E-02", db_path=db_path, monkeypatch=monkeypatch)
    )

    def _boom(*args: object, **kwargs: object) -> list[dict]:
        raise json.JSONDecodeError("truncated", "doc", 0)

    monkeypatch.setattr("triagedesk.replay.read_spans", _boom)

    code = main(["replay", "--thread-id", thread_id, "--db", str(db_path)])

    assert code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "truncated" in err
