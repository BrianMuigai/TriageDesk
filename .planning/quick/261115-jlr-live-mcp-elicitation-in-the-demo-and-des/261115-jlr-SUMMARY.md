---
phase: quick-261115-jlr
plan: 01
quick_id: 261115-jlr
subsystem: mcp-elicitation / demo / desk / cli
tags: [mcp, elicitation, demo, desk, durable, live-final]
status: complete
requires: [request_clarification tool (v1.3), langchain.mcp MCPAdapter (World A)]
provides:
  - "mcp.adapter.with_live_clarification — the one opt-in seam (adapter-loaded request_clarification, in process)"
  - "mcp.elicitation.resume_with_answers — the one answers->resume rule (demo + CLI)"
  - "online `clarify` demo beat on E-09 with [elicit]/[nurse] lines and `demo --answer`"
  - "durable.resume_thread(wrap_tools=...) — injected tool-map decorator"
  - "online desk question panel reached; /clarify resumes to the gate"
affects: [demo/run.py, desk/pipeline.py, cli.py, durable.py, docs/DEMO.md, docs/DESK.md, docs/MCP.md, STATUS.md, README.md]
tech-stack:
  added: []
  patterns: ["opt-in tool-map decorator injected per surface (SOLID D/I)", "beta warning silenced at its single import source"]
key-files:
  created:
    - tests/test_live_clarification.py
  modified:
    - src/triagedesk/mcp/adapter.py
    - src/triagedesk/mcp/elicitation.py
    - src/triagedesk/demo/run.py
    - demo/storyboard.yaml
    - src/triagedesk/cli.py
    - src/triagedesk/durable.py
    - src/triagedesk/desk/pipeline.py
    - tests/test_demo.py
    - tests/test_desk.py
    - docs/DEMO.md
    - docs/DESK.md
    - docs/MCP.md
    - STATUS.md
    - README.md
decisions:
  - "Live elicitation is opt-in per surface via with_live_clarification; the eval harness never uses it and keeps recording `unavailable`"
  - "An answer-only `triagedesk resume --answer` that reveals the approval gate stops there (paused again) instead of demanding --decision; --decision is still required when the approval is the pending payload"
  - "The demo reads the outcome from the APPROVAL payload it answered, never the run's first payload (which may be the question)"
metrics:
  duration: "~24 min (14:29 -> 14:53 +03:00)"
  completed: 2026-11-15
  tests_before: 904
  tests_after: 923
actuals:
  tokens: 11868
  tasks: 3
  commits: 3
plan_head_before: 202840353828abfa726760377c1cfdced241b0f6
plan_head_after: 5b61432f5e4300204da369ab8c617a468ffe6e30
---

# Quick 261115-jlr: Live MCP elicitation in the demo and the desk — Summary

**What shipped:** an opt-in seam (`with_live_clarification`) loads the real owned `request_clarification` tool through the shipped `langchain.mcp` adapter in process. Three surfaces now pause on a genuine `mcp_elicitation` interrupt and act on the nurse's answer: the online `demo --beat clarify`, the online desk question panel, and `triagedesk resume --answer`. The deterministic matcher re-reads the answer and the result is gated by the named approval. A real `qwen2.5:1.5b` run asked on the first attempt, re-matched `hypoglycaemia`, scored RED and committed under the demo nurse.

## Tasks

| # | Task | Commit | Key files |
|---|------|--------|-----------|
| 1 (tracer) | Opt-in seam + online `clarify` demo beat | 53f8f52 | mcp/adapter.py, mcp/elicitation.py, demo/run.py, demo/storyboard.yaml, tests/test_live_clarification.py, tests/test_demo.py, docs/DEMO.md |
| 2 | CLI `--answer`, desk online + /clarify, resume reaches the real tool | a4ab2fb | durable.py, desk/pipeline.py, cli.py, tests/test_live_clarification.py, tests/test_desk.py |
| 3 | Live verification + honest docs | 5b61432 | docs/DEMO.md, docs/DESK.md, docs/MCP.md, STATUS.md, README.md |

