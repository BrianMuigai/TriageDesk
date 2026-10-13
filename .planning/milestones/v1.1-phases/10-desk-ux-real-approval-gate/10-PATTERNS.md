# Phase 10: Desk UX & Real Approval Gate - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 9 (3 new modules/assets sets, 1 new test, 1 new doc, 1 doc edit, 1 config edit, 1 CLI edit)
**Analogs found:** 7 / 9 (2 static assets have no code analog — see *No Analog Found*)

> **Read this with `docs/CONVENTIONS.md` (DRY + SOLID, iron-clad).** Every assignment below is chosen to
> preserve the project's one-schema / one-citation-helper / one-colour-producer / one-pause-resume-helper
> invariants. The surface is **presentation-only**: it renders graph-owned typed outputs and never
> re-derives a colour, citation, target time, or confidence value (D10-02/D10-04/D10-07).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/triagedesk/desk/__init__.py` | package-init | request-response (re-export) | `src/triagedesk/demo/__init__.py` | exact (peer package init) |
| `src/triagedesk/desk/server.py` | controller/service (bridge) | request-response | `src/triagedesk/demo/run.py` + `src/triagedesk/durable.py` | exact (peer runner + the plumbing it reuses) |
| `src/triagedesk/desk/static/index.html` | view/asset | static file-I/O | *(none — see No Analog Found)* | none |
| `src/triagedesk/desk/static/styles.css` | asset | static file-I/O | *(none — see No Analog Found)* | none |
| `src/triagedesk/cli.py` (MODIFY) | CLI/entry | request-response | the existing `resume`/`replay` subcommands in the same file | exact (same-file precedent) |
| `pyproject.toml` (MODIFY) | config | n/a | the existing `src/triagedesk/replay.py` TID251 ignore | exact (same-block precedent) |
| `tests/test_desk.py` | test | request-response + in-process handler | `tests/test_durable_cli.py` + `tests/test_demo.py` | exact |
| `docs/DESK.md` | doc | n/a | `docs/DEMO.md` (structure) + `tests/test_demo_runbook.py` (guard pattern) | role-match |
| `docs/DECISIONS.md` (MODIFY) | doc | n/a | the existing D-rows (last is `D22`) | exact (same-file precedent) |

All analog paths above are **git-tracked source** (verified with `git ls-files` this session):
`src/triagedesk/{durable.py,cli.py,demo/run.py}`, `tests/{conftest.py,test_durable_cli.py,test_demo.py,test_no_duplicated_sats.py}`,
`pyproject.toml`, `docs/{DECISIONS.md,DEMO.md}`. No gitignored mirror path is used.

---

## Pattern Assignments

### `src/triagedesk/desk/__init__.py` (package-init, request-response)

**Analog:** `src/triagedesk/demo/__init__.py`

The peer package exposes exactly ONE public seam and re-exports it, so callers never import a private
module. Copy this shape verbatim (substituting the desk seam).

**Whole-file pattern** (`demo/__init__.py:1-12`):
```python
"""The scripted demo package (DOCS-01, D-01, D-07).

The public seam is :func:`triagedesk.demo.run.run_demo` ... The runner reuses the shipped seams
... and re-implements none of them.
"""

from triagedesk.demo.run import list_beats, load_storyboard, run_demo

__all__ = ["list_beats", "load_storyboard", "run_demo"]
```

For `desk/`, the public seam is the serve entry point (e.g. `serve`) and any pure helpers the tests
import (`form_to_case`, `render_state`, `decide`). Keep the docstring's *"reuses the shipped seams and
re-implements none of them"* claim honest — it is the DRY posture the code-review gate checks.

---

### `src/triagedesk/desk/server.py` (controller/service, request-response)

**Analog:** `src/triagedesk/demo/run.py` (the peer presentation runner — same layer, same discipline)
**Plumbing analog:** `src/triagedesk/durable.py` (the ONE pause/resume helper it reuses — do NOT re-implement)

This is the phase's core file. It is a **thin bridge** (D10-02): it validates via `CaseInput`, runs to
the gate via `durable.run_to_gate`, resumes via `durable.resume_thread`, and renders the graph's typed
outputs. It owns NO scoring, routing, gate, or write logic.

#### Imports pattern (mirror `demo/run.py:17-36`)

```python
from __future__ import annotations

