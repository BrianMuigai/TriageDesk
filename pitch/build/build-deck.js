// Build the TriageDesk pitch deck.
//
//   node pitch/build/build-deck.js
//
// Everything on the slides comes from two places: the measured evaluation report
// (evals/results/report.json, digest 0ae3dde6…) and the unit-economics sheet
// (pitch/UNIT-ECONOMICS.md). Where a figure is an assumption it is labelled as one
// on the slide. Nothing here is a number nobody can trace.

const path = require("path");
const pptxgen = require("/tmp/opencode/node_modules/pptxgenjs");
const { applyTheme } = require(
  "/home/brian/.claude/skills/synced/ae38753c-5e5b-4688-a2af-d2c4c1efd85f_4cc50d69-9e7e-490f-9b64-6bc6d4c682f2/pptx/scripts/apply_theme.js",
);
const S = require("./deck-system");

const { P, T, W, H, M, CW, THEME } = S;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "TriageDesk";
pres.subject = "African Agentic AI Design Challenge — Nairobi edition";
pres.title = "TriageDesk — sourced, nurse-approved triage";
pres.company = "TriageDesk";
pres.theme = { headFontFace: T.head, bodyFontFace: T.body };

const OUT = path.join(__dirname, "..", "TriageDesk-Pitch.pptx");

// Every text frame anchors to the top unless it explicitly asks for middle. pptxgenjs
// centres text vertically by default, which silently pushes body copy down inside tall
// boxes and makes the deck look mis-aligned.
function addT(slide, text, opts = {}) {
  slide.addText(text, { valign: "top", margin: 0, ...opts });
}



// ---------------------------------------------------------------- slide helpers

function newSlide(section, n, active = -1) {
  const slide = pres.addSlide();
  S.ground(slide, pres);
  S.footer(slide, section, n, active);
  return slide;
}

function mono(slide, text, o) {
  slide.addShape("roundRect", {
    x: o.x,
    y: o.y,
    w: o.w,
    h: o.h,
    fill: { color: "0A1316" },
    line: { color: P.line, width: 1 },
    rectRadius: 0.06,
  });
  slide.addText(text, {
    x: o.x + 0.18,
    y: o.y + 0.1,
    w: o.w - 0.36,
    h: o.h - 0.2,
    fontFace: "Courier New",
    fontSize: o.size || 11,
    color: P.textDim,
    margin: 0,
    valign: "middle",
    isTextBox: true,
  });
}

// ============================================================ 1. COVER ========
{
  const s = pres.addSlide();
  s.background = { color: P.ink };
  s.addImage({
    path: path.join(__dirname, "..", "assets", "cover.jpg"),
    x: 0,
    y: 0,
    w: W,
    h: H,
  });

  // The artwork is the cover. Keep the challenge identity and repository visible in
  // the dark band at the very bottom, without competing with the designed title.
  addT(s, "Brian Muigai   ·   Apache-2.0   ·   github.com/BrianMuigai/TriageDesk   ·   one command from a clean clone", {
    x: M,
    y: H - 0.26,
    w: CW,
    h: 0.18,
    fontFace: T.body,
    fontSize: 8,
    color: "D7FFF6",
    transparency: 15,
    margin: 0,
    isTextBox: true,
  });

  s.addNotes(
    "0:00 — 6 seconds. Warm, not rehearsed.\n\n" +
      "Good morning. I'm Brian Muigai. This is TriageDesk — the triage scale your nurses already know, without the paper. " +
      "It gives a triage nurse a sourced, nurse-approved priority in the time it takes to write a card.\n\n" +
      "Five minutes: a problem you'll recognise, a fix you can watch, a price you can afford.",
  );
}

// ============================================================ 2. HOOK ==========
{
  const s = newSlide("The hook", 2, 1);

  S.eyebrow(s, "The problem — in one number");
  S.title(s, "Your nurses already use SATS.\nThey do it on a paper chart, by hand.", { size: 34, lines: 2 });

  addT(s, "51%", {
    x: M, y: 2.5, w: 4.2, h: 1.1,
    fontFace: T.head, fontSize: 72, bold: true, color: P.orange, margin: 0, isTextBox: true,
  });
  addT(s, "of emergency calls matched the expert standard, even after training — Wangara 2019, KNH", {
    x: M, y: 3.62, w: 4.2, h: 0.95,
    fontFace: T.body, fontSize: 13, color: P.muted, margin: 0, isTextBox: true,
  });

  addT(s,
    [
      { text: "Not because nurses are careless.\n\n", options: { color: P.text, bold: true } },
      { text: "Because the most important decision of the morning — who is actually dying — is being asked of a skilled human with a pen, a paper chart, and nineteen people behind her.\n\n", options: { color: P.textDim } },
      { text: "SATS is right. The paper is the problem.", options: { color: P.accent, bold: true, italic: true } },
    ],
    { x: 5.6, y: 2.55, w: 7.1, h: 3.3, fontFace: T.body, fontSize: 17, lineSpacingMultiple: 1.28, margin: 0, isTextBox: true },
  );

  addT(s, "Wangara et al., Int J Emerg Med 2019 — SATS at Kenyatta National Hospital. Full sources: appendix A5.", {
    x: M, y: 6.3, w: 11, h: 0.3, fontFace: T.body, fontSize: 10, italic: true, color: P.muted, margin: 0, isTextBox: true,
  });

  s.addNotes(
    "0:06 — 30 seconds.\n\n" +
      "Here is the honest framing, because I will not insult your nurses. They are trained. They run SATS already — it is the best triage scale in low-resource care, and it is proven. The problem is the delivery: it lives on a paper chart, worked out by hand, in seconds, with a queue behind her.\n\n" +
      "And here is the part that should worry you: in the study that validated SATS at Kenyatta National Hospital, trained staff matched the expert on the emergency calls only 51% of the time. Not because they are careless. Because the single most important decision of the morning is being asked of a human with a pen.\n\n" +
      "SATS is right. The paper is the problem.",
  );
}

