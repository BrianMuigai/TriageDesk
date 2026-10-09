"""The single home for the extraction prompt template (D-02; hashed by SAFE-04).

``llm/client.py`` imports :data:`EXTRACTION_PROMPT` from here — the prompt is
never inlined at a call site. Plan 01-04 hashes this module's bytes as the
prompt provenance artefact.
"""

from __future__ import annotations

EXTRACTION_PROMPT = """You are a triage-desk assistant. Convert the nurse's note into JSON that matches the schema below.

Rules:
- Extract only what the note states. If a vital is not present, use null. NEVER guess, default or impute a value.
- `mobility` must be one of: walking, with_help, stretcher.
- `avpu` must be one of: alert, voice, pain, unresponsive.
- `trauma` is true only if the note describes trauma; otherwise false.
- Select `matched_discriminator_ids` ONLY from the closed list below. If none match, return [] and set `no_discriminator_matched` to true.
- Put the nurse's original wording in `case.complaint`.
- Do NOT compute any score, colour, or arithmetic. Only structure the note.

JSON schema:
{schema}

Closed discriminator id list (may be empty until Phase 2 populates it):
{discriminator_ids}

Nurse's note:
{note}
"""
