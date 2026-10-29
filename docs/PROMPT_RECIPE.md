# PromptRecipe v1 / v1.1

Static, versioned creative specifications for AI Image Prompt Factory.

A **PromptRecipe** is a thin identity and revision wrapper around an existing
semantic specification. It is not a second compiler or free-form templating
engine. Version **1.1** adds an optional closed set of constrained enum
variables that may replace only three authorized scalar destinations before
the unchanged V3.4 compiler runs.

```text
PromptRecipe
    ↓ validation (envelope + variable rules + lint_spec)
Existing semantic_spec  (+ optional constrained substitutions)
    ↓ unchanged compiler
compile_result()
    ↓ unchanged
Compiled prompt + recipe receipt
```

## Schemas

| Version | File |
| --- | --- |
| `1.0` | `data/schemas/prompt_recipe.schema.json` |
| `1.1` | `data/schemas/prompt_recipe_v1_1.schema.json` |

Both are Draft 2020-12. The v1.0 schema is unchanged: PR4 does not modify it.

### Shared envelope

Required fields:

| Field | Constraint |
| --- | --- |
| `recipe_schema_version` | `"1.0"` or `"1.1"` (exact const per schema file) |
| `recipe_id` | Lowercase slug (`example-recipe`) |
| `recipe_version` | Three-component numeric (`1.0.0`) |
| `title` | Nonempty string |
| `semantic_spec` | Complete object accepted by `request.schema.json` |

Optional: `description`.

The envelope is closed (`additionalProperties: false`).

Embedded `semantic_spec` values are validated independently with the existing
request schema and `lint_spec()` semantic gates. The recipe layer does not
duplicate the semantic schema. The baseline specification must be complete and
valid **without** substitution. Placeholders are not used.

### v1.1 constrained variables

Optional `variables` object, at most three entries. Each key is a stable
lowercase ASCII identifier (`^[a-z][a-z0-9_]*$`). Each definition is closed and
requires:

| Field | Constraint |
| --- | --- |
| `type` | Exactly `"enum"` |
| `target` | Exactly one of the approved destinations below |
| `choices` | 2–8 distinct nonempty string literals |
| `required` | Optional boolean; default `false` |
| `description` | Optional string |

Approved destinations only:

- `director.camera`
- `director.light_source`
- `output.aspect_ratio`

For `output.aspect_ratio`, choices are limited to the prompt-composition
vocabulary `"1:1"` and `"4:5"`. These are not image-API size guarantees.

Rules enforced at runtime:

- The existing baseline value at each target must appear in that variable's choices.
- Only one variable may own any given target.
- No independent default values: the embedded semantic specification is the
  optional-variable baseline.
- Director choice strings must be Unicode NFC, within length/UTF-8 bounds, and
  must not contain control characters, newlines, or bidirectional controls.
  These checks are transport/safety bounds, not complete semantic safety;
  authors remain responsible for curating options compatible with each recipe.

Forbidden destinations include request/route, identity and body-transformation
fields, locks, reference roles, TransformationPack / EraPack / ArtMethodPack
selections, historical fields, artifact form/state, requested elements,
evidence, generation flags, lexical profile, compilation parameters, and recipe
metadata.

## Runtime API

Module: `aipf.recipes`

- `load_recipe(path)` — read JSON; rejects duplicate keys and nonstandard numeric constants; no compilation
- `load_bindings(path)` — read a bindings object with the same strict JSON rules
- `validate_recipe(recipe)` — envelope + semantic findings (definition / baseline only)
- `validate_recipe(recipe, bindings)` — also validate an explicit invocation (`{}` reports missing required variables)
- `resolve_recipe(recipe, bindings=None)` — deep copy of baseline or resolved specification
- `compile_recipe(recipe, bindings=None)` — call `compile_result` and return a receipt envelope

v1.0: omitting bindings preserves PR3 behavior. Explicitly submitted bindings
(including `{}`) are rejected because v1.0 does not support them.

v1.1: omitting bindings on `resolve_recipe` / `compile_recipe` is treated as an
empty invocation. `validate_recipe(recipe)` without bindings does not require
invocation values.

Resolution replaces only authorized scalar target values, then re-validates the
resolved specification with existing lint/gates. Automatic semantic repairs are
not applied. For v1.1, any `evidence_retrieval_failure` warning is treated as blocking at
the recipe layer regardless of message wording; general `lint_spec` warning
behavior is otherwise preserved. Director binding diagnostics are length-bounded
and do not echo arbitrarily large submitted values.

## Deterministic hashing

Canonical serialization (unchanged from PR3):

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
```

SHA-256 digests:

- **recipe_sha256** — complete validated recipe object (unmodified definition)
- **semantic_spec_sha256** — embedded baseline specification only
- **prompt_sha256** — exact UTF-8 bytes of the compiled prompt
- **evidence_snapshot_sha256** — from the compiler evidence snapshot

v1.1 receipts additionally include `variable_resolution`:

- `submitted_bindings_sha256`
- `effective_bindings_sha256`
- `resolved_semantic_spec_sha256`
- `effective_bindings`
- `submitted_variable_names` (sorted)

Omitted optional bindings and explicitly submitted baseline values share
effective-binding and resolved-spec hashes; their submitted-binding hashes
differ.

Receipts contain no timestamps, UUIDs, host paths, or other nondeterministic
fields. Content hashes detect change; they do not prove global revision
uniqueness across external copies.

Published recipe revisions are **intended to be immutable**.

## Compilation receipt

Successful `compile_recipe` / `aipf recipe compile --json` returns the PR3
envelope fields. v1.1 adds `variable_resolution` as described above.
`compilation` remains the existing `compile_result()` dictionary without changes.

A receipt does **not** imply image generation, model verification, scientific
evaluation, or independent human review.

## CLI

```bash
aipf recipe validate recipe.json
aipf recipe validate recipe.json --bindings values.json
aipf recipe compile recipe.json
aipf recipe compile recipe.json --bindings values.json
aipf recipe compile recipe.json --bindings values.json --json
```

- **validate** — recipe (+ optional bindings) + semantic validation; exit `1` on errors
- **compile** (plain) — exact compiled prompt on stdout (no banners/metadata)
- **compile --json** — receipt envelope
- argparse usage errors exit `2`

Invalid invocations must not emit compiled prompts. Recipe JSON CLI output and
diagnostics use `ensure_ascii=True` for Windows cp1252-safe transport.

Legacy commands (`compile`, `lint`, `classify`, `audit`, `evidence`) are
unchanged and do not auto-detect recipes.

## Boundaries

Recipes may carry existing symbolic reference IDs and roles unchanged.
Identity locks and reference-role restrictions remain authoritative.

Not in scope for PromptRecipe v1.1 / PR4:

- PromptCollection / PromptPack / marketplace
- Image generation or model adapters
- Reference binary packaging
- Scientific EXP-019 workflows
- Automatic version migration
- Arbitrary JSON Pointer patching or expression evaluation
