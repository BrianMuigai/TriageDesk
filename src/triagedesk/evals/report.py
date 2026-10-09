"""The machine-generated eval report (D-02, D-08, EVAL-02).

The report is the sole record of a run: it carries, per case, the three run colours, the
matched-discriminator sets, the three SEPARATE stability flags, per-run latency and the
token totals, plus the provenance hashes (model tag, Ollama version, prompt hash, the two
SATS YAML hashes, harness commit SHA) needed to reproduce or disprove the run. It also
carries a ``report_digest`` sealing its non-volatile content, so a hand-edited number is
detectable (D-08, Pitfall 18).

The whole report is serialised through the ONE canonical JSON path (``core.hashing``) —
untrusted complaint text is never string-concatenated into it (T-04-03, M-13).
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from triagedesk.core.hashing import canonical_json, hash_prompt, hash_rule_object, hash_value
from triagedesk.core.rules import load_discriminators, load_tews
from triagedesk.llm.client import DEFAULT_MODEL
from triagedesk.llm.prompts import EXTRACTION_PROMPT

Mode = Literal["real", "offline"]

# The provenance hashes that must recompute from the substrate, never be read from a
# stale manifest: a drifted YAML is caught here (D-08).
_UNKNOWN = "unknown"


class Provenance(BaseModel):
    """The hashes and version facts that make a run reproducible (D-08, §8)."""

    model_tag: str
    ollama_version: str
    prompt_hash: str
    sats_tews_hash: str
    sats_discriminators_hash: str
    harness_commit: str


class ReportCase(BaseModel):
    """One case's measured result across its runs (D-02).

    ``colours``, ``matched_discriminators`` and ``citations`` are the per-run captures
    (never averaged); the three stability flags are computed SEPARATELY so a stable
    colour with an unstable citation list is visible (Pitfall 6). ``outcomes`` is the
    first-class per-run terminal outcome (a colour or RECOVER/ABSTAIN/RECHECK) read from
    the graph's own terminal state (ORCH-05). ``passed`` is the accuracy verdict: every
    run's outcome equals ``expected`` AND colour and matched-set are stable.
    ``tokens_in``/``tokens_out`` are the case's totals across runs; ``latency_s`` is
    per-run.
    """

    case_id: str
    expected: str
    runs: int
    colours: list[str | None] = Field(default_factory=list)
    outcomes: list[str | None] = Field(default_factory=list)
    matched_discriminators: list[list[str]] = Field(default_factory=list)
    citations: list[list[str]] = Field(default_factory=list)
    colour_stable: bool = False
    matched_set_stable: bool = False
    field_stable: bool = False
    passed: bool = False
    latency_s: list[float] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    declared_failure: bool = False


class Report(BaseModel):
    """The complete machine-generated report (D-08, EVAL-02).

    ``mode`` labels an offline (stubbed-model) run so it can never be presented as a real
    measured run (T-04-01, Pitfall 16).
    """

    mode: Mode
    runs: int
    cases_dir: str
    provenance: Provenance
    cases: list[ReportCase] = Field(default_factory=list)
    report_digest: str = ""


def _git_commit() -> str:
    """Return the current git commit SHA, or ``"unknown"`` when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return _UNKNOWN
    return result.stdout.strip() or _UNKNOWN


def _ollama_version() -> str:
    """Read the running Ollama server's version, or ``"unknown"`` when unreachable."""
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/version", timeout=2) as response:
            return str(json.loads(response.read()).get("version", _UNKNOWN))
    except (OSError, ValueError):
        return _UNKNOWN


def build_provenance(mode: Mode) -> Provenance:
    """Assemble the provenance block, recomputing every hash from the loaded substrate.

    The SATS YAML and prompt hashes are RECOMPUTED through the ONE hashing path (never
    read from ``evidence/hashes.json``), so a drifted YAML is caught rather than trusted
    (D-08). The Ollama version is read only for a real run; an offline run records
    ``"unknown"`` (T-04-01).
    """
    return Provenance(
        model_tag=DEFAULT_MODEL,
        ollama_version=_ollama_version() if mode == "real" else _UNKNOWN,
        prompt_hash=hash_prompt(EXTRACTION_PROMPT),
        sats_tews_hash=hash_rule_object(load_tews()),
        sats_discriminators_hash=hash_rule_object(load_discriminators()),
        harness_commit=_git_commit(),
    )


def _digest_payload(report: Report) -> dict[str, Any]:
    """The non-volatile content the ``report_digest`` seals (D-08, Pitfall 18).

    Deliberately EXCLUDES latency, token counts and timestamps: the same behaviour must
    reproduce the same digest, while a real change (an outcome or a stability flag) does
    not. Only the case ids, expected/measured outcomes, the stability flags and the
    provenance block are covered.
    """
    return {
        "provenance": report.provenance.model_dump(mode="json"),
        "cases": [
            {
                "case_id": case.case_id,
                "expected": case.expected,
                "runs": case.runs,
                "colours": case.colours,
                "outcomes": case.outcomes,
                "matched_discriminators": case.matched_discriminators,
                "citations": case.citations,
                "colour_stable": case.colour_stable,
                "matched_set_stable": case.matched_set_stable,
                "field_stable": case.field_stable,
                "declared_failure": case.declared_failure,
            }
            for case in report.cases
        ],
    }


def compute_report_digest(report: Report) -> str:
    """The canonical digest of a report's non-volatile content (the ONE sealing path)."""
    return hash_value(_digest_payload(report))


def write_report(path: str | Path, report: Report) -> Report:
    """Seal *report* with its digest and write it through the canonical JSON path.

    Returns the sealed report (with ``report_digest`` set). The serialisation goes through
    ``core.hashing.canonical_json`` so untrusted complaint text is never concatenated into
    the document (T-04-03).
    """
    sealed = report.model_copy(update={"report_digest": compute_report_digest(report)})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical_json(sealed) + "\n", encoding="utf-8")
    return sealed


__all__ = [
    "Mode",
    "Provenance",
    "Report",
    "ReportCase",
    "build_provenance",
    "compute_report_digest",
    "write_report",
]
