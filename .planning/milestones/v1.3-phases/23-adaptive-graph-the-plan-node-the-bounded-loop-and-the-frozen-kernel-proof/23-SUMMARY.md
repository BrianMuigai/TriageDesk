# Phase 23 — SUMMARY

**Status:** complete · **Commits:** `18bc16f`, `056c1a4` (plus the phase-record commit)

## What shipped

The adaptive envelope is real: `retrieve → plan → {gather_evidence, ask_question, re_extract} → … →
finish_investigation → score`. The planner chooses from the closed set, the guard disposes, the loop is
bounded at three steps with no repeats, and the emergency arm enters the kernel through the same
`finish_investigation` node so the structural claim stays exact.

Measured structural facts on the compiled graph:

| Edge property | Value |
| --- | --- |
| predecessors of `score` | `{finish_investigation}` |
| predecessors of `commit` | `{approval_gate}` |
| successors of `retrieve` | `{finish_investigation, plan}` |
| successors of `plan` | `{ask_question, finish_investigation, gather_evidence, re_extract}` |

## Verification

- `uv run pytest -q` → **891 passed**.
- `uv run ruff check src tests` → clean.
- Offline eval (`--offline`, 24 cases × 3 runs) → gate **passed**, **48/48 colour-expected runs correct**,
  under-triage `[]`, over-triage `[]`, INV-1..INV-4 all true — identical to the v1.2 measurement, so the
  planner changed no colour.

## Honest gaps

- The adaptive arm is proven with fake tools in the graph tests; the live model path is exercised by the
  real-mode eval in Phase 24, which is where the adaptive-vs-baseline delta is measured.
- `ask_question`'s interrupt round-trip is proven at the adapter layer (Phase 21) and with a fake tool here;
  the desk's question surface is Phase 21's, unchanged.
