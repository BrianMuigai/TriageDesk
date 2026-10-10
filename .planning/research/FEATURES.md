# Feature Research — v1.1 Score Uplift (new capabilities)

**Domain:** Clinical triage-support / clinical decision support (CDS) agent for a nurse-led outpatient triage desk
**Researched:** 2026-10-10
**Confidence:** MEDIUM–HIGH — the frozen v1.0 implementation and its docs were read directly (HIGH); external
best-practice claims were gathered by web search and are **LOW**, rising to **MEDIUM** where official docs
(LangChain/LangGraph, OTel GenAI) or peer-reviewed sources agree, per the `classify-confidence` seam.

> **Scope note (subsequent milestone).** This file covers **only the seven new capabilities** in the v1.1
> milestone. The existing v1.0 features — deterministic cited SATS/TEWS scoring, the 5 owned MCP tools, the
> borrowed SQLite MCP, the LangGraph approval gate, the hash-chained audit, deterioration re-check, missing-vital
> recovery + safe abstention, the local open-weights model, and the 14-case honest evaluation (incl. declared
> failure E-09) — are **frozen and not re-researched here**. The earlier landscape (`archived v1.0` research)
> remains valid background. This file answers: *for each new capability, what does "expected behaviour" mean,
> what is table-stakes vs differentiator vs anti-feature **for a trustworthy, safety-critical triage agent**,
> and how does it fit the triage desk (the 20-point criterion) and safety?*

---

## 0. The lens: what "trustworthy + fit-to-desk" demands

Two facts from the frozen work frame every new capability:

1. **Under-triage is the dangerous error, and vague complaints are where it hides.** The declared failure
   E-09 ("feeling unwell" + known diabetic → under-triaged) is a *retrieval* failure: the deterministic alias
   matcher (`core/matcher.py`) needs an exact token sequence, so a vague complaint matches nothing and the
   system falls back to a low-acuity vitals-only colour. The matcher **deliberately** excludes "feeling unwell"
   so E-09 cannot be tuned green by adding one alias (`data/sats_discriminators.yaml` comment). Any RAG fix must
   therefore be a *real* retrieval improvement, not a keyword patch.
2. **The score is deterministic and sourced; the risk is at the edges, not the core.** The TEWS/override
   scorer (`core/scorer.py`) is pure and cited. The new capabilities all live at the **edges** — retrieval,
   uncertainty, the human surface, runtime durability, observability. Each must *strengthen* the frozen spine
   without adding a path that can set a colour silently, break reproducibility, or egress data.

The `STATUS.md` "fit to triage desk" line (estimated **7–12 of 20**) is capped by: no clinician interview (G2,
out of scope to fix here), **no desk surface** (U1), a **hardcoded** approval value (U2), **un-surfaced
uncertainty** (U4), and **14–17 s** latency (U3). The new capabilities that move this number are the card (3),
the real gate (4), and the no-match banner (5). RAG (1), calibrated confidence (2), durable checkpoints (6),
span tracing (7), and the live-rule demo (8) move **agentic depth (JC-1, 30 pts)**, **evaluation & reliability
(JC-4)**, **defensibility (JC-5)**, and **live-review readiness (ST-1)**.

### What a 2026 trustworthy triage agent is *expected* to do (the baseline)

Across CDS design literature (the CDS "Five Rights", automation-bias/alert-fatigue findings already documented
in the v1.0 research) and current selective-prediction work, a *trustworthy* agent at the point of care is
expected to: **(a)** ground every claim in a retrievable, attributable source; **(b)** know and *say* when it
does not know, and defer rather than guess; **(c)** keep the human the actor — information, not a verdict;
**(d)** survive audit (reproducible, replayable, tamper-evident); and **(e)** fit the workflow (seconds, legible,
one-handed). The seven capabilities map almost one-to-one onto (a)–(e). That is the standard this file holds
each feature to.

## 1. Capability landscape (one table per capability)

Each capability is graded **Table stake** (expected; missing ⇒ unsafe/incomplete), **Differentiator** (sets the
trustworthy agent apart; where v1.1 competes), or **Anti-feature** (looks good, actively harmful — do not build).
Complexity is rated for this solo, ~6-day, CPU-only build. Dependencies reference frozen v1.0 modules.

### 1.1 Retrieval-grounded knowledge (RAG) over the SATS KB — the honest fix for E-09

