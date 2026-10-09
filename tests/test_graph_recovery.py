"""Recovery + abstention proof suite (Plan 03-04, ORCH-04/ORCH-05, D-03).

Two safety branches are proven here, plus the bounded extraction retry:

1. a case missing a scored vital routes to the recovery terminal with the vital
   named and NO colour committed — the graph never guesses a value;
2. an out-of-scope (missing-age / paediatric) case routes to the abstention /
   escalation terminal with a reason and NO adult colour;
3. neither terminal calls ``commit_priority`` (no queue write on a non-scored path);
4. an invalid extraction is retried exactly once, then falls back to the
   deterministic, model-free path — never emitting an uncited or partial priority.

The tools are injected as fake async callables (``tests/conftest.py``), so the
suite never launches the MCP subprocess or the model.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from conftest import COMPLETE_CASE, build_graph_tools
from triagedesk.core.schema import CaseInput, RecoveryRequest
from triagedesk.graph import nodes as nodes_module
from triagedesk.graph.build import build_graph

NOTE = (
    "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, "
    "temperature 38.9, no trauma. Presenting with central chest pain."
)

# A complete adult case missing exactly one scored vital (respiratory_rate).
MISSING_VITAL_CASE = COMPLETE_CASE.model_copy(update={"respiratory_rate": None})

# A complete-vitals case with no adult age — the scorer must abstain (out of scope).
NO_AGE_CASE = COMPLETE_CASE.model_copy(update={"age_years": None, "complaint": "unwell child"})


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


# --------------------------------------------------------------- recovery terminal


async def test_missing_vital_routes_to_the_recovery_terminal() -> None:
    """A missing scored vital names the vital and commits no colour (ORCH-05, D-03)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=MISSING_VITAL_CASE, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE}, _config("recovery"))

    recovery = result.get("recovery")
    assert isinstance(recovery, RecoveryRequest), "did not reach the recovery terminal"
    assert "respiratory_rate" in recovery.missing_vitals, recovery.missing_vitals
    assert recovery.reason, "the recovery request must carry a re-measure reason"
    # No colour was committed, and the run never reached the gate or the commit.
    assert result.get("commit_result") is None
    assert not result.get("__interrupt__"), "a missing-vital case must not reach the gate"
    assert "commit_priority" not in [name for name, _ in calls]


# -------------------------------------------------------------- abstention terminal


async def test_out_of_scope_case_routes_to_the_abstention_terminal() -> None:
    """An out-of-scope case abstains with a reason and no adult colour (ORCH-05, D-03)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=NO_AGE_CASE, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE}, _config("abstain"))

    escalation = result.get("escalation")
    assert escalation is not None, "did not reach the abstention/escalation terminal"
    assert escalation.reason, "the escalation must explain why it abstained"
    # The priority carries no adult colour, and nothing was committed.
    priority = result.get("priority")
    assert priority is not None and priority.colour is None
    assert priority.out_of_scope is True
    assert result.get("commit_result") is None
    assert "commit_priority" not in [name for name, _ in calls]


async def test_neither_terminal_calls_commit_priority() -> None:
    """Both safe terminals stop without any queue-affecting write (ORCH-05, D-03)."""
    for case, thread in (
        (MISSING_VITAL_CASE, "no-commit-recovery"),
        (NO_AGE_CASE, "no-commit-escalate"),
    ):
        calls: list[tuple[str, Any]] = []
        tools = build_graph_tools(case=case, calls=calls)
        app = build_graph(tools, checkpointer=InMemorySaver())

        result = await app.ainvoke({"raw_note": NOTE}, _config(thread))

        assert "commit_priority" not in [name for name, _ in calls], thread
        assert result.get("commit_result") is None, thread


# ------------------------------------------------------- bounded retry + fallback


def _always_failing_normalize(inp: dict[str, Any]) -> Any:
    """An extraction that always raises — exercises the bounded retry."""
    raise RuntimeError("extraction tool unavailable")


async def test_bounded_extraction_retries_exactly_once() -> None:
    """A failing extraction is attempted exactly twice (one retry), then bounded (ORCH-04)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(normalize_impl=_always_failing_normalize, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    await app.ainvoke({"raw_note": NOTE}, _config("retry-once"))

    attempts = [name for name, _ in calls if name == "normalize_case"]
    assert len(attempts) == nodes_module._EXTRACTION_MAX_ATTEMPTS
    assert nodes_module._EXTRACTION_MAX_ATTEMPTS == 2, "the retry bound is one retry"


async def test_second_invalid_result_uses_the_fallback() -> None:
    """After the bounded retry, an already-parsed case is scored deterministically (ORCH-04)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(normalize_impl=_always_failing_normalize, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    # The caller already holds the structured case (the model is unavailable).
    result = await app.ainvoke(
        {"raw_note": NOTE, "case": COMPLETE_CASE}, _config("fallback-structured")
    )

    assert result.get("__interrupt__"), "the fallback did not reach the gate"
    payload = result["__interrupt__"][0].value
    assert payload["colour"] is not None
    assert payload["citations"], "the fallback emitted an uncited priority"
    assert len(payload["citations"]) == len(payload["triggered_rules"])


async def test_fallback_parses_a_structured_raw_note_without_the_model() -> None:
    """A structured JSON note is parsed deterministically when extraction fails (ORCH-04)."""
    tools = build_graph_tools(normalize_impl=_always_failing_normalize)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke(
        {"raw_note": COMPLETE_CASE.model_dump_json()}, _config("fallback-json")
    )

    assert result.get("__interrupt__"), "the JSON fallback did not reach the gate"


async def test_exhausted_retry_without_a_fallback_escalates() -> None:
    """A stubborn failure with no structured fallback terminates safely — no priority (ORCH-04)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(normalize_impl=_always_failing_normalize, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke({"raw_note": NOTE}, _config("fallback-escalate"))

    assert result.get("escalation") is not None, "did not reach a safe terminal"
    assert result.get("priority") is None, "no priority may be produced from a failed extraction"
    assert result.get("commit_result") is None
    assert "commit_priority" not in [name for name, _ in calls]


def test_deterministic_fallback_is_model_free() -> None:
    """The fallback never imports the model — it reads only typed structured fields (D-02)."""
    case = nodes_module._structured_case({"case": COMPLETE_CASE})
    assert case is not None and case.complaint == COMPLETE_CASE.complaint
    # A non-structured note has no recoverable fields, so the caller must escalate.
    assert nodes_module._structured_case({"raw_note": NOTE}) is None


def test_fallback_case_type_is_the_shared_contract() -> None:
    """The recovered fallback is the ONE ``CaseInput`` contract (D-14)."""
    parsed = nodes_module._structured_case({"raw_note": COMPLETE_CASE.model_dump_json()})
    assert isinstance(parsed, CaseInput)