import html
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from triagedesk.core.schema import CaseInput
from triagedesk.durable import PausedRun, approval_decision, resume_thread, run_to_gate
from triagedesk.evals.case import CaseSpec, TERMINAL_OUTCOMES
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder
from triagedesk.graph.build import CHECKPOINTS_DB_PATH
```

> `demo/run.py:28-36` is the precedent for importing `durable` + `evals.*` + `graph.build` from a layer
> above core. The `desk/` package reaches `triagedesk.mcp`/`triagedesk.store` **only** through the
> existing `mcp.server.resolve_store` seam (if at all) — which is exactly why `pyproject.toml` needs the
> TID251 ignore below.

#### The tool map + run-to-gate pattern (`demo/run.py:191-251`, `durable.py:111-153`)

Reuse `durable.run_to_gate` — **never** a bespoke interrupt handler or a second checkpointer lifecycle.
`demo/run.py::_run_durable` is the exact peer shape (it resolves the store seam, builds the tool map,
runs to the gate, and exits without resuming):

```python
# demo/run.py:223-235 — the peer's run-to-gate call (the bridge does the same, then renders)
resolved_store = store if store is not None else await server_module.resolve_store()
tools = build_tools(case, offline=offline, recorder=UsageRecorder())
server_module.set_store(resolved_store)
try:
    paused = await run_to_gate(
        tools, raw_note=case.note, case=case.case, db_path=resume_db,
        previous_case=case.previous_case,
    )
finally:
    server_module.set_store(None)
```

`run_to_gate`'s contract (`durable.py:111-153`) — the bridge must handle **all four** outcomes honestly:
- `paused=True, payload=<dict>` → render the card + the real gate (Committable state).
- `paused=False, payload=None, existed=False` → a terminal (`escalate`/`request_missing_info`/recovery):
  render the terminal copy; render the banner if `no_match`/`confidence.deferral` fired.
- `existed=True` → a repeat submit of the same content-addressed case (D10-19 / Pitfall 5). Handle it
  explicitly (fresh session `checkpoints.db`, or re-read the pending interrupt) — **do not** assume
  `payload is not None` when `paused` is False.

The offline tool map (RESEARCH Code Examples; `evals/tools.py:77-142`, `evals/case.py:62-96`):
```python
def _tools_for(case: CaseInput):
    spec = CaseSpec(
        id="desk", description="desk submission", note=case.complaint, case=case,
        expected=TERMINAL_OUTCOMES[0], pass_criteria="never evaluated", source="desk",
    )
    return build_tools(spec, offline=True, recorder=UsageRecorder())
```
`TERMINAL_OUTCOMES[0]` is the same declared-harness-terminal trick `durable._RESUME_PLACEHOLDER` uses
(`durable.py:47-55`) to keep a SATS colour literal out of code (CONVENTIONS §1). `expected` is never read.

#### The pause/resume plumbing — reuse, never rebuild (`durable.py`)

The bridge's decision POST calls the ONE decision builder and the ONE resume helper:

```python
# durable.py:178-218 — the ONE decision-shape builder (do NOT re-implement the blank check)
def approval_decision(decision, *, approver=None, role=None, colour=None, approved_at=None):
    ...
    if decision == "dismiss":
        return {"decision": "dismiss", "approved_at": timestamp}
    ...
    if not (approver or "").strip():
        raise DurableError(f"--approver is required for a {decision!r} decision")
    if not (role or "").strip():
        raise DurableError(f"--role is required for a {decision!r} decision")
    ...
```

```python
# durable.py:221-242 — the ONE resume entry point (builds the placeholder tool map in-process)
async def resume_thread(*, thread_id, decision, db_path):
    from triagedesk.evals.tools import build_tools
    from triagedesk.evals.usage import UsageRecorder
    tools = build_tools(_RESUME_PLACEHOLDER, offline=True, recorder=UsageRecorder())
    return await resume_paused(tools, thread_id=thread_id, decision=decision, db_path=db_path)
