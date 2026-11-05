# Session Handoff

- Date: 2026-11-05
- Canonical `main` (branch base): `293ab648e58bed5ee0eaa26ef15499c0a89d67a7`
- Feature branch: `feat/cr-006-held-light`
- Prior on main: CR-005 Silk on Plaster (PR #50)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 / CR-002 / CR-003 / CR-004 / CR-005 `1.0.0` digests unchanged; no private custody edits

## Change

CR-006: Held Light PromptRecipe — two-reference `new_generation` fragrance
campaign composing CR-001 fashion subject (`identity`/`outfit`/`hairstyle`) with
CR-003 perfume flacon (`artifact`). Pose intentionally unassigned on Ref A;
environment/plinth unassigned on Ref B. Symbolic references + source SHAs only;
no host-absolute private paths. No image generation.

## Digests (CR-006 `1.0.0`)

- Recipe SHA-256: `2222db4d21923c9ee3e2630fd2bcd4dc14808ce702d48db7588369b9d5798f51`
- Baseline prompt SHA-256: `5bb47d64c127019cd89070cfcaa460401e325e46e38dbdc3d931db36e4947ec4`
- Ref A (CR-001) SHA-256: `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e`
- Ref B (CR-003) SHA-256: `43a9ff6e0a0aaed177fae1145ac3e1ed88566ab507952c4e68fde97d10b3d1c4`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of CR-006 PR. Do not merge without approval. Do not prepare or
generate campaign images without separate authorization (must attach both
verified CR-001 and CR-003 PNGs plus the exact CR-006 prompt). No private
gallery sixth card without separate authorization.
