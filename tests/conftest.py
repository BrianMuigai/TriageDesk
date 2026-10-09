"""Shared offline test doubles (Plan 03-02, D-13).

ONE in-memory ``Store`` double implements the full protocol, so every offline
server/tool-contract test runs without launching the borrowed SQLite subprocess
(DRY — one fake, not one per test module). An autouse fixture injects it into the
owned server's store seam (``mcp.server.set_store``), so the real commit path is
exercised against the fake rather than the borrowed default.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from triagedesk.mcp import server as server_module
from triagedesk.store import CaseRow, QueueRow


class InMemoryStore:
    """A minimal in-memory :class:`~triagedesk.store.Store` — the ONE protocol double.

    Records every protocol call in ``calls`` so a test can assert the refusal path
    touched no store, and holds ``rows``/``cases`` for committed state.
    """

    def __init__(self) -> None:
        self.rows: list[QueueRow] = []
        self.cases: dict[str, CaseRow] = {}
        self.calls: list[tuple[str, tuple[object, ...]]] = []

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
