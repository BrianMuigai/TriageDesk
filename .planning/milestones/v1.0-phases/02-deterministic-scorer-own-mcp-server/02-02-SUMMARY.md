---
phase: 02-deterministic-scorer-own-mcp-server
plan: 02
subsystem: core
tags: [python, pydantic, mcp, sats, discriminators, deterministic-matcher, override, injection-resistance]

# Dependency graph
requires:
  - phase: 02-deterministic-scorer-own-mcp-server
    provides: "core/scorer.py score_priority (TEWS colour + citations), PriorityResult/TriggeredRule contracts, mcp/server.py tool seam"
provides:
  - "core/matcher.py — the pure, boundary-respecting alias lookup with an explicit no_match (D-05/D-06)"
  - "MatchResult contract in the one schema module (D-09)"
  - "most-urgent-wins discriminator override in core/scorer.py (SCORE-02)"
  - "mcp/server.py exposes match_discriminators as a thin owned tool (TOOL-02)"
  - "tests/test_matcher.py + test_scorer_override.py + test_matcher_determinism.py — the matching/override/determinism proof suite"
affects: [02-03, phase-3, phase-4]

# Actuals (#2632) — pairs with the plan's estimate (tokens: 48000, raw_tokens: 33000).
# Same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 6446        # chars/4 over the realized diff (25784 chars, src + tests)
  raw_tokens: 6446    # same — nothing generated in this plan
  tasks: 3
  commits: 3
  plan_head_before: 19ad0dc31531ce4cc36102e097951ac2ab42fbd8
  plan_head_after: 61dc6350a6309fe5d83d1cb5b18f8659bcce36fb

tech-stack:
  added: []
  patterns:
    - "Boundary-respecting alias match: tokenise complaint + alias with one regex, match a contiguous token sequence (never a raw substring)"
    - "Closed-set guarantee: matcher ids come only from data/sats_discriminators.yaml; unmatched -> explicit no_match with the declared warning"
    - "Data-derived urgency order: a colour's urgency rank is its lower TEWS bound in data/sats_tews.yaml (no colour token inlined)"
    - "Most-urgent-wins override raises colour/target/destination to the winning category; a lower-urgency match never lowers a colour"

key-files:
  created:
    - src/triagedesk/core/matcher.py
    - tests/test_matcher.py
    - tests/test_scorer_override.py
    - tests/test_matcher_determinism.py
  modified:
    - src/triagedesk/core/schema.py
    - src/triagedesk/core/scorer.py
    - src/triagedesk/mcp/server.py

key-decisions:
  - "Alias matching is token-boundary based, not substring: a short alias never fires inside an unrelated word (hypothermia !-> hypo; sobbing !-> sob) (SAFE-01, D-05)."
  - "The matcher is a pure function over the one loader with no model and no fuzzy judgement; an unmatched complaint returns the declared no_match warning, never a guessed id (D-06, T-02-07)."
  - "The override's urgency order is data-derived from the TEWS colour bands' lower bounds, so no colour token is hard-coded in core/ (CONVENTIONS §1, T-02-08)."
  - "Unknown matched ids are ignored by the scorer, so a caller can never inject a category or a colour (T-02-08)."
  - "The firing category is recorded as one TriggeredRule (points 0 — it reclassifies via colour, not TEWS points) so citations == triggered_rules holds after the override."

patterns-established:
  - "Determinism is enforced, not assumed: the same input is scored five times and the matched set/colour/citation set must be identical"
  - "Injection resistance is proven by construction: complaint prose is never read by the scorer; only vitals + closed-set ids drive the colour"

requirements-completed: [SCORE-02, SAFE-01, TOOL-02]

