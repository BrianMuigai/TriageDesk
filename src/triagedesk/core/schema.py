"""The ONE schema module (D-14).

Imported by the MCP tool contracts, the Ollama ``format=`` JSON schema, and
(later) graph state. This module is pure: no I/O, and it imports nothing from
``llm`` / ``mcp`` / ``store`` (D-13).

The model may only *structure* a note and *select* discriminator ids from a
closed set — it never computes a TEWS score or a colour (D-03).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mobility = Literal["walking", "with_help", "stretcher"]
AVPU = Literal["alert", "voice", "pain", "unresponsive"]


class CaseInput(BaseModel):
    """What the nurse provides (INTAKE-01).

    Every vital is nullable and defaults to ``None`` — a missing vital is
    represented honestly and is never imputed (Roadmap SC2).

    Each field carries a *plausible physiological* range so that an impossible or
    wrong-unit value is rejected instead of silently scored (T-01-01-03). These
    bounds are a schema concern and are deliberately distinct from the SATS TEWS
    scoring bands, which live only in ``data/sats_tews.yaml`` (CONVENTIONS §1).
    """

    age_years: int | None = Field(default=None, ge=0, le=130)
    # A months-expressed or ambiguous age is representable so the scorer can fail
    # closed (Roadmap SC2): only an unambiguous adult-year integer may be scored.
    age_months: int | None = Field(default=None, ge=0, le=1560)
    age_ambiguous: bool = False
    height_cm: float | None = Field(default=None, ge=30.0, le=260.0)
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    heart_rate: int | None = Field(default=None, ge=0, le=350)
    systolic_bp: int | None = Field(default=None, ge=0, le=400)
    diastolic_bp: int | None = Field(default=None, ge=0, le=300)  # captured, not scored (§4.1)
    temperature_c: float | None = Field(default=None, ge=20.0, le=45.0)  # rejects °F magnitudes
    spo2: int | None = Field(default=None, ge=0, le=100)  # captured, not scored (§4.1)
    mobility: Mobility | None = None
    avpu: AVPU | None = None
    trauma: bool | None = None
    complaint: str = ""  # UNTRUSTED free text (SECURITY.md T-1)


class ExtractionResult(BaseModel):
    """What the model may return — schema-constrained, then validated.

    No numbers are computed here; the model selects discriminator ids from the
    closed set defined by the discriminator data (D-03). The closed set itself
    lives in ``data/sats_discriminators.yaml`` (Phase 01-02), never in code.
    """

    case: CaseInput
    matched_discriminator_ids: list[str] = Field(default_factory=list)
    no_discriminator_matched: bool = False  # coverage signal (v1 field)


class TriggeredRule(BaseModel):
    """One TEWS rule that fired — the unit the citations are derived from (D-01).

    ``rule_id`` is the structural parameter key from the loaded data (never a
    clinical value); ``detail`` is a human-readable ``parameter=value -> points``
    string; ``citation`` is produced by the one citation helper.
    """

    rule_id: str
    detail: str
    points: int
    citation: str


class PriorityResult(BaseModel):
    """The pure scorer's contract (D-01).

    The invariant ``len(citations) == len(triggered_rules)`` is fixed: every
    fired rule is cited exactly once (SCORE-03). A failed-closed (out-of-scope or
    abstained) result carries no colour, no total and no citations.
    """

    colour: str | None = None
    tews: int | None = None
    target: str | None = None
    destination: str | None = None
    triggered_rules: list[TriggeredRule] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    matched_discriminator_ids: list[str] = Field(default_factory=list)
    missing_vitals: list[str] = Field(default_factory=list)
    used_vitals: list[str] = Field(default_factory=list)
    out_of_scope: bool = False
    abstained: bool = False
    reason: str | None = None


class MatchResult(BaseModel):
    """The deterministic discriminator matcher's contract (D-05, D-06).

    ``matched_ids`` are always members of the closed discriminator set declared
    in ``data/sats_discriminators.yaml`` (D-06), sorted so repeated identical
    input yields an identical list. When nothing matches, ``no_match`` is ``True``
    and ``warning`` carries the declared coverage-gap warning — the matcher never
    guesses an id (SAFE-01).
    """

    matched_ids: list[str] = Field(default_factory=list)
    no_match: bool = False
    warning: str | None = None
