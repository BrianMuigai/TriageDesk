"""The ONE loader for the SATS rule substrate (D-08, CONVENTIONS §1).

``data/sats_tews.yaml`` is the machine authority for TEWS bands, colour
thresholds, target times and out-of-scope predicates. ``data/sats_discriminators.yaml``
is the machine authority for clinical discriminators, their categories/colours and
the explicit no-match outcome (D-11). Both are read *only* here; no band, threshold,
discriminator string or citation is ever inlined in code.

Pure module: reads data files, has no model/MCP/storage dependency, and imports
nothing from ``llm`` / ``mcp`` / ``store`` (D-13).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

# src/triagedesk/core/rules.py -> repo root is parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = _REPO_ROOT / "data"
TEWS_PATH = DATA_DIR / "sats_tews.yaml"
DISCRIMINATORS_PATH = DATA_DIR / "sats_discriminators.yaml"


class Band(BaseModel):
    """One scoring band. Bands are inclusive; ``value`` is for categorical params."""

    points: int
    min: float | None = None
    max: float | None = None
    value: str | None = None


class Parameter(BaseModel):
    """A TEWS parameter and its bands (numeric or categorical)."""

    unit: str | None = None
    bands: list[Band]


class ColourBand(BaseModel):
    """A TEWS total -> colour threshold (inclusive)."""

    colour: str
    min: int
    max: int | None = None


class TargetTime(BaseModel):
    """Priority -> target time and destination."""

    target: str
    destination: str


class OutOfScope(BaseModel):
    """The fail-closed out-of-scope predicate, as data (D-09)."""

    adult_min_age_years: int
    adult_min_height_cm: int
    on_missing_age: str


class TewsRules(BaseModel):
    """The typed rule substrate loaded from ``data/sats_tews.yaml``."""

    version: int
    citation: str
    parameters: dict[str, Parameter]
    tews_to_colour: list[ColourBand]
    target_times: dict[str, TargetTime]
    out_of_scope: OutOfScope


def load_tews(path: Path | None = None) -> TewsRules:
    """Load and validate the TEWS rule substrate from *path* (default: the data file)."""
    source = path or TEWS_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    return TewsRules.model_validate(raw)


class Discriminator(BaseModel):
    """One clinical discriminator: an id, its category, a short label and aliases."""

    id: str
    category: str
    label: str
    aliases: list[str]


class DiscriminatorCategory(BaseModel):
    """A discriminator category and the priority colour it resolves to."""

    colour: str
    citation_ref: str


class NoMatch(BaseModel):
    """The explicit 'nothing matched' outcome (D-11) — a coverage-gap signal."""

    result: str
    warning: str


class DiscriminatorRules(BaseModel):
    """The typed discriminator substrate loaded from ``data/sats_discriminators.yaml``."""

    version: int
    citation: str
    categories: dict[str, DiscriminatorCategory]
    discriminators: list[Discriminator]
    no_match: NoMatch


def load_discriminators(path: Path | None = None) -> DiscriminatorRules:
    """Load and validate the discriminator substrate from *path* (default: the data file)."""
    source = path or DISCRIMINATORS_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    return DiscriminatorRules.model_validate(raw)


@lru_cache(maxsize=1)
def get_tews() -> TewsRules:
    """Return the TEWS rule substrate, loaded once per process."""
    return load_tews()


@lru_cache(maxsize=1)
def get_discriminators() -> DiscriminatorRules:
    """Return the discriminator substrate, loaded once per process."""
    return load_discriminators()
