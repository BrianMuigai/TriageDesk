# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Score Uplift

**Shipped:** 2026-10-13
**Phases:** 7 (6–12) | **Plans:** 19 | **Tasks:** 42 | **Tests:** 424 → 454

### What Was Built

- **Durable execution** (Phase 6): the lifecycle runs through the real `checkpointed_graph`; a paused case
  resumes after a full process restart on a content-derived `thread_id`; an `edit` supersedes the queue row in
  place (the queue is keyed on the immutable `CaseInput`, not the scored colour).
- **Local observability + read-only replay** (Phase 7): ONE JSONL span writer fed from the existing seams,
  cloud tracing provably inert, a first-class content-derived `trace_id` sealed in the audit chain, and a
  `triagedesk replay` that is structurally unable to re-commit.
- **Calibrated confidence & abstention** (Phase 8): a deterministic four-component coverage/deferral signal
  with the sixth owned tool `assess_confidence` and an `assess` node — low confidence can only escalate or
  ask for missing info, never commit, never downgrade a colour.
- **Retrieval grounding + borrowed-MCP depth** (Phase 9): a pure integer lexical scorer producing attributed
  closed-set passages under a contract where a colour is unrepresentable, a routing-neutral `ground` node,
  and the borrowed server's read paths genuinely reached behind an unchanged `Store` protocol with a
  fail-closed statement guard.
- **Desk UX + real approval gate** (Phase 10): a dependency-free local HTML surface that renders the
  suggested priority with adjacent citations, a loud typed-signal uncertainty banner, and a real
  approve/edit/dismiss gate — provably unable to commit, escape or egress.
- **Honest evaluation + rigour docs** (Phase 11) and **milestone-close documentation** (Phase 12): E-04 and
  E-07 fixed at their real root causes, the 16-case suite re-run over the real graph, `EVALS.md` regenerated
  as a pure projection with reconciled counts, a literal one-command README, a rehearsed live-review runbook
  whose headline beat is a demonstrated data-only extension, and an honest clinical-fit re-declaration.

### What Worked

- **Additive seams.** Every capability attached at a published seam (a new node, a new tool, a new contract,
  an adapter behind an existing protocol). The frozen v1.0 spine — the scorer's arithmetic, the citation
  helper, the `@audited` interceptor — was never edited, and the milestone's integration check confirmed
  every seam wired end-to-end.
- **Research that measured instead of assuming.** Phase 11's research ran the real model and overturned the
  brief's stated root cause for E-04 (it was a dropped `age_years`, not a discriminator failure) and for
  E-07 (a fixture note/golden-case inconsistency, not an extraction gap). The plan was written against the
  measurement, not the guess.
- **Owner decisions at the real forks.** The `no_match` override's absolute deferral, the E-07 fixture
  repair, the "publish as measured" eval regeneration, and the banner/gate split were each surfaced as an
  explicit decision with the evidence, rather than quietly chosen.
- **Honesty locks as code.** `EVALS.md` is only ever the generator's projection; the §4 row set is reconciled
  fail-closed; the digest seals the per-case facts the published numbers derive from; the residual misses and
  the declared failure stay visible.

### What Was Inefficient

- **Verification staleness.** Every phase that touched shared files moved the covered-file fingerprint of
  earlier phases, flipping their reports to `stale`. Phases 6–11 needed a batch re-verification before the
  audit. A fingerprint scoped to a phase's *own* deliverables (not every shared file it happened to touch)
  would have avoided ~6 redundant verifier runs.
- **Schema sensitivity at 1.5B.** Changing the extraction contract to fix one case reshuffled which other
  cases passed (E-08 → a deferral, E-11 → a miss). Each change was honest but the churn cost a re-review and
  an owner round-trip. A fixed extraction contract earlier would have concentrated the churn.
- **`commit_docs: false` friction.** GSD's commit helper skips `.planning/`, so every fixer committed with
  plain git and the milestone archive needed a manual commit. The convention is deliberate, but it made the
  bookkeeping noisier than it needed to be.

### Patterns Established

- **One helper per concern, enforced by guards:** one span writer, one tokeniser, one contiguous-sequence
  helper, one citation formatter, one colour producer, one pause/resume helper, one store resolver.
- **Structural safety over conventional safety:** read-only replay builds no graph; the retrieval contract
  has no colour field to fill; the surface has no commit path at all.
- **Runbook-drift guards:** every documented command is driven through the public CLI by a test, so docs
  cannot silently diverge from the shipped tool.
- **Disposition ledgers:** each phase's review findings get a per-finding `REVIEW-DISPOSITION.md` so a
  triaged finding is distinguishable from a forgotten one.
- **Flag, never claim:** human steps (the demo upload, the clinician review) are marked `human_needed` and
  recorded as deferred, never asserted as done.

### Key Lessons

1. **Measure the root cause before planning the fix.** Phase 11's live diagnosis changed both of its fixes
   from the brief's assumptions to the actual causes — a plan built on the stated cause would have failed.
2. **A safety property must be structural.** Every "cannot" in this milestone is enforced by construction
   (no field, no edge, no path) and then proven — not asserted in prose.
3. **Honesty beats green.** The published evaluation still shows a declared failure and two honest misses;
   the milestone is stronger for it than a tuned suite would have been.
4. **Surface the fork, don't absorb it.** The four owner decisions were the highest-leverage moments of the
   milestone; each one, if silently defaulted, would have produced a defensible-but-wrong artefact.
5. **Re-verify once, at the end.** Re-verifying a phase after every later phase's additive edit is waste;
   batch it against the final codebase.

### Cost Observations

- Model mix: single-model (DeepSeek V4.1 Flash) orchestrator with specialist subagents per role
  (researcher, pattern-mapper, planner, plan-checker, executor, code-reviewer, code-fixer, verifier,
  ui-researcher, ui-checker, ui-auditor, integration-checker, security-auditor).
- Sessions: one long autonomous run (discuss → plan → execute → review → verify per phase, then the
  lifecycle).
- Notable: the review-and-fix loops found real defects in every phase (a fabricated failed-commit audit
  record; a CSRF-reachable gate; a non-fail-closed SQL guard; a `trauma` checkbox that made the default
  path unreachable) — the loop paid for itself repeatedly.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Tests | Review findings fixed | Notable |
|-----------|--------|-------|-------|----------------------|---------|
| v1.0 MVP | 5 | 21 | 239 | — (pre-GSD review loop) | The safety spine, frozen at `v1.0-submission`. |
| v1.1 Score Uplift | 7 | 19 | 454 | 30+ across 7 phases (incl. 4 criticals) | Additive capabilities on a frozen spine; every "cannot" proven structurally; honesty locks in code. |

### Recurring Themes

- **Guards beat intentions.** The strongest outcomes came from turning each claim into a test that fails
  when the property breaks.
- **Shared-file coupling is the cost centre.** The allowlist's set-equality across four sites and the
  covered-file fingerprints both demanded coordinated, one-wave changes.
- **Human steps are a first-class state.** Recording them as deferred (with a resume command) kept the
  milestone honest and the automation complete.
