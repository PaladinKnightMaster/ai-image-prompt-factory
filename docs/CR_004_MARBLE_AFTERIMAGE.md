# CR-004 Marble Afterimage

Creative Research recipe: **source-backed** V3.4 artifact transformation from the
verified CR-001 fashion photograph into a contemporary free-standing marble
sculpture. PromptRecipe library only in this delivery—no image generation,
custody import, or gallery index changes.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-004-marble-afterimage/1.0.0.json` |
| `recipe_id` | `cr-004-marble-afterimage` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |
| TransformationPack | `portrait_to_volumetric_sculpture` |
| ArtMethodPack | `marble_sculpture` |
| Artifact form / state | `free_standing_statue` / `newly_created` |
| EraPacks | none |

## Source selection

| Field | Value |
| --- | --- |
| Source | Verified CR-001 private original, resolved through local private candidate/import evidence during operator handoff |
| SHA-256 | `0dcf8af6cac15441d5e728f98ac53314442984d3a27a5dd193effa2bac46f41e` |
| Symbolic reference id | `cr001-c0-l0-4x5-source` |
| Roles | `identity`, `pose`, `outfit`, `hairstyle` |

The source PNG was verified byte-identical before recipe authoring. It is **not**
copied into Git. Machine-specific absolute paths stay outside the repository.
Recipe `references[].notes` record the SHA and portable handoff language only;
PromptRecipe does **not** package reference binaries
([PROMPT_RECIPE.md](PROMPT_RECIPE.md) boundaries).

The physical PNG must be attached to the later ChatGPT Images request. The
compiled prompt alone does not contain source image pixels. Attachment
submission is operator-attested/uncaptured under current tooling. This recipe
is a source-conditioned `artifact_transform`, not ordinary `new_generation`.

## Transformation architecture decisions

- Use existing `artifact_transform` + `portrait_to_volumetric_sculpture` (validated
  by compile/lint; matches V3.4 marble bust candidate pattern without Greek EraPack).
- `marble_sculpture` + `free_standing_statue` + `newly_created` for a contemporary
  gallery object, not excavated antiquity.
- Empty historical packs: marble material must not imply Classical Greek
  reconstruction.
- Identity `recognizable_identity`; body `artistic_stylization` for medium
  translation into stone.
- Camera-only v1.1 variables (3 gallery framings); aspect fixed at `4:5`.

## Source-reference submission requirements

Compile/prepare produce **text prompts only**. A filesystem path in notes or
docs is **not** evidence that the model received the image.

| Channel | How the source reaches the model | Provenance today |
| --- | --- | --- |
| ChatGPT Images (manual) | Owner must upload the verified CR-001 PNG as the image input alongside `prompt.txt` | **Operator-attested / uncaptured** unless a future gate records attachment hashes |
| OpenAI Images API (`generate_api.py --image`) | Supported edit-mode reference path exists in tooling | Out of scope for this milestone; not executed |

A filesystem path in text alone is not an attached reference. A SHA-256
identifies bytes; it does not prove the source was uploaded to ChatGPT.
Do not claim application-captured attachment unless a later authorized gate
records it. Do not invent new provenance schema fields in this PR.

## Research sources and mechanisms

| Source | Type | Mechanism used |
| --- | --- | --- |
| AIPF `references/art-methods/marble_sculpture.json` | in-repo ArtMethodPack | Stone continuity, support, tool/finish hierarchy, failure modes |
| AIPF `portrait_to_volumetric_sculpture` pack | in-repo TransformationPack | Portrait → volumetric object delta; avoid living-skin-in-sculpture |
| Getty Villa — Statue of a Draped Woman (collection object) | museum object | Heavy carved drapery as primary sculptural mass language |
| Digital Sculpture Project — VMFA Caligula technical study | sculpture technique | Hidden/weight-bearing supports, plinth contact, block continuity |
| Met marble / polychromy resources (ArtMethodPack citations) | museum | Material behavior; avoid automatic pure-white stereotype |

Artistic photographic interpretation (quiet gallery, restrained light) is labeled
as director framing, not archaeological claim.

## Intended preserved vs changed properties

**Preserve (from source reference):** adult identity recognizability; stance;
gown major silhouette/drape architecture; single figure; adult subject.

**Change:** living flesh/cloth/hair → carved marble volumes; textile speculars →
stone ridge/trough drapery; studio fashion set → contemporary gallery + plinth;
medium is sculpture object, not living photograph with marble filter.

## Creative acceptance criteria (later generation gate)

1. Result reads as a free-standing marble statue, not living marble-skin.
2. Source identity/pose/gown silhouette remain recognizable.
3. Plinth/support and contact shadow are physically plausible.
4. No Classical Greek / excavated antiquity claims in the image.
5. No extra people, logos, or unrelated props.
6. Operator can show the verified CR-001 PNG was the image input used.

## Known limitations

- Single photograph cannot prove exact 3D reconstruction.
- Models often leave living skin patches, floating hair, or cloth physics.
- ChatGPT Web attachment is not currently hash-captured by prepare/verify.
- Deterministic compile ≠ demonstrated visual success.

## Digests

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `232f1fe8f9ab20dc33e5aa70c2469ae02b05e12214214bfedff9d18a666b67c2` |
| Baseline compiled prompt (c0 / 4:5) | `f42f2631e644e037c70ac2bf959c2587eff26fb981ae97dd169cf057b0d3d02d` |

## Baseline compiled prompt audit

- Route/transform: `artifact_transform` with portrait → volumetric_sculpture.
- Reference discipline names `cr001-c0-l0-4x5-source` with identity/pose/outfit/hairstyle.
- Marble ArtMethod + free-standing form + newly_created state present.
- Support, carved drapery, gallery light present; living-skin avoidances present.
- Explicit negation of Classical Greek reconstruction / excavated antiquity.
- Aspect `4:5`. No Song/fashion-product leakage from CR-002/CR-003.

## Manual ChatGPT Images feasibility

Feasible as an **owner-operated** later gate:

1. Prepare recipe baseline under D: private root (separate authorization).
2. Upload verified CR-001 PNG (`0dcf8af6…f41e`) as the image input.
3. Paste adapter-effective `prompt.txt`.
4. Attest attachment + prompt submission; import output with existing manual tools.

Not authorized in this milestone.

## Validation commands

```bash
aipf recipe validate recipes/cr-004-marble-afterimage/1.0.0.json
aipf recipe compile recipes/cr-004-marble-afterimage/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Out of scope

Image generation, CR-001–003 edits, private gallery index changes, compiler or
pack expansion, EXP-019 / ESR / AIQ claims, merge without owner approval.
