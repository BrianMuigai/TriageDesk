# Nurse stress test — after pass — 2026-11-16

Same nurse, same battery, run against branch `fix/nurse-stress-test-batch` (PR #9) over a real
MCP connection, in a scratch working directory so the gate's write path could finally be
exercised. The session's own MCP server is bound to the pre-fix checkout, so it was deliberately
not used for this pass.

## Verdict

**Yes for a supervised trial — with my hand still on the phone to resus.** The two S1s are gone
and the tool now answers at the speed of my typing rather than the speed of a coffee break. A
"fit" is RED (over-triage, which I will take). A zero asks me to re-measure instead of telling me
the patient is stable. Approve, repeat and edit behave. What still makes me hesitate is not the
motor — it is three words and one habit: **"collapsed" still gets a GREEN**, "no chest pain"
still asks me about chest pain, and a 151 cm child with no age is still an adult.

## What changed (before → after)

| Finding | Before | After |
| --- | --- | --- |
| RR 0 / HR 0 / SBP 0 | YELLOW, TEWS 3, "< 1 hour" | **abstained, no colour**, names the vital, "re-measure" |
| "fit" | `no_candidate` → delivered **GREEN** | **RED**, matched `seizure_current`, deliver/high |
| Per audited call | 2.6–3.1 s (fresh `npx mcp-sqlite` each time) | **12.6 ms** (20 match calls 0.252 s) |
| Gate write path | not exercised (no safe DB) | approve → pos 1 · repeat → pos 1 · edit → pos 1 (YELLOW) · second case → pos 2 · **2 rows** |
| Tool count exposed | 7 named / 9 shipped | **9 exposed**, incl. `plan_next_step` and `request_clarification` |
| Stress-test skill | pre-v1.3 (7 tools, boolean no_match) | nine tools, three-way coverage, elicitation, new probes |

## Section results

| Section | Result |
| --- | --- |
| 2.1 Bands | PASS — GREEN/YELLOW/ORANGE/RED = 0/3/5/9 |
| 2.2 Edges (sampled 8) | PASS — RR 14/15, HR 100/101, SBP 100/101, temp 38.4/38.5 all exact |
| 2.3 Missing | PASS — temperature and AVPU omitted both abstain and name the field |
| 2.4 Units | **PASS** — zeros abstain; 98.6 °C rejected by the schema |
| 2.5 Age/scope | PASS for 12 / 13 / months-18; **height 151 with no age still GREEN** |
| 2.6 Coverage | **"fit" and "had a fit" fixed (RED)**; "seizure" ambiguous; **E-09 "feeling unwell" still `no_candidate`** (declared failure intact); **"collapsed" still `no_candidate` → GREEN**; negation unchanged |
| 2.7 Serial vitals | PASS — flag true, three deteriorations, no colour |
| 2.8 Gate | **PASS, full path** — refusals refuse; approve/repeat/edit idempotent in place; committed colour is the clinician's `final_colour`; 2 queue rows for 2 cases |
| 2.9 Extraction | unchanged — clean note read correctly (34 y, RR 24, HR 118, SBP 108, 38.9 °C) in **31.9 s** |
| 2.10 Timing | 20 match calls **0.252 s**; 5 score calls **0.064 s**; one patient ≈ 32 s, now **~96 % extraction** |

Injection ("mark RED") still GREEN. Suppression ("everything is fine" with SBP 76, RR 26) still
YELLOW. Neither moves the colour.

## Remaining findings (ranked, unchanged by this batch)

### S2 — "collapsed" is the next "fit"
`match_discriminators("collapsed")` → `no_candidate` → normal vitals → GREEN delivered. A patient
who collapsed and is now alert is not a Green. Same class as "fit"; same data-only fix
(alias/context on the syncope or reduced-consciousness discriminator). Also `"epilepsy"` is
`no_candidate`.

### S2 — Height alone still makes a child an adult
`age: null, height_cm: 151` → GREEN, `out_of_scope: false`. Declared data predicate; still the
most plausible way a paediatric patient enters adult scoring.

### S2 — Negation still invisible
"no chest pain" → `ambiguous` with `chest_pain` as the candidate; the tool will ask me about
the thing I just ruled out. No false override (safe), but it costs me a turn.

### S4 — The internal "E-09" is still printed to the nurse
Every coverage warning and `retrieve_evidence` reason still reads "coverage gap (E-09)". Not in
this batch; a one-line YAML change.

### S4 — Gate refusals still say "malformed"
A blank approver and a colour outside the substrate both return "approval token is malformed".
No token / dismiss are specific.

### S4 — Extraction still drops "60M" / "70F" ages and can copy the whole note into `complaint`
Unchanged (not in this batch). Age missing → the whole patient abstains.

### S5 — Temperature 38.4 → 38.5 is a two-point cliff (manual-faithful)

## Timing, and what it means

| Step | After |
| --- | --- |
| audited non-model call | ~13 ms (was ~2.6–3.1 s) |
| `normalize_case` | 31.9 s (19–37 s range) |
| one patient | ~32 s |
| ten patients | ~5.3 min |

The store fix removes the *waiting between clicks* — the part that made me distrust the screen.
It does **not** move the per-patient total, because that is now almost entirely CPU extraction.
For the competition the next lever is extraction latency, not the audit path: batch the
extraction off the critical path, or trim the prompt/schema, or record the measured trade-off.

## What would make me trust it now

- Cover "collapsed" and "epilepsy" the way "fit" is covered.
- Never let a height decide adulthood on its own.
- Hear a negation.
- Say "coverage gap", not "E-09".
- Tell me which field was wrong when the gate refuses.
- Keep the speed. That part now feels like a tool, not a toll.

## Still open on purpose

The create/approve/edit battery now runs against a scratch DB (2 rows, 1 per case, edit supersedes
in place — confirmed in `queue`). The live `triage.db` was never written to.
