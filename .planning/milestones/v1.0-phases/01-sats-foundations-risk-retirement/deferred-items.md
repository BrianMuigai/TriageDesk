# Deferred items — Phase 01 (SATS Foundations & Risk Retirement)

Out-of-scope discoveries logged during execution and **not** fixed here (SCOPE BOUNDARY:
only issues directly caused by the current task are auto-fixed).

| # | Found in plan | File | Issue | Disposition | Status |
|---|---------------|------|-------|-------------|--------|
| 1 | 01-02 | `scripts/spike_model.py:87` | ruff `F841` — local variable `warm` assigned but never used (pre-existing from 01-01) | Verified already fixed at the v1.1 close: the warm-run timing value is now used and `uv run ruff check .` passes. | Resolved |
| 2 | 01-02 | `src/triagedesk/llm/prompts.py:10,13,17` | ruff `E501` — long lines inside the prompt template literal (pre-existing from 01-01) | Verified already fixed at the v1.1 close: the module carries an explicit `E501` per-file ignore (the prompt bytes are the SAFE-04 artefact) and `uv run ruff check .` passes. | Resolved |

_Logged: 2026-10-09 (Plan 01-02). Resolutions recorded 2026-10-13 at the v1.1 milestone close (the
`audit-open acknowledge` CLI writer cannot anchor a GFM-table-shaped entry, so the resolution is recorded
in the file directly; both items were verified already fixed, not merely suppressed)._