The Task 1 tracer gate ran in interactive `end-of-phase` mode with automated-only `<verify>`. The verify was re-run and passed (90 targeted tests, ruff, every grep gate, and the bare offline demo with `< /dev/null` printing 6 `BEAT` lines). No checkpoint was needed.

## Verification

- `uv run pytest -q` → **923 passed** (baseline was 904; this plan added 19 tests in `tests/test_live_clarification.py`).
- `uv run ruff check` → clean.
- mypy on the touched files: `adapter.py` and `demo/run.py` still have the 2 pre-existing errors (`dict` type-arg on `borrowed_server_config`, untyped `yaml`). `durable.py`, `desk/pipeline.py` and `cli.py` have 0 errors.
- `uv run python scripts/emit_evals.py --check` → `EVALS.md is up to date (report 0ae3dde6ca3f3615)`. `git diff -- evals/results/` is empty.
- `MCPAdapter` is imported only in `src/triagedesk/mcp/adapter.py`. `src/triagedesk/evals/` never references the seam. `durable.py` imports no `triagedesk.mcp` module. No `low glucose` text appears under `src/`.
- `uv run python -c "from triagedesk.mcp import adapter"` prints no `LangChainBetaWarning`. Before this plan it printed one.
- No `spans.jsonl` is left at the repo root, and no `docs/assets/*` file was staged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `triagedesk resume --answer` raised at the gate it revealed**
- **Found during:** Task 2 (CLI resume over a real checkpoint).
- **Issue:** `_resume_policy` raised `DurableError("--decision is required…")` when an answer-only resume moved the run on to the approval gate. That contradicted `main`'s own "paused again at the approval gate; nothing has been committed" branch, which was meant for exactly this case. Before this plan nothing could reach the bug, because no surface paused at a real question.
- **Fix:** the policy now remembers whether this resume answered a question. If it did and no `--decision` was given, it returns `None` at the approval, so the gate stays paused for a named decision. When the approval is the pending payload, a missing `--decision` still names the flag. All existing `tests/test_durable_cli.py` tests pass unchanged.
- **Files modified:** src/triagedesk/cli.py
- **Commit:** a4ab2fb

**2. [Rule 1 - Bug, test] The desk-online test stub hit the wrong patch site**
- **Found during:** Task 2.
- **Issue:** The plan said `_online_extraction` calls `desk.extraction.extract_complaint` through the module. In fact `desk/server.py` imports `extract_complaint` by name. Stubbing `extraction_module.extract_complaint` therefore did nothing: the first desk test silently reached the live Ollama, and the second, depending on order, fell back to the offline path. That made the tests flaky and non-hermetic.
- **Fix:** the test now stubs `extraction_module.extract_async`, the same patch site `tests/test_desk_online.py` uses, and the real closed-set filter still runs over it. The module went from ~25 s to ~7 s and is hermetic.
- **Files modified:** tests/test_live_clarification.py
- **Commit:** a4ab2fb

**3. [Rule 1 - Bug, test] A server tool was called after `run_demo` had restored the store seam**
- **Found during:** Task 1.
- **Issue:** `store_seam` always resets to the borrowed default on exit. Calling `server_module.match_discriminators` after `run_demo` made the audit interceptor resolve the borrowed `npx` store, which failed with `fileno` under capsys.
- **Fix:** the test reads the matcher before the run.
- **Commit:** 53f8f52

**4. [CLAUDE.md DRY] DEMO.md does not restate the alias list**
- The plan's grounded facts listed four aliases. Copying them into the docs would duplicate `data/sats_discriminators.yaml`, so the caveat cites the YAML and gives one example ("low glucose").

### Notes on plan expectations vs live reality
- **Post-answer routing online:** the live model chose `gather_evidence` and then `finish_investigation` after the answer. With the stubbed model in the tests, the guard instead overrode a second `ask_question` to finish. Both routes end at RED → approval → commit, and the docs excerpt elides those lines.
- **Run-to-run variation:** across the two live `--answer` runs the chosen actions and every non-model value were identical, but the model's free-text `rationale` / `signals` differed (see the diff below). DEMO.md says this explicitly rather than claiming byte-identical runs.

## Live runs (verbatim — Ollama `qwen2.5:1.5b`, 2026-11-15)

