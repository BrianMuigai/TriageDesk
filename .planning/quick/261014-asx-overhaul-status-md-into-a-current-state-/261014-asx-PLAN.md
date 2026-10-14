---
phase: quick
plan: "261014-asx"
type: execute
wave: 1
depends_on: []
files_modified:
  - STATUS.md
  - docs/DECISIONS.md
  - docs/REQUIREMENTS.md
autonomous: true
requirements: [QUICK-261014]
estimate:
  tokens: 34000
  raw_tokens: 21000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "STATUS.md reads as a CURRENT-state gap analysis: the resolved entries (G3/G4/G6/G7) are gone with no record, the §8 done-lists and the whole 'UX (done in Phases 8–12)' block are removed, the header 'Since the v1.1 close' changelog block is deleted, and §7 carries no 'Landed in v1.1' history paragraph."
    - "No estimate moved: §0's `~79–94`, §1's `6/6`, §2's `4/5` and every §3 `Pts`/`Est.` cell are byte-identical to the pre-overhaul revision (`d535ba0:STATUS.md`)."
    - "The §5 ranked list contains exactly the five open gaps G1, G2, G5, G8, G9 — the G-IDs stay stable, the list ordinals renumber 1–5, and no removed ID (G3/G4/G6/G7) appears anywhere in STATUS.md."
    - "§3's 'Why not full' cells cite only live caps (G1, G2, U1, U3, G5); no resolved ID remains, and the ranges are untouched."
    - "§6 keeps U1–U5 and the strengths (incl. the queue-position-on-commit feedback) with the stale 're-scoped after Phase 10' framing dropped; §8 keeps only open actions."
    - "Every cross-reference to a removed STATUS gap ID is gone from docs/DECISIONS.md and docs/REQUIREMENTS.md — including the SB-3 row's `G3 resolved` tag (its referent is STATUS G3, which Task 1 removes); the surviving G1/G2 references (DECISIONS.md:300, DEMO.md:8) and REQUIREMENTS' own hyphenated G-3/G-8/G-10 are intact."
    - "tests/test_docs_final.py stays green and only STATUS.md, docs/DECISIONS.md and docs/REQUIREMENTS.md change (the pre-existing unrelated docs/assets/architecture.pdf working-tree edit is left alone)."
  artifacts:
    - path: STATUS.md
      provides: "The honest self-assessment rewritten as a current gap analysis — resolved entries removed with no record, done-lists and the header changelog block dropped, §3 reasons cleaned to live caps, §5 reduced to the five open gaps, and every score estimate held byte-identical."
    - path: docs/DECISIONS.md
      provides: "D22's 'Why' sentence no longer names the removed STATUS G7 identifier — the read-path rationale is preserved."
    - path: docs/REQUIREMENTS.md
      provides: "SB-3's `G3 resolved` tag is dropped and SB-8, SW-3, ST-1 and the traceability row no longer cite the removed G3/G4/G6 IDs or the wrong U1–U7 range; the range now names the surviving open set."
  key_links:
    - "STATUS §5's open set ↔ docs/REQUIREMENTS.md traceability row (~line 134): the row must name the same surviving IDs (G1/G2/G5/G8/G9) and UX U1–U5 — no second source of the gap set."
    - "STATUS §5's G1/G2 ↔ docs/DECISIONS.md (~line 300) and docs/DEMO.md (~line 8): those G1/G2 references survive untouched and must stay consistent with STATUS."
    - "STATUS.md keeps linking EVALS.md/ARCHITECTURE.md for figures rather than copying them in (DRY); the overhaul adds no new figure."
---

<objective>
Overhaul `STATUS.md` into a **current-state gap analysis** — what is true now and what to do next — instead of a ledger of what was done, then repair the cross-references the removals orphan.

The doc has drifted into a changelog: a "Since the v1.1 close" block above the verdict, three "resolved" entries sitting in the §5 gap list, a done-list and a "UX (done in Phases 8–12)" block in §8, a history paragraph in §7, stale "re-scoped after Phase 10" framing in §6, and §3 "Why not full" cells that cite resolved gap IDs as if they were live caps.

