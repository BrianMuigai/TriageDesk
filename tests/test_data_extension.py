"""The hermetic data-only-extension proof (REV-01, D12-02, T-12-02, T-12-05).

Demonstrates — rather than asserts — the phase's headline claim: **the live extension is a
data edit**. ONE discriminator added to the discriminator substrate re-scores through the
**shipped** matcher and scorer with no code change, and the substrate-shape safety predicates
still hold.

The harness is **hermetic**: it writes only under ``tmp_path`` and redirects the ONE loader
seam (``rules.DISCRIMINATORS_PATH``) plus drops the per-process ``@lru_cache`` — the exact
equivalent of the reviewer running a **fresh process** after editing the YAML. The illustrative
addition lives ONLY in this module; the real ``data/sats_discriminators.yaml`` is never written.

The chosen alias is deliberately absent from every published ``evals/cases/*.yaml`` fixture, so
the demonstration adds a NEW capability rather than re-tuning a published case (it must never
tune the declared **E-09** failure green — RESEARCH Pitfall 3 / A1).

Nothing here re-implements matching or scoring: the shipped ``match_discriminators`` and
``score_priority`` are driven through the shipped loader (DRY, SOLID: L).
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from triagedesk.core import rules
from triagedesk.core.matcher import match_discriminators
from triagedesk.core.schema import CaseInput
from triagedesk.core.scorer import score_priority
from triagedesk.evals.case import load_cases


def _load_shipped_substrate_predicates() -> ModuleType:
    """Load the shipped substrate-shape predicates from the sibling test module by path.

    ``tests/`` is not an importable package under pytest, so the module is loaded from its
    file path. The predicates are the SHIPPED ones (``tests/test_sats_discriminators.py``),
    never a hand-copied predicate list — so "the safety suite is green WITH the addition" is
    demonstrated against the real checks.
    """
    path = Path(__file__).resolve().parent / "test_sats_discriminators.py"
    spec = importlib.util.spec_from_file_location("_review_sats_predicates", path)
    assert spec is not None and spec.loader is not None, f"could not load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# The illustrative addition — an EXISTING category (colour uniqueness holds) with a UNIQUE
# alias. It lives ONLY in this test module; it is never written to the real data file.
ADDITION = {
    "id": "severe_headache",
    "category": "very_urgent",
    "label": "Severe headache",
    "aliases": ["severe headache"],
}

# The bundled synthetic fixtures, resolved from the repo root.
CASES_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"


def _redirect_loader_to_extended_substrate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Write the real substrate + ONE addition to ``tmp_path`` and redirect the ONE loader.

    Reads the real substrate through ``rules.DISCRIMINATORS_PATH`` (still the real path at
    this point), appends the addition, dumps to a tmp file, then points the loader at it and
    drops the per-process cache — the hermetic equivalent of a fresh process re-reading an
    edited file. Callers MUST clear the cache again in a ``finally`` so no other test sees the
    tmp substrate.
    """
    raw = yaml.safe_load(rules.DISCRIMINATORS_PATH.read_text(encoding="utf-8"))
    raw["discriminators"].append(ADDITION)
    tmp = tmp_path / "sats_discriminators.yaml"
    tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)
    rules.get_discriminators.cache_clear()
    return tmp