coverage:
  - id: D1
    description: "A free-text complaint is matched to discriminator ids by a deterministic alias lookup with an explicit no_match outcome."
    requirement: "TOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_matcher.py#test_known_alias_phrase_returns_its_id + test_unmatched_complaint_returns_the_declared_no_match"
        status: pass
      - kind: unit
        ref: "tests/test_matcher.py#test_owned_server_exposes_the_match_discriminators_tool"
        status: pass
    human_judgment: false
  - id: D2
    description: "Short aliases match only on word boundaries: unrelated words (hypothermia/sobbing) never fire the hypo/sob aliases."
    requirement: "SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_matcher.py#test_short_alias_does_not_fire_inside_an_unrelated_word"
        status: pass
    human_judgment: false
  - id: D3
    description: "The final colour is the more urgent of the TEWS colour and the most-urgent matched discriminator category, with that category's target time."
    requirement: "SCORE-02"
    verification:
      - kind: unit
        ref: "tests/test_scorer_override.py#test_a_more_urgent_discriminator_overrides_low_vitals + test_most_urgent_category_wins_independent_of_input_order"
        status: pass
      - kind: unit
        ref: "tests/test_scorer_override.py#test_a_lower_urgency_discriminator_cannot_lower_a_higher_colour"
        status: pass
    human_judgment: false
  - id: D4
    description: "Injected or omitted complaint text cannot change the colour; the colour is never read from the complaint."
    requirement: "SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_matcher_determinism.py#test_injected_instructions_do_not_change_the_colour + test_complaint_text_never_enters_the_score + test_omitting_the_only_match_reverts_to_the_tews_colour"
        status: pass
    human_judgment: false
  - id: D5
    description: "The matched discriminator set, colour and citations are identical across repeated runs for identical input."
    requirement: "SCORE-02"
    verification:
      - kind: unit
        ref: "tests/test_matcher_determinism.py#test_repeated_identical_input_is_identical"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-09
status: complete
---

# Phase 2 Plan 02: Deterministic Alias Matcher & Most-Urgent-Wins Override Summary

**A pure boundary-respecting alias lookup turns a complaint into closed-set discriminator ids (or an explicit `no_match`), and the scorer raises the colour to the most-urgent matched category with its cited target time — so injected or omitted complaint text can never move the colour.**

## Performance

- **Duration:** ~6 min (14:52:36Z → 14:59:01Z)
- **Started:** 2026-10-09T14:52:36Z
- **Completed:** 2026-10-09T14:59:01Z
- **Tasks:** 3/3
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments

- **Discriminator matching is now a deterministic data lookup (D-05/D-06, SAFE-01).** `core/matcher.py` tokenises the complaint and each alias with one shared regex and matches a *contiguous token sequence* — never a raw substring — so `"hypothermia"` cannot fire `hypo` and `"sobbing"` cannot fire `sob`. Unmatched input returns the declared `no_match` warning; the matcher never guesses an id.
- **The closed set is structural.** Returned ids are drawn only from `data/sats_discriminators.yaml`; a test asserts every id is a member of that set (D-06, T-02-07).
- **Most-urgent-wins override (SCORE-02).** `score_priority` now looks up each matched id's category, derives urgency from the TEWS colour bands' lower bounds (no colour token inlined), and raises `colour`/`target`/`destination` to the winning category when it is more urgent than the TEWS colour. A lower-urgency match cannot lower a higher colour; the result is independent of input order (T-02-08).
- **Citations still equal triggered rules.** The firing category is recorded as one `TriggeredRule` carrying its `citation_ref` through the one citation helper, so `citations == triggered_rules` holds after the override.
- **Injection and omission are proven inert (SAFE-01).** The scorer reads no complaint prose — only typed vitals and closed-set ids — so injected instructions cannot raise the colour and dropping the only match simply reverts to the TEWS colour.
- **The owned server exposes `match_discriminators`** as a thin, contract-typed tool (TOOL-02), verified over the in-memory MCP client.

## Task Commits

Each task was committed atomically:

