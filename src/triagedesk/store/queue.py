"""The ONE idempotent queue write (GATE-03, D-06).

Crash-safety is the idempotency key itself — ``case_id`` plus a content hash over
IMMUTABLE case content. A retry re-derives the same key, so the upsert is a no-op and a
second row cannot appear. This does NOT rest on a transaction primitive: the borrowed
server exposes no transaction call, so any store-level transaction would be
belt-and-braces only (D-06, Pitfall 14).

The key deliberately covers immutable case content only. The approval timestamp and
every other volatile field are structurally excluded (only ``IMMUTABLE_FIELDS`` are
read), so a retry can never churn the key into a duplicate (Pitfall 14).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from triagedesk.core.hashing import hash_value
from triagedesk.store import QueueRow, Store

# The ONLY fields that may enter the idempotency key. Every one is immutable case
# content; a volatile field (the approval timestamp, wall-clock, actor) must never
# appear here or a retry would churn the key into a duplicate (D-06, Pitfall 14).
IMMUTABLE_FIELDS: tuple[str, ...] = (
    "colour",
    "target",
    "triggered_rules",
    "citations",
    "used_vitals",
)


def content_hash(case_id: str, content: BaseModel | Mapping[str, Any]) -> str:
    """Hash ONLY immutable case content — the idempotency half of the key (D-06).

    Delegates to the ONE hashing path (``core.hashing.hash_value``): sorted-key compact
    JSON then sha256, so dict order and whitespace never churn the digest while a real
    scored-field change does. The approval timestamp and every other volatile field are
    structurally excluded — only ``IMMUTABLE_FIELDS`` are read, so an extra key (e.g.
    ``approved_at``) cannot influence the digest (Pitfall 14).
    """
    plain = content.model_dump(mode="json") if isinstance(content, BaseModel) else dict(content)
    immutable = {field: plain[field] for field in IMMUTABLE_FIELDS if field in plain}
    return hash_value({"case_id": case_id, **immutable})


async def commit_to_queue(
    store: Store,
    *,
    case_id: str,
    colour: str,
    content: BaseModel | Mapping[str, Any],
    target: str | None = None,
) -> tuple[QueueRow, bool]:
    """Idempotently place one case in the queue (GATE-03, D-06).

    Returns ``(row, created)``. If a row with the same (``case_id``, content hash) key
    already exists it is returned UNCHANGED and nothing is inserted — the idempotency
    key is the crash-safety mechanism, so a crash-retry that re-derives the same key is
    a no-op and a second row cannot appear.
    """
    key = content_hash(case_id, content)
    existing = await store.read_queue_row(case_id, key)
    if existing is not None:
        return existing, False
    row = QueueRow(
        case_id=case_id,
        content_hash=key,
        colour=colour,
        target=target,
        position=await store.next_position(),
        created_at=datetime.now(UTC),
    )
    await store.upsert_queue_row(row)
    return row, True


__all__ = ["IMMUTABLE_FIELDS", "commit_to_queue", "content_hash"]
