# Phase 8: Calibrated Confidence & Abstention - Research

**Researched:** 2026-10-12
**Domain:** Deterministic selective-prediction / abstention signal + offline calibration measurement
**Confidence:** HIGH on the codebase seams; MEDIUM on the calibration-measurement design (a genuinely under-specified small-sample question)

## Summary

Phase 8 adds a **deterministic coverage/deferral signal** to an otherwise-unchanged triage graph. It is
greenfield: `grep` confirms no `confidence`, `deferral`, `calibration`, or `assess_confidence` symbol
exists anywhere in `src/` or `tests/`. The signal is a pure function of three already-typed objects the
graph holds after `score` — `CaseInput`, `MatchResult` (as `state["matched_ids"]` + `state["no_match"]`),
and `PriorityResult` — and it reads the SATS bands only through the one loader (`core/rules.py`). It is
exposed as a 6th owned MCP tool and drives a new `assess` node whose routing can only reach `escalate` or
`request_missing_info`, both of which already have **no edge to `commit`** — so "never commit" is
structural, not conventional.

The single largest implementation hazard is **surface drift**: the owned-tool allowlist grows from five to
six, and two test-side tool factories (`tests/conftest.py::build_graph_tools` and
`evals/tools.py::build_tools`) feed `build_graph`, which asserts the allowlist. If those two factories are
not updated in the same wave as the allowlist, **every graph and eval test raises at composition** —
roughly the whole suite. The second hazard is that deferring the `no_match` class (E-09) is an intended
**behavioural change** to a measured case: E-09 currently scores GREEN and commits as the declared failure;
after Phase 8 it must be loudly deferred to a terminal, which moves it out of the under-triage direction
split and therefore changes the published `analysis` block in `report.json` and `EVALS.md` — both of which
must be regenerated (never hand-edited).

**Primary recommendation:** Implement four small, additive, one-owner changes in one wave — a new pure
`core/confidence.py` + a new `ConfidenceResult` in the ONE schema module, a new `assess_confidence` tool in
`mcp/server.py`, a new `assess` node + `route_after_assess` in the graph, and additive report/analysis
fields projected only through `scripts/emit_evals.py`. Update the two tool factories and the exact-set
allowlist test in the *same* wave. Treat the ECE/risk–coverage figures as a **declared small-sample
measure of the harness's coverage signal**, never a clinical probability, and never expose a scalar
confidence in the tool contract.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Confidence/deferral computation | Core (pure `core/confidence.py`) | — | Mirrors `core/scorer.py` purity; no model, MCP client, store, or I/O (D8-03). Reads only `core/schema.py` + `core/rules.py` data. |
| Signal contract | Core (`core/schema.py`) | — | The ONE schema module owns every typed contract (D8-02, D-14). |
| Tool exposure | MCP owned server (`mcp/server.py`) | Adapter (`mcp/adapter.py` unchanged) | A 6th `@server.tool()` joins the same `@audited` shape; discovery is unchanged (D8-05/07). |
| Routing decision | Graph composition (`graph/build.py` + `graph/nodes.py`) | State channel (`graph/state.py`) | Extend by a NEW node; nodes route, they do not compute (SOLID: S; D8-08). |
| Calibration measurement | Eval harness (`evals/analysis.py`) | Report contract (`evals/report.py`) | Offline, deterministic, over the already-computed per-case facts; never re-runs the graph. |
| Published figures | Generator (`scripts/emit_evals.py`) | `EVALS.md` (projection only) | Single-source rule (D8-14): no hand-typed number in any doc. |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D8-01:** The signal is computed from exactly four components: **vitals coverage**, **discriminator
  coverage**, the **override-vs-TEWS path**, and **TEWS distance from the band edge**. A deterministic
  function of the typed case, the `MatchResult` and the `PriorityResult` — never of a model probability,
  logprob, or token count.
- **D8-02:** The output contract is a typed model in the ONE schema module (`core/schema.py`): a
  `deferral` boolean, a small closed-set level, the per-component breakdown, and a human-readable reason.
  **No percentage** and nothing readable as a clinical probability.
- **D8-03:** The computation lives in a NEW pure `core/confidence.py`, mirroring `core/scorer.py`'s purity
  (no model, no MCP client, no I/O). `core/scorer.py` is not edited.
- **D8-04:** No percentage, no "87% sure" framing anywhere in the contract, the tool output, or the CLI.
- **D8-05:** A new owned MCP tool `assess_confidence`; `OWNED_TOOL_ALLOWLIST` grows from five to six in the
  SAME wave, and the allowlist assertion covers it.
- **D8-06:** The tool's input and output are typed contracts from the ONE schema module (the case/
  `CaseInput`, the `MatchResult`, the `PriorityResult` in; the confidence contract out) — no dict
  passthrough, no second schema.
- **D8-07:** The tool is **pure and side-effect-free**: no store, no queue row, no approval token. Still
  audited by the ONE `@audited` interceptor.
- **D8-08:** Wiring is a **NEW `assess` node** placed after `score` (SOLID: O). Routing after `assess`
  consults the signal, so a deferral can only route to `escalate` or `request_missing_info`.
- **D8-09:** The threshold is derived from a **stated asymmetric cost** (a missed emergency ≫ a needless
  deferral), recorded in `docs/DECISIONS.md` with the two costs named. A named constant derived from that
  rationale, never a value tuned to make a test green.
- **D8-10:** The **deferral rate is reported** by the offline analysis, next to the outcome breakdown.
- **D8-11:** `no_match` (`MatchResult.no_match`) **forces a deferral** regardless of the other components.
- **D8-12:** The signal can **never downgrade a scored colour** and never reach `commit`; proven by a test
  that a deferral on an otherwise-committing case ends at `escalate`/`request_missing_info` with no queue
  row and no commit.
