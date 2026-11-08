# CR-011 Era Reframing — Tang Court-Leisure Photographic Transfer

Creator Research recipe: **source-conditioned photographic era reframing** of
the verified CR-001 Material-Driven Fashion subject. Ask for one historically
informed Tang-dynasty court-leisure editorial of the **same recognizable adult
woman** while preserving facial identity, broad three-quarter stance, weight
logic, subject hierarchy, and eye-level full-length framing.

This milestone tests an **already supported** capability (`reference_transform`
+ attached source + EraPack `tang` + explicit preserve/change role boundaries).
It does **not** add new routes, packs, schemas, mask/ROI transport, or
reconstruction claims.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-011-era-reframing/1.0.0.json` |
| `recipe_id` | `cr-011-era-reframing` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `reference_transform` |
| EraPack | `tang` |
| Historical strictness | `historically_informed` |
| TransformationPack | none |
| ArtMethodPack | none (`art.method` null) |
| Artifact form / state | null / null |
| Variables | none (single embedded baseline) |

## Creative objective

Start from the exact CR-001 fashion photograph (modern champagne-satin
architectural evening gown, contemporary low chignon, warm-gray cyclorama).
Produce a living photographic reinterpretation of that same subject in a
Tang-informed court-leisure wardrobe, hair, makeup, accessories, and timber
architectural staging under soft daylight.

Goal class:

| Class | Meaning | CR-011 |
| --- | --- | --- |
| A | Unrelated new person / unlocked identity invent | Reject (that is CR-002 territory) |
| B | Same person, modern gown retained or only recolored | Reject |
| C | Same person, Tang-informed wardrobe/hair/set change with pose/framing continuity | **Target** |
| D | Exact historical reconstruction of a dated ensemble | **Not claimed** |

## Distinction from existing recipes

| Recipe | Why CR-011 is different |
| --- | --- |
| CR-001 | Modern fashion invent; no source reference; CR-011 *consumes* CR-001 as source |
| CR-002 | Song historically-informed invent with `identity_unlocked` and no attachment |
| CR-004 | Medium transform of CR-001 into marble; preserves gown silhouette as stone |
| CR-006 | Dual-ref campaign that **locks** CR-001 outfit/hairstyle |
| CR-009 / CR-010 | Same route family, but vase revision / product viewpoint—not fashion era transfer |

## Feasibility verdict

**Supported for semantic source-conditioned era reframing (photographic).**

| Capability | Verdict |
| --- | --- |
| Source-conditioned transform of an attached fashion photo | **Supported** via `reference_transform` |
| Identity / pose / layout governance via assigned roles | **Supported** |
| Deliberate outfit/hair/environment/palette change via role omission | **Supported** |
| Tang historically-informed anchors via EraPack `tang` | **Supported** |
| Photographic output with `art.method` null | **Supported** |
| Pixel-exact identity or masked local edit | **Not installed; not claimed** |
| Academic reconstruction of a dated Tang garment find | **Not claimed** |

Selected route: **`reference_transform`**.

Rejected for this experiment:

- `new_generation` — would authorize unlocked-identity invent (CR-002 pattern).
- `artifact_transform` — medium rematerialization; not a living photographic era transfer.
- Assigning `outfit` / `hairstyle` / `environment` / `palette` — would lock the modern gown, chignon, cyclorama, or champagne palette that must change.
- New routes or packs — not authorized.

## Reference-role configuration

| Role | Assigned? | Rationale |
| --- | --- | --- |
| `identity` | **Yes** | Recognizable adult facial appearance |
| `pose` | **Yes** | Broad three-quarter stance and weight logic |
| `layout` | **Yes** | Eye-level full-length subject hierarchy / framing |
| `outfit` | **No** | Intended wardrobe transformation axis |
| `hairstyle` | **No** | Intended hair transformation axis |
| `environment` | **No** | Intended set/architecture transformation axis |
| `palette` | **No** | Period silk/timber palette may differ from champagne satin |

Symbolic reference id: `cr001-c0-l0-4x5-source`.

## Source integrity (CR-001)

| Field | Value |
| --- | --- |
| Source | Verified CR-001 private import original |
| SHA-256 | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| Observed dimensions | 1122 × 1402 |
| Symbolic reference id | `cr001-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `layout` |

