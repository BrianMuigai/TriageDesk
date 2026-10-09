# CONVENTIONS — TriageDesk

> **IRON-CLAD RULE.** All code, tests, configuration, and documentation MUST adhere to **DRY** and
> **SOLID**. A change that violates either is rejected at review and blocks the phase. No exceptions.
> This file is the single source of truth for engineering standards; other docs reference it, they do
> not repeat it.

## 1. DRY — single source of truth

| Concern | The one place it lives | Everyone else |
| --- | --- | --- |
| SATS TEWS bands + colour thresholds | `data/sats_tews.yaml` | read via the loader |
| SATS discriminators + categories | `data/sats_discriminators.yaml` | read via the loader |
| Vitals / case schema | one schema module (typed) | import it |
| Citation formatting | one helper | call it — never inline strings |
| Audit-log record shape | one logging function | every tool call routes through it |
| Tool contracts | one declaration per tool | MCP server + graph share it |
| Design detail | this file + root docs | `.planning/` and root docs **link**, never duplicate |

Any TEWS threshold, discriminator string, or citation that appears in more than one place **in code or at
runtime** is a defect. This rule is scoped to code + runtime: `data/*.yaml` is the machine authority and no
SATS value may be re-derived or inlined under `src/`. `docs/SATS.md` is the human-readable transcription
reference derived from the same manual; it is never imported at runtime and is excluded from this gate by
design.

## 2. SOLID — applied to this codebase

- **S** — *Single responsibility.* One job per module, tool, and graph node. `score_priority` scores
  and returns citations; it does **not** persist or notify. A graph node routes; it does not compute.
- **O** — *Open/closed.* Extend by **data and configuration**, not by editing working code. A new SATS
  rule is a YAML edit; a new capability is a **new** node + a **new** tool, leaving existing ones
  untouched. (This is also what makes the live "add a requirement" review a one-line change.)
- **L** — *Liskov substitution.* Every MCP tool honours its declared contract; no tool silently changes
  its return shape. Swapping the owned store implementation for the borrowed SQLite MCP must not break
  callers.
- **I** — *Interface segregation.* Narrow tool interfaces. No "fat" tool that does everything. A node
  depends only on the tools it actually uses.
- **D** — *Dependency inversion.* The high-level graph depends on the **MCP tool interface**, not on
  concrete implementations. The scorer, the store, and the model are **injectable** dependencies
  (enables isolated testing and the owned/borrowed server swap).

## 3. Enforcement (wired into GSD gates)

| Gate | Check |
| --- | --- |
| **plan-check** | Every plan cites how it respects DRY/SOLID; reject plans that duplicate logic or create god-nodes. |
| **code review** | Flag duplicated logic, responsibility leaks, and hard-coded SATS values outside `data/`. |
| **verifier** | Confirm no SATS band/discriminator/citation appears outside its single source of truth **in code or at runtime** (`data/*.yaml` is authoritative; `docs/SATS.md` is the human-readable reference and is excluded by design). |
| **transition** | A violation is a blocker, not a nit. |

## 4. Rejected anti-patterns

- Duplicated TEWS thresholds or colour bands anywhere in code or at runtime outside `data/` (`docs/SATS.md` is the human-readable reference, not a code source).
- A "god" graph node that normalizes, scores, gates, and writes.
- A tool that both scores **and** writes to the queue (violates SRP **and** the safety gate).
- Copy-pasted citation strings instead of the shared helper.
- Documentation that restates content instead of linking to its single source.

---
*Established: 2026-10-09. Iron-clad: applies to all phases, all agents, all artifacts.*
