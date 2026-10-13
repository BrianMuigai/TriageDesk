---
phase: quick
plan: "261013-sbd"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/triagedesk/core/schema.py
  - src/triagedesk/mcp/server.py
  - src/triagedesk/desk/server.py
  - tests/test_desk.py
  - tests/test_mcp_tools.py
  - tests/test_commit_idempotent.py
  - docs/DESK.md
  - docs/DEMO.md
  - docs/DECISIONS.md
autonomous: true
requirements: [QUICK-261013]
estimate:
  tokens: 42000
  raw_tokens: 30000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A nurse who approves or edits a case at the desk sees the queue position the gated write actually assigned, on the post-decision panel."
    - "A repeat submit or an edit of the SAME case shows the SAME queue position (supersede-in-place), and the queue holds exactly one row for it."
    - "A CommitResult that carries no position (the existing seam/test double) still renders today's exact panel copy — no crash, no behaviour change for existing seams."
    - "The CLI's commit reason string is unchanged in wording and content (docs/DEMO.md:178 and the demo-runbook guard stay green)."
    - "The desk package still imports neither triagedesk.store.queue nor triagedesk.mcp.server (the no-self-commit guard stays green)."
  artifacts:
    - path: src/triagedesk/core/schema.py
      provides: "CommitResult.position: int | None = None — the typed queue position on the ONE gated-commit contract (additive; CommitResult keeps no extra=forbid)."
    - path: src/triagedesk/mcp/server.py
      provides: "commit_priority's success return passes position=row.position; the reason string is left byte-identical."
    - path: src/triagedesk/desk/server.py
      provides: "_decision_view names the position when present and falls back to today's exact copy when it is None."
    - path: docs/DESK.md
      provides: "The desk transcript's committed line names the queue position."
    - path: docs/DEMO.md
      provides: "The desk storyboard rows 267-268 match the real filmed beats (two approvals -> positions 1 and 2)."
    - path: docs/DECISIONS.md
      provides: "A D26 row recording WHY the position is a typed field, never parsed from the free-text reason."
  key_links:
    - "CommitResult.position is set only from row.position in mcp/server.py::commit_priority — the desk never reads the free-text reason and never recomputes a position."
    - "desk/server.py::_decision_view reads the position from the typed CommitResult channel (getattr(commit, 'position', None)), never from CommitResult.reason."
    - "docs/DESK.md and docs/DEMO.md quote the same committed-panel copy the desk renders, so the pinned transcript cannot drift from the surface."
---

<objective>
Make the desk's post-decision panel name the queue position the gated write assigned, so the desk demo shows the patient actually landing in the queue instead of only asserting the commit.

Purpose: Today `src/triagedesk/desk/server.py::_decision_view()` hard-codes `Approved by NAME (ROLE) — committed to the queue.` The real queue position exists (the store assigns it, and the CLI reason already carries it in prose) but the panel cannot show it because the typed commit contract drops it. This closes that gap with a typed field — never string-parsing the free-text reason, which the desk module's stated doctrine forbids (it reads typed channels only; see the module docstring and `terminal_kind()`'s explicit avoidance of `Escalation.reason`).

Output: `CommitResult.position` flows from the store row through the MCP tool contract to the desk panel; the panel names the position when present and keeps today's exact copy when it is absent; the pinned transcript docs and the WHY (DECISIONS.md) are updated; a corrected DEMO.md storyboard row replaces an inaccurate gloss.
</objective>

<execution_context>
@/home/brian/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/brian/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/CONVENTIONS.md
@docs/DESK.md
@src/triagedesk/core/schema.py
@src/triagedesk/mcp/server.py
@src/triagedesk/desk/server.py
@tests/test_desk.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: End-to-end "a commit assigns a position and the panel names it"</name>
  <files>src/triagedesk/core/schema.py, src/triagedesk/mcp/server.py, src/triagedesk/desk/server.py, tests/test_desk.py</files>
  <behavior>
    - The ONE committed-panel copy (approve and edit) ends `— committed to the queue at position 1.` when the commit carried position 1.
    - The same copy falls back to today's exact `— committed to the queue.` when the commit carries no position (None).
    - The CLI reason string is untouched (regression: demo-runbook guard).
  </behavior>
  <action>Wire ONE path — a real desk approval — through every layer this change touches, end to end.

In `src/triagedesk/core/schema.py`, add `position: int | None = None` to `CommitResult` (the class at ~line 339), after `reason`. This is additive only: `CommitResult` is deliberately the one contract model that does NOT declare `extra="forbid"` (unlike `ExtractionResult`, `PriorityResult`, `EvidencePassage`/`EvidenceResult`, `HandoverCard`), so a field added with a default still validates every existing constructor and reader. Extend the `CommitResult` docstring to name `position` as the queue position the gated write assigned on a commit (`None` when unknown or refused), so the contract documents its own new field.

