---
phase: quick-261116-h0z
plan: 01
subsystem: docs
tags: [skill, mcp, json, handover, contract, sats, dr-y]

requires: []
provides:
  - "the canonical machine-readable handover: references/output-contract.md (envelope, closed sets, invariants, examples)"
  - "SKILL.md requires exactly one fenced json handover block per triage turn"
  - "six contract tests that make the handover drift-proof"
affects: [triagedesk-triage-skill, docs/MCP.md, eval-harness, desk-integration]

actuals:
  tokens: 5168
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Contract-as-reference: one Markdown reference owns the literals; SKILL.md links and restates only what an operator can get wrong"
    - "Independent-expectation tests: the closed sets live in the test module as the assertion, never as a second runtime source"

key-files:
  created:
    - src/triagedesk/skills/triagedesk-triage/references/output-contract.md
  modified:
    - src/triagedesk/skills/triagedesk-triage/SKILL.md
    - tests/test_triage_skill.py
    - docs/MCP.md

key-decisions:
  - "The handover block is declared a projection, never the authority: the hash-chained audit record and the committed queue row win on any disagreement."
  - "queue.committed is true only after commit_priority returned committed: true, and it carries that returned position — never an intended one."
  - "One reference owns the envelope, closed sets, invariants, mapping and examples; SKILL.md links it and restates only the four operator-facing invariants."
  - "The new reference ships with no installer change because _skill_files already walks references/ recursively."

patterns-established:
  - "A machine-readable contract reference is validated by parsing its own fenced examples and asserting them against closed sets held in the test module."

requirements-completed: []

coverage:
  - id: D1
    description: "The canonical JSON handover contract reference with eleven envelope fields, six closed sets, six invariants, the status mapping and three valid examples"
    verification:
      - kind: unit
        ref: "tests/test_triage_skill.py::test_the_output_contract_names_every_closed_set_value"
        status: pass
      - kind: unit
        ref: "tests/test_triage_skill.py::test_handover_examples_obey_the_invariants"
        status: pass
    human_judgment: false
  - id: D2
    description: "SKILL.md requires one handover block per turn and links the contract without restating its tables"
    verification:
      - kind: unit
        ref: "tests/test_triage_skill.py::test_the_skill_requires_one_handover_block"
        status: pass
    human_judgment: false
  - id: D3
    description: "The reference installs with the skill and is named in docs/MCP.md"
    verification:
      - kind: unit
        ref: "tests/test_triage_skill.py::test_the_package_can_install_the_skill"
        status: pass
    human_judgment: false
  - id: D4
    description: "No SATS threshold, band or colour rule is restated outside data/*.yaml"
    verification:
      - kind: unit
        ref: "tests/test_triage_skill.py::test_the_output_contract_restates_no_sats_band"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-11-16
status: complete
---

# Quick task 261116-h0z: canonical structured JSON handover — Summary

**The triage skill now specifies a single `triagedesk.handover/1` JSON block per turn, backed by one
contract reference (eleven fields, six closed sets, six invariants, three valid examples) and six
tests that fail if it claims a commit, a colour or an audit fact it does not have.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-11-16T09:20:20Z
- **Completed:** 2026-11-16T09:24:54Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `references/output-contract.md` ships as package data: the handover envelope (eleven top-level
  fields), the six closed sets, the six hard invariants, the `status` → `next_action` mapping and
  three worked examples (`awaiting_clinician`, `clarify`, `deferred`) that obey every invariant.
- The block is explicitly a **projection**: the hash-chained audit record and the committed queue row
  remain authoritative, `audit` never carries a hash/chain position/record id, and a consumer
  reconciles before acting.
- `SKILL.md` gains non-negotiable 9, workflow step 8 ("Emit the handover"), a four-bullet
  `## Structured output` section and a reference bullet — 35 added lines, no table restated.
- Six new tests hold the contract: verbatim requirement phrase, every closed-set value named, every
  example parses and stays closed, every invariant holds, no SATS band restated, and the reference
  installs with the skill. `docs/MCP.md` names it in one bullet.
- The approval-token test is untouched and still scoped to `tool-contracts.md`; the frontmatter,
  nine-tool list, fail-closed vocabulary and `data/*.yaml` pointer are byte-identical.

