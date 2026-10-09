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
