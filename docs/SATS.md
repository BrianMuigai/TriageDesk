# SATS domain model — South African Triage Scale

> The clinical reference TriageDesk is built on. Source: **SATS Training Manual (2012), EMSSA**
> (<https://emssa.org.za>) plus published SATS validation studies.
> ⚠️ **Verification flag:** the tables below are transcribed from the manual during design. Before the
> scoring tool is relied upon, every band and every discriminator must be re-checked verbatim against
> the manual (Figures 2, 5, 12–14). Nothing here is a substitute for the published scale.

---

## 1. What SATS is

SATS turns a patient's **physiology** and **presenting complaint** into one of five colour-coded
priority levels. It has two parts:

1. a **Triage Early Warning Score (TEWS)** derived from vital signs, and
2. a list of **clinical discriminators** (specific presentations) that can *override* the TEWS colour.

The **final priority is the more urgent of** the TEWS colour and the highest discriminator category
found.

## 2. The five-step process (adult)

1. Look for **emergency signs** and ask the presenting complaint. If present → **Red**; take to resus;
   **do not calculate TEWS**.
2. Look for **very urgent signs** → **Orange** (still measure vitals and calculate TEWS).
3. Look for **urgent signs** → **Yellow** (still measure vitals and calculate TEWS).
4. Measure vital signs and **calculate TEWS**.
5. Match TEWS to its colour; apply discriminator overrides; check additional investigations; adjust for
   senior healthcare professional (SHCP) discretion.

## 3. Priority levels & target times (Table 3)

| Colour | Name | Target time to treatment | Destination |
| --- | --- | --- | --- |
| 🔴 **RED** | Emergency | **Immediate** | Resuscitation room |
| 🟠 **ORANGE** | Very urgent | **< 10 min** | Majors |
| 🟡 **YELLOW** | Urgent | **< 1 hour** | Majors |
| 🟢 **GREEN** | Routine / non-urgent | **< 4 hours** | Designated area |
| 🔵 **BLUE** | Deceased | **< 2 hours** | Doctor for certification |

## 4. Adult TEWS (age > 12 years, or > 150 cm)

Each parameter contributes 0–3 points. **Total = TEWS.**

| Parameter | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Mobility | Walking | With help | Stretcher / immobile | — |
| Respiratory rate | 9–14 | 15–20 | 21–29 | < 9 or ≥ 30 |
| Heart rate | 51–100 | 41–50 or 101–110 | 111–129 | < 41 or ≥ 130 |
| Systolic BP | 101–199 | 81–100 | 71–80 | < 71 or ≥ 200 |
| Temperature | 35.0–38.4 °C | — | < 35 or > 38.4 | — |
| AVPU | Alert | Reacts to voice | Reacts to pain | Unresponsive |
| Trauma | No | Yes | — | — |

### TEWS → colour

| TEWS total | Colour |
| --- | --- |
| **0, 1, 2** | 🟢 Green (routine) |
| **3 or 4** | 🟡 Yellow (urgent) |
| **5 or 6** | 🟠 Orange (very urgent) |
| **7 or more** | 🔴 Red (emergency) |

### 4.1 Vitals coverage (fidelity note)

The brief lists vitals as *"blood pressure, pulse, temperature, respiratory rate, oxygen saturation."*
Adult SATS TEWS scores only **systolic blood pressure**, pulse, temperature and respiratory rate (plus
mobility, AVPU and trauma). It does **not** score:

- **oxygen saturation (SpO₂)** — captured and logged as an input vital, but **not** part of the adult
  TEWS, so it does not change the colour; and
- **diastolic blood pressure** — captured, unused by TEWS.

TriageDesk records every vital the nurse enters (including SpO₂) on the case card and in the audit
trail, but the **score is computed only from what SATS defines**. This is deliberate: adding an SpO₂
weighting would be *inventing a scale*, which the brief forbids.

## 5. Clinical discriminators (adult)

Discriminators override TEWS: the most urgent category present wins.

### Emergency (→ Red)
- Obstructed airway — not breathing
- Seizure — current
- Burn — facial / inhalation
- Hypoglycaemia — glucose < 3 mmol/L
- Cardiac arrest
- AVPU responds only to **pain** or **unresponsive**
- Confusion

### Very urgent (→ Orange)
High-energy transfer (severe mechanism) · acute shortness of breath · reduced level of
consciousness/confused · coughing blood · chest pain · stabbed neck · uncontrolled haemorrhage
(arterial) · seizure (post-ictal) · acute focal neurology (stroke) · aggression · threatened limb ·
eye injury · dislocation of a larger joint · compound fracture · burn > 20% · electrical burn ·
circumferential burn · chemical burn · poisoning/overdose · diabetic glucose > 11 with ketonuria ·
vomiting fresh blood · pregnancy with abdominal trauma · pregnancy with abdominal pain · severe pain

### Urgent (→ Yellow)
Persistent vomiting · pregnancy with trauma · pregnancy with PV bleed · moderate pain · controlled
haemorrhage · dislocation of finger/toe · closed fracture · other burns · abdominal pain · diabetic
glucose > 17 without ketonuria

> Additional investigations (e.g. finger-prick glucose, urine ketones) and SHCP discretion are part of
> the full chart; they are **stretch** items for TriageDesk (`PROJECT.md` §6).

## 6. Paediatric SATS (out of scope → abstain)

Children use age-banded charts (younger child < 3 y / < 95 cm; older child 3–12 y / 95–150 cm) with
different TEWS bands and clinical signs. **TriageDesk does not score children**: on detecting a
paediatric or otherwise out-of-scope presentation it **abstains and escalates to a human**
(`DECISIONS.md` D6, eval case E-06).

## 7. How TriageDesk encodes SATS

| File | Contents |
| --- | --- |
| `data/sats_tews.yaml` | parameter → bands → points; plus TEWS→colour thresholds |
| `data/sats_discriminators.yaml` | discriminator → category (Emergency/Very Urgent/Urgent) → citation |
| `docs/SATS.md` | this reference (human-readable) |

The **deterministic scorer** (`score_priority`) reads the YAML and returns, for any case, the colour,
the TEWS total, the list of triggered rules, and a citation per rule. The model never overrides these.

## 8. Citations

- SATS Training Manual 2012, Emergency Medicine Society of South Africa (EMSSA).
- SATS validation literature (e.g. *Validity and reliability of the South African Triage Scale in
  low-resource settings*; *A multicentre validation of the revised South African Triage Scale*).
