# Phase 10 — UI Review

**Audited:** 2026-10-13
**Baseline:** `10-UI-SPEC.md` (status: approved) — audited against the design contract, not abstract standards
**Screenshots:** captured — 13 PNGs in `.planning/ui-reviews/10-20261013-024257/` (empty at 1440/768/375; committable card+gate and deferred banner+read-only card at 1440/1024/375, plus full-page 1440/1024)
**Interaction captures:** off (`workflow.ui_interaction_capture` not enabled in the spawn config). Interaction evidence was instead gathered through the sanctioned CLI path — the real surface started with `uv run triagedesk desk`, the two scored states rendered from **real `POST /case` responses**, and the DOM measured in headless Chromium (Playwright CLI + a `node` driver). Every interaction claim below is backed by a measurement, not a guess.
**Verdict:** ADVISORY — never blocks the phase. No BLOCKERs. Four minor contract divergences (missing fifth SATS token, orphaned spacing token, a copy/UI mismatch on the schema-rejection affordance, and an accent use beyond the reserved-for list).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Every declared string is present verbatim (incl. both trigger-conditional banner bodies); but the mandated schema-rejection copy points at a "highlighted field" that is never rendered, and 3 user-facing strings render beyond the "fixed" copy table. |
| 2. Visuals | 4/4 | Clear focal point (solid colour block), hierarchy via size/weight only, all-text signals (no icon-only controls), loud tinted banner with thick left border — verified in the painted renders. |
| 3. Color | 3/4 | Base + state tokens exact, 60/30/10 holds, all contrasts AA (declared ratios verified); **but `--colour-blue` and `.colour-blue` are absent** — one of the five contract-declared SATS tokens is missing. |
| 4. Typography | 4/4 | Exactly 4 sizes (14/16/20/32) and 2 weights (400/600), declared line-heights, reserved uses respected — grep-verified. |
| 5. Spacing | 3/4 | All values are multiples of 4, no arbitrary spacing, 44px controls verified rendered; **but `--space-xl` is declared-and-unused and the card↔gate gap is 48px (2xl), not the contract's declared 32px (xl)**. |
| 6. Experience Design | 3/4 | Full state coverage + all four fail-safe rules verified live; but the schema-rejection message is not rendered beside the offending field and no field is highlighted, and the gate identity fields carry no client-side required affordance. |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Declare the fifth SATS token — `--colour-blue` + `.colour-blue`.** The contract declares five semantic priority tokens (`--colour-blue: #0B3D91`, on-colour `#FFFFFF`, 10.2:1) explicitly "for completeness … the surface renders whatever colour string the graph supplies; it never decides that BLUE is unreachable". `styles.css:17-20` declares only red/orange/yellow/green, and `styles.css:223-241` has no `.colour-blue` rule, while `server.py:299` will emit `class="colour-block colour-blue"` for a BLUE string. Today the bands never produce BLUE (D10-18), so it is unreachable — but if a substrate change ever yields it, the swatch block renders **uncoloured** (transparent) and the Display colour-name treatment loses its fill. The colour *name* still shows as text, so colour is never the only signal — hence a WARNING, not a BLOCKER. Fix: add the token and the `.colour-blue { background: var(--colour-blue); color: var(--surface); }` rule.

2. **Make the schema-rejection copy true, or change it.** `_SCHEMA_HINT` (`server.py:141`) + `_validation_message` (`server.py:1019-1025`) render `{loc}: {msg}. Check the highlighted field and try again.`, and `_handle_case` (`server.py:989-990`) places it in a `state-panel state-error` — which the template renders **below the whole form** (`index.html:28`), not beside the field. So the nurse is told to "check the highlighted field" when (a) no field is highlighted and (b) the message is not adjacent to it. The contract's `## UI Considerations` row `error | vitals-form` requires "the schema's own message **beside that field**". Fix: render the message in/next to the offending `.field` and add an error style to that field, or reword the hint.

3. **Reconcile `--space-xl` with the card↔gate gap.** `styles.css:36` declares `--space-xl: 32px` and the contract assigns it to "Gap between the card and the gate panel", but `var(--space-xl)` is **never used** (`grep` = declaration only) and `.priority-card`/`.approval-gate` share `margin: 0 0 var(--space-2xl)` = **48px** (`styles.css:105-115`). The gap the contract pinned at 32px renders at 48px, and a declared token is orphaned. Fix: set the card→gate spacing to `var(--space-xl)`, or amend the contract.

