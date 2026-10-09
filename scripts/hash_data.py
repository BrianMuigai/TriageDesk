"""Generate the pinned-substrate hash manifest (SAFE-04, D-17).

Through the ONE helper in ``core/hashing.py`` this script hashes:

* every ``data/*.yaml`` file (via the one loader where a loader exists),
* the extraction prompt template declared in ``llm/prompts.py``,
* the tool schemas declared in ``core/schema.py`` (``model_json_schema()``),

and writes the digests plus the selected model tag to ``evidence/hashes.json``.
This file is the version manifest every Phase-3 audit record names (D-17).

It exits non-zero if a required input (a ``data/*.yaml``, the prompt module, a
tool schema) is missing, so a silently-dropped substrate cannot produce a
partial manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from triagedesk.core import hashing
from triagedesk.core.rules import (
    DISCRIMINATORS_PATH,
    TEWS_PATH,
    load_discriminators,
    load_tews,
)
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.llm import prompts as prompt_module
from triagedesk.llm.client import DEFAULT_MODEL

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_OUT = REPO_ROOT / "evidence" / "hashes.json"

# The one loader per data file (CONVENTIONS §1). An unknown ``data/*.yaml`` falls
# back to a plain normalised YAML load, so a future data file is hashed too.
_DATA_LOADERS = {
    TEWS_PATH.name: load_tews,
    DISCRIMINATORS_PATH.name: load_discriminators,
}
_REQUIRED_DATA_FILES = (TEWS_PATH.name, DISCRIMINATORS_PATH.name)

# The tool contracts hashed from the one schema module (D-14).
_SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "CaseInput": CaseInput,
    "ExtractionResult": ExtractionResult,
}

# Model evidence recorded by the Phase-1 model spike (Plan 01-01).
_MODEL_EVIDENCE = REPO_ROOT / "evidence" / "model-spike.json"


def _load_data(path: Path) -> BaseModel | Any:
    """Load one ``data/*.yaml`` file through its loader (or a normalised fallback)."""
    loader = _DATA_LOADERS.get(path.name)
    if loader is not None:
        return loader(path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _hash_data_files() -> dict[str, str]:
    """Hash every ``data/*.yaml``; fail if a required file is missing."""
    files = sorted(DATA_DIR.glob("*.yaml"))
    present = {path.name for path in files}
    missing = [name for name in _REQUIRED_DATA_FILES if name not in present]
    if missing:
        raise SystemExit(f"required data file(s) missing under {DATA_DIR}: {missing}")
    return {path.name: hashing.hash_rule_object(_load_data(path)) for path in files}


def _hash_prompts() -> dict[str, str]:
    """Hash every declared prompt template constant in ``llm/prompts.py``."""
    templates = {
        name: hashing.hash_prompt(getattr(prompt_module, name))
        for name in dir(prompt_module)
        if not name.startswith("_")
        and name.isupper()
        and isinstance(getattr(prompt_module, name), str)
    }
    if not templates:
        raise SystemExit(f"no prompt template found in module {prompt_module.__name__}")
    return templates


def _hash_schemas() -> dict[str, str]:
    """Hash the tool schemas declared by the one schema module."""
    return {
        name: hashing.hash_tool_schema(model.model_json_schema())
        for name, model in _SCHEMA_MODELS.items()
    }


def _model_info() -> dict[str, str]:
    """Return the selected model tag (and licence when the spike evidence is present)."""
    info: dict[str, str] = {"model_tag": DEFAULT_MODEL}
    if not _MODEL_EVIDENCE.exists():
        return info
    evidence = json.loads(_MODEL_EVIDENCE.read_text(encoding="utf-8"))
    selected = evidence.get("selected_model")
    if selected and selected != DEFAULT_MODEL:
        raise SystemExit(
            f"model tag mismatch: llm/client.py DEFAULT_MODEL={DEFAULT_MODEL!r} but "
            f"evidence/model-spike.json selected_model={selected!r}"
        )
    licence = evidence.get("fallback", {}).get("licence") or evidence.get("primary", {}).get(
        "licence"
    )
    if licence:
        info["model_licence"] = licence
    return info


def build_manifest() -> dict[str, Any]:
    """Build the complete pinned-substrate manifest."""
    return {
        "generated_by": "scripts/hash_data.py",
        "algorithm": hashing.ALGORITHM,
        "canonical_form": "sorted-key JSON, compact separators, UTF-8",
        **_model_info(),
        "data": _hash_data_files(),
        "prompts": _hash_prompts(),
        "schemas": _hash_schemas(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the pinned-substrate hash manifest.")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="manifest output path (JSON)"
    )
    args = parser.parse_args(argv)

    manifest = build_manifest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out}: model={manifest['model_tag']} "
        f"data={len(manifest['data'])} prompts={len(manifest['prompts'])} "
        f"schemas={len(manifest['schemas'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
