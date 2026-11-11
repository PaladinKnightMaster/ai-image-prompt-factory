# CR-015 Cut-Space Portrait

Creative Research recipe: **source-conditioned** art-style transformation from the
verified CR-001 fashion photograph into a contemporary layered-paper pop-up
diorama. PromptRecipe library only in this delivery—no image generation, custody
import, or gallery index changes.

**Status: RECIPE IMPLEMENTED — GENERATION PENDING**

**No CR-015 output has yet been generated.**

| Field | Value |
| --- | --- |
| Path | `recipes/cr-015-cut-space-portrait/1.0.0.json` |
| `recipe_id` | `cr-015-cut-space-portrait` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `art_style_transform` |
| TransformationPack | none |
| ArtMethodPack | `paper_cut_layered` |
| Artifact form / state | `popup_diorama` / `newly_created` |
| EraPacks | none |
| Selected concepts | none (paper ArtMethod has no `concept_refs`) |
| Variables | none (single embedded baseline) |

## Creative objective

Preserve recognizable continuity of the CR-001 adult subject’s facial structure
and broad expression, standing stance, key anatomical proportions, overall gown
silhouette (including draped neckline and major gathered-fabric architecture),
hairstyle silhouette, and full-figure fashion hierarchy. Transform the
photographic representation into discrete supportable cut-paper components with
believable cuts, bridges/tabs/hinges or glued joins, foreground/midground/background
layer spacing, construction-generated cast shadows, and intentional cut negative
space.

The experimental variable is **visual construction logic**, not merely paper
texture or illustration style. The modern gown must remain modern. Outfit
preservation means recognizable garment architecture and silhouette, **not**
exhaustive seam tracing or photographic satin reflectance. Identity preservation
does **not** require photographic skin rendering.

The result must be unmistakably different from a photograph with a digital paper
texture filter, from CR-012 Keyblock Echo (relief-print / woodblock grammar),
from CR-013 Silkline Portrait (gongbi fine-line meticulous painting), and from
CR-014 Inkflow Figure (expressive ink brushwork).

## Research novelty versus prior CR methods

| Experiment | Primary mechanism |
| --- | --- |
| CR-012 | Relief-print color and contour construction |
| CR-013 | Gongbi fine-line pigment representation |
| CR-014 | Expressive ink brushwork and abstraction |
| CR-015 | Physical paper-cut topology and layered depth |

CR-004/005/007 tested stone volume, mural pigment, and ceramic decoration. None
previously exercised discrete supportable paper components with construction-caused
shadows and structural negative space.

## Source selection