**Expected behaviour.** The presenting complaint is retrieved *against* the closed SATS discriminator KB, and
retrieval returns **attributable evidence** — a ranked set of discriminator ids (each already carrying its
category, colour and citation) plus a similarity/coverage signal — **not** generated prose. Retrieval happens
**instead of, or in front of**, the exact-token matcher; the deterministic scorer still owns the colour, so a
retrieved id can only ever *raise* acuity (override), never silently lower it. The retrieval result is recorded
in provenance (model + KB + threshold hashes), so the run stays reproducible.

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Closed-set retrieval** — retrieval output is ids drawn from `data/sats_discriminators.yaml` only, each carrying its citation | MEDIUM | Depends on frozen `core/matcher.py` + `core/rules.py`; the closed set is the safety property that makes retrieval "grounded". |
| Table stake | **Retrieval never sets the colour** — it feeds `matched_discriminator_ids` into the existing scorer | LOW | Reuses `score_priority`'s override path unchanged; keeps D-01/D-02 intact. |
| Table stake | **Attributable evidence on the card** — the card shows *which* KB entry matched and *why* (alias/score), not just an id | LOW | Depends on capability 3 (card). |
| Differentiator | **Hybrid retrieval** — exact alias match first, then *thresholded* local embedding similarity over discriminator labels/aliases (catch vague complaints like "feeling unwell") | MEDIUM–HIGH | Local embedding model via Ollama (no egress); pin + hash it. Adds one node/tool (`retrieve_discriminators`). |
| Differentiator | **Similarity threshold with fail-safe** — below threshold ⇒ return `no_match` (feed the banner), never pick a weak top-1 | MEDIUM | The honest close of E-09: vague complaint ⇒ flagged, not silently under-triaged. |
| Differentiator | **E-09 flips from declared failure to a *measured pass or a flagged defer*** | MEDIUM | Requires re-running the measured suite; either outcome is defensible if retrieval is real. |
| Differentiator | **Second borrowed MCP server (vector/graph KB)** used for retrieval | HIGH | Exercises the under-used borrowed-server surface (STATUS G7) *and* delivers RAG; but adds a dependency + local-embedding plumbing. Weigh vs in-repo hybrid. |
| Anti-feature | **Generative RAG** — the model writes a "relevant guidance" paragraph | — | Reintroduces hallucination on the safety path; clinical RAG literature shows hallucination *rising* with context churn ("grounded but misguided"). Cite, don't compose. |
| Anti-feature | **Unthresholded semantic top-1** — always return the nearest discriminator | — | A vague complaint would force a spurious override; worse than no match. |
| Anti-feature | **Tuning E-09 by adding a literal alias** ("feeling unwell" → diabetes id) | LOW | Dodges the real fix and defeats the declared-failure honesty; the YAML comment explicitly forbids it. |
| Anti-feature | **"Similar historical cases" advice** | — | Implies diagnosis/prognosis from priors; outside SATS and forbidden (SN-1). |

**Safety:** retrieval must be **monotone-safe** — it can only add evidence. Any low-confidence retrieval must
**degrade to the banner + human confirm**, never to a lower colour. **Fit to desk:** turns the scariest failure
mode (vague complaint under-triage) into a visible flag the nurse acts on.

### 1.2 Calibrated confidence + abstention (selective prediction)

**Expected behaviour.** The agent exhibits a **coverage/uncertainty signal** that is **honest, source-based, and
routing-changing**: it is composed from things the system actually knows — did a discriminator match? how strong
was the match? were all scored vitals present? — and it *changes behaviour* (route to banner, abstain, or ask).
It is **not** a fabricated clinical probability. Where the frozen system already abstains on paediatrics, this
generalises abstention to the vague-complaint / weak-match class.

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **A single, typed coverage/uncertainty field** on the priority result (e.g. `discriminator_coverage: matched\|weak\|none`), derived deterministically | LOW | Extends `PriorityResult` / `MatchResult`; one new field, one new derivation helper. |
| Table stake | **Uncertainty drives routing** — `none`/`weak` forces the human-confirm path, not a silent colour | MEDIUM | Depends on the banner (1.4) + gate (1.3). |
| Table stake | **No pseudo-probability shown as clinical risk** — bands/wording, never "87% sure this is ORANGE" | LOW | Matches the v1.0 anti-feature ruling; an uncalibrated number invites automation bias. |
| Differentiator | **Selective-prediction framing measured on the eval set** — report *coverage* vs *under-triage* (a risk–coverage view), not just accuracy | MEDIUM | Add eval metrics; with 14 cases this is a **declared, small-sample** measure (honesty > precision). |
| Differentiator | **Abstention extends beyond paediatrics** — weak/no match + chronic condition ⇒ ask/confirm rather than score silently | MEDIUM | The E-09 class; complements RAG (retrieval improves match, confidence decides when to defer). |
| Differentiator | **Calibration is *declared*, not faked** — if a numeric confidence is shown, ECE/reliability is declared unmeasurable at this data scale | LOW | Peer-reviewed triage work pairs calibration with conformal/deferral; we state the limitation. |
| Anti-feature | **Softmax/temperature "confidence" from the LLM** | MEDIUM | LLM self-reported confidence is famously miscalibrated (overconfident); it would mislead. |
| Anti-feature | **Confidence that never changes the outcome** | LOW | Decorative confidence erodes trust; it must gate/flag or it is noise. |
| Anti-feature | **Suppressing a real finding behind "low confidence"** | — | A low score must never *hide* a high-acuity vital; confidence speaks only to *discriminator match*, not to TEWS. |

