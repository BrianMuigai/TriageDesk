# Q&A BRIEF — two minutes, and the questions we want

> **The arithmetic of two minutes.** A judge takes ~20 seconds to ask. Three to five questions fit. You
> cannot answer everything, so the job is not to be ready for everything — it is to **choose which four
> questions you get**. That is what this file engineers.

---

## 1. How the steering works

Three mechanisms, in order of power.

**① The three doors, on the closing slide.** You point at them while you sit down:

> "Ask us about the 60-second p95 tail, the E-09 failure, or what breaks at 100 desks."

Why it works: a judge with an open floor takes the offered menu. Each door opens onto a prepared answer
where **the weakness is already conceded and the fix is dated**. A judge who asks "what breaks at 100
desks" is handing you the scalability criterion to answer on your own terms.

**② The bridges.** Every prepared answer ends with a bridge into the next strength — "…and that is why
the gate sits on the commit and not on the score." Judges follow the last sentence they hear.

**③ The card.** Hand one to each judge as you finish (content in §5). It carries the six numbers and the
repo URL, so the detail questions get answered by the paper in their hand and the two minutes go to
judgement, not recall.

**What you are steering away from:** any question that implies the problem is not evidenced — it now is
(appendix A5) — and any question about a clinician who has not yet interviewed us.

---

## 2. The clock discipline

- **20 seconds, then stop.** Counting in your head: one sentence of answer, one number, one bridge.
- **Never answer two questions at once.** "That is two questions — the short version is X; ask me the
  second one next."
- **If a judge interrupts, let them.** The interruption tells you which part they care about; answer that
  part only.
- **Never fill silence.** The judge will use it, and their next question is usually easier.

---

## 3. The answer bank

### 3.1 Tool integration (30% — the criterion that decides ties)

**Q. Which integrations are live, and which are simulated?**
> Live: our nine-tool MCP server over stdio, the borrowed `mcp-sqlite` server, the LangGraph orchestrator,
> the local model, the audit chain — all in the run you just saw. Simulated: nothing. Replayed: the
> model's extraction on the offline fixture, and only when the model is cold. The tool calls are live
> either way.

*Bridge:* "Which is also why the log is the demo, not the slides."

