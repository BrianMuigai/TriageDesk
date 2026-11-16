# Quick task 261116-u9l — UI Review

**Audited:** 2026-11-16
**Baseline:** No UI-SPEC exists for this quick task. Audited against the winning sketch direction
(`.planning/sketches/001-triage-desk-chat/README.md` — Variant **A: Workbench**), the sketch manifest's
design direction and reference points, the shipped surface contract in `docs/DESK.md`, and the abstract
6-pillar standards.
**Screenshots:** captured (3 viewports + 6 server-rendered state captures) in
`.planning/ui-reviews/261116-u9l-20261116-222730/`
**Interaction captures:** off (`workflow.ui_interaction_capture` is false). State surfaces below were
produced by POSTing to the running desk and screenshotting the real response — they are server-rendered
state captures, not scripted interaction captures; all interaction findings are marked code/HTTP-derived.

> **Dev-server note.** The workflow scan set pointed at `:3000` and `:8080`; both are unrelated apps
> (a Vite "Phonic Dashboard" on 3000, an unrelated FastAPI 404 on 8080). The real TriageDesk desk was
> already listening on `127.0.0.1:8765` (pid 94245) and every capture below came from it, so no other
> application was audited.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | Strong safety copy overall, but the no-match banner is rendered on clarification/recovery screens where nothing exists to confirm, and raw machine tokens (`respiratory_rate=24`, `approve`) surface as clinical copy. |
| 2. Visuals | 3/4 | Clear rail → workspace → conversation focal path; but the result/gate render as dashboard cards, not messages, and the "sticky" intake the sketch promised is not sticky. |
| 3. Color | 2/4 | Token discipline and contrast are excellent; the two most urgent clinical swatches (RED `#b3261e`, ORANGE `#9a3412`) are nearly indistinguishable dark reds. |
| 4. Typography | 3/4 | Coherent hierarchy and a system font stack, but 8 sizes / 4 weights and 11px metadata + 13px bubble copy are small for a desk. |
| 5. Spacing | 2/4 | Good 4/8/16/24/32/48/64 token scale, but ~12 off-scale px values, nav targets below the required 44px, and a large dead band in the chat column. |
| 6. Experience Design | 2/4 | State machinery is genuinely thorough, but a chosen gate colour is silently discarded by "Approve", and autofocus smooth-scrolls the page past the safety framing and the decision controls. |

**Overall: 14/24**

---

## Top 3 Priority Fixes

1. **Gate colour radios are silently ignored by "Approve suggestion" (BLOCKER).**
   `gate.py:36-42` renders `Choose the priority colour` with four radios, and `durable.py:294-297` only
   uses the posted colour when `decision == "edit"`. Verified against the live desk: selecting
   **YELLOW** and pressing **Approve suggestion** committed **ORANGE** (`handover-desktop.png` shows
   `colour-name">ORANGE` and `Approved by Nurse Audit`). A nurse can believe they set YELLOW while the
   suggested ORANGE is what reaches the queue.
   *Fix:* either make "Approve suggestion" honour the selected colour, or hide/disable the radio group
   unless "Edit colour" is the active path and label it "Colour for an edit"; add one line stating
   "Approve commits the suggested colour."

2. **Autofocus + global smooth scroll lands the page mid-screen at ≤1080px (BLOCKER).**
   `forms.py:199,267,289` puts `autofocus` on the first vitals field, and `styles.css:66-68` sets
   `html { scroll-behavior: smooth }`. At 375px and 768px the intake sits below the conversation, so the
   browser smooth-scrolls to `#age_years` on load. After 3s the mobile viewport is scrolled ~900px down
   (`mobile-wait3s.png`), and the tablet ~590px down (`tablet-wait3s.png`) — the welcome bubble's
   scope/approval framing and the page identity are off-screen on first paint. The same autofocus also
   skips past the approval gate after scoring: focus lands after the decision controls in DOM order, so a
   keyboard user must wrap around to reach "Approve".
   *Fix:* drop the intake autofocus when the workspace is single-column (or focus with
   `{preventScroll:true}`), scope `scroll-behavior: smooth` to anchor navigation, and move focus to the
   gate's `#approver-name` when a gate renders.

