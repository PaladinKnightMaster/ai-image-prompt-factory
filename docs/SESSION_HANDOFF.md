# Session Handoff

Read [project state](PROJECT_STATE.md), [experiment lab](EXPERIMENT_LAB.md), and the [EXP-019 v1.1.1 preregistration](../experiments/preregistrations/EXP-019.PREREGISTRATION.md) before continuing.

- Date: 2026-09-25
- Branch: `codex/exp-019-host-metadata-amendment`; base canonical `main`: `923453714228c8a936b52e29cf884ce3c9a7835d`
- Stable release: V3.3; V3.4 implementation merged, empirical validation pending, unreleased
- EXP-019: active v1.1.1 host-evidence amendment frozen, `planned`, and scientifically unexecuted. V1.0.0 was never executed; the first v1.1.0 real run stopped before first import because exact host request time was not observable.

## Change

V1.1.1 retains the exact fixture, C/A/B prompt bytes, twelve-slot order, two-review protocol, scoring, safeguards, and promotion limits. Host request and completion times now use observed exact ISO-8601 values or `null` with `not_observable` status. A same-conversation text-only metadata query and JSON sidecar are required for each future image; the import binds sidecar and image hashes into private attempt provenance. The v1.1.0 run `EXP-019-1.1.0-20260925T171442Z-GZ8Y`, its root checkpoint, and its unimported HADCEH raster remain untouched and excluded from v1.1.1.

## Validation and next task

Offline synthetic host-evidence and historical compatibility tests passed. Full pytest: 309 passed. Repository validator: passed, 19/19 regressions and 10/10 golden baselines, with no generated diff or raw-image leak. Worktree will be clean after the amendment commit. **Next task:** independently review and re-audit v1.1.1, then publish through the normal branch workflow before any new real run. No v1.1.1 generation, import, review, receipt, result, or lexical-effectiveness conclusion exists; V3.4 remains unreleased.
