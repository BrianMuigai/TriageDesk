# UNIT ECONOMICS — the working behind every number in the deck

> **Why this file exists.** The judging rubric scores *cost per completed outcome*, *who pays*, *what
> they will pay*, and *margin at 10× and 100×*. A deck that asserts those numbers is worth nothing. This
> page shows the arithmetic in **Kenyan shillings (KES)**, names which inputs are **measured** and which
> are **assumptions**, and states where the model breaks.
>
> **Currency.** All figures are in KES. For cross-checking, ≈ **KES 129 = US$1** (approximate; the
> arithmetic does not depend on the exact rate — every number here is a local KES figure, not a conversion).
>
> Measured anchors come from `evals/results/report.json` (digest `0ae3dde6…`, 24 cases × 3 runs).
> Assumptions are the team's own and can be changed — the arithmetic is a spreadsheet, not a claim.

---

## 1. The two measured anchors

| Anchor | Value | Source |
|---|---|---|
| Tokens per completed outcome | **1,344 in / 146 out** | `report.json` — 96,747 / 10,491 tokens over 72 runs |
| Model calls per outcome | **3.1 mean · 4 worst** | 1 extraction + 2.1 mean plan steps; the planner is hard-capped at 3 steps |
| Latency | **p50 17.8 s · p95 60 s** | same report, 72 runs, local CPU |
| Inference cost per outcome | **KES 0.00** | local model: no per-token fee, no egress |

Nothing else in this file is measured. Everything below is an assumption with a stated basis.

## 2. The assumptions

| Input | Value | Basis |
|---|---|---|
| Patients per desk per day | 200 | A busy district-OPD morning plus afternoon |
| Working days per month | 22 | Standard |
| Outcomes per desk per month | 4,400 | 200 × 22 |
| Hardware | KES 70,000, amortised over 36 months → **KES 1,944/month** (KES 60,000 at 100× → **KES 1,667**) | One mini-PC that holds the measured latency |
| Power | 65 W × 8 h × KES 27/kWh × 22 days → **KES 309/month** | Kenya Power small-commercial tariff |
| Support | 3 h (pilot) · 0.2 h (10×) · 0.05 h (100×) per desk/month at KES 2,000/h | Deployment and hand-holding, then centralised |
| Nurse confirmation | 8 s per case at KES 400/h loaded | **Not incremental** — she triages either way |

## 3. Cost to serve one completed outcome

Cost per outcome = `(hardware ÷ 36 + power + support) ÷ 4,400`

| | Hardware | Power | Support | Total / month | **Cost / outcome** |
|---|---|---|---|---|---|
| Pilot · 1 desk | 1,944 | 309 | 6,000 | 8,253 | **KES 1.88** |
| 10 desks | 1,944 | 309 | 400 | 2,653 | **KES 0.60** |
| 100 desks | 1,667 | 309 | 100 | 2,076 | **KES 0.47** |

The pilot is genuinely more expensive per outcome — one engineer holding one nurse's hand. That is the
honest shape of an early deployment, and the deck shows it rather than starting the curve at 10×.

**What grows linearly:** nurse confirmation (8 s, the customer's time), support hours, SMS fees if that
channel is added. **What falls:** hardware amortisation, support per desk. **What never appears:** a
per-token bill.

## 4. Price and margin

| | Pilot | 10 desks | 100 desks |
|---|---|---|---|
| Price / desk / month | KES 0 (design partner) | KES 6,000 | KES 4,800 |
| Price / outcome | — | KES 1.36 | KES 1.09 |
| Cost / outcome | KES 1.88 | KES 0.60 | KES 0.47 |
| **Margin / outcome** | — | **56%** | **57%** |
| Margin / desk / month | −KES 8,253 | +KES 3,347 | +KES 2,724 |

Price ÷ 4,400 outcomes: `6,000 ÷ 4,400 = KES 1.36`. Margin: `(6,000 − 2,653) ÷ 6,000 = 55.8% → 56%`.

**The curve does not improve at 100×.** It compresses slightly, because we discount the list price. That
is deliberate: a margin that *falls* with a volume discount and *holds* above 55% is a business. A margin
that magically rises is a slide.

## 5. The value side (criterion 4)

- Today: **15–45 s** per patient to choose a colour, from memory, under load. Midpoint 30 s.
- With TriageDesk: **17.8 s p50** to a cited draft, **8 s** to confirm or edit → ~10 s of nurse attention
  after the draft lands.
- Saving: **~20 s per patient** → 200 patients = **66.7 min per desk-day** → **24.4 h/month** →
  **≈ KES 9,800/month** at KES 400/h.
- Per outcome: `20 s × 400 ÷ 3,600 = **KES 2.22**` of nurse time saved.
- Price per outcome: **KES 1.36**. The hospital keeps **KES 0.86 per outcome (~39%)** from day one, before
  counting any clinical risk that is caught earlier.

### Where this argument breaks — say this before a judge does

The nurse-time case is **volume-dependent**. At KES 6,000/desk/month the break-even is:

`6,000 ÷ (2.22 × 22) = **123 patients per desk-day**`

Below ~120 patients a day, the minutes saved no longer cover the price, and the case has to rest on the
thing the minutes are a proxy for: an urgent patient surfaced at the desk instead of after the wait. Two
responses, both honest:

1. **Price per outcome** instead of per desk below that volume (`KES 1.40` an outcome, no floor).
2. **Do not sell to a quiet desk.** A 40-patient rural clinic is a different product, and we would say so.

## 6. The comparison we did not hide

A hosted frontier API would cost **less in cash at one desk** — fractions of a shilling of tokens per
outcome against KES 1.88 of amortised hardware. We chose the local 1.5B model anyway, for three reasons
that are not in the cash column:

1. **Data cannot leave the facility** — a hard requirement, and an instant disqualifier if broken.
2. **The agent must run when the network does not.** A desk that stops working during a power or link
   outage is not a triage tool.
3. **At 100 desks the fixed cost is KES 0.47 per outcome** and the marginal cost of the next patient is
   electricity — there is no bill that grows with a bad month.

If a judge prefers the API maths, the answer is: *"At one desk you are right. We are not selling one
desk forever, and we are not allowed to send a patient's vitals to a provider."*

## 7. What would change these numbers

| Change | Effect |
|---|---|
| `qwen2.5:1.5b` → `qwen3.5:4b` | Better extraction, ~3× the wall-clock on this host; tokens per outcome unchanged, cost unchanged (local) |
| Desk precompute cache already shipped | Removes the model call when the nurse is still typing vitals — the lever that moves p95 |
| Fewer planner steps | 3.1 → 2.0 calls saves ~35% of compute, not cash |
| Authenticated approver (SSO/badge) | Adds ~KES 130–390/desk/month in identity cost; non-negotiable before a real facility |
| SMS channel | Adds a real per-message cost — the only line that scales linearly with patients |

## 8. Sources

- `evals/results/report.json` — tokens, latency, coverage, digest `0ae3dde6ca3f…` (measured).
- `docs/PROJECT.md` §3.1 — the assumption-labelled desk-time model this file extends.
- `STATUS.md` §5 — the declared gaps (G3 latency tail, G4 approver authentication, G9 single-machine desk).
