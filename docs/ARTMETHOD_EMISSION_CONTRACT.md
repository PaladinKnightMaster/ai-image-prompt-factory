# ArtMethod Emission Contract (`art_method_emission_contract`)

Track A (CR-017) introduces an explicit opt-in emission contract for ArtMethod prose.

## Field

- Location on semantic_spec: `/art/art_method_emission_contract`
- Schema: `data/schemas/request.schema.json`
- Enum: `legacy` | `state_aware_v1`
- Optional. **Absent means legacy.**
- Null is invalid.

## Pack capability

ArtMethod packs may declare:

`supported_art_method_emission_contracts`

When `state_aware_v1` is listed, the pack must also provide:

- `technique.prompt_core` / `technique.surface` / `technique.edge`
- `condition_overlays` keyed by the ten registry artifact states

Current Track A pack: `mineral_pigment_mural` v1.2.0 (legacy strings preserved).

## Behavior

| Selector | Behavior |
|---|---|
| absent / `legacy` | Historical core + surface/edge emission |
| `state_aware_v1` | Technique + state overlay; XOR with legacy fragments |
| `state_aware_v1` + transformation | Hard error |
| `state_aware_v1` + null/missing/unknown state | Hard error |
| `state_aware_v1` without pack capability | Hard error |

Invariant: `SELECTED_EMISSION_CONTRACT_COUNT = 1`.

## Compatibility

Existing recipes without the selector remain legacy. Stage 0 legacy prompt-byte parity is required for protected baselines. No silent migration.

Workshop-margin correction remains out of scope (`WORKSHOP_MARGIN_CORRECTION_NOT_ESTABLISHED`).