In `src/triagedesk/mcp/server.py::commit_priority`, the success `CommitResult(...)` return (currently `committed=True, reason=...` at ~line 310) passes `position=row.position` as well. `row` is the `QueueRow` returned by `commit_to_queue`. Do NOT change the `reason` string on ~line 312 — it is the CLI demo's line and is pinned verbatim by `docs/DEMO.md:178` and `tests/test_demo_runbook.py`; leave it byte-identical.

In `src/triagedesk/desk/server.py::_decision_view` (the committed branch, ~lines 748-756), read the position from the typed channel and append it to BOTH committed copies (the `edit` copy and the `approve` copy): render `… — committed to the queue at position {position}.` when the position is present, and fall back to today's exact copy (no position clause) when it is absent. Read it with `getattr(commit, "position", None)` — the same guarded `getattr` idiom already used one line below for `committed`/`reason`, so a `CommitResult` built without the field (the eval stub in `tests/conftest.py`) still renders. Add NO new import, route, runtime coupling or store access to the desk package: `tests/test_desk.py::test_no_self_commit_path_in_the_desk_package` forbids any `desk/` module from importing `triagedesk.store.queue` or `triagedesk.mcp.server`, and the position is only read off the already-present `commit_result` object.

In `tests/test_desk.py`, update the happy-path assertion at ~line 299 (`test_form_to_card_to_gate_to_commit`) from `"Approved by Nurse Demo (triage nurse) — committed to the queue."` to `"Approved by Nurse Demo (triage nurse) — committed to the queue at position 1."`. That test drives the REAL commit tool through the injected in-memory store seam, whose `next_position()` returns 1 for the first row, so 1 is the assigned position. (The other two `"committed to the queue"` checks at ~lines 394 and 662 contain no trailing period and still match the new copy unchanged — leave them.)</action>
  <verify>
    <automated>uv run pytest tests/test_desk.py -q -k form_to_card_to_gate_to_commit</automated>
  </verify>
  <done>An approval (and an edit) at the desk renders `… — committed to the queue at position 1.`; a `CommitResult` without a position still renders today's exact copy; the CLI reason string and the demo-runbook guard are untouched.</done>
</task>

<task type="auto">
  <name>Task 2: Lock the contract — position present, idempotent per case, and the None fallback</name>
  <files>tests/test_mcp_tools.py, tests/test_commit_idempotent.py, tests/test_desk.py</files>
  <action>Add the assertions that make the typed-position contract and the fallback un-regressable. No source file changes in this task.

In `tests/test_mcp_tools.py::test_commit_priority_commits_once_through_the_injected_store` (~line 128), the test already parses both `CommitResult`s (first and repeat) from the real tool call. Extend it: assert the first parsed result's `position == 1`, and assert the repeat's `position` equals the first's `position` — a repeat of the SAME case keeps the SAME position (supersede-in-place). Reuse the already-parsed `CommitResult.model_validate_json(...)` values rather than re-parsing.

In `tests/test_commit_idempotent.py`, add one contract-level test that an approve followed by an edit of the SAME case (same `case_id` and identical `case` content, so the content-derived key is equal) yields TWO `CommitResult`s whose `position` are equal (both 1 for a fresh injected store) and whose `committed` is `True`, while the injected store holds exactly one row. Drive it through the real owned tool with `Client(server_module.server)` and the `injected_store` seam, exactly as the sibling tests in this file do; the approve uses `colour=...` and the edit uses a token whose `final_colour` differs, so the second write supersedes rather than inserts. Assert on the typed `position` field only — never on the `reason` text.

In `tests/test_desk.py`, add two hermetic render tests beside the existing `render_state(result=..., form_values=...)` usage (~line 1088), so they do not depend on store numbering:
(1) a position-bearing `CommitResult(committed=True, position=3, reason="accepted")` passed as `result={"commit_result": ...}` with `form_values={"decision": "approve", "name": "Nurse Demo", "role": "triage nurse"}` renders `Approved by Nurse Demo (triage nurse) — committed to the queue at position 3.`;
(2) a position-less `CommitResult(committed=True, reason="accepted")` renders today's exact `Approved by Nurse Demo (triage nurse) — committed to the queue.` — the fallback the eval stub and any older checkpoint state rely on.</action>
  <verify>
    <automated>uv run pytest tests/test_mcp_tools.py tests/test_commit_idempotent.py tests/test_desk.py -q</automated>
  </verify>
  <done>The gated commit populates `position`; a repeat and an edit of the same case keep the same position with one row; the position-bearing panel copy and the None fallback are both asserted; the desk test subset is green.</done>
</task>

