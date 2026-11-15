"""Live clarification on every surface: the opt-in adapter seam, end to end (quick 261115-jlr).

The ONE offline proof module for the live question path. Nothing here reaches Ollama: the
MODEL is stubbed (``extract_async`` returns the fixture's case, ``propose_plan_async`` always
asks), while the planner guard, the shipped ``langchain.mcp`` adapter, the owned server's
``request_clarification`` and the elicitation round-trip are all real — the seam loads the tool
through ``MCPAdapter`` in process, so the pause is a genuine ``mcp_elicitation`` interrupt.

The safety claims under test: an answer is an observation re-matched by the deterministic
matcher (the colour is ``score_priority``'s), an answer never answers the approval gate, a
decline or a blank answer records nothing, a non-alias answer resolves nothing, no run waits on
a non-interactive stdin, and the offline planner never asks.
"""

from __future__ import annotations

import io
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from conftest import async_return
from test_plan_audit import _always_proposes
from triagedesk.core import coverage
from triagedesk.core.schema import ExtractionResult, InterruptType, PlanAction
from triagedesk.demo.run import run_demo
from triagedesk.durable import approval_decision, invoke_graph
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import build_graph, in_memory_checkpointer
from triagedesk.mcp import server as server_module
from triagedesk.mcp.adapter import with_live_clarification
from triagedesk.mcp.elicitation import (
    ACCEPT,
    CLARIFICATION_REQUEST_KEY,
    DECLINE,
    answer_field,
    answer_prompts,
    form_requests,
    is_elicitation,
    resume_with_answers,
)
from triagedesk.store.memory import InMemoryStore

pytestmark = pytest.mark.filterwarnings(
    "ignore::langchain_core._api.beta_decorator.LangChainBetaWarning"
)

CASES_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"

# An answer that NAMES the finding (an alias in the discriminator data), and one that only
# states a number — the matcher is alias text, so only the first resolves anything.
ANSWER = "low glucose, 2.1 mmol/L"
NON_ALIAS = "glucose 2.1"

APPROVER = "Nurse Test"
ROLE = "triage nurse"


def _e09() -> CaseSpec:
    """The declared-failure fixture, loaded through the ONE loader (never re-typed)."""
    return next(case for case in load_cases(CASES_DIR) if case.id == "E-09")


def _stub_model_that_asks(monkeypatch: pytest.MonkeyPatch, case: CaseSpec) -> None:
    """Stub the MODEL only: extraction returns the case, the planner always proposes a question.

    The shipped guard in ``server_module.plan_next_step`` stays real, so whether the proposal
    is admitted is decided by the system under test, not by this stub.
    """
    monkeypatch.setattr(
        server_module,
        "extract_async",
        async_return(ExtractionResult(case=case.case, matched_discriminator_ids=[])),
    )
    monkeypatch.setattr(
        server_module, "propose_plan_async", _always_proposes(PlanAction.ASK_QUESTION)
    )


