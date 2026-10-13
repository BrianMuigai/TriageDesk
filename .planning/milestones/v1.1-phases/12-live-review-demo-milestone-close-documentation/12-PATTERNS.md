# Phase 12: Live Review, Demo & Milestone-Close Documentation - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 13 (3 new, 10 modified)
**Analogs found:** 13 / 13 (all analogs git-tracked; verified with `git ls-files`)

> This is a **docs + guards** phase — it changes no `src/` behaviour. The patterns that matter are the
> **runbook-drift guard**, the **hermetic data-only test seam**, the **doc guards**, and the
> **link-don't-restate** convention. Every excerpt below is copy-ready.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/REVIEW.md` (NEW) | doc / runbook | transform (prose) | `docs/DESK.md` | role-match (literal guarded quickstart) |
| `tests/test_review_runbook.py` (NEW) | test (guard) | request-response (drives CLI) | `tests/test_desk_runbook.py` + `tests/test_readme_runbook.py` | exact (same guard shape) |
| `tests/test_data_extension.py` (NEW) | test (harness) | transform / CRUD (load→match→score) | `tests/conftest.py` + `tests/test_sats_discriminators.py` | role-match (test, different data flow) |
| `docs/DEMO.md` (MODIFY) | doc / runbook | transform (prose) | itself + guard `tests/test_demo_runbook.py` | exact |
| `README.md` (MODIFY) | doc | transform (prose) | itself + guards `test_docs_final.py` / `test_readme_runbook.py` | exact |
| `ARCHITECTURE.md` (MODIFY) | doc (word-budgeted) | transform (prose) | itself + guard `test_docs_final.py` | exact |
| `EVALS.md` (MODIFY) | doc (generator projection) | transform (prose) | itself + `scripts/emit_evals.py` + guard `test_eval_report.py` | exact |
| `DESCRIPTION.md` (MODIFY) | doc (±10% of 300 words) | transform (prose) | itself + guard `test_docs_final.py` | exact |
| `STATUS.md` (MODIFY) | doc (unguarded) | transform (prose) | itself | exact |
| `docs/REQUIREMENTS.md` (MODIFY) | doc (unguarded) | transform (prose) | itself | exact |
| `docs/ROADMAP.md` (MODIFY) | doc (unguarded, packaging) | transform (prose) | itself | exact |
| `docs/DECISIONS.md` (MODIFY, optional) | doc (ADR-lite) | transform (prose) | itself | exact |
| `tests/test_docs_final.py` (MODIFY, only if a guard changes) | test (guard) | transform | itself | exact |

---

## Pattern Assignments

### `docs/REVIEW.md` (NEW — doc / runbook)

**Analog:** `docs/DESK.md` (a literal, guarded quickstart) and `docs/DEMO.md` (the beat table).

The runbook is **literal and ordered** (D12-01): prose beats with exact commands in fenced blocks, and
every command in a `uv run triagedesk …` fenced block so the guard can extract and drive it.

**Document header / declared honest status pattern** — `docs/DESK.md:1-7`:
```markdown
# REVIEW — TriageDesk live-review rehearsal runbook

> **One page, driven from the page.** This is the 10-minute live technical review (Stage 2). Every
> command below is exercised against the shipped CLI by [`tests/test_review_runbook.py`](../tests/test_review_runbook.py),
> so the walkthrough cannot drift. The live extension is a **data edit** — one line in
> `data/sats_discriminators.yaml`, no code change.

> **"Reload" means a fresh process.** `get_discriminators()` is `@lru_cache`d per process, so an edit is
> picked up by running the command again in a NEW process. There is no `--reload` and no cache-clear flag.
```

**Fenced-command pattern** (the guard extracts these — every command must be a `uv run triagedesk …`
invocation) — mirror `docs/DESK.md:18-24`:
```bash
# 0. Show the starting state (no match for the new phrase) — fresh process:
uv run triagedesk desk

# 1. Add ONE discriminator into an EXISTING category with a UNIQUE alias (data-only edit), then:
#    reload = run the command again in a NEW process (no hot reload exists).
uv run triagedesk desk

# 2. Prove no code changed:
git status --porcelain -- src/     # MUST print nothing

# 3. The safety suite is green WITH the addition:
uv run pytest -q
```

**Human-action flag pattern** (D12-05 — flag, never claim) — mirror `docs/DEMO.md:3-5`:
```markdown
> **What is human.** The recording and the public upload are **HUMAN** actions; this runbook prepares
> the script and a runnable dry-run and does not claim a video exists or is hosted.
```

