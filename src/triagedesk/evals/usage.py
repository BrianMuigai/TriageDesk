"""The ONE per-run token recorder (D-08, Pitfall 16).

Token cost is read from the local model's OWN usage counters through the injectable
``usage_sink`` seam on :func:`triagedesk.llm.client.extract` — the counts come from the
SAME ``ollama.generate`` response the extraction already consumes. Accounting therefore
never issues a second model call, and an offline run (no model) honestly records zero.
"""

from __future__ import annotations

from collections.abc import Callable

from triagedesk.core.schema import ExtractionResult
from triagedesk.llm.client import extract as _client_extract


class UsageRecorder:
    """Accumulates ``(tokens_in, tokens_out)`` per run (reset before each run).

    The runner resets the recorder before every run so the recorded pairs belong to
    exactly one run; :meth:`totals` sums the run's pairs for the report.
    """

    def __init__(self) -> None:
        self._runs: list[tuple[int, int]] = []

    def reset(self) -> None:
        """Clear the accumulated pairs — called before each run (one sink per run)."""
        self._runs = []

    def sink(self, tokens_in: int, tokens_out: int) -> None:
        """Record one model response's usage — the seam handed to ``extract``."""
        self._runs.append((tokens_in, tokens_out))

    @property
    def runs(self) -> list[tuple[int, int]]:
        """The recorded pairs for the current run (one per model call)."""
        return list(self._runs)

    def totals(self) -> tuple[int, int]:
        """The current run's total ``(tokens_in, tokens_out)``."""
        return (
            sum(tokens_in for tokens_in, _ in self._runs),
            sum(tokens_out for _, tokens_out in self._runs),
        )


def recorded_extract(recorder: UsageRecorder) -> Callable[[str], ExtractionResult]:
    """Return the real ``extract`` bound to *recorder*'s usage sink (no second call).

    The wrapper calls :func:`triagedesk.llm.client.extract` with the recorder as its
    ``usage_sink``, so the usage is read from the one response the extraction consumes.
    """

    def extract(note: str) -> ExtractionResult:
        return _client_extract(note, usage_sink=recorder.sink)

    return extract


__all__ = ["UsageRecorder", "recorded_extract"]
