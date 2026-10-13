"""The desk surface package (UX-02, UX-03, UX-04; D10-01…D10-16).

The public seam is :func:`triagedesk.desk.server.serve` — the one-command local HTTP
bridge the CLI's ``desk`` subcommand calls. The bridge renders the graph's own typed
outputs and reuses the shipped seams (``durable.run_to_gate`` /
``durable.approval_decision`` / ``durable.resume_thread``, ``evals.tools.offline_tools``,
``core.schema.CaseInput``) and re-implements none of them.
"""

from triagedesk.desk.server import (
    decide,
    form_to_case,
    make_server,
    render_state,
    serve,
    submit_case,
)

__all__ = [
    "decide",
    "form_to_case",
    "make_server",
    "render_state",
    "serve",
    "submit_case",
]
