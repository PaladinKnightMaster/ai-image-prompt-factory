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

## Locate and validate CR-002

| Field | Value |
| --- | --- |
| Path | `recipes/cr-002-song-corridor-editorial/1.0.0.json` |
| `recipe_id` | `cr-002-song-corridor-editorial` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |

Research brief, sources, and EraPack limitations:
[CR_002_SONG_CORRIDOR_EDITORIAL.md](CR_002_SONG_CORRIDOR_EDITORIAL.md).

```bash
aipf recipe validate recipes/cr-002-song-corridor-editorial/1.0.0.json
aipf recipe compile recipes/cr-002-song-corridor-editorial/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-002

- Living photographic editorial request and locks (adult subject; no fantasy
  xianxia; no Tang/Qing default styling; historically informed, not reconstruction)
- Route `new_generation`
- Identity `identity_unlocked`; body mode `presentation_only`
- EraPack `song` only; `art.method` / form / state all `null`
- Beizi + ruqun layering, restrained hair, timber corridor staging, daylight
- Pose / weight / hand logic, spatial depth, micro-story

### Supported variations (CR-002)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline corridor-axis full-length; low full-length; medium-long beizi focus |
| `light` | `director.light_source` | baseline soft courtyard daylight; narrower side shaft; broader overcast |
| `aspect` | `output.aspect_ratio` | `4:5` (baseline), `1:1` |

## Locate and validate CR-003

| Field | Value |
| --- | --- |
| Path | `recipes/cr-003-refraction-ledger/1.0.0.json` |
| `recipe_id` | `cr-003-refraction-ledger` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |

Research brief, photographic principles, and acceptance criteria:
[CR_003_REFRACTION_LEDGER.md](CR_003_REFRACTION_LEDGER.md).

```bash
aipf recipe validate recipes/cr-003-refraction-ledger/1.0.0.json
aipf recipe compile recipes/cr-003-refraction-ledger/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-003

- Luxury commercial product still-life request and locks (product only; no humans;
  no logos/lettering; photographic material fidelity)
- Route `new_generation`
- Identity `identity_unlocked`; body mode `presentation_only`
- Empty historical packs; `art.method` / form / state all `null`
- Faceted transparent glass flacon, brushed-metal cap, honed limestone plinth
- Studio depth, material response, micro-story

### Supported variations (CR-003)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline eye-level three-quarter hero; elevated plinth-top; tighter glass/cap crop |
| `light` | `director.light_source` | bright-field flags; dark-field luxury; dual strip + negative fill |
| `aspect` | `output.aspect_ratio` | `4:5` (baseline), `1:1` |

## Locate and validate CR-004

| Field | Value |
| --- | --- |
| Path | `recipes/cr-004-marble-afterimage/1.0.0.json` |
| `recipe_id` | `cr-004-marble-afterimage` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |

Research brief, source SHA, and attachment limits:
[CR_004_MARBLE_AFTERIMAGE.md](CR_004_MARBLE_AFTERIMAGE.md).

```bash
aipf recipe validate recipes/cr-004-marble-afterimage/1.0.0.json
aipf recipe compile recipes/cr-004-marble-afterimage/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-004

- Source-backed marble sculpture transformation request and locks
- Route `artifact_transform` with `portrait_to_volumetric_sculpture`
- ArtMethod `marble_sculpture`; form `free_standing_statue`; state `newly_created`
- Empty EraPack list (no Classical Greek reconstruction claim)
- Symbolic reference `cr001-c0-l0-4x5-source` (identity/pose/outfit/hairstyle)
- Identity `recognizable_identity`; body `artistic_stylization`
- Aspect fixed at `4:5`

### Supported variations (CR-004)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline full-statue gallery hero; elevated plinth-top; medium-long drapery emphasis |

## Locate and validate CR-005

| Field | Value |
| --- | --- |
| Path | `recipes/cr-005-silk-on-plaster/1.0.0.json` |
| `recipe_id` | `cr-005-silk-on-plaster` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |

Research brief, source SHA, mural constraints, and attachment limits:
[CR_005_SILK_ON_PLASTER.md](CR_005_SILK_ON_PLASTER.md).

```bash
aipf recipe validate recipes/cr-005-silk-on-plaster/1.0.0.json
aipf recipe compile recipes/cr-005-silk-on-plaster/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-005