- **D8-13:** Calibration is measured on a **declared held-out split**; the split is stated explicitly.
- **D8-14:** Numbers are emitted into `report.json` and projected into `EVALS.md` **only** by
  `scripts/emit_evals.py`. No hand-typed number in any doc.
- **D8-15:** ECE and risk–coverage are reported and explicitly declared a **small-sample** measure, with
  the sample size named.
- **D8-16:** The deferral rate is reported from `report.json`, not restated anywhere else.

### the agent's Discretion

- The exact component weights/decision procedure inside `core/confidence.py`, provided D8-01/D8-02 hold and
  the threshold is traceable to D8-09.
- The closed-set level vocabulary and the reason strings.
- Whether the `assess` node stores the signal in a new state channel (preferred) or re-derives it in routing.
- The exact ECE / risk–coverage binning for a 14-case sample, given the small-sample caveat must be explicit.
- The held-out split's exact composition, provided it is declared and not chosen after seeing the result.

### Deferred Ideas (OUT OF SCOPE)

- The desk-facing banner and card that render the signal (UX-01/UX-02) — Phase 10.
- A mandatory clarifying-question loop when no discriminator matches (DISC-01) — future requirements.
- Full calibration at larger sample size (CAL-02) — future requirements; this phase declares the limit.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-02 | Deterministic coverage/deferral signal (never a model probability, never a percentage as clinical risk), exposed by an `assess_confidence` tool, wired to routing so low confidence routes to escalate/request-missing-info and never `commit`, and never downgrades a scored colour. | Four-component signal definition (§Signal Components); 6th-tool addition sites (§Adding the Sixth Tool); minimal node/routing wiring with structurally-commitless terminals (§Routing Change); the one-way-safety proof tests (§Proving One-Way Safety). |

<user_constraints>

> **Note:** The `<user_constraints>` block above is reproduced from
> `08-CONTEXT.md` (USER DECISIONS D8-01…D8-16, the agent's Discretion, Deferred Ideas) and is binding on
> the planner. Scope research to these; do not explore alternatives to locked decisions.

</user_constraints>

## Signal Components — the four inputs, precisely

Every component below is a **deterministic read of an already-populated typed object**. None requires
re-deriving a colour. All four inputs are available in the graph state at the point the new `assess` node
runs (immediately after `score`, before `verify`).

State channels populated by the time `assess` runs (from `graph/state.py:36-45`):
`raw_note`, `case`, `matched_ids`, `no_match`, `priority`, `attempt`, `route`. Confirmed by reading the
`retrieve` and `score` node bodies in `graph/nodes.py`.

### (a) Vitals coverage — `PriorityResult.used_vitals` / `missing_vitals`

`[VERIFIED: src/triagedesk/core/schema.py:89-101]` — the exact field set:
```python
    colour: str | None = None
    tews: int | None = None
    target: str | None = None
    destination: str | None = None
    triggered_rules: list[TriggeredRule] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    matched_discriminator_ids: list[str] = Field(default_factory=list)
    missing_vitals: list[str] = Field(default_factory=list)
    used_vitals: list[str] = Field(default_factory=list)
    out_of_scope: bool = False
    abstained: bool = False
    reason: str | None = None
```

`used_vitals` and `missing_vitals` **partition** the scored TEWS parameter set. In
`score_priority`, the loop over `rules.parameters.items()` appends `name` to `missing` when the case
field is `None` and to `used` otherwise (`src/triagedesk/core/scorer.py:221-226`). The denominator is
therefore `len(get_tews().parameters)` — read from the data authority, never inlined. The signal is a
**count pair** (used vs total) plus the `missing_vitals` list; it is *not* a percentage field.

### (b) Discriminator coverage — `MatchResult.matched_ids` vs the closed set, and `no_match`

`[VERIFIED: src/triagedesk/core/schema.py:113-115]` — the exact field set:
```python
    matched_ids: list[str] = Field(default_factory=list)
    no_match: bool = False
    warning: str | None = None
```

The `retrieve` node stores these as `matched_ids` and `no_match` on the state
(`src/triagedesk/graph/nodes.py:175`): `return {"matched_ids": list(match.matched_ids), "no_match":
match.no_match}`. The closed-set denominator is `len(get_discriminators().discriminators)`. Per **D8-11**,
`no_match is True` forces a deferral regardless of every other component. The matcher sets `no_match=True`
with an empty id list and the declared warning when nothing matches
(`src/triagedesk/core/matcher.py:69-74`).

### (c) Override-vs-TEWS path — did a discriminator change the colour?

`[VERIFIED: src/triagedesk/core/scorer.py:242-255]` — the override block:
```python
    colour = _colour_for(rules, tews)
    override = _most_urgent_category(matched_discriminator_ids, rules)
    if override is not None:
        category_name, category = override
        urgency = _colour_urgency(rules)
        if urgency[category.colour] > urgency[colour]:
            colour = category.colour
            triggered.append(
                TriggeredRule(
                    rule_id=category_name,
                    detail=f"discriminator override: {category_name} -> {category.colour}",
                    points=0,
                    citation=format_citation(category.citation_ref, get_discriminators().citation),
                )
            )
```

The override rule is appended **only when the discriminator actually raised the colour** (the
`urgency[...] > urgency[...]` guard). The rule's `rule_id` is the discriminator **category name**
(`emergency` / `very_urgent` / `urgent`), which is disjoint from the TEWS parameter keys and from
`"tews_baseline"`. So the exact, DRY-safe signal is:

> `override_fired = any(rule.rule_id in get_discriminators().categories for rule in priority.triggered_rules)`

This reads the discriminator **data authority** (`categories` keys) and the already-produced
`triggered_rules` — it does **not** re-derive a colour, so it does not violate "the colour is produced in
exactly one place". *(Do NOT parse the human-readable `detail` string, and do NOT re-implement
total→colour mapping in `core/confidence.py` — see Pitfalls 2 and 3.)*

