# EIT-01 — Era-Informed Transformation Integrity

**Status:** Compatibility-safe compiler enhancement (PR track)  
**Engineering baseline:** `6c03fe484070211eb1a1998019169f4090bba68f`  
**Feature branch:** `feat/eit-01-era-informed-transformation`  
**Date:** 2026-11-12  

TIV-01 confirmed that TransformationPack compilation retained a historical header while suppressing selective EraPack anchors and method-specific fragments (`if not transformation:`). That suppression was intentional V3.4 behavior. EIT-01 is a controlled enhancement, not an unexplained regression repair.

Compiler emission does **not** establish generated-image fidelity or historical authenticity. This track does not claim that all historical eras, mythologies, or fantasy worlds have been visually tested.

## 1. Original suppression behavior

On the TransformationPack path, the compiler previously:

| Emitted | Suppressed |
| --- | --- |
| Historical header (`historical`) | Selective `era_*` anchors (wardrobe, hairstyle, architecture, textiles, lighting) |
| Representation delta | Method-matched `era_fragment_*` prose |
| Lexical realization / avoid | ArtMethod `prompt_fragments.core` and material-behavior prose |
| Compatibility lead (without accepted-claim restatement) | Survival-bias legacy prose |
| Overlay fragments | — |

Affected combinations include any request that pairs an installed EraPack with one of the four TransformationPacks. Existing compatibility, evidence, and concept-selection gates remained active for lexicalization; only EraPack narrative fragments were blanked.

## 2. Compatibility problem addressed

Representation transforms still need era-specific **method-matched** guidance (sculptural torque, bust truncation, wall-bound mural restraint, ceramic tradition warnings) without:

- injecting living-scene wardrobe/architecture anchors onto sculptures, prints, walls, or vessels;
- falling back to the first available EraPack fragment;
- bypassing conditional craft-process concept gates (bokashi, polychromy, pouncing);
- silently rewriting frozen Creative Recipe prompts.

## 3. Chosen rule

Under an active TransformationPack:

1. **Keep** the historical header, overlays, hybrids, representation delta, form/state, lexicalization, and failure checks.
2. **Keep suppressing** selective `era_*` living-scene anchors.
3. **Emit** `_era_fragment(...)` only when the existing method/route/occasion preference matches an installed fragment key (no arbitrary fallback).
4. **Additionally withhold** a matched fragment when it contains the preferred term of an **unselected** conditional lexicon concept whose domain is `craft_process` (evidence precedence vs. V3.4 concept selection).
5. Stamp transformation compilations as **`compiler_version = 3.4.1`** (standard path remains `3.2.0`).

### Precedence

1. TransformationPack representation delta and ArtMethod/form lexicalization remain primary material authority.
2. Method-matched EraPack fragment adds era-specific representation guidance when evidence-compatible.
3. Unselected craft-process vocabulary in a fragment blocks that fragment until the concept is explicitly selected.
4. If no suitable fragment exists, retain header + existing constraints; do not invent prose.

## 4. Alternatives rejected

| Alternative | Why rejected |
| --- | --- |
| Restore all selective anchors under transformation | Violates Rule C; living-scene wardrobe/architecture on nonliving targets |
| First-available fragment fallback | Violates Rule B (e.g., Classical `living` on a bust) |
| Emit ukiyoe fragment always for Edo prints | Injects unselected `bokashi` and breaks V3.4 conditional-leak regression |
| New schema opt-in / major version architecture | Unnecessary: frozen CR transforms are era-empty; scoped `3.4.1` suffices |
| Hard-coded era prose in the compiler | Violates Rule E; packs remain the source of truth |
| EraPack / ArtMethod content edits | Out of EIT-01 authorization |

## 5. Representative outcomes

| Case | Era / method / transform | Fragment outcome |
| --- | --- | --- |
| E1 | Hellenistic + marble + volumetric sculpture | Emits sculpture fragment (torque/weight/support) |
| E2 | Roman Imperial + bronze + volumetric sculpture | Emits bust fragment; no marble-carving substitution; bronze lexical gap unchanged |
| E3 | Dunhuang + mineral mural + architectural mural | Emits mural fragment; strict narrowing gate preserved; no pouncing/buon fresco |
| E4 | Edo + woodblock + relief print | Header + print lexicalization; ukiyoe fragment withheld until `woodblock.bokashi` selected |
| E5 | Edo + blue-white ceramic + decorated artifact | Emits ceramic fragment; not print language; warns against Ming Jingdezhen import |

## 6. Negative controls

Verified against real installed codes/behavior:

- No living-portrait fragment on Classical sculpture transforms
- No selective wardrobe/architecture anchors on busts
- No Edo print fragment substituted onto ceramic
- No polychromy without evidence/selection
- Dunhuang `dunhuang_strict_narrowing` still errors under strict mode without subperiod
- Wuxia remains an overlay, not a historical era fragment
- `transformation_method_incompatible` still blocks wrong families
- No era sections when packs are empty
- Tang living fragment is not used as sculpture fallback
- `generation_requested` remains false on EIT inputs
- Standard non-transformation compilation unchanged (`compiler_version` 3.2.0)

## 7. Versioning and frozen-output impact

| Class | Impact |
| --- | --- |
| Creative Recipes with TransformationPacks (CR-004/005/007/012) | `packs=[]` → **prompt digests unchanged**; receipt `compiler_version` moves `3.4.0` → `3.4.1` |
| Golden / regression baselines | No TransformationPack+EraPack frozen prompt rewrites |
| Candidate cases (`v34-*`) | Test-only; may gain method-matched fragments where evidence allows |
| Standard path | Unchanged |
| TIV-01 historical report | Preserved as record of pre-EIT suppression; one obsolete assertion updated |

No frozen CR prompt text was edited. No golden expected-prompt snapshots were overwritten.

## 8. Prompt sections affected

Added under transformation when authorized: `era_fragment_<era_id>`.

Unchanged suppression: `era_<era_id>` selective anchors, ArtMethod core/material-behavior prose on the transformation path.

## 9. Remaining limitations

- Edo woodblock `ukiyoe` fragment remains gated on explicit `woodblock.bokashi` selection because the installed fragment text includes that craft-process term.
- Bronze sculpture still lacks positive `concept_refs` lexicalization (known coverage gap; not repaired here).
- Compiler emission ≠ image fidelity or authenticated reconstruction.
- Genre/fantasy overlays are not historical eras and were not reclassified.
- No new EraPacks, TransformationPacks, schema fields, or gallery/CR mutations.

## 10. Tests

- `tests/test_era_informed_transformation.py` — E1–E5, negatives, determinism, frozen recipe digests, version stamp
- `tests/test_transformation_integration_verification.py` — anchor-path assertion narrowed for EIT-01
