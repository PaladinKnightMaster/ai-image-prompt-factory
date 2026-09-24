# Session Handoff

Read [project state](PROJECT_STATE.md), [roadmap](ROADMAP.md), [decisions](DECISIONS.md), and the [frozen EXP-019 preregistration](../experiments/preregistrations/EXP-019.PREREGISTRATION.md) before continuing.

- Date: 2026-09-24
- Branch: `codex/exp-019-execution-infrastructure`; base canonical `main`: `a5ee6e52e97f267d2ee69b2153e681227e5b9499` (PR #8 merge)
- Stable release: V3.3; V3.4 implementation merged, empirical validation pending, unreleased
- EXP-019 v1.0.0: frozen, `planned`, unexecuted; no generation, receipt, review, result, or empirical conclusion

## Implementation

This branch implements the frozen twelve-slot execution, full raster validation, attempt and run receipts, two blind reviews, two-freeze reveal, and deterministic three-condition analysis. The final corrective patch adds [remote Git provenance checkpoints](EXP-019_REMOTE_PROVENANCE.md) for the run root, every completed attempt, and each reviewer freeze. Retry, reveal, receipt validation, and result analysis fetch and verify the external chain. The fixture, definition, C/A/B prompts, V3.3 behavior, and scientific rules remain unchanged.

## Validation and next task

PR #9 is open. Its first CI run exposed a test setup conflict: repository-local `.pytest_tmp` held synthetic rasters when the privacy test scanned the worktree. This branch now lets pytest use the system temporary directory; the privacy test and EXP-019 protocol remain unchanged. A clean Python 3.12 install passed all 266 tests and repository validation (19/19 regressions, 10 golden baselines, no errors). The four pre-existing EXP-016 `pattern_implications` schema errors are unchanged. Worktree: verify clean after commit. Next task: confirm PR #9 passes both CI runners, then review it through the normal merge workflow. Do not generate images until execution readiness is separately authorized.
