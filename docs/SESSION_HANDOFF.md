# Session Handoff

- Date: 2026-09-28
- Branch: `codex/exp-019-degraded-host-provenance`; base `main`: `9e7a963072658f97f6bee98b91bf6b8dcfcdcc81` (merged PR #12)
- Worktree: `D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\ai-image-prompt-factory`
- Stable release: V3.3; V3.4 empirical validation and release remain pending.

## Change

[EXP-019-DHP-20260928-01](../experiments/amendments/EXP-019.v1.1.1.DEGRADED-HOST-PROVENANCE-01.md)
is a separate byte-frozen second post-start publication candidate. It preserves the invalid initial
host response and admits only the exact empty observed host-path contradiction through explicit
prepare/import commands, trusted capture hashes and truthful attestations. The original generation
conversation is permanently unavailable. The merged first metadata-recovery addendum, definition,
fixture, prompts and all scientific rules remain unchanged. Preparation consumes zero attempts or
checkpoints; successful future import consumes attempt 1 and binds the wrapper through the normal
external checkpoint. Degraded analysis/export reports verified bindings and reduced host traceability;
ordinary import remains strict. Earlier receipts are not migrated or relabeled.

## Real-run boundary and next task

The existing original raster and rejected response remain staged and unchanged. No real recovery,
degraded preparation/import, image generation, scoring, reveal, analysis, checkpoint or next-slot
execution occurred. The real run remains 2 generated, 0 failed, 10 planned, zero blocked-slot
attempts and two attempt checkpoints; its remote head is unchanged. All 56 current-run files and
31 historical v1.1.0 files match the preservation baseline.

Independently review the [publication audit](EXP-019_DEGRADED_HOST_PUBLICATION_AUDIT.md) and PR,
then obtain reviewed merge before separately authorized real degraded preparation/import. Stop with
an open unmerged PR. Do not replay metadata or regenerate the image during publication review.

## Validation

Full unit suite: 477 passed (102 new degraded-host tests; 280 EXP-019 tests total). Validation details
are recorded in the publication audit. The validator passes with 579 local JSON files,
19/19 regressions, 10/10 golden cases and zero errors. No unrelated regenerated diff. New tests
use synthetic fixtures, including an actual temporary bare Git remote for the complete review,
analysis and sanitized export chain. Added-content privacy scan passes.