// ============================================================ 3. PROBLEM ======
{
  const s = newSlide("Problem relevance", 3, 3);

  S.eyebrow(s, "Criterion 2 · problem relevance and local insight");
  S.title(s, "The scale is right. The delivery is 2015.", { size: 34, lines: 2 });

  const stats = [
    ["15–45 s", "to work the paper SATS chart by hand,\nfrom memory, while the queue grows"],
    ["0", "record of why — no citation, no name,\nno audit trail behind the colour"],
    ["64%", "agreement on a case even after training;\nthe human, not the scale, is the weak link"],
  ];
  stats.forEach(([v, l], i) => {
    S.stat(s, { x: M + i * 4.05, y: 2.12, w: 3.75, value: v, label: l, vsize: 34, hvalue: 0.62 });
  });

  const checks = [
    ["Named user", "A triage nurse at a district-hospital OPD desk — and the SHCP who signs the colour."],
    ["Sized", "69,000 A&E visits a year at one hospital — and 47 county referral hospitals across Kenya, with no national triage standard."],
    ["Today's workaround", "The paper SATS chart: colour worked out by hand, written top-right, queue by arrival."],
    ["Local reality", "One shared PC, weak network, English intake, patient data must not leave the building."],
    ["Why not a form", "A form cannot read a free-text complaint; a chatbot cannot write a queue under a name."],
    ["Evidence", "Wangara 2019 (KNH) + SATS (EMSSA 2012). The scale is validated; the delivery is not."],
  ];

  const cw = (CW - 0.44) / 3;
  checks.forEach(([label, body], i) => {
    const x = M + (i % 3) * (cw + 0.22);
    const y = 3.42 + Math.floor(i / 3) * 1.62;
    S.card(s, { x, y, w: cw, h: 1.44 });
    addT(s, label.toUpperCase(), { x: x + 0.22, y: y + 0.16, w: cw - 0.44, h: 0.26, fontFace: T.body, fontSize: 10, bold: true, color: P.accent, charSpacing: 1.2, margin: 0, isTextBox: true });
    addT(s, body, { x: x + 0.22, y: y + 0.46, w: cw - 0.44, h: 0.86, fontFace: T.body, fontSize: 13, color: P.textDim, margin: 0, isTextBox: true });
  });

  addT(s, "Wangara et al., Int J Emerg Med 2019 — SATS at Kenyatta National Hospital. Full sources: appendix A5.", {
    x: M, y: 6.62, w: 11, h: 0.3, fontFace: T.body, fontSize: 10, italic: true, color: P.muted, margin: 0, isTextBox: true,
  });

  s.addNotes(
    "0:35 — 30 seconds.\n\n" +
      "Here is the gap, and it is not a skills gap. Your nurses already run SATS — they are trained, they are good. But it lives on a paper chart, and a paper chart does three things badly: it is slow, it leaves no record of why a colour was chosen, and it asks the most critical call of the day — the emergency — of a tired human at 07:40.\n\n" +
      "A form cannot read the complaint. A chatbot cannot write the queue under a name. That is why this is an agent.",
  );
}

// ============================================================ 4. SOLUTION ====
{
  const s = newSlide("The solution", 4, 0);

  S.eyebrow(s, "What we built — in one glance");
  S.title(s, "We did not invent triage.\nWe put the validated one on the desk.", { size: 32, lines: 2 });

  const pillars = [
    ["Sourced", "Every colour cites the exact rule, vital and discriminator behind it. An unsourced urgency flag is a system failure, not a feature."],
    ["Offline", "A 1.5B open model on local CPU. No network, no egress — it keeps running when the link does not."],
    ["Gated", "Exactly one action writes the queue, and it refuses without a named nurse or clinician."],
  ];
  const cw = (CW - 0.44) / 3;
  pillars.forEach(([h, b], i) => {
    const x = M + i * (cw + 0.22);
    S.card(s, { x, y: 2.5, w: cw, h: 2.3, fill: i === 1 ? P.surfaceUp : P.surface, line: i === 1 ? "2A4A46" : P.line });
    addT(s, h.toUpperCase(), { x: x + 0.24, y: 2.68, w: cw - 0.48, h: 0.3, fontFace: T.body, fontSize: 12, bold: true, color: P.accent, charSpacing: 1.4, margin: 0, isTextBox: true });
    addT(s, b, { x: x + 0.24, y: 3.06, w: cw - 0.48, h: 1.6, fontFace: T.body, fontSize: 13, color: P.textDim, margin: 0, isTextBox: true });
  });

  addT(s, "It scores or sequences. It never diagnoses, never prescribes, and never moves a patient on its own.", {
    x: M, y: 5.14, w: CW, h: 0.4, fontFace: T.head, fontSize: 17, italic: true, color: P.text, margin: 0, isTextBox: true,
  });

  s.addNotes(
    "1:05 — 25 seconds.\n\n" +
      "Here is the whole product in one glance. We did not invent a new triage system — the medicine is settled. We put the validated South African Triage Scale on the desk. Three things make it safe: every colour is sourced, the model is offline so data never leaves the building, and the one action that can move a patient is gated behind a named nurse or clinician.\n\n" +
      "Now watch it work.",
  );
}

