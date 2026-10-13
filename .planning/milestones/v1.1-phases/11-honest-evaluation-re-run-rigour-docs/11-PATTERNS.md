# Phase 11: Honest Evaluation Re-run & Rigour Docs - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 9 (5 modify-source/config, 2 regenerate, 4 new/updated tests)
**Analogs found:** 9 / 9 (every target has a tracked in-repo analog)

> **IRON-CLAD (DRY + SOLID, `docs/CONVENTIONS.md`):** the ONE schema module, the ONE generator,
> the ONE report. `EVALS.md` is a *projection* of `report.json`; no figure is restated anywhere
> else; no expectation/threshold/golden value is edited to make a case pass (D11-02), except the
> owner-confirmed **D11-14** fixture-note repair. No literal discriminator alias (D11-02).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/triagedesk/core/schema.py` (add `Field(description=…)` on `CaseInput.age_years`) | model (schema) | transform (contract) | the same file's existing `Field(...)` declarations (lines 36-47) | exact (same file) |
| `evals/cases/E-07.yaml` (repair note to include `temperature 36.8`) | test fixture (data) | transform (declared input) | `evals/cases/E-02.yaml` (note states temp ↔ golden declares it) + `evals/cases/E-05.yaml` (note omits temp ↔ golden omits it) | exact (fixture-consistency pattern) |
| `evals/results/report.json` + `EVALS.md` (REGENERATED, never hand-edited) | config / published artefact | transform (projection) | the pipeline itself: `scripts/emit_evals.py --write` | exact |
| `scripts/emit_evals.py` (add §4 row-set reconciliation guard; add H-01/H-02 template rows) | utility (script) | transform | its own `validate_report` + `--check` (lines 294-347) and `_render_case_table` (176-200) | exact (same file) |
| `README.md` (literal one-command quickstart) | doc | request-response (documented invocation) | `docs/DESK.md` "One-time setup"/"Start the desk" + `docs/DEMO.md` "The one-command path" | exact (literal-command style) |
| `tests/test_docs_final.py` (drop the `uv sync --locked` requirement) | test (doc guard) | transform | itself + the CLI-driving pattern in `tests/test_demo_runbook.py` | exact |
| `docs/DECISIONS.md` (ADR row: extraction fix + E-07 fixture repair) | doc (ADR-lite) | transform | its own recent rows D19–D23 | exact |
| `src/triagedesk/llm/prompts.py` (OPTIONAL — research says the schema description alone is the fix) | config (prompt) | transform | `EXTRACTION_PROMPT` (lines 10-29) | role-match (likely untouched) |
| NEW/updated tests (E-04 real outcome, E-07 repaired-note outcome, count reconciliation, README one-command guard) | test | transform / request-response | `tests/test_eval_honest_terminal.py` + `tests/test_eval_suite.py` + `tests/test_eval_report.py` + `tests/test_demo_runbook.py` | exact |

---

## Pattern Assignments

### `src/triagedesk/core/schema.py` (model, transform) — the E-04 fix

**Analog:** the same file's existing `Field(...)` declarations (exact, same model).

The `Field(...)` style is already uniform across `CaseInput`; the fix adds a `description=` to one
field. The description enters **both** the prompt text and Ollama's `format=` grammar because
`llm/client.extract()` sends `ExtractionResult.model_json_schema()` as both (see Pattern 1 in
`11-RESEARCH.md`).

**Existing field style to match** (lines 36-47):
```python
    age_years: int | None = Field(default=None, ge=0, le=130)
    # A months-expressed or ambiguous age is representable so the scorer can fail
    # closed (Roadmap SC2): only an unambiguous adult-year integer may be scored.
    age_months: int | None = Field(default=None, ge=0, le=1560)
    age_ambiguous: bool = False
    height_cm: float | None = Field(default=None, ge=30.0, le=260.0)
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    heart_rate: int | None = Field(default=None, ge=0, le=350)
    systolic_bp: int | None = Field(default=None, ge=0, le=400)
    diastolic_bp: int | None = Field(default=None, ge=0, le=300)  # captured, not scored (§4.1)
    temperature_c: float | None = Field(default=None, ge=20.0, le=45.0)  # rejects °F magnitudes
    spo2: int | None = Field(default=None, ge=0, le=100)  # captured, not scored (§4.1)
```

**The whole change** (replace line 36) — the description must be **general** (no fixture number):
```python
    age_years: int | None = Field(
        default=None,
        ge=0,
        le=130,
        description=(
            "The patient's age in whole years, parsed from a stated age such as "
            "'a 74 year old patient'."
        ),
    )
