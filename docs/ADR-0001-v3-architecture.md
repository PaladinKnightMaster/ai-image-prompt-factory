# ADR-0001 — V3 Architecture: Prompt Compiler, Not Prompt Warehouse

**Status:** Accepted for V3.0  
**Date:** 2026-09-07

## Decision

V3 is a small installable skill backed by progressively loaded, structured modules. Its canonical output is a GPT Image 2 production prompt. Image generation, editing, evaluation, and gallery packaging are downstream workflows rather than assumptions baked into every request.

The runtime pipeline is:

```text
User Request
→ Task Classifier
→ Explicit Parameter Lock
→ Reference-Image Role Assignment
→ Route Selection
→ Historical/Cultural Context Detection
→ Temporal-Cultural Gate
→ Art/Craft Gate
→ Director Gate
→ Conflict Resolver
→ GPT Image 2 Compiler
→ Optional Generation
→ Result Evaluator
→ Surgical Revision
→ Optional Gallery Case Packaging
```

## What we adopt

### From `gpt-image-2-1.0.4`

Adopt:

- a deliberately small root `SKILL.md`;
- runtime-mode detection before execution;
- progressive disclosure through narrowly scoped reference modules;
- separate generate/edit scripts;
- a clear prompt-writing methodology that distinguishes simple natural-language tasks from highly structured/layout-heavy tasks;
- package manifest and installable skill shape.

Modify:

- V3 is **prompt-first**, so runtime detection controls optional execution, not whether prompt compilation occurs;
- category templates become routes + composable knowledge modules rather than dozens of independent final prompts;
- JSON is the internal semantic representation, while final output is normally natural-language production prose.

Reject:

- a large template catalog as the organizing center of the product;
- asking for missing fields merely because a template contains them—V3 asks only when ambiguity changes the result materially.

### From AI Image Prompt Factory V2.1

Adopt:

- explicit reference roles;
- identity-mode controls;
- body-transformation modes and separation of anatomy/pose/camera/garment/stylization;
- transformation workflows;
- prompt linting and guardrail concepts;
- evaluation scorecards, failure classification, and surgical revisions;
- GPT Image production-brief compilation and compact/standard/extended profiles;
- pose/hair/outfit concepts as modular visual controls.

Modify:

- `free_generation` becomes the clearer `identity_unlocked`;
- `hairstyle` becomes an explicit reference role in addition to V2.1’s original role set;
- historical reasoning changes from broad cultural packs into first-class era/site/overlay modules with explicit compatibility values and evidence confidence;
- evaluation axes are consolidated around the V3 product differentiators rather than using one long universal checklist;
- V2.1’s Custom GPT installation/docs hierarchy is no longer the architecture.

Reject:

- keeping V2.1 file layout for backward compatibility;
- migrating every V2.1 modern style recipe or benchmark prompt;
- duplicate sources of truth between Custom GPT uploads, developer JSON, gallery records, and prose docs.

### From the upgraded Image Library

Adopt as distilled knowledge:

- named pose mechanics and hand/body logic;
- hairstyle taxonomy and controllable hairstyle variables;
- outfit construction/layering patterns;
- transformation patterns such as artifact conversion, watercolor memory, paper craft, historical restaging, and modern museum encounters;
- design-system thinking for posters, grids, storyboards, and reference-role composition;
- successful sample outputs as future evidence for regression/golden-case curation.

Reject:

- copying long source prompts into the runtime;
- treating visual examples as proof of historical accuracy;
- including the 606 sample images in the minimal V3 runtime package.

### From `female-portrait-director` / `female-outfit-director`

Adopt:

- small root workflow;
- explicit loading order;
- registries for selecting only the needed route/tool/style module;
- core rules inherited by specialized routes;
- separate reference-image lock logic from styling logic.

Modify:

- V3 is subject-agnostic rather than female-portrait-specific;
- the main router selects semantic task routes plus era/art modules rather than one portrait aesthetic;
- style selection cannot outrank historical/artifact compatibility.

Reject:

- assuming portrait/outfit direction is the top-level product abstraction.

Reference projects:

- https://github.com/liyue-aigc/female-portrait-director
- https://github.com/liyue-aigc/female-outfit-director

### From Garden `gpt-image-2`

Adopt runtime portability and explicit generation/edit paths. The attached 1.0.4 package is the primary implementation reference; the live repository is useful for current structure comparison.

- https://github.com/ConardLi/garden-skills/tree/main/skills/gpt-image-2

### From gallery/prompt-library projects

`awesome-gpt-image-2`, YouMind, EvoLink, and related collections are strongest as galleries, prompt discovery systems, and example corpora. V3 borrows their **case/data separation** and sample-linking ideas, but not prompt volume as the product center.

- https://github.com/freestylefly/awesome-gpt-image-2
- https://github.com/YouMind-OpenLab/ai-image-prompts-skill
- https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts
- https://github.com/wuyoscar/GPT-Image2-Skill
- https://github.com/TanShilongMario/PromptSkill4image

## What makes V3 unique

The differentiator is a **compatibility-aware visual compiler**. V3 reasons about whether visible elements belong together before polishing them aesthetically.

The architecture explicitly separates:

- user facts from defaults;
- identity from body transformation;
- reference roles from reference content;
- historical era from genre overlay;
- historical era from art method;
- art method from artifact form;
- artifact form from artifact state;
- factual confidence from visual desirability;
- scene direction from keyword decoration;
- prompt compilation from image execution;
- evaluation from revision.

This prevents common failure patterns that a prompt collection cannot solve: an Edo layout silently importing a face, a Tang portrait borrowing Qing rank dress, “Dunhuang” becoming one generic timeless costume, marble behaving like bronze with a material word swapped, or a reference image overwriting body/identity without permission.

## Why registries + structured JSON

Canonical modules are JSON because they must be independently testable, machine-readable, reusable by the compiler/evaluator/gallery, and able to preserve evidence/confidence. Human-readable Markdown explains the system but does not redefine data.

The final GPT Image 2 prompt remains natural language because a production brief is easier for users to inspect, edit, and execute than a nested machine schema.

## Progressive-disclosure invariant

A normal request should load:

1. core locks/precedence;
2. one route;
3. zero to two historical/site/genre packs;
4. zero or one primary art method;
5. artifact form/state only when needed;
6. only the relevant pose/hair/wardrobe/environment helper if needed.

Loading all 13 era packs or all 12 art methods for a single prompt is an architectural failure.

## Known V3.0 tradeoffs

- Initial era packs are research-backed foundations, not exhaustive costume encyclopedias.
- Compatibility checking is currently rule/registry based; it does not yet have a dense pairwise ontology of every object × period × region combination.
- Direct API execution is deliberately conservative and dry-run by default.
- Automated vision scoring is not bundled; host-native evaluators can consume the evaluation schema, while the local CLI generates score summaries/revision prompts from recorded observations.
- Gallery cases are specs first. Final generated images are intentionally optional in V3.0.
