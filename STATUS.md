# STATUS — TriageDesk vs the Agentic AI for Africa Challenge

> **Honest self-assessment.** Refreshed 2026-10-14 (post-v1.1 desk hardening) against the live brief:
> <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> This is a gap analysis, not a victory lap. It says what is done, what is missing, and what would
> move the score.
> **Snapshot:** [`EVALS.md`](EVALS.md) is the current single source for every measured number, and
> [`ARCHITECTURE.md`](ARCHITECTURE.md) for the agent shape; this file links them rather than
> restating their figures.

---

## 0. Verdict

**Not 100%.** The *build* is essentially complete and the eligibility bar is met, but there is **one
hard submission gap** (the demo video is recorded but **not uploaded**) and **one partially-met
20-point criterion** (no clinician interview). Adding the UX lens lowers the honest estimate further.

| Dimension | Status |
| --- | --- |
| Eligible / not disqualified | ✅ (two confirmations pending — G8 timing, G9 eligibility) |
| "What to build" (6 items) | ✅ **6/6** |
| "What to submit" (5 items) | 🟡 **4/5** — video not uploaded |
| Judging criteria (100 pts) | 🟡 **est. ~79–94** |
| Instant disqualifiers (8) | ✅ none triggered |

---

## 1. "What to build" — 6/6 ✅

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| Own MCP server, ≥3 tools, ≥1 acting | 7 tools: `normalize_case`, `match_discriminators`, `retrieve_evidence`, `score_priority`, `assess_confidence`, `raise_recheck_flag`, `commit_priority` | ✅ |
| One MCP server you did not write (+ one line why) | borrowed pinned `mcp-sqlite`; rationale in `docs/DECISIONS.md` D5 | ✅ (read paths exercised — MCP-01) |
| Open-source orchestration | LangGraph | ✅ |
| One full task on an open-weights model; data cannot leave the country | local `qwen2.5:1.5b` (the measured default — [`EVALS.md`](EVALS.md)), no egress (`strace`-verified) | ✅ |
| Logged tool call for every action + a gate on every irreversible one | hash-chained audit; `commit` has exactly one inbound edge (`approval_gate`) | ✅ |
| New work, built during the submission period | greenfield; first commit 2026-10-09 | ✅ (timing to confirm — G8) |

## 2. "What to submit" — 4/5 🟡

| Requirement | Status |
| --- | --- |
| Public repo + OSI licence + README one command | ✅ public, Apache-2.0 — one command (`uv run triagedesk demo`) |
| Demo video <3 min, **uploaded to YouTube/Vimeo, publicly visible** | ❌ the brief wants ONE video under 3 min *with the tool calls on screen*; the 33 s terminal run (`docs/assets/triagedesk-demo.mp4`) has the tool calls but is thin, and the 2:55 captioned desk walkthrough (`docs/assets/desk-demo.mp4`) has the length and narration but **no tool calls** — so neither is a complete candidate, and **neither is uploaded** (G1) |
| ~300-word description | ✅ `DESCRIPTION.md` — within ±10% of 300, guarded by `tests/test_docs_final.py` |
| ARCHITECTURE.md — one page | ✅ one page (see [`ARCHITECTURE.md`](ARCHITECTURE.md)) |
| EVALS.md — 8+ tasks + one unfixed failure | ✅ 16 cases; E-09 declared |

## 3. Judging criteria — honest self-score

