---
phase: 22
phase_name: "Deterministic emergency bypass — the model does not delay a critical patient"
verified_at: "2026-11-14"
verifier: gsd-executor
status: passed
covered_files:
  - src/triagedesk/core/emergency.py
  - src/triagedesk/graph/state.py
  - src/triagedesk/graph/nodes.py
  - src/triagedesk/graph/build.py
  - src/triagedesk/graph/__init__.py
  - tests/conftest.py
  - tests/test_emergency.py
  - tests/test_emergency_bypass.py
  - tests/test_purity.py
  - tests/test_no_duplicated_sats.py
  - STATUS.md
covered_digest: "v4:sha256:ce449b4b30dc3d84449b67f70a0addf4e37c1655f566e38b87be4291c62e2354"
commands:
  - "uv run pytest -q -> 857 passed"
  - "uv run ruff check src tests -> All checks passed"
  - "uv run mypy src -> 29 errors in 6 files (baseline 29; no new errors)"
---

# Phase 22 Verification

## Gate results

| Gate | Command | Result |
| --- | --- | --- |
| Tests | `uv run pytest -q` | **857 passed** (Phase 21 left 836; +21) |
| Lint | `uv run ruff check src tests` | clean |
| Types | `uv run mypy src` | 29 errors, exactly the pre-existing baseline; `core/emergency.py` contributes none |

The mypy error set remains confined to `core/rules.py`, `demo/run.py`, `graph/build.py`,
`graph/nodes.py`, `graph/state.py` and `mcp/adapter.py`; no new error was introduced by this
phase (the two `graph/build.py` errors are the same pre-existing `run_case`/comprehension
diagnostics, shifted in line number).

## Requirement → evidence

| Requirement | Verdict | Evidence |
| --- | --- | --- |
| **EMERG-01** — a pure pre-check runs before any model call; when it fires the graph skips extraction and the planner and enters at `retrieve → score` | met | `core/emergency.py::assess_emergency`; `graph/nodes.py::emergency_check`; `graph/build.py::route_after_emergency`; topology test `tests/test_emergency.py::test_topology_has_the_pre_check_and_both_arms`; `tests/test_emergency_bypass.py::test_fast_arm_skips_extraction_but_runs_the_kernel` (no `normalize_case`, order starts `ingest → emergency_check → retrieve → score`) |
| **EMERG-02** — reuses the ONE scorer and loaded bands; cannot disagree with the kernel and never produces a colour | met | `assess_emergency` calls `scorer.score_priority(case, [])`; the most urgent band is `max(core.rules.colour_urgency())`; `EmergencyVerdict.model_fields == {fired, reason, trigger}` (`tests/test_emergency.py::test_verdict_has_no_colour_or_priority_field`); `tests/test_purity.py::test_emergency_module_is_pure` |
| **EMERG-03** — the fast arm still passes `verify → recheck → assess → approval_gate → commit`; it cannot write a row and cannot bypass the clinician | met | `tests/test_emergency_bypass.py::test_fast_arm_skips_extraction_but_runs_the_kernel` (executed order includes verify/recheck/assess/approval_gate); `::test_fast_arm_writes_nothing_before_the_gate` (empty write list, no `commit_priority`, `commit_result is None`); `::test_fast_arm_payload_carries_the_bypass_fact` |
| **EMERG-04** — an incomplete or unstructured case never fires; no imputation | met | `tests/test_emergency.py::test_does_not_fire_when_a_scored_vital_is_missing`, `::test_does_not_fire_on_an_out_of_scope_case`, `::test_does_not_fire_on_an_unstructured_case`; `::test_firing_matches_the_data_derived_predicate_across_bundled_cases` sweeps all 24 eval cases; `tests/test_emergency_bypass.py::test_normal_arm_runs_the_unchanged_sequence` |
| **EMERG-05** — the bypass is a provenance fact and an audit/span event | met | `TriageState.emergency`; `approval_gate` payload `emergency`; `tests/test_emergency_bypass.py::test_emergency_check_emits_one_span_with_the_trace_id` (one node span, content trace id); `::test_a_paused_run_reloads_the_verdict_as_a_typed_model` (durable provenance survives restart) |

## Invariants re-checked (unchanged by this phase)

| Invariant | Evidence |
| --- | --- |
| The colour is produced in exactly ONE place | `core/scorer.py` untouched (`git diff 3b0daa2..HEAD --name-only` excludes it); the pre-check reads `score_priority` and emits no colour |
| `core/citations.py` and the `@audited` interceptor are untouched | same diff check |
| `commit_priority` remains the only queue-affecting tool | `tests/test_emergency_bypass.py` proves no pre-gate call; `tests/test_commit_idempotent.py` still green |
| The approval gate still needs a named clinician | `tests/test_graph_durable.py` approve/edit/dismiss suites still green |
| No SATS value is inlined under `src/` | `tests/test_no_duplicated_sats.py` green; the one structural-key exemption is pinned to `{"emergency"}` |
| The normal arm is unchanged apart from the pre-check node | `tests/test_emergency_bypass.py::test_normal_arm_runs_the_unchanged_sequence` |

## Honest notes

- The pre-check sees no discriminators by design, so a discriminator-only emergency (E-04) takes
  the normal path and earns its colour in the kernel. This is intentional.
- The desk's online mode still computes extraction before entering the graph; the bypass removes
  the in-graph `normalize` node, which is the guarantee this phase proves.
