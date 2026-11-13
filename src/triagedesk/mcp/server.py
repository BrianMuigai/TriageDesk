"""Owned MCP server (SDK v2, stdio) exposing the nine triage tools (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. Every tool returns a shared ``core.schema`` contract (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/`` + ``store/``; nothing depends on this server except
the adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.

``commit_priority`` is the ONE queue-affecting tool. It is the real gated write: it
validates the approval token, REFUSES (touching no store) when the token is absent,
malformed or a ``dismiss``, and otherwise performs the idempotent queue write through
the injectable :class:`~triagedesk.store.Store` seam (D-05, D-06, GATE-02/03).

``plan_next_step`` and ``request_clarification`` are the two v1.3 tools that **exist and are
allowlisted but are not yet called by any graph node** (Phase 23 wires the ``plan`` node), so
the shipped graph still runs the seven-tool path. Do not describe the surface as "nine
shipped tools": seven are on the shipped path, two are substrate.

Every tool is wrapped by ONE uniform interceptor (:func:`audited`) that appends exactly
one chained audit record per call through ``store/audit.append``, so no owned tool call
escapes the audit (AUDIT-01, AUDIT-03, D-08).
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import MCPServer
from mcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    render_elicitation_schema,
)
from mcp.server.mcpserver.context import Context
from mcp.shared.exceptions import MCPError, NoBackChannelError
from mcp.types import (
    MISSING_REQUIRED_CLIENT_CAPABILITY,
    ElicitRequest,
    ElicitRequestFormParams,
    InputRequiredResult,
)
from mcp.types.version import is_version_at_least
from pydantic import BaseModel, Field, ValidationError, create_model

from triagedesk.core import (
    confidence,
    coverage,
    grounding,
    matcher,
    planner,
    recheck,
    retrieval,
    scorer,
)
from triagedesk.core.approval import committed_colour, target_for_colour
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    ClarificationAnswer,
    CommitResult,
    ConfidenceResult,
    ElicitationOutcome,
    EvidenceResult,
    ExtractionResult,
    InvestigationState,
    MatchResult,
    PlanDecision,
    PriorityResult,
    RecheckFlag,
)
from triagedesk.llm.client import extract_async, propose_plan_async
from triagedesk.mcp.elicitation import CLARIFICATION_REQUEST_KEY, answer_field
from triagedesk.observability import current_trace_id, span
from triagedesk.store import Store, default_store
from triagedesk.store.audit import append
from triagedesk.store.queue import commit_to_queue

# The owned server. Name is positional; everything else is keyword (SDK v2).
server = MCPServer("triagedesk-triage", version="0.1.0")

# The injectable store seam (D-13, SOLID: D): the commit path depends on the Store
# protocol, not on the borrowed implementation. Tests inject an in-memory fake; the
# production default is the borrowed SQLite MCP server (D-10). ``None`` means "resolve
# the default on demand".
_store: Store | None = None


def set_store(store: Store | None) -> None:
    """Inject (or clear) the store seam the commit path resolves (D-13).

    Tests pass an in-memory ``Store`` double so the suite never launches the borrowed
    subprocess; passing ``None`` restores the borrowed default (D-10).
    """
    global _store
    _store = store


async def resolve_store() -> Store:
    """Resolve the store through the injectable seam, else the borrowed factory (D-10, D-13).

    The published store-resolution seam: the commit path, the durable demo's ``--durable``
    flow and the read-only replay projection all resolve their store through THIS, never a
    concrete import, so a World-B store swap is a single injection (SOLID: D/L) and there is
    exactly one resolver (DRY).
    """
    if _store is not None:
        return _store
    return await default_store()


@asynccontextmanager
async def store_seam(
    store: Store | None = None,
    *,
    default: Callable[[], Store] | None = None,
) -> AsyncIterator[Store]:
    """Install the store seam for the duration of one block — the ONE install path (D-13).

    The single place the seam is *held*: it resolves the store once — the injected
    ``store`` when given, else a caller's offline ``default`` factory, else the ONE
    resolver :func:`resolve_store` (the borrowed default) — installs it through
    :func:`set_store`, yields that SAME instance so the caller reads what it installed,
    and always clears the seam to ``None`` in a ``finally``.

    The restore always resets to ``None`` (never a saved prior store): an offline run
    installs an in-memory double that must never leak into a later call, so the seam's
    post-condition is the borrowed default, exactly as :func:`set_store`'s contract
    states. Callers therefore never repeat the resolve/install/restore ceremony.
    """
    if store is not None:
        resolved = store
    elif default is not None:
        resolved = default()
    else:
        resolved = await resolve_store()
    set_store(resolved)
    try:
        yield resolved
    finally:
        set_store(None)


def _jsonable(value: Any) -> Any:
    """Reduce a tool input/output to a plain JSON structure (the ONE normaliser).

    Pydantic contracts are dumped in JSON mode; everything else is passed through
    unchanged. This keeps untrusted complaint text serialisable through the one
    canonical path (M-13) without the server restating a serialisation concern.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def audited(*, approval: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap ONE owned tool so its call appends exactly one chained record (AUDIT-01).

    The single interceptor, applied uniformly to every ``@server.tool()`` (DRY, T-03-15):
    the tool body stays free of audit code, and no owned tool call escapes the audit
    (AUDIT-03). The record's ``tool`` is the wrapped function's own name, so the audit
    name can never drift from the registered tool name.

    The append happens AFTER the tool's own logic, so a refused commit is still recorded
    as a refused call — the audit never claims a write that did not happen. ``approval``
    marks the gated commit: the record's actor is the clinician, and on a successful
    commit it carries the named approver and role from the validated token (AUDIT-02).

    Alongside the audit record, the wrapper opens ONE ``tool`` span around the call
    (D7-01) and the record carries the current content-derived ``trace_id`` (D7-06), so
    the record joins to its spans in the local stream. The audit behaviour is otherwise
    unchanged: exactly one chained record per call, refusal path and actor/approver logic
    untouched (D-18).
    """
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = fn.__name__
        signature = inspect.signature(fn)

        async def record(
            args: tuple[Any, ...], kwargs: dict[str, Any], result: Any, error: str | None
        ) -> None:
            try:
                bound = signature.bind(*args, **kwargs)
                bound.apply_defaults()
                inputs = {name: _jsonable(value) for name, value in bound.arguments.items()}
            except TypeError:
                inputs = {}
            outputs = _jsonable(result)
            if error is not None:
                outputs = {"error": error}
            elif not isinstance(outputs, dict):
                outputs = {"result": outputs}
            approved_by: str | None = None
            role: str | None = None
            if approval and bool(getattr(result, "committed", False)):
                token = inputs.get("approval_token")
                if isinstance(token, Mapping):
                    approved_by = token.get("approved_by")
                    role = token.get("role")
            store = await resolve_store()
            await append(
                store,
                {
                    "case_id": str(inputs.get("case_id") or ""),
                    "tool": tool_name,
                    "actor": "clinician" if approval else "agent",
                    "inputs": inputs,
                    "outputs": outputs,
                    "approved_by": approved_by,
                    "role": role,
                    "trace_id": current_trace_id(),
                },
            )

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            trace_id = current_trace_id()
            try:
                with span("tool", tool_name, attributes={"trace_id": trace_id}):
                    result = fn(*args, **kwargs)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as exc:  # noqa: BLE001 — the tool boundary is external
                await record(args, kwargs, None, f"{type(exc).__name__}: {exc}")
                raise
            await record(args, kwargs, result, None)
            return result

        return wrapper

    return decorate


@server.tool()
@audited()
async def normalize_case(raw_note: str) -> ExtractionResult:
    """Parse a triage note into the typed case schema. Read-only.

    Single-purpose and contract-typed: it returns the one shared
    ``ExtractionResult`` schema (D-14), so the server contract and the model
    contract cannot drift. Read-only — it never writes to the queue (D-06).

    The extraction is awaited through the async transport, so a slow model call no
    longer pins the event loop. The contract, the read-only guarantee and the
    closed-set filter are unchanged: the model may only *structure* a note and
    *select* ids; it may not choose a discriminator outside the closed set, and an
    id now also needs one of its declared aliases in the note. Model-returned ids
    are therefore filtered to the declared set (unknown ids dropped) and grounded
    against the note (unevidenced ids dropped), with ``no_discriminator_matched``
    following what survives (T-02-11, T-14-01). Missing vitals stay ``None`` — never
    imputed.
    """
    result = await extract_async(raw_note)
    return grounding.ground_extraction(result, raw_note)


@server.tool()
@audited()
def score_priority(
    case: CaseInput,
    matched_discriminator_ids: list[str] | None = None,
) -> PriorityResult:
    """Score a typed case deterministically — no model on this path (D-02).

    A thin, contract-typed adapter over the pure ``core.scorer.score_priority``
    function (SOLID: S/D): it touches no model and cannot inject a colour. The
    returned ``PriorityResult`` carries the colour, TEWS total, target time and
    one citation per triggered rule.

    The tool contract fails closed on an incomplete case: when a scored vital is
    absent it returns ``abstained=True`` with no colour, no total and no citations,
    naming the missing vitals in ``reason``. The shipped graph already routes on
    ``missing_vitals``; this guard protects a caller that invokes the MCP tool
    directly and would otherwise see a GREEN with no evidence (nurse stress test
    S1-4, SAFE-01).
    """
    priority = scorer.score_priority(case, matched_discriminator_ids)
    if not priority.missing_vitals:
        return priority
    missing = ", ".join(priority.missing_vitals)
    return priority.model_copy(
        update={
            "colour": None,
            "tews": None,
            "target": None,
            "destination": None,
            "triggered_rules": [],
            "citations": [],
            "abstained": True,
            "reason": f"missing scored vitals: {missing}; re-measure before scoring",
        }
    )


@server.tool()
@audited()
def assess_confidence(
    matched_ids: list[str],
    no_match: bool,
    priority: PriorityResult,
    retrieval_status: str = "matched",
    candidates: list[str] | None = None,
    questions: list[str] | None = None,
    clarification_round: int = 0,
) -> ConfidenceResult:
    """Return the deterministic coverage signal — no model, no store (D8-07, COV-03).

    A thin, contract-typed adapter over the pure ``core.confidence.assess`` function
    (SOLID: S/D): it reads only the typed inputs it uses and returns the confidence
    contract. It takes no ``CaseInput``, so the declared tool contract cannot carry a
    field the signal ignores (WR-03). It touches no store, writes no queue row and takes
    no approval token; the signal can only route the graph to a more cautious terminal
    (clarify, defer or recovery), never to the commit (D8-07, D8-12).

    The coverage arguments are the matcher's own classification (COV-01): they can turn
    a deferral into a bounded clarification or a vitals-only delivery, and they never
    add a scored discriminator or a colour.
    """
    return confidence.assess(
        matched_ids,
        no_match,
        priority,
        retrieval_status=retrieval_status,
        candidates=candidates,
        questions=questions,
        clarification_round=clarification_round,
    )


@server.tool()
@audited()
def match_discriminators(complaint: str, note: str = "") -> MatchResult:
    """Match a free-text complaint to closed-set discriminator ids (D-05, D-06).

    A thin, contract-typed adapter over the pure ``core.matcher`` function
    (SOLID: S/D): a deterministic alias lookup with no model and no fuzzy
    judgement. It returns ids from the closed discriminator set only, or an
    explicit ``no_match`` result — never a guessed id (SAFE-01).

    ``note`` is optional context for the coverage classifier only (COV-01): a stated
    condition such as "known diabetic" can turn a vague complaint into a targeted
    clarification. It never adds an id to ``matched_ids`` and never sets a colour.
    """
    matched = matcher.match_discriminators(complaint)
    verdict = coverage.classify(complaint, note or complaint)
    return matched.model_copy(
        update={
            "retrieval_status": verdict.status,
            "candidates": list(verdict.candidates),
            "questions": list(verdict.questions),
        }
    )


@server.tool()
@audited()
def retrieve_evidence(complaint: str) -> EvidenceResult:
    """Return attributed SATS KB excerpts for a complaint — read-only, no queue effect (D9-06).

    A thin, contract-typed adapter over the pure ``core.retrieval.retrieve`` function
    (SOLID: S/D): it carries no audit code of its own — the ONE ``@audited`` interceptor
    supplies its audit record and ``tool`` span. Its own logic touches no store and sets
    no queue row and no approval token (D9-06); the uniform ``@audited`` interceptor does
    record the call (AUDIT-01). It reads only the loaded ``data/*.yaml`` substrate through
    the one loader, and returns a contract with no colour field, so it can *show* grounding
    but can never *set* a priority (D9-03).
    """
    return retrieval.retrieve(complaint)


@server.tool()
@audited()
def raise_recheck_flag(previous: CaseInput, current: CaseInput) -> RecheckFlag:
    """Compare serial vitals into a second-look flag — never a re-classification (D-08).

    A thin, contract-typed adapter over the pure ``core.recheck.compare_vitals``
    function (SOLID: S/D): it returns a flag and the before/after vitals only. It
    never returns a colour and never reorders the queue (TOOL-04, T-02-10).
    """
    return recheck.compare_vitals(previous, current)


@server.tool()
@audited()
async def plan_next_step(investigation: InvestigationState) -> PlanDecision:
    """Propose the next investigation action — the deterministic guard decides (ADAPT-02).

    A thin, contract-typed adapter (SOLID: S/D): admissibility comes from the pure
    ``core.planner`` policy, the proposal from the ONE model wrapper, and the audit record and
    ``tool`` span from the ONE ``@audited`` interceptor. It carries no policy of its own.

    Read-only (ADAPT-04): it touches no store, writes no queue row, takes no approval token and
    returns a contract with no colour, priority or commit field — an investigation action can
    only add a fact, never a clinical decision.

    The fast path is the routine case: when the ONLY admissible action is
    ``finish_investigation`` the model is **not called**, so a case that needs no investigation
    costs exactly what it costs today. Otherwise the model proposes and
    ``core.planner.validate_proposal`` accepts or replaces the proposal; the returned action is
    therefore always a member of ``admissible_actions(investigation)`` — the tool's contract
    cannot express an inadmissible action (ADAPT-02, ADAPT-06).
    """
    if planner.admissible_actions(investigation) == planner.FINISH_ONLY:
        return planner.default_plan(investigation)
    return planner.validate_proposal(await propose_plan_async(investigation), investigation)


# The first protocol revision whose ``tools/call`` carries elicitation inside an
# ``InputRequiredResult`` (the multi-round-trip flow) instead of a server-initiated request.
# Pinned to the revision, NOT ``LATEST_MODERN_VERSION``, so a future revision cannot silently
# move the gate. On an older connection the legacy back-channel ``ctx.elicit`` is used instead.
_INPUT_REQUIRED_VERSION = "2026-07-28"

# The human-facing prompt for a clarification round. Static text: the QUESTIONS are derived
# per candidate and ride the form's property descriptions, so no question is authored here.
_CLARIFICATION_MESSAGE = (
    "One detail would resolve this triage case. Answer what you can — a blank field is an "
    "unanswered question, not a finding."
)


def _clarification_questions(candidates: list[str]) -> list[str]:
    """Derive at most three targeted questions from closed-set candidate ids (ELICIT-06).

    The ONE owner of question text is ``core.coverage.question_for`` (the same helper the
    coverage classifier uses), so a caller supplies **ids** and can never author a question.
    An id outside the closed set is skipped rather than raising — a data typo must not crash
    a tool call — and the bound is the classifier's own ``MAX_CLARIFICATION_QUESTIONS``, so
    the two cannot disagree about how many questions a nurse is asked.
    """
    questions: list[str] = []
    for candidate in candidates:
        if len(questions) >= coverage.MAX_CLARIFICATION_QUESTIONS:
            break
        try:
            question = coverage.question_for(candidate)
        except KeyError:
            continue  # not a declared discriminator: nothing to ask about
        questions.append(question)
    return questions


def _clarification_form(questions: list[str]) -> type[BaseModel]:
    """Build the spec-valid elicitation form: one string property per question.

    MCP elicitation admits primitive properties only, so the form is a flat model of ``str``
    fields named ``q1..qN`` (the ONE naming rule, ``mcp.elicitation.answer_field``) whose
    descriptions carry the derived question text. ``create_model`` is used because the field
    count is data-driven, not fixed.
    """
    form: type[BaseModel] = create_model(  # type: ignore[call-overload]
        "ClarificationForm",
        **{
            answer_field(index): (str, Field(default="", description=question))
            for index, question in enumerate(questions, start=1)
        },
    )
    return form


def _answers(form: type[BaseModel], content: Any) -> list[str]:
    """The human's answers in question order, blanks dropped.

    ``content`` is a mapping from the modern round trip, or the validated form model the
    legacy ``ctx.elicit`` returns; both are read the same way. A blank field is an
    unanswered question, not a finding: carrying ``""`` as an answer would let an untouched
    input become an observation (ELICIT-03/08).
    """
    if isinstance(content, BaseModel):
        content = content.model_dump()
    if not isinstance(content, Mapping):
        return []
    answers: list[str] = []
    for name in form.model_fields:
        value = content.get(name)
        if isinstance(value, str) and value.strip():
            answers.append(value)
    return answers


def _client_can_elicit(ctx: Context | None) -> bool:
    """True only when the connected client declared the elicitation capability.

    A ``None`` ctx (an in-process caller with no MCP client) or a ctx outside a request
    cannot elicit, so the answer is honestly ``unavailable`` rather than a fabricated value.
    """
    if ctx is None:
        return False
    try:
        capabilities = ctx.client_capabilities
    except (ValueError, AttributeError):
        return False
    return capabilities is not None and capabilities.elicitation is not None


def _unavailable(reason: str) -> ClarificationAnswer:
    """The ONE non-answer for a client that could not be asked (never a clinical value)."""
    return ClarificationAnswer(outcome=ElicitationOutcome.UNAVAILABLE, reason=reason)


def _outcome_from_responses(
    responses: Any, form: type[BaseModel]
) -> ClarificationAnswer:
    """Map a resumed elicitation round to one of the four outcomes (ELICIT-03).

    A cancel anywhere outranks a decline (a cancel abandons the call, a decline only the
    question), and either way **no** answer is carried. Only an all-accept round produces
    ``accepted`` with answers. A missing request, or a response this server did not mint, is
    ``unavailable`` — never an answer.
    """
    if not isinstance(responses, Mapping):
        return _unavailable("the client returned no elicitation response")
    response = responses.get(CLARIFICATION_REQUEST_KEY)
    action = getattr(response, "action", None)
    if action is None and isinstance(response, Mapping):
        action = response.get("action")
    if action == "cancel":
        return ClarificationAnswer(outcome=ElicitationOutcome.CANCELLED)
    if action == "decline":
        return ClarificationAnswer(outcome=ElicitationOutcome.DECLINED)
    if action != "accept":
        return _unavailable("the client did not answer the clarification request")
    content = getattr(response, "content", None)
    if content is None and isinstance(response, Mapping):
        content = response.get("content")
    return ClarificationAnswer(
        outcome=ElicitationOutcome.ACCEPTED, answers=_answers(form, content)
    )


async def _ask(questions: list[str], ctx: Context) -> ClarificationAnswer | InputRequiredResult:
    """Ask the questions over whichever transport this connection can carry — ONE branch.

    The 2026-07-28 transport forbids a server-initiated request, so elicitation there rides
    the multi-round-trip flow: the first round returns an ``InputRequiredResult`` and the
    client retries with ``input_responses``. An older connection has a back-channel, so the
    legacy ``ctx.elicit`` is used. Both paths feed the ONE outcome mapping, so the four
    outcomes cannot differ by transport.

    A missing capability or a connection with no back-channel is ``unavailable``; **any other
    exception propagates**, because a transport failure must never be reported as a clinical
    answer.
    """
    form = _clarification_form(questions)
    version = getattr(ctx, "protocol_version", None)
    if version is not None and is_version_at_least(version, _INPUT_REQUIRED_VERSION):
        responses = ctx.input_responses
        if responses is None:
            return InputRequiredResult(
                input_requests={
                    CLARIFICATION_REQUEST_KEY: ElicitRequest(
                        params=ElicitRequestFormParams(
                            message=_CLARIFICATION_MESSAGE,
                            requested_schema=render_elicitation_schema(form),
                        )
                    )
                }
            )
        return _outcome_from_responses(responses, form)

    try:
        result = await ctx.elicit(_CLARIFICATION_MESSAGE, form)
    except NoBackChannelError:
        return _unavailable("this connection has no back-channel for a server-initiated question")
    except MCPError as exc:
        if getattr(exc, "code", None) == MISSING_REQUIRED_CLIENT_CAPABILITY:
            return _unavailable("the client did not declare the elicitation capability")
        raise
    if isinstance(result, AcceptedElicitation):
        return ClarificationAnswer(
            outcome=ElicitationOutcome.ACCEPTED,
            answers=_answers(form, result.data),
        )
    if isinstance(result, DeclinedElicitation):
        return ClarificationAnswer(outcome=ElicitationOutcome.DECLINED)
    assert isinstance(result, CancelledElicitation)  # the union is exhaustive
    return ClarificationAnswer(outcome=ElicitationOutcome.CANCELLED)


@server.tool()
@audited()
async def request_clarification(
    candidates: list[str], ctx: Context | None = None
) -> ClarificationAnswer | InputRequiredResult:
    """Ask the nurse at most three targeted questions **inside** this call (ELICIT-01).

    The ninth owned tool, and read-only: no store, no queue row, no approval token, and a
    contract with no colour/priority/target field — so an answer is an *observation* that
    can never advance the case past the clinician's gate (ELICIT-01/08).

    Every question is derived from ``core.coverage.question_for``, the ONE owner of question
    text: the caller supplies closed-set discriminator **ids** and cannot author a question,
    so a question that does not trace to a loaded definition is not asked (ELICIT-06). At
    most ``coverage.MAX_CLARIFICATION_QUESTIONS`` are asked; an id outside the closed set is
    skipped.

    Four outcomes are distinguished (ELICIT-03): ``accepted`` (the only one carrying
    answers), ``declined``, ``cancelled`` and ``unavailable`` (the client cannot elicit). A
    decline, a cancel or an unavailable client is **not** a negative clinical response and is
    never converted into a value.

    On a 2026-07-28 connection the first round returns an ``InputRequiredResult`` (the
    transport forbids a server-initiated request), which the shipped adapter turns into a
    LangGraph ``interrupt()`` of type ``mcp_elicitation``; on an older connection the legacy
    ``ctx.elicit`` back-channel is used. ``ctx`` is optional so an in-process caller honestly
    receives ``unavailable`` instead of a fabricated answer.
    """
    questions = _clarification_questions(candidates)
    if not questions:
        return _unavailable("no candidate id names a declared discriminator; nothing to ask")
    if not _client_can_elicit(ctx):
        return _unavailable("the connected client cannot elicit an answer")
    assert ctx is not None  # _client_can_elicit proved it
    return await _ask(questions, ctx)


@server.tool()
@audited(approval=True)
async def commit_priority(
    case_id: str,
    colour: str,
    case: CaseInput,
    approval_token: dict[str, object] | None = None,
) -> CommitResult:
    """The queue-affecting gate — the real idempotent commit (GATE-02, GATE-03).

    The ONLY queue-affecting tool. The refusal path returns BEFORE any store call: a
    call with no token, a malformed token, or a ``dismiss`` decision is refused
    (``refused=True``) and touches no store (D-05, T-03-09). Only a validated token
    reaches the store, through the injectable :class:`~triagedesk.store.Store` seam.

    The write is idempotent on (``case_id``, immutable case-content hash), so an
    ``approve`` and an ``edit`` of the same case re-derive the SAME key and the queue
    row is superseded in place rather than duplicated (D6-04, D6-06). The committed
    colour is the clinician's ``final_colour`` for an ``edit`` and the scored ``colour``
    for an ``approve`` (D-05). The typed ``case`` is validated by the ONE schema module
    (T-06-02); no dict passthrough enters the key. The returned ``colour`` and ``target``
    report what the queue row actually holds — the target derived from the committed
    colour through the loaded substrate, never the pre-approval priority's — so a reader
    never re-derives either field.
    """
    if approval_token is None:
        return CommitResult(refused=True, reason="no approval token supplied; refusing to commit")
    try:
        token = ApprovalToken.model_validate(approval_token)
    except ValidationError:
        return CommitResult(refused=True, reason="approval token is malformed; refusing to commit")
    if token.decision == "dismiss":
        return CommitResult(
            refused=True, reason="clinician dismissed the priority; refusing to commit"
        )

    store = await resolve_store()
    committed = committed_colour(token, colour)
    row, created = await commit_to_queue(
        store,
        case_id=case_id,
        colour=committed,
        content=case,
        target=target_for_colour(committed),
    )
    verb = "committed" if created else "already committed"
    return CommitResult(
        committed=True,
        reason=f"{verb} case {row.case_id} at queue position {row.position} ({row.colour})",
        position=row.position,
        colour=row.colour,
        target=row.target,
    )


if __name__ == "__main__":
    server.run(transport="stdio")
