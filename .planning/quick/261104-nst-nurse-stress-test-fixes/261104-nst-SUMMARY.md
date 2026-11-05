# Quick task 261104-nst — summary

**Status:** completed · **Date:** 2026-11-04

## What changed

1. **Negation-aware matching (S1-1).**
   - `data/text_terms.yaml` is the new single source for interpretation terms (negators,
     clause boundaries, categorical phrases).
   - `core/rules.py` loads it through the one loader (`get_text_terms()`).
   - `core/matcher.py` suppresses an alias inside a negation scope. Boundary rules:
     punctuation/contrast/conjunction ends the scope; `or` continues it; `not only` is additive.
   - `core/retrieval.py` now reuses `alias_matches` / `tokenize_with_spans`, so retrieval
     cannot disagree with the matcher on a negated phrase.

2. **Fail-closed tool contract (S1-4).**
   - `mcp/server.py::score_priority` returns `abstained=True`, `colour=None`, `tews=None`,
     no rules/citations, and a named `reason` when `missing_vitals` is non-empty.
   - `core/scorer.score_priority` is unchanged; the graph still routes on `missing_vitals`.

3. **Deterministic extraction grounding (S1-2, S1-3).**
   - New `llm/notes.py::grounded_case`, applied by `llm/client.py::extract` after validation:
     drops unstated numeric/categorical values, takes the AFTER value of serial readings,
     converts explicit or >45 °F, and recovers a stated age/months/mobility/AVPU/trauma.

4. **Recovery copy (S2-2).**
   - `desk/copy.py::recovery_copy` and `desk/views.py::_terminal_panel` now name the missing
     vitals: "A scored vital is missing (temperature). Re-measure before scoring."

## Tests added

- `tests/test_matcher.py`: five negation/boundary cases.
- `tests/test_llm_notes.py`: serial, BP pair, °F, invented mobility, unstated temperature,
  recovered age/months, unchanged complete case.
- `tests/test_mcp_tools.py`: incomplete `score_priority` refuses.
- `tests/test_desk.py`: recovery panel names the vital.
- `tests/test_retrieval.py`: asserts the shared negation-aware helper.

## Verification

- `uv run pytest -q` → **528 passed**
- `uv run ruff check src tests` → clean
- `mypy` on every changed file → clean (repo-wide mypy still reports the pre-existing
  missing `types-PyYAML` stub)
- Live MCP re-test: `not confused` / `no chest pain` / `denies chest pain` / `no shortness of
  breath` → `no_match`; serial `RR 18 -> 24, HR 92 -> 118` → `24/118`; `temp 98.6` → `37.0`;
  dropped age `28` recovered; incomplete case → no colour + 7 named missing vitals.

## Deliberately out of scope

- Coverage expansion (S2-1), the deferred GREEN anchor (S2-3), the internal `E-09` copy leak
  (S3-1), and model/MCP latency (S4-1). Recorded in
  `.planning/nurse-stress-test/REPORT.md` with the competition ranking.
- `docs/MCP.md` / `README.md`: owned by the concurrent skill-install task; the tool docstring
  documents the new refusal contract until that lands.
