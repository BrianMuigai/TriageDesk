---
quick_id: 261115-uys
slug: interactive-terminal-triage
verified: "2026-11-15"
status: passed
score: "5/5 must-haves"
---

# Verification — interactive terminal triage

| Must-have | Evidence | Verdict |
| --- | --- | --- |
| The terminal drives one patient through the shipped graph, no browser and no fixture | `main()` → `desk.pipeline.submit_case` → durable gate; a real `--online --note` run reached the handover card and committed one row | PASS |
| A raw note is read by the ONE grounded composition and unstated values are dropped | `test_extract_note_is_the_one_grounded_composition` (a model-supplied `respiratory_rate` the note never states is nulled); `extract_grounded` is shared with `normalize_case` | PASS |
| No new decision path | The surface delegates to `submit_case` / `answer_clarification` / `decide` and `mcp.elicitation`; `test_no_self_commit_path_in_the_desk_package` passes | PASS |
| An answer is an observation, not an approval | `answer_clarification` resumes with `respond=lambda _payload: None`, so the gate stays paused; `test_the_clarification_form_declines_when_nothing_is_typed` pins the refusal | PASS |
| A blank approver cannot commit; a dismissal writes nothing | `test_a_blank_approver_never_commits`, `test_dismiss_writes_nothing` (both assert zero queue rows) | PASS |

## Measured checks

- `uv run pytest -q` → **967 passed**.
- `uv run ruff check src tests` → All checks passed.
- Real run: `uv run triagedesk triage --online --note "40 year old man, walking, alert. RR 24, HR 118, systolic BP 108, temperature 38.9, no trauma. Presenting with central chest pain."` → extracted age/AVPU/RR/HR/systolic/temperature/complaint, named the unstated fields, scored ORANGE with three citations, approved as a named clinician, queue position 7.

## Gaps

- Raw notes require `--online` (the model); offline they are refused with a named reason.
- The eval harness cannot answer an elicitation (no MCP client); the terminal can.
