"""The interactive terminal surface — intake, gate and honest terminals (CLI-TRIAGE).

The surface is presentation only, so these tests pin the three things that could drift:

1. **Intake is the schema.** ``collect_case`` builds a ``CaseInput`` and re-prompts on a bad
   value; a blank vital stays ``None`` (never imputed) and a blank complaint is rejected.
2. **The gate still decides.** An ``approve`` writes exactly one queue row through the shipped
   seam; a ``dismiss`` writes none; a blank approver is refused by ``durable``, not by the CLI.
3. **An answer is not an approval.** The clarification form is built from the server's own
   requested schema and declines when nothing is typed; the terminal renderer never invents a
   card for a run that ended at a safe terminal.

No model and no borrowed subprocess: the offline tool map and the injected in-memory store are
the shared conftest seams.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from triagedesk.core.schema import ClarificationRequest, Escalation, HandoverCard
from triagedesk.desk.interactive import _clarification_form, collect_case, main, render_outcome

# One complete adult case, in the order ``collect_case`` asks it.
APPROVE_ANSWERS = [
    "40",  # age (years)
    "1",  # AVPU -> alert
    "24",  # respiratory rate
    "94",  # SpO2
    "118",  # heart rate
    "108",  # systolic
    "70",  # diastolic
    "38.9",  # temperature
    "1",  # mobility -> walking
    "n",  # trauma
    "central chest pain",  # complaint
    "1",  # decision -> approve
    "Dr Test",  # name
    "clinician",  # role
    "n",  # next patient?
]


def _scripted(answers: list[str], prompts: list[str] | None = None):
    """An ``ask`` callable that pops one scripted answer per prompt and records the prompt."""
    remaining = list(answers)

    def ask(prompt: str) -> str:
        if prompts is not None:
            prompts.append(prompt)
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return ask


def _told() -> tuple[list[str], object]:
    lines: list[str] = []
    return lines, lines.append


def test_collect_case_builds_the_one_schema_and_keeps_blanks_empty() -> None:
    """A blank vital stays ``None``; the typed fields land on ``CaseInput`` (INTAKE-01)."""
    answers = [
        "40",
        "1",
        "",  # respiratory rate skipped
        "",
        "118",
        "108",
        "",
        "38.9",
        "1",
        "n",
        "central chest pain",
    ]
    case = collect_case(_scripted(answers))

    assert case is not None
    assert case.age_years == 40
    assert case.respiratory_rate is None
    assert case.spo2 is None
    assert case.diastolic_bp is None
    assert case.complaint == "central chest pain"


def test_a_blank_complaint_is_re_prompted() -> None:
    """The graph has nothing to match without a complaint, so it is required (not guessed)."""
    prompts: list[str] = []
    answers = [
        "40",
        "1",
        "24",
        "94",
        "118",
        "108",
        "70",
        "38.9",
        "1",
        "n",
        "",  # blank complaint -> re-prompt
        "central chest pain",
    ]
    case = collect_case(_scripted(answers, prompts))

    assert case is not None
    assert case.complaint == "central chest pain"
    assert sum("Complaint" in prompt for prompt in prompts) == 2


def test_an_impossible_value_is_re_prompted_not_scored() -> None:
    """A wrong-unit temperature never reaches the scorer (T-01-01-03)."""
    answers = [
        "40",
        "1",
        "24",
        "94",
        "118",
        "108",
        "70",
        "104",  # Fahrenheit magnitude -> rejected
        "38.9",
        "1",
        "n",
        "central chest pain",
    ]
    case = collect_case(_scripted(answers))

    assert case is not None
    assert case.temperature_c == 38.9


def test_approve_writes_exactly_one_queue_row(
    tmp_path: Path, injected_store: Any
) -> None:
    """The terminal path reaches the shipped gate and commits one row (GATE-02)."""
    lines, tell = _told()
    code = main(
        db_path=tmp_path / "checkpoints.db",
        online=False,
        ask=_scripted(APPROVE_ANSWERS),
        tell=tell,
    )

    assert code == 0
    rows = injected_store.rows
    assert len(rows) == 1
    assert rows[0].colour == "ORANGE"
    assert any("Handover card" in line for line in lines)
    assert any("Dr Test" in line for line in lines)


def test_dismiss_writes_nothing(tmp_path: Path, injected_store: Any) -> None:
    """A dismissal commits nothing — the refusal is the gate's own behaviour (D-05)."""
    answers = APPROVE_ANSWERS[:11] + ["3", "n"]  # decision -> dismiss
    lines, tell = _told()
    code = main(
        db_path=tmp_path / "checkpoints.db",
        online=False,
        ask=_scripted(answers),
        tell=tell,
    )

    assert code == 0
    assert injected_store.rows == []
    assert any("not written" in line or "No priority delivered" in line for line in lines)


