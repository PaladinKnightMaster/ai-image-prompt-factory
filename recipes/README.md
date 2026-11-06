# Creative PromptRecipe library

Worktree collection of original, versioned **PromptRecipe** instances for the
Creative Research track. Recipes wrap a complete V3.4 `semantic_spec` and use
the existing `aipf.recipes` validate/compile APIs. This is not a PromptPack,
StylePack, marketplace, or template engine.

## Layout

```text
recipes/
  README.md
  <recipe_id>/
    <recipe_version>.json    # immutable published revision
```

- **`recipe_id`** — stable lowercase slug (must match the folder name).
- **`recipe_version`** — three-component numeric version (must match the file stem).
- **`recipe_schema_version`** — `"1.0"` or `"1.1"` inside the JSON envelope.

Released `(recipe_id, recipe_version)` pairs must not be silently rewritten.
Ship corrections as a new `recipe_version` file. Content hashes in compile
receipts detect change; they do not enforce global uniqueness across external
copies.

Duplicate `(recipe_id, recipe_version)` pairs across this tree are rejected by
`tests/test_creative_recipe_library.py`.

## Current recipes

| Recipe ID | Version | Title | Schema |
| --- | --- | --- | --- |
| `cr-001-material-driven-fashion-editorial` | `1.0.0` | CR-001 Material-Driven Fashion Editorial | `1.1` |
| `cr-002-song-corridor-editorial` | `1.0.0` | CR-002 Song Corridor Editorial | `1.1` |
| `cr-003-refraction-ledger` | `1.0.0` | CR-003 Refraction Ledger | `1.1` |
| `cr-004-marble-afterimage` | `1.0.0` | CR-004 Marble Afterimage | `1.1` |
| `cr-005-silk-on-plaster` | `1.0.0` | CR-005 Silk on Plaster | `1.1` |
| `cr-006-held-light` | `1.0.0` | CR-006 Held Light — Multi-Reference Fragrance Editorial | `1.1` |
| `cr-007-porcelain-echo` | `1.0.0` | CR-007 Porcelain Echo | `1.1` |
| *(cr-008 blocked)* | — | Golden Fault — localized edit not implemented | — |
| `cr-009-golden-seam` | `1.0.0` | CR-009 Golden Seam — Controlled Whole-Image Revision | `1.1` |
| `cr-010-the-second-angle` | `1.0.0` | The Second Angle — Product Viewpoint Transfer | `1.1` |

## Validate and compile CR-001

From the repository root (source checkout):

```bash
aipf recipe validate recipes/cr-001-material-driven-fashion-editorial/1.0.0.json
aipf recipe compile recipes/cr-001-material-driven-fashion-editorial/1.0.0.json
aipf recipe compile recipes/cr-001-material-driven-fashion-editorial/1.0.0.json --json
```

Optional v1.1 bindings (camera / light / aspect only):

```bash
aipf recipe compile recipes/cr-001-material-driven-fashion-editorial/1.0.0.json --bindings path/to/bindings.json --json
```

Compilation uses the local V3.4 compiler only. It does **not** call an image
provider and does **not** attach gallery outputs.

## Authoring vocabulary vs compiler inputs

The V2-derived files under `references/wardrobe/`, `references/hair/`,
`references/makeup/`, `references/poses/`, and `references/environments/` may
inform human authoring. They are **not** loaded by the compiler in this track
and are not referenced as runtime pack IDs inside recipes.

## Out of scope for this library (PR-CR-001)

- PromptPack / StylePack / ArtifactPack
- Generic template interpolation beyond PromptRecipe v1.1 enum variables
- Wheel knowledge packaging of `recipes/`
- Gallery images, raster policy, or Pages publication (later PR-CR-002 / PR-CR-003)
- EXP-019 / ESR scientific workflows

See also [PROMPT_RECIPE.md](../docs/PROMPT_RECIPE.md) and
[CREATIVE_RECIPE_LIBRARY.md](../docs/CREATIVE_RECIPE_LIBRARY.md).
