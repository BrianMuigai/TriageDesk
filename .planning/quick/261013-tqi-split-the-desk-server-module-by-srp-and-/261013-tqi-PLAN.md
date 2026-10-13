---
phase: quick
plan: "261013-tqi"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/triagedesk/desk/server.py
  - src/triagedesk/desk/copy.py
  - src/triagedesk/desk/markup.py
  - src/triagedesk/desk/assets.py
  - src/triagedesk/desk/pipeline.py
  - src/triagedesk/desk/forms.py
  - src/triagedesk/desk/card.py
  - src/triagedesk/desk/gate.py
  - src/triagedesk/desk/views.py
  - README.md
autonomous: true
requirements: [QUICK-261013]
estimate:
  tokens: 64000
  raw_tokens: 42000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`src/triagedesk/desk/server.py` stays the HTTP layer AND the facade: every name the suite reaches or patches remains an attribute of `triagedesk.desk.server` — `render_state`, `banner_trigger`, `terminal_kind`, `editable_colours`, `_loopback_host`, `DeskServer`, `DeskHandler`, `form_to_case`, `make_server`, `serve`, `submit_case`, `decide`, `STATIC_DIR`, `_ASSETS` — so `desk_server.render_state(...)`, `desk_server._loopback_host(...)`, `desk_server.banner_trigger(...)`, `desk_server.terminal_kind(...)` and `monkeypatch.setattr('triagedesk.desk.server.serve'|'...decide', …)` all keep working with ZERO test edits."
    - "`DeskHandler._handle_decision`/`_handle_case` stay in `server.py` and call `decide`/`submit_case` as bare names; because a function's bare-name lookup resolves through its defining module's globals (the `server` module object the patch mutates), the `monkeypatch.setattr('triagedesk.desk.server.decide', boom)` patch at `tests/test_desk.py:1161` is observed at the call site."
    - "Zero behaviour change: no rendered string, route, header, guard, copy value, form control, colour set or view branch changes; the FULL `tests/test_desk.py` plus the runbook guards pass with no test edits."
    - "`_escaped` and `STATIC_DIR`/`_ASSETS` each have exactly ONE home and are imported, never restated: no module recomputes `Path(__file__).parent / 'static'` and no module re-implements HTML escaping (CONVENTIONS §1)."
    - "The desk package still imports neither `triagedesk.store.queue` nor `triagedesk.mcp.server` (the recursive `test_no_self_commit_path_in_the_desk_package` guard stays green), no new module adds a direct `triagedesk.evals.case` import, and no SATS colour/threshold literal enters `src/**/*.py`."
    - "The README gains a `## Running the demos` section whose every fenced `uv run triagedesk …` invocation is accepted by the shipped CLI AND reaches the demo/desk seam, with `uv run triagedesk demo` and `uv run triagedesk desk` both still present."
  artifacts:
    - path: src/triagedesk/desk/copy.py
      provides: "The ONE home for every user-facing string (`_BANNER_*`, `_EMPTY_*`, `_CARD_FRAMING`, `_READ_ONLY_FRAMING`, `_NO_EVIDENCE_LINE`, `_DEFERRED_COPY`, `_ESCALATED_COPY`, `_RECOVERY_COPY`, `_UNREACHED_COPY`, `_DISMISSED_COPY`, `_TIMEOUT_COPY`, `_FAILURE_COPY`, `_SCHEMA_HINT`, `_NO_THREAD_COPY`); imports nothing."
    - path: src/triagedesk/desk/markup.py
      provides: "The ONE escaping rule `_escaped(value) -> str` (ASVS V5); imports stdlib `html`."
    - path: src/triagedesk/desk/assets.py
      provides: "The ONE static-asset path `STATIC_DIR` and the fixed allowlist `_ASSETS`; imports `pathlib.Path`."
    - path: src/triagedesk/desk/pipeline.py
      provides: "The desk's thin graph-runner seam: `_tools_for`, `submit_case`, `decide` (unmoved bodies)."
    - path: src/triagedesk/desk/forms.py
      provides: "`form_to_case` + the schema-derived control helpers (`_base_annotation`, `_annotation_kind`, `_enum_values`, `_bounds`, `_fmt_bound`, `_option_label`, `_vitals_field`, `_vitals_fields`) + `_TRUTHY`, `_VITALS_LAYOUT`, `_CSRF_FIELD`, `_csrf_field`."
    - path: src/triagedesk/desk/card.py
      provides: "`_colour_class`, `_why_vitals_rows`, `_evidence_rows`, `_card_html`, `_card_payload_from_state`."
    - path: src/triagedesk/desk/gate.py
      provides: "`editable_colours`, `_gate_html`."
    - path: src/triagedesk/desk/views.py
      provides: "`banner_trigger`, `terminal_kind`, `_panel`, `_banner_html`, `_terminal_panel`, `_empty_view`, `_paused_view`, `_decision_view`, `_error_panel`, `_render`, `render_state`."
    - path: src/triagedesk/desk/server.py
      provides: "The HTTP layer (`DeskServer`, `DeskHandler`, `make_server`, `serve`, `_loopback_host`, `_refuse_non_loopback`, `_validation_field`, `_validation_message`, `_MAX_BODY_BYTES`, `_LOOPBACK_HOSTNAMES`) plus the facade re-exports of every moved public name."
    - path: README.md
      provides: "A `## Running the demos` section (storyboard demo + desk surface) that links to `docs/DEMO.md`/`docs/DESK.md` rather than restating them."
  key_links:
    - "`server.py` -> `views.render_state`; `views.py` -> `assets.STATIC_DIR` + `forms._vitals_fields`/`_csrf_field` + `card._card_html`/`_card_payload_from_state` + `gate._gate_html` + `markup._escaped` + `copy`; `forms`/`card`/`gate` -> `markup._escaped`. The render graph is acyclic: nothing imports `server`, so `STATIC_DIR`/`_ASSETS` can be a leaf without a cycle."
    - "`server.py` imports and re-exports `render_state`, `banner_trigger`, `terminal_kind`, `editable_colours`, `form_to_case`, `submit_case`, `decide`, `STATIC_DIR`, `_ASSETS` — the facade that `desk/__init__.py`, `cli.py` and the suite reach."
    - "`server.DeskHandler._handle_decision` -> bare `decide` (a `server` global imported from `pipeline`), so the monkeypatch seam at `tests/test_desk.py:1161` still intercepts the call."
    - "`markup._escaped` and `assets.STATIC_DIR`/`_ASSETS` are imported by BOTH the new render modules and `server.py`; neither rule is restated anywhere (CONVENTIONS §1)."
