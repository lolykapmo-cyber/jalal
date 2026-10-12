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

Set in the slide XML by `src/postprocess.py`, because pptxgenjs writes neither
transitions nor animations:

- **Morph** (`byObject`, 1.1 s) on 15 slides, with a `<mc:Fallback>` cross-fade for
  renderers that predate PowerPoint 2016.
- **Fade through black** on the four section dividers and the takeaways slide.
- **Fade** on the title slide.

Images that should morph across a slide change share the name `!!mark`, the `!!`
prefix being how PowerPoint forces a morph match. Title placeholders morph on
their own because Morph pairs placeholders of the same type.

## 3D objects and animation

Five slides carry real 3D: `src/three.py` is a small software renderer (lathed
meshes, z-buffer, Blinn-Phong shading, 2x supersampling) and `src/scenes3d.py`
builds the scenes and writes them as looping GIFs, which PowerPoint plays by
itself in Slide Show view.

| Slide | Scene |
|---|---|
| 1 | Two-tone capsule tumbling, drug particles in orbit |
| 8 | A molecule crossing a lipid bilayer while the ionized one is turned back |
| 13 | A bile-salt micelle rotating around the drug it carries |
| 15 | Gastric acid deflecting off an enteric-coated capsule |
| 16 | Ca²⁺, Fe²⁺ and Mg²⁺ closing in on the drug to form a complex |

Each GIF's background is the exact fill of the slide area behind it (reserved in
the GIF palette, since median-cut otherwise shifts a flat colour by a few levels
and the panel shows as a rectangle), so the objects appear to float on the slide.

On the same five slides plus the takeaways, `postprocess.py` writes a `<p:timing>`
tree: 67 entrance effects (fade, float-up, zoom). Every step starts automatically
with an absolute delay — nothing waits on a click, so no content can stay hidden
if the presenter just advances slides. Shapes listed together in
`src/effects.json` animate as one unit, which is how a card and its icon, heading
and body arrive together without PowerPoint groups.

## Artwork

All 38 images are generated, not stock: 11 vector illustrations (GI tract, absorption
across the epithelium, lipid bilayer permeability, pH scale, bile-salt micelle,
enteric-coated capsule, chelation, secretions, food effect, aspirin structure,
ionization equilibrium) plus a 21-icon line set, authored as SVG and rasterised, and the five rendered
3D animations below.

## Rebuilding

```sh
cd src
npm install pptxgenjs sharp
node art.js                                   # regenerate img/*.png
NODE_PATH="$PWD/node_modules" node deck.js    # build the .pptx and apply the theme
python3 scenes3d.py                           # regenerate img/*.gif (~6 min)
python3 postprocess.py ../GI-pH-and-Secretions-in-Drug-Absorption.pptx \
        transitions.json effects.json
```
