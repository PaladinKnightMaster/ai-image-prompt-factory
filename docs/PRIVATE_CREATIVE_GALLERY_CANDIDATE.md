# Private Creative Gallery Candidate (PR-CR-003A)

Private-only linkage between a verified PromptRecipe preparation bundle, a
`chatgpt_web_manual` import, qualitative creative-review notes, and a local HTML
preview. This is **not** public gallery publication (PR-CR-003B), not Pages
deployment, and not EXP-019 / ESR / AIPF-AIQ scientific evaluation.

## Policy B

1. Stage candidates under the **external** private creative custody tree
   (for example `…/06_private_gallery_candidates/<candidate_id>/`).
2. Keep rasters and candidate JSON **outside** the git repository.
3. Require separate owner rights review + publication approval before any
   public promotion.
4. Public `website/generate_gallery.py` / `website/generated` / Pages remain
   unchanged and continue to fail closed for unpublished assets.

## Storage layout (private disk only)

```text
AIPF_Creative_Private/.../cr001-…/
  01_preparation_immutable/     # prep (unchanged)
  04_chatgpt_web_raw_immutable/ # custody original (unchanged)
  05_chatgpt_web_import/        # manual import (unchanged)
  06_private_gallery_candidates/
    <candidate_id>/
      candidate.json            # schema: creative_gallery_candidate
      preview.html              # local file:// preview; references import PNG
```

The candidate directory must **not** contain PNG copies. The preview references
the verified import `original.png` by absolute `file://` URI.

Forbidden destinations: `website/generated`, any `cases/` path, and the git
repository tree.

## Operator commands (future authorized use)

```powershell
python scripts/creative_recipe_generation.py create-private-gallery-candidate `
  --candidate-id cr-001-c0-l0-4x5-manual `
  --prep-dir C:\path\to\01_preparation_immutable `
  --import-dir C:\path\to\05_chatgpt_web_import `
  --output-dir C:\path\to\06_private_gallery_candidates\cr-001-c0-l0-4x5-manual `
  --expect-image-sha256 0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e `
  --expect-recipe-id cr-001-material-driven-fashion-editorial `
  --expect-recipe-version 1.0.0 `
  --recommendation KEEP `
  --strength "garment architecture" `
  --strength "satin drape" `
  --limitation "one image only" `
  --limitation "model unknown" `
  --non-custody-assessment-sha256 5283b90fdbabf7f38119ba7cae244900b041f2a3aa5f43649b0ad093059d1d68

python scripts/creative_recipe_generation.py verify-private-gallery-candidate `
  C:\path\to\06_private_gallery_candidates\cr-001-c0-l0-4x5-manual

# After a preview-renderer UX update: rewrite only preview.html (owner-operated).
# Verifies the candidate first; preserves candidate.json and all custody evidence.
python scripts/creative_recipe_generation.py refresh-private-gallery-preview `
  C:\path\to\06_private_gallery_candidates\cr-001-c0-l0-4x5-manual

# Open preview.html locally in a browser (private machine only)
```

Creation always re-verifies prep + import, recomputes image digests, and refuses
mismatches, API-origin claims, and non-empty destinations.

## Private preview presentation (PR-CR-003A-UX1 / UX2 / UX3)

`preview.html` is an offline, image-first editorial page generated from
`candidate.json` plus the linked adapter-effective prompt. It uses local CSS
only (no CDN fonts, analytics, or network assets). The only permitted script is
a reviewed inline **Copy prompt** handler (`<script id="aipf-copy-prompt">`)
that copies the verified adapter-effective prompt via `navigator.clipboard`
with a local selectable/`execCommand` fallback for `file://` browsers. No
external script URLs or telemetry.

Primary scan path: hero image → title → compact core-spec badges (version,
decision, aspect, optional `cN`/`lN` chips, channel, private) → compiled
prompt (with header **Copy prompt** control) → qualitative review. Long
camera/lighting prose and recipe/candidate identifiers live under **Advanced
details**. Technical hashes and authenticity limits remain under collapsible
**Provenance**. Refreshing the preview never publishes and never modifies
`candidate.json`.

## Contract highlights

| Field | PR-CR-003A value |
| --- | --- |
| `candidate_status` | `private_candidate` |
| `generation_channel` | `chatgpt_web_manual` |
| `evidence_level` | `locally_verified_manual_import` |
| `model_identity.status` | `unknown` |
| `rights_review_status` | `pending` |
| `publication_approval_status` | `pending` |
| `chatgpt_effective_prompt_known` | `false` |
| `qualitative_review.scientific_claims` | `false` |

Schema: `data/schemas/creative_gallery_candidate.schema.json`.

Local manual-import hash consistency is **not** independent provider-origin
proof. Operator-attested prompt submission is not an independently captured
ChatGPT paste unless a capture file was used at import time.

## Why candidates are not public

- Public gallery only renders images with publishable statuses and files next
  to case records.
- Repo raster quarantine forbids committing PNGs under `cases/`.
- Pages deploys only `website/generated`.
- Manual-import source records remain `publication_status: private_only`.
- Promotion requires a separately authorized PR-CR-003B with rights clearance
  and owner publication approval.

## Separations

- Not API generation provenance (`locally_verified_generation`).
- Not EXP-019 host-native science.
- Not ESR scoring or AIPF-AIQ claims.
- Does not modify CR-001 recipe bytes.
