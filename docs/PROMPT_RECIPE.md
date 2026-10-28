# PromptRecipe v1

Static, versioned creative specifications for AI Image Prompt Factory.

A **PromptRecipe** is a thin identity and revision wrapper around an existing
semantic specification. It is not a second compiler, templating engine, or
variable system.

```text
PromptRecipe
    ↓ validation (envelope + lint_spec)
Existing semantic_spec
    ↓ unchanged
compile_result()
    ↓ unchanged
Compiled prompt + recipe receipt
```

## Schema

File: `data/schemas/prompt_recipe.schema.json` (Draft 2020-12).

Required fields:

| Field | Constraint |
| --- | --- |
| `recipe_schema_version` | Must be `"1.0"` |
| `recipe_id` | Lowercase slug (`example-recipe`) |
| `recipe_version` | Three-component numeric (`1.0.0`) |
| `title` | Nonempty string |
| `semantic_spec` | Complete object accepted by `request.schema.json` |

Optional: `description`.

The envelope is closed (`additionalProperties: false`). PR4-style `variables`,
override maps, and other extension fields are rejected.

Embedded `semantic_spec` values are validated independently with the existing
request schema and `lint_spec()` semantic gates. The recipe layer does not
duplicate the semantic schema.

## Runtime API

Module: `aipf.recipes`

- `load_recipe(path)` — read JSON; no compilation
- `validate_recipe(recipe)` — envelope + semantic findings (errors vs warnings)
- `resolve_recipe(recipe)` — deep copy of `semantic_spec` (value-identical)
- `compile_recipe(recipe)` — call `compile_result` and return a receipt envelope

Resolution never injects defaults, rewrites locks, chooses transformations, or
inserts recipe metadata into the semantic specification.

## Deterministic hashing

Canonical serialization:

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
```

SHA-256 digests:

- **recipe_sha256** — complete validated recipe object
- **semantic_spec_sha256** — embedded specification only
- **prompt_sha256** — exact UTF-8 bytes of the compiled prompt
- **evidence_snapshot_sha256** — from the compiler evidence snapshot

Receipts contain no timestamps, UUIDs, host paths, or other nondeterministic
fields. Content hashes detect change; they do not prove global revision
uniqueness across external copies.

Published recipe revisions are **intended to be immutable**. PR3 does not
provide a registry, overwrite command, or automatic version migration.

## Compilation receipt

Successful `compile_recipe` / `aipf recipe compile --json` returns:

```json
{
  "recipe": {
    "recipe_id": "...",
    "recipe_version": "...",
    "recipe_schema_version": "1.0",
    "recipe_sha256": "...",
    "semantic_spec_sha256": "..."
  },
  "compilation": {},
  "prompt_sha256": "...",
  "compiler_version": "...",
  "evidence_snapshot_sha256": "..."
}
```

`compilation` is the existing `compile_result()` dictionary without changes.

A receipt does **not** imply image generation, model verification, scientific
evaluation, or independent human review.

## CLI

```bash
aipf recipe validate recipe.json
aipf recipe compile recipe.json
aipf recipe compile recipe.json --json
```

- **validate** — recipe + semantic validation only; nonzero exit on errors
- **compile** (plain) — exact compiled prompt on stdout (no banners/metadata)
- **compile --json** — receipt envelope

Legacy commands (`compile`, `lint`, `classify`, `audit`, `evidence`) are
unchanged and do not auto-detect recipes. PR3 does not add profile overrides
for recipe compile; the embedded specification controls compilation.

## Boundaries

Recipes may carry existing symbolic reference IDs and roles unchanged.
Identity locks and reference-role restrictions remain authoritative.

Not in scope for PromptRecipe v1 / PR3:

- Constrained variables (PR4)
- PromptCollection / PromptPack / marketplace
- Image generation or model adapters
- Reference binary packaging
- Scientific EXP-019 workflows
- Automatic version migration