### (d) TEWS distance from the band edge — `PriorityResult.tews` vs `data/sats_tews.yaml`

`[VERIFIED: data/sats_tews.yaml:80-84]` — the bands (inclusive; `max` absent = open upper end):
```yaml
tews_to_colour:
  - {colour: GREEN, min: 0, max: 2}
  - {colour: YELLOW, min: 3, max: 4}
  - {colour: ORANGE, min: 5, max: 6}
  - {colour: RED, min: 7}
```

`TewsRules.tews_to_colour` is `list[ColourBand]` with `min: int` and `max: int | None`
(`src/triagedesk/core/rules.py:44-49,74`). The component finds the band containing the observed
`priority.tews` (inclusive `min ≤ tews ≤ max`, with a missing `max` treated as unbounded) and computes
`min(tews - band.min, band.max - tews)`. A small distance means the case sits **near a colour boundary**,
so a single measurement shift could flip the colour — i.e. low confidence. The band edges come from the
data; **no band number is inlined** (CONVENTIONS §1; `tests/test_no_duplicated_sats.py` scans `src/**.py`
literals against the data leaves — this guard passes provided the code reads the bands, not literals).

### Availability confirmation at `assess` (after `score`)

| Component | Reads | Available? | Why |
|-----------|-------|-----------|-----|
| (a) Vitals coverage | `state["priority"].used_vitals` / `.missing_vitals`; `get_tews().parameters` | ✅ | `score` writes `priority`; the parameter set is the data authority. |
| (b) Discriminator coverage | `state["matched_ids"]`, `state["no_match"]`; `get_discriminators().discriminators` | ✅ | `retrieve` writes both channels before `score`. |
| (c) Override-vs-TEWS | `state["priority"].triggered_rules`; `get_discriminators().categories` | ✅ | Populated by `score`. |
| (d) TEWS band distance | `state["priority"].tews`; `get_tews().tews_to_colour` | ✅ | Populated by `score`. |

**Out-of-scope / abstained cases never reach `assess`:** `route_after_score` already diverts
`out_of_scope` → `escalate` and `missing_vitals` → `request_missing_info` before the neutral branch
(`src/triagedesk/graph/build.py:127-140`). `assess` therefore only ever sees a scored (non-abstained)
priority with all four signals well-formed.

## Adding the Sixth Owned Tool — every site that must change in one wave

The tool is declared exactly like the other five: a `@server.tool()` / `@audited()` function in
`mcp/server.py` that is a thin, contract-typed adapter over the pure `core/confidence.py` function. Every
place a tool's existence is asserted or enumerated:

| # | Site | Kind | Breaks if unchanged? |
|---|------|------|----------------------|
| 1 | `src/triagedesk/mcp/server.py` | Declare `@server.tool() @audited() def assess_confidence(...)` | n/a (new) |
| 2 | `src/triagedesk/graph/build.py` `OWNED_TOOL_ALLOWLIST` (`:65-71`) | Add `"assess_confidence"` | n/a (new) |
| 3 | `src/triagedesk/evals/tools.py` `build_tools` (`:124-130`) | Add an `assess_confidence` callable | **YES — hard break** (see below) |
| 4 | `tests/conftest.py` `build_graph_tools` (`:200-206`) | Add an `assess_confidence` callable | **YES — hard break** |
| 5 | `tests/test_safety_spine.py::test_graph_startup_asserts_the_tool_allowlist` (`:190-196`) | Exact set equality on the allowlist | **YES — breaks** |
| 6 | `tests/test_mcp_server.py` (`:32-38`) | Superset check `names >= {5}` | No — but update the "five-tool" comment |
| 7 | `tests/test_mcp_tools.py` (`:179-184`) | Membership check on `commit_priority` | No |
| 8 | `tests/test_audit_chain.py::test_every_tool_call_appends_exactly_one_chained_record` (`:252-286`) | Manually calls the 5 tools and asserts their record list | No (the 6th is not invoked there) — add a new test for the 6th |

**Critical dependency — sites 3 and 4 are the whole-suite hazard.** `build_graph` begins with
`assert_tool_allowlist(tools.keys())` (`src/triagedesk/graph/build.py:198`), and
`assert_tool_allowlist` uses **set equality**:
`[VERIFIED: src/triagedesk/graph/build.py:74-89]`
```python
def assert_tool_allowlist(tool_names: Iterable[str]) -> None:
    ...
    discovered = set(tool_names)
    expected = set(OWNED_TOOL_ALLOWLIST)
    missing = expected - discovered
    unexpected = discovered - expected
    if missing or unexpected:
        raise RuntimeError(...)
```
`evals/tools.py::build_tools` and `tests/conftest.py::build_graph_tools` each return exactly the five
names. `evals/tools.py::build_tools` also feeds `durable.resume_thread` (`durable.py:239`) and
`demo/run.py` (`:177,:224`). So if the allowlist grows to six without updating **both** factories, every
graph/eval/demo/durable test raises `RuntimeError` at composition. Update sites 2, 3, 4, 5 in a single
commit/wave.

**Exact allowlist quote to update:** `[VERIFIED: src/triagedesk/graph/build.py:65-71]`
```python
OWNED_TOOL_ALLOWLIST: tuple[str, ...] = (
    "normalize_case",
    "match_discriminators",
    "score_priority",
    "raise_recheck_flag",
    "commit_priority",
)
```

