// Illustration generator for the GI pH / drug absorption deck.
// Renders hand-authored SVG to transparent PNG via sharp.
const sharp = require('sharp');
const path = require('path');
const OUT = path.join(__dirname, 'img');

const P = {
  deep:   '#0B2B32',
  teal:   '#0E7C86',
  teal2:  '#12616B',
  mint:   '#17B3A3',
  mintL:  '#7FD9CE',
  pale:   '#E6F2F0',
  amber:  '#E8A33D',
  amberL: '#F6D9A8',
  terra:  '#C8553D',
  terraL: '#EBB3A6',
  slate:  '#3D6E8C',
  slateL: '#A9C4D3',
  gray:   '#5B7B7E',
  white:  '#FFFFFF',
};
const F = 'Carlito, Calibri, Liberation Sans, Arial, sans-serif';

function svg(w, h, body, scale = 3) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w * scale}" height="${h * scale}">
<defs>
<filter id="sh" x="-30%" y="-30%" width="160%" height="160%">
  <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#0B2B32" flood-opacity="0.18"/>
</filter>
<linearGradient id="acidG" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#C8553D"/><stop offset="0.28" stop-color="#E8A33D"/>
  <stop offset="0.52" stop-color="#C9CE72"/><stop offset="0.68" stop-color="#17B3A3"/>
  <stop offset="1" stop-color="#2F5E8C"/>
</linearGradient>
<linearGradient id="stomG" x1="0" y1="0" x2="0.4" y2="1">
  <stop offset="0" stop-color="#F3C98B"/><stop offset="1" stop-color="#E8A33D"/>
</linearGradient>
<linearGradient id="intG" x1="0" y1="0" x2="0.6" y2="1">
  <stop offset="0" stop-color="#3FA79E"/><stop offset="1" stop-color="#0E7C86"/>
