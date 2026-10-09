"""Canonical hashing for the pinned clinical substrate (SAFE-04, D-17).

One helper hashes a value's **normalised** form — never raw file bytes — so that
dictionary key reordering and comment/whitespace edits do **not** churn a digest
while a real content change does (01-RESEARCH Open Question #4). Prompt
templates, the loaded rule substrate and the tool schemas are all hashed through
this single path, so every audit record (Phase 3) names the same, reproducible
version identifiers (D-17).

Pure module: stdlib + ``pydantic`` only; it imports nothing from ``llm`` /
``mcp`` / ``store`` (D-13).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

ALGORITHM = "sha256"


def _to_plain(value: Any) -> Any:
    """Recursively reduce *value* to a plain, JSON-serialisable structure.

    Pydantic models are dumped in JSON mode; mappings and sequences are walked so
    that nested models and values are normalised too. This is the ONE traversal —
    every entry point below funnels through it.
    """
    if isinstance(value, BaseModel):
        return _to_plain(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Serialise *value* to canonical JSON — sorted keys, fixed UTF-8, no churn.

    Sorting keys makes the digest independent of dict insertion order; compact
    separators drop insignificant whitespace; ``ensure_ascii=False`` keeps a
    stable, readable encoding.
    """
    return json.dumps(
        _to_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def hash_value(value: Any) -> str:
    """Return the stable ``sha256`` hex digest of *value*'s normalised form.

    The one hashing path: every caller (rules, prompts, schemas) goes through
    here, so no caller ever hashes by hand.
    """
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def hash_rule_object(rules: BaseModel | Mapping[str, Any]) -> str:
    """Hash a loaded rule object — a pydantic model or its dumped mapping."""
    return hash_value(rules)


def hash_prompt(template: str) -> str:
    """Hash a prompt template string (the declared template, never a raw file)."""
    return hash_value(template)


def hash_tool_schema(schema: Mapping[str, Any]) -> str:
    """Hash a tool-schema mapping (e.g. ``Model.model_json_schema()``)."""
    return hash_value(schema)
