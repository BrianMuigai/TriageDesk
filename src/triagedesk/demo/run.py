"""The one-command demo runner (DOCS-01, D-01, D-07).

``uv run triagedesk demo`` runs the whole storyboard OFFLINE on the bundled synthetic
fixtures: each beat runs through the REAL graph via the shipped seams
(``evals.case.load_cases`` + ``evals.tools.build_tools`` + ``graph.build.build_graph``),
every owned tool call is printed (name + inputs -> outputs) so the tool path is visible
on screen (D-07), the run pauses at the approval gate, and the gated commit is shown
REFUSING without a named nurse.

Like ``evals.runner.run_eval``, the runner installs the store through the ONE seam context
manager (``mcp.server.store_seam``), which restores the borrowed default on exit, so the
offline path launches no borrowed ``npx mcp-sqlite`` subprocess (D-01, T-05-10). No value is
hard-coded: every printed colour, citation and tool name is returned by the real graph
(T-05-01). This is packaging, not new capability — no scoring logic lives here.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from triagedesk.durable import approval_decision, invoke_graph, run_to_gate
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.runner import _capture, _checkpointer
from triagedesk.evals.tools import ToolMap, build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import CHECKPOINTS_DB_PATH, build_graph
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

    Delegates to the ONE decision builder (``durable.approval_decision``), so the demo
    and ``triagedesk resume`` cannot drift on the token shape. ``final_colour`` is filled
    by the graph from the scored colour for an ``approve`` decision.
    """
    return approval_decision("approve", approver=DEMO_NURSE_NAME, role=DEMO_NURSE_ROLE)


def _resume_for(beat: Beat) -> dict[str, Any]:
    """The gate resume value for *beat*: the refusal beat refuses, the rest approve.

    Both decisions come from the ONE builder (``durable.approval_decision``), so the
    demo, the eval runner and ``triagedesk resume`` cannot drift on the token shape
    (T-05-03, T-05-11, IN-05 — DRY).
    """
    if beat.name == REFUSAL_BEAT:
        return approval_decision("dismiss")
    return _named_approval()


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
    result, payload = await invoke_graph(graph, initial, config, _resume_for(beat))
    rows_added = len(await store.read_queue_rows()) - rows_before
    _print_outcome(case, payload, result, rows_added=rows_added)
    print()


async def _run_durable(
    selected: list[Beat],
    cases: Mapping[str, CaseSpec],
    *,
    offline: bool,
    store: Store | None,
    db_path: str | Path | None,
) -> int:
    """Run ONE beat to the durable approval gate, print the resume command, and exit.

    The two-command storyboard's first half (D6-11): resolve the store seam, run the case
    over ``checkpoints.db`` to the gate, print the content-derived ``thread_id`` and the
    exact ``resume`` command, then exit WITHOUT resuming — a single in-process pause would
    not demonstrate persistence. Returns 2 when anything but exactly one beat is selected,
    because the durable thread is content-addressed (two beats on one case would collide).
    """
    if len(selected) != 1:
        print(
            f"--durable runs exactly one beat at a time; selected {len(selected)}. "
            "Select one with --beat <name>.",
            file=sys.stderr,
        )
        return 2

    beat = selected[0]
    case = cases[beat.case]
    resume_db = Path(db_path) if db_path is not None else CHECKPOINTS_DB_PATH
    # ``--durable`` installs its store through the ONE seam context manager
    # (``mcp.server.store_seam``): with nothing injected it resolves the borrowed default
    # through the ONE resolver, so the queue row still survives the restart (D6-14, D-13,
    # SOLID: D). A test injects the in-memory double so no borrowed subprocess is launched;
    # a second resolver here would be a duplicate seam.
    tools = build_tools(case, offline=offline, recorder=UsageRecorder())
    async with server_module.store_seam(store):
        paused = await run_to_gate(
            _traced_tools(tools, _print_tool_call),
            raw_note=case.note,
            case=case.case,
            db_path=resume_db,
            previous_case=case.previous_case,
        )

    if paused.existed:
        print(
            "[durable] a durable thread already exists for this case; "
            f"remove {resume_db} to replay the story."
        )
        return 0
    if not paused.paused:
        print("[durable] the case reached a terminal without pausing at the approval gate.")
        return 0
    print(f"[durable] thread_id={paused.thread_id} paused at approval gate")
    print(
        f"[durable] resume: uv run triagedesk resume --thread-id {paused.thread_id} "
        f"--decision approve --approver NAME --role ROLE --db {resume_db}"
    )
    return 0


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
    durable: bool = False,
    db_path: str | Path | None = None,
) -> int:
    """Run the selected storyboard beats offline through the real graph; return 0.

    ``store`` injects the store the gated commit resolves (default: a fresh in-memory
    store, so no borrowed subprocess is launched) — the ONE seam the demo regression test
    uses (SOLID: D). ``offline`` defaults to True, so the bare ``uv run triagedesk demo``
    runs from a clean clone with no model pulled (D-01). The store is installed through the
    ONE seam context manager (``mcp.server.store_seam``), which restores the borrowed default
    on exit, so the offline path never falls through to the borrowed ``npx mcp-sqlite``
    subprocess (T-05-10).

    ``durable`` swaps the in-memory saver for ``checkpointed_graph`` over *db_path*
    (``checkpoints.db`` by default) and runs exactly ONE beat to the gate, printing the
    resume command instead of resuming (D6-08, D6-11). The default path is unchanged.
    """
    storyboard = load_storyboard()
    try:
        selected = _select(storyboard, beats)
    except KeyError as exc:
        print(f"unknown beat(s): {exc.args[0]}", file=sys.stderr)
        return 2

    cases = {case.id: case for case in load_cases(fixture_dir)}
    if durable:
        return await _run_durable(
            selected, cases, offline=offline, store=store, db_path=db_path
        )
    async with server_module.store_seam(store, default=InMemoryStore) as resolved_store:
        for index, beat in enumerate(selected, start=1):
            await _run_beat(
                beat,
                cases[beat.case],
                offline=offline,
                index=index,
                total=len(selected),
                store=resolved_store,
            )
    return 0


__all__ = [
    "DEFAULT_FIXTURE_DIR",
    "STORYBOARD_PATH",
    "Beat",
    "list_beats",
    "load_storyboard",
    "run_demo",
]
