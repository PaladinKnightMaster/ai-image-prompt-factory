# Session Handoff

Read [project state](PROJECT_STATE.md), [experiment lab](EXPERIMENT_LAB.md), and the [EXP-019 v1.1.1 preregistration](../experiments/preregistrations/EXP-019.PREREGISTRATION.md) before continuing.

- Date: 2026-09-25
- Branch: `codex/exp-019-host-metadata-amendment`; base canonical `main`: `923453714228c8a936b52e29cf884ce3c9a7835d`
- Worktree: `D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\ai-image-prompt-factory`; query-integrity correction follows `720d37ce736859ce8f20e4cfef5c3d76653d8f14`
- Stable release: V3.3; V3.4 implementation merged, empirical validation pending, unreleased
- EXP-019: active v1.1.1 host-evidence amendment frozen, `planned`, and scientifically unexecuted. V1.0.0 was never executed; the first v1.1.0 real run stopped before first import because exact host request time was not observable.

## Change

V1.1.1 retains the exact fixture, C/A/B prompt bytes, twelve-slot order, two-review protocol, scoring, safeguards, timestamp semantics, and promotion limits. A successful import now hashes the actual canonical per-slot packaged metadata query, requires agreement with the manifest and frozen-template rendering, and rejects missing or alternate files before output promotion or attempt consumption. The exact verified bytes are copied once into private `provenance-freeze/execution-receipts/`; that frozen copy is authoritative after import and is checked against the finalized receipt and external attempt digest. The leftover generation package is non-authoritative. Same-conversation origin and host response remain operator-attested. The v1.1.0 run `EXP-019-1.1.0-20260925T171442Z-GZ8Y`, its root checkpoint, and its unimported HADCEH raster remain untouched and excluded from v1.1.1.

## Validation and next task

Synthetic package tampering, manifest forgery, wrong-slot and alternate query, frozen-copy tampering, coordinated local rewrite, review, and historical compatibility tests passed. Full pytest: 334 passed. Repository validator: passed, 19/19 regressions and 10/10 golden baselines, with no generated diff or raw-image leak. **Next task:** independently re-audit the query-integrity correction, then publish through the normal branch workflow before any new real run. No real v1.1.1 generation, import, review, receipt, result, or lexical-effectiveness conclusion exists; V3.4 remains unreleased.
