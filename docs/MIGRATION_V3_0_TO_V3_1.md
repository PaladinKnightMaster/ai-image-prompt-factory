# Migration: V3.0 → V3.1

## Preserved

- semantic request/case shape
- route system
- reference roles
- identity/body modes
- four historical modes
- era/site/genre distinction
- 13 era/site/overlay packs
- 12 art-method modules
- artifact form/state
- director fields
- compact/standard/extended compiler profiles
- golden case directories
- prompt-first / optional-generation behavior

## Added

- `evidence/` source/claim/index layer
- claim/source schemas and knowledge versions
- mode-sensitive compatibility audit
- evidence snapshot and source-version metadata in cases
- survival-bias prompt behavior
- corpus ingestion/hash/license/dedup indexes
- regression cases/reports/baselines
- semantic and prompt-section diffing
- expanded evaluator and surgical revision plan
- Gallery V2 metadata/publication gating
- current GPT Image 2 model snapshot metadata where known

## Compatibility

V3.0 golden cases were migrated in place to case version 3.1 while preserving their primary semantics. Compiler output can change because evidence and historical-mode clauses are now intentionally material, so raw prompt hashes are expected to differ from V3.0.

## Breaking behavior by design

A request that V3.0 might have accepted aesthetically can now be adapted/qualified/rejected when evidence conflicts with the requested historical strictness. This is a product improvement, not a backward-compatibility bug.