---

<objective>
Split the 1169-line `src/triagedesk/desk/server.py` into single-responsibility modules and document how to drive the two demos in the README.

`server.py` currently carries five unrelated responsibilities in one file: UI copy, the vitals form + schema-derived controls, the card renderers, the gate renderer, the view assembly, the graph-runner seam, AND the HTTP server. The split moves each responsibility to its own module, leaving `server.py` as the HTTP layer and the public facade (the seam every test and the CLI reach). It is a **PURE MOVE**: zero behaviour change, zero test churn.

Purpose: DRY + SOLID are iron-clad (`docs/CONVENTIONS.md`); a god-module that renders the UI, drives the graph and serves HTTP violates SRP (`S`), and the module is already too large to read in one pass. Splitting it also gives each user-facing string one home (`copy.py`) and each rendering primitive one home.

Output:
- The 8 new `desk/` modules (`copy`, `markup`, `assets`, `pipeline`, `forms`, `card`, `gate`, `views`) and a rewritten `server.py` that imports + re-exports them.
- A `## Running the demos` README section (storyboard demo + desk surface), linking to the runbooks.

### The module map (6 agreed modules + 2 justified leaf modules)

The agreed map named 6 new modules. Two tiny leaf modules are added because the map omitted the home for the shared `_escaped` rule and left `STATIC_DIR`/`_ASSETS` in `server.py` — which the render modules also need, and importing them from `server.py` would create a module import CYCLE (`server.py` imports `views` for the facade). Marking these two primitives explicit is the better SRP boundary and the only way to have ONE home per rule with no cycle and no restatement:

