# Session Handoff

- Date: 2026-11-05
- Canonical `main` (branch base): `45ac7b99e6de72f85da0d544cf1fa4807decf926`
- Feature branch: `feat/cr-007-porcelain-echo`
- Prior on main: CR-006 Held Light (PR #51)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 / CR-002 / CR-003 / CR-004 / CR-005 / CR-006 `1.0.0` digests unchanged; no private custody edits

## Change

CR-007: Porcelain Echo PromptRecipe — source-backed `artifact_transform`
(`portrait_to_decorated_artifact` + `blue_white_ceramic` + `vase` +
`newly_created`, selected `ceramic.porcelain_body`) translating CR-002 into
contemporary cobalt underglaze figurative decoration on a free-standing porcelain
vase. Symbolic reference + source SHA only; no host-absolute private paths. No
image generation.

## Digests (CR-007 `1.0.0`)

- Recipe SHA-256: `6af6a0756b344d45a4281e882280f593bd3ffed09b54d9be7b0f86ceb14c3b42`
- Baseline prompt SHA-256: `ae067b7b1d6c1b1877cdd1b4f9d39d5ab0e6bc861611178b0c47b68fca4138eb`
- Source (CR-002) SHA-256: `a457c47cd96633b18d69e218f3316edb9886ea58114b96f2b4c0d1dce18221e0`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of CR-007 PR. Do not merge without approval. Do not prepare or
generate ceramic images without separate authorization (must attach verified
CR-002 PNG plus the exact CR-007 prompt in the same request). No private gallery
seventh card without separate authorization.
