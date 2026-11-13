"""Executable DRY guard: SATS scoring values live only in ``data/*.yaml``.

CONVENTIONS §1 makes ``data/*.yaml`` the single source of truth for the SATS
**scoring substrate** — the numeric band edges, colour thresholds and
discriminator labels/aliases. This test loads every leaf of both data files
*through the one loader* (``core/rules.py``) and asserts no discriminating
clinical value reappears as a literal under ``src/**.py``.

Guard scope — the input-domain vs scoring-band boundary
-------------------------------------------------------
The guard covers the **scoring substrate** only: the values a scorer uses to turn
vitals into a colour. It deliberately does NOT flag ``core/schema.py``'s
``Literal`` enums (``mobility`` = walking/with_help/stretcher; ``avpu`` =
alert/voice/pain/unresponsive) or its plausible physiological ranges (e.g.
temperature 20-45 °C). Those are **input-domain constraints** — which values the
nurse may enter and which the model may return — a distinct concern from the
categorical/numeric scoring bands in the YAML, and are intentionally not sourced
from ``data/``. A future reader must NOT "fix" this by moving the enums into the
YAML: they are a different concern (RESEARCH Pitfall 3; the STATE decision
"schema plausible-range bounds are distinct from SATS TEWS bands").

Mechanism
---------
A single :func:`_leaf_values` helper collects every scalar leaf from the loaded
data (the shared traversal — do not duplicate it). String leaves are compared
*exactly* against string literals in ``src/``; docstrings are excluded, because
documentation is out of the DRY gate by design (as ``docs/SATS.md`` is). The
*discriminating* numeric leaves are compared against numeric literals:
discriminating numbers are those with a fractional part or two or more
significant digits. Single-digit band points (0-3) are ubiquitous in ordinary
code and are covered instead by the data-driven band-edge tests
(``tests/test_sats_bands.py``), which derive every boundary from the data.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import CaseInput

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

# Input-domain enum fields whose values are NOT scoring substrate (see docstring).
INPUT_DOMAIN_FIELDS = ("mobility", "avpu")
_BOUND_KEYS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")


def _leaf_values(node: Any) -> Iterator[tuple[str, Any]]:
    """Yield ``("str"|"num", value)`` for every scalar leaf of a nested structure.

    The ONE shared traversal helper used by both the string and numeric guards.
    """
    if isinstance(node, dict):
        for value in node.values():
            yield from _leaf_values(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _leaf_values(value)
    elif isinstance(node, bool):
        return  # booleans are not scoring substrate
    elif isinstance(node, str):
        yield ("str", node)
    elif isinstance(node, (int, float)):
        yield ("num", node)


def _collect(spec: Any, key: str, out: set) -> None:
    """Recursively collect every ``key`` value (enum list or numeric) from a schema."""
    if isinstance(spec, dict):
        value = spec.get(key)
        if key == "enum" and isinstance(value, list):
            out.update(value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out.add(float(value))
        for child in spec.values():
            _collect(child, key, out)
    elif isinstance(spec, list):
        for child in spec:
            _collect(child, key, out)


def _data_leaves() -> tuple[set[str], set[float]]:
    """Every string and numeric leaf from ``data/*.yaml`` via the one loader."""
    leaves = list(_leaf_values(get_tews().model_dump()))
    leaves += list(_leaf_values(get_discriminators().model_dump()))
    strings = {value for kind, value in leaves if kind == "str"}
    numbers = {float(value) for kind, value in leaves if kind == "num"}
    return strings, numbers


def _input_domain_enums() -> set[str]:
    props = CaseInput.model_json_schema()["properties"]
    enums: set[str] = set()
    for field in INPUT_DOMAIN_FIELDS:
        _collect(props[field], "enum", enums)
    return enums


def _plausible_bounds() -> set[float]:
    bounds: set[float] = set()
    for key in _BOUND_KEYS:
        _collect(CaseInput.model_json_schema(), key, bounds)
    return bounds


def _forbidden_values() -> tuple[set[str], set[float]]:
    """The scoring-substrate values that may not appear as ``src/`` literals."""
    strings, numbers = _data_leaves()
    forbidden_strings = strings - _input_domain_enums()
    discriminating = {n for n in numbers if abs(n) >= 10 or n != int(n)}
    forbidden_numbers = discriminating - _plausible_bounds()
    return forbidden_strings, forbidden_numbers


def _docstrings(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                found.add(doc)
    return found


def _scan_source(source: str) -> tuple[set[str], set[float]]:
    """String literals (docstrings excluded) and numeric literals in *source*."""
    tree = ast.parse(source)
    docstrings = _docstrings(tree)
    strings: set[str] = set()
    numbers: set[float] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if isinstance(node.value, str):
            if node.value not in docstrings:
                strings.add(node.value)
        elif isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            numbers.add(float(node.value))
    return strings, numbers


def test_no_scoring_value_is_duplicated_under_src() -> None:
    forbidden_strings, forbidden_numbers = _forbidden_values()
    offenders: dict[str, dict[str, list]] = {}
    for path in sorted(SRC_DIR.rglob("*.py")):
        strings, numbers = _scan_source(path.read_text(encoding="utf-8"))
        bad_strings = sorted(strings & forbidden_strings)
        bad_numbers = sorted(numbers & forbidden_numbers)
        if bad_strings or bad_numbers:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = {
                "strings": bad_strings,
                "numbers": bad_numbers,
            }
    assert not offenders, (
        "SATS scoring values must live only in data/*.yaml (CONVENTIONS §1); "
        f"found literals under src/: {offenders}"
    )


def test_guard_is_not_vacuous() -> None:
    """The guard fails on a hard-coded discriminator label and band edge."""
    forbidden_strings, forbidden_numbers = _forbidden_values()
    assert forbidden_strings, "no discriminating string substrate was collected"
    assert forbidden_numbers, "no discriminating numeric substrate was collected"
    label = sorted(forbidden_strings)[0]
    edge = sorted(forbidden_numbers)[0]
    strings, numbers = _scan_source(f"LABEL = {label!r}\nEDGE = {edge!r}\n")
    assert label in strings & forbidden_strings
    assert edge in numbers & forbidden_numbers
