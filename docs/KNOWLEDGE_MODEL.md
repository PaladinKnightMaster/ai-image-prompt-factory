# V3 Knowledge Model

## Semantic request

A request is normalized into `data/schemas/request.schema.json`. The spec stores user locks, reference roles, identity/body policies, historical context, art method/form/state, director decisions, and output profile separately.

The separation is deliberate. For example:

```text
ERA: Edo
ROLE: urban adult portrait subject
ART METHOD: Japanese woodblock print
ARTIFACT FORM: album leaf
ARTIFACT STATE: newly created
NARRATIVE: adjusting a sleeve while glancing toward the viewer
```

is fundamentally different from a single `"Edo ukiyo-e style"` tag.

## Era/site/overlay pack

Every pack exposes the requested domains when meaningful:

- period / subperiod guidance
- region
- social role
- gender presentation
- occasion
- wardrobe
- textile/material
- hairstyle/headwear
- makeup/grooming
- jewelry
- architecture
- interior/furniture
- food/drink/tableware
- musical instruments
- weapons/tools
- transportation
- writing/calligraphy
- ritual/custom
- lighting technology
- flora/season
- visual arts
- incompatible/anachronistic elements
- evidence/confidence
- prompt fragments

Not every field is equally known for every pack. Empty or low-confidence fields are preferable to invented certainty.

## Compatibility values

`canonical`, `well_attested`, `plausible`, `interpretive`, `rare`, `anachronistic`, `incompatible`, `unknown`.

The values describe the relationship between an element and a bounded context. They are not aesthetic ratings.

## Art method

Each method controls:

- material
- fabrication process
- visible production marks
- edge behavior
- mark-making
- color behavior
- surface behavior
- composition behavior
- structural limitations
- aging/weathering
- artifact compatibility
- prompt fragments
- typical image-generation failures
- evaluation criteria

This is why marble and bronze are separate modules: a carved brittle crystalline material and a cast reflective copper alloy have different feasible forms, surface transitions, joins, aging, and failure modes.

## Artifact form

Form defines geometry and viewing logic independently of method: `bust`, `free_standing_statue`, `relief`, `plate`, `vase`, `scroll`, `popup_diorama`, and so on.

## Artifact state

State changes the physical history of the object. `museum_conserved` is not “aged + clean”; it implies stabilization/display logic. `modern_reconstruction` must not receive archaeological damage by default. `excavated` should not become a generic dirt filter.

## Director gate

The director gate turns a semantically correct spec into a strong image. It resolves physical and narrative questions that adjective piles ignore: exact moment, weight, hand assignments, moving fabric, foreground/midground/background, camera position, motivated light and emotional micro-story.
