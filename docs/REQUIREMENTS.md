# REQUIREMENTS — TriageDesk

> **Source of truth:** the challenge brief at
> <https://agentic-africa-challenge.lovable.app/tracks/healthcare>
> This document tracks **every** requirement, judging criterion, and instant-disqualifier from that
> page, and maps each to the artifact that satisfies it and its current status.
>
> **Updated 2026-10-13, post-build (v1.1 milestone close).** Full honest gap analysis — the one
> submission gap, UX, and state-of-the-art gaps — lives in [`../STATUS.md`](../STATUS.md).
>
> Legend — Status: ✅ **done & verified** · 🟡 **partial / open** · ⛔ **not done / blocked** · ⏳ **active
> (time-bounded)**.

---

## 0. How to read this document

Each item has: **ID · the requirement (paraphrased from the brief) · how we satisfy it · owning
artifact · status**. Section 10 is the single **traceability matrix**. Section 11 lists **open gaps and
risks** — items we cannot yet close, tracked honestly.

---

## 1. Eligibility & submission rules

| ID | Requirement (from brief) | How we satisfy it | Artifact | Status |
| --- | --- | --- | --- | --- |
| EL-1 | Open to developers aged 18+, resident anywhere in Africa; solo or teams up to 3 | Solo entry; eligibility confirmed at application | PROJECT.md §8 | 🟡 confirm at submit |
| EL-2 | One project per team; may not enter same project under more than one theme | Single theme: Symptom-based priority scoring | PROJECT.md §4 | ✅ |
| EL-3 | Repo must carry an OSI-approved licence | Apache-2.0 | LICENSE | ✅ |
| EL-4 | Submissions in English; agent may handle documents in any language | English build; multilingual kept out of scope | PROJECT.md §6 | ✅ |
| EL-5 | New work, built during the submission period; existing project resubmitted is not allowed | Greenfield; first commit 2026-10-09, inside the window | ROADMAP.md | ✅ |
| EL-6 | Repos cloned at deadline; commits after deadline disqualify | Frozen + tagged `v1.0-submission`; commits monitored until 2026-10-15 | ROADMAP.md §Freeze | ⏳ active |
| EL-7 | Ownership retained; organiser permission to reference/demonstrate | Apache-2.0 grants use; note in README | LICENSE / README | ✅ |

## 2. Safety non-negotiables (from the Overview)

| ID | Requirement | How we satisfy it | Artifact | Status |
| --- | --- | --- | --- | --- |
| SN-1 | Agent **never diagnoses** | No diagnostic output exists; outputs are priority + citations only; safety clause in prompts and README | ../ARCHITECTURE.md §6 | ✅ |
| SN-2 | Agent **never prescribes** | No medication/treatment tool exists | ../ARCHITECTURE.md | ✅ |
| SN-3 | Agent **never decides who gets seen** | Only tool that changes queue state is gated on named approval | ../ARCHITECTURE.md §5 | ✅ |
| SN-4 | **Nurse/clinician confirms every priority** before patient sent to a bay | LangGraph `interrupt()` approval gate before `commit_priority` | ../ARCHITECTURE.md §5 | ✅ |
| SN-5 | If condition changes while waiting, agent **raises for a second look; cannot act on it** | `raise_recheck_flag` is non-mutating relative to queue position; flags only | ../ARCHITECTURE.md §4 | ✅ |
| SN-6 | **Every priority cites** the vitals/symptom behind it; unsourced flag is worse than none | Deterministic scorer emits `triggered_rules[]` + `citations[]`; `verify` node rejects uncited output | ../ARCHITECTURE.md §3–4 | ✅ |

## 3. What to build

