"""The ninth owned tool's four-outcome contract (Plan 21-01, ELICIT-01/03/06/08).

Every assertion here runs offline: a **fake** ``Context`` stands in for the transport, so the
tool's derivation, its spec-valid form, and its outcome mapping are proved without a
subprocess, a borrowed store or a model. The real end-to-end round-trip through the shipped
adapter is proved separately in ``tests/test_elicitation_roundtrip.py`` (Plan 21-02).

What is deliberately asserted:

* the question text comes **only** from ``core.coverage.question_for`` — the ONE owner — so a
  caller cannot author a question (ELICIT-06);
* an id outside the closed set is skipped, and more than
  ``coverage.MAX_CLARIFICATION_QUESTIONS`` candidates are trimmed;
* the form is spec-valid (one flat ``string`` property per question, no ``anyOf``/null);
* all four outcomes are distinguished, and only ``accepted`` carries answers (ELICIT-03);
* a transport failure that is neither a capability nor a back-channel problem **propagates**
  — a transport failure is never swallowed as a clinical answer;
* the answer contract cannot express a clinical value (ELICIT-08).
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from mcp.shared.exceptions import MCPError, NoBackChannelError
from mcp.types import MISSING_REQUIRED_CLIENT_CAPABILITY, InputRequiredResult
from pydantic import BaseModel, ConfigDict, PrivateAttr, ValidationError

from triagedesk.core import coverage
from triagedesk.core.rules import get_discriminators
from triagedesk.core.schema import (
    ClarificationAnswer,
    ElicitationOutcome,
    InterruptType,
)
from triagedesk.mcp import server as server_module

# The modern era (input-required round trips) and an older one (legacy back-channel).
_MODERN = "2026-07-28"
_LEGACY = "2025-11-25"


def _declared_ids(count: int) -> list[str]:
    """*count* ids from the loaded closed set — never a literal id (CONVENTIONS §1)."""
    return [item.id for item in get_discriminators().discriminators[:count]]


class _Capabilities(BaseModel):
    """A minimal stand-in for the SDK's ``ClientCapabilities`` (JSON-serialisable)."""

    elicitation: dict[str, Any] | None = None


