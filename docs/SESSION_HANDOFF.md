# Session Handoff

- Date: 2026-11-05
- Canonical `main` (branch base): `80a053d86de153e42c294ada88bc543ee574885e`
- Feature branch: `feat/cr-005-silk-on-plaster`
- Prior on main: CR-004 Marble Afterimage portable (PR #49)
- Stable release: V3.3 (`v3.3.0`); unchanged
- `COMPILER_VERSION` remains `3.2.0`
- CR-001 / CR-002 / CR-003 / CR-004 `1.0.0` digests unchanged; no private custody edits

## Change

CR-005: Silk on Plaster PromptRecipe — source-backed `artifact_transform`
(`portrait_to_architectural_mural` + `mineral_pigment_mural` + `wall_surface` +
`newly_created`) from verified CR-002 original. Symbolic reference + source SHA
only; no host-absolute private paths. No image generation.

## Digests (CR-005 `1.0.0`)

- Recipe SHA-256: `cfe891967c42206606b278306d8f0e16158aece2610759e8060e3ea5cf0eaf88`
- Baseline prompt SHA-256: `6e3f9d6416fffc05c4e94cf81c3312a80b3564f1cd1689a54bfbe31da13984da`
- Source image SHA-256: `a457c47cd96633b18d69e218f3316edb9886ea58114b96f2b4c0d1dce18221e0`

## Validation

- Focused: `tests/test_creative_recipe_library.py`
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of CR-005 PR. Do not merge without approval. Do not prepare or
generate mural images without separate authorization (must attach verified
CR-002 PNG). No private gallery fifth card without separate authorization.
