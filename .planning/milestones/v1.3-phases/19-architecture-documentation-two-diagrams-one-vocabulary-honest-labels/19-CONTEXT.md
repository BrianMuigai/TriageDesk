# Phase 19 — Architecture documentation: CONTEXT

**Phase:** 19 · **Milestone:** v1.3 Adaptive Triage · **Date:** 2026-11-13

## Goal

A judge understands the clinical workflow in under a minute and an engineer can trace a model call, an
MCP interaction, a database access, a checkpoint write and an audit record — with every element marked
implemented, tested, proposed or outstanding.

## Decisions carried in (owner-approved 2026-11-13)

- **Two diagrams, two audiences.** A = adaptive clinical workflow (judge / clinician / product reviewer,
  < 1 minute). B = component and infrastructure (engineer, traceable call path). C = comprehensive
  reference, retained.
- **One renderer.** `docs/render-architecture.sh [stem]` renders any `docs/assets/<stem>.mmd` to SVG+PDF.
  No hand-edited binary output.
- **One vocabulary.** Diagram labels use the source names (`normalize`, `retrieve`, `plan`,
  `approval_gate`, `commit`, `handover`, the nine tool names). No synonym drift.
- **Honesty rule.** Every element is implemented+tested, partial, proposed, or outstanding. Proposed
  features carry "PROPOSED" in the diagram title and are labelled as such in README/SECURITY/STATUS.
- **The emergency bypass is drawn** (deterministic, no model, no planner) but marked proposed.
- **Not drawn because it does not exist:** a four-state observation model (stated / missing / not
  assessed / explicitly negative). Structured vitals are two-state today; text-level negation is handled.
  Recorded as an outstanding limitation (DOC-06) rather than depicted as if implemented.

## Constraint

`ARCHITECTURE.md` is guarded at ≤700 words and ≤110 lines (`tests/test_docs_final.py`). The diagram links
replace prose rather than add to it.