class _FakeContext(BaseModel):
    """A fake MCP ``Context``: the four facts the tool reads, and one async ``elicit``.

    A pydantic model on purpose — the ONE ``@audited`` interceptor serialises every bound
    argument, so a fake that could not be dumped would fail the audit path rather than the
    behaviour under test. The error and the call log are private attributes, which
    ``model_dump`` excludes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    protocol_version: str = _MODERN
    input_responses: dict[str, Any] | None = None
    capabilities: _Capabilities = _Capabilities(elicitation={"form": {}})
    elicit_result: Any = None

    _error: BaseException | None = PrivateAttr(default=None)
    _calls: list[tuple[str, type]] = PrivateAttr(default_factory=list)

    def __init__(self, **data: Any) -> None:
        error = data.pop("elicit_error", None)
        super().__init__(**data)
        self._error = error

    @property
    def elicit_calls(self) -> list[tuple[str, type]]:
        return self._calls

    @property
    def client_capabilities(self) -> _Capabilities:
        return self.capabilities

    async def elicit(self, message: str, form: type) -> Any:
        self._calls.append((message, form))
        if self._error is not None:
            raise self._error
        return self.elicit_result


def _accepts(content: dict[str, str]) -> dict[str, Any]:
    """The resumed responses shape an accepting client sends (built by hand here, on purpose:
    the *server* side must not depend on the resume builder it is being tested against)."""
    return {"clarification": {"action": "accept", "content": content}}


def _action(name: str) -> dict[str, Any]:
    """The resumed responses shape for a refusal action."""
    return {"clarification": {"action": name}}


# --------------------------------------------------------------- the wire contract


def test_the_elicitation_interrupt_type_mirrors_the_adapter() -> None:
    """``InterruptType.ELICITATION`` equals the shipped adapter's own constant.

    The literal is declared in the pure contract module (so the CLI path never imports
    ``langchain.mcp`` and emits no beta warning); this assertion is what keeps that
    declaration honest against the driver that actually mints the payload.
    """
    from langchain.mcp.elicitation import ELICITATION_INTERRUPT_TYPE

    assert InterruptType.ELICITATION.value == ELICITATION_INTERRUPT_TYPE


def test_the_answer_contract_cannot_express_a_clinical_value() -> None:
    """A colour/priority cannot ride an answer, and a refusal cannot carry answers (ELICIT-08)."""
    accepted = ClarificationAnswer(outcome=ElicitationOutcome.ACCEPTED, answers=["crushing"])
    assert accepted.answers == ["crushing"]

    with pytest.raises(ValidationError):
        ClarificationAnswer(
            outcome=ElicitationOutcome.ACCEPTED, answers=["x"], colour="RED"  # type: ignore[call-arg]
        )

    for outcome in (
        ElicitationOutcome.DECLINED,
        ElicitationOutcome.CANCELLED,
        ElicitationOutcome.UNAVAILABLE,
    ):
        with pytest.raises(ValidationError):
            ClarificationAnswer(outcome=outcome, answers=["x"])


# --------------------------------------------------------------- derivation (ELICIT-06)


async def test_the_first_round_returns_a_spec_valid_form_of_derived_questions() -> None:
    """The first round asks; each property's description IS ``coverage.question_for``."""
    ids = _declared_ids(2)
    ctx = _FakeContext()

    result = await server_module.request_clarification(ids, ctx)

    assert isinstance(result, InputRequiredResult)
    requests = list(result.input_requests or {})
    assert requests == ["clarification"], "the tool mints exactly one form request"
    request = result.input_requests["clarification"]
    schema = request.params.requested_schema  # type: ignore[union-attr]
    assert schema["type"] == "object"
    properties = schema["properties"]
    assert list(properties) == ["q1", "q2"]
    for index, discriminator_id in enumerate(ids, start=1):
        prop = properties[f"q{index}"]
        assert prop["type"] == "string", "MCP elicitation admits primitive properties only"
        assert "anyOf" not in prop and prop["type"] != "null"
        # The question text is the ONE owner's, verbatim — never authored by the tool.
        assert prop["description"] == coverage.question_for(discriminator_id)
    assert ctx.elicit_calls == [], "the modern path must not touch the legacy back-channel"


async def test_an_unknown_candidate_is_skipped_and_a_known_one_is_still_asked() -> None:
    """An id outside the closed set is skipped, never asked (a data typo cannot crash a call)."""
    known = _declared_ids(1)[0]

    result = await server_module.request_clarification(
        ["not_a_declared_discriminator", known], _FakeContext()
    )

    assert isinstance(result, InputRequiredResult)
    properties = result.input_requests["clarification"].params.requested_schema["properties"]  # type: ignore[union-attr]
    assert list(properties) == ["q1"]
    assert properties["q1"]["description"] == coverage.question_for(known)


async def test_more_than_three_candidates_are_trimmed_to_the_one_bound() -> None:
    """At most ``coverage.MAX_CLARIFICATION_QUESTIONS`` questions — the classifier's bound."""
    ids = _declared_ids(5)
    assert len(ids) == 5

    result = await server_module.request_clarification(ids, _FakeContext())

    assert isinstance(result, InputRequiredResult)
    properties = result.input_requests["clarification"].params.requested_schema["properties"]  # type: ignore[union-attr]
    assert len(properties) == coverage.MAX_CLARIFICATION_QUESTIONS


