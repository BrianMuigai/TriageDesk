"""The ONE HTML-escaping rule for the desk surface (ASVS V5)."""

from __future__ import annotations

import html
from typing import Any


def _escaped(value: Any) -> str:
    """Escape one rendered value for HTML (ASVS V5)."""
    return html.escape(str(value))