**Verified-claim notes to carry (from RESEARCH, not to be re-derived):**
- Reload semantics: new process, no flag (`src/triagedesk/core/rules.py:132-135`).
- The live edit must use an **existing category** + a **unique alias** — else the safety suite legitimately
  fails (`tests/test_sats_discriminators.py:44-67`).
- The chosen phrase must be **absent from every `evals/cases/*.yaml`** (do NOT tune E-09; `docs/REQUIREMENTS.md:81`).

**Guard:** `docs/REVIEW.md` is read by `tests/test_review_runbook.py`; see the next block.

---

### `tests/test_review_runbook.py` (NEW — test guard)

**Analogs:** `tests/test_desk_runbook.py` (fenced-block extractor + `shlex` + spy) and
`tests/test_readme_runbook.py` (async `run_demo` spy + sync `serve` spy), plus `tests/test_demo_runbook.py`
(honesty-clause asserts).

**Imports + fence/invocation regexes + extractor** — from `tests/test_desk_runbook.py:19-51`:
```python
from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest

from triagedesk.cli import main
from triagedesk.demo import run as demo_run
from triagedesk.desk import server as desk_server
from triagedesk.evals import runner as eval_runner   # the NEW seam this guard adds

RUNBOOK_PATH = Path("docs/REVIEW.md")

# Fenced blocks (```...```) and a ``uv run triagedesk <cmd>`` invocation inside one.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION_RE = re.compile(r"uv run triagedesk ([^\n`]+)")


def _runbook_text() -> str:
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def _documented_invocations(text: str) -> list[list[str]]:
    """Every ``uv run triagedesk`` invocation in the fenced blocks, as argv ``main`` receives.

    Any inline ``# …`` trailing comment is stripped (mirrors ``tests/test_readme_runbook.py:54-58``).
    """
    fenced = "\n".join(_FENCE_RE.findall(text))
    invocations: list[list[str]] = []
    for match in _INVOCATION_RE.findall(fenced):
        command = match.split("#", 1)[0].strip()
        if command:
            invocations.append(shlex.split(command))
    return invocations
```

**Drive the shipped CLI with ALL side-effect seams spied** — the key delta is the **new lazily-imported
`evals.runner.run_eval` seam**. In `cli.main` the handlers are imported lazily inside `main`
(`src/triagedesk/cli.py:162-166`), so monkeypatching the **module attribute** works on each `main()` call:
```python
def test_documented_invocations_are_accepted_by_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """No documented invocation the shipped CLI rejects (the runbook cannot invent a flag)."""
    invocations = _documented_invocations(_runbook_text())
    assert invocations, "docs/REVIEW.md documents no triagedesk invocation"

    demo_calls: list[dict[str, Any]] = []
    desk_calls: list[dict[str, Any]] = []
    eval_calls: list[dict[str, Any]] = []

    async def _run_demo_spy(*args: Any, **kwargs: Any) -> int:
        demo_calls.append(kwargs); return 0

    async def _run_eval_spy(*args: Any, **kwargs: Any) -> int:
        eval_calls.append(kwargs); return 0

    def _serve_spy(*args: Any, **kwargs: Any) -> None:
        desk_calls.append(kwargs)

    monkeypatch.setattr(demo_run, "run_demo", _run_demo_spy)
    monkeypatch.setattr(eval_runner, "run_eval", _run_eval_spy)   # NEW seam (cli.py:164)
    monkeypatch.setattr(desk_server, "serve", _serve_spy)

    for argv in invocations:
        before = (len(demo_calls), len(desk_calls), len(eval_calls))
        assert main(argv) == 0, f"the shipped CLI rejected a documented invocation: {argv}"
        after = (len(demo_calls), len(desk_calls), len(eval_calls))
        assert sum(after) > sum(before), f"the documented invocation never reached a seam: {argv}"
```

**Honesty-clause asserts** — mirror `tests/test_demo_runbook.py:80-90`:
```python
def test_runbook_declares_the_human_actions() -> None:
    text = _runbook_text().lower()
    assert "human" in text
    assert "upload" in text          # the hosted demo is human (docs/REQUIREMENTS.md G-9)

def test_runbook_names_the_data_only_extension() -> None:
    text = _runbook_text()
    assert "data/sats_discriminators.yaml" in text
    assert "no code" in text.lower()

