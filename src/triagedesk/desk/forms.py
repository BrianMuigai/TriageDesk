"""The desk vitals form: build a `CaseInput` from the posted form and render the form controls
from the ONE schema (D10-13).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, get_args

from triagedesk.core.schema import CaseInput
from triagedesk.desk.markup import _escaped

# The checkbox values that read as "set". Deliberately excludes the bare word a data file
# might also carry, so the guard's exact-match scan is never tripped.
_TRUTHY = frozenset({"true", "on", "1"})

# The form field carrying the per-server CSRF token (WR-01). The token is minted once per
# server on ``GET /`` and required on every POST, so a cross-origin page cannot satisfy it.
_CSRF_FIELD = "csrf_token"

# The vitals form's field order and human labels (presentation only). Each control's kind,
# plausible range and select options are read from the ONE ``CaseInput`` schema at render
# time, so the form can never offer a range or an option the schema would reject and no
# bound is restated (CONVENTIONS §1, D10-13).
_VITALS_LAYOUT: tuple[tuple[str, str], ...] = (
    ("age_years", "Age (years)"),
    ("age_months", "Age (months)"),
    ("age_ambiguous", "Age unclear"),
    ("height_cm", "Height (cm)"),
    ("respiratory_rate", "Breathing rate"),
    ("heart_rate", "Heart rate"),
    ("systolic_bp", "Systolic BP"),
    ("diastolic_bp", "Diastolic BP"),
    ("temperature_c", "Temperature (°C)"),
    ("spo2", "Oxygen saturation"),
    ("mobility", "Mobility"),
    ("avpu", "Alertness (AVPU)"),
    ("trauma", "Trauma"),
    ("complaint", "Complaint"),
)


def form_to_case(form: Mapping[str, str]) -> CaseInput:
    """Build and validate a :class:`CaseInput` from the posted vitals form (D10-13).

    An absent or empty optional numeric/enum field maps to ``None`` (never ``""`` or ``0``);
    an absent ``trauma`` checkbox maps to ``None`` (never ``False``); ``age_ambiguous``
    defaults to ``False``; ``complaint`` defaults to ``""``. Validation is the ONE
    ``CaseInput.model_validate`` — the schema is the only validation *and coercion* rule. A
    numeric field's raw string is handed to the schema as-is (no ``int()``/``float()``
    pre-cast here), so a browser-reachable value the schema rejects (e.g. ``1e2`` in a
    ``type=number`` field) yields the schema's own :class:`pydantic.ValidationError` — which
    the handler renders beside the field — rather than a bare ``ValueError`` escaping the
    request handler.
    """

    def _number(key: str) -> Any:
        """Pass the raw string through; the ONE schema coerces and validates it (D10-13)."""
        raw = str(form.get(key, "")).strip()
        return raw or None

    def _choice(key: str) -> str | None:
        raw = str(form.get(key, "")).strip()
        return raw or None

    def _optional_flag(key: str) -> bool | None:
        if key not in form or str(form.get(key, "")).strip() == "":
            return None
        return str(form[key]).strip().lower() in _TRUTHY

    payload: dict[str, Any] = {
        "age_years": _number("age_years"),
        "age_months": _number("age_months"),
        "age_ambiguous": str(form.get("age_ambiguous", "")).strip().lower() in _TRUTHY,
        "height_cm": _number("height_cm"),
        "respiratory_rate": _number("respiratory_rate"),
        "heart_rate": _number("heart_rate"),
        "systolic_bp": _number("systolic_bp"),
        "diastolic_bp": _number("diastolic_bp"),
        "temperature_c": _number("temperature_c"),
        "spo2": _number("spo2"),
        "mobility": _choice("mobility"),
        "avpu": _choice("avpu"),
        "trauma": _optional_flag("trauma"),
        "complaint": str(form.get("complaint", "")) or "",
    }
    return CaseInput.model_validate(payload)


def _csrf_field(token: str | None) -> str:
    """Render the per-server CSRF token as a hidden field (WR-01), or nothing without one.

    Every rendered form carries this field, so a same-origin submission from the surface always
    satisfies the POST check while a cross-origin page (which cannot read the token) cannot.
    """
    if not token:
        return ""
    return f'<input type="hidden" name="{_CSRF_FIELD}" value="{_escaped(token)}">'


def _base_annotation(name: str) -> Any:
    """The non-``None`` annotation of a ``CaseInput`` field (unwrapping ``| None``)."""
    annotation = CaseInput.model_fields[name].annotation
    non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
    return non_none[0] if non_none else annotation


def _annotation_kind(name: str) -> str:
    """Classify a ``CaseInput`` field into the form control it needs (from the schema)."""
    base = _base_annotation(name)
    if base is bool:
        return "checkbox"
    if base is int:
        return "int"
    if base is float:
        return "float"
    if get_args(base):  # a Literal[...] enum field
        return "select"
    return "text"


def _enum_values(name: str) -> list[str]:
    """The ``Literal`` options of an enum field, read from the schema (never restated)."""
    return [str(value) for value in get_args(_base_annotation(name))]


def _bounds(name: str) -> tuple[Any, Any]:
    """The ``(ge, le)`` plausible bounds of a numeric field, read from its ``FieldInfo``."""
    metadata = CaseInput.model_fields[name].metadata
    low = next((getattr(m, "ge", None) for m in metadata if hasattr(m, "ge")), None)
    high = next((getattr(m, "le", None) for m in metadata if hasattr(m, "le")), None)
    return low, high


def _fmt_bound(value: Any) -> str:
    """Render a numeric bound without a trailing ``.0`` (so ``30.0`` -> ``30``)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _option_label(value: str) -> str:
    """The human label for a schema enum value (``with_help`` -> ``With help``)."""
    return value.replace("_", " ").capitalize()


