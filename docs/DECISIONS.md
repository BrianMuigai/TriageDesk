# DECISIONS — TriageDesk

> ADR-lite. Each decision: **context · decision · why · consequence**. Rationale is preserved so the
> live technical review can be answered from the record, and so third-party components are **disclosed**
> (instant-disqualifier DQ-8).

---

### D1 — Hybrid: deterministic scorer + LLM orchestration
**Decision:** the model orchestrates, extracts, and explains; a **deterministic tool** computes the
SATS/TEWS score and citations. No number ever comes from the LLM.
**Why:** defensibility (a priority must survive a clinical-audit question) and evaluation honesty
(deterministic cases with known expected outputs). An LLM computing arithmetic is neither auditable nor
reproducible.
**Consequence:** more code in the scoring tool; far stronger JC-4 and JC-5.

### D2 — Use the South African Triage Scale (SATS)
**Decision:** build on SATS (EMSSA), not an invented scale or the Manchester Triage System.
**Why:** the brief explicitly requires an existing triage scale; SATS is openly published, designed for
resource-limited African settings, and is a two-part algorithm (TEWS + clinical discriminators) that is
straightforward to encode. MTS is licensed (proprietary), which conflicts with an open-source repo.
**Consequence:** adult SATS in scope; paediatric SATS de-scoped (see D6). Source: SATS Training Manual
2012 (EMSSA), <https://emssa.org.za>.

### D3 — Local open-weights model: qwen2.5:1.5b default, qwen3.5:4b fallback, RAM-constrained
**Decision:** run the agent loop on a locally installed Qwen via Ollama. The Phase-1 model spike
(`evidence/model-spike.json`) selected **`qwen2.5:1.5b`** as the **default** because with the 4B loaded
available RAM fell to 641 MB (< 1024 MB budget); **`qwen3.5:4b`** (3.3 GB) remains the verified
**fallback**. Frontier models optional and never required to run. Extraction uses **structured JSON
output** (`format=<schema>`), not native tool-calling.
**Why:** eligibility requires a full task on an open-weights model, and patient data must not leave the
country; both Qwens ran the path end-to-end, and the smaller one is the safe default on this host.
**Constraint discovered:** the host has **~6.9 GB RAM total and as little as ~0.8 GB free** — the 4B
needs ~3.3 GB, so it cannot be the default here; the fallback keeps the demo runnable.
**Consequence:** possible latency/swap pressure (documented in `REQUIREMENTS.md` G-2); measured in
Phase 1 and recorded honestly. Both `qwen2.5:1.5b` and `qwen3.5:4b` licences are recorded in the NOTICE.

### D4 — LangGraph for orchestration
**Decision:** LangGraph.
**Why:** open source; its `interrupt()` + checkpointer model maps directly onto "gate every irreversible
action on a named approver"; the explicit graph is easy to walk a judge through; node boundaries are
reusable. Alternatives (CrewAI, Pydantic AI, smolagents) were viable but had a weaker story for the
approval gate.
**Consequence:** slightly more boilerplate; much clearer agent shape for JC-1 and ST-1.

### D5 — Borrow the SQLite MCP server
**Decision:** use a pre-existing, **maintained** SQLite MCP server for the case/queue store and audit
table (candidates: `jparkerweb/mcp-sqlite`, `rusq/mcp-sqlite`). The official reference server is
archived and is not used.
**Why (one line):** *persistence, schema and query safety are solved — hand-rolling a database layer
adds zero triage value and adds auditable surface area we would have to defend.*
**Considered and declined:** a vector-store MCP for discriminator retrieval (stronger citation story,
more setup time). Its absence is exactly what makes case **E-09** fail — recorded as the honest
unfixed failure.
**Consequence:** satisfies BW-3; the "boring but correct" storage choice is deliberate. Because the
graph depends on the tool interface, swapping the server is a one-module change.

