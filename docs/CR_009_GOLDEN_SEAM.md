# CR-009 Golden Seam — Controlled Whole-Image Revision

Creator Research recipe: **source-conditioned whole-image revision** of the
verified CR-007 Porcelain Echo photograph. Request one restrained gold-lacquer
repair seam on the existing vase’s upper-right shoulder while semantically
prioritizing preservation of the recognizable source object, decoration, camera,
and studio setting.

This milestone tests an **already supported** capability. It does **not**
implement, bypass, or resolve the blocked CR-008 localized-editing gap.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-009-golden-seam/1.0.0.json` |
| `recipe_id` | `cr-009-golden-seam` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `reference_transform` |
| TransformationPack | none |
| ArtMethodPack | none (`art.method` null) |
| Artifact form / state | null / null |
| Variables | none (single baseline camera embedded) |

## Experiment objective

Start from the exact CR-007 product photograph. Ask for a small, physically
plausible gold-lacquer repair seam. Because AIPF has **no enforceable spatial
editing boundary**, the model may regenerate the complete image. Evaluate how
much unwanted change occurs outside the intended area.

Do **not** claim pixel-exact source preservation, a true localized edit, or
mask-based production.

## Feasibility verdict

**Supported for whole-image revision (not localized edit).**

| Capability | Verdict |
| --- | --- |
| A. Source-backed whole-image transformation | Available via routes + packs (CR-004/005/007 pattern) — **not** used here |
| B. Existing-image editing (whole-image) | **Supported** via `reference_transform` + attached source + semantic preserve/change prose |
| C. Masked / region-scoped editing | **Not supported** (CR-008 blocked) |
| D. Semantic preservation instructions | **Supported** as prompt guidance only |

Selected route: **`reference_transform`**
(“Transform a person/object/photo while preserving assigned reference roles”;
logic: state preserve/change boundaries before style or scene translation).

Rejected for this experiment:

- `artifact_transform` — implies medium translation into an artifact; CR-007 is
  already an artifact photograph, not a portrait to re-materialize.
- `new_generation` — implies a new scene rather than revising the attached image.
- Any invented `localized_edit` / mask route — not installed; would reopen CR-008.

Reference roles (single symbolic source): `identity`, `artifact`, `environment`,
`layout`, `palette`.

## Difference from blocked CR-008

| | CR-008 Golden Fault | CR-009 Golden Seam |
| --- | --- | --- |
| Goal | Controlled **localized** edit | Controlled **whole-image** revision |
| Spatial ROI / mask | Required for truthful claim | Explicitly **absent** |
| Outside-region pixel lock | Required | **Not claimed** |
| Recipe | Not implemented | Implemented |
| Route | None selected (blocked) | `reference_transform` |
| Status | Research COMPLETED / Implementation BLOCKED | Recipe MERGE-candidate (no generation) |

## Source integrity (CR-007 edit target)

| Field | Value |
| --- | --- |
| Source | Verified CR-007 private import original |
| SHA-256 | `15b082d7573ee973740553d463aa2693634fcc45a6d0a4d8538dd5e0c4dcbc97` |
| Observed dimensions | 1122 × 1402 |
| Byte length | 2,050,051 |
| Symbolic reference id | `cr007-c0-4x5-source` |
| Roles | `identity`, `artifact`, `environment`, `layout`, `palette` |

Private custody/import/gallery linkage for this SHA was re-verified under
CR-GATE-043 `cr007-c0-4x5`. Source bytes are **not** copied into Git. Absolute
private paths stay outside tracked recipe content. CR-002 is an upstream
creative ancestor only—not a second required attachment.

## Material research references

Primary research remains [CR_008_GOLDEN_FAULT.md](CR_008_GOLDEN_FAULT.md).
CR-009 reuses those gold-lacquer principles without repeating the full survey:

- Lacquer as joining/filling material; powdered gold as metallic finish
- Irregular fracture geometry following ceramic curvature
- Structural repair appearance vs ornamental gilding
- Small restrained metallic reflections; glaze↔repair transition
- Fictional contemporary repair visualization on an AI-generated object—not an
  authenticated Japanese artifact or completed conservation treatment

Citations retained from CR-008 (material/conservation context, not compositions
to copy): Smithsonian Beauty of Broken Objects; NMAA repair/gold materials pages;
Golden Seams / Freer tea-bowl commentary.

## Requested change (semantic, not ROI)

- One narrow irregular gold-lacquer repair seam on the visible **upper-right
  shoulder** (viewer’s right), away from the painted face
- Optional one short branch only if fracture geometry justifies it
- Seam follows vessel curvature; restrained metallic reflections; integrated
  with glazed ceramic—not floating ornament or a gold vein network
- No additional cracks/chips elsewhere

No fake ROI coordinates, mask assets, or region-control fields.

## Semantic preservation strategy

Ask the model to preserve as closely as a whole-image edit allows: silhouette;
rim/opening; neck/shoulders/foot; cobalt portrait (face, hair, floral ornament,
garments); floral and existing architectural motifs; glaze appearance;
background; lighting; camera framing; perspective; 4:5 composition.

Existing corridor-style architectural motifs remain as in CR-007—do **not** try
to “fix” prior environment-role leakage under this recipe.

All preservation language is **semantic preference**, not enforceable pixel
boundaries.

## Limitations of whole-image editing

- Attaching a PNG selects adapter `mode=edit` for the API path, or ChatGPT Images
  attachment for the manual path; these are **not** proven identical behaviors.
- Compiler still emits a production brief; it does not emit masks.
- The model may regenerate unrelated regions while attempting the seam.
- Text “preserve X” does not guarantee unchanged pixels.
- Success is judged by recognizable object continuity + restrained edit presence,
  not by pixel-diff pass rates.

## Qualitative acceptance criteria (later generation gate)

| Axis | KEEP | REVISE | REJECT |
| --- | --- | --- | --- |
| A. Requested edit presence | Clear restrained gold-lacquer seam on upper-right shoulder | Weak/ambiguous seam | Seam absent |
| B. Repair credibility | Reads as lacquer join + gold finish | Mildly paint-like | Ornamental gilding / floating gold |
| C. Vessel geometry | Silhouette/rim/foot match source | Mild drift | Redesigned vase |
| D. Portrait/ornament fidelity | Face, hair, garments, motifs intact | Minor motif drift | Portrait change / wholesale repaint |
| E. Background/camera | Studio + framing match | Mild lighting drift | New scene / reframe |
| F. Unintended changes | No extra cracks; no gold network | Small extras | Extensive damage/gilding |
| G. Creative usefulness | Recognizable CR-007 revision | Borderline | Different blue-and-white vase |

A visually attractive gold-decorated vase is **not** sufficient.

### Future comparison (not generated now)

Recommend a later original-versus-edit comparison page. An aligned-image
difference map may help spot global drift, but do not assume pixel alignment,
equate every changed pixel with creative failure, invent scientific pass rates,
or treat similarity as proof of masked editing. No difference maps in this
milestone.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `8bff3467bbe5a1436881098b82eafee239a4644c78b6d08af48a635e196817ed` |
| Baseline compiled prompt | `7273bd83193d65a47cf97b789aff64bf69abe901a87cbcfe67a08cf900d52f5a` |

## Future operator handoff (not authorized here)

A separately authorized ChatGPT Images request must include, in the **same**
request:

1. Verified CR-007 original PNG (`15b082d7…c4dcbc97`) as the **existing image to
   edit**
2. Exact prepared CR-009 adapter-effective prompt

No mask attachment is authorized or expected. Present the source as an image to
edit, not mere aesthetic inspiration. Attachment and prompt submission remain
operator-attested/uncaptured unless a separately supported evidence channel
exists. ChatGPT Web behavior is not asserted identical to
`generate_api.py --image` API `edit` mode. Provider-verified model identity and
internal effective prompt remain unknown.

## Provenance limitations

- PromptRecipe does not package reference binaries.
- SHA identifies bytes; it does not prove upload.
- Whole-image edit ≠ localized edit; semantic locks ≠ pixel locks.
- Deterministic compile ≠ demonstrated visual success.
- No eighth gallery card, no public publication, no CR-008 implementation reopen.

## Rights and publication restrictions

Private absolute paths stay outside Git. No public publication. No private
preparation/custody/import/gallery changes in this delivery. CR-001–CR-007
creative evidence remains untouched. Untracked `.superpowers` / EXP-019 drafts
remain out of scope.

## Validation commands

```bash
aipf recipe validate recipes/cr-009-golden-seam/1.0.0.json
aipf recipe compile recipes/cr-009-golden-seam/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Out of scope

Image generation/editing, API execution, private prep/custody/gallery, CR-008
implementation, compiler/schema/route/pack/adapter/mask expansion, CR-001–CR-007
evidence edits, EXP-019 / ESR / AIQ / G4/G5 work, merge without owner approval.