| Criterion | Pts | Est. | Why not full |
| --- | --- | --- | --- |
| Agentic depth & MCP craft | 30 | **27–30** | Strong. Borrowed-server read paths now exercised |
| Open-source rigour | 20 | **18–20** | Honest README; one-command quickstart; the desk module is SRP-split and the store seam de-duplicated |
| **Fit to the triage desk** | 20 | **9–14** | **No clinician interview** (G2) + a still-single-machine prototype desk surface (U1) + unchanged model-extraction latency ([`EVALS.md`](EVALS.md) §3) (U3). New UX evidence now exists — the captioned desk walkthrough (`docs/assets/desk-demo.mp4`) and the queue-position-on-commit payoff (§6) — but the range does not move |
| Evaluation & reliability | 15 | **13–15** | Honest & measured; 2 recorded gate failures + 1 declared deferral + 3 coverage deferrals |
| Defensibility | 10 | **9–10** | Deterministic, cited, hash-chained audit, cost/run — strong |
| Demo | 5 | **3–5** | Recorded, failure shown — but 33 s and not hosted (G1/G5). Neither recording is a complete candidate: the 33 s terminal run (`docs/assets/triagedesk-demo.mp4`) has the tool calls but is thin, while the 2:55 captioned desk walkthrough (`docs/assets/desk-demo.mp4`) has the length and narration but **no tool calls** |

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
3. **G5 — Demo length and content.** The brief wants ONE video under 3 min *with the tool calls on
   screen*, and neither recording is a complete candidate. The 33 s terminal run
   (`docs/assets/triagedesk-demo.mp4`) has the tool calls but is thin; the 2:55 captioned desk
   walkthrough (`docs/assets/desk-demo.mp4`) has the length and narration but **no tool calls**. Neither
   closes the requirement — **G5 is not closed.**
4. **G8 — Submission-period timing.** Page says "Opens TBC, closes TBC"; confirm the window was open on
   2026-10-09.
5. **G9 — Eligibility to confirm.** "Resident anywhere in Africa," 18+, solo — confirm at application.

---

## 6. UX considerations

