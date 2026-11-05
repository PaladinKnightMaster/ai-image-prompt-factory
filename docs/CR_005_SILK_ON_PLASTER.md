# CR-005 Silk on Plaster

Creative Research recipe: **source-backed** V3.4 artifact transformation from the
verified CR-002 Song Corridor Editorial photograph into a contemporary
mineral-pigment architectural mural on prepared plaster. PromptRecipe library
only in this delivery—no image generation, custody import, or gallery index
changes.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-005-silk-on-plaster/1.0.0.json` |
| `recipe_id` | `cr-005-silk-on-plaster` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |
| TransformationPack | `portrait_to_architectural_mural` |
| ArtMethodPack | `mineral_pigment_mural` |
| Artifact form / state | `wall_surface` / `newly_created` |
| EraPacks | none |

## Creative brief

Preserve the CR-002 adult figure’s recognizable identity, stance/silhouette,
restrained upswept hairstyle, and layered open-front garment fold architecture.
Transform photographic person, silk, and depth cues into a wall-bound mural:
matte mineral pigment on a physically plausible plaster plane, shown with enough
surrounding architecture (wall, optional corner/ceiling junction, floor) to read
as an installed contemporary commission in a quiet cultural gallery.

The target is **not** an excavated Song mural, Dunhuang cave reconstruction, or
framed canvas. Source Song-informed fashion cues may remain visually readable in
painted wardrobe language; they do not authorize historical authenticity claims.

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
| AIPF `references/art-methods/mineral_pigment_mural.json` | in-repo ArtMethodPack | Wall-bound pigment, plaster interruption, failure modes (digital fresco filter, living skin pasted into mural) |
| AIPF `portrait_to_architectural_mural` pack | in-repo TransformationPack | Portrait → architectural mural delta; avoid photograph pasted onto a wall |
| Getty Conservation Institute — *Organic Materials in Wall Paintings* project / report | conservation science | Fresco = pigment on fresh lime plaster fixed by carbonation; secco / organic-binder painting on dry plaster is historically common and must not be collapsed into a universal “fresco” label |
| Getty AAT — *buon fresco* / *fresco secco* | controlled vocabulary | Distinguishes wet-plaster fixation from dry-plaster binder techniques |
| Mora, Mora & Philippot — *The Conservation of Wall Paintings* (ICCROM, 1977) and related ICCROM mural-conservation materials | conservation manual | Wall paintings are integral to architectural fabric; rendering/plaster layers, pigment adhesion, and architectural context matter more than treating the image as a detachable picture |
| CIE 157:2004 museum lighting context; CIE museum luminance-contrast studies | museum lighting | Quiet gallery presentation favors controlled exhibit/wall luminance relationships and glare avoidance rather than theatrical specular spectacle |

**Interpretation for CR-005 (not historical attribution):** Prefer a contemporary
mineral-pigment mural language on prepared plaster. Do not invent Song-dynasty
excavation provenance. Do not force buon-fresco authenticity theater or fake
ancient loss overlays. Painted fabric must remain planar pigment drapery sharing
the wall support.

## Transformation architecture

- Route `artifact_transform` (not `new_generation`).
- Pack `portrait_to_architectural_mural` → target representation `architectural_mural`.
- Method family `painting_on_wall` is the accepted family for that target
  (`transformation_art_gate`).
- Form `wall_surface` is declared compatible by `mineral_pigment_mural`.
- State `newly_created` for a fresh contemporary commission (clean finish; no fake
  archaeological damage).
- Empty EraPack list: mural material must not imply Dunhuang/Song reconstruction.
- Identity `recognizable_identity`; body `artistic_stylization`.
- Reference roles preserve figure/wardrobe identity while omitting `environment`
  so the corridor set can become gallery architecture.
- Camera-only v1.1 variables (1 baseline + 2 architectural variants); aspect fixed
  at `4:5`.

## Exact supported pack/method/form choices

Validated against installed registries/gates (no new packs or schema changes):

| Component | Exact ID |
| --- | --- |
| TransformationPack | `portrait_to_architectural_mural` |
| Source / target representation | `portrait` → `architectural_mural` |
| ArtMethodPack | `mineral_pigment_mural` |
| Artifact form | `wall_surface` |
| Artifact state | `newly_created` |
| EraPacks | `[]` |

## Physical mural constraints

- Mural is inseparable from a prepared plaster wall plane.
- Brush/pigment edges may be interrupted by plaster grain.
- Surrounding architecture (floor meeting wall; optional corner/ceiling junction)
  establishes installation scale.
- Gallery lighting is soft, directional, and matte-friendly—no theatrical god-rays
  or living-skin speculars inside the mural field.
- Avoid framed canvas, pasted poster, floating panels, and living models standing
  in front of painted scenery.
- Avoid fabric physically protruding from the wall without artistic justification.

## Source-fidelity constraints

Preserve from CR-002: recognizable primary figure; general pose/silhouette;
hairstyle structure; layered garment arrangement; major folds/decorative visual
characteristics; coherent figure–clothing relationship.

Change: photographic person/fabric/depth → painted pigment mural composition;
photographic surface → plaster wall; corridor background → deliberate gallery
architectural presentation.

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
2. Representation change is portrait → `architectural_mural`.
3. Exact supported method/form/state: `mineral_pigment_mural` /
   `wall_surface` / `newly_created`.
4. Source figure and wardrobe preservation are locked in request, identity, and
   director fields.
5. Painted medium replaces photographic realism inside the artwork.
6. Mural is part of architecture (wall plane, floor relationship, optional corner).
7. Surface, lighting, and perspective instructions are coherent and contemporary.
8. Composition aspect `4:5`.
9. Explicit negation of excavated Song / Dunhuang authenticity claims.
10. No contradictory bright-field/dark-field or living-vs-painted pairs in baseline.
11. No CR-001 evening-gown / CR-003 perfume / CR-004 marble leakage in compiled
    baseline.
12. No host-absolute private paths in tracked recipe or this document.

Negative semantic audit: removing `transformation` and forcing `new_generation`
drops the transformation section and changes `prompt_sha256`.

Deterministic compile ≠ demonstrated visual success.

## Failure modes

- Living model standing in front of a mural
- Framed artwork / canvas / pasted poster / floating panel
- Photographic skin or silk retained inside the painted field
- Fabric protruding from the wall
- Uniform cracked-wall overlay or digital fresco filter
- Fake archaeological soot/loss theater
- Unsupported Song/Dunhuang authenticity claims
- Decorative calligraphy or brand text

## Acceptance criteria (later generation gate)

1. Result reads as a wall-integrated mineral-pigment mural, not a living person.
2. Source identity/pose/hairstyle/wardrobe silhouette remain recognizable.
3. Plaster wall, planar perspective, and floor/architecture scale are plausible.
4. No excavated Song/Dunhuang authenticity cues.
5. No extra people, logos, calligraphy, frames, or floating panels.
6. Operator can show the verified CR-002 PNG was the image input used.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `cfe891967c42206606b278306d8f0e16158aece2610759e8060e3ea5cf0eaf88` |
| Baseline compiled prompt (c0 / 4:5) | `6e3f9d6416fffc05c4e94cf81c3312a80b3564f1cd1689a54bfbe31da13984da` |

## Manual ChatGPT Images attachment requirements

Feasible as an **owner-operated** later gate (not authorized here):

1. Prepare recipe baseline under the private creative root (separate authorization).
2. Upload verified CR-002 PNG (`a457c47c…21e0`) as the image input.
3. Paste adapter-effective `prompt.txt`.
4. Attest attachment + prompt submission; import output with existing manual tools.

## Provenance limitations

- Single photograph cannot prove exact mural transfer geometry.
- Models often leave living-skin patches, poster-on-wall composites, or cracked
  overlays.
- ChatGPT Web attachment is not currently hash-captured by prepare/verify.
- Installed mural lexicon glosses retain some earthen-plaster conservation
  vocabulary from Mogao-oriented sources; this recipe counters with empty EraPacks,
  `newly_created`, and explicit contemporary-commission language, but does not
  rewrite ArtMethodPack text.
- Deterministic compile ≠ successful generation.
- No private gallery fifth card, no public publication, no EXP-019/ESR/AIQ claim.

## Validation commands

```bash
aipf recipe validate recipes/cr-005-silk-on-plaster/1.0.0.json
aipf recipe compile recipes/cr-005-silk-on-plaster/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Out of scope

Image generation, CR-001–004 edits, private gallery index changes, compiler or
pack expansion, EXP-019 / ESR / AIQ claims, merge without owner approval.