def _vitals_field(
    name: str,
    label: str,
    form: Mapping[str, str],
    field_error: tuple[str, str] | None = None,
) -> str:
    """Render one vitals field, repopulated from *form* and bounded by the schema (D10-13).

    The controls are generated from the ONE ``CaseInput`` schema: a numeric field's ``min``/
    ``max`` come from its own ``FieldInfo`` bounds and a select's options from its ``Literal``,
    so no range or option is restated in markup and the form can never offer a value the schema
    would reject.

    When *field_error* names this field, the control is marked ``aria-invalid`` and the ONE
    schema's own rejection renders inside this ``.field`` — the UI-SPEC ``## UI Considerations``
    requirement that an invalid field's message appear **beside that field**, which is what makes
    the mandated "Check the highlighted field" copy literally true.
    """
    kind = _annotation_kind(name)
    raw = str(form.get(name, ""))
    checked_layout = kind == "checkbox"
    if kind in ("int", "float"):
        low, high = _bounds(name)
        step = "1" if kind == "int" else "0.1"
        mode = ' inputmode="numeric"' if kind == "int" else ""
        control = (
            f'<input id="{name}" name="{name}" type="number"{mode} step="{step}" '
            f'min="{_escaped(_fmt_bound(low))}" max="{_escaped(_fmt_bound(high))}" '
            f'value="{_escaped(raw.strip())}">'
        )
    elif kind == "checkbox":
        checked = " checked" if raw.strip().lower() in _TRUTHY else ""
        # A checkbox alone cannot express False: an unchecked box is not a successful control,
        # so the browser omits the key entirely and the ONE schema reads the field as absent
        # (``None``). For a scored vital (``trauma``) that omission is the recovery terminal, so
        # the common "no trauma" patient could never reach the gate (CR-01). Pair the checkbox
        # with a hidden ``false``: the checkbox MUST come first, because the form data set is
        # built in tree order and the handler keeps ``parse_qs(...)[key][0]`` — a checked box
        # yields ``["true", "false"]`` -> True while an unchecked box yields ``["false"]`` ->
        # False. The hidden input carries no ``id`` (the checkbox owns the ``<label for>``).
        control = (
            f'<input id="{name}" name="{name}" type="checkbox" value="true"{checked}>'
            f'<input type="hidden" name="{name}" value="false">'
        )
    elif kind == "select":
        options = "".join(
            f'<option value="{_escaped(value)}"'
            f'{" selected" if raw.strip() == value else ""}>'
            f"{_escaped(_option_label(value))}</option>"
            for value in _enum_values(name)
        )
        control = (
            f'<select id="{name}" name="{name}">'
            f'<option value="">—</option>{options}</select>'
        )
    else:
        control = f'<textarea id="{name}" name="{name}" rows="3">{_escaped(raw)}</textarea>'

    label_html = f'<label for="{name}">{_escaped(label)}</label>'
    classes = "field field-check" if checked_layout else "field"
    if field_error is not None and field_error[0] == name:
        classes += " field-error"
        # Mark the control itself invalid for assistive tech (the first ``>`` closes the
        # opening tag), then render the ONE schema's own message beside it inside this field.
        control = control.replace(">", ' aria-invalid="true">', 1)
        message = (
            f'<p class="field-error-message" role="alert">{_escaped(field_error[1])}</p>'
        )
    else:
        message = ""
    inner = f"{control}{label_html}" if checked_layout else f"{label_html}{control}"
    return f'<div class="{classes}">{inner}{message}</div>'


def _vitals_fields(form: Mapping[str, str], field_error: tuple[str, str] | None = None) -> str:
    """Render the vitals form's field block, repopulated from *form* (WR-03).

    The controls are generated from the ONE ``CaseInput`` schema (D10-13): a numeric
    field's ``min``/``max`` come from its own ``FieldInfo`` bounds and a select's options
    from its ``Literal``, so no range or option is restated in markup and the form can
    never offer a value the schema would reject. The submitted values are rendered back,
    so a rejected submission never discards what the nurse typed. *field_error* names the
    offending field so its message renders beside it (never only below the form).
    """
    return "".join(
        _vitals_field(name, label, form, field_error) for name, label in _VITALS_LAYOUT
    )
