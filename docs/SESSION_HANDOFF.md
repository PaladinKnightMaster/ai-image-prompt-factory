# Session Handoff

- Date: 2026-11-03
- Canonical `main` at branch start: `ddab78c2e3a2ff9cf79354f3c078000b1a24ece7`
- Feature branch: `feat/pr-cr-002-recipe-generation-provenance`
- PR: https://github.com/PaladinKnightMaster/ai-image-prompt-factory/pull/39
- Stable release: V3.3 (`v3.3.0`); unchanged by PR-CR-002
- CR-001 `1.0.0` unchanged
- No live image generation, gallery publication, EXP-019, or G4/G5 authorization

## Change

PR-CR-002: optional `creative_provenance` on generation metadata, offline
prepare/verify bundle tooling (`aipf.creative_provenance`,
`scripts/creative_recipe_generation.py`), docs, and focused tests. No new
executor; no network in the preparation path.

Follow-up correction: offline verify never elevates to
`provider_confirmed_partial` based on a self-authored
`provider_verified_model_id`; that level remains reserved.

## Validation

- Focused: `tests/test_creative_recipe_provenance.py` — pass (incl. forged-provider-ID)
- Full: `python -m pytest -q`
- Inventory: `python aipf_packaging/stage_knowledge.py verify`
- `python scripts/validate_repo.py` on clean detached worktree
- CR-001 `1.0.0` digests unchanged (`recipe_sha256=60c4547e…`,
  `prompt_sha256=92f4c664…`)

## Next task

Owner review of PR #39. Do not merge without separate approval.
PR-CR-003, live generation campaigns, and camera-c2 visual tests remain
unauthorized.
