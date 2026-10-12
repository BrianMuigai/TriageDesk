"""One-way safety + contract-shape proofs for the deterministic confidence signal.

AGENT-02, D8-02/D8-04/D8-11/D8-12: the signal never carries a probability, a ``no_match``
case is never high confidence, the deferral threshold is a named constant, and the scorer
has no confidence input (so the scored colour can never be downgraded). Offline and
deterministic — the pure module and the real scorer only; no model, no MCP subprocess.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from conftest import imported_modules
from triagedesk.core import confidence, scorer
from triagedesk.core.confidence import (
    COMPONENT_NAMES,
    DEFERRAL_MIN_SATISFIED_COMPONENTS,
    assess,
)
from triagedesk.core.schema import (
    CaseInput,
    ConfidenceComponent,
    ConfidenceResult,
    PriorityResult,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCORER_SOURCE = (
    REPO_ROOT / "src" / "triagedesk" / "core" / "scorer.py"
).read_text(encoding="utf-8")

# Field-name tokens that would mark a probability/score smuggled onto the contract.
_FORBIDDEN_FIELD_TOKENS = ("score", "probability", "percent")

CASE = CaseInput(
    age_years=40,
    mobility="walking",
    avpu="alert",
    respiratory_rate=24,
    heart_rate=118,
    systolic_bp=108,
    temperature_c=38.9,
    trauma=False,
    complaint="central chest pain",
)

# A complete-vitals adult case whose complaint matches no discriminator (D8-11).
NO_MATCH_CASE = CaseInput(
    age_years=60,
    mobility="walking",
    avpu="alert",
    respiratory_rate=14,
    heart_rate=80,
    systolic_bp=120,
    temperature_c=36.8,
    trauma=False,
    complaint="feeling unwell",
)


def _priority(
    *,
    tews: int = 6,
    used: list[str] | None = None,
    missing: list[str] | None = None,
) -> PriorityResult:
    """A minimal scored priority with controllable coverage inputs."""
    return PriorityResult(
        tews=tews,
        used_vitals=list(used if used is not None else ["respiratory_rate"]),
        missing_vitals=list(missing if missing is not None else []),
    )


def test_assess_is_deterministic() -> None:
    """The same typed inputs yield an equal signal (D8-01)."""
    first = assess(CASE, ["chest_pain"], False, _priority())
    second = assess(CASE, ["chest_pain"], False, _priority())
    assert first == second


def test_assess_reports_the_declared_components() -> None:
    """All declared components are present, in order, from the ONE owner (D8-01)."""
    result = assess(CASE, ["chest_pain"], False, _priority())
    assert [component.name for component in result.components] == list(COMPONENT_NAMES)


def test_no_match_forces_a_deferral_never_high_confidence() -> None:
    """A no-match priority is deferred at ``low`` regardless of the other components (D8-11)."""
    priority = scorer.score_priority(NO_MATCH_CASE, [])
    result = assess(NO_MATCH_CASE, [], True, priority)

    assert result.deferral is True
    assert result.level == "low"
    assert "discriminator" in result.reason.lower()


def test_contract_carries_no_float_or_probability_field() -> None:
    """No field is a float and none is readable as a score/probability/percentage (D8-02/D8-04)."""
    for model in (ConfidenceResult, ConfidenceComponent):
        for name, field in model.model_fields.items():
            assert field.annotation is not float, f"{model.__name__}.{name} is a float"
            lowered = name.lower()
            offenders = [t for t in _FORBIDDEN_FIELD_TOKENS if t in lowered]
            assert not offenders, f"{model.__name__}.{name} reads as {offenders}"
    # There is deliberately no colour field: the signal can never downgrade one (D8-12).
    assert "colour" not in ConfidenceResult.model_fields

    # The serialised signal contains no percentage sign.
    result = assess(CASE, ["chest_pain"], False, _priority())
    assert "%" not in result.model_dump_json()


def test_deferral_threshold_is_a_named_constant_and_flips_on_the_count() -> None:
    """The threshold is a module-level int and the deferral decision flips across it (D8-09)."""
    assert isinstance(DEFERRAL_MIN_SATISFIED_COMPONENTS, int)
    assert confidence.DEFERRAL_MIN_SATISFIED_COMPONENTS == DEFERRAL_MIN_SATISFIED_COMPONENTS

    # Exactly one satisfied component (discriminator coverage only) -> defer.
    one_satisfied = assess(
        CASE, ["chest_pain"], False, _priority(tews=0, missing=["respiratory_rate"])
    )
    # Exactly DEFERRAL_MIN satisfied (vitals + discriminator) -> do not defer.
    at_threshold = assess(CASE, ["chest_pain"], False, _priority(tews=0))

    assert one_satisfied.deferral is True
    assert one_satisfied.level == "low"
    assert at_threshold.deferral is False


def test_scorer_has_no_confidence_input_and_does_not_import_confidence() -> None:
    """The scorer is one-way: no confidence import and no confidence argument (D8-12)."""
    assert "triagedesk.core.confidence" not in imported_modules(SCORER_SOURCE)
    parameters = inspect.signature(scorer.score_priority).parameters
    assert not any("confidence" in name for name in parameters), parameters
