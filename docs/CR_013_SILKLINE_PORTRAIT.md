# CR-013 Silkline Portrait

Creative Research recipe: **source-conditioned** art-style transformation from the
verified CR-001 fashion photograph into a contemporary gongbi-inspired meticulous
Chinese figure painting on an album-leaf support. PromptRecipe library only in
this delivery—no image generation, custody import, or gallery index changes.

**Status: RECIPE IMPLEMENTED — GENERATION PENDING**

**No CR-013 output has yet been generated.**

| Field | Value |
| --- | --- |
| Path | `recipes/cr-013-silkline-portrait/1.0.0.json` |
| `recipe_id` | `cr-013-silkline-portrait` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `art_style_transform` |
| TransformationPack | none |
| ArtMethodPack | `gongbi_painting` |
| Artifact form / state | `album_leaf` / `newly_created` |
| EraPacks | none |
| Selected concepts | none (painting ArtMethod has no `concept_refs`) |
| Variables | none (single embedded baseline) |

## Creative objective

Preserve recognizable continuity of the CR-001 adult subject’s facial structure
and expression, standing stance, key anatomical proportions, architectural gown
silhouette (including original neckline and draped construction), hairstyle
silhouette, and full-figure fashion hierarchy. Transform the photographic
representation into precise controlled fine brush contours, deliberate line
hierarchy, patient layered pigment, subtle tonal transitions, carefully
articulated folds, and a credible smooth prepared painting support.

The modern gown must remain modern. Outfit preservation means recognizable
garment construction and silhouette, **not** photographic satin reflectance.
Identity preservation does **not** require photographic skin rendering.

The result must be unmistakably different from a photograph with a digital
painting-texture filter and meaningfully distinct from CR-012 Keyblock Echo
(relief-print / woodblock grammar).

## Source selection

| Field | Value |
| --- | --- |
| Source | Verified CR-001 private original, resolved through local private candidate/import evidence during operator handoff |
| SHA-256 | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| Observed dimensions | 1122 × 1402 |
| Symbolic reference id | `cr001-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `outfit`, `hairstyle` |

CR-001 is reused intentionally so Silkline Portrait can be compared with CR-012
Keyblock Echo as a second art-method transform of the same canonical portrait.
The source PNG is **not** copied into Git. Absolute local paths stay outside the
repository. Recipe notes record the SHA and portable handoff language only.
Do not attach or condition on the generated CR-012 image.

## Why `art_style_transform` without a TransformationPack

- Route `art_style_transform` is the installed pictorial/craft-method path that
  does not require an era and does not require a physical-artifact TransformationPack.
- Installed TransformationPacks (`portrait_to_relief_print`, mural, sculpture,
  decorated artifact) are semantically unrelated to meticulous figure painting;
  forcing one would fail family gates or misrepresent the objective.
- `gongbi_painting` declares family `painting` and has **no** `concept_refs`.
  The V3.4 lexical path used under TransformationPack therefore cannot realize
  gongbi process concepts, and inventing concept IDs is out of scope.
- Without a TransformationPack, the compiler emits ArtMethod `prompt_fragments.core`,
  surface behavior, edge behavior, and the first three pack failure checks on the
  ordinary `3.2.0` path. That is the intended realization for this recipe.

## Installed gongbi ArtMethod behavior

Expected emitted method guidance includes:

- Precise fine contour drawing and patient layered color
- Controlled garment folds, hair ornaments, and facial planes
- Crisp but organic brush edges on silk/paper
- Smooth prepared silk/paper field with brush-built color (not photographic gloss)
- Deliberate controlled edges that separate forms more clearly than spontaneous
  ink-wash traditions

Compatible artifact forms declared by the pack include `album_leaf`. Silk support
is expressed through pack surface language and method variant wording; there is
no separate installed “silk” artifact-form enum.

## Body-mode rationale

Identity `recognizable_identity`; body `artistic_stylization` so medium
translation into painted figure grammar is allowed while pose and key proportions
remain locked in request/director fields. Body mode `preserve` would inject
anatomy-only-change prose that conflicts with photographic-to-painting translation
(same lesson as CR-012).

## Historical-authenticity boundaries

- Empty EraPack list: technique language must not imply a dated dynasty workshop
  production or named historical artist attribution.
- Contemporary digital gongbi-**inspired** interpretation only.
- Do not present the image as a handmade original or museum-authenticated
  historical painting.
- Do not invent historical Chinese costume for a modern fashion source.

## Anti-failure requirements

Require explicit exclusion of:

- Woodblock / relief-print appearance, keyblock carving, separated printing-block
  registration, and baren-impression simulation
- Loose expressive ink-wash painting
- Generic anime or cartoon depiction
- Uniform vector line art
- Watercolor or oil-paint substitution
- Photographic texture-overlay effects
- Historical costume replacement
- Fabricated historical attribution or unsupported handmade-production claims

Negative contrast wording such as “not a woodblock print” is acceptable.
Positive woodblock process instructions are not.

## Known compiler limitations

- Only the first three of five `gongbi_painting.typical_generation_failures` are
  auto-emitted (`anime cel shading`, missing brush/line hierarchy, hyperreal skin
  pores). Ink-wash looseness and glitter drift must remain in request/director text.
- No `lexical_realization` or `transformation` sections are expected.
- Compiler version for this path is `3.2.0`.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `f0c8b40717a77942195827eb95b79ed6032d25149a4c843617aaee0659024f7f` |
| Baseline compiled prompt (4:5) | `87d0280dc48a3c3801df7fdc0b6ba8eef6d9d7752bcae8300dbc937aa213d3c6` |

## Baseline compiled prompt audit

- Route: `art_style_transform` with **no** TransformationPack.
- Reference discipline names `cr001-c0-l0-4x5-source` with
  identity/pose/outfit/hairstyle.
- Gongbi ArtMethod core fragment, surface/edge material behavior, `album_leaf`,
  and `newly_created` present.
- No `transformation` / `lexical_realization` sections; no dynasty historical banner.
- Material failure checks include anime / brush hierarchy / hyperreal pores.
- Aspect `4:5`. No StylePack / PromptPack. Empty `variables`.

## Planned visual acceptance criteria (later generation gate)

1. Recognizable source-to-result continuity (face, stance, gown silhouette/neckline, hair).
2. Meaningful photographic-to-gongbi painting transformation.
3. Credible fine-line contour hierarchy and layered pigment structure.
4. Appropriate prepared painting-support material language.
5. Modern fashion wardrobe retained (no historical costume substitution).
6. Absence of woodblock/relief-print, anime/cartoon, ink-wash, or photo-filter looks.
7. Anatomical and visual coherence.
8. Overall creative quality.

Historical authenticity is assessed separately and is **not** claimed here.
One generated candidate would be exploratory creative evidence only—not general
reliability validation.

## Manual ChatGPT Images feasibility

Feasible as an **owner-operated** later gate:

- Attach the verified CR-001 PNG and the exact compiled baseline prompt in one request.
- Do not attach CR-012 output.
- No private gallery promotion without a separate authorization gate.

## Preparation and generation status

| Item | Status |
| --- | --- |
| Recipe `1.0.0` | Implemented |
| Image generation | **Pending** (not authorized in this PR) |
| Private preparation bundle | Not created |
| Gallery candidate | Absent |
| Private gallery (`CR-GATE-017`) | Unchanged eleven-card baseline |
