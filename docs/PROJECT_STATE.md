# Current Project State

- Last updated: 2026-09-23
- Current stable release: V3.3 Empirical Lab
- Stable tag: `v3.3.0` (annotated; closure commit `3c0119e`)
- Main HEAD at this synchronization base: `3617a040483410b4d4e2d0468a48165c69087a3e`
- Test state: on this documentation branch, 171 pytest tests passed and `scripts/validate_repo.py` passed on 2026-09-23; see the [current handoff](SESSION_HANDOFF.md).

## Current status

**V3.3 Empirical Lab: CLOSED.** The release tag marks scientific closure and is integrated into `main`. Later `main` commits fixed CI portability and corrected an EXP-017 source-hash notation without changing the underlying result or conclusion. Package and manifest version are `3.3.0`; the compiler/evidence-snapshot lineage remains `3.2.0` by design. See the [release notes](RELEASE_NOTES_V3.3.md).

## Strongest established findings

- Explicit identity/outfit/pose reference-role assignment has credible positive evidence for cross-reference leakage control in the tested context. EXP-017 is the strongest clean local result.
- EXP-016 had a strong score signal but incomplete generation binding; EXP-018 was inconclusive on an independent fixture realization. Cross-fixture generalization remains unresolved.
- V3.3 supports no universal superiority or statistical-significance claim and no automatic compiler, pattern-confidence, or golden-case promotion from this evidence.

The detailed, corrected source of these conclusions is the [V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md).

## Current architecture

A prompt-first compiler uses structured request/case data, explicit locks and reference roles, routed era/art/material knowledge, evidence-aware compatibility checks, and readable production prompts. Optional generation, empirical experiments, independent evaluation, regression cases, and public/internal galleries build on that shared data. The [runtime contract](../SKILL.md) and [architecture ADRs](DECISIONS.md) hold the details.

## Next scope

**V3.4 Transformation Intelligence: PLANNED, not implemented.** Candidate capabilities and later tracks are in the [capability roadmap](ROADMAP.md). This synchronization branch contains process documentation only.

## Open questions

- Does the reference-role effect persist across multiple independently frozen fixture triplets under one protocol?
- How should composable transformation routes preserve identity, historical evidence, material behavior, and artifact state without duplicate prompt libraries?
- Which first-party cases can safely become stronger gallery and regression evidence?

## Canonical references

[V3.3 evidence synthesis](V3.3_EVIDENCE_SYNTHESIS.md) · [V3.3 release notes](RELEASE_NOTES_V3.3.md) · [roadmap](ROADMAP.md) · [decision index](DECISIONS.md) · [research queue](RESEARCH_QUEUE.md) · [session handoff](SESSION_HANDOFF.md)