**Safety:** the confidence signal must be **conservative about urgency** — it may escalate to "confirm", never
downgrade a scored colour. **Fit to desk:** replaces "the machine is sure" with "the machine shows its working
and its doubt", which is exactly the automation-bias mitigation the desk needs.

### 1.3 Desk-facing UX — human-readable priority card

**Expected behaviour.** A nurse sees a **glanceable, colour-coded card** that reads `SUGGESTED: ORANGE · < 10 min ·
why: RR 24 + HR 118 + T 38.9`, with citations adjacent to the evidence and the word **SUGGESTED** (information,
not a verdict). The card is rendered from the existing typed `PriorityResult` / `HandoverCard` — no new clinical
logic — and is legible under queue pressure.

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Human-readable card** (colour + target time + “why” vitals + citations), replacing the raw JSON dump | LOW–MEDIUM | Pure rendering of frozen `PriorityResult`/`HandoverCard`; `rich` is already a transitive dep. No number is invented. |
| Table stake | **“SUGGESTED” framing, not a verdict** | LOW | The card is advice the nurse confirms; wording is a safety feature, not polish. |
| Table stake | **Citations adjacent to the colour** (automation-bias mitigation) | LOW | Reuses the frozen `citations[]`; keeps the "information over verdict" rule. |
| Table stake | **Handles all terminals legibly** — RED/GREEN/ABSTAIN/RECOVER/recheck all render as cards, not crashes/raw states | LOW | Covers `escalate`/`request_missing_info`/`second_look` terminals. |
| Differentiator | **Desk-grade ergonomics** — large colour block, one-line “why”, big approve affordance, keyboard-first | MEDIUM | Directly attacks U1/U5/U6; `rich`/`textual` surface. |
| Differentiator | **Latency honesty on the card** — show the instant deterministic score and the model’s measured cost separately | LOW | Attacks U3; "seconds" claim becomes honest. |
| Anti-feature | **Verdict framing** (“this patient *is* ORANGE”) | LOW | Encourages automation bias; the nurse is the decision-maker. |
| Anti-feature | **A pretty JSON viewer** | LOW | Not a desk surface; still requires terminal literacy. |
| Anti-feature | **Hiding the failure case from the card** | — | The demo/card must still surface E-09; hiding it forfeits reliability points. |

**Safety:** the card is the *last human-readable gate before a queue write*; it must be impossible to commit
from it without an explicit decision (see 1.4). **Fit to desk:** this is the highest-leverage UX item for the
20-point criterion — it converts "a prototype/terminal storyboard" (STATUS §6) into something a nurse could touch.

### 1.4 Real approve / edit / dismiss gate interaction (no hardcoded value)

**Expected behaviour.** The approval gate is a **real prompt** at the desk: it shows the SUGGESTED priority and
its evidence, then takes an explicit decision — **approve / edit (choose a different colour) / dismiss** — with a
**named approver and role**, and **it writes nothing** until that decision arrives. The frozen graph already
supports all three decisions (`ApprovalToken` with `decision ∈ {approve, edit, dismiss}`, `final_colour`
validated against the loaded colour set) and the gate is side-effect-free before `interrupt()` — the gap is
purely that the demo **hardcodes approve** (U2).

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Real interactive prompt** — no defaulted/hardcoded value; the operator chooses | MEDIUM | Depends on frozen `approval_gate` (`graph/nodes.py`) + card (1.3). Do NOT put a side effect before `interrupt()` (a resumed node re-runs from the top — frozen D-04 rule). |
| Table stake | **Named approver + role captured** and echoed on the card/audit | LOW | Reuses `ApprovalToken`; the audit already records `approved_by`/`role` on a committed token. |
| Table stake | **Dismiss writes nothing** | LOW | Already true (`commit_priority` refuses `dismiss`); the UI must make it reachable and observe the zero-row delta. |
| Table stake | **Edit path validated** — an edited colour must be a declared colour and is the committed colour | LOW | Frozen `final_colour` validator; the UI must supply it, and the audit shows an `edit` decision. |
| Differentiator | **Evidence-forward gate** — the prompt re-shows citations so the decision is informed, not a rubber stamp | LOW | Complements the card; counters the "hardcoded approve reads as a rubber stamp" finding (U2). |
| Differentiator | **Gate latency/ergonomics** — a nurse can confirm in ~1 keystroke while staying in flow | LOW–MEDIUM | Ties to the desk criterion; keyboard-first. |
| Differentiator | **Rehearsed double-beat demo** — same case commits under a named nurse *and* refuses without one | LOW | Already a storyboard beat; make the *interaction* live in the recording. |
| Anti-feature | **Default-Yes / pre-filled approve** | LOW | The classic automation-bias trap; turns the gate into a rubber stamp. |
| Anti-feature | **Single OK button** with no edit/dismiss | LOW | Removes the clinician’s authority to disagree; editorially weak vs the brief ("approve/edit/dismiss"). |
| Anti-feature | **Auto-commit on timeout** | — | An unattended write to a queue is the disqualifier (SN-3/DQ-3). |
| Anti-feature | **Storing the decision in the card schema** | LOW | Keep the decision in the approval/audit path, not the clinical card (field-set lock, SAFE-02). |

