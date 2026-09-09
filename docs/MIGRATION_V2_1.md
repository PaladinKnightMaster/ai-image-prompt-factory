# V2.1 → V3.0 Migration Map

## Migrated directly or with small renaming

| V2.1 concept | V3 destination | Change |
|---|---|---|
| Reference roles | `references/core/reference_roles.json` | adds first-class `hairstyle`; makes role boundaries explicit |
| Identity policy | `references/core/identity_modes.json` | `free_generation` renamed `identity_unlocked` |
| Body transformation system | `references/core/body_modes.json` | same five core modes; axes explicitly separated |
| ChatGPT Images adapter | `references/core/gpt_image_2_adapter.json` | GPT Image 2 becomes primary adapter; prompt remains natural production brief |
| Prompt linter | `src/aipf/linting.py` | keeps high-value rules, adds era/art/form gates |
| Evaluation + surgical revision | `evaluation/` + `src/aipf/evaluation.py` | re-centered on V3 failure classes and independent evaluation axes |
| Pose library concepts | `references/poses/core_poses.json` | curated mechanics only; no long finished prompts |
| Hair library concepts | `references/hair/core_hair.json` | family + control dimensions rather than prompt catalog |
| Outfit ontology | `references/wardrobe/assembly_rules.json` | construction/layering + historical precedence |
| Scene/environment patterns | `references/environments/core_environments.json` | compact scene stack and reusable presets |

## Replaced rather than migrated

- `china_dynasty_foundation` → separate Han/Tang/Song/Ming/Qing packs with common schema.
- broad cultural style packs → era/site/genre packs with compatibility and confidence labels.
- old artifact recipes → art method + artifact form + artifact state composition.
- workflow-specific duplicate prompt files → route registry + semantic spec + compiler.
- separate gallery/benchmark prompt copies → case records as the source of truth.

## Intentionally not migrated

- old Custom GPT installation hierarchy;
- V2.1-only conversation starters;
- large prompt bodies that duplicate structured knowledge;
- generic camera brand presets whose only purpose is “premium” wording;
- body ideals or face-reshaping defaults;
- style recipes that do not yet have a distinct material/process model;
- benchmarks that cannot be reproduced without their exact output/reference assets.

## Compatibility note

V3.0 does not promise schema-level backward compatibility with V2.1. A compatibility layer would preserve accidental architecture and slow the transition to era/art/material composition. If V2.1 import becomes important, it should be added in V3.1 as an explicit converter that maps old records into the V3 semantic schema.