- Source-backed mineral-pigment architectural mural transformation request and locks
- Route `artifact_transform` with `portrait_to_architectural_mural`
- ArtMethod `mineral_pigment_mural`; form `wall_surface`; state `newly_created`
- Empty EraPack list (no excavated Song / Dunhuang reconstruction claim)
- Symbolic reference `cr002-c0-l0-4x5-source` (identity/pose/outfit/hairstyle)
- Identity `recognizable_identity`; body `artistic_stylization`
- Aspect fixed at `4:5`

### Supported variations (CR-005)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline three-quarter mural+floor; oblique corner/ceiling continuity; medium-long pigment-drapery emphasis |

## Locate and validate CR-006

| Field | Value |
| --- | --- |
| Path | `recipes/cr-006-held-light/1.0.0.json` |
| `recipe_id` | `cr-006-held-light` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `new_generation` |

Research brief, dual source SHAs, role architecture, and two-image attachment limits:
[CR_006_HELD_LIGHT.md](CR_006_HELD_LIGHT.md).

```bash
aipf recipe validate recipes/cr-006-held-light/1.0.0.json
aipf recipe compile recipes/cr-006-held-light/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-006

- Two-reference luxury fragrance campaign request and locks
- Route `new_generation` (new photographic campaign scene; not medium transform)
- Empty EraPack list; `art.method` / form / state all `null`
- Symbolic reference A `cr001-c0-l0-4x5-source` (`identity`, `outfit`, `hairstyle`)
- Symbolic reference B `cr003-c0-l0-4x5-source` (`artifact` only; no environment/plinth)
- Identity `recognizable_identity`; body `presentation_only` with pose adaptation for grip
- Aspect fixed at `4:5`

### Supported variations (CR-006)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline three-quarter campaign; closer mid-length face+flacon; slightly low vertical gown with mid-torso flacon |

## Locate and validate CR-007

| Field | Value |
| --- | --- |
| Path | `recipes/cr-007-porcelain-echo/1.0.0.json` |
| `recipe_id` | `cr-007-porcelain-echo` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |

Research brief, source SHA, ceramic constraints, and attachment limits:
[CR_007_PORCELAIN_ECHO.md](CR_007_PORCELAIN_ECHO.md).

```bash
aipf recipe validate recipes/cr-007-porcelain-echo/1.0.0.json
aipf recipe compile recipes/cr-007-porcelain-echo/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-007

- Source-backed porcelain decorated-artifact transformation request and locks
- Route `artifact_transform` with `portrait_to_decorated_artifact`
- ArtMethod `blue_white_ceramic`; form `vase`; state `newly_created`
- Selected concept `ceramic.porcelain_body`; empty EraPack list (no Song authenticity / Ming court copy claim)
- Symbolic reference `cr002-c0-l0-4x5-source` (identity/pose/outfit/hairstyle)
- Identity `recognizable_identity`; body `artistic_stylization`
- Aspect fixed at `4:5`

### Supported variations (CR-007)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline eye-level three-quarter vessel hero; slightly elevated shoulder-to-belly curvature wrap |

## CR-008 status (blocked)

| Field | Value |
| --- | --- |
| Proposed `recipe_id` | `cr-008-golden-fault` |
| Proposed version | `1.0.0` |
| Working title | Golden Fault — Localized Porcelain Repair |
| Feasibility | **BLOCKED — LOCAL EDIT CAPABILITY GAP** |
| Recipe path | *not implemented* |

CR-008 requires source-conditioned **localized** editing of the verified CR-007
vase (one gold-lacquer repair on the upper-right shoulder) with a credible
outside-region preservation contract. The installed stack supports whole-image
reference transforms and whole-image API `edit` without mask/ROI transport; it
does not support enforceable local edit semantics. No substitute
`artifact_transform` / `new_generation` recipe was authored.

