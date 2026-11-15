# CR-016 The Ferry Across Unpainted Water

Creative Research recipe: original Southern Song–informed **Chinese ink landscape**
as a vertical hanging-scroll painting on silk. PromptRecipe library draft—
no image generation, custody import, adapter freeze, or gallery index changes
in this delivery.

**Status: RECIPE DRAFT VALIDATED — GENERATION / PROMPT-FREEZE PENDING OWNER REVIEW**

**No CR-016 output has yet been generated.**

| Field | Value |
| --- | --- |
| Path | `recipes/cr-016-ferry-unpainted-water/1.0.0.json` |
| `recipe_id` | `cr-016-ferry-unpainted-water` |
| `recipe_version` | `1.0.0` |
| `recipe_schema_version` | `1.1` |
| Route | `new_generation` |
| TransformationPack | none |
| EraPack | `song` |
| ArtMethodPack | `chinese_ink_painting` |
| Artifact form / state | `scroll` / `newly_created` |
| Painting support (prose) | silk |
| Scroll type (prose) | vertical hanging scroll |
| Presentation | painting as principal image (4:5) |
| Historical strictness | `historically_informed` |
| References | none |
| Variables | none (single embedded baseline) |
| Recipe SHA-256 | `399023d58cc080847483024a0483ecf63a26b60e3384e65293dbdd58610e48aa` |
| Baseline compiled prompt SHA-256 | `304fabd4de18b02a49107205313ca00c4520ac9b6c543680ea5c7dd097fab184` |
| Compiler version (offline) | `3.2.0` |

## Creative objective

Demonstrate an historically informed Southern Song ink landscape with coherent
hanging-scroll pictorial hierarchy, wet/dry brush contrast, ink-density
hierarchy, atmospheric recession through ink value and void, and a subordinate
ferry narrative. The ferry and one or two tiny travelers remain readable but
must not become a fashion or character portrait.

This recipe is intentionally **not** a transform of CR-001 and is distinct from:

- CR-002 Song Corridor Editorial (living photographic Song fashion)
- CR-014 Inkflow Figure (CR-001 fashion afterimage; `album_leaf`; no EraPack)

## Research grounding

Authoring carries forward the private concept-spec packet
`AIPF_Creative_Private/CR-REENTRY-CONCEPT-SPEC-01` (external manifest SHA-256
`639656c66114b1947f9deab8c93ac73b423cfc3e70b9d9fb2df5f057401d4930`). Primary
public anchors include Cleveland CMA 1988.20 (Southern Song hanging scroll, ink
on silk) for format/support/subordinate-figure practice, with Met Fan Kuan–style
hanging-scroll evidence used only as Northern monumental contrast—not a
composition to copy. Installed AIPF sources: `references/eras/song.json`,
`references/art-methods/chinese_ink_painting.json`, ISV-01 Song+ink offline
combo (compiler evidence only; not visual proof).

Creative inventions: ferry narrative and exact composition. Non-claims: no
named artist, seals, calligraphy, collector marks, or documentary reconstruction
of a surviving masterpiece. Digital generation is not authenticated handmade
production.

## Why this pack architecture

- `new_generation` — original landscape; no identity reference required
- `song` + `historically_informed` — Southern Song lyrical mist guidance
- `chinese_ink_painting` + `scroll` + `newly_created` — installed compatibility
- No TransformationPack — painting method emits on standard compiler `3.2.0`
- Aspect `4:5` — PromptRecipe vocabulary supports `1:1`/`4:5` only; vertical
  hanging-scroll hierarchy maps to portrait field; horizontal handscroll panoramic
  ratios are not authorized without schema expansion

## Residual compiler notes (non-blocking)

Standard non-transform compilation still emits selective Song living anchors
(`era_song`: robes/hair/timber/silk). Recipe request, locks, hybrids, and
director instruct that those anchors may supply only optional minimal traveler
notation—or be omitted—and must not become corridor fashion staging. Method core
retains inclusive “paper/silk” capability language; variant/director lock **silk
only**. Form registry text mentions mounting/border logic; presentation remains
painting-as-image (quiet margin allowed; no roller/product shot).

## Planned visual acceptance criteria (later generation gate)

1. Readable Chinese ink landscape identity  
2. Coherent vertical hanging-scroll composition in 4:5  
3. Wet/dry brush contrast  
4. Ink-density hierarchy  
5. Pictorial atmospheric recession (not photographic DOF)  
6. Intentional unpainted silk as water/atmosphere  
7. Subordinate but readable ferry narrative  
8. Plausible ink-on-silk behavior without fake aging  
9. No false text, seals, signatures, or attribution  
10. Clear differentiation from CR-002 and CR-014  

Disqualifying failures include photo+ink overlay, fashion-portrait dominance,
handscroll panoramic substitution, mounted-scroll product photography as primary
subject, Northern monumental fill crowding out mist/void, fake calligraphy/seals,
and fabricated aging contradicting `newly_created`.

Owner KEEP is not automatic and is not authorized by this documentation alone.

## Manual ChatGPT Images feasibility

Feasible as an **owner-operated** later gate after recipe review and **separate
authorization**. Image generation is **not** authorized by this documentation
alone. When authorized later: prepare via
`scripts/creative_recipe_generation.py prepare`, submit adapter-effective
`prompt.txt` (not `compiler_prompt.txt`), preserve original-byte custody, then
evaluate against the criteria above. Offline compile digests above are
**compiler evidence** only—not a frozen gallery-generation adapter prompt.

## Non-claims

- Does not reopen CR-008  
- Does not modify APCC / EXP-019 / AIQ  
- Does not promote a private or public gallery card  
- Does not prove provider visual fidelity from offline compilation  
