# Session Handoff

- Date: 2026-11-06
- Canonical `main` (branch base): `91b42aebe777005d506eb706d562246013ece790`
- Feature branch: `feat/cr-010-the-second-angle`
- Prior on main: CR-009 Golden Seam (PR #54)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 through CR-007 and CR-009 `1.0.0` digests unchanged; CR-008 remains research-only/blocked; no private custody edits

## Change

CR-010: The Second Angle PromptRecipe — source-conditioned **product
viewpoint transfer** via installed `reference_transform` of the verified
CR-003 perfume photograph. Requests one eye-level three-quarter viewpoint
approximately 30° off the source near-frontal view while preserving
recognizable bottle design, faceted clear glass, brushed-metal cap, plinth,
and studio character. Roles: `artifact`/`environment`/`palette` only (no
`layout`/`pose`/`identity` lock of frontal framing). Descriptive camera
prose only; no numeric yaw field; no 3D-reconstruction claim; no new route/
pack/schema. No image generation.

## Digests (CR-010 `1.0.0`)

- Recipe SHA-256: `fdf3b4181313e83a2a3c7c60aaec0cfb92cfc2c46e6a72622a3aa629188e9183`
- Baseline prompt SHA-256: `eecb60fd973d07e03a9a38ad73ce707b6c0cd52b862817604a3c921bf3610215`
- Source (CR-003) SHA-256: `43a9ff6e0a0aaed177fae1145ac3e1ed88566ab507952c4e68fde97d10b3d1c4`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of CR-010 PR. Do not merge without approval. Do not prepare or
generate viewpoint images without separate authorization (must attach verified
CR-003 PNG plus the exact CR-010 prompt in the same request). No ninth gallery
card without separate authorization. Do not reopen CR-008 implementation.