def _policy(answers: list[str], *, approve: bool = True) -> tuple[Any, list[dict[str, Any]]]:
    """A respond policy that records every payload; answers questions, then the gate."""
    seen: list[dict[str, Any]] = []

    def respond(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        seen.append(dict(payload))
        if is_elicitation(payload):
            return resume_with_answers(payload, answers)
        if not approve:
            return None
        return approval_decision("approve", approver=APPROVER, role=ROLE)

    return respond, seen


async def _run_e09(answers: list[str], *, approve: bool = True) -> tuple[Any, list[dict]]:
    """Run E-09 online through the seam over an in-memory checkpointer."""
    case = _e09()
    tools = with_live_clarification(
        build_tools(case, offline=False, recorder=UsageRecorder())
    )
    graph = build_graph(tools, checkpointer=in_memory_checkpointer())
    config = {"configurable": {"thread_id": f"live-{'-'.join(answers) or 'none'}-{approve}"}}
    respond, seen = _policy(answers, approve=approve)
    result, _first = await invoke_graph(
        graph, {"raw_note": case.note, "case": case.case}, config, {}, respond=respond
    )
    return result, seen


# ---------------------------------------------------------------- the seam itself


def test_the_seam_replaces_exactly_one_tool_and_mutates_nothing() -> None:
    """SOLID I: only ``request_clarification`` changes; every other callable is the same object."""
    tools = build_tools(_e09(), offline=False, recorder=UsageRecorder())
    before = dict(tools)

    wrapped = with_live_clarification(tools)

    assert wrapped is not tools
    assert set(wrapped) == set(tools)
    assert wrapped["request_clarification"] is not tools["request_clarification"]
    for name, fn in tools.items():
        if name != "request_clarification":
            assert wrapped[name] is fn, name
    assert tools == before, "the seam mutated the input mapping"


def _payload(fields: list[str]) -> dict[str, Any]:
    """A minimal elicitation payload with one form request over *fields*."""
    return {
        "type": InterruptType.ELICITATION.value,
        "tool_name": "request_clarification",
        "requests": [
            {
                "key": CLARIFICATION_REQUEST_KEY,
                "mode": "form",
                "message": "m",
                "requested_schema": {
                    "properties": {name: {"type": "string"} for name in fields}
                },
            }
        ],
    }


def test_resume_with_answers_accepts_in_question_order() -> None:
    """Answers pair with the form fields in order; the request key addresses them."""
    value = resume_with_answers(_payload(["q1", "q2"]), ["first", "second"])
    response = value["responses"][CLARIFICATION_REQUEST_KEY]
    assert response["action"] == ACCEPT
    assert response["content"] == {"q1": "first", "q2": "second"}


@pytest.mark.parametrize("supplied", [[], ["", "   "]])
def test_resume_with_answers_declines_when_nothing_was_answered(supplied: list[str]) -> None:
    """No answer, or only blanks, is the absence of an observation: decline (ELICIT-03/08)."""
    value = resume_with_answers(_payload(["q1", "q2"]), supplied)
    assert value == {"responses": {CLARIFICATION_REQUEST_KEY: {"action": DECLINE}}}


def test_resume_with_answers_declines_a_payload_with_no_form_request() -> None:
    """A payload with nothing answerable declines under the ONE request key."""
    value = resume_with_answers({"type": InterruptType.ELICITATION.value}, ["anything"])
    assert value == {"responses": {CLARIFICATION_REQUEST_KEY: {"action": DECLINE}}}


# ------------------------------------------------------- the graph over the seam


async def test_an_accepted_answer_is_rematched_scored_and_committed_only_by_approval(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """Pause in the real tool → answer → re-match → score_priority's colour → gated commit."""
    case = _e09()
    _stub_model_that_asks(monkeypatch, case)

    result, seen = await _run_e09([ANSWER])

    assert seen, "the run never paused"
    assert seen[0]["type"] == InterruptType.ELICITATION
    match = await server_module.match_discriminators(case.case.complaint, case.note)
    derived = {coverage.question_for(item) for item in match.candidates}
    prompts = answer_prompts(form_requests(seen[0])[0])
    assert prompts, "the server asked no question"
    assert set(prompts) <= derived, "a question did not come from the one question owner"
    assert any(payload.get("type") == InterruptType.APPROVAL for payload in seen[1:])

    assert result["nurse_answers"] == [ANSWER]
    answer_ids = (await server_module.match_discriminators(ANSWER, "")).matched_ids
    assert answer_ids and set(answer_ids) <= set(result["matched_ids"])
    scored = await server_module.score_priority(case.case, list(result["matched_ids"]))
    assert result["priority"].colour == scored.colour
    assert result["commit_result"].committed
    assert len(injected_store.rows) == 1


async def test_an_answer_never_answers_the_approval_gate(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """Answering the question leaves the gate paused for a named clinician; no row is written."""
    _stub_model_that_asks(monkeypatch, _e09())

    result, _seen = await _run_e09([ANSWER], approve=False)

    pending = result.get("__interrupt__")
    assert pending, "the run did not stop at the approval gate"
    assert dict(pending[0].value)["type"] == InterruptType.APPROVAL
    assert injected_store.rows == []


async def test_a_decline_records_nothing(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """A decline is not a negative finding: no answers, no ids, no queue row."""
    _stub_model_that_asks(monkeypatch, _e09())

    result, _seen = await _run_e09([])

    assert result["elicitation_outcome"] == "declined"
    assert not result.get("nurse_answers")
    assert list(result.get("matched_ids") or []) == []
    assert injected_store.rows == []


async def test_a_non_alias_answer_is_recorded_but_resolves_nothing(
    monkeypatch: pytest.MonkeyPatch, injected_store: Any
) -> None:
    """The alias-matching caveat, pinned: a bare number is recorded and matches no finding."""
    assert (await server_module.match_discriminators(NON_ALIAS, "")).matched_ids == []
    _stub_model_that_asks(monkeypatch, _e09())

    result, _seen = await _run_e09([NON_ALIAS])

    assert result["nurse_answers"] == [NON_ALIAS]
    assert list(result.get("matched_ids") or []) == []
    assert injected_store.rows == []


# ------------------------------------------------------------- the demo runner


async def test_the_online_clarify_beat_asks_and_acts_on_the_answer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The runner prints the server's question, the nurse's answer, the tool result, the commit."""
    case = _e09()
    _stub_model_that_asks(monkeypatch, case)
    # Read before the run: ``run_demo`` restores the store seam to its default on exit.
    match = await server_module.match_discriminators(case.case.complaint, case.note)
    store = InMemoryStore()

    assert await run_demo(beats=["clarify"], offline=False, answers=[ANSWER], store=store) == 0

    out = capsys.readouterr().out
    elicit = [line for line in out.splitlines() if line.startswith("[elicit]")]
    assert any(
        coverage.question_for(item) in line for item in match.candidates for line in elicit
    ), out
    assert f"[nurse] {answer_field(1)}: {ANSWER}" in out
    assert any(line.startswith("[tool] request_clarification") for line in out.splitlines())
    assert any("commit" in line and "committed" in line for line in out.splitlines()), out
    assert "SHOWN MISMATCH" not in out
    assert len(await store.read_queue_rows()) == 1


async def test_a_non_interactive_run_without_answers_declines_and_never_waits(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """pytest's stdin is not a TTY: no answers → one decline line, no commit, exit 0."""
    _stub_model_that_asks(monkeypatch, _e09())

    assert await run_demo(beats=["clarify"], offline=False, store=InMemoryStore()) == 0

    out = capsys.readouterr().out
    assert "[nurse] declined" in out
    assert "committed" not in out


class _TtyInput(io.StringIO):
    """A stdin double that claims to be an interactive terminal."""

    def isatty(self) -> bool:
        return True


async def test_an_interactive_terminal_is_asked(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Online + a TTY + no ``answers``: the presenter types the answer at the prompt."""
    _stub_model_that_asks(monkeypatch, _e09())
    monkeypatch.setattr("sys.stdin", _TtyInput(f"{ANSWER}\n\n\n"))
    store = InMemoryStore()

    assert await run_demo(beats=["clarify"], offline=False, store=store) == 0

    capsys.readouterr()
    assert len(await store.read_queue_rows()) == 1


async def test_the_offline_clarify_beat_never_asks(capsys: pytest.CaptureFixture[str]) -> None:
    """Offline the deterministic planner never asks, so no question is printed."""
    assert await run_demo(beats=["clarify"], store=InMemoryStore()) == 0

    assert "[elicit]" not in capsys.readouterr().out
