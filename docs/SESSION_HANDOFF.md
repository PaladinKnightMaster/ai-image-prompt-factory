# Session Handoff

- Date: 2026-11-03
- Canonical `main` at branch start: `47ca580cb2ced538e29089d1084b8527ddd44f41`
- Feature branch: `feat/pr-cr-003a-ux1-private-preview-redesign`
- Stable release: V3.3 (`v3.3.0`); unchanged
- CR-001 `1.0.0` unchanged
- Real private CR-001 candidate not modified in this PR

## Change

PR-CR-003A-UX1: redesign private candidate `preview.html` as an offline
image-first editorial page; add `refresh-private-gallery-preview` to rewrite
only the derived preview after verification. No publication, no recipe/compiler
changes, no real custody writes during implementation.

## Validation

- Focused: `tests/test_private_gallery_candidate.py` — 16 passed
- Full pytest / `validate_repo.py` — see PR checks

## Next task

Owner review of the UX PR. After merge, owner may run
`refresh-private-gallery-preview` on the real CR-001 private candidate
directory (separate authorization already implied by post-merge acceptance).
Do not start PR-CR-003B without separate approval.