```

`resume_paused` refuses a thread with no pending gate (`durable.py:168-175`, `if not snapshot.next:
raise DurableError(...)`) — so the bridge surfaces that `DurableError` rather than fabricating a resume.
The bridge **must not** add a commit path: the only route to a queue row is the resumed `approval_gate`
interrupt through the gated `commit_priority` tool (D10-11/D10-12).

#### The exact payload keys to render (`graph/nodes.py:333-343` — verbatim)

```python
payload = {
    "case_id": case_id_for_note(state["raw_note"]),
    "colour": priority.colour,
    "target": priority.target,
    "triggered_rules": [rule.model_dump(mode="json") for rule in priority.triggered_rules],
    "citations": list(priority.citations),
    "missing_vitals": list(priority.missing_vitals),
    "matched_ids": list(state.get("matched_ids") or []),
    "no_match": bool(state.get("no_match")),
    "second_look": second_look.model_dump(mode="json") if second_look is not None else None,
}
```

#### The state channels the bridge must ALSO read (`graph/state.py:40-65`)

The payload lacks `evidence` and `confidence` (RESEARCH finding #2). `PausedRun.result` (the paused
`ainvoke` result, or `dict(snapshot.values)` when `existed=True`) carries them:

```python
raw_note: str
case: CaseInput | None
matched_ids: list[str]
no_match: bool
priority: PriorityResult | None
commit_result: CommitResult | None
second_look: RecheckFlag | None
confidence: ConfidenceResult | None   # ← banner trigger (UX-01)
evidence: EvidenceResult | None       # ← evidence list (UX-02)
escalation: Escalation | None         # ← terminal-kind (escalated)
recovery: RecoveryRequest | None      # ← terminal-kind (recovery)
```

**View-model mapping (presentation only):**

| UI element | Source | Notes |
|---|---|---|
| Suggested colour name + label | payload `colour` | Render the string verbatim; never map a number→colour |
| Target time | payload `target` | Substrate string, rendered verbatim |
| Why-vitals rows | payload `triggered_rules[]` → `detail` + `citation` | Baseline row is already in `triggered_rules` (`scorer.py:262-270`) |
| Evidence list | state `evidence.passages[]` → `label` + `citation`; `evidence.no_match`/`reason` | Empty ⇒ the no-evidence line |
| Not recorded | payload `missing_vitals` | |
| Second look | payload/state `second_look` | |
| Banner trigger | state `no_match` OR `confidence.deferral` | See *Shared: banner* below |
| Terminal kind | state `confidence.deferral` / `escalation` / `recovery` | Typed, not a string on `reason` |
| Committed/refused | state `commit_result` (`committed`/`refused`/`reason`) | After resume only |

#### The banner trigger — the ONE rule (typed, never a heuristic)

```python
def banner_trigger(state) -> str | None:
    if bool(state.get("no_match")):
        return "no_match"
    confidence = state.get("confidence")
    if confidence is not None and confidence.deferral:
        return "deferral"
    return None
```
Banner BODY varies with the trigger (UI-SPEC copy); treatment does not. **Never** fire on
`evidence.no_match` (a different fact) or on `missing_vitals` alone. Routing fact
(`graph/build.py:168-176` + `core/confidence.py:174-180`): `no_match ⇒ deferral ⇒ escalate`, so a
case paused at the gate always has `no_match=False` and `confidence.deferral=False` — the banner renders
on the **terminal** branch (D10-17), not alongside the gate.

#### Vitals validation — the ONE schema (`core/schema.py:24-51`)

```python
class CaseInput(BaseModel):
    age_years: int | None = Field(default=None, ge=0, le=130)
    age_months: int | None = Field(default=None, ge=0, le=1560)
    age_ambiguous: bool = False
    height_cm: float | None = Field(default=None, ge=30.0, le=260.0)
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    heart_rate: int | None = Field(default=None, ge=0, le=350)
    systolic_bp: int | None = Field(default=None, ge=0, le=400)
    diastolic_bp: int | None = Field(default=None, ge=0, le=300)
    temperature_c: float | None = Field(default=None, ge=20.0, le=45.0)
    spo2: int | None = Field(default=None, ge=0, le=100)
    mobility: Mobility | None = None
    avpu: AVPU | None = None
    trauma: bool | None = None
    complaint: str = ""  # UNTRUSTED free text (SECURITY.md T-1)
