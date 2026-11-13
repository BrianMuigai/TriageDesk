"""Every planner decision is a durable, replayable fact (ADAPT-05).

The decision is recorded twice, by the two writers that already exist and are not modified:

* the ONE ``@audited`` interceptor appends exactly one audit record per ``plan_next_step``
  call, carrying the full ``PlanDecision`` as its output — the durable "why next?" record
  (action, rationale, signals, step, whether the guard overrode the proposal, and why);
* the ``plan`` node emits one ``decision`` span carrying the structural facts only — the
  action, the step, the budget and the override flag. Never the rationale, the complaint or
  the note (D7-08).

This suite drives the SHIPPED graph with the SHIPPED planner tool (only the model proposal is
stubbed) and reads both streams back for one adaptive run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import pytest

from conftest import build_graph_tools
from triagedesk.core.schema import (
    CaseInput,
    InvestigationState,
    PlanAction,
    PlanProposal,
)
from triagedesk.graph.build import build_graph
from triagedesk.graph.nodes import case_id_for_note
from triagedesk.mcp import server as server_module
from triagedesk.observability.spans import read_spans

NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, no trauma. "
    "Presenting with central chest pain."
)

# A scored vital is absent, so ``re_extract`` is admissible and the proposal is honoured once.
INCOMPLETE_CASE = CaseInput(
    age_years=40,
    mobility="walking",
    avpu="alert",
    respiratory_rate=24,
    heart_rate=118,
    systolic_bp=108,
    trauma=False,
    complaint="central chest pain",
)


def _real_plan_tool() -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
    """The shipped audited tool, adapted to the graph's injected ``name -> callable`` shape."""

    async def plan_next_step(inp: Mapping[str, Any]) -> Any:
        return await server_module.plan_next_step(
            InvestigationState.model_validate(inp["investigation"])
        )

    return plan_next_step


def _always_proposes(action: PlanAction) -> Callable[..., Awaitable[PlanProposal]]:
    """The model stub: it always asks for the same action; the guard decides."""

    async def propose(*_args: Any, **_kwargs: Any) -> PlanProposal:
        return PlanProposal(action=action, rationale="stub: the note may still hold a vital")

    return propose


async def _run(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> tuple[Mapping[str, Any], list[Any]]:
    """Run one adaptive case with the shipped planner tool and return the state + records."""
    monkeypatch.setattr(
        server_module, "propose_plan_async", _always_proposes(PlanAction.RE_EXTRACT)
    )
    tools = build_graph_tools(case=INCOMPLETE_CASE)
    tools["plan_next_step"] = _real_plan_tool()
    app = build_graph(tools)

    result = await app.ainvoke({"raw_note": NOTE, "case": INCOMPLETE_CASE})
    records = [
        record
        for record in await injected_store.read_audit_records()
        if record.tool == "plan_next_step"
    ]
    return result, records


async def test_one_audit_record_per_decision_carries_the_whole_decision(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """The honoured proposal and the guard override are both recoverable from the audit."""
    result, records = await _run(monkeypatch, injected_store)

    assert len(records) == 2, "one record per planner call, no more"
    honoured, overridden = (record.outputs for record in records)

    assert honoured["action"] == PlanAction.RE_EXTRACT.value
    assert honoured["rationale"] == "stub: the note may still hold a vital"
    assert honoured["step"] == 1
    assert honoured["overridden"] is False

    assert overridden["action"] == PlanAction.FINISH_INVESTIGATION.value
    assert overridden["step"] == 2
    assert overridden["overridden"] is True
    assert overridden["proposed_action"] == PlanAction.RE_EXTRACT.value
    assert overridden["override_reason"], "an override must say why"

    # The audit record is the durable fact; the state carries the same decision.
    assert result["investigation"].history[0] is PlanAction.RE_EXTRACT
    assert result["investigation"].guard_overrides == 1


async def test_the_decision_span_carries_the_structural_facts_only(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """The span names the action, the step and the override — never the rationale (D7-08)."""
    result, _records = await _run(monkeypatch, injected_store)
    del result

    decisions = [
        entry
        for entry in read_spans()
        if entry["kind"] == "decision" and entry["name"] == "plan"
    ]

    assert len(decisions) == 2
    first, second = (entry["attributes"] for entry in decisions)
    assert first["action"] == PlanAction.RE_EXTRACT.value
    assert first["step"] == 1
    assert first["overridden"] is False
    assert second["action"] == PlanAction.FINISH_INVESTIGATION.value
    assert second["step"] == 2
    assert second["overridden"] is True
    assert second["proposed_action"] == PlanAction.RE_EXTRACT.value
    # The structural fact never carries free text from the model.
    assert set(first) == {"action", "step", "budget_left", "overridden", "proposed_action"}


async def test_the_decision_span_belongs_to_the_case_trace(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """The decision is attributable to the case: it carries the content-derived trace id."""
    result, _records = await _run(monkeypatch, injected_store)
    del result

    trace_id = case_id_for_note(NOTE)
    decisions = [
        entry
        for entry in read_spans()
        if entry["kind"] == "decision" and entry["name"] == "plan"
    ]

    assert decisions
    assert all(entry["trace_id"] == trace_id for entry in decisions)
