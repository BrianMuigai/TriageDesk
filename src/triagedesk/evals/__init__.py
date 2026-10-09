"""The honest evaluation harness (Phase 4, D-01, EVAL-01/EVAL-02).

``triagedesk eval`` runs each case N times through the SAME graph interface and writes a
machine-generated report carrying the colour, the matched-discriminator set, the three
SEPARATE stability flags, per-run latency, token cost and the provenance hashes. The
report is the sole record of a run — reproducible, not retyped (D-08).
"""

from __future__ import annotations

from triagedesk.evals.analysis import analyse, colour_urgency
from triagedesk.evals.case import TERMINAL_OUTCOMES, CaseSpec, declared_outcomes, load_cases
from triagedesk.evals.report import (
    Analysis,
    Provenance,
    Report,
    ReportCase,
    build_provenance,
    compute_report_digest,
    write_report,
)
from triagedesk.evals.runner import run_eval
from triagedesk.evals.tools import ToolMap, build_tools, recorded_extract_seam
from triagedesk.evals.usage import UsageRecorder, recorded_extract

__all__ = [
    "TERMINAL_OUTCOMES",
    "Analysis",
    "CaseSpec",
    "Provenance",
    "Report",
    "ReportCase",
    "ToolMap",
    "UsageRecorder",
    "analyse",
    "build_provenance",
    "build_tools",
    "colour_urgency",
    "compute_report_digest",
    "declared_outcomes",
    "load_cases",
    "recorded_extract",
    "recorded_extract_seam",
    "run_eval",
    "write_report",
]
