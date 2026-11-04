# CR-003 Refraction Ledger

Creative Research recipe: original luxury **photographic** product still-life
focused on transparent faceted glass, brushed metal, and honed limestone.
PromptRecipe library only—no image generation, custody import, or gallery
publication in this delivery.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-003-refraction-ledger/1.0.0.json` |
| `recipe_id` | `cr-003-refraction-ledger` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `new_generation` |
| Historical packs | none (`packs: []`) |
| ArtMethodPack | none (`art.method` / form / state = `null`) |

## Original creative brief

**Refraction Ledger** — an unbranded short vertical faceted glass perfume flacon
with a flush brushed-metal cap, centered on a honed limestone plinth in a
controlled studio. Communicate luxury commercial product photography: readable
glass thickness, controlled reflection/refraction cues, credible brushed-metal
grain, fine matte stone texture, plausible contact shadows, restrained palette,
and deliberate editorial composition. No humans, logos, lettering, or unrelated
props. Photographic material realism without excessive CGI gloss.

## Research sources and extracted principles

Targeted photographic/material references (techniques only; no proprietary
prompts or third-party images were copied):

| Source | Type | Extracted principle |
| --- | --- | --- |
| Pro Photo Studio — How to Photograph Glass Products | commercial how-to | Light the environment glass reflects/transmits; bright-field uses lit surround + black flags for dark edge lines |
| DIY Photography — dark-field / bright-field crossover | studio technique | Dark-field: dark surround + side white cards for luminous edges; do not mix opposing field tactics in one setup |
| WestcottU — Dark Field Imaging | studio technique | Large rear light blocked by a dark patch; spill grazes edges; keep lens off direct source |
| Society of Photographers — glass contrast | technique overview | Contrast reveals form; light surround → dark cards; dark surround → light cards |
| Nightjar / reflective-product notes | commercial practice | Graduated diffusion reflections; brushed metal needs directional grain, not flat wipe-out diffusion |
| Real Room Lighting — brushed vs polished metal | material lighting | Brushed: moderate diffusion + directional highlight; polished: mirror-like singular specular |
| VenusLens / PixelPrep — flags, strips, negative fill | modifier practice | Strip lights for bottle/cap linear highlights; matte black flags as reflection design |
| Lithoprime / Verostone / pedestal product notes | stone & plinth | Honed stone is matte/diffuse; softboxes or overcast-like key reveal texture without glare; soft contact shadow under plinth |

### Mechanisms that influence the recipe

1. **Glass is an environment mirror/transmitter** — describe surround + flags, not “light the glass directly.”
2. **Bright-field vs dark-field are mutually exclusive strategies** — each lighting variant commits to one.
3. **Brushed metal ≠ polished chrome** — elongated soft grain highlights, not mirror blowouts.
4. **Honed limestone** — matte pores, soft falloff; avoid polished marble glare language.
5. **Strip + negative fill** — commercial bottle form without conflicting reflections.
6. **AI failure modes to avoid in wording** — opaque crystal glass, melted facets, chrome-everything metal, floating product with no contact shadow, brand lettering, extra props, human hands.

Established photographic techniques are stated as lighting/material direction.
Artistic interpretation (restrained palette, “ledger” micro-story) is labeled as
editorial framing, not optical law. Caustics/refraction are plausibility goals,
not claims of verified ray-accurate simulation.

## Material and lighting decisions

| Layer | Decision |
| --- | --- |
| Glass | Transparent faceted flacon; readable wall thickness; calm clear liquid |
| Metal | Brushed satin grain cap flush on neck; not polished chrome |
| Stone | Honed limestone plinth; matte fine texture |
| Baseline light (l0) | Bright-field: light surround + black flags for dark glass edges + soft strip on cap |
| Light l1 | Dark-field luxury: charcoal surround + luminous side edge lines |
| Light l2 | Dual strip + negative fill; single coherent strategy (no second field style) |
| Palette | Warm-neutral gray studio; restrained commercial tonality |

## Schema / route rationale

- PromptRecipe **v1.1** with variables only on `director.camera`,
  `director.light_source`, `output.aspect_ratio`.
- Route `new_generation` (supported compatible path for living photographic output).
- Empty EraPack list; `art.method` null — photographic product, not artifact/
  art-method transform.
- No new TransformationPack, ArtMethodPack, or historical pack.
- Director fields originally oriented to human editorial are reused with
  **product-still-life semantics** (no schema invention). Compiler still emits a
  generic body/presentation sentence; recipe text keeps product-only locks.

## Variant definitions

| Key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | c0 eye-level three-quarter hero; c1 slightly elevated onto plinth top; c2 tighter glass/cap junction crop |
| `light` | `director.light_source` | l0 bright-field flags; l1 dark-field luxury; l2 dual strip + negative fill |
| `aspect` | `output.aspect_ratio` | `4:5` (baseline), `1:1` |

All **18** camera × light × aspect combinations are supported bindings. Product
identity (faceted flacon + brushed cap + limestone plinth) is static across
variants.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `844a63f40d8c1e2fa9339c06f7936daad2d1fb14186372e2b70727078d94f1f3` |
| Baseline compiled prompt (c0/l0/4:5) | `e0c131daf9badac5ec5cac960a33e14f928345a299846a5ad767bb50feee271f` |

## Baseline compiled prompt audit (c0/l0/4:5)

- Photographic product still-life language present; no fashion gown / Song / ink.
- Transparent glass, brushed metal, limestone plinth roles distinct.
- Bright-field edge definition only in baseline light (no dark-field contradiction).
- Aspect `4:5` substituted; no ArtMethod or EraPack sections.
- States photographic plausibility for caustics/reflections; avoids ray-traced
  showcase promises.
- Compiler body line remains generic presentation text (engine invariant; not
  changed in this PR).

## Known generative-image limitations

- Models often thicken glass into opaque crystal or melt facet geometry.
- Metal may become mirror chrome or plastic gray.
- Reflections may invent room clutter, logos, or duplicated bottles.
- Contact shadows and liquid meniscus are frequently wrong or absent.
- Prompt quality does **not** prove rendered physical accuracy.

## Creative acceptance criteria (for a later generation gate)

1. Single unbranded flacon + seated brushed-metal cap + limestone plinth only.
2. Glass reads transparent with edge thickness; not opaque crystal block.
3. Metal reads brushed, not polished chrome or painted plastic.
4. Stone reads matte/honed; soft plausible contact shadow.
5. Lighting matches the chosen field strategy without mixed bright/dark edges.
6. No humans, lettering, logos, or unrelated props.
7. Looks like commercial still-life photography, not fantasy CGI sculpture.

## Preparation and manual image-generation plan

**Not executed in this milestone.** After separately approved merge:

1. Prepare baseline c0/l0/4:5 under D: private root (`AIPF_Creative_Private`).
2. Verify compiler and adapter-effective prompt digests.
3. Owner-operated ChatGPT Images generation (one image).
4. Preserve original PNG; verified manual-import provenance.
5. Visual assessment against acceptance criteria.
6. Private gallery candidate + index card only if accepted (separate gate).

## Validation commands

```bash
aipf recipe validate recipes/cr-003-refraction-ledger/1.0.0.json
aipf recipe compile recipes/cr-003-refraction-ledger/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Out of scope

Image generation, CR-001/CR-002 edits, private custody/gallery evidence changes,
D: migration archive edits, public gallery / Pages, EXP-019 / ESR / AIQ / G4/G5,
compiler or pack-family expansion, CI / branch-protection changes.
