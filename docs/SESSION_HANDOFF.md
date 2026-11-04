# Session Handoff

- Date: 2026-11-03
- Canonical `main` at branch start: `6c6359bdbd6762f73ac0f6450fe68dc43b5ac699`
- Feature branch: `feat/pr-cr-003a-private-gallery-candidate`
- Branch HEAD: see latest commit on branch
- PR: https://github.com/PaladinKnightMaster/ai-image-prompt-factory/pull/41
- Stable release: V3.3 (`v3.3.0`); unchanged
- CR-001 `1.0.0` unchanged
- No real CR-001 private candidate creation, gallery publication, or PR-CR-003B

## Change

PR-CR-003A: private creative gallery candidate schema, create/verify CLI,
local HTML preview (file:// to import PNG; no raster copy into candidate dir
or git), synthetic tests, and docs. Public gallery/Pages behavior unchanged.

## Validation

- Focused: `tests/test_private_gallery_candidate.py` — 13 passed
- Inventory/sdist — passed after commit
- Full: `1085 passed, 13 skipped` (pre-commit sdist flake resolved by commit)
- `python aipf_packaging/stage_knowledge.py verify` — OK 104 files
- `python scripts/validate_repo.py` — ok

## Next task

Owner review of PR #41. Do not merge without separate approval. Do not create
the real CR-001 private candidate without separate authorization.
