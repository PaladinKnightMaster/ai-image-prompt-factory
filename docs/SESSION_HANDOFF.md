# Session Handoff

Purpose: Continue from committed repository state. Read [project state](PROJECT_STATE.md), [roadmap](ROADMAP.md), [decisions](DECISIONS.md), and the [V3.4 architecture freeze](V3.4_ARCHITECTURE_FREEZE.md).

## Current handoff

- Date: 2026-09-24
- Branch: `codex/exp-019-preregistration-freeze`, based on canonical `main` at `94eb511ffea50693e3f94d25a07a648911327e7a`
- Worktree: expected clean after the preregistration commit; verify with `git status`
- Stable release: V3.3 Empirical Lab, tag `v3.3.0`
- V3.4: architecture and implementation merged to `main`; empirical validation pending; unreleased

### EXP-019 freeze

EXP-019 v1.0.0 is a planned, unexecuted Domain-Grounded Lexical Realization Isolation-Bench test of `woodblock.bokashi`. Its [textual fixture](../experiments/fixtures/EXP-019/EXP-019-BOKASHI-01.fixture.json) and [preregistration](../experiments/preregistrations/EXP-019.PREREGISTRATION.md) are frozen. The fixture and definition hashes, exact C/A/B prompt hashes, four-replicate invocation order, two-review rule, safeguards, retry limits, and provenance gates are bound there. No EXP-019 generation, receipt, output, result, or lexical-effectiveness conclusion exists. Execution readiness, including capture of two independent frozen reviews, must be verified before any generation.

### Validation

Full pytest suite: 199 passed. Repository validator: passed, including 19/19 regressions and distributable raster/privacy checks. The fixture and definition file hashes and all three prompt byte/count bindings were verified. No V3.3 result, V3.4 runtime/compiler/lexicon behavior, golden baseline, or release metadata changed.

### Exact next task

Verify the frozen EXP-019 execution/readiness gates, then execute its 12 independent invocations without changing the fixture, prompts, or preregistered review and analysis rules.
