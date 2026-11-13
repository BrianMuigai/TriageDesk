---
phase: 22
plan: "02"
subsystem: tests
tags: [emergency, bypass, proof, observability, purity]
requires:
  - core.emergency.assess_emergency
  - graph.build.emergency_check
provides:
  - "proof: fast arm skips normalize_case and keeps the kernel"
  - "proof: no pre-gate queue write on either arm"
  - "proof: the bypass is a span and a payload fact"
affects:
  - tests/test_purity.py
  - STATUS.md
tech-stack:
  added: []
  patterns:
    - "the executed node order is read from the ONE span sink"
    - "durable pause reloads a typed verdict"
key-files:
  created:
    - tests/test_emergency_bypass.py
  modified:
    - tests/test_purity.py
    - STATUS.md
decisions:
  - "The audit event is the existing composition-root _spanned wrapper; no second writer was added."
  - "The proof reads node order from observability.spans.read_spans, so the audit fact and the topology proof share one source."
metrics:
  duration: "~20 min"
  completed: "2026-11-14"
  tasks: 3
  commits: 1
  plan_head_before: "955da91"
  plan_head_after: "1418b38"
status: complete
---

# Phase 22 Plan 02: Proof — the model is skipped, the kernel is not Summary

## One-liner

Six offline proofs show the fast arm never calls `normalize_case` while every kernel tool and
node still runs, the normal arm keeps today's order, nothing is written before the gate, and
the bypass is a span plus a typed payload fact that survives a durable pause.

## What was proven

- **Model skipped:** on the fast arm `normalize_case` is absent from the recorded calls while
  `match_discriminators`, `score_priority`, `retrieve_evidence`, `raise_recheck_flag` and
  `assess_confidence` all run.
- **Kernel intact:** the executed node order is exactly
  `ingest, emergency_check, retrieve, score, ground, verify, recheck, assess, approval_gate`.
- **Gate respected:** the run pauses at the interrupt, `commit_result` is `None`, the write
  list is empty and `commit_priority` was never called.
- **Normal arm unchanged:** the order is today's order with `emergency_check` inserted after
  `ingest`; `normalize_case` still runs and the colour equals the scorer's own result.
- **Audited:** exactly one `node` span named `emergency_check` carries the content-derived
  trace id; the fast payload names `fired`, `reason` and `trigger`, the normal payload is `None`.
- **Durable:** a paused run reopened from SQLite still reports an `EmergencyVerdict`.
- **Purity:** `core/emergency.py` is named as a pure contract beside the planner.

## Deviations from Plan

None — the plan executed as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- `tests/test_emergency_bypass.py` exists.
- Commit `1418b38` is an ancestor of HEAD.
- `uv run pytest -q` → 857 passed.