1. **Task 1: Deterministic alias matcher and the match_discriminators tool** - `84f4386` (feat)
2. **Task 2: Most-urgent-wins discriminator override in the scorer** - `8b698d9` (feat)
3. **Task 3: Determinism and injection-resistance tests for matching** - `61dc635` (test)

**Plan metadata:** committed together with this SUMMARY and STATE.md (docs: complete plan)

## Files Created/Modified

- `src/triagedesk/core/matcher.py` — the pure `match_discriminators` (shared token pattern, contiguous-sequence match, sorted closed-set ids, explicit no_match)
- `src/triagedesk/core/schema.py` — added the `MatchResult` contract (`matched_ids`, `no_match`, `warning`)
- `src/triagedesk/core/scorer.py` — `_colour_urgency` (data-derived), `_most_urgent_category`, and the override applied after the TEWS colour
- `src/triagedesk/mcp/server.py` — added the `match_discriminators` tool (thin adapter over the pure function)
- `tests/test_matcher.py` — known aliases, case/whitespace insensitivity, false-positive collision, explicit no_match, closed-set membership, stable ordering, tool contract
- `tests/test_scorer_override.py` — override, order-independence, no-downgrade, empty set, cited override rule
- `tests/test_matcher_determinism.py` — repeated-input determinism, injection, complaint-prose isolation, omission

## Decisions Made

- **Boundary matching, not substring.** One regex tokenises both sides, so a match is always an adjacent token sequence — this is the mechanism that closes Pitfall 3/7 substring leakage.
- **Urgency is read from data.** A colour's urgency rank is its lower TEWS bound in `data/sats_tews.yaml`; the override never names `RED`/`ORANGE`/`YELLOW`, so the DRY guard stays green (CONVENTIONS §1).
- **Unknown ids are ignored, never trusted.** A caller cannot smuggle a category or colour through `matched_discriminator_ids` (T-02-08).
- **The override rule carries points 0.** It reclassifies via the category colour rather than contributing TEWS points, keeping the TEWS total and the citation invariant intact.

## Deviations from Plan

None - plan executed exactly as written. (Three line-length lint fixes were applied to the new test files during Task 3; these are formatting only, not deviations.)

## Issues Encountered

None. The pre-existing ruff findings in `scripts/spike_model.py` and `src/triagedesk/llm/prompts.py`, and the pre-existing mypy findings in `core/rules.py` (missing `types-PyYAML`) and `mcp/adapter.py`, are outside this plan's scope and were left untouched.

## User Setup Required

None - no external service configuration required. (No package installs occurred; the reserved package-legitimacy gate stays in force for any future install.)

## Next Phase Readiness

- **For Plan 02-03 (remaining owned tools):** the pattern is unchanged — a thin `@server.tool()` adapter over a pure `core/` function, contract-typed to the shared schema. The server now exposes `normalize_case`, `score_priority`, and `match_discriminators`; `raise_recheck_flag` and the gated `commit_priority` stub remain.
- **For Phase 3 (graph wiring):** `match_discriminators` returns closed-set ids and an explicit no_match, so the graph can route a coverage gap deterministically; `score_priority` consumes those ids to apply the override without reading complaint prose.
- **For Phase 4 (evaluation):** the matcher's determinism and injection-resistance tests are the E-13-direction evidence the evaluation will build on; "feeling unwell" remains deliberately unmatched (E-09 stays the declared coverage gap).

---

*Phase: 02-deterministic-scorer-own-mcp-server*
*Completed: 2026-10-09*

## Self-Check: PASSED

- All 7 key files exist on disk (matcher, schema, scorer, server, 3 test files).
- All 3 plan commits are ancestors of HEAD: `84f4386`, `8b698d9`, `61dc635`.
- Full suite green: `uv run pytest -q` → 101 passed; `uv run python scripts/spike_score.py` → exit 0.
- Guards green: `tests/test_purity.py`, `tests/test_no_duplicated_sats.py` pass (matcher is pure; no SATS value inlined under `src/`).
