# Phase 19 — SUMMARY

**Status:** complete · **Commits:** `db418aa`, `4286ce4`

## What shipped

- **Diagram A — clinical workflow** (`docs/assets/architecture-workflow.{mmd,svg,pdf}`): patient intake →
  deterministic emergency check (with fast path) → normalize → retrieve → plan (four actions, guard,
  budgets) → frozen kernel → clinician decision → gated commit → card → queue order. Safe exits in red.
  A dashed note states the planner cannot score, approve or commit.
- **Diagram B — components and infrastructure** (`docs/assets/architecture-components.{mmd,svg,pdf}`):
  desk/CLI → LangGraph engine (planner, checkpoints) → MCP client over stdio → owned server with nine
  tools (`plan_next_step`, `request_clarification`, `commit_priority` distinguished) → local model, rule
  sources, borrowed read paths, Store seam, `triage.db`, `spans.jsonl`, audit chain, offline boundary.
  The elicitation request/response path is drawn.
- **Diagram C — reference** (`docs/assets/architecture-v1.3.{mmd,svg,pdf}`): the comprehensive view.
- **One renderer:** `docs/render-architecture.sh [stem]` (backwards compatible; default `architecture`).
- **`ARCHITECTURE.md`** leads with the two-layer shape and links all three diagrams; **641 words**
  (guard: ≤700 / ≤110 lines).
- **`README.md`** links both diagrams and marks the planner, the two proposed tools and the emergency
  bypass as *proposed, not shipped*.
- **`SECURITY.md`** states 7 shipped + 2 proposed tools; adds T-11 (answer is not approval), T-12
  (planner cannot widen its authority), T-13 (emergency bypass skips no control).
- **`STATUS.md`** gains the four-state legend (implemented+tested / partial / proposed / gap / deliberate)
  and marks G7, dynamic planning and the emergency bypass as 🧪 proposed.

## Verification

- `uv run pytest -q` → **647 passed**.
- `tests/test_docs_final.py` → 9 passed (word/line bounds, measured model name, README quickstart).
- Diagram labels checked against source names; proposed elements labelled.

## Deferred / outstanding

- The canonical `docs/assets/architecture.pdf` remains the stale v1.0 render; Phase 24 regenerates it from
  shipped code once the planner, elicitation and bypass exist.
- Four-state observation model: declared as a limitation, not implemented.
