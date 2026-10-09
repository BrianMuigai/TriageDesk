"""Run each eval case N times through the SAME graph interface (D-01, EVAL-02).

The harness consumes the one graph interface (``TriageState`` + ``interrupt``) — never a
bespoke code path. For each selected case, for each of ``runs`` iterations it resets the
usage sink, builds the injected tools, compiles the graph over an in-memory checkpointer,
invokes it with a per-run ``thread_id``, and captures the outcome.

Because the graph pauses at ``approval_gate``, the colour and citations are read from the
interrupt payload and the run is resumed with an unapproved ``dismiss`` decision — so no
queue write happens and the refusal is observable. The three stability flags are computed
SEPARATELY (D-02): a run-to-run difference in colour or matched-discriminator set is a
recorded instability, never averaged away or hidden behind a majority (Pitfall 12).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from triagedesk.evals.analysis import analyse
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.invariants import (
    INVARIANT_IDS,
    InvariantReport,
    RunEvidence,
    evaluate,
)
from triagedesk.evals.report import (
    GateResult,
    GateViolation,
    Mode,
    Report,
    ReportCase,
    build_provenance,
    write_report,
)
from triagedesk.evals.tools import ToolMap, build_tools, recorded_extract_seam
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import _allowed_msgpack_modules, build_graph
from triagedesk.mcp import server as server_module
from triagedesk.store import Store
from triagedesk.store.memory import InMemoryStore

# A tool factory lets a caller (a test) inject an alternating tool mapping so an
# instability is real and observable rather than simulated in an assertion (SOLID: D).
ToolFactory = Callable[[CaseSpec, bool, UsageRecorder], ToolMap]

# The unapproved resume value: a ``dismiss`` with no named approver, so the gated commit
# refuses it and no queue row is written — the eval never bypasses the gate (D-05).
_UNAPPROVED_RESUME: dict[str, Any] = {"decision": "dismiss"}


def _default_tool_factory(case: CaseSpec, offline: bool, recorder: UsageRecorder) -> ToolMap:
    """The production tool factory: the real owned tools, model stubbed offline."""
    return build_tools(case, offline=offline, recorder=recorder)


def _capture(result: Any, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Capture the outcome facts of one run from the interrupt payload or the end state.

    Reads the graph's own channels — never re-derives a colour or re-scores. When the run
    paused at the gate, the payload is the source (the colour and the evidence the
    clinician saw); otherwise the terminal state is read directly. The graph's terminal
    channels (``recovery``/``escalation``/``second_look``) are captured too, so the runner
    can map a first-class outcome without re-deriving one (ORCH-05).
    """
    recovery = result.get("recovery")
    escalation = result.get("escalation")
    second_look = result.get("second_look")
    if payload is not None:
        colour = payload.get("colour")
        citations = list(payload.get("citations") or [])
        triggered = list(payload.get("triggered_rules") or [])
        matched = list(payload.get("matched_ids") or [])
    else:
        priority = result.get("priority")
        triggered = (
            [rule.model_dump(mode="json") for rule in priority.triggered_rules]
            if priority is not None
            else []
        )
        colour = priority.colour if priority is not None else None
        citations = list(priority.citations) if priority is not None else []
        matched = list(result.get("matched_ids") or [])
    return {
        "colour": colour,
        "citations": citations,
        "triggered_rules": triggered,
        "matched_ids": matched,
        "recovery": recovery is not None,
        "escalation": escalation is not None,
        "second_look": (
            second_look.model_dump(mode="json") if second_look is not None else None
        ),
    }


def _outcome(captured: dict[str, Any], expected: str) -> str | None:
    """Map one run's graph terminal state to a first-class outcome (EVALS §4).

    Precedence, reading the graph's own terminals — never a re-derived colour: a set
    ``escalation`` -> ``ABSTAIN``; a set ``recovery`` -> ``RECOVER``; a set ``second_look``
    flag for a case whose declared expectation is ``RECHECK`` -> ``RECHECK``; otherwise the
    scored colour from the gate payload.
    """
    if captured["escalation"]:
        return "ABSTAIN"
    if captured["recovery"]:
        return "RECOVER"
    second_look = captured["second_look"]
    if second_look is not None and second_look.get("flag") and expected == "RECHECK":
        return "RECHECK"
    colour: str | None = captured["colour"]
    return colour