</linearGradient>
</defs>
${body}</svg>`;
}

const jobs = [];
function add(name, w, h, body, scale) {
  jobs.push({ name, svg: svg(w, h, body, scale) });
}

/* ------------------------------------------------------------------ */
/* 1. GI tract — stylised, colour-coded by pH zone                      */
/* ------------------------------------------------------------------ */
const STOMACH = 'M252 150 C262 196 270 226 304 244 C340 263 356 292 352 324 '
              + 'C346 372 302 402 252 398 C186 392 146 338 146 274 '
              + 'C146 212 182 160 222 150 Z';
const OESO    = 'M252 36 L252 152';
const DUOD    = 'M352 310 C402 316 420 356 410 394 C400 432 364 448 330 446';
const COILS   = 'M330 446 C250 446 208 470 208 486 C208 504 258 512 334 512 '
              + 'C406 512 436 526 436 544 C436 562 376 570 300 570 '
              + 'C226 570 196 584 196 600 C196 618 252 626 330 626 '
              + 'C396 626 420 638 416 652';

function giTract(dark) {
  const line = dark ? '#0B2B32' : '#FFFFFF';
  const label = dark ? P.white : P.deep;
  const sub = dark ? P.mintL : P.gray;
  return `
  <g transform="translate(96,0)">
    <path d="${OESO}" stroke="${P.terraL}" stroke-width="30" stroke-linecap="round" fill="none"/>
    <path d="${OESO}" stroke="${line}" stroke-width="7" stroke-linecap="round" fill="none" opacity="0.55"/>
    <path d="${STOMACH}" fill="url(#stomG)" stroke="${P.terra}" stroke-width="5" stroke-linejoin="round"/>
    <path d="M232 200 C222 244 232 290 262 320" stroke="${P.terra}" stroke-width="4"
          fill="none" opacity="0.45" stroke-linecap="round"/>
    <path d="M196 214 C186 258 196 304 226 334" stroke="${P.terra}" stroke-width="4"
          fill="none" opacity="0.3" stroke-linecap="round"/>
    <path d="${DUOD}" stroke="${P.amber}" stroke-width="30" fill="none" stroke-linecap="round"/>
    <path d="${DUOD}" stroke="${line}" stroke-width="8" fill="none" stroke-linecap="round" opacity="0.5"/>
    <path d="${COILS}" stroke="url(#intG)" stroke-width="30" fill="none"
          stroke-linecap="round" stroke-linejoin="round"/>
    <path d="${COILS}" stroke="${line}" stroke-width="8" fill="none"
          stroke-linecap="round" stroke-linejoin="round" opacity="0.45"/>
  </g>
    <g font-family="${F}" font-size="22" fill="${label}">
      <circle cx="222" cy="252" r="7" fill="${P.terra}"/>
      <text x="204" y="248" font-weight="700" text-anchor="end">Stomach</text>
      <text x="204" y="276" font-size="20" fill="${sub}" text-anchor="end">pH 1 – 3</text>
      <circle cx="548" cy="384" r="7" fill="${P.amber}"/>
      <text x="566" y="380" font-weight="700">Duodenum</text>
      <text x="566" y="408" font-size="20" fill="${sub}">pH 5 – 6</text>
      <circle cx="272" cy="556" r="7" fill="${P.teal}"/>
      <text x="254" y="552" font-weight="700" text-anchor="end">Small intestine</text>
      <text x="254" y="580" font-size="20" fill="${sub}" text-anchor="end">pH 6 – 7.5</text>
    </g>`;
}
add('gi_light', 800, 700, giTract(false));
add('gi_dark', 800, 700, giTract(true));

// Unlabelled silhouette for decorative use on dark slides
add('gi_mark', 470, 700, `
  <g opacity="0.95">
    <path d="${OESO}" stroke="${P.mint}" stroke-width="26" stroke-linecap="round" fill="none" opacity="0.35"/>
    <path d="${STOMACH}" fill="none" stroke="${P.mint}" stroke-width="7" stroke-linejoin="round" opacity="0.6"/>
    <path d="${DUOD}" stroke="${P.mint}" stroke-width="26" fill="none" stroke-linecap="round" opacity="0.4"/>
    <path d="${COILS}" stroke="${P.mint}" stroke-width="26" fill="none"
          stroke-linecap="round" stroke-linejoin="round" opacity="0.45"/>
  </g>`);

/* ------------------------------------------------------------------ */
/* 2. Absorption: lumen -> epithelium -> blood                          */
/* ------------------------------------------------------------------ */
(function () {
  let villi = '';
  for (let i = 0; i < 6; i++) {
    const y = 46 + i * 50;
    villi += `<path d="M330 ${y} C300 ${y - 14} 288 ${y + 2} 292 ${y + 16}
               C296 ${y + 30} 316 ${y + 34} 330 ${y + 26} Z" fill="${P.mintL}" stroke="${P.teal}" stroke-width="3"/>`;
  }
  let cells = '';
  for (let i = 0; i < 6; i++) {
    cells += `<rect x="332" y="${34 + i * 50}" width="74" height="44" rx="10"
              fill="${P.pale}" stroke="${P.teal}" stroke-width="3"/>
              <circle cx="369" cy="${56 + i * 50}" r="8" fill="${P.mint}"/>`;
  }
  let rbc = '';
  for (let i = 0; i < 5; i++) {
    rbc += `<ellipse cx="${520 + (i % 2) * 44}" cy="${66 + i * 56}" rx="26" ry="17"
            fill="${P.terraL}" stroke="${P.terra}" stroke-width="3"/>`;
  }
  add('absorption', 760, 398, `
    <rect x="16" y="18" width="300" height="320" rx="22" fill="${P.amberL}" opacity="0.5"/>
    <rect x="470" y="18" width="274" height="320" rx="22" fill="${P.pale}"/>
    <rect x="486" y="34" width="242" height="288" rx="18" fill="${P.white}" stroke="${P.terra}"
          stroke-width="4" stroke-dasharray="10 9"/>
    ${rbc}
    ${cells}${villi}
    <g fill="${P.teal2}">
      <rect x="60" y="84" width="112" height="52" rx="26" fill="${P.white}" stroke="${P.teal}" stroke-width="5"/>
      <rect x="60" y="84" width="56" height="52" rx="26" fill="${P.mint}" stroke="${P.teal}" stroke-width="5"/>
      <circle cx="200" cy="112" r="9"/><circle cx="238" cy="146" r="7"/>
      <circle cx="168" cy="186" r="8"/><circle cx="226" cy="214" r="10"/>
      <circle cx="140" cy="252" r="7"/><circle cx="208" cy="288" r="9"/>
      <circle cx="262" cy="248" r="7"/><circle cx="252" cy="330" r="8"/>
    </g>
    <path d="M250 200 L452 200" stroke="${P.teal}" stroke-width="10" stroke-linecap="round"
          marker-end="url(#ar)"/>
    <defs><marker id="ar" markerWidth="9" markerHeight="9" refX="5" refY="4.5" orient="auto">
      <path d="M0 0 L9 4.5 L0 9 z" fill="${P.teal}"/></marker></defs>
    <g font-family="${F}" font-size="22" font-weight="700" fill="${P.deep}" text-anchor="middle">
      <text x="166" y="382">GI lumen</text>
      <text x="369" y="382">Epithelium</text>
      <text x="607" y="382">Bloodstream</text>
    </g>`);
})();

