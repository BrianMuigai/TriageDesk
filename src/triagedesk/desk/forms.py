"""The desk vitals form: build a `CaseInput` from the posted form and render the form controls
from the ONE schema (D10-13).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, get_args

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.desk.markup import _escaped

# The checkbox values that read as "set". Deliberately excludes the bare word a data file
# might also carry, so the guard's exact-match scan is never tripped.
_TRUTHY = frozenset({"true", "on", "1"})

# The form field carrying the per-server CSRF token (WR-01). The token is minted once per
# server on ``GET /`` and required on every POST, so a cross-origin page cannot satisfy it.
_CSRF_FIELD = "csrf_token"

# The vitals form's field order and human labels (presentation only). The order is the
# CLINICAL reading order: the context block first, then the scored vitals from head to toe,
# then the complaint. Because the DOM order IS the tab order, the nurse can drive the whole
# form from the keyboard without a ``tabindex``. Each control's kind, plausible range and
# select options are read from the ONE ``CaseInput`` schema at render time, so the form can
# never offer a range or an option the schema would reject and no bound is restated
# (CONVENTIONS §1, D10-13).
_VITALS_LAYOUT: tuple[tuple[str, str], ...] = (
    ("age_years", "Age (years)"),
    ("age_months", "Age (months)"),
    ("age_ambiguous", "Age unclear"),
    ("height_cm", "Height (cm)"),
    ("avpu", "Alertness (AVPU)"),
    ("respiratory_rate", "Breathing rate"),
    ("spo2", "Oxygen saturation"),
    ("heart_rate", "Heart rate"),
    ("systolic_bp", "Systolic BP"),
    ("diastolic_bp", "Diastolic BP"),
    ("temperature_c", "Temperature (°C)"),
    ("mobility", "Mobility"),
    ("trauma", "Trauma"),
    ("complaint", "Complaint"),
)

# The page's reading groups. They partition ``_VITALS_LAYOUT`` in the SAME order, so the DOM
# order (which is the tab order) is unchanged while the eye gets the clinical blocks a busy
# desk expects. A test keeps this partition equal to the ONE layout.
_VITALS_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Patient context", ("age_years", "age_months", "age_ambiguous", "height_cm")),
    (
        "Observations",
        (
            "avpu",
            "respiratory_rate",
            "spo2",
            "heart_rate",
            "systolic_bp",
            "diastolic_bp",
            "temperature_c",
        ),
    ),
    ("Function", ("mobility", "trauma")),
    ("Presentation", ("complaint",)),
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
    autofocus: bool = False,
) -> str:
    """Render one vitals field, repopulated from *form* and bounded by the schema (D10-13).

    The controls are generated from the ONE ``CaseInput`` schema: a numeric field's ``min``/
    ``max`` come from its own ``FieldInfo`` bounds and a select's options from its ``Literal``,
    so no range or option is restated in markup and the form can never offer a value the schema
    would reject.

    ``autofocus`` and ``enterkeyhint`` are PRESENTATION attributes only (Plan 13-03): they move
    the caret and the on-screen keyboard, never a field name, value, bound or the submission.
    ``autofocus`` is applied to the numeric/select/text control only — never to the checkbox or
    its hidden companion — and ``enterkeyhint`` lets the keyboard advance on a numeric entry and
    submit on the complaint.

    When *field_error* names this field, the control is marked ``aria-invalid`` and the ONE
    schema's own rejection renders inside this ``.field`` — the UI-SPEC ``## UI Considerations``
    requirement that an invalid field's message appear **beside that field**, which is what makes
    the mandated "Check the highlighted field" copy literally true.
    """
    kind = _annotation_kind(name)
    raw = str(form.get(name, ""))
    checked_layout = kind == "checkbox"
    focus = " autofocus" if autofocus else ""
    if kind in ("int", "float"):
        low, high = _bounds(name)
        step = "1" if kind == "int" else "0.1"
        mode = ' inputmode="numeric"' if kind == "int" else ""
        control = (
            f'<input id="{name}" name="{name}" type="number"{mode} step="{step}" '
            f'min="{_escaped(_fmt_bound(low))}" max="{_escaped(_fmt_bound(high))}" '
            f'enterkeyhint="next"{focus} value="{_escaped(raw.strip())}">'
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
            f"{' selected' if raw.strip() == value else ''}>"
            f"{_escaped(_option_label(value))}</option>"
            for value in _enum_values(name)
        )
        control = (
            f'<select id="{name}" name="{name}"{focus}>'
            f'<option value="">—</option>{options}</select>'
        )
    else:
        control = (
            f'<textarea id="{name}" name="{name}" rows="3" '
            f'enterkeyhint="enter"{focus}>{_escaped(raw)}</textarea>'
        )

    label_html = f'<label for="{name}">{_escaped(label)}</label>'
    classes = "field field-check" if checked_layout else "field"
    if field_error is not None and field_error[0] == name:
        classes += " field-error"
        # Mark the control itself invalid for assistive tech (the first ``>`` closes the
        # opening tag), then render the ONE schema's own message beside it inside this field.
        control = control.replace(">", ' aria-invalid="true">', 1)
        message = f'<p class="field-error-message" role="alert">{_escaped(field_error[1])}</p>'
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
    offending field so its message renders beside it (never only below the form). The first
    control in the clinical layout is autofocused, so the keyboard starts where the reading
    starts (Plan 13-03).
    """
    return "".join(
        _vitals_field(name, label, form, field_error, autofocus=(index == 0))
        for index, (name, label) in enumerate(_VITALS_LAYOUT)
    )