Purpose: the doc's whole value is that it is an honest, current assessment ("a gap analysis, not a victory lap"). Resolved items and done-lists make it read as history, not assessment, and the resolved-ID citations in §3 falsely imply those caps still hold. Removing them keeps the assessment truthful.

**Two locked decisions (do not revisit):**
1. **Resolved items are removed ENTIRELY — no record.** The history already lives in `EVALS.md`, `docs/DECISIONS.md` and the milestone audit; STATUS does not carry it.
2. **The numeric self-scores DO NOT MOVE.** §0's `~79–94`, §1's `6/6`, §2's `4/5` and every §3 `Pts`/`Est.` cell stay byte-identical; only the *reasons* get cleaned to name LIVE caps. Inflating a number would defeat the doc's stated purpose.

**The only new factual content permitted** is the demo-content nuance (§2/§5): the brief wants ONE video under 3 min *with the tool calls on screen*; the 33 s terminal run (`docs/assets/triagedesk-demo.mp4`) has the tool calls but is thin, while the 2:55 captioned desk walkthrough (`docs/assets/desk-demo.mp4`) has the length and narration but **no tool calls** — so neither is a complete candidate, and neither is uploaded. Both properties are measured (`ffprobe`: 32.88 s and 175.03 s) and both recordings are already described in the repo.

Output: a `STATUS.md` that reads as a current assessment, plus six cross-reference lines fixed in `docs/DECISIONS.md` and `docs/REQUIREMENTS.md` so the docs do not contradict each other.

### HARD CONSTRAINTS (do NOT violate)
- **No estimate moves.** §0's `~79–94`/`6/6`/`4/5`, §1's `6/6`, §2's `4/5`, and every §3 `Pts`/`Est.` cell are byte-identical before and after.
- **No new claim** that is not already true and checkable in the repo. The only new factual content is the demo-content nuance above.
- **Do not touch** `README.md`, `EVALS.md`, `ARCHITECTURE.md`, `DESCRIPTION.md`, `docs/DESK.md`, any source file or any test file. The six cross-reference lines below are the ONLY changes outside `STATUS.md`.
- **Link, don't restate** (DRY): keep pointing at `EVALS.md`/`ARCHITECTURE.md` for figures.
- Keep the doc's terse, evidence-linked voice. It should read as a current assessment, not a changelog.
- `tests/test_docs_final.py` guards `README.md`/`ARCHITECTURE.md`/`DESCRIPTION.md`/`EVALS.md` and must stay green.
- A pre-existing, unrelated working-tree edit to an asset file under `docs/assets/` (not a `.md`) is present before this task and must be left untouched.
</objective>

