# Phase 12: Live Review, Demo & Milestone-Close Documentation - Research

**Researched:** 2026-10-13
**Domain:** Live-review rehearsal harness · demo runbook refresh · honest-fit re-declaration · submission-doc refresh (no source-behaviour change)
**Confidence:** HIGH (the phase is almost entirely in-repo: every claim below was read from a file or produced by running the shipped CLI this session)

> **Frontend gate note (binding):** the ROADMAP UI gate flagged this phase `frontend: true` by matching the
> word "screen" in the goal. This is a **FALSE POSITIVE** — a docs/rehearsal phase with **no UI work**.
> Plan with `--skip-ui`; do **not** create UI tasks. `[VERIFIED: .planning/config.json:28 — "ui_phase": true]`
> (the flag exists but this phase produces no UI).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**The live review rehearsal (REV-01)**
- **D12-01:** A **rehearsal runbook** (`docs/REVIEW.md`) scripts the 10-minute walkthrough as literal, ordered beats with the exact commands and the expected output, so the review can be driven from the page.
- **D12-02:** The "live extension" is **data-only**: adding a discriminator to `data/sats_discriminators.yaml`, reloading, and re-scoring must pass the safety suite with **no code edit**. A **dry-run harness/test** proves it (a temporary data addition → a re-score → the suite green → the addition reverted), so the claim is demonstrated, not asserted.
- **D12-03:** Every command in the runbook is **guarded by a drift test** (the established runbook pattern) that drives the shipped CLI, so the documented invocation cannot drift.

**The demo (DEMO-02)**
- **D12-04:** A **2–3 minute narrated demo script** (`docs/DEMO.md`, refreshed) with the narration beats, the on-screen commands, and the point at which the **measured eval run shows a failure, unedited and un-tuned**.
- **D12-05:** **The recording and the public upload are HUMAN actions.** The phase prepares the script, the narration, and a runnable dry-run, and **flags the recording/upload as `human_needed`** — it never claims a video exists or is hosted.

**Clinical fit (FIT-01)**
- **D12-06:** **The gap is re-declared honestly** in `README.md`/`EVALS.md`: no triage nurse/clinician review was obtained, so the fit-to-desk claim is scoped to what was actually built and measured. If a review is obtained later, a clearly marked slot exists for the quote — but nothing is invented.
- **D12-07:** **No over-claim anywhere**: the review status, the demo status, the clinician status and every measured number are stated as they are (including the residual eval misses).

