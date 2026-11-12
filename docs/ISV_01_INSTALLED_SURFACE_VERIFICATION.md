# ISV-01 — Installed Surface Verification

**Status:** Offline verification complete (test-only PR track)  
**Engineering baseline:** `278f448494c9f553a2d358d8fe376fea8b7de85f` (`main` = `origin/main`)  
**Feature branch:** `test/isv-01-installed-surface-verification`  
**Date:** 2026-11-11  

This report verifies that every installed ArtMethodPack and EraPack can be exercised through a valid existing runtime path, that distinctive instructions survive compilation, and that incompatible requests are rejected or adapted by established policy. It does **not** generate images, edit packs, or change compiler behavior.

## 1. Baseline

| Check | Result |
| --- | --- |
| Local `main` / `origin/main` / branch base | `278f448494c9f553a2d358d8fe376fea8b7de85f` |
| Tracked worktree at branch creation | Clean (untracked only: `.superpowers/`, EXP-019 drafts — preserved) |
| Private gallery accepted cards | 14 (`index_manifest.json` `candidates`) |
| Gallery `index.html` SHA-256 | `c9d4e73e1322192004a86d64dc55efc59758bacd37c4622fcba53a95f82913d3` |
| Gallery `index_manifest.json` SHA-256 | `6e9428a58593d766e4fbc6e5134b66bf78e5e30b6608809e6f9eda52bdefa4eb` |
| Rollback epochs | 13 |
| Private artifact modification | None |

CR-015 remains formally closed. No Creative Recipes or images were created in this track.

## 2. Installed registry inventory (verified)

### ArtMethodPacks — 12

| ID | Version | Family | Representative form | Route used |
| --- | --- | --- | --- | --- |
| `marble_sculpture` | 1.1.0 | sculpture | `free_standing_statue` | `artifact_transform` |
| `bronze_sculpture` | 1.1.0 | sculpture | `bust` | `artifact_transform` |
| `carved_stone_relief` | 1.0.0 | sculpture | `relief` | `artifact_transform` |
| `chinese_ink_painting` | 1.0.0 | painting | `scroll` | `art_style_transform` |
| `gongbi_painting` | 1.0.0 | painting | `scroll` | `art_style_transform` |
| `mineral_pigment_mural` | 1.1.0 | painting_on_wall | `wall_surface` | `art_style_transform` |
| `watercolor` | 1.0.0 | painting | `album_leaf` | `art_style_transform` |
| `japanese_woodblock_print` | 1.1.0 | printmaking | `print_sheet` | `art_style_transform` |
| `blue_white_ceramic` | 1.1.0 | ceramic_decoration | `vase` | `artifact_transform` |
| `manuscript_miniature` | 1.0.0 | painting_on_parchment | `book_page` | `art_style_transform` |
| `paper_cut_layered` | 1.0.0 | paper | `popup_diorama` | `art_style_transform` |
| `embroidery_textile` | 1.0.0 | textile | `folding_screen` | `art_style_transform` |

Source: `references/art-methods/registry.json` (schema `data/schemas/art_method.schema.json`).

### EraPack registry — 13

| ID | Version | Pack type |
| --- | --- | --- |
| `han` | 1.0.0 | `historical_era` |
| `tang` | 1.1.0 | `historical_era` |
| `song` | 1.0.0 | `historical_era` |
| `ming` | 1.1.0 | `historical_era` |
| `qing` | 1.0.0 | `historical_era` |
| `dunhuang` | 1.1.0 | `site_tradition` |
| `wuxia` | 1.0.0 | `genre_overlay` |
| `xianxia` | 1.0.0 | `fantasy_overlay` |
| `heian` | 1.0.0 | `historical_era` |
| `edo` | 1.1.0 | `historical_era` |
| `classical_greek` | 1.1.0 | `historical_era` |
| `hellenistic_greek` | 1.1.0 | `historical_era` |
| `roman_imperial` | 1.1.0 | `historical_era` |

