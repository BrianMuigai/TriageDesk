# STATUS — TriageDesk vs the Agentic AI for Africa Challenge

> **Honest self-assessment.** Refreshed 2026-10-13 (v1.1 milestone close) against the live brief:
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
| Eligible / not disqualified | ✅ (one confirmation pending — G9) |
| "What to build" (6 items) | ✅ **6/6** |
| "What to submit" (5 items) | 🟡 **4/5** — video not uploaded |
| Judging criteria (100 pts) | 🟡 **est. ~75–90** |
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
| Public repo + OSI licence + README one command | ✅ public, Apache-2.0 — one command (`uv run triagedesk demo`); G3 resolved |
| Demo video <3 min, **uploaded to YouTube/Vimeo, publicly visible** | ❌ recorded (`docs/assets/triagedesk-demo.mp4`, 33 s) but **NOT uploaded** (G1) |
| ~300-word description | ✅ `DESCRIPTION.md` — within ±10% of 300, guarded by `tests/test_docs_final.py` |
| ARCHITECTURE.md — one page | ✅ one page (see [`ARCHITECTURE.md`](ARCHITECTURE.md)) |
| EVALS.md — 8+ tasks + one unfixed failure | ✅ 16 cases; E-09 declared (G4) |

## 3. Judging criteria — honest self-score

| Criterion | Pts | Est. | Why not full |
| --- | --- | --- | --- |
| Agentic depth & MCP craft | 30 | **27–30** | Strong. Borrowed-server read paths now exercised (G7 resolved) |
| Open-source rigour | 20 | **18–20** | Honest README; one-command quickstart (G3 resolved) |
| **Fit to the triage desk** | 20 | **9–14** | **No clinician interview** (G2) + a prototype desk surface + model-extraction latency ([`EVALS.md`](EVALS.md) §3) (U1/U3) |
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
6. **G6 — resolved (Phase 12).** "A new requirement added live while we watch." The guarded
   [`docs/REVIEW.md`](docs/REVIEW.md) runbook rehearses the data-only extension and the 10-min code
   walkthrough — its `uv run triagedesk …` commands are exercised by `tests/test_review_runbook.py`,
   and the durable dismissal is driven end-to-end (pause → resume). What remains **human** is
   performing it live on the day.
7. **G7 — resolved (Phase 9).** The borrowed server's read paths (`db_info`, `list_tables`,
   `get_table_schema`, `read_records`) are now exercised behind the unchanged `Store` protocol
   (MCP-01); a mutation on the read path fails closed before reaching the server.
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
| Triage nurse | a **loopback desk surface** (`uv run triagedesk desk`) + the CLI | a real browser surface over the shipped graph — still single-machine and English-only |
| Clinician approver | a real **approve / edit / dismiss** gate over `interrupt()`/resume | the interaction exists; approver *authentication* stays a declared gap (G-8) |

### UX gaps (ranked) — re-scoped after Phase 10

- **U1 — The desk surface is a prototype, not a deployed tool.** Phase 10 ships a loopback browser
  surface ([`docs/DESK.md`](docs/DESK.md)) over the shipped graph; it is single-machine, English-only,
  assumes one shared terminal, and is not integrated with any hospital system.
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
no dx/rx framing · the failure is shown, not hidden · one-command reproducibility for a reviewer.

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

**Landed in v1.1 (Phases 6–10):** retrieval-grounded knowledge over the SATS KB (deterministic
lexical, no embeddings — Phase 9); a coverage/deferral signal (Phase 8); durable `checkpoints.db`
execution (Phase 6); span tracing + read-only replay (Phase 7); and the loopback desk surface
(Phase 10).

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
- **Live review rehearsed** — the guarded `docs/REVIEW.md` runbook, incl. the data-only
  "add a discriminator to `data/sats_discriminators.yaml` live and re-score" beat (G6 resolved).
- **E-07 and E-04 fixed** (Phase 11); the measured eval was re-run; E-09 stays declared (G4).
- **README one command — done**; the EVALS numbers are reconciled (G3/G4).

**UX (done in Phases 8–12):**
- Human-readable **priority card** (not JSON) — the desk surface renders it.
- A visible **"no match — nurse to confirm"** deferral banner — shipped (U4).
- The gate as a **real approve/edit/dismiss prompt** over `interrupt()`/resume — shipped (U2).
- Show the **fast deterministic path**; state the model latency honestly (U3) — in `docs/DEMO.md`.
- A one-screen **desk quickstart** — `docs/DESK.md`.

**UX (remaining):** vitals-entry ergonomics (numeric keypad, units, defaults), environment/accessibility
(U5), and approver authentication (G-8).

**Polish:**
- Extend the demo to ~2–3 min with the eval run + on-screen narration (G5) — scripted in `docs/DEMO.md`.
- Optionally add a **frontier-model comparison on synthetic data** (the brief invites it).

---

## 9. Bottom line

- **Build: done.** All 6 "what to build" items, all safety rules, no disqualifiers; repo frozen, tagged
  (`v1.0-submission`) and pushed; the full suite is green (`uv run pytest -q`); honest measured evaluation; the v1.1 milestone
  (Phases 6–12) adds durable execution, tracing/replay, retrieval grounding, deferral, and the desk
  surface.
- **Submission: one step short.** Upload the video.
- **Score ceiling:** capped mainly by **fit-to-desk (no clinician review; desk surface still a
  prototype)** and **demo (short + unhosted)** — both improvable before 2026-10-15.
- **State of the art:** already ahead of most on **trust, auditability, and honesty**; the v1.1 line
  closed the retrieval, tracing, durable-execution and confidence clusters, leaving **memory,
  multimodal, online eval** and **calibrated confidence** as the open capability gaps.
