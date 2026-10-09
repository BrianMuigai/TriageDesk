"""Dual independent transcription diff for the SATS rule substrate (D-10).

Transcription **A** is the machine authority — ``data/sats_tews.yaml`` and
``data/sats_discriminators.yaml`` (read through the one loader, ``core/rules.py``).
Transcription **B** is the independent second transcription in
``evidence/sats_transcription_b.yaml``, written by a different route (range strings
mirroring the manual's table rows). This script normalises both to a common form
and diffs them band-by-band, parameter-by-parameter, threshold-by-threshold and
discriminator-by-discriminator.

Exit code is non-zero if any band, threshold, target time, out-of-scope predicate
or discriminator category disagrees, and every disagreement is printed. With
``--report <path>`` the result, the resolved ambiguities and the residual
uncertainties are written to a markdown verification report.

No SATS value lives in this script: it parses both transcriptions generically.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

# Repo root is the parent of this script's directory.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from triagedesk.core.rules import (  # noqa: E402
    DISCRIMINATORS_PATH,
    TEWS_PATH,
    get_discriminators,
    get_tews,
)

TRANSCRIPTION_B_PATH = _REPO_ROOT / "evidence" / "sats_transcription_b.yaml"

# Canonical band = (points, inclusive_min_or_None, inclusive_max_or_None, value_or_None).
CanonicalBand = tuple[int, float | None, float | None, str | None]


def _num(value: object) -> float | None:
    return None if value is None else round(float(value), 4)


def _resolution(boundaries: list[float]) -> float:
    """The parameter's resolution: 1 for integer scales, else 0.1."""
    finite = [b for b in boundaries if b is not None]
    return 1.0 if all(b.is_integer() for b in finite) else 0.1


def _parse_range(text: str, step: float) -> tuple[float | None, float | None]:
    """Parse a range string to an inclusive (lo, hi) pair at the given resolution.

    ``<9`` -> ``(None, 8)``; ``>=30`` -> ``(30, None)``; ``>38.4`` -> ``(38.5, None)``;
    ``9-14`` -> ``(9, 14)``. Strict inequalities are converted to inclusive
    bounds so both transcription conventions are comparable.
    """
    t = str(text).strip()
    if t.startswith(">="):
        return round(float(t[2:].strip()), 4), None
    if t.startswith("<="):
        return None, round(float(t[2:].strip()), 4)
    if t.startswith(">"):
        return round(float(t[1:].strip()) + step, 4), None
    if t.startswith("<"):
        return None, round(float(t[1:].strip()) - step, 4)
    if "-" in t:
        lo, hi = t.split("-", 1)
        return round(float(lo.strip()), 4), round(float(hi.strip()), 4)
    raise ValueError(f"unparseable range: {text!r}")


def canonical_tews_a() -> dict[str, dict]:
    """Normalise transcription A (data/*.yaml via the loader) to canonical form."""
    rules = get_tews()
    out: dict[str, dict] = {}
    for name, param in rules.parameters.items():
        bands: set[CanonicalBand] = {
            (b.points, _num(b.min), _num(b.max), b.value) for b in param.bands
        }
        out[name] = {"unit": param.unit, "bands": bands}
    return out


def canonical_tews_b(raw: dict) -> dict[str, dict]:
    """Normalise transcription B (range-string rows) to canonical form."""
    out: dict[str, dict] = {}
    for name, param in raw["tews"].items():
        boundaries: list[float] = []
        for row in param["rows"]:
            if "range" not in row:
                continue
            t = str(row["range"]).strip()
            stripped = (
                t.replace(">=", " ").replace("<=", " ").replace(">", " ").replace("<", " ")
            )
            for token in stripped.split("-"):
                try:
                    boundaries.append(float(token))
                except ValueError:
                    pass
        step = _resolution(boundaries)
        bands: set[CanonicalBand] = set()
        for row in param["rows"]:
            if row.get("value") is not None:
                bands.add((row["points"], None, None, row["value"]))
            else:
                lo, hi = _parse_range(row["range"], step)
                bands.add((row["points"], lo, hi, None))
        out[name] = {"unit": param.get("unit"), "bands": bands}
    return out