def test_runbook_shows_the_e09_failure() -> None:
    assert "E-09" in _runbook_text()
```

> **Why the `run_eval` seam is required:** if the runbook documents `uv run triagedesk eval …`, the guard
> must spy `run_eval` or the test would launch a real (~10 min, `mode: real`) eval. See RESEARCH §runbook
> pattern + `src/triagedesk/cli.py:164,169-178`.

---

### `tests/test_data_extension.py` (NEW — hermetic data-only harness)

**Analogs:** `tests/conftest.py` (the monkeypatch-seam idioms) and `tests/test_sats_discriminators.py`
(loading the substrate through the ONE loader). The seam itself is `src/triagedesk/core/rules.py:25,119-135`.

This proves D12-02 hermetically: write only to `tmp_path`, redirect the ONE loader, drop the per-process
cache, assert a **before/after change** through the **shipped** matcher + scorer.

**The API being driven (copy the contract exactly):**
```python
# src/triagedesk/core/rules.py:25,119-135
DISCRIMINATORS_PATH = DATA_DIR / "sats_discriminators.yaml"

def load_discriminators(path: Path | None = None) -> DiscriminatorRules: ...

@lru_cache(maxsize=1)
def get_discriminators() -> DiscriminatorRules:  # loaded once per process
    return load_discriminators()

# src/triagedesk/core/matcher.py:65   -> match_discriminators(complaint: str) -> MatchResult
# src/triagedesk/core/scorer.py:194   -> score_priority(case: CaseInput, matched_discriminator_ids=None) -> PriorityResult
```

**The hermetic harness shape** (from RESEARCH §Dry-run harness, verified seams):
```python
from __future__ import annotations

from pathlib import Path

import yaml

from triagedesk.core import rules
from triagedesk.core.matcher import match_discriminators
from triagedesk.core.schema import CaseInput
from triagedesk.core.scorer import score_priority

# The illustrative addition lives ONLY in this test — never in the real data file.
NEW = {
    "id": "pathfinder_probe",
    "category": "very_urgent",          # an EXISTING category (colour uniqueness holds)
    "label": "Probe",
    "aliases": ["pathfinder probe"],    # a UNIQUE alias, absent from every evals/cases fixture
}


def test_a_data_only_addition_rescores_without_code_change(tmp_path: Path, monkeypatch) -> None:
    # 0. BEFORE: the phrase matches nothing (a change, not a constant).
    assert match_discriminators(NEW["aliases"][0]).no_match is True

    # 1. tmp copy of the real substrate + ONE new discriminator (writes only to tmp_path).
    raw = yaml.safe_load(rules.DISCRIMINATORS_PATH.read_text(encoding="utf-8"))
    raw["discriminators"].append(NEW)
    tmp = tmp_path / "sats_discriminators.yaml"
    tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    # 2. redirect the ONE loader to the tmp file and drop the per-process cache.
    monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)
    rules.get_discriminators.cache_clear()
    try:
        # 3. AFTER: the SHIPPED matcher returns the new id; the SHIPPED scorer overrides the colour.
        assert match_discriminators(NEW["aliases"][0]).matched_ids == [NEW["id"]]
        case = CaseInput(
            age_years=40, mobility="walking", avpu="alert", respiratory_rate=14,
            heart_rate=80, systolic_bp=120, temperature_c=36.8, trauma=False,
            complaint=NEW["aliases"][0],
        )
        assert score_priority(case, [NEW["id"]]).colour == "ORANGE"
    finally:
        rules.get_discriminators.cache_clear()   # never leak the tmp substrate to another test
