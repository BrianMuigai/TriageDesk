"""The scripted demo package (DOCS-01, D-01, D-07).

The public seam is :func:`triagedesk.demo.run.run_demo` — the one-command offline
storyboard runner the CLI's ``demo`` subcommand calls — plus :func:`list_beats`, the
manifest lister ``--list`` uses. The runner reuses the shipped seams
(``evals.case.load_cases`` + ``evals.tools.build_tools`` + ``graph.build.build_graph``)
and re-implements none of them.
"""

from triagedesk.demo.run import list_beats, load_storyboard, run_demo

__all__ = ["list_beats", "load_storyboard", "run_demo"]
