<!-- generated-by: gsd-doc-writer -->
# TESTING — TriageDesk

How the offline proof suite is organised, how to run it, and how the measured evaluation is
produced. Every command below was verified against this commit. The suite itself is the source
of truth for its size: **600 tests collected as of this commit** (`uv run pytest --collect-only -q`).

Related: [`../README.md`](../README.md) (quickstart), [`../EVALS.md`](../EVALS.md) (measured
results — the single published source for every number), [`DEMO.md`](DEMO.md) (demo runbook).

## 1. Quick start

```bash
uv run pytest -q              # full suite; offline — no model, no borrowed MCP subprocess
uv run ruff check src tests   # lint
```

`uv run` syncs the locked environment from `uv.lock` before running. Pytest is configured in
`pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`), so no extra flags or
environment setup are required. Tests use the shared doubles in `tests/conftest.py` (one
in-memory `Store`, an autouse `tmp_path` span sink), which is why the suite never launches
Ollama or `npx mcp-sqlite`.

## 2. Test layers

| Layer | What it proves | Modules |
| --- | --- | --- |
| Safety invariants | Handover card holds no dx/rx prose; no dx/rx tool is registered; the graph path imports no network client or credentials; INV-1..INV-4 fail closed | `test_safety_spine.py`, `test_eval_invariants.py`, `test_purity.py`, `test_graph_purity.py` |
| Gate & commit idempotency | `commit_priority` refuses without a valid token, commits once on retry, supersedes an edit in place, and leaves no queue row on `dismiss` | `test_commit_idempotent.py`, `test_graph_durable.py`, `test_durable_cli.py` |
| Graph routing | Score path is model-free; RECHECK/RECOVER/ABSTAIN terminals route correctly; bounded retry fires exactly once; confidence deferral is honest | `test_graph_recheck.py`, `test_graph_confidence.py`, `test_graph_grounding.py`, `test_graph_recovery.py` |
| Desk surface | The nurse-facing bridge works over loopback with the injected store and a `tmp_path` checkpoint; forms and waiting-list states behave | `test_desk.py`, `test_desk_forms.py`, `test_desk_waiting.py`, `test_desk_online.py` |
| Audit chain | One hash-chained record per tool call; chain verifies after restart; tampering is reported; reconciliation finds a queue row with no approval record | `test_audit_chain.py`, `test_hashing.py` |
| Eval harness | Case coverage, the declared E-09 failure, direction split, report shape, invariants, extraction fidelity, and tracer hygiene | `test_eval_suite.py`, `test_eval_report.py`, `test_eval_invariants.py`, `test_eval_fidelity.py`, `test_eval_tracer.py`, `test_eval_honest_terminal.py` |
| Store seam | The `Store` protocol holds for both the in-memory double and the borrowed SQLite wiring; the server seam is cleared on error | `test_store_seam.py`, `test_borrowed_store.py` |
| Domain rules | SATS bands/discriminators, scorer overrides, matcher determinism, recheck, retrieval, and schema rejection | `test_sats_bands.py`, `test_sats_discriminators.py`, `test_scorer*.py`, `test_matcher*.py`, `test_recheck.py`, `test_retrieval.py`, `test_schema_rejects.py` |
| Doc guards | Submission docs stay within declared bounds and keep the real quickstart; runbooks match the shipped commands; `EVALS.md` is a projection of the report | `test_docs_final.py`, `test_readme_runbook.py`, `test_demo_runbook.py`, `test_mcp_runbook.py`, `test_desk_runbook.py` |
| Observability | Node/tool/model spans carry the content trace id, and no span artefact leaks into the repository root | `test_observability.py` |

## 3. The evaluation harness

```bash
# Measured run — real local model (Ollama + qwen2.5:1.5b)
uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json

# Deterministic CI gate — stubbed model + golden extractions, no Ollama
uv run triagedesk eval --cases evals/cases --runs 3 \
  --report evals/results/report.ci.json --offline

# One case, one run (filter + fewer samples)
uv run triagedesk eval --offline --case E-02 --runs 1 --report /tmp/opencode/report.json
```

Flags (from `triagedesk eval --help`):

| Flag | Meaning | Default |
| --- | --- | --- |
| `--cases` | Directory of `.yaml` case fixtures | `evals/cases` |
| `--runs` | Runs per case | `3` |
| `--report` | Report output path (JSON) | `evals/results/report.json` |
| `--offline` | Stub the model, use golden extractions (deterministic CI mode) | off |
| `--case` | Run a single case id | all cases |

The command exits `0` when the gate passes and `1` when any safety invariant or undeclared
accuracy miss fails, which is what makes it usable as a CI gate. The report is written to the
`--report` path. **Real-mode results are model-dependent** — latency, token counts, stability,
and occasionally colour can vary with the machine and model build. The deterministic offline
run is the CI gate; it is not a substitute for the measured run. [`../EVALS.md`](../EVALS.md)
is the single published source for the measured figures and the declared failures; do not copy
its numbers into other docs.

## 4. Regenerating EVALS.md

```bash
uv run python scripts/emit_evals.py --write   # refresh result cells from the report
uv run python scripts/emit_evals.py --check   # exit 1 if EVALS.md is stale
```

`EVALS.md` is a hand-written narrative whose **result cells** are generated from
`evals/results/report.json`. The generator rewrites only the §3 measured column, the §4
`Runs`/`Result` cells, the §5 invariant results, the §6.1 deferral record, and the source line;
the prose is preserved. It is idempotent.

Before rendering, it recomputes the report's `report_digest` and **refuses to publish a
report whose digest does not match** — so a hand-edited report cannot silently become a
published number. It also fails closed if the §4 case rows and the report's case set differ
(a missing or stale row is an error, not a silent skip). `--check` is the guard used by the
test suite; `--write` is the only supported way to update the document.

## 5. Known gotchas

- **`spans.jsonl` in the repo root.** A prior `uv run triagedesk demo` or eval run writes this
  gitignored runtime sink. `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`
  asserts it is absent, so the test fails if a demo ran first. The fix is to remove the
  artefact (`rm spans.jsonl`), not to edit the test. The autouse fixture redirects the sink to
  `tmp_path` for the rest of the suite.
- **No checks on a PR.** Both workflows (`.github/workflows/smoke.yml`, `eval-gate.yml`) are
  `workflow_dispatch`-only after the submission freeze, so a pull request shows no CI checks.
  Run `uv run ruff check src tests`, `uv run pytest -q`, and the offline eval locally before
  pushing. `eval-gate` runs lint, tests, then the `--offline` eval; `smoke` runs the bare
  `uv run triagedesk demo`.

## 6. What is not covered

- **No clinician review.** Expected colours derive from published SATS rules, not from
  clinician adjudication; see [`../EVALS.md`](../EVALS.md) §7 for the declared gap.
- **Synthetic data only.** The fixtures are synthetic; no real patient data is used or leaves
  the machine.
- **Small samples.** The measured set and the calibration split are small; see
  [`../EVALS.md`](../EVALS.md) §3 and §7. The calibration figure is a declared small-sample
  measure, not a validated probability.
- **Real-mode variance is not CI-gated.** CI runs the offline stub; the measured report must
  be regenerated on the target machine and published through the generator.
