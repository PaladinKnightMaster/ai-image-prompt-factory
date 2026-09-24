# Current Project State

- Last updated: 2026-09-23
- Current stable release: V3.3 Empirical Lab
- Stable tag: `v3.3.0` (annotated; closure commit `3c0119e`)
- Architecture freeze base HEAD: `a86b66cee21c37e9a055ee0b3809082b7413d370` on `main`
- Current implementation branch: `feat/v3.4-transformation-intelligence`, created from `main` at `8c8eeeaa662e6536aca3610374d1016ca61eb134`; see the [current handoff](SESSION_HANDOFF.md).

## Current status

**V3.3 Empirical Lab: CLOSED.** The release tag marks scientific closure and is integrated into `main`. Later `main` commits fixed CI portability and corrected an EXP-017 source-hash notation without changing the underlying result or conclusion. Package and manifest version are `3.3.0`; the compiler/evidence-snapshot lineage remains `3.2.0` by design. See the [release notes](RELEASE_NOTES_V3.3.md).

**V3.4 Transformation Intelligence: architecture frozen; implementation in progress on the feature branch.** The canonical [architecture freeze](V3.4_ARCHITECTURE_FREEZE.md) remains authoritative. The four-family MVP is implemented for review and validation on the branch, but V3.4 is not merged or released. V3.3 remains the stable released baseline.

## Strongest established findings

- Explicit identity/outfit/pose reference-role assignment has credible positive evidence for cross-reference leakage control in the tested context. EXP-017 is the strongest clean local result.
- EXP-016 had a strong score signal but incomplete generation binding; EXP-018 was inconclusive on an independent fixture realization. Cross-fixture generalization remains unresolved.
- V3.3 supports no universal superiority or statistical-significance claim and no automatic compiler, pattern-confidence, or golden-case promotion from this evidence.

The detailed, corrected source of these conclusions is the [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md).

## Current architecture

A prompt-first compiler uses structured request/case data, explicit locks and reference roles, routed era/art/material knowledge, evidence-aware compatibility checks, and readable production prompts. Optional generation, empirical experiments, independent evaluation, regression cases, and public/internal galleries build on that shared data. The [runtime contract](../SKILL.md) and [architecture ADRs](DECISIONS.md) hold the details.

## Next scope

Complete implementation review and PR preparation for the frozen V3.4 Transformation Intelligence architecture. Do not run the planned lexical image-generation experiment as part of implementation. Later tracks remain in the [capability roadmap](ROADMAP.md).

## Open questions

- Does the reference-role effect persist across multiple independently frozen fixture triplets under one protocol?
- How should composable transformation routes preserve identity, historical evidence, material behavior, and artifact state without duplicate prompt libraries?
- Which first-party cases can safely become stronger gallery and regression evidence?

## Canonical references

[V3.4 architecture freeze](V3.4_ARCHITECTURE_FREEZE.md) · [V3.4 implementation evidence](V3.4_IMPLEMENTATION_EVIDENCE.md) · [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md) · [V3.3 release notes](RELEASE_NOTES_V3.3.md) · [roadmap](ROADMAP.md) · [decision index](DECISIONS.md) · [research queue](RESEARCH_QUEUE.md) · [session handoff](SESSION_HANDOFF.md)