def _checkpointer() -> InMemorySaver:
    """An in-memory saver carrying the graph's ONE msgpack allowlist (DRY).

    Reuses ``graph.build``'s single allowlist of state types, so the eval's throwaway
    checkpointer registers the same contracts the durable saver does and the resume does
    not trip the future strict-msgpack block. An allowlist — never ``True``.
    """
    return InMemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
    )


async def _run_once(
    case: CaseSpec, run_index: int, tools: ToolMap
) -> tuple[dict[str, Any], float, Any]:
    """Invoke the graph once, resume past the gate if paused, and time the whole run."""
    graph = build_graph(tools, checkpointer=_checkpointer())
    config = {"configurable": {"thread_id": f"{case.id}-{run_index}"}}
    initial: dict[str, Any] = {"raw_note": case.note, "case": case.case}
    previous = getattr(case, "previous_case", None)
    if previous is not None:
        initial["previous_case"] = previous

    started = time.perf_counter()
    result = await graph.ainvoke(initial, config)
    payload: dict[str, Any] | None = None
    if result.get("__interrupt__"):
        payload = dict(result["__interrupt__"][0].value)
        result = await graph.ainvoke(Command(resume=dict(_UNAPPROVED_RESUME)), config)
    latency = time.perf_counter() - started
    return _capture(result, payload), latency, result


def _evidence(
    case: CaseSpec, result: Any, store: Store, rows_before: int, rows_after: int
) -> RunEvidence:
    """Assemble one run's typed evidence for the invariant evaluator (EVAL-03).

    The graph's own terminal channels are read from the final state (``priority``,
    ``commit_result``, ``handover``, ``escalation``, ``recovery``) — never re-derived — and
    the eval store plus the queue-row delta are passed through for INV-2.
    """
    return RunEvidence(
        case_id=case.id,
        expected=case.expected,
        priority=result.get("priority"),
        commit_result=result.get("commit_result"),
        handover=result.get("handover"),
        escalation=result.get("escalation"),
        recovery=result.get("recovery"),
        store=store,
        rows_added=rows_after - rows_before,
    )


def _fold_invariants(
    reports: list[InvariantReport],
) -> tuple[dict[str, bool], dict[str, str]]:
    """Fold the per-run invariant verdicts into one map plus the failure reasons (D-06).

    An invariant holds for a case only when it held on EVERY run; a failed invariant keeps
    the reason(s) the predicate gave, so the report names WHY it broke.
    """
    results: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    for invariant_id in INVARIANT_IDS:
        failures = [
            report.reasons.get(invariant_id, "")
            for report in reports
            if not report.results.get(invariant_id, False)
        ]
        results[invariant_id] = not failures
        if failures:
            reasons[invariant_id] = "; ".join(reason for reason in failures if reason)
    return results, reasons


def _build_gate(report_cases: list[ReportCase]) -> GateResult:
    """Derive the enforcement verdict from the folded case results (D-06, T-04-11).

    A violated invariant is a violation on ANY case (the declared failure included — an
    invariant break is never excused by an expected accuracy miss); a case that failed
    accuracy or stability and is not the declared failure is an unexpected failure. The
    gate passes only when both lists are empty.
    """
    violations = [
        GateViolation(
            case_id=case.case_id,
            invariant=invariant_id,
            reason=case.invariant_reasons.get(invariant_id, ""),
        )
        for case in report_cases
        for invariant_id in INVARIANT_IDS
        if not case.invariants.get(invariant_id, True)
    ]
    unexpected = [
        case.case_id
        for case in report_cases
        if not case.passed and not case.declared_failure
    ]
    return GateResult(
        passed=not violations and not unexpected,
        violations=violations,
        unexpected_failures=unexpected,
    )


