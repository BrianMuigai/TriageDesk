"""The ``triagedesk`` console entry point (D-01, EVAL-02).

The thinnest possible shell over the async eval runner: it parses the ``eval`` command
with stdlib ``argparse`` (no new dependency, SAFE-04) and hands the arguments to
``triagedesk.evals.runner.run_eval``. The runner's integer exit code is returned from
``main``, which the console script passes to ``sys.exit``.
"""

from __future__ import annotations

import argparse
import asyncio

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
    return 2  # pragma: no cover - argparse rejects an unknown command first


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
