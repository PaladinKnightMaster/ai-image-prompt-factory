# TIV-01 — Transformation Integration Verification

**Status:** Offline verification complete (test-only PR track)  
**Engineering baseline:** `150bef8dcfeeded416e1640cf0ee5ded696d57b0`  
**Feature branch:** `test/tiv-01-transformation-integration`  
**Date:** 2026-11-11  

ISV-01 covered the non-TransformationPack ArtMethod/Era emission path. TIV-01 verifies the previously excluded **V3.4 TransformationPack** path: representation-change emission, ArtMethod lexicalization, form/era/reference interactions, and rejection gates.

This track establishes: schema-valid · runtime-loaded · compatible · compiler-emitted.  
It does **not** establish empirical / generated-image fidelity.

## 1. Baseline

| Check | Result |
| --- | --- |
| `main` / `origin/main` | `150bef8dcfeeded416e1640cf0ee5ded696d57b0` |
| Tracked worktree | Clean (untracked `.superpowers/` + EXP-019 drafts preserved) |
| Private gallery | 14 cards; index `c9d4e73e…13d3`; manifest `6e9428a5…a4eb`; 13 rollbacks |
| CR-015 | Closed; no private writes |

## 2. Installed TransformationPack inventory

Source: `references/transformations/registry.json` · schema `data/schemas/transformation_pack.schema.json`.

| ID | Version | Source → target | Geometry (summary) | Depth (summary) | Surface mapping (summary) |
| --- | --- | --- | --- | --- | --- |
| `portrait_to_volumetric_sculpture` | 1.0.0 | portrait → volumetric_sculpture | 3D object with support/termination | camera shading → readable volume | continuous object surface, not living-face filter |
| `portrait_to_architectural_mural` | 1.0.0 | portrait → architectural_mural | fixed architectural plane | photographic depth → planar contour hierarchy | marks/losses share wall support |
| `portrait_to_relief_print` | 1.0.0 | portrait → relief_print | contour + bounded color regions on sheet | photographic modeling → graphic value hierarchy | marks impressed on sheet, not screen+paper texture |
| `portrait_to_decorated_artifact` | 1.0.0 | portrait → decorated_artifact | decoration constrained by object zones | depth → object-bound motif hierarchy | wrap/foreshorten with curvature; not flat decal |

Packs are representation-only: they do not embed era or material authority.

## 3. Compiler path: standard vs TransformationPack

### Activation

Lexicalization / TransformationPack path activates when `spec.transformation` is present and resolves via `resolve_transformation`.

### What is emitted on the TransformationPack path

| Section | Content |
| --- | --- |
| `transformation` | Literal `representation_delta.geometry` + `.depth` + `.surface_mapping` with `source → target` |
| `lexical_realization` | Realized concepts from ArtMethod/era/form `concept_refs` (core + authorized selected) |
| `lexical_avoid` | Avoid clauses for resolved concepts (when present) |
| `material_failure_checks` | ArtMethod `typical_generation_failures` (first three) |
| `artifact_form` / `artifact_state` | Form geometry + state text |
| `references` / `identity` | Role isolation + identity mode |

### What is suppressed on the TransformationPack path

| Omitted section | Notes |
| --- | --- |
| `art_method` (`prompt_fragments.core`) | Replaced by lexical realization when `concept_refs` exist |
| `material_behavior` (surface/edge prose) | Same |
| `era_*` selective anchors / fragments | Historical header may remain; selective era prose is suppressed while a transformation is active |
| TransformationPack `failure_modes` as prose | Carried in resolution object; **not** auto-copied into prompt (method failures still emit) |

### ArtMethod `concept_refs`

| Method | concept_refs | Transform-path material lexicalization |
| --- | --- | --- |
| `marble_sculpture` | yes | Positive marble/carved-stone lexical clauses |
| `bronze_sculpture` | **no** | Representation delta + bronze failure checks only; no positive cast/patina lexical section |
| `mineral_pigment_mural` | yes | Wall/plaster/mineral lexical clauses |
| `japanese_woodblock_print` | yes | Keyblock/color/registration lexical clauses |
| `blue_white_ceramic` | yes | Cobalt/glaze/zones/curvature lexical clauses |
| Other installed methods | mostly no | Compatible with TransformationPacks only if family gate allows |

Conditional omission of standard ArtMethod prose under TransformationPack is **intentional**. Absence of `concept_refs` on bronze is a **coverage gap**, not a silent failure of the representation-delta contract.

## 4. Integration ledger

| Pack | Method / form | Era example | Schema | Gate | Compiler | Geometry/Depth/Surface | Lexicalization | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| volumetric sculpture | marble / bust | classical_greek | PASS | PASS | PASS | all three in `transformation` | marble concepts | **PASS — REPRESENTATION TRANSFORMATION VERIFIED OFFLINE** + **PASS — CONDITIONAL LEXICALIZATION VERIFIED** |
| volumetric sculpture | bronze / bust | roman_imperial | PASS | PASS | PASS | all three emitted | empty concepts (no refs) | **PASS — REPRESENTATION TRANSFORMATION VERIFIED OFFLINE**; material lexicalization **PARTIAL** |
| architectural mural | mineral mural / wall_surface | dunhuang | PASS | PASS | PASS | all three | mural concepts; not buon fresco | **PASS — REPRESENTATION TRANSFORMATION VERIFIED OFFLINE** + **PASS — CONDITIONAL LEXICALIZATION VERIFIED** |
| relief print | woodblock / print_sheet | edo | PASS | PASS | PASS | all three | print concepts | **PASS — REPRESENTATION TRANSFORMATION VERIFIED OFFLINE** + **PASS — CONDITIONAL LEXICALIZATION VERIFIED** |
| decorated artifact | blue-white / vase | none or edo | PASS | PASS | PASS | all three | ceramic concepts; object-bound | **PASS — REPRESENTATION TRANSFORMATION VERIFIED OFFLINE** + **PASS — CONDITIONAL LEXICALIZATION VERIFIED** |

