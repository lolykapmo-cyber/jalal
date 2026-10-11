const pptxgen = require('pptxgenjs');
const path = require('path');
const { applyTheme } = require('/root/.claude/skills/synced/bdef7cdd-414e-425f-91d9-5ca8d0432a0c_66163980-dc2d-4b5a-b667-8924e89efa70/pptx/scripts/apply_theme.js');

const IMG = n => path.join(__dirname, 'img', n + '.png');
const OUT = path.join(__dirname, 'GI-pH-and-Secretions-in-Drug-Absorption.pptx');

const THEME = {
  name: 'Pharma GI Teal',
  headFontFace: 'Cambria',
  bodyFontFace: 'Calibri',
  colors: {
    dk1: '0B2B32', lt1: 'FFFFFF',
    dk2: '0E4A54', lt2: 'EFF7F5',
    accent1: '0E7C86', accent2: '17B3A3', accent3: 'E8A33D',
    accent4: 'C8553D', accent5: '3D6E8C', accent6: '5B7B7E',
    hlink: '0E7C86', folHlink: '5B7B7E',
  },
};
const HEX = { deep: '0B2B32', dk2: '0E4A54', tint: 'EFF7F5', teal: '0E7C86',
              mint: '17B3A3', amber: 'E8A33D', terra: 'C8553D', slate: '3D6E8C',
              gray: '5B7B7E', white: 'FFFFFF' };

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';            // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = 'Department of Pharmacy';
pres.company = 'Department of Pharmacy';
pres.title = 'Role of Gastrointestinal pH and Secretions in Drug Absorption';
pres.subject = 'Biopharmaceutics';
const C = pres.SchemeColor;

const M = 0.72;                 // left margin
const W = 11.9;                 // content width
const DECK_FOOT = 'Role of Gastrointestinal pH and Secretions in Drug Absorption';

/* ===================== layouts ===================== */
pres.defineSlideMaster({
  title: 'COVER', background: { color: HEX.deep },
  objects: [
    { placeholder: { options: { name: 'kicker', type: 'body', x: M, y: 1.42, w: 8.2, h: 0.4,
        fontSize: 15, bold: true, charSpacing: 3, color: C.accent2, valign: 'middle' }, text: ' ' } },
    { placeholder: { options: { name: 'title', type: 'title', x: M, y: 1.92, w: 8.4, h: 2.5,
        fontSize: 40, bold: true, color: C.background1, align: 'left', valign: 'top',
        lineSpacingMultiple: 1.06 }, text: ' ' } },
    { placeholder: { options: { name: 'body', type: 'body', x: M, y: 4.86, w: 7.2, h: 1.9,
        fontSize: 16, color: C.accent2, valign: 'top' }, text: ' ' } },
  ],
});

pres.defineSlideMaster({
  title: 'DIVIDER', background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: 'kicker', type: 'body', x: M, y: 2.5, w: 6, h: 0.5,
        fontSize: 16, bold: true, charSpacing: 4, color: C.accent2, valign: 'middle' }, text: ' ' } },
    { placeholder: { options: { name: 'title', type: 'title', x: M, y: 3.05, w: 8.1, h: 1.9,
        fontSize: 38, bold: true, color: C.background1, align: 'left', valign: 'top',
        lineSpacingMultiple: 1.05 }, text: ' ' } },
    { placeholder: { options: { name: 'body', type: 'body', x: M, y: 4.95, w: 7.4, h: 0.9,
        fontSize: 15, color: C.accent2, valign: 'top' }, text: ' ' } },
  ],
});

function contentLayout(name, bg) {
  pres.defineSlideMaster({
    title: name, background: { color: bg },
    objects: [
      { placeholder: { options: { name: 'title', type: 'title', x: M, y: 0.46, w: W, h: 0.82,
          fontSize: 31, bold: true, color: C.text1, align: 'left', valign: 'middle' }, text: ' ' } },
      { text: { text: DECK_FOOT, options: { x: M, y: 6.98, w: 9.4, h: 0.3, fontSize: 10,
          color: C.accent6, align: 'left', valign: 'middle', isTextBox: true, margin: 0 } } },
    ],
    slideNumber: { x: 12.3, y: 6.98, w: 0.4, h: 0.3, fontSize: 11, color: HEX.gray, align: 'right' },
  });
}
contentLayout('CONTENT', HEX.white);
contentLayout('CONTENT_TINT', HEX.tint);

pres.defineSlideMaster({
  title: 'CLOSING', background: { color: HEX.deep },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: M, y: 0.72, w: W, h: 1.0,
        fontSize: 34, bold: true, color: C.background1, align: 'left', valign: 'middle' }, text: ' ' } },
  ],
});

/* ===================== helpers ===================== */
const shadow = (o = {}) => Object.assign({ type: 'outer', color: HEX.deep, opacity: 0.13,
  blur: 11, offset: 2, angle: 90 }, o);

function card(s, o) {
  s.addShape(pres.ShapeType.roundRect, {
    x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: o.r || 0.13,
    fill: o.fill || { color: C.background1 },
    line: o.line === null ? { type: 'none' } : (o.line || { color: C.accent2, width: 1 }),
    shadow: o.flat ? undefined : shadow(),
    objectName: o.name,
  });
}

function iconCircle(s, o) {
  const d = o.d || 0.62;
  s.addShape(pres.ShapeType.ellipse, { x: o.x, y: o.y, w: d, h: d,
    fill: { color: o.color || C.accent1 }, line: { type: 'none' }, objectName: o.name });
  const i = d * 0.54;
  s.addImage({ path: IMG('ic_' + o.icon), x: o.x + (d - i) / 2, y: o.y + (d - i) / 2, w: i, h: i });
}

