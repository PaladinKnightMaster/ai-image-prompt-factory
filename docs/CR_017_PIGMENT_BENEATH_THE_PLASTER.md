# CR-017 Pigment Beneath the Plaster

Creative Research recipe: original Tang-informed **secular mineral-pigment mural**
as the principal image on prepared plaster. PromptRecipe library draft—
no image generation, custody import, adapter freeze, or gallery index changes
in this delivery.

**Status: RECIPE DRAFT VALIDATED — GENERATION / PROMPT-FREEZE PENDING OWNER REVIEW**

**No CR-017 output has yet been generated.**

| Field | Value |
| --- | --- |
| Path | `recipes/cr-017-pigment-beneath-plaster/1.0.0.json` |
| `recipe_id` | `cr-017-pigment-beneath-plaster` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `new_generation` |
| TransformationPack | none |
| EraPack | `tang` |
| Site tradition | none |
| ArtMethodPack | `mineral_pigment_mural` |
| Artifact form / state | `wall_surface` / `newly_created` |
| Presentation | mural as principal image (4:5) |
| Historical strictness | `historically_informed` |
| References | none |
| Variables | none (single embedded baseline) |
| Raw recipe SHA-256 | `7b7f1a8ec969206519cedb8186d34224759bc1f15c0825d142acb173cf5031a0` |
| Canonical recipe SHA-256 | `820b3b7a008a2c5312af61c67d9c0c09e552db62c04ced80373e40f41c497d69` |
| Semantic-spec SHA-256 | `222b0aae775310839df1473e96fca489e966d627974a0f6ae0936b4f5128b7e1` |
| Baseline compiled prompt SHA-256 | `5bd1c2bfd865fb3040f07ce6e4e92d722e123759ada6a7f7ea82e419dd8bd85d` |
| Compiled UTF-8 bytes | `7049` |
| Compiler version (offline) | `3.2.0` |

## Creative objective

Demonstrate a reference-free, Tang-informed secular wall painting with three
restrained adult attendants in a planar procession, limited painted timber
architectural motifs, matte mineral pigment on prepared plaster, and a small
deliberate unfinished workshop margin revealing ground and plaster without
fake archaeological aging.

This recipe is intentionally **not** a transform of CR-001 and is distinct from:

- CR-005 Silk on Plaster (source-conditioned contemporary fashion mural)
- CR-011 Era Reframing (Tang living photographic wardrobe transfer)
- CR-016 Ferry Across Unpainted Water (Song ink landscape on silk scroll)

## Research grounding

Authoring follows the owner-authorized concept specification and private formal
recipe draft gates (`AIPF-CR-NEXT-MURAL-CONCEPT-SPEC-01`,
`AIPF-CR-NEXT-MURAL-RECIPE-AUTHOR-01`). Public/institutional anchors include
Getty Mogao wall-painting conservation science for plaster/ground/pigment
**technique analogy**, and Tang tomb attendant mural evidence (for example
Shaanxi History Museum Palace Maids) for a secular attendant **subject-family
analogy**. Installed AIPF sources: `references/eras/tang.json`,
`references/art-methods/mineral_pigment_mural.json`, ISV-01 Tang/mural offline
compatibility (compiler evidence only; not visual proof).

Creative inventions: exact three-figure procession and workshop-margin
composition. Non-claims: no named artist, seals, calligraphy, collector marks,
or documentary reconstruction of a surviving Chang’an palace mural. Digital
generation is not authenticated handmade production. Cave-site sacred programs
are excluded; Dunhuang is not used as an EraPack.

## Why this pack architecture

- `new_generation` — original mural; no identity reference required
- `tang` + `historically_informed` — Tang-informed secular attendant guidance
- `mineral_pigment_mural` + `wall_surface` + `newly_created` — installed compatibility
- No TransformationPack — method emits on standard compiler `3.2.0`
- No site-tradition pack — avoids sacred cave-temple priming
- Aspect `4:5` — gallery-consistent portrait field for wall-bound mural study

## Residual compiler notes (non-blocking for library integration)

Standard non-transform compilation still emits ArtMethod core / material-behavior
language that mentions localized loss, aging, cracks, and abrasions. Recipe
request, variant, and director assert `newly_created` precedence and intact
pigment except the intentional unfinished workshop margin.

Recorded classification:

`UNRESOLVED_PACK_LEAKAGE — REQUEST-LEVEL MITIGATION PRESENT`

This is a documented recipe-level limitation. Deterministic offline compilation
is **not** proof of image fidelity. Generation remains separately unauthorized.

## Planned visual acceptance criteria (later generation gate)

1. Tang-informed secular mural grammar (not generic fantasy)  
2. Plausible earthen plaster / prepared-ground appearance  
3. Matte mineral pigment with credible granularity  
4. Distinct painted outlines and color boundaries  
5. Wall-integrated planar composition  
6. Three attendants subordinate to mural program  
7. Newly created finish (no excavated aging theater)  
8. Mural as principal image (not museum install photo)  
9. No false text, seals, sacred cave program, or provenance claims  
10. Clear differentiation from CR-005, CR-011, and CR-016  

Disqualifying failures include living people in front of a wall, fashion-portrait
dominance, sacred deity programs, uniform cracked-plaster / digital fresco
filters, large fake losses, framed canvas/poster reading, and invented
inscriptions.

Owner KEEP is not automatic and is not authorized by this documentation alone.

## Manual ChatGPT Images feasibility

Feasible as an **owner-operated** later gate after recipe review and **separate
authorization**. Image generation is **not** authorized by this documentation
alone. When authorized later: prepare via
`scripts/creative_recipe_generation.py prepare`, submit adapter-effective
`prompt.txt` (not `compiler_prompt.txt`), preserve original-byte custody, then
evaluate against the criteria above. Offline compile digests above are
**compiler evidence** only—not a frozen gallery-generation adapter prompt.

## Non-claims

- Does not reopen CR-008  
- Does not modify APCC / EXP-019 / AIQ  
- Does not promote a private or public gallery card  
- Does not prove provider visual fidelity from offline compilation  
- Does not claim authenticated Tang palace mural reconstruction  