def _colour_canonical_a() -> set[tuple[str, float | None, float | None]]:
    return {(b.colour, _num(b.min), _num(b.max)) for b in get_tews().tews_to_colour}


def _colour_canonical_b(raw: dict) -> set[tuple[str, float | None, float | None]]:
    out: set[tuple[str, float | None, float | None]] = set()
    for row in raw["tews_to_colour"]:
        lo, hi = _parse_range(row["range"], 1.0)
        out.add((row["colour"], lo, hi))
    return out


def _targets_a() -> dict[str, tuple[str, str]]:
    return {k: (v.target, v.destination) for k, v in get_tews().target_times.items()}


def _targets_b(raw: dict) -> dict[str, tuple[str, str]]:
    return {
        k: (v["target"], v["destination"]) for k, v in raw["target_times"].items()
    }


def _scope_a() -> dict:
    s = get_tews().out_of_scope
    return {
        "adult_min_age_years": s.adult_min_age_years,
        "adult_min_height_cm": s.adult_min_height_cm,
        "on_missing_age": s.on_missing_age,
    }


def _scope_b(raw: dict) -> dict:
    return dict(raw["out_of_scope"])


def _discriminators_a() -> dict[str, str]:
    return {d.id: d.category for d in get_discriminators().discriminators}


def _discriminators_b(raw: dict) -> dict[str, str]:
    return dict(raw["discriminator_categories"])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare() -> tuple[list[str], dict]:
    """Return (disagreements, facts). Empty disagreements == agreement."""
    raw = yaml.safe_load(TRANSCRIPTION_B_PATH.read_text(encoding="utf-8"))
    disagreements: list[str] = []

    tews_a = canonical_tews_a()
    tews_b = canonical_tews_b(raw)
    if set(tews_a) != set(tews_b):
        disagreements.append(
            f"TEWS parameters differ: only-A={sorted(set(tews_a) - set(tews_b))} "
            f"only-B={sorted(set(tews_b) - set(tews_a))}"
        )
    for name in sorted(set(tews_a) & set(tews_b)):
        if tews_a[name]["unit"] != tews_b[name]["unit"]:
            disagreements.append(
                f"{name}: unit A={tews_a[name]['unit']!r} B={tews_b[name]['unit']!r}"
            )
        only_a = tews_a[name]["bands"] - tews_b[name]["bands"]
        only_b = tews_b[name]["bands"] - tews_a[name]["bands"]
        if only_a or only_b:
            disagreements.append(
                f"{name}: band mismatch only-A={sorted(only_a)} only-B={sorted(only_b)}"
            )

    colours_a = _colour_canonical_a()
    colours_b = _colour_canonical_b(raw)
    if colours_a != colours_b:
        disagreements.append(
            f"colour thresholds differ: only-A={sorted(colours_a - colours_b)} "
            f"only-B={sorted(colours_b - colours_a)}"
        )

    targets_a = _targets_a()
    targets_b = _targets_b(raw)
    if targets_a != targets_b:
        disagreements.append(f"target times differ: A={targets_a} B={targets_b}")

    scope_a = _scope_a()
    scope_b = _scope_b(raw)
    if scope_a != scope_b:
        disagreements.append(f"out-of-scope predicate differs: A={scope_a} B={scope_b}")

    discs_a = _discriminators_a()
    discs_b = _discriminators_b(raw)
    if discs_a != discs_b:
        only_a = {k: discs_a[k] for k in set(discs_a) - set(discs_b)}
        only_b = {k: discs_b[k] for k in set(discs_b) - set(discs_a)}
        changed = {
            k: (discs_a[k], discs_b[k])
            for k in set(discs_a) & set(discs_b)
            if discs_a[k] != discs_b[k]
        }
        disagreements.append(
            f"discriminator categories differ: only-A={only_a} only-B={only_b} "
            f"changed={changed}"
        )

    facts = {
        "parameters": len(tews_a),
        "colours": len(colours_a),
        "discriminators": len(discs_a),
        "targets": len(targets_a),
        "resolved_ambiguities": raw.get("resolved_ambiguities", []),
        "residual_uncertainties": raw.get("residual_uncertainties", []),
        "inputs": {
            "A": [TEWS_PATH, DISCRIMINATORS_PATH],
            "B": [TRANSCRIPTION_B_PATH],
        },
    }
    return disagreements, facts