Research brief, capability matrix, material citations, deferred edit
specification, and comparison plan:
[CR_008_GOLDEN_FAULT.md](CR_008_GOLDEN_FAULT.md).

CR-008 remains research-only and **implementation blocked**. It is not a
completed generated recipe and does not add a gallery card.

## Locate and validate CR-009

| Field | Value |
| --- | --- |
| Path | `recipes/cr-009-golden-seam/1.0.0.json` |
| `recipe_id` | `cr-009-golden-seam` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `reference_transform` |

Whole-image revision (not localized edit) of verified CR-007 porcelain:
[CR_009_GOLDEN_SEAM.md](CR_009_GOLDEN_SEAM.md). Does **not** resolve CR-008.

```bash
aipf recipe validate recipes/cr-009-golden-seam/1.0.0.json
aipf recipe compile recipes/cr-009-golden-seam/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-009

- Source-conditioned whole-image revision request and locks
- Route `reference_transform` (no TransformationPack; not `artifact_transform`)
- `art.method` / form / state all `null` (photographic revision, not medium remake)
- Symbolic reference `cr007-c0-4x5-source` (identity/artifact/environment/layout/palette)
- Identity `recognizable_identity`; body `preserve`
- Aspect fixed at `4:5`; empty `variables` (single embedded baseline camera)
- Explicit non-claims: no mask/ROI, no pixel-exact outside-region preservation

### Supported variations (CR-009)

None in `1.0.0` — single baseline framing only.

## Locate and validate CR-010

| Field | Value |
| --- | --- |
| Path | `recipes/cr-010-the-second-angle/1.0.0.json` |
| `recipe_id` | `cr-010-the-second-angle` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `reference_transform` |

Source-conditioned product viewpoint transfer of verified CR-003 perfume:
[CR_010_THE_SECOND_ANGLE.md](CR_010_THE_SECOND_ANGLE.md). Descriptive camera
only; no numeric yaw field; no 3D-reconstruction claim; does **not** reopen
CR-008.

```bash
aipf recipe validate recipes/cr-010-the-second-angle/1.0.0.json
aipf recipe compile recipes/cr-010-the-second-angle/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-010

- Source-conditioned product viewpoint-transfer request and locks
- Route `reference_transform` (no TransformationPack; not `new_generation`)
- `art.method` / form / state all `null`
- Symbolic reference `cr003-c0-l0-4x5-source` (`artifact` / `environment` / `palette`; no `layout` / `pose` / `identity`)
- Identity `identity_unlocked`; body `presentation_only` with required camera-presentation change
- Aspect fixed at `4:5`; empty `variables` (single embedded baseline camera)
- Explicit non-claims: no numeric camera yaw, no exact 3D reconstruction

### Supported variations (CR-010)

None in `1.0.0` — single baseline three-quarter viewpoint instruction only.

## Locate and validate CR-011

| Field | Value |
| --- | --- |
| Path | `recipes/cr-011-era-reframing/1.0.0.json` |
| `recipe_id` | `cr-011-era-reframing` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `reference_transform` |
| Status | Implemented recipe; generated; owner-accepted; privately gallery-promoted as the tenth card in the accepted ten-card private gallery (`CR-GATE-017`) |

Source-conditioned Tang era reframing of verified CR-001 fashion subject:
[CR_011_ERA_REFRAMING.md](CR_011_ERA_REFRAMING.md). Historically informed (not
reconstruction); no TransformationPack; does **not** reopen CR-008.

