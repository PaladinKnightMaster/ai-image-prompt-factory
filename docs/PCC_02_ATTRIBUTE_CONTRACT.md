# PCC-02 — Attribute Preservation/Change Contract (Slice 1)

**Status:** Implemented (opt-in compiler/validation path)  
**Architecture source:** PCC-01 Alternative B  
**Engineering baseline:** `236b7130adb8c6ef82411e39e93b0e603083c4da`  
**Feature branch:** `feat/pcc-02-attribute-contract-slice1`

This document describes the first Attribute Preservation/Change Contract (APCC)
implementation. It does **not** claim visual validation of fashion styling or
identity preservation. Compiler emission is not provider-side fidelity.

## 1. Architecture decision (from PCC-01)

PCC-01 selected **Alternative B**: a structured, opt-in `attribute_contract`
section rather than extending opaque `locks` or conflating intent into
reference-role assignments.

- Reference roles remain **ownership / permission boundaries**.
- APCC states remain **preserve / change / unconstrained** intent.
- Provider attachment evidence and observed image fidelity remain separate.

`reinterpret` is deferred. Hairstyle, pose, makeup, environment, artifact
material reinterpretation, and derived-reference lineage are deferred.

## 2. Exact APCC schema shape

Optional request field (JSON Schema in `data/schemas/request.schema.json`):

```json
{
  "attribute_contract": {
    "attributes": [
      {
        "attribute": "identity.face",
        "intent": "preserve",
        "source_reference_id": "portrait_A"
      },
      {
        "attribute": "wardrobe.garment",
        "intent": "change",
        "target": {
          "text": "Replace the original clothing with a tailored ivory silk evening gown, structured bodice, fitted waist, and controlled fabric drape."
        }
      }
    ]
  }
}
```

Wardrobe change may instead use an outfit reference target:

```json
"target": { "reference_id": "outfit_B" }
```

Rules:

- `additionalProperties: false` on the contract and each entry / target.
- Exactly one of `target.text` or `target.reference_id` for a wardrobe change
  (combined text+reference is rejected).
- Text targets are nonempty and bounded to 500 characters.
- No mask, ROI, or pixel-lock fields.

## 3. Supported request version

| Condition | Behavior |
| --- | --- |
| `version: "3.5"` + `attribute_contract` | APCC validation + emission; `compiler_version` **`3.5.0`** |
| `version: "3.5"` without `attribute_contract` | Legacy compile path; stamp **`3.2.0`** |
| `version` in `{3.0,3.1,3.2,3.4}` without APCC | Unchanged legacy path |
| APCC present on non-`3.5` version | Error `attribute_contract_version` |

Request schema version enum admits `"3.5"`. PromptRecipe envelope versions
(`1.0` / `1.1`) are unchanged; embedded `semantic_spec` may use `3.5` only in
**new** recipes. Frozen Creative Recipes are not modified.

## 4. Supported attributes and intents

| Attribute | Intents |
| --- | --- |
| `identity.face` | `preserve`, `unconstrained` |
| `wardrobe.garment` | `preserve`, `change`, `unconstrained` |

Unknown attributes/intents fail validation. Duplicate declarations for the same
attribute fail validation.

## 5. Supported route and representation scope

Slice 1 supports:

- Route: **`reference_transform`** only
- Living photographic portrait wardrobe/identity control
- Identity modes for preserve: **`strict_identity`**, **`recognizable_identity`**

Fail-closed unsupported contexts (`attribute_unsupported_context`):

- Any Representation `transformation` pack
- Any set `art.method` / `artifact_form` / `artifact_state`
- Routes other than `reference_transform`
- `historical.strictness: strict_reconstruction`

Legacy non-APCC requests for sculpture, mural, print, ceramic, historical, and
product routes remain unchanged.

## 6. Source reference ownership

Authoritative role policy remains `references/core/reference_roles.json`.

| Attribute | Required role |
| --- | --- |
| `identity.face` | `identity` |
| `wardrobe.garment` | `outfit` |

- Preserve requires `source_reference_id` resolving to a reference with the
  required role.
- Wardrobe preserve must not be inferred from an identity-only reference.
- One reference may legally hold multiple roles when explicitly assigned.
- Multiple references may share a role globally; APCC rejects only when the
  **same attribute** is declared twice / ambiguously sourced.

## 7. Explicit garment targets

For `wardrobe.garment` + `intent: change`, require exactly one:

1. **Text target** — explicit garment description (`target.text`)
2. **Outfit reference** — `target.reference_id` with role `outfit`

Director prose is not a substitute target. No automatic garment recognition.
`references/wardrobe/` remains authoring-only (no runtime pack loader).

## 8. Conflict and validation semantics

Hard errors (block compilation before APCC emission):