Private custody/import/gallery linkage for this SHA lives under CR-GATE-005B
`cr001-c0-l0-4x5`. Source bytes are **not** copied into Git. Absolute private
paths stay outside tracked recipe content. CR-001 is the only required source
image.

## Preservation and change contract

Preserve:

- Recognizable facial identity
- Natural adult anatomical proportions
- Broad three-quarter standing orientation and weight-distribution logic
- Overall subject hierarchy
- Eye-level full-length editorial framing (4:5)
- Photographic realism (living person, not medium remake)

Change:

- Modern champagne-satin architectural evening gown → Tang-informed high-waisted
  long silk skirt + layered upper garments
- Contemporary low chignon → elaborate upswept Tang-informed hairstyle with
  restrained ornament
- Modern editorial makeup → period-coherent makeup with visible skin texture
- Warm-gray cyclorama → quiet timber courtyard / covered-walk architectural staging
- Soft architectural daylight motivated by openings

## Professional wardrobe / textile / hair / makeup direction

Authoring vocabulary (historically informed, not reconstruction):

- High-waisted long silk skirt with soft columnar volume and hem weight
- Layered upper garments with readable construction and calm directional sheen
- Elaborate upswept hairstyle; ornament density restrained for court-leisure status
- Makeup coherent with Tang visual culture without heavy beautification
- Accessories limited; no Qing Manchu court robe language; no Song slim beizi as
  the dominant silhouette

EraPack `tang` supplies selective anchors (wardrobe, updos, timber/tiled palace
courtyard, silk). Compiler compatibility language may further discourage later
blue-and-white porcelain as a default Tang prop.

## Known limitations

- Image models may drift toward Song beizi, Qing court dress, xianxia costume, or
  modern gown recolor; recipe prose and EraPack avoid clauses mitigate but do not
  guarantee success.
- Facial identity continuity is semantic, not pixel-exact.
- Pose/framing continuity is editorial guidance under whole-image transform.
- Tang pack is a foundation pack (medium confidence); exact decade/reign/status
  ensembles are not reconstructed here.
- API `edit` activates when an image is attached; ChatGPT Images manual workflow
  remains operator-attested.
- No mask/ROI enforcement exists; CR-008 remains blocked and is not reopened.

## Qualitative visual evaluation (predefined)

Before any generation, KEEP requires **both** recognizable CR-001 subject
continuity **and** clear Tang-informed period transformation. Review:

1. Recognizable source-subject continuity
2. Clear period-specific wardrobe / hair / set transformation
3. Credible garment and fabric construction
4. Coherent hair and makeup
5. Plausible era-specific accessories and environment
6. Absence of major historical anachronisms (Song beizi default, Qing court robe,
   xianxia, modern gown retention)
7. No unwanted anatomical, compositional, or facial distortions
8. Editorial photographic quality consistent with the objective

Subjective creative KEEP is not historical research evidence. A single successful
output does not establish reliable era-transfer performance.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `b1dbfcd54ba22f5dee70c5a16e446b6110b4a91f14e9e1ffa06f6a61ebda1c30` |
| Baseline compiled prompt | `f44b9d8f15bee39abe87a5a5b08a02be91b98b315ad321ad72dbb9b06d5e2715` |
| Source (CR-001) | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |

The compiled prompt digest is the PromptRecipe compiler receipt `prompt_sha256`.
It is **not** automatically an adapter-effective generation prompt unless a later
authorized prepare gate produces and records one.

## Future manual source-attachment procedure

Separately authorized ChatGPT Images (or API edit) request must include **in the
same request**:

1. The verified CR-001 original PNG (hash above; not a screenshot/thumbnail)
2. The exact prepared CR-011 prompt from an authorized prepare gate

Request one Tang-informed photographic era reframing of the attached original.
Manual attachment and prompt submission remain operator-attested/uncaptured.

**No image generation is authorized by this documentation alone.**
No private preparation case, custody artifact, or gallery card is created by this
recipe implementation.

## Provenance and authenticity limits

- Recipe and compiler digests prove prompt-library integrity, not generation success.
- Source SHA proves local byte identity of the CR-001 import, not upload proof.
- Semantic/negative prompt audits prove conditioning text changes; they do **not**
  prove model identity or era fidelity.
- CR-008 remains blocked (localized edit/mask gap). CR-011 does not reopen it.
- No tenth gallery entry, public publication, or merge authorization is implied here.