function bullets(s, items, o) {
  s.addText(items.map((t, i) => ({
    text: t, options: { bullet: { indent: 16 }, breakLine: i !== items.length - 1 },
  })), Object.assign({
    x: o.x, y: o.y, w: o.w, h: o.h, fontSize: o.size || 14.5, color: o.color || C.text2,
    valign: 'top', isTextBox: true, paraSpaceAfter: o.gap === undefined ? 8 : o.gap,
    lineSpacingMultiple: 1.04, margin: 0,
  }, o.extra || {}));
}

function heading(s, text, o) {
  s.addText(text, { x: o.x, y: o.y, w: o.w, h: o.h || 0.36, fontSize: o.size || 19,
    bold: true, color: o.color || C.accent1, valign: 'middle', isTextBox: true, margin: 0,
    objectName: o.name });
}

function callout(s, o) {
  card(s, { x: o.x, y: o.y, w: o.w, h: o.h, fill: { color: o.fill || C.accent2, transparency: 86 },
    line: { color: o.fill || C.accent2, width: 1.25 }, flat: true, name: o.name });
  iconCircle(s, { x: o.x + 0.3, y: o.y + (o.h - 0.56) / 2, d: 0.56, icon: o.icon, color: o.fill || C.accent1 });
  s.addText(o.rich || o.text, { x: o.x + 1.08, y: o.y + 0.1, w: o.w - 1.4, h: o.h - 0.2,
    fontSize: o.size || 14.5, color: C.text1, valign: 'middle', isTextBox: true, margin: 0 });
}

const TRANS = [];               // transition per slide, filled as slides are added
function slide(master, section, trans) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  TRANS.push(trans || 'morph');
  return s;
}

/* ===================== 1. cover ===================== */
pres.addSection({ title: 'Opening' });
{
  const s = slide('COVER', 'Opening', 'fade');
  s.addShape(pres.ShapeType.ellipse, { x: 8.3, y: -1.5, w: 7.2, h: 7.2,
    fill: { color: C.accent1, transparency: 72 }, line: { type: 'none' } });
  s.addShape(pres.ShapeType.ellipse, { x: 10.1, y: 3.1, w: 4.6, h: 4.6,
    fill: { color: C.accent2, transparency: 84 }, line: { type: 'none' } });
  s.addImage({ path: IMG('gi_mark'), x: 9.05, y: 1.18, w: 3.4, h: 5.06, objectName: '!!mark' });
  s.addText('BIOPHARMACEUTICS  ·  DRUG ABSORPTION', { placeholder: 'kicker' });
  s.addText('Role of Gastrointestinal pH and Secretions in Drug Absorption',
    { placeholder: 'title', objectName: '!!deckTitle' });
  s.addText([
    { text: 'Presented by:  ', options: { color: C.background1, bold: true } },
    { text: '______________________', options: { color: C.accent2, breakLine: true } },
    { text: 'Department of Pharmacy', options: { color: C.background1, breakLine: true } },
    { text: 'University:  ', options: { color: C.background1, bold: true } },
    { text: '______________________', options: { color: C.accent2 } },
  ], { placeholder: 'body', lineSpacingMultiple: 1.45 });
  s.addNotes('Title slide. Fill in the presenter name and the university before the session.');
}

/* ===================== 2. agenda ===================== */
{
  const s = slide('CONTENT', 'Opening');
  s.addText('What this presentation covers', { placeholder: 'title' });
  const items = [
    ['list', 'Drug absorption', 'Definition and where it happens'],
    ['droplet', 'Gastrointestinal pH', 'pH of the stomach, duodenum and intestine'],
    ['charge', 'Ionization and permeability', 'Unionized vs. ionized drug, Henderson–Hasselbalch'],
    ['beaker', 'Gastrointestinal secretions', 'HCl, bicarbonate, bile salts, intestinal fluid'],
    ['capsule', 'Clinical examples', 'Omeprazole, ketoconazole, aspirin, tetracyclines'],
    ['layers', 'Food, antacids and applications', 'Interactions and formulation strategies'],
  ];
  const cols = [M, 6.84], rowY = [1.62, 3.37, 5.12], cw = 5.78, ch = 1.52;
  items.forEach((it, i) => {
    const x = cols[i % 2], y = rowY[Math.floor(i / 2)];
    card(s, { x, y, w: cw, h: ch, fill: { color: C.background2 }, line: null, flat: true });
    iconCircle(s, { x: x + 0.34, y: y + 0.45, d: 0.62, icon: it[0],
      color: i % 2 ? C.accent1 : C.accent2 });
    s.addText(`0${i + 1}`, { x: x + 0.34, y: y + 0.12, w: 0.7, h: 0.3, fontSize: 11.5,
      bold: true, color: C.accent6, isTextBox: true, margin: 0 });
    s.addText(it[1], { x: x + 1.14, y: y + 0.36, w: cw - 1.5, h: 0.38, fontSize: 17,
      bold: true, color: C.text1, isTextBox: true, margin: 0, valign: 'middle' });
    s.addText(it[2], { x: x + 1.14, y: y + 0.78, w: cw - 1.5, h: 0.5, fontSize: 13,
      color: C.accent6, isTextBox: true, margin: 0, valign: 'top' });
  });
  s.addNotes('Roadmap of the talk: physiology first, then the mechanism, then the clinical consequences.');
}