```

Form→schema rules (RESEARCH Pattern 2): empty optional fields map to `None` (not `""`/`0`); an
unanswered `trauma` checkbox is `None` (not `False`); on `ValidationError`, surface
`exc.errors()[i]["msg"]` (the schema's OWN message) beside the field — **no second validation rule**
(D10-13). The enum **values** (`walking`/`with_help`/`stretcher`, `alert`/`voice`/`pain`/`unresponsive`)
may be inlined — they are input-domain enums, excluded from the no-duplicated-SATS guard
(`test_no_duplicated_sats.py:48-49`).

#### The editable-colour set — the gate's OWN expression (D10-18)

```python
# core/schema.py:303 — the exact set the gate validates against; derive the edit radio from THIS
allowed = {band.colour for band in get_tews().tews_to_colour}   # {GREEN, YELLOW, ORANGE, RED} today
```
Never offer a colour `ApprovalToken` would refuse (no BLUE — it exists only in `target_times`).

#### Static asset serving — fixed allowlist, no traversal (RESEARCH Pattern 5)

```python
STATIC = Path(__file__).parent / "static"
_ASSETS = {"index.html": "text/html; charset=utf-8", "styles.css": "text/css; charset=utf-8"}

class DeskHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib naming)
        name = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        if name not in _ASSETS:
            self.send_error(404); return
        body = (STATIC / name).read_bytes()
        self.send_response(200); self.send_header("Content-Type", _ASSETS[name])
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

def serve(port: int = 8765) -> None:
    ThreadingHTTPServer(("127.0.0.1", port), DeskHandler).serve_forever()  # localhost only (D10-03)
```
Never `SimpleHTTPRequestHandler` (follows symlinks) and never `Path(base) / self.path`. `html.escape()`
every rendered string (complaint above all, plus name/role/citation/label) — the complaint is untrusted
(`tests/test_safety_spine.py:136`; SECURITY.md T-1). `port=0` lets the OS pick a port for the in-process
test.

---

### `src/triagedesk/desk/static/index.html` (view/asset, static file-I/O)

**Analog:** none (see *No Analog Found*). Governed by **two binding guards**:

1. **Keep SATS literals OUT of Python.** `tests/test_no_duplicated_sats.py:147-162` scans every
   `src/**/*.py` string literal for colour/target/discriminator leaves. A colour name (`RED`/`GREEN`/
   `YELLOW`/`ORANGE`) or a target time (`Immediate`, `< 10 min`) inlined in a Python template string
   **fails the guard**. Keeping markup in `.html`/`.css` (not scanned) avoids this (RESEARCH Pattern 5).
   Python may still build a class name generically: `f"colour-{colour.lower()}"` — no SATS literal.
2. **Copywriting + design contract** — `10-UI-SPEC.md` is prescriptive: the exact strings in the
   `## Copywriting Contract` table, the four type sizes / two weights, the 60/30/10 palette, the
   `--colour-*` / state tokens, ≥44px control heights, visible focus rings, `aria-live="polite"` banner,
   and the hard rule that **colour is never the only signal** (D10-08). No token from
   `HandoverCard.FORBIDDEN_FIELD_TOKENS` (`core/schema.py:349-358`) may appear in any rendered string.

---

### `src/triagedesk/desk/static/styles.css` (asset, static file-I/O)

