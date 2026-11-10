# CR-014 Inkflow Figure

Creative Research recipe: **source-conditioned** art-style transformation from the
verified CR-001 fashion photograph into a contemporary expressive Chinese ink
figure painting on an absorbent album-leaf support. PromptRecipe library only in
this delivery—no image generation, custody import, or gallery index changes.

**Status: RECIPE IMPLEMENTED — GENERATION PENDING**

**No CR-014 output has yet been generated.**

| Field | Value |
| --- | --- |
| Path | `recipes/cr-014-inkflow-figure/1.0.0.json` |
| `recipe_id` | `cr-014-inkflow-figure` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `art_style_transform` |
| TransformationPack | none |
| ArtMethodPack | `chinese_ink_painting` |
| Artifact form / state | `album_leaf` / `newly_created` |
| EraPacks | none |
| Selected concepts | none (painting ArtMethod has no `concept_refs`) |
| Variables | none (single embedded baseline) |

## Creative objective

Preserve recognizable continuity of the CR-001 adult subject’s facial structure
and broad expression, standing stance, key anatomical proportions, overall gown
silhouette (including draped neckline and major gathered-fabric architecture),
hairstyle silhouette, and full-figure fashion hierarchy. Transform the
photographic representation into variable calligraphic brushwork, wet/dry ink
contrast, tonal ink washes, selective omission of nonessential detail, and
intentional negative space on an absorbent painting support.

The modern gown must remain modern. Outfit preservation means recognizable
garment architecture and silhouette, **not** exhaustive seam tracing or
photographic satin reflectance. Identity preservation does **not** require
photographic skin rendering.

The result must be unmistakably different from a photograph with a digital
ink-texture filter, from CR-012 Keyblock Echo (relief-print / woodblock grammar),
and from CR-013 Silkline Portrait (gongbi fine-line meticulous painting).

## Source selection