// ============================================================ 5. DEMO =========
{
  const s = newSlide("Live demo", 5, 2);

  S.eyebrow(s, "Criterion 1 · tool integration — 30%");
  S.title(s, "Watch the log, not the screen", { size: 38 });
  S.deck(s, "Four things to score while it runs. Every line below is written to the audit chain as it happens.");

  const beats = [
    ["01", "Three tools, one outcome", "Complaint → discriminators → cited evidence → score. Chained, not prompted."],
    ["02", "A tool that refuses", "Missing temperature: it asks for a re-measure and fabricates nothing."],
    ["03", "No name, no queue row", "The same case twice: once approved, once refused by the gate."],
    ["04", "A failure we publish", "E-09, vague complaint: clarified, never coloured. It is in EVALS.md §6."],
  ];
  beats.forEach(([n, head, sub], i) => {
    const y = 2.62 + i * 0.98;
    addT(s, n, {
      x: M,
      y: y - 0.06,
      w: 0.7,
      h: 0.5,
      fontFace: T.head,
      fontSize: 24,
      bold: true,
      color: P.accent,
      margin: 0,
      isTextBox: true,
    });
    addT(s, head, {
      x: M + 0.78,
      y,
      w: 7.4,
      h: 0.34,
      fontFace: T.body,
      fontSize: 16,
      bold: true,
      color: P.text,
      margin: 0,
      isTextBox: true,
    });
    addT(s, sub, {
      x: M + 0.78,
      y: y + 0.33,
      w: 7.5,
      h: 0.32,
      fontFace: T.body,
      fontSize: 12.5,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    });
  });

  const cx = 8.62;
  S.card(s, { x: cx, y: 2.42, w: 4.06, h: 3.86, fill: P.surfaceUp });
  addT(s, "RUNNING NOW", {
    x: cx + 0.24,
    y: 2.58,
    w: 3.6,
    h: 0.26,
    fontFace: T.body,
    fontSize: 10,
    bold: true,
    color: P.accent,
    charSpacing: 1.3,
    margin: 0,
    isTextBox: true,
  });
  const runLines = [
    "E-02  escalated vitals  →  ORANGE",
    "E-02  no approver       →  REFUSED",
    "E-07  serial vitals     →  recheck",
    "E-09  vague complaint   →  clarified",
  ];
  runLines.forEach((t, i) => {
    addT(s, t, {
      x: cx + 0.24,
      y: 2.94 + i * 0.38,
      w: 3.6,
      h: 0.3,
      fontFace: "Courier New",
      fontSize: 11.5,
      color: i === 3 ? P.yellow : P.textDim,
      margin: 0,
      isTextBox: true,
    });
  });
  addT(s, 
    "The same SATS flow KNH validated (Wangara 2019) — plus the audit table for the run you just watched.",
    {
      x: cx + 0.24,
      y: 4.58,
      w: 3.6,
      h: 0.8,
      fontFace: T.body,
      fontSize: 12,
      italic: true,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    },
  );
  mono(s, "SELECT seq, tool, actor, approved_by\nFROM audit ORDER BY seq DESC LIMIT 10;", {
    x: cx + 0.24,
    y: 5.42,
    w: 3.58,
    h: 0.62,
    size: 9.5,
  });

  s.addNotes(
    "1:30 — 2 minutes 10. Run it, narrate only the four beats. Do not narrate the animation.\n\n" +
      "Beat 1, escalation: watch the log at the bottom — match_discriminators, then retrieve_evidence, then score_priority. Three tools, one answer, and the citation names the rule.\n\n" +
      "Beat 2, refusal: same patient, same colour, no name on the approval. The gate refuses and no queue row is written. That refusal is the product.\n\n" +
      "Beat 3, deterioration: serial vitals cross a threshold while the patient waits. It raises a second look. It does not re-classify and it does not reorder the queue.\n\n" +
      "Beat 4, the failure: E-09. Vague complaint, known diabetic. We expected ORANGE. We get a bounded clarification, not a colour. It is published as a failure.\n\n" +
      "Fallback: if the model is cold, drop --online and say so. The tool calls are live either way.",
  );
}

// ============================================================ 6. INTEGRATION ==
{
  const s = newSlide("Integration", 6, 1);

  S.eyebrow(s, "Criterion 1 · what is live, what is sandbox, what is planned");
  S.title(s, "Two MCP servers. Nine tools. Three that act.\nOne that can write.", { size: 32, lines: 2 });

  const cols = [
    {
      label: "Live now",
      colour: P.accent,
      items: [
        "Owned triage server — 9 tools over stdio",
        "Borrowed mcp-sqlite 1.0.9 — read paths exercised",
        "LangGraph orchestrator, explicit graph, no ReAct",
        "Local qwen2.5:1.5b via Ollama, offline",
        "Hash-chained audit in the same store as the queue",
      ],
    },
    {
      label: "Sandbox",
      colour: P.muted,
      items: [
        "Nothing in this demo is mocked.",
        "The only replay is the model's extraction on the offline fixture.",
        "Every tool call above is a live stdio MCP call.",
      ],
    },
    {
      label: "Planned",
      colour: P.orange,
      items: [
        "Hospital records — DHIS2 / OpenMRS, HL7 FHIR",
        "SMS and USSD via Africa’s Talking",
        "French and local-language intake",
      ],
    },
  ];

  const cw = (CW - 0.44) / 3;
  cols.forEach((c, i) => {
    const x = M + i * (cw + 0.22);
    S.card(s, { x, y: 2.72, w: cw, h: 2.72, fill: i === 0 ? P.surfaceUp : P.surface });
    S.columnHead(s, x + 0.24, 2.9, cw - 0.48, c.label, c.colour);
    S.bullets(s, c.items, {
      x: x + 0.24,
      y: 3.26,
      w: cw - 0.46,
      h: 2.0,
      size: 12.5,
      gap: 7,
    });
  });

  S.card(s, { x: M, y: 5.62, w: CW, h: 1.06, fill: "142A2A", line: "2A4A46" });
  addT(s, 
    [
      {
        text: "If a tool times out: ",
        options: { bold: true, color: P.text },
      },
      {
        text: "bounded retry → deterministic fallback → a fail-closed terminal. No default approve, no invented value.   ",
        options: { color: P.textDim },
      },
      {
        text: "To connect real systems next week: ",
        options: { bold: true, color: P.text },
      },
      {
        text: "one adapter: DHIS2 or OpenMRS over FHIR. The graph binds to the tool interface, not the adapter.",
        options: { color: P.textDim },
      },
    ],
    {
      x: M + 0.26,
      y: 5.72,
      w: CW - 0.52,
      h: 0.86,
      fontFace: T.body,
      fontSize: 13,
      margin: 0,
      valign: "middle",
      isTextBox: true,
    },
  );

  s.addNotes(
    "3:40 — 18 seconds.\n\n" +
      "Left column is running: our server, the borrowed SQLite server, the graph, the local model, the audit chain. Middle column is empty on purpose — nothing here is mocked. The one replay is the model's extraction on the offline fixture, and we say so before you ask. Right column is what we have not built, and what it costs to build: one adapter module, because the graph depends on the tool interface, not on the adapter.",
  );
}

