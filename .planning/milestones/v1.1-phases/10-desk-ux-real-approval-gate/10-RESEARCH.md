# Phase 10: Desk UX & Real Approval Gate - Research

**Researched:** 2026-10-12
**Domain:** Dependency-free local HTML desk surface (stdlib `http.server`) bridging a LangGraph human-approval gate
**Confidence:** HIGH for the in-repo seams (read line-by-line this session); MEDIUM for the stdlib HTTP mechanics (standard library, well-known)

## Summary

This phase is **presentation over existing seams**. Everything it renders already exists as a typed object or an
untyped-but-graph-owned payload; the only genuinely new artifact is a stdlib `http.server` bridge plus hand-authored
HTML/CSS and a `desk` CLI subcommand. The hard work is **wiring discipline**: reading the right channels, never
re-deriving a colour/citation/confidence value, and never introducing a commit path.

Three findings dominate the plan and must be resolved before task decomposition:

1. **The uncertainty banner is a TERMINAL-state component, not a gate companion.** Under the frozen routing
   (`graph/build.py::route_after_assess`), a `no_match` or low-coverage case **defers and routes to
   `escalate`/`request_missing_info` — it never reaches `approval_gate`**. Therefore `no_match` is *always* `False`
   and `confidence.deferral` is *always* `False` for any case that pauses at the gate. The UI-SPEC's "Deferred" row
   ("banner **and** the card; the gate is present") is **not reachable** as written; the banner must render on the
   deferred/escalated terminal state, alongside a read-only suggestion card and the terminal copy — with **no gate
   controls**. This is a conflict between the approved UI-SPEC and the carried decision D8-12 that the planner must
   surface and resolve (see Open Question 1).

2. **The interrupt payload does NOT carry `evidence` or `confidence`.** `approval_gate`'s payload has
   `colour`, `target`, `triggered_rules`, `citations`, `missing_vitals`, `matched_ids`, `no_match`, `second_look`,
   `case_id` — but the evidence list (UX-02) and the deferral signal (UX-01) live only on the **state channels**
   `evidence` and `confidence`. The bridge must read the paused **state snapshot** (not just the payload) to render
   the evidence list and to evaluate the banner trigger.

3. **The gate's editable colour set is the substrate's `tews_to_colour` (4 colours today), not the UI-SPEC's "five".**
   `ApprovalToken` validates `final_colour` against `{band.colour for band in get_tews().tews_to_colour}`
   (`core/schema.py:303`), which excludes `BLUE`. Offering `BLUE` in the edit radio (as the UI-SPEC's five-name list
   and `--colour-blue` token imply) would produce a decision the gate refuses. The editable set must be derived from
   the **same** expression the gate validates against (Open Question 2).