**Why it matters here:** "Fit to triage desk" (20 pts) is essentially a UX question ("does a nurse do a
real thing *faster, at the desk, under real queue pressure*?"), the Demo (5 pts) is UX, and the brief's
schedule includes "UX refinement."

### What a user actually touches today

| Actor | Current surface | Reality |
| --- | --- | --- |
| Triage nurse | a **loopback desk surface** (`uv run triagedesk desk`) + the CLI | a real browser surface over the shipped graph — still single-machine and English-only |
| Clinician approver | a real **approve / edit / dismiss** gate over `interrupt()`/resume | the interaction exists; approver *authentication* stays a declared gap (G-8) |

### UX gaps (ranked)

- **U1 — The desk surface is a prototype, not a deployed tool.** Phase 10 ships a loopback browser
  surface ([`docs/DESK.md`](docs/DESK.md)) over the shipped graph; it is single-machine, English-only,
  assumes one shared terminal, and is not integrated with any hospital system. The package is now
  SRP-split and a captioned walkthrough is recorded (`docs/assets/desk-demo.mp4`), but the surface's
  substance is **unchanged**.
- **U2 — Approver authentication is still open.** The gate is now a real approve/edit/dismiss
  interaction, but the approver's *identity* is recorded, not authenticated (G-8).
- **U3 — Latency vs "Seconds".** The brief promises *seconds*; the measured real-model extraction
  latency is reported in [`EVALS.md`](EVALS.md) §3. The deterministic score is instant — the local
  model's extraction dominates. Too slow for the desk.
- **U4 — Vitals-entry ergonomics are thin.** The desk form validates through the ONE `CaseInput`
  schema, but there is no numeric-keypad-friendly, unit-aware, missing-vital-prompting entry.
- **U5 — Environment/accessibility unaddressed.** Busy desk, interruptions, one-handed/gloved entry,
  shared terminal, English-only.

### UX strengths (keep them)

Colour-coded, legible output · **citations shown next to the colour** (the automation-bias mitigation) ·
no dx/rx framing · the failure is shown, not hidden · **queue-position-on-commit feedback** — the
post-decision panel names the queue position the gated write assigned, so the write is visible rather
than implied · one-command reproducibility for a reviewer.

---

## 7. State-of-the-art gap analysis

**Verdict:** a **state-of-the-art *trustworthy* agent for a narrow, safety-critical niche** — excellent
on reliability, human authority, auditability, structural safety, and honest evaluation — but **not a
state-of-the-art *general* agent**. The distance to "cutting edge" is almost entirely the
**capability / knowledge / memory / observability** cluster.

| SOTA agent pillar | TriageDesk | Verdict |
| --- | --- | --- |
| Tool use / MCP craft | 7 owned tools + borrowed SQLite MCP | ✅ present |
| Explicit control flow / orchestration | LangGraph state machine | ✅ present |
| Human-in-the-loop / approval gate | `interrupt()` gate; real approve/edit/dismiss desk surface | ✅ present |
| Reliability engineering | retries, deterministic fallback, idempotency, invariants | ✅ present |
| Guardrails / safety | structural: no dx/rx tools, citation invariant, gate | ✅ present (strong) |
| Prompt-injection resistance | prose-as-data + deterministic scorer | ✅ present |
| Reproducibility | hashing, pinned deps, deterministic scorer | ✅ present |
| Evaluation | 16 cases, invariants, honest failure | 🟡 strong but offline-only |
| Dynamic planning / adaptive routing | fixed graph (bounded) | 🟡 partial — deliberate |
| **Knowledge grounding (RAG)** | deterministic lexical retrieval over the YAML KB (no embeddings); evidence is display-only | ✅ present |
| **Calibrated confidence + abstention** | deterministic coverage/deferral signal; no calibrated probability | 🟡 partial |
| **Durable/resumable execution** | durable approve/resume over `checkpoints.db` (Phase 6) | ✅ present |
| **Observability / tracing / replay** | local span tracing + read-only replay (Phase 7) | ✅ present |
| Online eval / calibration / drift | offline report only | ❌ gap |
| Cost/latency management | cost reported; latency in [`EVALS.md`](EVALS.md) §3; no routing/caching/budgets | ❌ gap |
| Approver authentication | recorded, not authenticated | ❌ gap (declared) |
| MCP sampling / elicitation (current spec) | static tool calls only | ❌ gap |
| Long-term / episodic memory | per-case only | ⛔ deliberate |
| Multimodal (voice/vision) | text only | ⛔ deliberate |
| Multi-agent (planner/executor/critic) | single graph + `verify` node | ⛔ deliberate |
| Runtime self-learning | none | ⛔ deliberate (unsafe here) |
| Broad action space / computer use | narrow, gated | ⛔ deliberate |

### Genuine gaps worth closing (safe, and they raise "agentic depth" — 30 pts)

**Still open:**
1. **Calibrated confidence + abstention** (selective prediction) — the coverage signal is
   deterministic, not a calibrated probability.
2. **MCP sampling / elicitation** — the current spec's agent↔server negotiation.
3. **Model routing / caching / budgets** — attacks the desk latency ([`EVALS.md`](EVALS.md) §3).
4. **Online eval + calibration + drift monitoring**.
5. **Multimodal intake** (voice + chart/cuff photo) — the real desk UX.

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
- **Rehearse the live review AND perform it on the day** — the guarded `docs/REVIEW.md` runbook, incl.
  the data-only "add a discriminator to `data/sats_discriminators.yaml` live and re-score" beat.
- **A single <3 min video that carries the tool calls** (G5) — scripted in `docs/DEMO.md`.

**UX (remaining):** vitals-entry ergonomics (U4: numeric keypad, units, defaults),
environment/accessibility (U5), and approver authentication (G-8).

**Polish:**
- Optionally add a **frontier-model comparison on synthetic data** (the brief invites it).

---

## 9. Bottom line

- **Build: done.** All 6 "what to build" items, all safety rules, no disqualifiers; repo frozen, tagged
  (`v1.0-submission`) and pushed; the full suite is green (**`463 passed`**); honest measured evaluation; the v1.1 milestone
  (Phases 6–12) adds durable execution, tracing/replay, retrieval grounding, deferral, and the desk
  surface; the post-v1.1 desk hardening adds the SRP split (`server.py` 1169 → 375 lines across nine
  modules) and the queue-position panel (the gated write is now visible on commit).
- **Submission: one step short.** Two recordings exist — the 33 s terminal candidate
  (`docs/assets/triagedesk-demo.mp4`) and the captioned 2:55 desk walkthrough (`docs/assets/desk-demo.mp4`)
  — but upload the video: neither is hosted.
- **Score ceiling:** capped mainly by **fit-to-desk (no clinician review; desk surface still a
  prototype)** and **demo (short + unhosted)** — both improvable before 2026-10-15.
- **State of the art:** already ahead of most on **trust, auditability, and honesty**; the v1.1 line
  closed the retrieval, tracing, durable-execution and confidence clusters, leaving **memory,
  multimodal, online eval** and **calibrated confidence** as the open capability gaps.