3. **False "nurse to confirm" banner on clarification and recovery terminals (BLOCKER).**
   `views.py:188-189` computes the banner before the terminal kind and `views.py:214-231` renders both.
   Clarification and recovery screens therefore show the 24px amber
   "No discriminator matched / low confidence — nurse to confirm … Confirm before you act"
   (`copy.py:10-17`) above copy that says no priority was committed and, in recovery, above
   "A scored vital is missing (temperature). Re-measure before scoring." There is no suggestion to
   confirm; the contradiction trains banner blindness on a safety surface (`clarification-desktop.png`).
   *Fix:* suppress the no-match banner whenever `terminal_kind()` is `clarification` or `recovery`, and
   give those terminals their own calm framing.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

The baseline copy is genuinely strong: the welcome states triage-only scope and the named-approval rule
(`copy.py:101-112`), every terminal says "nothing has been committed", the offline note confirmation is
honest (`copy.py:120-123`), and the empty state is specific ("Enter the patient's vitals and complaint,
then choose Get suggested priority."). No generic `Submit`/`OK`/`Cancel` labels exist. The failures are
in state combinations and in leaked internals:

- **BLOCKER — contradictory safety banner on clarification/recovery.** See Top 3 #3.
  `clarification-desktop.png`, `vitalsonly-desktop.png`; `views.py:188-231`, `copy.py:10-17`.
- **Raw machine values presented as clinical facts.** The priority card's "Why these vitals" renders
  `respiratory_rate=24 → 2 points`, `heart_rate=118 → 2 points`, `temperature=38.9 → 2 points`
  (`card.py:36-41` passes the scorer's `detail` through). Human labels exist in the same UI
  ("Breathing rate", "Heart rate") — the rule text should use them.
- **Raw token as a human fact.** The handover's Decision fact shows `approve` in lower case
  (`chat.py:188`); it should read "Approved" / "Edited" / "Dismissed".
- **Clarification copy points at an affordance that is not there.** "One detail would resolve this case.
  Answer below and resubmit" (`copy.py:46-49`) has no answer field in the panel; at desktop the
  complaint field is to the *right*, not below. The two prompts are rule labels
  ("Ask about: Diabetic glucose > 11 with ketonuria"), not answerable questions, and the only submit
  action is labelled "Get suggested priority".
- **Waiting room repeats itself three times and changes its name.**
  `views.py:442-443` sets the h1 to "Queue"; `views.py:401-409` renders "QUEUE / Waiting room"; the
  panel renders another "Waiting room" h2 and a `<caption>` "Waiting room"
  (`waiting.py:100-113`). Screen readers hear it three times (`waiting.png`, `waiting-mobile.png`).
- **Duplicate author label.** On first paint "TriageDesk assistant" appears twice consecutively — once
  for the welcome bubble (`chat.py:58-65`) and once for the result wrapper (`views.py:379-382`) — giving
  the empty state the appearance of two assistant messages.
- **Documented state contradicted.** `DESK.md:148-150` says "a sore throat" is delivered normally, not
  clarified; the shipped surface returned a clarification asking "Persistent vomiting" plus the
  no-match banner (`vitalsonly-desktop.png`). This may be graph/data rather than presentation, but it is
  what the copy says on screen.

### Pillar 2: Visuals (3/4)

The shell is coherent and the focal point is unambiguous: dark orientation rail → topbar → conversation
primary, scored intake secondary. Badges ("Suggestion only" / "Scored input") correctly frame the two
surfaces. Problems:

- **The suggestion/gate read as dashboard widgets, not messages.** The sketch's own test is "whether the
  suggestion card reads as a message, not a dashboard widget". Only `.chat-body` messages get the bubble
  treatment (`styles.css:388-402`); `.priority-card`, `.approval-gate` and `.handover-card` render as
  white 16px-radius, 1px-bordered cards with 24px padding (`styles.css:671-681`) inside the log
  (`case-desktop.png`, `clarification-desktop.png`). The visual language splits into bubbles and panels.
- **"Sticky structured intake" is not implemented.** The sketch winner promises "keeps the scored vitals
  visible and sticky beside it"; the plan's Task 2 says "a sticky intake card"; `styles.css:508-512`
  explicitly sets `.intake-panel { position: static; }` (repeated at 1070-1074). On a long result + gate
  the scored input scrolls completely out of view (`case-desktop.png`).
- **Collapse point deviates from the design direction.** The sketch asks for density checks at 1280 and
  collapse at 980/620; the workspace collapses at **1080** (`styles.css:1065`). At 980–1080 the entire
  intake is below the fold behind a 750px conversation (`w980.png`).
- **Large dead band in the chat column on empty/tablet states.** `.conversation` min-height is
  `calc(100vh - 150px)` and `.chat-log` flex-grows (`styles.css:347-361`), leaving ~230px of empty space
  between the empty-state card and the composer at 768 (`tablet.png`) and ~130px at 620 (`w620.png`).
- **Complaint field wastes half its row.** "Presentation / Complaint" occupies one cell of the two-column
  `.field-grid` (`forms.py:48-64`, `styles.css:534-538`), leaving the right half empty even though the
  complaint is the field the whole chat flow depends on (`desktop-full.png`, `clarification-desktop.png`).
- **Waiting-room table breaks at 375px.** `width: 100%` plus `overflow-x: auto`
  (`styles.css:987-1005`) squeezes the table: "Waiting 17316 min" wraps to three lines and the TARGET
  column is clipped (`waiting-mobile.png`). The `POSITION` column also reads 1,4,5,2,3… because rows are
  acuity-sorted while the stored position is shown — with no rank column it looks like a broken sort.

### Pillar 3: Color (2/4)

Token discipline is strong: every clinical and semantic colour is a CSS custom property
(`styles.css:8-42`), teal is consistently the single action colour (17 `var(--accent*)` uses), and the
60/30/10 split reads correctly (light canvas ~60, white surfaces ~30, teal <10). Measured contrast passes
everywhere: muted text on surface 5.87:1, white on accent 5.47:1, caution 8.15:1, error 9.16:1, success
7.29:1, focus ring on rail 3.22:1. No external URL, font import or asset fetch exists.

- **BLOCKER-adjacent — RED and ORANGE are not distinguishable at a glance.** `--colour-red: #b3261e`
  and `--colour-orange: #9a3412` (`styles.css:25-26`) are both dark reds 19° apart in hue. In the
  waiting room they sit on adjacent rows and read as the same colour (`waiting.png`, `waiting-mobile.png`);
  in the priority card the "ORANGE" swatch reads brown. For a product whose clinical language *is* the
  SATS colour, the two most urgent bands must be instantaneously separable (and "Orange" should be
  orange, not burnt umber). The NAME is present as text, which prevents a colour-only failure — but the
  at-a-glance acuity signal is compromised.
- **Five direct `#ffffff` literals** bypass the token set (`styles.css:140,175,180,401,749…`) where an
  `--on-accent` token would keep the palette single-source.
- **"Suggestion only" badge remains in states with no suggestion** (clarification, recovery), where the
  teal badge asserts the opposite of the panel (`clarification-desktop.png`).

### Pillar 4: Typography (3/4)

System font stack, no web font fetch, sensible line heights. Measured distribution: **8 distinct sizes**
(11×8, 12×8, 13×5, 14×10, 15×1, 16×9, 24×3, 32×1) and **4 weights** (400/600/700/800). The hierarchy is
legible (32 swatch > 24 page/banner > 16 lead > 13–14 body > 11–12 metadata), but it exceeds the abstract
"≤4 sizes / ≤2 weights" bar and the 11–14px cluster is too close together to read as distinct levels.

- 11px metadata (`chat-author`, `eyebrow`, `field-group legend`, `badge`, `composer-hint`,
  `waiting-table th`; `styles.css:191-198,238-245,376-382,499-504`) is below a comfortable desk minimum;
  the composer hint in particular is hard to read at 375 (`mobile-full.png`).
- Chat body copy is 13px (`styles.css:412-422`) and the welcome bubble measures ~83 characters per line
  at 1440 — above the comfortable 45–75 range for scanning under time pressure.
- Radius scale is similarly loosened: `12px` on `.brand-mark` sits outside the declared 6/10/16/22 set
  (`styles.css:52-56,138`).

### Pillar 5: Spacing (2/4)

The token scale is correct and used for the main layout (`--space-xs`…`--space-3xl`), and wrapping rules
on `.evidence-list li` / `.banner-headline` are preserved. Ten-plus values bypass the scale:

- `gap: 6px` (`styles.css:162,435`), `padding: 10px 12px` (168), `padding: 7px 12px` (263),
  `padding: 8px 12px` (291), `padding: 5px 10px` (340), `gap: 14px` (356,453), `margin-bottom: 6px`
  (478), `margin: 3px 0 0` (947), `padding: 8px 10px` (1108). Off-scale values 3/5/7/10/14 are used
  where 4/8/16 tokens exist.
- **44px targets are missed on the rail.** `.nav-link` is `padding: 10px 12px` with 14px/1.5 text ≈ 41px
  (`styles.css:165-171`), and 8px padding at ≤860 ≈ 37px (1107-1110). The plan's Task 2 requires
  "44px targets"; buttons, inputs and colour labels do meet 44px.
- **Dead space** in the chat column (see Visuals) and the **half-width complaint** are spacing failures
  too: the chat log's flex-grow plus `min-height` produces an empty band on empty/tablet states, and the
  grid leaves half of the Presentation row unused.
- Vertical rhythm inside the result area is uneven: the shared card rule adds `margin-bottom: 48px`
  (`styles.css:671-681`) on top of `.chat-result`'s 14px gap (`styles.css:450-457`), so card/gate
  spacing is visibly larger than bubble spacing.

### Pillar 6: Experience Design (2/4)

The state machinery is the strongest part of the build: submit buttons relabel and set `aria-busy` before
posting, the gate disables siblings but never the submitter, the timeout panel reveals without submitting
(`index.html:62-147`), double submits are guarded, focus-visible is explicit, skip link and `<label for>`
coverage are complete, and every terminal carries "nothing has been committed". Two of the defects
below are severe enough to pull the score down on their own:

- **BLOCKER — a chosen colour is discarded by Approve.** See Top 3 #1. This is the gate's primary
  action and the one place a wrong colour reaches the queue.
- **BLOCKER — first paint and focus order are wrong at ≤1080.** See Top 3 #2. The safety framing is
  hidden by a scroll the user did not ask for, and after scoring, autofocus lands *past* the decision
  controls in tab order.
- **Nested live regions double-announce.** `.chat-log` is `role="log" aria-live="polite"`
  (`views.py:392-393`) and contains `role="status"` panels (`views.py:107-116`) and an
  `aria-live="polite"` banner (`views.py:368`). Screen readers can announce the same outcome twice on a
  clinical surface.
- **Urgency order is inverted in the gate.** `editable_colours()` returns an alphabetically
  `sorted(...)` set (`gate.py:15-27`), so the radios read GREEN → ORANGE → RED → YELLOW — least urgent
  first, directly beside the primary "Approve suggestion" button (`case-desktop.png`). The substrate
  already exposes `core.rules.colour_urgency` (used by the waiting room); the gate should use the same
  order and lead with RED.
- **Two different "question" surfaces.** The mid-run elicitation panel is a real form with answer fields
  and a decline control (`clarification.py`), while the bounded clarification terminal is prose asking the
  nurse to edit the complaint field elsewhere (`views.py:142-150`). Same conceptual state, two different
  affordances.
- **Destructive confirmation exists where it matters** (`data-confirm` on Clear form, `index.html:78-85`)
  — a positive. Dismiss correctly commits nothing and needs none.
- **Waiting-room numbers are unformatted.** "Waiting 17304 min" (12 days) is raw arithmetic in a queue
  view (`waiting.py:72-83`), which reads as broken data.

---

## Additional Recommendations (beyond the top 3)

4. **Make the intake sticky at ≥1080** (`styles.css:508-512`) or give it its own scroll, so the scored
   input stays beside the card and gate as the sketch promised. *WARNING.*
5. **Re-tune the SATS swatches**: ORANGE to a genuinely orange hue (e.g. `#c2410c`/`#ea580c`) and verify
   RED vs ORANGE at 12px swatch size against deuteranopia simulation; keep the name text.
   *WARNING — clinical signal.*
6. **Move the no-match banner or the terminal** so a clarification/recovery screen never says "confirm
   before you act" (Top 3 #3) — pair with removing "Suggestion only" in those states.
7. **Humanise the card's rule text** (`respiratory_rate=24` → "Breathing rate 24") in the scorer output
   or at render time in `card.py`.
8. **De-duplicate the waiting-room headings** (one h1 "Waiting room", caption visually hidden) and pick
   one term — Queue or Waiting room, not both (`views.py:442-443`, `waiting.py:100-113`).
9. **Make the waiting table survive 375px**: `min-width` on the table + horizontal scroll, or a stacked
   row layout; and add a visible acuity rank so 1,4,5,2,3 is explicable.
10. **Give the complaint field the full row** (`forms.py:63`, `styles.css:534-538`) — it is the chat
    flow's primary input and the clarification answer path.
11. **Restore 44px rail targets** (`styles.css:168,1108`) and replace off-scale 3/5/7/10/14px values
    with tokens.
12. **Reduce the 11–14px cluster** to a 3–4 step metadata scale and lift chat body copy to 14–15px.
13. **Nest one live region, not three** (`views.py:368,392`): keep `role="log"` and drop the child
    `aria-live`/`role="status"` duplication.
14. **Scope `scroll-behavior: smooth`** to `:target`/anchor navigation instead of `html`.

---

## Evidence

Captured from the shipped desk (`127.0.0.1:8765`), desktop 1440×900, tablet 768×1024, mobile 375×812:

| Capture | What it shows |
|---------|---------------|
| `desktop.png`, `desktop-full.png`, `mobile.png`, `mobile-full.png`, `tablet.png`, `w1280.png`, `w980.png`, `w860.png`, `w620.png` | Empty state and shell at each breakpoint; intake below the fold at ≤1080; dead band at 620/768 |
| `mobile-wait3s.png`, `tablet-wait3s.png` | The autofocus smooth-scroll landing mid-page (after 3 s) |
| `case-desktop.png`, `case-mobile.png` | Card + gate; GREEN/ORANGE/RED/YELLOW radio order; widget-style card |
| `clarification-desktop.png` | Clarification terminal + contradictory no-match banner; no answer control; half-width complaint |
| `vitalsonly-desktop.png` | Documented "sore throat → normal delivery" state shipped as a clarification + banner |
| `handover-desktop.png` | Approve with YELLOW selected committed ORANGE; handover facts; raw `approve` token |
| `waiting.png`, `waiting-mobile.png` | Triple "Waiting room"; RED/ORANGE ambiguity; clipped TARGET at 375; scrambled-looking position order |

Positive verifications: no external URL, `@import`, `url()` or font fetch anywhere in `index.html` /
`styles.css`; no `white-space: nowrap`; all interactive controls except rail nav meet 44px; measured
contrast ≥3.22:1 on every pair (text ≥5.27:1); form controls are generated from `CaseInput` with labels
and `aria-invalid` beside the offending field.

---

## Files Audited

- `src/triagedesk/desk/static/index.html`
- `src/triagedesk/desk/static/styles.css`
- `src/triagedesk/desk/chat.py`
- `src/triagedesk/desk/views.py`
- `src/triagedesk/desk/forms.py`
- `src/triagedesk/desk/copy.py`
- `src/triagedesk/desk/card.py`
- `src/triagedesk/desk/gate.py`
- `src/triagedesk/desk/waiting.py`
- `src/triagedesk/desk/clarification.py`
- `src/triagedesk/desk/server.py` (note/decision handlers)
- `src/triagedesk/durable.py` (`approval_decision` colour handling)
- `docs/DESK.md`
- `.planning/quick/261116-u9l-modern-chat-style-triage-desk-ui-with-st/261116-u9l-PLAN.md`
- `.planning/sketches/001-triage-desk-chat/README.md`, `.planning/sketches/MANIFEST.md`

Registry audit: not applicable — no `components.json`, no shadcn, no third-party registries.
