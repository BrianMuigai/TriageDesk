# STATUS — TriageDesk vs the Agentic AI for Africa Challenge

> **Honest self-assessment, post-submission.** Refreshed 2026-11-05 against the live brief:
> <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> This is a gap analysis, not a victory lap. It says what is done, what is missing, and what would
> move the score.
>
> **How to read it.** Two kinds of claim appear below and they are labelled. **Measured** means a
> command in this repository produced it (re-run on 2026-11-05). **Estimate** means a judgement —
> the self-score is the main one, and it is marked as such. [`EVALS.md`](EVALS.md) is the single
> source for every evaluation number and [`ARCHITECTURE.md`](ARCHITECTURE.md) for the agent shape;
> this file links them rather than restating their figures.
>
> **What is live.** `v1.0-submission` is the frozen, tagged submission commit. The live branch
> (`post-submission/desk-fit`, PR #2 against `main`) is **not** frozen: it carries additive
> post-submission work (Phase 13 *Desk Fit*, Phase 14 *Evidence Fidelity*). Read "shipped" below as
> "on the live branch"; read "submitted" as "on the tag".

---

## 0. Verdict

**Not 100.** The build is complete and the eligibility bar is met. The submission is delivered —
including the demo video, which was **uploaded to Google Drive during submission**. One 20-point
criterion stays partially met because **no clinician or triage nurse has reviewed the system**, and
that is the single largest remaining score gap. The latency figure is pessimistic (measured under
host load) and a quiet-machine re-run is pending.

| Dimension | Status | Basis |
| --- | --- | --- |
| Eligible / not disqualified | ✅ none of the eight structural disqualifiers triggered | measured (`docs/REQUIREMENTS.md` §7) |
| "What to build" (6 items) | ✅ **6/6** | measured |
| "What to submit" (5 items) | 🟡 **5/5 delivered** — video on Google Drive; the brief's YouTube/Vimeo wording is a residual caveat (G1) | measured |
| Judging criteria (100 pts) | 🟡 **est. 83–93** (mid-80s to low-90s) | **estimate** |
| Instant disqualifiers (8) | ✅ none triggered | measured |
| Test suite | ✅ **600 passed** | measured (`uv run pytest -q`) |
| Measured evaluation | ✅ 19/19 colour-expected runs correct · under-triage 0 · over-triage 0 · gate delivery 16/16 · E-09 declared failure · E-11 recorded gate failure | measured (digest `8b600014`, [`EVALS.md`](EVALS.md) §3) |

*Test caveat:* a gitignored root `spans.jsonl` left by an earlier demo or eval run makes
`test_no_spans_artifact_is_written_to_the_repo_root` fail until it is deleted. The 600-pass figure
above is from a clean tree.

---

## 1. "What to build" — 6/6 ✅

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| Own MCP server, ≥3 different tools, ≥1 that acts | 7 tools in `src/triagedesk/mcp/server.py`: `normalize_case`, `match_discriminators`, `retrieve_evidence`, `score_priority`, `assess_confidence`, `raise_recheck_flag`, `commit_priority`. `score_priority` scores, `raise_recheck_flag` flags, `commit_priority` writes | ✅ |
| One MCP server you did not write, + one line on why | borrowed, version-pinned `mcp-sqlite@1.0.9`; its read paths are genuinely exercised on the agent path, not merely declared; rationale in [`docs/DECISIONS.md`](docs/DECISIONS.md) D5 | ✅ |
| Open-source orchestration | LangGraph state machine (`src/triagedesk/graph/`) — no closed no-code builder anywhere in the path | ✅ |
| One full task on an open-weights model; data cannot leave the country | the whole end-to-end task runs locally on `qwen2.5:1.5b` via Ollama (the measured default, D3); no network egress in the agent path (`strace`-verified). `qwen3.5:4b` is a documented alternative, not an automatic fallback | ✅ |
| Logged tool call for every action, and a gate on every irreversible one | hash-chained audit (`src/triagedesk/store/audit.py`); `commit` has exactly one inbound edge, from `approval_gate` (`src/triagedesk/graph/build.py`) | ✅ |
| New work, built during the submission period | greenfield; first commit 2026-10-09 | ✅ |

Not counted, because the brief makes it optional: a frontier-model comparison on synthetic data
(BW-7) is **not built**.

## 2. "What to submit" — 5/5 delivered 🟡

| Requirement | Status |
| --- | --- |
| Public repo + OSI licence + README that runs in one command | ✅ public, Apache-2.0; `uv run triagedesk demo` (`uv run` syncs from the committed `uv.lock`, so there is no separate install step) |
| Demo video < 3 min, uploaded publicly | 🟡 **delivered** — `docs/assets/triagedesk-demo.mp4` (2:28, measured) is a real unedited screen recording with the seven owned tools' calls on screen, the measured evaluation, and the declared E-09 failure. It was **uploaded to Google Drive during submission** ([folder](https://drive.google.com/drive/folders/1s1sgXHJjr6XsGr-ggTlyY6BT3FSG9ZJ3)). The brief names YouTube/Vimeo, so the platform wording is the residual caveat (G1) — not an unuploaded video |
| ~300-word description | ✅ `DESCRIPTION.md`, within ±10% of 300 words, guarded by `tests/test_docs_final.py` |
| `ARCHITECTURE.md` — one page | ✅ one page, guarded (≤ 700 words and ≤ 110 lines) by the same test |
| `EVALS.md` — 8+ tasks, plus one failure not fixed and what you would try next | ✅ 16 cases; E-09 declared with a "what we would try next" list |

All five artefacts exist in the repository. The only partially-met item is the **hosting platform**
of the video, not its content or its existence.

## 3. Judging criteria — honest self-score (**estimate**)

| Criterion | Pts | Est. | Why not full |
| --- | --- | --- | --- |
| Agentic depth & MCP craft | 30 | **27–29** | Seven reusable tool contracts, an explicit graph, one fail-closed evidence check, and three recovery paths (missing vital, tool failure, out-of-scope). Docked for: no MCP sampling/elicitation, and a fixed graph rather than dynamic planning — a deliberate safety choice that still reads as less "agentic depth" than a planner |
| Open-source rigour | 20 | **18–19** | One command from a clean clone, committed lock, CI smoke test, honest status docs, and a desk package split by responsibility. Docked for: the borrowed server needs Node and a one-time `npx` fetch, and only Linux/macOS is exercised |
| **Fit to the triage desk** | 20 | **12–16** | A real desk surface now ships (acuity-ordered read-only waiting room, keyboard-first vitals, real approve/edit/dismiss gate, background precompute) — but **no clinician or triage-nurse review** (G2), it is a single-machine loopback prototype (G9), English-only, and model latency is not yet "seconds" on a loaded machine (G3) |
| Evaluation & reliability | 15 | **13–14** | Measured and honest: 3 runs/case, safety invariants on every run, one declared failure, one recorded gate failure, variation and cost reported. Docked for: E-09 unfixed, E-11 still failing the gate, roughly half the reached-assess runs deferring, and no online eval or drift monitoring (G6) |
| Defensibility | 10 | **9–10** | Deterministic SATS scorer, exact citations, hash-chained audit, known cost per run. Nothing material is missing |
| Demo | 5 | **4–5** | Complete 2:28 recording, tool calls on screen, the measured eval and the declared failure shown. Docked only if the brief's YouTube/Vimeo wording is enforced (G1) |
| **Total** | **100** | **83–93** | **estimate** — the band is wide because three criteria turn on facts outside the repository (clinician access, hosting platform, a quiet machine) |

## 4. Instant disqualifiers — none ✅

No chatbot wrapper · not a single-endpoint proxy · no diagnosis, prescription, or autonomous queue
move · every priority cited · synthetic data only · the repo runs from a clean clone · results are
real and digest-stamped · greenfield and disclosed.

## 5. Gaps & misses (ranked)

1. **G2 — No clinician or triage-nurse review.** The 20-point "fit to the desk" criterion asks
   directly *"did you talk to one?"*. We declare the gap ([`EVALS.md`](EVALS.md) §7) but still lose
   the points. **Fix:** one real triage-nurse or clinician review, plus an attributed quote in
   `EVALS.md` §7. This is the single biggest available score mover.
2. **G3 — Latency is not yet "seconds" on a loaded machine.** The measured p50 is 19.98 s and p95 is
   55.03 s, but that re-run happened under host load (load average 8.4–10.9 on 12 cores); a
   single-case re-check on the same code gave 13.5–17.0 s. Treat the published figure as
   **pessimistic**; a quiet-machine re-run is pending. The deterministic scorer is instant — local
   model extraction dominates.
3. **G1 — Demo hosting platform.** The video is delivered and uploaded, but to Google Drive. The
   brief names YouTube/Vimeo. Re-hosting the existing 2:28 file there closes it; the content does
   not change. *(Residual caveat, not a blocker.)*
4. **G4 — Approver identity is recorded, not authenticated.** The gate captures `approved_by` and
   `role`; it cannot prove who typed them. An authenticated approver (SSO/badge) is a production
   requirement, declared in [`SECURITY.md`](SECURITY.md) T-8.
5. **G5 — Two evaluation misses remain visible.** E-09 (vague complaint, discriminator not retrieved)
   is the declared failure; it now **defers** rather than under-triaging. E-11 is the one recorded
   gate failure. E-13 (prompt injection) is no longer a gate failure — it defers as reduced
   coverage. Details and the full table live in [`EVALS.md`](EVALS.md) §4 and §6.
6. **G6 — No online evaluation, drift monitoring, or calibrated probability.** The report is an
   offline measurement. Calibration is a declared small-sample ECE, explicitly **not** a validated
   calibrated probability.
7. **G7 — No MCP sampling or elicitation.** The server exposes static tool contracts; it never asks
   the client for a model call or a clarification mid-task.
8. **G8 — No multimodal intake.** Vitals and complaint are typed. Voice and a chart/cuff photo are
   the real desk interface and are absent.
9. **G9 — The desk is a single-machine, loopback-only prototype.** `127.0.0.1`, one shared terminal,
   English-only, no hospital-system integration, no multi-desk deployment.
10. **G10 — No automatic model fallback.** `qwen2.5:1.5b` is the measured default and `qwen3.5:4b`
    is documented as the alternative, but nothing switches between them at runtime.

## 6. UX considerations

**Why it matters here:** "Fit to the triage desk" (20 pts) is essentially a UX question — does a
nurse do a real thing *faster, at the desk, under real queue pressure?* — the demo (5 pts) is UX,
and the brief's schedule includes UX refinement.

### What a user actually touches today

| Actor | Current surface | Reality |
| --- | --- | --- |
| Triage nurse | a loopback desk surface (`uv run triagedesk desk`) plus the CLI | a real browser surface over the shipped graph — still single-machine and English-only |
| Clinician approver | a real **approve / edit / dismiss** gate over `interrupt()`/resume, with durable resume from `checkpoints.db` | the interaction is real; the approver's *authentication* is the declared gap (G4) |
| Reviewer / auditor | the hash-chained audit log and the read-only replay | every action is attributable and replayable |

The desk surface is offline by default (no model call). `--online` runs the local model on the
free-text complaint while the deterministic scorer still decides the colour. `GET /waiting` renders
the committed queue as an acuity-ordered, **read-only** waiting room — it never writes a row. The
complaint's extraction precomputes in the background while the nurse finishes the vitals, and the
form is keyboard-first: DOM order is tab order, so no pointer is required.

### UX gaps (ranked)

- **U1 — A prototype, not a deployed tool.** Loopback only, one shared terminal, no hospital-system
  integration, no multi-user concurrency story (G9).
- **U2 — Approver authentication is open.** The gate is real; the identity behind it is not proven
  (G4).
- **U3 — Latency versus "seconds".** The deterministic score is instant; local model extraction
  dominates and the published figure is pessimistic pending a quiet re-run (G3).
- **U4 — Vitals-entry ergonomics are still thin.** Keyboard-first entry ships; unit handling and
  missing-vital prompting do not.
- **U5 — Environment and accessibility are unaddressed.** Busy desk, interruptions, one-handed or
  gloved entry, shared terminal, English-only, no screen-reader pass.

### UX strengths (keep them)

Colour-coded, legible output · **citations shown next to the colour** (the automation-bias
mitigation) · no diagnosis or prescription framing · the failure is shown, not hidden ·
**queue-position-on-commit feedback** — the post-decision panel names the queue position the gated
write assigned, so the write is visible rather than implied · a timeout commits nothing (no default
approve) · one-command reproducibility for a reviewer.

---

## 7. State-of-the-art gap analysis

**Verdict:** a state-of-the-art **trustworthy** agent for a narrow, safety-critical niche — strong on
reliability, human authority, auditability, structural safety, and honest evaluation — but **not** a
state-of-the-art *general* agent. The distance to "cutting edge" is almost entirely the
**capability / knowledge / memory / observability** cluster.

| SOTA agent pillar | TriageDesk | Verdict |
| --- | --- | --- |
| Tool use / MCP craft | 7 owned tools + a borrowed SQLite MCP with exercised read paths | ✅ present |
| Explicit control flow / orchestration | LangGraph state machine | ✅ present |
| Human-in-the-loop / approval gate | `interrupt()` gate; real approve/edit/dismiss desk surface; durable resume | ✅ present |
| Reliability engineering | bounded extraction retry, deterministic fallback, idempotency, fail-closed terminals, invariants | ✅ present |
| Guardrails / safety | structural: no dx/rx tools, citation invariant, gate, fail-closed evidence check | ✅ present (strong) |
| Prompt-injection resistance | prose-as-data + deterministic scorer; E-13 adds no evidence | ✅ present |
| Reproducibility | hashing, pinned deps, deterministic scorer, sealed schema hash | ✅ present |
| Evaluation | 16 cases, invariants, honest failures | 🟡 strong offline; no online eval or drift (G6) |
| Dynamic planning / adaptive routing | fixed graph (bounded) | 🟡 partial — deliberate |
| Knowledge grounding (RAG) | deterministic lexical retrieval over the YAML KB (no embeddings); evidence is display-only | ✅ present |
| Grounded extraction | Phase 14 grounds every extracted sign in the complaint text, with a fail-closed check | ✅ present |
| Calibrated confidence + abstention | deterministic coverage/deferral signal; small-sample ECE, not a calibrated probability | 🟡 partial (G6) |
| Durable / resumable execution | durable approve/resume over `checkpoints.db` | ✅ present |
| Observability / tracing / replay | local span tracing + read-only replay | ✅ present |
| Online eval / calibration / drift | offline report only | ❌ gap (G6) |
| Cost / latency management | cost reported; latency reported; a desk precompute cache exists; no model routing or budgets | ❌ gap (G3, G10) |
| Approver authentication | recorded, not authenticated | ❌ gap (G4) |
| MCP sampling / elicitation | static tool calls only | ❌ gap (G7) |
| Long-term / episodic memory | per-case only | ⛔ deliberate |
| Multimodal (voice/vision) | text only | ⛔ deliberate (G8) |
| Multi-agent (planner/executor/critic) | single graph + `verify` node | ⛔ deliberate |
| Runtime self-learning | none | ⛔ deliberate (unsafe here) |
| Broad action space / computer use | narrow, gated | ⛔ deliberate |

### Genuine gaps worth closing (safe, and they raise "agentic depth" — 30 pts)

1. **Calibrated confidence + abstention** (selective prediction) — the coverage signal is
   deterministic; the ECE is a declared small-sample bound, not a probability.
2. **MCP sampling / elicitation** — the current spec's agent↔server negotiation; the natural home for
   the clarifying question E-09 needs.
3. **Model routing / budgets / a real fallback path** — attacks desk latency and makes the
   `qwen3.5:4b` alternative operational instead of documented.
4. **Online evaluation + drift monitoring.**
5. **Multimodal intake** (voice + chart/cuff photo) — the real desk interface.

### What we correctly chose *not* to have

Runtime self-learning, autonomous queue movement, long-term memory of patient data, free-form ReAct,
multi-agent autonomy, a frontier model in the required path, and a broad action space. Each would
make the system "more cutting-edge" in the generic sense **and make it unsafe** for triage. Their
absence is a feature — and it is the discipline the brief rewards ("three tools that work beat nine
that half-work").

---

## 8. Action list

**Delivered (no longer blocking):** the demo video is recorded (2:28) and uploaded to Google Drive
during submission. Submission itself is complete.

**Top score movers, in order:**
1. **One clinician or triage-nurse review** (G2) — an attributed quote in `EVALS.md` §7 and the
   README. The largest single gain available.
2. **A quiet-machine latency re-run** (G3) — re-run the measured evaluation on an idle host and let
   `scripts/emit_evals.py` republish the figures. The current number is pessimistic.
3. **Re-host the video on YouTube or Vimeo** (G1) — same file, no re-recording.

**Then (capability, in value order):** approver authentication (G4) · online eval and drift (G6) ·
calibrated confidence (G6) · MCP sampling/elicitation (G7) · multimodal intake (G8) · model routing
and a real fallback (G10) · vitals-entry units and missing-vital prompting (U4) · accessibility and
environment work (U5).

**Optional polish:** a frontier-model comparison on synthetic data (the brief invites it, and it must
never be required to run).

---

## 9. Bottom line

- **Build: done.** All 6 "what to build" items, all safety non-negotiables, no disqualifiers. The
  frozen submission tag is `v1.0-submission`; the live branch carries additive post-submission work
  and is not frozen. **600 tests pass** on a clean tree (delete a stray gitignored `spans.jsonl`
  first), and the evaluation is measured and digest-stamped.
- **Submission: delivered.** All five artefacts exist, and the demo video is recorded and uploaded.
  The one residual caveat is the hosting platform the brief names (G1).
- **Score ceiling:** capped mainly by **fit-to-desk** — the missing clinician review is worth more
  than any code change still on the list — then by the **pessimistic latency figure** and the
  **video platform**. Honest estimate: **83–93 of 100**, not 100.
- **State of the art:** already ahead of most on **trust, auditability, and honesty**. The remaining
  capability distance is **online eval, calibrated confidence, sampling/elicitation, multimodal
  intake, and memory** — the last of which is a deliberate omission, not an oversight.