| New module | Moves OUT of `server.py` |
|---|---|
| `copy.py` | every user-facing string constant |
| `markup.py` | `_escaped` — the ONE escaping rule |
| `assets.py` | `STATIC_DIR`, `_ASSETS` — the ONE static-asset path |
| `forms.py` | `form_to_case` + schema-derived controls + `_TRUTHY`, `_VITALS_LAYOUT`, `_CSRF_FIELD`, `_csrf_field` |
| `card.py` | `_colour_class`, `_why_vitals_rows`, `_evidence_rows`, `_card_html`, `_card_payload_from_state` |
| `gate.py` | `editable_colours`, `_gate_html` |
| `views.py` | `banner_trigger`, `terminal_kind`, `_panel`, `_banner_html`, `_terminal_panel`, `_empty_view`, `_paused_view`, `_decision_view`, `_error_panel`, `_render`, `render_state` |
| `pipeline.py` | `_tools_for`, `submit_case`, `decide` |
| `server.py` | the HTTP layer + the facade re-exports |

### The monkeypatch seam (why the handler stays put)

`tests/test_desk.py:1161` does `monkeypatch.setattr("triagedesk.desk.server.decide", boom)` and expects `_handle_decision`'s CALL SITE to observe it. `_handle_decision` is HTTP-layer code and stays in `server.py`; it calls the bare name `decide`, which `server.py` imports from `pipeline.py`. A function's bare-name lookup resolves through its **defining module's** globals — the `server` module object the patch mutates — so the patch is observed. The same holds for `monkeypatch.setattr("triagedesk.desk.server.serve", fake)`: `serve` stays a module-level attribute of `server.py`. This is the simplest honest arrangement (no lazy `from … import module` indirection, no `server.decide(...)` re-lookup), and it is the reason the handler is NOT moved to a new module.

### DRY constraints honoured
- `_escaped` → ONE home (`markup.py`); `STATIC_DIR`/`_ASSETS` → ONE home (`assets.py`). Both imported, never restated.
- No new module imports `triagedesk.store.queue`, `triagedesk.mcp.server`, or `triagedesk.evals.case`; the desk keeps reaching `mcp.server` only transitively via `evals.tools`.
- No SATS colour/threshold literal enters any new module (colour names live only in `desk/static/styles.css`).
- No new dependency; `pyproject.toml`/`uv.lock` untouched.

### Out of scope (do NOT touch)
Merging the `desk/`/`demo/` folders; `demo/run.py`'s private imports; the queue-effect copy overlap; re-recording `docs/assets/desk-demo.mp4`.
</objective>

<execution_context>
@/home/brian/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/brian/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md
@docs/CONVENTIONS.md
@src/triagedesk/desk/server.py
@src/triagedesk/desk/__init__.py
@src/triagedesk/desk/static/index.html
@src/triagedesk/cli.py
@tests/test_desk.py
@tests/test_desk_runbook.py
@tests/test_readme_runbook.py
@tests/test_review_runbook.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extract the shared leaves and the graph runner (copy.py, markup.py, assets.py, pipeline.py)</name>
  <files>src/triagedesk/desk/copy.py, src/triagedesk/desk/markup.py, src/triagedesk/desk/assets.py, src/triagedesk/desk/pipeline.py, src/triagedesk/desk/server.py</files>
  <action>Pure MOVE: cut four leaf/runner modules out of `server.py` and have `server.py` import them. Change no value, no string, no branch. Every moved function keeps its docstring verbatim; each new module gets a one-line module docstring naming its single responsibility.

