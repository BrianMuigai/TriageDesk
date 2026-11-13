# Phase 22 — Deterministic emergency bypass: CONTEXT

**Phase:** 22 · **Requirements:** EMERG-01..05

## Goal

A structured case that the pure scorer already puts in the most urgent band reaches the kernel **without
waiting for extraction or the planner** — and still cannot commit without the clinician.

## Why this is the honest counterweight to "more agentic"

The planner adds a model decision on underdetermined cases. The emergency bypass is the opposite move: it
removes the model entirely when the vitals already carry the answer. "Agentic" must include knowing when
*not* to deliberate.

## Hard constraints

- DRY + SOLID. Do not edit `core/scorer.py`, `core/citations.py`, or the `@audited` interceptor.
- The colour is still produced in exactly ONE place: the kernel's `score_priority` call. The pre-check may
  **read** a score to decide whether to skip the model; it must never emit a colour.
- The bypass skips `normalize` (and, from Phase 23, `plan`). It never skips
  `score → ground → verify → recheck → assess → approval_gate → commit`.
- No imputation: an incomplete or unstructured case never fires.

## Design

### `core/emergency.py` (new, pure)

```python
class EmergencyVerdict(BaseModel):
    fired: bool
    reason: str = ""
    trigger: list[str] = []      # human-readable facts, e.g. ["colour=RED", "tews=12"]

def assess_emergency(case: CaseInput) -> EmergencyVerdict
```

- Score with `scorer.score_priority(case, [])` — the same pure function the kernel uses.
- The **most urgent colour** comes from the loaded substrate (`core.rules.colour_urgency()`, already the
  ONE data-derived order used by the waiting room). Never a hard-coded colour literal.
- Fire only when: the score did not abstain, there are no `missing_vitals`, and the colour is the most
  urgent band. Otherwise `fired=False` with a short reason.
- Imports nothing from `llm`, `mcp`, `store` (the existing purity guard covers `core/`).

### Node + route

- New node `emergency_check` in `graph/nodes.py` (or a small `graph/emergency.py` re-exported through
  `make_nodes`): reads `state["case"]`; a `CaseInput` → `assess_emergency`; no case → not fired. Writes
  `emergency` and `route`.
- Topology: `ingest → emergency_check → (emergency: retrieve | normal: normalize → retrieve) → score → …`.
  The emergency arm skips `normalize` only; from Phase 23 the normal arm goes `retrieve → plan` while the
  emergency arm stays `retrieve → score`.
- `TRACER_NODES` gains `emergency_check` (the tracer test asserts a superset, so this is safe).

### Provenance (EMERG-05)

- `TriageState.emergency: EmergencyVerdict | None`.
- The `approval_gate` payload gains `"emergency": {...} | None` so the clinician sees that the case was
  fast-tracked and why. Additive — existing readers unaffected.
- The node span (the composition-root `_spanned` wrapper) is the audit event; no extra writer.

## Tests

1. `assess_emergency` fires on a complete case whose TEWS is the most urgent band; does not fire on a
   complete non-critical case; does not fire when a scored vital is missing; does not fire on an
   out-of-scope (paediatric) case.
2. Graph: an emergency case reaches the approval interrupt **without** calling `normalize_case`
   (spy on the tool map) and still calls `score_priority`, `retrieve_evidence`, `raise_recheck_flag`,
   `assess_confidence`.
3. Graph: the normal arm still calls `normalize_case`.
4. No queue write before the interrupt on either arm; `commit_priority` is not called.
5. The paused payload carries the emergency fact for the fast arm and `None` otherwise.
6. Purity: `core/emergency.py` imports nothing from `llm`/`mcp`/`store`.

## Definition of done

`uv run pytest -q` green; `ruff` clean; `mypy` no new errors; atomic commits; `ARCHITECTURE.md` §3 already
describes the bypass (no change needed); `STATUS.md` moves the bypass from 🧪 to ✅ **only after** the
tests prove it.
