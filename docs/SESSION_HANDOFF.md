# Session Handoff

- Date: 2026-11-05
- Canonical `main` (branch base): `7d3b3759b7aee771dda7b54293b907fc1f63a81e`
- Feature branch: `feat/cr-009-golden-seam`
- Prior on main: CR-008 Golden Fault feasibility (PR #53; implementation blocked)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 through CR-007 `1.0.0` digests unchanged; CR-008 remains research-only/blocked; no private custody edits

## Change

CR-009: Golden Seam PromptRecipe — source-conditioned **whole-image revision**
via installed `reference_transform` of the verified CR-007 porcelain photograph,
requesting one restrained gold-lacquer repair seam with semantic preservation
guidance. No TransformationPack, no mask/ROI, no pixel-exact preservation claim.
Does not implement or resolve CR-008 localized-edit gap. Symbolic CR-007 source
SHA only; no host-absolute private paths. No image generation.

## Digests (CR-009 `1.0.0`)

- Recipe SHA-256: `8bff3467bbe5a1436881098b82eafee239a4644c78b6d08af48a635e196817ed`
- Baseline prompt SHA-256: `7273bd83193d65a47cf97b789aff64bf69abe901a87cbcfe67a08cf900d52f5a`
- Source (CR-007) SHA-256: `15b082d7573ee973740553d463aa2693634fcc45a6d0a4d8538dd5e0c4dcbc97`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of CR-009 PR. Do not merge without approval. Do not prepare or
generate revision images without separate authorization (must attach verified
CR-007 PNG plus the exact CR-009 prompt in the same request; no mask). No
eighth gallery card without separate authorization. Do not reopen CR-008
implementation.