/* ------------------------------------------------------------------ */
/* 3. Membrane permeability: unionized vs ionized                       */
/* ------------------------------------------------------------------ */
(function () {
  let heads = '';
  for (let x = 24; x < 820; x += 34) {
    heads += `<circle cx="${x}" cy="196" r="14" fill="${P.amberL}" stroke="${P.amber}" stroke-width="3"/>
              <path d="M${x - 5} 210 l0 34 M${x + 5} 210 l0 34" stroke="${P.amber}" stroke-width="4" stroke-linecap="round"/>
              <circle cx="${x}" cy="258" r="14" fill="${P.amberL}" stroke="${P.amber}" stroke-width="3"/>`;
  }
  add('membrane', 840, 440, `
    <rect x="0" y="0" width="840" height="182" rx="16" fill="${P.pale}" opacity="0.75"/>
    <rect x="0" y="272" width="840" height="168" rx="16" fill="${P.pale}" opacity="0.4"/>
    ${heads}
    <g>
      <circle cx="206" cy="92" r="42" fill="${P.white}" stroke="${P.teal}" stroke-width="6"/>
      <text x="206" y="102" font-family="${F}" font-size="30" font-weight="700"
            fill="${P.teal2}" text-anchor="middle">HA</text>
      <path d="M206 142 L206 318" stroke="${P.mint}" stroke-width="10" stroke-linecap="round"
            marker-end="url(#ar2)"/>
      <circle cx="206" cy="372" r="30" fill="${P.mint}" opacity="0.25"/>
      <text x="206" y="382" font-family="${F}" font-size="24" font-weight="700"
            fill="${P.teal2}" text-anchor="middle">HA</text>
    </g>
    <g>
      <circle cx="628" cy="92" r="42" fill="${P.white}" stroke="${P.terra}" stroke-width="6"/>
      <text x="628" y="102" font-family="${F}" font-size="28" font-weight="700"
            fill="${P.terra}" text-anchor="middle">A</text>
      <circle cx="668" cy="58" r="17" fill="${P.terra}"/>
      <path d="M660 58 h16" stroke="${P.white}" stroke-width="4" stroke-linecap="round"/>
      <path d="M628 142 L628 172" stroke="${P.terra}" stroke-width="10" stroke-linecap="round"/>
      <circle cx="628" cy="226" r="36" fill="${P.white}" opacity="0.92"/>
      <path d="M608 206 L648 246 M648 206 L608 246" stroke="${P.terra}" stroke-width="10" stroke-linecap="round"/>
      <circle cx="548" cy="78" r="9" fill="${P.slateL}"/><circle cx="700" cy="128" r="8" fill="${P.slateL}"/>
      <circle cx="568" cy="140" r="7" fill="${P.slateL}"/><circle cx="690" cy="46" r="7" fill="${P.slateL}"/>
    </g>
    <defs><marker id="ar2" markerWidth="9" markerHeight="9" refX="5" refY="4.5" orient="auto">
      <path d="M0 0 L9 4.5 L0 9 z" fill="${P.mint}"/></marker></defs>
    <g font-family="${F}" font-size="21" fill="${P.deep}">
      <text x="24" y="34" font-weight="700">Unionized — crosses the lipid membrane</text>
      <text x="206" y="424" font-size="20" fill="${P.gray}" text-anchor="middle">Absorbed into blood</text>
      <text x="560" y="34" font-weight="700" fill="${P.terra}">Ionized — poor permeability</text>
      <text x="24" y="312" font-size="20" fill="${P.amber}" font-weight="700">Lipid bilayer</text>
    </g>`);
})();

