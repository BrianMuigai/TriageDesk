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

from triagedesk.core.schema import ExtractionResult
from triagedesk.llm.prompts import EXTRACTION_PROMPT

# The injectable usage seam (D-08, Pitfall 16): a caller may supply a sink that is
# handed ``(prompt_eval_count, eval_count)`` read from the SAME ``ollama.generate``
# response the extraction already consumes — never a second model call. The default
# ``None`` keeps every existing caller (e.g. ``mcp.server.normalize_case``) unchanged
# (Liskov; SOLID: D — an injected dependency, no global state).
UsageSink = Callable[[int, int], None]

# Model tags are config values here: a model swap is a config change behind this
# wrapper (SOLID: D). The Phase-1 spike measures RAM/latency for both and selects
# the default; the outcome is recorded in evidence/model-spike.json (D-01).
PRIMARY_MODEL = "qwen3.5:4b"
FALLBACK_MODEL = "qwen2.5:1.5b"

# Selected default, decided by the Phase-1 model spike on measured evidence
# (evidence/model-spike.json): with qwen3.5:4b loaded, available RAM fell to
# 587 MB (< 1024 MB budget), so the smaller Qwen is the safe default.
DEFAULT_MODEL = FALLBACK_MODEL

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

    Raises :class:`ExtractionError` on an empty or unparsable response — it never
    returns unvalidated data.
    """
    schema = ExtractionResult.model_json_schema()
    prompt = EXTRACTION_PROMPT.format(
        schema=schema,
        discriminator_ids=", ".join(discriminator_ids or []) or "(none yet)",
        note=note,
    )
    response = ollama.generate(
        model=model,
        prompt=prompt,
        format=schema,  # grammar-constrained decoding
        think=False,  # REQUIRED for qwen3.5:4b — else `response` is empty
        options=OPTIONS,
    )
    if usage_sink is not None:
        usage_sink(*_response_usage(response))
    raw = _response_text(response)
    if not raw.strip():
        raise ExtractionError(
            "model returned an empty response (is think=False set for this model?)"
        )
    try:
        return ExtractionResult.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001 — re-raised as a typed error
        raise ExtractionError(f"model returned unparsable or schema-invalid JSON: {exc}") from exc
