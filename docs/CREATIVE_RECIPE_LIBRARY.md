# Creative Recipe Library (PR-CR-001)

Engineering documentation for the worktree PromptRecipe collection under
`recipes/`. This track delivers original, versioned creative recipes on top of
existing V3.4 PromptRecipe v1.0/v1.1 infrastructure. It is **not** a product
release, empirical result, gallery publication, or PyPI change.

## Locate and validate CR-001

| Field | Value |
| --- | --- |
| Path | `recipes/cr-001-material-driven-fashion-editorial/1.0.0.json` |
| `recipe_id` | `cr-001-material-driven-fashion-editorial` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |

```bash
aipf recipe validate recipes/cr-001-material-driven-fashion-editorial/1.0.0.json
aipf recipe compile recipes/cr-001-material-driven-fashion-editorial/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Versioning

- Folder name equals `recipe_id`.
- File stem equals `recipe_version` (`MAJOR.MINOR.PATCH`).
- Published revisions are intended to be **immutable**. Do not edit a released
  file in place; add a new version file instead.
- Compile receipts expose `recipe_sha256`, `semantic_spec_sha256`, and
  `prompt_sha256` for change detection (see [PROMPT_RECIPE.md](PROMPT_RECIPE.md)).
- Tests reject duplicate `(recipe_id, recipe_version)` pairs in `recipes/`.

## What is static in CR-001

These elements are authored into the baseline `semantic_spec` and are **not**
v1.1 variables:

- Living editorial request and locks
- Route `new_generation`
- Identity `identity_unlocked`; body mode `presentation_only`
- Empty historical packs; `art.method` / form / state all `null`
- Garment construction, silhouette, fabric drape, and material response
- Hair (sleek low chignon) and makeup (editorial polished with skin texture)
- Pose / weight / hand logic
- Foreground / midground / background atmosphere
- Micro-story

## Supported variations (v1.1 allowlist only)

Optional enum variables (at most three; baselines included in choices):

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline three-quarter full-length; low full-length; medium-long bodice focus |
| `light` | `director.light_source` | baseline soft key+fill+rim; narrower key; broader near-frontal soft key |
| `aspect` | `output.aspect_ratio` | `4:5` (baseline), `1:1` |

There is **no** garment, hairstyle, makeup, or material interpolation engine.
Changing those requires a new `recipe_version`.

## Why V2 creative references stay authoring-only

`references/wardrobe/`, `hair/`, `makeup/`, `poses/`, and `environments/` are
curated taxonomies without PromptRecipe/compiler loaders. PR-CR-001 does not add
runtime loaders or pack families. Authors may read them for vocabulary; the
compiler resolves only the embedded `semantic_spec`.

## Why PromptPack / StylePack / templates are absent

PromptRecipe deliberately excludes PromptCollection / PromptPack / marketplace
and free-form templating ([PROMPT_RECIPE.md](PROMPT_RECIPE.md) boundaries).
StylePack and ArtifactPack are not defined for this PR. Creative reuse is the
versioned recipe file plus the closed v1.1 override allowlist.

## Why no gallery image is attached

PR-CR-001 is recipe-library only. Authentic gallery publication, raster policy
reconciliation, and recipe-to-generation provenance binding are reserved for
later authorized PRs (PR-CR-002 / PR-CR-003). Status enums alone do not prove
publication rights or generation authenticity.

## Packaging note

`recipes/` is a **worktree** library. It is not added to
`aipf_packaging/resource_inventory.json` in this PR.

## Provenance (PR-CR-002)

Recipe→generation binding, private staging, and evidence limits are documented
in [CREATIVE_RECIPE_PROVENANCE.md](CREATIVE_RECIPE_PROVENANCE.md). Use
`scripts/creative_recipe_generation.py prepare|verify` for offline bundles.
Live image generation and gallery publication remain separately authorized.