/* ------------------------------------------------------------------ */
/* 4. pH scale                                                          */
/* ------------------------------------------------------------------ */
(function () {
  let ticks = '';
  for (let i = 1; i <= 14; i++) {
    const x = 40 + (i - 1) * 62;
    ticks += `<text x="${x}" y="150" font-family="${F}" font-size="22" font-weight="700"
              fill="${P.deep}" text-anchor="middle">${i}</text>
              <path d="M${x} 104 l0 12" stroke="${P.white}" stroke-width="3" opacity="0.7"/>`;
  }
  function pin(x, label, color) {
    return `<g><path d="M${x} 96 L${x - 16} 60 L${x + 16} 60 Z" fill="${color}"/>
      <rect x="${x - 86}" y="14" width="172" height="48" rx="12" fill="${color}"/>
      <text x="${x}" y="45" font-family="${F}" font-size="22" font-weight="700" fill="${P.white}"
      text-anchor="middle">${label}</text></g>`;
  }
  add('ph_scale', 920, 170, `
    <rect x="18" y="72" width="884" height="46" rx="23" fill="url(#acidG)"/>
    ${ticks}
    ${pin(102, 'Stomach 1–3', P.terra)}
    ${pin(382, 'Duodenum 5–6', P.amber)}
    ${pin(692, 'Intestine 6–7.5', P.teal)}`);
})();

/* ------------------------------------------------------------------ */
/* 5. Bile salt micelle                                                 */
/* ------------------------------------------------------------------ */
(function () {
  let salts = '';
  const n = 18, R = 128;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const cx = 260 + Math.cos(a) * R, cy = 230 + Math.sin(a) * R;
    const hx = 260 + Math.cos(a) * (R + 34), hy = 230 + Math.sin(a) * (R + 34);
    salts += `<path d="M${cx} ${cy} L${hx} ${hy}" stroke="${P.amber}" stroke-width="7" stroke-linecap="round"/>
              <circle cx="${hx}" cy="${hy}" r="15" fill="${P.amber}"/>`;
  }
  add('micelle', 520, 470, `
    <circle cx="260" cy="230" r="128" fill="${P.pale}"/>
    ${salts}
    <g fill="${P.teal}">
      <rect x="208" y="196" width="96" height="44" rx="22" fill="${P.white}" stroke="${P.teal}" stroke-width="5"/>
      <rect x="208" y="196" width="48" height="44" rx="22" fill="${P.mint}" stroke="${P.teal}" stroke-width="5"/>
      <circle cx="222" cy="152" r="11"/><circle cx="296" cy="272" r="10"/>
      <circle cx="206" cy="282" r="9"/><circle cx="312" cy="170" r="8"/>
    </g>
    <text x="260" y="446" font-family="${F}" font-size="23" font-weight="700" fill="${P.deep}"
          text-anchor="middle">Micelle carrying a poorly soluble drug</text>`);
})();

