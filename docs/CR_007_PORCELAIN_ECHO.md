# CR-007 Porcelain Echo — Portrait on Curved Ceramic

Creative Research recipe: **source-backed** V3.4 artifact transformation from the
verified CR-002 Song Corridor Editorial photograph into a contemporary
handcrafted porcelain art vessel decorated with recognizable figurative
underglaze painting. PromptRecipe library only in this delivery—no image
generation, custody import, or gallery index changes.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-007-porcelain-echo/1.0.0.json` |
| `recipe_id` | `cr-007-porcelain-echo` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |
| TransformationPack | `portrait_to_decorated_artifact` |
| ArtMethodPack | `blue_white_ceramic` |
| Artifact form / state | `vase` / `newly_created` |
| EraPacks | none |
| Selected concept | `ceramic.porcelain_body` |

## Creative brief

Preserve the CR-002 adult figure’s recognizable identity: general facial
structure and gaze orientation, restrained upswept hairstyle with floral
ornament, layered pale clothing / sleeve relationships, and distinctive
silhouette. Translate the living photograph into brush-painted cobalt underglaze
decoration physically integrated with one free-standing contemporary porcelain
vase, photographed three-quarter in a quiet gallery or product-photography
setting so curvature, rim, foot, and glaze speculars remain readable.

The target is **not** an authenticated Song-dynasty artifact, excavated
antiquity, flat portrait, framed painting, poster, carved-stone figure, wall
painting installation, living person beside/inside the vase, or rectangular
photo decal. Source Song-informed fashion cues may remain visually readable in
painted ceramic language; they do not authorize historical authenticity claims.

## Source selection

| Field | Value |
| --- | --- |
| Source | Verified CR-002 private original, resolved through local private candidate/import evidence during operator handoff |
| SHA-256 | `a457c47cd96633b18d69e218f3316edb9886ea58114b96f2b4c0d1dce18221e0` |
| Observed dimensions | 1122 × 1402 |
| Symbolic reference id | `cr002-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `outfit`, `hairstyle` |

The source PNG was verified byte-identical before recipe authoring against the
D:-native private import original referenced by the existing CR-002 private
candidate. It is **not** copied into Git. Machine-specific absolute paths stay
outside the repository. Recipe `references[].notes` record the SHA and portable
handoff language only; PromptRecipe does **not** package reference binaries
([PROMPT_RECIPE.md](PROMPT_RECIPE.md) boundaries).

Do not substitute non-byte-identical assessment attachments. The SHA identifies
bytes and does not prove ChatGPT upload.

## Research findings and cited sources

| Source | Type | Mechanism used |
| --- | --- | --- |
| AIPF `references/art-methods/blue_white_ceramic.json` | in-repo ArtMethodPack | Cobalt under transparent glaze; curvature wrap; failure modes (photo decal, paint above glaze, flat poster vase) |
| AIPF `portrait_to_decorated_artifact` pack | in-repo TransformationPack | Portrait → decorated artifact delta; object-zone recomposition; forbid flat decal |
| AIPF `references/artifacts/forms.json` (`vase`) | in-repo ArtifactPack | Rotational body; motif scale across neck/shoulder/belly; vessel-zone + curvature concepts |
| V&A — Chinese blue-and-white ceramics article (ArtMethodPack source) | museum | Cobalt pigment on pale body under transparent glaze; brush application |
| RISD Museum — *On the Surface: Contemporary Ceramics* | museum guide | Distinguishes contemporary painting/slip/glaze decoration from decal transfer; form and surface conceived together |
| Museum of Oriental Ceramics, Osaka — ceramics guidance | museum | Viewing ceramic objects as three-dimensional craft with surface and form interdependence (contextual research; fetch intermittently unavailable) |
| Smithsonian NMAH — Haviland & Co. Mammoth Vase | museum collection | Large painted porcelain vessel as freestanding decorated object (form/photography context; not compositional copy) |
| National Museum of Korea — underglaze / slip ceramic techniques | museum | Historical underglaze and slip painting as craft processes distinct from later authentication theater |
| Mikawachi / underglaze-blue craft literature (gosu brush painting) | craft documentation | Underglaze cobalt on absorbent bisque; painterly shading vs pattern reduction on curved ware |

