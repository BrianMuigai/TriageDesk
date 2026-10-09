# Feature Research

**Domain:** Clinical triage-support / clinical decision support (CDS) agent for a nurse-led outpatient triage desk
**Researched:** 2026-10-09
**Confidence:** MEDIUM (internal design docs and SATS primary references are HIGH; external literature was
gathered via web search and is treated as LOW per the provider tier, though most retrieved sources are
peer-reviewed journals)

> Scope note: this file is the **feature landscape** — what a credible triage/CDS agent has, what
> differentiates it, and what it must deliberately refuse to be. It is not a restatement of the project's
> requirements; those live in `REQUIREMENTS.md`. Features below are grounded in the South African Triage
> Scale (SATS), the CDS "Five Rights" framework, and published triage/CDS literature, then mapped to the
> 6-day solo MVP.

---

## 1. What the domain expects (the grounding)

Two bodies of evidence shape this landscape:

**A. Triage scales are applied noisily, and under-triage is the dangerous error.**
SATS has good inter-/intra-rater reliability (Twomey 2012), but bedside accuracy is imperfect and
directional: Conti 2022 reported nurse accuracy of **34.2%** with **36.3% under-triage** and 29.5%
over-triage; Mould-Millman 2021 reported **30% under-triage / 13% over-triage**; the MSF Timergara
study reported high specificity (97%) but only moderate sensitivity (70%). Published validation sets
accept under-triage thresholds around 5–10% and tolerate much higher over-triage. **The core insight:**
a triage-support tool earns trust by (a) never removing the clinician, (b) always showing the evidence,
(c) supporting a re-look when the patient changes, and (d) surviving audit — not by claiming to be more
accurate than a nurse.

**B. CDS fails predictably for design reasons, not accuracy reasons.**
Alert fatigue (too many low-value, interruptive alerts → reflexive override) and automation bias
(over-trusting machine output and abandoning confirmatory reasoning) are the two documented harms. The
mitigations are well established: deliver the **right information, to the right person, in the right
format, through the right channel, at the right time** (the CDS "Five Rights", Osheroff/AHRQ); prefer
**information over a verdict**; tier by severity; and keep the human the actor. The triage-CDS review
literature (Fernandes 2020, 62 papers) converges on "assist, not replace" and on standardisation,
risk-flagging, and workflow fit as the value.

Everything below is a consequence of those two facts.

---

## 2. Feature Landscape

### Table Stakes (Users Expect These)

