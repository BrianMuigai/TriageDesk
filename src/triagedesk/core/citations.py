"""The ONE citation helper (D-15, CONVENTIONS §1).

Every priority and every triggered rule is cited through this function; no
citation string is inlined anywhere else. This is the seam the Phase-2 scorer
calls, so citations have exactly one home.

Pure module: no I/O, no ``llm`` / ``mcp`` / ``store`` imports (D-13). The source
attribution is supplied by the caller from ``data/*.yaml`` (the machine
authority) — it is never hard-coded here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    """A single sourced citation for one triggered rule."""

    source: str
    reference: str

    def __str__(self) -> str:
        return f"{self.source} — {self.reference}"


def format_citation(reference: str, source: str) -> str:
    """Format one citation from a rule's *reference* and its *source*.

    This is the single home for citation formatting (D-15); callers pass the
    rule's own ``citation_ref`` and the source string from the loaded data, and
    never build a citation string themselves.
    """
    if not reference.strip():
        raise ValueError("citation reference must not be empty")
    if not source.strip():
        raise ValueError("citation source must not be empty")
    return str(Citation(source=source, reference=reference))