<task type="auto">
  <name>Task 3: Update the pinned transcripts and record the WHY</name>
  <files>docs/DESK.md, docs/DEMO.md, docs/DECISIONS.md</files>
  <action>Bring the docs the surface pins back in sync with the new copy, and record the design reason (DRY: the docs quote the surface's own string; they never restate the logic).

`docs/DESK.md` line ~59: change the sample line `Approved by NAME (ROLE) — committed to the queue.` to name the position, e.g. `Approved by NAME (ROLE) — committed to the queue at position 1.` (the transcript is illustrative; the runbook guard at `tests/test_desk_runbook.py` pins the colours/target/internal-identifier set, not this copy).

`docs/DEMO.md` desk storyboard:
- Row ~267 (Happy path, E-04): extend the quoted panel copy to `Approved by Nurse A. Demo (triage nurse) — committed to the queue at position 1`.
- Row ~268 (Edge — edit, E-10): the filmed beat submits a DIFFERENT patient (E-10 vs E-04), so it commits a genuinely NEW row. Replace the inaccurate gloss "the row is superseded, not duplicated" and the old copy with the real beat: the quoted copy becomes `Edited to ORANGE by Nurse A. Demo (triage nurse) — committed to the queue at position 2`, and the gloss becomes that two approvals land at positions 1 and 2 (a second patient is a second row). Do NOT change what the demo does — only describe the real beat accurately.

`docs/DECISIONS.md`: append a new row after D25 (the file's current tail) titled `### D26 — The committed queue position is a typed field, never parsed from the reason`. State the decision (the position the gated write assigned is exposed as `CommitResult.position: int | None`; the desk names it when present and falls back to the old copy when absent) and the WHY: the desk module reads typed channels only and never a free-text reason (per the `desk/server.py` module docstring and `terminal_kind()`'s explicit avoidance of `Escalation.reason`), so the panel must not string-parse `CommitResult.reason` even though the CLI's reason happens to carry the position in prose; the field is additive because `CommitResult` is the one contract model without `extra="forbid"`, so every existing reader is unaffected. Do not restate the position copy string or any SATS value here (CONVENTIONS §1) — link the reasoning, not the literal.

Leave `docs/DEMO.md:178` (the CLI `commit : … at queue position 1 …` transcript) untouched — the CLI reason string is unchanged by this task.</action>
  <verify>
    <automated>uv run pytest tests/test_desk_runbook.py tests/test_demo_runbook.py -q</automated>
    <automated>grep -q 'committed to the queue at position 1' docs/DESK.md && grep -q 'committed to the queue at position 2' docs/DEMO.md && grep -q 'D26' docs/DECISIONS.md</automated>
  </verify>
  <done>The desk transcript and the demo storyboard quote the position-bearing copy; the edit beat reads position 2 with an accurate two-row gloss; DECISIONS.md carries the D26 typed-field rationale; the doc guards stay green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| store row → MCP tool contract | `row.position` (an internal integer) becomes a field on the returned `CommitResult`. |
| MCP tool result → desk render | The typed `position` is interpolated into HTML panel copy the nurse reads. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-01 | Information Disclosure | `desk/server.py::_decision_view` panel copy | low | accept | The position is a non-sensitive local queue ordinal already surfaced by the CLI; the panel escapes all copy through `_panel`/`_escaped`; no new input crosses a trust boundary. |
| T-quick-02 | Tampering | `CommitResult.position` additive field | low | accept | The field is producer-set from `row.position` in the gated tool and is read-only in the desk; the desk imports no store/queue or mcp.server module, so it cannot forge a position (`test_no_self_commit_path_in_the_desk_package`). |
| T-quick-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency is added or changed by this task; `pyproject.toml` and `uv.lock` are untouched, so the package-legitimacy gate has nothing new to admit. |
</threat_model>

<verification>
Run the focused subset that covers the touched surface (this repo carries extensive structural/guard tests; the whole suite is not needed):

```
uv run pytest tests/test_desk.py tests/test_mcp_tools.py tests/test_commit_idempotent.py tests/test_desk_runbook.py tests/test_demo_runbook.py -q
```

Plus the doc-content checks from Task 3's second verify.
</verification>

<success_criteria>
- `CommitResult.position` exists (additive, default `None`); `mcp/server.py::commit_priority` sets it from `row.position`; the `reason` string is byte-identical.
- The desk panel names the position when present and renders today's exact copy when it is `None`.
- A repeat and an edit of the same case keep the same position and one queue row.
- The desk package imports no `triagedesk.store.queue` and no `triagedesk.mcp.server`.
- `docs/DESK.md`, `docs/DEMO.md` (rows 267-268) and `docs/DECISIONS.md` (D26) reflect the change; the doc guards pass.
- The focused pytest subset is green.
</success_criteria>

<output>
Create `.planning/quick/261013-sbd-desk-panel-shows-the-queue-position-the-/261013-sbd-SUMMARY.md` when done
</output>
