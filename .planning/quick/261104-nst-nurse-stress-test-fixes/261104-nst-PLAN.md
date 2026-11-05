---
quick_id: 261104-nst
slug: nurse-stress-test-fixes
status: completed
branch: post-submission/hardening
autonomous: true
depends_on: []
files_modified:
  - src/triagedesk/core/matcher.py
  - src/triagedesk/llm/notes.py
  - src/triagedesk/llm/client.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/desk/copy.py
  - src/triagedesk/desk/views.py
  - tests/test_matcher.py
  - tests/test_llm_notes.py
  - tests/test_mcp_tools.py
  - tests/test_desk.py
---

# Quick task 261104-nst — close the three nurse-stress-test defects

## Goal

Fix the three highest-severity findings from the nurse stress test without touching the
concurrent hardening work (`confidence.py`, `graph/build.py`, `graph/nodes.py`,
`graph/state.py`, `test_graph_tracer.py`, `src/triagedesk/skills/`, `docs/MCP.md`, `README.md`).

## Deliverables

1. **Negation-aware matcher** (`core/matcher.py`, `tests/test_matcher.py`): a negator in the
   same clause suppresses an alias match. "not confused" must not be RED, "no chest pain" must
   not be ORANGE. Boundary rules: punctuation and contrast/conjunction words end the negation
   scope; "or" continues it.
2. **Fail closed at the tool boundary** (`mcp/server.py`, `tests/test_mcp_tools.py`):
   `score_priority` returns `abstained=True`, `colour=None`, `citations=[]` and a named
   `missing_vitals` reason when a scored vital is absent — so a raw MCP caller cannot get a
   GREEN with no citations. The pure `core.scorer.score_priority` stays a calculator; the graph
   still routes on `missing_vitals`.
3. **Deterministic extraction hardening** (`llm/notes.py`, `llm/client.py`,
   `tests/test_llm_notes.py`): after the model returns, (a) null any numeric/categorical value
   the note does not state, (b) take the AFTER value of a serial reading, (c) convert an
   explicit or >45 temperature from °F, (d) recover a stated age/months and stated
   mobility/AVPU/trauma deterministically. This fixes the before-value under-triage, the
   invented mobility, the dropped age, and the 98.6 °F guess.
4. **Name the missing vital in the desk recovery panel** (`desk/copy.py`, `desk/views.py`,
   `tests/test_desk.py`): "A scored vital is missing (temperature). Re-measure before scoring."

## Verification

```bash
uv run pytest tests/test_matcher.py tests/test_llm_notes.py tests/test_mcp_tools.py tests/test_desk.py tests/test_graph_recovery.py tests/test_eval_suite.py -q
uv run ruff check src tests
uv run mypy src
```

Then re-run the nurse battery: negation, incomplete case, serial note, °F note, recovery UI.

## Out of scope (recorded, not fixed here)

Coverage expansion (S2-1), the deferred GREEN anchor (S2-3), the E-09 copy leak (S3-1), and
latency (S4-1). See `.planning/nurse-stress-test/REPORT.md`.
