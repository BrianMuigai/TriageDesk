"""Build the graph's injected tool mapping for the eval harness (D-13, SOLID: D/L).

The graph depends on an injected ``name -> async callable`` mapping, never on a concrete
adapter. This module builds that mapping for the harness: the real owned tools are called
IN-PROCESS (``triagedesk.mcp.server``), so the gate under test is the shipped gate, not a
copy (SOLID: L). Only the model is stubbed, and only in offline mode: ``normalize_case``
returns the fixture's golden extraction with zero usage while every other tool — the
deterministic matcher, scorer, recheck and the real gated commit — runs for real.

:func:`build_tools` serves the harness (a ``CaseSpec``); :func:`offline_tools` is the
harness-free entry point for a caller that already has a structured ``CaseInput`` and no
fixture (the desk submission and the durable resume). Both delegate to the ONE private
``_tool_map`` core, so the mapping is assembled in exactly one place (DRY).

In real mode ``normalize_case`` drives the real owned server, whose module-level
``extract`` is wrapped (via :func:`recorded_extract_seam`) with the run's usage sink, so
token cost is read from the one model response (D-08, Pitfall 16).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from triagedesk.core.schema import CaseInput, ExtractionResult, PriorityResult
from triagedesk.evals.case import CaseSpec, FaultInjection
from triagedesk.evals.usage import UsageRecorder, recorded_extract
from triagedesk.mcp import server as server_module

# The graph's injected tool interface: a name -> async callable taking a single mapping
# (the same shape ``graph.nodes.ToolMap`` declares).
ToolMap = Mapping[str, Callable[[Mapping[str, Any]], Awaitable[Any]]]


@contextmanager
def recorded_extract_seam(recorder: UsageRecorder) -> Iterator[None]:
    """Patch the owned server's ``extract`` with the recorder for the duration of a run.

    The owned server imported ``extract`` into its own namespace; this swaps that name for
    a wrapper carrying *recorder*'s usage sink, then restores it. So the real
    ``normalize_case`` tool reports its token cost without a second model call, and the
    patch never leaks past the run (T-04-09).

    ``extract`` is an imported re-export in the server module (not a declared attribute),
    so the swap is applied through the module namespace dict — the same object attribute
    lookup uses — keeping the patch explicit without a private-name import.
    """
    namespace = vars(server_module)
    original = namespace["extract"]
    namespace["extract"] = recorded_extract(recorder)
    try:
        yield
    finally:
        namespace["extract"] = original


def _injected_normalize(
    inner: Callable[[Mapping[str, Any]], Awaitable[Any]], inject: FaultInjection
) -> Callable[[Mapping[str, Any]], Awaitable[Any]]:
    """Wrap a ``normalize_case`` callable with the declared E-12 fault (Pitfall 13).

    The wrapper is built fresh inside :func:`build_tools` for one case and one run, so
    the injected fault is torn down with that case's tool mapping and can never leak into
    another case (T-04-09). When declared, the FIRST call raises a timeout and the NEXT
    returns unparseable text, so the graph's bounded retry is exhausted and its
    deterministic fallback is exercised — the real retry path, not a simulation.
    """
    state = {"calls": 0}

    async def injected(inp: Mapping[str, Any]) -> Any:
        state["calls"] += 1
        if inject.tool_timeout and state["calls"] == 1:
            raise TimeoutError("injected tool timeout")
        if inject.malformed_json:
            return "{malformed json"
        return await inner(inp)

    return injected


def _tool_map(
    case: CaseInput,
    *,
    offline: bool,
    inject: FaultInjection | None,
    recorder: UsageRecorder,
) -> dict[str, Any]:
    """Build the injected tool mapping from a resolved ``CaseInput`` and fault — the ONE core.

    Both :func:`build_tools` (the harness path, ``CaseSpec``-shaped) and :func:`offline_tools`
    (the harness-free path, ``CaseInput``-shaped) delegate here, so the seven-tool mapping is
    assembled in exactly one place (DRY). Every tool is the real owned tool called in-process;
    only ``normalize_case`` is stubbed in offline mode (returning *case*'s own extraction with
    no model call). The injected ``recorder`` is unused here directly — the caller patches the
    server's ``extract`` with it via :func:`recorded_extract_seam` — but it is threaded through
    so the mapping is built from the same per-run recorder the seam uses.

    When ``inject`` is declared, the ``normalize_case`` callable is wrapped with the fault
    (T-04-09) so the graph's real bounded retry and deterministic fallback run.
    """
    del recorder  # the seam is applied by the caller; kept in the signature for symmetry

    async def normalize_case(inp: Mapping[str, Any]) -> Any:
        # The graph's own ``parse_tool_result`` is the ONE parser of a tool payload, so
        # this callable returns the server's result unchanged and lets the graph coerce it.
        if offline:
            return ExtractionResult(case=case, matched_discriminator_ids=[])
        return await server_module.normalize_case(str(inp["raw_note"]))

    normalize = (
        normalize_case
        if inject is None
        else _injected_normalize(normalize_case, inject)
    )

    async def match_discriminators(inp: Mapping[str, Any]) -> Any:
        return await server_module.match_discriminators(str(inp["complaint"]))

    async def score_priority(inp: Mapping[str, Any]) -> Any:
        parsed = CaseInput.model_validate(inp["case"])
        return await server_module.score_priority(
            parsed, inp.get("matched_discriminator_ids")
        )

    async def raise_recheck_flag(inp: Mapping[str, Any]) -> Any:
        previous = CaseInput.model_validate(inp["previous"])
        current = CaseInput.model_validate(inp["current"])
        return await server_module.raise_recheck_flag(previous, current)

    async def assess_confidence(inp: Mapping[str, Any]) -> Any:
        return await server_module.assess_confidence(
            list(inp.get("matched_ids") or []),
            bool(inp.get("no_match")),
            PriorityResult.model_validate(inp["priority"]),
        )

    async def retrieve_evidence(inp: Mapping[str, Any]) -> Any:
        return await server_module.retrieve_evidence(str(inp["complaint"]))

    async def commit_priority(inp: Mapping[str, Any]) -> Any:
        case = CaseInput.model_validate(inp["case"])
        return await server_module.commit_priority(
            str(inp["case_id"]), str(inp["colour"]), case, inp.get("approval_token")
        )

    return {
        "normalize_case": normalize,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "assess_confidence": assess_confidence,
        "retrieve_evidence": retrieve_evidence,
        "commit_priority": commit_priority,
    }


def build_tools(case: CaseSpec, *, offline: bool, recorder: UsageRecorder) -> dict[str, Any]:
    """Build the harness tool mapping for one case (D-13).

    A one-line delegate to the shared :func:`_tool_map` core: it unpacks the harness
    ``CaseSpec`` into its ``CaseInput`` and declared fault, so the harness path and the
    harness-free :func:`offline_tools` path cannot drift (DRY).
    """
    return _tool_map(case.case, offline=offline, inject=case.inject, recorder=recorder)


def offline_tools(case: CaseInput, recorder: UsageRecorder) -> dict[str, Any]:
    """Build the offline tool mapping from a bare ``CaseInput`` — the harness-free entry point.

    The entry point for a caller that has a structured case but no evaluation fixture (the desk
    submission and the durable resume): it needs no ``CaseSpec`` and no declared terminal, so it
    fabricates none. The mapping is the same seven real owned tools as :func:`build_tools` —
    model stubbed offline with *case*'s own extraction and no injected fault — so the caller sees
    the shipped gate, never a copy (SOLID: L).
    """
    return _tool_map(case, offline=True, inject=None, recorder=recorder)


__all__ = ["ToolMap", "build_tools", "offline_tools", "recorded_extract_seam"]