| Code | Condition |
| --- | --- |
| `attribute_contract_version` | APCC without version `3.5` |
| `attribute_unknown` | Unsupported attribute id |
| `attribute_unsupported_intent` | Intent illegal for attribute |
| `attribute_duplicate_declaration` | Same attribute declared more than once |
| `attribute_source_missing` | Preserve without source |
| `attribute_unknown_source` | Unknown reference id |
| `attribute_source_role_mismatch` | Source/target lacks required role |
| `attribute_change_target_missing` | Change without usable target |
| `attribute_change_target_ambiguous` | Both text and reference_id supplied |
| `attribute_identity_mode_conflict` | Face preserve with incompatible identity mode |
| `attribute_unsupported_context` | Unsupported route / transform / art / strict reconstruction |
| `attribute_lock_conflict` | Typed lock opposes wardrobe change |
| `attribute_intent_field_mismatch` | Intent-incompatible fields (preserve+target, change+source_reference_id, unconstrained+source/target) |
| `attribute_duplicate_reference_id` | APCC request has multiple `references[]` entries with the same nonempty id |
| `schema` | Structural schema violations (unknown fields, etc.) |

Intent field compatibility (PCC-02-PREMERGE-HARDENING-01):

| Intent | Required | Forbidden |
| --- | --- | --- |
| `preserve` | `source_reference_id` | `target` |
| `change` | `target` (exactly one of text / reference_id) | `source_reference_id` |
| `unconstrained` | — | `source_reference_id`, `target` |

Duplicate reference ids are rejected only when `attribute_contract` is present.
Distinct ids sharing an `outfit` role remain legal when APCC explicitly selects
one. Multi-role assignment on a single id remains legal. Legacy non-APCC
requests are unchanged.

Recognized typed wardrobe-preserve lock keys (boolean `true`):

- `preserve_source_outfit`
- `preserve_outfit`
- `forbid_wardrobe_change`

### Residual free-text limitations

Unrestricted `request`, `director`, `locked_features`, and most free-form
`locks` keys are **not** fully conflict-parsed. APCC validates structured
contract fields and the typed locks above. Authors remain responsible for
keeping free-text prose consistent with the contract.

## 9. Deterministic prompt section emission

When APCC is present and valid, the compiler may emit:

1. `attribute_preserve` — stable attribute order (`identity.face`, then
   `wardrobe.garment`)
2. `attribute_change` — same stable order

Sections are omitted when no preserve/change intents exist (e.g. all
`unconstrained`). Declaration order in JSON does not affect prompt bytes.
Emission states:

- Controlled attribute and source/target
- Role-isolation boundaries
- Explicit non-claim: not pixel-perfect / not masked local edit
- Wardrobe change does not authorize facial redesign

Existing `references` isolation prose remains.

## 10. Compiler versioning and legacy compatibility

| Path | Stamp |
| --- | --- |
| Standard / no APCC | `3.2.0` |
| TransformationPack | `3.4.1` |
| APCC (`attribute_contract` present) | `3.5.0` |

Frozen Creative Recipe prompt digests must remain stable. PCC-02 does not edit
recipe files, golden prompts, packs, or private gallery evidence.

Packaging integrity mirrors updated solely because `request.schema.json` is an
allowlisted knowledge resource:

- `aipf_packaging/resource_inventory.json` (hash/size/`total_bytes`)
- `tests/test_package_portability.py` locked `total_bytes` assertion

## 11. What offline tests establish

Module: `tests/test_attribute_contract_pcc02.py`

Establishes:

- Valid identity preserve + wardrobe change (text and outfit-ref targets)
- Wardrobe preserve from outfit role
- Unconstrained intents
- Multi-role single reference
- Deterministic ordering and repeated compilation
- Negative ownership / target / version / context / mode / lock conflicts
- Selected frozen CR prompt digest stability

Does **not** establish:

- Generated-image identity or wardrobe fidelity
- Provider attachment verification
- Fashion aesthetic quality

## 12. Provider attachment and fidelity limitations

- Symbolic `references[].id` values are request-local ids, not upload proofs.
- The compiler does not verify that an image file was attached to a provider call.
- Semantic preserve/change instructions are not guarantees of model compliance.
- No mask/ROI editing API is represented.

## 13. Deferred work

- `reinterpret` intent
- `hair.*`, `pose.*`, makeup, environment attributes
- Multi-reference composition matrices beyond slice-1 ownership checks
- Artifact / historical material reinterpretation under APCC
- Derived-reference lineage
- Bronze lexical parity and broader transformation failure-mode emission
- New era/fantasy knowledge packs

## 14. Future visual-evaluation requirements

A later manual experiment should score independently:

- Identity recognition
- Requested wardrobe-change compliance
- Unrequested attribute drift
- Reference-role isolation
- Material realism where applicable
- Original-byte custody / provenance

Attractiveness is not the primary technical metric. Outfit-correct results that
lose identity must not receive an unqualified PASS. One accepted image is not
scientific reliability.
