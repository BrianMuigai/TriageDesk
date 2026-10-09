"""The one-command demo runner (DOCS-01, D-01, D-07).

``uv run triagedesk demo`` runs the whole storyboard OFFLINE on the bundled synthetic
fixtures: each beat runs through the REAL graph via the shipped seams
(``evals.case.load_cases`` + ``evals.tools.build_tools`` + ``graph.build.build_graph``),
every owned tool call is printed (name + inputs -> outputs) so the tool path is visible
on screen (D-07), the run pauses at the approval gate, and the gated commit is shown
REFUSING without a named nurse.

Like ``evals.runner.run_eval``, the runner injects the in-memory store into the owned
server's seam (``mcp.server.set_store``, restored in a ``finally``), so the offline path
launches no borrowed ``npx mcp-sqlite`` subprocess (D-01, T-05-10). No value is
hard-coded: every printed colour, citation and tool name is returned by the real graph
(T-05-01). This is packaging, not new capability — no scoring logic lives here.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from langgraph.types import Command
from pydantic import BaseModel

from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.runner import _capture, _checkpointer
from triagedesk.evals.tools import ToolMap, build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import build_graph
from triagedesk.mcp import server as server_module
from triagedesk.store import Store
from triagedesk.store.memory import InMemoryStore

# The demo manifest and its default fixture directory, named once so the CLI and the
# runner agree (DRY). The fixture directory is the same bundled synthetic cases the eval
# harness uses.
STORYBOARD_PATH = "demo/storyboard.yaml"
DEFAULT_FIXTURE_DIR = "evals/cases"

# The synthetic, named approver the demo uses for the beats that commit. A demo identity
# only — no real person, no credential (T-05-02).
DEMO_NURSE_NAME = "Nurse Demo"
DEMO_NURSE_ROLE = "triage nurse"

# The one beat that demonstrates the gate refusing without a named nurse (D-07).
REFUSAL_BEAT = "refusal"

# The unapproved resume value, declared ONCE (the literal is never scattered): a
# ``dismiss`` naming no approver, so the gated commit refuses it and no queue row is
# written (T-05-03, T-05-11).
_UNAPPROVED_RESUME: dict[str, Any] = {"decision": "dismiss"}


class Beat(BaseModel):
    """One storyboard beat: a name, the bundled eval case id it runs, and a label."""

    name: str
    case: str
    label: str


def load_storyboard(path: str | Path = STORYBOARD_PATH) -> list[Beat]:
    """Load the beat manifest (a YAML list of ``{name, case, label}``) in declared order."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [Beat.model_validate(entry) for entry in raw]


def list_beats(path: str | Path = STORYBOARD_PATH) -> int:
    """Print the beat names and labels from the manifest; return the exit code."""
    for beat in load_storyboard(path):
        print(f"{beat.name}\t{beat.label}")
    return 0


def _render(value: Any) -> str:
    """Render a tool input/output for the screen (the ONE demo serialiser)."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, default=str, sort_keys=True)


def _traced_tools(
    tools: ToolMap, on_call: Callable[[str, Mapping[str, Any], Any], None]
) -> dict[str, Any]:
    """Wrap every tool callable so each call is visible on screen (D-07).

    The wrapper prints the call AFTER the real tool returns and BEFORE it hands the value
    back, so what is shown is exactly what the graph receives — never a staged copy.
    """

    def traced(
        name: str, fn: Callable[[Mapping[str, Any]], Awaitable[Any]]
    ) -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
        async def wrapper(inp: Mapping[str, Any]) -> Any:
            output = await fn(inp)
            on_call(name, inp, output)
            return output

        return wrapper

    return {name: traced(name, fn) for name, fn in tools.items()}


def _print_tool_call(name: str, inputs: Mapping[str, Any], outputs: Any) -> None:
    """Print one owned tool call: ``[tool] <name> <inputs> -> <outputs>`` (D-07)."""
    print(f"[tool] {name} {_render(dict(inputs))} -> {_render(outputs)}")


def _named_approval() -> dict[str, Any]:
    """A well-formed named approval — the demo's synthetic nurse (T-05-11).

    Carries every field ``ApprovalToken`` requires, including ``approved_at``, so the
    gated commit validates the token and writes exactly one queue row. ``final_colour``
    is filled by the graph from the scored colour for an ``approve`` decision.
    """
    return {
        "decision": "approve",
        "approved_by": DEMO_NURSE_NAME,
        "role": DEMO_NURSE_ROLE,
        "approved_at": datetime.now(UTC).isoformat(),
    }


def _resume_for(beat: Beat) -> dict[str, Any]:
    """The gate resume value for *beat*: the refusal beat refuses, the rest approve."""
    return _UNAPPROVED_RESUME if beat.name == REFUSAL_BEAT else _named_approval()


def _print_outcome(
    case: CaseSpec, payload: dict[str, Any] | None, result: Any, *, rows_added: int
) -> None:
    """Print the beat's sourced outcome — every value read from the graph (T-05-01)."""
    captured = _capture(result, payload)
    priority = result.get("priority")
    if payload is not None:
        target = payload.get("target")
    else:
        target = priority.target if priority is not None else None

    print("--- outcome ---")
    print(f"  colour       : {captured['colour']}")
    print(f"  target       : {target}")
    print(f"  matched ids  : {sorted(captured['matched_ids'])}")
    for citation in captured["citations"]:
        print(f"  citation     : {citation}")
    commit = result.get("commit_result")
    if commit is not None:
        print(f"  commit       : {commit.reason}")
    if commit is not None and commit.refused:
        # The demo's climax (D-07): the gated commit refused and wrote NOTHING. The row
        # delta is read from the store, so the refusal is shown, not asserted by fiat.
        print(f"  GATE REFUSED : no queue row written (rows added this beat: {rows_added})")
    second_look = result.get("second_look")
    if second_look is not None:
        print(f"  second look  : {second_look.model_dump_json()}")
    handover = result.get("handover")
    if handover is not None:
        print(f"  handover card: {handover.model_dump_json()}")
    if case.declared_failure:
        measured = captured["colour"]
        verdict = "SHOWN MISMATCH" if measured != case.expected else "match"
        print(f"  DECLARED     : {case.expected}")
        print(f"  MEASURED     : {measured} ({verdict})")