Create `src/triagedesk/desk/copy.py` — move verbatim the UI copy constants from `server.py` lines 113-141: `_BANNER_HEADLINE`, `_BANNER_NO_MATCH_BODY`, `_BANNER_LOW_CONFIDENCE_BODY`, `_EMPTY_HEADING`, `_EMPTY_BODY`, `_CARD_FRAMING`, `_READ_ONLY_FRAMING`, `_NO_EVIDENCE_LINE`, `_DEFERRED_COPY`, `_ESCALATED_COPY`, `_RECOVERY_COPY`, `_UNREACHED_COPY`, `_DISMISSED_COPY`, `_TIMEOUT_COPY`, `_FAILURE_COPY`, `_SCHEMA_HINT`, `_NO_THREAD_COPY` — with their leading comments. No imports. Docstring: "The desk surface's ONE home for every user-facing string (UX copy). Imported by the render modules and the HTTP layer; restated nowhere."

Create `src/triagedesk/desk/markup.py` — move `_escaped` (lines 292-294) verbatim, plus `import html`. Docstring: "The ONE HTML-escaping rule for the desk surface (ASVS V5)." Do NOT add `_colour_class` here (it stays with the card renderer until Task 2).

Create `src/triagedesk/desk/assets.py` — move `STATIC_DIR` (line 63, with its comment) and `_ASSETS` (lines 67-70, with its comment) verbatim, plus `from pathlib import Path`. Docstring: "The ONE static-asset path and the fixed two-name allowlist for the desk surface." These are the single source: every other module imports them and computes no path and no allowlist of its own.

Create `src/triagedesk/desk/pipeline.py` — move `_tools_for`, `submit_case`, `decide` (lines 191-234) verbatim with their docstrings. Imports: `from collections.abc import Mapping`; `from pathlib import Path`; `from typing import Any`; `from triagedesk.core.schema import CaseInput`; `from triagedesk.durable import PausedRun, approval_decision, resume_thread, run_to_gate`; `from triagedesk.evals.tools import offline_tools`; `from triagedesk.evals.usage import UsageRecorder`. Docstring: "The desk's thin graph-runner seam: build the offline tool map, run a case to the approval gate, and resume it with a named decision (D10-11). Reuses the shipped plumbing and re-implements none of it."

Modify `src/triagedesk/desk/server.py`:
- Delete the four moved constants/functions. Add imports: `from triagedesk.desk.assets import STATIC_DIR, _ASSETS`; `from triagedesk.desk.markup import _escaped`; `from triagedesk.desk.pipeline import decide, submit_case`; and `from triagedesk.desk.copy import _BANNER_HEADLINE, _BANNER_NO_MATCH_BODY, _BANNER_LOW_CONFIDENCE_BODY, _EMPTY_HEADING, _EMPTY_BODY, _CARD_FRAMING, _READ_ONLY_FRAMING, _NO_EVIDENCE_LINE, _DEFERRED_COPY, _ESCALATED_COPY, _RECOVERY_COPY, _UNREACHED_COPY, _DISMISSED_COPY, _TIMEOUT_COPY, _FAILURE_COPY, _SCHEMA_HINT, _NO_THREAD_COPY` (every name the still-resident render code references). Remove ONLY the imports that became genuinely unused — `import html` was used solely by `_escaped`, so drop it; keep `secrets` (still used by `DeskServer`/`_csrf_ok`) and every import still referenced by the resident code, verifying by usage so `ruff check` (F401) is clean.
- The render code that remains in `server.py` (the forms/card/gate/views helpers, still resident until Task 2) now resolves `_escaped`, the copy constants and `STATIC_DIR` from the new leaf modules — no source edits to those functions.
- Leave the module-level docstring intact except for one added sentence noting `server.py` is the HTTP layer + facade over the split modules.
- Keep `__all__` unchanged (it already lists `DeskHandler`, `DeskServer`, `STATIC_DIR`, `banner_trigger`, `decide`, `editable_colours`, `form_to_case`, `make_server`, `render_state`, `serve`, `submit_case`, `terminal_kind`).

Do NOT touch `tests/` and do NOT change any string, route, header or guard. This is verifiable by the suite passing unedited.</action>
  <verify>
    <automated>uv run pytest tests/test_desk.py tests/test_desk_runbook.py tests/test_readme_runbook.py tests/test_review_runbook.py -q && uv run ruff check src/triagedesk/desk</automated>
  </verify>
  <done>`copy.py`, `markup.py`, `assets.py`, `pipeline.py` exist and own the copy strings, `_escaped`, `STATIC_DIR`/`_ASSETS` and the runner respectively; `server.py` imports them; the full desk suite and the three runbook guards are green; ruff is clean; no behaviour changed.</done>
