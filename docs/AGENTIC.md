# AGENTIC — is this a rules engine with an LLM bolted on?

> **The reviewer's question, verbatim:**
>
> *"Is this genuinely an agentic system, or a deterministic clinical rules engine with an LLM
> extraction step and an MCP integration?"*
>
> This page answers it with behaviour, a structural proof, and a measured number — not with
> adjectives. Every figure lives in [`EVALS.md`](EVALS.md) §3.3 and is generated from
> `evals/results/report.json` and `evals/results/report.baseline.json`; this page links to it
> rather than restating it as an independent source.

## 1. What the system decides — and where

The graph has **two layers with different authorities**:

| Layer | Decides | Authority |
| --- | --- | --- |
| **Adaptive envelope** (`retrieve → plan → action → … → finish_investigation`) | *how much* to investigate before scoring: gather cited evidence, ask one targeted question, re-read the note, or stop | the model **proposes** one action from a closed set; `core.planner` — deterministic code — **decides** whether that action is admissible |
| **Frozen safety kernel** (`score → ground → verify → recheck → assess → approval_gate → commit → handover`) | *what the answer is*: the colour, its citations, the recheck flag, the deferral, the commit | deterministic code and one named clinician; **no model vocabulary exists** for any of it |

The planner is real: it changes what the system does next, per case, from the state it observes.
On an ambiguous complaint it can ask; on a missing scored vital it can re-read; on a case with no
evidence yet it can gather; and it can stop. That is a decision the extraction step cannot make.

## 2. What it structurally cannot decide

This is the part that matters more than the autonomy, and it is enforced by construction, not by
prompting:

- **The action set is closed and typed.** `PlanAction` has exactly four members —
  `gather_evidence`, `ask_question`, `re_extract`, `finish_investigation`. None names `score`,
  the gate or the commit. The router's edge map is *derived* from the enum, so an action cannot
  be added in one place and silently routed in another.
- **The model is never the authority.** `core.planner.validate_proposal` accepts a proposal only
  if the current typed state admits it; a missing, malformed, inadmissible or over-budget
  proposal is replaced with `finish_investigation`, with `overridden=True` and a reason. A bad
  proposal cannot widen what the graph can do — it can only end the investigation.
- **`finish_investigation` is the only edge into `score`.** Every investigation action loops
  back to the planner (or to retrieval); none has an edge to `score`, `approval_gate` or
  `commit`. `commit` keeps exactly one inbound edge, `approval_gate`. The kernel is a
  non-skippable suffix.
- **The budget is hard.** At most `MAX_INVESTIGATION_STEPS` decisions, no repeated action, one
  clarification round. Budget exhaustion admits only the exit; it never guesses.
- **The structural claims are tested on the compiled graph**, not on a copy:
  `tests/test_frozen_kernel.py` and `tests/test_eval_adaptive.py` assert the predecessor sets on
  both the adaptive and the baseline arm.

So the honest formulation is: **the model decides how much to investigate; it never decides what
the answer is.** A rules engine cannot choose to ask a question or re-read a note; a free agent
could choose to invent a colour, and this one cannot.

## 3. The measured delta — does the envelope earn its keep?

The same 24-case suite, same fixtures, same model, is run twice: the **adaptive** arm (planner on)
and the **baseline** arm (`retrieve → finish_investigation`, the v1.2 path). The generated table
in [`EVALS.md`](EVALS.md) §3.3 reports colour correctness, coverage, clarified/deferred, mean
steps, guard-override rate and p50/p95 for both arms, with the delta.

The delta is published as measured. If the planner adds steps and latency without moving colour
correctness on this suite, that is what the table says — the suite is deliberately small and the
baseline already scores well, so the honest reading is "the envelope buys *adaptive behaviour*,
not accuracy, on these cases". The cases that make the envelope observable are the ambiguous and
missing-vital ones: the baseline cannot ask, and the adaptive arm can.

## 4. The counterweight: the deterministic emergency bypass

Autonomy is only defensible if the most urgent case does not wait for it. A deterministic
pre-check runs **before any model call**: a critical structured case takes the fast arm straight
to `retrieve → finish_investigation`, skipping extraction **and** the planner. The kernel still
scores, verifies, rechecks, assesses and gates; the clinician still decides. The bypass can only
make the path shorter, never less safe, and it is audited. This is why "the planner may decide"
does not mean "a sick patient waits for a 1.5B model to think".

## 5. What the artefacts mean (DOC-06)

- **The committed queue row is authoritative for handover — not the printed card.** The card is a
  rendering; the queue row written by `commit_priority` under a named approval is the record.
- **Answering a clarification is not approval.** An elicited answer is appended as an observation.
  It never sets a colour, never advances the case past the gate, and is typed separately from the
  approval token. A declined, cancelled or unavailable elicitation is not a negative finding.
- **Approver identity is recorded, not authenticated (G4).** The gate captures `approved_by` and
  `role`; production requires an authenticated identity (SSO/badge) before the token is issued.
  This is a declared gap, not a claim.
- **Structured observations are two-state today.** A sign is *stated* or *missing*; text-level
  negation ("no chest pain", "denies bleeding") is handled in the extraction/merge rules. A
  four-state observation model (stated-present / stated-absent / unknown / not-assessed) is an
  **outstanding limitation** — it is not drawn as if it existed.

## 6. The limits we are not hiding

- **Bounded action set, not free-form planning.** The planner chooses among four read-only
  actions inside a 3-step budget. It cannot compose new actions, write code, call arbitrary
  tools, or plan several moves ahead.
- **The model is a 1.5B CPU model.** Its proposals are slow and sometimes inadmissible; the guard
  exists because of that, and the measured guard-override rate is published rather than hidden.
- **Elicitation needs a client that can answer.** In-process callers honestly receive
  `unavailable`; the four outcomes are distinguished, and a refusal is never converted into a
  value.
- **The measurement is small.** 24 synthetic cases, one model, one machine. It demonstrates that
  the envelope changes behaviour; it does not establish a clinical accuracy gain.
- **No clinician review** has been obtained (`EVALS.md` §7). Nothing here is a clinical claim.

## 7. Where to look

- The measurement: [`EVALS.md`](EVALS.md) §3.3 (generated).
- The topology and the gate: [`ARCHITECTURE.md`](ARCHITECTURE.md) §3–5.
- The decisions: [`docs/DECISIONS.md`](docs/DECISIONS.md) D31–D34 and the D1 revision.
- The threat model: [`SECURITY.md`](SECURITY.md) §3 (T-11, T-12, T-13).
- The code: `src/triagedesk/core/planner.py`, `src/triagedesk/graph/planning.py`,
  `src/triagedesk/graph/build.py`.