```bash
aipf recipe validate recipes/cr-011-era-reframing/1.0.0.json
aipf recipe compile recipes/cr-011-era-reframing/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-011

- Source-conditioned photographic era-reframing request and locks
- Route `reference_transform` (no TransformationPack; not `new_generation`)
- EraPack `tang`; strictness `historically_informed`
- `art.method` / form / state all `null`
- Symbolic reference `cr001-c0-l0-4x5-source` (`identity` / `pose` / `layout`; no `outfit` / `hairstyle` / `environment` / `palette`)
- Identity `recognizable_identity`; body `preserve` with required garment change
- Aspect fixed at `4:5`; empty `variables` (single embedded baseline)
- Explicit non-claims: no pixel-exact identity, no masked local edit, no dated reconstruction

### Supported variations (CR-011)

None in `1.0.0` — single baseline Tang court-leisure reframing only.

## Locate and validate CR-012

| Field | Value |
| --- | --- |
| Path | `recipes/cr-012-keyblock-echo/1.0.0.json` |
| `recipe_id` | `cr-012-keyblock-echo` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `artifact_transform` |
| Status | Implemented recipe; generated; owner-accepted; privately gallery-promoted as the eleventh card in the accepted eleven-card private gallery (`CR-GATE-017`) |

Source-backed V3.4 relief-print transformation of verified CR-001 fashion
subject into a Japanese woodblock-inspired print sheet:
[CR_012_KEYBLOCK_ECHO.md](CR_012_KEYBLOCK_ECHO.md). Uses installed
`portrait_to_relief_print` + `japanese_woodblock_print` + `print_sheet`; no
EraPack; does **not** reopen CR-008.

```bash
aipf recipe validate recipes/cr-012-keyblock-echo/1.0.0.json
aipf recipe compile recipes/cr-012-keyblock-echo/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-012

- Source-backed relief-print request and locks
- Route `artifact_transform` with TransformationPack `portrait_to_relief_print`
- ArtMethod `japanese_woodblock_print`; form `print_sheet`; state `newly_created`
- Empty EraPack list; no Edo authenticity claim
- Symbolic reference `cr001-c0-l0-4x5-source` (`identity` / `pose` / `outfit` / `hairstyle`)
- Identity `recognizable_identity`; body `artistic_stylization` for medium translation
- Aspect fixed at `4:5`; camera-only v1.1 variables
- Explicit non-claims: no authenticated Edo production, no anime/ink-wash substitution

### Supported variations (CR-012)

| Variable key | Target | Choices |
| --- | --- | --- |
| `camera` | `director.camera` | baseline full-figure sheet; elevated sheet-table; medium-long contour/color emphasis |

## Locate and validate CR-013

| Field | Value |
| --- | --- |
| Path | `recipes/cr-013-silkline-portrait/1.0.0.json` |
| `recipe_id` | `cr-013-silkline-portrait` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `art_style_transform` |
| Status | Implemented recipe; generated; owner-accepted; privately gallery-promoted as the twelfth card in the accepted twelve-card private gallery (`CR-GATE-017`) |

Source-conditioned gongbi-inspired meticulous figure painting of verified CR-001
fashion subject on an album-leaf support:
[CR_013_SILKLINE_PORTRAIT.md](CR_013_SILKLINE_PORTRAIT.md). Uses installed
`art_style_transform` + `gongbi_painting` + `album_leaf`; no TransformationPack;
no EraPack; does **not** reopen CR-008 or CR-012.

```bash
aipf recipe validate recipes/cr-013-silkline-portrait/1.0.0.json
aipf recipe compile recipes/cr-013-silkline-portrait/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-013

- Source-conditioned gongbi painting request and locks
- Route `art_style_transform` (no TransformationPack; not `artifact_transform`)
- ArtMethod `gongbi_painting`; form `album_leaf`; state `newly_created`
- Empty EraPack list; no dynasty or named-artist authenticity claim
- Symbolic reference `cr001-c0-l0-4x5-source` (`identity` / `pose` / `outfit` / `hairstyle`)
- Identity `recognizable_identity`; body `artistic_stylization` for medium translation
- Aspect fixed at `4:5`; empty `variables` (single embedded baseline)
- Explicit non-claims: no woodblock/relief-print process, no ink-wash/anime substitution, no historical costume replacement, no generation in this PR

### Supported variations (CR-013)

None in `1.0.0` — single baseline full-figure album-leaf gongbi framing only.

## Locate and validate CR-014

| Field | Value |
| --- | --- |
| Path | `recipes/cr-014-inkflow-figure/1.0.0.json` |
| `recipe_id` | `cr-014-inkflow-figure` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `art_style_transform` |
| Status | Implemented recipe; generated; owner-accepted; privately gallery-promoted as the thirteenth card in CR-GATE-017 |

Source-conditioned expressive Chinese ink figure painting of verified CR-001
fashion subject on an absorbent album-leaf support:
[CR_014_INKFLOW_FIGURE.md](CR_014_INKFLOW_FIGURE.md). Uses installed
`art_style_transform` + `chinese_ink_painting` + `album_leaf`; no TransformationPack;
no EraPack; does **not** reopen CR-008, CR-012, or CR-013.

```bash
aipf recipe validate recipes/cr-014-inkflow-figure/1.0.0.json
aipf recipe compile recipes/cr-014-inkflow-figure/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-014

