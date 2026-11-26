# Bronze ArtMethod State-Aware Emission (`bronze_sculpture` v1.2.0)

Additive Track B pilot on the CR-017 `art_method_emission_contract` architecture.

## Four-part material semantics

| Part | Meaning | Emission placement |
|---|---|---|
| A Fabrication technique | Casting, chasing, joins, mounts, metal response | `technique.prompt_core`, `technique.edge` |
| B Intentional surface finish | Deliberately applied / workshop patination or coloration | `technique.surface` (+ light core clause) |
| C Natural surface condition | Naturally developed stable surface character | `condition_overlays` (non-null states) |
| D Deterioration | Active corrosion, loss, structural damage | `condition_overlays` when state-justified |

### Intentional patina versus natural patina

- **Intentional / workshop patination** is a fabrication finish. It may appear on newly manufactured objects via technique fields.
- **Naturally developed stable surface patina** is lifecycle condition. It belongs in overlays such as `aged` or `museum_conserved`.
- Bare unqualified **patina** is prohibited in technique fields. Prefer `patination` / `patinated coloration` with an intentional qualifier, or `naturally developed stable surface patina` in overlays.

## Condition-overlay authoring

- Fresh-like states (`newly_created`, `modern_reconstruction`, `replica`, `fantasy_artifact`) keep **null** overlays.
- Null overlay does **not** forbid intentional applied finish (that comes from technique).
- Non-null overlays must be semantically justified for the registry state.
- Do not put positive deterioration instructions into technique fields.

## Ten-state mapping

See pack `condition_overlays` and the approved design matrix. Registry states are authoritative; do not invent mappings.

## Legacy versus state-aware emission

| Selector | Behavior |
|---|---|
| absent / `legacy` | v1.1.0 legacy fragments + surface/edge (Stage 0 byte parity) |
| `state_aware_v1` | technique + optional overlay; XOR with legacy fragments; compiler `3.6.0` |

No silent migration of existing recipes/cases.

## Version compatibility

- Pack id remains `bronze_sculpture`.
- Version `1.2.0` is additive: legacy fields preserved byte-for-byte relative to v1.1.0 content.
- Shared schema/compiler unchanged.
- Transformation path (`portrait_to_volumetric_sculpture`) unchanged; state_aware remains incompatible with transformation.
