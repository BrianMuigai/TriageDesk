<!-- IRON-CLAD: do not remove. Placed outside GSD markers so it survives regeneration. -->
> ## IRON-CLAD RULE — DRY + SOLID
>
> **All code, tests, configuration, and documentation MUST adhere to DRY and SOLID.** A change that
> violates either is rejected at review and **blocks the phase**. No exceptions.
>
> Authoritative standard: [`CONVENTIONS.md`](./CONVENTIONS.md) — mandatory reading before any
> `Edit`, `Write`, or code generation.
>
> In short: SATS rules live only in `data/*.yaml`; citations come from one helper; tools are narrow and
> single-purpose; the graph depends on the tool *interface*, not concrete implementations; extend by
> data/config — not by editing working code.

<!-- GSD:project-start source:PROJECT.md -->

## Project

**TriageDesk**

TriageDesk is an agentic triage-support tool for the outpatient (OPD) triage desk of a busy public
hospital in Africa. It turns the vitals and presenting complaint a nurse already has in front of her
into a **sourced, SATS-grounded priority level in seconds** — and it never diagnoses, prescribes, or
moves a patient without a named clinician's approval. It is an entry in the *Agentic AI for Africa*
challenge (Health & Wellbeing track, **Symptom-based priority scoring**).

> Note: the repository-root `PROJECT.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `EVALS.md`,
> `DECISIONS.md`, `SECURITY.md` are the **public submission artifacts**. This `.planning/PROJECT.md`
> is GSD's internal working memory. Keep them consistent, but do not treat them as the same file.

**Core Value:** **A triage nurse gets a sourced, confirmable priority for each patient in seconds, and nothing reaches
the queue without her approval.** If everything else fails, this must work.

### Constraints

- **Team**: solo — scope discipline is a scored skill.
- **Timeline**: ~6 days (today 2026-10-09 → deadline 2026-10-15); repos are cloned at the deadline and
  post-deadline commits disqualify.
- **Compute**: local CPU only; small quantised open-weights model.
- **Stack**: required MCP + open-source orchestration; no closed no-code builders.
- **Data**: synthetic only; no health data leaves the machine.
- **Compliance**: every challenge requirement is tracked in `../REQUIREMENTS.md`.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

**IRON-CLAD RULE: DRY + SOLID** — see root `CONVENTIONS.md`. Violations block the phase.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