/* ===================== 3. introduction ===================== */
pres.addSection({ title: 'Introduction' });
{
  const s = slide('CONTENT', 'Introduction');
  s.addText('What is drug absorption', { placeholder: 'title' });
  bullets(s, [
    'Drug absorption is the movement of a drug from the gastrointestinal tract into the bloodstream.',
    'Most orally administered drugs are absorbed mainly from the small intestine.',
    'Gastrointestinal pH and secretions can affect drug absorption.',
  ], { x: M, y: 1.62, w: 5.1, h: 2.9, size: 15.5, gap: 14 });
  callout(s, { x: M, y: 4.72, w: 5.1, h: 1.52, icon: 'bulb', fill: C.accent3,
    rich: [
      { text: 'Key idea', options: { bold: true, fontSize: 14, breakLine: true } },
      { text: 'GI conditions can change how much and how quickly a drug is absorbed.',
        options: { fontSize: 14 } },
    ] });
  s.addImage({ path: IMG('absorption'), x: 6.35, y: 1.92, w: 6.25, h: 3.27 });
  s.addText('From the lumen, across the intestinal epithelium, into the blood',
    { x: 6.35, y: 5.36, w: 6.25, h: 0.38, fontSize: 13, italic: true, color: C.accent6,
      align: 'center', isTextBox: true, margin: 0 });
  s.addNotes('Absorption = movement from the GI tract into the systemic circulation. '
    + 'The small intestine dominates because of its very large surface area.');
}

/* ===================== 4. what GI conditions influence ===================== */
{
  const s = slide('CONTENT_TINT', 'Introduction');
  s.addText('Gastrointestinal conditions influence four things', { placeholder: 'title' });
  const four = [
    ['droplet', 'Drug solubility', 'How much drug can dissolve in the GI fluids', C.accent1],
    ['charge', 'Drug ionization', 'The balance between ionized and unionized drug', C.accent2],
    ['shield', 'Drug stability', 'Whether the drug survives the gastric environment', C.accent4],
    ['dissolve', 'Drug dissolution', 'How fast the dosage form releases dissolved drug', C.accent3],
  ];
  four.forEach((f, i) => {
    const x = M + i * 3.05, y = 1.72, w = 2.75, h = 3.05;
    card(s, { x, y, w, h, fill: { color: C.background1 }, line: null });
    iconCircle(s, { x: x + (w - 0.78) / 2, y: y + 0.42, d: 0.78, icon: f[0], color: f[3] });
    s.addText(f[1], { x: x + 0.18, y: y + 1.42, w: w - 0.36, h: 0.6, fontSize: 17, bold: true,
      color: C.text1, align: 'center', valign: 'top', isTextBox: true, margin: 0 });
    s.addText(f[2], { x: x + 0.22, y: y + 2.04, w: w - 0.44, h: 1.0, fontSize: 13,
      color: C.accent6, align: 'center', valign: 'top', isTextBox: true, margin: 0 });
  });
  callout(s, { x: M, y: 5.26, w: W, h: 1.0, icon: 'target', fill: C.accent1, size: 15,
    text: 'Together these determine the extent and the rate of oral drug absorption.' });
  s.addNotes('These four properties are the link between gut physiology and plasma concentration.');
}

/* ===================== 5. divider 01 ===================== */
pres.addSection({ title: 'Gastrointestinal pH' });
function divider(num, title, sub, imgY) {
  const s = slide('DIVIDER', arguments[3] === undefined ? undefined : undefined, 'fade');
  TRANS[TRANS.length - 1] = 'fadeBlack';
  return s;
}
{
  const s = pres.addSlide({ masterName: 'DIVIDER', sectionTitle: 'Gastrointestinal pH' });
  TRANS.push('fadeBlack');
  s.addShape(pres.ShapeType.ellipse, { x: 8.6, y: -1.2, w: 6.6, h: 6.6,
    fill: { color: C.accent1, transparency: 76 }, line: { type: 'none' } });
  s.addImage({ path: IMG('gi_mark'), x: 9.3, y: 1.3, w: 3.1, h: 4.62, objectName: '!!mark' });
  s.addText('SECTION 01', { placeholder: 'kicker' });
  s.addText('Gastrointestinal pH and Drug Absorption',
    { placeholder: 'title', objectName: '!!sec1' });
  s.addText('The gastrointestinal tract has different pH environments', { placeholder: 'body' });
}

/* ===================== 6. pH along the tract ===================== */
{
  const s = slide('CONTENT', 'Gastrointestinal pH');
  s.addText('pH changes along the gastrointestinal tract',
    { placeholder: 'title', objectName: '!!sec1' });
  const rows = [
    ['Stomach', '1 – 3', C.accent4, 'acid'],
    ['Duodenum', '5 – 6', C.accent3, 'droplet'],
    ['Small intestine', '6 – 7.5', C.accent1, 'intestine'],
  ];
  s.addText([
    { text: 'SITE', options: { bold: true, charSpacing: 2 } },
  ], { x: M + 0.2, y: 1.52, w: 3, h: 0.3, fontSize: 11.5, color: C.accent6, isTextBox: true, margin: 0 });
  s.addText('APPROXIMATE pH', { x: M + 3.4, y: 1.52, w: 2.5, h: 0.3, fontSize: 11.5, bold: true,
    charSpacing: 2, color: C.accent6, align: 'right', isTextBox: true, margin: 0 });
  rows.forEach((r, i) => {
    const y = 1.92 + i * 1.12;
    card(s, { x: M, y, w: 6.0, h: 0.94, fill: { color: C.background2 }, line: null, flat: true });
    iconCircle(s, { x: M + 0.24, y: y + 0.19, d: 0.56, icon: r[3], color: r[2] });
    s.addText(r[0], { x: M + 1.02, y, w: 2.9, h: 0.94, fontSize: 17, bold: true, color: C.text1,
      valign: 'middle', isTextBox: true, margin: 0 });
    s.addText(r[1], { x: M + 3.5, y, w: 2.3, h: 0.94, fontSize: 23, bold: true, color: r[2],
      align: 'right', valign: 'middle', isTextBox: true, margin: 0 });
  });
  s.addImage({ path: IMG('ph_scale'), x: M, y: 5.52, w: 6.0, h: 1.11 });
  s.addImage({ path: IMG('gi_light'), x: 7.44, y: 1.42, w: 5.3, h: 4.64, objectName: '!!gi' });
  s.addNotes('Approximate values; they vary with fasting or fed state, age and disease.');
}