**Interpretation for CR-007 (not historical attribution):** Prefer contemporary
studio porcelain with cobalt underglaze figurative decoration and thin clear
glaze. Do not invent Song excavation provenance or Ming Jingdezhen court copy
claims. Do not copy distinctive third-party compositions (e.g. Mammoth Vase
narrative panels). Underglaze (pigment under glaze, high-fire integrated) is the
installed method path; overglaze enamel is **not** selected because no separate
overglaze ArtMethodPack is installed and `blue_white_ceramic` encodes underglaze
logic.

**Material compatibility note:** Early creative preference for muted sage pigment
is **not** used. Installed `blue_white_ceramic` restricts color behavior to
cobalt blue / reserved white. The recipe uses cobalt indigo on pale ivory
porcelain body only.

## Transformation architecture

- Route `artifact_transform` (not `new_generation`).
- Pack `portrait_to_decorated_artifact` → target representation `decorated_artifact`.
- Method family `ceramic_decoration` is the accepted family for that target
  (`transformation_art_gate`).
- Form `vase` is declared compatible by `blue_white_ceramic`.
- State `newly_created` for a fresh contemporary studio vessel (clean finish; no
  fake archaeological damage).
- Explicit `selected_concepts`: `ceramic.porcelain_body` (conditional method
  concept; pale porcelain ground).
- Empty EraPack list: ceramic material must not imply Song authenticity or Ming
  court reconstruction.
- Identity `recognizable_identity`; body `artistic_stylization` with pose
  recomposition allowed for curved-surface layout.
- Reference roles preserve figure/wardrobe/hairstyle while omitting `environment`
  so the corridor set does not become the photographic set.
- Camera-only v1.1 variables (1 baseline + 1 elevated variant); aspect fixed at
  `4:5`.

## Exact supported pack/method/form choices

Validated against installed registries/gates (no new packs or schema changes):

| Component | Exact ID |
| --- | --- |
| TransformationPack | `portrait_to_decorated_artifact` |
| Source / target representation | `portrait` → `decorated_artifact` |
| ArtMethodPack | `blue_white_ceramic` |
| Artifact form | `vase` |
| Artifact state | `newly_created` |
| EraPacks | `[]` |
| Selected concepts | `ceramic.porcelain_body` |

Identifiers **not** invented: no `porcelain_underglaze` ArtMethodPack; no
`ceramic_vessel` form. Closest installed combination is above.

## Physical ceramic constraints

- One free-standing rotational vase with believable rim opening and foot.
- Pale ivory porcelain body; cobalt underglaze fused beneath thin transparent glaze.
- Reserved white ground between brush motifs.
- Glaze specular highlights sit above painted pigment (materials differentiated).
- Decoration wraps neck/shoulder/belly with foreshortening; no floating vinyl
  stickers or rectangular photo paste-ups.
- Soft directional studio/gallery light defining volume without plastic hotspots.
- Avoid dynasty marks, maker inscriptions, branding, and archaeological dirt theater.

## Curved-surface decoration logic

Source portrait governs painted subject identity. Target artifact specification
governs vessel form, material, finish, and photographic setting. Motif hierarchy
follows object zones; scale may change across belly vs neck. Exact photographic
pose may be recomposed when required for coherent wrap—recognizability of face,
hair, layered clothing, and silhouette remains mandatory.

## Preservation versus stylization

| Preserve | Allow |
| --- | --- |
| Facial structure / gaze orientation | Contour simplification |
| Upswept hair + floral ornament | Reduced tonal complexity |
| Layered pale clothing / sleeve relationships | Curved-field recomposition |
| Distinctive silhouette | Painterly cobalt stylization |
| Source as painted subject authority | Selective ornamental framing |

## Source-reference submission requirements

Compile/prepare produce **text prompts only**. A filesystem path in notes or
docs is **not** evidence that the model received the image.

| Channel | How the source reaches the model | Provenance today |
| --- | --- | --- |
| ChatGPT Images (manual) | Owner must upload the verified CR-002 PNG as the image input alongside `prompt.txt` | **Operator-attested / uncaptured** unless a future gate records attachment hashes |
| OpenAI Images API (`generate_api.py --image`) | Supported edit-mode reference path exists in tooling | Out of scope for this milestone; not executed |