Source: `references/eras/registry.json` (schema `data/schemas/era_pack.schema.json`).

## 3. Test methodology

- Module: `tests/test_installed_surface_verification.py`
- Approach: smallest representative valid specs; real `lint_spec` + `compile_result`; semantic substring assertions on emitted sections
- Non-transformation path used so ArtMethod `prompt_fragments.core`, `surface_behavior`, `edge_behavior`, and top failure checks are exercised (V3.4 TransformationPack lexicalization is out of scope for these positive method-emission checks)
- No whole-prompt golden snapshots were added; existing golden baselines were not rewritten
- No image generation or provider calls

## 4. Compiler emission contract (observed)

On the standard non-transformation path, the compiler emits:

| Pack / artifact field | Emission |
| --- | --- |
| `name` + `prompt_fragments.core` | `art_method` section |
| `surface_behavior` + `edge_behavior` | `material_behavior` section |
| `typical_generation_failures` (first 3) | `material_failure_checks` |
| Artifact form / state registry text | `artifact_form` / `artifact_state` |
| `evaluation_criteria` | **Conditional** — `extended` profile `audit_notes` only |
| `concept_refs` | **Conditional** — TransformationPack / lexical path only |
| `material`, `fabrication_process`, `visible_production_marks`, `mark_making`, `color_behavior`, `composition_behavior`, `structural_limitations`, `aging_weathering`, `artifact_compatibility`, `sources`, `scope_note` | **Not emitted as prose** — metadata / gate / evaluation inputs |

Non-emission of metadata or evaluation-reserved fields is **not** classified as an implementation defect. Classification uses the ledger vocabulary below.

## 5. ArtMethod field-to-emission ledger

| ID | Schema / loader | Compiler | Distinctive emission | Non-emitted (intentional / conditional) | Classification | Coverage |
| --- | --- | --- | --- | --- | --- | --- |
| `marble_sculpture` | PASS | PASS | carved stone masses; crystalline stone; polish hierarchy | fabrication list, sources, eval (standard) | **PASS — VERIFIED EMISSION** | Existing golden/regression + ISV-01 |
| `bronze_sculpture` | PASS | PASS | cast copper-alloy; patina; metal reflection | same family of meta fields | **PASS — VERIFIED EMISSION** | Existing + ISV-01 |
| `carved_stone_relief` | PASS | PASS | backing plane; relief depth; carved hierarchy | same | **PASS — VERIFIED EMISSION** | ISV-01 (new positive path) |
| `chinese_ink_painting` | PASS | PASS | brush/ink dilution; absorbent paper; blank space | same | **PASS — VERIFIED EMISSION** | Existing CR-014 / Song cases + ISV-01 |
| `gongbi_painting` | PASS | PASS | fine contour; layered color; controlled edges | same | **PASS — VERIFIED EMISSION** | Existing CR-013 + ISV-01 |
| `mineral_pigment_mural` | PASS | PASS | prepared wall; mineral/plaster; mural composition; not buon fresco | same; “fresco” appears only as failure avoidance (`digital fresco filter`) | **PASS — VERIFIED EMISSION** | Existing Dunhuang golden + ISV-01 |
| `watercolor` | PASS | PASS | transparent washes; reserve light; granulation; paper tooth / capillary edges | fabrication list; living-portrait form unsupported | **PASS — VERIFIED EMISSION** | ISV-01 (new; offline only — **no image validation**) |
| `japanese_woodblock_print` | PASS | PASS | carved-and-printed; registration; bokashi; keyline | same | **PASS — VERIFIED EMISSION** | Existing Edo / CR-012 + ISV-01 |
| `blue_white_ceramic` | PASS | PASS | cobalt under glaze; ceramic curvature; firing/glaze logic | same | **PASS — VERIFIED EMISSION** | Existing Edo ceramic + ISV-01 |
| `manuscript_miniature` | PASS | PASS | manuscript page; parchment; tempera/gold as page object | not a standalone tempera pack; culture-specific optional detail not fabricated | **PASS — VERIFIED EMISSION** | ISV-01 (new positive path) |
| `paper_cut_layered` | PASS | PASS | cut planes; layer thickness; cast shadows; negative space | same | **PASS — VERIFIED EMISSION** | Existing CR-015 + ISV-01 |
| `embroidery_textile` | PASS | PASS | stitch direction; thread; textile ground; printed-fabric failure check | same | **PASS — VERIFIED EMISSION** | ISV-01 (new positive path) |