| Field | Value |
| --- | --- |
| Source | Verified CR-001 private original, resolved through local private candidate/import evidence during operator handoff |
| SHA-256 | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| Observed dimensions | 1122 × 1402 |
| Symbolic reference id | `cr001-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `outfit`, `hairstyle` |

CR-001 is reused intentionally so Inkflow Figure can be compared with CR-012 and
CR-013 as a third art-method transform of the same canonical portrait.
The source PNG is **not** copied into Git. Absolute local paths stay outside the
repository. Recipe notes record the SHA and portable handoff language only.
Do not attach or condition on generated CR-012 or CR-013 images.

## Hierarchical preservation contract

**Structural continuity — required**

- Recognizable adult facial identity and broad expression
- Original standing stance and key adult proportions
- Overall gown silhouette, draped neckline, major gathered-fabric architecture
- Hairstyle silhouette and full-figure composition

**Representational flexibility — permitted**

- Abbreviated or omitted minor seams, pleats, and nonessential folds
- Ink-wash substitution for photographic satin highlights
- Nonphotographic skin modeling
- Reduced fine texture and purposeful unpainted support
- Freer expressive brush contours that still preserve major architecture

## Why `art_style_transform` without a TransformationPack

- Route `art_style_transform` is the installed pictorial/craft-method path that
  does not require an era and does not require a physical-artifact TransformationPack.
- Installed TransformationPacks (`portrait_to_relief_print`, mural, sculpture,
  decorated artifact) are semantically unrelated to expressive ink figure painting;
  forcing one would fail family gates or misrepresent the objective.
- `chinese_ink_painting` declares family `painting` and has **no** `concept_refs`.
  The V3.4 lexical path used under TransformationPack therefore cannot realize
  ink process concepts, and inventing concept IDs is out of scope.
- Without a TransformationPack, the compiler emits ArtMethod `prompt_fragments.core`,
  surface behavior, edge behavior, and the first three pack failure checks on the
  ordinary `3.2.0` path. That is the intended realization for this recipe.

## Why empty EraPacks

Empty EraPack list keeps technique language free of a dated dynasty workshop
banner, named historical artist attribution, or authentic traditional-manufacture
claim. `historically_informed` strictness remains only as the installed semantic
contract default for non-strict creative transforms; with no packs loaded, no
era anchors or historical integrity banner are emitted.

## Body-mode rationale

Identity `recognizable_identity`; body `artistic_stylization` so medium
translation into expressive ink-figure grammar is allowed while pose and key
proportions remain locked in request/director fields. Body mode `preserve` would
inject anatomy-only-change prose that conflicts with photographic-to-ink
translation (same lesson as CR-012 / CR-013).

## Installed Chinese-ink ArtMethod behavior

Expected emitted method guidance includes:

- Calligraphic brush line, controlled ink dilution, dry/wet stroke contrast
- Meaningful untouched paper/silk; brush rhythm describing form rather than
  tracing a photo under a filter
- Absorbent fibers/silk affecting stroke edges
- Edges that can be decisive calligraphic contours or dissolved wash edges

Compatible artifact forms declared by the pack include `album_leaf`.

## Wet/dry, density, negative space, and selective omission

Because several pack fields do **not** auto-emit on this route, the recipe places
operational instructions in `request` and `director`:

- Variable pressure, tapered strokes, directional brush rhythm
- Wet washes for broad masses vs dry-brush structural accents
- Ink-density hierarchy: untouched support → pale gray → intermediate → dark
  structural marks → selective concentrated black
- Negative space that participates in silhouette, body/gown separation, and
  overlapping masses (blank backdrop alone is insufficient)
- Selective omission of nonessential seams, minor folds, individual hair strands,
  and photographic microdetail without dropping major source-defining structures

## Historical-authenticity and decoration boundaries

- No dynasty authenticity claim and no named historical artist attribution
- Contemporary digital expressive-ink-**inspired** interpretation only
- Do not present the image as a handmade original or museum-authenticated
  historical painting
- Do not invent historical Chinese costume for a modern fashion source
- Calligraphic *brushwork* does **not** authorize written calligraphy text,
  red seals, signatures, or inscriptions

## Anti-failure requirements

Require explicit exclusion of:

- Gongbi fine-line meticulous contour-and-layered-color painting with uniform
  thin outlines and exhaustive fold tracing
- Woodblock / relief-print appearance, keyblock carving, separated printing-block
  registration, kentō marks, and baren-impression simulation
- Photograph with black watercolor or ink-texture overlay
- Uniform grayscale or sepia digital fashion illustration
- Western watercolor substitution
- Generic anime or cartoon depiction
- Uniform vector line art
- Random decorative black splatter without structural brush logic
- Photorealistic airbrushed facial gradients
- Historical costume replacement
- Fabricated historical attribution or unsupported handmade-production claims

Negative contrast wording such as “not a woodblock print” or “not gongbi” is
acceptable. Positive woodblock or gongbi process instructions are not.

## Known compiler limitations

- Only the first three of five `chinese_ink_painting.typical_generation_failures`
  are auto-emitted (`photograph with black watercolor overlay`, `uniform gray wash`,
  `airbrushed gradients`). Fake calligraphy and every-hair overdetail must remain
  in request/director text.
- Pack fields `composition_behavior`, `color_behavior`, `structural_limitations`,
  extended `mark_making`, `fabrication_process`, and `aging_weathering` are not
  auto-emitted on this non-transformation path; carry essentials in request/director.
- No `lexical_realization` or `transformation` sections are expected.
- Compiler version for this path is `3.2.0`.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `593e060e227ed3f89a7fd9c416ee86d93e587a050ede35af3c1d26bae4166ecd` |
| Baseline compiled prompt (4:5) | `8261cd7d2f411f3d8e835f2d54b36972170a08d5d782d4b93f990ff93584f6a4` |

## Baseline compiled prompt audit

- Route: `art_style_transform` with **no** TransformationPack.
- Reference discipline names `cr001-c0-l0-4x5-source` with
  identity/pose/outfit/hairstyle.
- Chinese ink ArtMethod core fragment, surface/edge material behavior,
  `album_leaf`, and `newly_created` present.
- Request/director carry wet/dry contrast, ink-density hierarchy, negative space,
  selective omission, anti-gongbi, anti-woodblock, anti-calligraphy/seals.
- No `transformation` / `lexical_realization` sections; no dynasty historical banner.
- Material failure checks include photo+watercolor overlay / uniform gray wash /
  airbrushed gradients.
- Aspect `4:5`. No StylePack / PromptPack. Empty `variables`.

## Planned visual acceptance criteria (later generation gate)

1. Identity recognition.
2. Standing pose and anatomy.
3. Gown silhouette and major drapery continuity (neckline + gathered architecture).
4. Hairstyle continuity.
5. Expressive calligraphic brushwork.
6. Credible wet/dry ink variation and wash gradation.
7. Purposeful negative space and support interaction.
8. Clear perceptual distinction from CR-013 gongbi and CR-012 woodblock methods.

An attractive illustration that fails criteria 5–7 must not automatically count as
a successful ink-painting-method demonstration. Physical brush technique and
material authenticity remain unverified visual interpretation.
One generated candidate would be exploratory creative evidence only—not general
reliability validation.

## Manual ChatGPT Images feasibility

Feasible as an **owner-operated** later gate after recipe merge and **separate
authorization**. Image generation is **not** authorized by this documentation
alone.

Manual custody uses the offline prepare workflow, not the compiler baseline as
the submission artifact:

1. Run `python scripts/creative_recipe_generation.py prepare` for this recipe
   into private storage (separate authorization).
2. Verify the immutable preparation `receipt.json` and `manifest.json`.
3. Compute the actual SHA-256 of the adapter-effective `prompt.txt` produced by
   that prepare gate. Do **not** invent or pre-claim that digest here; it is
   unknown until preparation exists.
4. Re-verify the canonical CR-001 original PNG against
   `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e`.
5. In one ChatGPT Images request, attach that verified PNG and paste the exact
   prepared `prompt.txt` text. Do not attach CR-012 or CR-013 outputs.
6. Preserve a genuine pre-submit screenshot when available.
7. Offline `input_references: []` (or similar local preview emptiness) does **not**
   prove provider-side attachment.

The Digests table baseline compiled prompt is **compiler evidence** only. It is
not the authoritative manual-submission artifact; submit adapter-effective
`prompt.txt` after prepare. No private gallery promotion without a separate
authorization gate.

## Preparation and generation status

| Item | Status |
| --- | --- |
| Recipe `1.0.0` | Implemented |
| Image generation | **Pending** (not authorized in this PR) |
| Private preparation bundle | Not created |
| Gallery candidate | Absent |
| Private gallery (`CR-GATE-017`) | Unchanged twelve-card baseline |