def _vitals_fieldset(
    form: Mapping[str, str],
    field_error: tuple[str, str] | None = None,
    *,
    autofocus_name: str | None = None,
) -> str:
    """Render the vitals controls in the page's clinical groups, in the ONE layout order.

    The groups are a presentation partition of :data:`_VITALS_LAYOUT`; every field is still
    rendered by :func:`_vitals_field` from the ONE schema, exactly once. The desk does not
    autofocus the first vital on page load: the conversation must be read first. A schema
    rejection can name the offending field, which then receives the single autofocus so the
    error is reachable without hunting.
    """
    labels = dict(_VITALS_LAYOUT)
    groups: list[str] = []
    for legend, names in _VITALS_GROUPS:
        controls = "".join(
            _vitals_field(
                name,
                labels[name],
                form,
                field_error,
                autofocus=(name == autofocus_name),
            )
            for name in names
        )
        groups.append(
            '<fieldset class="field-group">'
            f"<legend>{_escaped(legend)}</legend>"
            f'<div class="field-grid">{controls}</div>'
            "</fieldset>"
        )
    return "".join(groups)


def humanize_rule_detail(detail: str) -> str:
    """Turn a scorer rule detail (``respiratory_rate=24 -> 2 points``) into a desk label.

    The parameter key is mapped through the ONE clinical layout, so the card shows the same
    label the form uses. A detail the layout does not name (for example the TEWS baseline
    row) is returned unchanged — the sourced string is never rewritten.
    """
    key, separator, rest = detail.partition("=")
    labels = dict(_VITALS_LAYOUT)
    label = labels.get(key) or labels.get(f"{key}_c")
    if separator and label:
        return f"{label} {rest}"
    return detail


def merge_form_over_case(form: Mapping[str, str], base: CaseInput) -> CaseInput:
    """Overlay only the fields the nurse actually posted on a model-extracted *base* case.

    A note-intake flow must not let an empty form erase what the note stated. The raw posted
    value decides: a blank field keeps the extraction's value, a non-blank field takes the
    nurse's validated value, and a boolean flag is only overlaid when it is set. Validation is
    still the ONE :func:`form_to_case`, so the note path can never introduce a value the form
    would reject.
    """
    typed = form_to_case(form)
    update: dict[str, Any] = {}
    for name in CaseInput.model_fields:
        raw = str(form.get(name, "")).strip()
        if isinstance(getattr(typed, name), bool):
            if raw.lower() in _TRUTHY:
                update[name] = True
            continue
        if raw:
            update[name] = getattr(typed, name)
    return base.model_copy(update=update)


def case_to_form_values(case: CaseInput) -> dict[str, str]:
    """Render a typed case back into the form's string values (the note prefill).

    ``None`` becomes blank (an absent value is never imputed), a true flag becomes the
    checkbox value, and every other value is its own string. The values are re-validated by
    the next :func:`form_to_case`, so this function never becomes a second schema.
    """
    values: dict[str, str] = {}
    for name in CaseInput.model_fields:
        value = getattr(case, name)
        if isinstance(value, bool):
            values[name] = "true" if value else ""
        elif value is None:
            values[name] = ""
        else:
            values[name] = str(value)
    return values


def note_sourced_fields(form: Mapping[str, str], extraction: ExtractionResult) -> list[str]:
    """The form fields whose value came from the note, not from the nurse.

    A field is note-sourced exactly when the nurse left it blank and the extraction produced
    a value. The confirm step shows this provenance so the human reviews the model's reading
    before it can influence a score.
    """
    sourced: list[str] = []
    for name in CaseInput.model_fields:
        if str(form.get(name, "")).strip():
            continue
        value = getattr(extraction.case, name)
        if value is None or value == "" or value is False:
            continue
        sourced.append(name)
    return sourced


def display_form_value(name: str, raw: str) -> str:
    """A human-readable value for the confirm summary, without inventing a clinical value."""
    value = raw.strip()
    if name == "age_ambiguous":
        return "Flagged" if value.lower() in _TRUTHY else "Not flagged"
    if name == "trauma":
        if not value:
            return "Not stated"
        return "Present" if value.lower() in _TRUTHY else "Absent"
    if not value:
        return "Not stated"
    if name in ("mobility", "avpu"):
        return _option_label(value)
    return value
