# Session Handoff

- Date: 2026-10-28
- Branch: `feat/prompt-recipe-foundation`; base `main`: `88f51a10a87d6600bf84bf280cb8d18fc084e8c4` (PR2 merge)
- Worktree: `D:\1_PROJECT\AI_Kits\AI Image Prompt Factory\IDEA_POOL\ai-image-prompt-factory`
- Stable release: V3.3; V3.4 empirical validation and release remain pending.

## Change

PR3 static versioned PromptRecipe foundation: closed `prompt_recipe.schema.json`,
`aipf.recipes` load/validate/resolve/compile with deterministic receipt hashes,
`aipf recipe validate|compile[--json]` CLI, packaging inventory 100 resources
(+`prompt_recipe.schema.json`), docs and tests. Thin wrapper around existing
`compile_result()` — no compiler, TransformationPack, lexicon, model-adapter,
or EXP-019 scientific changes.

## Validation

- `python -m pytest -q`: 938 passed, 13 skipped
- Recipe-focused: 33 passed; seven-case source/recipe parity exact
- Isolated tracked-only `validate_repo.py`: ok
- `aipf regress`: 19/19
- `aipf baseline-check`: 10/10 stable
- Portability: inventory/wheel/sdist/recipe CLI installed-wheel checks passed

## Next task

Owner review of local PR3 commit. Do not push, open PR, merge, release, start
PR4, or advance EXP-019 science without authorization.
