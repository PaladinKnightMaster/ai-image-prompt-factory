# CR-012 Keyblock Echo

Creative Research recipe: **source-backed** V3.4 artifact transformation from the
verified CR-001 fashion photograph into a contemporary Japanese
woodblock-inspired relief print on a physical print sheet. PromptRecipe library
only in this delivery—no image generation, custody import, or gallery index
changes.

**No CR-012 output has yet been generated.**

| Field | Value |
| --- | --- |
| Path | `recipes/cr-012-keyblock-echo/1.0.0.json` |
| `recipe_id` | `cr-012-keyblock-echo` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |
| TransformationPack | `portrait_to_relief_print` |
| ArtMethodPack | `japanese_woodblock_print` |
| Artifact form / state | `print_sheet` / `newly_created` |
| EraPacks | none |
| Selected concepts | none (core woodblock concepts auto-resolved) |

## Creative objective

Preserve recognizable continuity of the CR-001 adult subject’s facial structure,
standing stance, key anatomical proportions, architectural gown silhouette /
construction, hairstyle silhouette, and broad subject hierarchy. Transform the
photographic representation into carved-keyblock-inspired contours, deliberately
separated ink-color regions, controlled planar value, credible multi-block color
relationships, absorbent paper character, and restrained registration /
impression cues on a sheet-conscious composition.

The result must be unmistakably different from a photograph with a digital
texture filter. Outfit preservation means recognizable garment construction and
silhouette, **not** photographic satin reflectance or pixel-level dress texture.
Identity preservation does **not** require photographic skin rendering.

## Source selection

| Field | Value |
| --- | --- |
| Source | Verified CR-001 private original, resolved through local private candidate/import evidence during operator handoff |
| SHA-256 | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| Observed dimensions | 1122 × 1402 |
| Symbolic reference id | `cr001-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `outfit`, `hairstyle` |

CR-001 is reused intentionally so Keyblock Echo can be compared with CR-004
Marble Afterimage as a second medium transform of the same canonical portrait.
The source PNG is **not** copied into Git. Absolute local paths stay outside the
repository. Recipe notes record the SHA and portable handoff language only.

## Transformation architecture

- Route `artifact_transform` (not `new_generation`).
- Pack `portrait_to_relief_print` → target representation `relief_print`.
- Method family `printmaking` is the accepted family for that target
  (`transformation_art_gate`).
- Form `print_sheet` is declared compatible by `japanese_woodblock_print`.
- State `newly_created` for a fresh contemporary print sheet (no forced antique
  damage).
- Empty EraPack list: woodblock process language must not imply authenticated
  Edo-period production or named historical printmaker attribution.
- Identity `recognizable_identity`; body `artistic_stylization` so medium
  translation into planar print grammar is allowed while pose and key proportions
  remain locked in request/director fields. (`preserve` body mode would inject
  contradictory anatomy-only-change prose against the relief-print delta.)
- Camera-only v1.1 variables (3 sheet framings); aspect fixed at `4:5`.
- `woodblock.bokashi` is **not** selected in `1.0.0` so the first experiment
  prioritizes readable keyblock contours and layered color blocks.

## Woodblock process terminology and lexical expectations

Installed ArtMethod core `concept_refs` resolve through the V3.4 lexical path
under transformation (no free-form duplicate process essay):

| Concept ID | Role in compiled prompt |
| --- | --- |
| `method.japanese_woodblock_print` | Relief-printed contour + separate color impressions |
| `woodblock.keyblock` | Principal carved contour block |
| `woodblock.color_block` | Separate color-area block |
| `woodblock.kento_registration` | Alignment notches across impressions |
| `woodblock.baren_printing` | Hand pressure transfer |
| `woodblock.kozo_paper` | Absorbent paper-mulberry support |

The TransformationPack supplies the portrait → relief_print representation
delta (contour/bounded color regions; impressed sheet, not screen+texture).

## Intended preserved vs changed properties

**Preserve (from source reference):** adult identity recognizability; standing
stance; key anatomical proportions; gown architectural silhouette/construction;
hairstyle silhouette; single figure; adult subject.

**Change:** photographic skin/satin/continuous modeling → keyblock contour +
separated ink-color regions + planar print value; living studio cyclorama →
sheet margins / paper negative space; medium is a print sheet, not a living
photograph with paper overlay.

## Failure modes / creative exclusions

- Generic anime or cartoon-filter aesthetics
- Vector illustration without print material cues
- Photograph merely overlaid with paper texture
- Photorealistic continuous shading
- Ink-wash painting or watercolor substitution
- Digital brush-stroke simulation instead of relief-print structure
- Unrecognizable subject replacement; loss of gown architecture; major pose change
- Anatomical errors; logos / invented typography
- Fabricated historical printmaker attribution
- Claims of authenticated Edo-period production or genuine handmade artifact status

This is an AI-generated, woodblock-**inspired** interpretation.

## Predeclared visual assessment (later generation gate)

1. Recognizable source-to-result continuity (face, stance, gown silhouette, hair).
2. Meaningful photographic-to-relief-print transformation.
3. Credible keyblock line and separated color-block structure.
4. Appropriate paper/ink/impression material language.
5. Intentional sheet composition and silhouette.
6. Absence of generic cartoon/anime substitution.
7. Anatomical and visual coherence.
8. Overall creative quality.

Historical authenticity is assessed separately and is **not** claimed here.
One generated candidate would be exploratory creative evidence only—not general
reliability validation.

## Historical / process authenticity limitations

- No EraPack is selected; no Edo banner appears in the compiled prompt.
- Process vocabulary comes from installed woodblock lexical concepts, not from
  claiming a dated workshop output.
- Do not present the image as a genuine handmade print or museum-authenticated
  historical artifact.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `580a9dbef44fb4b6b9d174611148bf2233505aa8657445a08314cf955ea85ec6` |
| Baseline compiled prompt (c0 / 4:5) | `940f156c45b14443026aefd401b91e7cf8133954c538a86504d58eb3bcecfb58` |

## Baseline compiled prompt audit

- Route/transform: `artifact_transform` with portrait → relief_print.
- Reference discipline names `cr001-c0-l0-4x5-source` with
  identity/pose/outfit/hairstyle.
- Woodblock ArtMethod lexicalization of all six core concepts present.
- `print_sheet` + `newly_created` present; no `edo period` historical banner.
- Material failure checks include anime / vector / photoreal avoidances.
- Aspect `4:5`. No StylePack / PromptPack. No bokashi selection in v1.0.0.

## Manual ChatGPT Images feasibility

Feasible as an **owner-operated** later gate:

1. Prepare recipe baseline under the private root (separate authorization).
2. Upload verified CR-001 PNG (`0dcf8af6…f41e`) as the image input.
3. Paste adapter-effective `prompt.txt`.
4. Attest attachment + prompt submission; import output with existing manual tools.

Not authorized in this milestone. No private preparation or generation is
started by this PR.

## Validation commands

```bash
aipf recipe validate recipes/cr-012-keyblock-echo/1.0.0.json
aipf recipe compile recipes/cr-012-keyblock-echo/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Out of scope

Image generation, private gallery index changes, pack/lexicon/schema/compiler
edits, CR-008 reopening, EXP-019 / ESR / AIQ claims, merge without owner approval.