**Q. Show us the tool-call log for the run we just watched.**
> *(run the query, don't describe it)* `SELECT seq, ts, case_id, tool, actor, approved_by, hash FROM audit …`
> Nine records, one per tool call, each hashed against the one above it, and `commit_priority` carries the
> approver's name. That is the same table a hospital auditor would read.

*Bridge:* "The queue row and the audit row are the same transaction — they cannot drift."

**Q. What happens if a tool times out or returns an error?**
> Three steps: a bounded retry, then a deterministic fallback, then a fail-closed terminal. A timeout
> commits nothing — there is no default approve and no invented value. The graph has a terminal state for
> "I could not finish", and reaching it is a correct outcome, not a crash.

**Q. What would it take to connect this to a real hospital system next week?**
> One adapter module. The graph depends on the tool *interface*, not on the adapter — that is a dependency
> inversion we built in deliberately. A queue/EMR write-back is a read and a gated write; an SMS or USSD
> gateway is a channel onto the same queue. The advisor-facing answer is a week per interface, because the
> clinical logic does not move.

**Q. Which actions need human approval, and where are credentials stored?**
> Exactly one action changes a queue: `commit_priority`, and it refuses without a named approval token —
> decision, timestamp, name, role, final colour. A deterioration flag raises a *second look* and cannot
> reorder anything. There are no credentials in the agent path at all: the model is local, the store is a
> local file, and the agent makes no outbound request. The one identity gap is that the approver's name is
> recorded, not authenticated — that is a badge or SSO before a real facility, and it is in the 90-day plan.

### 3.2 Problem relevance (20%)

**Q. Who exactly has this problem, and who did you speak to?**
> The triage nurse at a district-hospital OPD desk, and the senior clinician who signs her colour. For the
> *problem* I don't need a conversation — the peer-reviewed record is on slide 3 and appendix A5: nurses
> already run SATS, but on paper and by hand, and even trained staff miss the emergency calls about half
> the time (Wangara 2019, KNH). For the *fit*, how honest do you want me to be? **No clinician has reviewed
> our build yet.** I have the eight-question interview written and mapped to the code that makes each
> answer true — what I do not have is the signature. That is the first thing on the 90-day plan, and it is
> the reason we are asking for fifteen minutes with a nurse in this room.

*Bridge:* "So the problem is evidenced; the fit is the open loop, and we priced the work to close it."

**Q. What would make an institution refuse to adopt this?**
> Four things, and we have an answer for three. A colour with no visible reason — every colour carries the
> rule, the vital and the citation. Another screen at a busy desk — it is keyboard-first, one screen, tab
> order is DOM order. Data leaving the building — there is no egress. The fourth is real: an approver
> identity that is recorded but not authenticated, and I would not deploy without fixing it.

### 3.3 Feasibility & cost (20%)

**Q. How many tokens did the run use, and what did it cost?**
> 1,344 in, 146 out for one completed outcome — measured over 72 runs, digest-stamped. About three model
> calls, under two shillings (KES 1.88) at one desk with hardware, power and support included. The run you watched writes its
> own token and latency record; it is in `spans.jsonl`.

**Q. What was built during the event, and what was reused?**
> Built: the nine-tool server, the graph and its gate, the audit chain, the evaluation harness, the desk
> surface, 647 tests. Reused, and declared: the SATS scale, `mcp-sqlite`, LangGraph, Ollama, Qwen weights.
> Greenfield repo, first commit 9 October.

**Q. What happens on a weak connection, or over SMS?**
> The agent path needs no network — that is the point of a local model. SMS is a planned *channel*, not a
> transport for inference: the queue pushes a notification, the nurse still works at the desk. The one cost
> that grows linearly with patients is the per-message fee, and we would price it as a pass-through.

### 3.4 User value (15%)

**Q. Who signs the cheque, and from which budget line?**
> The hospital OPD budget, per desk — KES 6,000 a month. It is deliberately sized to be a line item a
> nurse-in-charge can sign, not a ministry procurement. That is a scope decision: a smaller sale that
> closes beats a bigger one that stalls.

**Q. If a donor funds the pilot, what happens when the grant ends?**
> The institutional price is already the price — KES 6,000, not a subsidised number. So the end of a
> grant is a budget decision, not a renegotiation. That is the only way a donor-funded pilot converts.

**Q. What evidence do you have that they will pay?**
> None signed. Ten structured price conversations and one signed pilot letter are the next thirty days, and
> I would rather show you an empty column than a number I invented.

### 3.5 Scale (15%)

**Q. What does the margin look like at 100×?**
> Fifty-six percent at a hundred desks, fifty-nine at ten. It compresses because we discount, not because
> the cost runs away: serve cost falls from KES 1.88 per outcome to KES 0.47.

**Q. What grows linearly with users?**
> The nurse's eight seconds — her time, not our cost. Support hours. And SMS fees, which is why that
> channel is priced separately. Nothing else on the curve is linear, which is why the margin holds.

**Q. Which institution is next, and could this travel to Central Africa?**
> I will not print a hospital's name before I have asked them, so the next adopter is a live conversation,
> not a logo. On travel: the clinical scale is data, not code — swapping SATS for a Francophone national
> scale is a YAML file. The real gate is multilingual intake and approver authentication, in that order.

### 3.6 The two questions that decide the score

**Q. Is this genuinely agentic, or a rules engine with an LLM bolted on?**
> Two layers with different authority. The model decides **how much to investigate** — gather evidence,
> ask a question, re-read the note, or stop — from four actions, inside a three-step budget, and a
> deterministic guard can veto it. It never decides **what the answer is**: no model vocabulary exists for
> the colour, the gate or the commit. And I publish the delta: on this suite the planner buys adaptive
> behaviour, not accuracy. It is in `docs/AGENTIC.md`, including that sentence.

*This is the strongest answer in the deck. It concedes the honest finding and still wins the criterion,
because a free agent could invent a colour and this one structurally cannot.*

**Q. What if the model gets it wrong?**
> The model never produces a number. It reads language; the colour is arithmetic on a published scale, and
> a vital it drops is recovered deterministically or the case stops. That is why E-09 — the case where we
> are wrong — asks a question instead of guessing. A wrong extraction costs us coverage, not safety.

---

## 4. When you do not know

Say exactly this, then bridge:

> "I don't know. Here is what I would measure to find out, and when I would have it."

Never invent a number, a hospital name, a clinician, or a citation. The rubric scores honesty explicitly,
and the repository is public — a judge can check every claim in ten seconds.

---

## 5. The card to hand over (print A6, one per judge)

```
TRIAGEDESK — the six numbers
─────────────────────────────────────────────
48/48   colour-expected runs correct, under-triage 0
24/24   priorities cite a rule, and reached the gate
1,344   tokens in / 146 out per outcome (72 runs)
3.1     model calls per outcome · 4 at worst
17.8 s  p50 · 60 s p95 · score itself is instant
KES 1.88 cost per outcome · KES 1.36 price · 56% margin

Live: our 9-tool MCP server + borrowed mcp-sqlite
Gate: one action writes a queue, and it needs a name
Offline: no network in the agent path, no egress

github.com/BrianMuigai/TriageDesk · Apache-2.0
uv run triagedesk demo
─────────────────────────────────────────────
```

---

## 6. The two-minute rehearsal, scored

Have someone read a question at random, and time you. You pass only if **all** of these are true:

| Test | Pass condition |
|---|---|
| Length | Every answer ≤ 25 seconds |
| Numbers | At least one specific number per answer |
| Concession | The E-09 or clinician question gets conceded in the first sentence |
| Bridge | Every answer ends by pointing at another criterion |
| No invention | You never name a hospital, a clinician, or a citation you do not have |
| Recovery | "I don't know" is said once without flinching |

Run it three times. The third run is the one you will actually give.