/* ------------------------------------------------------------------ */
/* 6. Enteric-coated dosage form                                        */
/* ------------------------------------------------------------------ */
add('enteric', 760, 380, `
  <text x="196" y="36" font-family="${F}" font-size="24" font-weight="700"
        fill="${P.terra}" text-anchor="middle">Gastric acid (HCl)</text>
  <g>
    <path d="M72 84 q14 -28 28 0 a16 16 0 0 1 -28 0" fill="${P.terra}"/>
    <path d="M152 74 q14 -28 28 0 a16 16 0 0 1 -28 0" fill="${P.terra}"/>
    <path d="M232 84 q14 -28 28 0 a16 16 0 0 1 -28 0" fill="${P.terra}"/>
    <path d="M310 74 q14 -28 28 0 a16 16 0 0 1 -28 0" fill="${P.terra}"/>
    <path d="M86 116 l0 24 M166 106 l0 24 M246 116 l0 24 M324 106 l0 24"
          stroke="${P.terra}" stroke-width="5" stroke-linecap="round" opacity="0.55"/>
    <path d="M62 176 q24 -26 48 0 M166 176 q24 -26 48 0 M270 176 q24 -26 48 0"
          stroke="${P.terra}" stroke-width="4" fill="none" opacity="0.35"/>
  </g>
  <g transform="translate(44,196)">
    <rect x="0" y="0" width="302" height="144" rx="72" fill="${P.slateL}" stroke="${P.slate}" stroke-width="6"/>
    <rect x="22" y="22" width="258" height="100" rx="50" fill="${P.white}" stroke="${P.teal}" stroke-width="5"/>
    <g fill="${P.mint}">
      <circle cx="96" cy="58" r="13"/><circle cx="150" cy="88" r="11"/>
      <circle cx="206" cy="56" r="12"/><circle cx="140" cy="46" r="9"/><circle cx="198" cy="96" r="9"/>
    </g>
  </g>
  <g font-family="${F}" font-size="23" fill="${P.deep}">
    <text x="420" y="188" font-weight="700" fill="${P.slate}">Enteric coat</text>
    <text x="420" y="218" font-size="21" fill="${P.gray}">resists gastric acid</text>
    <text x="420" y="278" font-weight="700" fill="${P.teal2}">Drug core</text>
    <text x="420" y="308" font-size="21" fill="${P.gray}">released in the intestine</text>
  </g>
  <path d="M376 180 L404 180 M376 270 L404 270" stroke="${P.gray}" stroke-width="3" opacity="0.5"/>`);

/* 7. Chelation / complex formation                                     */
/* ------------------------------------------------------------------ */
add('chelation', 640, 400, `
  <g>
    <rect x="34" y="128" width="180" height="92" rx="46" fill="${P.white}" stroke="${P.teal}" stroke-width="6"/>
    <text x="124" y="184" font-family="${F}" font-size="24" font-weight="700"
          fill="${P.teal2}" text-anchor="middle">Drug</text>
    <text x="268" y="186" font-family="${F}" font-size="44" font-weight="700" fill="${P.gray}"
          text-anchor="middle">+</text>
    <g font-family="${F}" font-size="21" font-weight="700" fill="${P.white}" text-anchor="middle">
      <circle cx="372" cy="104" r="40" fill="${P.amber}"/><text x="372" y="112">Ca²⁺</text>
      <circle cx="458" cy="174" r="40" fill="${P.terra}"/><text x="458" y="182">Fe²⁺</text>
      <circle cx="372" cy="244" r="40" fill="${P.slate}"/><text x="372" y="252">Mg²⁺</text>
    </g>
    <path d="M214 174 L332 118 M214 174 L418 174 M214 174 L332 230"
          stroke="${P.gray}" stroke-width="5" stroke-dasharray="9 8"/>
  </g>
  <g>
    <rect x="118" y="300" width="404" height="66" rx="33" fill="${P.terraL}" opacity="0.55"/>
    <text x="320" y="342" font-family="${F}" font-size="23" font-weight="700"
          fill="${P.terra}" text-anchor="middle">Insoluble complex → absorption reduced</text>
  </g>`);

