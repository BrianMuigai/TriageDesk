"""The keyboard-first vitals-entry proofs (Plan 13-03, JC-3).

Proves the form's keyboard flow is PRESENTATION only: the first control is autofocused
exactly once, numeric controls carry ``enterkeyhint="next"`` and the complaint carries
``enterkeyhint="enter"``, the DOM order (which IS the tab order) follows the clinical
layout, and no field name, bound, value or submission path changed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from test_desk import _bound_text, _schema_bound
from triagedesk.desk import server as desk_server
from triagedesk.desk.forms import _VITALS_LAYOUT

FORMS_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "triagedesk" / "desk" / "forms.py"
)

# The stdlib/schema/markup modules the form module already imports — no third-party addition.
_ALLOWED_IMPORTS = frozenset(
    {
        "__future__",
        "collections.abc",
        "typing",
        "triagedesk.core.schema",
        "triagedesk.desk.markup",
    }
)

_NUMERIC_FIELDS = (
    "age_years",
    "age_months",
    "height_cm",
    "respiratory_rate",
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "temperature_c",
    "spo2",
)


def _vitals_block(body: str) -> str:
    """The inner HTML of the ONE vitals form (the field block's scan subject)."""
    return body.split('<form id="vitals-form"', 1)[1].split("</form>", 1)[0]


def test_first_vital_is_autofocused_exactly_once() -> None:
    """Exactly one autofocus exists, on the first clinical control (``age_years``)."""
    body = desk_server.render_state()

    assert body.count("autofocus") == 1, "the page carries more than one autofocus"
    assert re.search(r'id="age_years"[^>]*\bautofocus\b', body)


def test_numeric_vitals_carry_enterkeyhint_next() -> None:
    """Every numeric control hints ``next``; the complaint hints ``enter``."""
    block = _vitals_block(desk_server.render_state())

    controls = re.findall(r'<input[^>]*type="number"[^>]*>', block)
    assert controls, "the vitals form rendered no numeric control"
    for control in controls:
        assert 'enterkeyhint="next"' in control, control

    complaint = re.search(r'<textarea id="complaint"[^>]*>', block)
    assert complaint is not None
    assert 'enterkeyhint="enter"' in complaint.group(0)


def test_tab_order_follows_the_clinical_layout() -> None:
    """The DOM order of the controls equals the ONE declared clinical layout."""
    block = _vitals_block(desk_server.render_state())

    ids = re.findall(r'<(?:input|select|textarea)[^>]*\bid="([^"]+)"', block)

    assert ids == [name for name, _ in _VITALS_LAYOUT]


def test_keyboard_flow_is_presentation_only() -> None:
    """Names, schema bounds and the submit action are unchanged by the keyboard attributes."""
    body = desk_server.render_state()
    block = _vitals_block(body)

    for name, _ in _VITALS_LAYOUT:
        assert f'name="{name}"' in block, name

    for name in _NUMERIC_FIELDS:
        low = _bound_text(_schema_bound(name, "ge"))
        high = _bound_text(_schema_bound(name, "le"))
        assert f'min="{low}" max="{high}"' in block, f"{name} bounds changed"

    # The submission path is the unchanged same-origin POST to /case.
    assert 'method="post" action="/case"' in body
    assert 'id="submit-vitals"' in body


def test_keyboard_flow_adds_no_dependency() -> None:
    """AST guard: the form module imports only its existing stdlib/schema/markup modules."""
    tree = ast.parse(FORMS_PATH.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)

    assert modules == _ALLOWED_IMPORTS, sorted(modules ^ _ALLOWED_IMPORTS)