**Safety:** the gate is *the* safety mechanism; making it interactive must **not** weaken the machine gate — the
token validation stays the enforcement, the prompt is only the human side. **Fit to desk:** the second half of
the 20-point UX story; "the approval *interaction* is not designed" (U2) is the exact gap.

### 1.5 Loud “no discriminator matched / low confidence — nurse to confirm” banner

**Expected behaviour.** When retrieval/matching yields nothing (or only a weak match), the tool raises an
**unmissable, distinct warning** that fuses capability 1 (no match) and capability 2 (low confidence), **names
what is unknown**, and **forces a nurse confirmation** before the priority is treated as final. It is a
first-class surface, not a boolean buried in JSON (`no_discriminator_matched: true` is currently buried — U4).

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Loud, distinct banner** — different colour/placement from the normal card | LOW | Depends on capability 2 (the signal) and 3 (the surface); reuses `no_discriminator_matched` + new coverage field. |
| Table stake | **Names the gap** — "no discriminator matched for this complaint — check for X / confirm priority" | LOW | The frozen `MatchResult.warning` already carries a data-driven message. |
| Table stake | **Forces confirmation** — the gate cannot be an unqualified approve while the banner shows | MEDIUM | Routing: weak/none ⇒ nurse-confirm path. |
| Differentiator | **Degrades to a clarifying question** for the E-09 class (vague complaint + chronic condition) | MEDIUM | The EVALS §6 "what we would try next" #1; pairs with abstention. |
| Differentiator | **Becomes a measured eval outcome** — the banner/no-match path is a first-class test case, not a hidden branch | LOW | Converts E-09 from "declared failure" to "declared *handled* uncertainty". |
| Anti-feature | **Muted/subtle indicator** (a grey note, a JSON flag) | LOW | Defeats the purpose; the whole point is a nurse cannot miss uncertainty (U4). |
| Anti-feature | **Over-alerting** — banner on every case | LOW | Alert fatigue → reflexive dismissal (v1.0 anti-feature). Fire it only on genuine weak/no match. |
| Anti-feature | **Auto-low-acuity fallback when nothing matches** | — | This *is* the E-09 bug; the banner replaces it with explicit uncertainty. |

**Safety:** the banner is the human-facing expression of abstention; **fit to desk:** it is the trust-building
cue that says "this tool knows what it doesn’t know".

### 1.6 Durable / resumable execution (LangGraph checkpoints wired E2E)

**Expected behaviour.** A case that pauses at the approval gate **survives a process restart**: the paused state
is read back from `checkpoints.db`, resumed with the clinician’s decision, and completes **to the same decision
with no duplicate queue write**. The saver (`AsyncSqliteSaver` via `checkpointed_graph`) and the serializer
allowlist already exist — the gap is that the E2E path uses `InMemorySaver` (`evals/runner.py`, `demo/run.py`)
and never exercises durability (STATUS §7).

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Paused case resumes after restart** — reopen `checkpoints.db`, see the pending interrupt, resume | MEDIUM | Wire frozen `checkpointed_graph` into the demo/CLI path; a documented `thread_id` scheme. |
| Table stake | **Separate checkpoint DB from the audit/domain DB** | LOW | Frozen D-09 rule; runtime state ≠ clinical record. Do not merge. |
| Table stake | **No duplicate queue write on resume** | LOW | Already guaranteed by the idempotent `commit_priority` key (case_id + content hash). |
| Differentiator | **A resume CLI subcommand** (`triagedesk resume <thread_id>`) + documented restart story | MEDIUM | Makes durability *demonstrable* in the live review/demo. |
| Differentiator | **Reconcile on resume** — the frozen `reconcile()` proves the queue and audit agree after a crash | LOW | Reuses `store/audit.reconcile`; strong defensibility beat. |
| Anti-feature | **One DB for checkpoints + audit** | LOW | Conflates immutable record with disposable state (DRY ambiguity); frozen decision forbids it. |
| Anti-feature | **“Durable” that only means in-memory + retry** | LOW | Doesn’t survive restart; not durable. |
| Anti-feature | **Resume that re-scores/re-runs the model** | MEDIUM | Re-runs may differ (non-reproducible); resume must replay the *checkpointed* state. |
| Anti-feature | **Unbounded checkpoint retention** | LOW | Disk growth + patient-state sprawl; define a retention/cleanup policy. |

**Safety:** durability protects the *human gate* — a crash mid-decision must not lose the pending case or write
it unapproved. **Fit to desk:** a desk tool that loses a paused patient on restart is unusable; this is a
prerequisite for any real deployment claim.

