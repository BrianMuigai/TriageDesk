# 24-03 — SUMMARY

**Status:** complete · **Commit:** `91e64c0`

- **`docs/AGENTIC.md`** — the reviewer-facing answer: what the system decides, what it structurally
  cannot decide, the measured delta (linked, not restated), the emergency bypass as the counterweight,
  and the limits (bounded action set, 1.5B proposals, elicitation needs a client, small sample, no
  clinician review).
- **`docs/DECISIONS.md`** — D31 (bounded autonomy over a frozen kernel), D32 (model proposes / guard
  disposes), D33 (server-side elicitation, four outcomes), D34 (deterministic emergency bypass), and the
  narrow revision of D1 from "the LLM never routes" to "the LLM never chooses the answer".
- **`STATUS.md`** — G7 closed for elicitation; dynamic planning, elicitation and the bypass move to ✅ with
  test evidence; the residual limits stay named.
- **`SECURITY.md`** — 9 shipped tools; T-11/T-12/T-13 shipped; the authoritative-artefact and
  answer-is-not-approval statements added.
- **`README.md` / `ARCHITECTURE.md`** — the shipped two-layer shape, 9 tools, and the AGENTIC link
  (ARCHITECTURE at 663 words / 93 lines, inside its guard).
- **Canonical diagram regenerated** from the shipped code (`architecture.mmd/pdf/svg`), including
  `emergency_check` and `finish_investigation`; the superseded v1.3 proposal assets are removed.
- DOC-06 statements: the committed queue row is authoritative (not the printed card), an answer is not an
  approval, approver identity is recorded not authenticated (G4), and structured observations are
  two-state with text-level negation (the four-state model is an outstanding limitation).
