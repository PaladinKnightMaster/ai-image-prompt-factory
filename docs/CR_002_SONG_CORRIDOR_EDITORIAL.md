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

### Known engine/EraPack tension (not fixed in this PR)

`references/eras/song.json` currently exposes a single `prompt_fragments`
entry keyed `ink`. Compiler `_era_fragment()` falls through to available
fragment keys when `art.method` is null, so baseline CR-002 compiles with the
Song ink-transformation sentence even though the recipe lock and request demand
a living photograph. CR-002 counters this in request, locks,
`intentional_hybrids`, and director material language. **Do not silently edit
the EraPack or compiler in this delivery**; a future pack authoring change
(e.g. a `living` / portrait fragment) would be the proper fix.

## Supported variables

| Key | Target | Baseline |
| --- | --- | --- |
| `camera` | `director.camera` | eye-level three-quarter full-length corridor axis frame |
| `light` | `director.light_source` | soft daylight from courtyard-side openings |
| `aspect` | `output.aspect_ratio` | `4:5` (also `1:1`) |

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