| ID | Requirement (verbatim intent) | How we satisfy it | Artifact | Status |
| --- | --- | --- | --- | --- |
| BW-1 | **Your own MCP server**, three or more different tools | `triagedesk` server: `normalize_case`, `match_discriminators`, `retrieve_evidence`, `score_priority`, `assess_confidence`, `raise_recheck_flag`, `commit_priority` (7 tools) | ../ARCHITECTURE.md §4 | ✅ |
| BW-2 | At least one tool **does something** — scores a priority, raises a re-check flag, routes a referral; read-only is not enough | `score_priority` (scores), `raise_recheck_flag` (flags), `commit_priority` (writes) are all acting tools | ../ARCHITECTURE.md §4 | ✅ |
| BW-3 | **One MCP server you did not write** — community, official, or vendor + one line on why it beats writing it yourself | Borrow **SQLite MCP** (`mcp-sqlite@1.0.9`); "persistence, schema and query safety are solved — hand-rolling a DB adds zero triage value" | ../ARCHITECTURE.md §4 | ✅ (read paths exercised — MCP-01) |
| BW-4 | **Open-source orchestration** — LangGraph / CrewAI / Pydantic AI / smolagents / Letta / Goose / n8n or equivalent; no closed no-code builders | **LangGraph** (open source) | DECISIONS.md D4 | ✅ |
| BW-5 | **One full task on an open-weights model** | The **entire end-to-end triage task** (raw input → plan → tool calls → sourced priority + handover) runs on **Qwen2.5** (open weights) via Ollama — the measured default is `qwen2.5:1.5b` ([`../EVALS.md`](../EVALS.md)); no frontier model in the required path | DECISIONS.md D3 | ✅ (demo default is the offline golden fixture; `--online` runs the model) |
| BW-6 | Patient health data **cannot leave the country / full stop** | Fully local inference + synthetic data; no network egress in the agent path | ../ARCHITECTURE.md §7 | ✅ (`strace`-verified) |
| BW-7 | Frontier model **optional, synthetic data only** | Frontier comparison (if any) runs only on the synthetic fixture; never required to run | PROJECT.md §6 C-3 | 🟡 optional, not built |
| BW-8 | **A logged tool call for every action** | Every tool call appended to the hash-chained audit log | ../ARCHITECTURE.md §6 | ✅ |
| BW-9 | **A gate on every irreversible one** — before a **priority**, a **referral**, or a **deterioration flag** reaches a patient's queue position | `commit_priority` is the only queue-mutating tool and requires an approval token; a re-check flag is surfaced as a second-look request and does not reorder the queue on its own | ../ARCHITECTURE.md §5 | ✅ |
| BW-10 | Log includes **inputs, outputs, timestamps, and a named clinician approving** | Audit schema fixed in ../ARCHITECTURE.md §6; approver + role captured | ../ARCHITECTURE.md §6 | ✅ |

## 4. What to submit

| ID | Requirement | How we satisfy it | Artifact | Status |
| --- | --- | --- | --- | --- |
| SB-1 | **Public code repository** | GitHub public repo — `github.com/BrianMuigai/TriageDesk` | ROADMAP.md | ✅ |
| SB-2 | **OSI-approved licence** | Apache-2.0 | LICENSE | ✅ |
| SB-3 | **README** that gets a stranger running in one command | `uv run triagedesk demo`; `uv run` auto-syncs from the committed `uv.lock`, so there is no separate install step | ../README.md | ✅ one command — G3 resolved |
| SB-4 | **Demo video under 3 minutes**, **uploaded to YouTube or Vimeo and publicly visible** | Recorded (`docs/assets/triagedesk-demo.mp4`, 33 s) — **not yet uploaded** | docs/DEMO.md | ⛔ the one submission blocker — STATUS G1 |
| SB-5 | **Unedited agent run, tool calls on screen** — **not slides** | Real unedited terminal run of `triagedesk demo --online`, incl. a failure | docs/assets/triagedesk-demo.mp4 | ✅ |
| SB-6 | **~300-word text description**: what it does, sub-theme, facility & workflow | DESCRIPTION.md — within ±10% of 300 (guarded by `tests/test_docs_final.py`) | DESCRIPTION.md | ✅ |
| SB-7 | **ARCHITECTURE.md — one page**: agent shape, MCP servers built vs borrowed, why | ARCHITECTURE.md (one page) | ../ARCHITECTURE.md | ✅ |
| SB-8 | **EVALS.md**: 8+ test tasks with pass/fail, plus one failure not fixed + what you'd try next | 16 cases, measured; E-09 declared | ../EVALS.md | ✅ (counts reconciled — G4/STATUS) |
| SB-9 | Repo that **runs** (not a repo that does not run) | One-command run + synthetic fixture + CI smoke test | ROADMAP.md | ✅ |

## 5. Data conduct

| ID | Requirement | How we satisfy it | Artifact | Status |
| --- | --- | --- | --- | --- |
| DC-1 | Data choice: public triage scale, own synthetic stream, or consented case data | Published scale (SATS) + own synthetic stream | SATS.md | ✅ |
| DC-2 | **Synthetic data is the default**, not the fallback | All fixtures synthetic; no external data | PROJECT.md §9 | ✅ |
| DC-3 | **Never real patient data without consent**, even de-identified | No real data used at all | PROJECT.md §9 | ✅ |
| DC-4 | Agent may handle documents in any language; submission in English | Submission English | PROJECT.md §6 | ✅ |

