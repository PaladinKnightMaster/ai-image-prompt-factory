---
name: ai-image-prompt-factory
description: Evidence-backed agentic image-prompt engineering skill for GPT Image 2. Converts plain-language visual requests and optional reference images into coherent production prompts using explicit locks, reference-role isolation, temporal-cultural evidence, art/craft/material reasoning, visual direction, compatibility audits, regression checks, evaluation, and surgical revision. Prompt generation is the primary output; image generation is optional.
---

# AI Image Prompt Factory V3.2

## Mission

Turn a short request into a **traceable visual production brief**, not a keyword pile. V3.2 should be able to answer internally: *what evidence influenced this decision, what is uncertain, and what would regress if the compiler changes?*

## Runtime sequence

1. **Task Classifier** — choose one primary route from `references/routes/registry.json`.
2. **Explicit Parameter Lock** — preserve user-specified facts unless unsafe/impossible.
3. **Reference Role Assignment** — assign only explicit roles from `references/core/reference_roles.json`.
4. **Route Selection** — load one primary route plus only necessary overlays.
5. **Context Detection** — load relevant era/site/genre pack(s), never all packs.
6. **Evidence Retrieval** — use `evidence/registry.json` to load only routed claim sets; keep source, claim, interpretation, and prompt implication separate.
7. **Compatibility Audit** — apply mode-sensitive evidence decisions and preserve uncertainty.
8. **Temporal-Cultural Gate** — resolve anachronisms, cross-cultural leakage, and unsupported certainty.
9. **Art/Craft Gate** — load one relevant art-method module and artifact form/state when applicable.
10. **Director Gate** — resolve moment, action, gaze, body weight, hands, prop interaction, spatial layers, motivated light, material response, and micro-story.
11. **Conflict Resolver** — follow `references/core/precedence.json`.
12. **GPT Image 2 Compiler** — compile compact / standard / extended natural-language production brief.
13. **Optional Generation / Editing** — only when explicitly requested/configured.
14. **Evaluation** — score independent axes; never substitute one beauty score for compliance/history/material/identity/technical defects.
15. **Regression Comparison** — distinguish semantic, prompt, and visual regression.
16. **Surgical Revision** — preserve successful dimensions and correct only failed dimensions.
17. **Case Promotion / Gallery** — package only with provenance and publication eligibility.

## Progressive disclosure

Load only what is needed. A Tang living portrait does not need every art method. An Edo Arita plate does not need ukiyo-e production logic unless the request actually combines them. A Dunhuang mural should not activate unrelated Tang cobalt evidence merely because both are Chinese historical contexts.

Evidence claim loading is routed by historical packs and art method, then filtered by meaningful trigger/context matching. Generic stopwords must never activate claims.

## Evidence rules

- **Source is not claim.** A museum object record can support existence/context; it does not dictate prompt prose.
- **Claim is not interpretation.** Record what the evidence supports separately from how the system visualizes it.
- **Interpretation is not certainty.** Preserve `canonical`, `well_attested`, `plausible`, `interpretive`, `rare`, `anachronistic`, `incompatible`, `unknown`.
- **Confidence needs provenance.** Never promote community prompt examples to historical authority.
- **Source conflicts remain visible.** Represent chronological/regional/scholarly variation rather than averaging it into fake certainty.
- **Evidence snapshots are immutable case context.** Golden cases pin claim IDs/versions and source IDs so later research cannot silently change old baselines.

## Historical strictness must change behavior

- `strict_reconstruction` — resolve or replace incompatible elements; aggressively qualify weak evidence.
- `historically_informed` — preserve strong anchors; adapt conflicts while retaining intent when possible.
- `period_drama` — allow familiar cinematic conventions, but classify them as adaptations rather than proof.
- `fantasy_hybrid` — allow deliberate mixture while keeping historical anchors and invented/later elements distinguishable.

Do not merely print the strictness label.

## Survival bias

Distinguish original appearance from present survival state. Examples include ancient sculpture polychromy, bronze survival/corrosion, faded mural pigments, textile loss, restoration, excavation, and museum conservation. Artifact state must materially alter the prompt.

## Reference roles

Allowed roles: `identity`, `pose`, `outfit`, `hairstyle`, `artifact`, `style`, `environment`, `layout`, `palette`.

A role is a permission boundary. Outfit does not import identity; layout does not alter identity; style does not import unrelated objects.

## Identity and body

Identity modes: `strict_identity`, `recognizable_identity`, `identity_inspired`, `identity_unlocked`.

Body modes: `preserve`, `presentation_only`, `creative_transformation`, `plausible_fitness_projection`, `artistic_stylization`.

Keep anatomy, pose, camera presentation, garment shaping, and stylization separate.

## Wuxia / Xianxia / Dunhuang

- Wuxia = genre overlay, not a dynasty.
- Xianxia = fantasy overlay, not historical evidence.
- Dunhuang = multi-century site/tradition; strict reconstruction needs a cave/subperiod or tightly bounded evidence family.

## Art and artifacts

Art method is independent from artifact form and state. Bronze is not marble with a material word swapped. Ukiyo-e is not a generic flat illustration. Blue-and-white ceramic is not “porcelain style”; map cobalt-under-glaze behavior to actual object geometry.

## Compiler discipline

Every sentence should control something visible or operational. Avoid camera-brand fetishism, repeated synonyms, meaningless “8K/masterpiece/best quality” stacks, and giant negative prompts. Prefer a readable visual contract.

## Evaluation and revision

Required independent axes:

- semantic compliance
- aesthetic quality
- historical/cultural integrity
- art/material fidelity
- identity fidelity where applicable
- technical defects

Use `evaluation/failure_taxonomy.json`. A revision must say what to preserve and what to change. Do not rewrite a successful identity/pose/composition because bronze patina failed.

## Sample-corpus hygiene

External sample images default to `unknown_license` + `metadata_only`. Hash/index them; do not redistribute them. Public gallery code must publish images only when a case/asset is explicitly eligible.

## Runtime modes

Run `python scripts/check_mode.py --json` when execution matters:

- **DIRECT_API** — explicit API configuration; compile first; execute only on request.
- **HOST_NATIVE** — host image tool exists; compile then delegate if requested.
- **ADVISOR** — prompt/audit only.

Never claim an image/evaluation/regression result that did not actually run.

## CLI

```bash
python scripts/validate_repo.py
python scripts/factory.py compile cases/golden/04-tang-court-lantern/case.json
python scripts/factory.py evidence cases/golden/04-tang-court-lantern/case.json
python scripts/factory.py audit cases/golden/04-tang-court-lantern/case.json
python scripts/factory.py diff old.json new.json
python scripts/run_regression.py
python scripts/build_baselines.py
python scripts/ingest_corpus.py /path/to/library.zip
python website/generate_gallery.py
```


## V3.2 empirical visual intelligence

Historical/material evidence and empirical prompt mechanisms are separate knowledge systems. Internal source examples may suggest VisualPatterns, but observed patterns are not automatically compiler-eligible. Load only validated, relevant patterns when `visual_patterns.enable_validated` or explicit pattern IDs request them. The internal corpus is development-time intelligence and must never be bulk-loaded for ordinary runtime requests.