### 1.7 Span-based tracing + replay

**Expected behaviour.** Every case produces a **local, structured trace** of spans (node → tool call → model
call) carrying inputs, outputs, timing and hashes, so a reviewer can **replay** a run deterministically from the
recorded checkpoint/trace. It must stay **on-machine** (no egress) and must not re-run the model on replay.

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Per-case, per-node span records** (name, start/end, inputs, outputs, hashes) | MEDIUM | Sits on top of the frozen audit (`store/audit`) and the graph nodes; one JSONL/OTel-style sink. |
| Table stake | **Local-only** — no SaaS egress (no LangSmith cloud) | LOW | Egress violates BW-6/residency; use local OTel/Langfuse-local or a JSONL span file. |
| Table stake | **Replay reads recorded state**, does not re-call the model | MEDIUM | Depends on checkpoints (1.6); replay of a checkpoint is deterministic; re-running the model is not. |
| Differentiator | **Trace → demo/review artifact** — show the span tree for one case on screen | LOW | Makes "agentic depth" visible (JC-1) and the walkthrough vivid (ST-1). |
| Differentiator | **Diff two runs** (e.g. before/after the E-09 fix) from their traces | MEDIUM | Converts "reproducible" into "provably changed". |
| Differentiator | **OTel GenAI semantic conventions** — emit standard attribute names so an external collector *could* consume them | MEDIUM | Future-proofs without adding egress now. |
| Anti-feature | **Cloud tracing SaaS (LangSmith/cloud Langfuse)** | LOW | Egress of clinical (even synthetic) traces; fails residency. LangSmith Studio is local but still LangChain-ecosystem-bound — prefer local OTel. |
| Anti-feature | **“Replay” that re-runs the model** | MEDIUM | Non-deterministic; can silently disagree with the recorded decision. |
| Anti-feature | **Tracing that captures raw complaint text to an external system** | LOW | Untrusted-input + privacy surface; keep it local. |
| Anti-feature | **Spans with no join key to the audit/case** | LOW | Unreplayable; every span must carry `case_id`/`thread_id`. |

**Safety:** a trace must be **read-only and tamper-consistent** with the audit; it must never become a second
source of truth for the colour. **Fit to desk:** not a nurse-facing feature — it earns **defensibility (JC-5)**
and **agentic depth (JC-1)** points and makes the live review walkable.

### 1.8 Live technical review readiness — add a SATS rule live (YAML) and re-score

**Expected behaviour.** Adding a discriminator (or band) is a **one-line YAML edit** that the loader validates,
that flows into matching/scoring with no code change, and from which a **re-score is shown live**. The change is
visible in the run’s provenance (KB hash), so the audit shows the rule version that produced a decision.

| Class | Feature | Complexity | Notes / dependency |
|-------|---------|------------|--------------------|
| Table stake | **Rule/discriminator is data, not code** | LOW | Frozen D-11: rules live in `data/*.yaml`, read only via `core/rules.py`. |
| Table stake | **Validating loader** — a malformed YAML rule fails loudly, not silently ignored | LOW | `core/rules.py` Pydantic-validates; add a coverage test for new entries. |
| Table stake | **Re-score after the edit** — the same case re-runs and the audit shows the new KB hash | LOW | Depends on provenance hashing (frozen D-17). |
| Differentiator | **A rehearsed 60-second live-demo script** — add a discriminator, run one case, show the colour move | LOW | Directly targets ST-1 ("a new requirement added live"); currently unrehearsed (G6). |
| Differentiator | **Change is visible + reversible** — the KB hash names the version; revert is one edit | LOW | Defensibility; pairs with tracing (1.7). |
| Anti-feature | **Editing code to add a rule** | LOW | Defeats the data-driven design and the live-review story. |
| Anti-feature | **Editing the human-readable `docs/SATS.md` as if it were the rule source** | LOW | Creates a second authority (violates CONVENTIONS §1 single-source rule); the YAML is the machine authority. |
| Anti-feature | **Un-validated YAML** — a typo silently drops a rule | LOW | Silent rule loss on a safety path; the loader must reject it. |

**Safety:** data-driven rules keep the change *reviewable by a clinician* and *hashable*; the live edit is safe
because the deterministic scorer, not the model, consumes it. **Fit to desk / review:** the cheapest capability
to build and the one most directly tied to the scored Stage-2 criterion (ST-1) — high value per unit of effort.

---

## 2. Consolidated view

### 2.1 Table stakes (all seven capabilities) — missing one makes the tool unsafe or incomplete

