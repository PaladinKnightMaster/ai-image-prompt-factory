# Session Handoff

- Date: 2026-11-07
- Canonical `main` (branch base): `31d59e99f207be35f3b726b8f286fa5a8f115a96`
- Feature branch: `feat/cr-011-era-reframing`
- Prior on main: CR-010 The Second Angle (PR #55)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 through CR-007, CR-009, and CR-010 `1.0.0` digests unchanged; CR-008 remains research-only/blocked; no private custody or gallery edits

## Change

CR-011: Era Reframing PromptRecipe — source-conditioned **photographic Tang
era transfer** via installed `reference_transform` of the verified CR-001
fashion photograph. Requests historically informed Tang court-leisure wardrobe,
hair, makeup, and timber architectural staging while preserving recognizable
identity, broad three-quarter stance, weight logic, and eye-level full-length
framing. Roles: `identity`/`pose`/`layout` only (no `outfit`/`hairstyle`/
`environment`/`palette`). EraPack `tang`; `art.method` null; no
TransformationPack; no reconstruction claim; no new route/pack/schema. No image
generation.

## Digests (CR-011 `1.0.0`)

- Recipe SHA-256: `b1dbfcd54ba22f5dee70c5a16e446b6110b4a91f14e9e1ffa06f6a61ebda1c30`
- Baseline prompt SHA-256: `f44b9d8f15bee39abe87a5a5b08a02be91b98b315ad321ad72dbb9b06d5e2715`
- Source (CR-001) SHA-256: `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of CR-011 PR. Do not merge without approval. Do not prepare or
generate era-reframing images without separate authorization (must attach
verified CR-001 PNG plus the exact CR-011 prompt in the same request). No tenth
gallery card without separate authorization. Do not reopen CR-008 implementation.