// ============================================================ 7. COST =========
{
  const s = newSlide("Cost to serve", 7, 0);

  S.eyebrow(s, "Criterion 3 · feasibility and cost to serve");
  S.title(s, "1,344 tokens. 3.1 model calls. Under KES 2.", { size: 34 });

  const stats = [
    ["1,344 / 146", "tokens in / out for one completed outcome — measured, 72 runs, digest-stamped"],
    ["3.1", "model calls per outcome: 1 extraction + 2.1 bounded plan steps, 4 at worst"],
    ["17.8 s", "p50 to a cited draft; 60 s p95 on a loaded CPU. The score itself is instant."],
  ];
  stats.forEach(([v, l], i) => {
    S.stat(s, {
      x: M + i * 4.05,
      y: 1.86,
      w: 3.8,
      value: v,
      label: l,
      vsize: 30,
      hvalue: 0.56,
    });
  });

  s.addChart(
    pres.ChartType.bar,
    [
      {
        name: "KES per completed outcome",
        labels: ["Pilot · 1 desk", "10 desks", "100 desks"],
        values: [1.88, 0.60, 0.47],
      },
    ],
    {
      x: M - 0.05,
      y: 2.95,
      w: 6.1,
      h: 3.2,
      barDir: "col",
      barGapWidthPct: 62,
      showLegend: false,
      showTitle: true,
      title: "Cost to serve one completed outcome — KES",
      titleFontFace: "+mn-lt",
      titleFontSize: 12,
      titleColor: P.textDim,
      chartColors: [P.orange, P.accent, P.accent],
      showValue: true,
      dataLabelPosition: "outEnd",
      dataLabelColor: P.text,
      dataLabelFontFace: "+mn-lt",
      dataLabelFontSize: 12,
      dataLabelFormatCode: "0.00",
      catAxisLabelFontFace: "+mn-lt",
      catAxisLabelFontSize: 11,
      catAxisLabelColor: P.muted,
      catAxisLineShow: false,
      valAxisLabelFontFace: "+mn-lt",
      valAxisLabelFontSize: 10,
      valAxisLabelColor: P.muted,
      valAxisMinVal: 0,
      valAxisMaxVal: 2.0,
      valAxisMajorUnit: 0.5,
      valAxisLineShow: false,
      valGridLine: { color: "23373B", size: 1 },
      catGridLine: { style: "none" },
    },
  );

  S.bullets(
    s,
    [
      "No per-token fee and no egress: the model is local, so the marginal cost of one more patient is electricity.",
      "What falls with volume: hardware amortisation and support hours per desk. What does not: power, and the nurse's 8 seconds.",
      "Levers already in the build: a 1.5B CPU model, a desk precompute cache, a hard 3-step planner budget, structured JSON instead of retries.",
    ],
    { x: 7.05, y: 3.0, w: 5.6, h: 2.6, size: 13, gap: 10 },
  );

  addT(s, 
    "A hosted API would cost less in cash at one desk. We did not choose it: patient data cannot leave the facility, and the agent must run when the network does not.",
    {
      x: 7.05,
      y: 5.62,
      w: 5.6,
      h: 0.9,
      fontFace: T.body,
      fontSize: 12,
      italic: true,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    },
  );

  s.addNotes(
    "3:58 — 16 seconds.\n\n" +
      "One outcome — a patient with a cited, approved priority — costs 1,344 tokens in and 146 out, about three model calls, and under two shillings at one desk (KES 1.88), hardware, power and support included. At a hundred desks it is under half a shilling (KES 0.47).\n\n" +
      "The model calls are bounded by construction: one extraction, at most three planning decisions. That is the number we control.",
  );
}

// ============================================================ 8. VALUE ========
{
  const s = newSlide("User value", 8, 1);

  S.eyebrow(s, "Criterion 4 · user value and willingness to pay");
  S.title(s, "We charge KES 1.36 for KES 2.22\nof nurse time.", { size: 34, lines: 2 });

  S.card(s, { x: M, y: 2.62, w: 5.86, h: 2.04 });
  S.columnHead(s, M + 0.26, 2.8, 5.3, "Today, at the desk", P.muted);
  S.bullets(
    s,
    [
      "15–45 s per patient to choose a colour, worsening as the queue grows",
      "Urgency surfaces when she physically reaches the card",
      "No record of why a colour was chosen",
      "The paper card, not a screen, is the system of record",
    ],
    { x: M + 0.26, y: 3.16, w: 5.34, h: 1.6, size: 13, gap: 8 },
  );

  S.card(s, { x: M + 6.17, y: 2.62, w: 5.86, h: 2.04, fill: P.surfaceUp, line: "2A4A46" });
  S.columnHead(s, M + 6.43, 2.8, 5.3, "With TriageDesk", P.accent);
  S.bullets(
    s,
    [
      "17.8 s p50 to a cited draft; 8 s to confirm or edit it",
      "≈ 20 s saved per patient → 66 min per desk-day",
      "Every colour carries the rule, the vital and the approver",
      "Approving, editing or dismissing is one keystroke",
    ],
    { x: M + 6.43, y: 3.16, w: 5.34, h: 1.6, size: 13, gap: 8 },
  );

  const blocks = [
    ["Who pays", "The county health budget or the facility’s own improvement fund — a line a nurse-in-charge can sign, not a ministry HQ procurement."],
    ["The price", "KES 6,000 per desk per month — KES 1.36 per outcome, less than one nurse-hour per working day."],
    [
      "What we can show",
      "No signed price conversation yet. That is the honest gap. Next 30 days: 10 structured price questions with nurse-in-charges and one signed pilot letter.",
    ],
  ];
  const bw = (CW - 0.44) / 3;
  blocks.forEach(([label, body], i) => {
    const x = M + i * (bw + 0.22);
    S.card(s, { x, y: 4.94, w: bw, h: 1.62, fill: i === 2 ? "2A1E14" : P.surface, line: i === 2 ? "5A3A22" : P.line });
    addT(s, label.toUpperCase(), {
      x: x + 0.22,
      y: 5.1,
      w: bw - 0.44,
      h: 0.26,
      fontFace: T.body,
      fontSize: 10,
      bold: true,
      color: i === 2 ? P.orange : P.accent,
      charSpacing: 1.2,
      margin: 0,
      isTextBox: true,
    });
    addT(s, body, {
      x: x + 0.22,
      y: 5.42,
      w: bw - 0.44,
      h: 1.05,
      fontFace: T.body,
      fontSize: 12,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    });
  });

  s.addNotes(
    "4:14 — 18 seconds.\n\n" +
      "The value is time and attention, not a diagnosis. Twenty seconds a patient, two hundred patients, is an hour and ten minutes of a nurse's day — about KES 9,800 a month. We charge KES 6,000. The hospital keeps the rest, from day one.\n\n" +
      "And I will say the awkward part before you do: we have not signed a price yet. Ten nurse-in-charge price conversations and one signed pilot letter is the next thirty days.",
  );
}

