"""Offline hardening: neutralise the transitive tracer and assert no egress (D7-03).

``langsmith`` and ``opentelemetry-api`` ship transitively with LangChain, and ``langsmith``
enables tracing the moment the ``LANGSMITH_TRACING(_V2)`` / ``LANGCHAIN_TRACING(_V2)``
environment reads as ``"true"`` — a single env read away from a real HTTPS POST to
``api.smith.langchain.com`` (07-RESEARCH Summary 3). This module is the ONE place the
tracer environment is neutralised AND the neutralisation is asserted, so "nothing left the
machine" is provable rather than assumed (D7-03, T-07-01).

It is deliberately OUTSIDE ``graph/``: it is the only module that reads the process
environment, and ``graph/`` must read none (the safety-spine AST guard scans every
``graph/*.py`` for ``os.environ``/``getenv``). The OpenTelemetry SDK is not installed (only
the API is), so OTLP is inert — there is no exporter to construct (assumption A2).

Nothing here ever *enables* a tracer; it only removes the env keys and clears the cached
env read (``get_env_var`` is ``@functools.lru_cache``, so a stale ``"true"`` would
otherwise re-enable egress within the process — Pitfall 2), then asserts tracing is off.
"""

from __future__ import annotations

import os

# The env keys that decide whether the transitive tracer egresses (D7-03, T-07-01). The
# OTLP endpoint keys are removed too, so no exporter could target a collector even if one
# were ever constructed (the SDK is absent today — A2).
_TRACING_ENV_VARS = (
    "LANGSMITH_TRACING",
    "LANGSMITH_TRACING_V2",
    "LANGCHAIN_TRACING",
    "LANGCHAIN_TRACING_V2",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
)


def harden_offline() -> None:
    """Remove the tracer env keys, clear the cached read, and assert tracing is off (D7-03).

    Called once at CLI startup. When ``langsmith`` is absent the call is a no-op success
    (nothing can egress without the library); otherwise it clears ``get_env_var``'s
    ``lru_cache`` (a stale cached ``"true"`` survives an env pop otherwise — Pitfall 2) and
    asserts :func:`langsmith.utils.tracing_is_enabled` is ``False`` — the assertion is the
    proof that egress is inert. It mutates NO process-wide tracer flag, so it leaves no
    global state behind (a private global override was considered as belt-and-braces but
    rejected: it would leak across a long-lived process/test session).
    """
    for name in _TRACING_ENV_VARS:
        os.environ.pop(name, None)

    try:
        from langsmith import utils as langsmith_utils
    except ImportError:
        return

    # ``get_env_var`` is ``@functools.lru_cache``-wrapped, so ``cache_clear`` exists at
    # runtime; mypy only sees the two ``@overload`` signatures (which omit the wrapper
    # attribute), hence the narrow ignore — [attr-defined] otherwise (IN-01).
    langsmith_utils.get_env_var.cache_clear()  # type: ignore[attr-defined]
    if langsmith_utils.tracing_is_enabled():
        raise RuntimeError("cloud tracing is still enabled (D7-03): egress is not inert")


__all__ = ["harden_offline"]