**PARTIAL note (all methods):** knowledge fields listed in §4 that are not prose-emitted remain available for gates/evaluation. Classified as intentional compiler scope, not silent omission of the method-defining contract. Method-defining contract for this track = core fragment + surface/edge (+ failure checks).

## 6. Era / overlay ledger

| ID | Type | Tested context | Strictness / compatibility | Emission | Classification |
| --- | --- | --- | --- | --- | --- |
| `han` | historical_era | living portrait | historically_informed | anchors + historical header | **PASS — VERIFIED EMISSION** |
| `tang` | historical_era | living portrait + lantern occasion | historically_informed | anchors + lantern fragment | **PASS — VERIFIED EMISSION** |
| `song` | historical_era | ink + scroll | historically_informed | anchors + ink fragment with method | **PASS — VERIFIED EMISSION** |
| `ming` | historical_era | living portrait | historically_informed | anchors | **PASS — VERIFIED EMISSION** |
| `qing` | historical_era | living portrait | historically_informed | anchors + court fragment | **PASS — VERIFIED EMISSION** |
| `heian` | historical_era | living portrait | historically_informed | anchors + court fragment | **PASS — VERIFIED EMISSION** |
| `edo` | historical_era | woodblock + print_sheet | historically_informed | anchors + ukiyoe fragment | **PASS — VERIFIED EMISSION** |
| `classical_greek` | historical_era | living portrait | historically_informed | living fragment explicitly rejects marble unless method is sculpture | **PASS — VERIFIED EMISSION** |
| `hellenistic_greek` | historical_era | marble statue | historically_informed | sculpture fragment + marble method | **PASS — VERIFIED EMISSION** |
| `roman_imperial` | historical_era | bronze bust | historically_informed | bust fragment + bronze method | **PASS — VERIFIED EMISSION** |
| `dunhuang` | site_tradition | Tang + mural + subperiod | historically_informed OK; strict without subperiod → `dunhuang_strict_narrowing` | mural fragment + site anchors | **PASS — VERIFIED EMISSION** / gate **PASS — VALIDLY BLOCKED** |
| `wuxia` | genre_overlay | Ming + period_drama | requires base era | overlay prose + Ming anchors | **PASS — VERIFIED EMISSION** |
| `xianxia` | fantasy_overlay | Tang + fantasy_hybrid | requires base era; not a historical period | overlay prose + hybrids | **PASS — VERIFIED EMISSION** |

## 7. Cross-domain combinations