async def _run_beat(
    beat: Beat, case: CaseSpec, *, offline: bool, index: int, total: int, store: Store
) -> None:
    """Run one beat through the real graph, tracing tools and resuming past the gate."""
    print("=" * 72)
    print(f"BEAT {index}/{total}: {beat.name} — {beat.label}")
    print(f"case: {case.id} ({case.description})")
    print("=" * 72)

    recorder = UsageRecorder()
    tools = build_tools(case, offline=offline, recorder=recorder)
    graph = build_graph(_traced_tools(tools, _print_tool_call), checkpointer=_checkpointer())
    config = {"configurable": {"thread_id": f"demo-{beat.name}-{index}"}}
    initial: dict[str, Any] = {"raw_note": case.note, "case": case.case}
    if case.previous_case is not None:
        initial["previous_case"] = case.previous_case

    rows_before = len(await store.read_queue_rows())
    result = await graph.ainvoke(initial, config)
    payload: dict[str, Any] | None = None
    if result.get("__interrupt__"):
        payload = dict(result["__interrupt__"][0].value)
        result = await graph.ainvoke(Command(resume=_resume_for(beat)), config)
    rows_added = len(await store.read_queue_rows()) - rows_before
    _print_outcome(case, payload, result, rows_added=rows_added)
    print()


def _select(storyboard: list[Beat], names: list[str] | None) -> list[Beat]:
    """Filter the storyboard to *names* (declared order preserved), or return it whole."""
    if not names:
        return storyboard
    wanted = set(names)
    unknown = wanted - {beat.name for beat in storyboard}
    if unknown:
        raise KeyError(", ".join(sorted(unknown)))
    return [beat for beat in storyboard if beat.name in wanted]


async def run_demo(
    *,
    beats: list[str] | None = None,
    offline: bool = True,
    fixture_dir: str | Path = DEFAULT_FIXTURE_DIR,
    store: Store | None = None,
) -> int:
    """Run the selected storyboard beats offline through the real graph; return 0.

    ``store`` injects the store the gated commit resolves (default: a fresh in-memory
    store, so no borrowed subprocess is launched) — the ONE seam the demo regression test
    uses (SOLID: D). ``offline`` defaults to True, so the bare ``uv run triagedesk demo``
    runs from a clean clone with no model pulled (D-01). The store is injected through
    ``mcp.server.set_store`` and restored in a ``finally``, so the offline path never
    falls through to the borrowed ``npx mcp-sqlite`` subprocess (T-05-10).
    """
    storyboard = load_storyboard()
    try:
        selected = _select(storyboard, beats)
    except KeyError as exc:
        print(f"unknown beat(s): {exc.args[0]}", file=sys.stderr)
        return 2

    cases = {case.id: case for case in load_cases(fixture_dir)}
    resolved_store = store if store is not None else InMemoryStore()
    server_module.set_store(resolved_store)
    try:
        for index, beat in enumerate(selected, start=1):
            await _run_beat(
                beat,
                cases[beat.case],
                offline=offline,
                index=index,
                total=len(selected),
                store=resolved_store,
            )
    finally:
        server_module.set_store(None)
    return 0


__all__ = [
    "DEFAULT_FIXTURE_DIR",
    "STORYBOARD_PATH",
    "Beat",
    "list_beats",
    "load_storyboard",
    "run_demo",
]