def test_a_blank_approver_never_commits(
    tmp_path: Path, injected_store: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """A blank identity cannot commit: the prompt re-asks, and running out of input stops.

    The prompt is an affordance; the enforcement is ``durable.approval_decision``. Either way
    the observable property is the one that matters: no row is written without a name.
    """
    answers = APPROVE_ANSWERS[:11] + ["1", ""]  # approve, blank name, then input runs out
    lines, tell = _told()
    code = main(
        db_path=tmp_path / "checkpoints.db",
        online=False,
        ask=_scripted(answers),
        tell=tell,
    )

    assert code == 0
    assert injected_store.rows == []
    assert "required" in capsys.readouterr().out


def test_the_clarification_form_declines_when_nothing_is_typed() -> None:
    """A blank answer is a decline, never an invented observation (ELICIT-03/08)."""
    payload = {
        "type": "mcp_elicitation",
        "requests": [
            {
                "mode": "form",
                "message": "One measurement would settle this.",
                "requested_schema": {
                    "properties": {"q1": {"type": "string", "description": "Capillary glucose"}}
                },
            }
        ],
    }
    form = _clarification_form(payload, _scripted([""]))

    assert form["action"] == "decline"
    assert "q1" not in form


def test_the_clarification_form_carries_typed_answers() -> None:
    """A typed answer rides the server's own field name (ELICIT-02)."""
    payload = {
        "type": "mcp_elicitation",
        "requests": [
            {
                "mode": "form",
                "message": "One measurement would settle this.",
                "requested_schema": {
                    "properties": {"q1": {"type": "string", "description": "Capillary glucose"}}
                },
            }
        ],
    }
    form = _clarification_form(payload, _scripted(["7.1 mmol/L"]))

    assert form["action"] == "accept"
    assert form["q1"] == "7.1 mmol/L"


def test_the_renderer_never_invents_a_card_for_a_safe_terminal() -> None:
    """An escalation prints the escalation, not an empty handover card (honesty)."""
    lines, tell = _told()
    render_outcome({"escalation": Escalation(reason="paediatric case")}, tell)

    assert any("No priority delivered" in line for line in lines)
    assert any("paediatric case" in line for line in lines)
    assert not any("Handover card" in line for line in lines)


def test_the_renderer_shows_the_clarification_questions() -> None:
    """A deferred-with-questions terminal names what is still missing."""
    lines, tell = _told()
    render_outcome(
        {
            "clarification": ClarificationRequest(
                questions=["What is the capillary glucose?"],
                candidates=["hypoglycaemia"],
                reason="the complaint is near a discriminator family but names none",
            )
        },
        tell,
    )

    assert any("capillary glucose" in line for line in lines)


def test_render_outcome_prints_a_committed_card() -> None:
    """A delivered card shows the committed colour, target and named approver (D-11)."""
    lines, tell = _told()
    render_outcome(
        {
            "handover": HandoverCard(
                case_id="abc",
                colour="ORANGE",
                target="< 10 min",
                citations=["SATS — heart_rate band"],
                decision="approve",
                approved_by="Dr Test",
                role="clinician",
            )
        },
        tell,
    )

    assert any("ORANGE" in line for line in lines)
    assert any("Dr Test" in line for line in lines)


@pytest.fixture(autouse=True)
def _no_stray_spans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Keep span output out of the repo root (the shared observability seam)."""
    from triagedesk.observability.spans import set_sink

    set_sink(tmp_path / "spans.jsonl")
    try:
        yield
    finally:
        set_sink(None)
