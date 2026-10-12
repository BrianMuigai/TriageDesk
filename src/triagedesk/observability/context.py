"""Per-task span/trace context (``contextvars``) for the local span writer (D7-05, D7-07).

This module owns the TWO pieces of per-task state the observability surface needs: the
current ``trace_id`` (content-derived, bound by the graph's node wrapper) and the
open-span stack used to resolve a child span's ``parent_id``. Both live in
``contextvars`` rather than module globals, so a span opened inside one asyncio task
cannot leak into a concurrent run (07-RESEARCH Pattern 1). The writer
(:mod:`triagedesk.observability.spans`) reads this state through the accessors here —
there is exactly ONE home for it (DRY, CONVENTIONS §1).

Nothing here reads the environment or reaches the network: the module is stdlib only, so
``graph/`` may import it without tripping the safety-spine AST guards (D7-04).
"""

from __future__ import annotations

import contextvars

# The content-derived trace root for the current task (empty until a node binds it).
_trace: contextvars.ContextVar[str] = contextvars.ContextVar(
    "triagedesk_trace_id", default=""
)

# The open-span stack; the top of the stack is the current span's parent (D7-07).
_span_stack: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
    "triagedesk_span_stack", default=()
)


def bind_trace(trace_id: str) -> None:
    """Bind *trace_id* as the current task's trace root (D7-05).

    Called by the graph's node wrapper at the ONE content derivation, so every span in a
    case's run (node, tool, model) shares the same content-derived trace id.
    """
    _trace.set(trace_id)


def current_trace_id() -> str:
    """Return the current task's trace id, or ``""`` when none is bound."""
    return _trace.get()


def push_span(span_id: str) -> contextvars.Token[tuple[str, ...]]:
    """Push *span_id* onto the open-span stack; return the reset token (LIFO)."""
    return _span_stack.set(_span_stack.get() + (span_id,))


def pop_span(token: contextvars.Token[tuple[str, ...]]) -> None:
    """Restore the open-span stack to the state *token* captured."""
    _span_stack.reset(token)


def current_parent_id() -> str | None:
    """Return the innermost open span's id (the parent), or ``None`` at the root."""
    stack = _span_stack.get()
    return stack[-1] if stack else None


__all__ = [
    "bind_trace",
    "current_parent_id",
    "current_trace_id",
    "pop_span",
    "push_span",
]
