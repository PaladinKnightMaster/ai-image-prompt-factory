# EraPack fragment medium-safe selection (AIPF-ERA-FRAGMENT-FIX-001)

## Defect

`_era_fragment()` previously appended every EraPack `prompt_fragments` key to its
preference list (`preferred += list(frags)`). When no ArtMethod/route/occasion
preference matched, the first available fragment was still selected.

For EraPack `song`, the only fragment is an **ink-transformation** instruction.
Photographic `new_generation` requests with `art.method: null` therefore received
a positive anti-photograph medium clause while still loading Song historical
anchors—an unintended coupling of era context to artistic medium.

## Correction

Remove the unconditional fallthrough. Fragment text is emitted only when an
explicit preference matches a fragment key:

- ArtMethod maps (e.g. `chinese_ink_painting` → `ink`, `mineral_pigment_mural` → `mural`)
- Occasion token `lantern` → `lantern`
- Route `historical_portrait` → `portrait` / `living` / `wuxia` / `court`

If nothing matches, **omit** the optional fragment. Structured EraPack anchors
(`era_<id>` from wardrobe/architecture/textiles/etc.) remain independent.

## Compatibility

| Scenario | Result |
| --- | --- |
| Song + photo + null method | Anchors kept; no ink fragment |
| Song + `chinese_ink_painting` | Ink fragment kept |
| Tang lantern occasion | Lantern fragment kept |
| Golden `09-song-ink-transform` | Unchanged |
| Golden `05-tang-dunhuang-mural` | Drops fallthrough Tang *living portrait* fragment; keeps Dunhuang mural fragment + Tang anchors |

`COMPILER_VERSION` remains `3.2.0`: this is a medium-safety bug fix within the
existing non-transformation compiler lineage, not a new compiler feature surface.
Prompt digests change only where an incompatible fallthrough fragment is removed.

## Out of scope

- No new EraPacks / living Song fragment in this PR
- No CR-002 recipe edits (remain on PR #45 for later reconciliation)
- Overlay packs (`wuxia` / `xianxia`) still use their separate first-value overlay path
