# CR-002 Song Corridor Editorial

Creative Research recipe: original living **photographic** fashion editorial
informed by Song-dynasty Chinese visual culture. PromptRecipe library only—
no image generation, gallery publication, or CR-001 custody changes in this
delivery.

| Field | Value |
| --- | --- |
| Path | `recipes/cr-002-song-corridor-editorial/1.0.0.json` |
| `recipe_id` | `cr-002-song-corridor-editorial` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `new_generation` |
| Historical strictness | `historically_informed` |
| EraPack | `song` (existing `references/eras/song.json`) |
| ArtMethodPack | none (`art.method` / form / state = `null`) |

## Creative brief

Quiet architectural elegance: an adult woman pauses in a Song-informed timber
covered corridor. Layered silk wardrobe (open-front beizi over slim ruqun),
restrained hair, soft daylight from courtyard openings, and clear
foreground / subject / background depth. Avoid fantasy costume, arbitrary
dynasty mixing, exaggerated cinematic light, and unsupported reconstruction
claims.

## Research sources and attribution

Primary EraPack anchors already ship in `references/eras/song.json` (Met
Heilbrunn Song overview; foundation pack scope note). Additional authoring
context used for CR-002 (not imported as images or third-party prompts):

| Source | Type | Used for |
| --- | --- | --- |
| Met Museum, Heilbrunn Timeline — Song dynasty | museum overview | Period framing; already cited by EraPack `song` |
| Jin / related Song women’s fashion scholarship (e.g. JHASS 2025 survey on Song women’s styles; DOI `10.26855/jhass.2025.05.008`) | secondary scholarship | Beizi as straight-collar open-front outer layer with side slits; layered complexity; Southern Song slimmer silhouette tendency |
| CSSN English summary of Tang→Song fashion shift | secondary overview | Move toward slender, more modest silhouettes vs late Tang flamboyance; pei / rank-sensitive ornaments |
| Ningbo Baoguo Temple (Northern Song main hall, 1013) public architectural summaries | surviving timber architecture | Song timber-hall plausibility for historically informed column/roof language |
| Met Astor Chinese Garden Court educator materials | museum architecture (Ming-style reconstruction) | Covered walkway as garden design type; **not** treated as Song evidence—used only to avoid claiming Ming court details as Song fact |

No third-party prompts were copied. No reference images were imported into the
repository.

## Unresolved historical uncertainties

- Exact beizi hem length, sleeve width, and slit height vary by Northern vs
  Southern Song, status, and occasion; CR-002 chooses a Southern Song-inspired
  slim open-front reading without dating a specific garment find.
- Women’s hair and ornament conventions are status- and scene-dependent; the
  recipe forbids Tang tower buns, Qing banner hair, and ceremonial phoenix
  crowns, but does not claim a single excavated hairstyle.
- Surviving Song covered residential corridors are scarce relative to later
  Jiangnan garden walkways; corridor staging is **historically informed** timber
  + plaster + tile language, not a reconstruction of a named Song building.
- Palette “quietness” is an aesthetic tendency in many Song pictorial contexts,
  not a universal dress code.

## V3.4 / PromptRecipe mapping

- PromptRecipe **v1.1** envelope with constrained variables only on
  `director.camera`, `director.light_source`, `output.aspect_ratio`.
- Compiler path unchanged; no new routes, packs, or runtime variables.
- Photographic output: `art.method` null avoids ArtMethodPack conflict by
  design.

### Compiler dependency (PR #46)

CR-002 requires the medium-safe EraPack fragment selector from
[ERA_FRAGMENT_MEDIUM_SAFE_SELECTION.md](ERA_FRAGMENT_MEDIUM_SAFE_SELECTION.md)
(merged PR #46). With that fix, Song photographic compiles keep `era_song`
anchors and **omit** `era_fragment_song` ink text when `art.method` is null.

CR-002-RECONCILE-001 therefore removed the obsolete
`intentional_hybrids` photographic-versus-ink disclaimer that only papered
over the pre-#46 fallthrough defect. No replacement negative medium clause was
added. Request/locks still state photographic living intent and forbid
fantasy/xianxia and Tang/Qing default styling.

### Digests (post-reconcile)

| Digest | SHA-256 |
| --- | --- |
| Recipe (`1.0.0.json`) | `2fc6fc85163206023c77c9d492e0f5437ec4f1ff00f0a2dbb04bcac84c5b59d9` |
| Baseline compiled prompt (c0/l0/4:5) | `0bf699d3c75fb89d0df8d48445fbe514f00b43d72e99a8bdb3a13cc71cb873a4` |

## Supported variables

| Key | Target | Baseline |
| --- | --- | --- |
| `camera` | `director.camera` | eye-level three-quarter full-length corridor axis frame |
| `light` | `director.light_source` | soft daylight from courtyard-side openings |
| `aspect` | `output.aspect_ratio` | `4:5` (also `1:1`) |

All 18 camera×light×aspect combinations are supported PromptRecipe bindings.
They share Song historically informed photographic context; framing and daylight
emphasis differ by binding. Medium-long crops prioritize beizi/face readability
while the static request still carries corridor wardrobe context.

## Validation commands

```bash
aipf recipe validate recipes/cr-002-song-corridor-editorial/1.0.0.json
aipf recipe compile recipes/cr-002-song-corridor-editorial/1.0.0.json --json
python -m pytest -q tests/test_creative_recipe_library.py
```

## Proposed first owner-operated ChatGPT Web configuration

Separate authorization required before any generation.

| Binding | Value |
| --- | --- |
| `camera` | baseline (corridor-axis three-quarter full-length) |
| `light` | baseline soft courtyard-side daylight |
| `aspect` | `4:5` |
| Channel | `chatgpt_web_manual` after `prepare` bundle (same provenance path as CR-001) |
| Expectation | historically informed living photograph; not ink; not public gallery |

## Out of scope

Image generation, CR-001 evidence access, private gallery candidate edits,
public gallery / Pages publication, PR-CR-003B, EXP-019 / ESR / AIQ / G4/G5,
compiler or new pack families.