## 6. Judging criteria (100 pts) — design intent

| ID | Criterion (pts) | What the judge checks | Our answer | Artifact |
| --- | --- | --- | --- | --- |
| JC-1 | Agentic depth & MCP craft (**30**) | Plans, calls tools, recovers — not one model call in a loop; tool boundaries a stranger could reuse | Explicit LangGraph plan with a `verify`/retry loop, missing-vital recovery, tool-failure recovery, safe abstention, and seven reusable tool contracts | ../ARCHITECTURE.md §3–4 |
| JC-2 | Open-source rigour (**20**) | Clone & run; README honest about unfinished | One-command run, synthetic fixture, CI smoke test, honest status table incl. unfinished items | README, EVALS |
| JC-3 | Fit to triage desk (**20**) | Named nurse does a real thing faster, at the desk, under queue pressure; *did you talk to one?* | Models the real five-step SATS desk process with an assumption-labelled throughput model; a loopback desk surface now ships ([`DEMO.md`](DEMO.md), [`DESK.md`](DESK.md)), while **no clinician interview available** remains a declared gap | PROJECT.md §3, §3.1; EVALS §7; STATUS §6 |
| JC-4 | Evaluation & reliability (**15**) | Honest test set, not curated to pass; run-to-run variation measured or hidden | 16 cases incl. a declared failure; 3 runs/case; variation + latency + cost reported | ../EVALS.md |
| JC-5 | Defensibility (**10**) | Priority survives a clinical-audit question; sourced, readable log; known cost per run | Deterministic SATS scorer + exact citations + hash-chained audit log + measured cost/run (tokens + wall-clock) | ../ARCHITECTURE.md §3, §6; ../EVALS.md §3.1 |
| JC-6 | Demo (**5**) | Three clear minutes, including where it fails | Recorded run with a failure segment (33 s) | docs/DEMO.md |

## 7. Instant disqualifiers — avoidance

| ID | Disqualifier (from brief) | Our structural safeguard | Status |
| --- | --- | --- | --- |
| DQ-1 | Chatbot wrapper with no autonomous tool use | Graph plans, calls acting tools, verifies, recovers; tools change state | ✅ |
| DQ-2 | MCP server that proxies a single endpoint | Our server exposes seven distinct tools with real logic; the borrowed server is external storage, not a proxy | ✅ |
| DQ-3 | Agent that diagnoses / prescribes / moves a patient without approval | No dx/rx tools; queue write gated on named approval | ✅ |
| DQ-4 | A priority level with no source | `verify` node blocks any uncited priority; INV-1 asserts it | ✅ |
| DQ-5 | Real patient health data without consent | Synthetic only; no real data | ✅ |
| DQ-6 | A repository that does not run | One-command run + a CI smoke test (`.github/workflows/smoke.yml`) that runs the demo on the synthetic fixture | ✅ |
| DQ-7 | Results presented as real runs that never happened | ../EVALS.md distinguishes planned vs measured; report is `mode: real` with a digest | ✅ |
| DQ-8 | Someone else's project, undisclosed | Greenfield; third-party components disclosed in DECISIONS.md | ✅ |

## 8. Security & hardening (beyond the brief's minimum)

Not required by the brief, tracked because the agent touches a clinical queue. Full detail in
[`../SECURITY.md`](../SECURITY.md).

| ID | Item | How we satisfy it | Artifact | Status |
| --- | --- | --- | --- | --- |
| SW-1 | **Untrusted input treated as data** (prompt-injection resistance) | Complaint parsed to typed fields; deterministic scorer; citation invariant; no source = rejected | ../SECURITY.md §4, DECISIONS.md D15, EVALS E-13 | ✅ (E-13/E-14 exercised) |
| SW-2 | **Least privilege** | Tool allowlist; no network/credentials; the gated write is the only mutation | ../SECURITY.md §5 | ✅ |
| SW-3 | **Idempotent irreversible writes** | `commit_priority` keyed by `case_id` + content hash | ../SECURITY.md §7, DECISIONS.md D16 | ✅ (key breadth — STATUS G4/integration) |
| SW-4 | **Approver identity + role recorded** | `approved_by`, `role`, `approved_at`, `decision`; authentication is a declared production requirement | ../SECURITY.md §6 | 🟡 authn deferred — G-8 |
| SW-5 | **Version pinning & hashing** | Prompts, model version, scale data, tool schemas pinned + hashed; audit names versions | ../SECURITY.md §8, DECISIONS.md D17 | ✅ |
| SW-6 | **Documented threat model** | T-1…T-10 mapped to controls | ../SECURITY.md §3 | ✅ |

