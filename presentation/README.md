# Role of Gastrointestinal pH and Secretions in Drug Absorption

A 20-slide PowerPoint deck (16:9) for a pharmacy / biopharmaceutics presentation.

**Deliverable:** `GI-pH-and-Secretions-in-Drug-Absorption.pptx`

## What is in the deck

| Slides | Content |
|---|---|
| 1–2 | Title and agenda |
| 3–4 | Drug absorption; the four properties GI conditions influence |
| 5–7 | Section 01 — GI pH: pH by site, how pH affects drugs |
| 8–10 | Ionized vs. unionized drug, weak acids/bases, Henderson–Hasselbalch |
| 11–13 | Section 02 — Secretions: HCl, bicarbonate, bile salts, intestinal fluid |
| 14–16 | Section 03 — Omeprazole, ketoconazole, aspirin, tetracyclines |
| 17–18 | Food, antacids and PPIs; pharmaceutical applications |
| 19–20 | Key takeaways and closing |

Slide 1 and slide 20 contain blanks for the presenter name and the university.
Every slide carries speaker notes.

## Transitions

Set in the slide XML, because pptxgenjs cannot write transitions:

- **Morph** (`byObject`, 1.1 s) on 15 slides, with a `<mc:Fallback>` cross-fade for
  renderers that predate PowerPoint 2016.
- **Fade through black** on the four section dividers and the takeaways slide.
- **Fade** on the title slide.

Shapes that should morph across a slide change share a name prefixed with `!!`
(`!!mark`, `!!sec1`…), which is how PowerPoint forces a morph match.

## Artwork

All 33 images are generated, not stock: 11 vector illustrations (GI tract, absorption
across the epithelium, lipid bilayer permeability, pH scale, bile-salt micelle,
enteric-coated capsule, chelation, secretions, food effect, aspirin structure,
ionization equilibrium) plus a 21-icon line set, authored as SVG and rasterised.

## Rebuilding

```sh
cd src
npm install pptxgenjs sharp
node art.js                                   # regenerate img/*.png
NODE_PATH="$PWD/node_modules" node deck.js    # build the .pptx and apply the theme
python3 transitions.py ../GI-pH-and-Secretions-in-Drug-Absorption.pptx transitions.json
```
