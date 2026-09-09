# V3.2 External Architecture Re-check

Audit date: 2026-09-07. These notes document architectural inspiration and target-model verification; they do not copy third-party repository content.

## GPT Image 2 target

OpenAI's current model documentation identifies `gpt-image-2` as the primary state-of-the-art image generation/editing model and lists the snapshot `gpt-image-2-2026-04-21`. V3.2 therefore continues to optimize one adapter deeply, records alias and snapshot separately when known, and does not invent unsupported generation controls.

Source: https://developers.openai.com/api/docs/models/gpt-image-2

## Female Portrait Director

The current public project continues to favor bounded tools/registries, explicit parameter locks, conflict handling, and progressive loading. V3.2 adopts the principle that a tool or pattern must have a bounded job, but uses empirical VisualPatterns and historical/material evidence rather than a portrait-style menu as the main knowledge abstraction.

Sources:
- https://github.com/liyue-aigc/female-portrait-director
- https://github.com/liyue-aigc/female-outfit-director

## Garden GPT Image 2 skill

The current Garden skill keeps runtime detection and separates local/API execution, host-native generation, and advisor/prompt-only behavior. V3.2 preserves compile-before-execute and optional generation; the new experiment lab remains useful offline.

Source: https://github.com/ConardLi/garden-skills/tree/main/skills/gpt-image-2

## awesome-gpt-image-2

The repository continues to emphasize Prompt-as-Code, atomic structured semantics, and reusable cases. V3.2 borrows the composability principle but makes a stronger epistemic distinction: collected examples are observations; only controlled first-party experiments can move a causal prompt mechanism toward validated compiler knowledge.

Source: https://github.com/freestylefly/awesome-gpt-image-2

## V3.2 differentiation

The new project-specific loop is:

`source example -> functional decomposition -> mechanism hypothesis -> VisualPattern -> controlled experiment -> confidence update -> compiler eligibility -> first-party benchmark`

That loop complements, rather than replaces, V3.1's historical/material evidence chain.