/* ===================== 7. how pH affects drugs ===================== */
{
  const s = slide('CONTENT_TINT', 'Gastrointestinal pH');
  s.addText('How does pH affect drugs', { placeholder: 'title' });
  const pts = [
    ['droplet', 'pH can change drug solubility.', C.accent1],
    ['charge', 'pH affects the ionization of weak acids and bases.', C.accent2],
    ['shield', 'It can affect the stability of acid-sensitive drugs.', C.accent4],
    ['dissolve', 'It can influence drug dissolution and availability for absorption.', C.accent3],
  ];
  pts.forEach((p, i) => {
    const x = i % 2 ? 6.84 : M, y = 1.62 + Math.floor(i / 2) * 1.86;
    card(s, { x, y, w: 5.78, h: 1.56, fill: { color: C.background1 }, line: null });
    iconCircle(s, { x: x + 0.36, y: y + 0.44, d: 0.68, icon: p[0], color: p[2] });
    s.addText(p[1], { x: x + 1.26, y: y + 0.2, w: 4.3, h: 1.16, fontSize: 15.5, color: C.text1,
      valign: 'middle', isTextBox: true, margin: 0 });
  });
  callout(s, { x: M, y: 5.42, w: W, h: 1.18, icon: 'alert', fill: C.accent4, size: 14.5,
    rich: [
      { text: 'Important.  ', options: { bold: true } },
      { text: 'Absorption is not determined by pH alone. Surface area, permeability, '
            + 'formulation, and other physiological factors are also important.' },
    ] });
  s.addNotes('Guard against the exam-style oversimplification that pH alone predicts absorption.');
}

/* ===================== 8. ionized vs unionized ===================== */
pres.addSection({ title: 'Ionization' });
{
  const s = slide('CONTENT', 'Ionization');
  s.addText('Ionized vs. unionized drug', { placeholder: 'title' });
  s.addImage({ path: IMG('membrane'), x: M, y: 1.78, w: 7.3, h: 3.82 });
  s.addText('Only the unionized fraction moves freely through the lipid bilayer',
    { x: M, y: 5.74, w: 7.3, h: 0.4, fontSize: 13, italic: true, color: C.accent6,
      align: 'center', isTextBox: true, margin: 0 });
  const bx = 8.36, bw = 4.26;
  card(s, { x: bx, y: 1.78, w: bw, h: 1.86, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: bx + 0.3, y: 2.02, d: 0.6, icon: 'capsule', color: C.accent1 });
  heading(s, 'Unionized form', { x: bx + 1.04, y: 2.04, w: bw - 1.3, size: 16 });
  s.addText('Generally crosses lipid membranes more easily.',
    { x: bx + 0.3, y: 2.76, w: bw - 0.6, h: 0.76, fontSize: 14, color: C.text2,
      isTextBox: true, margin: 0, valign: 'top' });
  card(s, { x: bx, y: 3.88, w: bw, h: 2.0, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: bx + 0.3, y: 4.12, d: 0.6, icon: 'charge', color: C.accent4 });
  heading(s, 'Ionized form', { x: bx + 1.04, y: 4.14, w: bw - 1.3, size: 16, color: C.accent4 });
  s.addText('Generally has lower membrane permeability but may have higher water solubility.',
    { x: bx + 0.3, y: 4.86, w: bw - 0.6, h: 1.1, fontSize: 14, color: C.text2,
      isTextBox: true, margin: 0, valign: 'top' });
  s.addNotes('Lipid membranes favour the neutral species; charge keeps a molecule in the aqueous phase.');
}

