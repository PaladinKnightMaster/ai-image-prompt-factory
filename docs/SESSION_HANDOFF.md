# Session Handoff

- Date: 2026-10-28
- Branch: `feat/v34-installed-package-portability`; base `main`: `5940b5f1d5e566a61f823a9781e8679a504cfd80` (merged PR1 / PR #30)
- Worktree: `D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\ai-image-prompt-factory`
- Stable release: V3.3; V3.4 empirical validation and release remain pending.

## Change

PR2 installed-package portability plus post-review corrections: reliable
`PackagedResourceWriteError` write guard for installed `_knowledge`, sdist
file-list filtering through `resource_inventory.json` (canary-proof), and a
BOM-free commit subject. Canonical knowledge remains repository trees; wheels
receive the derived allowlisted copy. No compiler, TransformationPack, lexicon
concept, model-adapter, or EXP-019 scientific changes.

## Validation

- `python -m pytest -q`: 902 passed, 13 skipped
- `python scripts/validate_repo.py`: ok on an isolated tracked-only tree
  (original untracked `.superpowers` UTF-16 JSON files preserved; dirty
  worktree still trips the pre-existing recursive JSON scan)
- `aipf regress`: 19/19; exit 0
- `aipf baseline-check regression/baselines/golden_baselines.json`: 10/10 stable
- Portability suite: write-guard negatives, sdist inventory exactness, canary
  exclusion, wheel / sdist / wheel-from-sdist, clean-install parity

## Next task

Owner review of correction commit, then authorized draft PR push/create only.
Do not start PR3 or EXP-019 scientific work from this branch.