// ============================================================ 9. SCALE ========
{
  const s = newSlide("Scale", 9, 0);

  S.eyebrow(s, "Criterion 5 · scalability and sustainable impact");
  S.title(s, "The margin holds, because only the nurse's\n8 seconds grows linearly.", { size: 32, lines: 2 });

  const rows = [
    [
      { text: "Per desk", options: { bold: true } },
      { text: "Pilot · 1 desk", options: { bold: true } },
      { text: "10 desks", options: { bold: true } },
      { text: "100 desks", options: { bold: true } },
    ],
    ["Price per desk / month", "KES 0 — design partner", "KES 6,000", "KES 4,800"],
    ["Cost to serve / outcome", "KES 1.88", "KES 0.60", "KES 0.47"],
    ["Price / outcome", "—", "KES 1.36", "KES 1.09"],
    ["Margin / outcome", "—", "56%", "57%"],
  ].map((r, ri) =>
    r.map((c, ci) => {
      const o = typeof c === "string" ? { text: c } : c;
      return {
        text: o.text,
        options: {
          fontFace: T.body,
          fontSize: ri === 0 ? 12 : 13,
          color: o.options?.bold ? P.text : ci === 0 ? P.muted : P.textDim,
          bold: !!o.options?.bold,
          fill: { color: ri === 0 ? "14262A" : ri % 2 ? P.surface : "1A2C31" },
          align: ci === 0 ? "left" : "center",
          valign: "middle",
          margin: 8,
        },
      };
    }),
  );

  s.addTable(rows, {
    x: M,
    y: 2.62,
    w: 7.55,
    colW: [2.55, 1.72, 1.64, 1.64],
    rowH: 0.42,
    border: { type: "solid", color: "2A4145", pt: 1 },
    autoPage: false,
  });

  const notes = [
    ["What grows linearly", "Nurse confirmation (8 s per case), support hours, and SMS fees if we add the channel. None of them is a surprise at 100×."],
    ["What falls", "Hardware amortisation and support per desk: KES 1.88 per outcome at one desk, KES 0.47 at a hundred."],
    ["Oversight at volume", "The gate does not weaken. One approver per desk, one inbound edge to commit, and the audit chain still verifies after a restart."],
    ["Next adopter", "Kenya first — one desk, then a county, then three counties — then the SATS region. The named first desk comes from the pilot letter, not this slide."],
  ];

  notes.forEach(([label, body], i) => {
    const y = 2.62 + i * 0.95;
    addT(s, label.toUpperCase(), {
      x: 8.5,
      y,
      w: 4.2,
      h: 0.26,
      fontFace: T.body,
      fontSize: 10,
      bold: true,
      color: i === 3 ? P.orange : P.accent,
      charSpacing: 1.2,
      margin: 0,
      isTextBox: true,
    });
    addT(s, body, {
      x: 8.5,
      y: y + 0.26,
      w: 4.2,
      h: 0.64,
      fontFace: T.body,
      fontSize: 11.5,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    });
  });

  addT(s, 
    "Impact we will measure against a baseline: time-to-first-assessment for RED and ORANGE patients; under-triage rate at the desk (baseline taken in the pilot); share of priorities carrying a cited rule — 100% by construction, checked on every run.",
    {
      x: M,
      y: 5.52,
      w: 7.4,
      h: 0.95,
      fontFace: T.body,
      fontSize: 12,
      italic: true,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    },
  );

  s.addNotes(
    "4:32 — 14 seconds.\n\n" +
      "At ten desks we charge KES 6,000 a desk and serve for about KES 2,600: fifty-six percent margin. At a hundred we discount to KES 4,800 and serve for about KES 2,100: fifty-seven. It does not explode, and it does not collapse — because the only line that grows with patients is the nurse's eight seconds, and that is her time, not our cost.\n\n" +
      "And the market isn't one desk: Kenya first — a county, then three — then the SATS region, where the same paper chart is already in use.",
  );
}

