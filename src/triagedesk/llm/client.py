"""Ollama extraction client (D-01/D-02/D-03).

The model *structures* the note and *selects* discriminator ids; it never
computes a number (D-03). Every response is Pydantic-validated before it is
returned; the wrapper raises on empty or unparsable output and never returns
unvalidated data (T-01-01-02).

Only the local Ollama server is called — no network client is imported on the
extraction path (T-01-01-05). The model tag is a config value here: a model swap
is a config change behind this wrapper (SOLID: D).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import ollama

from triagedesk.core.planner import admissible_actions
from triagedesk.core.schema import ExtractionResult, InvestigationState, PlanProposal
from triagedesk.llm.notes import grounded_case
from triagedesk.llm.prompts import EXTRACTION_PROMPT, PLAN_PROMPT
from triagedesk.observability import span

# The injectable usage seam (D-08, Pitfall 16): a caller may supply a sink that is
# handed ``(prompt_eval_count, eval_count)`` read from the SAME ``ollama.generate``
# response the extraction already consumes — never a second model call. The default
# ``None`` keeps every existing caller (e.g. ``mcp.server.normalize_case``) unchanged
# (Liskov; SOLID: D — an injected dependency, no global state).
UsageSink = Callable[[int, int], None]

# Model tags are config values here: a model swap is a config change behind this
# wrapper (SOLID: D). The Phase-1 spike measured RAM/latency for both and selected
# the default; the outcome is recorded in evidence/model-spike.json (D-01).
BIG_MODEL = "qwen3.5:4b"  # the larger, aspirational alternative (docs' "verified fallback")
SMALL_MODEL = "qwen2.5:1.5b"

# Selected default, decided by the Phase-1 model spike on measured evidence
# (evidence/model-spike.json): with the 4B (qwen3.5:4b) loaded, available RAM fell
# to 641 MB (< 1024 MB budget), so the smaller Qwen (qwen2.5:1.5b) is the safe
# default. The 4B is the aspirational alternative / verified fallback (DECISIONS D3).
DEFAULT_MODEL = SMALL_MODEL

# `think=False` is MANDATORY: qwen3.5:4b is a reasoning model and without it the
# constrained JSON is emitted into the thinking channel and `response` is empty
# (Pitfall 1). temperature=0 + fixed seed keep extraction reproducible.
OPTIONS: dict[str, Any] = {"temperature": 0, "seed": 42, "num_ctx": 2048}


class ExtractionError(RuntimeError):
    """Raised when the model returns empty or unparsable / schema-invalid output."""


def _response_text(response: Any) -> str:
    """Read the generated text from an ollama response (object or mapping)."""
    if isinstance(response, dict):
        return str(response.get("response", ""))
    return str(getattr(response, "response", ""))


def _response_usage(response: Any) -> tuple[int, int]:
    """Read ``(prompt_eval_count, eval_count)`` from an ollama response (the ONE reader).

    The counts come from the SAME response object the extraction consumes — the local
    model reports its own token usage, so accounting never costs a second call and a
    missing count degrades honestly to 0 rather than a guessed value (D-08, Pitfall 16).
    """
    def _get(name: str) -> Any:
        if isinstance(response, dict):
            return response.get(name)
        return getattr(response, name, None)

    return int(_get("prompt_eval_count") or 0), int(_get("eval_count") or 0)


def _prompt_for(
    note: str, discriminator_ids: list[str] | None
) -> tuple[dict[str, Any], str]:
    """Build the ONE grammar schema and prompt both transports send (DRY).

    Returns ``(schema, prompt)``: the schema is sent as the constrained-decoding grammar
    AND rendered into the prompt, so a caller cannot drift the two apart.
    """
    schema = ExtractionResult.model_json_schema()
    prompt = EXTRACTION_PROMPT.format(
        schema=schema,
        discriminator_ids=", ".join(discriminator_ids or []) or "(none yet)",
        note=note,
    )
    return schema, prompt


def _usage_attrs(response: Any, attrs: dict[str, Any]) -> None:
    """Copy the response's token counts into the open span's attributes.

    :func:`_response_usage` stays the ONE reader of the counters; this only places them
    where the span already looks, inside the span block so they are captured on exit.
    """
    attrs["tokens_in"], attrs["tokens_out"] = _response_usage(response)


def _parsed(response: Any, note: str) -> ExtractionResult:
    """Validate and ground one model response — the ONE parser both transports use.

    Raises :class:`ExtractionError` on an empty or unparsable response, so neither
    transport can return unvalidated data.
    """
    raw = _response_text(response)
    if not raw.strip():
        raise ExtractionError(
            "model returned an empty response (is think=False set for this model?)"
        )
    try:
        parsed = ExtractionResult.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001 — re-raised as a typed error
        raise ExtractionError(f"model returned unparsable or schema-invalid JSON: {exc}") from exc
    # The model structures; it is not trusted to be complete or exact. The deterministic
    # grounding step drops unstated values, takes the AFTER value of a serial reading,
    # converts °F, and recovers a stated age/categorical the model dropped (SAFE-01,
    # nurse stress test S1-2/S1-3).
    return parsed.model_copy(update={"case": grounded_case(parsed.case, note)})


def extract(
    note: str,
    *,
    model: str = DEFAULT_MODEL,
    discriminator_ids: list[str] | None = None,
    usage_sink: UsageSink | None = None,
) -> ExtractionResult:
    """Extract a validated :class:`ExtractionResult` from a free-text triage note.

    When *usage_sink* is supplied it is invoked with the response's
    ``(prompt_eval_count, eval_count)`` — read from the one response below, before the
    payload is parsed, so even a malformed response records its true cost. The return
    type is unchanged, so existing callers are untouched (Liskov; SOLID: D).

    The ONE local model call is wrapped in a ``model`` span (D7-01) whose attributes are
    deliberately minimal — the model tag and the token counts only, never the note, the
    prompt or the completion (D7-08). The span is emitted here, so an offline run whose
    model is stubbed above this boundary emits no model span (Pitfall 6).

    Raises :class:`ExtractionError` on an empty or unparsable response — it never
    returns unvalidated data.
    """
    schema, prompt = _prompt_for(note, discriminator_ids)
    attrs: dict[str, Any] = {"model": model}
    with span("model", model, attributes=attrs):
        response = ollama.generate(
            model=model,
            prompt=prompt,
            format=schema,  # grammar-constrained decoding
            think=False,  # REQUIRED for qwen3.5:4b — else `response` is empty
            options=OPTIONS,
        )
        _usage_attrs(response, attrs)
    if usage_sink is not None:
        usage_sink(attrs["tokens_in"], attrs["tokens_out"])
    return _parsed(response, note)


# The async client is built LAZILY on first use and reused afterwards. It is never
# constructed at import time: ``desk.server`` imports this module, and the offline/harden
# ordering assumes no client (and no network) is primed just by importing it.
_ASYNC_CLIENT: ollama.AsyncClient | None = None


def _async_client() -> ollama.AsyncClient:
    """Return the ONE lazily-built async Ollama client (never at import time)."""
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is None:
        _ASYNC_CLIENT = ollama.AsyncClient()
    return _ASYNC_CLIENT


async def _async_generate(*, model: str, prompt: str, schema: dict[str, Any]) -> Any:
    """Await one async generation — the ONE patchable async transport seam.

    The mirror of ``ollama.generate`` on the sync path: both transports differ only here,
    so the prompt, parser, grounding and span rules stay in exactly one place (DRY).
    """
    return await _async_client().generate(
        model=model,
        prompt=prompt,
        format=schema,  # grammar-constrained decoding
        think=False,  # REQUIRED for qwen3.5:4b — else `response` is empty
        options=OPTIONS,
    )


async def extract_async(
    note: str,
    *,
    model: str = DEFAULT_MODEL,
    discriminator_ids: list[str] | None = None,
    usage_sink: UsageSink | None = None,
) -> ExtractionResult:
    """Await a validated :class:`ExtractionResult` — the async transport of :func:`extract`.

    The ONE core serves both transports: :func:`_prompt_for` builds the same schema and
    prompt, :func:`_parsed` applies the same validation and grounding, and the same
    ``model`` span is emitted with the same minimal attributes (the model tag and token
    counts only, never the note, the prompt or the completion — D7-08). No new dependency
    is added: ``ollama.AsyncClient`` ships with the already-pinned ``ollama``.

    Raises :class:`ExtractionError` on an empty or unparsable response — it never returns
    unvalidated data.
    """
    schema, prompt = _prompt_for(note, discriminator_ids)
    attrs: dict[str, Any] = {"model": model}
    with span("model", model, attributes=attrs):
        response = await _async_generate(model=model, prompt=prompt, schema=schema)
        _usage_attrs(response, attrs)
    if usage_sink is not None:
        usage_sink(attrs["tokens_in"], attrs["tokens_out"])
    return _parsed(response, note)


def _proposal(response: Any) -> PlanProposal | None:
    """Validate one planner response — ``None`` on any empty/unparsable/schema-invalid payload.

    The planner path DEGRADES rather than raises: a transport or schema failure becomes
    ``None`` so :func:`triagedesk.core.planner.validate_proposal` can substitute the default
    (ADAPT-02). The extraction path keeps its fail-loud :class:`ExtractionError` contract,
    because there is no safe default extraction — there is a safe default action.
    """
    raw = _response_text(response)
    if not raw.strip():
        return None
    try:
        return PlanProposal.model_validate_json(raw)
    except ValueError:  # pydantic's ValidationError is a ValueError
        return None


async def propose_plan_async(
    state: InvestigationState,
    *,
    model: str = DEFAULT_MODEL,
    usage_sink: UsageSink | None = None,
) -> PlanProposal | None:
    """Ask the local model to PROPOSE the next investigation action (ADAPT-02).

    Structured output only: the grammar is ``PlanProposal.model_json_schema()``, sent as the
    ``format=`` constraint exactly as the extraction call does, through the SAME lazily-built
    async client and the SAME ``model`` span with the same minimal attributes (never the note,
    the prompt or the completion — D7-08).

    The prompt's admissible list comes from :func:`triagedesk.core.planner.admissible_actions`
    — the guard's own policy — so the prompt cannot drift from the validator that judges the
    answer (DRY).

    Returns ``None`` when the model is unavailable or its payload is empty, unparsable or
    schema-invalid. The caller (``plan_next_step``) hands that ``None`` to the guard, which
    substitutes ``finish_investigation``; this function never raises and never returns
    unvalidated data.
    """
    schema = PlanProposal.model_json_schema()
    admissible = ", ".join(sorted(action.value for action in admissible_actions(state)))
    prompt = PLAN_PROMPT.format(
        schema=schema,
        admissible=admissible,
        state=state.model_dump_json(indent=2),
    )
    attrs: dict[str, Any] = {"model": model}
    with span("model", model, attributes=attrs):
        try:
            response = await _async_generate(model=model, prompt=prompt, schema=schema)
        except Exception:  # noqa: BLE001 — a transport failure degrades to the guard (ADAPT-02)
            return None
        _usage_attrs(response, attrs)
    if usage_sink is not None:
        usage_sink(attrs["tokens_in"], attrs["tokens_out"])
    return _proposal(response)
