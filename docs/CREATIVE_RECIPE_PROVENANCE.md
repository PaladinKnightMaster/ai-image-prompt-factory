# Creative Recipe → Generation Provenance (PR-CR-002)

Offline bridge between versioned **PromptRecipe** compile receipts and
**generation metadata** / local asset digests. This is engineering provenance
for the Creative Research track. It is **not** EXP-019 scientific provenance,
not gallery publication, and not independent third-party attestation.

## Identity chain

```text
recipe_id + recipe_version + recipe_schema_version
  → recipe_sha256 (immutable definition)
  → semantic_spec_sha256 (baseline embedded spec)
  → effective bindings (+ submitted/effective/resolved hashes for v1.1)
  → compile_recipe receipt
  → exact UTF-8 prompt + prompt_sha256
  → generation metadata (same prompt_sha256)
  → optional local output.png + result.output_sha256
```

Definition hashes (`recipe_sha256`, baseline `semantic_spec_sha256`) are stable
across bindings. Per-variation hashes (`resolved_semantic_spec_sha256`,
`prompt_sha256`, `output_sha256`) change with bindings or attempts.

## Exact prompt integrity

- Prompt bytes are UTF-8 without BOM.
- The V3.4 compiler ends prompts with a single trailing newline after an
  internal strip. `normalize_request` strips again for CLI compatibility.
- Provenance therefore records:
  - `prompt_sha256` — digest of **compiler** `receipt.compilation.prompt`
  - `adapter_prompt_sha256` — digest of `compilation.prompt.strip()` (API path)
- Bundle `compiler_prompt.txt` stores the compiler form; `prompt.txt` stores the
  adapter-effective form used with generation metadata `prompt_sha256`.
- Unexpected leading/trailing whitespace beyond that documented pair fails closed.

## `creative_provenance` on generation metadata

Optional object on `data/schemas/generation_metadata.schema.json`. Required only
when a record claims PromptRecipe origin. Legacy metadata without the object
remains valid.

Key fields: recipe identity, recipe/semantic/prompt/receipt digests, compiler
version, and (for v1.1) binding hashes and `effective_bindings`.

## Private staging

```bash
python scripts/creative_recipe_generation.py prepare \
  recipes/cr-001-material-driven-fashion-editorial/1.0.0.json \
  --output-dir /absolute/private/bundle \
  --bindings bindings.json

python scripts/creative_recipe_generation.py verify /absolute/private/bundle \
  --expect-recipe-id cr-001-material-driven-fashion-editorial \
  --expect-recipe-version 1.0.0
```

- Staging path must be absolute, or relative under `AIPF_CREATIVE_OUTPUT_PATH`.
- Paths under `website/generated` are refused.
- Preparation is **dry-run only** (no network).
- Existing files are not overwritten unless `--force`.
- Do not commit rasters; repository quarantine remains.

Bundle files: `manifest.json`, `receipt.json`, `prompt.txt`, `generation.json`,
`bindings.json`, `adapter_request_preview.json`, optional later `output.png`.

## Evidence authenticity limitations

| Level | Meaning |
| --- | --- |
| `compilation_consistent` | Locally verifiable compilation integrity: receipt ↔ prompt ↔ dry-run metadata |
| `locally_verified_generation` | Locally verifiable **API-path** generation + asset integrity (completed flag, file, digest match) |
| `locally_verified_manual_import` | Locally verifiable **ChatGPT Web manual** import: PNG bytes, custody/expect hash, recipe linkage (PR-CR-002A) |
| `incomplete_or_unverifiable` | Dry-run with invalid completion claims, URL-only, missing/mismatched asset, or failed checks |
| `provider_confirmed_partial` | **Reserved.** Not granted by offline verification of self-authored metadata |

Distinguish carefully:

- **Locally verifiable:** recipe/prompt/receipt digests, adapter prompt bytes, binding equality, local `output_sha256` match.
- **Recorded but unverified:** a non-null `provider_verified_model_id` in editable `generation.json` is a **claim**, not proof of a provider event. It does not raise `evidence_level`.
- **Not currently authenticated:** true provider-origin confirmation requires a future separately authorized attestation channel. PR-CR-002 does not implement it.

`ok: true` means local checks passed. It does **not** imply independent provider confirmation. Never invent `provider_verified_model_id`. Hash matches in self-authored JSON are not third-party attestation. Operator attestations remain out-of-band.

## Successful vs incomplete records

- **Incomplete:** `dry_run: true`, `generation_completed: false`, URL transport,
  missing image, digest mismatch.
