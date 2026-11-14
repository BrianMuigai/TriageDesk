# Deferred items — Phase 14

Out-of-scope discoveries found during 14-03's stale-prose audit. Not fixed here; logged for a
future plan.

| Item | File:line | Why it is stale | Why deferred |
| --- | --- | --- | --- |
| Diagram still labels `verify` as a model critic | `docs/assets/architecture.mmd:77` (`N5 -. critic .-> QWEN`) | `graph/nodes.verify` is deterministic and makes no model call; the edge to the local model is false. | The generated `architecture.svg` / `architecture.pdf` are tracked derivatives; regenerating them runs `npx @mermaid-js/mermaid-cli` (a package install, forbidden by this plan's T-14-SC zero-install rule). 14-03 is scoped to the prose in `ARCHITECTURE.md` and `docs/REQUIREMENTS.md`. |
| Diagram lists a prompt that does not exist in the server | `docs/assets/architecture.mmd:39` (`P2["verify_priority"]`) | No `verify_priority` prompt exists under `src/`; the verify step is a deterministic function. | Same generated-derivative constraint as above. |
