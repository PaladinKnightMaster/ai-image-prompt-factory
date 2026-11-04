# Session Handoff

- Date: 2026-11-03
- Canonical `main` at branch start: `6c6359bdbd6762f73ac0f6450fe68dc43b5ac699`
- Feature branch: `feat/pr-cr-003a-private-gallery-candidate`
- Stable release: V3.3 (`v3.3.0`); unchanged
- CR-001 `1.0.0` unchanged
- No real CR-001 private candidate creation, gallery publication, or PR-CR-003B

## Change

PR-CR-003A: private creative gallery candidate schema, create/verify CLI,
local HTML preview (file:// to import PNG; no raster copy into candidate dir
or git), synthetic tests, and docs. Public gallery/Pages behavior unchanged.

## Validation

- Focused: `tests/test_private_gallery_candidate.py`
- Inventory: `python aipf_packaging/stage_knowledge.py verify`
- Full: `python -m pytest -q`
- `python scripts/validate_repo.py`

## Next task

Owner review of the PR-CR-003A pull request. Do not merge without separate
approval. Do not create the real CR-001 private candidate without separate
authorization.