## 9. Stage 2 — the live technical review

| ID | Requirement | How we prepare | Artifact | Status |
| --- | --- | --- | --- | --- |
| ST-1 | 10-min code walkthrough + a **new requirement added live** while judges watch | Keep SATS rules in **YAML data files**, so adding a rule/level is a one-line edit; keep graph nodes small and named we can explain line-by-line | [`REVIEW.md`](REVIEW.md) (the guarded runbook), ../ARCHITECTURE.md §8, DECISIONS.md D14 | ✅ rehearsed — STATUS G6 resolved |

## 10. Traceability matrix (requirement → artifact)

| Artifact | Requirements covered |
| --- | --- |
| `../README.md` | SB-3, JC-2 |
| `../STATUS.md` | honest gap analysis (G1–G9, UX U1–U7, SOTA gaps) |
| `PROJECT.md` | EL-2, EL-4, SN-1…6, BW-6, DC-2, DC-3, JC-3 |
| `REQUIREMENTS.md` | all (index) |
| `../ARCHITECTURE.md` | BW-1, BW-2, BW-3, BW-6, BW-8, BW-9, BW-10, SN-3…6, JC-1, JC-5, ST-1 |
| `../EVALS.md` | SB-8, JC-4, JC-5 |
| `DESCRIPTION.md` | SB-6 |
| `DECISIONS.md` | BW-4, BW-5, DQ-8, SW-1, SW-3, SW-5 |
| `../SECURITY.md` | SW-1…SW-6, JC-5 |
| `ROADMAP.md` | EL-6, SB-4, SB-5, SB-9, ST-1 |
| `SATS.md` | DC-1, JC-5 |
| `docs/DEMO.md` | SB-4, SB-5, JC-6 |
| `LICENSE` | EL-3, SB-2 |

## 11. Open gaps & risks (tracked honestly)

| # | Gap / risk | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- |
| G-1 | **No clinician interview** | Loses part of JC-3 (20 pts) | Ground in published SATS/OPD workflow; declared gap; attempt one call before 2026-10-15 | **OPEN** |
| G-2 | RAM ceiling — a 4B may not fit | BW-5 | **Resolved:** measured in Phase 1; `qwen2.5:1.5b` default, `qwen3.5:4b` fallback; both run E2E | ✅ resolved |
| G-3 | Host Python is 3.14 | wheels | **Resolved:** Python 3.12 pinned via `uv` | ✅ resolved |
| G-4 | Borrowed MCP server availability | BW-3 | **Resolved:** `mcp-sqlite@1.0.9` adopted (World A); MCP spec 2026-07-28 | ✅ resolved |
| G-5 | Multi-step tool-calling reliability on a small CPU model | JC-1 | **Resolved:** explicit graph + structured output; E-12 covers failure recovery | ✅ resolved |
| G-6 | Deadline (2026-10-15) | EL-6 | Frozen + tagged; **no post-deadline commits** | ⏳ active |
| G-7 | Paediatric triage out of scope | Clinical completeness | **Resolved:** safe abstention + escalation (E-06); never mis-scores a child | ✅ resolved |
| G-8 | **Approver authentication deferred** (identity recorded only) | T-8 | Declared production requirement (`../SECURITY.md` §6) | **OPEN** (declared) |
| G-9 | **Demo video not uploaded** (SB-4) | The one submission blocker | Upload `docs/assets/triagedesk-demo.mp4` to YouTube/Vimeo (Public) | **OPEN** — human |
| G-10 | **README "one command" is two** (SB-3) | Open-source rigour | **Resolved:** `uv run triagedesk demo` is the literal one-liner (`uv run` auto-syncs); a test guards it (D11-09) | ✅ resolved |
| G-11 | **Residual desk-UX gaps** (JC-3, JC-6) | Fit-to-desk + demo | Desk surface + real approve/edit/dismiss gate shipped (Phase 10, [`DESK.md`](DESK.md)); remaining: vitals-entry ergonomics, environment/accessibility, approver authn (STATUS §6) | 🟡 **partial** |

> The full ranked analysis, UX considerations, and state-of-the-art gap assessment are in
> [`../STATUS.md`](../STATUS.md).
