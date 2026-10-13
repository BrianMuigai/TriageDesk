"""The ONE static-asset path and the fixed two-name allowlist for the desk surface."""

from __future__ import annotations

from pathlib import Path

# The one home for the two hand-authored assets (D10-01). Keeping the markup out of Python
# string literals is what keeps a SATS colour/band literal out of ``src/**/*.py`` (CONVENTIONS
# §1); the Python emits only a generic ``colour-{name}`` class.
STATIC_DIR = Path(__file__).parent / "static"

# The fixed two-name asset allowlist: filename -> content type. A request for anything not in
# this map is a 404, so no path is ever built from ``self.path`` (no traversal).
_ASSETS: dict[str, str] = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
}