def render_report(disagreements: list[str], facts: dict) -> str:
    """Render the markdown verification report."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    passed = not disagreements
    lines: list[str] = []
    lines.append("# SATS dual-transcription verification (D-10)")
    lines.append("")
    lines.append(f"- **Generated:** {now} (UTC)")
    lines.append("- **Method:** two independent transcriptions normalised to a common form")
    lines.append(
        "  and diffed band-by-band, parameter-by-parameter and discriminator-by-discriminator."
    )
    lines.append("- **Script:** `scripts/transcribe_diff.py`")
    lines.append("")
    lines.append("## Inputs (provenance)")
    lines.append("")
    lines.append("| Transcription | File | sha256 |")
    lines.append("| --- | --- | --- |")
    for label, paths in facts["inputs"].items():
        for p in paths:
            lines.append(f"| {label} | `{p.relative_to(_REPO_ROOT)}` | `{_sha256(p)}` |")
    lines.append("")
    lines.append("## Compared")
    lines.append("")
    lines.append(
        f"- **TEWS parameters:** {facts['parameters']} (bands, inclusive edges, points, units)"
    )
    lines.append(f"- **TEWS→colour thresholds:** {facts['colours']}")
    lines.append(f"- **Target times / destinations:** {facts['targets']}")
    lines.append("- **Out-of-scope predicate:** adult age/height + missing-age behaviour")
    lines.append(f"- **Discriminator categories:** {facts['discriminators']} ids → category")
    lines.append("")
    lines.append("## Result")
    lines.append("")
    if passed:
        lines.append(
            "**VERIFICATION PASSED** — the two independent transcriptions agree on every "
            "band, threshold, target time, out-of-scope predicate and discriminator category."
        )
    else:
        lines.append(
            f"**VERIFICATION FAILED** — {len(disagreements)} disagreement(s):"
        )
        lines.append("")
        for item in disagreements:
            lines.append(f"- {item}")
    lines.append("")
    lines.append("## Resolved ambiguities")
    lines.append("")
    for entry in facts["resolved_ambiguities"]:
        lines.append(f"- **Issue:** {entry['issue']}")
        lines.append(f"  **Resolution:** {entry['resolution']}")
    lines.append("")
    lines.append("## Residual uncertainty")
    lines.append("")
    for entry in facts["residual_uncertainties"]:
        lines.append(f"- {entry}")
    lines.append("")
    lines.append("## Scoping note (SC1)")
    lines.append("")
    lines.append(
        "`docs/SATS.md` is the **human-readable transcription reference** derived from the same "
        "SATS manual; it is **never imported at runtime**. `data/*.yaml` is the machine authority, "
        "and the SC1 'single source of truth' gate is scoped to **code + runtime**. "
        "`evidence/sats_transcription_b.yaml` is a verification artefact, not a runtime authority."
    )
    lines.append("")
    lines.append("> `docs/SATS.md` remains the human-readable reference and links to the")
    lines.append("> YAML as the machine source; it is not a second authority for the thresholds.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None, help="Write a markdown report here.")
    args = parser.parse_args(argv)

    disagreements, facts = compare()
    for item in disagreements:
        print(f"DISAGREEMENT: {item}")
    if disagreements:
        print(f"RESULT: FAIL ({len(disagreements)} disagreement(s))")
    else:
        print(
            "RESULT: PASS — transcriptions agree on "
            f"{facts['parameters']} parameters, {facts['colours']} colour thresholds, "
            f"{facts['discriminators']} discriminators."
        )

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(disagreements, facts), encoding="utf-8")
        print(f"report written: {args.report}")

    return 1 if disagreements else 0


if __name__ == "__main__":
    raise SystemExit(main())
