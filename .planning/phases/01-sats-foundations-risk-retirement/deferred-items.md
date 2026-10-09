# Deferred items — Phase 01 (SATS Foundations & Risk Retirement)

Out-of-scope discoveries logged during execution and **not** fixed here (SCOPE BOUNDARY:
only issues directly caused by the current task are auto-fixed).

| # | Found in plan | File | Issue | Disposition |
|---|---------------|------|-------|-------------|
| 1 | 01-02 | `scripts/spike_model.py:87` | ruff `F841` — local variable `warm` assigned but never used (pre-existing from 01-01) | Deferred — unrelated to 01-02; fix in a later plan or a dedicated cleanup. |
| 2 | 01-02 | `src/triagedesk/llm/prompts.py:10,13,17` | ruff `E501` — long lines inside the prompt template literal (pre-existing from 01-01) | Deferred — the long lines are prompt prose; unrelated to 01-02. |

_Logged: 2026-10-09 (Plan 01-02)._
