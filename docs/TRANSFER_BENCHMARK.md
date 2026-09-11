# V3.3 Corpus-Derived Transfer Benchmark

## Purpose

V3.3 now separates empirical work into two layers.

The **Isolation Bench** answers: *does a narrowly defined prompt mechanism have a detectable effect under a simple controlled prompt?*

The **Transfer Bench** answers: *does that mechanism remain useful, neutral, or harmful when the prompt resembles a real production brief with multiple interacting visual requirements?*

The second question cannot be answered safely by copying private creator prompts into experiments. Transfer Benchmark v1 therefore uses private corpus indexes only for mechanism-level distillation and aggregate recurrence signals. All public prompts are first-party AIPF text.

## Why the transfer layer is needed

The private distillation indexes contain 191 prompt records. Aggregate clause counts show substantial recurrence in composition (557), lighting (660), wardrobe (483), material (368), pose (252), hand logic (219), narrative (78), fabric physics (51), and reference-role language (41). Aggregate prompt-method signals are also dense: structure (181), emotion (138), medium (131), design-system framing (119), constraints (111), variable templates (86), narrative (27), and reference handling (20).

These counts are useful for deciding which contexts deserve transfer tests. They are **not causal evidence** and do not promote VisualPatterns.

## Architecture

```text
benchmarks/
  candidates/                  # existing first-party golden candidates
  golden/                      # still empty until full promotion criteria are met
  transfer/
    README.md
    archetypes/
      TB-A01.json ... TB-A07.json
    mappings/
      EXP-007-015.v1.json

data/schemas/
  transfer_archetype.schema.json
  transfer_mapping.schema.json

tests/
  test_v33_transfer.py
```

Transfer archetypes are versioned experimental fixtures. They are deliberately separate from benchmark candidates and golden outputs.

## Archetype set

### TB-A01 — Editorial Fashion Motion Portrait

Production-like photographic fashion scene with visible hands, a prop, a mid-turn garment, layered spatial depth, side-window light, and an 85mm portrait perspective.

Mapped experiments: EXP-007, EXP-011, EXP-012.

### TB-A02 — Narrative Restoration Studio Portrait

Environmental portrait with a micro-action, hand-object interaction, work-context details, layered depth, and mixed practical/window light.

Mapped experiments: EXP-008, EXP-009.

### TB-A03 — Historically Grounded Scholar Study

Historically coherent positive-content scene designed to test whether anachronisms are resolved before composition rather than contradicted only by a final negative clause.

Mapped experiment: EXP-015.

### TB-A04 — Porcelain Material Study

Object-centered artifact scene using porcelain body, underglaze, glaze behavior, side lighting, and negative space. It is intentionally not assigned to EXP-007 through EXP-015; it is reserved for later transfer replications of material and medium mechanisms.

### TB-A05 — Stylized Rooftop Courier Key Art

Dense non-photographic scene with action, environment, lighting, layered composition, material separation, and explicit exclusions.

Mapped experiment: EXP-010.

### TB-A06 — Identity-Only Reference Transfer

One project-owned identity fixture controls identity only while the target wardrobe, pose, framing, and environment are newly specified.

Mapped experiment: EXP-013. Execution is blocked until a first-party identity fixture is frozen and hashed.

### TB-A07 — Three-Role Reference Composition

Three project-owned fixtures separately control identity, outfit, and pose.

Mapped experiment: EXP-014. Execution is blocked until all three first-party fixtures, their hashes, and ordering are frozen.

## EXP-007 through EXP-015 mapping

| Experiment | Archetype | Factor | Primary visible dimension | Readiness |
| --- | --- | --- | --- | --- |
| EXP-007 | TB-A01 | 8K/masterpiece phrase | photographic_rendering_quality | ready |
| EXP-008 | TB-A02 | broad vs targeted constraints | targeted_failure_mode_control | ready |
| EXP-009 | TB-A02 | adjective stack vs precise emotion | emotional_specificity | ready |
| EXP-010 | TB-A05 | natural language vs JSON-style syntax | scene_constraint_fidelity | ready |
| EXP-011 | TB-A01 | generic vs constructed garment language | garment_construction_fidelity | ready |
| EXP-012 | TB-A01 | no fabric physics vs explicit response | fabric_motion_coherence | ready |
| EXP-013 | TB-A06 | repeated vs single identity lock | identity_fidelity | blocked on first-party fixture |
| EXP-014 | TB-A07 | implicit vs explicit reference roles | reference_role_fidelity | blocked on first-party fixtures |
| EXP-015 | TB-A03 | post-hoc negation vs positive pre-resolution | historical_cultural_coherence | ready |

## Contamination and provenance rules

1. Raw private source prompt text, source prompt IDs, source images, image hashes, and creator-specific phrasing never enter public transfer fixtures.
2. Private indexes may contribute only aggregate counts, mechanism labels, and recurrence signals.
3. Every public baseline prompt must be newly authored by AIPF and carry a SHA-256 hash.
4. A source-corpus observation can justify *testing* a mechanism; it cannot by itself justify compiler eligibility or pattern promotion.
5. Private corpus images are forbidden as reference fixtures. Reference experiments require first-party or project-owned fixtures with frozen hashes.
6. Once a transfer run begins, the archetype ID, version, and prompt hash are immutable for that run. Any substantive prompt edit requires an archetype version bump.
7. One experiment still changes one declared factor. Richer context does not relax single-factor discipline.
8. Existing EXP-001 through EXP-006 evidence remains unchanged. Transfer replication creates new evidence rather than rewriting isolation results.

## Validation plan

The transfer test suite validates:

- all seven archetypes against a strict JSON schema;
- baseline prompt hashes;
- first-party/publication-safe provenance flags;
- absence of private prompt IDs and creator names from the public transfer surface;
- exact one-to-one coverage of EXP-007 through EXP-015 in the mapping;
- version agreement between mapping, archetypes, and experiment definitions;
- removal of the old generic portrait baseline from EXP-007 through EXP-015;
- factor-specific prompt transformations for EXP-007, EXP-008, EXP-009, EXP-011, EXP-012, and EXP-015;
- semantic-anchor preservation across natural-language and JSON-style EXP-010 prompts;
- blocked execution state for EXP-013 and EXP-014 until first-party reference fixtures exist.

The normal repository validator and full pytest suite remain the release gate.
