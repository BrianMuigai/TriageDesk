"""Docs-finalisation guards (DOCS-02, D-03/D-05/D-06, T-05-09).

Keeps the hand-written submission docs honest and to their declared bounds, so a doc cannot
drift out of spec after finalisation:

* ``ARCHITECTURE.md`` is a genuine one page (≤ 700 words AND ≤ 110 lines);
* ``DESCRIPTION.md`` is within ±10% of its 300-word target;
* ``README.md`` carries the real one-command quickstart and no stale pre-build status rows.

The bounds are the plan's declared one-page / ~300-word targets; the guard fails in the
direction of a doc drifting out of spec, never the reverse.
"""

from __future__ import annotations

import re
from pathlib import Path

ARCHITECTURE = Path("ARCHITECTURE.md")
DESCRIPTION = Path("DESCRIPTION.md")
README = Path("README.md")

# The plan's declared bounds (05-03-PLAN must_haves / verification).
ARCH_MAX_WORDS = 700
ARCH_MAX_LINES = 110
DESCRIPTION_TARGET = 300
DESCRIPTION_TOLERANCE = 0.10

# Stale pre-build status framing that must NOT survive finalisation (D-06).
STALE_STATUS_ROWS = ("Not built", "Not recorded", "pre-build")


def _text(path: Path) -> str:
    """Read a doc as text."""
    return path.read_text(encoding="utf-8")


def _prose_words(text: str) -> int:
    """Word count of prose, ignoring HTML comments and markdown heading lines."""
    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = [line for line in without_comments.splitlines() if not line.lstrip().startswith("#")]
    return len("\n".join(lines).split())


def test_architecture_is_one_page() -> None:
    """ARCHITECTURE.md is a genuine one page (≤ 700 words AND ≤ 110 lines)."""
    text = _text(ARCHITECTURE)
    assert len(text.split()) <= ARCH_MAX_WORDS, "ARCHITECTURE.md exceeds the 700-word bound"
    assert len(text.splitlines()) <= ARCH_MAX_LINES, "ARCHITECTURE.md exceeds the 110-line bound"


def test_architecture_names_the_measured_model() -> None:
    """ARCHITECTURE.md names the measured default model, not a contradicted claim (D-03)."""
    assert "qwen2.5:1.5b" in _text(ARCHITECTURE)


def test_description_is_about_300_words() -> None:
    """DESCRIPTION.md is within ±10% of 300 words (D-05)."""
    words = _prose_words(_text(DESCRIPTION))
    low = DESCRIPTION_TARGET * (1 - DESCRIPTION_TOLERANCE)
    high = DESCRIPTION_TARGET * (1 + DESCRIPTION_TOLERANCE)
    assert low <= words <= high, f"DESCRIPTION.md is {words} words (want {low:.0f}-{high:.0f})"


def test_readme_has_the_one_command_quickstart() -> None:
    """README.md carries the REAL one-command quickstart (D-06)."""
    text = _text(README)
    assert "uv sync --locked" in text
    assert "uv run triagedesk demo" in text


def test_readme_has_no_stale_prebuild_status_rows() -> None:
    """README.md no longer carries the stale pre-build status framing (D-06)."""
    text = _text(README)
    for stale in STALE_STATUS_ROWS:
        assert stale not in text, f"README.md still carries the stale status row {stale!r}"


def test_readme_points_at_the_declared_failure() -> None:
    """README.md stays honest about what is unfinished (links EVALS.md, names E-09)."""
    text = _text(README)
    assert "EVALS.md" in text
    assert "E-09" in text
