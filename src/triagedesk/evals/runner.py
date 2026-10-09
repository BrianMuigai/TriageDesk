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

from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.report import Mode, Report, ReportCase, build_provenance, write_report
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
    clinician saw); otherwise the terminal state is read directly.
    """
    if payload is not None:
        return {
            "colour": payload.get("colour"),
            "citations": list(payload.get("citations") or []),
            "triggered_rules": list(payload.get("triggered_rules") or []),
            "matched_ids": list(payload.get("matched_ids") or []),
        }
    priority = result.get("priority")
    triggered = (
        [rule.model_dump(mode="json") for rule in priority.triggered_rules]
        if priority is not None
        else []
    )
    return {
        "colour": priority.colour if priority is not None else None,
        "citations": list(priority.citations) if priority is not None else [],
        "triggered_rules": triggered,
        "matched_ids": list(result.get("matched_ids") or []),
    }


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


async def _run_case(
    case: CaseSpec, *, runs: int, offline: bool, factory: ToolFactory
) -> ReportCase:
    """Run one case ``runs`` times and reduce the captures into a :class:`ReportCase`."""
    recorder = UsageRecorder()
    captures: list[dict[str, Any]] = []
    latency_s: list[float] = []
    tokens_in = 0
    tokens_out = 0

    for run_index in range(runs):
        recorder.reset()
        tools = factory(case, offline, recorder)
        seam = nullcontext() if offline else recorded_extract_seam(recorder)
        with seam:
            captured, latency, _ = await _run_once(case, run_index, tools)
        captures.append(captured)
        latency_s.append(latency)
        run_in, run_out = recorder.totals()
        tokens_in += run_in
        tokens_out += run_out

    colours = [captured["colour"] for captured in captures]
    matched = [sorted(captured["matched_ids"]) for captured in captures]
    citations = [captured["citations"] for captured in captures]
    triggered = [captured["triggered_rules"] for captured in captures]

    return ReportCase(
        case_id=case.id,
        expected=case.expected,
        runs=runs,
        colours=colours,
        matched_discriminators=matched,
        citations=citations,
        colour_stable=len(set(colours)) == 1,
        matched_set_stable=len({tuple(ids) for ids in matched}) == 1,
        field_stable=(
            all(citation == citations[0] for citation in citations)
            and all(rules == triggered[0] for rules in triggered)
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
    the proof suite (SOLID: D). For this plan the exit code is always 0; the invariant
    gate is expanded in a later plan.
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
            await _run_case(case, runs=runs, offline=offline, factory=factory)
            for case in cases
        ]
    finally:
        server_module.set_store(None)

    report = Report(
        mode=mode,
        runs=runs,
        cases_dir=str(cases_dir),
        provenance=build_provenance(mode),
        cases=report_cases,
    )
    write_report(report_path, report)
    return 0


__all__ = ["ToolFactory", "run_eval"]
