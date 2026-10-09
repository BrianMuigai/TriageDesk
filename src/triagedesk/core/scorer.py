"""Pure deterministic TEWS scorer (D-01, D-02, D-03, D-04).

No number ever comes from the model (D-02): this module imports nothing from
``llm`` / ``mcp`` / ``store`` (enforced by ``tests/test_purity.py``). Every band,
threshold, colour and target time is read from ``data/sats_tews.yaml`` through the
one loader (``core/rules.py``) — no SATS value is inlined here (CONVENTIONS §1).

The two safety branches fail closed:

* out-of-scope input (paediatric / missing / months-expressed / ambiguous age)
  abstains and never receives an adult colour (D-03);
* a missing scored vital is reported in ``missing_vitals`` and never imputed
  (D-04) — the score uses only nurse-provided fields.
"""

from __future__ import annotations

import math

from triagedesk.core.citations import format_citation
from triagedesk.core.rules import (
    Band,
    DiscriminatorCategory,
    Parameter,
    TewsRules,
    get_discriminators,
    get_tews,
)
from triagedesk.core.schema import CaseInput, PriorityResult, TriggeredRule


def _band_bounds(band: Band) -> tuple[float, float]:
    """The inclusive ``[low, high]`` of *band*, with open ends as infinities."""
    low = band.min if band.min is not None else -math.inf
    high = band.max if band.max is not None else math.inf
    return low, high


def _is_categorical(param: Parameter) -> bool:
    """True when *param*'s bands carry a discrete ``value`` (not a numeric range)."""
    return any(band.value is not None for band in param.bands)


def _match_categorical(param: Parameter, value: str) -> Band | None:
    """The band whose discrete ``value`` equals *value* (data-driven lookup)."""
    for band in param.bands:
        if band.value == value:
            return band
    return None


def _match_boolean(param: Parameter, value: bool) -> Band:
    """Map a boolean to its band without inlining the ``yes``/``no`` tokens.

    The truthy band is the highest-points band and the falsy band the lowest
    (the data is the authority; the scorer never names the tokens).
    """
    ordered = sorted(param.bands, key=lambda band: band.points)
    return ordered[-1] if value else ordered[0]


def _edge_distance(band: Band, value: float) -> float:
    """Distance from *value* to the nearest edge of *band* (0 if inside)."""
    low, high = _band_bounds(band)
    if value < low:
        return low - value
    if value > high:
        return value - high
    return 0.0


def _match_numeric(param: Parameter, value: float) -> Band:
    """Select the band for a numeric *value*, total over the accepted range.

    An inclusive band containing the value wins. If a valid in-range value falls
    in a gap between adjacent bands (no band contains it), the nearest band by
    edge distance is selected and, on a tie, the higher-points band — so an
    implausible value never under-triages (fail-closed, SCORE-05).

    Distances are compared with a relative tolerance so that an exact tie
    (e.g. temperature 34.95, equidistant from 34.9 and 35.0) is not broken by
    binary floating-point representation — a hair's difference must not let the
    lower-points band win.
    """
    for band in param.bands:
        low, high = _band_bounds(band)
        if low <= value <= high:
            return band
    distances = [(_edge_distance(band, value), band) for band in param.bands]
    nearest = min(distance for distance, _ in distances)
    tolerance = max(abs(nearest), 1.0) * 1e-9
    tied = [band for distance, band in distances if distance <= nearest + tolerance]
    return max(tied, key=lambda band: band.points)


def _select_band(param: Parameter, value: object) -> Band | None:
    """Select the band for a typed *value* of any supported kind (or None)."""
    if isinstance(value, bool):
        return _match_boolean(param, value)
    if _is_categorical(param):
        return _match_categorical(param, value)  # type: ignore[arg-type]
    return _match_numeric(param, float(value))  # type: ignore[arg-type]


def _out_of_scope(case: CaseInput, rules: TewsRules) -> tuple[bool, str | None]:
    """Evaluate the fail-closed out-of-scope predicate from its data (D-03).

    A months-expressed or ambiguous age abstains first — it can never receive an
    adult colour. Otherwise adult = age > adult_min_age_years OR height >
    adult_min_height_cm; a missing age returns the declared ``on_missing_age``
    behaviour (abstain) and never defaults to adult.
    """
    scope = rules.out_of_scope
    if case.age_months is not None:
        return True, "age is expressed in months; only an unambiguous adult-year integer is scored"
    if case.age_ambiguous:
        return True, "age is ambiguous; refusing to score an adult colour"
    if case.height_cm is not None and case.height_cm > scope.adult_min_height_cm:
        return False, None
    if case.age_years is None:
        return True, "age is missing; abstaining per the declared on_missing_age behaviour"
    if case.age_years <= scope.adult_min_age_years:
        return True, f"age {case.age_years} is at or below the adult minimum"
    return False, None