**Primary recommendation:** Build one new `src/triagedesk/desk/` package (a peer of `demo/run.py`) exposing pure
functions — `form_to_case`, `render_state`, `decide` — plus a thin `BaseHTTPRequestHandler`. Reuse
`durable.run_to_gate` (pause), `durable.resume_paused` (resume) and `durable.approval_decision` (the ONE decision
shape) over a session `checkpoints.db`; reuse `evals.tools.build_tools` for the offline tool mapping. Keep HTML/CSS
as separate asset files (not Python string literals) so the no-duplicated-SATS guard stays green. Add the `desk`
subcommand to `cli.py` with a lazy import after `harden_offline()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Render suggested colour/target/why-vitals/citations (UX-02) | Browser/Client (HTML/CSS) | — | Presentation-only; values come from the graph's typed outputs |
| Render evidence list (UX-02) | Browser/Client | API/Backend bridge | Bridge serialises the `evidence` channel; browser paints it |
| Uncertainty banner (UX-01) | API/Backend bridge (trigger decision) | Browser/Client (paint) | The trigger is a typed fact (`no_match` OR `confidence.deferral`); the bridge decides which body string |
| Approve/edit/dismiss gate (UX-03) | API/Backend bridge | Browser/Client (form) | The decision resumes the graph via `durable`; the browser only collects `{decision,name,role,colour}` |
| Queue commit | Graph (resumed `approval_gate` → `commit`) | — | The ONLY route to a queue row; the surface never commits (D10-12) |
| Vitals validation (UX-04) | API/Backend bridge | — | Validates through the ONE `CaseInput`; the browser form is a dumb field collector |
| Static asset serving | API/Backend bridge | — | stdlib handler reads HTML/CSS from `desk/static/`; localhost-only |
| Quickstart doc (UX-04) | Docs (`docs/DESK.md`) | — | One-screen runbook; not coupled to graph internals |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Surface architecture**
- **D10-01:** The surface is ONE local HTML page served by a **stdlib `http.server`** handler. No build
  step, no CDN, no framework, no new dependency. It runs from a literal one-command entry point
  (`uv run triagedesk desk`).
- **D10-02:** The server is a **thin bridge**, not a second implementation: it renders the graph's own
  outputs — the interrupt payload, the `PriorityResult`, the `evidence` channel and the `ConfidenceResult` —
  and **never re-derives a colour, a citation or a confidence value**.
- **D10-03:** It binds **localhost only** and makes no external request; the agent path stays offline. No
  egress, no telemetry, no CDN asset.
- **D10-04:** The surface is **presentation-only** (SOLID: S): no scoring, routing or gate logic lives in it.
  Any decision it shows was made by the graph.

**The priority card & citations**
- **D10-05:** The card renders the **suggested** colour, the target time, and the "why" vitals next to their
  **adjacent citations** — framed as a **suggestion**, never a diagnosis. No diagnostic/assessment/plan/
  prescription language (the `HandoverCard` forbidden-token discipline applies to every rendered string).
- **D10-06:** Every rendered clinical claim is **sourced**: citations come from the ONE citation helper
  (`core/citations.py`); the card never invents an unsourced line.
- **D10-07:** The card consumes the graph's **typed** outputs and the `evidence` channel; it never re-runs
  the model, the matcher or the scorer.
- **D10-08:** Colour is **not the only signal**: each colour is accompanied by its text label, so the card is
  legible without colour perception.

**The uncertainty banner & the gate**
- **D10-09:** A **loud banner** shows whenever the typed uncertainty signal fires — `no_match` or a deferral
  from `assess` — reading "no discriminator matched / low confidence — nurse to confirm". It is driven by
  the **typed signal** (UX-01), so the E-09 class becomes a visible flag rather than a buried JSON key.
- **D10-10:** The gate is a real **approve / edit / dismiss** interaction that records a **named approver**.
  A `dismiss` commits **no** artefact, and a **timeout defaults to no approve** — there is no auto-commit and
  no default-approve path.
- **D10-11:** The gate's decisions flow through the **existing** `approval_gate` interrupt and the gated
  `commit_priority` contract — no new write path, no bypass.
- **D10-12:** The surface can never commit on its own: the only route to a queue row remains the resumed
  interrupt through the gated tool.

**Vitals entry & the quickstart**
- **D10-13:** A minimal vitals-entry form validates through the **ONE shared schema** (`core/schema.py`'s
  `CaseInput`) — the same schema the graph consumes — and surfaces the schema's own rejection for invalid
  input (no second validation rule).
- **D10-14:** A **one-screen desk quickstart** gives a first desk-facing interaction in literal steps,
  without coupling the reader to graph internals.
- **D10-15:** The surface is **testable end-to-end** (form → graph → card → gate) and the tests stay
  hermetic (no network, no model, no borrowed subprocess, no repo-root artefact).
- **D10-16:** No new dependency. The whole surface ships as stdlib + the existing stack.

### the agent's Discretion
- The exact HTML/CSS layout, the markup structure, and the visual treatment (the UI-SPEC owns this).
- The HTTP route shape and the request/response encoding, provided D10-02/D10-03 hold.
- Whether the page is server-rendered per request or a single page with a small fetch loop.
- How the timeout is expressed (a client timer, a server deadline, or both), provided D10-10 holds.
- The quickstart's exact wording and where it lives.

### Deferred Ideas (OUT OF SCOPE)
- Multimodal intake (voice + chart/cuff photo) — UX-05, future requirements.
- A mandatory clarifying-question loop when no discriminator matches — DISC-01.
- Multilingual UI — LANG-01.
- A production deployment/hosting story — out of scope (local prototype).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UX-01 | A loud "no discriminator matched / low confidence — nurse to confirm" banner is shown, backed by a typed uncertainty field that drives routing, so the E-09 class becomes a visible flag rather than a buried JSON key. | Banner trigger = `no_match` (payload/state) OR `confidence.deferral` (state channel). **Routing finding:** both imply a terminal, so the banner renders on the deferred/escalated terminal, not at the gate. Trigger-conditional body per UI-SPEC. See Architecture Pattern 4. |
| UX-02 | A human-readable priority card renders the **suggested** colour, target time, and the "why" vitals next to adjacent citations — framed as a suggestion, never a verdict, and never a diagnosis. | Card data: payload `colour`/`target`/`triggered_rules` (each `detail` + `citation`) + `evidence.passages`. Baseline citation is already a `triggered_rules` row (no substrate read). Forbidden-token discipline from `HandoverCard.FORBIDDEN_FIELD_TOKENS`. See Architecture Pattern 1. |
| UX-03 | The approval gate is a real approve/edit/dismiss interaction that records a named approver and commits no artefact on dismiss or on timeout (no default approve) — the human decision is no longer a hardcoded value. | Decision built by `durable.approval_decision`; resume via `durable.resume_paused`; commit refusal path in `mcp/server.py::commit_priority`. Timeout = no POST = no resume = no commit (by construction). Editable colours must match the gate's accepted set. See Architecture Pattern 3. |
| UX-04 | A minimal vitals-entry surface (validating through the one shared schema) plus a one-screen desk quickstart give a first desk-facing interaction without coupling to graph internals. | Form fields mirror `CaseInput`; validation is `CaseInput.model_validate` catching `ValidationError`; one quickstart doc at `docs/DESK.md`. See Architecture Pattern 2 and Pattern 6. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `http.server` / `socketserver` (stdlib) | Python 3.12 stdlib | Serve the one local HTML page and the JSON bridge routes | Zero-dependency, offline, no build step — exactly D10-01/D10-16. `ThreadingHTTPServer` + `BaseHTTPRequestHandler` is the canonical stdlib pattern. |
| `json` (stdlib) | 3.12 stdlib | Encode/decode the bridge's typed payloads | The graph's own `model_dump(mode="json")` output is already JSON-ready. |
| `html` (stdlib) | 3.12 stdlib | Escape untrusted strings (complaint, name, role) | Prevents the untrusted complaint from injecting markup (SECURITY.md T-1; ASVS V5). |
| `urllib.parse` (stdlib) | 3.12 stdlib | Parse form-encoded POST bodies (`parse_qs`) | stdlib form decoding; no dependency. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `triagedesk.durable` (in-repo) | — | The ONE pause/resume helper (`run_to_gate`, `resume_paused`, `approval_decision`) | Every gate interaction; never a second resume path |
| `triagedesk.evals.tools.build_tools` (in-repo) | — | The ONE offline tool mapping (real owned tools, model stubbed) | Building the tool map the graph runs over |
| `triagedesk.core.schema.CaseInput` (in-repo) | — | The ONE vitals schema | Form validation — no second validator |
| `triagedesk.core.rules.get_tews` (in-repo) | — | The ONE substrate loader | Deriving the editable-colour set from the data authority |
| `triagedesk.mcp.server.resolve_store` (in-repo) | — | The ONE store-resolution seam | The commit path resolves its store; tests inject the fake |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `http.server` | `flask`/`fastapi`/`starlette` | Forbidden — new dependency + build step (D10-01/D10-16). The project ships stdlib-only. |
| Hand-authored HTML/CSS assets | A Jinja2 template | Jinja2 is not a declared dependency; and embedding templates in `.py` would trip the no-duplicated-SATS guard. Plain `str.format`/`string.Template` + asset files is enough. |
| Server-rendered HTML per request | SPA + JSON fetch loop | Both allowed by D10 discretion; server-rendered is simpler and needs no client JS. |
| A terminal TUI (`rich`) | Browser HTML | Research ARCHITECTURE.md suggested `rich`, but D10-01 **locks HTML**; `rich` is transitive, not a chosen dep. |

**Installation:** none — no new dependency (D10-16).

**Version verification:** no package is added; the runtime is the pinned Python 3.12 (`.python-version` → `3.12`) via the committed `uv.lock`. Verified this session: host `uv` is `0.12.24` and the repo pins `3.12` (host default is 3.14, hence the pin).

## Package Legitimacy Audit

**Not applicable.** This phase installs **no external packages** (D10-16: "No new dependency. The whole surface
ships as stdlib + the existing stack."). The Package Legitimacy Gate is therefore skipped by construction — there is
no registry lookup to perform, no `postinstall` to inspect, and no `[ASSUMED]`/`[SUS]`/`[SLOP]` disposition to
record. `pyproject.toml` `dependencies` and `[dependency-groups]` are unchanged by this phase.

## Architecture Patterns

### System Architecture Diagram

```
  Nurse (browser, localhost)
        │  GET /                      │ POST /case (form)          │ POST /decision (form)
        ▼                             ▼                            ▼
  ┌───────────────────────────────────────────────────────────────────────────┐
  │ DESK BRIDGE  (src/triagedesk/desk/  — stdlib http.server, 127.0.0.1 only)   │
  │  · form_to_case(): form dict ──► CaseInput.model_validate (ONE schema)      │
  │  · render_state(): graph state ──► view-model (colour, target, why, evidence,│
  │                    banner trigger, terminal kind)  ──► HTML (escaped)       │
  │  · decide(): {decision,name,role,colour} ──► durable.approval_decision       │
  └───────▲──────────────────────────────────────────────────┬─────────────────┘
          │ reads graph state channels                        │ run_to_gate / resume_paused
          │ (priority, evidence, confidence,                  │ (durable — the ONE helper)
          │  matched_ids, no_match, second_look,              │
          │  escalation, recovery, commit_result)             │
  ┌───────┴──────────────────────────────────────────────────▼─────────────────┐
  │ GRAPH  (frozen)  ingest → normalize → retrieve → score → ground → verify    │
  │        → recheck → assess ──deferral──► escalate | request_missing_info      │
  │                        └──ok──────────► approval_gate(interrupt) → commit    │
  │                                          │ (pause on checkpoints.db)         │
  └──────────────────────────────────────────┼───────────────────────────────────┘
                                             ▼
                              commit_priority (the ONLY queue write;
                              refuses no-token / malformed / dismiss)
