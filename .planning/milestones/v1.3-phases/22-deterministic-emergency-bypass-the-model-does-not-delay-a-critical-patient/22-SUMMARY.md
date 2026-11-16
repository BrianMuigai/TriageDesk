---
phase: 22
phase_name: "Deterministic emergency bypass — the model does not delay a critical patient"
milestone: v1.3
requirements: [EMERG-01, EMERG-02, EMERG-03, EMERG-04, EMERG-05]
plans: ["22-01", "22-02"]
status: complete
completed: "2026-11-14"
commits:
  - 5992e31
  - 955da91
  - 1418b38
metrics:
  plans: 2
  tests_added: 21
  total_tests: 857
  mypy_errors: 29
  mypy_baseline: 29
---

# Phase 22: Deterministic emergency bypass Summary

## Outcome

A structured case whose vitals the pure scorer already puts in the most urgent band now reaches
the kernel **without waiting for extraction** — and still cannot write a queue row or bypass the
clinician. The model is removed only where the answer is already deterministic; the safety spine
is untouched.

The graph is now:

```
ingest → emergency_check → (fast: retrieve | normal: normalize → retrieve)
       → score → ground → verify → recheck → assess → approval_gate → commit → handover
```

## Requirements

| Requirement | Verdict | Where |
| --- | --- | --- |
| EMERG-01 — pure pre-check before any model call; fast arm enters at `retrieve → score` | met | `core/emergency.py`; `graph/nodes.py::emergency_check`; `graph/build.py` topology |
| EMERG-02 — reuses the ONE scorer and loaded bands; never produces a colour | met | `assess_emergency` calls `score_priority(case, [])`; `EmergencyVerdict` has no colour field |
| EMERG-03 — still passes verify/recheck/assess/gate/commit; no queue row, no clinician bypass | met | `tests/test_emergency_bypass.py` fast-arm kernel + no-write proofs |
| EMERG-04 — incomplete/unstructured cases never fire | met | missing-vital, out-of-scope and unstructured tests; eval-case predicate sweep |
| EMERG-05 — recorded as provenance and an audit/span event | met | `TriageState.emergency`, approval payload `emergency`, `emergency_check` node span, durable reload |

## What changed

| File | Change |
| --- | --- |
| `src/triagedesk/core/emergency.py` | new pure verdict + pre-check |
| `src/triagedesk/graph/state.py` | `emergency` channel |
| `src/triagedesk/graph/nodes.py` | `emergency_check`; approval payload fact |
| `src/triagedesk/graph/build.py` | router, topology, `TRACER_NODES`, msgpack allowlist |
| `src/triagedesk/graph/__init__.py` | export the router |
| `tests/conftest.py` | `EMERGENCY_CASE` |
| `tests/test_emergency.py` | pre-check + both-arm suite |
| `tests/test_emergency_bypass.py` | proof suite |
| `tests/test_purity.py` | named emergency purity contract |
| `tests/test_no_duplicated_sats.py` | ONE pinned structural-key exemption |
| `STATUS.md` | bypass moved 🧪 → ✅ |

## Deviations

1. **Durable allowlist extended** (Rule 2): a blocked Pydantic type silently deserialises as a
   dict, which would erase the verdict on resume. `_allowed_msgpack_modules()` now covers
   `core.schema` + `core.emergency`.
2. **DRY guard scope** (Rule 1): the CONTEXT-fixed `emergency` channel key collides with a loaded
   discriminator category spelling. The guard gained one exact, documented
   `STRUCTURAL_CHANNEL_KEYS` exemption, pinned narrow by its own test — it was not weakened.

## Honest gaps

- The pre-check deliberately ignores discriminators (they are not retrieved yet on the fast arm).
  A case that is RED only because of a discriminator (e.g. eval E-04: TEWS 4 + emergency AVPU
  discriminator) takes the normal path and earns RED in the kernel. This is the intended reading
  of "the vitals already carry the answer", not a bypass miss.
- The desk's **online** mode computes extraction before it enters the graph, so the bypass skips
  the in-graph `normalize` node but not that earlier pre-computation. The in-graph guarantee
  (no model on the fast arm) is proven; moving the online extraction call behind the pre-check
  is out of scope for this phase.
