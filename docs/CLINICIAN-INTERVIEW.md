# CLINICIAN INTERVIEW — eight questions for a triage nurse

> **Status: instrument + drafted responses. Not an attestation.**
> No clinician or triage nurse has reviewed TriageDesk, confirmed these answers, or signed the block
> at the end of this file. The responses below are drafted from the published SATS desk process and
> the shipped system — they are what we *believe* a triage nurse would say. Until §Attestation is
> signed, `EVALS.md` §7 must keep saying **none obtained**, and nothing here may be quoted as a review.

**Why this file exists.** The 20-point fit-to-desk criterion asks one blunt question: *did you talk to
one?* This is the exact page to put in front of one, so the conversation takes fifteen minutes instead
of an hour — and so every answer can be checked against what is actually built (§What each answer
commits us to).

## How to run it

1. Hand over this page. Read the question, then the drafted answer, aloud.
2. **Let the nurse interrupt.** A correction is the valuable output, not agreement.
3. Write corrections in the margin; mark *confirmed* or *corrected* per answer.
4. Ask the two closing questions (§Two closing questions).
5. Sign §Attestation. Only then update the status line above and `EVALS.md` §7.

## The script

> *Read first:* "These are eight answers I've written down from watching how the desk works and from
> what we built. I'd rather you tell me where I'm wrong than agree with me."

### 1. Walk me through your last busy morning, minute by minute, from patient arrival to colour.

> 07:40, twenty waiting. Registration hands over the paper card. I take RR, AVPU, BP, temperature —
> SpO₂ if the probe works — and write them on the card. I pick a colour in fifteen to forty-five
> seconds, write it top-right, and point the patient to majors, minors or resus.

*Probe:* Is that the real order? Where do the fifteen to forty-five seconds actually go?

### 2. Where does the paper card physically go, and who touches it?

> Created at records, carried by the patient, written on by me, handed to the streaming nurse, then
> the doctor, then back to records for filing. TriageDesk doesn't touch it — it writes the digital
> queue and I still write the card by hand.

*Probe:* Would you want it on the card, or is a second place to look the thing you'd refuse?

### 3. When two patients look equally sick, how do you choose?

> SATS breaks the tie before I do: a red-flag discriminator beats the score, the score beats my
> impression. Same colour and no danger signs — I use gut, and if I'm still unsure I up-triage the one
> I'd rather be wrong about. The queue sorts by colour then arrival; it never ranks two patients
> against each other.

*Probe:* Is up-triage-on-doubt a rule you'd accept, or does it create a shortcut people learn to game?

### 4. What would make you distrust a colour a screen gave you?

> No visible reason, missing vitals quietly filled in, or a colour that contradicts what I can see.
> So every colour carries the rule, the vital and the citation; missing vitals are named, never
> imputed; red flags override the score; and no match gives a deferral banner, not a guess.

*Probe:* Which of those four failures would stop you using it after the first time?

### 5. What's the one number you always have? The one you almost never have?

> Always: respiratory rate and AVPU — eyes and a watch. Almost never: blood glucose, and often
> temperature when the thermometer's broken. That's why a missing vital is a first-class output here,
> not a zero.

*Probe:* What else is routinely absent that we would be wrong to impute?

### 6. How long does triage take per patient today — best case, busy morning?

> Twenty to thirty seconds to complete the card, fifteen to forty-five to decide — a minute or two
> best case, three to five on a busy morning. Scoring is instant; the local model adds about twenty
> seconds at median under load, about fourteen quiet. We publish both.

*Probe:* What would the extra seconds cost you at 07:40?

### 7. If this sat on your desk, what would you ignore?

> The prose explanation. I'd read the colour and the one-line reason and skip the rest. So colour and
> reason sit above the fold, evidence is one line, and the model reads the complaint while I'm still
> typing vitals.

*Probe:* How much evidence before you stop reading?

### 8. What would have to be true for you to use it on a real patient?

