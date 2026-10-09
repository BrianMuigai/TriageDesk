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
from typing import Any

import pytest
from pydantic import ValidationError

from triagedesk.core import matcher, recheck, scorer
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    CommitResult,
    ExtractionResult,
)
from triagedesk.mcp import server as server_module
from triagedesk.store import CaseRow, QueueRow
from triagedesk.store.audit import GENESIS, AuditRecord
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


class _Memory:
    """The shared backing state of the in-memory store — the "database" a restart reopens.

    Holding the state in a separate object (rather than on the store handle) lets
    ``InMemoryStore.restart()`` hand back a *fresh handle over the same data*, which is
    how the audit suite simulates a process restart without a real SQLite file (M-6).
    """

    def __init__(self) -> None:
        self.rows: list[QueueRow] = []
        self.cases: dict[str, CaseRow] = {}
        self.audit_records: list[AuditRecord] = []
        self.chain_head: str = GENESIS


class InMemoryStore:
    """A minimal in-memory :class:`~triagedesk.store.Store` — the ONE protocol double.

    Records every queue/case protocol call in ``calls`` so a test can assert the refusal
    path touched no store, and holds ``rows``/``cases`` for committed state. The audit
    seam (``audit_records``/``chain_head``) is stored alongside, so the fake satisfies
    the whole protocol — including the audit half — in one place (DRY, D-13).
    """

    def __init__(self, memory: _Memory | None = None) -> None:
        self._memory = memory if memory is not None else _Memory()
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def restart(self) -> InMemoryStore:
        """Return a fresh handle over the same backing state — a simulated restart (M-6)."""
        return InMemoryStore(self._memory)

    @property
    def rows(self) -> list[QueueRow]:
        return self._memory.rows

    @property
    def cases(self) -> dict[str, CaseRow]:
        return self._memory.cases

    @property
    def audit_records(self) -> list[AuditRecord]:
        return self._memory.audit_records

    @property
    def chain_head(self) -> str:
        return self._memory.chain_head

    async def ensure_schema(self) -> None:
        self.calls.append(("ensure_schema", ()))

    async def read_queue_row(self, case_id: str, content_hash: str) -> QueueRow | None:
        self.calls.append(("read_queue_row", (case_id, content_hash)))
        for row in self.rows:
            if row.case_id == case_id and row.content_hash == content_hash:
                return row
        return None

    async def next_position(self) -> int:
        self.calls.append(("next_position", ()))
        return len(self.rows) + 1

    async def upsert_queue_row(self, row: QueueRow) -> None:
        self.calls.append(("upsert_queue_row", (row.case_id, row.content_hash)))
        key = (row.case_id, row.content_hash)
        if all((existing.case_id, existing.content_hash) != key for existing in self.rows):
            self.rows.append(row)

    async def read_case(self, case_id: str) -> CaseRow | None:
        self.calls.append(("read_case", (case_id,)))
        return self.cases.get(case_id)

    async def read_queue_rows(self) -> list[QueueRow]:
        return list(self.rows)

    async def read_chain_head(self) -> str:
        return self._memory.chain_head

    async def write_chain_head(self, head: str) -> None:
        self._memory.chain_head = head

    async def append_audit_record(self, record: AuditRecord) -> None:
        self._memory.audit_records.append(record)

    async def read_audit_records(self) -> list[AuditRecord]:
        return list(self._memory.audit_records)


@pytest.fixture
def memory_store() -> InMemoryStore:
    """A fresh in-memory Store for a test (also injected into the server seam)."""
    return InMemoryStore()


@pytest.fixture(autouse=True)
def injected_store(memory_store: InMemoryStore) -> Iterator[InMemoryStore]:
    """Inject the shared fake into the owned server's store seam (D-13).

    Autouse so EVERY offline server/tool test exercises the injectable seam; the
    fixture yields the store so a test can assert what was (or was not) written.
    """
    server_module.set_store(memory_store)
    try:
        yield memory_store
    finally:
        server_module.set_store(None)


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
    calls: list[tuple[str, Any]] | None = None,
    writes: list[Any] | None = None,
    store: InMemoryStore | None = None,
) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Build the offline graph tool mapping — the ONE fake for the graph proof suites.

    The graph depends on an injected ``name -> async callable`` mapping (D-13), so
    the proof suites supply these fakes and never launch the MCP subprocess or the
    model. Kept here (not per test module) so the fake is defined once (DRY).
    ``normalize_impl`` overrides the extraction; ``store``, when given, receives the
    real idempotent queue write.
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

    async def commit_priority(inp: dict[str, Any]) -> CommitResult:
        calls.append(("commit_priority", inp))
        token = inp.get("approval_token")
        if token is None:
            return CommitResult(refused=True, reason="no approval token supplied")
        try:
            ApprovalToken.model_validate(token)
        except ValidationError:
            return CommitResult(refused=True, reason="approval token is malformed")
        writes.append(inp)
        if store is not None:
            await commit_to_queue(
                store,
                case_id=inp["case_id"],
                colour=inp["colour"],
                content={"colour": inp["colour"]},
            )
        return CommitResult(committed=store is not None, reason="accepted")

    return {
        "normalize_case": normalize_case,
        "match_discriminators": match_discriminators,
        "score_priority": score_priority,
        "raise_recheck_flag": raise_recheck_flag,
        "commit_priority": commit_priority,
    }
