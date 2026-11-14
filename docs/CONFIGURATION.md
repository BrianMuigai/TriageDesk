<!-- generated-by: gsd-doc-writer -->
# CONFIGURATION — TriageDesk

Every configurable surface of the shipped commands. Run steps: [`README.md`](../README.md); desk: [`docs/DESK.md`](./DESK.md); numbers: [`EVALS.md`](../EVALS.md).

## 1. Runtime

- Python `>=3.12,<3.13`; `.python-version` pins `3.12`. `uv` manages the environment.
- `uv.lock` is committed; `uv run` syncs from it before executing (`uv sync --locked` for an explicit install).
- Entry point: `triagedesk = "triagedesk.cli:main"` (`pyproject.toml`).

```bash
uv run triagedesk demo     # offline storyboard, no model call
uv run triagedesk --help   # eval, demo, resume, replay, desk
```

## 2. Model

| Setting | Value | Where |
|---|---|---|
| Default model | `qwen2.5:1.5b` (fallback `qwen3.5:4b`) | `src/triagedesk/llm/client.py` — `DEFAULT_MODEL`, `BIG_MODEL` |
| Decoding options | `temperature=0`, `seed=42`, `num_ctx=2048` | same file — `OPTIONS` |
| `think` | `False` (mandatory) | `extract()` / `extract_async()` call sites |

**There is no CLI flag and no environment variable to switch models.** The tag is a code
constant: edit `DEFAULT_MODEL`, or pass `model=` where `extract`/`extract_async` is called
directly. `provenance.model_tag` reads that same constant.

`OLLAMA_HOST` is the only environment variable that configures the project. The `ollama`
client library uses it for the server address (default `http://127.0.0.1:11434`), and
`evals/report.py` reads it to probe `/api/version`; a bare `host:port` is prefixed `http://`.

The CLI calls `harden_offline()` before importing any handler, removing
`LANGSMITH_TRACING*`, `LANGCHAIN_TRACING*` and `OTEL_EXPORTER_OTLP*`. These are neutralised,
not configurable.

## 3. Storage

Two SQLite files, in the working directory, both gitignored (`*.db`):

| File | Holds | Configurable? |
|---|---|---|
| `triage.db` | Clinical record, queue rows and hash-chained audit log — `store/__init__.py` `DOMAIN_DB_PATH`, via the borrowed SQLite MCP server | **No CLI flag.** `default_store()` always uses `triage.db`. |
| `checkpoints.db` | LangGraph runtime state only — `graph/build.py` `CHECKPOINTS_DB_PATH` | Yes, `--db` on `demo --durable`, `resume`, `replay`, `desk`. |

They are separate by design: the audit record is an immutable clinical artefact, a checkpoint
is disposable runtime state, so a checkpointer write is never mistaken for an audit event.
Deleting `checkpoints.db` loses paused threads, not committed queue rows.

## 4. CLI flags

From `src/triagedesk/cli.py` (argparse); each verified with `uv run triagedesk <cmd> --help`.

| Command | Flag | Default | Meaning |
|---|---|---|---|
| `demo` | `--online` | off | Use the pulled local model instead of the offline golden fixture |
| `demo` | `--beat NAME` | all beats | Run one storyboard beat (repeatable) |
| `demo` | `--list` | — | List beat names/labels, then exit |
| `demo` | `--fixture DIR` | `evals/cases` | Case-fixture directory |
| `demo` | `--durable` | off | Run one beat to the durable approval gate and print the resume command |
| `desk` | `--host HOST` | `127.0.0.1` | Bind address (loopback only) |
| `desk` | `--port PORT` | `8765` | Bind port |
| `desk` | `--online` | off | Real local extraction on the free-text complaint |
| `eval` | `--cases DIR` | `evals/cases` | Case-fixture directory |
| `eval` | `--runs N` | `3` | Runs per case |
| `eval` | `--report FILE` | `evals/results/report.json` | JSON report output |
| `eval` | `--offline` | off | Stub the model, use golden extractions (deterministic CI) |
| `eval` | `--case ID` | all | Run a single case id |
| `resume` | `--thread-id ID` | **required** | Content-derived id printed by `demo --durable` |
| `resume` | `--decision` | **required** | `approve` \| `edit` \| `dismiss` |
| `resume` | `--approver NAME` | none | Gate-required for `approve`/`edit` |
| `resume` | `--role ROLE` | none | Gate-required for `approve`/`edit` |
| `resume` | `--colour COLOUR` | none | Gate-required for `edit` |
| `replay` | `--thread-id ID` | **required** | Case to reconstruct (read-only) |

`--db FILE` (default `checkpoints.db`) is accepted by `demo --durable`, `resume`, `replay`
and `desk`; it selects the checkpoint file, never `triage.db`.

## 5. Desk modes

| Mode | How | Behaviour |
|---|---|---|
| Offline (default) | `uv run triagedesk desk` | Deterministic; no model call. |
| Online | `uv run triagedesk desk --online` | One real `extract_async` per new complaint, with a precompute cache; failure degrades to the offline path. |

The bind guard in `DeskServer.__init__` requires a **literal loopback IP** (`127.0.0.0/8` or
`::1`); `--host localhost` is refused and the CLI exposes no override, so a non-loopback bind
cannot be requested. Requests are also checked for loopback `Host`, same-origin `Origin` and a per-server CSRF token — see [`docs/DESK.md`](./DESK.md).

## 6. Rule substrate

All SATS thresholds are data, never code; the only reader is `src/triagedesk/core/rules.py`, and nothing else may inline a band, threshold, colour or citation.

| File | Contents |
|---|---|
| `data/sats_tews.yaml` | TEWS bands, TEWS-total → colour thresholds, target times, out-of-scope predicates, citations |
| `data/sats_discriminators.yaml` | Discriminator ids → category → colour, aliases, citation refs |
| `data/text_terms.yaml` | Linguistic terms used by the deterministic matcher |

Paths resolve from the repository root (`parents[3]` of `core/rules.py`), so the files must ship with the checkout; the eval report recomputes their hashes, making drift detectable.

## 7. Evaluation options

```bash
uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json
uv run triagedesk eval --offline      # deterministic CI, model stubbed
uv run triagedesk eval --case E-09    # one case
```

`--offline` labels the report `mode: "offline"` so a stubbed run is never presented as
measured. Every report carries `report_digest` and provenance (model, Ollama version, prompt/schema/rule hashes, commit).

`EVALS.md` is a projection of the report, not hand-edited:

```bash
uv run python scripts/emit_evals.py --report evals/results/report.json --write
uv run python scripts/emit_evals.py --report evals/results/report.json --check
# §3.3 additionally reads evals/results/report.adaptive.json (the adaptive arm) and
# evals/results/report.baseline.json (the `--no-planner` arm).
```

Both accept `--evals PATH` (default `EVALS.md`); `--check` exits non-zero on any difference. Measured figures live in [`EVALS.md`](../EVALS.md).