**Tool body (D8-06/07):** take the typed inputs (the `CaseInput`, the `MatchResult`-equivalent —
`matched_ids` + `no_match` — and the `PriorityResult`), return the `ConfidenceResult`. No store access, no
queue, no token. It is wrapped by the same `@audited()` interceptor and therefore appends exactly one
chained audit record and emits one `tool` span (unchanged interceptor behaviour, D-18).

## Routing Change — minimal SRP-respecting wiring

Current composition (`src/triagedesk/graph/build.py:204-232`): `START → ingest → normalize →
(retrieve → score | escalate) → (score: escalate | request_missing_info | verify) → (verify: recheck |
score | END) → recheck → approval_gate → commit → handover → END`, with
`request_missing_info → END` and `escalate → END`.

`[VERIFIED: src/triagedesk/graph/build.py:127-140]` — the existing post-score router:
```python
def route_after_score(state: TriageState) -> str:
    priority = state.get("priority")
    if priority is not None and priority.out_of_scope:
        return "escalate"
    if priority is not None and priority.missing_vitals:
        return "request_missing_info"
    return "verify"
```

**Recommended minimal change** (keeps `route_after_score`'s *decisions* untouched; only re-points its
neutral target):

1. Add `"assess"` to `TRACER_NODES` (superset-checked — see §Blast Radius) and a `_make_assess` factory to
   `make_nodes` in `graph/nodes.py`.
2. Change the conditional-edge mapping on `score` so its neutral target is `assess`, not `verify`
   (`{"escalate": "escalate", "request_missing_info": "request_missing_info", "verify": "assess"}`).
3. Add `route_after_assess(state) -> str`: read the new `confidence` state channel; if
   `confidence.deferral` route to `escalate` or `request_missing_info` (the deferral reason decides which);
   otherwise route to `verify`.
4. Register `graph.add_conditional_edges("assess", route_after_assess, {"escalate": "escalate",
   "request_missing_info": "request_missing_info", "verify": "verify"})`.

**"Never commit" is structural.** `[VERIFIED: src/triagedesk/graph/build.py:230-231]`
```python
    graph.add_edge("request_missing_info", END)
    graph.add_edge("escalate", END)
```
Neither terminal has any edge to `commit`; `commit` is reachable only via `approval_gate`, which is
reachable only via `recheck`, which is reachable only via `verify`. So a deferral that routes to either
terminal cannot reach `commit` in the compiled graph — the property is enforced by topology, not by a
convention the code must remember (D8-12). `route_after_verify` (`:143-154`) is unaffected.

**"Never downgrade a colour" is structural.** `score_priority` takes **only**
`(case, matched_discriminator_ids)` (`src/triagedesk/core/scorer.py:194-197`) — there is no confidence
input. `assess` runs after `score` and only writes a new channel plus routes; it does not mutate
`priority`. The scored colour therefore survives on the `priority` object unchanged on every path (a
deferral path simply ends at a terminal that produces no handover card, so no colour reaches the queue).

## Offline Calibration Measurement

### The four units to extend, additively

| Concern | Owner | Additive change |
|---------|-------|-----------------|
| Per-case deferral facts | `evals/report.py::ReportCase` (`:65-85`) | Add e.g. `confidence_levels: list[str]`, `deferrals: list[bool]` (defaulted) |
| Aggregate deferral + calibration | `evals/report.py::Analysis` (`:114-157`) | Add `deferral_rate`, `deferral_count`, `deferral_cases`, and a `calibration` sub-block |
| Sealing | `evals/report.py::_digest_payload` (`:227-260`) | Extend the explicit payload if the new fields must be tamper-sealed (see below) |
| Projection | `scripts/emit_evals.py` (`:84-105`) | Add a `_measured_metrics` entry per new §3 row |

`ReportCase` and `Report` use Pydantic defaults throughout, so **adding defaulted fields is additive** and
does not break `tests/test_eval_report.py`, which constructs these models by explicit keyword
(`test_eval_report.py:103-138`).

**Digest decision (must be deliberate).** `_digest_payload` enumerates an explicit key list; a new
`ReportCase`/`Report` field is **NOT** sealed automatically. The deferral decision is deterministic (a pure
function of the case), so sealing it strengthens tamper-detection and is recommended: add the new per-case
deferral fields to `_digest_payload`. The **calibration aggregates** (ECE, risk–coverage points) belong in
`Analysis`, which is deliberately **excluded** from the digest (`src/triagedesk/evals/report.py:160-179`)
exactly like the volatile latency/token figures — keep them there.

### Declared held-out split

The suite already carries a declared split: `[VERIFIED: evals/cases/H-01.yaml, H-02.yaml]` have
`held_out: true`; all of `E-01…E-14` have `held_out: false`. `test_eval_suite.py:79-82` already asserts
"at least two held-out cases" and `:106-115` asserts every held-out case passes. So the natural declared
split is:

- **Calibration split:** `E-01…E-14` (n=14) — where the D8-09 threshold is justified.
- **Held-out split:** `H-01`, `H-02` (n=2) — bounds the declared failure, never iterated against.

