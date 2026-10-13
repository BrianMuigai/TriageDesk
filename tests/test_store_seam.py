"""Focused unit proof for the ONE store-seam installer (``mcp.server.store_seam``).

The store-seam context manager replaced three hand-written copies of the
resolve-or-inject -> ``set_store`` -> ``try/finally set_store(None)`` ceremony
(``evals/runner.py`` and the two ``demo/run.py`` sites). These tests pin its contract
directly: it resolves once, installs the resolved store through the ONE write path,
yields that same instance so a caller reads what it installed, and always clears the
seam to ``None`` on exit — including on exception — so an injected offline double can
never leak into a later call (D-13).
"""

from __future__ import annotations

import pytest

from triagedesk.mcp import server as server_module
from triagedesk.store.memory import InMemoryStore


async def test_injected_store_is_installed_and_yielded(
    injected_store: InMemoryStore,
) -> None:
    """An injected store is installed, yielded, and the ONE resolver agrees it is the seam."""
    async with server_module.store_seam(injected_store) as resolved:
        assert resolved is injected_store
        assert await server_module.resolve_store() is injected_store


async def test_default_factory_supplies_the_store_when_none_is_injected() -> None:
    """With no injected store, the caller's ``default`` factory is used and yielded."""
    made = InMemoryStore()
    async with server_module.store_seam(default=lambda: made) as resolved:
        assert resolved is made
        assert await server_module.resolve_store() is made


async def test_resolver_is_consulted_when_neither_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With neither a store nor a factory, the ONE resolver supplies the store."""
    sentinel = InMemoryStore()

    async def fake_resolve() -> InMemoryStore:
        return sentinel

    monkeypatch.setattr(server_module, "resolve_store", fake_resolve)
    async with server_module.store_seam() as resolved:
        assert resolved is sentinel


async def test_seam_is_cleared_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception inside the block still restores the borrowed default (the seam is ``None``)."""
    sentinel = InMemoryStore()

    async def fake_default() -> InMemoryStore:
        return sentinel

    monkeypatch.setattr(server_module, "default_store", fake_default)

    injected = InMemoryStore()
    with pytest.raises(RuntimeError):
        async with server_module.store_seam(injected):
            raise RuntimeError("boom")

    # The seam was reset to ``None`` (not left holding ``injected``), so the ONE resolver
    # now falls through to the borrowed default factory — proven by the sentinel identity,
    # which can only be reached when ``_store`` is ``None``.
    assert await server_module.resolve_store() is sentinel
