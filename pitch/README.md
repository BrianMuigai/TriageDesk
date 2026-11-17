# PITCH — TriageDesk

The 5-minute pitch and the 2-minute Q&A, built against the **African Agentic AI Design Challenge —
Nairobi edition** judging framework (Tool Integration 30 · Problem Relevance 20 · Feasibility &
Cost-to-Serve 20 · User Value & Willingness to Pay 15 · Scalability 15).

| File | What it is |
|---|---|
| `TriageDesk-Pitch.pptx` | The deck. 11 presented slides + 5 appendix slides. Speaker notes on every slide. |
| `SCRIPT.md` | The 5:00 run of show: words, timings, demo commands, the fallback ladder, the rehearsal drill. |
| `QA-BRIEF.md` | The 2:00 playbook: how to steer the questions, 16 prepared answers, the handout card. |
| `UNIT-ECONOMICS.md` | The arithmetic behind every number, which inputs are measured and which are assumptions, and where the model breaks. |
| `build/` | The generator (`build-deck.js` + `deck-system.js`). The deck is code, so a number changes in one place. |

## The argument the deck makes

1. **The problem is proven, not asserted** — nurses already run SATS, but on paper, by hand; even
   trained staff miss the emergency calls about half the time (Wangara 2019, 20%).
2. **The fix is the validated scale on the desk** — sourced, offline, gated (solution).
3. **It is live**: nine owned MCP tools, a borrowed SQLite server, a hash-chained audit, and a gate that
   refuses without a name (30% criterion).
4. **It is cheap and bounded**: 1,344 tokens, 3.1 model calls, under KES 2 per completed outcome (20%).
5. **It pays for itself**: KES 2.22 of nurse time saved against a KES 1.36 price (15%).
6. **The margin holds at 100×** because only the nurse's eight seconds grows linearly (15%).
7. **It says what it has not earned** — no clinician review yet, English only, no EMR write-back — and
   dates the fix.

## Before you present: five things to verify

The deck is honest about what is measured and what is assumed. Keep it that way.

1. `uv run pytest -q` — the deck claims **647** passing tests (`STATUS.md` §0). If the count has moved,
   change the appendix slide, not the claim.
2. `evals/results/report.json` — if the report has been regenerated, the digest and the p50/p95 change.
   Re-run `python3 scripts/emit_evals.py` and update slide 5 and appendix A3.
3. `sqlite3 triage.db "SELECT count(*) FROM audit;"` — the audit table must be non-empty for the live log
   query on slide 3 to show the run you just watched.
4. `ollama ps` — the model must be warm. A cold first call measured 51 s.
5. **The five fill-in slots**, which only you can answer:
   - the date of the booked clinician interview (slide 8);
   - the named next adopter, once you have asked them (slide 7);
   - the number of price conversations actually held (slide 6);
   - the patient volume at the target desk, if it is not ~200/day (it drives `UNIT-ECONOMICS.md` §5).

## Rebuild the deck

```bash
npm install pptxgenjs                       # once, anywhere on NODE_PATH
NODE_PATH=<dir-with-node_modules> node pitch/build/build-deck.js
```

Then render and read it before you trust it:

```bash
soffice --headless --convert-to pdf pitch/TriageDesk-Pitch.pptx
pdftoppm -jpeg -r 110 TriageDesk-Pitch.pdf slide     # inspect every page
```

## The design rules

- **Ink ground, one mint signal, and the four SATS colours used only as data.** The acuity chips in the
  footer are the motif; no decorative stripes.
- **Cambria for statements, Calibri for evidence** — the serif is the voice, the sans is the record.
- **Every slide answers one rubric criterion**, and its eyebrow names the criterion so a judge scoring on
  a sheet can find it without hunting.
- **Assumptions are labelled on the slide**, not buried in an appendix. Two numbers on slide 2 and four
  on slide 5 are assumptions; the rest are traceable to `report.json`.
