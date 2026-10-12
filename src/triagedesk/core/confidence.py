"""Pure deterministic coverage/deferral signal (D8-01, D8-02, D8-03).

A deterministic function of already-typed objects the graph holds after ``score`` —
the matched discriminator ids plus ``MatchResult.no_match``, and the scored
``PriorityResult``. Never a model probability, logprob or token count (D8-01).

This module imports nothing from ``llm`` / ``mcp`` / ``store`` (enforced by
``tests/test_purity.py``); every band and category is read from ``data/*.yaml``
through the one loader (``core/rules.py``) — no SATS value is inlined here
(CONVENTIONS §1). ``core/scorer.py`` is not edited and takes no confidence input, so
the scored colour can never be downgraded by this signal (D8-12).

The signal can only make the system *more* cautious: a deferral routes the graph to
a safe terminal (``escalate`` / ``request_missing_info``), and it never produces a
colour (Pitfall 2).
"""

from __future__ import annotations

from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import (
    ConfidenceComponent,
    ConfidenceLevel,
    ConfidenceResult,
    PriorityResult,
)

# The named threshold the deferral decision derives from (D8-09). A missed emergency
# is far more costly than a needless deferral (see ``docs/DECISIONS.md`` D20), so the
# bar for answering is set high: a case must show at least this many satisfied
# coverage components to proceed to the approval gate. This is a named constant
# derived from that stated cost — never a value tuned to make a test green.
DEFERRAL_MIN_SATISFIED_COMPONENTS = 2

# The satisfied-component count at or above which the signal reads ``high``.
_LEVEL_HIGH_MIN_SATISFIED = 3

# How near a TEWS colour-band edge a case may sit and still count as covered. The
# band edges come from the data (``get_tews().tews_to_colour``); this tolerance is a
# structural margin (a single-point move across the boundary), not a clinical value.
_TEWS_BAND_EDGE_TOLERANCE = 1

# The coverage components ``assess`` evaluates, in the order it reports them (D8-01).
# Declared ONCE here so the arity the offline ECE normalises by (``evals.analysis``) and
# the names the tests assert against derive from the same source: adding or removing a
# component cannot silently mis-normalise a published figure (CONVENTIONS §1).
_VITALS_COVERAGE = "vitals_coverage"
_DISCRIMINATOR_COVERAGE = "discriminator_coverage"
_OVERRIDE_PATH = "override_path"
_TEWS_BAND_DISTANCE = "tews_band_distance"

COMPONENT_NAMES: tuple[str, ...] = (
    _VITALS_COVERAGE,
    _DISCRIMINATOR_COVERAGE,
    _OVERRIDE_PATH,
    _TEWS_BAND_DISTANCE,
)
# The signal's arity — the ONE source for the offline ECE normaliser, never a bare literal.
COMPONENT_COUNT = len(COMPONENT_NAMES)


def _vitals_component(priority: PriorityResult) -> ConfidenceComponent:
    """Vitals coverage — a recorded-vs-total count, never a percentage (D8-01)."""
    total = len(get_tews().parameters)
    detail = f"{len(priority.used_vitals)} of {total} scored vitals recorded"
    return ConfidenceComponent(
        name=_VITALS_COVERAGE,
        satisfied=not priority.missing_vitals,
        detail=detail,
    )


def _discriminator_component(
    matched_ids: list[str], no_match: bool
) -> ConfidenceComponent:
    """Discriminator coverage — satisfied when the matcher found a discriminator."""
    total = len(get_discriminators().discriminators)
    detail = f"{len(matched_ids)} of {total} discriminators matched"
    return ConfidenceComponent(
        name=_DISCRIMINATOR_COVERAGE,
        satisfied=not no_match,
        detail=detail,
    )


def _override_component(priority: PriorityResult) -> ConfidenceComponent:
    """Override-vs-TEWS path — did a discriminator genuinely raise the colour?

    Read as the already-produced override rule's ``rule_id`` naming a discriminator
    category, so this never re-derives a colour or parses the human ``detail`` string
    (Pitfall 2). The category key set is the discriminator data authority.
    """
    categories = get_discriminators().categories
    fired = any(rule.rule_id in categories for rule in priority.triggered_rules)
    detail = (
        "a discriminator override raised the priority"
        if fired
        else "no discriminator override fired"
    )
    return ConfidenceComponent(name=_OVERRIDE_PATH, satisfied=fired, detail=detail)


