"""The ONE typed graph state (D-01, D-13).

``TriageState`` is the single channel definition every node reads from and writes
to. It is deliberately thin: it names the typed contract objects (from
``core.schema``) and nothing else, so the graph can never smuggle an untyped
value between nodes. It imports only ``core.schema`` — no model, no MCP client —
so the state shape is independent of how any edge is implemented (SOLID: D).
"""

from __future__ import annotations

from typing import TypedDict

from triagedesk.core.schema import (
    CaseInput,
    CommitResult,
    ConfidenceResult,
    Escalation,
    HandoverCard,
    PriorityResult,
    RecheckFlag,
    RecoveryRequest,
)


class TriageState(TypedDict, total=False):
    """The single graph state channel (D-01).

    Every field is optional (``total=False``) so each node returns a partial
    update: ``ingest`` seeds ``raw_note``/``attempt``; ``normalize`` adds ``case``;
    ``retrieve`` adds ``matched_ids``/``no_match``; ``score`` adds ``priority``;
    ``verify`` sets ``route`` (and bumps ``attempt`` on a retry); ``recheck`` adds
    ``second_look``; ``assess`` adds ``confidence``; ``approval_gate`` adds the
    resumed ``approval``; ``commit`` adds ``commit_result``; ``handover`` adds
    ``handover``. ``error`` is reserved for a fail-closed stop.
    """

    raw_note: str
    case: CaseInput | None
    matched_ids: list[str]
    no_match: bool
    priority: PriorityResult | None
    approval: dict | None
    commit_result: CommitResult | None
    handover: HandoverCard | None
    route: str | None
    error: str | None
    attempt: int
    # Safe terminals (ORCH-05, D-03): a typed recovery/escalation the graph stops on.
    recovery: RecoveryRequest | None
    escalation: Escalation | None
    # Serial-vitals second look (GATE-04, D-07): the previous case and the flag it raises.
    previous_case: CaseInput | None
    second_look: RecheckFlag | None
    # Deterministic coverage/deferral signal (AGENT-02, D8-08): written by ``assess`` and
    # consulted by ``route_after_assess``. It never reaches ``commit`` (D8-12).
    confidence: ConfidenceResult | None