// ============================================================ 10. HONESTY ======
{
  const s = newSlide("What we have not earned", 10, 3);

  S.eyebrow(s, "The part most teams skip");
  S.title(s, "Three things we have not earned yet", { size: 36 });

  const items = [
    [
      "No clinician has reviewed it",
      "The eight-question instrument is written and the session is being booked. Until it is signed, we do not claim fit to the desk — and STATUS.md says so in the repository.",
    ],
    [
      "English intake only",
      "The clinical scale is data, not code: swapping SATS for a Francophone national scale is a YAML file. Multilingual intake is the real work, and it is the gate on Central African expansion.",
    ],
    [
      "No EMR write-back yet",
      "The queue is our SQLite store today. The hospital's DHIS2 or OpenMRS record is one adapter away, because the graph binds to the tool interface.",
    ],
  ];

  items.forEach(([head, body], i) => {
    const y = 2.46 + i * 1.22;
    addT(s, String(i + 1), {
      x: M,
      y: y - 0.04,
      w: 0.5,
      h: 0.4,
      fontFace: T.head,
      fontSize: 22,
      bold: true,
      color: P.orange,
      margin: 0,
      isTextBox: true,
    });
    addT(s, head, {
      x: M + 0.62,
      y,
      w: 5.2,
      h: 0.34,
      fontFace: T.body,
      fontSize: 15,
      bold: true,
      color: P.text,
      margin: 0,
      isTextBox: true,
    });
    addT(s, body, {
      x: M + 0.62,
      y: y + 0.36,
      w: 7.2,
      h: 0.78,
      fontFace: T.body,
      fontSize: 12.5,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    });
  });

  S.card(s, { x: 8.55, y: 2.42, w: 4.13, h: 3.9, fill: "2A1E14", line: "5A3A22" });
  addT(s, "THE FAILURE WE PUBLISH", {
    x: 8.79,
    y: 2.6,
    w: 3.65,
    h: 0.26,
    fontFace: T.body,
    fontSize: 10,
    bold: true,
    color: P.orange,
    charSpacing: 1.3,
    margin: 0,
    isTextBox: true,
  });
  addT(s, "E-09", {
    x: 8.79,
    y: 2.92,
    w: 3.6,
    h: 0.6,
    fontFace: T.head,
    fontSize: 32,
    bold: true,
    color: P.text,
    margin: 0,
    isTextBox: true,
  });
  addT(s, 
    "\u201cFeeling unwell\u201d, known diabetic. Expected ORANGE. The discriminator is not retrieved, so the agent asks one bounded question and delivers no colour.\n\nIt is in EVALS.md \u00a76, with what we would try next \u2014 not in a footnote.",
    {
      x: 8.79,
      y: 3.66,
      w: 3.65,
      h: 2.3,
      fontFace: T.body,
      fontSize: 12,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    },
  );

  s.addNotes(
    "4:46 — 7 seconds.\n\n" +
      "Three things we have not earned: no clinician has reviewed it, intake is English only, and we do not write to an EMR yet. We name them because you will find them in the repo anyway, and because a triage tool that hides its gaps has already failed the only test that matters.\n\n" +
      "The one failure we publish is E-09: a vague complaint is clarified, not guessed. It is on the appendix slide.",
  );
}

// ============================================================ 11. CLOSE ========
{
  const s = newSlide("Close", 11, 1);

  S.eyebrow(s, "The ask");
  S.title(s, "What we want from this room", { size: 38 });

  const asks = [
    ["15 minutes", "with a triage nurse or SHCP — the one input we cannot build, and the one that turns our fit claim into evidence."],
    ["One desk, 30 days", "at a district OPD, on synthetic or de-identified cases, with the gate and the audit chain switched on."],
    ["One introduction", "to a county or hospital health team — the payer we have priced for and not yet met."],
  ];
  asks.forEach(([head, body], i) => {
    const x = M + i * ((CW - 0.44) / 3 + 0.22);
    const w = (CW - 0.44) / 3;
    S.card(s, { x, y: 2.34, w, h: 1.96, fill: i === 0 ? P.surfaceUp : P.surface, line: i === 0 ? "2A4A46" : P.line });
    addT(s, head, {
      x: x + 0.24,
      y: 2.54,
      w: w - 0.48,
      h: 0.48,
      fontFace: T.head,
      fontSize: 22,
      bold: true,
      color: P.accent,
      margin: 0,
      isTextBox: true,
    });
    addT(s, body, {
      x: x + 0.24,
      y: 3.06,
      w: w - 0.48,
      h: 1.1,
      fontFace: T.body,
      fontSize: 12.5,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    });
  });

  addT(s, "Three doors for the next two minutes", {
    x: M,
    y: 4.72,
    w: 10,
    h: 0.34,
    fontFace: T.body,
    fontSize: 14,
    bold: true,
    color: P.text,
    margin: 0,
    isTextBox: true,
  });
  const doors = ["the 60-second p95 tail", "the E-09 failure", "what breaks at 100 desks"];
  doors.forEach((d, i) => {
    const x = M + i * 3.5;
    S.card(s, { x, y: 5.14, w: 3.28, h: 0.62, fill: "14262A" });
    addT(s, `Ask us about ${d}`, {
      x: x + 0.2,
      y: 5.14,
      w: 2.9,
      h: 0.62,
      fontFace: T.body,
      fontSize: 12,
      color: P.textDim,
      valign: "middle",
      margin: 0,
      isTextBox: true,
    });
  });

  addT(s, "Scores or sequences. Never diagnoses. Never moves a patient without a name.", {
    x: M,
    y: 6.14,
    w: 11.5,
    h: 0.4,
    fontFace: T.head,
    fontSize: 17,
    italic: true,
    color: P.text,
    margin: 0,
    isTextBox: true,
  });

  s.addNotes(
    "4:53 — 7 seconds to the close.\n\n" +
      "One nurse, fifteen minutes. One desk, thirty days. One introduction to the payer. That is the whole ask.\n\n" +
      "And when you open the questions — we would rather you spend them here: the sixty-second tail, the E-09 failure, and what breaks at a hundred desks. We have numbers for all three.",
  );
}

// ============================================================ APPENDIX ========

