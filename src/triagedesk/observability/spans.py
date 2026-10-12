"""The ONE local span writer (D7-01, D7-02, D7-04).

Every span the triage run emits — a tool call from the ``@audited`` interceptor, a graph
node from the composition-root wrapper, a model call from the ``llm/client`` boundary —
is written here and nowhere else (D7-04; DRY, the same rule that gives the audit exactly
one append path). A span is ONE JSON object per line in ONE local, append-only file;
nothing here reaches the network, so the sink is a purely local artefact (D7-02).

The single JSON line carries exactly these keys, and no clinical text ever enters them
(D7-08)::

    trace_id, span_id, parent_id, kind, name, started, ended, duration_ms, attributes

``kind`` is ``"tool"``, ``"node"`` or ``"model"`` (D7-07). ``attributes`` is a small,
caller-supplied mapping of ids/timings/counts — never a complaint, prompt or completion.
The sink path is named ONCE (:data:`SPANS_PATH`) and is overridable for tests via
:func:`set_sink`, mirroring the store seam ``mcp.server.set_store`` (SOLID: D). The
matching reader (:func:`read_spans`) lives beside the writer so the line format has
exactly ONE home.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from triagedesk.observability.context import (
    current_parent_id,
    current_trace_id,
    pop_span,
    push_span,
)

# The ONE default sink path, named once (D7-02). Append-only JSONL; gitignored.
SPANS_PATH = Path("spans.jsonl")

# The injectable sink override — a module global (not a contextvar) so a test fixture's
# redirection is process-wide and deterministic, mirroring ``mcp.server._store``.
_sink: Path | None = None


def set_sink(path: Path | None) -> None:
    """Inject (or clear) the span sink path (D7-02).

    Tests pass a ``tmp_path`` file so the suite never writes ``spans.jsonl`` into the
    repository; passing ``None`` restores the :data:`SPANS_PATH` default (SOLID: D).
    """
    global _sink
    _sink = path


def emit_span(
    *,
    trace_id: str,
    span_id: str,
    parent_id: str | None,
    kind: str,
    name: str,
    started: str,
    ended: str,
    duration_ms: float,
    attributes: Mapping[str, Any] | None = None,
) -> None:
    """Append ONE span as a single JSON line to the local sink (D7-02, D7-04).

    The ONLY function that writes a span line. It resolves the sink from :func:`set_sink`
    or :data:`SPANS_PATH`, then opens it append-only — a local, synchronous file write
    with no network path. The keys are exactly those documented in the module docstring,
    serialised with ``sort_keys`` so a line is stable for diffing and replay (D7-07).
    """
    line: dict[str, Any] = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_id": parent_id,
        "kind": kind,
        "name": name,
        "started": started,
        "ended": ended,
        "duration_ms": duration_ms,
        "attributes": dict(attributes) if attributes is not None else {},
    }
    path = _sink if _sink is not None else SPANS_PATH
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, default=str, sort_keys=True) + "\n")


def read_spans(
    path: Path | None = None, *, trace_id: str | None = None
) -> list[dict[str, Any]]:
    """Read the local span stream :func:`emit_span` wrote (the ONE span reader, D7-15).

    Colocated with the writer so the JSONL format lives in exactly ONE module (DRY,
    CONVENTIONS §1): the encoding in :func:`emit_span` and the decoding here can never
    drift. It reads *path* when given, else the injected sink, else :data:`SPANS_PATH`;
    parses each non-empty line as one JSON object; and returns the rows in file order.
    When *trace_id* is given the result is filtered to that case's trace, so the shared
    stream projects one case's timeline (D7-05). A missing file is an empty stream, never
    an error — a case that predates tracing simply has no spans. Read-only: nothing here
    writes, so a reader can never perturb the sink.
    """
    resolved = path if path is not None else (_sink if _sink is not None else SPANS_PATH)
    if not resolved.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw_line in resolved.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        if trace_id is None or row.get("trace_id") == trace_id:
            rows.append(row)
    return rows


@contextmanager
def span(
    kind: str, name: str, attributes: dict[str, Any] | None = None
) -> Iterator[dict[str, Any]]:
    """Time a block and emit ONE span for it on exit — the ONE emit seam (D7-04).

    On entry it resolves the parent from the open-span stack, mints a fresh ``span_id``,
    captures the start time, and pushes the span id; on exit it pops the span and calls
    :func:`emit_span` once with the elapsed duration. The SAME ``attributes`` object the
    caller passed is emitted, so a caller may mutate it inside the block (the model span
    records its token counts this way) and have the mutation captured on exit.
    """
    parent_id = current_parent_id()
    span_id = uuid.uuid4().hex
    started = datetime.now(UTC).isoformat()
    started_perf = time.perf_counter()
    token = push_span(span_id)
    resolved: dict[str, Any] = attributes if attributes is not None else {}
    try:
        yield resolved
    finally:
        pop_span(token)
        emit_span(
            trace_id=current_trace_id(),
            span_id=span_id,
            parent_id=parent_id,
            kind=kind,
            name=name,
            started=started,
            ended=datetime.now(UTC).isoformat(),
            duration_ms=(time.perf_counter() - started_perf) * 1000.0,
            attributes=resolved,
        )


__all__ = ["SPANS_PATH", "emit_span", "read_spans", "set_sink", "span"]