| # | Combination | Result |
| --- | --- | --- |
| 1 | Classical Greek living portrait vs marble sculpture | Living omits `art_method`; living fragment warns against marble unless sculpture method; marble emits carved-stone method | PASS |
| 2 | Hellenistic Greek + marble | Compiles; Hellenistic anchors + marble emission | PASS |
| 3 | Roman Imperial + bronze | Compiles; bronze cast/patina distinct from marble | PASS |
| 4 | Ming + Wuxia | Compiles under `period_drama`; genre overlay emitted | PASS |
| 5 | Tang + Xianxia fantasy_hybrid | Compiles; overlay + intentional hybrids | PASS |
| 6 | Edo + Japanese woodblock | Compiles; registration/bokashi present | PASS |
| 7 | Song + Chinese ink | Compiles; ink method + Song anchors | PASS |
| 8 | Dunhuang + mineral mural + site subperiod | Compiles with `aged` wall_surface | PASS |
| 9 | Contemporary portrait as watercolor | **Supported via `album_leaf`**, not a living-portrait form (watercolor `artifact_compatibility` has no living form) | PASS — valid adapted path |
| 10 | Contemporary paper-cut | `popup_diorama` compiles with layer/shadow semantics | PASS |
| 11 | Manuscript + embroidery surfaces | Both compile on declared forms | PASS |
| 12 | Incompatible: Wuxia-only / Xianxia-only / watercolor+statue / Dunhuang strict without subperiod | `genre_as_era`, `art_form_incompatible`, `dunhuang_strict_narrowing` | **PASS — VALIDLY BLOCKED** |

## 8. Confirmed gaps and limitations (not blocking ISV-01)

1. **Offline ≠ visual validation.** Watercolor, embroidery, manuscript, relief, and other methods have **no** generated-image evaluation in this track. Do not infer provider fidelity from compiler emission.
2. **Uneven prior creative coverage.** Several installed methods (e.g. watercolor, embroidery, manuscript, carved relief) lacked dedicated positive regression paths before ISV-01; ISV-01 adds offline coverage only.
3. **Authoring taxonomies** that are not runtime-loaded remain out of inventory (unchanged).
4. **TransformationPack lexical path** is separately gated; ISV-01 positive ArtMethod emission tests intentionally use the non-transformation path where core fragments emit.
5. **No production defects** requiring compiler/pack edits were found that block this verification PR. Remaining “PARTIAL” items are intentional non-prose fields under the current compiler contract.

## 9. Unsupported / blocked scenarios (documented, expected)

- Overlay-only historical packs (`wuxia`, `xianxia`) without a base era/region → `genre_as_era`
- Dunhuang `strict_reconstruction` without `subperiod` → `dunhuang_strict_narrowing`
- Art method + incompatible artifact form → `art_form_incompatible`
- Watercolor as a freestanding living-portrait artifact form → unsupported by pack compatibility; use paper forms (`album_leaf`, etc.)

## 10. Recommended next fixes (not authorized here)

Smallest evidence-justified follow-ups:

1. Controlled offline-to-image experiment for watercolor (and/or embroidery/manuscript) if visual fidelity is the next risk.
2. Optional compiler enhancement to emit selected fabrication/mark fields when evaluation demands them (separate authorization; would be production compiler change).
3. Broader Hellenistic sculpture / Wuxia combination **image** evaluation if empirical claims are needed (ISV-01 already covers offline emission).

Do not begin those tasks from this document alone.

## 11. Validation commands

```text
python -m pytest -q tests/test_installed_surface_verification.py
python -m pytest -q
python scripts/validate_repo.py
```

ISV-01 focused result at authorship: **74 passed**.

Full suite at authorship: **1261 passed, 13 skipped** (`python -m pytest -q`).

`python scripts/validate_repo.py`: registries/modules/regressions OK (`art_methods` 12, `era_packs` 13, regression 19/19). Local `ok: false` solely from the known unrelated untracked `.superpowers/` invalid JSON files — preserved, not deleted. Tracked-source validation otherwise clean.

Preserve untracked `.superpowers/` and EXP-019 drafts; do not delete user files to force a green local `validate_repo` scan of untracked trees.

## 12. Changed paths (authorized)

- `tests/test_installed_surface_verification.py`
- `docs/ISV_01_INSTALLED_SURFACE_VERIFICATION.md`

No other tracked files. In particular, `docs/SESSION_HANDOFF.md` is **not** an authorized ISV-01 change and must remain identical to approved main.

No changes under `src/aipf/`, `references/`, `compatibility/`, `data/schemas/`, `recipes/`, golden outputs, gallery, or CI workflows.
