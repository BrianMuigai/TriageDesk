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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from triagedesk.observability.offline import harden_offline

# The defaults named once so the CLI and the docs agree (DRY).
DEFAULT_CASES_DIR = "evals/cases"
DEFAULT_REPORT_PATH = "evals/results/report.json"
DEFAULT_RUNS = 3


def _resume_policy(args: argparse.Namespace) -> Any:
    """Build the ONE respond policy for ``resume`` — the CLI's whole answer logic (ELICIT-05).

    The policy receives each interrupt payload and returns what to resume with:

    * an **elicitation** is answered with ``--answer`` values, one per question in the order
      they were asked; with no ``--answer`` it is **declined** — the documented default,
      because a refusal is never converted into a value;
    * an **approval** is answered with ``--decision`` through the ONE
      ``durable.approval_decision`` (which rejects a blank identity or a missing colour), and a
      missing ``--decision`` names the flag rather than inventing a decision.

    Both imports are lazy: this function runs inside ``main`` after ``harden_offline()``, so no
    transitive dependency can prime a tracer from the environment at import time (D7-03).
    """
    from triagedesk.durable import DurableError, approval_decision
    from triagedesk.mcp.elicitation import (
        CLARIFICATION_REQUEST_KEY,
        accept_responses,
        answer_fields,
        answers_in_order,
        decline_responses,
        form_requests,
        is_elicitation,
    )

    def policy(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if is_elicitation(payload):
            requests = form_requests(payload)
            request = requests[0] if requests else {}
            key = str(request.get("key") or CLARIFICATION_REQUEST_KEY)
            if args.answer and request:
                return accept_responses(
                    key, answers_in_order(answer_fields(request), args.answer)
                )
            return decline_responses(key)
        if decision is None:
            raise DurableError(
                "--decision is required when the paused case is an approval gate"
            )
        return decision

    # Validate the decision EAGERLY when one was supplied, so a blank identity or a missing
    # edit colour is refused before the checkpoint is even opened (T-06-05, WR-06). An
    # elicitation-only resume supplies no ``--decision`` and is therefore not validated here.
    decision = (
        approval_decision(
            args.decision,
            approver=args.approver,
            role=args.role,
            colour=args.colour,
        )
        if args.decision
        else None
    )
    return policy


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
    eval_parser.add_argument(
        "--no-planner",
        dest="planner",
        action="store_false",
        default=True,
        help=(
            "run the baseline arm: retrieve -> finish_investigation, no planner and no "
            "investigation (the v1.2 path, MEAS-02)"
        ),
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
        default=None,
        help="the clinician's decision at the gate (required when an approval is pending)",
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
        "--answer",
        action="append",
        default=None,
        metavar="ANSWER",
        help=(
            "one answer per question, in the order the questions were asked (repeatable). "
            "An elicitation with no --answer is declined"
        ),
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

    desk_parser = subcommands.add_parser(
        "desk", help="serve the local triage desk surface (loopback only)"
    )
    desk_parser.add_argument(
        "--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)"
    )
    desk_parser.add_argument(
        "--port", type=int, default=8765, help="bind port (default: 8765)"
    )
    desk_parser.add_argument(
        "--db",
        default=None,
        help="checkpoint file (default: checkpoints.db)",
    )
    desk_parser.add_argument(
        "--online",
        action="store_true",
        help="run the real local model on the free-text complaint (default: offline)",
    )

    skill_parser = subcommands.add_parser(
        "skill", help="install or locate the packaged usage skill"
    )
    skill_sub = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_install = skill_sub.add_parser(
        "install", help="copy the usage skill into a skills directory"
    )
    skill_install.add_argument(
        "--path",
        type=Path,
        required=True,
        help="skills directory (creates <path>/triagedesk-triage)",
    )
    skill_install.add_argument(
        "--force",
        action="store_true",
        help="replace a differing installed skill",
    )
    skill_sub.add_parser("path", help="print the packaged skill directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and dispatch; return the process exit code."""
    # Harden FIRST — before any command handler is imported, so no transitive dependency can
    # prime a tracer from the environment at import time (D7-03, WR-06). The handlers are
    # imported lazily below this line, never at module import.
    harden_offline()
    args = _build_parser().parse_args(argv)
    if args.command == "skill":
        # Imported LAZILY inside ``main``, after ``harden_offline()`` has already run,
        # so the package-resource read cannot prime a tracer from the environment.
        from triagedesk.skills import install_skill, skill_root

        if args.skill_command == "path":
            print(skill_root())
            return 0
        try:
            print(install_skill(args.path, force=args.force))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    # The heavy command handlers are imported only after the lightweight ``skill``
    # command has returned, so a package-only install can locate/install the skill
    # without the full graph/model stack. They are still imported after
    # ``harden_offline()``, never at module import (D7-03, WR-06).
    from triagedesk.demo.run import list_beats, run_demo
    from triagedesk.durable import resume_thread
    from triagedesk.evals.runner import run_eval
    from triagedesk.graph.build import CHECKPOINTS_DB_PATH
    from triagedesk.mcp.elicitation import is_elicitation
    from triagedesk.replay import replay_case

    if args.command == "eval":
        return asyncio.run(
            run_eval(
                cases_dir=args.cases,
                runs=args.runs,
                report_path=args.report,
                offline=args.offline,
                case_filter=args.case_filter,
                planner=args.planner,
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
            result = asyncio.run(
                resume_thread(
                    thread_id=args.thread_id,
                    decision=None,
                    db_path=args.db or CHECKPOINTS_DB_PATH,
                    respond=_resume_policy(args),
                )
            )
        except (ValueError, RuntimeError, sqlite3.Error, ExceptionGroup) as exc:
            # ``durable.DurableError`` is a ``RuntimeError``; the borrowed store and the
            # SQLite checkpointer surface as ``RuntimeError`` (sometimes wrapped in an
            # ``ExceptionGroup``) or ``sqlite3.Error``; a decode/deserialisation failure is
            # a ``ValueError``. A clinical CLI reports the failure cleanly with a non-zero
            # exit rather than a raw traceback (WR-04).
            print(str(exc), file=sys.stderr)
            return 1
        # A resume can answer a QUESTION and leave the case at the gate: say so, because
        # "nothing was committed" is the fact the operator must not have to infer (ELICIT-05).
        pending = result.get("__interrupt__")
        if pending:
            payload = dict(pending[0].value)
            at = "a question" if is_elicitation(payload) else "the approval gate"
            print(
                f"paused again at {at}; nothing has been committed. "
                "Run resume again to continue.",
                file=sys.stderr,
            )
            return 0
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
        except (ValueError, RuntimeError, sqlite3.Error, ExceptionGroup) as exc:
            # ``replay.ReplayError`` is a ``RuntimeError``; the SQLite checkpointer surfaces as
            # ``sqlite3.Error`` (sometimes wrapped in an ``ExceptionGroup``); a corrupt span
            # line is a ``ValueError`` (the reader skips these, but the CLI catches one anyway
            # so a decode failure can never traceback). A clinical CLI reports the failure
            # cleanly with a non-zero exit rather than a raw traceback (WR-04). Replay is
            # read-only, so there is nothing to roll back.
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    if args.command == "desk":
        # Imported LAZILY inside ``main`` — after ``harden_offline()`` has already run — so no
        # transitive dependency can prime a tracer from the environment at import time (D10-03,
        # WR-06). The handler is imported here, never at module import.
        from triagedesk.desk.server import serve

        try:
            serve(
                host=args.host,
                port=args.port,
                db_path=args.db or CHECKPOINTS_DB_PATH,
                online=args.online,
            )
        except (ValueError, RuntimeError, sqlite3.Error, ExceptionGroup) as exc:
            # A bind failure, a bad ``--db`` or an unexpected runtime error is reported cleanly
            # with a non-zero exit rather than a raw traceback (WR-04). The surface commits
            # nothing, so there is nothing to roll back.
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    return 2  # pragma: no cover - argparse rejects an unknown command first


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