### D6 — Safe abstention on paediatric / out-of-scope input
**Decision:** the agent **detects** paediatric (age <12) or otherwise out-of-scope input and **abstains
+ escalates** to a human, instead of scoring with the adult chart.
**Why:** mis-scoring a child is dangerous. A deliberate, visible safe-failure is a stronger and more
honest story than a silent wrong answer.
**Consequence:** paediatric triage is out of scope (declared in `PROJECT.md`); tested as case E-06.

### D7 — Apache-2.0 licence
**Decision:** Apache-2.0 (OSI-approved).
**Why:** includes an explicit patent grant, which is appropriate for a health-adjacent project, while
remaining permissive.
**Consequence:** satisfies EL-3 and SB-2.

### D8 — English-only build
**Decision:** English input/output only; multilingual support is architecture-aware but out of scope.
**Why:** solo build under a ~6-day deadline; keeps prompt and eval surface small.
**Consequence:** the agent's multilingual potential is documented but not demonstrated.

### D9 — Synthetic data only
**Decision:** all fixtures are self-constructed synthetic patient records; a published scale is the
only external reference.
**Why:** the brief makes synthetic the default; no real patient data, consenting or not, avoids the
gravest instant-disqualifier entirely.
**Consequence:** no egress, no consent risk (DC-1…DC-3, DQ-5).

### D10 — Explicit graph over free-form ReAct
**Decision:** fix the control flow in the LangGraph graph; the model only makes bounded decisions at
named nodes.
**Why:** a small CPU model is an unreliable free agent. This keeps runs reproducible, which is what the
reliability criterion rewards.
**Consequence:** less "emergent" behaviour; far fewer random failures.

### D11 — SATS rules live in YAML data, not code
**Decision:** `data/sats_tews.yaml` and `data/sats_discriminators.yaml` hold the scoring logic.
**Why:** the live review (ST-1) adds a requirement on the spot; a one-line data edit makes that look
effortless. It also separates clinical content review from code.
**Consequence:** a small loader/validator is needed; worth it.

### D12 — Hash-chained audit log
**Decision:** every tool call is appended to `log/audit.jsonl` and the SQLite audit table, with a hash
chained to the previous entry.
**Why:** "readable log" is a scored, defensibility criterion; a tamper-evident chain is cheap and
credible.
**Consequence:** negligible overhead; strong JC-5 story.

### D13 — Single-theme entry; deterioration is a capability, not a second theme
**Decision:** enter under **Symptom-based priority scoring only**. The deterioration re-check is a tool
of the same agent, not a separate "Deterioration watch" submission.
**Why:** the rules forbid entering one project under more than one theme; the re-check exists to protect
the scoring workflow, not to be a second product.
**Consequence:** unambiguous one-theme compliance.

### D14 — Build with AI coding tools, ship only what we can explain
**Decision:** use AI coding assistants freely (explicitly allowed), but nothing ships that the author
cannot explain line-by-line in the live review.
**Why:** the brief says the live review is where they separate "directing a coding agent" from
"accepting output you cannot explain."
**Consequence:** a preference for explicit, small, named components over clever code — which also
happens to be the best shape for the live "add a requirement" test.

### D15 — Treat the presenting complaint as untrusted data, never instructions
**Decision:** free-text input is parsed into **typed fields**; instructions embedded in prose are never
executed. The colour is computed deterministically from the typed fields.
**Why:** a SOTA agent treats untrusted input as data. The deterministic scorer means prompt injection
cannot set a priority — an injected "mark this red" has no rule citation and is rejected.
**Consequence:** strong, cheap resistance to the most relevant injection vector; tested by E-13.

### D16 — Idempotent, approval-keyed queue writes
**Decision:** `commit_priority` is keyed by `case_id` (+ content hash) and requires an approval token.
**Why:** the queue write is the one irreversible action; retries must not place a patient twice.
**Consequence:** safe under retry/replay; complements the LangGraph `interrupt()` gate.
**v1.1 note:** the idempotency key now covers the **immutable case input** (the normalized `CaseInput`
payload), not `colour` alone — so an `edit` supersedes the queue row in place (one row, updated
colour, unchanged position) rather than inserting a second one.