### Invalid configurations (real codes)

| Case | Code | Classification |
| --- | --- | --- |
| Wrong ArtMethod family for target | `transformation_method_incompatible` | **PASS — INVALID CONFIGURATION CORRECTLY BLOCKED** |
| Transformation without method/form | `transformation_requires_artifact` | **PASS — INVALID CONFIGURATION CORRECTLY BLOCKED** |
| Unknown pack ID | `unknown_transformation_pack` | **PASS — INVALID CONFIGURATION CORRECTLY BLOCKED** |
| Concept not available from selected packs | `unavailable_concept` | **PASS — INVALID CONFIGURATION CORRECTLY BLOCKED** |
| Non-portrait `source_representation` | `schema` | **PASS — INVALID CONFIGURATION CORRECTLY BLOCKED** |
| Form not in method compatibility | `art_form_incompatible` | **PASS — INVALID CONFIGURATION CORRECTLY BLOCKED** |

No confirmed production defect required stopping TIV-01.

## 5. Historical / reference / chaining

### Era combinations exercised

- Hellenistic Greek + marble freestanding statue + volumetric sculpture — transform + marble lexical; era header present; selective era anchors suppressed under transformation (existing V3.4 behavior).
- Roman Imperial + bronze bust + volumetric sculpture — transform emits; bronze does not collapse to marble lexical.
- Dunhuang + mineral mural — wall binding + mural lexical; site name in historical header.
- Edo + woodblock — print mechanism + registration lexical.
- Edo + blue-white vase — object-bound decoration remains distinct from living portrait language.

Genre overlays (Wuxia/Xianxia) are **not** TransformationPacks and were not reclassified here.

### Reference roles (existing contract)

Legal roles: `identity`, `pose`, `outfit`, `hairstyle`, `artifact`, `style`, `environment`, `layout`, `palette`.

Under TransformationPack compilation:

- Role isolation prose still emits.
- `recognizable_identity` can coexist with sculpture/mural/print/ceramic translation.
- Preservation of identity does **not** mean preserving living skin, photographic garment material, or a freestanding figure on a vase — representation delta + method failures/lexical clauses state the non-living target.
- Offline symbolic roles do **not** prove provider attachment or visual identity fidelity.

Missing for future architecture (not TIV-01 failures): dedicated pose/hair/wardrobe runtime controls beyond role labels; stronger explicit “preserve X / transform Y” matrices.

### Chained A→B→C feasibility

Request schema supports `references` + `transformation`, but **lacks** first-class fields for:

- derived-from / parent reference linkage
- prior generation original-byte SHA-256 on the reference object
- declared lineage between B and C inside the request

Gallery/import schemas elsewhere can record image SHA-256 and provenance for custody, yet that is not the same as a compiler request lineage contract.  
Classification: **UNSUPPORTED — CONTRACT NOT IMPLEMENTED** (enhancement), not a TIV-01 regression.

## 6. Test methodology and results

Module: `tests/test_transformation_integration_verification.py`

- Real schema validation, loaders, `lint_spec`, `compile_result`
- Semantic assertions on `transformation` / lexical / failure sections
- With-vs-without TransformationPack path comparison
- Representative era and reference-role cases
- Real rejection codes only
- Deterministic double-compile
- `generation_requested` remains false on candidates

Focused TIV-01 result at authorship: **25 passed**.  
TIV-01 + ISV-01 combined: **99 passed**.  
Full suite at authorship: **1286 passed, 13 skipped**.  
`validate_repo.py`: tracked registries/regressions OK; known untracked `.superpowers/` UTF-8 noise only.

Existing coverage retained: `tests/test_v34_transformations.py`, `tests/test_v34_lexicalization.py`, ISV-01 module.

## 7. Gaps and recommended next track

1. **Bronze (and other methods without `concept_refs`)** lack positive material lexicalization on the TransformationPack path — representation change still works. Smallest repair if desired: author `concept_refs` for `bronze_sculpture` (separate pack/lexicon gate).
2. **Reference-role / preservation architecture** remains the larger product gap for face+wardrobe/pose workflows and multi-step reuse.
3. **Chained transformation lineage** needs an explicit schema/compiler contract before A→B→C can be verified deterministically end-to-end.
4. **Visual validation** of the four packs remains unproven (offline ≠ image fidelity).

Recommended single next track after owner review: **reference-role/preservation architecture** if creative workflows are the priority; otherwise **bronze concept_refs** if completing sculpture material parity on the transform path is the priority. Do not start either from this document alone.

## 8. Changed paths (authorized)

1. `tests/test_transformation_integration_verification.py`
2. `docs/TIV_01_TRANSFORMATION_INTEGRATION_VERIFICATION.md`

No `docs/SESSION_HANDOFF.md`. No production, pack, schema, recipe, gallery, or CI changes.

## 9. Distinction reminder

| Claim | Status |
| --- | --- |
| Installed knowledge | Yes — four packs |
| Schema support | Verified |
| Compiler emission of representation delta | Verified offline |
| Offline verification | This document |
| Generated-image fidelity | **Not** claimed |
| Original-byte custody / provider attestation | **Not** claimed |
| Owner creative acceptance | **Not** claimed |