<execution_context>
@/home/brian/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/brian/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md
@docs/CONVENTIONS.md
@STATUS.md
@docs/REQUIREMENTS.md
@docs/DECISIONS.md
@docs/DEMO.md
@tests/test_docs_final.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Overhaul STATUS.md into a current-state gap analysis (header, §0–§9)</name>
  <files>STATUS.md</files>
  <action>Rewrite `STATUS.md` in place so it reads as a current gap analysis. Read the whole file first; use scoped edits. Preserve every FIGURE byte-identical (§0's `~79–94`, §1's `6/6`, §2's `4/5`, and every §3 `Pts`/`Est.` cell), the terse evidence-linked voice, and the `EVALS.md`/`ARCHITECTURE.md` links. Introduce no new `N/M` fraction token anywhere. Make exactly these changes:

1. **Header.** Keep the refresh marker `Refreshed 2026-10-14 (post-v1.1 desk hardening)` and the brief link plus the "Snapshot" paragraph. DELETE the entire blockquote beginning `> **Since the v1.1 close (2026-10-14) — evidence and engineering hygiene…` through its final sentence (the changelog block). Absorb its facts where they belong: the queue-position payoff (the post-decision panel names the queue position the gated write assigned) and the captioned 2:55 desk walkthrough → §2's demo row and §6's strengths; the desk SRP split (`server.py` 1169 → 375 lines across nine modules) and the single-seam de-duplication → §3's Open-source rigour row as hygiene evidence; `463 passed` → §9. Do not restate those facts as a stacked block.

2. **§0 Verdict.** Keep the five-row dimension table with the SAME statuses and its `G8`/`G9` references. Tighten the prose so it names the two live caps: the demo video is recorded but **not uploaded** (the one hard submission gap) and there is **no clinician interview** (the partially-met 20-point criterion). Keep `~79–94`, `6/6` and `4/5` unchanged.

3. **§1 "What to build" — 6/6.** Keep the whole section and its `6/6`; it is requirement evidence, not a gap. Drop only a dangling removed-gap parenthetical if one is present (there is none — keep `MCP-01` and `G8` as they are).

4. **§2 "What to submit" — keep `4/5`.** README row: drop the trailing `G3 resolved` tag, keep `uv run triagedesk demo`. Demo-video row: rewrite so it tells the truth about the brief — the brief wants ONE video under 3 min *with the tool calls on screen*; the 33 s terminal run (`docs/assets/triagedesk-demo.mp4`) has the tool calls but is thin; the 2:55 captioned desk walkthrough (`docs/assets/desk-demo.mp4`) has the length and narration but NO tool calls — so neither is a complete candidate, and neither is uploaded (G1). Keep the ❌. EVALS row: drop the dangling `(G4)` tag, keep `16 cases; E-09 declared`. Leave the other two rows unchanged.

5. **§3 Judging criteria — RANGES BYTE-IDENTICAL** (every `Pts` and `Est.` cell, including `~79–94`). Clean each `Why not full` cell to LIVE caps only (G1, G2, U1, U3, G5); remove every resolved ID:
   - Agentic-depth row (`27–30`): drop `(G7 resolved)`; keep "Strong. Borrowed-server read paths now exercised".
   - Open-source-rigour row (`18–20`): drop `(G3 resolved)`; add the hygiene evidence — the desk module is SRP-split and the store seam de-duplicated.
   - Fit-to-desk row (`9–14`): keep `(G2)`, `(U1)`, `(U3)` and the existing UX-evidence note (the captioned walkthrough and the queue-position-on-commit payoff, cross-referenced to §6).
   - Evaluation-and-reliability row (`13–15`): drop the `(G4)` tag; keep the facts (2 recorded gate failures + 1 declared deferral + 3 coverage deferrals).
   - Defensibility row (`9–10`): unchanged.
   - Demo row (`3–5`): keep `(G1/G5)`; fold in the content truth (neither recording is a complete candidate — the 33 s has the tool calls but is thin, the 2:55 has the length but no tool calls).

6. **§4 Instant disqualifiers.** Keep unchanged.

7. **§5 Gaps & misses (ranked) — open gaps only.** Keep G1, G2, G5, G8, G9; REMOVE the G3, G4, G6 and G7 entries entirely (no record — the history lives in `EVALS.md`/`docs/DECISIONS.md`/the milestone audit). The G-IDs must stay stable; renumber the list ordinals 1–5. Fold the demo-content truth into G5 so it covers BOTH length and content (the 33 s run has the tool calls but is thin; the 2:55 walkthrough has length + narration but no tool calls; neither is a complete candidate; state plainly that G5 is not closed). The human remnant of the live-review gap — "perform the live review on the day" — is still open but belongs in §8 as an action, not here.

8. **§6 UX considerations.** Keep the section and U1–U5 (all live). Drop the stale `— re-scoped after Phase 10` framing from the "UX gaps (ranked)" heading. Keep the strengths, including the queue-position-on-commit feedback (the post-decision panel names the queue position the gated write assigned).

9. **§7 SOTA gap analysis.** DELETE the `**Landed in v1.1 (Phases 6–10):** …` history paragraph. Keep the pillar table, the "Still open" list, and "What we correctly chose not to have".

10. **§8 Action list — open actions only.** REMOVE every done item (the `E-07 and E-04 fixed (Phase 11)` line and the `README one command — done` line) and the entire `**UX (done in Phases 8–12):**` block. Keep: upload the video (G1); one clinician review + a quote (G2); the live-review rehearsal AND performing it on the day (the human remnant moved out of §5); a single <3 min video that carries the tool calls (G5); UX remaining (U4, U5, approver authentication); the optional frontier-model comparison on synthetic data.

11. **§9 Bottom line.** Make it current: build done; `463 passed`; the post-v1.1 hardening (the SRP split and the queue-position panel); submission one step short (the upload); score ceiling unchanged; SOTA standing. Keep the score-ceiling substance (fit-to-desk capped by no clinician review + a prototype desk surface; demo capped by short + unhosted). Raise no estimate.

Do not touch any other file.</action>
  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && git show d535ba0:STATUS.md | grep -oE '\*\*(27–30|18–20|9–14|13–15|9–10|3–5)\*\*|~79–94|[0-9]+/[0-9]+|\| [0-9]+ \| \*\*[0-9]+–[0-9]+\*\* \|' | sort > /tmp/est_before.txt && grep -oE '\*\*(27–30|18–20|9–14|13–15|9–10|3–5)\*\*|~79–94|[0-9]+/[0-9]+|\| [0-9]+ \| \*\*[0-9]+–[0-9]+\*\* \|' STATUS.md | sort > /tmp/est_after.txt && test "$(wc -l < /tmp/est_after.txt)" -eq 11 && diff /tmp/est_before.txt /tmp/est_after.txt && [ "$(grep -oE '\bG[0-9]+\b' STATUS.md | sort -u | tr '\n' ' ')" = "G1 G2 G5 G8 G9 " ] && [ "$(grep -oE '\bU[0-9]+\b' STATUS.md | sort -u | tr '\n' ' ')" = "U1 U2 U3 U4 U5 " ] && [ "$(grep -cE '^[0-9]+\. \*\*G[0-9]' STATUS.md)" -eq 5 ] && [ "$(git diff --name-only -- STATUS.md docs/DECISIONS.md docs/REQUIREMENTS.md docs/DEMO.md | sort | tr '\n' ' ')" = "STATUS.md " ] && uv run pytest tests/test_docs_final.py -q</automated>
  </verify>
  <done>STATUS.md carries the 2026-10-14 marker with the "Since the v1.1 close" changelog block deleted and its facts absorbed into §2/§3/§6/§9; §0 names the two live caps and keeps its five-row table; §1 keeps `6/6`; §2's demo row states the tool-calls/content truth for both recordings and keeps the ❌; §3's ranges are byte-identical with every `Why not full` cell naming only G1/G2/U1/U3/G5; §5 lists exactly G1/G2/G5/G8/G9 as ordinals 1–5 with the demo-content truth folded into G5; §6 keeps U1–U5 + strengths and drops the stale framing; §7 has no history paragraph; §8 has only open actions; §9 is current and raises no estimate. The estimate token set is byte-identical to `d535ba0:STATUS.md`, STATUS.md contains only G1/G2/G5/G8/G9 and U1–U5, the ranked list has five entries, and only STATUS.md changed among `.md` files.</done>
</task>

<task type="auto">
  <name>Task 2: Fix the dangling cross-references in docs/DECISIONS.md and docs/REQUIREMENTS.md</name>
  <files>docs/DECISIONS.md, docs/REQUIREMENTS.md</files>
  <action>Removing the STATUS G3/G4/G6/G7 entries orphans six references in other docs. Fix each so the sentence's MEANING is preserved and only the dangling identifier is dropped — do not delete surrounding substance and do not invent a new ID. Touch ONLY these lines:

1. `docs/REQUIREMENTS.md` SB-3 row (~line 68): drop the trailing `— G3 resolved` tag, leaving `✅ one command`. The referent is STATUS G3 (which Task 1 removes) — git history shows this cell previously read `🟡 two commands — STATUS G3`, so it is a STATUS reference, not REQUIREMENTS' own gap. REQUIREMENTS' own hyphenated `G-3` ("Host Python is 3.14") is a different token and stays untouched.
2. `docs/REQUIREMENTS.md` SB-8 row (~line 73): change `(counts reconciled — G4/STATUS)` to `(counts reconciled)`.
3. `docs/REQUIREMENTS.md` SW-3 row (~line 118): change `(key breadth — STATUS G4/integration)` to `(key breadth — integration-verified)`.
4. `docs/REQUIREMENTS.md` ST-1 row (~line 127): change `rehearsed — STATUS G6 resolved` to `rehearsed`.
5. `docs/REQUIREMENTS.md` traceability row (~line 134): change `honest gap analysis (G1–G9, UX U1–U7, SOTA gaps)` to `honest gap analysis (open gaps G1/G2/G5/G8/G9, UX U1–U5, SOTA gaps)` — the range is corrected to the surviving open IDs and the UX range to U1–U5.
6. `docs/DECISIONS.md` (the D22 "Why" sentence, ~line 220): replace the parenthetical `(the Phase-1 STATUS G7 gap)` with `(the Phase-1 borrowed-read-path gap)` — same meaning, no removed ID.

Do NOT touch `docs/REQUIREMENTS.md`'s own hyphenated `G-1…G-11` table (those `G-N` tokens never match the bare `\bG[0-9]+\b` gate), `docs/DEMO.md` line ~8 or `docs/DECISIONS.md` line ~300 (those `G1`/`G2` references survive). No other file changes.</action>
  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && grep -q 'borrowed-read-path gap' docs/DECISIONS.md && grep -q 'counts reconciled' docs/REQUIREMENTS.md && grep -q 'key breadth — integration-verified' docs/REQUIREMENTS.md && grep -q '✅ rehearsed' docs/REQUIREMENTS.md && grep -q 'open gaps G1/G2/G5/G8/G9, UX U1–U5' docs/REQUIREMENTS.md && grep -q '✅ one command |' docs/REQUIREMENTS.md && [ "$(grep -oE '\bG[0-9]+\b' docs/DECISIONS.md | sort -u | tr '\n' ' ')" = "G1 G2 " ] && [ "$(grep -rhoE '\bG[0-9]+\b' --include='*.md' docs/ | sort -u | tr '\n' ' ')" = "G1 G2 G5 G8 G9 " ] && [ "$(grep -rhoE '\bU[0-9]+\b' --include='*.md' docs/ | sort -u | tr '\n' ' ')" = "U1 U5 " ] && uv run pytest tests/test_docs_final.py -q</automated>
  </verify>
  <done>The SB-3 row reads `✅ one command` (the `— G3 resolved` tag dropped); the D22 sentence reads `(the Phase-1 borrowed-read-path gap)`; the SB-8 row reads `(counts reconciled)`; the SW-3 row reads `(key breadth — integration-verified)`; the ST-1 row reads `✅ rehearsed`; the traceability row reads `open gaps G1/G2/G5/G8/G9, UX U1–U5`. Across `docs/*.md` the only bare `G` tokens are G1/G2/G5/G8/G9 and the only `U` tokens are U1/U5 — no removed STATUS ID survives, and `tests/test_docs_final.py` is green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| STATUS.md → reviewer | The doc is the honest self-assessment a reviewer reads; a resolved item left in, a done-list, or a moved estimate destroys its credibility. |
| STATUS.md ↔ other docs | STATUS and `docs/REQUIREMENTS.md`/`docs/DECISIONS.md` cross-reference the same gap IDs; a removal here must not leave a dangling reference there (a second source of the gap set). |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-261014-asx-01 | Repudiation / Tampering (integrity of the assessment) | STATUS.md §0/§1/§2/§3 estimate cells | medium | mitigate | Estimates must not move; Task 1 diffs the extracted estimate token set against the fixed pre-overhaul revision `d535ba0:STATUS.md` (byte-identical), and the plan verification re-checks the same revision — so the guard cannot go vacuous once Task 1 commits. |
| T-quick-261014-asx-02 | Repudiation (unverifiable claim / dangling reference) | STATUS.md §5 and docs/DECISIONS.md, docs/REQUIREMENTS.md | medium | mitigate | Only the measured demo-content nuance is added; the gap sets are asserted by exact set-equality on the surviving IDs, and the cross-references are verified by set-equality on `docs/*.md` (no removed ID survives). |
| T-quick-261014-asx-03 | Tampering (scope creep into guarded docs) | README.md / ARCHITECTURE.md / DESCRIPTION.md / EVALS.md | medium | mitigate | Those files are not touched; `tests/test_docs_final.py` must stay green, proving the guards still hold. |
| T-quick-261014-asx-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency is added or changed — this is a documentation-only task, so the package-legitimacy gate has nothing new to admit. |
</threat_model>

<verification>
Run from the repo root.

**1. Estimate cells are byte-identical to the pre-overhaul revision** (the invariant that matters). Compare the extracted token set against the ad2-close revision `d535ba0:STATUS.md` (Task 1 uses the same fixed revision, so the comparison stays sound after Task 1 commits):
```
git show d535ba0:STATUS.md | grep -oE '\*\*(27–30|18–20|9–14|13–15|9–10|3–5)\*\*|~79–94|[0-9]+/[0-9]+|\| [0-9]+ \| \*\*[0-9]+–[0-9]+\*\* \|' | sort > /tmp/est_base.txt
grep -oE '\*\*(27–30|18–20|9–14|13–15|9–10|3–5)\*\*|~79–94|[0-9]+/[0-9]+|\| [0-9]+ \| \*\*[0-9]+–[0-9]+\*\* \|' STATUS.md | sort > /tmp/est_now.txt
test "$(wc -l < /tmp/est_now.txt)" -eq 11
diff /tmp/est_base.txt /tmp/est_now.txt
```

**2. No removed gap ID survives; the open sets are correct.**
```
grep -oE '\bG[0-9]+\b' STATUS.md | sort -u | tr '\n' ' '        # -> G1 G2 G5 G8 G9
grep -oE '\bU[0-9]+\b' STATUS.md | sort -u | tr '\n' ' '        # -> U1 U2 U3 U4 U5
grep -cE '^[0-9]+\. \*\*G[0-9]' STATUS.md                       # -> 5
grep -rhoE '\bG[0-9]+\b' --include='*.md' docs/ | sort -u       # -> G1 G2 G5 G8 G9
grep -rhoE '\bU[0-9]+\b' --include='*.md' docs/ | sort -u       # -> U1 U5
```

**3. Scope: only the three intended docs changed** (explicit paths — `.planning/**.md` plan/summary files are excluded, as is the pre-existing non-`.md` asset edit under `docs/assets/`):
```
git diff --name-only d535ba0 -- STATUS.md docs/DECISIONS.md docs/REQUIREMENTS.md docs/DEMO.md | sort
# -> STATUS.md ; docs/DECISIONS.md ; docs/REQUIREMENTS.md
git diff --quiet d535ba0 -- docs/DEMO.md && echo "DEMO.md unchanged"
```

**4. Doc guards stay green:**
```
uv run pytest tests/test_docs_final.py -q
```
</verification>

<success_criteria>
- STATUS.md reads as a current gap analysis: the "Since the v1.1 close" block is gone (its facts absorbed into §2/§3/§6/§9), §5 lists only the five open gaps G1/G2/G5/G8/G9 as ordinals 1–5, §7 has no history paragraph, §8 has only open actions and no "UX (done …)" block, and §6 drops the stale framing while keeping U1–U5 + strengths.
- §0's `~79–94`/`6/6`/`4/5`, §1's `6/6`, §2's `4/5`, and every §3 `Pts`/`Est.` cell are byte-identical to `d535ba0:STATUS.md`.
- §3's "Why not full" cells cite only live caps (G1, G2, U1, U3, G5).
- The demo-content truth (33 s has the tool calls but is thin; 2:55 has the length but no tool calls; neither is a complete candidate) appears in §2 and §5, and nowhere else.
- `docs/DECISIONS.md` and `docs/REQUIREMENTS.md` carry no dangling reference to a removed STATUS gap ID — the SB-3 row's `G3 resolved` tag is dropped; the surviving G1/G2 references and REQUIREMENTS' own hyphenated G-3/G-8/G-10 are intact.
- `uv run pytest tests/test_docs_final.py -q` is green, and only STATUS.md, docs/DECISIONS.md and docs/REQUIREMENTS.md changed among `.md` files.
</success_criteria>

<output>
Create `.planning/quick/261014-asx-overhaul-status-md-into-a-current-state-/261014-asx-SUMMARY.md` when done
</output>