/* ===================== 9. weak acids and bases ===================== */
{
  const s = slide('CONTENT_TINT', 'Ionization');
  s.addText('Weak acids and weak bases', { placeholder: 'title' });
  // left card — weak acids
  card(s, { x: M, y: 1.6, w: 5.78, h: 4.86, fill: { color: C.background1 }, line: null });
  iconCircle(s, { x: M + 0.42, y: 1.94, d: 0.66, icon: 'acid', color: C.accent4 });
  heading(s, 'Weak acids', { x: M + 1.26, y: 1.98, w: 3.6, size: 20, color: C.accent4 });
  s.addText('Low pH  →  more unionized form',
    { x: M + 0.42, y: 2.78, w: 4.94, h: 0.42, fontSize: 16, bold: true, color: C.text1,
      isTextBox: true, margin: 0 });
  s.addText('Example: Aspirin', { x: M + 0.42, y: 3.22, w: 4.94, h: 0.36, fontSize: 14,
    color: C.accent6, isTextBox: true, margin: 0 });
  s.addImage({ path: IMG('aspirin'), x: M + 1.08, y: 3.68, w: 3.6, h: 2.45 });
  // right card — weak bases
  card(s, { x: 6.84, y: 1.6, w: 5.78, h: 4.86, fill: { color: C.background1 }, line: null });
  iconCircle(s, { x: 7.26, y: 1.94, d: 0.66, icon: 'droplet', color: C.accent5 });
  heading(s, 'Weak bases', { x: 8.1, y: 1.98, w: 3.6, size: 20, color: C.accent5 });
  s.addText('Higher pH  →  more unionized form',
    { x: 7.26, y: 2.78, w: 4.94, h: 0.42, fontSize: 16, bold: true, color: C.text1,
      isTextBox: true, margin: 0 });
  s.addText('The opposite pattern to weak acids', { x: 7.26, y: 3.22, w: 4.94, h: 0.36,
    fontSize: 14, color: C.accent6, isTextBox: true, margin: 0 });
  // pH ladder graphic for bases
  const lx = 7.26, ly = 3.86;
  s.addShape(pres.ShapeType.roundRect, { x: lx, y: ly, w: 4.94, h: 0.46, rectRadius: 0.22,
    fill: { color: C.accent5, transparency: 80 }, line: { type: 'none' } });
  s.addText('Gastric pH  1 – 3', { x: lx + 0.18, y: ly, w: 4.6, h: 0.46, fontSize: 13.5,
    bold: true, color: C.accent5, valign: 'middle', isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.downArrow, { x: lx + 2.19, y: ly + 0.56, w: 0.56, h: 0.56,
    fill: { color: C.accent5 }, line: { type: 'none' } });
  s.addShape(pres.ShapeType.roundRect, { x: lx, y: ly + 1.2, w: 4.94, h: 0.46, rectRadius: 0.22,
    fill: { color: C.accent1, transparency: 72 }, line: { type: 'none' } });
  s.addText('Intestinal pH  6 – 7.5', { x: lx + 0.18, y: ly + 1.2, w: 4.6, h: 0.46, fontSize: 13.5,
    bold: true, color: C.accent1, valign: 'middle', isTextBox: true, margin: 0 });
  s.addText('more unionized base  →  better permeability',
    { x: lx, y: ly + 1.74, w: 4.94, h: 0.38, fontSize: 12.5, italic: true, color: C.accent6,
      isTextBox: true, margin: 0 });
  s.addNotes('Aspirin is the classic weak acid; most antihistamines and opioids are weak bases.');
}

/* ===================== 10. Henderson–Hasselbalch ===================== */
{
  const s = slide('CONTENT', 'Ionization');
  s.addText('Henderson–Hasselbalch equation', { placeholder: 'title' });
  const eq = [
    ['For weak acids', 'pH  =  pKa  +  log ( [A⁻] / [HA] )', C.accent4],
    ['For weak bases', 'pH  =  pKa  +  log ( [B] / [BH⁺] )', C.accent5],
  ];
  eq.forEach((e, i) => {
    const x = i ? 6.84 : M;
    card(s, { x, y: 1.6, w: 5.78, h: 1.74, fill: { color: C.background2 }, line: null, flat: true });
    s.addText(e[0], { x: x + 0.42, y: 1.82, w: 4.9, h: 0.36, fontSize: 14, bold: true,
      color: e[2], isTextBox: true, margin: 0 });
    s.addText(e[1], { x: x + 0.42, y: 2.3, w: 4.94, h: 0.84, fontSize: 24, bold: true,
      color: C.text1, valign: 'middle', isTextBox: true, margin: 0 });
  });
  s.addImage({ path: IMG('equilibrium'), x: 3.97, y: 3.58, w: 5.4, h: 2.25 });
  callout(s, { x: M, y: 5.94, w: W, h: 0.84, icon: 'target', fill: C.accent1, size: 15,
    rich: [
      { text: 'Key point.  ', options: { bold: true } },
      { text: 'pH determines the ratio of ionized to unionized drug.' },
    ] });
  s.addNotes('At pH = pKa the drug is 50% ionized. One pH unit away from the pKa shifts the ratio tenfold.');
}

/* ===================== 11. divider 02 ===================== */
pres.addSection({ title: 'Secretions' });
{
  const s = pres.addSlide({ masterName: 'DIVIDER', sectionTitle: 'Secretions' });
  TRANS.push('fadeBlack');
  s.addShape(pres.ShapeType.ellipse, { x: 8.6, y: -1.2, w: 6.6, h: 6.6,
    fill: { color: C.accent1, transparency: 76 }, line: { type: 'none' } });
  s.addImage({ path: IMG('gi_mark'), x: 9.3, y: 1.3, w: 3.1, h: 4.62, objectName: '!!mark' });
  s.addText('SECTION 02', { placeholder: 'kicker' });
  s.addText('Gastrointestinal Secretions', { placeholder: 'title', objectName: '!!sec2' });
  s.addText('Acid, bicarbonate, bile salts and intestinal fluid', { placeholder: 'body' });
}

/* ===================== 12. acid + bicarbonate ===================== */
{
  const s = slide('CONTENT', 'Secretions');
  s.addText('Gastric acid and bicarbonate', { placeholder: 'title', objectName: '!!sec2' });
  s.addImage({ path: IMG('secretions'), x: 0.46, y: 2.0, w: 6.6, h: 3.81 });
  s.addText('Acid from the stomach is neutralized by pancreatic bicarbonate in the duodenum',
    { x: 0.46, y: 5.92, w: 6.6, h: 0.56, fontSize: 13, italic: true, color: C.accent6,
      align: 'center', isTextBox: true, margin: 0 });
  const bx = 7.4, bw = 5.22;
  card(s, { x: bx, y: 1.6, w: bw, h: 2.34, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: bx + 0.32, y: 1.86, d: 0.62, icon: 'acid', color: C.accent4 });
  heading(s, 'Gastric acid (HCl)', { x: bx + 1.08, y: 1.88, w: 3.9, size: 17, color: C.accent4 });
  bullets(s, ['Produced by parietal cells.',
              'Creates the acidic gastric environment.',
              'Can affect drug solubility, ionization, and stability.'],
    { x: bx + 0.34, y: 2.6, w: bw - 0.68, h: 1.26, size: 13.5, gap: 5 });
  card(s, { x: bx, y: 4.16, w: bw, h: 2.32, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: bx + 0.32, y: 4.42, d: 0.62, icon: 'beaker', color: C.accent1 });
  heading(s, 'Bicarbonate (HCO₃⁻)', { x: bx + 1.08, y: 4.44, w: 3.9, size: 17 });
  bullets(s, ['Mainly supplied to the duodenum by pancreatic secretions.',
              'Helps neutralize gastric acid.',
              'Raises intestinal pH.'],
    { x: bx + 0.34, y: 5.16, w: bw - 0.68, h: 1.22, size: 13.5, gap: 5 });
  s.addNotes('The acid–bicarbonate pair sets the pH gradient that the rest of the lecture depends on.');
}

/* ===================== 13. bile salts + intestinal secretions ===================== */
{
  const s = slide('CONTENT_TINT', 'Secretions');
  s.addText('Bile salts and intestinal secretions', { placeholder: 'title' });
  card(s, { x: M, y: 1.6, w: 7.0, h: 2.62, fill: { color: C.background1 }, line: null });
  iconCircle(s, { x: M + 0.42, y: 1.9, d: 0.66, icon: 'bile', color: C.accent3 });
  heading(s, 'Bile salts', { x: M + 1.26, y: 1.94, w: 4.4, size: 20, color: C.accent3 });
  bullets(s, ['Secreted into the small intestine.',
              'Form micelles and improve the solubilization of some poorly water-soluble drugs.'],
    { x: M + 0.44, y: 2.76, w: 6.1, h: 1.6, size: 14.5, gap: 9 });
  s.addImage({ path: IMG('micelle'), x: 8.42, y: 1.42, w: 3.45, h: 3.12 });
  card(s, { x: M, y: 4.76, w: W, h: 1.72, fill: { color: C.background1 }, line: null });
  iconCircle(s, { x: M + 0.42, y: 5.1, d: 0.66, icon: 'exchange', color: C.accent2 });
  heading(s, 'Intestinal secretions', { x: M + 1.26, y: 5.14, w: 4.4, size: 20, color: C.accent1 });
  s.addText([
    { text: 'Provide water, electrolytes, mucus, and enzymes.',
      options: { bullet: { indent: 16 }, breakLine: true } },
    { text: 'Support drug dissolution and movement toward the intestinal surface.',
      options: { bullet: { indent: 16 } } },
  ], { x: 6.1, y: 5.06, w: 6.3, h: 1.14, fontSize: 14, color: C.text2, isTextBox: true,
       margin: 0, valign: 'middle', paraSpaceAfter: 6 });
  s.addNotes('Bile salts matter most for lipophilic, poorly soluble (BCS class II) drugs.');
}

/* ===================== 14. divider 03 ===================== */
pres.addSection({ title: 'Clinical examples' });
{
  const s = pres.addSlide({ masterName: 'DIVIDER', sectionTitle: 'Clinical examples' });
  TRANS.push('fadeBlack');
  s.addShape(pres.ShapeType.ellipse, { x: 8.6, y: -1.2, w: 6.6, h: 6.6,
    fill: { color: C.accent1, transparency: 76 }, line: { type: 'none' } });
  s.addImage({ path: IMG('gi_mark'), x: 9.3, y: 1.3, w: 3.1, h: 4.62, objectName: '!!mark' });
  s.addText('SECTION 03', { placeholder: 'kicker' });
  s.addText('Clinical Examples', { placeholder: 'title', objectName: '!!sec3' });
  s.addText('Four drugs whose absorption depends on GI pH and secretions', { placeholder: 'body' });
}

/* ===================== 15. omeprazole + ketoconazole ===================== */
{
  const s = slide('CONTENT', 'Clinical examples');
  s.addText('Omeprazole and ketoconazole', { placeholder: 'title', objectName: '!!sec3' });
  // Omeprazole
  card(s, { x: M, y: 1.56, w: 5.78, h: 4.94, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: M + 0.4, y: 1.84, d: 0.66, icon: 'shield', color: C.accent1 });
  heading(s, 'Omeprazole', { x: M + 1.24, y: 1.88, w: 4.2, size: 20 });
  bullets(s, ['Acid-sensitive drug.',
              'Formulated as a delayed-release, enteric-coated dosage form.',
              'Protects the drug from gastric acid.'],
    { x: M + 0.42, y: 2.6, w: 4.96, h: 1.44, size: 14, gap: 6 });
  s.addImage({ path: IMG('enteric'), x: 1.21, y: 4.0, w: 4.8, h: 2.4 });
  // Ketoconazole
  card(s, { x: 6.84, y: 1.56, w: 5.78, h: 4.94, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: 7.24, y: 1.84, d: 0.66, icon: 'acid', color: C.accent4 });
  heading(s, 'Ketoconazole', { x: 8.08, y: 1.88, w: 4.2, size: 20, color: C.accent4 });
  bullets(s, ['Oral absorption depends on an acidic environment.',
              'Increased gastric pH may reduce its dissolution and absorption.'],
    { x: 7.26, y: 2.66, w: 4.96, h: 1.2, size: 14, gap: 6 });
  const steps = [['bottle', 'Gastric pH rises', C.accent5],
                 ['dissolve', 'Dissolution falls', C.accent3],
                 ['trend', 'Absorption falls', C.accent4]];
  steps.forEach((st, i) => {
    const y = 4.06 + i * 0.82;
    s.addShape(pres.ShapeType.roundRect, { x: 7.26, y, w: 4.94, h: 0.66, rectRadius: 0.12,
      fill: { color: C.background1 }, line: { color: st[2], width: 1 } });
    iconCircle(s, { x: 7.42, y: y + 0.07, d: 0.52, icon: st[0], color: st[2] });
    s.addText(st[1], { x: 8.08, y, w: 4.0, h: 0.66, fontSize: 14.5, bold: true, color: C.text1,
      valign: 'middle', isTextBox: true, margin: 0 });
    if (i < 2) s.addShape(pres.ShapeType.triangle, { x: 9.61, y: y + 0.7, w: 0.24, h: 0.1,
      fill: { color: C.accent6 }, line: { type: 'none' }, rotate: 180 });
  });
  s.addNotes('Omeprazole is protected from acid; ketoconazole needs acid. Opposite formulation problems.');
}

/* ===================== 16. aspirin + tetracyclines ===================== */
{
  const s = slide('CONTENT_TINT', 'Clinical examples');
  s.addText('Aspirin and tetracyclines', { placeholder: 'title' });
  card(s, { x: M, y: 1.56, w: 5.78, h: 4.94, fill: { color: C.background1 }, line: null });
  iconCircle(s, { x: M + 0.4, y: 1.84, d: 0.66, icon: 'acid', color: C.accent4 });
  heading(s, 'Aspirin', { x: M + 1.24, y: 1.88, w: 4.2, size: 20, color: C.accent4 });
  bullets(s, ['A weak acid.',
              'Its ionization changes with GI pH.',
              'However, most drug absorption occurs in the small intestine because of its '
              + 'large surface area.'],
    { x: M + 0.42, y: 2.66, w: 4.96, h: 1.9, size: 14, gap: 6 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.42, y: 4.66, w: 4.96, h: 1.56, rectRadius: 0.13,
    fill: { color: C.accent2, transparency: 86 }, line: { type: 'none' } });
  iconCircle(s, { x: M + 0.74, y: 5.1, d: 0.68, icon: 'intestine', color: C.accent1 });
  s.addText([
    { text: 'Surface area wins', options: { bold: true, fontSize: 14.5, breakLine: true } },
    { text: 'Site of absorption is not decided by pH alone.', options: { fontSize: 13.5 } },
  ], { x: M + 1.62, y: 4.82, w: 3.6, h: 1.24, color: C.text1, valign: 'middle',
       isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
  card(s, { x: 6.84, y: 1.56, w: 5.78, h: 4.94, fill: { color: C.background1 }, line: null });
  iconCircle(s, { x: 7.24, y: 1.84, d: 0.66, icon: 'exchange', color: C.accent5 });
  heading(s, 'Tetracyclines', { x: 8.08, y: 1.88, w: 4.2, size: 20, color: C.accent5 });
  bullets(s, ['Can form complexes with calcium, iron, and magnesium.',
              'This can reduce drug absorption.'],
    { x: 7.26, y: 2.66, w: 4.96, h: 1.0, size: 14, gap: 6 });
  s.addImage({ path: IMG('chelation'), x: 7.65, y: 3.72, w: 4.16, h: 2.6 });
  s.addNotes('Counsel patients: separate tetracyclines from dairy products, antacids and iron tablets.');
}

/* ===================== 17. food, antacids and PPIs ===================== */
pres.addSection({ title: 'Applications' });
{
  const s = slide('CONTENT', 'Applications');
  s.addText('Food, antacids and proton pump inhibitors', { placeholder: 'title' });
  card(s, { x: M, y: 1.56, w: 6.3, h: 4.92, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: M + 0.42, y: 1.86, d: 0.66, icon: 'food', color: C.accent3 });
  heading(s, 'Food', { x: M + 1.26, y: 1.9, w: 4.2, size: 20, color: C.accent3 });
  s.addText('Food may:', { x: M + 0.44, y: 2.62, w: 5.4, h: 0.32, fontSize: 14, bold: true,
    color: C.text1, isTextBox: true, margin: 0 });
  bullets(s, ['Change gastric pH.',
              'Delay gastric emptying.',
              'Increase bile secretion.',
              'Bind to some drugs.',
              'Increase or decrease drug absorption.'],
    { x: M + 0.44, y: 3.0, w: 5.4, h: 2.0, size: 14, gap: 7 });
  s.addImage({ path: IMG('food'), x: 2.22, y: 4.34, w: 3.3, h: 2.02 });
  card(s, { x: 7.4, y: 1.56, w: 5.22, h: 4.92, fill: { color: C.background2 }, line: null, flat: true });
  iconCircle(s, { x: 7.82, y: 1.86, d: 0.66, icon: 'bottle', color: C.accent5 });
  heading(s, 'Antacids & PPIs', { x: 8.66, y: 1.9, w: 3.6, size: 20, color: C.accent5 });
  bullets(s, ['Increase gastric pH.',
              'May reduce the absorption of drugs that require an acidic environment '
              + 'for dissolution.'],
    { x: 7.82, y: 2.66, w: 4.4, h: 1.6, size: 14.5, gap: 9 });
  s.addShape(pres.ShapeType.roundRect, { x: 7.82, y: 4.42, w: 4.4, h: 0.46, rectRadius: 0.22,
    fill: { color: C.accent4, transparency: 84 }, line: { type: 'none' } });
  s.addText('Normal gastric pH  1 – 3', { x: 8.0, y: 4.42, w: 4.1, h: 0.46, fontSize: 13.5,
    bold: true, color: C.accent4, valign: 'middle', isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.downArrow, { x: 9.74, y: 4.96, w: 0.56, h: 0.56,
    fill: { color: C.accent5 }, line: { type: 'none' } });
  s.addShape(pres.ShapeType.roundRect, { x: 7.82, y: 5.6, w: 4.4, h: 0.46, rectRadius: 0.22,
    fill: { color: C.accent5, transparency: 80 }, line: { type: 'none' } });
  s.addText('With an antacid or PPI  →  higher pH', { x: 8.0, y: 5.6, w: 4.1, h: 0.46,
    fontSize: 13.5, bold: true, color: C.accent5, valign: 'middle', isTextBox: true, margin: 0 });
  s.addText('Example: ketoconazole taken with an antacid',
    { x: 7.82, y: 6.1, w: 4.4, h: 0.36, fontSize: 13, italic: true, color: C.accent6,
      isTextBox: true, margin: 0 });
  s.addNotes('Separating doses in time is the usual practical answer to an antacid interaction.');
}

/* ===================== 18. pharmaceutical applications ===================== */
{
  const s = slide('CONTENT_TINT', 'Applications');
  s.addText('Pharmaceutical applications', { placeholder: 'title' });
  const apps = [
    ['layers', 'Enteric-coated tablets', C.accent1],
    ['target', 'pH-dependent drug delivery', C.accent2],
    ['clock', 'Delayed-release formulations', C.accent3],
    ['trend', 'Improving bioavailability', C.accent5],
    ['exchange', 'Managing drug–drug and drug–food interactions', C.accent4],
  ];
  apps.slice(0, 3).forEach((a, i) => {
    const x = M + i * 4.1, w = 3.7, y = 1.74, h = 2.14;
    card(s, { x, y, w, h, fill: { color: C.background1 }, line: null });
    iconCircle(s, { x: x + (w - 0.84) / 2, y: y + 0.42, d: 0.84, icon: a[0], color: a[2] });
    s.addText(a[1], { x: x + 0.2, y: y + 1.44, w: w - 0.4, h: 0.72, fontSize: 16.5, bold: true,
      color: C.text1, align: 'center', valign: 'top', isTextBox: true, margin: 0 });
  });
  apps.slice(3).forEach((a, i) => {
    const x = M + i * 6.14, w = 5.76, y = 4.3, h = 2.0;
    card(s, { x, y, w, h, fill: { color: C.background1 }, line: null });
    iconCircle(s, { x: x + 0.42, y: y + 0.58, d: 0.84, icon: a[0], color: a[2] });
    s.addText(a[1], { x: x + 1.46, y: y + 0.35, w: w - 1.8, h: 1.3, fontSize: 16.5, bold: true,
      color: C.text1, valign: 'middle', isTextBox: true, margin: 0 });
  });
  s.addNotes('These are the formulation and counselling levers that follow from the physiology.');
}

/* ===================== 19. key takeaways ===================== */
pres.addSection({ title: 'Closing' });
{
  const s = pres.addSlide({ masterName: 'CLOSING', sectionTitle: 'Closing' });
  TRANS.push('fadeBlack');
  s.addShape(pres.ShapeType.ellipse, { x: 9.4, y: 2.9, w: 5.4, h: 5.4,
    fill: { color: C.accent1, transparency: 80 }, line: { type: 'none' } });
  s.addImage({ path: IMG('gi_mark'), x: 10.3, y: 2.0, w: 2.5, h: 3.73, objectName: '!!mark' });
  s.addText('Key takeaways', { placeholder: 'title' });
  const take = [
    ['droplet', 'pH varies along the gut', 'Stomach 1–3, duodenum 5–6, small intestine 6–7.5.'],
    ['charge', 'pH sets the ionization ratio', 'And with it solubility, stability and permeability.'],
    ['beaker', 'Secretions shape dissolution', 'HCl, bicarbonate, bile salts and intestinal fluid.'],
    ['layers', 'Formulation answers the problem', 'Enteric coats, delayed release, dose separation.'],
  ];
  take.forEach((t, i) => {
    const y = 1.92 + i * 1.18;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: 9.1, h: 1.0, rectRadius: 0.12,
      fill: { color: C.accent1, transparency: 70 }, line: { type: 'none' } });
    iconCircle(s, { x: M + 0.28, y: y + 0.19, d: 0.62, icon: t[0], color: C.accent2 });
    s.addText(t[1], { x: M + 1.08, y: y + 0.12, w: 7.8, h: 0.4, fontSize: 16, bold: true,
      color: C.background1, valign: 'middle', isTextBox: true, margin: 0 });
    s.addText(t[2], { x: M + 1.08, y: y + 0.5, w: 7.8, h: 0.38, fontSize: 13,
      color: C.accent2, valign: 'middle', isTextBox: true, margin: 0 });
  });
  s.addNotes('Close on the mechanism, not the drug list: pH and secretions act through four properties.');
}

/* ===================== 20. thank you ===================== */
{
  const s = pres.addSlide({ masterName: 'COVER', sectionTitle: 'Closing' });
  TRANS.push('morph');
  s.addShape(pres.ShapeType.ellipse, { x: 8.3, y: -1.5, w: 7.2, h: 7.2,
    fill: { color: C.accent1, transparency: 72 }, line: { type: 'none' } });
  s.addShape(pres.ShapeType.ellipse, { x: 10.1, y: 3.1, w: 4.6, h: 4.6,
    fill: { color: C.accent2, transparency: 84 }, line: { type: 'none' } });
  s.addImage({ path: IMG('gi_mark'), x: 9.05, y: 1.18, w: 3.4, h: 5.06, objectName: '!!mark' });
  s.addText('THANK YOU', { placeholder: 'kicker' });
  s.addText('Questions are welcome', { placeholder: 'title', objectName: '!!deckTitle' });
  s.addText([
    { text: 'Name:  ', options: { color: C.background1, bold: true } },
    { text: '______________________', options: { color: C.accent2, breakLine: true } },
    { text: 'Department of Pharmacy', options: { color: C.background1, breakLine: true } },
    { text: 'University:  ', options: { color: C.background1, bold: true } },
    { text: '______________________', options: { color: C.accent2 } },
  ], { placeholder: 'body', lineSpacingMultiple: 1.45 });
  s.addNotes('Thank the audience and invite questions.');
}

/* ===================== write ===================== */
pres.writeFile({ fileName: OUT })
  .then(() => applyTheme(OUT, THEME))
  .then(() => {
    require('fs').writeFileSync(path.join(__dirname, 'transitions.json'), JSON.stringify(TRANS));
    console.log('wrote', OUT, '\nslides:', TRANS.length, '\ntransitions:', TRANS.join(','));
  })
  .catch(e => { console.error('FAILED:', e); process.exit(1); });
