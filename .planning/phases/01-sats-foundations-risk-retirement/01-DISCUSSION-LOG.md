# Phase 1: SATS Foundations & Risk Retirement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-09
**Phase:** 1-SATS Foundations & Risk Retirement
**Areas discussed:** Model & extraction contract, MCP strategy & server, SATS data encoding, Module boundaries & DRY/SOLID

---

## Model & extraction contract

| Option | Description | Selected |
|--------|-------------|----------|
| 1.5B primary, 3B opt-in | Apache-2.0, fits host RAM; 3B if benchmark proves fit | |
| 3B primary if it fits | Better quality; RAM risk on 7 GB box | |
| Decide purely by benchmark | Run both, pick by quality × latency × RAM | |
| **`qwen3.5:4b` (user-provided)** | Already installed locally (3.3 GB) | ✓ |

**User's choice:** Use the locally installed `qwen3.5:4b` model.
**Notes:** The machine currently shows only ~0.8 GB free RAM (6.1 GB in use), so Phase 1 must *measure*
that the 4B runs within budget (freeing memory for the demo) and keep a documented smaller-Qwen fallback.
Model authority and the strict-JSON extraction contract were accepted as proposed (D-02, D-03).

---

## MCP strategy & server

| Option | Description | Selected |
|--------|-------------|----------|
| World A + documented World B fallback | `langchain.mcp.MCPAdapter` behind a spike; deprecated adapter as one-module fallback | ✓ |
| World B from the start | Pin deprecated adapter + `mcp<2`; safer but a dead-end dependency | |
| World A only | No fallback | |

**User's choice:** World A with a documented World B fallback (D-04). Borrowed server `jparkerweb/mcp-sqlite`, pinned (D-05). Gate stays ours (D-06). Evidence bar agreed (D-07).

---

## SATS data encoding

| Option | Description | Selected |
|--------|-------------|----------|
| Two YAML files, adult-only, dual-transcription verification, deterministic alias match | Single source of truth; paediatric abstain | ✓ |
| One YAML file | Less separation of concerns | |
| Adult + full paediatric | Out of scope for the deadline | |
| Embedding retrieval for discriminators | Deferred to v2 | |

**User's choice:** Two-file adult chart with dual-transcription verification and deterministic alias matching (D-08…D-11).

---

## Module boundaries & DRY/SOLID

| Option | Description | Selected |
|--------|-------------|----------|
| Layered `core/ (pure) · llm/ · mcp/ · store/ · graph/` + AST purity guard + one schema module | Enforces DRY/SOLID structurally | ✓ |
| Flat package | Faster now, drifts later | |
| Enforce by code review only | No mechanical guarantee | |

**User's choice:** Layered layout with an AST purity guard and one shared schema module (D-12…D-15).

---

## the agent's Discretion

- YAML key naming/shape, test framework specifics, spike transcript format, exact pinned versions.

## Deferred Ideas

- Discriminator confidence field + clarifying-question loop (E-09 fix).
- Embedding-based discriminator retrieval.
- Referral / department routing tool.
- "Additional investigations" column + SHCP discretion.
- Multilingual clinical lexicon.
- Paediatric SATS charts.
