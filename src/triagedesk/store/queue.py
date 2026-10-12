"""The ONE idempotent queue write (GATE-03, D-06).

Crash-safety is the idempotency key itself — ``case_id`` plus a content hash over the
immutable case input. A retry re-derives the same key, so an identical write is a no-op
and a second row cannot appear; a different ``colour``/``target`` for the same key
supersedes the row in place (D6-06). This does NOT rest on a transaction primitive: the
borrowed server exposes no transaction call, so any store-level transaction would be
belt-and-braces only (D-06, Pitfall 14).

The key deliberately covers the immutable case input only (the normalized ``CaseInput``
payload). The approval timestamp and every other volatile field are structurally
excluded (only ``IMMUTABLE_FIELDS`` are read), so a retry can never churn the key into
a duplicate, and an ``approve`` and an ``edit`` of the same case re-derive the SAME key
— so exactly one row exists per case (D6-04, Pitfall 14).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from triagedesk.core.hashing import hash_value
from triagedesk.core.schema import CaseInput
from triagedesk.store import QueueRow, Store

# The ONLY fields that may enter the idempotency key. Derived from the case schema so
# a future case field is covered automatically and cannot drift (DRY, D6-05). Every
# field is immutable case input; the scored outputs (``colour``, ``target``, …) are
# mutable details of one row and must never key it, or an ``edit`` would fork identity
# (D6-04). A volatile field (approval timestamp, wall-clock, actor) is structurally
# excluded by the same derivation (D-06, Pitfall 14).
IMMUTABLE_FIELDS: tuple[str, ...] = tuple(CaseInput.model_fields)


def content_hash(case_id: str, content: BaseModel | Mapping[str, Any]) -> str:
    """Hash ONLY immutable case content — the idempotency half of the key (D-06).

    Delegates to the ONE hashing path (``core.hashing.hash_value``): sorted-key compact
    JSON then sha256, so dict order and whitespace never churn the digest while a real
    case-input change does. The approval timestamp and every other volatile field are
    structurally excluded — only ``IMMUTABLE_FIELDS`` are read (derived from the schema),
    so an extra key (e.g. ``approved_at``) cannot influence the digest (Pitfall 14).
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
    """Idempotently place one case in the queue, superseding in place on an edit (GATE-03).

    Returns ``(row, created)``. The key covers the immutable case input, so an
    ``approve`` and an ``edit`` of the same case re-derive the SAME key. If a row with
    that (``case_id``, content hash) already exists, the caller's ``colour``/``target``
    supersede it IN PLACE — ``position`` and ``created_at`` are preserved and no second
    row is inserted (D6-04, D6-06). A crash-retry that re-derives the same key and
    colour is a no-op; the key is the whole crash-safety mechanism.
    """
    key = content_hash(case_id, content)
    existing = await store.read_queue_row(case_id, key)
    if existing is not None:
        if existing.colour != colour or existing.target != target:
            # Supersede in place: preserve position/created_at, update only the
            # mutable fields the clinician may have changed on an edit (D6-06).
            updated = existing.model_copy(update={"colour": colour, "target": target})
            await store.upsert_queue_row(updated)
            return updated, False
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