The model proposed `ask_question` on the **first attempt**, so no retries were needed. All live runs are recorded below. `spans.jsonl` was removed after each one.

### Attempt 1 — `uv run triagedesk demo --online --beat clarify --answer "low glucose, 2.1 mmol/L"` (rc=0)

```
mode: online — local model qwen2.5:1.5b via Ollama
========================================================================
BEAT 1/1: clarify — Online: the agent asks the nurse mid-call and acts on the answer
case: E-09 (Vague complaint)
========================================================================
[tool] normalize_case {"raw_note": "60 year old man, known diabetic, walking, alert, no trauma. RR 14, HR 80, systolic BP 120, temperature 36.8. Complaint: feeling unwell."} -> {"case": {"age_ambiguous": false, "age_months": null, "age_years": 60, "avpu": "alert", "complaint": "feeling unwell", "diastolic_bp": null, "heart_rate": 80, "height_cm": null, "mobility": "walking", "respiratory_rate": 14, "spo2": null, "systolic_bp": 120, "temperature_c": 36.8, "trauma": false}, "matched_discriminator_ids": [], "no_discriminator_matched": true}
[tool] match_discriminators {"complaint": "feeling unwell", "note": "60 year old man, known diabetic, walking, alert, no trauma. RR 14, HR 80, systolic BP 120, temperature 36.8. Complaint: feeling unwell."} -> {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "matched_ids": [], "no_match": true, "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "warning": "no discriminator matched \u2014 coverage gap (E-09); do not infer a colour from the complaint"}
[tool] plan_next_step {"investigation": {"budget_left": 3, "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "complaint": "feeling unwell", "has_evidence": false, "history": [], "missing_vitals": [], "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "step": 0}} -> {"action": "ask_question", "budget_left": 2, "overridden": false, "override_reason": null, "proposed_action": "ask_question", "rationale": "The current state indicates that the complaint is feeling unwell, but there are no specific symptoms or evidence to focus on. Asking a clarifying question about checking capillary glucose and ketones will help gather more relevant information.", "signals": ["check_glucose", "check_ketones"], "step": 1}
[elicit] request_clarification: One detail would resolve this triage case. Answer what you can — a blank field is an unanswered question, not a finding.
[elicit] request_clarification asks q1: Ask about: Hypoglycaemia — glucose < 3 mmol/L
[elicit] request_clarification asks q2: Ask about: Diabetic glucose > 11 with ketonuria
[elicit] request_clarification asks q3: Ask about: Diabetic glucose > 17 without ketonuria
[nurse] q1: low glucose, 2.1 mmol/L
[nurse] q2: (no answer)
[nurse] q3: (no answer)
[tool] request_clarification {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"]} -> [{"id": "lc_63c51a44-ddc5-4a49-b48f-ea0c3d23bb85", "text": "{\n  \"outcome\": \"accepted\",\n  \"answers\": [\n    \"low glucose, 2.1 mmol/L\"\n  ],\n  \"reason\": null\n}", "type": "text"}]
[tool] match_discriminators {"complaint": "feeling unwell low glucose, 2.1 mmol/L", "note": "60 year old man, known diabetic, walking, alert, no trauma. RR 14, HR 80, systolic BP 120, temperature 36.8. Complaint: feeling unwell."} -> {"candidates": ["hypoglycaemia"], "matched_ids": ["hypoglycaemia"], "no_match": false, "questions": [], "retrieval_status": "matched", "warning": null}
[tool] plan_next_step {"investigation": {"budget_left": 2, "candidates": ["hypoglycaemia"], "clarification_round": 1, "complaint": "feeling unwell", "has_evidence": false, "history": ["ask_question"], "missing_vitals": [], "questions": [], "retrieval_status": "matched", "step": 1}} -> {"action": "gather_evidence", "budget_left": 1, "overridden": false, "override_reason": null, "proposed_action": "gather_evidence", "rationale": "Retrieve attributed knowledge-base excerpts for the complaint to gather more information.", "signals": ["feeling unwell", "hypoglycaemia"], "step": 2}
[tool] retrieve_evidence {"complaint": "feeling unwell"} -> {"no_match": true, "passages": [], "reason": "no discriminator matched \u2014 coverage gap (E-09); do not infer a colour from the complaint"}
[tool] plan_next_step {"investigation": {"budget_left": 1, "candidates": ["hypoglycaemia"], "clarification_round": 1, "complaint": "feeling unwell", "has_evidence": true, "history": ["ask_question", "gather_evidence"], "missing_vitals": [], "questions": [], "retrieval_status": "matched", "step": 2}} -> {"action": "finish_investigation", "budget_left": 0, "overridden": false, "override_reason": null, "proposed_action": null, "rationale": "finish_investigation is the default: the case proceeds to the deterministic kernel unchanged", "signals": [], "step": 3}
[tool] score_priority {"case": {"age_ambiguous": false, "age_months": null, "age_years": 60, "avpu": "alert", "complaint": "feeling unwell", "diastolic_bp": null, "heart_rate": 80, "height_cm": null, "mobility": "walking", "respiratory_rate": 14, "spo2": null, "systolic_bp": 120, "temperature_c": 36.8, "trauma": false}, "matched_discriminator_ids": ["hypoglycaemia"]} -> {"abstained": false, "citations": ["SATS Training Manual 2012 (EMSSA), adult clinical discriminators \u2014 SATS Table: Emergency discriminators"], "colour": "RED", "destination": "Resuscitation room", "matched_discriminator_ids": ["hypoglycaemia"], "missing_vitals": [], "out_of_scope": false, "reason": null, "target": "Immediate", "tews": 0, "triggered_rules": [{"citation": "SATS Training Manual 2012 (EMSSA), adult clinical discriminators \u2014 SATS Table: Emergency discriminators", "detail": "discriminator override: emergency -> RED", "points": 0, "rule_id": "emergency"}], "used_vitals": ["mobility", "respiratory_rate", "heart_rate", "systolic_bp", "temperature", "avpu", "trauma"]}
[tool] assess_confidence {"candidates": ["hypoglycaemia"], "clarification_round": 1, "matched_ids": ["hypoglycaemia"], "no_match": false, "priority": {"abstained": false, "citations": ["SATS Training Manual 2012 (EMSSA), adult clinical discriminators \u2014 SATS Table: Emergency discriminators"], "colour": "RED", "destination": "Resuscitation room", "matched_discriminator_ids": ["hypoglycaemia"], "missing_vitals": [], "out_of_scope": false, "reason": null, "target": "Immediate", "tews": 0, "triggered_rules": [{"citation": "SATS Training Manual 2012 (EMSSA), adult clinical discriminators \u2014 SATS Table: Emergency discriminators", "detail": "discriminator override: emergency -> RED", "points": 0, "rule_id": "emergency"}], "used_vitals": ["mobility", "respiratory_rate", "heart_rate", "systolic_bp", "temperature", "avpu", "trauma"]}, "questions": [], "retrieval_status": "matched"} -> {"action": "deliver", "candidates": [], "components": [{"detail": "7 of 7 scored vitals recorded", "name": "vitals_coverage", "satisfied": true}, {"detail": "1 of 41 discriminators matched", "name": "discriminator_coverage", "satisfied": true}, {"detail": "a discriminator override raised the priority", "name": "override_path", "satisfied": true}, {"detail": "tews distance 0 from the band edge", "name": "tews_band_distance", "satisfied": false}], "deferral": false, "level": "high", "questions": [], "reason": ""}
[tool] commit_priority {"approval_token": {"approved_at": "2026-11-15T11:48:00.413446+00:00", "approved_by": "Nurse Demo", "decision": "approve", "final_colour": "RED", "role": "triage nurse"}, "case": {"age_ambiguous": false, "age_months": null, "age_years": 60, "avpu": "alert", "complaint": "feeling unwell", "diastolic_bp": null, "heart_rate": 80, "height_cm": null, "mobility": "walking", "respiratory_rate": 14, "spo2": null, "systolic_bp": 120, "temperature_c": 36.8, "trauma": false}, "case_id": "52a30522f6fe4a61", "colour": "RED"} -> {"colour": "RED", "committed": true, "position": 1, "reason": "committed case 52a30522f6fe4a61 at queue position 1 (RED)", "refused": false, "target": "Immediate"}
--- outcome ---
  colour       : RED
  target       : Immediate
  matched ids  : ['hypoglycaemia']
  answers      : ['low glucose, 2.1 mmol/L']
  elicitation  : accepted
  citation     : SATS Training Manual 2012 (EMSSA), adult clinical discriminators — SATS Table: Emergency discriminators
  commit       : committed case 52a30522f6fe4a61 at queue position 1 (RED)
  handover card: {"case_id":"52a30522f6fe4a61","colour":"RED","target":"Immediate","citations":["SATS Training Manual 2012 (EMSSA), adult clinical discriminators — SATS Table: Emergency discriminators"],"triggered_rules":[{"rule_id":"emergency","detail":"discriminator override: emergency -> RED","points":0,"citation":"SATS Training Manual 2012 (EMSSA), adult clinical discriminators — SATS Table: Emergency discriminators"}],"missing_vitals":[],"matched_discriminator_ids":["hypoglycaemia"],"no_discriminator_matched":false,"second_look":null,"decision":"approve","approved_by":"Nurse Demo","role":"triage nurse"}
  DECLARED     : ORANGE (the eval expectation for the note alone — not compared: this run added a nurse answer)
```