## Task Commits

1. **Task 1: Write `references/output-contract.md`** — `8f9e79c` (docs)
2. **Task 2: Require the handover block in SKILL.md** — `1768594` (docs)
3. **Task 2 follow-up: keep the asserted phrase unbroken** — `54064db` (docs)
4. **Task 3: lock the contract with tests and name it in docs/MCP.md** — `35a66b9` (test)

Measured from the plan ledger `4a24c8f..35a66b9`: **4 commits**, 365 insertions, 0 deletions.

## Files Created/Modified

- `src/triagedesk/skills/triagedesk-triage/references/output-contract.md` — the canonical handover
  contract: envelope table, closed sets, hard invariants, status mapping, three examples, consumer note.
- `src/triagedesk/skills/triagedesk-triage/SKILL.md` — non-negotiable 9, workflow step 8, the short
  `## Structured output` section, and the reference bullet.
- `tests/test_triage_skill.py` — `OUTPUT_CONTRACT_FILE`, `HANDOVER_SCHEMA`, `CLOSED_SETS`,
  `DELIVERED_STATUSES`, `STATUS_NEXT_ACTION`, `_contract()`/`_handover_examples()`/`_at()` helpers,
  five new tests and one installer assertion (six new assertions total).
- `docs/MCP.md` § "The installed skill" — one bullet naming the handover block.

## Decisions Made

- **Projection, not authority.** The contract says a consumer must reconcile against the audit trail
  and that the queue row wins on disagreement. Without that sentence the block would read as a second
  record of truth (DRY violation at the semantic layer).
- **`audit` carries tool names only.** Stating explicitly that no hash, chain position or record id is
  emitted is what stops a harness inventing one; the test asserts the key set.
- **Closed-set literals live in the test module.** Same pattern as the existing fail-closed-vocabulary
  test: the test is the independent expectation, not a second runtime source, so DRY holds.
- **Every example names only the tools actually reached.** `clarify`/`deferred` omit
  `retrieve_evidence` where the turn never got there, and both carry `priority.colour: null`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The required phrase could not be asserted verbatim as first wrapped**
- **Found during:** Task 2 verification
- **Issue:** Non-negotiable 9 initially wrapped the phrase across a line break, so
  `"exactly one fenced \`json\` handover block"` was not contiguous in `SKILL.md` and the plan's own
  verify assertion (mirrored by the new test) would fail.
- **Fix:** Re-wrapped item 9 so the phrase sits on one line.
- **Files modified:** `src/triagedesk/skills/triagedesk-triage/SKILL.md`
- **Verification:** `test_the_skill_requires_one_handover_block` passes.
- **Committed in:** `54064db`

---

**Total deviations:** 1 auto-fixed (Rule 1).
**Impact on plan:** No scope change — the fix only satisfies the plan's stated verbatim requirement.

## Issues Encountered

- `uv run pytest -q` reports **972 passed, 1 failed**: `tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root`
  fails because a `spans.jsonl` exists at the repo root. That file is gitignored, was written at
  09:19:22Z (one minute **before** this plan started) and is being produced by a live
  `triagedesk triage --online` process from another session (PID 201705) still running in this
  checkout. It is unrelated to this plan — which touches no runtime code — and was left alone rather
  than deleted out from under the concurrent session. The full suite is green with that single
  environmental test deselected: **972 passed, 1 deselected**.

## Known Stubs

None.

## Threat Flags

None — this change adds documentation and tests only; no network endpoint, auth path, file access
pattern or schema at a trust boundary changed.

## User Setup Required

None.

## Verification

```bash
uv run pytest tests/test_triage_skill.py -q          # 16 passed
uv run pytest tests/test_triage_skill.py tests/test_install_mcp.py -q  # 42 passed
uv run pytest -q --deselect tests/test_observability.py::test_no_spans_artifact_is_written_to_the_repo_root  # 972 passed
uv run ruff check tests/test_triage_skill.py        # All checks passed
```

Manual spot-check of the invariant the task exists for: the `clarify` example carries
`priority.colour: null`, `queue.committed: false`, `gate.state: "not_reached"` and
`next_action: "ask_clarification"`.

## Self-Check: PASSED
