# Requirements: TriageDesk

**Defined:** 2026-11-13 (milestone **v1.2 Coverage Recovery**)
**Core Value:** A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches the queue without her approval.

> Iron-clad engineering rule: **DRY + SOLID** (`docs/CONVENTIONS.md`). Every requirement below must be
> met without duplicating logic or violating the single-source-of-truth rule. The scorer, the citation
> helper and the audit interceptor are not edited; retrieval informs *coverage*, never a colour.

---

## v1.2 Requirements

### Coverage

- [x] **COV-01**: The matcher classifies every complaint deterministically into `matched`, `ambiguous`
      or `no_candidate` — using the closed discriminator set plus data-driven high-risk context terms,
      never a model probability. The classifier is pure, reproducible, and boundary-respecting.

- [x] **COV-02**: A `no_candidate` complaint with complete vitals is **delivered** on the TEWS band —
      the SATS answer when no discriminator applies — and the card states `vitals-only` in its provenance.
      A partially-recorded case still recovers; nothing is imputed.

- [x] **COV-03**: An `ambiguous` complaint yields a **bounded clarification** (at most three targeted
      questions naming the candidate discriminators) instead of a bare deferral: no colour, no gate, no
      commit. One answer round may follow; a second ambiguity defers. A clarification is never counted as
      a delivered colour.

- [x] **COV-04**: Domain context is data, not code: `data/text_terms.yaml` carries the stopwords, the
      conservative stem rules and the condition → discriminator context map; no term or threshold is
      inlined.

### Extraction completeness

- [x] **COV-05**: Every **stated** single vital (respiratory rate, heart rate, systolic BP, SpO2) is
      recovered deterministically when the model drops it, exactly as age/serial/temperature already are.
      A value the note does not state is still never imputed.

- [x] **COV-06**: E-11 (very-urgent trauma) is run repeatedly (≥9 runs) and no run terminates at
      `RECOVER` while the note states every scored vital; any remaining variance is reported, not hidden.

### Evaluation & safety

- [x] **COV-07**: The eval reports **delivered / clarified / deferred** separately, with a coverage rate
      and a deferral rate. The gate excludes an all-clarify case from `unexpected_failures` on the same
      terms as an all-deferral case, and still cannot mask a wrong colour.

- [x] **COV-08**: New synthetic cases cover (a) ambiguous complaints with chronic conditions, (b)
      contradictory vitals, (c) incomplete vitals, (d) noisy/duplicated vitals, and (e) a held-out set
      never used to author the retrieval rules.

- [x] **COV-09**: All four safety invariants (INV-1..INV-4) hold on every run; no under-triage is
      introduced; `EVALS.md` is regenerated only from `report.json` (`--check` exits 0).

### Documentation

- [x] **COV-10**: `EVALS.md`, `README.md`, `STATUS.md`, `docs/DESK.md` and `ARCHITECTURE.md` state the
      new coverage behaviour and its measured result honestly, including what still defers and why.
