"""Deterministic emergency pre-check — the model does not delay a critical patient.

This module answers ONE question: *may the graph skip extraction for this case?* It
scores the already-structured case with the kernel's own pure scorer
(:func:`triagedesk.core.scorer.score_priority`) and fires only when that score is a
complete, in-scope result in the **most urgent** band.

The pre-check never emits a colour. Its verdict contract has no colour, priority,
target or destination field, so a pre-check colour is *unrepresentable* rather than
merely discouraged; the kernel's ``score_priority`` call remains the ONE colour
producer (CONVENTIONS §1/§2). The most urgent band is derived from the loaded
substrate through :func:`triagedesk.core.rules.colour_urgency` — the same
data-derived acuity order the waiting room uses — so no colour token or threshold is
inlined here.

No imputation: an abstained/out-of-scope case, or one missing a scored vital, never
fires and takes the normal extraction path. The module is pure: it imports nothing
from ``llm`` / ``mcp`` / ``store`` (enforced by ``tests/test_purity.py``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from triagedesk.core.rules import colour_urgency
from triagedesk.core.schema import CaseInput
from triagedesk.core.scorer import score_priority


class EmergencyVerdict(BaseModel):
    """Whether the deterministic pre-check may skip the model, and why (EMERG-01/02).

    ``fired`` is the routing decision; ``reason`` is a human-readable explanation and
    ``trigger`` holds the facts that made the case eligible (e.g. ``colour=…``,
    ``tews=…``). There is deliberately no colour, priority, target or destination
    field: the verdict is a *routing* fact, never a clinical one, so it cannot become a
    second colour producer (mirrors :class:`~triagedesk.core.schema.EvidencePassage`).
    """

    fired: bool
    reason: str = ""
    trigger: list[str] = Field(default_factory=list)


def _most_urgent_colour() -> str:
    """The most urgent colour, ranked by the ONE data-derived acuity order (D-01).

    ``core.rules.colour_urgency`` maps every colour to its band's lower TEWS bound; the
    highest bound is the most urgent band. No colour token is hard-coded (CONVENTIONS §1).
    """
    urgency = colour_urgency()
    return max(urgency, key=lambda colour: urgency[colour])


def assess_emergency(case: CaseInput) -> EmergencyVerdict:
    """Decide whether *case* may skip extraction — a pure read of the kernel's score.

    The case is scored with the exact function the kernel uses, with no discriminators
    (they are not yet retrieved on the fast arm). The check fires only when the score did
    not abstain, is in scope, reports no missing scored vital, and lands in the most
    urgent band. Every other outcome returns ``fired=False`` with a short reason, so the
    normal extraction path is taken and no value is guessed (EMERG-04).
    """
    priority = score_priority(case, [])
    if priority.abstained or priority.out_of_scope:
        return EmergencyVerdict(
            fired=False,
            reason=priority.reason or "the case did not score; the pre-check does not fire",
        )
    if priority.missing_vitals:
        return EmergencyVerdict(
            fired=False,
            reason="a scored vital is missing; the pre-check never fires on a partial case",
        )
    most_urgent = _most_urgent_colour()
    if priority.colour == most_urgent:
        return EmergencyVerdict(
            fired=True,
            reason="the deterministic score is in the most urgent band",
            trigger=[f"colour={priority.colour}", f"tews={priority.tews}"],
        )
    return EmergencyVerdict(
        fired=False,
        reason="the deterministic score is below the most urgent band",
    )