// A1 — unit economics working
{
  const s = newSlide("Appendix · unit economics", 12, 0);
  S.eyebrow(s, "Appendix A1 · every input, so the arithmetic can be checked");
  S.title(s, "How the KES 1.88 is built", { size: 34 });

  const rows = [
    ["Input", "Value", "Where it comes from"],
    ["Patients per desk per day", "200", "Assumption — a busy district OPD morning plus afternoon"],
    ["Working days per month", "22", "Assumption"],
    ["Completed outcomes per desk / month", "4,400", "200 × 22"],
    ["Hardware", "KES 70,000, amortised 36 months (KES 60,000 at 100×)", "One mini-PC capable of the measured latency"],
    ["Power", "65 W × 8 h × KES 27/kWh", "Assumption — local tariff"],
    ["Support", "3 h (pilot) · 0.2 h (10×) · 0.05 h (100×) per desk / month", "KES 2,000/h"],
    ["Tokens per outcome", "1,344 in / 146 out", "Measured: evals/results/report.json, 72 runs"],
    ["Model calls per outcome", "3.1 mean · 4 worst", "1 extraction + 2.1 plan steps; 3-step hard cap"],
    ["Nurse confirmation", "8 s per case", "Not incremental — she triages either way"],
  ].map((r, ri) =>
    r.map((c, ci) => ({
      text: c,
      options: {
        fontFace: T.body,
        fontSize: 10.5,
        color: ri === 0 ? P.accent : ci === 0 ? P.text : P.textDim,
        bold: ri === 0,
        fill: { color: ri === 0 ? "14262A" : ri % 2 ? P.surface : "1A2C31" },
        align: ci === 2 ? "left" : ci === 1 ? "center" : "left",
        margin: 6,
      },
    })),
  );
  s.addTable(rows, {
    x: M,
    y: 2.3,
    w: 12.0,
    colW: [3.5, 4.6, 3.9],
    rowH: 0.36,
    border: { type: "solid", color: "2A4145", pt: 1 },
    autoPage: false,
  });

  addT(s, 
    "Cost / outcome = (hardware ÷ 36 + power + support) ÷ 4,400.  Pilot: (1,944 + 309 + 6,000) ÷ 4,400 = KES 1.88.  10 desks: KES 0.60.  100 desks: KES 0.47.  (≈ KES 129 = US$1, stated for cross-check.)",
    {
      x: M,
      y: 6.28,
      w: CW,
      h: 0.4,
      fontFace: "Courier New",
      fontSize: 11,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    },
  );
  s.addNotes("Appendix. Open this if a judge asks how the number is built. Every input is on the slide; two are assumptions and are labelled.");
}

// A2 — tool inventory
{
  const s = newSlide("Appendix · tools", 13, 1);
  S.eyebrow(s, "Appendix A2 · the nine owned tools");
  S.title(s, "What each tool may do", { size: 34 });

  const rows = [
    ["Tool", "Read / act", "Contract"],
    ["normalize_case", "read", "prose + vitals → structured JSON, missing[], out_of_scope"],
    ["match_discriminators", "read", "complaint → discriminator ids + coverage status"],
    ["retrieve_evidence", "read", "cited SATS passages"],
    ["assess_confidence", "read", "deliver / clarify / defer"],
    ["plan_next_step", "read", "one admissible action from a closed set of four"],
    ["request_clarification", "read", "≤3 targeted questions, mid-call, via MCP elicitation"],
    ["score_priority", "act", "colour, TEWS, citations[], target time"],
    ["raise_recheck_flag", "act", "serial vitals → second look, never a verdict"],
    ["commit_priority", "act + gated", "approved case → queue write + audit; refuses without a token"],
  ].map((r, ri) =>
    r.map((c, ci) => ({
      text: c,
      options: {
        fontFace: ci === 0 ? "Courier New" : T.body,
        fontSize: 10.5,
        color: ri === 0 ? P.accent : c.startsWith("act") ? P.text : P.textDim,
        bold: ri === 0,
        fill: { color: ri === 0 ? "14262A" : ri % 2 ? P.surface : "1A2C31" },
        margin: 6,
      },
    })),
  );
  s.addTable(rows, {
    x: M,
    y: 2.28,
    w: 12.0,
    colW: [3.2, 1.6, 7.2],
    rowH: 0.36,
    border: { type: "solid", color: "2A4145", pt: 1 },
    autoPage: false,
  });

  addT(s, 
    "Borrowed server: mcp-sqlite 1.0.9 over stdio — read paths exercised behind the Store protocol. Only one owned tool mutates the queue, and it has exactly one inbound edge: the approval gate.",
    {
      x: M,
      y: 6.34,
      w: CW,
      h: 0.4,
      fontFace: T.body,
      fontSize: 11,
      italic: true,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    },
  );
  s.addNotes("Appendix. Three read-only planning tools, two acting tools, one gated write. The gated write is the only queue mutation in the system.");
}

// A3 — the measured evidence
{
  const s = newSlide("Appendix · evidence", 14, 0);
  S.eyebrow(s, "Appendix A3 · what was measured, and what failed");
  S.title(s, "The numbers behind the claims", { size: 34 });

  const stats = [
    ["48/48", "colour-expected runs correct · under-triage 0 · over-triage 0"],
    ["24/24", "priorities cite a vital or discriminator · gate delivery 24/24"],
    ["48/60", "delivered · 9 clarified · 0 deferred (the rest are recheck or abstain)"],
    ["647", "tests pass on a clean tree · evaluator digest 0ae3dde6"],
  ];
  stats.forEach(([v, l], i) => {
    S.stat(s, {
      x: M + (i % 2) * 3.0,
      y: 2.34 + Math.floor(i / 2) * 1.8,
      w: 2.8,
      value: v,
      label: l,
      vsize: 26,
      hvalue: 0.5,
    });
  });

  S.card(s, { x: 6.75, y: 2.3, w: 5.93, h: 2.95, fill: P.surfaceUp });
  addT(s, "THE DECLARED FAILURE, IN FULL", {
    x: 7.26,
    y: 2.5,
    w: 5.2,
    h: 0.26,
    fontFace: T.body,
    fontSize: 10,
    bold: true,
    color: P.orange,
    charSpacing: 1.3,
    margin: 0,
    isTextBox: true,
  });
  addT(s, 
    "E-09 · \u201cfeeling unwell\u201d, known diabetic, normal vitals.\n\n" +
      "Expected ORANGE via a discriminator. The discriminator is not retrieved, so the case is clarified — one bounded question about glucose and ketones — and delivers no colour. That is reduced coverage, not a wrong colour, and it is reported separately.\n\n" +
      "What we would try next: a richer complaint ontology, and the same elicitation the planner already uses, with a second question round.",
    {
      x: 7.01,
      y: 2.8,
      w: 5.45,
      h: 2.35,
      fontFace: T.body,
      fontSize: 11.5,
      color: P.textDim,
      margin: 0,
      isTextBox: true,
    },
  );

  addT(s, 
    "Run it yourself: uv run triagedesk eval --cases evals/cases --runs 3 --report evals/results/report.json",
    {
      x: M,
      y: 5.66,
      w: CW,
      h: 0.3,
      fontFace: "Courier New",
      fontSize: 10.5,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    },
  );
  s.addNotes("Appendix. Use this if a judge challenges the accuracy claim. It includes the failure, the denominator, and how to re-run it.");
}