| Feature | Why expected | Complexity |
|---------|--------------|------------|
| Closed-set, cited retrieval (RAG) | Grounding is the precondition for trust; an ungrounded retrieval is a hallucination vector | MEDIUM |
| Typed, honest uncertainty signal that changes routing | Selective prediction: a trustworthy agent knows when it doesn’t know | LOW–MEDIUM |
| Human-readable, colour-coded “SUGGESTED” card with adjacent citations | The only sane point-of-decision surface; verdict framing invites automation bias | LOW–MEDIUM |
| Real approve/edit/dismiss prompt with a named approver; nothing written before the decision | The brief’s non-negotiable (SN-4/SN-3); the frozen machine gate is not the human interaction | MEDIUM |
| Loud “no match / low confidence — confirm” banner | Turns the E-09 class into a visible, actionable flag instead of a silent under-triage | LOW |
| Durable, restart-surviving pause with no duplicate write | A desk tool cannot lose a paused patient; the gate must persist | MEDIUM |
| Local per-case spans + deterministic replay | Reproducibility/defensibility; the review must be walkable | MEDIUM |
| Rules in validated YAML with a re-score | Data-driven extensibility is the live-review answer and the SOLID-O design | LOW |

### 2.2 Differentiators (where v1.1 separates a *trustworthy* agent from a generic one)

| Feature | Value proposition | Complexity |
|---------|-------------------|------------|
| Hybrid thresholded retrieval that flips E-09 (or cleanly defers) | The honest fix to the one declared failure; the biggest single capability upgrade | MEDIUM–HIGH |
| Selective-prediction metrics (coverage vs under-triage) reported on the eval | Reliability with an uncertainty story, not just point accuracy | MEDIUM |
| Evidence-forward, one-keystroke gate + desk-grade ergonomics | Moves the 20-pt “fit to desk” number directly | LOW–MEDIUM |
| Uncertainty ⇒ clarifying question / forced confirm | Generalises abstention beyond paediatrics | MEDIUM |
| Resume CLI + reconcile-on-resume | Makes durability demonstrable and audit-consistent | MEDIUM |
| Trace diffing + OTel-GenAI span shape | Proves a change (e.g. the E-09 fix) without re-running the model | MEDIUM |
| Rehearsed 60-second live-rule demo | Highest value-per-effort for Stage-2 (ST-1) | LOW |

### 2.3 Anti-features (do NOT build — they look like progress and are dangerous)

| Anti-feature | Why problematic | Build instead |
|--------------|-----------------|---------------|
| Generative RAG that writes guidance prose | Hallucination on the safety path; clinical RAG can *worsen* groundedness under churn | Cited, closed-set retrieval that only feeds the scorer |
| Any pseudo-probability shown as clinical risk | Uncalibrated numbers invite over-trust; indefensible at 14 cases | Coverage bands / explicit defer |
| Confidence that never changes routing | Decorative trust theatre | A signal that gates the confirm path |
| Default-yes / single-OK gate; auto-commit on timeout | Rubber-stamp / automation bias; unattended write is a disqualifier | Explicit approve/edit/dismiss, no default |
| Auto-low-acuity colour when no discriminator matches | *Is* the E-09 bug | Loud banner + human confirm |
| Cloud tracing SaaS; replay that re-runs the model | Egress violates residency; non-reproducible | Local spans; replay-from-checkpoint |
| One DB for checkpoints + audit; unbounded retention | Conflates record with runtime state; sprawl | Two files (frozen D-9); a retention policy |
| Adding a literal alias to “pass” E-09 | Defeats the declared-failure honesty | Real retrieval + flagged defer |
| Editing code (or `docs/SATS.md`) to add a rule | Two authorities / no data-driven story | Validate the YAML |

### 2.4 Feature dependencies

```
[Local embedding model (pinned+hashed)] ──requires──> [Hybrid discriminator retrieval]
        │                                                     │
        │                                   ┌─────────────────┴─────────────────┐
        ▼                                   ▼                                   ▼
[Closed-set + citation guard]      [Uncertainty / coverage signal] ──drives──> [Loud no-match banner]
        │                                   │                                   │
        └────────────► [score_priority (frozen)] <──────────────┐               │
                                 │                              │               │
                                 ▼                              ▼               ▼
                        [Human-readable card] ──requires──> [Real approve/edit/dismiss gate]
                                 │
                                 ▼
                        [Durable checkpoints E2E] ──enhances──> [Span tracing + replay]
                                                                        │
[YAML rule/band edit] ──feeds──> [Validating loader] ──enhances──> [Provenance hash] ──shown in──> [trace/audit]
```

**Dependency notes.**
- **Retrieval requires a pinned local embedding model:** determinism/reproducibility survives only if the model +
  threshold + KB are hashed into provenance (frozen D-17). Ollama supports local embeddings — no egress.
- **Confidence requires a match-quality signal:** it composes the matcher/RAG output with vital completeness; it
  cannot be a model self-report.
