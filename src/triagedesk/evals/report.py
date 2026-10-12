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
    first-class per-run terminal outcome (a colour or RECOVER/ABSTAIN/RECHECK/ABORT) read
    from the graph's own terminal state (ORCH-05). ``delivered``/``routes``/``attempts``
    are the run's terminal facts — whether a handover card was produced through the gate,
    and the graph's own routing channel — so a card-less abort is distinguishable from a
    delivered colour (G-2). ``invariants`` is the per-invariant verdict (folded across
    runs) and ``invariant_reasons`` names WHY a failed invariant broke; ``invariants_pass``
    is the fold of that map. ``passed`` is the accuracy verdict: every run's outcome equals
    ``expected`` AND every invariant holds AND colour and matched-set are stable.
    ``tokens_in``/``tokens_out`` are the case's totals across runs; ``latency_s`` is per-run.

    ``held_out`` records the declared calibration split (a held-out case bounds the declared
    failure and is never iterated against, D8-13). ``confidence_levels`` / ``deferrals`` /
    ``confidence_satisfied`` are the per-run coverage-signal captures read from the graph's own
    ``confidence`` channel — ``None`` for a run that short-circuited before ``assess``. The
    internal ordinal scalar (``confidence_satisfied``) lives ONLY here in ``evals/``: it is never
    in ``core.schema`` and never in a tool output (D8-04, A2).
    """

    case_id: str
    expected: str
    runs: int
    colours: list[str | None] = Field(default_factory=list)
    outcomes: list[str | None] = Field(default_factory=list)
    matched_discriminators: list[list[str]] = Field(default_factory=list)
    citations: list[list[str]] = Field(default_factory=list)
    delivered: list[bool] = Field(default_factory=list)
    routes: list[str | None] = Field(default_factory=list)
    attempts: list[int] = Field(default_factory=list)
    colour_stable: bool = False
    matched_set_stable: bool = False
    field_stable: bool = False
    invariants: dict[str, bool] = Field(default_factory=dict)
    invariants_pass: bool = False
    invariant_reasons: dict[str, str] = Field(default_factory=dict)
    passed: bool = False
    latency_s: list[float] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    declared_failure: bool = False
    # The declared calibration split (D8-13) and the per-run coverage-signal facts (D8-10).
    held_out: bool = False
    confidence_levels: list[str | None] = Field(default_factory=list)
    deferrals: list[bool | None] = Field(default_factory=list)
    confidence_satisfied: list[int | None] = Field(default_factory=list)


class GateViolation(BaseModel):
    """One invariant violation the gate reports (EVAL-03, D-06).

    Names the exact case and invariant (and the reason the predicate gave), so a CI log
    points at the failing run rather than a bare non-zero exit.
    """

    case_id: str
    invariant: str
    reason: str = ""


class GateResult(BaseModel):
    """The eval gate verdict — the machine-readable reason for the exit code (D-06).

    ``passed`` is ``True`` only when no invariant was violated on any run and no
    non-declared accuracy miss is present. ``violations`` names every broken invariant
    (per case) and ``unexpected_failures`` lists the non-declared cases that missed. The
    single declared failure (E-09) is an allowed miss and never appears here.
    """

    passed: bool = False
    violations: list[GateViolation] = Field(default_factory=list)
    unexpected_failures: list[str] = Field(default_factory=list)


class RiskCoveragePoint(BaseModel):
    """One point on the risk–coverage curve (D8-13, D8-15).

    ``threshold`` is the deterministic ordinal coverage count at which the point is swept;
    ``coverage`` is the fraction of measured runs at or above it and ``risk`` the error rate
    among those runs. It is a *ranking* over the deterministic signal — never a probability —
    so it stays compatible with "never a model probability" (D8-04). It is only ever built with
    an explicit ``threshold``, so it needs no bare-constructible default.
    """

    threshold: int
    coverage: float = 0.0
    risk: float = 0.0


class Calibration(BaseModel):
    """The declared-split calibration block over a measured report (D8-13, D8-15).

    ``calibration_ids``/``held_out_ids`` name the two splits explicitly (the calibration split
    is ``held_out=False``; the held-out split bounds the declared failure) and ``n_*`` name their
    sizes. ``risk_coverage`` sweeps the deterministic rank; ``ece`` is the offline expected
    calibration error over the calibration split, binned coarsely (``ece_bins``). Both are
    declared a small-sample measure (``small_sample_caveat`` names both ``n``s) and are NEVER
    presented as a validated calibrated probability (D8-04, D8-15, A2).

    Every field is defaulted so a bare ``Calibration()`` is valid: the model is reached through
    ``Analysis.calibration = Field(default_factory=Calibration)``, so it MUST construct with no
    arguments (as must a bare ``Analysis()`` and a ``Report(...)`` built without ``analysis``).
    """

    calibration_ids: list[str] = Field(default_factory=list)
    held_out_ids: list[str] = Field(default_factory=list)
    n_calibration: int = 0
    n_held_out: int = 0
    risk_coverage: list[RiskCoveragePoint] = Field(default_factory=list)
    ece: float = 0.0
    ece_bins: int = 0
    small_sample_caveat: str = ""


class Analysis(BaseModel):
    """The safety-relevant aggregate block over a report (EVAL-04, EVAL-05, D-03).

    Under-triage and over-triage are carried SEPARATELY (``under_triage`` /
    ``over_triage``: the offending case ids, with the per-run counts), never collapsed
    into one symmetric accuracy figure (D-03, Pitfall 8). ``terminal_*`` reports the
    RECOVER/ABSTAIN/RECHECK correctness on its own — those outcomes are excluded from the
    colour direction split. The two stability summaries are kept distinct and the
    latency/token figures make the measured cost visible (D-02, EVAL-05).

    ``red_expected_count`` / ``red_miss_count`` / ``red_miss_cases`` surface the
    safety-critical miss — an under-triaged most-urgent (RED) case — with its own weight
    so the asymmetry reads explicitly (Pitfall 8). The most-urgent colour is derived from
    the loaded substrate, never a hard-coded literal (CONVENTIONS §1).

    ``aborted_cases`` / ``aborted_count`` report the runs that stopped at ``END`` without a
    handover card (``ABORT_OUTCOME``) on their own — an abort is never folded into the
    under/over direction split or the colour accuracy figure (G-2, T-04-26).

    ``deferral_count`` / ``deferral_runs`` / ``deferral_rate`` / ``deferral_cases`` report the
    coverage deferrals SEPARATELY, next to the outcome breakdown (D8-10, D8-16): a deferral is
    reduced coverage, not a wrong answer. ``calibration`` carries the declared-split
    calibration block (D8-13, D8-15).
    """

    colour_runs: int = 0
    colour_correct: int = 0
    colour_accuracy: float = 0.0
    under_triage: list[str] = Field(default_factory=list)
    under_triage_count: int = 0
    over_triage: list[str] = Field(default_factory=list)
    over_triage_count: int = 0
    terminal_runs: int = 0
    terminal_correct: int = 0
    terminal_counts: dict[str, int] = Field(default_factory=dict)
    terminal_misses: list[str] = Field(default_factory=list)
    aborted_cases: list[str] = Field(default_factory=list)
    aborted_count: int = 0
    colour_stable_cases: list[str] = Field(default_factory=list)
    colour_unstable_cases: list[str] = Field(default_factory=list)
    field_stable_cases: list[str] = Field(default_factory=list)
    field_unstable_cases: list[str] = Field(default_factory=list)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    red_expected_count: int = 0
    red_miss_count: int = 0
    red_miss_cases: list[str] = Field(default_factory=list)
    deferral_count: int = 0
    deferral_runs: int = 0
    deferral_rate: float = 0.0
    deferral_cases: list[str] = Field(default_factory=list)
    calibration: Calibration = Field(default_factory=Calibration)


class Report(BaseModel):
    """The complete machine-generated report (D-08, EVAL-02).

    ``mode`` labels an offline (stubbed-model) run so it can never be presented as a real
    measured run (T-04-01, Pitfall 16). ``invariants`` is the aggregate per-invariant
    verdict (folded across every case) and ``gate`` is the enforcement verdict the exit
    code is derived from. ``analysis`` is the self-contained aggregate block
    (EVAL-04/EVAL-05) — it is NOT sealed in ``report_digest`` because it carries the
    volatile latency/token totals (D-08).
    """

    mode: Mode
    runs: int
    cases_dir: str
    provenance: Provenance
    cases: list[ReportCase] = Field(default_factory=list)
    invariants: dict[str, bool] = Field(default_factory=dict)
    gate: GateResult = Field(default_factory=GateResult)
    analysis: Analysis = Field(default_factory=Analysis)
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
    reproduce the same digest, while a real change (an outcome, a stability flag or an
    invariant verdict) does not. Only the case ids, expected/measured outcomes, the
    stability flags, the invariant verdicts, the gate and the provenance block are covered.

    The per-case coverage/deferral facts (``held_out``, ``confidence_levels``, ``deferrals``)
    are sealed too: a flipped deferral is a change in the published safety behaviour, so it
    must move ``report_digest`` (D8-14). The aggregate ``Calibration`` block is left in
    ``Analysis`` (which the digest never covers — it carries the volatile cost totals), so
    only the deterministic per-case content is sealed here.
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
                "delivered": case.delivered,
                "routes": case.routes,
                "attempts": case.attempts,
                "colour_stable": case.colour_stable,
                "matched_set_stable": case.matched_set_stable,
                "field_stable": case.field_stable,
                "invariants": case.invariants,
                "invariants_pass": case.invariants_pass,
                "declared_failure": case.declared_failure,
                "held_out": case.held_out,
                "confidence_levels": case.confidence_levels,
                "deferrals": case.deferrals,
            }
            for case in report.cases
        ],
        "invariants": report.invariants,
        "gate": report.gate.model_dump(mode="json"),
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
    "Analysis",
    "Calibration",
    "GateResult",
    "GateViolation",
    "Mode",
    "Provenance",
    "Report",
    "ReportCase",
    "RiskCoveragePoint",
    "build_provenance",
    "compute_report_digest",
    "write_report",
]
