# CR-008 Golden Fault — Localized Porcelain Repair (Feasibility Research)

Creator Research milestone for a **source-conditioned localized edit** of the
verified CR-007 Porcelain Echo vase: one limited gold-lacquer repair line on the
upper-right shoulder, preserving the remainder of the same image as closely as a
supported editing workflow allows.

**This delivery is research and feasibility only.** No PromptRecipe was
implemented. No image generation or editing. No private preparation, custody,
import, or gallery assets. No compiler, schema, route, or pack expansion.

| Field | Value |
| --- | --- |
| Proposed `recipe_id` | `cr-008-golden-fault` |
| Proposed version | `1.0.0` |
| Working title | Golden Fault — Localized Porcelain Repair |
| Feasibility verdict | **BLOCKED — LOCAL EDIT CAPABILITY GAP** |
| Recipe path | *not implemented* |
| Recipe SHA-256 | *n/a* |
| Baseline prompt SHA-256 | *n/a* |

## Feasibility verdict

AIPF can express **source-backed whole-image regeneration / medium translation**
and can call the Images API in whole-image `edit` mode when reference files are
attached. It **cannot** currently represent a **controlled localized edit** with
a truthful outside-region preservation contract.

Therefore CR-008 stops before recipe implementation. Using `new_generation` or
generic `artifact_transform` as a substitute would misrepresent a whole-image
regeneration as a bounded local repair and is not authorized.

### Capability matrix (A–H)

| ID | Capability | Verdict | Evidence |
| --- | --- | --- | --- |
| A | One existing source image as edit target | **PARTIAL** | Symbolic `references[]` + operator/API attachment; no dedicated edit-target / canvas role |
| B | Narrowly specified edit region | **NO** | No mask, ROI, bbox, or paint-region field; `historical.region` is geographic/cultural |
| C | Source-preservation outside that region | **NO** | Prompt prose can request it; nothing scopes “outside region”; no pixel lock |
| D | Material-specific change within that region | **PARTIAL** | Whole-image ArtMethod / TransformationPack only |
| E | Unchanged camera, scene, silhouette | **PARTIAL** | Locks / identity / body modes are semantic; not pixel-enforceable |
| F | Image-editing request vs fresh generation | **PARTIAL** | Adapter `mode=edit` when images attached; compiler still emits a production brief |
| G | Semantic preservation vs enforceable masking | **YES (honest gap)** | Docs/guidance distinguish instruction from attachment; schema has no mask-enforceability claim |
| H | Actual source attachment requirements | **PARTIAL** | Documented CR handoffs; binaries out of PromptRecipe; ChatGPT attachment operator-attested |

### Exact supported contracts inspected

| Layer | Installed identifiers / behavior | Localized edit? |
| --- | --- | --- |
| Routes (`references/routes/registry.json`, `data/schemas/request.schema.json`) | `new_generation`, `reference_transform`, `historical_portrait`, `artifact_transform`, `art_style_transform`, `storyboard_or_grid`, `design_layout`, `evaluation_revision` | No ROI route. Closest whole-image: `reference_transform` / `artifact_transform` |
| Reference roles (`references/core/reference_roles.json`) | `identity`, `pose`, `outfit`, `hairstyle`, `artifact`, `style`, `environment`, `layout`, `palette` | Permission boundaries for import, not pixel masks. No `edit_target` / `mask_guide` |
| TransformationPacks | `portrait_to_volumetric_sculpture`, `portrait_to_architectural_mural`, `portrait_to_relief_print`, `portrait_to_decorated_artifact` | Full medium translation deltas |
| ArtMethodPacks | includes `blue_white_ceramic`; no gold-lacquer / kintsugi pack | Global material language |
| Artifact states | includes `partially_restored`, `damaged`, `museum_conserved` | Lifecycle appearance labels, **not** edit masks |
| Adapter (`references/core/gpt_image_2_adapter.json`, `src/aipf/model_adapter.py`) | modes `generate` \| `edit`; `edit` iff image paths present | Whole-image edit conditioning |
| Executor (`scripts/generate_api.py`) | `--image` (appendable); **no `--mask`** | No mask transport |
| Schemas under `data/schemas/` | no `mask` / `edit_region` / `inpaint` / `preserve_outside` matches | Confirmed absent |
| Compiler (`src/aipf/compiler.py`) | Text production brief; role discipline; transformation deltas | Does not branch on pixel ROI or API edit mode |
| CR-004–CR-007 pattern | Source-backed whole-object transforms / new campaigns | Not localized canvas edits |

Identifiers **not** present (do not invent): `localized_edit`, `surgical_edit`,
`kintsugi_repair`, `gold_lacquer` route/pack IDs, mask attachment fields.