```

> **Reuse, don't re-implement** (DRY / SOLID:L): drive `match_discriminators` + `score_priority`, never a
> parallel copy. `monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp)` + `cache_clear()` is the **only**
> seam needed (nothing else caches a copy — `matcher.py:73`, `scorer.py:157` both call `get_discriminators()`).
> Optional belt-and-braces "no code edit" check: `subprocess.run(["git","status","--porcelain","--","src/"]).stdout == b""`
> — mirrors `tests/test_docs_final.py:106-111` (the suite already shells out).

---

### `docs/DEMO.md` (MODIFY — refresh + close the Phase-11 drift)

**Analog:** itself; its guard is `tests/test_demo_runbook.py`.

**What must change (D12-10, verified in RESEARCH §The Phase-11 deferred drift):**
- `routine` (E-01) and `deterioration` (E-07) now **defer** — delete their `commit : … queue position N` lines
  (`docs/DEMO.md:137,164`).
- `escalation` (E-02) commits at **queue position 1** (`docs/DEMO.md:150`).
- Beats show **seven** owned tools, not five (`docs/DEMO.md:116-117`).
- `failure` (E-09) block is unchanged (`docs/DEMO.md:188-189`).
- **Delete** the "Known drift" block (`docs/DEMO.md:110-119`).

**Guard constraints the edit must preserve** (`tests/test_demo_runbook.py`):
- documented `--beat` names == CLI `demo --list` names (**set equality both ways**) — `:65-72`;
- bare `uv run triagedesk demo` present — `:75-77`;
- honest clauses `human` / `screen recording` / `unedited` present — `:80-85`;
- `E-09` present — `:88-90`;
- the gate's dismissal refusal string present verbatim — `:93-127`.

**Outcome-block format to re-transcribe faithfully** (from the shipped runner; keep the exact shape) —
`docs/DEMO.md:131-138`:
```text
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  matched ids  : []
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band
```

**If re-transcription is not feasible, the D12-10 alternative:** mark the blocks **illustrative** and show
the live command. Either way the doc must stop contradicting the shipped CLI.

---

### `README.md` (MODIFY — v1.1 refresh)

**Analog:** itself. **Guards:** `tests/test_docs_final.py:77-101`, `tests/test_readme_runbook.py`.

**Stale claims to sweep** (from RESEARCH §stale-claim inventory): badge `:11` (`status-v1.0--submission`),
`Frozen submission` line `:53`, capability list `:53-55`.

**Guards that MUST stay green** (do not break while editing):
```python
# tests/test_docs_final.py:77-101
assert "uv run triagedesk demo" in text          # keep verbatim (README.md:84)
assert "uv sync --locked" not in text            # do NOT add a two-step install
for stale in ("Not built", "Not recorded", "pre-build"): assert stale not in text
assert "EVALS.md" in text and "E-09" in text     # keep the honest pointer (README.md:73)
```
```python
# tests/test_readme_runbook.py:97-104
assert "uv run triagedesk demo" in _readme_text()   # bare one-command path
assert "uv run triagedesk desk" in _readme_text()   # optional second command (README.md:87)
```

**Link-don't-restate pattern** (DRY — CONVENTIONS §1) — the established form, `README.md:70-75,94`:
```markdown
[`EVALS.md`](EVALS.md) is the single source for every number.
[`docs/DEMO.md`](docs/DEMO.md) — it does not restate the demo here (DRY).
```

---

### `ARCHITECTURE.md` (MODIFY — **word-budget-neutral**)

**Analog:** itself. **Guard:** `tests/test_docs_final.py:57-67`.

**THE HARD CONSTRAINT — measured 698/700 words, 94/110 lines** (`len(text.split()) <= 700` over ALL
tokens incl. headings/tables/blocks):
```python
# tests/test_docs_final.py:57-67
def test_architecture_is_one_page() -> None:
    text = _text(ARCHITECTURE)
    assert len(text.split()) <= 700, "ARCHITECTURE.md exceeds the 700-word bound"
    assert len(text.splitlines()) <= 110, "ARCHITECTURE.md exceeds the 110-line bound"

def test_architecture_names_the_measured_model() -> None:
    assert "qwen2.5:1.5b" in _text(ARCHITECTURE)   # keep ARCHITECTURE.md:92 verbatim
```

**Edit rule:** replace/collapse node-table rows — **do not append**. The node table (`ARCHITECTURE.md:20-30`)
lists 9 nodes; refresh to the real `TRACER_NODES` (13) via a **compact combined row** (e.g. group the
terminals) rather than adding rows. Never trade away the `qwen2.5:1.5b` line.

---

### `EVALS.md` (MODIFY — **narrative only; numbers are generated**)

**Analog:** itself; the **sole writer of every number** is `scripts/emit_evals.py`. **Guards:**
`tests/test_docs_final.py:104-124`, `tests/test_eval_report.py`.

**Golden rule (D12-09):** edit only hand-written narrative; every generated cell/block must stay
`== emit_evals --check`:
```python
# tests/test_docs_final.py:104-111
result = subprocess.run([sys.executable, "scripts/emit_evals.py", "--report",
                         "evals/results/report.json", "--check"], ...)