- Source-conditioned expressive ink painting request and locks
- Route `art_style_transform` (no TransformationPack; not `artifact_transform`)
- ArtMethod `chinese_ink_painting`; form `album_leaf`; state `newly_created`
- Empty EraPack list; no dynasty or named-artist authenticity claim
- Symbolic reference `cr001-c0-l0-4x5-source` (`identity` / `pose` / `outfit` / `hairstyle`)
- Identity `recognizable_identity`; body `artistic_stylization` for medium translation
- Hierarchical preservation: major gown architecture locked; minor folds/seams omittable
- Aspect fixed at `4:5`; empty `variables` (single embedded baseline)
- Explicit non-claims: no gongbi fine-line substitution, no woodblock/relief-print process, no fake calligraphy/seals, no historical costume replacement, no generation in this PR

### Supported variations (CR-014)

None in `1.0.0` — single baseline full-figure album-leaf expressive-ink framing only.

## Locate and validate CR-015

| Field | Value |
| --- | --- |
| Path | `recipes/cr-015-cut-space-portrait/1.0.0.json` |
| `recipe_id` | `cr-015-cut-space-portrait` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `art_style_transform` |
| Status | Implemented recipe; generation pending; not gallery-accepted |

Source-conditioned layered-paper pop-up diorama of verified CR-001 fashion
subject:
[CR_015_CUT_SPACE_PORTRAIT.md](CR_015_CUT_SPACE_PORTRAIT.md). Uses installed
`art_style_transform` + `paper_cut_layered` + `popup_diorama`; no TransformationPack;
no EraPack; does **not** reopen CR-008, CR-012, CR-013, or CR-014.

```bash
aipf recipe validate recipes/cr-015-cut-space-portrait/1.0.0.json
aipf recipe compile recipes/cr-015-cut-space-portrait/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

### What is static in CR-015

- Source-conditioned layered-paper construction request and locks
- Route `art_style_transform` (no TransformationPack; not `artifact_transform`)
- ArtMethod `paper_cut_layered`; form `popup_diorama`; state `newly_created`
- Empty EraPack list; no handmade/museum/dynasty authenticity claim
- Symbolic reference `cr001-c0-l0-4x5-source` (`identity` / `pose` / `outfit` / `hairstyle`)
- Identity `recognizable_identity`; body `artistic_stylization` for medium translation
- Hierarchical preservation: major face/pose/gown/hairstyle architecture locked; minor folds/seams/hair strands omittable into supported paper shapes
- Paper topology: bridges/tabs/folds/glued joins, F/M/B layer spacing, construction-caused shadows, structural negative space
- Aspect fixed at `4:5`; empty `variables` (single embedded baseline)
- Explicit non-claims: no photo-texture overlay, no CGI plastic, no sculpture/woodblock/gongbi/ink-wash primary substitution, no historical costume replacement, no generation in this PR

### Supported variations (CR-015)

None in `1.0.0` — single baseline full-figure layered-paper pop-up framing only.

## Packaging note

`recipes/` is a **worktree** library. It is not added to
`aipf_packaging/resource_inventory.json` in this PR.

## Provenance (generation binding track)

Recipe→generation binding, private staging, and evidence limits are documented
in [CREATIVE_RECIPE_PROVENANCE.md](CREATIVE_RECIPE_PROVENANCE.md). Use
`scripts/creative_recipe_generation.py prepare|verify` for offline bundles.
Live image generation and gallery publication remain separately authorized.
