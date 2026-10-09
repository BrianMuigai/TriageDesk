"""Tests for the canonical hashing helper (SAFE-04, D-17).

The digest must be **stable under normalisation** — dictionary key reordering
and source comment/whitespace edits leave it unchanged — while a real content
change churns it. All assertions run offline (no model, no MCP).
"""

from __future__ import annotations

import hashlib

import yaml

from triagedesk.core import hashing
from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import ExtractionResult
from triagedesk.llm.prompts import EXTRACTION_PROMPT

# --- normalisation: key order, comments and whitespace do not churn ----------

_PLAIN_YAML = """
temperature:
  bands:
    - points: 0
      min: 35.0
    - points: 1
      min: 38.5
"""

# Same facts, but with comments, blank lines and different spacing.
_COMMENTED_YAML = """
# SATS temperature bands (illustrative fixture for the hashing test)
temperature:            # the parameter

  bands:

    - points: 0
      min: 35.0         # lower bound (inclusive)
    - points: 1
      min: 38.5         # fever threshold
"""


def test_digest_is_sha256_hex() -> None:
    digest = hashing.hash_value({"a": 1})
    assert len(digest) == 64
    assert all(char in "0123456789abcdef" for char in digest)


def test_key_reordering_does_not_change_digest() -> None:
    a = {"alpha": 1, "beta": {"x": [1, 2], "y": "z"}}
    b = {"beta": {"y": "z", "x": [1, 2]}, "alpha": 1}
    assert hashing.hash_value(a) == hashing.hash_value(b)


def test_yaml_comments_and_whitespace_do_not_change_digest() -> None:
    plain = yaml.safe_load(_PLAIN_YAML)
    commented = yaml.safe_load(_COMMENTED_YAML)
    assert plain == commented
    assert hashing.hash_value(plain) == hashing.hash_value(commented)


def test_real_value_change_changes_digest() -> None:
    base = {"rr": {"bands": [{"min": 9, "points": 1}]}}
    changed = {"rr": {"bands": [{"min": 9, "points": 2}]}}
    assert hashing.hash_value(base) != hashing.hash_value(changed)


def test_canonical_json_sorts_keys_and_is_compact() -> None:
    assert hashing.canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


# --- the loaded substrate hashes through the same path -----------------------


def test_loaded_rule_object_hashes_stably() -> None:
    assert hashing.hash_rule_object(get_tews()) == hashing.hash_rule_object(get_tews())
    assert hashing.hash_rule_object(get_discriminators()) == hashing.hash_rule_object(
        get_discriminators()
    )


def test_loaded_rule_object_is_order_independent() -> None:
    dumped = get_tews().model_dump(mode="json")
    shuffled = dict(reversed(list(dumped.items())))
    assert hashing.hash_value(dumped) == hashing.hash_value(shuffled)


def test_tool_schema_hashes_and_is_order_independent() -> None:
    schema = ExtractionResult.model_json_schema()
    reordered = dict(reversed(list(schema.items())))
    assert hashing.hash_tool_schema(schema) == hashing.hash_tool_schema(reordered)


def test_prompt_string_hashes() -> None:
    assert hashing.hash_prompt(EXTRACTION_PROMPT) == hashing.hash_value(EXTRACTION_PROMPT)
    assert hashing.hash_prompt(EXTRACTION_PROMPT) != hashing.hash_prompt(
        EXTRACTION_PROMPT + " "
    )


# --- entry points share one path ---------------------------------------------


def test_entry_points_share_one_hashes_path() -> None:
    assert hashing.hash_rule_object({"a": 1}) == hashing.hash_value({"a": 1})
    assert hashing.hash_prompt("p") == hashing.hash_value("p")
    assert hashing.hash_tool_schema({"a": 1}) == hashing.hash_value({"a": 1})
    assert hashing.hash_value({"a": 1}) == hashlib.sha256(
        b'{"a":1}'
    ).hexdigest()
