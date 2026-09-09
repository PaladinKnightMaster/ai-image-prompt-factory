# Regression Testing

## Level 1 — semantic regression

Runs without an image API. Checks classifier/route, locks, overlays, evidence retrieval, compatibility decisions, uncertainty and lint findings.

## Level 2 — prompt regression

Runs without an image API. Checks required/forbidden clauses, prompt structure/hash, evidence snapshot hash, progressive loading, and known leakage defects.

`cases/regression/` currently contains 19 targeted cases covering Tang blue-and-white modes, Ming/Wuxia, Wuxia without a base, Xianxia hybrid behavior, unbounded strict Dunhuang, Greek marble artifact states, Greek living interpretation, Roman bronze material behavior, Edo ukiyo-e, Edo Arita ceramic separation, and reference-role leakage.

## Level 3 — visual regression

Requires a real generated output and evaluator input. The evaluator records independent scores/subscores, failure classes, model metadata, evidence snapshot hash, and surgical revision. V3.1 does not mark this layer passed when no model output exists.

## Golden baselines

`regression/baselines/golden_baselines.json` stores deterministic hashes for:

- semantic case record
- compiled prompt
- evidence snapshot
- compiler/skill/model metadata

Use `aipf baseline` (or `python scripts/build_baselines.py`) to refresh an intentional baseline and `aipf baseline-check regression/baselines/golden_baselines.json` to compare the current compiler state against it.

This is designed to expose drift; it is not a claim that text hashes alone prove image quality.