def test_data_only_addition_rescores_without_code_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BEFORE the edit the phrase matches nothing; AFTER it re-scores through the shipped path."""
    phrase = ADDITION["aliases"][0]

    # 0. BEFORE — the phrase matches nothing against the REAL substrate (a change to
    #    demonstrate, not a constant).
    before = match_discriminators(phrase)
    assert before.no_match is True
    assert before.matched_ids == []

    # 1-2. The tmp substrate + the loader redirect (the hermetic "reload").
    _redirect_loader_to_extended_substrate(tmp_path, monkeypatch)
    try:
        # 3. AFTER — the SHIPPED matcher consumes the tmp substrate and returns the new id.
        after = match_discriminators(phrase)
        assert after.no_match is False
        assert after.matched_ids == [ADDITION["id"]]

        # The SHIPPED scorer overrides a normal-vitals GREEN to the category's colour.
        case = CaseInput(
            age_years=40,
            mobility="walking",
            avpu="alert",
            respiratory_rate=14,
            heart_rate=80,
            systolic_bp=120,
            temperature_c=36.8,
            trauma=False,
            complaint=phrase,
        )
        assert score_priority(case).colour == "GREEN"  # vitals alone
        assert score_priority(case, [ADDITION["id"]]).colour == "ORANGE"  # the override fires
    finally:
        rules.get_discriminators.cache_clear()


def test_the_extension_is_well_formed_and_unambiguous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The substrate-shape safety predicates hold WITH the addition (demonstrated, not asserted)."""
    phrase = ADDITION["aliases"][0]

    _redirect_loader_to_extended_substrate(tmp_path, monkeypatch)
    try:
        extended = rules.get_discriminators()

        # (a) the new alias is unique across all discriminators (case-insensitive).
        matches = sum(
            1
            for disc in extended.discriminators
            for alias in disc.aliases
            if alias.casefold().strip() == phrase.casefold()
        )
        assert matches == 1, f"the alias {phrase!r} is not unique across discriminators"

        # (b) the SHIPPED substrate-shape predicates pass against the redirected loader.
        predicates = _load_shipped_substrate_predicates()
        predicates.test_every_discriminator_is_well_formed(extended)
        predicates.test_ids_are_unique(extended)
        predicates.test_aliases_are_unambiguous_across_discriminators(extended)
        predicates.test_every_category_is_used(extended)
        predicates.test_every_category_maps_to_a_colour(extended)
        predicates.test_explicit_no_match_entry_exists(extended)
        predicates.test_alias_lookup_is_deterministic_and_reports_no_match(extended)
    finally:
        rules.get_discriminators.cache_clear()


def test_the_chosen_alias_is_absent_from_every_published_case() -> None:
    """The alias is absent from every fixture, so the extension cannot re-tune a published case."""
    phrase = ADDITION["aliases"][0]
    specs = load_cases(CASES_DIR)
    assert specs, "no published eval cases were loaded — the absence check would be vacuous"
    for spec in specs:
        assert phrase not in spec.note.casefold(), f"{spec.id}: the alias appears in the note"
        assert phrase not in spec.case.complaint.casefold(), (
            f"{spec.id}: the alias appears in the complaint"
        )


def _src_status() -> tuple[int, bytes]:
    """The ``git status --porcelain -- src/`` return code and output (the ONE fingerprint).

    The return code is paired with the output so a FAILED ``git`` call (empty stdout) cannot be
    mistaken for a clean tree — the vacuous-pass failure mode IN-02 named.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "src/"],
        capture_output=True,
    )
    return result.returncode, result.stdout


def test_the_extension_never_touches_src(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The demonstration edits no source file (IN-02).

    ``src/``'s working-tree status is byte-identical BEFORE and AFTER the demonstration harness
    (which writes only under ``tmp_path``), so the check is scoped to the demonstration: an
    unrelated ``src/`` edit already present in the tree does not fail it. The ``git`` return code
    is asserted first, so a failed invocation cannot pass vacuously.
    """
    code_before, status_before = _src_status()
    assert code_before == 0, "git status failed; the src/ check would be vacuous"

    # Exercise the demonstration harness end to end (the same path the sibling tests drive).
    phrase = ADDITION["aliases"][0]
    _redirect_loader_to_extended_substrate(tmp_path, monkeypatch)
    try:
        after = match_discriminators(phrase)
        assert after.matched_ids == [ADDITION["id"]], "the harness did not exercise the loader"
    finally:
        rules.get_discriminators.cache_clear()

    code_after, status_after = _src_status()
    assert code_after == 0, "git status failed; the src/ check would be vacuous"
    assert status_after == status_before, (
        f"the demonstration changed src/: {status_before!r} -> {status_after!r}"
    )