**The submission-document refresh (DOCS-06)**
- **D12-08:** **Every submission document is refreshed to the v1.1 state** — `README.md`, `ARCHITECTURE.md`, `EVALS.md`, `DESCRIPTION.md`, `STATUS.md`, `docs/REQUIREMENTS.md`, `docs/ROADMAP.md` — with **no stale v1.0 claim** (no "5 tools", no "two commands", no pre-v1.1 counts, no resolved-gap claimed as open or vice versa).
- **D12-09:** `EVALS.md` remains **only** the `scripts/emit_evals.py` projection of `report.json`; the other docs **link** to it rather than restating its numbers (the one-source rule).
- **D12-10:** The **`docs/DEMO.md` output-block drift deferred from Phase 11 is closed here** — the demo is re-run and the recorded blocks re-transcribed faithfully (or the blocks are clearly marked as illustrative with the live command shown), so the doc no longer contradicts the shipped CLI.
- **D12-11:** Every existing doc guard stays green (`tests/test_docs_final.py`'s one-page ARCHITECTURE guard, the one-command README guard, the projection guard, the declared-failure guard).

### the agent's Discretion
- The runbook's beat ordering and the demo's narration wording.
- Whether `docs/REVIEW.md` is a new file or a section of `docs/DEMO.md` (a new file is preferred for clarity).
- How the data-only dry-run is harnessed (a test with a tmp data dir, or a script that reverts).
- The exact honest wording of the clinical-fit gap.

### Deferred Ideas (OUT OF SCOPE)
- Multimodal intake, a clarifying-question loop, multilingual UI (UX-05/DISC-01/LANG-01) — future requirements.
- Larger-sample calibration (CAL-02) and online eval (AGENT-06).
- Model routing/latency work (AGENT-05).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REV-01 | Live technical review rehearsed end-to-end: a 10-minute walkthrough plus a dry-run "add a discriminator to `data/sats_discriminators.yaml` live, reload, and re-score" that passes the safety suite. | §The data-only live extension (exact mechanism + exact commands + dry-run harness design) and §The runbook-guard pattern. |
| DEMO-02 | The demo runs to 2–3 minutes with narration and the measured eval run on screen, still unedited and still showing a failure. | §The current demo (measured content + exact commands) + §Showing the measured eval honestly (the silent-eval finding). |
| FIT-01 | A single triage nurse/clinician review is obtained and quoted in README/EVALS if access can be arranged; if not, the gap is re-declared honestly rather than over-claimed. | §The clinical-fit re-declaration (exact wording + marked slot + current over-claim audit). |
| DOCS-06 | At milestone end, every submission document (README, ARCHITECTURE, EVALS, DESCRIPTION, STATUS, `docs/REQUIREMENTS`, `docs/ROADMAP`) is refreshed to the v1.1 state with no stale v1.0 claims. | §The stale-claim inventory (every line + exact correction) + §Blast radius. |
</phase_requirements>

## Summary

Phase 12 edits **no source behaviour**: it is a runbook, a dry-run harness, a doc refresh, and one honest
re-declaration. Three findings shape every plan decision:

1. **"Reload" means a fresh process — there is no reload flag.** `core/rules.py` loads the discriminator
   substrate through `get_discriminators()`, decorated `@lru_cache(maxsize=1)` and documented "loaded once
   per process" `[VERIFIED: src/triagedesk/core/rules.py:132-135]`. A reviewer's YAML edit is picked up
   simply by running a **new** command/process (CLI or desk restart). There is **no** `--reload`, no
   cache-clear flag, and adding one would be a source change this phase forbids. The honest runbook wording
   is: *"reload = run the command again in a new process."*
2. **The measured eval is silent and its real mode takes ~10 minutes.** `run_eval` has **no `print`**
   (verified: `grep -rn "print(" src/triagedesk/evals/` → none) — it writes `evals/results/report.json` and
   returns the gate exit code. `--offline` completes in **2.9 s**; the committed report is `mode: real`
   (3×16 real-model runs ≈ 13 s/case ⇒ ~10 min). A 2–3-minute demo therefore **cannot literally stream the
   real eval run**; the honest on-screen artefact is the committed `EVALS.md`/`report.json` plus the live
   `failure` beat (E-09) that already prints `DECLARED: ORANGE` vs `MEASURED: GREEN (SHOWN MISMATCH)`.
3. **`ARCHITECTURE.md` has only 2 words of headroom.** Its guard is `len(text.split()) <= 700` (all tokens,
   incl. headings/tables/blocks) and it currently measures **698 words / 94 lines** `[VERIFIED:
   tests/test_docs_final.py:57-61 + measured this session]`. Refreshing its stale node table *must not exceed
   700 words* — the refresh is effectively word-budget-neutral (replace, don't append).

**Primary recommendation:** prepare a NEW guarded `docs/REVIEW.md` runbook; prove the data-only extension
with a **hermetic tmp-data-dir test** (monkeypatch `rules.DISCRIMINATORS_PATH` + `get_discriminators.cache_clear()`);
re-run the demo and **re-transcribe the outcome blocks** into `docs/DEMO.md` (closing the Phase-11 drift);
add a **marked, attributed** clinician-review slot in README + `EVALS.md` §7 with no invented quote; and sweep
the enumerated v1.0 claims in the seven docs — keeping every existing guard green.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| The data-only live extension | **Data** (`data/sats_discriminators.yaml`) | Core loader (`core/rules.py`) | Extend by config (SOLID:O); the loader is the ONE read path and the matcher/scorer already consume it. |
| "Reload" semantics | **Runtime / process** | — | The substrate is `@lru_cache`d per process; a new process re-reads the file. No code layer involved. |
| Runbook-drift guard | **Test tier** (`tests/`) | CLI public `main` surface | Every documented command is driven through `triagedesk.cli.main` with side-effect seams spied (established pattern). |
| Dry-run harness | **Test tier** (`tests/`) | Data loader seam | A tmp data dir + loader->matcher->scorer assertion; writes only to tmp, never to `src/`. |
| Demo refresh | **Docs** (`docs/DEMO.md`) | CLI (`demo` runner) | The doc is transcribed FROM the shipped runner's output; the runner is the source of truth. |
| Clinical-fit re-declaration | **Docs** (README + `EVALS.md` §7) | — | A narrative declaration; `EVALS.md` §7 is hand-written narrative, NOT a generated number. |
| Submission-doc refresh | **Docs** (7 files) | Existing doc guards | Each doc has a guard that constrains its edit; the guard, not the doc, is the contract. |

---

## Standard Stack

**No new dependency, no version pin changes.** The phase uses only what is already present and locked.

### Core (existing, used by this phase)
| Tool | Version (this session) | Purpose here | Source |
|------|------------------------|--------------|--------|
| Python | `3.12.15` | Runtime for the hermetic harness + CLI | `[VERIFIED: measured this session]` |
| pytest | `9.1.1` (via `.venv`) | The "safety suite" + the new guards | `[VERIFIED: pytest run this session]` |
| uv | `0.12.24` | The documented runner (`uv run triagedesk ...`) | `[VERIFIED: measured this session]` |
| git | `2.53.0` | The "no code edit" proof (`git status --porcelain -- src/`) | `[VERIFIED: measured this session]` |
| PyYAML (`yaml`) | pinned in `uv.lock` | The dry-run harness writes a tmp YAML via the loader | `[VERIFIED: src/triagedesk/core/rules.py:18]` |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `subprocess` (stdlib) | Shell out for the "no code edit" check / drone the CLI in a guard | Only where an existing guard already does so (`tests/test_docs_final.py:106-111` shells to `emit_evals`). |
| `shlex` (stdlib) | Parse documented invocations into argv | Mirrors `tests/test_desk_runbook.py:22,51`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| A hermetic tmp-data-dir harness | Editing the real `data/*.yaml` then reverting in a `try/finally` | Reverting the real file is NOT hermetic — a crash mid-test leaves the repo dirty, and `tests hermetically` is a hard phase constraint. Prefer the tmp dir. |
| A NEW `docs/REVIEW.md` | A section inside `docs/DEMO.md` | D12 discretion prefers a new file; a separate file keeps one concern per document and is unconstrained by `test_demo_runbook.py`'s beat assertions. |
| Showing the live real eval | Showing the committed `EVALS.md` | The real eval is ~10 min; it cannot fit 2–3 min. The committed projection IS the measured artefact. |

**Installation:** none. `[VERIFIED: no package install performed or required this session]`

## Package Legitimacy Audit

> **Not applicable — this phase installs no external packages.** It adds no dependency, changes no pin, and
> introduces only a new doc (`docs/REVIEW.md`), new tests, and a possible `scripts/` rehearsal helper. The
> one borrowed server (`mcp-sqlite`) is already pinned and unchanged. Verdict: **no packages to audit.**

---

## The data-only live extension (REV-01 headline)

### The exact mechanism (read this session)

The discriminator substrate is read **only** through `core/rules.py` `[VERIFIED:
src/triagedesk/core/rules.py:1-11,119-135]`:

```python
# src/triagedesk/core/rules.py:119-135
def load_discriminators(path: Path | None = None) -> DiscriminatorRules:
    """Load and validate the discriminator substrate from *path* (default: the data file)."""
    source = path or DISCRIMINATORS_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    return DiscriminatorRules.model_validate(raw)

@lru_cache(maxsize=1)
def get_tews() -> TewsRules:
    """Return the TEWS rule substrate, loaded once per process."""
    return load_tews()

@lru_cache(maxsize=1)
def get_discriminators() -> DiscriminatorRules:
    """Return the discriminator substrate, loaded once per process."""
    return load_discriminators()
```

- `DISCRIMINATORS_PATH` is `DATA_DIR / "sats_discriminators.yaml"` `[VERIFIED: src/triagedesk/core/rules.py:25]`.
- `load_discriminators` **accepts a `path`** — the seam a tmp-data-dir harness uses.
- `get_discriminators` is `@lru_cache(maxsize=1)` → **loaded once per process** (the "reload" fact).
- `matcher.match_discriminators` calls `get_discriminators()` on **every** invocation `[VERIFIED:
  src/triagedesk/core/matcher.py:65-89]`; `scorer._most_urgent_category` calls it too `[VERIFIED:
  src/triagedesk/core/scorer.py:157-164]`. So nothing caches a copy beyond the ONE lru_cache.

A discriminator entry is `{id, category, label, aliases}` `[VERIFIED: data/sats_discriminators.yaml:35-38,
86-92]`:

```yaml
# data/sats_discriminators.yaml:35-38
  - id: obstructed_airway
    category: emergency
    label: "Obstructed airway — not breathing"
    aliases: ["obstructed airway", "airway obstruction", "not breathing", "no breathing", "choking", "apnoea", "apnea"]
```

Categories and their colours are `[VERIFIED: data/sats_discriminators.yaml:21-30]`:

```yaml
# data/sats_discriminators.yaml:21-30
categories:
  emergency:
    colour: RED
    citation_ref: "SATS Table: Emergency discriminators"
  very_urgent:
    colour: ORANGE
    citation_ref: "SATS Table: Very urgent discriminators"
  urgent:
    colour: YELLOW
    citation_ref: "SATS Table: Urgent discriminators"
```

### What "reload" means in the shipped system

**A fresh process.** The CLI re-reads the file on each invocation; the desk re-reads it on restart. There is
no cache-clear flag. The literal demonstration is therefore: *edit the YAML → run a NEW `uv run triagedesk …`
command*. The runbook must state this plainly and must NOT imply a hot reload.

### The safety suite that must pass

`tests/test_safety_spine.py` is the named safety-spine suite `[VERIFIED: tests/test_safety_spine.py:1-14]`.
The full suite is the strongest evidence. **Baseline: 444 passed in 32.14s** `[VERIFIED: measured this
session]`. The phase should name, in the runbook and the harness:

- `uv run pytest -q` (the whole 444-test suite) — the strongest "safety suite green" claim;
- specifically the substrate-shape predicates in `tests/test_sats_discriminators.py` (well-formed entry,
  unique ids, **alias ambiguity across discriminators**, every category used, every category maps to a
  unique colour) `[VERIFIED: tests/test_sats_discriminators.py:27-72]`;
- the DRY guard `tests/test_no_duplicated_sats.py` (a new alias must not also be inlined under `src/`)
  `[VERIFIED: tests/test_no_duplicated_sats.py:147-162]`;
- the matcher/scorer suites: `tests/test_matcher.py`, `tests/test_matcher_determinism.py`,
  `tests/test_scorer*.py`.

> **Critical pitfall (verified by reading the predicates):** the safety suite will **legitimately fail** if
> the live edit introduces an **ambiguous alias** (an alias already used by another discriminator) or a **new
> category reusing an existing colour** (colours must be unique) `[VERIFIED:
> tests/test_sats_discriminators.py:44-67]`. The runbook must therefore instruct the reviewer to add a
> discriminator **into an existing category** with a **unique alias** — a legend that says "pick a phrase not
> already in the file". This is the correct behaviour, not a defect.

### Exact commands a reviewer would type (proposed; the `[ASSUMED]` marker is only on the chosen phrase)

Design the live beat so the re-score is **visible** (a colour change) and **orthogonal to every eval fixture**
(it must NOT touch E-09's "feeling unwell", which is the declared failure — adding that alias would tune the
test green and is explicitly Out of Scope `[VERIFIED: docs/REQUIREMENTS.md:81]`).

```bash
# 0. Prove the starting state (no match for the new phrase) — fresh process
uv run triagedesk desk            # then type complaint "severe headache" -> no_match / deferral banner

# 1. Back up the machine authority, then append ONE discriminator (data-only).
cp data/sats_discriminators.yaml /tmp/sats_discriminators.bak.yaml

# 2. Reload = a NEW process. Re-run the same complaint:
#    the claim is that the colour now changes with zero code change.
#    (Run the desk again in a fresh process, or a one-line loader check — see the harness below.)

# 3. Prove no code changed:
git status --porcelain -- src/     # MUST print nothing

# 4. The safety suite is green WITH the addition:
uv run pytest -q

# 5. Revert the data edit (there is no in-band revert; this is the restore step):
git checkout -- data/sats_discriminators.yaml
```

> The chosen phrase ("severe headache" → a very_urgent override) is `[ASSUMED]` — it is a proposal, not read
> from any file, and no `severe headache`/`headache` discriminator currently exists in
> `data/sats_discriminators.yaml`. The planner must pick a phrase **not present in any `evals/cases/*.yaml`
> fixture** so the demonstration adds a NEW capability rather than re-tuning a published case.

**Command provenance:** `uv run triagedesk demo` is the documented literal one-liner `[VERIFIED:
README.md:84, docs/DEMO.md:31]`; `uv run triagedesk desk` is the documented desk one-liner `[VERIFIED:
README.md:87, docs/DESK.md:20]`; `uv run pytest -q` is the CI test command `[VERIFIED:
.github/workflows/eval-gate.yml]`.

### Dry-run harness design (D12-02) — hermetic

The harness proves *add-only, no-code* by writing **only to a tmp data dir** and driving the ONE loader:

```python
# tests/test_data_extension.py (proposed — [ASSUMED] shape, not yet written)
import shutil, yaml
from pathlib import Path
from triagedesk.core import rules
from triagedesk.core.matcher import match_discriminators
from triagedesk.core.scorer import score_priority
from triagedesk.core.schema import CaseInput

NEW = {"id": "pathfinder_probe", "category": "very_urgent",
       "label": "Probe", "aliases": ["pathfinder probe"]}   # [ASSUMED] illustrative only

def test_a_data_only_addition_rescores_without_code_change(tmp_path, monkeypatch):
    # 1. tmp copy of the real substrate + ONE new discriminator
    raw = yaml.safe_load(rules.DISCRIMINATORS_PATH.read_text(encoding="utf-8"))
    raw["discriminators"].append(NEW)
    tmp = tmp_path / "sats_discriminators.yaml"
    tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    # 2. redirect the ONE loader to the tmp file and drop the per-process cache
    monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)
    rules.get_discriminators.cache_clear()
    try:
        # 3. matcher now returns the new id; scorer now overrides to very_urgent's colour
        assert match_discriminators("pathfinder probe").matched_ids == ["pathfinder_probe"]
        case = CaseInput(age_years=40, mobility="walking", avpu="alert",
                         respiratory_rate=14, heart_rate=80, systolic_bp=120,
                         temperature_c=36.8, trauma=False, complaint="pathfinder probe")
        assert score_priority(case, ["pathfinder_probe"]).colour == "ORANGE"
    finally:
        rules.get_discriminators.cache_clear()
```

Notes for the planner:
- `monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)` + `rules.get_discriminators.cache_clear()` is the
  **only** seam needed (nothing else caches a copy) `[VERIFIED: src/triagedesk/core/rules.py:25,119-135]`.
- Assert **before/after** (`no_match=True` before, `matched_ids==[...]` after) so the proof is a *change*, not
  a constant.
- Assert the tmp addition **never touched `src/`** (the test writes only to `tmp_path`). Add a belt-and-braces
  `subprocess.run(["git","status","--porcelain","--","src/"]).stdout == b""` only if the suite already shells
  out elsewhere (`test_docs_final.py:106` does) — it keeps the "no code edit" claim checkable.
- Keep the illustrative `NEW` id/alias **out of the real data file** (it lives only inside the test).

---

## The current demo (DEMO-02)

### What it actually plays (measured this session)

`uv run triagedesk demo` runs five beats offline in order `[VERIFIED: demo/storyboard.yaml:9-23 +
measured this session]`:

| Beat | Case | Current measured outcome (this session) |
|------|------|------------------------------------------|
| `routine` | E-01 | `GREEN` / `< 4 hours`, `matched ids: []`, citation = respiratory_rate band. **No `commit` line** (deferred). |
| `escalation` | E-02 | `ORANGE` / `< 10 min`, 3 citations, `commit : committed case 9300336d37c3651c at queue position 1 (ORANGE)`. |
| `deterioration` | E-07 | `ORANGE` / `< 10 min`, 3 citations, `second look : {"flag":true,"deteriorations":["respiratory_rate","heart_rate","systolic_bp"],...}`. **No `commit` line** (deferred). |
| `refusal` | E-02 | `ORANGE`, `commit : clinician dismissed the priority; refusing to commit`, `GATE REFUSED : no queue row written (rows added this beat: 0)`. |
| `failure` | E-09 | `GREEN` / `< 4 hours`, baseline citation, `DECLARED : ORANGE`, `MEASURED : GREEN (SHOWN MISMATCH)`. |

Each beat prints its real tool calls — **seven** owned tools are visible across the run (`normalize_case`,
`match_discriminators`, `score_priority`, `retrieve_evidence`, `assess_confidence`, `raise_recheck_flag`,
`commit_priority`) `[VERIFIED: measured this session]`.

**The demo is fast** (offline, in-memory store, no model, no borrowed server). It does **not** naturally run
2–3 minutes; the runbook's timing comes from **narration**, not from slow execution. `--online` (real model)
is the slow path (`docs/assets/demo.tape` sleeps 112 s after a single `--online` run).

### The Phase-11 deferred drift this phase must close (D12-10)

`docs/DEMO.md` §"Expected on-screen output per beat" is the **v1.0-freeze transcript** and carries a dated
"Known drift" note `[VERIFIED: docs/DEMO.md:110-119]`. Measured against today's output:

| Doc claim (stale) | Measured reality | Location |
|-------------------|------------------|----------|
| `routine` ends `commit : … queue position 1 (GREEN)` | `routine` **defers** — there is **no commit line** | `docs/DEMO.md:137` |
| `escalation` commits at **queue position 2** | commits at **queue position 1** | `docs/DEMO.md:150` |
| `deterioration` ends `commit : … queue position 3 (ORANGE)` | **defers** — no commit line; `second look:` line only | `docs/DEMO.md:164` |
| per-beat annotations name **five** owned tools | the run shows **seven** | `docs/DEMO.md:116-117` |
| `failure` shows `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)` | **matches** (unchanged) | `docs/DEMO.md:188-189` |

**Action:** re-run `uv run triagedesk demo`, re-transcribe the five `--- outcome ---` blocks faithfully (or
mark them illustrative + show the live command, per D12-10), and delete the now-obsolete "Known drift" note.

### Showing the measured eval honestly

- `uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json` is the committed
  harness command `[VERIFIED: EVALS.md:22-24]`. It runs **`mode: real`** by default and is **silent**
  (no stdout) `[VERIFIED: measured this session]`.
- `uv run triagedesk eval … --offline` completes in **2.9 s** and is also silent (exit 0) `[VERIFIED:
  measured this session]`.
- The **measured artefact on screen** is `EVALS.md` (the projection) and/or `evals/results/report.json`; the
  **live failure** is the `failure` beat (E-09). Neither the 2–3-minute demo nor the 10-minute review can
  stream 3×16 real-model runs (≈10 min). The runbook must say this plainly rather than imply a live ~10-min
  run fits the recording.

### What is HUMAN (D12-05) — flag, never claim

| Item | Status | Evidence |
|------|--------|----------|
| Screen recording | **HUMAN** | `docs/DEMO.md:3-5` already declares it |
| Public upload (YouTube/Vimeo) | **HUMAN — the one submission blocker** | `STATUS.md:44,69-71` (G1); `docs/REQUIREMENTS.md:159` (G-9) |
| A local `mp4` exists | Recorded, **unhosted** | `docs/assets/triagedesk-demo.mp4`, duration **32.88 s** `[VERIFIED: ffprobe this session]` |

The phase prepares the script + narration + a runnable dry-run and marks recording/upload `human_needed`; it
must NOT assert a hosted video.

---

## The runbook-guard pattern (D12-03)

Every runbook is guarded by a test that drives the shipped CLI through its **public `main`** with side-effect
seams spied, so a documented invocation cannot drift. The three existing guards establish the pattern:

- `tests/test_demo_runbook.py` — reads `docs/DEMO.md`, extracts fenced `--beat <name>` names, drives
  `main(["demo","--list"])`, asserts **set equality both ways**, asserts the bare one-command path, asserts
  the honesty clauses (`human` / `screen recording` / `unedited`), asserts `E-09` is present, and couples the
  gate's own dismissal reason to the doc `[VERIFIED: tests/test_demo_runbook.py:31-44,65-127]`.
- `tests/test_desk_runbook.py` — reads `docs/DESK.md`, extracts `uv run triagedesk desk …` invocations, spies
  `desk_server.serve`, drives `main`; asserts the one-command + URL; the fail-safe clauses; the
  transcript-vs-substrate equality; and "names no graph-internal identifier" `[VERIFIED:
  tests/test_desk_runbook.py:34-129]`.
- `tests/test_readme_runbook.py` — reads `README.md`, extracts `uv run triagedesk <cmd>`, spies `run_demo` +
  `serve`, drives `main`; asserts the bare demo and the optional desk command `[VERIFIED:
  tests/test_readme_runbook.py:33-104]`.

**A new `docs/REVIEW.md` guard (`tests/test_review_runbook.py`) should follow the same shape:**

```python
# proposed guard shape [ASSUMED] — mirrors the established pattern
RUNBOOK = Path("docs/REVIEW.md")
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION = re.compile(r"uv run triagedesk ([^\n`#]+)")

def test_documented_invocations_are_accepted_by_the_cli(monkeypatch):
    # spy the SIDE-EFFECT seams so nothing runs: run_demo, serve, AND run_eval
    monkeypatch.setattr(demo_run, "run_demo", _async_stub)
    monkeypatch.setattr(desk_server, "serve", _sync_spy)
    monkeypatch.setattr(runner_module, "run_eval", _async_stub)   # triagedesk.evals.runner.run_eval
    for argv in _documented_invocations(_text()):
        assert main(argv) == 0

def test_runbook_declares_the_human_actions():        # recording + upload flagged, not claimed
def test_runbook_names_the_data_only_extension():     # data/sats_discriminators.yaml + "no code"
def test_runbook_shows_the_e09_failure():             # E-09 present
```

> **Seam note (verified this session):** in `cli.main` the handlers are imported **lazily inside `main`**
> (`from triagedesk.evals.runner import run_eval`, `from triagedesk.demo.run import list_beats, run_demo`)
> `[VERIFIED: src/triagedesk/cli.py:161-168]`. Monkeypatching the **module attribute**
> (`triagedesk.evals.runner.run_eval`) works because the `from … import` re-reads the attribute at each
> `main()` call. The eval seam is a NEW spy the existing guards do not have.

---

## The clinical-fit re-declaration (FIT-01)

**What the docs currently claim (no over-claim found):**

- `EVALS.md` §7 "Clinician validation (declared gap)": *"We do not have guaranteed access … The expected
  colours in §4 are derived from the published SATS rules, not from clinician adjudication."* `[VERIFIED:
  EVALS.md:184-192]`. It also carries a **stale date**: *"a single clinician review before Day 5"* — Day 5 was
  2026-10-13 `[VERIFIED: EVALS.md:191-192]`.
- `README.md`: *"Clinician validation remains a declared gap"* `[VERIFIED: README.md:73,75]`.
- `docs/REQUIREMENTS.md` JC-3 / G-1 and `docs/PROJECT.md` §3.1 honest notes agree `[VERIFIED:
  docs/REQUIREMENTS.md:91,151; docs/PROJECT.md:36-45]`.

**Recommended exact action (FIT-01 + D12-06/07):**
1. Re-declare, in `README.md` and `EVALS.md` §7, that **no** triage nurse/clinician review was obtained,
   scoped to what was built and measured.
2. Replace the stale "before Day 5" line with a **marked, attributed, empty** slot:
   > *Clinician review: **none obtained** as of 2026-10-13. If a triage nurse/clinician review is arranged,
   > add their attributed quote here (name/role/date, with consent). Nothing is claimed until it is.*
3. Invent **nothing**. The `the agent's Discretion` item is the exact wording.

**Over-claim audit:** the only over-claim risk is the *date*, not the substance. Keep the phrase "declared
gap" and never write a quote that was not obtained.

---

## The stale-claim inventory (DOCS-06) — every line + exact correction

Read this section as the executor's checklist. Guarded docs are marked ⚠ (an edit must keep the guard green).

### `README.md` ⚠ (guards: `test_docs_final.py`, `test_readme_runbook.py`)
| Line (current) | Stale v1.0 claim | Correction |
|----------------|------------------|------------|
| `:11` | badge `status-v1.0--submission` | Update to the v1.1 status wording (keep the real one-command quickstart). |
| `:53` | "**Frozen submission (`v1.0-submission`)**" | Reflect v1.1 capabilities (durable resume, deferral banner, retrieval, desk surface) without dropping `v1.0-submission` as the frozen tag. |
| `:53-55` | capability list omits every v1.1 capability | Add a concise v1.1 capability sentence; **keep** `uv run triagedesk demo` `:84` and `uv run triagedesk desk` `:87` verbatim, and keep `EVALS.md` + `E-09` present `:73`. |

### `ARCHITECTURE.md` ⚠ (guards: `test_architecture_is_one_page` ≤700 words/≤110 lines; names `qwen2.5:1.5b`)
**698/700 words — only 2 words of headroom.** `[VERIFIED: measured this session]`
| Line (current) | Stale v1.0 claim | Correction |
|----------------|------------------|------------|
| `:20-30` node table lists 9 nodes | missing v1.1 nodes `ground`, `assess`, `request_missing_info`, `escalate` | Refresh to the real `TRACER_NODES` (13) `[VERIFIED: src/triagedesk/graph/build.py:100-114]` — **word-neutral: replace rows/tighten prose so total ≤700**. |
| `:38` "seven tools" | already correct ✅ | keep |

> If the table cannot be extended within 700 words, prefer a compact combined row (e.g. group the terminals)
> over deleting the model-name line — `test_architecture_names_the_measured_model` requires `qwen2.5:1.5b`
> `[VERIFIED: tests/test_docs_final.py:64-67]`.

### `DESCRIPTION.md` ⚠ (guard: within ±10% of 300 words; prose count **302**) `[VERIFIED: measured this session]`
| Line (current) | Stale v1.0 claim | Correction |
|----------------|------------------|------------|
| `:14-18` | describes the model + tools but no v1.1 capability | Add a short v1.1 clause (durable approve gate / deferral-on-no-match / desk surface), staying within the 270–330 bound `[VERIFIED: tests/test_docs_final.py:29-32,69-74]`. |

### `EVALS.md` ⚠ (guards: `emit_evals --check` exit 0; finalised header; E-09 present)
| Line (current) | Note | Correction |
|----------------|------|------------|
| `:184-192` §7 | hand-written narrative (not a generated number) | FIT-01: re-declare + marked slot; remove the stale "before Day 5" date. Do NOT touch generated cells/blocks. |
| generated §3/§4/§6.1 | must stay == `emit_evals --check` | any change must come from a **report regeneration**, not hand-editing (D12-09). |

### `STATUS.md` (no test guard — free to refresh)
| Line (current) | Stale v1.0 claim | Correction |
|----------------|------------------|------------|
| `:35` | "local `qwen2.5:1.5b` / `qwen3.5:4b`" | Reconcile with the measured default (`qwen2.5:1.5b`); link EVALS. |
| `:44,80` | 33 s video | still true (measured 32.88 s) — keep, but tie to the **upload** (G1). |
| `:46` | "697 words / 94 lines" | stale (698/94) and will move with the ARCHITECTURE refresh — replace with a link, not a restated count. |
| `:55` | "no desk surface + 13–17 s latency" | STALE — the desk surface now exists (Phase 10); latency must link to EVALS §3. |
| `:84-85` G7 | "borrowed MCP under-exercised; only `query` invoked" | STALE — Phase 9 (MCP-01) exercises the read paths; update to resolved/partial. |
| `:102-103` UX table | nurse surface = "a CLI + JSON"; approver = "hardcoded approve value" | STALE — Phase 10 delivered the desk HTML surface + real approve/edit/dismiss gate. |
| `:116-122` U1/U2/U4/U7 | "no desk surface / gate not an interaction / uncertainty buried / no UI contract" | STALE — Phase 10 addressed these; re-scope honestly (what remains: latency, vitals-entry ergonomics, environment). |
| `:151,153` SOTA table | `Durable/resumable execution` ❌ "not wired E2E"; `Observability` ❌ "no spans" | STALE — Phases 6/7 delivered these; update to present. |
| `:149-150` | RAG ❌ "no retrieval"; confidence ❌ "none" | STALE — Phase 9 delivered deterministic lexical retrieval; Phase 8 delivered coverage/deferral. Re-scope (no embedding retrieval; no calibrated probability). |
| `:214-221` | "444 tests pass" | still true unless new guards are added — update the count after adding them. |

### `docs/REQUIREMENTS.md` (no test guard)
| Line (current) | Stale v1.0 claim | Correction |
|----------------|------------------|------------|
| `:89` JC-1 | "5 reusable tool contracts" | STALE → 7 `[VERIFIED: src/triagedesk/graph/build.py:68-76]`. |
| `:101` DQ-2 | "exposes 5 distinct tools" | STALE → 7. |
| `:53` BW-3 | "✅ (under-exercised — STATUS G7)" | STALE — Phase 9 exercised read paths; update. |
| `:91` JC-3 | "no clinician interview … and no desk surface" | STALE on "no desk surface" (Phase 10); keep the clinician gap (FIT-01). |
| `:127` ST-1 | "🟡 ready by design; rehearsal pending" | This phase rehearses it → update after REV-01. |
| `:159` G-9 | demo video not uploaded | still true — the upload stays a flagged human step. |
| `:161` G-11 | "No desk-facing UX surface / gate interaction … OPEN" | STALE — Phase 10 built it; re-scope. |
| `:8` | "Updated 2026-10-10, post-build" | bump the date. |

### `docs/ROADMAP.md` (no test guard)
| Line (current) | Stale v1.0 claim | Correction |
|----------------|------------------|------------|
| `:3-6,12-16` | "5 phases / twenty…" v1.0 packaging framing | Refresh to note the v1.1 milestone phases (6–12) `[VERIFIED: .planning/ROADMAP.md:42-48]`; keep it a *packaging* doc that links, not restates. |

> **Complete-guard sweep (D12-11):** after every edit, run `uv run pytest -q` and confirm the four doc guards
> plus `test_eval_report.py` stay green.

---

## Blast radius

Baseline: **444 passed in 32.14s** `[VERIFIED: measured this session]`. Tests that read a doc and can break
when it changes (verified by grep this session):

| Test file | Doc it reads | Breaks when… |
|-----------|--------------|--------------|
| `tests/test_docs_final.py` | `ARCHITECTURE.md`, `DESCRIPTION.md`, `README.md`, `EVALS.md` | ARCH >700 words / >110 lines; DESCRIPTION out of ±10% of 300; README loses `uv run triagedesk demo` or gains `uv sync --locked`, or gains a stale row (`Not built`/`Not recorded`/`pre-build`), or loses `EVALS.md`/`E-09`; `emit_evals --check` ≠ 0; EVALS gains stale framing. |
| `tests/test_readme_runbook.py` | `README.md` | a documented `uv run triagedesk …` invocation the CLI rejects; the bare demo or the desk command removed. |
| `tests/test_demo_runbook.py` | `docs/DEMO.md` | documented beats ≠ CLI beats (either direction); bare command removed; `human`/`screen recording`/`unedited` removed; `E-09` removed; the dismissal-refusal string removed. |
| `tests/test_desk_runbook.py` | `docs/DESK.md` | (only if DESK.md is touched) an invocation rejected; the URL removed; a fail-safe clause removed; a graph-internal identifier named. |
| `tests/test_eval_report.py` | `EVALS.md` + `report.json` | §4 rows ≠ report cases; a declared failure rendered as a bare pass; a gate failure missing from §6.1; report not `mode: real`. |
| **NEW** `tests/test_review_runbook.py` | `docs/REVIEW.md` | (new) a documented invocation the CLI rejects; the human flags removed; the data-only extension unnamed. |
| **NEW** `tests/test_data_extension.py` | (tmp data only) | the loader no longer honours a `path`; the matcher/scorer no longer consume the substrate. |

**No existing test reads `STATUS.md`, `docs/REQUIREMENTS.md`, or `docs/ROADMAP.md`** — those three are
unguarded and can be swept freely `[VERIFIED: grep over tests/ this session]`.

**Adding the two new test files raises the count above 444**; update `STATUS.md:215` to the new number.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Proving a data-only extension | A bespoke re-implementation of matching/scoring | The shipped `match_discriminators` + `score_priority` via the ONE loader | A re-implementation would prove nothing about the shipped path (DRY, SOLID:L). |
| Reloading the substrate | A cache-clear CLI flag | A **fresh process** | The `@lru_cache` is per process by design; a flag is a source change this phase forbids. |
| Guarding a runbook | A new bespoke doc-reader | The established fenced-block + `main` + spy pattern (`test_desk_runbook.py`) | One consistent pattern; the CLI is the source of truth. |
| Showing the measured eval | Re-running the 10-min real eval live | The committed `EVALS.md`/`report.json` + the live `failure` beat | The real run cannot fit 2–3 min; the projection IS the measured artefact. |
| Emitting the eval numbers | Hand-editing `EVALS.md` | `scripts/emit_evals.py --write` from `report.json` | D12-09: EVALS.md is only the projection. |

**Key insight:** the project's whole safety story is *"extend by data, not code"* (SOLID:O). Phase 12 is the
place that story is **demonstrated** — so the harness must exercise the *shipped* loader/matcher/scorer, never
a parallel copy.

---

## Runtime State Inventory

> Included because this phase mutates docs and a data file at the milestone close (a docs migration).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the domain/audit DBs (`triage.db`, `checkpoints.db`) are runtime artefacts, gitignored `[VERIFIED: .gitignore:19]`, untouched by a doc/runbook phase. | None |
| Live service config | None — no hosted service; the demo upload is an **external** human action (G1), not config in this repo. | Flag in the runbook as `human_needed` |
| OS-registered state | None — no scheduler/pm2/launchd/systemd state involved. | None |
| Secrets/env vars | None — the offline path needs no credentials `[VERIFIED: docs/DEMO.md:24-25]`; no env var is renamed. | None |
| Build artifacts | The recorded video `docs/assets/triagedesk-demo.mp4` (**32.88 s**) is a committed asset, not a build artefact; the `spans.jsonl`/`*.db` runtime files are gitignored. | Keep the video asset; do not claim it is hosted |
| Frozen tag | `v1.0-submission` is the frozen tag `[VERIFIED: git tag this session: v1.0, v1.0-submission]`; v1.1 is additive. | Doc refresh must not contradict the frozen v1.0 tag |

**Canonical question:** *After every doc is updated, what runtime system still carries a stale v1.0 string?* —
**Nothing** in this repo. The only stale artefact is the **hosted-video** state, which is human and external.

---

## Common Pitfalls

### Pitfall 1: Assuming a hot "reload" exists
**What goes wrong:** the runbook implies the running process picks up the YAML edit live.
**Why:** `get_discriminators()` is `@lru_cache(maxsize=1)` — per process `[VERIFIED:
src/triagedesk/core/rules.py:132-135]`.
**How to avoid:** state "run the command again in a new process"; never document a `--reload`.
**Warning signs:** a documented flag the CLI does not have (the runbook guard would fail).

### Pitfall 2: A live edit that trips the substrate-shape safety tests
**What goes wrong:** the added alias collides with an existing one, or a new category reuses a colour.
**Why:** `test_aliases_are_unambiguous_across_discriminators` and `test_every_category_maps_to_a_colour`
require uniqueness `[VERIFIED: tests/test_sats_discriminators.py:44-67]`.
**How to avoid:** add into an **existing** category with a **unique** alias; say so in the runbook.
**Warning signs:** `pytest` fails on the discriminator-shape tests during rehearsal.

### Pitfall 3: Tuning E-09 green by accident
**What goes wrong:** the demo alias equals "feeling unwell" (or any E-09 fixture phrase).
**Why:** that is the declared failure, and adding its alias is explicitly Out of Scope `[VERIFIED:
docs/REQUIREMENTS.md:81]`.
**How to avoid:** choose a phrase absent from every `evals/cases/*.yaml`.

### Pitfall 4: Non-hermetic harness (real-file edit)
**What goes wrong:** a test edits the real `data/sats_discriminators.yaml` and reverts in `finally`; a crash
leaves the repo dirty.
**Why:** the real file is repo state, not fixture state.
**How to avoid:** tmp path + `monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)` +
`cache_clear()`.

### Pitfall 5: Blowing the ARCHITECTURE 700-word bound
**What goes wrong:** the node-table refresh pushes total tokens over 700.
**Why:** `test_architecture_is_one_page` counts **all** `text.split()` tokens; current 698/700.
**How to avoid:** make the table refresh word-neutral (replace/collapse rows; trim prose elsewhere).

### Pitfall 6: Hand-editing `EVALS.md` numbers
**What goes wrong:** `emit_evals --check` exits non-zero.
**Why:** EVALS.md numbers are the projection `[VERIFIED: tests/test_docs_final.py:104-111]`.
**How to avoid:** edit only narrative; regenerate numbers from `report.json`.

### Pitfall 7: Claiming the demo is recorded/hosted
**What goes wrong:** an over-claim that fails the honesty rule.
**Why:** D12-05/D12-07.
**How to avoid:** `human_needed` marker; `docs/DEMO.md` keeps `human`/`screen recording`/`unedited`
(guarded by `test_demo_runbook.py`).

### Pitfall 8: Re-introducing the two-step install in README
**What goes wrong:** adding `uv sync --locked` (as `docs/DESK.md` still shows it).
**Why:** `test_docs_final.test_readme_has_the_one_command_quickstart` forbids `uv sync --locked` in
**README** `[VERIFIED: tests/test_docs_final.py:86-87]`.
**How to avoid:** leave the README quickstart exactly as `uv run triagedesk demo`.

---

## Code Examples (verified patterns from the repo)

### Driving the CLI in a guard with side-effect seams spied
```python
# Source: tests/test_readme_runbook.py:74-94 (established pattern)
demo_calls, desk_calls = [], []
async def _run_demo_spy(*a, **k): demo_calls.append(k); return 0
def _serve_spy(*a, **k): desk_calls.append(k)
monkeypatch.setattr(demo_run, "run_demo", _run_demo_spy)
monkeypatch.setattr(desk_server, "serve", _serve_spy)
for argv in invocations:
    assert main(argv) == 0
```

### Redirecting the ONE loader to a tmp data file (the data-extension seam)
```python
# Source: src/triagedesk/core/rules.py:25,119-135 (the API being used)
monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp_path / "sats_discriminators.yaml")
rules.get_discriminators.cache_clear()   # drop the per-process cache
```

### The committed harness command (do not restate its numbers elsewhere)
```bash
# Source: EVALS.md:22-24
uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docs/DEMO.md` v1.0-freeze transcript with a "Known drift" note | Re-transcribed output after a re-run | This phase (D12-10) | The doc stops contradicting the shipped CLI. |
| STATUS.md "genuine gap" rows for durable/observability/confidence/RAG | Present capabilities (Phases 6–10) | This phase (DOCS-06) | The self-assessment stops under-claiming resolved work. |
| No live-review rehearsal (`ST-1 🟡 rehearsal pending`) | A rehearsed, guarded `docs/REVIEW.md` | This phase (REV-01) | The Stage-2 "add a requirement live" is demonstrated. |

**Deprecated/outdated:** the "Known drift" note in `docs/DEMO.md:110-119` is deleted once the re-transcription
lands.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The chosen live-extension phrase (e.g. "severe headache") is not in any eval fixture. | §data-only extension | If it is, the demo re-tunes a published case — pick another phrase after grepping `evals/cases/`. |
| A2 | The reviewer can run a local terminal + `uv` during the review (the desk/CLI story). | §data-only extension, §demo | The live demo would collapse; the review would have to be desktop-shared. |
| A3 | `docs/REVIEW.md` (new) is the right home vs a `docs/DEMO.md` section. | §runbook pattern | Low — D12 discretion; either works, the guard pattern is the same. |
| A4 | The DESK/README/DEMO invocations in the new runbook are all CLI-accepted (so the guard passes). | §runbook pattern | The guard fails; fix the invocation. |
| A5 | The video stays a `human_needed` step (owner has not arranged the upload). | §demo | If an upload link is arranged, the doc should carry the real URL, not a placeholder. |

**If this table is empty:** not applicable — the items above need confirmation or a grep before locking.

---

## Open Questions (RESOLVED)

1. **Which exact alias for the live extension?**
   - What we know: it must be unique, in an existing category, and absent from every `evals/cases/*.yaml`.
   - What's unclear: the best phrase for the *narration*.
   - Recommendation: grep `evals/cases/` for the candidate phrase in the plan and pick a clean one; document the choice.
   - **Resolution:** the alias is `"severe headache"` (id `severe_headache`, category `very_urgent`); plan 12-01 selects it and `tests/test_data_extension.py::test_the_chosen_alias_is_absent_from_every_published_case` proves it is absent from every `evals/cases/*.yaml` fixture (so the extension adds a capability and cannot re-tune E-09).

2. **Does the review's "measured eval on screen" mean `EVALS.md` or a live `--offline` run?**
   - What we know: real mode ≈10 min and is silent; `--offline` is 2.9 s and silent; `EVALS.md` is the projection.
   - What's unclear: presenter preference.
   - Recommendation: show `EVALS.md` (the measured artefact) + narrate the `failure` beat; do not imply a live 10-min run.
   - **Resolution:** show the committed `EVALS.md` projection (the `report.json` artifact) plus the live `uv run triagedesk demo --beat failure` beat, which prints `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN MISMATCH)`; the ~10-min real run is NOT streamed. Pinned in plan 12-01 beat 6 and plan 12-02's measured-eval beat.

3. **Does `docs/REVIEW.md` need its own `DESK.md`-style transcript guard, or is invocation-guarding enough?**
   - Recommendation: invocation-guarding + honesty-clause assertions (mirror `test_demo_runbook.py`); a transcript guard is optional and adds fragility.
   - **Resolution:** invocation-guarding only — `tests/test_review_runbook.py` drives every documented `uv run triagedesk …` through the shipped `main` with all five side-effect seams spied, plus the honesty-clause asserts; no transcript guard (plan 12-01 Task 1).

4. **Should the freeze-protocol commit timing be rehearsed here?**
   - What we know: the freeze/dsc protocol lives in `docs/ROADMAP.md` §Freeze; a post-deadline commit disqualifies.
   - Recommendation: note in the runbook that doc edits must land **before** the freeze; do not rehearse the freeze itself in this phase.
   - **Resolution:** not rehearsed — plan 12-01 instead adds the note to `docs/REVIEW.md`'s beat list that any remaining doc edit must land **before** the repository freeze (a post-deadline commit disqualifies); the freeze itself is not rehearsed on the day.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python (venv) | harness + CLI | ✓ | 3.12.15 | — |
| uv | documented runner | ✓ | 0.12.24 | — |
| pytest | safety suite | ✓ | 9.1.1 | — |
| git | "no code edit" proof | ✓ | 2.53.0 | `diff` of `src/` snapshot |
| node/npx | borrowed server (not needed offline) | ✓ | 22.14.0 / 11.8.0 | offline path needs neither |
| Ollama | `--online` demo only | ✓ | 0.30.6 | offline demo needs no model |
| ffprobe | confirm the video duration | ✓ | 8.0.1 | `ls -la` size only |
| YouTube/Vimeo upload | the demo submission (G1) | ✗ | — | **HUMAN step** — flag, never claim |

**Missing dependencies with no fallback:** the hosted-demo-video upload — a **human** action; the phase must
flag it `human_needed` (D12-05) and never assert it is done.

**Missing dependencies with fallback:** none blocking.

---

## Security Domain

> `security_enforcement` is enabled `[VERIFIED: .planning/config.json:48]`; this phase changes no runtime
> behaviour, so the applicable surface is documentation honesty + the rehearsal procedure.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth surface changes (approver authn remains a declared gap). |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (documentation) | The safety suite's substrate-shape predicates gate any documented data edit `[VERIFIED: tests/test_sats_discriminators.py]`. |
| V6 Cryptography | no | No crypto touched. |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Runbook instructs exposing a network surface | Information disclosure | Only loopback/local commands are documented; the desk is loopback-only `[VERIFIED: docs/DESK.md:3-7]`. |
| A doc claims a safety property the code does not hold | Repudiation / over-claim | Keep every doc guard green; keep `human_needed` flags. |
| Editing the frozen safety spine | Tampering | No `src/` change; `git status --porcelain -- src/` stays empty. |

---

## Sources

### Primary (HIGH confidence — read or executed this session)
- `src/triagedesk/core/rules.py` — the ONE loader; `@lru_cache` per process; `path` seam.
- `src/triagedesk/core/matcher.py`, `src/triagedesk/core/scorer.py` — consume the loader on every call.
- `src/triagedesk/core/schema.py` — `CaseInput`, `MatchResult`, `PriorityResult` (no colour on the evidence contract).
- `src/triagedesk/cli.py` — `main`, lazy handler imports, the `demo`/`eval`/`desk` subcommands.
- `src/triagedesk/demo/run.py` + `demo/storyboard.yaml` — the five beats.
- `src/triagedesk/graph/build.py` — `TRACER_NODES` (13), `OWNED_TOOL_ALLOWLIST` (7), `checkpointed_graph`.
- `src/triagedesk/evals/runner.py`, `src/triagedesk/evals/tools.py` — silent `run_eval`; matcher runs for real offline.
- `scripts/emit_evals.py` — EVALS.md is the projection; `--check`/`--write`.
- `tests/test_docs_final.py`, `tests/test_demo_runbook.py`, `tests/test_desk_runbook.py`, `tests/test_readme_runbook.py`, `tests/test_safety_spine.py`, `tests/test_sats_discriminators.py`, `tests/test_no_duplicated_sats.py`, `tests/test_eval_report.py` — the guards.
- `data/sats_discriminators.yaml`, `data/sats_tews.yaml` — the machine authorities.
- All seven submission docs + `STATUS.md` + `docs/DEMO.md`/`DESK.md`/`CONVENTIONS.md`/`PROJECT.md`.
- **Measured:** the full suite (**444 passed in 32.14s**), the whole demo run, `eval --offline` (2.9 s, silent),
  the tool/uv/ollama/git versions, the video duration (32.88 s), ARCHITECTURE (698 words/94 lines), DESCRIPTION (302).

### Secondary (MEDIUM confidence)
- `docs/assets/demo.tape` — the vhs recording tape (112 s sleep; `--online`).

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new stack; everything read/executed.
- Architecture: HIGH — the loader/reload/matcher facts were read from source and confirmed by running the CLI.
- Pitfalls: HIGH — the guard bounds and the substrate-shape predicates were read verbatim.

**Research date:** 2026-10-13
**Valid until:** 2026-10-20 (7 days — the deadline is 2026-10-15; this is a fast-moving close-out).
