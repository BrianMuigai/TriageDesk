# Pitfalls Research — v1.1 Score Uplift

**Domain:** Adding capabilities to a **frozen, safety-critical** agentic clinical triage-support tool
(SATS-grounded, human-gated, local open-weights model, offline, synthetic-only)
**Project:** TriageDesk — *Agentic AI for Africa* challenge, Health track, "Symptom-based priority scoring"
**Milestone:** v1.1 Score Uplift (adds the seven named capabilities — plus the borrowed-MCP exercise — on top of the frozen v1.0 safety spine)
**Researched:** 2026-10-10
**Confidence:** **HIGH** for project-specific pitfalls (derived from the frozen `src/triagedesk/**`, the
v1.0 milestone audit, and the root design docs); **MEDIUM** for clinical/agent-engineering generalities
(peer-reviewed + official-docs sources).

> **Scope of this document.** This is *not* a re-run of the v1.0 pitfalls work (preserved at git tag `v1.0-submission`).
> v1.0 asked *"how do we build the safety spine without getting the colour wrong?"* This file asks a
> narrower and sharper question: **"what breaks when you bolt these seven capabilities onto a system that
> already works and has already been declared safe?"** The dangerous class of change in an additive
> milestone is **a new path that bypasses an existing invariant** — a second way to produce a colour, a
> second log, a second persistence write, a confidence that overrides a deterministic answer, or a gate
> that is now interactive and therefore no longer trustworthy by construction.

> **Read this with the v1.0 pitfalls (git tag `v1.0-submission`).** Everything that earlier work said about
> band edges, imputed vitals, injection-suppression, over/under-triage asymmetry, and the honesty rules
> still holds. The pitfalls below are the ones the *new* capabilities introduce or re-open.

## Grounding in the frozen v1.0 reality

Every pitfall below is filtered against what actually shipped, not what the roadmap said. The load-bearing
facts:

- **The colour is produced in exactly one place.** `core/scorer.py::score_priority` is pure and
  data-driven; `data/*.yaml` is the machine authority; `citations == triggered_rules` by construction.
- **The gate is structural, not procedural.** `graph/nodes.py::approval_gate` performs **no side effect
  before `interrupt()`**; `commit` is the *next* node and the only node with an edge to the queue write.
- **One audit path.** `mcp/server.py::audited` is the single interceptor; `store/audit.py` is the single
  record shape + `SHA256(prev_hash‖canonical_record)` chain; `verify()` and `reconcile()` are read-only.
- **The commit is idempotent** on `(case_id, content_hash)` over `IMMUTABLE_FIELDS` — but the shipped key
  is **narrower than `IMMUTABLE_FIELDS`** (covers `colour` only), which the v1.0 audit already logged as a
  warning (`WARN GATE-03/TOOL-05`: a same-`case_id` **edit** with a different colour writes a second row).
- **Durable checkpoints are built but unused E2E.** `graph/build.py::checkpointed_graph` exists and is
  tested; every E2E entry point (`runner.py`, `demo/run.py`) uses `InMemorySaver`.
- **The eval harness is the sole source of `EVALS.md` numbers**, and E-09 is a *declared* failure that
  `data/sats_discriminators.yaml` explicitly says must **not** be tuned green.
- **There is no retrieval, no confidence, no tracing, no desk surface.** Those are the gaps this milestone
  closes — and therefore the surfaces where new invariants must be created, not merely preserved.

## How to read the phase mapping

The v1.1 roadmap is not yet created. Pitfalls are mapped to **capability phases** that mirror the v1.1
milestone's own target-feature groups. The roadmapper should re-map these to its own phase numbers; the
**capability names are stable** regardless of numbering.

| Phase label | Capability (v1.1 target feature) | Track |
| --- | --- | --- |
| **P-Docs** | Docs & rigour (one-command README, EVALS reconciliation) | Docs |
| **P-Eval** | Fix E-04/E-07, re-run suite, **calibrated confidence + abstention** | Evaluation |
| **P-Gate** | **Real approve/edit/dismiss gate interaction** | Desk UX |
| **P-UX** | **Desk priority card** + vitals entry + loud no-match/low-confidence banner | Desk UX |
| **P-RAG** | **RAG grounding** over the SATS discriminator KB | Agentic depth |
| **P-MCP** | Borrowed MCP **exercised beyond `query`** (read-only storage) | Agentic depth |
| **P-Ckpt** | **Durable `checkpoints.db` wired E2E** | Agentic depth |
| **P-Trace** | **Span-based tracing + replay** | Agentic depth |
| **P-Live** | Live-review "**add a rule live**" rehearsal (ST-1) | Review & demo |
| **P-Demo** | Demo refresh + docs + freeze discipline | Review & demo |

---

## Critical Pitfalls

Mistakes that would make a real patient's priority wrong, void a safety invariant, or forfeit the
challenge — each concrete to *these* capabilities, with warning signs and an owning phase.

### Pitfall 1: RAG becomes a **second colour path** — retrieval output trusted as evidence

**What goes wrong:**
The capability is "retrieval-grounded discriminator selection" — a genuine improvement over the keyword
matcher. The failure is that the *retrieved* result is allowed to do more than **propose candidate ids
from the closed set**. Two concrete regressions: (a) the retrieved text/score is passed into `score`
and — directly or via a model — seeds the colour, so a second, un-audited colour producer exists
alongside `score_priority`; or (b) retrieval returns a free-text "discriminator" (a label, a manual
sentence, a category) that is cited on the card but is **not a member of the closed set** in
`data/sats_discriminators.yaml`. The moment a retrieved string can appear in `citations[]` without being a
declared rule, the v1.0 invariant `citations == triggered_rules` no longer implies "every priority is
sourced from the scale".

**Why it happens:**
The v1.0 design was "extend by data, not by editing working code" (SOLID-O). RAG looks like a *retrieval*
upgrade, so it is easy to add it as a new node that returns richer objects, and equally easy to let the
richer object flow into scoring "because the model ranked it highest". The existing matcher already
returns a closed-set `MatchResult`; a retrieval rewrite quietly broadens the contract.

**How to avoid:**
- Retrieval may output **only** ids from the closed set, plus a deterministic rank/score and an explicit
  `no_match` — the *same* `MatchResult` contract, widened at most by a `candidates: [{id, score}]` field.
  It must not return labels, categories, colours, or free text that reaches `citations[]`.
- `score_priority` remains the **only** producer of a colour. Retrieval feeds `matched_discriminator_ids`;
  it never returns a colour and never bypasses the `_most_urgent_category` max-urgency resolution.
- Extend `verify` and INV-1: every `matched_id` (and every citation) must be a declared discriminator/category
  id; a retrieved id that is not in the closed set is dropped, not surfaced.
- Add a guard test mirroring `tests/test_no_duplicated_sats.py`: *no retrieval result may contain a colour
  token or a string that is not a declared id.*

**Warning signs:**
- A new node/module imports the model *and* can hand a value to `score`.
- `MatchResult` grows a free-text or `colour` field.
- A card citation that does not appear in `data/sats_discriminators.yaml`.
- `citations == triggered_rules` still passes but a citation's text is a retrieved sentence.

**Phase to address:** **P-RAG**, enforced at the P-RAG verifier/code-review gate; INV-1 extension lands in P-Eval.