</task>

<task type="auto">
  <name>Task 2: Extract the render modules and finish server.py as the HTTP layer + facade</name>
  <files>src/triagedesk/desk/forms.py, src/triagedesk/desk/card.py, src/triagedesk/desk/gate.py, src/triagedesk/desk/views.py, src/triagedesk/desk/server.py</files>
  <action>Pure MOVE: cut the four render modules out of `server.py`; `server.py` becomes the HTTP layer + the facade. No value, string, branch or docstring wording changes; each moved function keeps its docstring verbatim.

Create `src/triagedesk/desk/forms.py` — move, in dependency order, `_base_annotation`, `_annotation_kind`, `_enum_values`, `_bounds`, `_fmt_bound`, `_option_label`, `_vitals_field`, `_vitals_fields`, `form_to_case`, plus the constants `_TRUTHY`, `_VITALS_LAYOUT`, `_CSRF_FIELD` and the helper `_csrf_field` (move `_CSRF_FIELD`+`_csrf_field` here because the gate and the vitals form both render it — it is a form control, and `forms` is the lowest render module, so both `gate` and `views` can import it without a cycle). Imports: `from collections.abc import Mapping`; `from typing import Any, get_args`; `from triagedesk.core.schema import CaseInput`; `from triagedesk.desk.markup import _escaped`. Do NOT import `ValidationError` here: no moved function references it (`form_to_case` raises it only via `CaseInput.model_validate`; the `except ValidationError` handler stays in `server.py`) — let `ruff check` (F401) confirm. Docstring: "The desk vitals form: build a `CaseInput` from the posted form and render the form controls from the ONE schema (D10-13)."

Create `src/triagedesk/desk/card.py` — move `_colour_class`, `_why_vitals_rows`, `_evidence_rows`, `_card_html`, `_card_payload_from_state`. Imports: `from collections.abc import Mapping`; `from typing import Any`; `from triagedesk.desk.markup import _escaped`; `from triagedesk.desk.copy import _NO_EVIDENCE_LINE, _CARD_FRAMING, _READ_ONLY_FRAMING`. Docstring: "The desk priority card: render the graph's own typed outputs as a suggestion with its citations and evidence (D10-05…D10-08)."

Create `src/triagedesk/desk/gate.py` — move `editable_colours`, `_gate_html`. Imports: `from triagedesk.core.rules import get_tews`; `from triagedesk.desk.markup import _escaped`; `from triagedesk.desk.forms import _csrf_field`; `from triagedesk.desk.copy import _TIMEOUT_COPY`. Docstring: "The desk approval gate: render the named-human decision form and the edit colour set the gate validates against (D10-18)."

