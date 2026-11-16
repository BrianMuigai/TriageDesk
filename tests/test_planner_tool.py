"""The eighth owned tool and the ONE model path for a plan (Plan 20-02, ADAPT-02/04).

Exercised over the SDK's in-memory client with the model stubbed, exactly as
``tests/test_mcp_tools.py`` does: no borrowed server, no subprocess, no network. The point of
this module is the *boundary*: the tool may only return an admissible action, and the routine
case must not call the model at all.

The autouse ``_model_seam_is_stubbed`` fixture in ``conftest`` already makes an unpatched
``propose_plan_async`` raise, so a test that forgets to stub it fails loudly instead of
reaching Ollama.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from mcp import Client

from triagedesk.core.planner import admissible_actions
from triagedesk.core.schema import (
    InvestigationState,
    PlanAction,
    PlanDecision,
    PlanProposal,
)
from triagedesk.llm import client
from triagedesk.mcp import server as server_module

# A state whose only admissible action is the exit: evidence in hand, no ambiguity, no
# missing vital, and no budget left. This is the routine case the fast path protects.
_FINISH_ONLY_STATE = InvestigationState(
    complaint="chest pain",
    retrieval_status="matched",
    has_evidence=True,
    budget_left=0,
)


def _decision(call: Any) -> PlanDecision:
    """Validate one MCP tool payload back to the shared contract (D-14)."""
    assert not call.is_error, f"plan_next_step errored: {call}"
    return PlanDecision.model_validate_json(call.content[0].text)


def _spy(proposal: PlanProposal | None) -> tuple[list[InvestigationState], Any]:
    """A recording stub for the ONE model wrapper — never touches Ollama."""
    calls: list[InvestigationState] = []

    async def stub(state: InvestigationState, **kwargs: Any) -> PlanProposal | None:
        calls.append(state)
        return proposal

    return calls, stub


async def test_plan_next_step_is_registered_on_the_owned_server() -> None:
    """The eighth tool is part of the owned surface a harness discovers."""
    async with Client(server_module.server) as client_:
        listed = await client_.list_tools()
    assert "plan_next_step" in {tool.name for tool in listed.tools}


def test_plan_next_step_is_async_and_contract_typed() -> None:
    """The tool is the async adapter the graph can await, over the shared contracts."""
    assert inspect.iscoroutinefunction(server_module.plan_next_step)
    signature = inspect.signature(server_module.plan_next_step)
    assert list(signature.parameters) == ["investigation"]


async def test_the_fast_path_never_calls_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """When only the exit is admissible the wrapper is not called (the spy stays empty)."""
    calls, spy = _spy(PlanProposal(action="gather_evidence"))
    monkeypatch.setattr(server_module, "propose_plan_async", spy)

    async with Client(server_module.server) as client_:
        call = await client_.call_tool(
            "plan_next_step", {"investigation": _FINISH_ONLY_STATE.model_dump(mode="json")}
        )

    decision = _decision(call)
    assert calls == [], "the fast path called the model"
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is False
    assert decision.step == _FINISH_ONLY_STATE.step + 1
    assert decision.budget_left == 0


async def test_an_admissible_proposal_is_returned_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model's admissible action reaches the caller, flagged as not overridden."""
    state = InvestigationState(complaint="chest pain", has_evidence=False)
    _, spy = _spy(PlanProposal(action="gather_evidence", rationale="no excerpt yet"))
    monkeypatch.setattr(server_module, "propose_plan_async", spy)

    async with Client(server_module.server) as client_:
        call = await client_.call_tool(
            "plan_next_step", {"investigation": state.model_dump(mode="json")}
        )

    decision = _decision(call)
    assert decision.action is PlanAction.GATHER_EVIDENCE
    assert decision.proposed_action is PlanAction.GATHER_EVIDENCE
    assert decision.overridden is False
    assert decision.rationale == "no excerpt yet"


async def test_an_inadmissible_proposal_degrades_through_the_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `matched` state cannot ask a question: the guard replaces the proposal (ADAPT-02)."""
    state = InvestigationState(complaint="chest pain", retrieval_status="matched")
    _, spy = _spy(PlanProposal(action="ask_question"))
    monkeypatch.setattr(server_module, "propose_plan_async", spy)

    async with Client(server_module.server) as client_:
        call = await client_.call_tool(
            "plan_next_step", {"investigation": state.model_dump(mode="json")}
        )

    decision = _decision(call)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.proposed_action is PlanAction.ASK_QUESTION
    assert decision.overridden is True
    assert "ask_question" in (decision.override_reason or "")


async def test_a_missing_proposal_degrades_through_the_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable model is a `None` proposal, and the guard finishes (ADAPT-02)."""
    state = InvestigationState(complaint="chest pain", has_evidence=False)
    _, spy = _spy(None)
    monkeypatch.setattr(server_module, "propose_plan_async", spy)

    async with Client(server_module.server) as client_:
        call = await client_.call_tool(
            "plan_next_step", {"investigation": state.model_dump(mode="json")}
        )

    decision = _decision(call)
    assert decision.action is PlanAction.FINISH_INVESTIGATION
    assert decision.overridden is True
    assert decision.proposed_action is None


async def test_the_tool_cannot_return_an_inadmissible_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Over every proposal the model could make, the decision stays admissible (ADAPT-02)."""
    state = InvestigationState(complaint="chest pain", retrieval_status="no_candidate")
    admissible = admissible_actions(state)

    for action in PlanAction:
        _, spy = _spy(PlanProposal(action=action))
        monkeypatch.setattr(server_module, "propose_plan_async", spy)
        async with Client(server_module.server) as client_:
            call = await client_.call_tool(
                "plan_next_step", {"investigation": state.model_dump(mode="json")}
            )
        assert _decision(call).action in admissible, action


async def test_the_prompt_lists_the_guards_own_admissible_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The prompt cannot disagree with the validator: both read `admissible_actions` (DRY)."""
    state = InvestigationState(complaint="chest pain", retrieval_status="matched")
    captured: dict[str, Any] = {}

    async def fake_generate(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return {
            "response": '{"action": "finish_investigation"}',
            "prompt_eval_count": 3,
            "eval_count": 2,
        }

    monkeypatch.setattr(client, "_async_generate", fake_generate)
    proposal = await client.propose_plan_async(state)

    assert proposal is not None
    assert proposal.action is PlanAction.FINISH_INVESTIGATION
    prompt = captured["prompt"]
    # The closed-set vocabulary is stated once, but the ADMISSIBILITY line is state-specific
    # and must equal the guard's own answer — `ask_question` is not offered for a matched state.
    admissible_line = next(
        line for line in prompt.splitlines() if "admissible for the current state" in line
    )
    assert "finish_investigation" in admissible_line
    assert "gather_evidence" in admissible_line
    assert "ask_question" not in admissible_line, "an inadmissible action was offered to the model"
    assert captured["schema"] == PlanProposal.model_json_schema()
