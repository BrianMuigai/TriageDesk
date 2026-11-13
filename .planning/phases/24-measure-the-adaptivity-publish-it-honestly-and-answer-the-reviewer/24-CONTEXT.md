# Phase 24 — Measure the adaptivity, publish it honestly, and answer the reviewer: CONTEXT

**Phase:** 24 · **Requirements:** MEAS-01..04, DOC-01..06

## Goal

The suite measures whether the planner earns its keep — adaptive vs default-finish on the same cases, with
steps and latency — and the docs answer "is this a rules engine?" with the measured delta and the
structural proof.

## Measurement design

### Two arms, one suite

- **adaptive** (default): the planner runs (`build_graph(..., planner=True)`).
- **baseline**: `build_graph(..., planner=False)` routes `retrieve → finish_investigation` directly — exactly
  the v1.2 path, no model proposal, no investigation.

Add `planner: bool = True` to `build_graph` and `run_eval`, and a CLI flag `--no-planner` on `triagedesk
eval`. The baseline arm must keep `finish_investigation` as the only predecessor of `score`.

### Per-case facts (MEAS-01)

Extend `ReportCase` with default-empty, index-aligned lists so older reports still validate:

- `investigation_steps: list[int | None]` — `state["investigation"].steps` per run;
- `plan_actions: list[list[str]]` — the decision history per run;
- `guard_overrides: list[int]` — overridden decisions per run;
- `elicitation_outcomes: list[str | None]` — the `ClarificationAnswer.outcome` seen, if any;
- `emergency_bypass: list[bool]` — whether the fast arm fired.

Extend `Analysis` with an `adaptive` block: `runs_with_investigation`, `mean_steps`, `max_steps`,
`action_counts`, `guard_override_rate`, `elicitation_counts`, `emergency_bypass_cases`.

Do **not** seal the new volatile facts into `report_digest` if that would break the existing digest
contract; follow the precedent set by `latency_s`/`tokens_*` (volatile, not sealed). The safety facts
(`outcomes`, `invariants`) stay sealed.

### Publishing (MEAS-02, MEAS-04)

- Run **both arms in real mode** (`qwen2.5:1.5b`, Ollama is up) and save
  `evals/results/report.json` (adaptive) and `evals/results/report.baseline.json`.
- If a real-mode run is not feasible, run both arms **offline** and say `mode: offline` in the report and
  EVALS.md — never label an offline run `real`.
- `scripts/emit_evals.py` gains one generated section comparing the arms: colour correctness, coverage,
  clarified/deferred, mean steps, guard-override rate, p50/p95, and the delta. `--check` must exit 0.
- **If the delta is zero or negative, publish that.** Do not tune a threshold, a case or a mode.

## Documentation (DOC-01..06)

- `docs/AGENTIC.md` (new): the reviewer-facing answer. Structure: the challenge quote → what the system
  decides → what it cannot decide (structural proof) → the measured adaptive-vs-baseline delta → the
  emergency bypass as the counterweight → the honest limits. Link it from README and ARCHITECTURE.
- `docs/DECISIONS.md`: D31 (bounded autonomy over a frozen kernel), D32 (model proposes / guard disposes),
  D33 (server-side elicitation with four outcomes), D34 (deterministic emergency bypass), and the narrow
  revision to D1's "LLM never routes" rule.
- `STATUS.md`: G7 closed; dynamic planning ✅ with the measured evidence; the residual limits named.
- `SECURITY.md`: tool inventory now **9 shipped** (they exist and are tested; the graph calls 8 of them —
  say so precisely), and T-11/T-12/T-13 move from proposed to shipped.
- `ARCHITECTURE.md`: keep ≤700 words / ≤110 lines; add the `docs/AGENTIC.md` link only if the budget allows.
- Regenerate the **canonical** `docs/assets/architecture.{mmd,svg,pdf}` from the shipped code (the current
  one is the stale v1.0 render). Use `docs/render-architecture.sh`; keep the proposed diagrams as-is or
  retitle them "shipped" only if every element is implemented.
- DOC-06: state that the committed queue row is authoritative for handover (not the printed card), that an
  answer is not an approval, that approver identity is recorded not authenticated (G4), and that structured
  observations are two-state today with text-level negation (the four-state model is an outstanding
  limitation).

## Definition of done

`uv run pytest -q` green; `ruff` clean; `mypy` no new errors; both arms measured and published;
`scripts/emit_evals.py --check` exits 0; the reviewer answer exists and is linked; atomic commits.
