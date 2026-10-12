"""The ONE read-only replay projection (D7-09…D7-15, AGENT-04).

Replay answers the nurse-reviewer's question — *what did this past case do and decide?* —
by **reading stored data only**: the LangGraph checkpoint (the run's typed channels,
including ``approval``/``commit_result``/``handover``/``priority``) plus the audit records
and the local span stream, joined by the content-derived ``trace_id``. It reconstructs and
renders a view; it re-runs nothing.

Read-only is **structural and row-level** (D7-10, T-07-05). Structurally, this module
compiles no graph and constructs no tool mapping, so no code path here can reach a
write-capable tool such as the gated commit — there is simply no tool surface to call. At
the row level it adds **no queue row and no commit/audit record**: that is the ROADMAP
"replay cannot write" criterion. It never touches the model either (D7-09, D7-16): it reads
the recorded spans rather than producing new ones. The functions it does use are published
read seams: the saver's checkpoint-read method for the recorded state (deserialised with the
ONE explicit msgpack allowlist, T-07-06), the store's ``read_audit_records`` (D7-15), and
:func:`triagedesk.observability.spans.read_spans`.

**Declared caveat (WR-01).** The read is not read-only at the *SQLite* level. The
checkpointer's read method necessarily runs its own idempotent ``setup()`` (``PRAGMA
journal_mode=WAL`` + ``CREATE TABLE IF NOT EXISTS``), so reading a checkpoint may create or
touch ``checkpoints.db`` — including materialising it for an absent thread; and resolving
the default audit store runs the borrowed server's ``ensure_schema`` (idempotent DDL).
These are schema initialisations only, never a queue write or a commit. A truly
non-mutating open is not available through the existing seams (``AsyncSqliteSaver``'s
``from_conn_string`` offers no read-only/URI form and its read method always calls
``setup()``; the borrowed server owns its own connection), so the property is documented
rather than overstated.

It sits ABOVE ``store``/``durable`` and owes them nothing new: the audit store is resolved
through the SAME injectable store seam the commit path uses, so a test injects a double and
no borrowed subprocess is launched (T-07-07).

Error posture mirrors ``durable.DurableError``: an absent thread raises :class:`ReplayError`
naming the thread id and the checkpoint file, so the CLI reports it cleanly.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from triagedesk.graph.build import CHECKPOINTS_DB_PATH, _allowed_msgpack_modules
from triagedesk.mcp import server as server_module
from triagedesk.observability.spans import read_spans
from triagedesk.store import Store


class ReplayError(RuntimeError):
    """Raised when a case cannot be reconstructed for replay (no checkpoint for the thread)."""


async def read_recorded(thread_id: str, db_path: str | Path) -> dict[str, Any]:
    """Read a finished thread's recorded channels from the checkpoint — a pure read (D7-09).

    Opens the SQLite saver over *db_path*, gives it the ONE explicit state-type allowlist
    (never ``True``, T-07-06), and returns the latest checkpoint's ``channel_values`` for
    *thread_id*: the graph's own typed channels (``priority``, ``approval``,
    ``commit_result``, ``handover``, ``matched_ids``, ...), exactly as the run wrote them.
    No invoke, no resume, no graph. An absent thread raises :class:`ReplayError` naming the
    thread id and the file.

    The saver's read method runs its own idempotent ``setup()`` (``PRAGMA journal_mode=WAL``
    + ``CREATE TABLE IF NOT EXISTS``), so opening the checkpoint may create/touch
    ``checkpoints.db`` — but no application row is ever written (WR-01).
    """
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        saver.serde = JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_modules())
        tup = await saver.aget_tuple(config)
    if tup is None:
        raise ReplayError(f"no checkpoint for thread_id {thread_id} in {db_path}")
    return dict(tup.checkpoint["channel_values"])


def _render(
    thread_id: str,
    values: Mapping[str, Any],
    records: list[Any],
    spans: list[dict[str, Any]],
) -> str:
    """Render the reconstructed case view as text — from stored channels ONLY (D7-11).

    Every value is read back from the checkpoint or the audit/span stream; nothing is
    re-derived or re-scored. The view carries the suggested colour and target, the
    citations and triggered rules, the matched discriminator ids, the human decision and
    approver, the commit reason, and a one-line-per-span timeline (D7-11). Text only —
    no machine-readable flag (D6-15 posture).
    """
    priority = values.get("priority")
    approval = values.get("approval")
    approval = approval if isinstance(approval, Mapping) else {}
    commit_result = values.get("commit_result")
    matched_ids = list(values.get("matched_ids") or [])

    lines: list[str] = [
        f"replay — thread_id {thread_id} (read-only: no model, no graph)",
        f"  colour       : {priority.colour if priority is not None else None}",
        f"  target       : {priority.target if priority is not None else None}",
    ]
    citations = list(priority.citations) if priority is not None else []
    for citation in citations:
        lines.append(f"  citation     : {citation}")
    rules = list(priority.triggered_rules) if priority is not None else []
    for rule in rules:
        lines.append(f"  rule         : {rule.rule_id} ({rule.points} points)")
    lines.append(f"  matched ids  : {sorted(str(matched_id) for matched_id in matched_ids)}")
    lines.append(f"  decision     : {approval.get('decision')}")
    lines.append(f"  approved by  : {approval.get('approved_by')}")
    lines.append(f"  role         : {approval.get('role')}")
    lines.append(
        f"  commit       : {commit_result.reason if commit_result is not None else None}"
    )
    lines.append(f"  audit records: {len(records)}")
    lines.append("  span timeline:")
    for span_row in spans:
        lines.append(
            f"    {span_row.get('started')} -> {span_row.get('ended')} "
            f"{span_row.get('kind')} {span_row.get('name')} "
            f"({span_row.get('duration_ms')} ms)"
        )
    return "\n".join(lines)


async def replay_case(
    thread_id: str,
    *,
    db_path: str | Path = CHECKPOINTS_DB_PATH,
    store: Store | None = None,
    spans_path: Path | None = None,
) -> str:
    """Reconstruct a past case read-only and return the rendered text view (D7-09/D7-11).

    Reads the recorded channels with :func:`read_recorded`, filters the audit records to
    *thread_id*'s ``trace_id`` (resolving the audit store through the ONE injectable seam,
    ``mcp.server._resolve_store``, exactly as the durable demo does), reads that case's
    spans through the ONE span reader, and renders the view. It calls only read-only store
    methods, and because it holds no tool mapping it cannot write or re-commit (T-07-05,
    T-07-07).

    The checkpoint is read BEFORE the store is resolved, so an absent thread fails with
    :class:`ReplayError` without ever launching the borrowed store (mirroring the durable
    ``resume`` posture: an absent thread touches no store). Resolving first would open the
    borrowed SQLite MCP server and run its schema DDL on an error path — a write replay must
    never perform (T-07-07). The checkpoint *read* is likewise not file-level read-only (the
    saver's ``setup()`` runs its WAL/DDL — see :func:`read_recorded`); the guarantee this
    function makes is the row-level one: it adds no queue row and no audit record (WR-01).
    """
    values = await read_recorded(thread_id, db_path)
    resolved = store if store is not None else await server_module._resolve_store()
    records = [
        record
        for record in await resolved.read_audit_records()
        if record.trace_id == thread_id
    ]
    spans = read_spans(spans_path, trace_id=thread_id)
    return _render(thread_id, values, records, spans)


__all__ = ["ReplayError", "read_recorded", "replay_case"]