```

**Contract the model fills** (lines 54-64) — unchanged; the planner must not touch it:
```python
class ExtractionResult(BaseModel):
    case: CaseInput
    matched_discriminator_ids: list[str] = Field(default_factory=list)
    no_discriminator_matched: bool = False  # coverage signal (v1 field)
```

**Purity guards this change MUST keep passing** (the schema is scanned as source):
- `tests/test_no_duplicated_sats.py::test_no_scoring_value_is_duplicated_under_src` scans every
  string literal under `src/**.py` (docstrings excluded) against the SATS substrate. A plain
  English `description=` sentence introduces **no** SATS value — but the plan must run this test
  after the edit (`docs/CONVENTIONS.md` §1, §3). Note the guard's own docstring (lines 9-20) already
  exempts `CaseInput`'s input-domain enums/ranges by design; the new description sits in the same
  exempted input-domain concern.
- `tests/test_graph_purity.py` — the model must not be on the score path; a schema description does
  not add a model call, so this holds unchanged.

**Error handling / validation:** the contract is already validated by
`ExtractionResult.model_validate_json` in `llm/client.py` (line 120). No change.

---

### `evals/cases/E-07.yaml` (test fixture, transform) — the D11-14 note repair

**Analog:** the fixture-consistency pattern across `evals/cases/*.yaml` — the free-text `note` must
state every vital the golden `case` declares.

**The inconsistency (current, lines 10-20):** the note omits temperature, the golden `case` declares
`temperature_c: 36.8`:
```yaml
note: >-
  55 year old man, walking, alert, no trauma. Serial vitals: systolic BP 118 -> 96,
  RR 16 -> 26, HR 80 -> 122. Complaint: looks worse than earlier.
case:
  age_years: 55
  ...
  systolic_bp: 96
  temperature_c: 36.8          # ← declared on the golden case, absent from the note
```

**The consistent pattern (analog A — `evals/cases/E-02.yaml` lines 8-18):** the note states the
temperature the golden case declares:
```yaml
note: >-
  45 year old man, walking, alert, no trauma. RR 24, HR 118, systolic BP 108,
  temperature 38.9. Complaint: cough, fast breathing.
case:
  ...
  temperature_c: 38.9
```

**The consistent pattern (analog B — `evals/cases/E-05.yaml` lines 8-18):** a genuinely-missing vital
is absent from **both** the note and the golden case (the honest missing-vital fixture):
```yaml
note: >-
  40 year old man, walking, alert, no trauma. RR 18, HR 82, systolic BP 120. No
  temperature recorded. Complaint: fever.
case:
  ...
  systolic_bp: 120
  # temperature_c deliberately absent — matches the note's "No temperature recorded"
```

**The repair (D11-14, owner-confirmed):** append the temperature the golden case already declares to
the E-07 `note` only — e.g. `... HR 80 -> 122. Temperature 36.8. Complaint: looks worse than
earlier.` The `case`/`previous_case` golden values and `expected: RECHECK` (line 33) are **unchanged**;
nothing is tuned green. The fixture-consistency rule the repair restores is the same rule E-02 and
E-05 already satisfy.

**Loader contract (unchanged):** `evals/case.py::CaseSpec` (lines 62-96) validates the fixture;
`note` is free text, `case`/`previous_case` are `CaseInput`, `expected` is validated against the
loaded substrate. The repair touches `note` only.

---

### `evals/results/report.json` + `EVALS.md` (config, projection) — REGENERATED, never hand-edited

**Analog:** the pipeline itself — the ONE generator, `scripts/emit_evals.py`.

**Do NOT hand-edit either file** (instant-disqualifier risk; digest stops recomputing). The exact
two-step regeneration (from `11-RESEARCH.md` "Code Examples"):
```bash
uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json
uv run python scripts/emit_evals.py --write
uv run python scripts/emit_evals.py --check     # must exit 0
```

**What the generator rewrites** (lines 277-291) — only result cells + the generated blocks; narrative
preserved verbatim:
```python
def render_evals(template: str, report: Report) -> str:
    analysis = analyse(report)
    lines = template.splitlines()
    lines = _render_metrics_table(lines, report, analysis)
    lines = _render_source_block(lines, report)
    lines = _render_case_table(lines, report)
    lines = _render_invariant_table(lines, report)
    lines = _render_deferral_block(lines, report, analysis)
    return "\n".join(lines) + "\n"
```

**The `--check` drift gate** (lines 329-338) — the test `test_evals_is_a_projection_of_the_report`
drives this and asserts exit 0:
```python
    if args.check:
        if generated != current:
            print(f"{args.evals} is out of date; re-run with --write ...", file=sys.stderr)
            return 1
        print(f"{args.evals} is up to date (report {report.report_digest[:16]})")
        return 0
```

**`mode: real` provenance** (the strongest evidence, D11-08) — the generated source block reads it
straight from the report (`_render_source_block`, lines 222-229):
```python
    body = [
        _BEGIN,
        f"> **Measured source:** `evals/results/report.json` · mode `{report.mode}` · "
        f"`report_digest: {report.report_digest}` · {report.runs} runs/case.",
        _END,
    ]
```

---

### `scripts/emit_evals.py` (utility, transform) — the §4 reconciliation guard + H-01/H-02 rows

**Analog:** its own `validate_report` + `--check` and `_render_case_table` (same file).

**The gap to close (D11-06):** `_render_case_table` only fills cells for rows **already present** in
the template — it never adds rows nor asserts coverage (lines 185-199):
```python
def _render_case_table(lines: list[str], report: Report) -> list[str]:
    """Fill the §4 per-case ``Runs (3×)`` and ``Result`` cells from the report."""
    start = _find_table(lines, ["#", "Case"])
    if start is None:
        return lines
    end = _table_end(lines, start)
    header = _split_row(lines[start])
    runs_index = header.index("Runs (3×)")
    result_index = header.index("Result")
    by_id = {case.case_id: case for case in report.cases}

    rows = [_render_row(header), lines[start + 1]]
    for line in lines[start + 2 : end]:
        cells = _pad(_split_row(line), len(header))
        case = by_id.get(cells[0])          # ← rows absent from the template are silently omitted
        if case is not None:
            cells[runs_index] = str(report.runs)
            ...
```

**The guard pattern to follow** — mirror the fail-closed `validate_report` style (raise → `--check`
exits non-zero) using the existing `_find_table`/`_table_end`/`_split_row` helpers:
```python
def _assert_case_table_covers_report(lines: list[str], report: Report) -> None:
    """Every report case must have a §4 row (D11-06: the report's own case set is the source)."""
    start = _find_table(lines, ["#", "Case"])
    if start is None:
        raise ValueError("EVALS.md is missing the §4 case table")
    end = _table_end(lines, start)
    row_ids = {
        _split_row(line)[0]
        for line in lines[start + 2 : end]
        if line.strip().startswith("|")
    }
    missing = {case.case_id for case in report.cases} - row_ids
    if missing:
        raise ValueError(f"EVALS.md §4 is missing rows for report cases: {sorted(missing)}")
```
Call it inside `render_evals` (or `validate_report`) so `--check` fails closed — the same posture as
`validate_report` (lines 294-300):
```python
def validate_report(report: Report) -> None:
    """Refuse a report whose ``report_digest`` does not recompute (T-04-18)."""
    if report.report_digest != compute_report_digest(report):
        raise ValueError(
            "report_digest does not recompute from the report's non-volatile content; "
            "refusing to publish a tampered report (D-08, T-04-18)"
        )
```

**The two H-01/H-02 template rows** are hand-written narrative rows (like E-01…E-14 in `EVALS.md`
lines 95-108) whose `Runs (3×)`/`Result` cells the generator then fills. §4's narrative table header
is `| # | Case | Synthetic input (vitals / complaint) | Expected | Pass criteria | Runs (3×) | Result |`.
*A fully-generated §4 table is not practical — the report carries no note/description/pass_criteria
(11-RESEARCH.md "Reconciliation options").*

**The digest gate stays authoritative** — `Report.report_digest` is sealed over the case set; a
hand-typed number anywhere still fails `--check`.

---

### `README.md` (doc, request-response) — the literal one-command quickstart

**Analog:** `docs/DESK.md` and `docs/DEMO.md`'s literal-command style.

**Current two-step (README lines 76-83) — to be replaced:**
```bash
uv sync --locked              # deterministic install from the committed uv.lock
uv run triagedesk demo        # the whole demo, offline, on the bundled synthetic fixture
```

**The literal one-command style to copy** (`docs/DEMO.md` "The one-command path", lines 27-39):
```bash
# Full sequence, one command, offline (the exact path CI runs):
uv run triagedesk demo
```

**`docs/DESK.md` "Start the desk" literal style** (lines 16-23) — the optional second command:
```bash
# The one command — serves the local page (loopback only, no external request):
uv run triagedesk desk
```

**The target (D11-09):** `uv run triagedesk demo` as the literal one-liner (`uv run` auto-syncs from
the committed lock, so no separate `uv sync` step); `uv run triagedesk desk` as the optional second
command. Do not restate `docs/DEMO.md`'s beats — link to it (DRY; the README already does this at
lines 88-89).

---

### `tests/test_docs_final.py` (test, transform) — drop the two-step-install requirement

**Analog:** itself + the CLI-driving runbook pattern.

**The exact assertion that currently REQUIRES the two-step (lines 77-81) — must change:**
```python
def test_readme_has_the_one_command_quickstart() -> None:
    """README.md carries the REAL one-command quickstart (D-06)."""
    text = _text(README)
    assert "uv sync --locked" in text
    assert "uv run triagedesk demo" in text
```

**The change (from `11-RESEARCH.md` Code Examples):**
```python
def test_readme_has_the_one_command_quickstart() -> None:
    """README.md carries the literal one-command quickstart; no separate install step (D11-09)."""
    text = _text(README)
    assert "uv run triagedesk demo" in text
    # `uv run` auto-syncs from the committed lock — the two-step install is gone (D11-09).
    assert "uv sync --locked" not in text
```

**Stronger alternative — reuse the CLI-driving pattern** (`tests/test_demo_runbook.py` lines 42-77),
which proves the documented invocation against the shipped `triagedesk.cli.main`:
```python
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INVOCATION_RE = re.compile(r"uv run triagedesk (demo[^\n`]*)")

def _documented_invocations(text: str) -> list[list[str]]:
    fenced = "\n".join(_FENCE_RE.findall(text))
    return [shlex.split(match) for match in _INVOCATION_RE.findall(fenced)]
```
`test_demo_runbook.py::test_runbook_documents_the_bare_one_command_path` (lines 75-77) is the literal
"one command present" check the README guard should mirror:
```python
def test_runbook_documents_the_bare_one_command_path() -> None:
    """The runbook documents the bare one-command path a stranger runs."""
    assert "uv run triagedesk demo" in _runbook_text()
```
*The existing README guard is the weaker "string present" pattern (11-RESEARCH.md Pattern 3); the
planner may keep it simple or upgrade to the CLI-driving pattern — either is D11-10-compliant.*

**Blast radius:** the suite baseline is **424 passing**; this edit must not drop it (11-RESEARCH.md
Pitfall 5). The other guards in this file (`test_evals_is_a_projection_of_the_report` lines 98-105)
are unaffected and keep enforcing the projection.

---

### `docs/DECISIONS.md` (doc, ADR-lite) — the extraction-fix decision row

**Analog:** the file's own recent ADR-lite rows D19–D23 (lines 149-253).

**The row shape to copy** — each row is `### D<n> — <title>` then `**Decision:**` · `**Why:**` ·
`**Consequence:**` (see D20 lines 176-187):
```markdown
### D20 — Asymmetric-cost deferral threshold for the coverage signal
**Decision:** the deterministic coverage/deferral signal (`core/confidence.assess`) answers a case only when
at least `DEFERRAL_MIN_SATISFIED_COMPONENTS` of its four components ... are satisfied; a `no_match`
case is deferred unconditionally.
**Why:** the two costs are **asymmetric** ...
**Consequence:** the signal can only ever make the system *more* cautious ...
```

**The new row must record (D11-01/D11-14):** the E-04 fix is a `Field(description=…)` on
`CaseInput.age_years` (a stronger structured-output contract at the model boundary, measured 14/14),
and the E-07 fixture note repair is a **test-data-inconsistency fix** that leaves `expected: RECHECK`
unchanged. The next free id is **D24** (D23 is the last row, line 229). Keep the "one source per
number" rule — do not restate the measured figures here; link `EVALS.md` (CONVENTIONS §1).

---

### `src/triagedesk/llm/prompts.py` (config, transform) — OPTIONAL, likely untouched

**Analog:** `EXTRACTION_PROMPT` (lines 10-29). **Research says the schema `description` alone is the
fix** — the prompt-only attempts were fragile and one shaded into tuning-to-the-test (11-RESEARCH.md
Pitfall 3 / "Anti-Patterns"). The prompt already carries the no-guess rule:
```python
- Extract only what the note states. If a vital is not present, use null. NEVER guess, default or impute a value.
```
**Recommendation for the planner:** do **not** edit the prompt. If a prompt example is ever added, it
must use **different** numbers than any fixture (D11-02). Treat this file as read-only unless a plan
carries explicit measured evidence that the schema description is insufficient.

---

### NEW/updated tests

#### T1. E-04 real-mode outcome (schema-description contract + real run)

**Analog:** `tests/test_eval_honest_terminal.py` (single-case real/offline run) + `tests/test_eval_suite.py`.

**Single-case run pattern** (`test_eval_honest_terminal.py` lines 162-173):
```python
async def _run_case(tmp_path: Path, case_id: str, **kwargs: Any) -> tuple[int, Report]:
    """Run one case offline and return (exit code, parsed report)."""
    report_path = tmp_path / "report.json"
    code = await run_eval(
        cases_dir=CASES_DIR, runs=3, report_path=report_path,
        offline=True, case_filter=case_id, **kwargs,
    )
    return code, Report.model_validate_json(report_path.read_text(encoding="utf-8"))
```
**Assertion pattern** (lines 196-204) — assert the measured `outcomes`/`colours` equal the expectation:
```python
    _, report = await _run_case(tmp_path, "E-02")
    case = report.cases[0]
    assert case.delivered == [True, True, True]
    assert case.outcomes == ["ORANGE"] * 3
    assert case.passed is True
```
**Plus a contract-level unit guard** (no model call): assert the schema description reaches
`model_json_schema()`:
```python
def test_age_years_contract_description_is_present() -> None:
    """The E-04 fix: the age contract carries a general description the model receives (D11-01)."""
    props = CaseInput.model_json_schema()["properties"]
    assert props["age_years"].get("description"), "age_years has no schema description"
```
**Note the offline control** (D11-04): the offline E-04 already passes (golden case); the honest
proof is the **real** run (`offline=False`) over the local model — keep both.

#### T2. E-07 repaired-note outcome

**Analog:** `tests/test_eval_suite.py::test_terminal_outcomes_are_first_class_and_write_no_queue_row`
(lines 142-165) and the fixture-consistency guard `test_matcher_returns_no_match_for_e09_...`
(lines 125-136).

**Terminal-outcome assertion pattern** (lines 148-155):
```python
    assert _report_case(report, "E-05").outcomes == ["RECOVER"] * 3
    assert _report_case(report, "E-06").outcomes == ["ABSTAIN"] * 3
    assert _report_case(report, "E-07").outcomes == ["RECHECK"] * 3
    assert store.rows == [], "a recovery/abstention/recheck case wrote a queue row"
```
**Fixture-consistency guard pattern** — load via `load_cases(CASES_DIR)` and assert the repaired note
now states the temperature the golden case declares (the D11-14 invariant; general, not a number
alias):
```python
def test_e07_note_states_every_scored_vital_its_golden_case_declares() -> None:
    """D11-14: E-07's note and golden case agree (the fixture can produce its own golden case)."""
    case = next(c for c in load_cases(CASES_DIR) if c.id == "E-07")
    assert "temperature" in case.note.lower()
    assert case.case.temperature_c is not None
    assert case.expected == "RECHECK"   # the expectation is UNCHANGED
```
**Honest-outcome note (D11-03/D11-14):** after the note repair the real path *may* still RECOVER if
the serial-arrow parsing mis-reads the vitals (11-RESEARCH.md "E-07 finding"). Whatever the real run
measures is recorded honestly in `EVALS.md`; the test asserts the **fixture consistency**, and the
re-run's measured outcome is what the report shows. Do not assert a green that the model cannot
produce.

#### T3. Count reconciliation

**Analog:** `tests/test_eval_report.py` generator guards (lines 296-324) + `tests/test_docs_final.py::test_evals_is_a_projection_of_the_report` (lines 98-105).

**Idempotence + sole-source pattern** (`test_eval_report.py` lines 312-319):
```python
    first = _EMIT.render_evals(_TEMPLATE, sealed)
    second = _EMIT.render_evals(first, sealed)
    assert first == second, "the generator is not idempotent"
    assert _cell(first, "| E-01 ", -2) == "\u2705"
```
**Reconciliation assertion** — every report case has a §4 row (drives the new generator guard):
```python
def test_every_report_case_has_a_section_4_row() -> None:
    """D11-06: the §4 row set equals the report's case set (no 14-vs-16 drift)."""
    report = Report.model_validate_json(REPORT.read_text(encoding="utf-8"))
    lines = EVALS.read_text(encoding="utf-8").splitlines()
    # reuse the generator's own helpers so the guard cannot drift from the renderer
    start = _EMIT._find_table(lines, ["#", "Case"])
    end = _EMIT._table_end(lines, start)
    row_ids = {_EMIT._split_row(line)[0] for line in lines[start + 2 : end] if line.strip().startswith("|")}
    assert row_ids == {c.case_id for c in report.cases}
```
**Projection gate** (unchanged, `test_docs_final.py` lines 98-105) — `--check` exits 0 after `--write`:
```python
    result = subprocess.run(
        [sys.executable, str(EMIT_EVALS), "--report", str(REPORT), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
```

#### T4. README one-command guard

**Analog:** `tests/test_demo_runbook.py` (lines 42-77) and `tests/test_desk_runbook.py` (lines 36-51).

The update to `tests/test_docs_final.py::test_readme_has_the_one_command_quickstart` (above) is the
minimal guard; the CLI-driving upgrade reuses the fenced-block + invocation-regex pattern. Whichever
is chosen, the guard must (a) assert the literal `uv run triagedesk demo` and (b) assert the absence
of the separate install step (D11-09/D11-10).

---

## Shared Patterns

### One source per number (`docs/CONVENTIONS.md` §1)
**Source:** `scripts/emit_evals.py` is the ONE writer; `evals/results/report.json` is the sole source.
**Apply to:** `EVALS.md`, `README.md`, `docs/DECISIONS.md` — none may restate a figure; each links
the report / `EVALS.md`. `test_evals_is_a_projection_of_the_report` enforces it mechanically.

### Fail-closed guard (raise → non-zero exit)
**Source:** `scripts/emit_evals.py::validate_report` (lines 294-300) + `main --check` (lines 329-338).
**Apply to:** the new §4 row-set reconciliation guard — raise a `ValueError` so `--check` exits
non-zero, exactly as the digest mismatch does.

### Drift guard drives the shipped CLI
**Source:** `tests/test_demo_runbook.py` (lines 42-77) / `tests/test_desk_runbook.py` (lines 36-51).
**Apply to:** the README one-command guard — read fenced code blocks, extract the
`uv run triagedesk …` invocation, and assert it against the shipped `triagedesk.cli.main` (never a
private helper).

### Never hand-edit a published artefact
**Source:** the `report_digest` seal (`evals/report.py`) + `compute_report_digest` refusal.
**Apply to:** `report.json` and `EVALS.md` — regenerate only via the pipeline; a hand edit stops the
digest recomputing and `--check` fails.

### Fixture note ↔ golden-case consistency
**Source:** `evals/cases/E-02.yaml` (temp present in both) and `evals/cases/E-05.yaml` (temp absent
from both).
**Apply to:** the E-07 note repair (D11-14) — the note must state every scored vital the golden
`case` declares.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | None. Every target maps to a tracked in-repo analog. |

**Deliberately excluded (must NOT be modified — D11-02 / 11-RESEARCH.md anti-patterns):**
- `src/triagedesk/core/scorer.py`, `core/matcher.py`, `core/recheck.py`, `core/confidence.py` — the
  fix must make these *see* the facts, never change their arithmetic.
- `src/triagedesk/core/citations` helper / `@audited` interceptor — untouched.
- `evals/cases/E-04.yaml` and every other fixture's `case`/`expected` — no expectation/golden edit
  (the ONE narrow exception is the E-07 **note** repair, D11-14).

---

## Metadata

**Analog search scope:** `src/triagedesk/`, `evals/`, `scripts/`, `tests/`, `docs/`, repo root.
**Files scanned:** 22 read in full/targeted (`schema.py`, `prompts.py`, `client.py`, `emit_evals.py`,
`report.py`, `case.py`, `test_docs_final.py`, `test_demo_runbook.py`, `test_desk_runbook.py`,
`test_eval_suite.py`, `test_eval_report.py`, `test_eval_honest_terminal.py`,
`test_no_duplicated_sats.py`, `README.md`, `EVALS.md`, `docs/DECISIONS.md`, `docs/DEMO.md`,
`docs/DESK.md`, `evals/cases/E-02/E-04/E-05/E-07.yaml`, `report.json`, `AGENTS.md`,
`docs/CONVENTIONS.md`).
**Tracked-source gate (#3645):** every analog path verified with `git ls-files -- <path>` (non-empty
= tracked); no gitignored mirror paths emitted.
**Pattern extraction date:** 2026-10-13

## PATTERN MAPPING COMPLETE
