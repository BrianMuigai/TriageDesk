"""ONE long-lived event loop owned by the desk server (Plan 13-01, JC-1).

The desk surface runs every checkpoint-touching coroutine on ONE loop, owned by a dedicated
daemon thread, for the server's whole lifetime. A request therefore never builds and
destroys a loop (the old ``asyncio.run`` per POST), and an ``await`` inside one coroutine
leaves the loop free to run another — which is what makes a precompute or a waiting-room
read possible while a submit is awaiting the model.

The loop is private: callers hand it coroutines through :meth:`DeskLoop.run` (blocking) or
:meth:`DeskLoop.submit` (fire-and-forget). After :meth:`DeskLoop.stop` both raise, so a
teardown bug surfaces instead of silently hanging a request on a closed loop.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any, TypeVar

_T = TypeVar("_T")


class DeskLoop:
    """A private event loop running on its own daemon thread.

    ``start`` blocks until the loop is actually running, so the first request can never
    race the loop's startup. ``stop`` is idempotent and joins the thread; it is fail-closed
    afterwards rather than leaving callers waiting on a loop that will never run again.
    """

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run, name="triagedesk-desk-loop", daemon=True
        )
        self._started = threading.Event()
        self._stopped = False

    @property
    def ident(self) -> int | None:
        """The owning thread's ident (``None`` before the thread starts)."""
        return self._thread.ident

    def _run(self) -> None:
        """Own the loop on this thread for its whole life (the thread's entry point)."""
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon(self._started.set)
        self.loop.run_forever()

    def start(self) -> None:
        """Start the loop thread and block until the loop is running."""
        if self._thread.is_alive():
            return
        self._thread.start()
        self._started.wait()

    def _check_running(self) -> None:
        """Raise when the loop is stopped or its thread is gone (fail-closed)."""
        if self._stopped or not self._thread.is_alive():
            raise RuntimeError("the desk event loop is stopped")

    def run(self, coro: Coroutine[Any, Any, _T]) -> _T:
        """Run *coro* on the owned loop and return its result (blocks the caller)."""
        self._check_running()
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def submit(self, coro: Coroutine[Any, Any, _T]) -> Future[_T]:
        """Schedule *coro* on the owned loop without waiting (fire-and-forget work)."""
        self._check_running()
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        """Stop and join the loop thread, then close the loop (idempotent)."""
        if self._stopped:
            return
        self._stopped = True
        if self._thread.is_alive():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self._thread.join()
        self.loop.close()


__all__ = ["DeskLoop"]
