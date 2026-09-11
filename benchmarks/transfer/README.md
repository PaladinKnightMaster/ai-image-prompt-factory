# V3.3 Transfer Benchmark

The Transfer Benchmark is the second empirical layer in AIPF V3.3.

- **Isolation Bench:** minimal prompts that isolate one factor with as little scene complexity as possible.
- **Transfer Bench:** richer first-party archetypes designed to test whether a mechanism survives in production-like prompts.

The Transfer Benchmark does not publish or replay private source prompts. Private corpus indexes are used only to identify recurring mechanism families and aggregate design signals. Every public archetype prompt is newly authored by the project.

## Layout

- `archetypes/` — versioned first-party prompt archetypes.
- `mappings/EXP-007-015.v1.json` — frozen mapping from remaining V3.3 experiments to transfer archetypes and factor guards.

Transfer archetypes are experimental fixtures, not golden benchmarks. They must not be placed in `benchmarks/golden/` merely because an experiment succeeds.

## Frozen v1 archetypes

| ID | Archetype | Primary coverage |
| --- | --- | --- |
| TB-A01 | Editorial Fashion Motion Portrait | quality wording, garment construction, fabric physics |
| TB-A02 | Narrative Restoration Studio Portrait | targeted constraints, precise emotion |
| TB-A03 | Historically Grounded Scholar Study | historical pre-resolution |
| TB-A04 | Porcelain Material Study | future artifact/material transfer replication |
| TB-A05 | Stylized Rooftop Courier Key Art | natural language vs structured prompt format |
| TB-A06 | Identity-Only Reference Transfer | identity-lock repetition |
| TB-A07 | Three-Role Reference Composition | explicit reference-role isolation |

## Evidence boundary

Corpus recurrence is used to choose what is worth testing, not to prove that a mechanism works. `observed` or `hypothesis` VisualPatterns remain epistemically unchanged until controlled experiment evidence justifies a separate registry update.

Reference-transfer experiments may use only first-party or project-owned fixture images with frozen hashes. Private corpus images are forbidden as public transfer fixtures.

Any change to a baseline archetype after generation has started requires a version bump. Runs must record the archetype ID, version, and prompt hash so transfer evidence stays reproducible.