---

### Pitfall 2: "Deceptive grounding" — a real citation that is about **the wrong rule**

**What goes wrong:**
The dangerous retrieval failure in clinical RAG is not a missing citation; it is a **real citation that
does not apply to the thing it is attached to** — a rule that exists and is sourced, correctly formatted,
and yet is not the rule that produced the priority. This is the retrieval-era version of v1.0's Pitfall 1
("cited ≠ correctly cited"): a discriminator is matched on weak similarity ("unwell", "generally weak"),
the category's colour is applied, the citation is genuine, the invariant holds — and the patient is
under-triaged. The published literature names the general form (*deceptive grounding / entity-attribution
failure*): an answer can pass hallucination, faithfulness **and** citation checks while the cited evidence
is about a different entity ([arXiv 2607.09349](#sources)). A triage analogue is a citation to
`severe_pain` attached to a case whose complaint only weakly implied "discomfort".

**Why it happens:**
RAG optimises for *plausible* retrieval, and citation checks generally verify *presence and existence*,
not *applicability*. The v1.0 invariant checks count equality, which catches a dropped citation but not a
misapplied one.

**How to avoid:**
- Bind the citation to the **exact fired rule**, never to a retrieved neighbour. `citations` must be
  1:1 with `triggered_rules` **and** each citation's `rule_id` must equal the fired rule's id.
- Add an **applicability check**: the id in `matched_ids` that justified an override must be the id whose
  citation is shown — not "some discriminator in the same category".
- Report **discriminator recall/coverage** per case (`matched_ids`, `no_match`) *separately* from colour
  accuracy, so a weakly-matched override is visible with its source.
- Keep a `no_match` → visible "NURSE TO CONFIRM" path: weak retrieval must degrade to *abstain/flag*, not to
  a confident lower colour.

**Warning signs:**
- An override fires off a low retrieval score with no coverage note.
- The card shows a category citation ("Very urgent discriminators") where a specific rule citation is expected.
- E-09 changes from FAIL to "pass" without a held-out vague case also passing.

**Phase to address:** **P-RAG** (contract) and **P-Eval** (coverage reporting + applicability assertion).

---

### Pitfall 3: E-09 is **tuned green** instead of genuinely fixed

**What goes wrong:**
The stated goal is "E-09 must genuinely improve, not be tuned green." The failure is silent overfitting:
RAG (or a broadened alias list) is added specifically to make E-09 return ORANGE, the retrieval/threshold
is adjusted until the expected colour matches, and the *expected colour or the test* is massaged. The
challenge scores "is the test set honest rather than curated to pass" (JC-4) and E-09 is the visible proof
of honesty. `data/sats_discriminators.yaml` even carries a comment that "feeling unwell" is deliberately
absent so E-09 is *not* tuned green. Adding retrieval is the correct fix path — but it is exactly the
change most likely to be overfitted under deadline pressure.

**Why it happens:**
Under a deadline, "make the failing case pass" is one edit away, and the eval author and the retrieval
author are the same person. The suite can then measure "did we tune to our own cases", not "did retrieval
generalise".

**How to avoid:**
- Freeze E-09's expected outcome and evidence: if retrieval fixes it, the *unchanged* case must pass; do
  **not** edit the expected colour, the complaint text, or the aliases to force a match.
- Add **held-out vague-presentation cases** authored but *not* iterated against, so the generalisation
  signal is independent of the tuned case.
- Treat any change to an expected colour as a reviewable, logged clinical-content event (`DECISIONS.md`),
  exactly as v1.0 required — never a silent edit to make a colour match.
- Regenerate `EVALS.md` **only** from `evals/results/report.json` (the harness is the sole writer). Report
  the new E-09 result *and* the held-out results together; if E-09 still fails, leave it declared.
- Report the **matched-id set**, not just the colour, so a "fixed" E-09 that is stable-but-lucky is visible.

**Warning signs:**
- E-09 flips to pass in the same commit that broadened aliases or added the retrieval threshold.
- A new `git log` entry on `data/sats_discriminators.yaml` with no rationale.
- The held-out vague cases do *not* exist (only E-09 changed).
- `EVALS.md` counts are hand-edited rather than harness-generated.

**Phase to address:** **P-RAG** (fix) with the honesty gate in **P-Docs/P-Eval**, enforced at plan-check and the eval gate.

---

### Pitfall 4: Retrieval introduces **non-determinism** into discriminator selection

**What goes wrong:**
v1.0's head-line claim is *the scorer is deterministic; pipeline stability is measured*. The matcher is a
pure alias lookup, so `matched_ids` are stable run-to-run. An embedding-based RAG over the KB can return a
**different top-k on different runs** (embedding drift, ANN tie-breaks, floating-point ordering, a model
re-quantisation), so the **matched set flaps**. Because discriminators *override* TEWS and the most urgent
wins, a flapping match swings the colour by one or more levels — and it looks like a passing case until the
third run. The eval already treats any run-to-run variation in colour **or** matched set as a hard failure
(`matched_set_stable` in `runner.py`), so a non-deterministic retriever can make the suite *impossible to
pass honestly* — or tempt the team to relax stability reporting.

**Why it happens:**
Retrieval is treated as "NLP nicety" rather than a safety-critical decision. Popular vector stores and
embedding endpoints are non-deterministic by default and rarely document tie-breaking.

**How to avoid:**
- Make retrieval **deterministic or pinned**: local, fixed, hashed embeddings (no remote endpoint, no
  model-download drift); a deterministic tie-break (score, then id sort) on equal similarity; and a
  recorded `embedding_model` + `kb_hash` in the audit/report provenance.
- Keep a **deterministic fallback** (the existing alias matcher) and prefer it for exact/alias hits; use
  retrieval only to add candidates — and if retrieval and alias disagree, the rule is explicit, not
  emergent.
- Preserve the stability contract: any case whose `matched_ids` differ across the 3 runs is a **fail**, not
  an average. Do not relax `matched_set_stable` to make a flapping RAG pass.
- Measure and report **field stability** (matched set) as the headline, not just colour stability.

**Warning signs:**
- `matched_set_stable: false` on any case.
- Token in/out or matched ids vary run-to-run with no logged reason.
- Retrieval uses a hosted embedding API (also a data-residency breach — see Security).
- The stability flags in the report are weakened in the same PR that adds retrieval.

**Phase to address:** **P-RAG** (determinism) with the reporting contract in **P-Eval**.

---

### Pitfall 5: A confidence number that **hides** the dangerous case (overconfidence in errors)

**What goes wrong:**
Calibrated confidence + abstention is the right idea, but the canonical failure is the model being
**confident and wrong**: if the score that triggers deferral is overconfident on exactly the cases that
matter, abstention **never fires** on the dangerous case ([arXiv 2603.02719](#sources)). Two concrete
regressions in TriageDesk terms: (a) the system attaches a high-confidence value to a case where the
discriminator did **not** match (a vague complaint that fell back to vitals) — so the nurse reads a
confident bare colour and the under-triage is *hidden by the confidence*, which is worse than no
confidence at all; (b) the confidence is shown as a **clinical probability / percentage** ("87% sure this
is ORANGE"), which is uncalibrated, indefensible, and invites over-trust.

**Why it happens:**
"Calibrated confidence" sounds like "a number between 0 and 1", so teams surface the model's logit or a
softmax and call it calibrated without ever measuring ECE, and without checking whether confidence
*tracks* the known-weak path (no discriminator matched).

**How to avoid:**
- Calibrate against a **held-out synthetic set**, report ECE / a reliability curve, and disclose that
  calibration is measured, not assumed. Calibration degrades under shift — say so.
- Confidence is **advisory metadata that can only make the system more cautious**: it may trigger a
  re-measure/escalate path, never a silent colour downgrade. A no-match case is *low coverage* regardless
  of any softmax value.
- Never present a confidence as a clinical probability. Show a **coverage/quality signal** ("no
  discriminator matched", "2 of 5 vitals missing") instead of a percentage.
- Report a **risk–coverage** picture, not a single accuracy number: at the chosen abstention threshold, what
  fraction defers and what the error is on retained cases.

**Warning signs:**
- A case shows "high confidence" while `no_discriminator_matched: true`.
- Any percentage/pseudo-probability on the card.
- No ECE / reliability measurement, no held-out calibration split.
- The abstention threshold is a hand-picked 0.5 rather than derived from a stated cost.

**Phase to address:** **P-Eval** (calibration + reporting) with the surfacing contract in **P-UX**.

---

### Pitfall 6: Abstain-too-often → alert fatigue and an unworkable desk

**What goes wrong:**
The mirror failure of Pitfall 5: an over-cautious threshold makes the agent defer so often that the nurse
stops reading the deferral as information ("everything is low-confidence, so just approve"). This is the
documented alert-fatigue / override-reflex route to harm, and it also defeats the milestone's own goal of
a nurse doing a real thing *faster*. The published selective-prediction work tunes the deferral threshold
to an **explicit expected clinical cost** (asymmetric: under-triage ≫ over-triage, deferral a small but
real cost) on a calibration split — not to "maximally cautious" ([Nature Sci Rep 2026](#sources)).

**Why it happens:**
"Safer" reads as "abstain more", and under deadline the easiest way to make failures disappear is to defer
them. Nobody measures the *deferral rate* as a first-class number, so over-abstention is invisible.

**How to avoid:**
- Set the threshold by minimising a **stated, asymmetric cost** on held-out cases; document the cost
  assumptions (under-triage cost ≫ over-triage cost ≫ deferral cost).
- Make abstention **actionable and specific**: name the missing vital(s) or the unmatched complaint and the
  next step ("re-measure temperature", "confirm complaint with the patient") — the shipped recovery/escalate
  terminals already model this; the card must not be a dead end.
- Report the **deferral rate** alongside coverage and error; treat a deferral rate near 100% (or near 0%) as
  a warning, not a win.
- Keep out-of-scope abstention (paediatric, missing/ambiguous age) **categorical** — that abstention is not
  a threshold and must never be traded away for coverage.

**Warning signs:**
- Most cases in the demo defer.
- Deferral reason text is generic ("low confidence") rather than naming what is missing.
- Paediatric/missing-age abstention shares a tunable threshold with the confidence path.

**Phase to address:** **P-Eval** (threshold by cost) with the actionable-copy contract in **P-UX**.

---

### Pitfall 7: The interactive gate becomes a **rubber stamp**

**What goes wrong:**
Making the gate a *real* approve/edit/dismiss interaction (from v1.0's hardcoded JSON) is the U2 fix — but
a real button is exactly the automation-bias surface research warns about: clinicians over-rely on CDSS
and will change a *correct* decision to an incorrect one after machine advice; "human-in-the-loop is a
design intent, not an empirical finding" — oversight must be engineered ([Goddard, JAMIA](#sources)). If
the new UI defaults to **approve**, puts the button first, hides the evidence behind a toggle, or makes
edit/dismiss slower than approve, then the milestone has replaced a hardcoded approval with a *reflexive*
one. That is worse: it looks like a human decision and isn't.

**Why it happens:**
Confirmations optimise for speed, and "a nurse does a real thing faster" pushes every incentive toward a
frictionless approve. Nobody measures whether the human ever *disagrees*.

**How to avoid:**
- Put the **evidence between the reviewer and the decision**: triggered rules + the vital values behind
  each + a prominent `no-discriminator-matched` flag + the second-look flag. A bare colour is un-auditable.
- Make **edit and dismiss first-class and one action away** — friction on *override* is the bug; friction on
  *blind approval* is the feature. Do not make "approve" the default-highlighted choice.
- Record every `decision` (`approve|edit|dismiss`) with the approver and role (the audit record already
  carries this) and **report the override rate** in `EVALS.md`. **A 0% override rate across the demo is a
  warning**, not a triumph — state it as such.
- Design for **disagreement-capable**: the nurse must be able to see *why* the agent is wrong at a glance.

**Warning signs:**
- The demo shows a single Enter/approve keystroke with no visible reasoning shown on screen.
- Edit/dismiss are buried in a submenu, or require retyping the colour.
- The eval/demo records approvals but never a single override.
- Reviewers describe the gate as "the pause" rather than "the audit surface".

**Phase to address:** **P-Gate** (interaction) and **P-Demo** (the demo must show a human *judging*, not
merely clicking); override-rate reporting in **P-Eval**.

---

### Pitfall 8: Durable resume **re-runs side effects** — duplicate audit, duplicate write

**What goes wrong:**
Wiring `checkpointed_graph` E2E (the Ckpt gap) exposes the single most-missed LangGraph rule: **on resume
the graph restarts the entire node from the top**, so every statement before `interrupt()` re-executes.
The v1.0 `approval_gate` was written side-effect-free on purpose, but the E2E wiring is precisely where a
helpful addition ("log 'approval requested'", "record a pending audit row", "bump a counter") gets placed
*before* the interrupt. On resume it fires twice → a duplicate audit record (which can still *verify*,
because the chain is append-only — a duplicate is not a chain break, so nothing alerts), or a duplicate
side effect. Related: `Command(resume=...)` is the only `Command` to pass *in*, the `thread_id` must match,
and the resume payload is **untrusted input** that must be validated.

**Why it happens:**
Interrupt looks like a pause ("execution waits"), so the mental model is "it stops here and continues
here". It does not — it *replays the node*. Authors add a small pre-interrupt effect because it "only runs
once".

**How to avoid:**
- Keep `approval_gate` **side-effect-free before `interrupt()`** — the v1.0 comment says this; make it a
  test, not a comment. The queue write and its audit stay in the *next* node (`commit`), which runs once.
- Any unavoidable pre-interrupt write must be an **upsert keyed by `case_id`** (idempotent), never an append.
- Validate the **resume value** with a typed `response_schema` (LangGraph `>=1.2.12`) so a malformed
  approval is rejected at the boundary, exactly as the gated tool already refuses a malformed token.
- Do **not** wrap `interrupt()` in a bare `try/except` (it pauses by raising); do not loop or conditionally
  skip `interrupt()` in one node (resume values match by **index** → exponential replay) — use a
  conditional edge instead.
- Add an E2E resume test that asserts **exactly one** `commit_priority` audit record and one queue row for
  a pause→resume cycle.

**Warning signs:**
- An audit record for the same `case_id`/tool appears twice with no second user action.
- Any append/log/HTTP call in `approval_gate` above the `interrupt(payload)` line.
- The resumed run's audit has `count(commit_priority) > 1`.
- `interrupt()` inside a `while`/`for` or a `try/except` in the new code.

**Phase to address:** **P-Ckpt** (E2E wiring + resume test); verified at the P-Ckpt gate.

---

### Pitfall 9: **Non-deterministic / wrong-thread resume** and the idempotency-key breadth bug

**What goes wrong:**
Two coupled resume failures. (a) **Wrong or unstable `thread_id`**: if the E2E path derives `thread_id`
from something volatile (a wall-clock, a random run id) the pause and the resume land in different threads,
so the graph starts fresh, re-scores, and can produce a *different* colour than the one the clinician
approved — the approved artefact and the committed artefact diverge. (b) **The key-breadth bug becomes
reachable**: the v1.0 audit already logged that the idempotency key covers **colour only**, so a
same-`case_id` **edit** with a different colour writes a *second queue row*. With `InMemorySaver` and a
hardcoded approve this was latent; once real edit/dismiss and durable resume are live, a click of **edit**
produces two rows for one case — a duplicate queue entry, which is the exact corruption the gate exists to
prevent.

**Why it happens:**
Resume determinism is assumed ("same thread_id? sure"). And the idempotency-key breadth was a known-but-
unexercised warning; nothing in v1.0's E2E flow ever hit the edit path, so the bug had no trigger.

**How to avoid:**
- `thread_id == case_id` (already the v1.0 intent: `case_id_for(raw_note)` is a stable content hash). Never
  a random or time-based id for a case that can pause.
- **Widen the idempotency key** to the immutable case content the key was always meant to cover
  (`IMMUTABLE_FIELDS`: colour, target, triggered_rules, citations, used_vitals) so an edit supersedes rather
  than duplicates; or key on `(case_id, decision_id)` so one approval = at most one row. Test: commit →
  resume with an **edit** → assert one row, updated, not two.
- Assert the **approved artefact equals the committed artefact**: the colour the clinician saw at the gate
  is the colour written to the queue (the `edit` case writes the clinician's `final_colour`; the `approve`
  case writes the *scored* colour, never a re-derived one).
- Keep `reconcile()` in the smoke test so a queue-write-without-audit window never ships silently.

**Warning signs:**
- `thread_id` contains a timestamp, uuid, or run index for a pausable case.
- A resume test that only exercises `approve` (the latent edit bug stays untested).
- `commit_to_queue` called with a content dict whose keys ≠ `IMMUTABLE_FIELDS`.
- Two queue rows with the same `case_id`.

**Phase to address:** **P-Ckpt** (thread-id + resume determinism) and **P-Gate** (edit path); the key fix is
a **P-Ckpt** blocker (it is a pre-existing logged warning that this milestone makes reachable).

---

### Pitfall 10: Tracing becomes a **second logging path** that diverges — or leaks — or bloats

**What goes wrong:**
Span-based tracing + replay (the observability gap) is safest when it is a **derived view** of the one
audit interceptor. Three regressions: (a) traces are emitted from a *separate* code path, so the trace and
the hash-chained audit disagree about what the agent did — two `log`s, two truths, and the defensibility
story splits (a DRY violation with a safety consequence); (b) spans capture raw **complaint text / prompts
/ model output** (which is patient data, synthetic here but the rule is "no PII-shaped fixtures / no real
data"), or a future change routes a real note through a hosted trace exporter (= egress = data-residency
breach); (c) on a CPU-only host, full-fidelity spans plus the local model plus the recorder exhaust RAM and
pass the latency budget, so tracing degrades the "seconds" promise.

**Why it happens:**
Tracing frameworks are usually added as auto-instrumentation *beside* existing logging; "add observability"
reads as additive, and the *last* thing anyone wants to optimise is the debug tooling — so it is shipped
un-sampled and un-redacted.

**How to avoid:**
- Emit spans from the **same interceptor** that appends the audit record (`mcp/server.py::audited`), so
  there is one event stream and the audit chain stays the **source of truth**; the trace is a projection.
  Keep `store/audit.py` the only writer of the chain.
- **Never** put raw complaint text, prompts, or model output in span attributes. Follow OTel's data
  minimisation guidance: hash/truncate/delete; keep ids, counts, colours, rule-ids, timings. Treat the note
  as PII-shaped even though it is synthetic ([OpenTelemetry: handling sensitive data](#sources)).
- Use **sampling** and a bounded buffer; keep spans off the hot path (no synchronous export per call); never
  let a trace exporter perform network I/O in the agent path (breaks the no-egress guarantee).
- **Replay must reconstruct from the same event stream** the audit uses (ids + inputs + outputs), not from a
  parallel trace; a replay that can disagree with the audit is a defect.

**Warning signs:**
- A second module writes a log/trace independently of `store/audit.append`.
- Span attributes contain the `complaint` string or a prompt.
- A remote trace endpoint is configured (egress).
- Demo latency rises and RAM headroom shrinks after tracing lands; traces un-sampled.

**Phase to address:** **P-Trace** (derived-view + redaction + sampling), verified at the P-Trace gate; no-egress
assertion re-run in **P-Demo**.

---

### Pitfall 11: The desk card shows a **colour without citations**, implies a diagnosis, or invites over-trust

**What goes wrong:**
The desk UX card is the new human surface. Three regressions: (a) the card renders the **colour and target
time but not the citations/evidence** (or buries them), so the nurse cannot audit it — this is the
automation-bias precondition and it also breaches the "every priority cites its source" non-negotiable on
the surface the human actually sees; (b) the card gains a free-text "assessment"/"impression"/"likely …
" line (diagnosis creep through presentation, exactly v1.0 Pitfall 9, now on a *new* surface that is not
covered by the existing `HandoverCard` schema guards); (c) the card shows a **confidence percentage** or
otherwise reads as a verdict ("ORANGE — confirmed") rather than a *proposal* ("SUGGESTED: ORANGE —
you decide").

**Why it happens:**
UX work optimises for glanceability, and a big coloured word is the most glanceable thing. The temptation is
to render a nicer string than the locked `HandoverCard`, which is precisely how diagnosis/prose creep
re-enters.

**How to avoid:**
- Render **from the locked `HandoverCard`** (`extra="forbid"` + `FORBIDDEN_FIELD_TOKENS`): no field exists
  for an assessment/impression/plan, so no prose can be smuggled in. The card is a *view* over that model,
  not a new string format.
- Show **citations next to the colour**, plus the `no_discriminator_matched` banner and the second-look
  flag — the shipped card already carries these fields; the UX must *surface* them, not drop them.
- Frame it as **SUGGESTED + evidence → you decide**. No "confirmed"/"final"; no percentage.
- Keep INV-3 as the guard and extend its scan to the rendered card (any new output string is an output
  field). A vitals-entry surface must not silently accept a °F temperature or impute a missing vital
  (reuse the existing schema bounds/rejection).

**Warning signs:**
- A rendered colour with no adjacent citation.
- Any "assessment"/"impression"/"likely"/"confirmed" string in the UI layer.
- A percentage on the card.
- Vitals entry that defaults/autocompletes a missing vital.

**Phase to address:** **P-UX** (card + entry), with INV-3 coverage extended in **P-Eval**.

---

### Pitfall 12: The live "add a rule live" edit **silently breaks a safety invariant**

**What goes wrong:**
The Stage-2 review adds a requirement live; the design promise is a **one-line YAML edit**. The failure is
a data edit that *looks* safe and silently changes the system's safety behaviour: (a) a new alias/rule
**shadows or collides** with an existing one (a broad alias such as "unwell" matches many complaints, or a
new discriminator id duplicates an existing id) so previously-stable colours change; (b) a new
discriminator's category/colour **violates most-urgent-wins** or introduces a citation that no rule fires;
(c) the edit **flips an existing eval's expected colour**, invalidating the honesty story; (d) the edit
isn't **validated or versioned**, so the audit chain can no longer name the exact ruleset that produced a
past priority; (e) the live edit **tunes E-09 green** by adding the very alias that was deliberately absent.
The stakes are higher than v1.0's "rehearsal pending": a live edit is a *runtime config change* that
bypasses code review, and the published feature-flag guidance (RBAC, audit logs, flag hygiene) and
identity-stable canary work (hold an identity-hash invariant across changes) both say runtime toggles need
the controls code changes get ([arXiv 2605.28097](#sources)).

**Why it happens:**
"The rules are data, so a live edit is safe" conflates *extensibility* with *invariant preservation*.
Nothing in the loader currently enforces referential integrity, uniqueness, or a post-edit invariant check.

**How to avoid:**
- Add a **loader validator** that fails closed on: duplicate ids, aliases that collide with an existing
  discriminator's id/alias, a discriminator whose category is not declared, and any rule that doesn't
  produce a citation. Validate on load, so a broken edit cannot take effect.
- Make every live edit **versioned + hashed**: `hash_rule_object(get_discriminators())` recorded in the
  audit (the hashing path exists: `core/hashing.py`), so past priorities name the ruleset that produced them.
- Rehearse on a **copy**, and after the edit **re-run the safety suite** (at minimum the invariant checks +
  one colour case) *live*, before scoring anything. The live edit must be a **new, non-shadowing** rule that
  does **not** change any existing expected colour and does **not** touch E-09's absent alias.
- Record the edit as a reviewable event (a `DECISIONS.md` line), matching v1.0's rule that a YAML change
  that flips a colour is a clinical-content change, not a code tweak.

**Warning signs:**
- An alias broad enough to match unrelated complaints ("unwell", "pain", "fever") added live.
- The live edit changes an existing eval's colour.
- No loader validation, no versioned hash, no post-edit smoke run.
- The live edit happens to be exactly what E-09 needed.

**Phase to address:** **P-Live** (rehearsal + additions) with the loader validator in **P-RAG** (KB owner) and
the versioned-hash/test gate in **P-Live**.

---

### Pitfall 13: Adding capabilities **duplicates logic** or creates a **second path to the queue** (DRY/SOLID erosion)

**What goes wrong:**
Every new capability is an opportunity to violate the iron-clad DRY + SOLID rule in a way that is also a
safety bug: a second place that produces a colour (a RAG "suggested colour", a confidence that "adjusts"
the colour), a second citation string, a new god-node that normalises+scores+persists, a confidence module
that re-implements band selection, or a tracing/interceptor path that becomes a second audit writer. The
v1.0 `CONVENTIONS.md` rejects exactly these, and the risk is *concentrated* in this milestone because the
additions are integration-shaped. A DRY violation here is not a style nit — two numbers that can disagree
is a correctness and audit risk.

**Why it happens:**
Additive features are naturally written as "a quick helper next to the thing it augments", and on a
deadline the fastest path is to re-derive a value rather than thread it through the existing single source.

**How to avoid:**
- Hold the OCP test for every change: *"can I add this as data, or as a new tool+node, without editing
  working code?"* A capability that edits the scorer, the gate, or the audit helper violates OCP.
- New capability = **new tool + new node**; the graph depends on the tool interface, not the implementation.
- Reuse the single sources: `data/*.yaml`, `core/citations.py`, `core/hashing.py`, `store/audit.py`,
  `core/schema.py`. No new module may inline a SATS value, colour, citation, or audit shape.
- Keep the existing guard tests green: `tests/test_purity.py` (core imports no llm/mcp), `test_no_duplicated_sats.py`,
  `test_graph_purity.py`. Add a guard for the new surfaces (retrieval returns closed-set ids only; confidence
  cannot mutate a colour).

**Warning signs:**
- A new module imports both `core` scoring data *and* re-derives bands/thresholds.
- A new node does more than route (it computes a colour or writes a store).
- A second `append_audit`/log call site outside `store/audit.py`.
- A citation string built inline rather than via `core/citations.format_citation`.

**Phase to address:** **all phases**, enforced at plan-check, code-review, and the verifier gate
(`docs/CONVENTIONS.md` §3).

### Pitfall 14: Replay **re-executes the gated commit** — a second queue write disguised as observability

**What goes wrong:**
Span tracing is paired with *replay* so a reviewer can re-run a past case. The failure: replay is implemented
by feeding the recorded inputs back through the **live graph**, so replaying a case whose trace reached
`approval_gate -> commit` **re-runs `commit_priority`** — a second queue write and a second audit record for a
single clinical decision. Because the v1.0 chain is append-only, the duplicate record *verifies* (a duplicate
is not a chain break, so nothing alerts); and because the shipped idempotency key is narrower than the
immutable content it was meant to cover (it covers `colour` only; see Pitfall 9), an `edit`-decision replay can
add a genuinely different second row. Tracing has silently become the second write path the gate exists to
prevent, and the "replay" that was meant to prove safety is the thing that corrupts the record.

**Why it happens:**
"Replay" reads as "run it again to watch", and the simplest implementation calls the same entry point
(`run_case` / the compiled graph). The side-effecting node is not obviously side-effecting from a trace UI,
and the idempotency-key breadth was a logged-but-unexercised warning until the interactive gate landed.

**How to avoid:**
- Make replay **read-only by construction**: reconstruct the timeline from the *checkpoint + audit/span event
  stream* (ids, inputs, outputs), never by re-invoking nodes that can write. If a graph re-run is unavoidable,
  compile it with the commit tool **replaced by a no-op/recording double** and assert `reconcile()` and the
  row count are unchanged afterwards.
- Give replay its own **mode** wired so `commit` is structurally unreachable — an injected tool map that has no
  `commit_priority`, not a conditional branch *inside* `commit` (which is editable, testable-away, and the
  exact anti-pattern the OCP rule rejects).
- Assert in a test: replay of a paused→approved case adds **zero** queue rows and **zero** `commit_priority`
  audit records, and the replayed colour equals the original.
- Keep `thread_id == case_id` (Pitfall 9) so replay reads the same checkpoint instead of starting a fresh,
  re-scoring run.

**Warning signs:**
- A replay command that calls the same `run_case`/graph entry point with the live owned-server tool map.
- `count(commit_priority)` grows after a "just replaying" run.
- Replay produces a new queue position for an already-queued case.
- The replay path has no no-op commit injection and no row-count assertion.

**Phase to address:** **P-Trace** (replay as a projection), with the idempotency-key fix in **P-Ckpt**.

---

### Pitfall 15: Exercising the borrowed MCP beyond `query` opens a **second, un-gated write path**

**What goes wrong:**
The milestone scores "exercise the borrowed server beyond `query`" (G7). The borrowed SQLite MCP server
exposes write tools (`write_query`/`insert`/`update`/`create_table`…). If any of those is called, it writes to
the domain store **without passing through the owned `audited` interceptor** (which wraps only the five owned
tools) and **without the approval gate** (which guards only `commit_priority`). The result is a change to
`triage.db` that has no audit record, that `reconcile()` cannot see (it cross-checks *queue rows*, not arbitrary
tables), and that can invalidate the idempotency assumptions the commit relies on. The gap is created by doing
literally what the milestone asked — "use more of the borrowed server".

**Why it happens:**
The borrowed server is deliberately a **separate** adapter context (to avoid era collapse, `mcp/adapter.py`), so
it is easy to forget it also sits *outside* the audit allowlist. Its write tools are one call away and "the
storage layer already exists", so a helpful refactor routes a write through it.

**How to avoid:**
- Keep the borrowed server **read-only in the agent path**. Exercise it beyond `query` with its *other read*
  tools (`list_tables`, `describe_table`, `read_query` against an allowlisted set of read statements) — that
  satisfies G7 without a write.
- If a write genuinely must go through the borrowed server, route it through a **new owned, audited tool** so
  it still hits the one interceptor and, if queue-affecting, the gate. Never call a borrowed write tool directly
  from a node.
- Add a **borrowed-tool allowlist + a statement guard** (reject `INSERT`/`UPDATE`/`DELETE`/`DROP` on the domain
  DB in the agent path) and assert both in a guard test, mirroring `assert_tool_allowlist` for the owned server.
- Keep `reconcile()` and INV-2 as the reconciliation backstop and add the borrowed-write tool to the
  "no un-audited write path" test.

**Warning signs:**
- A borrowed call named `write_query`/`insert`/`update`/`create_table` anywhere in the agent path.
- A change to `triage.db` whose tool name is not one of the five owned tools.
- `reconcile()` has no visibility into the mutated table.
- The borrowed adapter is loaded with no tool allowlist or statement restriction.

**Phase to address:** **P-MCP** (borrowed-tool allowlist + read-only posture), verified at the P-MCP gate; the
reconciliation backstop is re-checked in **P-Ckpt**.

---

## Technical Debt Patterns

Shortcuts that seem reasonable under the deadline but create long-term problems — several of which are also
*safety* debts because two values that can disagree is a correctness and audit risk, not a style nit.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Broaden the keyword alias list so E-09 returns ORANGE | No new dependency; E-09 "passes" in minutes | Overfits the single visible case; no generalisation; forfeits the challenge's honesty criterion (JC-4); hides that retrieval was never built | **Never** — this is the explicit "must not be tuned green" forfeit |
| Ship "confidence" as the model's softmax/logit, uncalibrated | A confidence field exists within a day | Confidence can be *confident and wrong*; abstention never fires on the dangerous class; indefensible in live review | **Never** as a displayed probability; acceptable only as an internal, non-surfaced tie-break |
| Keep `InMemorySaver` for the E2E demo while `checkpointed_graph` sits built-but-unused | No wiring risk before the demo | The approval artefact is not durable; the resume story is a claim, not a fact | Only if **declared** not-wired (it currently is, `STATUS.md` §7) — never while claiming it works |
| Default the gate to `approve` / one-keystroke confirm | Demo looks fast; fewer clicks | Rubber-stamp; a 0% override rate that *looks* like success | **Never** for a defaulted approve; a typed, explicit decision with evidence shown is fine |
| Emit spans from a helper *beside* `store/audit.append` | One line; no refactor of the interceptor | Two truths about what the agent did — a DRY violation with a safety consequence | Never as a **second writer**; acceptable as a read-only **projection** of the audit event stream |
| Un-sampled, full-fidelity spans on the CPU-only host | Simplest tracing config | RAM/latency regression; the "seconds" promise slips; trace bloat | Sampling / bounded buffer is acceptable; un-sampled full fidelity during the model run is not |
| Read the YAML KB from disk on every call | "Always fresh" | A file edited mid-run makes selection non-deterministic; no hashed ruleset in the audit | Only with a per-run ruleset hash recorded (the loader is cached once) |
| Hand-edit `EVALS.md` counts to reconcile 14-vs-16 | Fixes the doc inconsistency in one edit | Presents a hand-typed number as harness output → instant-disqualifier risk | **Never** — regenerate from `report.json` |
| Widen a discriminator alias live to demo extensibility | The one-line edit "looks effortless" | Collision/shadowing silently flips existing colours; the audit can no longer name the ruleset | **Never** without a loader validator + a re-run |

## Integration Gotchas

Common mistakes when wiring the *new* capabilities into the existing seams (each already has a single home in
the frozen v1.0 code — the trap is bypassing it).

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LangGraph `interrupt()` / resume | Placing a side effect (log, counter, "pending" row) **before** `interrupt()` | Keep the gate node side-effect-free; effects belong in the `commit` node that runs once (Pitfall 8) |
| LangGraph `thread_id` | Deriving it from a timestamp / uuid / run index | `thread_id == case_id` (the content hash `case_id_for`) so pause and resume share a thread (Pitfall 9) |
| LangGraph SQLite checkpointer | Reusing `triage.db` for checkpoints | Keep `checkpoints.db` separate from the domain DB (already the design, D-09) — do not "simplify" to one file |
| `langchain.mcp` adapter | Merging the owned (modern) and borrowed (legacy) servers into one `MCPConfig` | Separate adapter contexts (era collapse) — as `mcp/adapter.py` already does |
| Ollama structured output | Asking the model for a confidence number or a colour | Confidence comes from deterministic coverage/quality signals; the model only structures/extracts (D-01/D-02) |
| RAG retriever | Letting retrieved free text or the KB hash enter `citations[]` or `score` | Retrieval returns closed-set ids + a rank + `no_match` — the same `MatchResult` contract (Pitfall 1) |
| Trace exporter | Configuring a remote (or localhost-HTTP) exporter inside the agent path | Local-only, sampled, off the hot path; **no network I/O** in the agent path (no-egress) |
| Idempotent commit | Passing a content dict whose keys ≠ `IMMUTABLE_FIELDS` | Pass exactly the immutable fields so an `edit` supersedes rather than duplicates (Pitfall 9) |
| Borrowed SQLite MCP | Calling its write tools directly from a node | The borrowed server is read-only in the agent path; wrap any needed write in an owned audited tool (Pitfall 15) |
| Eval harness / `EVALS.md` | Hand-editing numbers | `scripts/emit_evals.py` (from `report.json`) stays the sole writer |

## Performance Traps

Patterns that pass on the developer's run but fail the "seconds" promise or the RAM budget on the CPU-only host.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-case embedding retrieval on CPU | p50/p95 latency climbs past the "seconds" promise | Precompute/pin embeddings at load; cache; keep the alias matcher as the fast exact path | As the discriminator KB or per-case candidate set grows, or on a model swap |
| Un-sampled spans + local model + recorder co-resident | RAM headroom shrinks; swap; latency up | Sample spans; bounded ring buffer; async/off-hot-path writes | Every call, on the ~0.8–2.3 GB headroom host |
| Runtime calibration sweep | Slow startup / the demo stalls | Calibrate **offline** on a held-out split; ship the fitted mapping as data | On startup if done at runtime |
| Large model on tight RAM | 14–17 s+ per case; swap | Keep the 1.5B default; measure with `ollama ps` before any swap | Already measured (D-03); worsens with tracing/RAG co-resident |
| Replay over unbounded traces | Replay slow; memory spikes | Bounded windows; replay one case/thread at a time | As the trace history grows |
| Two SQLite files (WAL) + model resident | I/O contention; a checkpointer write on the hot path | Single writer; keep checkpoint writes off the scoring path | Under concurrent cases on one CPU host |

## Security Mistakes

Domain-specific issues beyond OWASP basics — here the "attack surface" is mostly the *new capability bypassing
an existing control*, not an external attacker.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Retrieval over untrusted complaint text | Indirect prompt injection steers retrieval into `citations[]` or the colour | The complaint is **data**; retrieval returns closed-set ids only; deterministic tie-break; INV-1 extension; keep enforcing E-13/E-14 |
| Trusting the resume payload | A forged/malformed approval commits a queue write | Validate with a typed `response_schema`; the gated tool already refuses a malformed token (defence in depth) |
| Raw complaint/prompt in span attributes or trace files | PII-shaped leakage; if ever exported → egress / data-residency breach | Hash/redact/summarise; keep ids, counts, colours, rule-ids, timings only; local-only exporter (Pitfall 10) |
| Borrowed MCP write tools reachable in the agent path | Un-audited, un-gated change to `triage.db` | Read-only borrowed posture; tool allowlist + statement guard; one audited write path (Pitfall 15) |
| Live YAML edit outside review | Silent invariant break; id/alias collision; the audit can't name the ruleset | Loader validator fails closed; versioned + hashed ruleset recorded; post-edit smoke run (Pitfall 12) |
| Confidence shown as a clinical probability | Over-trust; an indefensible percentage; false precision | Advisory coverage/quality signal only; never a percentage (Pitfall 5) |
| Chain-head truncation via replay/backfill | A shorter but *valid* chain hides deletions | Persist the chain head (already done); `verify()` compares to the persisted head; re-run after any replay/backfill |
| World-readable `checkpoints.db` / trace on a shared desk terminal | Leakage of synthetic-but-PII-shaped fixtures; tampering | Local file permissions; synthetic-only fixtures; real data never enters the machine |

## UX Pitfalls

The desk card and the gate are the two human surfaces this milestone adds; both are automation-bias surfaces.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Colour rendered without adjacent citations | The nurse cannot audit it; the automation-bias precondition | Citations next to the colour, rendered from the locked `HandoverCard` (Pitfall 11) |
| Confidence percentage on the card | Over-trust; false precision | "SUGGESTED: ORANGE — you decide" + a coverage/quality signal ("no discriminator matched") |
| "Approve" default-highlighted / one-keystroke | Rubber stamp | No default approve; edit/dismiss one action away; evidence shown between reviewer and decision (Pitfall 7) |
| No-match banner buried in JSON | Under-triage missed under queue pressure | Loud "**NO DISCRIMINATOR MATCHED — nurse to confirm**" banner (U4) |
| Generic abstention copy ("low confidence") | Unactionable; contributes to alert fatigue | Name the missing vital / unmatched complaint **and** the next step ("re-measure temperature") |
| Vitals entry auto-fills a missing vital | Imputes a value; violates the never-impute rule | Leave blank + prompt; reuse the schema's physiological bounds (which reject °F magnitudes) |
| Card reads as a verdict ("ORANGE — confirmed") | Over-trust; erodes the human's authority | Frame as a proposal; no "confirmed"/"final" wording |
| Model latency hidden behind the deterministic path | The nurse is unsure whether to wait | Show the fast deterministic result; state the model latency honestly (U3) |
| Gloved / one-handed entry assumed away | Unusable at the desk | Keypad-friendly, large targets, numeric-first entry (U5/U6) |
| English-only copy unaddressed | Exclusion at an African desk | Declared scope (D8), but avoid idioms and keep copy plain |

## "Looks Done But Isn't" Checklist

Things that appear complete in a demo or a green test but are missing the load-bearing piece.

- [ ] **RAG grounding:** Often missing a *held-out* vague case — verify retrieval passes a case authored but never iterated against, not just E-09, and that retrieval returns only closed-set ids (no colour, no free text).
- [ ] **Calibrated confidence:** Often missing ECE / a reliability curve and a held-out calibration split — verify calibration is **measured**, and the threshold is derived from a stated cost, not a hand-picked 0.5.
- [ ] **Abstention:** Often missing the *deferral rate* as a reported number — verify the rate is reported, and a no-match case shows a flag, not a confident bare colour.
- [ ] **Gate interaction:** Often missing a real override in the demo — verify the override rate is reported (0% is a warning, not a win) and edit/dismiss are one action away.
- [ ] **Durable checkpoints:** Often "built but not wired" — verify the E2E entry points (`runner.py`, `demo/run.py`) actually use `checkpointed_graph`, with a restart-between-pause-and-resume test.
- [ ] **Resume idempotency:** Often only the `approve` path is tested — verify an **edit**-resume yields one row updated (not two) and exactly one `commit_priority` audit record.
- [ ] **Replay safety:** Often re-runs the graph — verify replay adds zero queue rows and zero commits (no-op commit injection), and the replayed colour equals the original.
- [ ] **Tracing derivation:** Often a second writer — verify spans derive from the audited interceptor and contain no raw complaint/prompt.
- [ ] **Desk card:** Often a new render path — verify it renders from the locked `HandoverCard` and INV-3 scans the rendered strings.
- [ ] **Live rule edit:** Often unvalidated — verify duplicate/collision fails closed, the ruleset is hashed into the audit, and the safety suite is re-run after the edit.
- [ ] **Borrowed MCP beyond query:** Often a hidden write — verify every borrowed call in the agent path is read-only and no un-audited write path exists.
- [ ] **Docs honesty:** Often hand-edited — verify `EVALS.md` is regenerated from `report.json` and the README is literally one command.

## Recovery Strategies

When a pitfall lands despite prevention — the cheapest reversal first, and the invariant to re-assert.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| RAG became a second colour path (P1) | MEDIUM/HIGH | Revert retrieval out of `score`; restore the `MatchResult` contract; re-run INV-1 + the guard test; re-run the suite |
| Deceptive grounding / wrong-rule citation (P2) | MEDIUM | Bind each citation to the fired rule's id; add the applicability check; report coverage; re-run |
| E-09 tuned green (P3) | HIGH | Revert the alias/expected-colour edit; regenerate `EVALS.md` from `report.json`; re-declare E-09 honestly; commit the rationale |
| Non-deterministic retrieval (P4) | MEDIUM | Pin/local embeddings; deterministic tie-break; restore `matched_set_stable`; re-run 3× and report |
| Miscalibrated / overconfident (P5) | MEDIUM | Recalibrate offline; remove any percentage; fall back to the coverage signal; report ECE + risk–coverage |
| Abstain-too-often (P6) | LOW/MEDIUM | Re-derive the threshold from the stated cost; make the copy specific; report the deferral rate |
| Rubber-stamp gate (P7) | MEDIUM | Re-order affordances (no default approve); require evidence shown; report the override rate |
| Duplicate audit/write on resume (P8) | HIGH | Move the effect after `interrupt()`; verify the chain still validates; re-issue the idempotent commit; add the exactly-one test |
| Wrong-thread / key-breadth edit duplicate (P9) | HIGH | Fix `thread_id == case_id`; widen the key to `IMMUTABLE_FIELDS` / `(case_id, decision_id)`; `reconcile()`; test edit-resume |
| Divergent second log (P10) | MEDIUM | Delete the second writer; derive spans from the audit stream; add an equality assertion in a test |
| Leaked / egress trace (P10) | HIGH | Disable the exporter; purge local trace files; re-run the no-egress (`strace`) check before the demo |
| Colour without citations on the card (P11) | MEDIUM | Render from `HandoverCard`; extend INV-3 to the rendered strings; re-run |
| Live edit broke an invariant (P12) | MEDIUM | Revert the YAML; re-hash the ruleset; re-run the safety suite + one colour case; re-declare the edit |
| Replay re-committed (P14) | HIGH | Remove the spurious row via the idempotent path (never a second ad-hoc write); assert replay is read-only; add the zero-write test |
| Borrowed MCP un-gated write (P15) | MEDIUM/HIGH | Restore the read-only borrowed posture; audit the affected table; wrap any needed write in an owned audited tool |

## Pitfall-to-Phase Mapping

How the roadmap phases should address these pitfalls. The **capability labels** above are stable; the roadmapper
re-maps them to its own phase numbers.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1 RAG second colour path | P-RAG | Guard test: retrieval output contains no colour and no non-declared id; INV-1 extended |
| P2 Deceptive grounding | P-RAG / P-Eval | Citation `rule_id` == the fired rule id; per-case coverage reported |
| P3 E-09 tuned green | P-RAG / P-Docs | Unchanged E-09 case passes **and** a held-out vague case passes; `EVALS.md` regenerated from `report.json` |
| P4 Non-deterministic retrieval | P-RAG / P-Eval | `matched_set_stable` true across 3 runs; embeddings pinned/local; `kb_hash` recorded |
| P5 Overconfident confidence | P-Eval / P-UX | ECE / reliability measured on a held-out split; no-match is low-coverage; no percentage on the card |
| P6 Abstain-too-often | P-Eval / P-UX | Deferral rate reported; reason names the missing vital/next step; out-of-scope abstention stays categorical |
| P7 Rubber-stamp gate | P-Gate / P-Demo | Override rate reported; demo shows a disagreement-capable decision; edit/dismiss one action away |
| P8 Duplicate side effects on resume | P-Ckpt | E2E resume test: exactly one `commit_priority` audit record and one queue row |
| P9 Wrong thread / key-breadth edit | P-Ckpt / P-Gate | `thread_id == case_id`; edit-resume writes one updated row, not two |
| P10 Divergent / leaking / bloating trace | P-Trace | Spans derive from the audited interceptor; no complaint/prompt in attributes; sampling on; no-egress re-check |
| P11 Colour without citations on the card | P-UX / P-Eval | Card renders from the locked `HandoverCard`; INV-3 scans the rendered strings |
| P12 Live edit breaks an invariant | P-Live / P-RAG | Loader validator fails closed on collision/duplicate; ruleset hashed into the audit; post-edit smoke run |
| P13 DRY/SOLID erosion | All | OCP test ("added as data or new tool+node, working code untouched"); `test_purity` / `test_no_duplicated_sats` / `test_graph_purity` green |
| P14 Replay re-commits | P-Trace / P-Ckpt | Replay of an approved case adds zero rows + zero commits; replayed colour == original |
| P15 Borrowed MCP un-gated write | P-MCP / P-Ckpt | Borrowed tools read-only in the agent path; allowlist + statement guard; `reconcile()` backstop |

## Sources

**Project-internal (HIGH — read directly this session):**

- `src/triagedesk/graph/{build,nodes,state}.py` — the gate/commit node boundary, `checkpointed_graph`, `TRACER_NODES`.
- `src/triagedesk/store/{audit,queue}.py` — the one audit chain + append path; the idempotency key over `IMMUTABLE_FIELDS`.
- `src/triagedesk/mcp/{server,adapter}.py` — the one `audited` interceptor; separate owned/borrowed adapter contexts.
- `src/triagedesk/core/{scorer,matcher,citations,schema}.py` — single colour producer; closed-set discriminator matcher; the locked `HandoverCard`.
- `src/triagedesk/evals/invariants.py` — INV-1..INV-4 as executable predicates.
- `src/triagedesk/llm/client.py` — structured-output extraction; no model-computed numbers.
- `EVALS.md`, `STATUS.md`, `.planning/PROJECT.md`, `docs/{DECISIONS,ROADMAP}.md` — the frozen reality and the declared gaps.

**External (verified this session — HIGH):**

- Caruzzo, Yoo, Kim, **"Deceptive Grounding: Entity Attribution Failure in Clinical Retrieval-Augmented Generation"**, arXiv:2607.09349 (Jul 2026; accepted NeurIPS 2026) — a response can pass hallucination, faithfulness, and citation checks while attributing another entity's real evidence to the queried one; entity-attribution verification is the missing check. Basis for **P2**. <https://arxiv.org/abs/2607.09349>
- **"Conformal selective prediction with cost aware deferral for safe clinical triage under distribution shift"**, *Scientific Reports* (Feb 2026), doi 10.1038/s41598-026-40637-w — the deferral threshold is selected by minimising an explicit asymmetric clinical cost (FN 10 · FP 1 · deferral 2); ECE and a risk–coverage profile are the headline, not accuracy. Basis for **P5/P6**. <https://www.nature.com/articles/s41598-026-40637-w>
- **"An Empirical Analysis of Calibration and Selective Prediction in Multimodal Clinical Condition Classification"**, arXiv:2603.02719 (May 2026) — aggregate ECE can look low while class-dependent miscalibration makes selective prediction fail precisely on the underrepresented, clinically-important class. Basis for **P5**. <https://arxiv.org/abs/2603.02719>
- Goddard, Roudsari, Wyatt, **"Automation bias: a systematic review of frequency, effect mediators, and mitigators"**, *JAMIA* 19(1):121 (2011) — clinicians may reverse a *correct* decision after wrong advice; mitigators include accountability, the on-screen position of advice, and information-vs-recommendation framing. Basis for **P7/P11**. <https://academic.oup.com/jamia/article/19/1/121/732640>
- **"ICAN-Deploy: Identity-Stable Canary Deployment for Safety-Critical Embodied Agents"**, arXiv:2605.28097 (May 2026) — a runtime config change can break "the agent you certified is still the agent you have" unless identity is held invariant (frozen, hashed names; mutable versions). Basis for **P12** (the live rule edit must preserve a stable, hashed ruleset identity). <https://arxiv.org/abs/2605.28097>

**External (carried from the v1.0 research at tag `v1.0-submission`; MEDIUM — not re-verified this session):**

- OpenTelemetry documentation on handling sensitive data — data minimisation for span attributes.
- Feature-flag / configuration-as-code governance guidance — runtime toggles need RBAC, an audit trail, and change control, not just a data edit.

---

*Pitfalls research for: adding seven capabilities to the frozen, safety-critical TriageDesk triage agent (v1.1 Score Uplift)*
*Researched: 2026-10-10*