/* ------------------------------------------------------------------ */
/* 8. Secretions into the gut                                          */
/* ------------------------------------------------------------------ */
add('secretions', 780, 450, `
  <g transform="translate(-30,-22) scale(0.78)">
    <path d="${OESO}" stroke="${P.terraL}" stroke-width="30" stroke-linecap="round" fill="none"/>
    <path d="${STOMACH}" fill="url(#stomG)" stroke="${P.terra}" stroke-width="6" stroke-linejoin="round"/>
    <path d="${DUOD}" stroke="${P.amber}" stroke-width="32" fill="none" stroke-linecap="round"/>
    <path d="${DUOD}" stroke="${P.white}" stroke-width="9" fill="none" stroke-linecap="round" opacity="0.5"/>
  </g>
  <g>
    <ellipse cx="588" cy="120" rx="112" ry="46" fill="${P.mintL}" stroke="${P.teal}" stroke-width="5"/>
    <text x="588" y="129" font-family="${F}" font-size="24" font-weight="700"
          fill="${P.teal2}" text-anchor="middle">Pancreas</text>
    <path d="M488 150 L296 228" stroke="${P.teal}" stroke-width="7" stroke-linecap="round"
          stroke-dasharray="2 13"/>
    <text x="452" y="206" font-family="${F}" font-size="23" font-weight="700" fill="${P.teal}">HCO₃⁻</text>
  </g>
  <g>
    <path d="M636 268 c-30 -36 -84 -32 -92 11 c-9 43 32 79 71 79 c43 0 62 -39 47 -71"
          fill="${P.amberL}" stroke="${P.amber}" stroke-width="5"/>
    <path d="M548 318 L300 296" stroke="${P.amber}" stroke-width="7" stroke-linecap="round"
          stroke-dasharray="2 13"/>
    <text x="616" y="404" font-family="${F}" font-size="23" font-weight="700"
          fill="${P.amber}" text-anchor="middle">Bile salts</text>
  </g>
  <g fill="${P.terra}" opacity="0.85">
    <circle cx="118" cy="178" r="8"/><circle cx="166" cy="214" r="7"/><circle cx="92" cy="232" r="7"/>
    <circle cx="150" cy="268" r="6"/>
  </g>
  <g font-family="${F}" font-size="23" font-weight="700">
    <text x="122" y="128" fill="${P.terra}">HCl</text>
    <text x="196" y="410" fill="${P.amber}" text-anchor="middle">Duodenum</text>
    <path d="M226 392 L272 334" stroke="${P.amber}" stroke-width="3" opacity="0.6"/>
  </g>`);

/* 9. Food effect                                                      */
/* ------------------------------------------------------------------ */
add('food', 620, 380, `
  <g transform="translate(26,24) scale(0.74)">
    <path d="${STOMACH}" fill="${P.amberL}" stroke="${P.amber}" stroke-width="6"/>
    <g fill="${P.terra}" opacity="0.65">
      <circle cx="222" cy="234" r="19"/><circle cx="272" cy="286" r="15"/>
      <circle cx="196" cy="300" r="17"/><circle cx="258" cy="200" r="13"/>
      <circle cx="166" cy="246" r="12"/><circle cx="238" cy="338" r="14"/>
    </g>
  </g>
  <g transform="translate(400,96)">
    <circle cx="90" cy="90" r="80" fill="${P.white}" stroke="${P.teal}" stroke-width="8"/>
    <path d="M90 40 L90 94 L128 114" stroke="${P.teal2}" stroke-width="10"
          stroke-linecap="round" fill="none"/>
  </g>
  <path d="M300 186 L384 186" stroke="${P.teal}" stroke-width="9" stroke-linecap="round"
        stroke-dasharray="4 16"/>
  <text x="490" y="316" font-family="${F}" font-size="22" font-weight="700"
        fill="${P.teal2}" text-anchor="middle">Delayed gastric emptying</text>`);

