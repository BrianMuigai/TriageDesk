"""The ONE home for the run-outcome projection contract (DRY, SOLID: D).

Both the eval runner (``evals.runner``) and the demo (``demo.run``) read a run's outcome
through this module: the SAME 12-key captured-outcome dict of the graph's terminal facts
(``colour``, ``citations``, ``triggered_rules``, ``matched_ids``, ``recovery``,
``escalation``, ``second_look``, ``delivered``, ``route``, ``attempt``, ``confidence``,
``error``). Because the projection is consumed by two modules, it belongs in a third that
is neither of them.

It depends on no graph, store or model module: it reads the objects it is passed, so a
consumer supplies the graph result and interrupt payload without this module importing the
graph (SOLID: D, interface segregation).
"""

from __future__ import annotations

from typing import Any

__all__ = ["capture_outcome", "error_capture"]


def capture_outcome(result: Any, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Capture the outcome facts of one run from the interrupt payload or the end state.

    Reads the graph's own channels — never re-derives a colour or re-scores. When the run
    paused at the gate, the payload is the source (the colour and the evidence the
    clinician saw); otherwise the terminal state is read directly. The graph's terminal
    channels (``recovery``/``escalation``/``second_look``) are captured too, so the runner
    can map a first-class outcome without re-deriving one (ORCH-05).

    The graph's own TERMINAL facts are captured here as well: ``delivered`` is True only
    when the run produced a ``handover`` card (i.e. it reached the approval gate), and
    ``route``/``attempt`` are the graph's own routing channels. They distinguish a run
    delivered THROUGH the gate from one that aborted at ``END`` — never re-derived (G-2).
    """
    recovery = result.get("recovery")
    escalation = result.get("escalation")
    second_look = result.get("second_look")
    # The graph's OWN confidence channel (written by ``assess``) is read here — the runner
    # never re-derives the signal (D8-08, T-08-08). ``None`` when the run short-circuited
    # before ``assess`` (a recovery/abstention case that never reached the scored path).
    confidence = result.get("confidence")
    if payload is not None:
        colour = payload.get("colour")
        citations = list(payload.get("citations") or [])
        triggered = list(payload.get("triggered_rules") or [])
        matched = list(payload.get("matched_ids") or [])
    else:
        priority = result.get("priority")
        triggered = (
            [rule.model_dump(mode="json") for rule in priority.triggered_rules]
            if priority is not None
            else []
        )
        colour = priority.colour if priority is not None else None
        citations = list(priority.citations) if priority is not None else []
        matched = list(result.get("matched_ids") or [])
    return {
        "colour": colour,
        "citations": citations,
        "triggered_rules": triggered,
        "matched_ids": matched,
        "recovery": recovery is not None,
        "escalation": escalation is not None,
        "second_look": (
            second_look.model_dump(mode="json") if second_look is not None else None
        ),
        "delivered": result.get("handover") is not None,
        "route": result.get("route"),
        "attempt": int(result.get("attempt") or 0),
        "confidence": confidence.model_dump(mode="json") if confidence is not None else None,
        "error": None,
    }


def error_capture(exc: Exception) -> dict[str, Any]:
    """The fail-closed capture for a run whose graph invocation raised (WR-04).

    A run that raised before producing a result carries no colour, no terminal and no
    confidence signal; it is recorded with an explicit ``error`` so the runner's
    first-class-outcome mapping maps it to the declared ``ABORT`` outcome (a non-delivered
    run) and the runner surfaces the message in ``ReportCase.run_errors`` — never as the
    ``None`` a legitimate short-circuit-before-assess uses.
    """
    return {
        "colour": None,
        "citations": [],
        "triggered_rules": [],
        "matched_ids": [],
        "recovery": False,
        "escalation": False,
        "second_look": None,
        "delivered": False,
        "route": None,
        "attempt": 0,
        "confidence": None,
        "error": f"{type(exc).__name__}: {exc}",
    }