async def _run_case(
    case: CaseSpec, *, runs: int, offline: bool, factory: ToolFactory, store: Store
) -> ReportCase:
    """Run one case ``runs`` times and reduce the captures into a :class:`ReportCase`."""
    recorder = UsageRecorder()
    captures: list[dict[str, Any]] = []
    latency_s: list[float] = []
    invariant_reports: list[InvariantReport] = []
    tokens_in = 0
    tokens_out = 0

    for run_index in range(runs):
        recorder.reset()
        tools = factory(case, offline, recorder)
        seam = nullcontext() if offline else recorded_extract_seam(recorder)
        rows_before = len(await store.read_queue_rows())
        with seam:
            captured, latency, result = await _run_once(case, run_index, tools)
        rows_after = len(await store.read_queue_rows())
        # The invariants run INSIDE this same loop, so the report and the exit code can
        # never disagree (DRY, EVAL-03).
        invariant_reports.append(
            await evaluate(_evidence(case, result, store, rows_before, rows_after))
        )
        captures.append(captured)
        latency_s.append(latency)
        run_in, run_out = recorder.totals()
        tokens_in += run_in
        tokens_out += run_out

    colours = [captured["colour"] for captured in captures]
    outcomes = [_outcome(captured, case.expected) for captured in captures]
    matched = [sorted(captured["matched_ids"]) for captured in captures]
    citations = [captured["citations"] for captured in captures]
    triggered = [captured["triggered_rules"] for captured in captures]

    colour_stable = len(set(colours)) == 1
    matched_set_stable = len({tuple(ids) for ids in matched}) == 1
    invariants, invariant_reasons = _fold_invariants(invariant_reports)
    invariants_pass = all(invariants.values())

    return ReportCase(
        case_id=case.id,
        expected=case.expected,
        runs=runs,
        colours=colours,
        outcomes=outcomes,
        matched_discriminators=matched,
        citations=citations,
        colour_stable=colour_stable,
        matched_set_stable=matched_set_stable,
        field_stable=(
            all(citation == citations[0] for citation in citations)
            and all(rules == triggered[0] for rules in triggered)
        ),
        invariants=invariants,
        invariants_pass=invariants_pass,
        invariant_reasons=invariant_reasons,
        passed=(
            all(outcome == case.expected for outcome in outcomes)
            and invariants_pass
            and colour_stable
            and matched_set_stable
        ),
        latency_s=latency_s,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        declared_failure=case.declared_failure,
    )


async def run_eval(
    cases_dir: str | Path,
    runs: int = 3,
    report_path: str | Path = "evals/results/report.json",
    offline: bool = False,
    case_filter: str | None = None,
    *,
    store: Store | None = None,
    tool_factory: ToolFactory | None = None,
) -> int:
    """Run the selected cases ``runs`` times and write the report; return the exit code.

    ``store`` injects the store the gated commit resolves (default: a fresh in-memory
    store, so no borrowed subprocess is launched); ``tool_factory`` injects the tool
    mapping (default: the real owned tools, model stubbed offline). Both are seams for
    the proof suite (SOLID: D).

    The exit code is the gate (D-06): non-zero when ANY invariant is violated on ANY run
    or when any case fails accuracy/stability and is not the declared failure. The declared
    failure (E-09) is an allowed accuracy miss, but an invariant break on ANY case — the
    declared failure included — still exits non-zero. The machine-readable reason is in the
    report's ``gate`` object, so a CI log points at the exact case and invariant.
    """
    cases = load_cases(cases_dir)
    if case_filter is not None:
        cases = [case for case in cases if case.id == case_filter]

    resolved_store = store if store is not None else InMemoryStore()
    factory = tool_factory if tool_factory is not None else _default_tool_factory
    mode: Mode = "offline" if offline else "real"

    server_module.set_store(resolved_store)
    try:
        report_cases = [
            await _run_case(
                case, runs=runs, offline=offline, factory=factory, store=resolved_store
            )
            for case in cases
        ]
    finally:
        server_module.set_store(None)

    aggregate_invariants = {
        invariant_id: all(
            case.invariants.get(invariant_id, False) for case in report_cases
        )
        for invariant_id in INVARIANT_IDS
    }
    gate = _build_gate(report_cases)
    report = Report(
        mode=mode,
        runs=runs,
        cases_dir=str(cases_dir),
        provenance=build_provenance(mode),
        cases=report_cases,
        invariants=aggregate_invariants,
        gate=gate,
    )
    # Populate the self-contained aggregate block from the SAME report, so the measured
    # run carries its own under/over split, stability and cost (EVAL-04, EVAL-05).
    report = report.model_copy(update={"analysis": analyse(report)})
    write_report(report_path, report)
    return 0 if gate.passed else 1


__all__ = ["ToolFactory", "run_eval"]