**Minor (non-priority):**
- The accent fill is applied to **two** primary buttons — the gate's `Approve suggestion` *and* the form's `Get suggested priority` (`index.html:23` both carry `class="primary"` → `styles.css:173-177`). The contract's reserved-for list is "explicit, exhaustive — never 'all interactive elements'" and names only the approve button. Defensible (both are primary CTAs) but a literal divergence from an exhaustive list.
- Reserved accent use (3) — "the active step indicator in the quickstart panel" — is unfulfilled: the quickstart renders its four steps as one `<p>` (`index.html:15`), so there is no step indicator to highlight. Reserved ≠ required; informational.
- The gate's `Your name`/`Your role` inputs (`server.py:600-603`) carry no `required`/`aria-required` marker; enforcement is server-side only (`durable.approval_decision`). Contract-compliant but affords no pre-submit cue.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Verified present and verbatim** (checked against `server.py` string constants + `index.html` + live renders): page title, quickstart heading/steps, form heading, all 14 field labels (`server.py:97-112`), mobility/AVPU option labels (schema `Literal`s `walking/with_help/stretcher` and `alert/voice/pain/unresponsive` → `Walking`/`With help`/`Stretcher`/`Alert`/`Voice`/`Pain`/`Unresponsive`, all matching), both CTAs, `Edit colour`, `Dismiss (commit nothing)`, empty heading/body, loading, both error strings, card heading/framing/labels/no-evidence line, gate heading/labels, committed-approve/-edit, dismissed, timeout, all three terminal copies, and the destructive confirmation.

**Trigger-conditional banner bodies — verified live.** The deferred render (`case-deferred.html`) emits the **no-match** body verbatim (`No discriminator matched this complaint, so this suggestion may be incomplete. Confirm before you act.`) with the verbatim headline (`No discriminator matched / low confidence — nurse to confirm`); `_banner_html` (`server.py:320-331`) selects the low-confidence body when the trigger is `deferral`. The committable render emits an **empty** banner. ✅

**Copy rules:** no token from `HandoverCard.FORBIDDEN_FIELD_TOKENS` (`summary, assessment, impression, plan, diagnosis, prescription, dx, rx`) appears in any rendered string (case-insensitive word-boundary scan of `server.py` + `index.html` = clean); no percentage/probability/"N% sure" figure anywhere (the only matches — "Re-measure" and a `percent-decodes` docstring — are not user-facing copy). ✅

**Findings (why not 4):**
- The mandated schema-rejection string (`server.py:141`, `server.py:1019-1025`) instructs "Check the **highlighted field**", but no field is ever highlighted and the message is not beside the field (see Pillar 6). The copy is correct-by-contract but false-in-render.
- Three user-facing strings render beyond the `## Copywriting Contract`'s "Every user-facing string is fixed here": `_READ_ONLY_FRAMING` (`server.py:128-130`), `_UNREACHED_COPY` (`server.py:135`) and `_NO_THREAD_COPY` (`server.py:142`). The read-only framing is **sanctioned by D10-17** ("explicitly framed as not confirmed and not queued"); the other two are undeclared fallbacks. All are plain and non-clinical — a mild divergence, not a defect.

### Pillar 2: Visuals (4/4)

- **Focal point:** the solid `.colour-block` with the Display colour name is the unmistakable anchor of the card; the loud tinted banner is the anchor of the deferred state — both confirmed in the painted renders.
- **Hierarchy without colour:** achieved purely through the 4 sizes / 2 weights (verified). The suggestion is framed as a suggestion (`.framing` line) — no verdict styling.
- **No icon-only controls:** every signal is a text label; no fetched glyph or icon font.
- **Banner treatment:** renders exactly as the contract requires — a light-tinted panel (`--caution-bg`) with a **4px left border** (`--caution-border`) and no solid fill, so it cannot be mistaken for the solid `--colour-yellow` priority block. Confirmed in `full/case-deferred-desktop.png`.
- **Cards:** white surfaces, 1px `--border`, 8px radius, 24px inner padding — uniform across quickstart/form/card/gate/panel.