def _colour_for(rules: TewsRules, total: int) -> str:
    """Map a TEWS *total* to its colour token (data-driven, inclusive bands)."""
    for band in rules.tews_to_colour:
        high = band.max if band.max is not None else math.inf
        if band.min <= total <= high:
            return band.colour
    raise ValueError(f"no colour band covers TEWS total {total}")


def _colour_urgency(rules: TewsRules) -> dict[str, float]:
    """Map each colour to a data-derived urgency rank (D-01, T-02-08).

    The rank is the colour band's lower TEWS bound from ``data/sats_tews.yaml``:
    a colour that begins at a higher TEWS total is more urgent (RED > ORANGE >
    YELLOW > GREEN). The order is derived from the data — no colour token is
    hard-coded here (CONVENTIONS §1).
    """
    return {band.colour: float(band.min) for band in rules.tews_to_colour}


def _most_urgent_category(
    matched_ids: list[str] | None, tews: TewsRules
) -> tuple[str, DiscriminatorCategory] | None:
    """The most-urgent discriminator category present among *matched_ids* (D-01).

    Urgency is data-derived (see ``_colour_urgency``), so the most-urgent category
    present wins independent of input order. Ids that are not in the closed set
    are ignored, so a caller can never inject a category or a colour (T-02-08).
    Returns ``None`` when no valid id matched.
    """
    disc = get_discriminators()
    category_of = {d.id: d.category for d in disc.discriminators}
    present = {category_of[id_] for id_ in (matched_ids or []) if id_ in category_of}
    if not present:
        return None
    urgency = _colour_urgency(tews)
    winner = max(present, key=lambda name: urgency[disc.categories[name].colour])
    return winner, disc.categories[winner]


def case_field(name: str) -> str:
    """Bind a data parameter key to its schema field name.

    The YAML parameter key is the structural name; the schema field may carry a
    unit suffix (``temperature`` -> ``temperature_c``). An exact field-name match
    wins; otherwise the unique field whose name starts with the parameter key is
    used. No clinical value is involved — only a structural binding.
    """
    fields = CaseInput.model_fields
    if name in fields:
        return name
    candidates = [field for field in fields if field.startswith(f"{name}_")]
    return candidates[0] if len(candidates) == 1 else name


def score_priority(
    case: CaseInput,
    matched_discriminator_ids: list[str] | None = None,
) -> PriorityResult:
    """Score one typed case deterministically, with no model involvement (D-01).

    Returns a cited SATS colour + TEWS total + target time when the case is adult
    and in scope; otherwise a fail-closed abstention. ``citations`` is derived 1:1
    from ``triggered_rules`` so the citation invariant holds by construction.
    """
    rules = get_tews()
    out_of_scope, reason = _out_of_scope(case, rules)
    if out_of_scope:
        return PriorityResult(
            matched_discriminator_ids=list(matched_discriminator_ids or []),
            out_of_scope=True,
            abstained=True,
            reason=reason,
        )

    triggered: list[TriggeredRule] = []
    missing: list[str] = []
    used: list[str] = []
    tews = 0
    for name, param in rules.parameters.items():
        value = getattr(case, case_field(name), None)
        if value is None:
            missing.append(name)
            continue
        used.append(name)
        band = _select_band(param, value)
        if band is None:
            continue
        tews += band.points
        if band.points > 0:
            triggered.append(
                TriggeredRule(
                    rule_id=name,
                    detail=f"{name}={value} -> {band.points} points",
                    points=band.points,
                    citation=format_citation(f"{name} band", rules.citation),
                )
            )

    colour = _colour_for(rules, tews)
    override = _most_urgent_category(matched_discriminator_ids, rules)
    if override is not None:
        category_name, category = override
        urgency = _colour_urgency(rules)
        if urgency[category.colour] > urgency[colour]:
            colour = category.colour
            triggered.append(
                TriggeredRule(
                    rule_id=category_name,
                    detail=f"discriminator override: {category_name} -> {category.colour}",
                    points=0,
                    citation=format_citation(category.citation_ref, get_discriminators().citation),
                )
            )
    target_time = rules.target_times[colour]
    return PriorityResult(
        colour=colour,
        tews=tews,
        target=target_time.target,
        destination=target_time.destination,
        triggered_rules=triggered,
        citations=[rule.citation for rule in triggered],
        matched_discriminator_ids=list(matched_discriminator_ids or []),
        missing_vitals=missing,
        used_vitals=used,
        out_of_scope=False,
        abstained=False,
    )