def _band_distance(tews: int) -> int:
    """Distance from *tews* to the nearest edge of its colour band (data-driven).

    The band is the inclusive ``get_tews().tews_to_colour`` band containing *tews*,
    with a missing ``max`` treated as an open (unbounded) upper end. No band edge is
    inlined (CONVENTIONS §1).

    The loop always returns for the loaded data: the top band is open-ended (its ``max``
    is ``None``) and TEWS is a non-negative sum, so every value matches some band. The
    fallback below is therefore UNREACHABLE today; it is retained (rather than left as an
    implicit ``None``) purely as an explicit sentinel, so a future data edit that removed
    the open-ended top band could not silently make this fall through.
    """
    for band in get_tews().tews_to_colour:
        high = band.max
        if band.min <= tews and (high is None or tews <= high):
            distance = tews - band.min
            if high is not None:
                distance = min(distance, high - tews)
            return distance
    # Unreachable with the loaded (open-ended top) bands — an explicit sentinel, not a
    # negative-total handler.
    return _TEWS_BAND_EDGE_TOLERANCE + 1


def _band_component(priority: PriorityResult) -> ConfidenceComponent:
    """TEWS distance from the band edge — satisfied when the case sits clear of it."""
    tews = priority.tews or 0
    distance = _band_distance(tews)
    return ConfidenceComponent(
        name=_TEWS_BAND_DISTANCE,
        satisfied=distance > _TEWS_BAND_EDGE_TOLERANCE,
        detail=f"tews distance {distance} from the band edge",
    )


def _level_for(satisfied_count: int) -> ConfidenceLevel:
    """Derive the closed-set level from the satisfied-component count."""
    if satisfied_count >= _LEVEL_HIGH_MIN_SATISFIED:
        return "high"
    if satisfied_count >= DEFERRAL_MIN_SATISFIED_COMPONENTS:
        return "moderate"
    return "low"


def assess(
    matched_ids: list[str],
    no_match: bool,
    priority: PriorityResult,
) -> ConfidenceResult:
    """Return the deterministic coverage/deferral signal for one scored case (D8-01).

    Every component in ``COMPONENT_NAMES`` is computed from already-typed objects:
    vitals coverage, discriminator coverage, the override-vs-TEWS path and the TEWS
    distance from the band edge. ``no_match`` forces a deferral regardless of the others
    (D8-11) — a case where no discriminator matched is never reported as high confidence.
    Otherwise a case defers when fewer than ``DEFERRAL_MIN_SATISFIED_COMPONENTS``
    components are satisfied. The signal never returns a colour and never a
    probability (D8-02, D8-12).

    The signal reads only the scored ``priority`` and the retrieved discriminator facts —
    it takes no ``CaseInput``, so the tool/node contract cannot carry a field the
    computation ignores (WR-03): the retry from ``score`` recomputes the same
    ``PriorityResult`` from the same case, so nothing is lost by not re-passing it.
    """
    components = [
        _vitals_component(priority),
        _discriminator_component(matched_ids, no_match),
        _override_component(priority),
        _band_component(priority),
    ]
    if no_match:
        return ConfidenceResult(
            deferral=True,
            level="low",
            components=components,
            reason="no discriminator matched the complaint; deferring for human review",
        )
    satisfied_count = sum(1 for component in components if component.satisfied)
    deferral = satisfied_count < DEFERRAL_MIN_SATISFIED_COMPONENTS
    reason = (
        f"only {satisfied_count} of {len(components)} coverage components satisfied"
        if deferral
        else ""
    )
    return ConfidenceResult(
        deferral=deferral,
        level=_level_for(satisfied_count),
        components=components,
        reason=reason,
    )


__all__ = ["COMPONENT_COUNT", "COMPONENT_NAMES", "DEFERRAL_MIN_SATISFIED_COMPONENTS", "assess"]