**Analog:** none (see *No Analog Found*). The CSS is where the substrate colour string → CSS custom
property mapping lives (presentation, not re-derivation): one class per colour (`colour-red`,
`colour-orange`, `colour-yellow`, `colour-green`, `colour-blue`) mapping to the swatch hex in the
UI-SPEC. The Python emits only `colour-{name.lower()}` — the colour NAMES live here, in an asset file the
SATS guard does not scan, not in a Python dict (RESEARCH *Don't Hand-Roll*).

---

### `src/triagedesk/cli.py` (MODIFY — CLI/entry, request-response)

**Analog:** the existing `resume`/`replay` subcommands in the same file.

#### Parser pattern (`cli.py:96-138`)

Add a `desk` parser alongside `resume`/`replay`, with `--host`/`--port`/`--db` defaults (localhost / a
fixed port / `checkpoints.db`):
```python
resume_parser = subcommands.add_parser("resume", help="resume a paused durable thread through the approval gate")
resume_parser.add_argument("--thread-id", required=True, help="...")
...
replay_parser = subcommands.add_parser("replay", help="read-only reconstruction of a past case ...")
replay_parser.add_argument("--db", default=None, help="checkpoint file (default: checkpoints.db)")
```

#### The harden-first + lazy-import requirement (Phase 7 WR-06) — `cli.py:141-151`

```python
def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and dispatch; return the process exit code."""
    # Harden FIRST — before any command handler is imported (D7-03, WR-06).
    harden_offline()
    from triagedesk.demo.run import list_beats, run_demo
    from triagedesk.durable import approval_decision, resume_thread
    from triagedesk.evals.runner import run_eval
    from triagedesk.graph.build import CHECKPOINTS_DB_PATH
    from triagedesk.replay import replay_case

    args = _build_parser().parse_args(argv)
    ...
```
The `desk` handler (`from triagedesk.desk.server import serve`) **must** be imported lazily *after*
`harden_offline()` inside `main`, never at module import. `observability/offline.py:37-61` is what
`harden_offline` does (pops the six tracer env keys, clears the cached read, asserts tracing off).

#### Dispatch + clean-failure pattern (`cli.py:176-208`)

Copy the `resume` block's error discipline for the `desk` handler: catch `(ValueError, RuntimeError,
sqlite3.Error, ExceptionGroup)`, print `str(exc)` to stderr, return non-zero — a clinical CLI reports a
failure cleanly rather than a raw traceback (WR-04).

---

### `pyproject.toml` (MODIFY — config)

**Analog:** the existing per-file-ignores block, particularly the `replay.py` entry.

#### The TID251 per-file-ignore block (`pyproject.toml:57-72`)

```toml
[tool.ruff.lint.per-file-ignores]
"src/triagedesk/llm/**" = ["TID251"]
"src/triagedesk/llm/prompts.py" = ["E501"]
"src/triagedesk/mcp/**" = ["TID251"]
"src/triagedesk/graph/**" = ["TID251"]
"src/triagedesk/store/**" = ["TID251"]
"src/triagedesk/evals/**" = ["TID251"]
"src/triagedesk/demo/**" = ["TID251"]
# Read-only replay resolves the audit store through the ONE ``mcp.server`` seam and names
# the ``Store`` protocol, exactly as ``demo/`` does — a layer above core, legitimately
# depending on those modules (D7-15, D-13).
"src/triagedesk/replay.py" = ["TID251"]
"scripts/**" = ["TID251"]
"tests/**" = ["TID251"]
```

**Add** `"src/triagedesk/desk/**" = ["TID251"]` (mirroring `demo/**`/`evals/**`), with a comment
matching the `replay.py` precedent (a layer above core, legitimately resolving the store through the ONE
`mcp.server` seam). Only needed if the bridge imports `triagedesk.mcp`/`triagedesk.store`; keeping the
bridge on non-banned modules avoids the need, but RESEARCH flags the ignore as the safe path.

---

### `tests/test_desk.py` (test — request-response + in-process handler)

**Analog:** `tests/test_durable_cli.py` (CLI-surface + in-process driving) and `tests/test_demo.py`
(row-delta honesty assertions).

#### Hermetic seams to reuse — do NOT rebuild (`tests/conftest.py`)

```python
# conftest.py:89-100 — autouse store injection into the ONE server seam (no borrowed subprocess)
@pytest.fixture(autouse=True)
def injected_store(memory_store: RecordingStore) -> Iterator[RecordingStore]:
    server_module.set_store(memory_store)
    try:
        yield memory_store
    finally:
        server_module.set_store(None)

# conftest.py:103-115 — autouse span-sink redirect to tmp_path (no repo-root spans.jsonl)
@pytest.fixture(autouse=True)
def _spans_sink(tmp_path: Path) -> Iterator[None]:
    set_sink(tmp_path / "spans.jsonl")
    ...
```
Use `tmp_path` for `checkpoints.db` (`.gitignore` already ignores `*.db`) and `build_tools(...,
offline=True)` (no model). Loopback-only HTTP: bind `127.0.0.1:0`.

#### In-process handler driving pattern (RESEARCH Code Examples)

```python
def test_form_to_card(tmp_path, injected_store):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path=tmp_path / "cp.db"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        data = urllib.parse.urlencode({"complaint": "central chest pain", "age_years": "40",
                                       "respiratory_rate": "24", "heart_rate": "118",
                                       "systolic_bp": "108", "temperature_c": "38.9",
                                       "mobility": "walking", "avpu": "alert"}).encode()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/case", data=data) as resp:
            body = resp.read().decode()
        assert "Suggested priority" in body
    finally:
        server.shutdown()
```

#### The pause + row-delta proof pattern (`test_durable_cli.py:221-258`, `test_demo.py:46-57`)

```python
# test_durable_cli.py:229-235 — drive the real graph to a paused gate over tmp_path
case = next(case for case in load_cases(CASES_DIR) if case.id == "E-02")
db_path = tmp_path / "checkpoints.db"
tools = build_tools(case, offline=True, recorder=UsageRecorder())
paused = asyncio.run(run_to_gate(tools, raw_note=case.note, case=case.case, db_path=db_path))
assert paused.paused, "the E-02 case did not pause at the approval gate"
```
```python
# test_demo.py:46-57 — a refused/dismissed decision writes NO row (assert the store's rows)
store = InMemoryStore()
assert await run_demo(beats=["refusal"], store=store) == 0
assert await store.read_queue_rows() == []
```

#### Required proofs for this suite (D10-15 / RESEARCH fail-safe strategy)

| Proof | How (pattern source) |
|---|---|
| Banner trigger fires from the typed signal | Build a terminal state with `no_match=True` / `confidence.deferral=True`; assert the banner copy renders. **Do not** fabricate a `no_match=True` paused case — the graph never produces one (Pitfall 1). |
| Read-only deferred path (no gate) | A deferred case renders the banner + read-only card and **no** approve/edit/dismiss controls (D10-17). |
| The gate (approve/edit/dismiss) | POST a decision → assert `commit_result`; approve/edit writes one row, edit uses the chosen colour. |
| Timeout fail-safe | A request that never submits a decision leaves the queue row count unchanged (timeout = no resume = no commit). |
| Vitals validation | An out-of-range field surfaces `CaseInput`'s own message beside the field; nothing is scored (D10-13). |
| No commit on dismiss | POST `decision=dismiss` → `commit_result.refused is True`, `committed is False`, zero rows. |
| No self-commit (structural) | Assert the `desk/` package never imports `triagedesk.store.queue` / `mcp.server.commit_priority` directly (AST scan, mirroring `conftest.imported_modules`). |
| No borrowed subprocess | The `injected_store` seam + a `monkeypatch` spy on `triagedesk.store.borrowed.open_borrowed_store` that raises (`test_durable_cli.py:76-80`). |

---

### `docs/DESK.md` (doc)

**Analog:** `docs/DEMO.md` (structure) + `tests/test_demo_runbook.py` (the guard pattern, if you add one).

RESEARCH recommends a **new** `docs/DESK.md`: it is unconstrained by any guard, whereas editing
`README.md`/`ARCHITECTURE.md`/`DESCRIPTION.md`/`EVALS.md` trips `tests/test_docs_final.py` and editing
`docs/DEMO.md` trips `tests/test_demo_runbook.py` (beat coverage + honesty clauses). Model the doc on
`docs/DEMO.md`'s one-screen runbook shape: a short intro blockquote, a one-time-setup fenced bash block,
the literal one-command path (`uv run triagedesk desk`), and a fenced `text` block of expected on-screen
output. If you want the quickstart guarded, copy the `test_demo_runbook.py` coupling pattern (drive the
shipped CLI/`--help` through the public `main` surface and assert the doc names what a presenter runs).

---

### `docs/DECISIONS.md` (MODIFY — doc)

**Analog:** the existing ADR-lite rows in the same file (last row is `D22`, `docs/DECISIONS.md:211-227`).

Add one row (next id `D23`) in the same **context · decision · why · consequence** shape, recording the
desk-surface design decision (stdlib `http.server`, presentation-only, one pause/resume helper, banner on
the terminal per D10-17, editable colours = the gate's accepted set per D10-18). Follow the existing
format exactly (bold `**Decision:**`/`**Why:**`/`**Consequence:**` lines).

---

## Shared Patterns

### Authentication / offline hardening
**Source:** `src/triagedesk/observability/offline.py:37-61`
**Apply to:** the `desk` CLI handler (called via `cli.main`'s first statement)
```python
def harden_offline() -> None:
    for name in _TRACING_ENV_VARS:
        os.environ.pop(name, None)
    try:
        from langsmith import utils as langsmith_utils
    except ImportError:
        return
    langsmith_utils.get_env_var.cache_clear()  # type: ignore[attr-defined]
    if langsmith_utils.tracing_is_enabled():
        raise RuntimeError("cloud tracing is still enabled (D7-03): egress is not inert")
```

### The ONE pause/resume helper (no second path)
**Source:** `src/triagedesk/durable.py` (`run_to_gate` 111-153, `resume_paused` 156-175,
`approval_decision` 178-218, `resume_thread` 221-242)
**Apply to:** every gate interaction in `desk/server.py`. Never re-implement the blank-name/role check,
never open a second checkpointer lifecycle, never call `commit_priority`/the store writer directly.

### The ONE store seam (dependency inversion)
**Source:** `src/triagedesk/mcp/server.py:58-78` (`set_store`/`resolve_store`)
**Apply to:** the bridge, *if* it needs a store at all — resolve through this seam only (as
`demo/run.py:223` does), so tests inject the fake and no borrowed subprocess launches. `resolve_store`
is the published resolver; a second resolver would be a duplicate seam (SOLID: D).

### The ONE citation helper
**Source:** `src/triagedesk/core/citations.py:28-39` (`format_citation`)
**Apply to:** every rendered citation. The card takes citation strings **already on the payload**
(`triggered_rules[].citation`, `citations[]`); it never formats or inlines one (D10-06). The baseline
citation is already a `triggered_rules` row (`scorer.py:262-270`) — the bridge never reads
`baseline_citation` from the substrate directly.

### The ONE schema (validation)
**Source:** `src/triagedesk/core/schema.py:24-51` (`CaseInput`) and `:303` (`ApprovalToken` colour set)
**Apply to:** the vitals form (validate with `CaseInput.model_validate` + catch `ValidationError`) and
the edit-colour control (derive from `{band.colour for band in get_tews().tews_to_colour}`).

### Output escaping (untrusted complaint)
**Source:** RESEARCH Pattern 5 / Pitfall 6 (SECURITY.md T-1; ASVS V5)
**Apply to:** every rendered string — `html.escape()` the complaint, name, role, and every
citation/label. Keep `Content-Type: text/html; charset=utf-8`. Never place user input in a response
header (the stdlib does not scrub CRLF).

### The no-duplicated-SATS guard (DRY)
**Source:** `tests/test_no_duplicated_sats.py:147-162` (scans `src/**/*.py` string literals)
**Apply to:** the whole `desk/` package. Keep markup in `.html`/`.css`; emit `colour-{name.lower()}`
generically; render colour/target strings from the graph's values — never inline a colour name or target
time in Python. Input-domain enums (`mobility`/`avpu`) are the only inlinable values
(`test_no_duplicated_sats.py:48-49`).

---

## No Analog Found

Files with no close match in the codebase (planner should use the UI-SPEC + RESEARCH patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/triagedesk/desk/static/index.html` | view/asset | static file-I/O | No tracked `.html` exists; nearest asset precedent is `docs/assets/` (non-served `.mmd`/`.svg`/`.mp4` artefacts). Use the UI-SPEC `## Copywriting Contract` + `## Surface Components` verbatim. |
| `src/triagedesk/desk/static/styles.css` | asset | static file-I/O | No tracked `.css` exists anywhere (`git ls-files '*.css'` is empty). Use the UI-SPEC token tables (spacing/typography/colour/state). |

---

## Metadata

**Analog search scope:** `src/triagedesk/**` (durable, cli, demo, graph, core, mcp, evals, observability,
store), `tests/**` (conftest, durable-cli, demo, docs-final, demo-runbook, no-duplicated-sats, purity,
safety-spine), `pyproject.toml`, `docs/**`.
**Files scanned:** 20+ (read directly this session; the RESEARCH's line-by-line in-repo citations were
re-verified for the payload, state, schema, and durable excerpts).
**Pattern extraction date:** 2026-10-13
**Git-tracked gate:** all named analog paths verified tracked (`git ls-files` non-empty); no gitignored
mirror path is used.

---

## PATTERN MAPPING COMPLETE