Because the held-out split is only 2 cases, report calibration **with the sample size named** and the
explicit small-sample caveat (D8-15); a 2-case ECE is a declared bound, not a validated figure. *(This
composition is the agent's discretion per D8-13; see Open Question 1 for the honest-reporting tension.)*

### Computing ECE and risk–coverage for n≈14

- **Risk–coverage (the defensible measure):** rank `report.cases` by the deterministic ordinal signal
  (e.g. number of satisfied components, or the normalized band-distance), then sweep the abstention
  threshold to plot **coverage** (fraction not deferred) against **risk** (error rate among non-deferred,
  using the existing `outcome == expected` fact the report already stores). This needs only a *ranking*,
  not a probability — it is fully compatible with "never a model probability".
- **ECE (the tension):** ECE classically needs a predicted probability. Since no probability may be
  exposed or presented as clinical risk (D8-02/04), compute ECE **only inside the offline analyser** over
  an **internal ordinal scalar** derived deterministically from the four components (never emitted by the
  tool, never in `core/schema.py`), binned coarsely (e.g. 4 bins for n≈14), against the empirical
  correctness the harness already computes. Report ECE with `n` named and the small-sample declaration;
  never present it as a validated calibrated probability. *(This separation — internal scalar for
  measurement only, no scalar in the contract — is the design point that keeps D8-04 intact.)*

### Projection into EVALS.md (never hand-edit)

`[VERIFIED: scripts/emit_evals.py:84-105]` `_measured_metrics` maps §3 metric-row labels to generated
strings, and `_render_metrics_table` refreshes the `Measured` column (`:108-127`). The **deferral rate is
an aggregate** (D8-10/D8-16), so it fits the §3 table next to `Error direction`. Add a hand-written
**row** (label + definition only, measured cell `TBD`) to the `EVALS.md` §3 table, then add the
corresponding `_measured_metrics` key. Adding a *row label/definition* is structural (allowed); adding a
*number* is not (D8-14). `test_docs_final.py::test_evals_is_a_projection_of_the_report` (`:98-105`) runs
`emit_evals.py --check` and asserts the committed `EVALS.md` equals the generator's output — so any report
change forces a **`--write` regeneration** of `EVALS.md` (never a manual edit).

### The E-09 behavioural change (must be regenerated, not tuned)

E-09's complaint matches nothing (`test_eval_suite.py:125-127` asserts `no_match is True`). Under D8-11 the
`assess` node now **forces a deferral** for it. Effect: E-09's measured outcome changes from a wrong GREEN
(an under-triage) to a terminal (`ABSTAIN`/`RECOVER`). In `analyse`
(`src/triagedesk/evals/analysis.py:113-139`), a **terminal outcome on a colour-expected case is excluded
from the direction split and (since expected ORANGE is a colour) is not counted as a terminal miss** — so
E-09 leaves `under_triage`, changing the published direction split (currently "under-triage 3"). E-09
remains `passed=False` (a terminal ≠ expected ORANGE), so it stays the sole declared failure
(`test_eval_suite.py:88-100` holds). **The committed `evals/results/report.json` and `EVALS.md` must be
regenerated** — the plan cannot hand-edit either, and must not tune the fixture to keep the old numbers.

## Proving the One-Way Safety Property (the concrete tests)

1. **Deferral on an otherwise-committing case ends at a terminal, with zero writes.** Drive a case that
   normally commits (e.g. the `COMPLETE_CASE` in `tests/conftest.py:120-130`) but with a forced deferral
   (a `no_match` case, or a component-threshold case), through `build_graph(build_graph_tools(...,
   writes=writes, store=memory_store))`; assert the final state has `escalation` or `recovery` set, the
   interrupt never fired (`"commit_priority" not in [name for name, _ in calls]`), `memory_store.rows == []`,
   and zero `commit_priority` audit records. This mirrors the existing `test_graph_recovery.py` pattern
   (`:62,:84,:87-99`).
2. **`no_match` is never high-confidence.** Assert `confidence.deferral is True` for any state with
   `no_match is True`, and prove it end-to-end by running E-09 (`build_tools` / offline) and asserting a
   terminal outcome with no queue row.
3. **No path lets the signal downgrade a colour.** (a) An AST/signature guard: `core/scorer.py` imports no
   `core/confidence` symbol and `score_priority`'s parameters contain no confidence argument
   (`src/triagedesk/core/scorer.py:194-197`). (b) `assess` never assigns to `priority`.
4. **"Never a percentage" is unrepresentable, not just discouraged.** Assert the `ConfidenceResult`
   contract has no float/percentage field (only a bool `deferral`, a closed-set `Literal` level, a
   component breakdown of counts/booleans, and a `reason: str`), and assert the tool's serialised output
   contains no `%` or "probability" token.
5. **`assess_confidence` is pure/side-effect-free.** Call it directly and assert `memory_store.rows == []`
   and no `commit_priority` audit record; only the one `assess_confidence` audit record is appended.

## Blast Radius — what breaks when each surface changes

| Change | Test / module | Effect |
|--------|---------------|--------|
| **Allowlist 5→6** | `tests/conftest.py::build_graph_tools`, `evals/tools.py::build_tools` | **Must add the new callable** or every graph/eval/demo/durable test raises `RuntimeError` (set-equality assert). |
| Allowlist 5→6 | `tests/test_safety_spine.py:190-196` | Exact-set assertion — **update to 6 names**. |
| Allowlist 5→6 | `tests/test_mcp_server.py:32-38` | Superset `>=` — **no break**; update the "five-tool" comment for accuracy. |
| Allowlist 5→6 | `tests/test_mcp_tools.py:179-184`, `tests/test_matcher.py:104-119`, `tests/test_recheck.py:86-99` | Membership checks — **no break**. |
| **Node added** | `tests/test_graph_tracer.py:42-48` | **Superset check** (`missing = expected - node_names`) → **adding a node is SAFE** (confirms the prompt's question). |
| Node added | `tests/test_observability.py:279-296` | Asserts each node emits **exactly one** span (uniqueness), not an exact node count → **no break**; the new node adds one more `node` span and one `tool` span. |
| Node added | `tests/test_safety_spine.py:217-232`, `tests/test_graph_purity.py` | AST guards scan `graph/` for network/credential/model imports → the new node must not read env or import `llm`/model (it must not). |
| **State channel added** | `graph/build.py::_allowed_msgpack_modules` (`:303-316`) | Derives BaseModel classes from `core/schema.py` → the new `ConfidenceResult` is auto-included **provided it is declared with `__module__ == core.schema`**. |
| State channel / card | `tests/test_safety_spine.py:44-59` `_EXPECTED_CARD_FIELDS` | Exact card field set — **breaks if `HandoverCard` gains a confidence field**. Recommendation: do **not** add it to the card (that is Phase 10's banner job), so this stays green. |
| **Report contract fields** | `tests/test_eval_report.py`, `tests/test_eval_honest_terminal.py`, `tests/test_eval_tracer.py` | Additive defaulted fields → **no break** (models built by keyword; digests recomputed, never hard-coded). |
| Report regenerated | `evals/results/report.json`, `EVALS.md` | Must be regenerated via the harness + `emit_evals.py --write`; `test_docs_final.py:98-105` (`--check`) fails if not. |
| E-09 deferred | `evals/results/report.json` `analysis.under_triage*`, `EVALS.md` §3 | Direction split changes; regenerate and re-read honestly (do not tune the fixture). |
| New §3 metric row | `EVALS.md` template + `_measured_metrics` | Row label/definition is hand-written; the measured value is generated. `render_evals` idempotency (`test_eval_report.py:238-266`) must hold. |

## Common Pitfalls

### Pitfall 1: Updating the allowlist without the two tool factories
**What goes wrong:** `build_graph` raises `RuntimeError: owned tool surface drifted` in nearly every test.
**Why:** `assert_tool_allowlist` is set-equality, and both `evals/tools.py::build_tools` (also used by
`durable` and `demo`) and `tests/conftest.py::build_graph_tools` return exactly five names.
**How to avoid:** change the allowlist, `mcp/server.py`, `evals/tools.py`, `tests/conftest.py`, and
`tests/test_safety_spine.py` in one wave/commit.
**Warning signs:** a suite-wide `RuntimeError` at `build_graph`, not a localised failure.

### Pitfall 2: Re-deriving the TEWS colour in `core/confidence.py`
**What goes wrong:** the `override-vs-TEWS` component is implemented by mapping `tews`→colour again, or by
parsing the `"discriminator override:"` detail string.
**Why:** both duplicate the ONE colour production (`core/scorer._colour_for`) or couple to a human string.
**How to avoid:** derive the override signal from `rule.rule_id in get_discriminators().categories`, and
derive the band distance from `get_tews().tews_to_colour` bounds — never produce a colour.
**Warning signs:** a second total→colour mapping, or a `.startswith("discriminator override")` check.

### Pitfall 3: Inlining a band edge or the magenta threshold
**What goes wrong:** a literal `7`/`5`/`2` band boundary or a bare threshold constant under `src/`.
**Why:** CONVENTIONS §1 + `tests/test_no_duplicated_sats.py` scan `src/**.py` literals against the data
leaves (discriminating numbers: `≥10` or non-integer; string leaves exactly). Band edges `0-6` are
single-digit and slip the numeric scan, but the **string** leaves (colours `GREEN`/`YELLOW`/…,
`tews_baseline`) are caught exactly.
**How to avoid:** read bands through `get_tews()`; derive the asymmetric-cost threshold as a **named
constant with a `docs/DECISIONS.md` rationale** (D8-09), not a literal sprinkled at call sites.
**Warning signs:** `test_no_duplicated_sats.py` red, or a bare `0.7`-style threshold appearing twice.

### Pitfall 4: Exposing a scalar confidence (a percentage in disguise)
**What goes wrong:** a `score: float` or `probability: float` field appears on the contract or the tool
output, or the CLI prints "87% confident".
**Why:** ECE naturally wants a probability; the temptation is to surface the internal scalar.
**How to avoid:** keep the contract to `deferral: bool` + closed-set level + counts/booleans + reason;
keep any measurement scalar internal to `evals/`. Add a contract-shape test that rejects a float field.
**Warning signs:** the word "probability"/"%" in the tool output, CLI, or schema.

### Pitfall 5: Hand-editing `EVALS.md` or `report.json`
**What goes wrong:** the deferral rate or calibration numbers are typed into the doc.
**Why:** `test_docs_final.py::test_evals_is_a_projection_of_the_report` runs `emit_evals.py --check`.
**How to avoid:** add fields to the report, `--write` `EVALS.md` through the generator; never edit a number.
**Warning signs:** `EVALS.md is out of date` from the generator check.

### Pitfall 6: Forgetting the E-09 behavioural change
**What goes wrong:** the phase ships, but the committed report/EVALS still show the old direction split, or
a developer "fixes" the new E-09 outcome by tuning a fixture.
**Why:** D8-11 makes a no-match case defer; E-09 is a no-match case; its outcome and hence the analysis
change.
**How to avoid:** plan the report regeneration as an explicit task and re-read the direction split
honestly (E-09 stays the declared failure, still `passed=False`).
**Warning signs:** a manually preserved "under-triage 3" or a changed E-09 `passed` value.

### Pitfall 7: A `no_match` case whose deferral still reaches `verify`/the gate
**What goes wrong:** the no-match deferral is implemented in a place that the gate path bypasses, so E-09
still commits.
**Why:** `route_after_score` does not check `no_match`; the deferral must be enforced by
`route_after_assess` on the neutral branch.
**How to avoid:** ensure `assess` runs on the `verify`-bound branch and that `route_after_assess` reads the
`no_match`-forced deferral.
**Warning signs:** the E-09 end-to-end test still produces a colour / a queue row.

## Code Examples

### The pure component (mirrors `core/scorer.py` purity — no model, MCP client, store, or I/O)

```python
# Source: pattern from src/triagedesk/core/scorer.py + src/triagedesk/core/rules.py
from triagedesk.core.rules import get_discriminators, get_tews
from triagedesk.core.schema import CaseInput, ConfidenceResult, PriorityResult

def assess(case: CaseInput, matched_ids: list[str], no_match: bool,
           priority: PriorityResult) -> ConfidenceResult:
    rules = get_tews()
    categories = set(get_discriminators().categories)
    # (a) vitals coverage — count pair, never a percentage
    used, missing = len(priority.used_vitals), len(priority.missing_vitals)
    total = len(rules.parameters)
    # (b) discriminator coverage
    matched = len(matched_ids)
    # (c) override-vs-TEWS — did a discriminator RAISE the colour?
    override_fired = any(rule.rule_id in categories for rule in priority.triggered_rules)
    # (d) TEWS distance from the band edge (data-driven; no inlined bound)
    band = next(b for b in rules.tews_to_colour
                if b.min <= (priority.tews or 0) and (b.max is None or (priority.tews or 0) <= b.max))
    upper = band.max if band.max is not None else (priority.tews or 0)
    distance = min((priority.tews or 0) - band.min, upper - (priority.tews or 0))
    ...
```

### The tool (same `@audited` shape as the other five)

```python
# Source: pattern from src/triagedesk/mcp/server.py:190-203
@server.tool()
@audited()
def assess_confidence(
    case: CaseInput,
    matched_ids: list[str],
    no_match: bool,
    priority: PriorityResult,
) -> ConfidenceResult:
    """Return the deterministic coverage/deferral signal — no model, no store (D8-07)."""
    return confidence.assess(case, matched_ids, no_match, priority)
```

### The router (structural caution — both terminals already end at END)

```python
# Source: pattern from src/triagedesk/graph/build.py:127-140
def route_after_assess(state: TriageState) -> str:
    signal = state.get("confidence")
    if signal is not None and signal.deferral:
        return "request_missing_info" if signal.reason_is_missing_info else "escalate"
    return "verify"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Symmetric accuracy figure for triage | Separate under-/over-triage, red-miss weighting | v1.0 (D-03) | Phase 8's deferral rate and direction split extend the same asymmetric framing. |
| Point estimate as "confidence" | Coverage/abstention signal + risk–coverage (selective prediction) | standard selective-prediction practice | The challenge's "no pseudo-probability as clinical risk" rule maps exactly onto abstention + coverage, not calibrated probability. |

**Deprecated/outdated:**
- Presenting any percentage as clinical risk — explicitly Out of Scope in `.planning/REQUIREMENTS.md:76`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The declared held-out split is `E-01…E-14` (calibration) vs `H-01/H-02` (held-out), reusing the existing `held_out` flag. | Offline Calibration | If the planner intends a different split, the ECE/coverage numbers and the D8-13 declaration differ. (Open Question 1.) |
| A2 | The calibration scalar (for ECE binning) may live internal to `evals/` and never appear in `core/schema.py` or the tool output. | Offline Calibration | If the reviewer reads any scalar as a "probability", D8-04 is contested. |
| A3 | The confidence signal is **not** added to `HandoverCard` (Phase 10's banner owns rendering). | Blast Radius | Adding it breaks `test_safety_spine.py::_EXPECTED_CARD_FIELDS` and expands this phase's scope. |
| A4 | The `assess` node runs on the `verify`-bound branch and is the enforcement point for the `no_match` deferral. | Routing Change | A wrong placement leaves E-09 committing (Pitfall 7). |
| A5 | The override signal is read as `rule_id ∈ get_discriminators().categories` (no colour re-derivation). | Signal Components (c) | A re-deriving implementation risks the DRY/one-colour-place gate (Pitfall 2). |

**If this table is not empty:** items A1–A5 are decisions the planner/discuss-phase should confirm before
locking the plan (A1 and A2 in particular).

## Open Questions (RESOLVED)

1. **Exact declared split and where ECE is reported.**
   - What we know: `H-01/H-02` are the existing declared held-out cases (n=2); `E-01…E-14` are the main
     suite (n=14). Success criterion 4 says calibration is "measured offline on a held-out split".
   - What's unclear: a 2-case ECE is degenerate; should ECE be reported on the held-out split (as worded),
     the calibration split, or both?
   - Recommendation: report the calibration-set ECE/risk–coverage as the substantive figure **and** the
     held-out bound on `H-01/H-02`, each with `n` named and the explicit small-sample declaration; never
     present either as validated. Declare the split before running.

2. **Polarity of the four components.**
   - What we know: D8-01 fixes *which* four, D8-discretion leaves weights/polarity open.
   - What's unclear: whether a discriminator **override** should *raise* or *lower* confidence, and how
     the four combine.
   - Recommendation: treat an override as *raising* confidence in the colour (a strong clinical signal),
     subject to the override rule only being present when the category genuinely raised the colour; treat
     small band distance, a `no_match`, and low vitals coverage as *lowering* it. Record the rationale with
     the D8-09 cost in `docs/DECISIONS.md`.

3. **How the deferral reason picks `escalate` vs `request_missing_info`.**
   - What we know: `request_missing_info` already means "a scored vital is missing"
     (`graph/nodes.py:211-220`); `escalate` carries an out-of-scope/abstention reason.
   - Recommendation: route missing-vitals-driven deferrals to `request_missing_info` and all other
     deferrals (no_match, band-edge, override-ambiguity) to `escalate`, so the terminal semantics stay
     single-purpose.

## Environment Availability

No external dependencies are added (hard constraint: no new dependency). The phase is code + fixtures +
offline analysis only.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (uv-managed) | Runtime | ✓ | 3.12 (project pin) | — |
| `pytest` + `pytest-asyncio` | Suite (279 passing baseline) | ✓ | present (dev deps) | — |
| Ollama / local model | **Not required** (offline calibration + deterministic signal) | n/a | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

Nyquist validation is enabled (no `workflow.nyquist_validation: false` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-asyncio` (existing; 279 passing baseline) |
| Config file | `pyproject.toml` (pytest config) |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv run pytest` |
| Focused example | `uv run pytest tests/test_graph_recovery.py tests/test_safety_spine.py -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-02 | `assess_confidence` computes the four-component signal deterministically (pure) | unit | `uv run pytest tests/test_confidence.py -x` | ❌ Wave 0 |
| AGENT-02 | Contract carries no percentage/float confidence field | unit/schema | `uv run pytest tests/test_confidence.py::test_no_percentage_field -x` | ❌ Wave 0 |
| AGENT-02 | Deferral routes to `escalate`/`request_missing_info`; never `commit`; zero queue rows | integration (graph) | `uv run pytest tests/test_graph_confidence.py -x` | ❌ Wave 0 |
| AGENT-02 | `no_match` forces a deferral; E-09 ends at a terminal | integration (eval) | `uv run pytest tests/test_eval_suite.py -x` (add assertion) | ✅ extend |
| AGENT-02 | Scorer has no confidence input (one-way down-grade guard) | unit/AST | `uv run pytest tests/test_purity.py tests/test_confidence.py -x` | ✅ extend |
| AGENT-02 | 6th tool audited + allowlist of 6 | contract | `uv run pytest tests/test_safety_spine.py tests/test_mcp_tools.py -x` | ✅ extend |
| AGENT-02 | Deferral rate + calibration in `report.json`; EVALS projection recomputes | unit/projection | `uv run pytest tests/test_eval_report.py tests/test_docs_final.py -x` | ✅ extend |

### Sampling Rate

- **Per task commit:** `uv run pytest -q`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green (baseline 279 + new tests) before `/gsd-verify-work`; also run
  `uv run python scripts/emit_evals.py --check` and the offline harness to regenerate `report.json`.

### Wave 0 Gaps

- [ ] `tests/test_confidence.py` — pure-signal unit tests (the four components, determinism, no percentage).
- [ ] `tests/test_graph_confidence.py` — routing/deferral integration + the one-way-safety proofs (or
      extend `tests/test_graph_recovery.py`).
- [ ] Extend `tests/test_safety_spine.py` (allowlist = 6) and `tests/conftest.py::build_graph_tools`
      (6th fake) and `evals/tools.py::build_tools` (6th real in-process tool).
- [ ] Regenerate `evals/results/report.json` + `EVALS.md` after the E-09 deferral change.

## Security Domain

`security_enforcement` is enabled (absent from config = enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Pydantic typed contracts (`core/schema.py`, the ONE schema module); the tool input is the typed `CaseInput`/`MatchResult`/`PriorityResult`, not free text. |
| V6 Cryptography | no | No crypto added; the existing audit hash chain is untouched. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Signal smuggling a model-derived number as "confidence" | Tampering | Contract shape has no float/percentage field; a shape test rejects one (D8-02/04). |
| Re-deriving a colour outside the scorer (a second colour producer) | Tampering | The component reads the already-produced colour + the discriminator data; a guard asserts `core/scorer.py` keeps its single production path. |
| Confidence signal enabling a write / downgrade | Elevation | `assess` is side-effect-free and routes only to `escalate`/`request_missing_info`, which have no edge to `commit` (structural). |
| Env/network access from the new `graph/` node or `core/` module | Information disclosure | Existing AST guards (`test_safety_spine.py`, `test_purity.py`) scan `graph/` and `core/`; the new code must read no env and import no network/model client. |

## Sources

### Primary (HIGH confidence)
- In-repo source of truth, read this session: `src/triagedesk/core/schema.py:89-115`, `core/scorer.py:194-284`,
  `core/matcher.py:51-75`, `core/rules.py:44-135`, `core/recheck.py`, `graph/build.py:65-316`,
  `graph/nodes.py:105-388`, `graph/state.py:25-52`, `mcp/server.py:91-280`, `evals/report.py`,
  `evals/analysis.py`, `evals/runner.py`, `evals/tools.py`, `evals/invariants.py`, `scripts/emit_evals.py`,
  `durable.py`, `data/sats_tews.yaml:80-100`, `data/sats_discriminators.yaml:20-208`.
- Guard/contract tests: `tests/conftest.py`, `tests/test_safety_spine.py`, `tests/test_graph_tracer.py`,
  `tests/test_eval_suite.py`, `tests/test_eval_report.py`, `tests/test_docs_final.py`,
  `tests/test_no_duplicated_sats.py`, `tests/test_purity.py`, `tests/test_graph_purity.py`,
  `tests/test_audit_chain.py`.
- `.planning/phases/08-calibrated-confidence-abstention/08-CONTEXT.md`, `.planning/REQUIREMENTS.md`,
  `.planning/STATE.md`, `docs/CONVENTIONS.md`, `docs/DECISIONS.md`, `EVALS.md` §3/§4/§5.

### Secondary (MEDIUM confidence)
- Selective-prediction framing (risk–coverage / abstention) as the principled alternative to a calibrated
  probability for small samples — standard practice, applied to this suite by construction (not fetched
  from a single citation this session; flagged as design discretion).

### Tertiary (LOW confidence)
- The exact numeric ECE values and bins — intentionally unresolved; they are measurements to be produced,
  not facts, and must carry the small-sample declaration.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; every seam read in-repo this session.
- Architecture: HIGH — allowlist/tool factories, node superset check, and commitless terminals all verified by reading the files.
- Calibration measurement: MEDIUM — the split and the ECE-vs-no-probability reconciliation are genuine design discretion (Open Questions 1–2, Assumptions A1–A2).
- Pitfalls: HIGH — derived from the concrete guard tests that will fail.

**Research date:** 2026-10-12
**Valid until:** stable — the seams are frozen (v1.0 tag `v1.0-submission`); revisit only if Phase 9 (retrieval) lands first and adds a `ground` node after `score`.