A triage nurse will not use or trust a support tool that lacks any of these. Missing = the tool is
either unsafe or feels incomplete; there is no credit for having them, but absence is disqualifying in
practice.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Sourced priority** — every priority cites the vitals/discriminator that produced it | CDS "right information" from a reputable source; the challenge treats an unsourced priority as *worse than none* (DQ-4, SN-6) | MEDIUM | Requires deterministic scorer + `data/*.yaml` + one citation helper. Output is `triggered_rules[] + citations[]`; a `verify` step rejects anything uncited. |
| **Explicit scope boundary** — visibly "not a diagnosis, not a decision" | Trust + challenge non-negotiables (SN-1/2/3, DQ-3); automation-bias mitigation: show information, not a verdict | LOW | Wording on every output + README + prompt; enforced structurally by having no dx/rx tools. |
| **Human confirmation gate before the queue** | SN-4; "assist not replace" norm; automation-bias safeguard | MEDIUM | LangGraph `interrupt()` before `commit_priority`; queue write refuses without an approval token. |
| **Named-approver audit trail** | Defensibility under clinical audit (JC-5); challenge requires inputs, outputs, timestamps, named approver (BW-10) | MEDIUM | One logging helper per tool call; `actor`, `approved_by`, `role`, `ts`; stored in JSONL + SQLite. |
| **Published-scale grounding (SATS / TEWS + discriminators)** | CDS "right information" must come from an established, published scale — inventing a scale is forbidden | MEDIUM | Rules live in `data/sats_tews.yaml` + `data/sats_discriminators.yaml`; loaded, never hard-coded (see `CONVENTIONS.md`). |
| **Deterministic scoring (no LLM arithmetic)** | Reproducibility + defensibility; a hallucinated number is the worst possible failure | MEDIUM | `score_priority` computes TEWS/colour/discriminator override in code; the model never produces a number. |
| **Structured intake from vitals + free-text complaint** | This is exactly the nurse's existing input at the desk; the tool must consume it without extra work | MEDIUM | `normalize_case` parses prose → typed fields, lists `missing[]`, flags `out_of_scope`. Fits the existing 5-step SATS desk process. |
| **Actionable output: colour + target time / disposition** | SATS colours carry target times (Red immediate → Blue <2h); an acuity without an action is not usable | LOW | Render colour, target time, and destination from the scored case. |
| **Handover / case card** | The nurse needs an artifact she can act on and record | LOW–MEDIUM | `handover` node renders the sourced card (vitals, triggered rules, citations, approver). |
| **Missing-vital recovery (ask, don't fabricate)** | Triage quality depends on the vital set; guessing a value invents evidence | MEDIUM | Conditional edge → `request_missing_info`; the scorer abstains from bands it cannot compute. |
| **Bounded response time ("in seconds")** | Core value: a nurse under queue pressure will abandon a tool that stalls | MEDIUM | Constrains model size (3B Q4 via Ollama), context, and constrained-output decoding; measured as p50/p95 in evals. |
| **Local-only / no data egress** | Eligibility (BW-6, "data cannot leave the country"); also trust and residency | MEDIUM | Fully local inference + local SQLite; synthetic data; no network in the agent path. |
| **Runs end-to-end (one command)** | "A repo that runs" (SB-9, DQ-6); an unusable demo is not a usable tool | LOW–MEDIUM | `uv run triagedesk demo` + synthetic fixture; CI smoke test. |

### Differentiators (Competitive Advantage)

These are where a credible tool separates itself. They are not required to be *usable*, but they are
what make it *defensible* and what the judging criteria reward (agentic depth, reliability,
defensibility).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Safe abstention on out-of-scope input** (e.g. paediatric) | Selective prediction / defer-to-human: a system that knows what it cannot score is safer than one that scores everything. Never mis-score a child. | MEDIUM | `normalize` detects `out_of_scope`; conditional edge → `escalate`; no adult SATS colour emitted (INV-4, E-06). |
| **Deterioration re-check flag (second look, no auto re-classification)** | Triage is temporal — a patient can change while waiting. Flags a re-look without silently reordering a queue. | MEDIUM–HIGH | `raise_recheck_flag` compares serial vitals; non-mutating w.r.t. queue position (SN-5, E-07). Distinct from auto re-triage, which is an anti-feature. |
| **Discriminator-override correctness** ("most urgent wins") | SATS's defining logic: a normal-vitals chest pain is ORANGE. Getting overrides right is what proves the tool understands the scale, not just TEWS. | MEDIUM | Depends on scorer + discriminator KB; E-03 (override) / E-04 (emergency discriminator). |
| **Calibrated confidence / "discriminator confidence" field** | Directly mitigates the dangerous under-triage failure mode (vague complaint → no discriminator matched) and automation bias by telling the nurse *when the match was weak*. | MEDIUM | Surfaced as match coverage/confidence, **not** a pseudo-probability presented as clinical risk. Named as the fix path for the declared E-09 failure. |
| **Bounded failure recovery** (retry once → deterministic fallback or escalate) | The challenge's definition of *agentic*: it recovers. Also prevents uncited/partial output under tool error. | MEDIUM | `verify` retries once; then score directly from parsed fields, else escalate (E-12). |
| **Prompt-injection resistance** (complaint treated as data, never instructions) | Extends trust to adversarial input; the deterministic scorer means no sentence can set a colour. | LOW–MEDIUM | Typed normalization + deterministic scorer + citation invariant (E-13, SECURITY.md). |
| **Hash-chained, tamper-evident audit log** | Stronger than a plain log: the priority survives an adversarial audit question. | MEDIUM | `prev_hash`/`hash` per record; readable and tamper-evident (JC-5). |
| **Idempotent gated write** | An irreversible write that is safe to retry is a clinical-grade property. | LOW–MEDIUM | `commit_priority` keyed by `case_id` + content hash (SW-3). |
| **Version pinning + hashing of prompts, model, and scale data** | Reproducibility: any run can be shown to have varied, or reproduced. | LOW–MEDIUM | Audit records model version, prompt hash, YAML hash (SW-5, D-17). |
| **Extend-by-data extensibility** (add a SATS rule in one line) | Low-resource desks and the live review both need rule changes without a code change. | LOW–MEDIUM | Rules in YAML; new capability = new node + new tool (ST-1, SOLID O). |
| **Honest evaluation incl. a declared, unfixed failure** | Reliability and defensibility are scored; hiding the failure forfeits them. | MEDIUM | 13 cases, run-to-run variation measured, one expected failure shown in the demo (JC-4, EVALS §6). |
| **Throughput / queue-pressure model** | Connects the tool to the actual bottleneck (60–90 min wait) rather than an abstract accuracy claim. | MEDIUM | Assumption-labelled model of the 5-step desk process (JC-3). |

### Anti-Features (Commonly Requested, Often Problematic)

Things that appear valuable but are unsafe, disqualifying, or scope-destroying. Each has a safer
alternative — usually the one already chosen.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Autonomous queue movement / auto-prioritisation** | "If it's smart, why not just place the patient?" | Instant disqualifier (DQ-3, SN-3); automation bias — a wrong machine move reverses correct clinical judgement. | Gated `commit_priority` with a named-approver token; the machine proposes, the nurse disposes. |
| **Diagnosis / differential generation** | Users expect health AI to "tell you what it is." | Forbidden (SN-1); it is outside a triage scale's competence and the challenge's rules. | Output priority + citations only; no diagnostic field exists. |
| **Prescribing / treatment recommendation** | Natural next step after a priority. | Forbidden (SN-2); unsafe without clinical authority and not this tool's job. | None — hand over the sourced card; the clinician decides care. |
| **Runtime self-learning / point-of-care adaptation** | "It should get better over time." | Unsafe and unauditable: rules drift, the hash-chain becomes meaningless, reproducibility dies. | Versioned rules in YAML, changed in **offline review** (open/closed by data). |
| **Free-form ReAct / open-ended agent loop** | "More agentic = better score." | A small CPU model is an unreliable free agent; non-reproducible and hard to audit (G-5). | Explicit LangGraph with bounded decisions; model handles language, not arithmetic or control flow. |
| **LLM-computed scores / numbers** | Convenient to let the model do the maths. | Non-deterministic and hallucination-prone; a wrong number is undefendable. | Deterministic scorer; the model never emits a number. |
| **Closed no-code builder or frontier model in the required path** | Faster to prototype; "better model = better output." | Disqualifying on tooling (BW-4); egress violates data residency (BW-6). | Open-source orchestration + local open-weights model (Qwen2.5 via Ollama). |
| **Chatbot-wrapper product (single model call)** | Cheapest to build. | DQ-1: chatbot with no autonomous tool use. | Agent graph that plans, calls acting tools, verifies, recovers. |
| **Real patient data / live hospital integration in v1** | Makes the demo "real." | Forbidden without consent (DC-3, DQ-5); out of scope and dangerous pre-validation. | Synthetic fixture; integration is a declared production requirement, not a v1 feature. |
| **Over-alerting / interruptive notifications** | "More alerts = safer." | Alert fatigue → reflexive override, the documented primary CDS failure. | One consolidated, actionable priority card + a single re-check flag, delivered at the point of decision. |
| **Multilingual input in v1** | The setting is multilingual. | Scope-destroying for a 6-day solo build; phrasing risk in a safety path. | Deferred; architecture stays aware (kept out of the critical path). |
| **Full paediatric SATS scoring** | Clinical completeness. | Age-banded charts differ; a mis-score on a child is the worst outcome. | Abstain + escalate to a human (D-6, G-7). |
| **"Confidence score" shown as a clinical probability** | Looks rigorous. | An uncalibrated number invites over-trust (automation bias) and is indefensible. | Abstain / flag weak matches instead of fabricating a probability. |
| **Silent auto-correction of nurse-entered vitals** | "Clean the data up for her." | Hides data-quality issues and is untraceable; changes evidence without consent. | Record as entered; flag implausible values; let the nurse correct. |

---

## 3. Feature Dependencies

```
Sourced priority (table stakes)
    ├──requires──> Deterministic scorer  ──requires──> SATS YAML data + typed vitals schema
    ├──requires──> Citation helper (single source, DRY)
    └──requires──> verify node (rejects uncited output)

Human confirmation gate (table stakes)
    ├──requires──> LangGraph interrupt() orchestration
    └──requires──> commit_priority tool (gated, idempotent)

Named-approver audit trail (table stakes)
    ├──requires──> one logging helper (single record shape)
    └──requires──> borrowed SQLite MCP (persistence)

Discriminator-override correctness (differentiator)
    ├──requires──> SATS discriminator KB (data/*.yaml)
    └──requires──> match_discriminators tool

Calibrated confidence (differentiator)
    └──requires──> match_discriminators returns coverage/confidence  ──enhances──> Sourced priority

Deterioration re-check (differentiator)
    ├──requires──> serial-vitals input
    └──requires──> non-mutating raise_recheck_flag tool

Safe abstention (differentiator)
    └──requires──> out_of_scope detection in normalize_case  ──conflicts──> Full paediatric SATS scoring

Bounded failure recovery (differentiator)
    ├──requires──> verify node
    └──enhances──> Deterministic scorer (deterministic fallback path)

Hash-chained audit (differentiator)
    └──requires──> audit record shape (prev_hash/hash)

Prompt-injection resistance (differentiator)
    ├──requires──> typed normalization
    └──requires──> Deterministic scorer (no sentence can set a colour)

Honest evaluation (differentiator)
    └──requires──> Throughput/latency + cost measurement

Extend-by-data extensibility (differentiator)
    └──requires──> rules in YAML + narrow tools (SOLID O/I)
```

### Dependency Notes

- **Sourced priority requires deterministic scoring + citation helper:** the citation *is* the evidence;
  without a single citation source (DRY) citations drift and the priority becomes indefensible.
- **Human gate requires orchestration interrupt + gated commit:** the gate is only real if the write
  physically cannot proceed without the approval token; otherwise it is theatre (DQ-3).
- **Audit requires one logging helper + the borrowed store:** every tool call must route through one
  record shape (CONVENTIONS DRY row "Audit-log record shape") or the chain breaks.
- **Calibrated confidence enhances sourced priority:** it is the honest fix for the known E-09 under-triage
  failure — it tells the nurse when the discriminator match was weak instead of silently falling back.
- **Safe abstention conflicts with full paediatric scoring:** they are mutually exclusive; choosing
  abstention is what makes the tool safe for children it cannot score.
- **Runtime self-learning conflicts with hash-chained audit + reproducibility:** adaptation would break the
  chain and make run-to-run comparison meaningless.
- **Free-form ReAct conflicts with deterministic, reproducible scoring:** an open loop cannot guarantee the
  same colour twice.

---

## 4. MVP Definition

Scoped ruthlessly for a **6-day solo build** (Oct 09 → Oct 15) on a ~6.9 GB RAM CPU-only host. The MVP is
deliberately the *safety spine* plus honest evidence, not the widest feature set.

### Launch With (v1)

- [ ] **Deterministic SATS scorer with citations** — the core value; nothing else matters if the priority
      is not sourced and reproducible.
- [ ] **Own MCP server (≥3 tools, incl. one gated write)** — required (BW-1/BW-2) and the agentic proof.
- [ ] **Borrowed SQLite MCP** — required (BW-3); avoids hand-rolling persistence.
- [ ] **Human approval gate on every queue-affecting action** — the safety spine (SN-4, BW-9).
- [ ] **Hash-chained audit log with named approver** — defensibility (BW-8/10, JC-5).
- [ ] **Missing-vital recovery + safe abstention** — recovers instead of guessing (E-05/E-06).
- [ ] **Deterioration re-check flag** — temporal safety without auto-reclassification (SN-5).
- [ ] **Local open-weights model end-to-end** — eligibility + residency (BW-5/6).
- [ ] **Handover / case card** — the nurse's actionable artifact.
- [ ] **One-command run + 13 honest eval cases (one declared failure)** — "a repo that runs" + credibility.
- [ ] **Demo video + ARCHITECTURE/EVALS/DESCRIPTION** — submission artifacts.

### Add After Validation (v1.x)

- [ ] **Discriminator confidence field** — the honest, low-cost fix for E-09; add once the core is stable.
- [ ] **Clarifying-question loop** when a complaint matches no discriminator and a chronic condition is
      present — the deeper fix for E-09 (new interaction surface; de-scoped from v1).
- [ ] **Embedding retrieval over the discriminator KB** — replaces keyword matching; deferred for time.
- [ ] **Referral routing node** — a stretch acting tool; gated like the queue write.
- [ ] **Multilingual input** — only if assessed safe and validated against the scale.

### Future Consideration (v2+)

- [ ] **Live hospital-system integration** — production concern; out of scope for the prototype.
- [ ] **Approver authentication** — identity is *recorded* in v1; *authentication* is a declared production
      requirement (SECURITY.md §6).
- [ ] **Full paediatric SATS** — only with age-banded charts validated; v1 abstains by design.
- [ ] **Offline rule-review / versioning pipeline** — governed scale updates without runtime learning.

---

## 5. Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Sourced priority | HIGH | MEDIUM | **P1** |
| Deterministic scorer | HIGH | MEDIUM | **P1** |
| Human approval gate | HIGH | MEDIUM | **P1** |
| Named-approver audit log | HIGH | MEDIUM | **P1** |
| Published-scale grounding (SATS data) | HIGH | MEDIUM | **P1** |
| Structured intake / normalize | HIGH | MEDIUM | **P1** |
| Missing-vital recovery | HIGH | MEDIUM | **P1** |
| Handover card + target time | HIGH | LOW | **P1** |
| Local-only / no egress | HIGH | MEDIUM | **P1** |
| One-command run + evals | HIGH | MEDIUM | **P1** |
| Safe abstention (paediatric) | HIGH | MEDIUM | **P1** |
| Deterioration re-check | MEDIUM | MEDIUM | **P1** |
| Discriminator-override correctness | HIGH | MEDIUM | **P1** |
| Bounded failure recovery | HIGH | MEDIUM | **P1** |
| Prompt-injection resistance | MEDIUM | LOW | **P2** |
| Hash-chained audit | MEDIUM | MEDIUM | **P2** |
| Idempotent gated write | MEDIUM | LOW | **P2** |
| Version pinning/hashing | MEDIUM | LOW | **P2** |
| Extend-by-data extensibility | MEDIUM | LOW | **P2** |
| Throughput/queue-pressure model | MEDIUM | MEDIUM | **P2** |
| Discriminator confidence | MEDIUM | MEDIUM | **P2** |
| Clarifying-question loop | MEDIUM | HIGH | **P3** |
| Embedding retrieval over KB | MEDIUM | HIGH | **P3** |
| Referral routing node | LOW | MEDIUM | **P3** |
| Multilingual input | MEDIUM | HIGH | **P3** |
| Hospital-system integration | LOW | HIGH | **P3** |

**Priority key:** P1 = must have for launch · P2 = should have, add when possible · P3 = future.

---

## 6. Competitor / Comparable Feature Analysis

The "competitors" are the triage scales and CDS tools a judge or clinician would compare against. The
column that matters is "our approach" — where we deliberately differ.

| Feature | ESI (5-level, resource-based) | Manchester Triage System (MTS) | Digital triage / CDS platforms | Our Approach (SATS-based) |
|---------|-------------------------------|--------------------------------|--------------------------------|---------------------------|
| Underlying logic | Resource-utilisation prediction | Presenting-complaint flowcharts | Often ML on vitals/history | **Published SATS TEWS + discriminator overrides** (open, African-context) |
| Output | Acuity level | Priority + target time | Risk flag / priority suggestion | **Colour + target time + cited rules** (never a diagnosis) |
| Source of a decision | Clinician judgement | Flowchart path | Model output | **Deterministic scorer + `triggered_rules[]`; model never emits a number** |
| Human role | Decides | Decides | Varies; often suggests | **Mandatory named-approver gate before any queue write** |
| Deterioration handling | Reassess | Reassess | Some prediction models | **Second-look flag, no auto-reclassification** |
| Auditability | Narrative chart | Narrative chart | Often opaque model output | **Hash-chained audit of inputs, outputs, approver** |
| Abstention / scope | Clinician discretion | Clinician discretion | Rare | **Explicit abstention on paediatric/out-of-scope** |
| Data residency | Local/national systems | Local/national systems | Frequently cloud | **Fully local, no egress; synthetic data** |
| Licensing | Regulated (e.g. ENA) | Licensed (licence cost) | Vendor/closed | **Apache-2.0, openly published scale** |

**Read:** we are not competing on raw accuracy with large-vendor CDS. We compete on *defensibility and
fit* — an open, evidence-pinned, human-gated, audit-survivable tool built on a scale designed for
African low-resource settings. That is precisely what the differentiators column protects.

---

## 7. Cross-cutting principles these features must respect (CDS "Five Rights")

| Right | How the feature set satisfies it |
|-------|----------------------------------|
| Right **information** | Sourced priority from a published scale (SATS), never invented. |
| Right **person** | Delivered to the triage nurse who can act at the desk — not to a bystander. |
| Right **format** | A single actionable case card (colour, target time, citations), not a wall of alerts. |
| Right **channel** | In-workflow at the desk; no separate login/handoff. |
| Right **time** | Sub-minute response, at the moment of triage decision; alert-fatigue avoided by one consolidated card. |

---

## 8. Sources

**Internal (HIGH confidence — curated design context):**
- `.planning/PROJECT.md`, `CONVENTIONS.md`, `ARCHITECTURE.md`, `REQUIREMENTS.md`, `EVALS.md`
- `docs/SATS.md` — SATS Training Manual 2012 (EMSSA) transcription; SATS validation literature references

**External (peer-reviewed, retrieved via web search → LOW provider tier):**
- Dalwai M. et al. *Is the South African Triage Scale valid for use in Afghanistan, Haiti and Sierra Leone?* BMJ Global Health 2017 — <https://gh.bmj.com/content/2/2/e000160>
- Mould-Millman N.K. et al. *Validity and reliability of the South African Triage Scale in the emergency department.* BMC Emerg Med 2021 — <https://link.springer.com/article/10.1186/s12873-021-00406-6>
- Meyer G.D. et al. *Validity of the South African Triage Scale in a rural district hospital.* 2018 — <https://pmc.ncbi.nlm.nih.gov/articles/PMC6277536>
- Twomey M. et al. *The South African Triage Scale (adult version) provides reliable triage when used by nurses and doctors.* 2012.
- Conti A. et al. *Implementation of the South African Triage Scale (SATS) in an Italian ED.* IJERPH 2022 — <https://www.mdpi.com/1660-4601/19/16/10298>
- Fernandes M. et al. *Clinical Decision Support Systems for Triage in the Emergency Department using Intelligent Systems: a Review.* Artif Intell Med 2020 — <https://pubmed.ncbi.nlm.nih.gov/31980099>
- Osheroff J. et al. *The Five Rights of Clinical Decision Support* (AHRQ/ONC framework) — <https://healthit.gov/clinical-quality-and-safety/clinical-decision-support>
- Goddard K. et al. *Automation bias: a systematic review of frequency, effect mediators, and mitigators.* JAMIA — <https://pmc.ncbi.nlm.nih.gov/articles/PMC3240751>
- Khera R. et al. *Automation Bias and Assistive AI: Risk of Harm From AI-Driven Clinical Decision Support.* JAMA 2024.
- AHRQ PSNet — *Clinical Decision Support Systems* primer; *Emergent Triage Miss* (under-triage as the dangerous direction).
- Selective prediction / abstention literature (defer-to-human under uncertainty) — e.g. arXiv 2502.18050; BMC Med Inform Decis Mak 2021 (asymmetric abstention).

---

*Feature research for: TriageDesk — agentic SATS triage support for a nurse-led OPD desk*
*Researched: 2026-10-09*
