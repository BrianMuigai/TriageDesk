"""Owned MCP server (SDK v2, stdio) exposing the seven triage tools (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. Every tool returns a shared ``core.schema`` contract (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/`` + ``store/``; nothing depends on this server except
the adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.

``commit_priority`` is the ONE queue-affecting tool. It is the real gated write: it
validates the approval token, REFUSES (touching no store) when the token is absent,
malformed or a ``dismiss``, and otherwise performs the idempotent queue write through
the injectable :class:`~triagedesk.store.Store` seam (D-05, D-06, GATE-02/03).

Every tool is wrapped by ONE uniform interceptor (:func:`audited`) that appends exactly
one chained audit record per call through ``store/audit.append``, so no owned tool call
escapes the audit (AUDIT-01, AUDIT-03, D-08).
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Mapping
from typing import Any

from mcp.server import MCPServer
from pydantic import BaseModel, ValidationError

from triagedesk.core import confidence, matcher, recheck, retrieval, scorer
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    CommitResult,
    ConfidenceResult,
    EvidenceResult,
    ExtractionResult,
    MatchResult,
    PriorityResult,
    RecheckFlag,
)
from triagedesk.llm.client import extract
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
def normalize_case(raw_note: str) -> ExtractionResult:
    """Parse a triage note into the typed case schema. Read-only.

    Single-purpose and contract-typed: it returns the one shared
    ``ExtractionResult`` schema (D-14), so the server contract and the model
    contract cannot drift. Read-only — it never writes to the queue (D-06).

    The model may only *structure* a note; it may not choose a discriminator
    outside the closed set. Model-returned ids are therefore filtered to the
    declared set (unknown ids dropped) and ``no_discriminator_matched`` is set
    when nothing survives (T-02-11). Missing vitals stay ``None`` — never imputed.
    """
    result = extract(raw_note)
    ids = matcher.validate_discriminator_ids(result.matched_discriminator_ids)
    return result.model_copy(
        update={"matched_discriminator_ids": ids, "no_discriminator_matched": not ids}
    )


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
    """
    return scorer.score_priority(case, matched_discriminator_ids)


@server.tool()
@audited()
def assess_confidence(
    matched_ids: list[str],
    no_match: bool,
    priority: PriorityResult,
) -> ConfidenceResult:
    """Return the deterministic coverage/deferral signal — no model, no store (D8-07).

    A thin, contract-typed adapter over the pure ``core.confidence.assess`` function
    (SOLID: S/D): it reads only the typed inputs it uses and returns the confidence
    contract. It takes no ``CaseInput``, so the declared tool contract cannot carry a
    field the signal ignores (WR-03). It touches no store, writes no queue row and takes
    no approval token; the signal can only route the graph to a more cautious terminal,
    never to the commit (D8-07, D8-12).
    """
    return confidence.assess(matched_ids, no_match, priority)


@server.tool()
@audited()
def match_discriminators(complaint: str) -> MatchResult:
    """Match a free-text complaint to closed-set discriminator ids (D-05, D-06).

    A thin, contract-typed adapter over the pure ``core.matcher`` function
    (SOLID: S/D): a deterministic alias lookup with no model and no fuzzy
    judgement. It returns ids from the closed discriminator set only, or an
    explicit ``no_match`` result — never a guessed id (SAFE-01).
    """
    return matcher.match_discriminators(complaint)


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
    (T-06-02); no dict passthrough enters the key.
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

    committed_colour = token.final_colour if token.decision == "edit" else colour
    store = await resolve_store()
    row, created = await commit_to_queue(
        store,
        case_id=case_id,
        colour=committed_colour,
        content=case,
    )
    verb = "committed" if created else "already committed"
    return CommitResult(
        committed=True,
        reason=f"{verb} case {row.case_id} at queue position {row.position} ({row.colour})",
    )


if __name__ == "__main__":
    server.run(transport="stdio")
