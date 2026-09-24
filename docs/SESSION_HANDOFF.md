# Session Handoff

Purpose: Continue from the committed repository state. Read [project state](PROJECT_STATE.md), [roadmap](ROADMAP.md), [decisions](DECISIONS.md), and the [V3.4 architecture freeze](V3.4_ARCHITECTURE_FREEZE.md).

## Current handoff

- Date: 2026-09-23
- Branch: `feat/v3.4-transformation-intelligence`
- HEAD: this implementation commit; resolve with `git rev-parse HEAD` after checkout
- Base: up-to-date `main` at `8c8eeeaa662e6536aca3610374d1016ca61eb134`
- Worktree: expected clean after the implementation commit; verify with `git status`
- Stable release: V3.3 Empirical Lab, tag `v3.3.0`
- V3.4 status: architecture frozen; implementation prepared for review, not merged or released

### Implementation summary

Added four generic, data-driven TransformationPacks, optional transformation request data, two artifact forms, and `concept_refs` in the existing method, form, and bounded Greek era knowledge. Added the 30-concept Visual Semantic Lexicon, candidate lookup, gated semantic concept plan, deterministic Lexical Realizer, compiler traces, transformation evaluation dimensions/failures, and exactly four ungenerated candidate cases. Added six canonical source records and one V3.4 pouncing claim without changing released V3.3 claims or results. EXP-019 defines a planned, unexecuted C/A/B lexical comparison.

The complete file inventory and four resolver, concept, trace, and prompt examples are in [V3.4 implementation evidence](V3.4_IMPLEMENTATION_EVIDENCE.md).

Legacy requests still use the V3.3 prose path. The four V3.4 families share one resolver and realizer. Conditional concepts are emitted only after explicit semantic selection and applicable gates. `historical_precision` changes expression detail, not historical strictness.

### Validation

Schema and repository validator: passed, including 30 lexicon concepts, four TransformationPacks, four V3.4 candidate cases, 23 evidence claims, and 19/19 legacy regression cases. Full pytest suite: 197 passed. Separate regression run: 19/19 passed. Golden baseline check: 10/10 stable, zero drift. `git diff --check` and local documentation links checked. The validator's distributable raster/privacy check passed; no private fixture/image bytes were added. No V3.3 empirical result or experiment artifact was modified. All commands used the bundled Python through `uv` because the local `.venv` points to a missing interpreter.

### Unresolved and next task

No image generations, visual evaluations, or lexical superiority claims exist for V3.4. Candidate references are placeholders pending separately frozen first-party fixtures. Review and merge the V3.4 implementation PR after code review; then separately freeze fixtures and preregistration details for EXP-019 before any image-generation experiment.