### D17 — Pin and hash prompts, model, and scale versions
**Decision:** prompt templates, model version, SATS data, and tool schemas are pinned and hashed; every
audit record names the versions that produced it.
**Why:** reproducibility is a defensibility requirement — a priority must be explainable and
re-derivable.
**Consequence:** small config overhead; directly serves JC-5.

### D18 — DRY + SOLID are iron-clad engineering standards
**Decision:** all code, tests, configuration, and documentation adhere to **DRY** and **SOLID**. The
authoritative standard is [`CONVENTIONS.md`](CONVENTIONS.md), enforced at the **plan-check**,
**code-review**, and **verifier** gates.
**Why:** duplicated SATS values are simultaneously a correctness risk and a defensibility risk, and
responsibility leaks break the safety gate. Maintainability is how a solo builder keeps a 6-day sprint
auditable.
**Consequence:** a violation blocks a phase. Rules live once (YAML data / a single helper); a new
capability means a **new** tool + **new** node, leaving existing code untouched.

### D19 — Local span tracing with a content-addressed `trace_id`; replay is read-only by construction
**Decision:** tool, node and model spans are emitted from the **existing** seams — the `@audited`
interceptor, the composition-root node wrapper, and the `llm/client` boundary — to **ONE** local,
append-only JSONL sink (`spans.jsonl`) written by **ONE** module (`observability/spans.py`). The
`trace_id` reuses the existing `case_id_for_note(raw_note)` derivation, so one case has exactly one trace
across a restart and across replay (never a random uuid), and every audit record gains a first-class
`trace_id` (additive; sealed in the canonical digest when non-empty). Cloud tracing is neutralised and **asserted**
inert at startup. Replay (`replay.py`) reconstructs a past case **read-only** from the checkpoint plus
the audit/span stream; it compiles no graph and builds no tool map, so the gated commit is structurally
unreachable and no model is called.
**Why:** "nothing left the machine" and "replay cannot write" must be *provable*, not asserted in prose.
Reading a finished thread's channels with the checkpointer's read method (no graph compile) is stronger
than a reduced tool map — there is no tool surface at all — and an asserted inert tracer is the only way
to guarantee the default LangChain/LangSmith packages already in the environment cannot egress.
**Consequence:** adding the audit field **widens** the `audit` table; when the column is absent,
`ensure_schema` applies an idempotent `ALTER TABLE … ADD COLUMN trace_id` (no migration framework —
synthetic, disposable data, the same posture D9 and the Phase-6 key change took), and pre-phase-7 rows
still **verify** because an empty `trace_id` is omitted from the canonical digest (WR-03). The span sink
is a new gitignored runtime artefact. Because the trace
runs on content-addressed identity, two storyboard beats sharing a case share one trace (documented, not
a bug). No new dependency and no new graph node were added: the phase is wiring plus one projection.
The trace binding travels in a per-task `contextvars` value and so does **not** cross the owned-MCP
**subprocess** boundary: the demonstrated in-process paths (demo, eval, resume, replay) carry the trace,
while the `graph.build.load_graph_tools` / `run_case` stdio-subprocess path records `trace_id=""` — a
declared limitation, not a silent claim (WR-02).
Rationale and the guaranteed properties: `SECURITY.md` §10.

