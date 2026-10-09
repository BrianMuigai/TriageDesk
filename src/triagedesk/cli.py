"""The ``triagedesk`` console entry point (D-01, EVAL-02, DOCS-01).

The thinnest possible shell over the async runners: it parses the ``eval`` and ``demo``
commands with stdlib ``argparse`` (no new dependency, SAFE-04) and hands the arguments to
``triagedesk.evals.runner.run_eval`` or ``triagedesk.demo.run.run_demo``. Each runner's
integer exit code is returned from ``main``, which the console script passes to
``sys.exit``.
"""

from __future__ import annotations

import argparse
import asyncio

from triagedesk.demo.run import list_beats, run_demo
from triagedesk.evals.runner import run_eval

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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and dispatch; return the process exit code."""
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
            )
        )
    return 2  # pragma: no cover - argparse rejects an unknown command first


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
