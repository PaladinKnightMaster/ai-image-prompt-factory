# Session Handoff

- Date: 2026-11-04
- Canonical `main` (branch base): `cb75043a17df1a81c41665617e93e9f688510463`
- Feature branch: `feat/cr-004-marble-afterimage`
- Prior on main: CR-003 Refraction Ledger (PR #47)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 / CR-002 / CR-003 `1.0.0` digests unchanged; no private custody edits

## Change

CR-004 Marble Afterimage: source-backed PromptRecipe transforming verified CR-001
fashion photograph into contemporary free-standing marble sculpture via
`artifact_transform` + `portrait_to_volumetric_sculpture` + `marble_sculpture`.
Documents ChatGPT Web attachment as operator-attested/uncaptured. No image
generation.

## Digests (CR-004 `1.0.0`)

- Recipe SHA-256: `b332fd424d18407dee3976d2457d51e187af0465778e5f7f2eed51c6f8e6a0fb`
- Baseline prompt SHA-256: `f42f2631e644e037c70ac2bf959c2587eff26fb981ae97dd169cf057b0d3d02d`
- Source image SHA-256: `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / clean `validate_repo.py` — see PR checks

## Next task

Owner review of CR-004 PR. Do not merge without approval. Do not prepare or
generate transformation images without separate authorization (must include
verified CR-001 PNG as image input).
