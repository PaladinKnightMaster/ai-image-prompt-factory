# Current Project State

- Last updated: 2026-09-24
- Canonical branch: `main`; V3.4 implementation merge commit: `aa6ae9bb57166d70840fb6ec6ca2a2f4a59b8a52` (PR #6)
- Current stable release: V3.3 Empirical Lab
- Stable tag: `v3.3.0` (annotated; closure commit `3c0119e`)
- Architecture freeze base HEAD: `a86b66cee21c37e9a055ee0b3809082b7413d370` on `main`

## Current status

**V3.3 Empirical Lab: CLOSED and latest stable release.** The release tag marks scientific closure and is integrated into `main`. Later `main` commits fixed CI portability and corrected an EXP-017 source-hash notation without changing the underlying result or conclusion. README and SKILL titles, package, and manifest retain the V3.3 release label; the compiler/evidence-snapshot lineage remains `3.2.0` by design. See the [release notes](RELEASE_NOTES_V3.3.md).

**V3.4 Transformation Intelligence: architecture frozen; implementation merged into `main`; empirical validation pending; release pending.** The canonical [architecture freeze](V3.4_ARCHITECTURE_FREEZE.md) remains authoritative. PR #6 merged the four-family MVP, documented in the [implementation evidence](V3.4_IMPLEMENTATION_EVIDENCE.md). EXP-019 v1.0.0 was preregistered but never executed. The v1.1.0 host-native [preregistration](../experiments/preregistrations/EXP-019.PREREGISTRATION.md) supersedes its execution mechanics before generation, preserving the same frozen [textual fixture](../experiments/fixtures/EXP-019/EXP-019-BOKASHI-01.fixture.json), prompts, and scientific rules. EXP-019 remains `planned` and unexecuted. No generation receipt or result exists, and no general image-generation benefit from domain-grounded lexical realization has been established.

EXP-019 execution infrastructure was merged before the v1.1.0 host-native amendment. Its offline synthetic rehearsal is not empirical evidence. Host-native execution and the V3.4+ private storage contract are being frozen on `codex/exp-019-host-native-freeze`; a fresh execution-readiness audit is required before any real generation.

## Strongest established findings

- Explicit identity/outfit/pose reference-role assignment has credible positive evidence for cross-reference leakage control in the tested context. EXP-017 is the strongest clean local result.
- EXP-016 had a strong score signal but incomplete generation binding; EXP-018 was inconclusive on an independent fixture realization. Cross-fixture generalization remains unresolved.
- V3.3 supports no universal superiority or statistical-significance claim and no automatic compiler, pattern-confidence, or golden-case promotion from this evidence.

The detailed, corrected source of these conclusions is the [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md).

## Current architecture

A prompt-first compiler uses structured request/case data, explicit locks and reference roles, routed era/art/material knowledge, evidence-aware compatibility checks, and readable production prompts. The merged V3.4 path adds generic representation transformations and deterministic lexical realization of resolved concepts. Optional generation, empirical experiments, independent evaluation, regression cases, and public/internal galleries build on shared data. The [runtime contract](../SKILL.md) and [architecture ADRs](DECISIONS.md) hold the details.

## Next scope

Review the EXP-019 v1.1.0 host-native freeze and re-audit execution readiness before any generation. Do not treat infrastructure tests as an empirical result or V3.4 release. Later tracks remain in the [capability roadmap](ROADMAP.md).

## Open questions

- Does the reference-role effect persist across multiple independently frozen fixture triplets under one protocol?
- How should composable transformation routes preserve identity, historical evidence, material behavior, and artifact state without duplicate prompt libraries?
- Which first-party cases can safely become stronger gallery and regression evidence?

## Canonical references

[V3.4 architecture freeze](V3.4_ARCHITECTURE_FREEZE.md) · [V3.4 implementation evidence](V3.4_IMPLEMENTATION_EVIDENCE.md) · [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md) · [V3.3 release notes](RELEASE_NOTES_V3.3.md) · [roadmap](ROADMAP.md) · [decision index](DECISIONS.md) · [research queue](RESEARCH_QUEUE.md) · [session handoff](SESSION_HANDOFF.md)
