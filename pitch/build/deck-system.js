// Design system for the TriageDesk pitch deck.
// One place for the palette, type scale, and the small set of repeated components
// (eyebrow, title, card, stat, footer). Every slide imports from here so the deck
// cannot drift slide to slide (DRY).
//
// Palette rationale: the deck is a clinical instrument, not a startup brochure. Ink
// ground, one mint signal colour, and the four SATS acuity colours used as data —
// never as decoration.

const P = {
  ink: "0E1A1D", // slide ground
  surface: "17272B", // card ground
  surfaceUp: "1E3136", // raised card
  line: "294045", // hairline border
  text: "F2F6F4",
  textDim: "C6D4D3",
  muted: "93A9AD",
  accent: "2ED3A3", // the one signal colour
  accentDim: "1B7A61",
  // SATS acuity — used as data only
  green: "2E9E5B",
  yellow: "E9B949",
  orange: "E07A2F",
  red: "D64545",
};

const T = {
  head: "Cambria",
  body: "Calibri",
};

const W = 13.333;
const H = 7.5;
const M = 0.65;
const CW = W - M * 2; // 12.033

const THEME = {
  name: "TriageDesk Ink",
  headFontFace: T.head,
  bodyFontFace: T.body,
  colors: {
    dk1: P.ink,
    lt1: P.text,
    dk2: P.surface,
    lt2: P.textDim,
    accent1: P.accent,
    accent2: P.orange,
    accent3: P.yellow,
    accent4: P.red,
    accent5: P.green,
    accent6: P.accentDim,
    hlink: P.accent,
    folHlink: P.muted,
  },
};

function ground(slide, pres) {
  slide.background = { color: P.ink };
}

function eyebrow(slide, text, x = M, y = 0.42) {
  slide.addText(text.toUpperCase(), {
    x,
    y,
    w: CW,
    h: 0.28,
    fontFace: T.body,
    fontSize: 11,
    bold: true,
    color: P.accent,
    charSpacing: 1.6,
    margin: 0,
    valign: "top",
    isTextBox: true,
  });
}

function title(slide, text, opts = {}) {
  const { x = M, y = 0.74, w = CW, size = 40, color = P.text, lines } = opts;
  slide.addText(text, {
    x,
    y,
    w,
    h: lines ? lines * 0.62 : 1.1,
    fontFace: T.head,
    fontSize: size,
    bold: true,
    color,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.02,
    isTextBox: true,
  });
}

function deck(slide, text, y = 1.86, w = 10.6) {
  slide.addText(text, {
    x: M,
    y,
    w,
    h: 0.6,
    fontFace: T.body,
    fontSize: 15,
    color: P.textDim,
    margin: 0,
    valign: "top",
    isTextBox: true,
  });
}

function card(slide, o) {
  const { x, y, w, h, fill = P.surface, line = P.line, radius = 0.09 } = o;
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    fill: { color: fill },
    line: { color: line, width: 1 },
    rectRadius: radius,
    shadow: { type: "none" },
  });
}

function stat(slide, o) {
  const { x, y, w, value, label, colour = P.accent, vsize = 38, hvalue = 0.72 } = o;
  slide.addText(value, {
    x,
    y,
    w,
    h: hvalue,
    fontFace: T.head,
    fontSize: vsize,
    bold: true,
    color: colour,
    margin: 0,
    valign: "top",
    isTextBox: true,
  });
  slide.addText(label, {
    x,
    y: y + hvalue - 0.03,
    w,
    h: 0.52,
    fontFace: T.body,
    fontSize: 12,
    color: P.muted,
    margin: 0,
    valign: "top",
    isTextBox: true,
  });
}

// The motif: the four SATS acuity chips. Small, in the footer, every content slide.
function chips(slide, x = 5.55, y = 7.06, size = 0.13, gap = 0.06, active = -1) {
  [P.green, P.yellow, P.orange, P.red].forEach((c, i) => {
    slide.addShape("rect", {
      x: x + i * (size + gap),
      y,
      w: size,
      h: size,
      fill: { color: c, transparency: active === -1 || active === i ? 0 : 55 },
      line: { color: P.ink, width: 0 },
    });
  });
}

function footer(slide, section, n, active = -1) {
  slide.addText(`TriageDesk · ${section}`, {
    x: M,
    y: 6.99,
    w: 4.4,
    h: 0.26,
    fontFace: T.body,
    fontSize: 10,
    color: P.muted,
    margin: 0,
    isTextBox: true,
  });
  chips(slide, 5.55, 7.06, 0.13, 0.06, active);
  slide.addText(String(n).padStart(2, "0"), {
    x: W - M - 0.6,
    y: 6.99,
    w: 0.6,
    h: 0.26,
    fontFace: T.body,
    fontSize: 10,
    color: P.muted,
    align: "right",
    margin: 0,
    isTextBox: true,
  });
}

// A labelled block used on the three-column slides.
function columnHead(slide, x, y, w, label, colour) {
  slide.addText(label.toUpperCase(), {
    x,
    y,
    w,
    h: 0.26,
    fontFace: T.body,
    fontSize: 10,
    bold: true,
    color: colour,
    charSpacing: 1.4,
    margin: 0,
    valign: "top",
    isTextBox: true,
  });
}

function bullets(slide, items, o) {
  const { x, y, w, h, size = 14, colour = P.textDim, gap = 8 } = o;
  slide.addText(
    items.map((t, i) => ({
      text: t,
      options: {
        bullet: { indent: 12 },
        breakLine: i < items.length - 1,
        paraSpaceAfter: gap,
      },
    })),
    {
      x,
      y,
      w,
      h,
      fontFace: T.body,
      fontSize: size,
      color: colour,
      margin: 0,
      valign: "top",
      isTextBox: true,
    },
  );
}

const CHART_FONT = (size) => ({ fontFace: T.body, fontSize: size, color: P.muted });

module.exports = {
  P,
  T,
  W,
  H,
  M,
  CW,
  THEME,
  ground,
  eyebrow,
  title,
  deck,
  card,
  stat,
  chips,
  footer,
  columnHead,
  bullets,
  CHART_FONT,
};