### D20 — Asymmetric-cost deferral threshold for the coverage signal
**Decision:** the deterministic coverage/deferral signal (`core/confidence.assess`) answers a case only when
at least `DEFERRAL_MIN_SATISFIED_COMPONENTS` of its four components — vitals coverage, discriminator
coverage, the override-vs-TEWS path, and the TEWS distance from the band edge — are satisfied; a `no_match`
case is deferred unconditionally.
**Why:** the two costs are **asymmetric** — a missed emergency (an under-triaged patient reaching the queue)
is vastly more costly than a needless deferral (a nurse re-checking a low-evidence case). Setting the answer
bar high buys safety at the cost of coverage, and the coverage lost is reported rather than hidden (D8-09,
D8-10).
**Consequence:** the signal can only ever make the system *more* cautious — a deferral routes to `escalate` /
`request_missing_info`, never to `commit`, and never changes a scored colour (D8-12). The named constant
lives once in `core/confidence.py`; this record is its rationale and it is never tuned to make a test green.

### D21 — Retrieval grounding over the SATS discriminator KB
**Decision:** The retrieval corpus is derived from `data/*.yaml` through the **ONE** loader
(`core/rules.py`) — the discriminator catalogue and its categories — with nothing re-authored and no SATS
value inlined. The ranking is an **in-house deterministic integer lexical scorer** with an explicit
`(-score, discriminator_id asc)` tie-break: no `rank-bm25`, no numpy, no embeddings, no vector store, and
**zero new dependencies**. The evidence contract (`EvidenceResult`) carries **no colour, target or priority
field**, so a colour is *unrepresentable* rather than merely unused (mirroring D8-04's no-float posture).
Retrieval runs **after `score`** in the `ground` node and writes only the `evidence` state channel, which
**no router reads**; the scorer remains the only colour producer and `citations == triggered_rules` is
untouched. The declared failure **E-09**'s honest outcome stays the committed deferral.
**Why:** ROADMAP SC2 is a **non-write** claim — retrieval must *show* the evidence that grounds a colour
while being structurally unable to *set* one. An in-house integer scorer keeps the ranking reproducible,
offline and dependency-free (sidestepping `rank-bm25`'s numpy-2 alias risk), and the *absence* of a colour
field is stronger than a rule not to use one. Attribution is the point: every returned passage carries the
closed-set discriminator id it came from, traceable to `data/*.yaml` (D9-01, D9-03, D9-10).
**Consequence:** The `evidence` channel is advisory display/provenance only — adding retrieval to a case
cannot change the path taken or the scored colour, proven channel-by-channel. **TEWS-band resolution:** the
band structure is read through the same ONE loader but yields **no passage family**, because band data is
colour-bearing and carries no complaint-addressable text, so a band passage would either emit a colour
(forbidden) or re-author band prose (forbidden). E-09 is addressed by real retrieval AND reported as a clean
defer — never by an added alias, fixture or threshold (D9-02, D9-07, D9-08, D9-09).

### D22 — Read-only borrowed MCP on the agent path
**Decision:** The borrowed SQLite server's read paths (`db_info`, `list_tables`, `get_table_schema`,
`read_records`) are exercised **behind the unchanged `Store` protocol**. A `READ_TOOLS` allowlist plus a
fail-closed leading-keyword statement guard (`is_read_only_statement`) sit in the **ONE** dispatch seam
(`BorrowedStore._call`), so a mutation presented on the read path is refused *before* the borrowed tool is
reached and the mutating record tools (`create_record`/`update_records`/`delete_records`) are **unnameable**.
`write=True` is reserved for the schema bootstrap and the gated commit, which stays the only mutation route.
**Why:** MCP-01 is an **integration** claim — the borrowed read tools must be genuinely *used*, not merely
declared (the Phase-1 STATUS G7 gap). Read-only by construction beats read-only by convention (the Phase-7
replay precedent), and the `Store` protocol shape must not change, so the graph keeps depending on the
interface, not the borrowed implementation (SOLID: D). The guard is a second, independent barrier beside the
allowlist (D9-11, D9-12, D9-13).
**Consequence:** A mutation on the agent path fails closed and provably reaches no borrowed server; the
queue/audit writes remain reachable only through the gated commit's parameterised `query`. An unverified
read-path wire shape **degrades** and is recorded on the adapter's `read_path_report` instead of crashing the
store-open path the demo, eval, resume and commit all depend on (D9-14). No new dependency and no
`Store`-protocol change.

### D23 — The desk surface is a dependency-free presentation bridge
**Decision:** the desk surface is ONE local HTML page served by a **stdlib `http.server`** handler
bound to **loopback only**, with no build step, no CDN and **no new dependency** (D10-01, D10-03,
D10-16). It is a **thin, presentation-only** bridge: it renders the graph's own typed outputs — the
`approval_gate` interrupt payload, the `PriorityResult`, the `evidence` channel and the confidence
signal — and **re-derives no colour, citation, target time or confidence value** (D10-02, D10-04,
D10-07). The vitals form validates through the ONE `CaseInput` schema and surfaces that schema's own
rejection (D10-13). Every gate decision flows through the ONE pause/resume plumbing and the gated
commit tool; the surface has **no commit path of its own**, a timeout is no approve and a dismiss
commits nothing (D10-10, D10-11, D10-12). The uncertainty banner renders on the **deferred/escalated
terminal**, never beside the gate: a `no_match`/deferral case routes to a terminal and never reaches
the approval gate, so a deferred case renders a read-only card and **no** gate (D10-17). The edit
control offers **exactly the colours the approval token validates against** — the band colours read
from the TEWS substrate — so the surface can never offer a decision the gate would refuse (D10-18).
**Why:** the human is the actor — the card *suggests*, the banner *flags*, and the gate is the only
route to the queue. A thin bridge over the shipped seams keeps one schema, one citation helper, one
colour producer and one pause/resume path (CONVENTIONS §1), so the surface cannot become a second
implementation of the clinical logic it displays. A stdlib handler keeps the surface readable
end-to-end and reproducible from a clean clone, with nothing to build and nothing to fetch.
**Consequence:** the surface is a peer presentation layer (like `demo/`): it holds no scoring,
routing or gate logic, and its only mapping is a substrate colour string to a CSS class. The banner
and the gate are disjoint by construction (a case at the gate never carries the deferral signal), so
the honest reachable design reopens no locked decision. The edit set, the copy and the token/colour
lists stay in their single sources (the substrate, the UI-SPEC and the schema) and are never restated
here. No new dependency, no graph change and no second validation rule.

### D24 — Extraction fidelity is fixed at the contract the model fills
**Decision:** the two fixable measured failures are corrected at the **extraction seam** (D11-01),
never in the scorer. (a) **E-04** — the emergency-discriminator case — is fixed by a **general
`Field(description=…)`** on `CaseInput.age_years`: the model intermittently dropped the stated age,
and a null age short-circuits to the fail-closed `ABSTAIN`, so the honesty lever is the **contract
the model is asked to fill**, not prose engineering of the prompt. The same seam carries a general
`Field(description=…)` on **every scored numeric vital** — the set `data/sats_tews.yaml` defines and
the serial-vitals recheck compares, bound to its schema field structurally rather than hand-listed —
that resolves a serial `before -> after` reading to the AFTER (current) value. Both descriptions are
general (no fixture number, no fixture wording, no SATS value) and the extraction schema is sealed
into the report provenance as `extraction_schema_hash`, so a contract change cannot leave the
published provenance stale. (b) **E-07** — the deterioration-recheck case — is a
**test-data-inconsistency repair** (D11-14): the fixture's free-text `note` omitted the temperature
its golden `case` already declared, so a faithful extraction could not produce the golden case; the
note now states it. The golden `case`, the `previous_case` and the expectation are **unchanged**.
**Why:** the ROADMAP premise ("the extraction loses the clinical phrasing") was only half true — the
matcher retrieved the emergency discriminator on every run, and E-07's blocker was a fixture defect,
not an extraction gap. Fixing the *contract* (the schema the model fills) keeps one schema source
(§1) and one extractor, where a deterministic field-parser would be a second extractor for one field
(SRP/DRY), a prompt worked-example quoting the fixture would be tuning to the test (D11-02), and a
scorer/routing relaxation would weaken the fail-closed design. Repairing the note restores the
fixture-consistency rule the other note-bearing fixtures already satisfy; it edits no expectation
and leaves the deterministic `--offline` control unregressed (D11-04).
**Consequence:** the model input changed while `prompt_hash` (which covers the prompt template only)
did not, so the provenance now also carries `extraction_schema_hash`, and the measured artefact is
re-generated and re-published rather than hand-edited. No expectation, threshold or golden value was
edited to make a case pass and no literal alias was added (D11-02); the published measured outcomes
live in `EVALS.md` and are not restated here.

### D25 — Milestone close: demonstrated-not-claimed, and two steps stay human
**Decision:** the Phase-12 close makes four honesty choices explicit. (a) The live extension is
demonstrated **data-only** — a discriminator added to `data/sats_discriminators.yaml` re-scores through
the shipped matcher/scorer in a **fresh process**; there is **no** hot reload and no cache-clear flag
(the substrate is `@lru_cache`d per process), and the demonstration is a hermetic harness, not a
narrative ([`REVIEW.md`](REVIEW.md)). (b) The demo shows the committed [`EVALS.md`](EVALS.md) projection
plus the live `failure` beat (E-09) and does **not** stream the ~10-minute real eval run — the
projection is the measured artefact ([`DEMO.md`](DEMO.md)). (c) The clinical-fit gap stays **declared**
with a marked, attributed, **empty** slot; no review is invented. (d) The demo-video upload and the
clinician review are **human** steps, flagged `human_needed`, never claimed.
**Why:** the milestone's whole credibility is "extend by data, not code" (D11) and "honest beats an
over-claim" — a rehearsal that pretended to hot-reload, a demo that faked a ~10-minute run, or a
fabricated clinician quote would each be a scored repudiation risk (D12-02, D12-05, D12-06, D12-07).
**Consequence:** the reviewer can drive the live extension from [`REVIEW.md`](REVIEW.md) and see the
same re-score the harness proves; the measured numbers live only in [`EVALS.md`](EVALS.md); and the two
genuinely-human steps stay visible as open items (STATUS G1/G2) rather than papered over. No source
behaviour and no dependency changed.

### D26 — The committed queue position is a typed field, never parsed from the reason
**Decision:** the queue position the gated write assigned is exposed as a typed
`CommitResult.position: int | None`, set once from the store's `row.position` in the gated commit
tool; the desk surface names the position when it is present and falls back to the position-free
copy when it is absent.
**Why:** the desk module reads **typed channels only** and never a free-text reason (per the
`desk/server.py` module docstring and `terminal_kind()`'s explicit avoidance of
`Escalation.reason`), so the panel must not string-parse `CommitResult.reason` even though the CLI's
reason happens to carry the position in prose. The field is additive because `CommitResult` is the
one contract model without `extra="forbid"`, so every existing constructor and reader is unaffected.
**Consequence:** the surface reads the position off the typed channel (`getattr(commit, "position",
None)`), never the reason; the CLI reason string is untouched; and the desk package still imports
neither the store/queue nor the MCP server (the no-self-commit guard stays green).

---

## Disclosed third-party components (DQ-8)

| Component | Origin | Licence/notes |
| --- | --- | --- |
| LangGraph | LangChain (open source) | MIT |
| MCP client adapter | `langchain.mcp` namespace | current; replaces archived `langchain-mcp-adapters` |
| Ollama | Ollama (open source) | MIT; runtime only |
| qwen2.5:1.5b | Alibaba (open weights) | selected default (D-01/D-03); Apache-2.0; licence in NOTICE |
| qwen3.5:4b | Alibaba (open weights) | verified fallback; Apache-2.0; licence in NOTICE |
| SQLite MCP server | maintained community (`jparkerweb/mcp-sqlite` / `rusq/mcp-sqlite`) | official reference server is archived |
| SATS manual | EMSSA | clinical content; cited, not redistributed wholesale |