Create `src/triagedesk/desk/views.py` — move `banner_trigger`, `terminal_kind`, `_panel`, `_banner_html` (note: currently named `_banner_html` and defined right after `_panel`), `_terminal_panel`, `_empty_view`, `_paused_view`, `_decision_view`, `_error_panel`, `_render`, `render_state`. Imports: `from collections.abc import Mapping`; `import string`; `from typing import Any`; `from triagedesk.durable import PausedRun`; `from triagedesk.desk.assets import STATIC_DIR`; `from triagedesk.desk.markup import _escaped`; `from triagedesk.desk.forms import _csrf_field, _vitals_fields`; `from triagedesk.desk.card import _card_html, _card_payload_from_state`; `from triagedesk.desk.gate import _gate_html`; and `from triagedesk.desk.copy import _BANNER_HEADLINE, _BANNER_NO_MATCH_BODY, _BANNER_LOW_CONFIDENCE_BODY, _EMPTY_HEADING, _EMPTY_BODY, _DEFERRED_COPY, _ESCALATED_COPY, _RECOVERY_COPY, _UNREACHED_COPY, _DISMISSED_COPY, _FAILURE_COPY` (import exactly the copy names `views.py` references — `_NO_EVIDENCE_LINE` is used only by `card.py`, so leave it there; let ruff's F401 confirm the set). Docstring: "The desk view assembly: choose the view for one state and substitute it into the ONE hand-authored template."

Modify `src/triagedesk/desk/server.py`:
- Delete every function/constant now moved (the render helpers) and the `_VITALS_LAYOUT`/`_TRUTHY`/`_CSRF_FIELD` constants.
- Add the facade imports: `from triagedesk.desk.assets import STATIC_DIR, _ASSETS`; `from triagedesk.desk.forms import _CSRF_FIELD, form_to_case`; `from triagedesk.desk.gate import editable_colours`; `from triagedesk.desk.pipeline import decide, submit_case`; `from triagedesk.desk.views import banner_trigger, render_state, terminal_kind`; `from triagedesk.desk.copy import _FAILURE_COPY, _NO_THREAD_COPY, _SCHEMA_HINT` (names still referenced by `_handle_case`, `_handle_decision`, `do_POST`, `_validation_message`).
- Keep `DeskServer`, `DeskHandler` (with `do_GET`, `do_POST`, `_page`, `_host_ok`, `_cross_origin`, `_csrf_ok`, `_handle_case`, `_handle_decision`), `_loopback_host`, `_refuse_non_loopback`, `_validation_field`, `_validation_message`, `make_server`, `serve`, `_MAX_BODY_BYTES`, `_LOOPBACK_HOSTNAMES` in `server.py`.
- CRITICAL: `_handle_decision` and `_handle_case` keep calling the bare names `decide` and `submit_case` (imported from `pipeline`); `_page` keeps calling `render_state` (imported from `views`). Do NOT rewrite these to `pipeline.decide(...)` / `views.render_state(...)` — the bare-name form is what makes the `triagedesk.desk.server.decide` monkeypatch seam hold.
- Trim `server.py`'s module docstring to describe the HTTP layer + facade, and note the split (the moved modules carry the UX behaviour).
- Keep `__all__` exactly as it is.
- Remove now-unused imports so `ruff check` (F401) and `uv run mypy` stay clean; do NOT leave an import that no line uses, and do NOT add `_escaped` to `server.py` (it is not referenced there after the split).

Do NOT touch `tests/`.</action>
  <verify>
    <automated>uv run pytest tests/test_desk.py tests/test_desk_runbook.py tests/test_readme_runbook.py tests/test_review_runbook.py -q && uv run ruff check src/triagedesk/desk && uv run python -c "from triagedesk.desk import decide, form_to_case, make_server, render_state, serve, submit_case; import triagedesk.desk.server as s; [getattr(s, n) for n in ('render_state','banner_trigger','terminal_kind','editable_colours','_loopback_host','DeskServer','DeskHandler','serve','decide','form_to_case','STATIC_DIR','_ASSETS')]"</automated>
  </verify>
  <done>`forms.py`, `card.py`, `gate.py`, `views.py` exist and own their responsibilities; `server.py` is the HTTP layer + facade; every patched/reached name is still an attribute of `triagedesk.desk.server`; the full desk suite and the runbook guards are green with no test edits; ruff is clean.</done>
</task>

<task type="auto">
  <name>Task 3: Document how to run the demos in the README</name>
  <files>README.md</files>
  <action>Add a concise `## Running the demos` section AFTER `## Quickstart` and BEFORE `## Repository map`; fold the Quickstart's now-duplicated drive prose into it so the drive mechanics have ONE home (DRY). The section links to the runbooks (`docs/DEMO.md`, `docs/DESK.md`) and does NOT restate them.

HARD CONSTRAINT — the README guard (`tests/test_readme_runbook.py`) extracts every fenced block, finds every ``uv run triagedesk <args>`` inside a fence, strips a trailing `# comment`, `shlex.split`s it, then asserts (a) `main(argv) == 0` and (b) that the invocation reached the demo OR desk seam. Consequences you MUST honour:
- A fence may contain ONLY these invocations (each parses and reaches `run_demo`/`serve`): `uv run triagedesk demo`, `uv run triagedesk demo --online`, `uv run triagedesk demo --beat <name>`, `uv run triagedesk demo --durable`, `uv run triagedesk desk`.
- `uv run triagedesk demo --list` returns via `list_beats()` (NOT `run_demo`) and `uv run triagedesk resume …` reaches NEITHER seam — these would FAIL the guard. Mention them ONLY as INLINE single-backticked code (outside any fence), exactly as the current README already does with `--beat <name>` on line 102.
- Do NOT invent a flag; verify every flag against `src/triagedesk/cli.py` (`demo`: `--online`/`--beat`/`--list`/`--fixture`/`--durable`/`--db`; `desk`: `--host`/`--port`/`--db`; `resume`: `--thread-id`/`--decision`/`--approver`/`--role`/`--colour`/`--db`).

Write the section with this content (keep it tight):
- An opening line: the two Quickstart commands are the whole surface; the full presenter scripts are [`docs/DEMO.md`](docs/DEMO.md) (storyboard) and [`docs/DESK.md`](docs/DESK.md) (desk), linked not restated.
- **The storyboard demo** — a `bash` fence containing, in order with short `#` comments: `uv run triagedesk demo` (offline default); `uv run triagedesk demo --online` (after `ollama pull qwen2.5:1.5b`); `uv run triagedesk demo --beat <name>` (repeatable, to compose a shorter run); `uv run triagedesk demo --durable` (one beat to the durable gate). Then PROSE (inline code only): list the beats with `uv run triagedesk demo --list`; `--durable` pauses ONE beat at the gate, prints its content-derived thread id, and exits WITHOUT resuming, and its printed follow-up is `uv run triagedesk resume --thread-id <id> --decision approve --approver <name> --role <role>` (add `--db <file>` only if the checkpoint was moved).
- **The desk surface** — a `bash` fence containing `uv run triagedesk desk` (loopback only, no external request). Then PROSE: open **http://127.0.0.1:8765** in a browser and stop with **Ctrl-C**; the surface binds loopback only and makes no external request; the recorded walkthrough is [`docs/assets/desk-demo.mp4`](docs/assets/desk-demo.mp4); the nurse-facing quickstart is [`docs/DESK.md`](docs/DESK.md).

In `## Quickstart`: keep the existing intro and the two-command fence (`uv run triagedesk demo` / `uv run triagedesk desk`) EXACTLY (both substrings must remain for `test_readme_documents_the_bare_one_command_path` / `test_readme_documents_the_optional_second_command`). Replace the trailing drive prose (the `--online`/`--beat <name>`/`docs/DEMO.md` sentence, currently around lines 99-105) with a one-line pointer to `## Running the demos`, and keep the pre-existing `pip`/`requirements.txt` sentence. Do not otherwise edit the README.</action>
  <verify>
    <automated>uv run pytest tests/test_readme_runbook.py tests/test_desk_runbook.py tests/test_review_runbook.py -q</automated>
  </verify>
  <done>The README has a `## Running the demos` section covering the storyboard demo (offline default, `--online`, `--beat`, `--durable` + the exact `resume` follow-up) and the desk surface (command, URL, Ctrl-C, loopback-only, the recorded walkthrough, runbook links); every fenced `uv run triagedesk …` invocation is accepted by the shipped CLI and reaches its seam; `uv run triagedesk demo` and `uv run triagedesk desk` remain present; all three runbook guards are green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP request -> `DeskHandler` | Unchanged: the split moves rendering out of `server.py`, but the loopback/Host/Origin/CSRF/Content-Length defences and the escaping of every rendered value stay exactly as they are. |
| desk package -> its import graph | The recursive guard (`test_no_self_commit_path_in_the_desk_package`) bounds every `desk/*.py`: no new module may import `triagedesk.store.queue` or `triagedesk.mcp.server`. |

## STRIDE Threat Register

| Threat ID | Threat Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|-----------------|-----------|----------|-------------|-----------------|
| T-quick-01 | Tampering / Information disclosure | `server.py` + new render modules | low | mitigate | A pure move: no rendered string, route, header or escape call changes; `_escaped` remains the ONE escaping rule (`markup.py`), so the ASVS V5 output-encoding property is preserved. The FULL `tests/test_desk.py` (incl. the escaping and CSRF proofs) must pass unedited. |
| T-quick-02 | Elevation of Privilege | desk import graph | low | mitigate | No new module imports `triagedesk.store.queue` or `triagedesk.mcp.server` (the recursive guard runs over the whole package and must stay green); the surface still cannot reach the commit path directly. |
| T-quick-03 | Tampering | `desk/static` resolution | low | mitigate | `STATIC_DIR`/`_ASSETS` move to ONE leaf (`assets.py`) and are imported, never restated; the fixed allowlist is unchanged, so no path is built from `self.path`. |
| T-quick-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency is added or changed: `pyproject.toml` and `uv.lock` are untouched, so the package-legitimacy gate has nothing new to admit. |
</threat_model>

<verification>
The touched surface is the desk package plus the README. Importers of the desk package (grep-verified): `src/triagedesk/cli.py`, `src/triagedesk/desk/__init__.py`, `tests/test_desk.py`, `tests/test_desk_runbook.py`, `tests/test_readme_runbook.py`, `tests/test_review_runbook.py` — the four test modules below cover all of them (the three runbook suites drive `cli.main`).

Behaviour-preservation (the full `tests/test_desk.py` plus every desk/runbook guard — the two runbook suites that drive `triagedesk.desk.server.serve`) and the facade import smoke:

```
uv run pytest tests/test_desk.py tests/test_desk_runbook.py tests/test_readme_runbook.py tests/test_review_runbook.py -q
uv run python -c "from triagedesk.desk import decide, form_to_case, make_server, render_state, serve, submit_case"
```

Structural + DRY checks (each must print nothing, or the split is wrong):

```
# STATIC_DIR / _ASSETS have ONE home (no second Path(__file__).parent / 'static' and no second allowlist):
grep -rn "__file__).parent" src/triagedesk/desk
# _escaped has ONE home (no second `def _escaped`):
grep -rn "def _escaped" src/triagedesk/desk
# the desk imports neither forbidden commit module (guard also enforces this):
grep -rn "store.queue\|mcp.server" src/triagedesk/desk
```

The first grep must match `src/triagedesk/desk/assets.py` only; the second must match `src/triagedesk/desk/markup.py` only; the third must print nothing.

Lint/type sanity on the split (strict mypy + ruff are configured):

```
uv run ruff check src/triagedesk/desk
```

Verify the monkeypatch seam explicitly (this is the one place a naive split breaks):

```
uv run pytest "tests/test_desk.py::test_a_failure_is_never_an_approve" "tests/test_desk.py::test_desk_entry_point_hardens_offline_before_serve" -q
```
</verification>

<success_criteria>
- `server.py` is the HTTP layer + the facade; the 8 new modules each own one responsibility; `copy.py` is the ONE home for every user-facing string.
- Every name the suite reaches or patches is still an attribute of `triagedesk.desk.server`; the `decide`/`serve` monkeypatch seams hold (proven by `test_a_failure_is_never_an_approve` and `test_desk_entry_point_hardens_offline_before_serve`).
- Zero behaviour change: the FULL `tests/test_desk.py` and the three runbook guards pass with no `tests/` edits; `desk/__init__.py` and `cli.py` are untouched.
- DRY: `_escaped` has ONE home, `STATIC_DIR`/`_ASSETS` have ONE home; no duplicate helper across the new modules; no forbidden import (`store.queue`, `mcp.server`) and no SATS literal enters the package.
- No new dependency; `pyproject.toml`/`uv.lock` untouched.
- The README documents how to run both demos in a `## Running the demos` section; every fenced invocation is CLI-accepted and reaches its seam; the two required command substrings remain.
</success_criteria>

<output>
Create `.planning/quick/261013-tqi-split-the-desk-server-module-by-srp-and-/261013-tqi-SUMMARY.md` when done
</output>
