"""Pure serial-vitals recheck (D-08, TOOL-04, T-02-10).

Two typed cases are compared purely: for every scored TEWS parameter, the band
points of the previous and current value are read from ``data/sats_tews.yaml`` and
a move to a *higher-points* band is a deterioration. The result is a second-look
flag carrying the before/after values — never a colour. This module never
re-classifies and has no queue or store access (D-08, M-4).

Pure module: it imports nothing from ``llm`` / ``mcp`` / ``store`` (D-13) and
reuses the ONE band-selection authority (``core.scorer.band_points``), so the
deterioration direction is derived from the data rather than a hard-coded
threshold (CONVENTIONS §1/§2).
"""

from __future__ import annotations

from triagedesk.core.rules import get_tews
from triagedesk.core.schema import CaseInput, RecheckFlag, VitalChange
from triagedesk.core.scorer import band_points, case_field

_FLAG_REASON = "serial vitals show deterioration; a second look is required"


def compare_vitals(previous: CaseInput, current: CaseInput) -> RecheckFlag:
    """Compare *previous* and *current* serial vitals into a second-look flag (D-08).

    For each scored TEWS parameter present on both sides, the before/after value
    and its band points are recorded; a vital whose band points rose is listed as
    a deterioration. The returned ``RecheckFlag`` has no colour: this function
    never re-classifies and never touches the queue (T-02-10).
    """
    rules = get_tews()
    changes: list[VitalChange] = []
    deteriorations: list[str] = []
    for name, param in rules.parameters.items():
        field = case_field(name)
        before = getattr(previous, field, None)
        after = getattr(current, field, None)
        if before is None or after is None:
            continue  # a vital absent on either side cannot be compared
        points_before = band_points(param, before)
        points_after = band_points(param, after)
        changes.append(
            VitalChange(
                parameter=name,
                before=before,
                after=after,
                points_before=points_before,
                points_after=points_after,
            )
        )
        if points_after > points_before:
            deteriorations.append(name)
    return RecheckFlag(
        flag=bool(deteriorations),
        deteriorations=deteriorations,
        changes=changes,
        reason=_FLAG_REASON if deteriorations else None,
    )