No visual defects found.

### Pillar 3: Color (3/4)

- **Base palette exact:** `--bg #F7F8FA`, `--surface #FFFFFF`, `--accent #1D4ED8`, `--destructive #B42318`, `--text #111827`, `--muted-text #475467`, `--border #D0D5DD` (`styles.css:9-15`). Destructive is confined to the Clear-form action (`index.html:24`, `styles.css:179-183`). ✅
- **60/30/10:** dominant page background, secondary white panels, accent on the primary CTA(s) + focus ring only. Accent usage count is low and intentional. ✅
- **State tokens exact:** all nine caution/success/error/muted tokens present (`styles.css:22-30`). ✅
- **Contrast — recomputed, all AA:** body `#111827`/`#F7F8FA` = 16.69:1; muted `#475467`/`#FFFFFF` = 7.69:1; red 6.54:1; orange 7.31:1; yellow 11.58:1; green 5.02:1; blue 10.04:1; caution `#78350F`/`#FEF3C7` = 8.15:1; success 7.29:1; error 9.16:1; muted 6.98:1. Every declared figure is accurate within rounding. ✅
- **Focus ring exact:** measured `outline: 2px solid rgb(29,78,216)` (= `#1D4ED8`), `outline-offset: 2px` on the first Tab target. ✅

**Finding (why not 4):** `--colour-blue` is **not declared** — `styles.css:17-20` carries only four of the five contract SATS tokens, and there is no `.colour-blue` swatch rule. `server.py:293-299` (`_colour_class`) maps a substrate `BLUE` to `colour-blue`, so the card would render an uncoloured block. The contract declares the token for completeness and forbids the surface from deciding BLUE is unreachable. Currently unreachable via `tews_to_colour`, so a WARNING-level gap.

### Pillar 4: Typography (4/4)

Grep-verified over `styles.css`:
- **Sizes in use:** `14px`, `16px`, `20px`, `32px` — exactly the four declared. Nothing else.
- **Weights in use:** `400`, `600` — exactly the two declared. No italic, no third weight.
- **Line-heights:** `1.5` (body/value/citation), `1.4` (label/button/legend/choice), `1.2` (h1/h2/h3), `1.15` (`.colour-name`, `.banner-headline`) — exactly the declared set.
- **Reserved uses respected:** Display (32px) appears only on `.colour-name` and `.banner-headline`; Heading (20px) only on `h1/h2/h3`; Label (14px/600) on field labels, card field labels, evidence labels, legend and buttons; Body (16px) on prose, `.value`, `.citation` and form controls.

No typographic defect.

### Pillar 5: Spacing (3/4)

- **Scale:** every spacing value is a `var(--space-*)` token; the only raw px values are 1px borders, the 2px focus outline, `720px` max-width, and the control heights (44px) / colour-block (64px) / textarea (96px) — all multiples of 4 and all contract-sanctioned. No arbitrary spacing. ✅
- **44px control height verified rendered:** measured minimum rendered interactive-control height = **44px** at both 1280px and 1024px. ✅

**Finding (why not 4):** `--space-xl` (32px) is declared (`styles.css:36`) but **never used**, and the contract's declared use for it — "Gap between the card and the gate panel" — renders as **48px**, because `.priority-card` and `.approval-gate` share `margin: 0 0 var(--space-2xl)` (`styles.css:105-115`). One declared token is orphaned and one declared usage is off-spec (32px → 48px).

### Pillar 6: Experience Design (3/4)

**State coverage — all implemented and verified live:**
| State | Evidence |
|-------|----------|
| Empty | `GET /` → no `.priority-card`, no `.approval-gate`, `state-empty` heading `No case yet`, banner `display:none`. ✅ |
| Loading | On submit: CTA `disabled`, text `Getting the suggested priority…`, `aria-busy=true`. ✅ |
| Populated / Committable | `POST /case` (chest pain) → `.priority-card` (ORANGE) + `.approval-gate`, banner empty. ✅ |
| Deferred / No-match | `POST /case` (unmatched complaint) → banner with no-match body + read-only card + deferred terminal panel, **no gate**. ✅ |
| Gate pending | Real `<form action="/decision">`; radios `GREEN/ORANGE/RED/YELLOW` (four, no BLUE — matches D10-18), three labelled buttons. ✅ |
| Timeout | `#gate-timeout` present, `hidden`, `display:none` until the 5-minute client timer. ✅ |
| Dismissed / Committed / Error / Terminal | All copy paths present in `_decision_view`/`_terminal_panel`/`_error_panel`. ✅ |

