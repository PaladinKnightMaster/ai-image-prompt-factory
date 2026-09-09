# External Repository Comparison — V3.1 Re-check

Audit date: 2026-09-07. This document records architectural inspiration, not copied content.

## Female Portrait Director / Outfit Director

Current public Female Portrait Director material identifies V1.6 and uses lightweight route/overlay/tool registries. Overlays augment rather than replace the primary route, tool modules remain bounded by locks, and help/tutorial content is loaded only when needed. Current outfit-director/female-outfit-director projects similarly package installable `SKILL.md + agents/openai.yaml + references` workflows and explicitly preserve reference identity in outfit operations.

**Adopt:** registry-driven routing, permission boundaries, progressive help/reference loading, reference locks.  
**Modify:** AIPF routes by visual task/history/material rather than portrait-style menu; evidence claims and compatibility audits sit between route selection and compilation.  
**Reject:** fixed portrait-style lists as the primary product abstraction.

References:
- https://github.com/liyue-aigc/female-portrait-director
- https://github.com/liyue-aigc/female-outfit-director
- https://github.com/liyue-aigc/outfit-director

## Garden GPT Image 2 skill

The current Garden-family GPT Image 2 skill uses three runtime modes (local/API, host-native, advisor/prompt-only), mode detection before execution, separate generation/edit workflows, and reusable reference templates.

**Adopt:** explicit runtime detection, compile-before-execute, host-native/API/advisor separation, prompt/image archival concepts.  
**Modify:** AIPF keeps generation optional and adds model/evidence/case regression metadata.  
**Reject:** making runtime execution the product center; AIPF's primary artifact remains the prompt plus audit.

Reference: https://github.com/ConardLi/garden-skills/tree/main/skills/gpt-image-2

## awesome-gpt-image-2

The current repository describes a Prompt-as-Code direction, atomic structured semantics and a 544-case gallery across multiple use categories.

**Adopt:** atomic/composable semantics, gallery cases as reusable test assets, automation-friendly structure.  
**Modify:** AIPF treats public prompt galleries as idea/sample sources, not historical evidence; cases include evidence snapshots and compatibility audits.  
**Reject:** optimizing for case count as a release metric.

Reference: https://github.com/freestylefly/awesome-gpt-image-2

## YouMind AI image prompts skill

The current skill exposes a manifest-driven dynamic category system and loads only the matched category file rather than all prompt data.

**Adopt:** manifest-first discovery and token-efficient progressive disclosure.  
**Modify:** AIPF manifests route evidence and canonical modules rather than selecting a finished prompt from a very large collection.  
**Reject:** treating category frequency/popularity as truth or compatibility evidence.

Reference: https://github.com/YouMind-OpenLab/ai-image-prompts-skill

## AIPF-specific differentiation

AIPF V3.1 combines the useful routing/progressive-loading ideas above with a separate evidence/provenance layer:

`source → claim → interpretation → compatibility action → natural-language prompt clause → evidence snapshot → regression baseline`

That chain, plus explicit reference-role isolation and material fabrication logic, is the core product difference.