## Baseline compiled prompt audit

1. Source-reference discipline names `cr002-c0-l0-4x5-source` with
   identity/pose/outfit/hairstyle only.
2. Representation change is portrait → `decorated_artifact`.
3. Exact supported method/form/state: `blue_white_ceramic` / `vase` /
   `newly_created`.
4. Portrait becomes painted underglaze decoration, not a living subject.
5. Source hairstyle and garment structure remain locked and directed.
6. Decoration follows vessel curvature / vessel zones.
7. Vessel volume, rim, and foot are physically specified.
8. Pigment and glaze are materially differentiated.
9. Lighting is soft directional ceramic product photography.
10. No historical authenticity claims; Song authenticity explicitly negated;
    Ming court copy explicitly rejected in method variant.
11. No marble / mural / fragrance-campaign instruction leakage in compiled
    baseline.
12. No host-absolute private paths in tracked recipe or this document.

Negative semantic audit: removing `transformation` and forcing `new_generation`
drops the transformation section, removes `decorated_artifact`, and changes
`prompt_sha256`.

Deterministic compile ≠ demonstrated visual success.

## Failure modes

- Source figure no longer recognizable
- Rectangular photo pasted onto ceramic / vinyl above glaze
- Living figure standing beside or inside the vase
- Wall painting installation instead of object decoration
- Flat canvas or tile when a vessel was required
- Decoration ignoring curvature / perspective
- Painted details floating above the surface
- Impossible rim, foot, or body geometry
- Glaze highlights and pigment treated as identical materials
- Authenticated Song / excavated antiquity presentation
- Unwanted text, maker marks, branding, or dynasty seals
- Close compositional copy of a third-party ceramic artwork

A beautiful ceramic vessel without source fidelity fails this recipe.

## Acceptance criteria (later generation gate)

1. Result reads as one finished free-standing decorated porcelain vase.
2. Source identity / hairstyle / wardrobe silhouette remain recognizable in paint.
3. Decoration wraps curvature; rim, foot, and base contact are plausible.
4. Underglaze pigment and glaze speculars remain distinct.
5. No Song authenticity theater, extra people, logos, or marks.
6. Operator can show the verified CR-002 PNG was the image input used with the
   exact prepared CR-007 adapter-effective prompt in the **same** request.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `6af6a0756b344d45a4281e882280f593bd3ffed09b54d9be7b0f86ceb14c3b42` |
| Baseline compiled prompt (c0 / 4:5) | `ae067b7b1d6c1b1877cdd1b4f9d39d5ab0e6bc861611178b0c47b68fca4138eb` |

## Manual ChatGPT Images attachment requirements

Feasible as an **owner-operated** later gate (not authorized here):

1. Prepare recipe baseline under the private creative root (separate authorization).
2. Upload verified CR-002 PNG (`a457c47c…21e0`) as the image input.
3. Paste adapter-effective `prompt.txt` in the **same** request.
4. Attest attachment + prompt submission; import output with existing manual tools.

The prompt alone does not supply image pixels.

## Provenance limitations

- Single photograph cannot prove exact curved-surface transfer geometry.
- Models often leave photo-decal composites, living skin patches, impossible
  vessel openings, or identical pigment/glaze materials.
- ChatGPT Web attachment is not currently hash-captured by prepare/verify.
- Installed `blue_white_ceramic` lexicon is cobalt/white; multi-pigment
  (sage/indigo dual palette) would require a new ArtMethodPack—not authorized.
- Deterministic compile ≠ successful generation.
- No private gallery seventh card, no public publication, no EXP-019/ESR/AIQ claim.

## Validation commands

```bash
aipf recipe validate recipes/cr-007-porcelain-echo/1.0.0.json
aipf recipe compile recipes/cr-007-porcelain-echo/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Out of scope

Image generation, CR-001–CR-006 edits, private gallery index changes, compiler or
pack expansion, EXP-019 / ESR / AIQ / G4/G5 claims, merge without owner approval.
