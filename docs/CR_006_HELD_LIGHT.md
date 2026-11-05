# CR-006 Held Light — Multi-Reference Fragrance Editorial

Creative Research recipe: **two-reference** contemporary luxury fragrance
campaign photograph composing the verified CR-001 fashion subject with the
verified CR-003 perfume flacon into one coherent editorial exposure.
PromptRecipe library only in this delivery—no image generation, custody
import, or gallery index changes.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-006-held-light/1.0.0.json` |
| `recipe_id` | `cr-006-held-light` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `new_generation` |
| Historical packs | none (`packs: []`) |
| ArtMethodPack | none (`art.method` / form / state = `null`) |
| TransformationPack | none (not an `artifact_transform`) |

## Creative concept

**Held Light** — an unbranded contemporary fragrance campaign still: one adult
fashion subject in the champagne satin gown holds a faceted transparent perfume
flacon at believable hand-held scale. The image must read as a single
photographic exposure with shared lighting, shadows, and perspective—not a
paste of two source frames.

## Verified references

| Ref | Source recipe | Symbolic ID | Roles | SHA-256 |
| --- | --- | --- | --- | --- |
| A — Fashion subject | CR-001 | `cr001-c0-l0-4x5-source` | `identity`, `outfit`, `hairstyle` | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| B — Perfume bottle | CR-003 | `cr003-c0-l0-4x5-source` | `artifact` | `43a9ff6e0a0aaed177fae1145ac3e1ed88566ab507952c4e68fde97d10b3d1c4` |

Both PNGs were verified byte-identical (1122 × 1402) before recipe authoring.
They are **not** copied into Git. Machine-specific absolute paths stay outside
the repository. Recipe `references[].notes` record SHA values and portable
handoff language only; PromptRecipe does **not** package reference binaries
([PROMPT_RECIPE.md](PROMPT_RECIPE.md) boundaries).

## Multi-reference route and role architecture

### Why `new_generation` (not `artifact_transform`)

CR-006 creates a **new living photographic campaign scene** conditioned by two
symbolic references. It does **not** translate a portrait into a different
fabrication medium (marble, mural, ceramic, etc.). Existing
`artifact_transform` packs (`portrait_to_volumetric_sculpture`,
`portrait_to_architectural_mural`, …) would mis-state the intent.

`new_generation` is a registered route and is legitimately compatible with
multiple `references[]` entries: the schema allows an array of independent
reference objects; the compiler emits per-ID role discipline; regression cases
already exercise two-to-five reference isolation
(`reg-layout-no-identity-leak`, `reg-style-no-object-leak`,
`reg-reference-five-role-isolation`). No invented route such as
`multi_reference_composite` exists or was added.

### Role separation

| Reference | Assigned roles | Intentionally omitted |
| --- | --- | --- |
| A (CR-001) | identity, outfit, hairstyle | `pose` (arms/hands must adapt); `environment` |
| B (CR-003) | artifact | `environment` / layout (exclude limestone plinth and CR-003 still-life set) |

Compiler reference clause (baseline):

> `cr001-c0-l0-4x5-source` supplies identity, outfit, hairstyle only;
> `cr003-c0-l0-4x5-source` supplies artifact only. Do not import unassigned
> identity, body, clothing, objects, layout, or style across references; also
> do not import unassigned palette, hairstyle, or environment.

Installed conflict semantics
(`references/core/conflict_resolution.json`): roles are permission boundaries;
only assigned roles transfer; overlapping role claims would require priority,
but CR-006 assigns **disjoint** roles so A/B do not compete for the same slot.

Installed role definitions (`references/core/reference_roles.json`):

- `identity` / `outfit` / `hairstyle` import face, garment construction, hair
  arrangement—not scene props.
- `artifact` imports object form, construction, and surface condition—not
  unrelated scene objects when environment is unassigned.

## Research sources

Photographic / production principles only. No proprietary advertising layouts,
protected prompts, or brand identities were copied.

| Source | Type | Extracted principle |
| --- | --- | --- |
| Corning Museum of Glass — Photographing Glass / reflective objects (Part 1) | museum studio practice | Control reflections deliberately; use fill cards/tents to block uncontrolled spill; manage specular intensity rather than “lighting glass directly.” |
| Society of Photographers — How to Light Glass Bottles (2024) | commercial technique | Large soft sources produce broader, less intense reflections on shiny surfaces; establish one main reflection before adding lights; source orientation changes reflection shape. |
| Adobe Express — Product photography tips | commercial guidance | Soft even light first; product-first composition; include scale/context when helpful; styling must support the product, not distract. |
| Pro Photo Studio / 43frames glass guides (cross-check with CR-003 notes) | commercial how-to | Bright-field vs dark-field are opposing strategies; light what glass reflects/transmits; black/white cards design edge definition. |
| AIPF `references/core/reference_roles.json` + `conflict_resolution.json` | in-repo contracts | Role isolation and overlap precedence for multi-reference prompts. |
| EXP-017 evidence synthesis | empirical (prior) | Explicit identity/outfit/pose role assignment has credible leakage-control evidence in tested context; not automatic proof for fashion+product composition. |

### Distinguish layers

| Layer | Status |
| --- | --- |
| Photographic production principles (glass flags, soft key, shared lighting) | Established craft guidance used as director language |
| AIPF compiler capabilities (symbolic multi-ref roles on `new_generation`) | Verified against schema, compiler, and regression cases |
| Image-model behavior under two attached references | **Unproven** in this milestone; no generation performed |

## Target composition

- One adult fashion subject; three-quarter fashion portrait with readable gown.
- Model holding or naturally presenting one perfume bottle.
- Clear visibility of glass facets and brushed-metal cap.
- Soft controlled editorial lighting; warm-neutral / restrained architectural studio.
- Contemporary luxury styling; baseline aspect `4:5`.

## Preservation versus permitted changes

**Reference A governs (preserve):** facial appearance; hair color / gathered
updo / framing strands; champagne satin gown; cowl neckline; structured fitted
bodice and major drapery; subject identity.

**Reference B governs (preserve):** faceted transparent glass body; overall
bottle proportions/silhouette; brushed-metal cap; cap-to-bottle geometry;
transparent optical appearance; no brand lettering.

**Target composition governs (new):** camera framing; hand position; product
placement; shared lighting; shared shadows and perspective.

**Permitted adaptation:** arm/hand pose changes for secure grip; gown cloth may
respond to the new gesture without redesigning the garment; CR-003 plinth/set
are not required product features.

**Do not invent** exact physical bottle dimensions from the photograph; use
plausible hand-held perfume-flacon scale, not oversized advertising-object
convention.

## Hand / object interaction constraints

- Believable contact pressure; no floating bottle.
- No extra hands, malformed fingers, or impossible grip.
- Glass must not fuse into skin or satin.
- Model and product share one perspective and shadow family.
- Facets must remain readable—avoid uncontrolled glare washout.

## Material and lighting guidance

- Satin: directional specular ribbons along fold crowns (fashion editorial).
- Glass: controlled edge/facet definition via graduated reflections; prefer one
  coherent surround strategy rather than mixing bright-field and dark-field
  tactics in one setup.
- Brushed metal: elongated grain highlights, not polished chrome blowouts.
- Shared soft key + gentle fill so skin, cloth, glass, and metal feel like one
  exposure.

## Expected failure modes

- Different-looking fashion subject or redesigned gown.
- Generic / redesigned perfume bottle or wrong cap geometry.
- Invented branding or lettering.
- Giant bottle or implausibly tiny product.
- Extra hands, fused glass, floating product.
- Inconsistent perspective or composited lighting.
- Facets lost to glare; limestone plinth imported as product geometry.
- Two separately framed images masquerading as one composition.
- A beautiful image that preserves only one source.

## Acceptance criteria (later generation gate)

1. Both verified PNGs were physically attached in the same request with the
   exact adapter-effective CR-006 prompt.
2. Subject face/hair/gown remain recognizably from Reference A.
3. Flacon shape/facets/cap remain recognizably from Reference B.
4. Hand-held scale and contact are physically plausible.
5. One coherent exposure under shared lighting.
6. No branding, no plinth-as-product, no collage artifact.
7. Operator can show intended reference order and role assignment.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `2222db4d21923c9ee3e2630fd2bcd4dc14808ce702d48db7588369b9d5798f51` |
| Baseline compiled prompt (c0 / 4:5) | `5bb47d64c127019cd89070cfcaa460401e325e46e38dbdc3d931db36e4947ec4` |

## Prompt semantic audit (baseline)

1. Two distinct symbolic references present in `references[]` and compiled
   reference discipline.
2. Both verified SHA-256 values appear in portable `notes` (no host-absolute
   private paths).
3. A and B have different responsibilities (identity/outfit/hairstyle vs
   artifact).
4. Route is `new_generation` with documented multi-ref compatibility.
5. Facial, hair, and gown preservation are explicit in request/locks/identity.
6. Product shape, faceting, and cap preservation are explicit.
7. Source pose may adapt; `pose` role intentionally unassigned on A.
8. Plausible hand-held scale and grip language present.
9. Shared scene lighting for satin/skin/glass/metal present.
10. No fabricated branding/labels/text.
11. No CR-002 mural or CR-004 marble instructions.
12. No host-absolute private paths in tracked fields.

### Negative reference-removal audit

| Mutation | Compiled reference clause changes | Prompt SHA changes |
| --- | --- | --- |
| Drop Ref A | Only `cr003… supplies artifact only` remains | Yes |
| Drop Ref B | Only `cr001… supplies identity, outfit, hairstyle only` remains | Yes |
| Drop both | `references` section absent | Yes |

Compiled output distinguishes the two references’ roles; dropping either
reference changes the semantic contract.

## Manual two-reference generation handoff (future authorization only)

The eventual ChatGPT Images request must include **three** inputs in one request:

1. Verified CR-001 original PNG (Reference A).
2. Verified CR-003 original PNG (Reference B).
3. Exact CR-006 adapter-effective compiled prompt.

Both PNGs must be physically attached. Paths or hashes in prompt text are **not**
attachment. Operator must verify intended order and role assignment.

## Provenance and authenticity limits

| Claim | Status |
| --- | --- |
| Recipe encodes symbolic IDs + SHA in notes | Yes |
| PromptRecipe packages PNG binaries | No |
| SHA proves upload / attachment | No |
| Provider-authenticated conditioning | Not claimed |
| Known internal effective provider prompt | Not claimed |
| Verified model identity | Not claimed |
| Independent attachment capture by current tooling | May be unavailable; operator-attested / uncaptured unless a later gate records it |

No generation, custody, import, or gallery evidence is created in this
milestone.

## Variant definitions

| Key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline three-quarter campaign; closer mid-length face+flacon; slightly low vertical gown with mid-torso flacon |

Aspect fixed at `4:5`. No light/aspect variable matrix.

## Schema / implementation boundaries observed

- No compiler, schema, pack, or existing CR-001–CR-005 recipe edits.
- No invented multi-reference route.
- No private paths in tracked files.
- No image generation or gallery work.