/* ------------------------------------------------------------------ */
/* 10. Aspirin skeletal structure                                      */
/* ------------------------------------------------------------------ */
add('aspirin', 470, 320, `
  <g stroke="${P.teal2}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M110 110 L162 80 L214 110 L214 170 L162 200 L110 170 Z"/>
    <path d="M122 122 L122 158 M172 94 L202 112 M202 168 L172 186"/>
    <path d="M214 110 L262 82"/>
    <path d="M256 70 L256 38 M268 70 L268 38"/>
    <path d="M262 82 L306 60"/>
    <path d="M214 170 L256 194"/>
    <path d="M280 206 L322 232"/>
    <path d="M316 232 L316 272 M328 232 L328 272"/>
    <path d="M322 232 L366 206"/>
  </g>
  <g font-family="${F}" font-size="26" font-weight="700" fill="${P.deep}">
    <text x="262" y="30" text-anchor="middle">O</text>
    <text x="316" y="60">OH</text>
    <text x="268" y="212" text-anchor="middle">O</text>
    <text x="322" y="300" text-anchor="middle">O</text>
    <text x="374" y="204">CH₃</text>
  </g>
`);

/* 11. Equilibrium see-saw (ionization ratio)                           */
/* ------------------------------------------------------------------ */
add('equilibrium', 720, 300, `
  <g>
    <rect x="36" y="86" width="250" height="90" rx="20" fill="${P.pale}" stroke="${P.teal}" stroke-width="5"/>
    <text x="161" y="142" font-family="${F}" font-size="30" font-weight="700"
          fill="${P.teal2}" text-anchor="middle">Unionized</text>
    <rect x="434" y="86" width="250" height="90" rx="20" fill="${P.terraL}" opacity="0.5"/>
    <rect x="434" y="86" width="250" height="90" rx="20" fill="none" stroke="${P.terra}" stroke-width="5"/>
    <text x="559" y="142" font-family="${F}" font-size="30" font-weight="700"
          fill="${P.terra}" text-anchor="middle">Ionized</text>
    <path d="M300 112 L418 112" stroke="${P.gray}" stroke-width="6" stroke-linecap="round" marker-end="url(#ar3)"/>
    <path d="M418 152 L300 152" stroke="${P.gray}" stroke-width="6" stroke-linecap="round" marker-end="url(#ar4)"/>
    <defs>
      <marker id="ar3" markerWidth="8" markerHeight="8" refX="4.5" refY="4" orient="auto">
        <path d="M0 0 L8 4 L0 8 z" fill="${P.gray}"/></marker>
      <marker id="ar4" markerWidth="8" markerHeight="8" refX="4.5" refY="4" orient="auto">
        <path d="M0 0 L8 4 L0 8 z" fill="${P.gray}"/></marker>
    </defs>
    <text x="360" y="238" font-family="${F}" font-size="24" font-weight="700"
          fill="${P.deep}" text-anchor="middle">Ratio set by pH and pKa</text>
  </g>`);

