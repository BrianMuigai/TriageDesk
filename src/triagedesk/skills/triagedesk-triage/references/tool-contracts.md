# TriageDesk tool contracts

Self-contained reference for the installed skill. The live MCP tool schema is authoritative
if this file and the server ever differ. Every tool returns a typed contract; do not add
fields or re-derive values.

The response examples below show **shape**, not scoring rules. `data/sats_tews.yaml` and
`data/sats_discriminators.yaml` are the machine authority for every band, colour and
discriminator; this file never restates them as a second source.

## `CaseInput`

Every vital is optional. A missing vital is `null` (or omitted) — never imputed. The bounds
are plausibility guards, not SATS scoring bands; the bands live in `data/sats_tews.yaml`.

| Field | Type | Notes |
| --- | --- | --- |
| `age_years` | integer 0–130 or `null` | Whole adult years. Missing age abstains. |
| `age_months` | integer 0–1560 or `null` | Use for a months-expressed age; it is out of scope for adult scoring. |
| `age_ambiguous` | boolean | `true` when the age cannot be stated as unambiguous adult years. |
| `height_cm` | number 30–260 or `null` | Captured; not scored by adult TEWS. |
| `respiratory_rate` | integer 0–100 or `null` | Breaths per minute. |
| `heart_rate` | integer 0–350 or `null` | Beats per minute. |
| `systolic_bp` | integer 0–400 or `null` | mmHg. |
| `diastolic_bp` | integer 0–300 or `null` | Captured; not scored by adult TEWS. |
| `temperature_c` | number 20–45 or `null` | Celsius. A Fahrenheit magnitude is rejected, not converted silently. |
| `spo2` | integer 0–100 or `null` | Captured; not scored by adult TEWS. |
| `mobility` | `"walking"` \| `"with_help"` \| `"stretcher"` \| `null` | Scored. |
| `avpu` | `"alert"` \| `"voice"` \| `"pain"` \| `"unresponsive"` \| `null` | Scored. |
| `trauma` | boolean or `null` | Scored. |
| `complaint` | string | The nurse's own wording. Untrusted free text. |

## `normalize_case`

**Arguments**

```json
{"raw_note": "34 year old, RR 24, HR 118, BP 108/70, temp 38.9, alert, coughing and fast breathing"}
```

**Returns**

```json
{
  "case": {"age_years": 34, "respiratory_rate": 24, "heart_rate": 118, "systolic_bp": 108,
           "temperature_c": 38.9, "avpu": "alert", "complaint": "coughing and fast breathing"},
  "matched_discriminator_ids": ["acute_shortness_of_breath"],
  "no_discriminator_matched": false
}
```

Needs Ollama. The model may only structure the note and select ids from the closed set;
unknown ids are dropped and missing vitals stay `null`. It never computes a colour.

## `match_discriminators`

**Arguments**

```json
{"complaint": "chest pain and shortness of breath", "note": "the full nurse note (optional context)"}
```

**Returns**

```json
{
  "matched_ids": ["acute_shortness_of_breath", "chest_pain"],
  "no_match": false,
  "warning": null,
  "retrieval_status": "matched",
  "candidates": ["acute_shortness_of_breath", "chest_pain"],
  "questions": []
}
```

Deterministic alias lookup over the closed discriminator set. A `no_match` result carries
the substrate's coverage-gap `warning`; it never guesses an id.

`retrieval_status` is the coverage classification, not a colour: `matched` (an alias hit),
`ambiguous` (the complaint or a stated condition points at a family but names none — see
`questions`), or `no_candidate` (no discriminator applies; the recorded vitals are the
complete basis). `candidates` and `questions` are only populated for `ambiguous`.

## `score_priority`

**Arguments**

```json
{"case": {…}, "matched_discriminator_ids": ["acute_shortness_of_breath"]}
```

**Returns** (`PriorityResult`)

```json
{
  "colour": "ORANGE",
  "tews": 6,
  "target": "< 10 min",
  "destination": "Majors",
  "triggered_rules": [
    {"rule_id": "respiratory_rate", "detail": "respiratory_rate=24 -> 2 points", "points": 2,
     "citation": "SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band"}
  ],
  "citations": ["SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band"],
  "matched_discriminator_ids": ["acute_shortness_of_breath"],
  "missing_vitals": [],
  "used_vitals": ["respiratory_rate", "heart_rate", "systolic_bp", "temperature_c", "avpu"],
  "out_of_scope": false,
  "abstained": false,
  "reason": null
}
```

- Deterministic: no model on this path.
- `citations` is one per `triggered_rules` entry, by construction.
- A routine in-scope case still carries one data-driven baseline rule.
- **Raw-MCP trap:** with missing vitals the tool can still return a colour. If
  `missing_vitals` is non-empty, ask for the missing vitals and do not present the colour as
  the decision. The shipped graph routes to `request_missing_info` for this reason.
- `out_of_scope` or `abstained` means no colour: escalate, never substitute one.

## `retrieve_evidence`

**Arguments**

