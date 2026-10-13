# STATUS — TriageDesk vs the Agentic AI for Africa Challenge

> **Honest self-assessment.** Written 2026-10-10 against the live brief:
> <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> This is a gap analysis, not a victory lap. It says what is done, what is missing, and what would
> move the score.
> **Snapshot:** the measured figures below are dated; [`EVALS.md`](EVALS.md) is the current single
> source for every measured number (a full STATUS refresh is Phase 12's DOCS-06).

---

## 0. Verdict

**Not 100%.** The *build* is essentially complete and the eligibility bar is met, but there is **one
hard submission gap** (the demo video is recorded but **not uploaded**) and **one partially-met
20-point criterion** (no clinician interview). Adding the UX lens lowers the honest estimate further.

| Dimension | Status |
| --- | --- |
| Eligible / not disqualified | ✅ (one confirmation pending — G9) |
| "What to build" (6 items) | ✅ **6/6** |
| "What to submit" (5 items) | 🟡 **4/5** — video not uploaded |
| Judging criteria (100 pts) | 🟡 **est. ~75–90** |
| Instant disqualifiers (8) | ✅ none triggered |

---

## 1. "What to build" — 6/6 ✅

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| Own MCP server, ≥3 tools, ≥1 acting | 5 tools: `normalize_case`, `match_discriminators`, `score_priority`, `raise_recheck_flag`, `commit_priority` | ✅ |
| One MCP server you did not write (+ one line why) | borrowed pinned `mcp-sqlite`; rationale in `docs/DECISIONS.md` D5 | ✅ (under-exercised — G7) |
| Open-source orchestration | LangGraph | ✅ |
| One full task on an open-weights model; data cannot leave the country | local `qwen2.5:1.5b` / `qwen3.5:4b`, no egress (`strace`-verified) | ✅ |
| Logged tool call for every action + a gate on every irreversible one | hash-chained audit; `commit` has exactly one inbound edge (`approval_gate`) | ✅ |
| New work, built during the submission period | greenfield; first commit 2026-10-09 | ✅ (timing to confirm — G8) |

## 2. "What to submit" — 4/5 🟡

| Requirement | Status |
| --- | --- |
| Public repo + OSI licence + README one command | ✅ public, Apache-2.0 — one command (`uv run triagedesk demo`); G3 resolved |
| Demo video <3 min, **uploaded to YouTube/Vimeo, publicly visible** | ❌ recorded (`docs/assets/triagedesk-demo.mp4`, 33 s) but **NOT uploaded** (G1) |
| ~300-word description | ✅ `DESCRIPTION.md` (302 words) |
| ARCHITECTURE.md — one page | ✅ 697 words / 94 lines |
| EVALS.md — 8+ tasks + one unfixed failure | ✅ 16 cases; E-09 declared (G4) |

## 3. Judging criteria — honest self-score

| Criterion | Pts | Est. | Why not full |
| --- | --- | --- | --- |
| Agentic depth & MCP craft | 30 | **27–30** | Strong. Borrowed-server tools under-exercised (G7) |
| Open-source rigour | 20 | **18–20** | Honest README; one-command quickstart (G3 resolved) |
| **Fit to the triage desk** | 20 | **7–12** | **No clinician interview** (G2) + **no desk surface** + 13–17 s latency (U1/U3) |
| Evaluation & reliability | 15 | **13–15** | Honest & measured; 2 recorded gate failures + 1 declared deferral + 3 coverage deferrals (G4) |
| Defensibility | 10 | **9–10** | Deterministic, cited, hash-chained audit, cost/run — strong |
| Demo | 5 | **3–5** | Recorded, failure shown — but 33 s and not hosted (G1/G5) |

## 4. Instant disqualifiers — none ✅

No chatbot wrapper · not a single-endpoint proxy · no diagnosis/prescription/autonomous queue move ·
every priority cited · synthetic only · repo runs · results are real · greenfield disclosed.

---

## 5. Gaps & misses (ranked)

1. **G1 — Demo video not uploaded.** The brief requires it *hosted and public*. **The only true
   submission blocker.** Fix: upload `docs/assets/triagedesk-demo.mp4` to YouTube/Vimeo (Public) and
   paste the link. *(Human step.)*
2. **G2 — No clinician interview.** "Fit to triage desk" explicitly asks *"did you talk to one?"* We
   declared the gap honestly but lose points. Fix: one real triage-nurse/clinician review + a quote.
3. **G3 — resolved.** The README now shows the literal one-liner `uv run triagedesk demo` (`uv`
   auto-syncs from the committed lock); the two-step install is gone and a test guards it.
4. **G4 — Eval optics.** The honest misses stay visible and the counts are reconciled: `EVALS.md`
   §4 lists **16 cases** and §3's figures are emitted from the same `report.json`. E-09 is the one
   declared failure (a coverage deferral, not a delivered under-triage); E-11 and E-13 are recorded
   gate failures and E-01/E-08/E-14 are coverage deferrals.
5. **G5 — Demo length.** 33 s is under 3 min but thin against "three clear minutes showing the agent
   working."
6. **G6 — Live-review readiness (Stage 2).** "A new requirement added live while we watch." Our YAML
   design makes this a one-line edit, but we have not **rehearsed** it or a 10-min code walkthrough.
7. **G7 — Borrowed MCP under-exercised.** Integration check: only the borrowed server's `query` tool is
   actually invoked; the other 7 are asserted-but-unused.
8. **G8 — Submission-period timing.** Page says "Opens TBC, closes TBC"; confirm the window was open on
   2026-10-09.
9. **G9 — Eligibility to confirm.** "Resident anywhere in Africa," 18+, solo — confirm at application.

---

## 6. UX considerations

**Why it matters here:** "Fit to triage desk" (20 pts) is essentially a UX question ("does a nurse do a
real thing *faster, at the desk, under real queue pressure*?"), the Demo (5 pts) is UX, and the brief's
schedule includes "UX refinement."

### What a user actually touches today

| Actor | Current surface | Reality |
| --- | --- | --- |
| Triage nurse | a **CLI** (`uv run triagedesk demo`) + a printed **JSON** `handover_card` | a prototype/terminal storyboard, not a desk tool |
| Clinician approver | a JSON blob; the demo **hardcodes** the approve value | the approval *interaction* is not designed |

### UX gaps (ranked)

- **U1 — No desk-facing surface.** The nurse would need a terminal and the ability to run `uv`. At a
  busy OPD that is a non-starter. *The biggest drag on "fit to triage desk."*
- **U2 — The approval gate is not an interaction.** Safety is machine-enforced (good), but the *human*
  side is a hardcoded decision. The evidence card should read "**SUGGESTED** priority + evidence → you
  decide" with a real approve/edit/dismiss affordance, or it risks reading as a **rubber stamp**
  (the automation-bias pitfall our own research flagged).
- **U3 — Latency vs "Seconds."** The brief promises *seconds*; the **measured real-model path is
  p50 13.06 s / p95 17.41 s**. The deterministic score is instant — the local model's extraction
  dominates. Too slow for the desk.
- **U4 — Uncertainty is not surfaced.** When no discriminator matches (the E-09 class) the card shows
  `no_discriminator_matched: true` buried in JSON. A nurse needs a loud "**no match — please check**".
- **U5 — Vitals-entry ergonomics absent.** No designed input (numeric-keypad-friendly, units, defaults,
  missing-vital prompting). We have the *logic*, not the *entry*.
- **U6 — Environment/accessibility unaddressed.** Busy desk, interruptions, one-handed/gloved entry,
  shared terminal, English-only.
- **U7 — No UX design contract.** No UI-SPEC / visual spec for the card.

### UX strengths (keep them)

Colour-coded, legible output · **citations shown next to the colour** (the automation-bias mitigation) ·
no dx/rx framing · the failure is shown, not hidden · one-command reproducibility for a reviewer.

---

## 7. State-of-the-art gap analysis

**Verdict:** a **state-of-the-art *trustworthy* agent for a narrow, safety-critical niche** — excellent
on reliability, human authority, auditability, structural safety, and honest evaluation — but **not a
state-of-the-art *general* agent**. The distance to "cutting edge" is almost entirely the
**capability / knowledge / memory / observability** cluster.

| SOTA agent pillar | TriageDesk | Verdict |
| --- | --- | --- |
| Tool use / MCP craft | 5 owned tools + borrowed SQLite MCP | ✅ present |
| Explicit control flow / orchestration | LangGraph state machine | ✅ present |
| Human-in-the-loop / approval gate | `interrupt()` gate; approve/edit/dismiss | ✅ present (interaction UX weak) |
| Reliability engineering | retries, deterministic fallback, idempotency, invariants | ✅ present |
| Guardrails / safety | structural: no dx/rx tools, citation invariant, gate | ✅ present (strong) |
| Prompt-injection resistance | prose-as-data + deterministic scorer | ✅ present |
| Reproducibility | hashing, pinned deps, deterministic scorer | ✅ present |
| Evaluation | 16 cases, invariants, honest failure | 🟡 strong but offline-only |
| Dynamic planning / adaptive routing | fixed graph (bounded) | 🟡 partial — deliberate |
| **Knowledge grounding (RAG)** | deterministic citations from YAML; **no retrieval** | ❌ **genuine gap** |
| **Calibrated confidence + abstention** | none (deferred to v2) | ❌ **genuine gap** |
| **Durable/resumable execution** | `checkpoints.db` built but **not wired E2E** (`InMemorySaver` used) | ❌ **genuine gap** |
| **Observability / tracing / replay** | JSONL audit only; no spans | ❌ **genuine gap** |
| Online eval / calibration / drift | offline report only | ❌ gap |
| Cost/latency management | cost reported; **13–17 s**, no routing/caching/budgets | ❌ gap |
| Approver authentication | recorded, not authenticated | ❌ gap (declared) |
| MCP sampling / elicitation (current spec) | static tool calls only | ❌ gap |
| Long-term / episodic memory | per-case only | ⛔ deliberate |
| Multimodal (voice/vision) | text only | ⛔ deliberate |
| Multi-agent (planner/executor/critic) | single graph + `verify` node | ⛔ deliberate |
| Runtime self-learning | none | ⛔ deliberate (unsafe here) |
| Broad action space / computer use | narrow, gated | ⛔ deliberate |

### Genuine gaps worth closing (safe, and they raise "agentic depth" — 30 pts)

1. **Retrieval-grounded knowledge (RAG)** over the SATS manual + local protocols — fixes **E-09** and
   turns deterministic lookup into real grounding. *Biggest capability upgrade.*
2. **Calibrated confidence + abstention** (selective prediction) — a hallmark of trustworthy SOTA
   agents; the honest fix for the E-09 class.
3. **Wire the durable `checkpoints.db`** into the E2E path — already built, just not exercised.
4. **Span-based tracing + replay** (OTel/LangSmith) on top of the audit log.
5. **MCP sampling / elicitation** — the current spec's agent↔server negotiation.
6. **Model routing / caching / budgets** — attacks the 13–17 s desk latency.
7. **Online eval + calibration + drift monitoring**.
8. **Multimodal intake** (voice + chart/cuff photo) — the real desk UX.

### What we correctly chose *not* to have

Runtime self-learning, autonomous queue movement, long-term memory of patient data, free-form ReAct,
multi-agent autonomy, a frontier model in the path, and a broad action space. Each would make it "more
cutting-edge" in the generic sense **and make it unsafe** for triage. Their absence is a feature — and
it is the discipline the brief rewards ("three tools that work beat nine that half-work").

---

## 8. Action list

**Must-do (blocks submission):**
- **Upload the demo video** (G1) and paste the link into the challenge form.

**High-value (score movers):**
- **One clinician review** + a one-line quote in README/EVALS (G2) — the biggest available points.
- **Rehearse the live review**: 10-min walkthrough + a dry-run "add a discriminator to
  `data/sats_discriminators.yaml` live and re-score" (G6).
- **E-07 and E-04 fixed** (Phase 11); the measured eval was re-run; E-09 stays declared (G4).
- **README one command — done**; the EVALS numbers are reconciled (G3/G4).

**UX (cheap → expensive):**
- Human-readable **priority card** ("SUGGESTED: ORANGE · <10 min · why: RR 24 + HR 118 + T 38.9") — not JSON.
- A visible **"LOW CONFIDENCE / NO DISCRIMINATOR MATCHED — nurse to confirm"** banner (U4).
- Make the gate a **real prompt** in the demo (evidence → explicit approve/edit/dismiss) (U2).
- Show the **fast deterministic path**; state the model latency honestly (U3).
- A one-screen **desk quickstart** in `docs/DEMO.md` (U5).
- *(Stretch)* a minimal `rich`/`textual` form for vitals entry — the first real desk surface.

**Polish:**
- Extend the demo to ~2–3 min with the eval run + on-screen narration (G5).
- Exercise one more borrowed-server tool (G7).
- Optionally add a **frontier-model comparison on synthetic data** (the brief invites it).

---

## 9. Bottom line

- **Build: done.** All 6 "what to build" items, all safety rules, no disqualifiers; repo frozen, tagged
  (`v1.0-submission`) and pushed; 444 tests pass; honest measured evaluation.
- **Submission: one step short.** Upload the video.
- **Score ceiling:** capped mainly by **fit-to-desk (no clinician + no desk surface)** and **demo
  (short + unhosted)** — both improvable before 2026-10-15.
- **State of the art:** already ahead of most on **trust, auditability, and honesty**; behind on
  **capability breadth** (retrieval, memory, multimodal, tracing, online eval). The two highest-leverage
  safe upgrades are **RAG grounding** and **calibrated confidence/abstention**.
