# DESCRIPTION — TriageDesk
<!-- ~300-word challenge submission description. -->
<!-- Count below is approximate; finalise at submission. -->

**TriageDesk** is an agentic triage-support tool for the outpatient (OPD) triage desk of a busy public
hospital. It takes the two things the nurse already has in front of her — a set of vitals and a
presenting complaint — and returns a **sourced priority level in seconds**, grounded in the existing
**South African Triage Scale (SATS)**. It never diagnoses, prescribes, or moves a patient on its own.

**Sub-theme:** symptom-based priority scoring.

**Facility and workflow:** a district or regional public-hospital OPD with one or two nurses, paper
case cards, and basic equipment — a blood-pressure cuff, a thermometer, and a pulse oximeter. When a
patient reaches the desk, the nurse enters their vitals and a one-line complaint. A local,
open-weights model (Qwen2.5 via Ollama) structures the note, selects relevant SATS clinical
discriminators, and calls a set of MCP tools. Those tools validate the vitals, compute the Triage
Early Warning Score deterministically, apply discriminator overrides, and propose a colour-coded
priority with the exact rule and vital that produced it. If a patient's condition worsens while they
wait, the agent raises a re-check flag for a second look; it does not re-classify on its own.

Every priority is gated. The case card cannot be written to the queue until a **named nurse or
clinician approves it**, and every tool call — inputs, outputs, timestamps, and approver — is logged
for audit. Priorities are suggestions the nurse confirms, never verdicts.

TriageDesk is open source: **LangGraph** for orchestration, a **purpose-built MCP server** for scoring
and flags, and the **SQLite MCP server** for storage. It runs **entirely offline on synthetic data**,
so no health data leaves the facility.

<!-- Approx. word count: 300 -->
