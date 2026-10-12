"""Local observability surface: ONE span writer + the per-task trace/span context (D7-02).

The package barrel re-exports the span writer and the trace context so the three emit
sites (``mcp/server``, ``graph/build``, ``llm/client``) import from ONE place (DRY,
CONVENTIONS §1). It deliberately does NOT import :mod:`triagedesk.observability.offline`:
that module reads the tracer environment, and the graph path must never pull it — ``graph/``
may not read the environment (D7-04, T-07-04).
"""

from triagedesk.observability.context import bind_trace, current_trace_id
from triagedesk.observability.spans import SPANS_PATH, emit_span, set_sink, span

__all__ = [
    "SPANS_PATH",
    "bind_trace",
    "current_trace_id",
    "emit_span",
    "set_sink",
    "span",
]
