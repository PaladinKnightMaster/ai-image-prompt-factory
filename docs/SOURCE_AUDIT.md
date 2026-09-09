# Source Audit

## Attached package inventory

The V3 build inspected the extracted contents of all three project packages rather than treating their filenames as sufficient evidence.

| Source | Files inspected | Images | Text/Markdown | Primary value |
|---|---:|---:|---:|---|
| `gpt-image-2-1.0.4` | 103 | 0 | 97 | installable skill structure, runtime modes, progressive references, generation/edit scripts, template methodology |
| `AI_Image_Prompt_Factory_v2_1_ChatGPT_Install_Kit` | 59 | 0 | 24 | semantic request schema, reference roles, identity/body controls, adapter, guardrail/linter, evaluation/revision |
| upgraded `Image Library` | 642 | 606 | 36 | visual/prompt mining corpus, hairstyle/pose/outfit systems, transformation patterns, artifact concepts, sample-output evidence |

### `gpt-image-2-1.0.4`

Observed root components:

- `SKILL.md`
- `manifest.json`
- `scripts/check-mode.js`
- `scripts/generate.js`
- `scripts/edit.js`
- `scripts/shared.js`
- `references/prompt-writing.md`
- category directories under `references/` containing narrowly scoped template Markdown files.

The most valuable structural idea is that the root skill contains runtime behavior and an index while detailed prompt knowledge is loaded progressively. Its prompt-writing guide also correctly argues that structured JSON is useful for complex layouts/multi-region outputs but should not be forced onto every simple single-subject image.

### V2.1 install kit

Observed structured knowledge includes:

- `reference_roles`
- `identity_policy`
- `body_transformation_system`
- `pose_library`
- `hair_library`
- `outfit_ontology`
- `cultural_traditions_v2`
- `china_dynasty_foundation`
- `transformation_workflows`
- `prompt_lint_rules` / `prompt_lint_rules_v2_1`
- camera/light/layout profiles
- GPT Image adapter
- evaluation and revision records
- JSON schemas and compiler/benchmark assets.

The V2.1 request schema already separates reference roles and contains the five requested body modes. The strongest reusable product insight is semantic separation, not its packaging hierarchy.

### Upgraded Image Library

The library now contains 606 sample-output images grouped under:

- `SAMPLE_OUTPUT/APC` — 100 images
- `SAMPLE_OUTPUT/FSC` — 24 images
- `SAMPLE_OUTPUT/GAC` — 33 images
- `SAMPLE_OUTPUT/LAC` — 71 images
- `SAMPLE_OUTPUT/LCC` — 378 images

High-value Markdown sources include:

- `100 Hairstyle-Led Prompts for Realistic Gravure.md`
- `Gravure-style Posing Prompt Collection.md`
- `100 Finished Japanese Gravure-Style Prompts.md`
- `OWN_Ancient Greece_Roman Age Studio Prompts.md`
- `OWN_Wuxia Historic Drama Studio Shot.md`
- `OWN_Transform Workflow Prompts.md`
- `Grand Masterpiece Artwork Prompt Kit.md`
- `Historical Scene Artwork.md`
- `SP_Paper-cut bas-relief artwork Prompt.md`
- `SP_Luxury Watercolor Illustration.md`
- `image-style-extraction-prompt-kit.md`
- multiple fashion/game/marketing/layout collections.

V3 intentionally mines **mechanics and vocabulary**, not long prompts. The sample images are not shipped in the runtime ZIP because 606 images would undermine progressive disclosure and create a false implication that aesthetic success equals historical/material validation.

## Migration filter

A source concept is migrated only if it passes all three tests:

1. it is reusable across multiple cases;
2. it can be expressed as a testable control or structured fact;
3. it does not require copying a large original prompt to retain value.

That filter is why pose mechanics, reference isolation, body modes, art-material behavior and evaluation survive, while long standalone “finished prompts” do not.