assert result.returncode == 0
```

**The FIT-01 edit is §7 only** — `EVALS.md:184-192`. Replace the stale *"before Day 5"* line with a
**marked, attributed, empty slot**:
```markdown
## 7. Clinician validation (declared gap)

We do **not** have guaranteed access to a triage nurse or clinician during the build window
(see `docs/PROJECT.md` §3 and `docs/REQUIREMENTS.md` G-1). The expected colours in §4 are derived from the
published SATS rules, not from clinician adjudication. This is an honest limitation:

- Grounding: SATS Training Manual (EMSSA) and published SATS validation studies.
- **Clinician review: none obtained as of 2026-10-13.** If a triage nurse/clinician review is arranged,
  add their attributed quote here (name/role/date, with consent). Nothing is claimed until it is.
```

**Do not touch the generated §3/§4/§6.1 cells** — any number change must come from a report regeneration
(`scripts/emit_evals.py --write`), never hand-editing.

---

### `DESCRIPTION.md` (MODIFY — ±10% of 300 words)

**Analog:** itself. **Guard:** `tests/test_docs_final.py:69-74` (prose count is currently **302**; the bound
is 270–330).

```python
# tests/test_docs_final.py:50-54,69-74
def _prose_words(text: str) -> int:
    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = [line for line in without_comments.splitlines() if not line.lstrip().startswith("#")]
    return len("\n".join(lines).split())
