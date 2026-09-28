# Current Project State

- Last updated: 2026-09-28
- Canonical branch: `main`; V3.4 implementation merge commit: `aa6ae9bb57166d70840fb6ec6ca2a2f4a59b8a52` (PR #6)
- Current stable release: V3.3 Empirical Lab
- Stable tag: `v3.3.0` (annotated; closure commit `3c0119e`)
- Architecture freeze base HEAD: `a86b66cee21c37e9a055ee0b3809082b7413d370` on `main`

## Current status

**V3.3 Empirical Lab: CLOSED and latest stable release.** The release tag marks scientific closure and is integrated into `main`. Later `main` commits fixed CI portability and corrected an EXP-017 source-hash notation without changing the underlying result or conclusion. README and SKILL titles, package, and manifest retain the V3.3 release label; the compiler/evidence-snapshot lineage remains `3.2.0` by design. See the [release notes](RELEASE_NOTES_V3.3.md).

**V3.4 Transformation Intelligence: architecture frozen; implementation merged into `main`; empirical validation pending; release pending.** The canonical [architecture freeze](V3.4_ARCHITECTURE_FREEZE.md) remains authoritative. PR #6 merged the four-family MVP, documented in the [implementation evidence](V3.4_IMPLEMENTATION_EVIDENCE.md). EXP-019 v1.0.0 was preregistered but never executed. The active v1.1.1 [preregistration](../experiments/preregistrations/EXP-019.PREREGISTRATION.md) preserves the frozen [textual fixture](../experiments/fixtures/EXP-019/EXP-019-BOKASHI-01.fixture.json), prompts, and scientific rules while allowing unavailable host timestamps to be recorded honestly. The definition remains `planned`; the private v1.1.1 run has two finalized host-native outputs, no reviewer scoring, and no result or analysis. Execution is paused before import of the third raster because its host sidecar failed validation. No general image-generation benefit from domain-grounded lexical realization has been established.

EXP-019 execution infrastructure was merged before the v1.1.0 host-native amendment. Its offline synthetic rehearsal is not empirical evidence. The first v1.1.0 real run has a root provenance checkpoint and one staged, unimported HADCEH raster; it stopped before the first accepted attempt because exact host request time was unavailable. Its image and run are excluded from any v1.1.1 execution. PR #11 merged the v1.1.1 text-only metadata-query and sidecar contract. PR #12 merged the [post-start metadata recovery addendum](../experiments/amendments/EXP-019.v1.1.1.METADATA-RECOVERY-01.md), which permits one bounded exact-query replay in the original conversation. Permanent conversation loss prevents that path for the next unimported raster; a separate degraded-host addendum is prepared for publication review. Both preserve the frozen scientific definition.

## Strongest established findings

- Explicit identity/outfit/pose reference-role assignment has credible positive evidence for cross-reference leakage control in the tested context. EXP-017 is the strongest clean local result.
- EXP-016 had a strong score signal but incomplete generation binding; EXP-018 was inconclusive on an independent fixture realization. Cross-fixture generalization remains unresolved.
- V3.3 supports no universal superiority or statistical-significance claim and no automatic compiler, pattern-confidence, or golden-case promotion from this evidence.

The detailed, corrected source of these conclusions is the [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md).

## Current architecture

A prompt-first compiler uses structured request/case data, explicit locks and reference roles, routed era/art/material knowledge, evidence-aware compatibility checks, and readable production prompts. The merged V3.4 path adds generic representation transformations and deterministic lexical realization of resolved concepts. Optional generation, empirical experiments, independent evaluation, regression cases, and public/internal galleries build on shared data. The [runtime contract](../SKILL.md) and [architecture ADRs](DECISIONS.md) hold the details.

## Next scope

PR #12 merged the unchanged EXP-019-MR-20260928-01 addendum. Permanent original-conversation loss
prevents its replay path for the blocked next slot. Review and publish the separate
[EXP-019-DHP-20260928-01](../experiments/amendments/EXP-019.v1.1.1.DEGRADED-HOST-PROVENANCE-01.md)
publication candidate before any explicit degraded preparation/import. It preserves raw rejected
evidence and permits only the exact empty observed host-path defect, with qualified provenance and
unchanged scientific rules. No real preparation/import, image generation, scoring, reveal, analysis
or checkpoint occurred during this implementation. Do not treat synthetic checks as an empirical
result or V3.4 release. Later tracks remain in the [capability roadmap](ROADMAP.md).

## Open questions

- Does the reference-role effect persist across multiple independently frozen fixture triplets under one protocol?
- How should composable transformation routes preserve identity, historical evidence, material behavior, and artifact state without duplicate prompt libraries?
- Which first-party cases can safely become stronger gallery and regression evidence?

## Canonical references

[V3.4 architecture freeze](V3.4_ARCHITECTURE_FREEZE.md) · [V3.4 implementation evidence](V3.4_IMPLEMENTATION_EVIDENCE.md) · [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md) · [V3.3 release notes](RELEASE_NOTES_V3.3.md) · [roadmap](ROADMAP.md) · [decision index](DECISIONS.md) · [research queue](RESEARCH_QUEUE.md) · [session handoff](SESSION_HANDOFF.md)
