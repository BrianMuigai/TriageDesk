"""The ONE schema module (D-14).

Imported by the MCP tool contracts, the Ollama ``format=`` JSON schema, and
(later) graph state. This module is pure: no I/O, and it imports nothing from
``llm`` / ``mcp`` / ``store`` (D-13).

The model may only *structure* a note and *select* discriminator ids from a
closed set — it never computes a TEWS score or a colour (D-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from triagedesk.core.rules import get_tews

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


ConfidenceLevel = Literal["high", "moderate", "low"]


class ConfidenceComponent(BaseModel):
    """One component of the deterministic coverage/deferral signal (D8-01).

    ``satisfied`` records positive evidence for the component — a fully-covered
    vital set, a matched discriminator, a firing override, or a case far from a
    TEWS band edge — and ``detail`` is a human-readable count/boolean phrase. There
    is deliberately no numeric weight, score or probability field: the component is
    evidence and a boolean, never a clinical risk figure (D8-02, D8-04).
    """

    name: str
    satisfied: bool = False
    detail: str = ""


class ConfidenceResult(BaseModel):
    """The deterministic coverage/deferral signal (D8-02, D8-04).

    A pure function of the typed case, the matched discriminator ids and the scored
    ``PriorityResult`` — never of a model probability, logprob or token count
    (D8-01). It carries a ``deferral`` decision, a small closed-set ``level``, the
    per-component breakdown and a human-readable ``reason``. There is deliberately
    no percentage and no float ``score``/``probability`` field: a model-derived
    number is *unrepresentable* rather than merely discouraged (D8-04). The signal
    can only ever make the system more cautious — a deferral routes to ``escalate``
    or ``request_missing_info`` and never reaches ``commit`` (D8-12).
    """

    deferral: bool = False
    level: ConfidenceLevel = "high"
    components: list[ConfidenceComponent] = Field(default_factory=list)
    reason: str = ""


class VitalChange(BaseModel):
    """One scored vital compared across two serial cases (D-08).

    ``before``/``after`` carry the raw value on each side (numeric, categorical or
    boolean); ``points_before``/``points_after`` are its TEWS band points read from
    ``data/sats_tews.yaml``. A move to a higher-points band is a deterioration.
    """

    parameter: str
    before: float | int | str | bool | None = None
    after: float | int | str | bool | None = None
    points_before: int
    points_after: int


class RecheckFlag(BaseModel):
    """Second-look flag from serial vitals — never a colour, never a reorder (D-08).

    ``flag`` is ``True`` when at least one scored vital moved to a higher-points
    TEWS band; ``deteriorations`` names those vitals; ``changes`` carries the
    before/after value and band points of every compared vital. There is
    deliberately no colour field: this result never re-classifies and never touches
    the queue (TOOL-04, T-02-10).
    """

    flag: bool = False
    deteriorations: list[str] = Field(default_factory=list)
    changes: list[VitalChange] = Field(default_factory=list)
    reason: str | None = None


class RecoveryRequest(BaseModel):
    """A re-measure request for a case missing a scored vital (ORCH-05, D-03).

    ``missing_vitals`` names the scored TEWS parameters absent from the case and
    ``reason`` carries the human-readable re-measure instruction. There is
    deliberately no colour field: the recovery terminal never scores and never
    guesses a value (D-03).
    """

    missing_vitals: list[str] = Field(default_factory=list)
    reason: str


class Escalation(BaseModel):
    """A safe abstention/escalation terminal (ORCH-05, D-03).

    ``reason`` states why the case could not be scored — an out-of-scope
    (paediatric / missing / ambiguous age) case, or an extraction that exhausted
    its bounded retry with no structured fallback. There is deliberately no colour
    field: an abstained case never receives an adult colour (D-03).
    """

    reason: str


class ApprovalToken(BaseModel):
    """The named-clinician approval the queue-affecting gate requires (D-05, TOOL-05).

    A well-formed ``approve``/``edit`` token names an approver and a role, records its
    decision, carries the ``approved_at`` timestamp, and states the ``final_colour`` the
    clinician authorised. ``final_colour`` is the ONE place an ``edit`` decision records the
    colour the clinician chose, so the committed colour is always the approved colour and
    never a re-derived one (D-05). The value is validated against the colour set read from
    the loaded substrate (``data/sats_tews.yaml``), never a hard-coded literal
    (CONVENTIONS §1).

    A ``dismiss`` is a legitimate refusal the gate never commits, so it carries **no**
    approver and **no** colour — only the decision and its timestamp (T-06-05). The identity
    and colour requirements are therefore enforced for ``approve``/``edit`` by
    :meth:`_identity_and_colour_required`, not by field-level ``min_length``; that placement
    is what lets the gate's ``dismiss`` branch be *reached* (rather than the token being
    rejected as malformed first), and what rejects a whitespace-only identity (WR-05/WR-06).

    ``commit_priority`` validates this shape and refuses anything else; the refusal decision
    is the ONE place the gate distinguishes a dismissal from a malformed token.
    """

    decision: Literal["approve", "edit", "dismiss"]
    approved_at: datetime
    approved_by: str = ""
    role: str = ""
    final_colour: str = ""

    @model_validator(mode="after")
    def _identity_and_colour_required(self) -> ApprovalToken:
        """Require a named clinician and a declared colour unless the decision is a dismiss.

        A ``dismiss`` short-circuits: the gate refuses it and writes nothing, so it needs no
        identity and no colour (T-06-05). For ``approve``/``edit`` the approver and role must
        be non-blank (a whitespace-only value counts as absent, so a fabricated blank identity
        can never approve — WR-06) and ``final_colour`` must name a colour declared by the
        loaded TEWS substrate (CONVENTIONS §1).
        """
        if self.decision == "dismiss":
            return self
        for name in ("approved_by", "role"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required for a {self.decision!r} decision")
        if not self.final_colour.strip():
            raise ValueError(f"final_colour is required for a {self.decision!r} decision")
        allowed = {band.colour for band in get_tews().tews_to_colour}
        if self.final_colour not in allowed:
            raise ValueError(
                f"final_colour {self.final_colour!r} is not a colour declared "
                "by the loaded substrate"
            )
        return self


class CommitResult(BaseModel):
    """The gated commit tool's contract (D-05, D-06).

    ``refused`` is ``True`` when no well-formed approval token was supplied (or the
    token was malformed, or the decision was ``dismiss``), in which case nothing is
    written. ``committed`` is ``True`` once the idempotent queue write has run through
    the injectable store seam; a repeat commit of identical content also returns
    ``committed=True`` but inserts no second row (GATE-03).
    """

    committed: bool = False
    refused: bool = False
    reason: str | None = None


class HandoverCard(BaseModel):
    """The clinician-facing handover card (D-11, SAFE-02).

    Renders the structured, sourced facts of one triage decision: the priority, its
    citations, the missing vitals, the matched discriminators and the named approval.
    It carries **no** diagnosis, assessment, impression, plan or prescription field —
    the *absence* of a field is the guard: the schema cannot express a clinical
    opinion, so the tool can never emit one (D-11). ``second_look`` carries the
    serial-vitals flag when one exists, and never re-classifies (D-08).

    The field set is **locked** two ways: ``extra="forbid"`` rejects any undeclared
    field at construction (a prose field cannot be smuggled onto the card), and
    ``FORBIDDEN_FIELD_TOKENS`` names the assessment-prose vocabulary that no field
    may contain. The guard test reads that ONE tuple, so the token list is not
    restated in the suite (DRY).
    """

    # An undeclared field is rejected rather than silently carried (SAFE-02, D-11).
    model_config = ConfigDict(extra="forbid")

    # The assessment-prose tokens no HandoverCard field may contain. Declared HERE,
    # the ONE source the guard test reads (SAFE-02, D-11, CONVENTIONS §1).
    FORBIDDEN_FIELD_TOKENS: ClassVar[tuple[str, ...]] = (
        "summary",
        "assessment",
        "impression",
        "plan",
        "diagnosis",
        "prescription",
        "dx",
        "rx",
    )

    case_id: str
    colour: str | None = None
    target: str | None = None
    citations: list[str] = Field(default_factory=list)
    triggered_rules: list[TriggeredRule] = Field(default_factory=list)
    missing_vitals: list[str] = Field(default_factory=list)
    matched_discriminator_ids: list[str] = Field(default_factory=list)
    no_discriminator_matched: bool = False
    second_look: RecheckFlag | None = None
    decision: str | None = None
    approved_by: str | None = None
    role: str | None = None