- **The banner requires confidence:** it is the human rendering of the call.
- **The real gate enhances the card:** the card is the evidence; the prompt is the decision.
- **Tracing requires durable checkpoints for replay:** replay reads recorded state, never a fresh model call.
- **The live-rule edit is independent and cheap** — it can ship first with zero new dependencies.
- **Conflicts:** cloud tracing conflicts with no-egress (BW-6); pseudo-probability confidence conflicts with the
  frozen anti-feature ruling; embedding retrieval (fuzzy) conflicts with strict determinism **unless** it is
  thresholded, closed-set, and provenance-hashed.

---

## 3. MVP definition for v1.1

### 3.1 Launch with (P1 — the milestone’s minimum)

- [ ] **Real approve/edit/dismiss prompt** (1.4) — closes U2; the highest-signal safety/UX fix, no new deps.
- [ ] **Human-readable priority card** (1.3) — closes U1; the biggest “fit to desk” mover.
- [ ] **Loud no-match / low-confidence banner** (1.5) + the **typed uncertainty field** (1.2 table-stake row) —
      closes U4 and makes the E-09 class honest.
- [ ] **Durable checkpoints wired E2E** (1.6) — already 80% built (`checkpointed_graph`); just exercise it.
- [ ] **Live YAML rule + re-score rehearsal** (1.8) — the cheapest, most directly-scored Stage-2 item.

### 3.2 Add after validation (P2 — the capability upgrades)

- [ ] **Retrieval-grounded RAG with a similarity threshold** (1.1) — the honest E-09 fix; re-run the measured
      suite and either pass or cleanly defer.
- [ ] **Selective-prediction reporting** (1.2 differentiator) — coverage vs under-triage on the eval set.
- [ ] **Span tracing + replay** (1.7) — local spans, replay from checkpoint.
- [ ] Reconcile the frozen eval optics (README one-command; the 14-vs-16 count) while re-running the suite.

### 3.3 Future consideration (P3 — defer)

- [ ] **A second borrowed MCP server (vector KB)** for retrieval (1.1) — attractive (also addresses G7) but adds
      a dependency and local-embedding plumbing; only if the in-repo hybrid proves insufficient.
- [ ] Online eval / drift monitoring; model routing/caching/budgets for the 14–17 s latency (U3).
- [ ] Multimodal intake (voice / cuff photo) — the real desk UX, but scope-destroying now.

---

## 4. Feature prioritization matrix

| Feature | Desk/trust value | Implementation cost | Judge-criterion leverage | Priority |
|---------|------------------|---------------------|--------------------------|----------|
| Real approve/edit/dismiss prompt | HIGH | MEDIUM | JC-3, JC-6, SN-3/4 | **P1** |
| Human-readable priority card | HIGH | LOW–MEDIUM | JC-3, JC-6 | **P1** |
| Loud no-match / low-confidence banner | HIGH | LOW | JC-3, JC-4, fixes E-09 class | **P1** |
| Typed uncertainty signal + routing | HIGH | LOW–MEDIUM | JC-1, JC-4 | **P1** |
| Durable checkpoints E2E | MEDIUM | MEDIUM | JC-1, JC-5 | **P1** |
| Live YAML rule + re-score rehearsal | MEDIUM | LOW | ST-1 (live review) | **P1** |
| Retrieval-grounded RAG (hybrid, thresholded) | HIGH | MEDIUM–HIGH | JC-1, JC-4, fixes E-09 | **P2** |
| Selective-prediction metrics | MEDIUM | LOW–MEDIUM | JC-4 | **P2** |
| Span tracing + replay | MEDIUM | MEDIUM | JC-1, JC-5, ST-1 | **P2** |
| Second borrowed MCP server (vector KB) | MEDIUM | HIGH | JC-1, G7 | **P3** |
| Model routing / caching / budgets (latency) | HIGH (desk) | HIGH | JC-3, U3 | **P3** |

**Priority key:** P1 = must have for the v1.1 launch; P2 = should have, next; P3 = nice to have / future.

---

## 5. Fit to the triage desk (the 20-point criterion) — mapping

| Desk reality (from STATUS §6) | New capability that addresses it | Residual risk |
|-------------------------------|----------------------------------|---------------|
| U1 — no desk surface; needs a terminal | Priority card (1.3), optional `rich`/`textual` form | Still a terminal, not a tablet UI; declare it as a prototype surface |
| U2 — approval gate is a hardcoded value | Real approve/edit/dismiss prompt (1.4) | The approver is still unauthenticated (declared gap G-8) |
| U3 — 14–17 s vs “seconds” | Card shows the instant deterministic score vs model cost (1.3); routing/caching deferred (P3) | Latency unchanged this milestone |
| U4 — uncertainty buried in JSON | Loud banner (1.5) + typed uncertainty (1.2) | Quality of the confidence signal depends on RAG (P2) |
| U5 — no vitals-entry ergonomics | Out of scope this milestone (minimal form is a stretch) | Declared gap remains |
| U6 — environment/accessibility | Card legibility + keyboard-first gate (1.3/1.4) | One-handed/gloved entry unaddressed |
| G2 — no clinician interview | **Cannot be fixed here** (human step) | Still the biggest single deduction; attempt before the deadline |

