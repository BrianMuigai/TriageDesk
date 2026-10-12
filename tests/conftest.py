"""Shared offline test doubles (Plan 03-02, D-13).

ONE in-memory ``Store`` double implements the full protocol, so every offline
server/tool-contract test runs without launching the borrowed SQLite subprocess
(DRY — one fake, not one per test module). An autouse fixture injects it into the
owned server's store seam (``mcp.server.set_store``), so the real commit path is
exercised against the fake rather than the borrowed default.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from triagedesk.core import confidence, matcher, recheck, retrieval, scorer
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    CommitResult,
    ExtractionResult,
    PriorityResult,
)
from triagedesk.mcp import server as server_module
from triagedesk.observability.spans import set_sink
from triagedesk.store.memory import InMemoryStore
from triagedesk.store.queue import commit_to_queue

# -------------------------------------------------------------------- AST guards
# Shared by the purity/safety guard suites so the import-scanning logic lives in
# exactly one place (DRY). The model-provider SDK roots that must NEVER appear on the
# graph path (ORCH-02), declared once.
NON_LOCAL_MODEL_PROVIDERS = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "cohere",
        "mistralai",
        "azure",
        "boto3",
        "vertexai",
    }
)


def imported_modules(source: str) -> list[str]:
    """Return the absolute dotted module names imported by *source* (the ONE AST helper).

    Relative imports (``from ..llm import x``) are deliberately excluded: the guard
    suites that use this helper scan external package roots, and the ``core/`` purity
    guard has its own relative-aware resolver (``tests/test_purity.py``).
    """
    modules: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


class RecordingStore(InMemoryStore):
    """The shared package store double plus the test-only queue-call recorder (DRY).

    A thin subclass of the ONE in-memory store (``triagedesk.store.memory``): it adds only
    the ``calls`` list the refusal tests assert on — a refused commit must touch no store —
    so the harness and the suite share a single implementation (CONVENTIONS §1).
    """

    def __init__(self, memory: Any = None) -> None:
        super().__init__(memory)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _note(self, name: str, *args: object) -> None:
        self.calls.append((name, args))


@pytest.fixture
def memory_store() -> RecordingStore:
    """A fresh in-memory Store for a test (also injected into the server seam)."""
    return RecordingStore()


@pytest.fixture(autouse=True)
def injected_store(memory_store: RecordingStore) -> Iterator[RecordingStore]:
    """Inject the shared fake into the owned server's store seam (D-13).

    Autouse so EVERY offline server/tool test exercises the injectable seam; the
    fixture yields the store so a test can assert what was (or was not) written.
    """
    server_module.set_store(memory_store)
    try:
        yield memory_store
    finally:
        server_module.set_store(None)


@pytest.fixture(autouse=True)
def _spans_sink(tmp_path: Path) -> Iterator[None]:
    """Redirect the ONE span sink to ``tmp_path`` for every test (Pitfall 5).

    Autouse so no test writes ``spans.jsonl`` into the repository root; the sibling of
    ``injected_store`` (a second process-wide seam redirect). Production keeps the
    repo-root default (D7-02).
    """
    set_sink(tmp_path / "spans.jsonl")
    try:
        yield
    finally:
        set_sink(None)


# --------------------------------------------------------------------------- graph
# The complete adult case the default fake extraction returns — all scored TEWS
# parameters are present, so the priority is cited and no recovery edge fires.
COMPLETE_CASE = CaseInput(
    age_years=40,
    mobility="walking",
    avpu="alert",
    respiratory_rate=24,
    heart_rate=118,
    systolic_bp=108,
    temperature_c=38.9,
    trauma=False,
    complaint="central chest pain",
)


def build_graph_tools(
    *,
    case: CaseInput | None = None,
    normalize_impl: Callable[[dict[str, Any]], Any] | None = None,
    retrieve_impl: Callable[[dict[str, Any]], Any] | None = None,
    calls: list[tuple[str, Any]] | None = None,
    writes: list[Any] | None = None,
    store: InMemoryStore | None = None,
) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Build the offline graph tool mapping — the ONE fake for the graph proof suites.

    The graph depends on an injected ``name -> async callable`` mapping (D-13), so
    the proof suites supply these fakes and never launch the MCP subprocess or the
    model. Kept here (not per test module) so the fake is defined once (DRY).
    ``normalize_impl`` overrides the extraction and ``retrieve_impl`` overrides the
    retrieval (the channel-isolation proof needs a differing ``evidence`` value);
    ``store``, when given, receives the real idempotent queue write.
    """
    calls = calls if calls is not None else []
    writes = writes if writes is not None else []
    resolved_case = case if case is not None else COMPLETE_CASE

    async def normalize_case(inp: dict[str, Any]) -> Any:
        calls.append(("normalize_case", inp))
        if normalize_impl is not None:
            return normalize_impl(inp)
        return ExtractionResult(case=resolved_case, matched_discriminator_ids=[])

    async def match_discriminators(inp: dict[str, Any]) -> Any:
        calls.append(("match_discriminators", inp))
        return matcher.match_discriminators(inp["complaint"])

    async def score_priority(inp: dict[str, Any]) -> Any:
        calls.append(("score_priority", inp))
        parsed = CaseInput.model_validate(inp["case"])
        return scorer.score_priority(parsed, inp.get("matched_discriminator_ids"))

    async def raise_recheck_flag(inp: dict[str, Any]) -> Any:
        calls.append(("raise_recheck_flag", inp))
        previous = CaseInput.model_validate(inp["previous"])
        current = CaseInput.model_validate(inp["current"])
        return recheck.compare_vitals(previous, current)

    async def assess_confidence(inp: dict[str, Any]) -> Any:
        calls.append(("assess_confidence", inp))
        return confidence.assess(
            list(inp.get("matched_ids") or []),
            bool(inp.get("no_match")),
            PriorityResult.model_validate(inp["priority"]),
        )

    async def retrieve_evidence(inp: dict[str, Any]) -> Any:
        calls.append(("retrieve_evidence", inp))
        if retrieve_impl is not None:
            return retrieve_impl(inp)
        return retrieval.retrieve(str(inp["complaint"]))

    async def commit_priority(inp: dict[str, Any]) -> CommitResult:
        calls.append(("commit_priority", inp))
        token = inp.get("approval_token")
        if token is None:
            return CommitResult(refused=True, reason="no approval token supplied")
        try:
            parsed = ApprovalToken.model_validate(token)
        except ValidationError:
            return CommitResult(refused=True, reason="approval token is malformed")
        # Mirror the real gate's refusal ORDER (``mcp/server.py::commit_priority``): a
        # well-formed ``dismiss`` is refused before any store access, so the eval's
        # unapproved resume (``durable.approval_decision("dismiss")``) never writes a row.
        if parsed.decision == "dismiss":
            return CommitResult(
                refused=True, reason="clinician dismissed the priority; refusing to commit"
            )
        writes.append(inp)
        if store is not None:
            await commit_to_queue(
                store,
                case_id=inp["case_id"],
                colour=inp["colour"],
                content=CaseInput.model_validate(inp["case"]),
            )
        return CommitResult(committed=store is not None, reason="accepted")

    return {
        "normalize_case": normalize_case,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "assess_confidence": assess_confidence,
        "retrieve_evidence": retrieve_evidence,
        "commit_priority": commit_priority,
    }