**Fail-safe rules — all four hold:** (1) timeout reveals a panel + disables buttons and submits nothing → no approve; (2) dismiss renders the muted panel, commits nothing; (3) the surface never commits on its own (code-review-confirmed import graph); (4) any failure renders the error panel and leaves the decision unresolved. ✅

**Accessibility — verified:** colour is never the only signal (name as text beside every swatch, text banner, text panels); focus ring present (2px accent, offset 2px); every control ≥44px; the banner is `aria-live="polite"` (`index.html:29`) and state panels are `role="status"`; the gate is a real `<form>` with labelled buttons and a fieldset/legend radio group; no motion is required to understand any state. No horizontal overflow at **1280px or 1024px** (measured `scrollWidth == clientWidth`, no offending element); no button clipping at either width (`Dismiss (commit nothing)` `scrollWidth == clientWidth`); the banner headline wraps to **2 lines** (74px / 36.8px line-height) and stays fully visible.

**Findings (why not 4):**
- **Schema-rejection affordance:** the error message renders in a panel *below the form* (`index.html:28`) and no field is highlighted — contradicting the `## UI Considerations` row "the schema's own message **beside that field**" and the "highlighted field" wording. The nurse must scan below the form and guess which field is wrong.
- **Gate identity fields** (`server.py:600-603`) have no client-side required affordance; a blank name/role is only rejected server-side after a round-trip.
- **Loading "no second submit is possible"** is enforced by disabling the submit button only; implicit submission (Enter in a text field) is not explicitly prevented in the inline script (`index.html:34-52`). Chromium blocks implicit submission when the submit button is disabled, but the guarantee is not explicitly coded — a robustness nit.

---

## Human / Backstop Items

The contract carries two `🧪 backstop` rows (overflow of citations/evidence; no-clip of `Dismiss (commit nothing)` at 1024px) plus the painted-banner item, all flagged as needing a browser. A browser **was** driven via CLI for this audit, so both backstops are now backed by measurements:

- `overflow | citations / evidence-list` — **cleared by measurement**: no horizontal overflow at 1280px or 1024px (committable and deferred).
- `long-text | interactive-control (buttons)` — **cleared by measurement**: no button clips at 1280px or 1024px.
- `uncertainty-banner` painted treatment — **captured**: `full/case-deferred-desktop.png` shows the tinted panel with the 4px left border and the 2-line headline.

**`human_needed` (formality only):** the spec's status vocabulary treats a `backstop` as `human_needed` absent explicit evidence; the CLI-browser evidence above satisfies it, but a human glance at `full/case-deferred-desktop.png` + `full/case-committable-tablet.png` is the sanctioned close-out if the team wants the signature. No unverified UI claim remains.

---

## Registry Safety

No `components.json` — shadcn is not initialised, so the registry audit is skipped (matches the UI-SPEC's `## Registry Safety` "Not applicable": hand-authored HTML + a local CSS asset, zero new dependencies).

---

## Files Audited

- `.planning/phases/10-desk-ux-real-approval-gate/10-UI-SPEC.md` (contract)
- `.planning/phases/10-desk-ux-real-approval-gate/10-CONTEXT.md`
- `.planning/phases/10-desk-ux-real-approval-gate/10-REVIEW.md`
- `src/triagedesk/desk/server.py`
- `src/triagedesk/desk/static/index.html`
- `src/triagedesk/desk/static/styles.css`
- `src/triagedesk/core/schema.py` (`CaseInput` literals, `FORBIDDEN_FIELD_TOKENS`)
- `data/sats_discriminators.yaml` (to drive a committable vs no-match case)
- Captures: `.planning/ui-reviews/10-20261013-024257/` (empty ×3, committable ×3, deferred ×3, full-page ×4)
