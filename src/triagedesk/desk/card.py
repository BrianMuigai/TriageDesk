"""The desk priority card: render the graph's own typed outputs as a suggestion with its
citations and evidence (D10-05…D10-08).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from triagedesk.desk.copy import (
    _CARD_FRAMING,
    _NO_EVIDENCE_LINE,
    _READ_ONLY_FRAMING,
)
from triagedesk.desk.markup import _escaped


def _colour_class(colour: str) -> str:
    """Map a substrate colour string to its CSS swatch class (a lookup, never a computation).

    The colour NAMES live only in ``styles.css`` (an asset the no-duplicated-SATS guard does
    not scan), so no SATS colour literal enters Python.
    """
    return f"colour-{colour.lower()}"


def _why_vitals_rows(payload: Mapping[str, Any]) -> str:
    """One row per ``triggered_rules`` entry: its ``detail`` beside its own ``citation``.

    The baseline row is already one such entry (``core/scorer.py`` emits a ``tews_baseline``
    rule for the rule-less TEWS-0 case), so the card never reads the substrate's baseline
    citation directly (D10-06).
    """
    rules = payload.get("triggered_rules") or []
    return "".join(
        f'<li>{_escaped(rule.get("detail", ""))} '
        f'<span class="citation">{_escaped(rule.get("citation", ""))}</span></li>'
        for rule in rules
    )


def _evidence_rows(evidence: Any) -> str:
    """One ranked row per ``evidence.passages`` entry, or the verbatim no-evidence line.

    The evidence list is read from the paused state snapshot's ``evidence`` channel (the
    interrupt payload omits it) and is capped by the substrate's own ``MAX_PASSAGES``, never
    by the surface.
    """
    passages = (
        list(getattr(evidence, "passages", None) or []) if evidence is not None else []
    )
    if not passages:
        return f'<li class="no-evidence">{_escaped(_NO_EVIDENCE_LINE)}</li>'
    return "".join(
        f'<li><span class="evidence-label">{_escaped(passage.label)}</span> '
        f'<span class="citation">{_escaped(passage.citation)}</span></li>'
        for passage in passages
    )


def _card_html(
    payload: Mapping[str, Any], evidence: Any = None, *, read_only: bool = False
) -> str:
    """Render the priority card from the graph's own outputs (D10-02/D10-05…D10-08).

    Every value is read from the payload (or a payload built from the state snapshot) — the
    colour, its target, each fired rule's ``detail`` beside its adjacent citation, the
    evidence grounding it, the missing vitals, the second-look flag and the case id — and
    re-derived nowhere. The colour is rendered with its name as text (D10-08). ``read_only``
    swaps the framing line for the deferred/read-only card (D10-17); the card itself is the
    same presentation in both cases.
    """
    colour = str(payload.get("colour") or "")
    target = str(payload.get("target") or "")
    case_id = str(payload.get("case_id") or "")
    missing = payload.get("missing_vitals") or []
    second_look = payload.get("second_look")

    rows = _why_vitals_rows(payload)
    evidence_rows = _evidence_rows(evidence)
    missing_text = ", ".join(str(item) for item in missing) if missing else "None"
    if second_look:
        flagged = bool(second_look.get("flag"))
        deteriorations = second_look.get("deteriorations") or []
        second_text = (
            "Flagged: " + ", ".join(str(item) for item in deteriorations)
            if flagged
            else "Not flagged"
        )
    else:
        second_text = "—"

    framing = _READ_ONLY_FRAMING if read_only else _CARD_FRAMING
    return (
        '<section class="priority-card" aria-labelledby="card-heading">'
        '<h2 id="card-heading">Suggested priority</h2>'
        f'<p class="framing">{_escaped(framing)}</p>'
        f'<div class="colour-block {_escaped(_colour_class(colour))}">'
        f'<span class="colour-name">{_escaped(colour)}</span></div>'
        f'<p><span class="label">Suggested colour:</span> '
        f'<span class="value">{_escaped(colour)}</span></p>'
        f'<p><span class="label">Target time:</span> '
        f'<span class="value">{_escaped(target)}</span></p>'
        "<h3>Why these vitals:</h3>"
        f'<ul class="why-vitals-list">{rows}</ul>'
        "<h3>Evidence from the SATS knowledge base:</h3>"
        f'<ul class="evidence-list">{evidence_rows}</ul>'
        f'<p><span class="label">Not recorded:</span> '
        f'<span class="value">{_escaped(missing_text)}</span></p>'
        f'<p><span class="label">Second look (serial vitals):</span> '
        f'<span class="value">{_escaped(second_text)}</span></p>'
        f'<p><span class="label">Case:</span> '
        f'<span class="value">{_escaped(case_id)}</span></p>'
        "</section>"
    )


def _card_payload_from_state(state: Mapping[str, Any], thread_id: str) -> dict[str, Any]:
    """Build the card's payload-shaped facts from a paused STATE snapshot (D10-17/D10-19).

    The interrupt payload is absent on the deferred and repeat-submission paths, so the card
    facts are read from the state's typed ``priority``/``second_look`` objects. Nothing is
    re-derived: ``case_id`` is the paused thread id (the ONE content-derived id).
    """
    priority = state.get("priority")
    second_look = state.get("second_look")
    rules = (
        [rule.model_dump(mode="json") for rule in priority.triggered_rules]
        if priority is not None
        else []
    )
    return {
        "case_id": thread_id,
        "colour": getattr(priority, "colour", None),
        "target": getattr(priority, "target", None),
        "triggered_rules": rules,
        "missing_vitals": list(getattr(priority, "missing_vitals", None) or []),
        "second_look": (
            second_look.model_dump(mode="json") if second_look is not None else None
        ),
    }