// A4 — security and rollout
{
  const s = newSlide("Appendix · security and rollout", 15, 0);
  S.eyebrow(s, "Appendix A4 · the controls, and the 90 days after this room");
  S.title(s, "Nothing moves without a name", { size: 34 });

  S.card(s, { x: M, y: 2.34, w: 5.86, h: 3.0 });
  S.columnHead(s, M + 0.26, 2.52, 5.3, "Controls, in the code today", P.accent);
  S.bullets(
    s,
    [
      "One inbound edge to commit — the interrupt() gate. No model vocabulary can reach it.",
      "Hash-chained audit: prev_hash + record, verified after a restart.",
      "No network in the agent path: inference is local, data stays in the building.",
      "Prompt injection: complaint text is data, and the colour is arithmetic.",
      "Refusals: a declined or unavailable elicitation is never converted into a value.",
    ],
    { x: M + 0.26, y: 2.88, w: 5.34, h: 2.9, size: 12, gap: 9 },
  );

  S.card(s, { x: 6.9, y: 2.34, w: 5.78, h: 3.0, fill: P.surfaceUp, line: "2A4A46" });
  S.columnHead(s, 7.16, 2.52, 5.2, "The 90 days after this room", P.orange);
  S.bullets(
    s,
    [
      "Days 1–30 · one nurse-in-charge review, signed; 10 price conversations; one pilot letter.",
      "Days 31–60 · one desk live on de-identified cases; measure time-to-first-assessment and under-triage.",
      "Days 61–90 · authenticated approver (badge or SSO), then the EMR adapter module.",
    ],
    { x: 7.16, y: 2.88, w: 5.24, h: 2.9, size: 12, gap: 10 },
  );

  addT(s, 
    "Declared gap: the approver's identity is recorded, not authenticated. In a real facility it must be a badge or SSO before the token is issued — SECURITY.md §6.",
    {
      x: M,
      y: 5.62,
      w: CW,
      h: 0.4,
      fontFace: T.body,
      fontSize: 11,
      italic: true,
      color: P.muted,
      margin: 0,
      isTextBox: true,
    },
  );
  addT(s, "Every claim in this deck reproduces from a clean clone: uv run triagedesk demo, then uv run triagedesk eval.", {
    x: M,
    y: 6.14,
    w: CW,
    h: 0.3,
    fontFace: T.body,
    fontSize: 11,
    italic: true,
    color: P.muted,
    margin: 0,
    isTextBox: true,
  });
  s.addNotes("Appendix. Security and the 90-day plan. The one control a hospital would ask about first is approver authentication — we name it before they do.");
}

// ============================================================ A5. SOURCES ====
{
  const s = newSlide("Appendix · sources", 16, 0);
  S.eyebrow(s, "Appendix A5 · the evidence behind the problem");
  S.title(s, "Where the numbers come from", { size: 34 });

  const rows = [
    ["Claim on the deck", "Source"],
    ["Trained staff matched the expert on the emergency calls only 51% of the time (64% overall)", "Wangara AA et al., Implementation and performance of the South African Triage Scale at Kenyatta National Hospital. Int J Emerg Med 2019;12:5 (Results, reliability)."],
    ["SATS sensitivity 92.2% for admission or death", "Same study, Results"],
    ["Overtriage fell 70.9% \u2192 62.3% under SATS (p<0.01)", "Same study, Table 3"],
    ["Kenya has no nationally accepted A&E triage system", "Wachira BW, Martin IBK. The state of emergency care in the Republic of Kenya. Afr J Emerg Med 2011;1(4):160\u2013165."],
    ["SATS target times: Red immediate, Orange 10 min, Yellow 1 h, Green 4 h", "Wangara 2019 (Discussion)"],
    ["The SATS scale itself (rules, TEWS, discriminators)", "South African Triage Group / EMSSA, Adult SATS chart, 2012"],
  ].map((r, ri) =>
    r.map((c, ci) => ({
      text: c,
      options: {
        fontFace: T.body,
        fontSize: 10.5,
        color: ri === 0 ? P.accent : ci === 0 ? P.text : P.textDim,
        bold: ri === 0,
        fill: { color: ri === 0 ? "14262A" : ri % 2 ? P.surface : "1A2C31" },
        margin: 6,
      },
    })),
  );
  s.addTable(rows, {
    x: M,
    y: 2.3,
    w: 12.0,
    colW: [5.2, 6.8],
    rowH: 0.42,
    border: { type: "solid", color: "2A4145", pt: 1 },
    autoPage: false,
  });

  addT(s, "All evaluation numbers on slides 5 and A3 trace to evals/results/report.json (digest 0ae3dde6…). Nothing on this deck is a statistic we could not point to.", {
    x: M,
    y: 6.34,
    w: CW,
    h: 0.4,
    fontFace: T.body,
    fontSize: 11,
    italic: true,
    color: P.muted,
    margin: 0,
    isTextBox: true,
  });
  s.addNotes("Appendix. The one slide that turns \u201cevidenced\u201d from a gap into a strength. Read it only if asked for a citation.");
}

// ============================================================ write ==========

pres
  .writeFile({ fileName: OUT })
  .then(() => applyTheme(OUT, THEME))
  .then(() => console.log("wrote", OUT))
  .catch((e) => {
    console.error(e);
    process.exit(1);
  });