# low = 270, high = 330
```

**Edit rule:** add a short v1.1 clause (`README.md:14-18` model+tools → add durable approve gate /
deferral-on-no-match / desk surface) while staying ≤ 330 prose words. Keep the `DESCRIPTION.md:2` comment.

---

### `STATUS.md` (MODIFY — unguarded, free to refresh)

**Analog:** itself. **No test reads it** (verified in RESEARCH §Blast radius) — sweep freely.

Stale rows to fix (RESEARCH §stale-claim inventory): `:35` model list, `:46` `697 words / 94 lines` →
**replace with a link, not a restated count**, `:55` "no desk surface + latency", `:84-85` G7, `:102-103`
UX table, `:116-122` U1/U2/U4/U7, `:149-153` SOTA table, `:214-221` test count (update after new guards).

**Link-don't-restate pattern** — `STATUS.md:7-8` already establishes it:
```markdown
> [`EVALS.md`](EVALS.md) is the current single source for every measured number.
```

---

### `docs/REQUIREMENTS.md` (MODIFY — unguarded)

**Analog:** itself. **No test reads it.** Stale rows (RESEARCH §inventory): `:89` JC-1 "5 reusable tool
contracts" → 7; `:101` DQ-2 "exposes 5 distinct tools" → 7; `:53` BW-3 under-exercised; `:91` JC-3
"no desk surface" (keep the clinician gap); `:127` ST-1 rehearsal pending → update after REV-01; `:159`
G-9 stays (human upload); `:161` G-11 → re-scope; `:8` bump the date.

Keep the whole-document **link** style — `docs/REQUIREMENTS.md:8-9`:
```markdown
> **Updated 2026-10-XX, post-build.** Full honest gap analysis … lives in [`../STATUS.md`](../STATUS.md).
```

---

### `docs/ROADMAP.md` (MODIFY — unguarded, packaging doc)

**Analog:** itself. Stale framing `:3-6,12-16` ("5 phases / twenty…" v1.0). Refresh to note the v1.1
milestone phases (6–12) while keeping it a **packaging** doc that links, not restates — `docs/ROADMAP.md:3-6`:
```markdown
> **Phase-level execution plan (authoritative): [`../.planning/ROADMAP.md`](../.planning/ROADMAP.md)** …
> This file covers **submission packaging only** … It deliberately does **not** repeat the phase plan (DRY).
```

---

### `docs/DECISIONS.md` (MODIFY, optional — one ADR row)

**Analog:** itself. **Only if the rehearsal surfaces a decision.** Follow the ADR-lite form — `docs/DECISIONS.md:9-15`:
```markdown
### D<n> — <decision>
**Decision:** …
**Why:** …
**Consequence:** …
```

---

### `tests/test_docs_final.py` (MODIFY — only if a guard's expectation legitimately changes)

**Analog:** itself. Prefer **not** to touch it. A legitimate change is, e.g., a stale framing tuple that a
v1.1 correction now contradicts — otherwise leave the guard as the immutable contract. Only adjust
`STALE_STATUS_ROWS`/`STALE_EVALS_FRAMING` (`tests/test_docs_final.py:35-42`) if a corrected doc would
otherwise fail, and never relax a bound (700 words / 110 lines / 270–330 prose).

---

## Shared Patterns

### Runbook-drift guard (fenced block → public `main` + spied seams)
**Sources:** `tests/test_desk_runbook.py:39-76`, `tests/test_readme_runbook.py:38-94`,
`tests/test_demo_runbook.py:43-62`
**Apply to:** the NEW `tests/test_review_runbook.py`; any doc that documents a CLI command.

Convention: `_FENCE_RE` extracts fenced blocks → `_INVOCATION_RE` captures the argv → `shlex.split` →
`assert main(argv) == 0` with every side-effect seam spied (`run_demo` async, `serve` sync, `run_eval` async
NEW). The public `main` is the source of truth (`src/triagedesk/cli.py:156`).

### The ONE data loader seam (hermetic tests)
**Source:** `src/triagedesk/core/rules.py:25,119-135`
**Apply to:** `tests/test_data_extension.py` and any test that must vary the substrate.
```python
monkeypatch.setattr(rules, "DISCRIMINATORS_PATH", tmp_path / "sats_discriminators.yaml")
rules.get_discriminators.cache_clear()
```

### Link-don't-restate (DRY — CONVENTIONS §1)
**Sources:** `docs/CONVENTIONS.md:8-24`; `README.md:70-75`; `STATUS.md:7-8`; `docs/DEMO.md:9-11`
**Apply to:** all seven refreshed docs. `EVALS.md` is the generator projection; every other doc **links** to
it and never restates a number.

### Honest re-declaration / flag-don't-claim
**Sources:** `docs/DEMO.md:3-5` (`human` / `screen recording` / `unedited`); `docs/REQUIREMENTS.md:159`
(G-9 human upload); `EVALS.md:184-192` (§7 declared gap)
**Apply to:** `docs/REVIEW.md`, `docs/DEMO.md`, `README.md`, `EVALS.md` §7. A human step is marked
`human_needed`; nothing is invented.

### Doc guards (the immutable contracts)
**Source:** `tests/test_docs_final.py`
| Guard | Constraint | Location |
|-------|-----------|----------|
| `test_architecture_is_one_page` | ≤ 700 words **AND** ≤ 110 lines (measured 698/94) | `:57-61` |
| `test_architecture_names_the_measured_model` | `qwen2.5:1.5b` present | `:64-67` |
| `test_description_is_about_300_words` | 270–330 prose words (measured 302) | `:69-74` |
| `test_readme_has_the_one_command_quickstart` | `uv run triagedesk demo` present, no `uv sync --locked` | `:77-87` |
| `test_readme_has_no_stale_prebuild_status_rows` | no `Not built`/`Not recorded`/`pre-build` | `:90-94` |
| `test_readme_points_at_the_declared_failure` | `EVALS.md` + `E-09` present | `:97-101` |
| `test_evals_is_a_projection_of_the_report` | `emit_evals --check` exits 0 | `:104-111` |
| `test_evals_header_is_finalised_not_prebuild` | no stale EVALS framing; "measured" present | `:114-119` |
| `test_evals_shows_the_declared_failure` | `E-09` present | `:122-124` |

---

## No Analog Found

None. Every file in Phase 12 is either an existing doc (its own analog) or a new guard/test with a
direct in-repo analog (existing runbook guards / the conftest seam). The **NEW** `evals.runner.run_eval`
**spy seam** is the one genuinely new guard element — but its *pattern* is the established
`monkeypatch.setattr(module, "attr", spy)` idiom (`tests/test_readme_runbook.py:84-85`).

---

## Metadata

**Analog search scope:** repo root docs (`README.md`, `ARCHITECTURE.md`, `EVALS.md`, `DESCRIPTION.md`,
`STATUS.md`), `docs/`, `tests/`, `src/triagedesk/{cli.py,core/{rules,matcher,scorer,schema}.py}`,
`scripts/`, `demo/`, `data/`. All analogs verified git-tracked (`git ls-files` — 28/28 tracked; no
gitignored-mirror paths emitted).
**Files scanned:** ~28 reads/greps this session.
**Pattern extraction date:** 2026-10-13
**Baseline context (from RESEARCH, not re-measured here):** 444 tests pass; ARCHITECTURE 698/700 words
/94 lines; DESCRIPTION 302 prose words; demo video 32.88 s (unhosted).

## PATTERN MAPPING COMPLETE