### Non-interactive decline — `uv run triagedesk demo --online --beat clarify < /dev/null` (rc=0)

```
mode: online — local model qwen2.5:1.5b via Ollama
========================================================================
BEAT 1/1: clarify — Online: the agent asks the nurse mid-call and acts on the answer
case: E-09 (Vague complaint)
========================================================================
[tool] normalize_case {"raw_note": "60 year old man, known diabetic, walking, alert, no trauma. RR 14, HR 80, systolic BP 120, temperature 36.8. Complaint: feeling unwell."} -> {"case": {"age_ambiguous": false, "age_months": null, "age_years": 60, "avpu": "alert", "complaint": "feeling unwell", "diastolic_bp": null, "heart_rate": 80, "height_cm": null, "mobility": "walking", "respiratory_rate": 14, "spo2": null, "systolic_bp": 120, "temperature_c": 36.8, "trauma": false}, "matched_discriminator_ids": [], "no_discriminator_matched": true}
[tool] match_discriminators {"complaint": "feeling unwell", "note": "60 year old man, known diabetic, walking, alert, no trauma. RR 14, HR 80, systolic BP 120, temperature 36.8. Complaint: feeling unwell."} -> {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "matched_ids": [], "no_match": true, "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "warning": "no discriminator matched \u2014 coverage gap (E-09); do not infer a colour from the complaint"}
[tool] plan_next_step {"investigation": {"budget_left": 3, "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "complaint": "feeling unwell", "has_evidence": false, "history": [], "missing_vitals": [], "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "step": 0}} -> {"action": "ask_question", "budget_left": 2, "overridden": false, "override_reason": null, "proposed_action": "ask_question", "rationale": "The current state indicates that the complaint is feeling unwell, and there are no candidates or missing vital signs. The nurse should ask a clarifying question to gather more information.", "signals": ["feeling_unwell", "complaint"], "step": 1}
[elicit] request_clarification: One detail would resolve this triage case. Answer what you can — a blank field is an unanswered question, not a finding.
[elicit] request_clarification asks q1: Ask about: Hypoglycaemia — glucose < 3 mmol/L
[elicit] request_clarification asks q2: Ask about: Diabetic glucose > 11 with ketonuria
[elicit] request_clarification asks q3: Ask about: Diabetic glucose > 17 without ketonuria
[nurse] declined — no answer given; nothing is recorded
[tool] request_clarification {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"]} -> [{"id": "lc_026aae73-cf31-483e-9fa0-d2248d3c110c", "text": "{\n  \"outcome\": \"declined\",\n  \"answers\": [],\n  \"reason\": null\n}", "type": "text"}]
[tool] match_discriminators {"complaint": "feeling unwell", "note": "60 year old man, known diabetic, walking, alert, no trauma. RR 14, HR 80, systolic BP 120, temperature 36.8. Complaint: feeling unwell."} -> {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "matched_ids": [], "no_match": true, "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "warning": "no discriminator matched \u2014 coverage gap (E-09); do not infer a colour from the complaint"}
[tool] plan_next_step {"investigation": {"budget_left": 2, "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "complaint": "feeling unwell", "has_evidence": false, "history": ["ask_question"], "missing_vitals": [], "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "step": 1}} -> {"action": "gather_evidence", "budget_left": 1, "overridden": false, "override_reason": null, "proposed_action": "gather_evidence", "rationale": "Retrieve attributed knowledge-base excerpts for the complaint to gather more specific information.", "signals": [], "step": 2}
[tool] retrieve_evidence {"complaint": "feeling unwell"} -> {"no_match": true, "passages": [], "reason": "no discriminator matched \u2014 coverage gap (E-09); do not infer a colour from the complaint"}
[tool] plan_next_step {"investigation": {"budget_left": 1, "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "complaint": "feeling unwell", "has_evidence": true, "history": ["ask_question", "gather_evidence"], "missing_vitals": [], "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "step": 2}} -> {"action": "finish_investigation", "budget_left": 0, "overridden": false, "override_reason": null, "proposed_action": null, "rationale": "finish_investigation is the default: the case proceeds to the deterministic kernel unchanged", "signals": [], "step": 3}
[tool] score_priority {"case": {"age_ambiguous": false, "age_months": null, "age_years": 60, "avpu": "alert", "complaint": "feeling unwell", "diastolic_bp": null, "heart_rate": 80, "height_cm": null, "mobility": "walking", "respiratory_rate": 14, "spo2": null, "systolic_bp": 120, "temperature_c": 36.8, "trauma": false}, "matched_discriminator_ids": []} -> {"abstained": false, "citations": ["SATS Training Manual 2012 (EMSSA), adult TEWS \u2014 all recorded parameters within normal SATS bands"], "colour": "GREEN", "destination": "Designated area", "matched_discriminator_ids": [], "missing_vitals": [], "out_of_scope": false, "reason": null, "target": "< 4 hours", "tews": 0, "triggered_rules": [{"citation": "SATS Training Manual 2012 (EMSSA), adult TEWS \u2014 all recorded parameters within normal SATS bands", "detail": "mobility, respiratory_rate, heart_rate, systolic_bp, temperature, avpu, trauma within normal SATS bands", "points": 0, "rule_id": "tews_baseline"}], "used_vitals": ["mobility", "respiratory_rate", "heart_rate", "systolic_bp", "temperature", "avpu", "trauma"]}
[tool] assess_confidence {"candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "matched_ids": [], "no_match": true, "priority": {"abstained": false, "citations": ["SATS Training Manual 2012 (EMSSA), adult TEWS \u2014 all recorded parameters within normal SATS bands"], "colour": "GREEN", "destination": "Designated area", "matched_discriminator_ids": [], "missing_vitals": [], "out_of_scope": false, "reason": null, "target": "< 4 hours", "tews": 0, "triggered_rules": [{"citation": "SATS Training Manual 2012 (EMSSA), adult TEWS \u2014 all recorded parameters within normal SATS bands", "detail": "mobility, respiratory_rate, heart_rate, systolic_bp, temperature, avpu, trauma within normal SATS bands", "points": 0, "rule_id": "tews_baseline"}], "used_vitals": ["mobility", "respiratory_rate", "heart_rate", "systolic_bp", "temperature", "avpu", "trauma"]}, "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous"} -> {"action": "clarify", "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "components": [{"detail": "7 of 7 scored vitals recorded", "name": "vitals_coverage", "satisfied": true}, {"detail": "0 of 41 discriminators matched", "name": "discriminator_coverage", "satisfied": false}, {"detail": "no discriminator override fired", "name": "override_path", "satisfied": false}, {"detail": "tews distance 0 from the band edge", "name": "tews_band_distance", "satisfied": false}], "deferral": false, "level": "low", "questions": ["Check: capillary glucose (mmol/L) and ketones"], "reason": "the complaint is near a discriminator family but names none"}
--- outcome ---
  colour       : GREEN
  target       : < 4 hours
  matched ids  : []
  elicitation  : declined
  citation     : SATS Training Manual 2012 (EMSSA), adult TEWS — all recorded parameters within normal SATS bands
  DECLARED     : ORANGE
  MEASURED     : GREEN (SHOWN MISMATCH)
```

