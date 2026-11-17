# SCRIPT — the winning five minutes (read this like you mean it)

> **This is not a speech to memorise word-for-word. It's a conversation you're having with five smart
> people.** Memorise the *beats*, not the commas. The words below are the shape of what to say — if a
> line feels wrong in your mouth, say it your way, as long as you keep the number and the point.
>
> **The arc:** a warm hello → a number that stops the room → the problem (it's the paper, not the nurse)
> → the fix in one glance → the proof → the price → the ask. The demo sits in the middle, where it proves
> something instead of just asserting it.
>
> **The thesis in one line, so you never lose the thread:**
> *Your nurses already use SATS. The problem is the paper. We put the scale on the desk, sourced and gated.*

---

## T–10 minutes, before you walk on

1. `ollama run qwen2.5:1.5b "warm"` then `ollama ps` — a cold first call measured 51 s.
2. `uv run triagedesk demo --list` — confirm the storyboard loads.
3. Terminal: dark, 18 pt, no notifications, `clear`.
4. Second tab, pre-typed: `sqlite3 triage.db "SELECT seq, ts, case_id, tool, actor, ifnull(approved_by,'-'), substr(hash,1,10) FROM audit ORDER BY seq DESC LIMIT 12;"`
5. Presenter view on — the notes are this script, trimmed.

---

## 0:00 — SLIDE 1 — Cover (6 s)

> Good morning. I'm **Brian Muigai**. This is TriageDesk — it gives a triage nurse a sourced,
> nurse-approved priority in the time it takes to write a card. And before you ask: no, it doesn't
> replace the nurse. It replaces the paper.

*Smile. Advance. Don't linger on the cover.*

## 0:06 — SLIDE 2 — The hook (30 s)

> Here's the thing nobody says out loud. Your nurses already use SATS — the South African Triage Scale —
> and it's genuinely good. Validated in a dozen countries. The problem is not the scale.
>
> The problem is that it lives on a paper chart, and a nurse works it out by hand, from memory, in about
> fifteen seconds, while nineteen people wait behind her.
>
> And here's the number that should keep you up at night. In the study that validated SATS at Kenyatta
> National Hospital, trained staff matched the expert on the **emergency** calls only **51%** of the time.
> Half. On the one call that can't be wrong.
>
> Not because nurses are careless. Because we're asking a human with a pen to do a computer's job, at
> 7:40 on a Tuesday.

*Let "half" land. This is the hook of the whole talk.*

## 0:35 — SLIDE 3 — The problem (30 s)

> So the gap isn't skill — it's delivery. A paper chart does three things badly. It's slow: fifteen to
> forty-five seconds a patient, and it gets slower as the queue grows. It leaves no record: tomorrow,
> nobody can tell you *why* this patient was orange. And it puts the one call that cannot be wrong on a
> tired human, at the busiest hour of the day.
>
> And this isn't one hospital. Kenya has forty-seven counties, each with a referral hospital, and no
> national triage standard — so the desk is everywhere, and the paper chart is everywhere with it.
>
> So we didn't build a new triage system. We built the thing that stops the good one being done on the
> back of a card.

## 1:05 — SLIDE 4 — The solution (25 s)

> Here's the whole product, and it's honestly simple. Three things. Every colour is **sourced** — it shows
> the exact rule and the vital that made it orange, so the nurse can check the homework. It runs
> **offline** — a one-and-a-half-billion-parameter model on the desk computer, so patient data never
> leaves the building and it works when the wifi doesn't, which in a district hospital is most of the
> time. And it's **gated** — exactly one action can move a patient, and it refuses until a real nurse or
> clinician puts their name on it.
>
> It scores or sequences. It never diagnoses, never prescribes, never moves anyone on its own. Watch.

*Cue: terminal. Run the first two beats:*

```bash
uv run triagedesk demo --online --beat escalation --beat refusal
```

## 1:30 — SLIDE 5 — The demo (130 s)

> Beat one. Normal vitals, chest pain. Watch the log at the bottom: `match_discriminators`, then
> `retrieve_evidence`, then `score_priority`. Three tools, one answer — and the citation names the rule.
> The nurse doesn't have to trust the screen; she can read *why*.
>
> Beat two. Same patient, same colour — no name on the approval. *(refusal runs)* The gate says no, and
> nothing is written. **That refusal is the product.** In a system like this, the most important feature
> is the one that says no.

```bash
uv run triagedesk demo --beat deterioration --beat failure
```

> Beat three. The patient's vitals slip while she waits. It raises a second look. It doesn't re-classify,
> doesn't reorder the queue. It taps the nurse on the shoulder; it doesn't grab the wheel.
>
> Beat four — and this is the part where we're wrong in public. E-09: "feeling unwell", known diabetic. We
> expected orange. It asks one careful question and delivers no colour. We published it as a failure,
> because if you're going to trust a triage tool, you want the one that tells you when it's guessing.
>
> And here's the audit table for everything you just watched. *(run the query)* Every row chained to the
> one above it, the nurse's name in the record. That's what a hospital auditor reads.

**If it stalls** (over 45 s on a beat): `Ctrl-C`, re-run without `--online`, and say —

> "The model is cold — it's competing with the projector. The tool calls are the same; the extraction is
> replayed from the fixture, and I won't pretend otherwise."

That sentence buys more than a fast demo.

## 3:40 — SLIDE 6 — Integration (18 s)

> Left column, running now. Middle, empty on purpose — nothing here is faked. Right, what's next, and I'll
> name it: hospital records over DHIS2 or OpenMRS, SMS over Africa's Talking, French intake. Each is one
> adapter, because the graph talks to an interface, not to a vendor.

## 3:58 — SLIDE 7 — Cost (16 s)

> One outcome — a cited, approved priority — is 1,344 tokens in, 146 out, three model calls, and under two
> shillings — KES 1.88 — hardware and support included. At a hundred desks, under half a shilling. The model
> is local,
> so the marginal cost of one more patient is roughly the electricity to think about them.

## 4:14 — SLIDE 8 — Value (18 s)

> Twenty seconds a patient, two hundred patients — that's an hour and ten minutes of a nurse's day, about
> KES 9,800 a month. We charge KES 6,000, from the county budget or the facility's own fund, a line
> a nurse-in-charge can sign without writing a proposal.
>
> And the awkward part, before you ask it: we haven't signed a price yet. Ten nurse-in-charge conversations
> and one signed pilot letter is the next thirty days. I'd rather show you an empty column than a number I
> made up.

## 4:32 — SLIDE 9 — Scale (14 s)

> At ten desks: six thousand a desk, about two thousand six hundred to serve — fifty-six percent margin. At a
> hundred: four thousand eight hundred and about two thousand one hundred — fifty-seven. It doesn't collapse,
> because the only thing that grows with patients is the nurse's
> eight seconds — and that's her time, not our cost.
>
> And the market isn't one desk. Kenya first — a county, then three — then Uganda, Tanzania, Malawi, where the
> same paper chart is already in use. We're not introducing triage here. We're taking the paper out of it.

## 4:46 — SLIDE 10 — What we haven't earned (7 s)

> Three things we haven't earned yet: no clinician has reviewed it, it's English-only, no EMR write-back.
> They're in the repo — so I'll say them before you find them.

## 4:53 — SLIDE 11 — The close (7 s)

> One nurse, fifteen minutes. One desk, thirty days. One introduction to the payer. That's the whole ask.

*Point at the three doors. Sit down. Stop talking. Let the silence pull the first question.*

---

## The five sentences that must come out right

1. **"It doesn't replace the nurse. It replaces the paper."** — the whole pitch in eight words.
2. **"That refusal is the product."** — said the instant the gate refuses.
3. **"No number comes from the model."** — the colour is arithmetic on a YAML file.
4. **"I'd rather show you an empty column than a number I made up."** — the honesty in one line.
5. **"Nothing here is faked."** — then: "the one replay is the extraction on the offline fixture, and I'll
   tell you when it happens."

## Three things not to say

- **"Seconds."** Extraction p50 is 17.8 s, p95 is 60 s. Say "under twenty seconds, a minute at the tail."
- **"We integrate with the ministry."** There's no procurement route. Say "one desk, one budget line."
- **"A clinician validated it."** No clinician has. The interview is written; the session is not.

## Where the humour is safe — and where it isn't

Joke about **the paper, the queue, the wifi, the projector, the bureaucracy, yourself**. Never joke about
a patient, a nurse's competence, or anyone's health. The line "asking a human with a pen to do a
computer's job, at 7:40 on a Tuesday" works because it is warm toward the nurse — it blames the system,
not the person. Keep that balance and the humour lands; lose it and the whole pitch goes cold.

---

## Tonight's rehearsal (30 minutes, do it twice)

1. **Read the cover and the hook aloud, alone**, until "half" lands without you thinking about it. The
   first forty seconds decide the next five minutes.
2. **Run the full five minutes against a stopwatch**, deck and demo, twice.
   - Under 4:30 → rushing. Over 5:15 → you added words that aren't here.
3. **Rehearse the stall.** Kill the model mid-run, do the fallback, say the honesty sentence. Ten seconds,
   no credibility lost.
4. **Have someone fire eight questions** from `QA-BRIEF.md` in two minutes. Twenty seconds each. If you
   speak past twenty, they say "next."

## The one sentence to fall asleep repeating

> *Your nurses already use SATS. The problem is the paper — half the emergency calls get missed. We put
> the scale on the desk, sourced and gated, and it says no without a name.*