**Net effect:** the P1 set moves U1/U2/U4 (three of the four explicitly-named desk gaps) and, with the live-rule
rehearsal, ST-1. The honest estimate should rise from the current **7–12/20** toward the low-to-mid teens — capped
by the unfixed clinician gap (G2) and the still-terminal surface.

---

## 6. Prior-art / comparison (how adjacent tools do this)

| Capability | Typical triage/CDS approach | Our approach (and why) |
|------------|-----------------------------|------------------------|
| Knowledge grounding | Commercial CDS embeds guideline corpora and often *generates* advice | Retrieval returns **closed-set, cited discriminators only**; the deterministic scorer owns the colour (no generative advice) |
| Uncertainty | Many tools emit a model probability; ablation shows over-confidence | **Coverage bands + explicit defer**, no pseudo-probability; selective-prediction framing reported honestly |
| Human gate | Often a clinician sign-off screen or an override button | LangGraph `interrupt()` gate with a **named** approve/edit/dismiss token; machine-enforced, human-interactive |
| Durability | Production agent stacks underline “checkpoints ≠ durable execution” | We scope durability precisely: **paused case survives restart, resumes to the same decision, no duplicate write** |
| Observability | SaaS tracing (LangSmith et al.) dominates | **Local** spans + replay from checkpoint, because egress is disqualifying here |
| Extensibility | Rule changes ship as software releases | **Data-driven YAML** with a validated loader and hash provenance — the live-review answer |

---

## 7. Sources

- **Internal (HIGH — read directly):** `.planning/PROJECT.md`; `EVALS.md` (§6 declared failure E-09; §7 clinician gap);
  `STATUS.md` (§3 fit-to-desk 7–12/20; §5 ranked gaps G1–G9; §6 UX U1–U7; §7 SOTA gap); `docs/REQUIREMENTS.md`
  (JC-1…JC-6, SN-1…6, ST-1, BW-*); `docs/DECISIONS.md` (D-02/D-05/D-09/D-11/D-13/D-17); `docs/SATS.md`;
  `data/sats_discriminators.yaml` (E-09 "do not tune green" comment); `core/{matcher,scorer,rules}.py`;
  `graph/{nodes,build,state}.py` (`interrupt`, `checkpointed_graph`, `AsyncSqliteSaver`); `store/audit.py`
  (`append/verify/reconcile`); `store/borrowed.py` (`EXPECTED_TOOLS` — only `query` exercised, G7);
  `mcp/server.py` + `mcp/adapter.py`; `core/schema.py` (`ApprovalToken`, `HandoverCard`, `MatchResult.no_match`);
  `llm/client.py`; `demo/run.py` (hardcoded approve, `InMemorySaver`); `evals/runner.py` (`InMemorySaver`).
- **External (LOW; MEDIUM where official/peer-reviewed agree):**
  - Selective prediction / abstention in clinical ML: *Conformal selective prediction with cost-aware deferral for
    clinical triage* (Nature Sci. Rep. 2026); *An Empirical Analysis of Calibration and Selective Prediction*
    (arXiv 2603.02719); *Learning Selective Deferral Policies for Reliable Medical …* (MDPI Technologies 2026) —
    MEDIUM (peer-reviewed), supporting "abstain/defer at low confidence" + calibration.
  - RAG in clinical settings + its failure modes: *RAG in clinical practice: a cautionary tale* (Nature 2026,
    "grounded but misguided"; hallucination surge with context churn); *Retrieval-augmented generation in
    medicine: a scoping review* (ScienceDirect 2026); *MEGA-RAG* (PMC 2025) — MEDIUM, supporting closed-set
    retrieval + citations over generative advice.
  - LangGraph durable execution / HITL: LangChain docs *Human-in-the-loop* and *Interrupts* (HIGH — official);
    community analyses ("checkpoints are not durable execution"; four key components incl. a checkpointer) — LOW.
  - Agent observability 2026: OpenTelemetry GenAI semantic conventions + "span replay"; LangSmith Studio is a
    *local* LangGraph UI; OTel is the convergence point — LOW/MEDIUM (blogs+vendor), OTel GenAI conventions HIGH
    (standard).
- **Confidence seam:** `query classify-confidence --provider websearch` → **LOW**; `--verified` → **MEDIUM**;
  `--provider context7` → **MEDIUM**.

---

*Feature research for: TriageDesk v1.1 Score Uplift — new capabilities only*
*Researched: 2026-10-10*
*Method: direct reading of the frozen v1.0 codebase + docs (HIGH) and targeted web search for external
best-practice claims (LOW→MEDIUM). Categories follow the v1.0 research conventions: table-stakes = expected,
differentiators = competitive advantage, anti-features = deliberately refused. The seven milestone capabilities
were split into eight sections (capability “desk UX” spans the card §1.3 and the gate §1.4, because their
dependencies and anti-features differ).*

