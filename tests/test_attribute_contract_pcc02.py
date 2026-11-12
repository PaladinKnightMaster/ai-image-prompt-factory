"""PCC-02 — Attribute Preservation/Change Contract slice 1 tests.

Offline only. No provider calls, no private gallery access, no recipe mutation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

import pytest

from aipf.compiler import compile_result
from aipf.io import load_json
from aipf.linting import lint_spec
from aipf.recipes import compile_recipe, load_recipe


def _errors(spec: dict) -> list[dict]:
    return [f for f in lint_spec(spec) if f["level"] == "error"]


def _error_codes(spec: dict) -> set[str]:
    return {f["code"] for f in _errors(spec)}


def _base_spec(**overrides) -> dict:
    spec = {
        "version": "3.5",
        "id": "pcc02-case",
        "request": (
            "Using the attached identity reference, produce one photographic "
            "editorial of the same recognizable adult while changing wardrobe "
            "to the designated garment target."
        ),
        "route": "reference_transform",
        "locks": {
            "adult_subject": True,
            "source_reference_required": True,
            "no_mask_or_roi_fields": True,
            "no_pixel_exact_identity_claim": True,
        },
        "references": [
            {
                "id": "portrait_A",
                "roles": ["identity"],
                "notes": "Identity source only for PCC-02 tests.",
            }
        ],
        "identity": {
            "mode": "recognizable_identity",
            "locked_features": ["recognizable adult facial appearance"],
        },
        "body_transformation": {
            "mode": "preserve",
            "anatomy_change": "none",
            "pose_change": "none unless required by garment change",
            "camera_presentation": "allowed for editorial framing",
            "garment_shaping": "required wardrobe change",
            "artistic_stylization": "none",
        },
        "historical": {
            "strictness": "historically_informed",
            "packs": [],
            "subperiod": None,
            "region": None,
            "role": None,
            "occasion": None,
            "intentional_hybrids": [],
        },
        "art": {
            "method": None,
            "artifact_form": None,
            "artifact_state": None,
            "variant": None,
        },
        "requested_elements": [],
        "director": {
            "moment": "a quiet settled editorial beat",
            "action": "standing three-quarter fashion stance",
            "gaze": "toward camera with calm focus",
            "camera": "eye-level three-quarter full-length editorial frame",
            "light_source": "soft directional editorial key",
            "micro_story": "PCC-02 identity preserve with wardrobe change",
        },
        "output": {
            "profile": "standard",
            "aspect_ratio": "4:5",
            "text_in_image": [],
            "generation_requested": False,
        },
        "attribute_contract": {
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {
                        "text": (
                            "Replace the original clothing with a tailored ivory "
                            "silk evening gown, structured bodice, fitted waist, "
                            "and controlled fabric drape."
                        )
                    },
                },
            ]
        },
    }
    for key, value in overrides.items():
        if key in {
            "historical",
            "art",
            "director",
            "output",
            "identity",
            "body_transformation",
            "locks",
            "attribute_contract",
        } and isinstance(value, dict):
            spec[key] = {**spec.get(key, {}), **value}
        else:
            spec[key] = value
    return spec


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_pcc02_identity_preserve_wardrobe_change_by_text():
    spec = _base_spec()
    assert _errors(spec) == []
    result = compile_result(spec)
    assert result["compiler_version"] == "3.5.0"
    assert "attribute_preserve" in result["prompt_sections"]
    assert "attribute_change" in result["prompt_sections"]
    preserve = result["prompt_sections"]["attribute_preserve"]
    change = result["prompt_sections"]["attribute_change"]
    assert "identity.face" in preserve
    assert "portrait_A" in preserve
    assert "not a pixel-perfect" in preserve.casefold() or "not pixel-perfect" in preserve.casefold()
    assert "wardrobe.garment" in change
    assert "ivory silk evening gown" in change
    assert "face redesign" in change.casefold() or "facial redesign" in change.casefold()
    assert spec["output"]["generation_requested"] is False
    refs = result["prompt_sections"]["references"]
    assert "portrait_A supplies identity only" in refs
    assert "Do not import unassigned" in refs


def test_pcc02_identity_preserve_wardrobe_change_by_outfit_reference():
    spec = _base_spec(
        references=[
            {"id": "portrait_A", "roles": ["identity"]},
            {"id": "outfit_B", "roles": ["outfit"]},
        ],
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {"reference_id": "outfit_B"},
                },
            ]
        },
    )
    assert _errors(spec) == []
    result = compile_result(spec)
    change = result["prompt_sections"]["attribute_change"]
    assert "outfit_B" in change
    assert "identity" in change.casefold()
    refs = result["prompt_sections"]["references"]
    assert "outfit_B supplies outfit only" in refs
    assert "portrait_A supplies identity only" in refs


def test_pcc02_wardrobe_preserve_from_outfit_reference():
    spec = _base_spec(
        references=[
            {"id": "portrait_A", "roles": ["identity"]},
            {"id": "outfit_B", "roles": ["outfit"]},
        ],
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "preserve",
                    "source_reference_id": "outfit_B",
                },
            ]
        },
    )
    assert _errors(spec) == []
    result = compile_result(spec)
    preserve = result["prompt_sections"]["attribute_preserve"]
    assert "wardrobe.garment" in preserve
    assert "outfit_B" in preserve
    assert "attribute_change" not in result["prompt_sections"]


def test_pcc02_explicit_unconstrained_intent():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {"attribute": "identity.face", "intent": "unconstrained"},
                {"attribute": "wardrobe.garment", "intent": "unconstrained"},
            ]
        },
        identity={"mode": "identity_unlocked", "locked_features": []},
    )
    assert _errors(spec) == []
    result = compile_result(spec)
    assert result["compiler_version"] == "3.5.0"
    assert "attribute_preserve" not in result["prompt_sections"]
    assert "attribute_change" not in result["prompt_sections"]


def test_pcc02_one_reference_with_multiple_legal_roles():
    spec = _base_spec(
        references=[
            {"id": "portrait_A", "roles": ["identity", "outfit"]},
        ],
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
            ]
        },
    )
    assert _errors(spec) == []
    result = compile_result(spec)
    refs = result["prompt_sections"]["references"]
    assert "portrait_A supplies identity, outfit only" in refs


def test_pcc02_repeated_compile_is_byte_identical():
    spec = _base_spec()
    a = compile_result(spec)["prompt"]
    b = compile_result(deepcopy(spec))["prompt"]
    assert a == b
    assert sha256(a.encode("utf-8")).hexdigest() == sha256(b.encode("utf-8")).hexdigest()


def test_pcc02_attribute_declaration_order_normalizes():
    first = _base_spec()
    second = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {
                        "text": (
                            "Replace the original clothing with a tailored ivory "
                            "silk evening gown, structured bodice, fitted waist, "
                            "and controlled fabric drape."
                        )
                    },
                },
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
            ]
        }
    )
    assert compile_result(first)["prompt"] == compile_result(second)["prompt"]


def test_pcc02_version_35_without_contract_uses_legacy_stamp():
    spec = _base_spec()
    del spec["attribute_contract"]
    assert _errors(spec) == []
    result = compile_result(spec)
    assert result["compiler_version"] == "3.2.0"
    assert "attribute_preserve" not in result["prompt_sections"]
    assert "attribute_change" not in result["prompt_sections"]


def test_pcc02_legacy_request_without_apcc_unchanged_path():
    spec = _base_spec(version="3.2")
    del spec["attribute_contract"]
    result = compile_result(spec)
    assert result["compiler_version"] == "3.2.0"
    assert "attribute_preserve" not in result["prompt_sections"]


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------


def test_pcc02_missing_identity_reference():
    spec = _base_spec(references=[])
    assert "attribute_unknown_source" in _error_codes(spec) or "attribute_source_missing" in _error_codes(spec)
    with pytest.raises(ValueError, match="Cannot compile invalid spec"):
        compile_result(spec)


def test_pcc02_missing_identity_role():
    spec = _base_spec(references=[{"id": "portrait_A", "roles": ["pose"]}])
    assert "attribute_source_role_mismatch" in _error_codes(spec)


def test_pcc02_missing_outfit_target():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {"attribute": "wardrobe.garment", "intent": "change"},
            ]
        }
    )
    codes = _error_codes(spec)
    assert "attribute_change_target_missing" in codes or "schema" in codes


def test_pcc02_wrong_outfit_target_role():
    spec = _base_spec(
        references=[
            {"id": "portrait_A", "roles": ["identity"]},
            {"id": "env_B", "roles": ["environment"]},
        ],
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {"reference_id": "env_B"},
                },
            ]
        },
    )
    assert "attribute_source_role_mismatch" in _error_codes(spec)


def test_pcc02_duplicate_attribute_declarations():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "identity.face",
                    "intent": "unconstrained",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {"text": "A black wool tailored blazer with peak lapels."},
                },
            ]
        }
    )
    assert "attribute_duplicate_declaration" in _error_codes(spec)


def test_pcc02_unsupported_attribute():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "hair.style",
                    "intent": "change",
                    "target": {"text": "A short bob with a side part."},
                }
            ]
        }
    )
    codes = _error_codes(spec)
    assert "attribute_unknown" in codes or "schema" in codes


def test_pcc02_unsupported_intent_for_identity():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "change",
                    "target": {"text": "redesign the face"},
                }
            ]
        }
    )
    assert "attribute_unsupported_intent" in _error_codes(spec)


def test_pcc02_apcc_on_legacy_version():
    spec = _base_spec(version="3.2")
    assert "attribute_contract_version" in _error_codes(spec)


def test_pcc02_apcc_on_unsupported_transformation():
    spec = _base_spec(
        route="artifact_transform",
        art={
            "method": "marble_sculpture",
            "artifact_form": "bust",
            "artifact_state": "newly_created",
            "variant": None,
        },
        transformation={
            "pack_id": "portrait_to_volumetric_sculpture",
            "selected_concepts": [],
        },
        body_transformation={"mode": "artistic_stylization"},
    )
    assert "attribute_unsupported_context" in _error_codes(spec)


def test_pcc02_invalid_reference_id():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "missing_ref",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {"text": "A black wool tailored blazer with peak lapels."},
                },
            ]
        }
    )
    assert "attribute_unknown_source" in _error_codes(spec)


def test_pcc02_incompatible_identity_mode():
    spec = _base_spec(identity={"mode": "identity_unlocked", "locked_features": []})
    assert "attribute_identity_mode_conflict" in _error_codes(spec)


def test_pcc02_unsupported_strict_historical():
    spec = _base_spec(
        historical={
            "strictness": "strict_reconstruction",
            "packs": ["tang"],
            "subperiod": "court leisure",
            "region": "China",
            "role": "court woman",
            "occasion": "court leisure",
            "intentional_hybrids": [],
        }
    )
    assert "attribute_unsupported_context" in _error_codes(spec)


def test_pcc02_unknown_apcc_field():
    spec = _base_spec()
    spec["attribute_contract"]["unexpected"] = True
    codes = _error_codes(spec)
    assert "schema" in codes


def test_pcc02_wardrobe_preserve_from_identity_only_source():
    spec = _base_spec(
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
            ]
        }
    )
    assert "attribute_source_role_mismatch" in _error_codes(spec)


def test_pcc02_ambiguous_duplicate_sources_same_attribute():
    """Two outfit refs without a single designated wardrobe source → error when both claimed."""
    spec = _base_spec(
        references=[
            {"id": "portrait_A", "roles": ["identity"]},
            {"id": "outfit_B", "roles": ["outfit"]},
            {"id": "outfit_C", "roles": ["outfit"]},
        ],
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {"reference_id": "outfit_B"},
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {"reference_id": "outfit_C"},
                },
            ]
        },
    )
    assert "attribute_duplicate_declaration" in _error_codes(spec)


def test_pcc02_combined_text_and_reference_target_rejected():
    spec = _base_spec(
        references=[
            {"id": "portrait_A", "roles": ["identity"]},
            {"id": "outfit_B", "roles": ["outfit"]},
        ],
        attribute_contract={
            "attributes": [
                {
                    "attribute": "identity.face",
                    "intent": "preserve",
                    "source_reference_id": "portrait_A",
                },
                {
                    "attribute": "wardrobe.garment",
                    "intent": "change",
                    "target": {
                        "text": "A black wool tailored blazer with peak lapels.",
                        "reference_id": "outfit_B",
                    },
                },
            ]
        },
    )
    codes = _error_codes(spec)
    assert "attribute_change_target_ambiguous" in codes or "schema" in codes


def test_pcc02_typed_lock_opposes_wardrobe_change():
    spec = _base_spec(
        locks={
            "adult_subject": True,
            "preserve_source_outfit": True,
        }
    )
    assert "attribute_lock_conflict" in _error_codes(spec)


# ---------------------------------------------------------------------------
# Regression digests (existing Creative Recipes; no APCC)
# ---------------------------------------------------------------------------


def test_pcc02_frozen_creative_recipe_prompt_digests_stable():
    cases = {
        "recipes/cr-001-material-driven-fashion-editorial/1.0.0.json": (
            "92f4c6643c005281ee2c287d72c05321aa0dd14043513761188a0b05c8e9a7e4"
        ),
        "recipes/cr-004-marble-afterimage/1.0.0.json": (
            "f42f2631e644e037c70ac2bf959c2587eff26fb981ae97dd169cf057b0d3d02d"
        ),
        "recipes/cr-011-era-reframing/1.0.0.json": (
            "f44b9d8f15bee39abe87a5a5b08a02be91b98b315ad321ad72dbb9b06d5e2715"
        ),
        "recipes/cr-015-cut-space-portrait/1.0.0.json": (
            "da5c59146a8bbb84846f52455952749c1dc1dffc65281b6bf7a64eed1b974142"
        ),
    }
    for path, expected in cases.items():
        receipt = compile_recipe(load_recipe(path))
        assert receipt["prompt_sha256"] == expected, path
        assert "attribute_preserve" not in receipt["compilation"]["prompt_sections"]
        assert "attribute_change" not in receipt["compilation"]["prompt_sections"]


def test_pcc02_schema_admits_version_35():
    schema = load_json("data/schemas/request.schema.json")
    assert "3.5" in schema["properties"]["version"]["enum"]
    assert "attribute_contract" in schema["properties"]
