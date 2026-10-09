"""The eval case-file format and loader (D-01, EVAL-02).

A case is a synthetic fixture: a free-text nurse note, the declared golden structured
extraction (the same fields as ``core.schema.CaseInput``), the expected outcome, the
pass criteria and the EVALS.md source the expectation traces to. The fixture is the
reviewable, declared input — the free-text note is untrusted, the golden case is the
extraction under test.

The accepted ``expected`` tokens are the colour set read from the loaded substrate
(``data/sats_tews.yaml``) plus the three graph terminal outcomes — never a hard-coded
colour list (CONVENTIONS §1). The terminal tokens are harness vocabulary (they name the
graph's safe terminals), not SATS clinical values, so they are declared once here.
"""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]  # no PyYAML stubs pinned (dev-only, no new dep)
from pydantic import BaseModel, field_validator

from triagedesk.core.rules import get_tews
from triagedesk.core.schema import CaseInput

# The three terminal outcomes a case may expect instead of a colour: the recovery
# (re-measure) terminal, the abstention/escalation terminal and the serial-vitals
# second look. Harness vocabulary — not SATS values (CONVENTIONS §1).
TERMINAL_OUTCOMES: tuple[str, ...] = ("RECOVER", "ABSTAIN", "RECHECK")


def declared_outcomes() -> set[str]:
    """The accepted ``expected`` tokens: the loaded colour set plus the terminals.

    The colours are read from the substrate (``data/sats_tews.yaml``) so a new band is a
    data edit, not a code edit (CONVENTIONS §1); the three terminals are the declared
    graph outcomes (D-03).
    """
    colours = {band.colour for band in get_tews().tews_to_colour}
    return colours | set(TERMINAL_OUTCOMES)


class FaultInjection(BaseModel):
    """The per-case injected fault the harness can apply (D-04, Pitfall 13).

    Declared as data on a fixture so the E-12 case can exercise the graph's real
    bounded retry and deterministic fallback: ``tool_timeout`` makes the first tool
    call raise and ``malformed_json`` makes the next return unparseable text. The
    injection is applied per-case and torn down with the case's tool mapping, so it
    can never leak into another case's run (T-04-09).
    """

    tool_timeout: bool = False
    malformed_json: bool = False


class CaseSpec(BaseModel):
    """One synthetic eval case with its declared expectation (D-01, EVAL-02).

    ``note`` is the untrusted free text; ``case`` is the golden, reviewable structured
    extraction. ``expected`` is a colour token or one of the three terminal outcomes and
    is validated against the loaded substrate. ``source`` records the EVALS.md row the
    expectation traces to, so the linkage is auditable (Pitfall 11).

    ``previous_case`` seeds the serial-vitals second look (E-07); ``inject`` declares the
    E-12 fault; ``held_out`` marks a case that bounds the declared failure and is never
    iterated against (D-04); ``declared_failure`` marks the one case we expect to fail.
    """

    id: str
    description: str
    note: str
    case: CaseInput
    expected: str
    pass_criteria: str
    source: str
    previous_case: CaseInput | None = None
    inject: FaultInjection | None = None
    held_out: bool = False
    declared_failure: bool = False

    @field_validator("expected")
    @classmethod
    def _expected_is_declared(cls, value: str) -> str:
        """Reject any expectation that is not a substrate colour or a declared terminal."""
        allowed = declared_outcomes()
        if value not in allowed:
            raise ValueError(
                f"expected {value!r} is not a declared colour or terminal outcome"
            )
        return value


def load_cases(directory: str | Path) -> list[CaseSpec]:
    """Load and validate every ``*.yaml`` case in *directory*, ordered by id."""
    path = Path(directory)
    specs = [
        CaseSpec.model_validate(yaml.safe_load(source.read_text(encoding="utf-8")))
        for source in sorted(path.glob("*.yaml"))
    ]
    return sorted(specs, key=lambda spec: spec.id)


__all__ = [
    "TERMINAL_OUTCOMES",
    "CaseSpec",
    "FaultInjection",
    "declared_outcomes",
    "load_cases",
]