### Smallest compatibility gap

Missing first-class pair (neither alone is enough for a truthful CR-008 claim):

1. **Semantic:** edit-region specifier + explicit outside-region source-preservation
   contract (ideally an edit-target / canvas role distinct from attribute-import
   roles), **and**
2. **Transport:** mask (or host-native localized-edit) attachment in
   `model_adapter` / `generate_api` / ChatGPT handoff metadata,

wired so the system can distinguish targeted editing from whole-scene
regeneration without falsely asserting pixel-level enforcement from text alone.

**No schema/route/pack/compiler expansion was authorized in this milestone.**

## Source integrity (CR-007 edit target)

| Field | Expected | Observed |
| --- | --- | --- |
| Private import original | CR-GATE-043 `cr007-c0-4x5/05_chatgpt_web_import/original.png` | Present |
| SHA-256 | `15b082d7573ee973740553d463aa2693634fcc45a6d0a4d8538dd5e0c4dcbc97` | Match |
| Dimensions | 1122 × 1402 | Match |
| Byte length | 2,050,051 | Match |

Private import `source.json` binds the same image SHA to recipe
`cr-007-porcelain-echo` `1.0.0` (recipe SHA
`6af6a0756b344d45a4281e882280f593bd3ffed09b54d9be7b0f86ceb14c3b42`, compiler
prompt SHA `ae067b7b1d6c1b1877cdd1b4f9d39d5ab0e6bc861611178b0c47b68fca4138eb`)
with `submission_verification: operator_attested_uncaptured`.

Source bytes were **not** rewritten, duplicated into Git, recompressed, or
overwritten. Absolute private paths remain outside tracked recipe content.
CR-002 is an upstream creative ancestor only; it is **not** required as a second
image attachment for a future CR-008 edit once a local-edit contract exists.

## Material research findings

This recipe concept visualizes a **fictional contemporary repair** applied to an
**AI-generated** porcelain object. It is **not** an authenticated Japanese
artifact and **not** a completed museum conservation treatment.

| Finding | Implication for a future local edit |
| --- | --- |
| Japanese gold-lacquer ceramic repair (kintsugi / kintsuguroi) joins broken ceramic with lacquer (urushi / plant resin), then finishes seams with powdered gold | Repair reads as a **structural join**, not floating gold paint or an ornamental vein network |
| Lacquer is the joining/filling material; gold is a metallic finish on the cured repair seam | Prompt must separate glazed porcelain body from lacquer join + gold finish |
| Lacquer ceramic repair long predates gold decoration; gold finish became associated especially with tea-ware aesthetics | Do not claim Ming/Song/Edo authenticity for CR-007/CR-008 |
| Physical fracture geometry is irregular, curvature-following, and typically sparse | Prefer one narrow irregular line; one short branch only if materially justified |
| Glazed blue-and-white porcelain already has hard speculars distinct from underglaze pigment | Gold reflections must sit on the repair seam without rewriting global glaze behavior |
| Common AI edit failures | Redesign whole vase; repaint portrait; change camera/background; decorate with gold patterns; invent extra cracks; break object into pieces |

### Primary citations (material / conservation; not compositions to copy)

| Source | URL | Notes |
| --- | --- | --- |
| Smithsonian — The Beauty of Broken Objects | https://www.si.edu/collections/snapshot/beauty-broken-objects | Freer Satsuma-type tea bowl; lacquer join + powdered gold; highlights object life rather than hiding damage |
| Smithsonian NMAA — Japanese art accessible label text | https://asia.si.edu/accessibility/japanese-art-from-the-collection-accessible-label-text/ | Conservation / repairing-and-preserving context (page fetch intermittently unavailable during this session; retain as designated primary reference) |
| Smithsonian NMAA — Gold (materials & techniques) | https://asia.si.edu/explore-art-culture/art-stories/materials-techniques/gold/ | Gold as material/technique reference (page fetch intermittently unavailable during this session) |
| Smithsonian exhibition context — Golden Seams | https://www.si.edu/exhibitions/golden-seams-japanese-art-mending-ceramics:event-exhib-4567 | Lacquer adhesive tradition + Japanese gold-powdered finish for ceramic mends |
| Related Freer tea-bowl commentary | https://asia-archive.si.edu/friday-fave-tea-bowl/ | Powdered gold over lacquer repairs; functional join that also transforms appearance |

## Intended local edit specification (deferred)

When a supported local-edit contract exists, the deferred creative target is:

| Field | Intent |
| --- | --- |
| Source object | CR-007 Porcelain Echo vase only |
| Region | Visible **upper-right shoulder** (viewer’s right), between neck transition and pavilion-roof motif, **away from the painted figure’s face** |
| Region suitability | **Suitable.** That zone has pale blossom / reserved white glaze with no face overlap; a narrow seam can follow shoulder curvature without covering the portrait |
| Edit | One subtle irregular gold-lacquer repaired fracture; optional single short secondary branch only if materially justified |
| Material | Lacquer join filled into a plausible fracture, gold/metallic finish on the seam, restrained thickness, small realistic metallic reflections, plausible glaze↔repair transition |
| Not allowed | Floating ornament; random decorative vein network; gold borders; dynasty marks; extra chips elsewhere; marble/metal/glass conversion; figure redesign |

### Preservation contract (deferred semantic requirements)

Preserve as closely as the future supported workflow allows: vase silhouette; rim
and opening; neck/shoulder proportions; body curvature; foot and contact shadow;
cobalt portrait (face, hair, floral ornament, garment); existing floral and
architectural motifs; glaze reflections outside the repair; camera framing;
perspective; background; lighting direction; original 4:5 composition.

Architectural motifs already present in CR-007 (known source-environment
resemblance from the prior milestone) are **out of scope** for CR-008’s
single-factor edit—do not repaint, remove, or relocate them under this brief.

### Explicit failure conditions (evaluation)

Reject if the vase is redesigned; portrait disappears or materially changes;
silhouette/rim changes; studio environment changes; gold covers large areas;
repair reads as decorative painting rather than a fracture join; unrelated
cracks/chips appear; gold floats; curvature is ignored; object appears
disconnected; cobalt is unnecessarily repainted; framing/background changes
materially; or the result is merely a new lookalike vase. An attractive
gold-decorated vase is **not** sufficient.

## Visual comparison plan (future; no derivatives now)

When an edited candidate exists under a supported contract, evaluate:

1. Original vs edited silhouette
2. Portrait and motif preservation
3. Spatial localization of the repair
4. Physical plausibility of the repaired fracture
5. Gold-lacquer material credibility
6. Scene, lighting, and camera consistency
7. Unexpected changes outside the target region

| Gate | KEEP | REVISE | REJECT |
| --- | --- | --- | --- |
| Localization | Repair confined to intended shoulder seam | Mild bleed or thickness issues | Broad gold network or wrong zone |
| Preservation | Portrait, motifs, camera, bg intact | Minor unintended glaze/motif drift | Redesign, portrait change, scene change |
| Material | Reads as lacquer join + gold finish on fracture | Slightly paint-like but fixable | Floating ornament / decorative gilding only |
| Structure | Single coherent vessel | Mild fracture overstatement | Disconnected shards / extra damage |

Recommend a future **aligned-image difference visualization** as a diagnostic aid.
Do **not** treat every pixel difference as a meaningful visual error (compression,
anti-aliasing, and micro-specular drift are expected). No difference maps or
image derivatives were generated in this research milestone.

## Recipe implementation result

**STOP — recipe not implemented.**

Reason: architecture supports only whole-image regeneration / text-instructed
preservation without a credible localized-preservation contract. Implementing
`recipes/cr-008-golden-fault/1.0.0.json` on `artifact_transform`,
`reference_transform`, or `new_generation` would silently substitute uncontrolled
regeneration for the required local edit.

Negative audit (compiler distinguishability): with current contracts, removing a
hypothetical “add gold repair line” clause from a whole-image transform prompt
would not switch the system from targeted editing to non-editing—both paths
remain production briefs without ROI/mask semantics. That failure mode alone
blocks truthful CR-008 recipe authoring under the authorized scope.

## Future handoff instructions (not authorized now)

A separately authorized future editing request must include:

1. The verified CR-007 original PNG (SHA above) as the **image to edit**
2. The exact CR-008 adapter-effective prompt (once a supported recipe exists)
3. Any mask/region artifact **only if** the installed workflow requires and can
   generate one—do not fabricate region-mask evidence

The request must state that the source is to be **edited**, not replaced with a
newly generated lookalike. Submission remains operator-attested/uncaptured unless
a separately supported evidence channel is available.

## Provenance limitations

- PromptRecipe does not package reference binaries.
- ChatGPT Web attachment and internal effective prompt are not independently
  captured on the current manual channel.
- SHA identifies bytes; it does not prove upload.
- Text preservation instructions are not pixel-level masks.
- No CR-008 generation, custody, gallery candidate, or public publication is
  authorized by this document.

## Privacy and publication restrictions

Private absolute paths stay outside Git. No public publication. No eighth gallery
card. No modification of existing original PNGs or CR-001–CR-007 creative
evidence. Untracked `.superpowers` and EXP-019 draft files are preserved and
out of scope.
