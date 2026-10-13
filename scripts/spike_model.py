"""Model-fit spike — the D-07 evidence that retires Day-1 unknown (a) (D-01).

Measures RAM and latency for the larger model (``qwen3.5:4b``) and runs the
schema-constrained extraction round-trip through ``llm/client.py`` on a fixed
synthetic note. It then runs the **identical** path end-to-end on the
smaller model (``qwen2.5:1.5b``) **unconditionally**, so Roadmap SC3 is satisfied
on evidence regardless of the budget gate's outcome. The gate then decides which
model is the *default*.

Writes the full record to ``evidence/model-spike.json``.

Usage:
    uv run python scripts/spike_model.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from triagedesk.core.schema import ExtractionResult
from triagedesk.llm.client import BIG_MODEL, SMALL_MODEL, extract

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "evidence" / "model-spike.json"

# Fixed synthetic note — synthetic data only (T-01-01-05). Same note the tracer uses.
NOTE = "RR 24, HR 118, BP 108/70, temp 38.9, alert, coughing and fast breathing"

# Budget gate (Pitfall 2): if available RAM with the larger model loaded falls
# below this, the smaller Qwen becomes the default.
MIN_AVAILABLE_MB = 1024


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def _free_available_mb() -> int:
    """Available RAM in MiB, from `free -m` (the 'available' column)."""
    for line in _run(["free", "-m"]).splitlines():
        if line.startswith("Mem:"):
            return int(line.split()[6])
    return 0


def _ollama_ps() -> str:
    return _run(["ollama", "ps"]).strip()


def _ps_size(model: str) -> str | None:
    for line in _ollama_ps().splitlines():
        if line.startswith(model):
            return line.split()[2]  # SIZE column
    return None


def _licence(model: str) -> str:
    text = _run(["ollama", "show", model, "--license"]).strip()
    return text.splitlines()[0].strip() if text else "unknown"


def _has_model(model: str) -> bool:
    return any(line.startswith(model) for line in _run(["ollama", "list"]).splitlines())


def _ensure_model(model: str) -> None:
    if not _has_model(model):
        print(f"[pull] {model} not present — pulling ...")
        subprocess.run(["ollama", "pull", model], check=True)


def _measure(model: str) -> dict:
    """Run the extraction round-trip cold then warm; record RAM, latency, validity."""
    ram_before = {"available_mb": _free_available_mb(), "ollama_ps": _ollama_ps()}
    subprocess.run(["ollama", "stop", model], capture_output=True, text=True)
    time.sleep(1)  # let the runner release memory

    t0 = time.time()
    cold: ExtractionResult = extract(NOTE, model=model)
    cold_s = round(time.time() - t0, 1)

    t0 = time.time()
    extract(NOTE, model=model)  # warm run: exercise the loaded model, timing only
    warm_s = round(time.time() - t0, 1)

    # extract() raises on empty/unparsable output, so reaching here proves the
    # response was non-empty and Pydantic-valid (T-01-01-02).
    assert isinstance(cold, ExtractionResult)
    assert cold.case.respiratory_rate == 24, cold.case.respiratory_rate

    return {
        "model": model,
        "licence": _licence(model),
        "ram_before": ram_before,
        "ram_after": {"available_mb": _free_available_mb(), "ollama_ps": _ollama_ps()},
        "ollama_ps_size_loaded": _ps_size(model),
        "cold_latency_s": cold_s,
        "warm_latency_s": warm_s,
        "response_empty": False,
        "parsed": cold.model_dump(),
    }


def main() -> int:
    _ensure_model(BIG_MODEL)
    _ensure_model(SMALL_MODEL)

    big = _measure(BIG_MODEL)
    small = _measure(SMALL_MODEL)
    small["ran_end_to_end"] = True

    # Budget gate: only the *default* depends on it; the smaller model was run either way.
    big_within_budget = big["ram_after"]["available_mb"] >= MIN_AVAILABLE_MB
    if big_within_budget:
        selected = BIG_MODEL
        rationale = (
            f"{BIG_MODEL} selected: available RAM with the model loaded was "
            f"{big['ram_after']['available_mb']} MB (>= {MIN_AVAILABLE_MB} MB budget) "
            f"and the round-trip returned valid JSON (warm {big['warm_latency_s']} s). "
            f"{SMALL_MODEL} is the safe smaller default (run end-to-end)."
        )
    else:
        selected = SMALL_MODEL
        rationale = (
            f"{SMALL_MODEL} selected: available RAM with {BIG_MODEL} loaded fell to "
            f"{big['ram_after']['available_mb']} MB (< {MIN_AVAILABLE_MB} MB budget), so the "
            f"smaller Qwen is the safe default. Both models ran the path end-to-end."
        )

    selected_record = big if selected == BIG_MODEL else small
    evidence = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": NOTE,
        "min_available_mb_budget": MIN_AVAILABLE_MB,
        # Evidence-schema keys kept as-is: "primary" = the larger candidate (qwen3.5:4b),
        # "fallback" = the smaller candidate (qwen2.5:1.5b).
        "primary": big,
        "fallback": small,
        "selected_model": selected,
        "selection_rationale": rationale,
        # Top-level mirrors the SELECTED model so the evidence is unambiguous.
        "response_empty": selected_record["response_empty"],
        "ram_after": selected_record["ram_after"],
    }

    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"[evidence] wrote {EVIDENCE_PATH}")
    print(f"[evidence] selected_model = {selected}")
    print(f"[evidence] {rationale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