- **Locally successful (engineering):** `dry_run: false`, `generation_completed: true`,
  `transport: b64_json`, file digest matches `result.output_sha256`, provenance
  block matches receipt.

Live `--execute` via `scripts/generate_api.py` requires **separate** owner
authorization. PR-CR-002 does not perform it.

## Camera c2 note (campaign policy only)

CR-001 may still declare camera choice c2. The **first authorized visual-test
campaign** excludes c2 because of framing ambiguity (CR-GATE-003). Allowed
campaign space when separately authorized: cameras c0–c1 × lights l0–l2 ×
aspects `4:5`/`1:1` (12 combinations). This document does not authorize running
them.

## Gallery separation

PR-CR-003 only. No automatic copy into `website/generated/`. Rights review and
owner publication approval remain independent of generation success.

## ChatGPT Web manual import (PR-CR-002A)

Manual ChatGPT Images downloads are a **distinct** channel from OpenAI Images
API generation. They use `record_kind: chatgpt_web_manual_source`,
`generation_channel: chatgpt_web_manual`, and evidence level
`locally_verified_manual_import`. Schema:
`data/schemas/chatgpt_web_manual_source.schema.json`.

This channel never writes API `transport` / `b64_json` fields, never sets
`provider_verified_model_id`, and cannot reach `provider_confirmed_partial`.

### Prompt-submission evidence (three concepts)

1. **Intended prompt** — verified AIPF preparation `prompt.txt` (adapter form)
   and receipt digests. Always recorded and locally verified.
2. **Operator-submitted prompt** — what the owner reports pasting into ChatGPT.
3. **Independently captured prompt evidence** — only when a separate capture
   file is preserved. The importer never copies preparation `prompt.txt` and
   labels it as ChatGPT capture evidence.

Rules:

- `--submitted-prompt <file>`: capture bytes must **exactly** equal preparation
  `prompt.txt`. Stored as `submitted_prompt_capture.txt` with
  `submission_verification: exact_match`.
- `--operator-attests-prompt-submission`: allowed when no capture exists.
  Records `independent_capture_status: unavailable` and
  `submission_verification: operator_attested_uncaptured`. No capture file is
  written.
- `chatgpt_effective_prompt_known` is always `false`.

### PowerShell operator workflow

```powershell
# 1) Prepare (once) into private storage — existing PR-CR-002 command
python scripts/creative_recipe_generation.py prepare `
  recipes/cr-001-material-driven-fashion-editorial/1.0.0.json `
  --output-dir C:\path\to\01_preparation_immutable `
  --bindings C:\path\to\bindings.json

# 2) Owner generates in ChatGPT Images using the preparation prompt.txt text,
#    downloads the PNG, and preserves original bytes + custody outside the repo.

# 3) Confirm digest
Get-FileHash -Algorithm SHA256 -LiteralPath C:\path\to\04_raw\image.png

# 4) Import (does not move or modify the preserved original)
python scripts/creative_recipe_generation.py import-chatgpt-web `
  --prep-dir C:\path\to\01_preparation_immutable `
  --image C:\path\to\04_raw\image.png `
  --custody C:\path\to\04_raw\download_custody.txt `
  --output-dir C:\path\to\05_chatgpt_web_import `
  --expect-image-sha256 <64-hex> `
  --operator-attests-prompt-submission `
  --attestation-note "Pasted preparation prompt.txt into ChatGPT Images"

# Or, when an independently captured submitted-prompt file exists:
#   --submitted-prompt C:\path\to\captured_submission.txt

python scripts/creative_recipe_generation.py verify-chatgpt-web `
  C:\path\to\05_chatgpt_web_import
```

Import refuses non-empty destinations and never overwrites import assets (no
`--force` in this MVP). Paths under `website/generated` (and repository
`cases/`) are refused. `publication_status` remains `private_only`. Private
gallery candidate staging (metadata + local preview only) is PR-CR-003A; see
[PRIVATE_CREATIVE_GALLERY_CANDIDATE.md](PRIVATE_CREATIVE_GALLERY_CANDIDATE.md).
Public Pages promotion remains PR-CR-003B and requires separate owner
authorization.

## Backward compatibility

- Non-recipe generation metadata unchanged and still schema-valid.
- PromptRecipe envelopes unchanged; CR-001 `1.0.0` unchanged.
- Existing `scripts/generate_api.py` executor unchanged as the sole live API path.
- ChatGPT web import is additive and does not alter API provenance semantics.
