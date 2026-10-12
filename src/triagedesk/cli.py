"""The ``triagedesk`` console entry point (D-01, EVAL-02, DOCS-01).

The thinnest possible shell over the async runners: it parses the ``eval``, ``demo``,
``resume`` and ``replay`` commands with stdlib ``argparse`` (no new dependency, SAFE-04) and
hands the arguments to ``triagedesk.evals.runner.run_eval``, ``triagedesk.demo.run.run_demo``,
``triagedesk.durable.resume_thread`` or ``triagedesk.replay.replay_case``. Each runner's
integer exit code is returned from ``main``, which the console script passes to ``sys.exit``.

No graph, store or decision-shape logic lives here: the durable decision rule is the ONE
``durable.approval_decision`` and the resume mechanism is the ONE
``durable.resume_thread`` (SOLID: S).

``main``'s FIRST statement is ``observability.offline.harden_offline`` — the ONE place the
transitive tracer environment is neutralised and asserted off, so no command egresses
(D7-03). The command handlers are imported lazily *after* it, so no transitive dependency can
prime a tracer from the environment at import time (WR-06).
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys

from triagedesk.observability.offline import harden_offline

# The defaults named once so the CLI and the docs agree (DRY).
DEFAULT_CASES_DIR = "evals/cases"
DEFAULT_REPORT_PATH = "evals/results/report.json"
DEFAULT_RUNS = 3


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``triagedesk`` argument parser (stdlib only, SAFE-04)."""
    parser = argparse.ArgumentParser(
        prog="triagedesk",
        description="TriageDesk — sourced, SATS-grounded triage support.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    eval_parser = subcommands.add_parser("eval", help="run the evaluation harness")
    eval_parser.add_argument(
        "--cases", default=DEFAULT_CASES_DIR, help="directory of case fixtures"
    )
    eval_parser.add_argument(
        "--runs", type=int, default=DEFAULT_RUNS, help="runs per case"
    )
    eval_parser.add_argument(
        "--report", default=DEFAULT_REPORT_PATH, help="report output path (JSON)"
    )
    eval_parser.add_argument(
        "--offline",
        action="store_true",
        help="stub the model and use the golden extractions (deterministic CI mode)",
    )
    eval_parser.add_argument(
        "--case", dest="case_filter", default=None, help="run a single case id"
    )

    demo_parser = subcommands.add_parser(
        "demo", help="run the scripted demo storyboard (offline by default)"
    )
    demo_parser.add_argument(
        "--online",
        action="store_true",
        help="use the pulled local model (default: the offline golden fixture)",
    )
    demo_parser.add_argument(
        "--beat",
        dest="beats",
        action="append",
        default=None,
        help="run a single storyboard beat by name (repeatable)",
    )
    demo_parser.add_argument(
        "--list",
        dest="list_beats",
        action="store_true",
        help="list the storyboard beat names and labels, then exit",
    )
    demo_parser.add_argument(
        "--fixture", default=DEFAULT_CASES_DIR, help="directory of case fixtures"
    )
    demo_parser.add_argument(
        "--durable",
        action="store_true",
        help="run ONE beat to the durable approval gate and print the resume command",
    )
    demo_parser.add_argument(
        "--db",
        default=None,
        help="checkpoint file for --durable (default: checkpoints.db)",
    )

    resume_parser = subcommands.add_parser(
        "resume", help="resume a paused durable thread through the approval gate"
    )
    resume_parser.add_argument(
        "--thread-id",
        required=True,
        help="the content-derived thread id printed by demo --durable",
    )
    resume_parser.add_argument(
        "--decision",
        choices=["approve", "edit", "dismiss"],
        required=True,
        help="the clinician's decision at the gate",
    )
    resume_parser.add_argument(
        "--approver", default=None, help="the named clinician (required for approve/edit)"
    )
    resume_parser.add_argument(
        "--role", default=None, help="the clinician's role (required for approve/edit)"
    )
    resume_parser.add_argument(
        "--colour", default=None, help="the edited colour (required for an edit decision)"
    )
    resume_parser.add_argument(
        "--db",
        default=None,
        help="checkpoint file (default: checkpoints.db)",
    )

    replay_parser = subcommands.add_parser(
        "replay", help="read-only reconstruction of a past case from checkpoint + stream"
    )
    replay_parser.add_argument(
        "--thread-id",
        required=True,
        help="the content-derived thread id of the case to reconstruct",
    )
    replay_parser.add_argument(
        "--db",
        default=None,
        help="checkpoint file (default: checkpoints.db)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and dispatch; return the process exit code."""
    # Harden FIRST — before any command handler is imported, so no transitive dependency can
    # prime a tracer from the environment at import time (D7-03, WR-06). The handlers are
    # imported lazily below this line, never at module import.
    harden_offline()
    from triagedesk.demo.run import list_beats, run_demo
    from triagedesk.durable import DurableError, approval_decision, resume_thread
    from triagedesk.evals.runner import run_eval
    from triagedesk.graph.build import CHECKPOINTS_DB_PATH
    from triagedesk.replay import ReplayError, replay_case

    args = _build_parser().parse_args(argv)
    if args.command == "eval":
        return asyncio.run(
            run_eval(
                cases_dir=args.cases,
                runs=args.runs,
                report_path=args.report,
                offline=args.offline,
                case_filter=args.case_filter,
            )
        )
    if args.command == "demo":
        if args.list_beats:
            return list_beats()
        return asyncio.run(
            run_demo(
                beats=args.beats,
                offline=not args.online,
                fixture_dir=args.fixture,
                durable=args.durable,
                db_path=args.db,
            )
        )
    if args.command == "resume":
        try:
            decision = approval_decision(
                args.decision,
                approver=args.approver,
                role=args.role,
                colour=args.colour,
            )
            result = asyncio.run(
                resume_thread(
                    thread_id=args.thread_id,
                    decision=decision,
                    db_path=args.db or CHECKPOINTS_DB_PATH,
                )
            )
        except (DurableError, RuntimeError, sqlite3.Error, ExceptionGroup) as exc:
            # ``DurableError`` is a ``RuntimeError``; the borrowed store and the SQLite
            # checkpointer surface as ``RuntimeError`` (sometimes wrapped in an
            # ``ExceptionGroup``) or ``sqlite3.Error``. A clinical CLI reports the failure
            # cleanly with a non-zero exit rather than a raw traceback (WR-04).
            print(str(exc), file=sys.stderr)
            return 1
        # Surface the gate's outcome so a refused approve/edit is never mistaken for a
        # commit (WR-02): a ``dismiss`` refusal is legitimate and exits 0; any other
        # refusal exits non-zero. The reason is the ONE ``CommitResult.reason`` the gate
        # already produces, so the CLI restates no gate logic (SOLID: S/D).
        commit = result.get("commit_result")
        if commit is not None:
            print(commit.reason, file=sys.stderr)
            if commit.refused and args.decision != "dismiss":
                return 1
        return 0
    if args.command == "replay":
        try:
            print(
                asyncio.run(
                    replay_case(args.thread_id, db_path=args.db or CHECKPOINTS_DB_PATH)
                )
            )
        except (ReplayError, RuntimeError, sqlite3.Error, ExceptionGroup) as exc:
            # ``ReplayError`` is a ``RuntimeError``; the SQLite checkpointer surfaces as
            # ``sqlite3.Error`` (sometimes wrapped in an ``ExceptionGroup``). A clinical CLI
            # reports the failure cleanly with a non-zero exit rather than a raw traceback
            # (WR-04). Replay is read-only, so there is nothing to roll back.
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    return 2  # pragma: no cover - argparse rejects an unknown command first


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