> A named clinician signs off the rules, it's validated on our patients, it works offline, it never
> acts alone, and I can audit every colour. The last three are built. The first two aren't — nobody
> has signed off the rules, and it hasn't been validated on our patients.

*Probe:* Who would that named person be, and what would they need to see?

## What each answer commits us to

Every response is a claim about the build. This is where a reviewer checks it — and where a correction
from the nurse becomes a code or doc change, not a debate.

| # | The claim | Where it is true in the build | If the nurse contradicts it |
| --- | --- | --- | --- |
| 1 | The loop is vitals → sourced colour → nurse decides | [`DESK.md`](DESK.md); `src/triagedesk/desk/` | We modelled the wrong loop — a design change, not a wording change. |
| 2 | The paper card stays paper; the digital queue is separate | `src/triagedesk/store/` write path; [`DESK.md`](DESK.md) | Add a card-print step, or drop the second surface. |
| 3 | Red flag beats score beats impression; queue orders by colour then arrival | `core/scorer.py`; `desk/waiting.py` → `order_rows` | The tie-break rule is wrong. |
| 4 | Rule + vital + citation on every colour; missing vitals named; no match defers | `core/scorer.py`; `core/citations.py`; `core/confidence.py` | The trust surface is insufficient — the biggest safety finding. |
| 5 | A missing vital is a first-class output, never a zero | `core/schema.py`; `core/scorer.py` | The recovery terminal is wrong. |
| 6 | Scoring is instant; model p50 ≈ 20 s loaded, ≈ 14 s quiet | [`../EVALS.md`](../EVALS.md) §3 | The latency cost is unacceptable at peak. |
| 7 | Colour and one-line reason sit above the fold | `desk/card.py` | Re-order the card, cut the copy. |
| 8 | Offline, never acts alone, every colour auditable — all built | [`../SECURITY.md`](../SECURITY.md) §6; `mcp/server.py` audit chain | One of the three is not as evidenced as we claim. |

## Two closing questions

1. **What is the one thing in this system that would make you stop using it?**
2. **Who would have to sign off before you'd trust a colour on a real patient?**

Both answers go in the attestation. The first is the risk register entry; the second is the name the
challenge is actually asking for.

## Attestation

Fill this in **only** if a real clinician or triage nurse went through the script. Do not fill it in on
their behalf, and do not add a quote they did not say.

| Field | Value |
| --- | --- |
| Clinician name | |
| Role and registration | |
| Facility / desk | |
| Date | |
| Time spent | |
| Answers confirmed unchanged | ___ / 8 |
| Answers corrected | *(attach or link the marked-up page)* |
| One thing that would make them stop using it | |
| Consent to quote | yes / no |
| Signature | |

*Signed §Attestation is the only thing that may be called a review. A corrected answer is a better
outcome than an agreed one — record the correction, not just the tick.*

## When §Attestation is signed

Update exactly these, and nothing else:

- **This file** — the status banner at the top.
- **[`../EVALS.md`](../EVALS.md) §7** — replace *"none obtained"* with the attributed quote
  (name / role / date, with consent) and the corrections that changed the build.
- **[`../README.md`](../README.md)** — the *What is unfinished* paragraph and the
  *No triage nurse/clinician review* bullet.
- **[`../STATUS.md`](../STATUS.md)** — gap **G2**, the §0 verdict, and the §8 action list.
- **[`REQUIREMENTS.md`](REQUIREMENTS.md)** — **JC-3** and **G-1**.
- **[`DEMO.md`](DEMO.md)** and **[`TESTING.md`](TESTING.md)** — the two "no clinician review" caveats.

## What this file does not do

It does not close G2. It does not substitute for a review, and it must not be read as one. It converts
an open-ended gap (*"we couldn't get a clinician"*) into a bounded, runnable task (*"one fifteen-minute
conversation, with the questions and the evidence already prepared"*) — and it makes every drafted
answer falsifiable against the code.