```

Data flow, end to end:
1. **Form submit** → bridge validates via `CaseInput` → builds `raw_note` (canonical case JSON) + `case`.
2. **`durable.run_to_gate(tools, raw_note=…, case=…, db_path=…)`** runs the graph; it either **pauses** at
   `approval_gate` (`paused=True`, `payload` set) or **terminates** (`paused=False`).
3. **Bridge renders** the view-model from the returned state (`PausedRun.result`) + payload.
4. **Decision submit** → bridge builds the decision via `durable.approval_decision` → **`durable.resume_paused`**
   resumes the interrupt → `commit` runs → `commit_result` (`committed` or `refused`).
5. **Bridge renders** the committed/dismissed/refused panel from `commit_result`.

### Pattern 1: The bridge's data flow — exactly which typed objects, from where

**What:** The bridge reads the graph's paused **state** plus the interrupt **payload**. The payload is an untyped
dict built by `approval_gate`; the state channels are typed Pydantic models.

**When to use:** Every render.

**The exact payload keys** — `graph/nodes.py:333-343` (verbatim):
```python
    payload = {
        "case_id": case_id_for_note(state["raw_note"]),
        "colour": priority.colour,
        "target": priority.target,
        "triggered_rules": [rule.model_dump(mode="json") for rule in priority.triggered_rules],
        "citations": list(priority.citations),
        "missing_vitals": list(priority.missing_vitals),
        "matched_ids": list(state.get("matched_ids") or []),
        "no_match": bool(state.get("no_match")),
        "second_look": second_look.model_dump(mode="json") if second_look is not None else None,
    }
```
`[VERIFIED: src/triagedesk/graph/nodes.py:333-343]`

**The state channels the bridge must additionally read** — `graph/state.py:40-65` (verbatim, abridged to the keys
the surface consumes):
```python
    raw_note: str
    case: CaseInput | None
    matched_ids: list[str]
    no_match: bool
    priority: PriorityResult | None
    approval: dict | None
    commit_result: CommitResult | None
    handover: HandoverCard | None
    route: str | None
    error: str | None
    attempt: int
    # Safe terminals (ORCH-05, D-03): a typed recovery/escalation the graph stops on.
    recovery: RecoveryRequest | None
    escalation: Escalation | None
    # Serial-vitals second look (GATE-04, D-07): the previous case and the flag it raises.
    previous_case: CaseInput | None
    second_look: RecheckFlag | None
    # Deterministic coverage/deferral signal (AGENT-02, D8-08): written by ``assess`` and
    # consulted by ``route_after_assess``. It never reaches ``commit`` (D8-12).
    confidence: ConfidenceResult | None
    # Attributable retrieval grounding (AGENT-03, D9-07/D9-08): written by ``ground`` and
    # consulted by NOTHING that routes. ...
    evidence: EvidenceResult | None
```
`[VERIFIED: src/triagedesk/graph/state.py:40-65]`

**Why both:** the payload lacks `evidence` and `confidence`; the state snapshot has them. `PausedRun.result`
(`durable.py:146-153`) is the interrupted `ainvoke` result when `paused=True`, and `dict(snapshot.values)` when
`existed=True` (`durable.py:133-141`) — **both include the channels written before the gate** (`priority`,
`evidence`, `confidence`, `matched_ids`, `no_match`, `second_look`).

**The view-model mapping (presentation only):**
| UI element | Source | Notes |
|---|---|---|
| Suggested colour name + label | payload `colour` (or `priority.colour`) | Render the string verbatim; never map a number→colour |
| Target time | payload `target` (or `priority.target`) | Substrate string, rendered verbatim |
| Why-vitals rows | payload `triggered_rules[]` → `detail` + `citation` | The baseline row is already in `triggered_rules` (see Pattern 1a) |
| Evidence list | state `evidence.passages[]` → `label` + `citation`; `evidence.no_match`/`reason` | Ranked; empty ⇒ the no-evidence line |
| Not recorded | payload `missing_vitals` | |
| Second look | payload/state `second_look` | |
| Banner trigger | state `no_match` OR `confidence.deferral` | See Pattern 4 |
| Terminal kind | state `confidence.deferral` / `escalation` / `recovery` | See Pattern 4 |
| Committed/refused | state `commit_result` (`committed`/`refused`/`reason`) | After resume only |

### Pattern 1a: The baseline citation is already on the payload (no substrate read)

The UI-SPEC's `why-vitals-list` empty case says a routine case "renders the substrate's `baseline_citation` line".
The scorer already emits that as a `TriggeredRule` — `core/scorer.py:262-270` (verbatim):
```python
    if not triggered and used:
        triggered.append(
            TriggeredRule(
                rule_id="tews_baseline",
                detail=f"{', '.join(used)} within normal SATS bands",
                points=0,
                citation=format_citation(rules.baseline_citation, rules.citation),
            )
        )
```
`[VERIFIED: src/triagedesk/core/scorer.py:262-270]` — and `citations=[rule.citation for rule in triggered]`
(`core/scorer.py:278`), so the baseline appears in both `triggered_rules` and `citations` on the payload. **The
bridge renders `triggered_rules` and never needs to read `baseline_citation` directly.**

### Pattern 2: Vitals form ↔ the ONE schema (`CaseInput`)

**What:** The form posts every `CaseInput` field; the bridge validates with `CaseInput.model_validate(payload)` and
catches `pydantic.ValidationError`.

**The exact field set** — `core/schema.py:20-51` (verbatim):
```python
Mobility = Literal["walking", "with_help", "stretcher"]
AVPU = Literal["alert", "voice", "pain", "unresponsive"]


class CaseInput(BaseModel):
    age_years: int | None = Field(default=None, ge=0, le=130)
    age_months: int | None = Field(default=None, ge=0, le=1560)
    age_ambiguous: bool = False
    height_cm: float | None = Field(default=None, ge=30.0, le=260.0)
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    heart_rate: int | None = Field(default=None, ge=0, le=350)
    systolic_bp: int | None = Field(default=None, ge=0, le=400)
    diastolic_bp: int | None = Field(default=None, ge=0, le=300)  # captured, not scored (§4.1)
    temperature_c: float | None = Field(default=None, ge=20.0, le=45.0)  # rejects °F magnitudes
    spo2: int | None = Field(default=None, ge=0, le=100)  # captured, not scored (§4.1)
    mobility: Mobility | None = None
    avpu: AVPU | None = None
    trauma: bool | None = None
    complaint: str = ""  # UNTRUSTED free text (SECURITY.md T-1)