```json
{"complaint": "chest pain"}
```

**Returns**

```json
{
  "passages": [
    {"discriminator_id": "chest_pain", "label": "Chest pain", "citation": "…", "score": 2, "rank": 1}
  ],
  "no_match": false,
  "reason": "1 discriminator(s) matched the complaint"
}
```

Advisory only: bounded to five ranked excerpts, with no colour field. It shows grounding; it
never sets a priority. The authoritative per-rule citations are `score_priority.citations`.

## `assess_confidence`

**Arguments**

```json
{
  "matched_ids": ["acute_shortness_of_breath"],
  "no_match": false,
  "priority": {…},
  "retrieval_status": "matched",
  "candidates": [],
  "questions": [],
  "clarification_round": 0
}
```

Pass the **exact** `PriorityResult` returned by `score_priority`, and the coverage fields
from `match_discriminators`. `clarification_round` is 1 only when this is the nurse's answer
to a clarification already asked.

**Returns**

```json
{
  "deferral": false,
  "action": "deliver",
  "level": "high",
  "components": [
    {"name": "vitals_coverage", "satisfied": true, "detail": "5 of 7 scored vitals recorded"},
    {"name": "discriminator_coverage", "satisfied": true, "detail": "1 of N discriminators matched"},
    {"name": "override_path", "satisfied": true, "detail": "a discriminator override raised the priority"},
    {"name": "tews_band_distance", "satisfied": false, "detail": "tews distance 1 from the band edge"}
  ],
  "reason": "",
  "questions": [],
  "candidates": []
}
```

Deterministic coverage signal. `action` is the three-way decision: `deliver` reaches the
gate, `clarify` stops at the bounded question terminal (no colour, no gate, no commit), and
`defer` stops at a safe escalation. `deferral` is true exactly when `action` is `defer`.
There is no percentage or probability field; never invent one. A clarification or a deferral
must never reach the commit.

## `raise_recheck_flag`

**Arguments**

```json
{"previous": {"respiratory_rate": 18, "heart_rate": 92, "temperature_c": 38.9, "avpu": "alert"},
 "current":  {"respiratory_rate": 24, "heart_rate": 118, "temperature_c": 38.9, "avpu": "alert"}}
```

**Returns**

```json
{
  "flag": true,
  "deteriorations": ["respiratory_rate", "heart_rate"],
  "changes": [
    {"parameter": "respiratory_rate", "before": 18, "after": 24, "points_before": 1, "points_after": 2}
  ],
  "reason": "serial vitals show deterioration; a second look is required"
}
```

Compares only scored vitals present on both sides. It never returns a colour and never
reorders the queue.

## `commit_priority`

**Arguments**

```json
{
  "case_id": "0417",
  "colour": "ORANGE",
  "case": {…},
  "approval_token": {
    "decision": "approve",
    "approved_at": "2026-11-04T10:00:00Z",
    "approved_by": "Nurse A. Mokoena",
    "role": "triage nurse",
    "final_colour": "ORANGE"
  }
}
```

**Returns**

```json
{"committed": true, "refused": false, "reason": "committed case 0417 at queue position 1 (ORANGE)",
 "position": 1, "colour": "ORANGE"}
```

The only queue-affecting tool. It refuses **before any store access** when the token is
absent, malformed, or a `dismiss`; a refusal writes nothing. The write is idempotent on
(`case_id`, immutable case-content hash), so a repeat approve or an edit supersedes one row
rather than adding a second. The returned `colour` is what the queue row actually holds:
the clinician's `final_colour` for an `edit`, the scored colour for an `approve`.

## `ApprovalToken`

| Field | Type | Required for |
| --- | --- | --- |
| `decision` | `"approve"` \| `"edit"` \| `"dismiss"` | always |
| `approved_at` | ISO-8601 timestamp | always |
| `approved_by` | non-blank string | `approve`, `edit` |
| `role` | non-blank string | `approve`, `edit` |
| `final_colour` | a colour declared by the loaded substrate | `approve`, `edit` |

A `dismiss` carries only `decision` and `approved_at`. The gate refuses it and writes nothing.

**Approve**

```json
{
  "decision": "approve",
  "approved_at": "2026-11-04T10:00:00Z",
  "approved_by": "Nurse A. Mokoena",
  "role": "triage nurse",
  "final_colour": "ORANGE"
}
```

**Dismiss**

```json
{"decision": "dismiss", "approved_at": "2026-11-04T10:00:00Z"}
```

## Minimal sequence

```text
normalize_case (free text only)
  -> match_discriminators(case.complaint)
  -> score_priority(case, matched_ids)
  -> retrieve_evidence(case.complaint)          # advisory
  -> assess_confidence(matched_ids, no_match, priority)
  -> raise_recheck_flag(previous, current)      # only with serial vitals
  -> [clinician decision]
  -> commit_priority(case_id, colour, case, approval_token)
```

Stop before the last step on `out_of_scope`, `abstained`, `missing_vitals`, `no_match`, or
`deferral`. A stop is a safe terminal, not a failure.