/* ------------------------------------------------------------------ */
/* Icons (white line icons for coloured circles)                        */
/* ------------------------------------------------------------------ */
const ICONS = {
  droplet: '<path d="M12 2.7l5.7 5.7a8 8 0 1 1-11.4 0z"/>',
  charge: '<circle cx="8" cy="8" r="5"/><path d="M5.8 8h4.4"/><circle cx="16" cy="16" r="5"/>'
        + '<path d="M13.8 16h4.4M16 13.8v4.4"/>',
  shield: '<path d="M12 21.5s7.5-3.8 7.5-9.5V5.3L12 2.5 4.5 5.3V12c0 5.7 7.5 9.5 7.5 9.5z"/>'
        + '<path d="M9 12l2 2 4-4"/>',
  dissolve: '<circle cx="12" cy="12" r="6.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2'
          + 'M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M19.1 4.9l-1.5 1.5M6.4 17.6l-1.5 1.5"/>',
  capsule: '<rect x="2.6" y="8.4" width="18.8" height="7.2" rx="3.6" transform="rotate(-45 12 12)"/>'
         + '<path d="M9.6 6.9l7.5 7.5"/>',
  stomach: '<path d="M10 2.6v3c0 2 .8 3 2.4 3.7 2 .9 3 2.4 2.8 4.1-.3 2.7-2.8 4.5-5.6 4.2'
         + '-3-.3-5.2-3-5.2-6.3 0-3 1.9-5.7 4-6.4"/><path d="M8.4 2.6h3.2"/>'
         + '<path d="M6.6 9.6c-.6 2.6 0 4.6 1.8 6"/>',
  intestine: '<path d="M18 4c-4 0-6 1.4-6 2.6S14 9 18 9s3 1.3 3 2.4-2 2.4-6 2.4-6 1.3-6 2.5S11 19 15 19"/>'
           + '<path d="M6 4h3M4 19h4"/>',
  beaker: '<path d="M9 3h6M10 3v6L4.8 18.6A2 2 0 0 0 6.6 21.6h10.8a2 2 0 0 0 1.8-3L14 9V3"/>'
        + '<path d="M7.2 14h9.6"/>',
  bile: '<path d="M8.5 3.2l3.6 3.6a5.1 5.1 0 1 1-7.2 0z"/>'
      + '<path d="M16.8 11.4l2.6 2.6a3.7 3.7 0 1 1-5.2 0z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6.5V12l3.8 2"/>',
  food: '<path d="M4 2.5v6a3 3 0 0 0 6 0v-6"/><path d="M7 11.5V21.5"/>'
      + '<path d="M18 2.5c-2 0-3.2 2.4-3.2 6s1.2 4.6 3.2 4.6v8.4"/>',
  bottle: '<path d="M9.5 2.5h5v3.4l2.6 2.8a3 3 0 0 1 .9 2.1v8.7a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-8.7'
        + 'a3 3 0 0 1 .9-2.1L9.5 5.9z"/><path d="M6 12.5h12"/>',
  layers: '<path d="M12 2.5L2.5 7 12 11.5 21.5 7z"/><path d="M2.5 16.8L12 21.4l9.5-4.6"/>'
        + '<path d="M2.5 11.9L12 16.5l9.5-4.6"/>',
  trend: '<path d="M22.5 6.5L13.5 15.5l-4.5-4.5L1.5 18.5"/><path d="M16.5 6.5h6v6"/>',
  exchange: '<path d="M17 1.5l4 4-4 4"/><path d="M3 11.5v-2a4 4 0 0 1 4-4h14"/>'
          + '<path d="M7 22.5l-4-4 4-4"/><path d="M21 12.5v2a4 4 0 0 1-4 4H3"/>',
  alert: '<path d="M10.3 3.9L1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
       + '<path d="M12 9.2v4.4M12 17.2h.02"/>',
  bulb: '<path d="M9 19h6M10 22h4"/><path d="M12 2a6.5 6.5 0 0 0-3.8 11.8c.7.5 1.1 1.3 1.1 2.2h5.4'
      + 'c0-.9.4-1.7 1.1-2.2A6.5 6.5 0 0 0 12 2z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.3"/>',
  list: '<path d="M8.5 6.5h12M8.5 12h12M8.5 17.5h12"/><circle cx="4" cy="6.5" r="1.4"/>'
      + '<circle cx="4" cy="12" r="1.4"/><circle cx="4" cy="17.5" r="1.4"/>',
  acid: '<path d="M12 2.7l5.7 5.7a8 8 0 1 1-11.4 0z"/><path d="M9.6 13.5h4.8M12 11.1v4.8"/>',
};
for (const [name, body] of Object.entries(ICONS)) {
  add(`ic_${name}`, 24, 24,
    `<g fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</g>`,
    14);
}

/* ------------------------------------------------------------------ */
Promise.all(jobs.map(j =>
  sharp(Buffer.from(j.svg)).png({ compressionLevel: 9 }).toFile(path.join(OUT, j.name + '.png'))
)).then(r => {
  console.log(`rendered ${r.length} images`);
}).catch(e => { console.error('FAILED:', e.message); process.exit(1); });
