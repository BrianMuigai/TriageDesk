"""Serial-vitals recheck proof suite (Plan 03-04, GATE-04, D-07, M-4).

The recheck is a *second look*, never a second classification:

1. deteriorating serial vitals set a flag with the before/after values in the graph
   state and in the handover card;
2. the queue position is unchanged across the recheck — the flag never reorders;
3. a stable follow-up yields no flag and an improvement is not reported as a
   deterioration;
4. the recheck node never calls ``commit_priority`` and never sets a colour.

The tools are injected as fake async callables (``tests/conftest.py``); the store is
the shared in-memory double, so no borrowed subprocess is launched.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from conftest import build_graph_tools
from triagedesk.core.schema import CaseInput, RecheckFlag
from triagedesk.graph.build import build_graph, run_case

NOTE = (
    "40 year old man, walking, alert. RR 26, HR 122, systolic BP 96, "
    "temperature 37.0, no trauma. Presenting with central chest pain."
)

# The earlier serial case (normal-ish vitals) and its deteriorated follow-up.
BASELINE = CaseInput(
    age_years=40,
    mobility="walking",
    respiratory_rate=16,
    heart_rate=80,
    systolic_bp=118,
    temperature_c=37.0,
    avpu="alert",
    trauma=False,
    complaint="central chest pain",
)
DETERIORATED = BASELINE.model_copy(
    update={"systolic_bp": 96, "respiratory_rate": 26, "heart_rate": 122}
)
# RR 16 -> 18 and HR 80 -> 84 stay within the same band: no deterioration.
STABLE = BASELINE.model_copy(update={"respiratory_rate": 18, "heart_rate": 84})


def _config(thread: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread}}


def _approval() -> dict[str, Any]:
    """A well-formed named-clinician approval resume value (GATE-02)."""
    return {
        "decision": "approve",
        "approved_by": "Dr A. Nurse",
        "role": "triage clinician",
        "approved_at": "2026-10-09T16:00:00Z",
    }


async def test_deterioration_sets_the_flag_in_state_and_handover_card() -> None:
    """A deterioration surfaces the before/after second look in state and card (GATE-04)."""
    tools = build_graph_tools(case=DETERIORATED)
    app = build_graph(tools, checkpointer=InMemorySaver())
    config = _config("recheck-flag")

    paused = await app.ainvoke({"raw_note": NOTE, "previous_case": BASELINE}, config)

    flag = paused["second_look"]
    assert isinstance(flag, RecheckFlag) and flag.flag is True
    sbp = next(change for change in flag.changes if change.parameter == "systolic_bp")
    assert sbp.before == 118 and sbp.after == 96

    done = await app.ainvoke(Command(resume=_approval()), config)
    assert done["handover"].second_look is not None
    assert done["handover"].second_look.flag is True


async def test_recheck_does_not_change_the_queue_position(memory_store) -> None:
    """The second look never reorders: the queue position is identical across it (GATE-04, M-4)."""
    tools = build_graph_tools(case=DETERIORATED, store=memory_store)
    app = build_graph(tools, checkpointer=InMemorySaver())
    config = _config("recheck-queue")

    paused = await app.ainvoke({"raw_note": NOTE, "previous_case": BASELINE}, config)

    # The recheck ran (the flag is set) yet touched no queue: no row exists.
    assert paused["second_look"].flag is True
    assert memory_store.rows == [], "the recheck wrote to the queue on its own"

    done = await app.ainvoke(Command(resume=_approval()), config)

    assert done["commit_result"].committed is True
    assert [row.position for row in memory_store.rows] == [1]


async def test_stable_follow_up_raises_no_flag() -> None:
    """A stable follow-up yields no second-look flag (GATE-04)."""
    tools = build_graph_tools(case=STABLE)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke(
        {"raw_note": NOTE, "previous_case": BASELINE}, _config("recheck-stable")
    )

    assert result["second_look"].flag is False
    assert result["second_look"].deteriorations == []


async def test_improvement_is_not_a_deterioration() -> None:
    """A recovering patient is never reported as deteriorating (GATE-04)."""
    tools = build_graph_tools(case=BASELINE)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke(
        {"raw_note": NOTE, "previous_case": DETERIORATED}, _config("recheck-improved")
    )

    flag = result["second_look"]
    assert "systolic_bp" not in flag.deteriorations
    assert "heart_rate" not in flag.deteriorations
    assert flag.flag is False


async def test_recheck_never_commits_and_never_sets_a_colour() -> None:
    """The recheck node calls no commit and the flag carries no colour (D-07, M-4)."""
    calls: list[tuple[str, Any]] = []
    tools = build_graph_tools(case=DETERIORATED, calls=calls)
    app = build_graph(tools, checkpointer=InMemorySaver())

    result = await app.ainvoke(
        {"raw_note": NOTE, "previous_case": BASELINE}, _config("recheck-no-commit")
    )

    assert "commit_priority" not in [name for name, _ in calls]
    assert "colour" not in RecheckFlag.model_fields
    assert not hasattr(result["second_look"], "colour")


async def test_run_case_threads_the_previous_case_into_the_state() -> None:
    """``run_case(..., previous_case=...)`` seeds the serial input path (GATE-04, D-07).

    The recheck runs only for a scored case; the missing-vital case here routes to a
    safe terminal before the gate, so the threading of ``previous_case`` is asserted
    directly on the returned state without needing a checkpointer.
    """
    tools = build_graph_tools(case=BASELINE.model_copy(update={"respiratory_rate": None}))

    result = await run_case(NOTE, tools=tools, previous_case=BASELINE)

    assert result.get("previous_case") == BASELINE
