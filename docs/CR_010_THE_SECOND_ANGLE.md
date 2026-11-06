# CR-010 The Second Angle — Product Viewpoint Transfer

Creator Research recipe: **source-conditioned product viewpoint transfer** of
the verified CR-003 Refraction Ledger perfume photograph. Ask for one clearly
distinguishable eye-level three-quarter camera view of the **same** unbranded
faceted-glass bottle while preserving recognizable product design, materials,
plinth, and studio character.

This milestone tests an **already supported** capability (`reference_transform`
+ attached source + descriptive camera prose). It does **not** add numeric
camera-yaw fields, novel-view routes, mask/ROI transport, or 3D reconstruction
engineering.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-010-the-second-angle/1.0.0.json` |
| `recipe_id` | `cr-010-the-second-angle` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `reference_transform` |
| TransformationPack | none |
| ArtMethodPack | none (`art.method` null) |
| Artifact form / state | null / null |
| Variables | none (single embedded baseline camera) |

## Creative objective

Start from the exact CR-003 product photograph (near-frontal studio still).
Produce a second catalog angle of that **same** bottle: approximately a
30-degree off-axis eye-level three-quarter view that reveals additional depth
and a meaningfully different side-facet arrangement.

Goal class **C** only:

| Class | Meaning | CR-010 |
| --- | --- | --- |
| A | Unrelated new product photograph | Reject |
| B | Same product, same viewpoint | Reject |
| C | Same product, new viewpoint | **Target** |
| D | Verified 3D geometry reconstruction | **Not claimed** |

## Feasibility verdict

**Supported for semantic product viewpoint transfer (descriptive camera only).**

| Capability | Verdict |
| --- | --- |
| Source-conditioned transform of an attached product photo | **Supported** via `reference_transform` |
| Product-design governance via `artifact` role | **Supported** |
| Studio/plinth context via `environment` without camera lock | **Supported** (role imports space/mood, not camera) |
| Palette continuity via `palette` | **Supported** |
| Deliberate new viewpoint via `director.camera` prose | **Supported** (descriptive only) |
| Numeric camera yaw / measured physical angle field | **Not installed** |
| Exact 3D reconstruction / novel-view synthesis route | **Not installed; not authorized** |
| Pixel-perfect silhouette equality across viewpoints | **Not required / not claimed** |

Selected route: **`reference_transform`**
(“Transform a person/object/photo while preserving assigned reference roles”;
logic: state preserve/change boundaries before style or scene translation).

Rejected for this experiment:

- `new_generation` — would authorize class A (unrelated product invent).
- `artifact_transform` — medium translation into an artifact; CR-003 is already
  a product photograph, not a portrait-to-object rematerialization.
- Invented `camera_transfer` / `novel_view` / `3d_reconstruction` routes — not
  installed; would violate the no-new-route boundary.
- Assigning `layout` or `pose` to the source — would risk locking the original
  frontal placement/orientation that the experiment must change.
- Person-oriented `identity` — installed semantics target face/person cues; product
  identity is expressed through `artifact` + request locks instead.

## Reference-role configuration

| Role | Assigned? | Rationale |
| --- | --- | --- |
| `artifact` | **Yes** | Bottle form, faceted-glass construction, brushed-metal cap, surface condition |
| `environment` | **Yes** | Pale limestone plinth + restrained neutral studio without importing camera |
| `palette` | **Yes** | Clear glass / satin metal / warm-neutral stone relationships |
| `layout` | **No** | Would import placement/panel/negative-space hierarchy and risk locking frontal framing |
| `pose` | **No** | Would import orientation cues that can fight a camera-orbit reading |
| `identity` | **No** | Person-specific; not a substitute for product design here |

Symbolic reference id: `cr003-c0-l0-4x5-source`.

## Source integrity (CR-003)

| Field | Value |
| --- | --- |
| Source | Verified CR-003 private import original |
| SHA-256 | `43a9ff6e0a0aaed177fae1145ac3e1ed88566ab507952c4e68fde97d10b3d1c4` |
| Observed dimensions | 1122 × 1402 |
| Byte length | 1,952,637 |
| Symbolic reference id | `cr003-c0-l0-4x5-source` |
| Roles | `artifact`, `environment`, `palette` |

Private custody/import/gallery linkage for this SHA was re-verified under
CR-GATE-020 `cr003-c0-l0-4x5` (`05_chatgpt_web_import` + private gallery
candidate). Source bytes are **not** copied into Git. Absolute private paths
stay outside tracked recipe content. CR-003 is the only required source image.

## Camera-binding support and limitations

- PromptRecipe v1.1 allows optional enum overrides only for `director.camera`,
  `director.light_source`, and `output.aspect_ratio`.
- CR-010 `1.0.0` embeds **one** descriptive baseline camera string and keeps
  `variables: {}` (no variation matrix).
- Approximate “30 degrees” language is **editorial intent**, not an independently
  measured physical yaw and not a schema-enforced numeric field.
- API `edit` mode activates when an image attachment is supplied
  (`model_adapter`); ChatGPT Images manual workflow remains operator-attested.
- Compiler emits role discipline + director camera prose; it does **not** enforce
  geometric viewpoint success in model output.

## Creator research findings and sources

### Physical / photographic principles (not model guarantees)

| Source | Type | Extracted principle |
| --- | --- | --- |
| Acquire Convert — Product Photography Angles | catalog practice | Three-quarter answers shape and depth; strong second image after a hero |
| Shotinger — Perfume Product Photography | ecommerce how-to | Front hero first; 30–45° three-quarter reveals thickness/shoulders; glass needs controlled reflections, not zero reflections |
| Pixora — Clear Glass Product Photography Guide | commercial how-to | Soft broad light; black cards for edge lines; longer focal length reduces distortion; consistent multi-angle sets |
| Ken Jones NYC — Reflective Product Photography | studio practice | Angle of incidence = angle of reflection (“family of angles”); camera move relocates highlights predictably |
| Dorian Iten — Understanding the Fresnel Effect | optics primer | Specular strength rises toward grazing angles; curved forms show viewpoint-dependent highlight zones |
| Ashikhmin & Shirley — An Anisotropic Phong BRDF Model | graphics/optics paper | Brushed metal is anisotropic; cylindrical brushing stretches highlights into streaks/ellipses that change with view |
| CR-003 Refraction Ledger research | in-repo | Bright-field/dark-field exclusivity; brushed ≠ chrome; honed limestone is matte |

### Distinctions recorded for this recipe

1. **Camera-relative vs object-relative rotation** — CR-010 asks for a camera
   orbit / second catalog angle around a stable upright bottle, not a prop tip
   or redesign.
2. **Reflections and refraction must update** — freezing source speculars would
   fake an unchanged viewpoint.
3. **Single-view uncertainty** — a photograph does not provide a complete 3D
   model; hidden surfaces may only be *plausibly* continued.
4. **Image-model behavior is assumed, not proven** — recipe semantics can request
   viewpoint transfer; KEEP/REJECT still requires human visual review after a
   separately authorized generation.

## Product-preservation priorities

Preserve:

- Overall bottle-design identity (recognizable as CR-003’s bottle)
- Transparent faceted-glass construction and clear colorless appearance
- Distinctive shoulder geometry and central body proportions
- Cylindrical brushed-metal cap and cap-to-body proportion
- Unbranded design; pale limestone plinth; restrained neutral studio; lighting character

Allow with the new perspective:

- Apparent front vs side facet widths and visible side-face depth
- Perspective foreshortening of bottle and plinth
- Relocated reflections, refraction patterns, and cap ellipse/cylinder shading

## Explicit failure conditions

Reject if:

- Viewpoint remains essentially identical (cosmetic lighting-only change)
- Bottle becomes a substantially different product design
- Cap changes shape/material, floats, or disconnects
- Facets are lost; glass becomes opaque, cloudy, or metallic
- Impossible contradictory front/side geometry; second neck / duplicated shoulder
- Implausible scale change; extra bottles; invented brand/label
- Model redesigns the product instead of changing viewing angle
- Output claims exact reconstruction of unseen geometry

A beautiful photograph of a **different** bottle is REJECT, not KEEP.

## Qualitative visual evaluation

KEEP requires **both** recognizable product fidelity **and** a genuine viewpoint
change. Review independently:

1. Recognizable product design
2. Meaningful viewpoint change
3. Facet and shoulder continuity
4. Cap geometry continuity
5. Glass transparency and refraction credibility
6. Material-lighting credibility under the new angle
7. Plinth and perspective coherence
8. Absence of unwanted product redesign

Evidence classes:

- **Observed** from source: visible facets, shoulder, cap, plinth, studio, glass clarity
- **Plausibly inferred**: partially hidden side/rear geometry continued consistently
- **Unsupported**: exact metric 3D fidelity or measured yaw verification

No pixel-level equality requirement across different camera views.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `fdf3b4181313e83a2a3c7c60aaec0cfb92cfc2c46e6a72622a3aa629188e9183` |
| Baseline compiled prompt | `eecb60fd973d07e03a9a38ad73ce707b6c0cd52b862817604a3c921bf3610215` |
| Source (CR-003) | `43a9ff6e0a0aaed177fae1145ac3e1ed88566ab507952c4e68fde97d10b3d1c4` |

## Future manual source-attachment procedure

Separately authorized ChatGPT Images (or API edit) request must include **in the
same request**:

1. The verified CR-003 original PNG (hash above; not a screenshot/thumbnail)
2. The exact prepared CR-010 adapter-effective prompt

Request one new product viewpoint derived from the attached original.
Manual attachment and prompt submission remain operator-attested/uncaptured.
Model identity and ChatGPT’s internal effective prompt remain unknown unless a
future channel separately attests them.

**No image generation is authorized by this documentation alone.**

## Provenance and authenticity limits

- Recipe and compiler digests prove prompt-library integrity, not generation success.
- Source SHA proves local byte identity of the CR-003 import, not upload proof.
- Semantic/negative prompt audits prove conditioning text changes; they do **not**
  prove model viewpoint consistency.
- Single-view geometry continuation is interpretive, not a verified mesh.
- CR-008 remains blocked (localized edit/mask gap). CR-010 does not reopen it.
- No ninth gallery entry, public publication, or Git merge is authorized here.