| Field | Value |
| --- | --- |
| Source | Verified CR-001 private original, resolved through local private candidate/import evidence during operator handoff |
| SHA-256 | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| Observed dimensions | 1122 × 1402 |
| Symbolic reference id | `cr001-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `outfit`, `hairstyle` |

CR-001 is reused intentionally so Cut-Space Portrait can be compared with
CR-012/013/014 as another art-method transform of the same canonical portrait.
The source PNG is **not** copied into Git. Absolute local paths stay outside the
repository. Recipe notes record the SHA and portable handoff language only.
Do not attach or condition on generated CR-012, CR-013, or CR-014 images.

## Hierarchical preservation contract

**Structural continuity — required**

- Recognizable adult facial identity and broad expression
- Original standing stance and key adult proportions
- Overall gown silhouette, draped neckline, major gathered-fabric architecture
- Hairstyle silhouette and full-figure composition

**Representational flexibility — permitted**

- Facial features as simplified supported paper shapes
- Hair as joined geometric masses or layered cutouts
- Abbreviated or omitted minor seams, repetitive tiny folds, and microdetail
- Paper-stock color relationships replacing photographic satin highlights
- Overlapping paper planes representing drapery hierarchy
- Purposeful cut-out omissions instead of tracing every source detail

## Why `popup_diorama`

Installed `paper_cut_layered` is compatible with `book_page`, `popup_diorama`,
`folding_screen`, and `album_leaf`. `popup_diorama` was selected because its form
geometry explicitly encodes layered cut/fold elements, hinges/tabs, and visible
cast shadows, and because pack composition guidance ties foreground/midground/background
physical spacing to pop-up/diorama mode. A flat `album_leaf` framing would risk
collapsing into illustrative paper texture without testing construction logic.

## Why `art_style_transform` without a TransformationPack

- Route `art_style_transform` is the installed pictorial/craft-method path that
  does not require an era and does not require a physical-artifact TransformationPack.
- Installed TransformationPacks (`portrait_to_relief_print`, mural, sculpture,
  decorated artifact) are semantically unrelated to layered paper construction;
  forcing one would fail family gates or misrepresent the objective.
- `paper_cut_layered` declares family `paper_craft` and has **no** `concept_refs`.
  The V3.4 lexical path used under TransformationPack therefore cannot realize
  paper process concepts, and inventing concept IDs is out of scope.
- Without a TransformationPack, the compiler emits ArtMethod `prompt_fragments.core`,
  surface behavior, edge behavior, and the first three pack failure checks on the
  ordinary `3.2.0` path. That is the intended realization for this recipe.

## Why empty EraPacks

Empty EraPack list keeps technique language free of a dated craft-tradition
banner, named historical artist attribution, or authentic handmade-manufacture
claim. `historically_informed` strictness remains only as the installed semantic
contract default for non-strict creative transforms; with no packs loaded, no
era anchors or historical integrity banner are emitted.

## Body-mode rationale

Identity `recognizable_identity`; body `artistic_stylization` so medium
translation into paper-construction grammar is allowed while pose and key
proportions remain locked in request/director fields. Body mode `preserve` would
inject anatomy-only-change prose that conflicts with photographic-to-paper
translation (same lesson as CR-012 / CR-013 / CR-014).

## Supportable paper topology

Expected construction behaviors include:

- Crisp cut silhouettes with consistent paper thickness and subtle edge fibers
- Discrete paper shapes assembled by bridges, tabs, folded supports, hinges, or
  glued/pasted overlaps
- Mechanically intelligible attachment even when every glue joint is not exposed
- Explicit ban on unsupported floating paper islands
- Face and hair as supported paper shapes / joined masses, not photographic
  skin shading or free-floating strands
- Gown neckline and gathered architecture as overlapping paper planes with
  physically meaningful waist/hip overlap

## Layer depth, shadows, and negative space

Because several pack fields do **not** auto-emit on this route, the recipe places
operational instructions in `request` and `director`:

- Foreground paper elements, middle-layer figure/garment forms, background
  support planes with plausible spacing and coherent occlusion
- Cast shadows from directional light interacting with thickness, cut edges, and
  layer gaps—not uniform digital drop shadows and not smooth CGI volume shading
- Intentional cut negative space clarifying arm/torso separation, hair/neckline
  contours, gown silhouette, drapery openings, and overlapping masses
- Blank background alone is insufficient; negative cuts must remain compatible
  with connected or glued construction

## Material and color behavior

- Matte fibrous paper stocks and clean newly created edges
- Restrained paper-stock color relationships instead of photographic satin gloss
- Visible physical layer hierarchy and subtle fiber behavior
- No aged parchment, stains, or museum-excavation patina unless a different
  artifact state is later authorized

## Historical-authenticity and decoration boundaries

- No handmade provenance claim and no museum authentication
- No dynasty attribution and no named historical artist authorship
- Contemporary digital layered-paper-**inspired** simulation only
- Do not invent historical costume, inscriptions, emblems, or signatures
- Do not claim the generated image proves physically buildable craftsmanship

## Anti-failure requirements

Require explicit exclusion of:

- Printed photograph with paper-texture overlay
- Flat painted illustration masquerading as cut paper
- Photographic facial shading or recolored satin folds as the principal means
- Unsupported floating paper islands or unsupported hair strands
- Smooth plastic CGI / inflated volumetric objects
- Uniform fake digital drop shadows unrelated to layer spacing
- Marble or stone sculpture language
- Woodblock / relief-print appearance, keyblock carving, or baren impression
- Gongbi fine-line pigment painting
- Expressive ink-wash brushwork as the primary construction
- Western watercolor substitution
- Generic anime or cartoon line art
- Generic digital collage without coherent support topology

Negative contrast wording such as “not a woodblock print” or “not gongbi” is
acceptable. Positive woodblock, gongbi, ink-wash, or sculpture process
instructions are not.

## Known compiler limitations

- Only the first three of five `paper_cut_layered.typical_generation_failures`
  are auto-emitted (`3D plastic toy look`, `smooth CGI surfaces`,
  `floating unsupported paper islands`). Printed-photo overlay and uniform fake
  drop shadows must remain in request/director text.
- Pack fields `composition_behavior`, `color_behavior`, `structural_limitations`,
  extended `mark_making`, `fabrication_process`, and `aging_weathering` are not
  auto-emitted on this non-transformation path; carry essentials in request/director.
- No `lexical_realization` or `transformation` sections are expected.
- Compiler version for this path is `3.2.0`.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `fe9a6a6a03520e40569df8e3a0c3c5703d31d869c83c02cbaff2331cb58f2e46` |
| Baseline compiled prompt (4:5) | `da5c59146a8bbb84846f52455952749c1dc1dffc65281b6bf7a64eed1b974142` |

## Baseline compiled prompt audit

- Route: `art_style_transform` with **no** TransformationPack.
- Reference discipline names `cr001-c0-l0-4x5-source` with
  identity/pose/outfit/hairstyle.
- Paper-cut ArtMethod core fragment, surface/edge material behavior,
  `popup_diorama`, and `newly_created` present.
- Request/director carry bridges/tabs/glued supports, F/M/B spacing,
  construction-caused shadows, structural negative space, selective omission,
  anti-photo-overlay, anti-CGI, anti-sculpture/woodblock/gongbi/ink-wash.
- No `transformation` / `lexical_realization` sections; no dynasty historical banner.
- Material failure checks include plastic / CGI / floating unsupported islands.
- Aspect `4:5`. No StylePack / PromptPack. Empty `variables`.

## Planned visual acceptance criteria (later generation gate)

1. Recognizable source identity.
2. Standing pose and gown continuity.
3. Hairstyle silhouette continuity.
4. Clear cut-paper contours and material thickness.
5. Plausible bridges, tabs, or joined layers.
6. Coherent foreground/midground/background depth.
7. Shadows caused by believable paper-layer separation.
8. Intentional negative space and overall distinction from existing artistic methods.

A visually attractive result with floating disconnected elements should fail the
structural-method criterion, even if identity preservation is excellent. Physical
craftsmanship and buildability remain unverified visual interpretation.
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
   prepared `prompt.txt` text. Do not attach CR-012, CR-013, or CR-014 outputs.
6. Preserve a genuine pre-submit screenshot when available.
7. Perform one owner-operated generation only after separate authorization.
8. Preserve original-byte custody and private creative evaluation afterward.
9. Offline `input_references: []` (or similar local preview emptiness) does **not**
   prove provider-side attachment.

The Digests table baseline compiled prompt is **compiler evidence** only. It is
not the authoritative manual-submission artifact; submit adapter-effective
`prompt.txt` after prepare. Do **not** submit `compiler_prompt.txt`. No private
gallery promotion without a separate authorization gate.

## Preparation and generation status

| Item | Status |
| --- | --- |
| Recipe `1.0.0` | Implemented |
| Image generation | **Pending** (not authorized in this PR) |
| Private preparation bundle | Not created |
| Gallery candidate | Absent |
| Private gallery (`CR-GATE-017`) | Unchanged thirteen-card baseline |
