"""Owned MCP server (SDK v2, stdio) exposing the five triage tools (D-04/D-12).

``from mcp.server import MCPServer`` — the v1 ``FastMCP`` import path was removed
in SDK v2. Every tool returns a shared ``core.schema`` contract (D-14), so the
server contract and the model contract cannot drift.

Depends on ``core/`` + ``llm/`` + ``store/``; nothing depends on this server except
the adapter seam (``mcp/adapter.py``), which launches it as a stdio subprocess.

``commit_priority`` is the ONE queue-affecting tool. It is the real gated write: it
validates the approval token, REFUSES (touching no store) when the token is absent,
malformed or a ``dismiss``, and otherwise performs the idempotent queue write through
the injectable :class:`~triagedesk.store.Store` seam (D-05, D-06, GATE-02/03).
"""

from __future__ import annotations

from mcp.server import MCPServer
from pydantic import ValidationError

from triagedesk.core import matcher, recheck, scorer
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    CommitResult,
    ExtractionResult,
    MatchResult,
    PriorityResult,
    RecheckFlag,
)
from triagedesk.llm.client import extract
from triagedesk.store import Store, default_store
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


async def _resolve_store() -> Store:
    """Resolve the store through the injectable seam, else the borrowed factory.

    The commit path calls THIS, never a concrete import, so a World-B store swap is a
    single injection (D-10, D-13, SOLID: D/L).
    """
    if _store is not None:
        return _store
    return await default_store()


@server.tool()
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
def match_discriminators(complaint: str) -> MatchResult:
    """Match a free-text complaint to closed-set discriminator ids (D-05, D-06).

    A thin, contract-typed adapter over the pure ``core.matcher`` function
    (SOLID: S/D): a deterministic alias lookup with no model and no fuzzy
    judgement. It returns ids from the closed discriminator set only, or an
    explicit ``no_match`` result — never a guessed id (SAFE-01).
    """
    return matcher.match_discriminators(complaint)


@server.tool()
def raise_recheck_flag(previous: CaseInput, current: CaseInput) -> RecheckFlag:
    """Compare serial vitals into a second-look flag — never a re-classification (D-08).

    A thin, contract-typed adapter over the pure ``core.recheck.compare_vitals``
    function (SOLID: S/D): it returns a flag and the before/after vitals only. It
    never returns a colour and never reorders the queue (TOOL-04, T-02-10).
    """
    return recheck.compare_vitals(previous, current)


@server.tool()
async def commit_priority(
    case_id: str, colour: str, approval_token: dict[str, object] | None = None
) -> CommitResult:
    """The queue-affecting gate — the real idempotent commit (GATE-02, GATE-03).

    The ONLY queue-affecting tool. The refusal path returns BEFORE any store call: a
    call with no token, a malformed token, or a ``dismiss`` decision is refused
    (``refused=True``) and touches no store (D-05, T-03-09). Only a validated token
    reaches the store, through the injectable :class:`~triagedesk.store.Store` seam.

    The write is idempotent on (``case_id``, immutable content hash), so a repeat or a
    crash-retry yields exactly one queue row (D-06, GATE-03). The committed colour is
    the clinician's ``final_colour`` for an ``edit`` and the scored ``colour`` for an
    ``approve`` (D-05).
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
    store = await _resolve_store()
    row, created = await commit_to_queue(
        store,
        case_id=case_id,
        colour=committed_colour,
        content={"colour": committed_colour},
    )
    verb = "committed" if created else "already committed"
    return CommitResult(
        committed=True,
        reason=f"{verb} case {row.case_id} at queue position {row.position} ({row.colour})",
    )


if __name__ == "__main__":
    server.run(transport="stdio")
