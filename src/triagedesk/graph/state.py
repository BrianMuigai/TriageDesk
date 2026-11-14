"""The ONE typed graph state (D-01, D-13).

``TriageState`` is the single channel definition every node reads from and writes
to. It is deliberately thin: it names the typed contract objects (from
``core.schema``) and nothing else, so the graph can never smuggle an untyped
value between nodes. It imports only ``core.schema`` — no model, no MCP client —
so the state shape is independent of how any edge is implemented (SOLID: D).
"""

from __future__ import annotations

from typing import TypedDict

from triagedesk.core.emergency import EmergencyVerdict
from triagedesk.core.schema import (
    CaseInput,
    ClarificationRequest,
    CommitResult,
    ConfidenceResult,
    Escalation,
    EvidenceResult,
    HandoverCard,
    InvestigationFacts,
    PlanDecision,
    PriorityResult,
    RecheckFlag,
    RecoveryRequest,
)


class TriageState(TypedDict, total=False):
    """The single graph state channel (D-01).

    Every field is optional (``total=False``) so each node returns a partial
    update: ``ingest`` seeds ``raw_note``/``attempt``; ``emergency_check`` adds
    ``emergency_verdict`` and the fast/normal ``route``; ``normalize`` adds ``case``;
    ``retrieve`` adds ``matched_ids``/``no_match``; ``score`` adds ``priority``;
    ``ground`` adds ``evidence``; ``verify`` sets ``route`` and records a failed
    check in ``attempt``; a failure is terminal. ``recheck`` adds ``second_look``;
    ``assess`` adds ``confidence``;
    ``approval_gate`` adds the resumed ``approval``; ``commit`` adds
    ``commit_result``; ``handover`` adds ``handover``. ``error`` is reserved for a
    fail-closed stop.
    """

    raw_note: str
    case: CaseInput | None
    matched_ids: list[str]
    no_match: bool
    # Retrieval coverage classification (COV-01): written by ``retrieve`` from the
    # matcher's own contract. ``retrieval_status``/``candidates``/``questions`` decide
    # ONLY whether ``assess`` asks for a clarification — they never add a scored id.
    retrieval_status: str
    candidates: list[str]
    clarification_questions: list[str]
    clarification_round: int
    priority: PriorityResult | None
    # Deterministic emergency pre-check (EMERG-01/02, EMERG-05): written by
    # ``emergency_check`` BEFORE ``normalize``. ``fired`` selects the fast arm, which skips
    # extraction only; the verdict carries no colour and the kernel still scores.
    emergency_verdict: EmergencyVerdict | None
    approval: dict | None
    commit_result: CommitResult | None
    handover: HandoverCard | None
    route: str | None
    error: str | None
    attempt: int
    # Safe terminals (ORCH-05, D-03): a typed recovery/escalation the graph stops on.
    recovery: RecoveryRequest | None
    escalation: Escalation | None
    # Bounded clarification terminal (COV-03): at most three questions, no colour,
    # no gate, no commit. One answer round may follow before a deferral.
    clarification: ClarificationRequest | None
    # Serial-vitals second look (GATE-04, D-07): the previous case and the flag it raises.
    previous_case: CaseInput | None
    second_look: RecheckFlag | None
    # Deterministic coverage/deferral signal (AGENT-02, D8-08): written by ``assess`` and
    # consulted by ``route_after_assess``. It never reaches ``commit`` (D8-12).
    confidence: ConfidenceResult | None
    # Attributable retrieval grounding (AGENT-03, D9-07/D9-08): written by ``ground`` and
    # consulted by NOTHING that routes. Advisory display/provenance only — no conditional
    # edge or router reads it, so the path taken (and the scored colour) is unchanged. It
    # needs no reducer: ``ground`` is the only writer and its value is a pure function of
    # the complaint (last-write-wins is correct).
    evidence: EvidenceResult | None
    # The bounded investigation loop (ADAPT-01/06). ``plan`` is the current decision and
    # ``investigation`` the typed accumulator; both have exactly ONE writer — the ``plan``
    # node — so the step counter and the action history cannot be advanced twice. The
    # emergency arm skips ``plan`` entirely, so both stay unset on that path.
    plan: PlanDecision | None
    investigation: InvestigationFacts
    # The nurse's accepted clarification answers (ELICIT-08): observations appended to the
    # case facts, never an approval and never a colour. ONE writer (``ask_question``); the
    # ``retrieve`` node re-matches against the note plus these answers.
    nurse_answers: list[str]
    # The four-way elicitation outcome seen on the last ``ask_question`` visit
    # (``accepted`` / ``declined`` / ``cancelled`` / ``unavailable``), written on EVERY
    # outcome — not only an acceptance — so the eval harness reports what actually happened
    # instead of re-deriving it from the audit log (MEAS-01). Never read by a router and
    # never a clinical fact: a decline is not a negative finding.
    elicitation_outcome: str | None