```
`[VERIFIED: src/triagedesk/core/schema.py:20-51]`

**Rules for the form → schema bridge:**
- Empty optional fields must map to `None`, not `""` or `0` (the schema distinguishes a missing vital honestly).
- `trauma` is `bool | None`; an unanswered checkbox must be `None`, not `False`.
- `complaint` is free text and **untrusted** — the bridge must HTML-escape it on render.
- On `ValidationError`, surface `exc.errors()[i]["msg"]` (the schema's own message) beside the field — **no second
  validation rule** (D10-13). The UI-SPEC error copy is `{the schema's own field message}. Check the highlighted
  field and try again.`
- The enum option **values** (`walking`/`with_help`/`stretcher`, `alert`/`voice`/`pain`/`unresponsive`) may be
  inlined — they are input-domain enums, explicitly excluded from the no-duplicated-SATS guard
  (`tests/test_no_duplicated_sats.py:48-49` `INPUT_DOMAIN_FIELDS = ("mobility", "avpu")`).

### Pattern 3: The fail-safe timeout & the gate (no path where the surface commits)

**What:** The bridge never commits. It only (a) runs to the gate, and (b) resumes with a human decision. A timeout
is simply "no decision POST arrives", so no resume happens and no commit is possible.

**The decision shape is the ONE builder** — `durable.py:196-218` (verbatim, abridged):
```python
    timestamp = approved_at or datetime.now(UTC).isoformat()
    if decision == "dismiss":
        return {"decision": "dismiss", "approved_at": timestamp}
    if decision not in _DECISIONS:
        raise DurableError(
            f"unknown decision {decision!r}; expected one of {', '.join(_DECISIONS)}"
        )
    if not (approver or "").strip():
        raise DurableError(f"--approver is required for a {decision!r} decision")
    if not (role or "").strip():
        raise DurableError(f"--role is required for a {decision!r} decision")
    token: dict[str, Any] = {
        "decision": decision,
        "approved_by": approver,
        "role": role,
        "approved_at": timestamp,
    }
    if decision == "edit":
        if not (colour or "").strip():
            raise DurableError("--colour is required for an 'edit' decision")
        token["final_colour"] = colour
    return token
```
`[VERIFIED: src/triagedesk/durable.py:196-218]` — the bridge **must** call this and surface its `DurableError` (a
whitespace-only name/role is rejected here, matching the UI-SPEC "whitespace-only counts as absent"). Do **not**
re-implement the blank check.

**The resume refuses if nothing is pending** — `durable.py:168-175` (verbatim):
```python
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    async with checkpointed_graph(tools, Path(db_path)) as graph:
        snapshot = await graph.aget_state(config)
        if not snapshot.next:
            raise DurableError(
                f"no pending approval gate for thread_id {thread_id} in {db_path}"
            )
        return await graph.ainvoke(Command(resume=dict(decision)), config)
```
`[VERIFIED: src/triagedesk/durable.py:168-175]`

**The gate refuses anything but a well-formed token** — `mcp/server.py:290-299` (verbatim):
```python
    if approval_token is None:
        return CommitResult(refused=True, reason="no approval token supplied; refusing to commit")
    try:
        token = ApprovalToken.model_validate(approval_token)
    except ValidationError:
        return CommitResult(refused=True, reason="approval token is malformed; refusing to commit")
    if token.decision == "dismiss":
        return CommitResult(
            refused=True, reason="clinician dismissed the priority; refusing to commit"
        )
```
`[VERIFIED: src/triagedesk/mcp/server.py:290-299]`

**Fail-safe proof strategy (for the planner's tests):**
- **Timeout:** assert the bridge exposes **no** route/function that calls `resume_paused`/`commit_priority` without a
  human decision; a request that never submits a decision leaves the queue row count unchanged.
- **Dismiss:** POST `decision=dismiss` → `commit_result.refused is True`, `committed is False`, zero rows.
- **Failure is never an approve:** a malformed/blank decision surfaces an error and leaves the decision unresolved
  (no resume, no row).
- **No self-commit:** grep/assert the `desk/` package never imports `triagedesk.store.queue` or
  `triagedesk.mcp.server.commit_priority` directly.

### Pattern 4: The uncertainty banner's typed triggers — and the routing consequence

**What:** The banner fires from a typed fact, never a string heuristic. The trigger is
`no_match` **OR** `confidence.deferral`.

**The routing fact** — `graph/build.py:168-176` (verbatim):
```python
    signal = state.get("confidence")
    if signal is not None and signal.deferral:
        priority = state.get("priority")
        # Defensive arm (see docstring): unreachable while ``route_after_score`` diverts
        # missing-vitals cases, but retained so a deferral always lands on a safe terminal.
        if priority is not None and priority.missing_vitals:
            return "request_missing_info"
        return "escalate"
    return "approval_gate"
```
`[VERIFIED: src/triagedesk/graph/build.py:168-176]`

**`no_match` forces a deferral** — `core/confidence.py:174-180` (verbatim):
```python
    if no_match:
        return ConfidenceResult(
            deferral=True,
            level="low",
            components=components,
            reason="no discriminator matched the complaint; deferring for human review",
        )
```
`[VERIFIED: src/triagedesk/core/confidence.py:174-180]`

**Consequence (the finding):** `no_match ⇒ deferral ⇒ escalate` (or `request_missing_info`), so **any case that
pauses at `approval_gate` has `no_match is False` and `confidence.deferral is False`**. The banner therefore appears
on the **deferred/escalated terminal**, not alongside the gate. The UI-SPEC's "Deferred" row ("banner and the card;
the gate is present") is unreachable. The recommended reachable design:

| Graph outcome | `paused` | Banner? | Card? | Gate? | Terminal copy |
|---|---|---|---|---|---|
| Paused at `approval_gate` | `True` | No (deferral impossible here) | Yes (full) | Yes | — |
| Deferred (`confidence.deferral`) | `False` | **Yes** (`no_match` body if `no_match` else deferral body) | Read-only suggestion (the score ran; `priority` is on the state) | **No** | `This case was deferred for human review — no priority was committed.` |
| Escalated (out-of-scope/abstained, no deferral) | `False` | No | No | No | `This case was escalated for human review — no priority was committed.` |
| Recovery (missing scored vital) | `False` | No | No | No | `A scored vital is missing. Re-measure before scoring.` |

**Trigger selection (the ONE rule):** `trigger = "no_match" if no_match else ("deferral" if confidence and
confidence.deferral else None)`. The body string varies with the trigger (UI-SPEC); the treatment (loud panel) does
not. Never fire on `evidence.no_match` (that is "no excerpt matched", a different fact) or on `missing_vitals` alone.

**Terminal-kind selection (typed, not string):** use `confidence.deferral` for the deferred copy; else if
`escalation is not None` for the escalated copy; else if `recovery is not None` for the recovery copy. Do **not**
infer the kind from `Escalation.reason` (it is a free-text reason that varies).

### Pattern 5: A dependency-free HTTP surface (stdlib shape)

**What:** `http.server.ThreadingHTTPServer` + a `BaseHTTPRequestHandler` subclass, bound to `127.0.0.1`.

**Bind localhost only (D10-03):**
```python
server = ThreadingHTTPServer(("127.0.0.1", port), DeskHandler)   # never "0.0.0.0"
```
Passing an explicit `("127.0.0.1", port)` address — never the bare port, never `""`/`"0.0.0.0"` — is the bind rule.
`port=0` lets the OS pick a free port (useful for the in-process test, which then reads `server.server_address`).

**Serve static assets without a build step:** keep `index.html` and `styles.css` as files under
`src/triagedesk/desk/static/` and read them via `Path(__file__).parent / "static" / <name>`; serve with a **fixed
allowlist of two filenames** (never a user-supplied path — prevents traversal). Content types: `text/html;
charset=utf-8`, `text/css; charset=utf-8`.

**Why assets, not inline templates (critical):** the no-duplicated-SATS guard
(`tests/test_no_duplicated_sats.py:147-162`) scans every `src/**/*.py` string literal for SATS values. A colour name
(`RED`/`GREEN`/`YELLOW`/`ORANGE` are `tews_to_colour` leaves) or a target time (`Immediate`, `< 10 min`, …) inlined
in a Python template string would **fail the guard**. Keeping markup in `.html`/`.css` files (not scanned) avoids
this. The Python may still build a CSS class name generically, e.g. `f"colour-{colour.lower()}"` — no SATS literal.

**Escaping (ASVS V5):** `html.escape()` every rendered string — the complaint above all, plus name/role and every
citation/label. The bridge is presentation-only but must not emit raw untrusted text.

**Offline:** `cli.main` already calls `harden_offline()` first (see Pattern 6); the bridge itself makes no outbound
request. `observability/offline.py::harden_offline` (`offline.py:37-61`) pops the six tracer env keys and asserts
`tracing_is_enabled()` is `False`.

### Pattern 6: CLI entry point (`uv run triagedesk desk`) and the quickstart doc

**The subcommand joins the existing argparse pattern** — `cli.py:42-138` builds `eval`/`demo`/`resume`/`replay`;
add a `desk` parser with `--host`/`--port`/`--db` (defaults localhost / a fixed port / `checkpoints.db`).

**The harden-first invariant** — `cli.py:146-151` (verbatim):
```python
    harden_offline()
    from triagedesk.demo.run import list_beats, run_demo
    from triagedesk.durable import approval_decision, resume_thread
    from triagedesk.evals.runner import run_eval
    from triagedesk.graph.build import CHECKPOINTS_DB_PATH
    from triagedesk.replay import replay_case
```
`[VERIFIED: src/triagedesk/cli.py:146-151]` — the `desk` handler **must be imported lazily inside `main`, after
`harden_offline()`**, never at module import (WR-06).

**Quickstart doc:** put the one-screen quickstart in a **new `docs/DESK.md`** (the project keeps runbooks under
`docs/`). This is the safest home because the existing doc guards constrain specific files only:
`tests/test_docs_final.py` constrains `ARCHITECTURE.md` (≤700 words/≤110 lines), `DESCRIPTION.md` (~300 words),
`README.md` (quickstart/no-stale/E-09) and `EVALS.md` (projection); `tests/test_demo_runbook.py` constrains
`docs/DEMO.md` (beat coverage + honesty clauses). A new `docs/DESK.md` is unconstrained, so it cannot break a guard.

### Anti-Patterns to Avoid
- **Re-deriving a colour/citation/confidence value in the bridge.** The bridge maps a substrate colour string to a
  CSS class only; it never computes a colour, band, or target (D10-02/D10-04).
- **Reading `baseline_citation` or the target times directly from the substrate to render the card.** They are
  already on the payload/`triggered_rules`; reading them again is a second source (violates D10-06).
- **Adding a graph node, a tool, or a routing change.** The phase is presentation-only; the graph and its
  `TRACER_NODES`/`OWNED_TOOL_ALLOWLIST` are untouched.
- **Embedding SATS literals in Python strings.** Trips `test_no_duplicated_sats.py`.
- **A second validation rule for the form.** Use `CaseInput`'s own `ValidationError`.
- **A second resume/commit path.** Use `durable.approval_decision` + `durable.resume_paused`.
- **Binding `0.0.0.0`.** Localhost only (D10-03).
- **Offering `BLUE` as an edit colour.** The gate's token validator rejects it (see Open Question 2).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pause/resume the graph at the gate | A bespoke interrupt handler / a second checkpointer lifecycle | `durable.run_to_gate` + `durable.resume_paused` (+ `durable.resume_thread`) | The ONE pause/resume helper (D10-11); a second path risks a second commit route |
| Build the resume decision dict | A second blank-check for name/role/colour | `durable.approval_decision` | It strips/validates exactly as `ApprovalToken` requires; whitespace-only is rejected (WR-06) |
| Validate the vitals form | A parallel field validator | `CaseInput.model_validate` + catch `ValidationError` | ONE schema module (D10-13); a second rule drifts from the graph's contract |
| Format a citation | An inline `f"{source} — {ref}"` | The citation string already on the payload (`triggered_rules[].citation`, `citations[]`) | ONE citation helper (`core/citations.py`); D10-06 |
| Decide whether to show the banner | A string/regex heuristic on a reason | The typed facts `no_match` / `confidence.deferral` | D10-09; a heuristic re-derives a value the graph owns |
| Map a colour to its CSS style | A Python `{colour: hex}` dict | A CSS class per colour (`colour-red`, …) in `styles.css`; Python emits `colour-{name.lower()}` | Keeps SATS colour names out of Python literals (no-duplicated-SATS guard) |
| Resolve the store | A concrete `default_store()` call in the bridge | The existing `mcp.server.resolve_store` seam (used by the commit path) | ONE resolver; tests inject the fake |
| Serve files by requested path | `Path(base) / self.path` | A fixed two-name allowlist | Prevents path traversal |

**Key insight:** every value the surface shows already exists as a typed object or a graph-owned payload. The bridge's
only legitimate computation is *presentation* — a lookup from a substrate string to a CSS class, and the selection of
which fixed copy string to show. Anything that looks like a clinical computation is a DRY violation.

## Common Pitfalls

### Pitfall 1: Rendering the banner at the gate (it can never be there)
**What goes wrong:** the bridge evaluates `no_match`/`deferral` only in the paused-at-gate path, so the banner never
fires (both are always `False` there), and the E-09 class shows no banner — UX-01 fails.
**Why it happens:** the UI-SPEC's "Deferred" row implies banner+card+gate co-occur; the graph routes deferrals to a
terminal.
**How to avoid:** render the banner in the **terminal** branch; keep the trigger evaluation trigger-driven so it is
correct wherever the typed signal is present.
**Warning signs:** a test that asserts a banner appears on a paused case — it would need a fabricated `no_match=True`
state, which the graph never produces.

### Pitfall 2: Reading only the interrupt payload
**What goes wrong:** the evidence list renders empty and the deferral trigger is always `False`, because the payload
lacks `evidence` and `confidence`.
**Why it happens:** the payload is the "evidence card's source" but is a subset of the state.
**How to avoid:** read the paused **state** (`PausedRun.result`) for `evidence`/`confidence`; use the payload for the
card facts (or read `priority` from the state — both are the graph's own output).
**Warning signs:** `evidence.passages` always `[]`; the deferral banner never fires.

### Pitfall 3: Inlining SATS literals in the Python bridge
**What goes wrong:** `uv run pytest tests/test_no_duplicated_sats.py` fails; the phase is blocked at the DRY gate.
**Why it happens:** a colour name (`RED`…) or target time (`Immediate`, `< 10 min`) is written into a Python
template string or a `{colour: hex}` dict.
**How to avoid:** keep markup in `.html`/`.css` assets; derive class names generically; render colour/target strings
from the graph's values.
**Warning signs:** the guard reports a `src/triagedesk/desk/*.py` offender with a colour/target string.

### Pitfall 4: A `ruff` TID251 lint failure for the new package
**What goes wrong:** `ruff check` fails because `desk/` imports `triagedesk.mcp`/`triagedesk.store`, which the
`banned-api` rule forbids outside the allowlisted packages.
**Why it happens:** `[tool.ruff.lint.per-file-ignores]` (`pyproject.toml:57-72`) disables TID251 for
`llm/`,`mcp/`,`graph/`,`store/`,`evals/`,`demo/`,`replay.py`,`scripts/`,`tests/` — but not a new `desk/`.
**How to avoid:** add `"src/triagedesk/desk/**" = ["TID251"]` (mirroring `demo/**`/`evals/**`) if the bridge reaches
those layers; or keep the bridge importing only non-banned modules.
**Warning signs:** a TID251 error naming a `desk/` file.

### Pitfall 5: The `existed=True` collision on a repeated case
**What goes wrong:** submitting the same case twice returns `PausedRun(paused=False, payload=None, existed=True)`;
the bridge renders a terminal/wrong state because it has no payload and no clear "gate pending" flag.
**Why it happens:** `run_to_gate` refuses to replay a thread that already has state (`durable.py:132-141`).
**How to avoid:** treat `existed` explicitly — either use a fresh/session `checkpoints.db`, or re-read the pending
interrupt from the snapshot, or surface an "already submitted" state. Do not assume `payload is not None` when
`paused` is False.
**Warning signs:** a repeated submit shows an empty card.

### Pitfall 6: XSS via the untrusted complaint
**What goes wrong:** the complaint (or name/role/citation) is interpolated into HTML unescaped; the adversarial
complaint from `tests/test_safety_spine.py` can inject markup.
**Why it happens:** string concatenation without escaping.
**How to avoid:** `html.escape()` every rendered string (ASVS V5). Keep the response `Content-Type: text/html;
charset=utf-8`.
**Warning signs:** a rendered `<script>`/`<img onerror=…>` from a crafted complaint.

### Pitfall 7: A commit path in the bridge
**What goes wrong:** the bridge calls `commit_priority` or writes the store directly, bypassing the gate (a challenge
disqualifier).
**Why it happens:** convenience — "the case is ready, just commit it".
**How to avoid:** the bridge only calls `run_to_gate` (pause) and `resume_paused`/`resume_thread` (human decision);
assert in a test that the `desk/` package never imports the queue/commit writer.
**Warning signs:** a queue row appears without a decision POST.

## Code Examples

### Building the tool map and running to the gate
```python
# Source: composes the shipped seams (durable.py, evals/tools.py, evals/case.py)
from triagedesk.core.schema import CaseInput
from triagedesk.durable import run_to_gate, resume_thread, approval_decision, PausedRun
from triagedesk.evals.case import CaseSpec, TERMINAL_OUTCOMES
from triagedesk.evals.tools import build_tools
from triagedesk.evals.usage import UsageRecorder

def _tools_for(case: CaseInput):
    # The offline tool builder returns the user's case from normalize_case (no model).
    spec = CaseSpec(
        id="desk", description="desk submission", note=case.complaint, case=case,
        expected=TERMINAL_OUTCOMES[0], pass_criteria="never evaluated", source="desk",
    )
    return build_tools(spec, offline=True, recorder=UsageRecorder())

async def submit(case: CaseInput, db_path: str) -> PausedRun:
    raw_note = case.model_dump_json()          # content-addressed thread id, stable per case
    return await run_to_gate(_tools_for(case), raw_note=raw_note, case=case, db_path=db_path)
```
> Note: `TERMINAL_OUTCOMES[0]` is the same "declared harness terminal" trick `durable._RESUME_PLACEHOLDER` uses
> (`durable.py:47-55`) to avoid a SATS colour literal in code. `expected` is never read on this path.

### The banner trigger (the ONE rule)
```python
def banner_trigger(state) -> str | None:
    if bool(state.get("no_match")):
        return "no_match"
    confidence = state.get("confidence")
    if confidence is not None and confidence.deferral:
        return "deferral"
    return None
```

### Resuming with a human decision (no self-commit)
```python
async def decide(thread_id: str, form: dict, db_path: str):
    decision = approval_decision(                    # the ONE decision-shape builder
        form["decision"], approver=form.get("name"), role=form.get("role"),
        colour=form.get("colour"),
    )                                                 # raises DurableError on blank name/role
    return await resume_thread(thread_id=thread_id, decision=decision, db_path=db_path)
```

### The HTTP skeleton (localhost-only, allowlisted assets)
```python
import html, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

STATIC = Path(__file__).parent / "static"
_ASSETS = {"index.html": "text/html; charset=utf-8", "styles.css": "text/css; charset=utf-8"}

class DeskHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib naming)
        name = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        if name not in _ASSETS:
            self.send_error(404); return
        body = (STATIC / name).read_bytes()
        self.send_response(200); self.send_header("Content-Type", _ASSETS[name])
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

def serve(port: int = 8765) -> None:
    ThreadingHTTPServer(("127.0.0.1", port), DeskHandler).serve_forever()  # localhost only
```

### The hermetic in-process test pattern
```python
# Source: stdlib loopback + the conftest hermetic seams (injected store, tmp checkpoints, tmp spans)
import threading, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer

def test_form_to_card(tmp_path, injected_store):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path=tmp_path / "cp.db"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        data = urllib.parse.urlencode({"complaint": "central chest pain", "age_years": "40",
                                       "respiratory_rate": "24", "heart_rate": "118",
                                       "systolic_bp": "108", "temperature_c": "38.9",
                                       "mobility": "walking", "avpu": "alert"}).encode()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/case", data=data) as resp:
            body = resp.read().decode()
        assert "Suggested priority" in body
    finally:
        server.shutdown()
```
> `injected_store` (autouse) and `_spans_sink` (autouse) are the conftest seams; `tmp_path` keeps
> `checkpoints.db` out of the repo root. Loopback only — no external network.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| A hardcoded demo decision (`_named_approval`) resumes the gate | A real approve/edit/dismiss form posts a decision that `durable.approval_decision` builds | Phase 10 (this phase) | The human decision is no longer a constant (UX-03) |
| The uncertainty signal is a buried JSON key (`confidence.deferral`, `no_match`) | A loud trigger-driven banner renders on the terminal | Phase 10 | The E-09 class becomes a visible flag (UX-01) |
| No desk surface (declared gap G11 / JC-3) | A dependency-free local HTML page over the existing seams | Phase 10 | Fit-to-desk gap closed (UX-04) |
| Terminal TUI (`rich`) was the research suggestion | HTML via stdlib `http.server` (locked by D10-01) | Phase 10 discuss | No build step, no new dep, reviewer-readable |

**Deprecated/outdated:**
- The research `ARCHITECTURE.md` suggestion to promote the interrupt payload to a typed `ApprovalRequest` schema
  contract is **not** a locked phase decision; the phase's canonical refs do not include it, and the phase is
  presentation-only. The bridge should render the existing untyped payload dict (it is the graph's own output).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The bridge pauses/resumes via `durable.run_to_gate` + `durable.resume_paused`/`resume_thread` over a session `checkpoints.db` (rather than holding the graph in-process). | Pattern 3 | If the owner prefers an in-process graph, the wiring changes; the gate semantics are unaffected either way. |
| A2 | The desk form path runs the **offline** tool mapping (`build_tools(..., offline=True)`) so the surface is model-free and hermetic; the model is not needed because the form already supplies a structured `CaseInput`. | Pattern 1 / Code Examples | If the desk must drive the real model for the complaint, tests lose hermeticity and the "no model" guarantee; the form path would need the online seam. |
| A3 | The banner renders on the **deferred terminal** with a read-only suggestion card and the terminal copy (no gate controls), because D8-12 forbids a deferral reaching the gate. | Pattern 4 | Conflicts with the UI-SPEC "Deferred" row; needs owner confirmation (Open Question 1). |
| A4 | The editable-colour set is the substrate's `tews_to_colour` colours (4 today), matching the gate's token validator — not the UI-SPEC's "five SATS names". | Pattern 3 / Open Question 2 | If BLUE is offered, an edit to BLUE is refused by the gate — a confusing dead control. |
| A5 | The one-screen quickstart lives in a new `docs/DESK.md`. | Pattern 6 | If placed in README/DEMO.md, the existing doc guards constrain it. |
| A6 | Every rendered string must be HTML-escaped (the complaint is untrusted). | Pitfall 6 | XSS via a crafted complaint in a local page. |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
(Not empty: A1–A6 need confirmation, A3/A4 most urgently.)

## Open Questions (RESOLVED)

All three questions below were resolved by the owner on 2026-10-13 and are implemented by plans 10-01/10-02;
each carries an inline **RESOLVED** note cross-referencing the CONTEXT decision that supersedes the
recommendation. The section is retained (not deleted) so the resolution trail is auditable.

1. **Where does the uncertainty banner render, given the graph routes deferrals to a terminal?** — **RESOLVED (D10-17).**
   - What we know: `route_after_assess` sends any `no_match`/deferral to `escalate`/`request_missing_info`
     (`graph/build.py:168-176`); `no_match` forces `deferral` (`core/confidence.py:174-180`). So a gated case never
     carries either trigger. D8-12 (carried) forbids a deferral reaching `commit`.
   - What's unclear: the UI-SPEC's "Deferred" row pairs the banner with the card **and the gate**, which is
     unreachable; it also has a separate "Terminal (deferred/escalated/recovery)" row.
   - Recommendation: render the banner on the **terminal** (deferred/escalated) branch, alongside a **read-only**
     suggestion card (the score ran, so `priority` is on the state) and the terminal copy, with **no gate**. Treat
     the UI-SPEC's "gate is present" as an imprecision subordinate to D8-12. Confirm with the owner; if they want
     banner+gate for deferrals, that requires a routing change (violating D8-12) and is out of scope for a
     presentation phase.
   - **RESOLVED (D10-17, owner-confirmed 2026-10-13):** the recommendation is adopted — a deferred case renders the
     banner plus a read-only card and **no gate**; a committable case renders the card plus the real gate and no
     banner. The UI-SPEC state contract was amended to match. Implemented by 10-02 Task 1. No routing change.

2. **Which colours are offered in the "Edit colour" control?** — **RESOLVED (D10-18).**
   - What we know: `ApprovalToken` validates `final_colour` against `{band.colour for band in get_tews().tews_to_colour}`
     (`core/schema.py:303`) = {GREEN, YELLOW, ORANGE, RED} today; BLUE exists only in `target_times`.
   - What's unclear: the UI-SPEC says "the five SATS names" and declares `--colour-blue`.
   - Recommendation: derive the editable set from the **same expression the gate validates against** (one source);
     offer the 4 band colours today. Confirm with the owner before adding BLUE (which the gate would refuse).
   - **RESOLVED (D10-18, owner-confirmed 2026-10-13):** the recommendation is adopted — the edit control is derived
     from `{band.colour for band in get_tews().tews_to_colour}` (the SAME expression `ApprovalToken` validates
     against), so BLUE is never offered. Implemented by 10-02 Task 2. The UI-SPEC's `--colour-blue` token stays as
     a completeness swatch for a colour the graph supplies, never as an offered edit option.

3. **How is the `existed=True` re-submit handled?** — **RESOLVED (D10-19).**
   - What we know: `run_to_gate` returns `paused=False, payload=None, existed=True` for an existing thread.
   - What's unclear: whether the desk should reuse a session `checkpoints.db` (collisions on identical cases) or a
     fresh file per submission.
   - Recommendation: use a session-scoped `checkpoints.db` and handle `existed` explicitly (surface "already
     submitted", or re-read the pending interrupt from the snapshot).
   - **RESOLVED (D10-19, owner-confirmed 2026-10-13):** a session `checkpoints.db` is used and `existed=True` is
     handled explicitly — the bridge re-renders the card and the gate from the snapshot values, and the resume
     path's own pending-gate check is the guard (a stale re-submit is refused by the ONE plumbing). Implemented by
     10-02 Task 2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 (uv-managed) | The whole surface | ✓ | `.python-version` = `3.12` | — |
| `uv` | `uv run triagedesk desk` | ✓ | `0.12.24` (host) | — |
| stdlib `http.server`/`json`/`html`/`urllib.parse` | The bridge | ✓ | Python 3.12 stdlib | — |
| (no external service / no new package) | — | — | — | — |

**Missing dependencies with no fallback:** none — the phase is stdlib-only (D10-16).
**Missing dependencies with fallback:** none.

## Testability & Existing-Test Impact

**Validation Architecture:** **SKIPPED** — `workflow.nyquist_validation` is explicitly `false` in
`.planning/config.json`.

### Test framework
| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`, `pyproject.toml:35-37`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) |
| Quick run command | `uv run pytest tests/test_desk.py -q` |
| Full suite command | `uv run pytest -q` |

### Hermetic seams available (reuse, do not rebuild)
- `tests/conftest.py::injected_store` (autouse) injects the in-memory `Store` into `mcp.server.set_store` — the
  commit path exercises the fake, never the borrowed subprocess.
- `tests/conftest.py::_spans_sink` (autouse) redirects the span sink to `tmp_path` — no repo-root `spans.jsonl`.
- `tmp_path` for `checkpoints.db` — no repo-root `.db` artefact (`.gitignore` already ignores `*.db`).
- Loopback-only HTTP: bind `127.0.0.1:0` and drive with `urllib.request` — no external network.
- Offline tools: `build_tools(..., offline=True)` — no model call.

### Every existing test that could break when a new subcommand/node/asset/module appears
| Change | Breaks? | Why / action |
|--------|---------|--------------|
| New `desk` CLI subcommand | **No** | No test asserts the exact subcommand set; `test_durable_cli.py`/`test_replay_read_only.py` parse specific commands only. |
| New `src/triagedesk/desk/` package | **No** | No test enumerates modules; `test_purity.py` scans `core/` only; `test_safety_spine.py`/`test_graph_tracer.py` scan `graph/` only. |
| New static asset files | **No** | No test asserts an asset list. |
| New graph node | N/A | Phase adds **no** node; `test_graph_tracer.py:42-48` uses a **superset** check anyway. |
| New owned tool | N/A | Phase adds **no** tool; the four set-equality sites are untouched. |
| **SATS literal in `desk/*.py`** | **YES** | `tests/test_no_duplicated_sats.py:147-162` scans `src/**/*.py` string literals for colour/target/discriminator leaves → keep markup in `.html`/`.css`. |
| **`desk/` imports `triagedesk.mcp`/`triagedesk.store`** | **YES (lint)** | `ruff` TID251 `banned-api` is scoped by `pyproject.toml:57-72`; add `"src/triagedesk/desk/**" = ["TID251"]` (mirroring `demo/**`/`evals/**`). |
| Editing `ARCHITECTURE.md`/`DESCRIPTION.md`/`README.md`/`EVALS.md` | **YES** | `tests/test_docs_final.py` guards each; keep them unchanged — put the quickstart in a new `docs/DESK.md`. |
| Editing `docs/DEMO.md` | **YES** | `tests/test_demo_runbook.py` guards beat coverage + honesty clauses; only edit if you keep those invariants. |
| New `docs/DESK.md` | **No** | Unconstrained by any guard. |

## Security Domain

> `security_enforcement: true` (`security_asvs_level: 1`, `security_block_on: high`).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single local operator; no login surface (D10-01) |
| V3 Session Management | no | Stateless requests; no cookies/session tokens |
| V4 Access Control | partial | Bind `127.0.0.1` only (D10-03); no remote exposure. Optionally validate the `Host` header (DNS-rebinding). |
| V5 Input Validation | yes | `CaseInput.model_validate` (ONE schema) + `html.escape()` output encoding for the untrusted complaint/name/role/citations |
| V6 Cryptography | no | None used |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stored/reflected XSS via the untrusted complaint (SECURITY.md T-1) | Tampering | `html.escape()` every rendered string; `Content-Type: text/html; charset=utf-8` |
| HTTP header injection via untrusted input | Tampering | Never place user input in a header; the stdlib docs warn `send_header`/`send_response_only` do not scrub CRLF `[CITED: docs.python.org/3/library/http.server.html]` |
| Path traversal when serving assets | Information disclosure | Fixed two-name allowlist; never `SimpleHTTPRequestHandler` (the docs note it follows symlinks and can serve outside the directory) `[CITED: docs.python.org/3/library/http.server.html]` |
| CSRF / DNS-rebinding against a localhost server | Spoofing | Localhost bind; no ambient auth to abuse; the only effect is a human-gated queue write. Consider a per-session nonce if hardening further. |
| Unintended commit / automation bias | Elevation of privilege | The gate refuses without a well-formed token; timeout = no resume = no commit; the bridge has no commit path |
| Data egress | Information disclosure | `harden_offline()` at CLI start; no outbound request; no CDN/webfont asset |
| Prompt injection via the complaint | Tampering | The form path is model-free (offline tools); if the model is used, it may only structure/select closed-set ids (D-03) |

## Sources

### Primary (HIGH confidence)
- In-repo, read line-by-line this session:
  - `src/triagedesk/graph/nodes.py` (`approval_gate` payload 333-343; `handover` 392-421)
  - `src/triagedesk/graph/state.py` (channels 40-65)
  - `src/triagedesk/graph/build.py` (`route_after_assess` 150-176; `CHECKPOINTS_DB_PATH` 43; `_allowed_msgpack_modules` 356-369)
  - `src/triagedesk/core/schema.py` (`CaseInput` 20-51; `ApprovalToken` 258-309; `HandoverCard` 327-371)
  - `src/triagedesk/core/confidence.py` (`assess` 148-193)
  - `src/triagedesk/core/scorer.py` (baseline rule 262-270; citations 278)
  - `src/triagedesk/core/citations.py` (`format_citation` 28-39)
  - `src/triagedesk/core/rules.py` (`get_tews` 126-129; `DATA_DIR` 23)
  - `src/triagedesk/core/retrieval.py` (`retrieve` 62-111)
  - `src/triagedesk/durable.py` (`run_to_gate` 111-153; `resume_paused` 156-175; `approval_decision` 178-218)
  - `src/triagedesk/mcp/server.py` (`commit_priority` 268-313; `audited` 93-168)
  - `src/triagedesk/evals/tools.py` (`build_tools` 77-142)
  - `src/triagedesk/evals/case.py` (`CaseSpec` 62-96; `TERMINAL_OUTCOMES` 28)
  - `src/triagedesk/cli.py` (`main` harden-first 141-153; parsers 34-138)
  - `src/triagedesk/observability/offline.py` (`harden_offline` 37-61)
  - `src/triagedesk/demo/run.py` (the peer-adapter pattern)
  - `tests/conftest.py`, `tests/test_durable_cli.py`, `tests/test_demo_runbook.py`, `tests/test_docs_final.py`, `tests/test_safety_spine.py`, `tests/test_no_duplicated_sats.py`, `tests/test_purity.py`, `tests/test_graph_tracer.py`
  - `pyproject.toml`, `.planning/config.json`, `docs/CONVENTIONS.md`, `.planning/research/ARCHITECTURE.md`
- `.planning/phases/10-desk-ux-real-approval-gate/10-CONTEXT.md` and `10-UI-SPEC.md` (binding decisions + approved contract)
- `.planning/phases/08-.../08-CONTEXT.md` (D8-11/D8-12) and `.planning/phases/09-.../09-CONTEXT.md` (evidence channel)

### Secondary (MEDIUM confidence)
- Python stdlib `http.server` — `[CITED: docs.python.org/3/library/http.server.html]` (fetched this session): `ThreadingHTTPServer`, `BaseHTTPRequestHandler` `do_GET`/`do_POST`, `send_response`/`send_header`/`end_headers`, `--bind 127.0.0.1` for localhost-only, the CRLF-header and symlink security notes.

### Tertiary (LOW confidence)
- None material — the phase is stdlib-only and in-repo.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only; no new dependency; the seams are read directly.
- Architecture: HIGH — the data flow is read from the frozen source; the routing/banner finding is derived from
  `route_after_assess` + `assess` (verbatim quotes above).
- Pitfalls: HIGH — each pitfall is tied to a specific guard/test or a specific refusal path.

**Research date:** 2026-10-12
**Valid until:** ~2026-11-11 (stable; the frozen v1.0 spine and the Phase 8/9 seams are locked).
