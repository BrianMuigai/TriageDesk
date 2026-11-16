"""The async extraction transport shares ONE core with the sync one (Plan 13-01, JC-1).

Proves that ``extract_async`` is not a second implementation: both transports build the
same prompt, run the same parser and grounding step, and emit the same minimal ``model``
span. Also proves the async transport genuinely yields — two calls are in flight together
— and that it fails closed on empty or invalid output, exactly like the sync path.
"""

from __future__ import annotations

import asyncio
from typing import Any

import ollama
import pytest

from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.llm import client
from triagedesk.observability.spans import read_spans


def _result() -> ExtractionResult:
    """One canned extraction the fake model returns."""
    return ExtractionResult(
        case=CaseInput(respiratory_rate=24, avpu="alert"),
        matched_discriminator_ids=[],
    )


def _response() -> dict[str, Any]:
    """The one canned Ollama response shape both transports consume."""
    return {
        "response": _result().model_dump_json(),
        "prompt_eval_count": 11,
        "eval_count": 7,
    }


def _model_spans() -> list[dict[str, Any]]:
    """The ``model`` spans written so far (the autouse fixture redirects the sink)."""
    return [row for row in read_spans() if row["kind"] == "model"]


async def _client_from_this_loop() -> ollama.AsyncClient:
    """Return the client the module builds for whichever loop is running this coroutine."""
    return client._async_client()


async def test_extract_and_extract_async_share_one_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both transports return equal results and emit the same ONE minimal model span."""
    response = _response()

    async def fake_async_generate(**kwargs: Any) -> Any:
        return response

    monkeypatch.setattr(client.ollama, "generate", lambda **kwargs: response)
    monkeypatch.setattr(client, "_async_generate", fake_async_generate)

    sync_result = client.extract("RR 24, alert")
    sync_spans = _model_spans()
    async_result = await client.extract_async("RR 24, alert")
    async_spans = _model_spans()[len(sync_spans):]

    assert sync_result == async_result, "the transports parsed/grounded differently"
    assert len(sync_spans) == 1, "the sync transport must emit exactly one model span"
    assert len(async_spans) == 1, "the async transport must emit exactly one model span"
    assert set(sync_spans[0]["attributes"]) == {"model", "tokens_in", "tokens_out"}
    assert sync_spans[0]["attributes"] == async_spans[0]["attributes"]
    attrs = sync_spans[0]["attributes"]
    assert (attrs["tokens_in"], attrs["tokens_out"]) == (11, 7)


async def test_extract_async_overlaps_two_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two awaited extractions are genuinely in flight together (the await yields)."""
    response = _response()
    in_flight = 0
    peak = 0

    async def slow_async_generate(**kwargs: Any) -> Any:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return response

    monkeypatch.setattr(client, "_async_generate", slow_async_generate)

    await asyncio.gather(client.extract_async("a"), client.extract_async("b"))

    # ``peak`` is the deterministic proof of overlap: the second call entered the
    # generator before the first returned. A wall-clock bound was removed because it
    # flaked under host load without adding evidence the counter does not already give.
    assert peak == 2, "the second extraction did not start before the first finished"


@pytest.mark.parametrize(
    "response",
    [
        {"response": "", "prompt_eval_count": 0, "eval_count": 0},
        {"response": "{not json", "prompt_eval_count": 0, "eval_count": 0},
    ],
    ids=["empty", "invalid-json"],
)
async def test_extract_async_raises_on_empty_and_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch, response: dict[str, Any]
) -> None:
    """The async transport never returns unvalidated data (the sync contract, unchanged)."""

    async def fake_async_generate(**kwargs: Any) -> Any:
        return response

    monkeypatch.setattr(client, "_async_generate", fake_async_generate)
    with pytest.raises(client.ExtractionError):
        await client.extract_async("RR 24")


async def test_extract_async_forwards_usage_from_the_one_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sink records exactly the one response's ``(tokens_in, tokens_out)`` pair."""
    response = _response()
    recorded: list[tuple[int, int]] = []

    async def fake_async_generate(**kwargs: Any) -> Any:
        return response

    monkeypatch.setattr(client, "_async_generate", fake_async_generate)

    await client.extract_async("RR 24", usage_sink=lambda i, o: recorded.append((i, o)))

    assert recorded == [(11, 7)]


async def test_async_client_is_built_lazily_and_reused() -> None:
    """The async client is built on first use in a loop and reused within that loop."""
    original = client._ASYNC_CLIENT
    client._ASYNC_CLIENT = None
    try:
        assert client._ASYNC_CLIENT is None, "a client was built before the first use"
        first = client._async_client()
        assert client._async_client() is first, "one loop must reuse the SAME client"
    finally:
        client._ASYNC_CLIENT = original


def test_async_client_is_rebuilt_for_a_new_event_loop() -> None:
    """A second ``asyncio.run`` gets a NEW client — the loop-bound failure mode is gone.

    An ``ollama.AsyncClient`` wraps a loop-bound ``httpx`` client, so reusing loop 1's client
    on loop 2 raises instantly; the planner then degraded to ``finish_investigation`` and E-09
    never asked its glucose question. Identity only: no network, no ``generate`` call.
    """
    original = client._ASYNC_CLIENT
    client._ASYNC_CLIENT = None
    try:
        first = asyncio.run(_client_from_this_loop())
        second = asyncio.run(_client_from_this_loop())
        assert first is not second, "the closed loop's client was reused on the next loop"
        third = asyncio.run(_client_from_this_loop())
        assert third is not first and third is not second, "each loop must get its own client"
    finally:
        client._ASYNC_CLIENT = original
