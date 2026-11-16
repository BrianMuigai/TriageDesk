"""The default store is opened ONCE per process per event loop (D-10, nurse stress test S4).

Resolving the borrowed store per tool call launched ``npx mcp-sqlite@1.0.9`` and ensured the
schema on every audited call — a measured ~2.6-3.1 s floor on ``match_discriminators`` and on
``score_priority``, which is pure integer arithmetic. The cache is keyed on
``(db_path, running event loop)`` for the same reason ``llm.client._async_client`` is
(commit ``4a24c8f``): the borrowed store holds async subprocess transports bound to the loop
that created them, so a second loop must get a fresh store.

Every test patches ``open_borrowed_store`` (or injects a store), so no test launches a
subprocess or touches the network.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from triagedesk.mcp import server as server_module
from triagedesk.store import (
    DOMAIN_DB_PATH,
    borrowed,
    default_store,
    reset_default_store,
)
from triagedesk.store.memory import InMemoryStore


@pytest.fixture(autouse=True)
def _empty_default_store_cache() -> None:
    """Start and end every test with no cached default store (the ONE invalidation path)."""
    reset_default_store()
    yield
    reset_default_store()


def _patch_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> list[Path]:
    """Patch the borrowed factory to record its paths and return a fresh in-memory store."""
    opened: list[Path] = []

    async def fake_open(db_path: Path) -> InMemoryStore:
        opened.append(db_path)
        return InMemoryStore()

    monkeypatch.setattr(borrowed, "open_borrowed_store", fake_open)
    return opened


async def test_one_loop_resolves_the_same_store_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two ``default_store`` calls on one loop return the SAME object and open once (S4)."""
    opened = _patch_factory(monkeypatch)
    db = tmp_path / "triage.db"

    first = await default_store(db)
    second = await default_store(db)

    assert first is second, "the default store was rebuilt on the second resolve"
    assert opened == [db], "the borrowed store was launched more than once on one loop"


async def test_a_different_db_path_gets_a_new_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cache is keyed on the db path too, so a different domain db rebuilds."""
    opened = _patch_factory(monkeypatch)
    first_db = tmp_path / "one.db"
    second_db = tmp_path / "two.db"

    first = await default_store(first_db)
    second = await default_store(second_db)

    assert first is not second
    assert opened == [first_db, second_db]


def test_a_second_event_loop_gets_a_new_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second ``asyncio.run`` gets its own store — the loop-bound transport rule (4a24c8f)."""
    opened = _patch_factory(monkeypatch)
    db = Path("/tmp/opencode/second-loop.db")

    first = asyncio.run(default_store(db))
    second = asyncio.run(default_store(db))

    assert first is not second, "a dead loop's store leaked into a new event loop"
    assert opened == [db, db], "the new loop did not reopen the borrowed store"


async def test_an_injected_store_wins_and_is_never_cached(
    injected_store: InMemoryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seam is consulted first, and the injected store never enters the default cache."""
    opened = _patch_factory(monkeypatch)

    assert await server_module.resolve_store() is injected_store
    assert await server_module.resolve_store() is injected_store
    assert opened == [], "an injected store still reached the borrowed factory"

    # Clearing the seam falls through to the borrowed default — NOT the store that was injected.
    server_module.set_store(None)
    default = await server_module.resolve_store()
    assert default is not injected_store
    assert opened == [DOMAIN_DB_PATH], "clearing the seam did not resolve the borrowed default"
    # ... and that default is now cached, so the next resolve does not reopen it.
    assert await server_module.resolve_store() is default
    assert opened == [DOMAIN_DB_PATH]


async def test_reset_drops_the_cached_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``reset_default_store`` is the ONE invalidation path: the next resolve reopens."""
    opened = _patch_factory(monkeypatch)
    db = tmp_path / "triage.db"

    first = await default_store(db)
    reset_default_store()
    second = await default_store(db)

    assert first is not second, "reset left the previous store cached"
    assert opened == [db, db]
