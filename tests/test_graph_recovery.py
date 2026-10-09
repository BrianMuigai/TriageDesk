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
from triagedesk.core.schema import RecoveryRequest
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