### Run 2 — the plan's Task 3 `<verify>` live command (verify rc=0)

This run was identical to attempt 1 except for the per-call adapter content ids (`lc_…`) and the approval timestamp. The only other differences were in the model's free text on two `plan_next_step` lines:

```
8c8
< [tool] plan_next_step {"investigation": {"budget_left": 3, "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "complaint": "feeling unwell", "has_evidence": false, "history": [], "missing_vitals": [], "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "step": 0}} -> {"action": "ask_question", "budget_left": 2, "overridden": false, "override_reason": null, "proposed_action": "ask_question", "rationale": "The current state indicates that the complaint is feeling unwell, but there are no specific symptoms or evidence to focus on. Asking a clarifying question about checking capillary glucose and ketones will help gather more relevant information.", "signals": ["check_glucose", "check_ketones"], "step": 1}
---
> [tool] plan_next_step {"investigation": {"budget_left": 3, "candidates": ["hypoglycaemia", "diabetic_hyperglycaemia_ketonuria", "diabetic_hyperglycaemia_no_ketonuria"], "clarification_round": 0, "complaint": "feeling unwell", "has_evidence": false, "history": [], "missing_vitals": [], "questions": ["Check: capillary glucose (mmol/L) and ketones"], "retrieval_status": "ambiguous", "step": 0}} -> {"action": "ask_question", "budget_left": 2, "overridden": false, "override_reason": null, "proposed_action": "ask_question", "rationale": "The current state indicates that the complaint is feeling unwell, and there are no candidates or missing vital signs. The nurse should ask a clarifying question to gather more information.", "signals": ["feeling_unwell", "complaint"], "step": 1}
18c18
< [tool] plan_next_step {"investigation": {"budget_left": 2, "candidates": ["hypoglycaemia"], "clarification_round": 1, "complaint": "feeling unwell", "has_evidence": false, "history": ["ask_question"], "missing_vitals": [], "questions": [], "retrieval_status": "matched", "step": 1}} -> {"action": "gather_evidence", "budget_left": 1, "overridden": false, "override_reason": null, "proposed_action": "gather_evidence", "rationale": "Retrieve attributed knowledge-base excerpts for the complaint to gather more information.", "signals": ["feeling unwell", "hypoglycaemia"], "step": 2}
---
> [tool] plan_next_step {"investigation": {"budget_left": 2, "candidates": ["hypoglycaemia"], "clarification_round": 1, "complaint": "feeling unwell", "has_evidence": false, "history": ["ask_question"], "missing_vitals": [], "questions": [], "retrieval_status": "matched", "step": 1}} -> {"action": "gather_evidence", "budget_left": 1, "overridden": false, "override_reason": null, "proposed_action": "gather_evidence", "rationale": "The complaint indicates a feeling of unwell, which could be related to hypoglycaemia. Retrieving evidence will help confirm or rule out this possibility.", "signals": ["feeling_unwell", "hypoglycaemia"], "step": 2}
```

## Human check (not run by the executor)
Two checks need a real terminal and browser:
- `uv run triagedesk demo --online --beat clarify`, then type an answer naming the finding at the `[nurse] q1>` prompt.
- `uv run triagedesk desk --online`, then submit the E-09 vitals with the complaint `known diabetic, feeling unwell`, answer the panel and confirm the gate appears.

The offline HTTP tests prove the same flow with the model stubbed. Run `rm -f spans.jsonl` afterwards.

## Threat Flags
None. There is no new network endpoint: `/clarify` already existed, and the in-process adapter session uses the in-memory transport. Every threat-register mitigation (T-jlr-01..07) is covered by a test in `tests/test_live_clarification.py` or by a grep gate.

## Known Stubs
None.

## Self-Check: PASSED

All created/modified key files exist; commits 53f8f52, a4ab2fb, 5b61432 are ancestors of HEAD; `git rev-list --count 2028403..HEAD` = 3.
