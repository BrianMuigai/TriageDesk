---
quick_id: 261116-hus
slug: cover-the-local-word-fit-as-a-seizure-presentation
status: complete
date: 2026-11-16
commit: 536a73e
files_modified:
  - data/sats_discriminators.yaml
  - tests/test_matcher.py
---

# Summary — cover the local word "fit"

## What shipped

A bare "fit" now names the seizure family instead of a coverage gap.

- **`data/sats_discriminators.yaml`** — `"fit"` added to the `seizure_current` alias list
  (between `"fitting"` and `"ongoing seizure"`), plus a short header note recording why
  (nurse stress test 2026-11-16, S1).
- Data only: no change to `core/matcher.py`, `core/coverage.py`, `core/retrieval.py`,
  `core/scorer.py`, the citation helper or the `@audited` interceptor. No new discriminator id,
  no new category, no threshold change, no eval fixture/expectation touched.

Measured before → after (the MCP tool, which composes the matcher with the coverage verdict):

| Complaint | Before | After |
| --- | --- | --- |
| `fit` | `no_candidate`, ids `[]` → delivered GREEN on normal vitals | `matched`, ids `["seizure_current"]` → RED |
| `had a fit` | `no_candidate` | `matched`, `seizure_current` (bare token match) |
| `fitting` / `convulsion` | `matched` | `matched` (unchanged) |
| `seizure` | `ambiguous`, both seizure candidates | unchanged |
| `feeling unwell` | `no_candidate` | **`no_candidate`** (E-09 untouched) |
| `fitness` / `benefit` | `no_candidate` | `no_candidate` (token boundary holds) |

## Tests added — `tests/test_matcher.py`

- `test_the_local_word_fit_names_a_seizure_discriminator` — over the owned MCP server:
  `retrieval_status in {"matched", "ambiguous"}`, the ids/candidates name the discriminator that
  declares `"fitting"` (read from the substrate, never restated), `retrieve_evidence("fit")` admits
  exactly the ids the matcher returned and `no_match` agrees with it.
- `test_feeling_unwell_still_reports_no_candidate` — the E-09 regression guard at the tool level:
  `no_candidate`, empty ids, empty candidates.
- `test_the_fit_alias_does_not_fire_inside_a_longer_word` — "fitness"/"benefit"/"profit" do not
  trigger the new one-token alias.

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest tests/test_matcher.py -q` | 47 passed |
| targeted suite (`coverage`, `retrieval`, `sats_discriminators`, `eval_suite`, `mcp_tools`) | 56 passed |
| `uv run pytest -q` | **977 passed** |
| `uv run ruff check src tests` | All checks passed |
| `uv run python scripts/emit_evals.py --check` | up to date (report `0ae3dde6ca3f3615`) |

## Decisions / deviations

- **Matched (RED) chosen over ambiguous.** The plan allowed either. The alias route keeps one
  authority: the matcher and `retrieve_evidence` share the alias list, so the two paths agree by
  construction — the ambiguous route (a `text_terms.yaml` context condition) would have left
  retrieval reporting `no_match` while the verdict said `ambiguous`. Over-triage is the fail-safe
  direction, and the RED is a suggestion the nurse still approves.
- **Reversal of quick-task `261104-w53` D2, as directed.** That task declined a bare `fit` out of
  fear of "fit for discharge". This plan's measured defect (a seizure complaint delivered GREEN)
  is the unsafe direction; the alias now wins over that hypothetical administrative phrasing.
- **No duplicate-alias problem:** `"fit"` is declared once across the catalogue
  (`test_every_declared_alias_matches_through_the_matcher` and
  `test_aliases_are_unambiguous_across_discriminators` pass).
- **`had a fit` also matches** as a side effect of the bare token. Accepted: it over-triages a
  possibly historical event to RED rather than deferring it — the same fail-safe direction.
- Nothing staged beyond the two files; `.planning/`, `spans.jsonl`, `checkpoints.db`, `triage.db`
  and untracked `docs/assets/*` were left alone.

## Honest notes

- `"no fit"` (a negation) still matches nothing in the matcher, but the coverage classifier asks
  one seizure question rather than delivering GREEN — the safe outcome for a denied seizure phrase.
- E-09 ("feeling unwell") remains the declared, unfixed coverage gap.