async def test_no_known_candidate_is_unavailable_and_asks_nothing() -> None:
    """Nothing to ask is not an answer: the outcome is ``unavailable`` with a reason."""
    ctx = _FakeContext()

    result = await server_module.request_clarification(["nope"], ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.UNAVAILABLE
    assert result.answers == []
    assert result.reason
    assert ctx.elicit_calls == []


# --------------------------------------------------------------- the four outcomes


async def test_an_accepted_round_returns_the_answers_in_field_order() -> None:
    """Only ``accepted`` carries answers, in question order, with blanks dropped."""
    ids = _declared_ids(2)
    ctx = _FakeContext(
        input_responses=_accepts({"q1": "crushing central pain", "q2": "   "})
    )

    result = await server_module.request_clarification(ids, ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.ACCEPTED
    assert result.answers == ["crushing central pain"], "a blank field is not an observation"


async def test_an_accepted_round_keeps_the_question_order_not_the_dict_order() -> None:
    """Answers follow the form's field order even when the client returns them reordered."""
    ids = _declared_ids(2)
    ctx = _FakeContext(input_responses=_accepts({"q2": "second", "q1": "first"}))

    result = await server_module.request_clarification(ids, ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.answers == ["first", "second"]


async def test_a_declined_round_returns_no_answers() -> None:
    """A decline is not a negative clinical response and carries no value (ELICIT-03)."""
    result = await server_module.request_clarification(
        _declared_ids(1), _FakeContext(input_responses=_action("decline"))
    )

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.DECLINED
    assert result.answers == []


async def test_a_cancelled_round_returns_no_answers() -> None:
    """A cancel abandons the question and carries no value either."""
    result = await server_module.request_clarification(
        _declared_ids(1), _FakeContext(input_responses=_action("cancel"))
    )

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.CANCELLED
    assert result.answers == []


async def test_a_client_without_the_capability_is_unavailable() -> None:
    """No declared elicitation capability means the client cannot be asked (not a refusal)."""
    ctx = _FakeContext(capabilities=_Capabilities(elicitation=None))

    result = await server_module.request_clarification(_declared_ids(1), ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.UNAVAILABLE
    assert result.answers == []
    assert ctx.elicit_calls == [], "an incapable client is never asked"


async def test_an_in_process_caller_with_no_context_is_unavailable() -> None:
    """``ctx=None`` (the in-process tool map) is honestly unavailable, never fabricated."""
    result = await server_module.request_clarification(_declared_ids(1), None)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.UNAVAILABLE
    assert result.answers == []


async def test_a_missing_capability_error_is_unavailable() -> None:
    """The SDK's ``MISSING_REQUIRED_CLIENT_CAPABILITY`` maps to ``unavailable``."""
    ctx = _FakeContext(
        protocol_version=_LEGACY,
        elicit_error=MCPError(
            code=MISSING_REQUIRED_CLIENT_CAPABILITY, message="no elicitation capability"
        ),
    )

    result = await server_module.request_clarification(_declared_ids(1), ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.UNAVAILABLE


async def test_a_connection_without_a_back_channel_is_unavailable() -> None:
    """A legacy connection with no back-channel cannot ask — unavailable, not a value."""
    ctx = _FakeContext(
        protocol_version=_LEGACY, elicit_error=NoBackChannelError("elicitation/create")
    )

    result = await server_module.request_clarification(_declared_ids(1), ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.UNAVAILABLE


async def test_a_transport_failure_propagates_and_is_never_an_answer() -> None:
    """Any other exception is a failure, not a clinical answer — it must escape."""
    ctx = _FakeContext(protocol_version=_LEGACY, elicit_error=RuntimeError("socket closed"))

    with pytest.raises(RuntimeError, match="socket closed"):
        await server_module.request_clarification(_declared_ids(1), ctx)


# --------------------------------------------------------------- the legacy path


async def test_the_legacy_path_accepts_through_the_back_channel() -> None:
    """An older connection elicits through ``ctx.elicit`` and maps the accepted data."""
    ids = _declared_ids(2)

    class _AcceptingContext(_FakeContext):
        async def elicit(self, message: str, form: type) -> Any:
            self._calls.append((message, form))
            return AcceptedElicitation(data=form(q1="worse on exertion", q2=""))

    ctx = _AcceptingContext(protocol_version=_LEGACY)

    result = await server_module.request_clarification(ids, ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is ElicitationOutcome.ACCEPTED
    assert result.answers == ["worse on exertion"]
    assert len(ctx.elicit_calls) == 1


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (DeclinedElicitation(), ElicitationOutcome.DECLINED),
        (CancelledElicitation(), ElicitationOutcome.CANCELLED),
    ],
)
async def test_the_legacy_path_maps_both_refusals(
    outcome: Any, expected: ElicitationOutcome
) -> None:
    """The legacy path distinguishes a decline from a cancel, and neither carries answers."""
    ctx = _FakeContext(protocol_version=_LEGACY, elicit_result=outcome)

    result = await server_module.request_clarification(_declared_ids(1), ctx)

    assert isinstance(result, ClarificationAnswer)
    assert result.outcome is expected
    assert result.answers == []
