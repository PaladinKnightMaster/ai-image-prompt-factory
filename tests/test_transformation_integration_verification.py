"""TIV-01 — Transformation Integration Verification (offline).

Proves the four installed TransformationPacks emit their representation-change
contracts through the real compiler, including ArtMethod/era/form/reference
interactions on the V3.4 lexical path. No image generation.
See docs/TIV_01_TRANSFORMATION_INTEGRATION_VERIFICATION.md.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from aipf.compiler import compile_result
from aipf.io import load_json
from aipf.linting import lint_spec
from aipf.transformations import resolve_transformation, transformation_packs

PACK_IDS = [
    "portrait_to_volumetric_sculpture",
    "portrait_to_architectural_mural",
    "portrait_to_relief_print",
    "portrait_to_decorated_artifact",
]

CANDIDATES = {
    "portrait_to_volumetric_sculpture": "v34-greek-marble-bust",
    "portrait_to_architectural_mural": "v34-dunhuang-mural",
    "portrait_to_relief_print": "v34-edo-woodblock",
    "portrait_to_decorated_artifact": "v34-blue-white-vase",
}


def _candidate(case_id: str) -> dict:
    return load_json(f"cases/candidates/{case_id}/case.json")


def _errors(spec: dict) -> list[dict]:
    return [f for f in lint_spec(spec) if f["level"] == "error"]


def _assert_delta_emitted(result: dict, pack: dict) -> None:
    """Representation-change contract must appear as compiled prose, not only as pack ID."""
    section = result["prompt_sections"]["transformation"]
    resolved = result["transformation_resolution"]
    assert resolved["pack_id"] == pack["id"]
    assert resolved["source_representation"] == pack["source_representation"]
    assert resolved["target_representation"] == pack["target_representation"]
    delta = pack["representation_delta"]
    assert f"portrait → {pack['target_representation']}" in section
    assert delta["geometry"] in section
    assert delta["depth"] in section
    assert delta["surface_mapping"] in section
    # Provenance: compiler copies pack delta into resolution and prompt.
    assert resolved["representation_delta"] == delta


# ---------------------------------------------------------------------------
# Inventory / schema
# ---------------------------------------------------------------------------


def test_tiv01_four_transformation_packs_registered_and_schema_valid():
    packs = transformation_packs()
    schema = load_json("data/schemas/transformation_pack.schema.json")
    assert list(packs) == PACK_IDS
    for pack_id in PACK_IDS:
        pack = packs[pack_id]
        Draft202012Validator(schema).validate(pack)
        assert pack["version"] == "1.0.0"
        assert pack["source_representation"] == "portrait"
        assert set(pack["representation_delta"]) == {"geometry", "depth", "surface_mapping"}
        assert pack["failure_modes"]


# ---------------------------------------------------------------------------
# Positive representation-change paths (all four packs)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_tiv01_pack_emits_geometry_depth_and_surface_mapping(pack_id: str):
    pack = transformation_packs()[pack_id]
    spec = _candidate(CANDIDATES[pack_id])
    assert not _errors(spec)
    assert spec["output"]["generation_requested"] is False
    result = compile_result(spec)
    _assert_delta_emitted(result, pack)
    assert "art_method" not in result["prompt_sections"]
    assert "material_behavior" not in result["prompt_sections"]
    assert "lexical_realization" in result["prompt_sections"] or pack_id == "portrait_to_volumetric_sculpture"
    # Candidate methods for mural/print/ceramic/marble all carry concept_refs.
    assert result["resolved_concepts"]
    assert "material_failure_checks" in result["prompt_sections"]


def test_tiv01_sculpture_marble_lexicalizes_carved_stone_not_living_skin():
    result = compile_result(_candidate("v34-greek-marble-bust"))
    lexical = result["prompt_sections"]["lexical_realization"].casefold()
    transform = result["prompt_sections"]["transformation"].casefold()
    failures = result["prompt_sections"]["material_failure_checks"].casefold()
    assert "marble sculpture" in lexical
    assert "carved stone" in lexical or "carved planar" in lexical
    assert "living face with a surface filter" in transform or "continuous surface" in transform
    assert "living skin" in failures
    assert "three-dimensional object" in transform
    assert "readable volume" in transform


def test_tiv01_sculpture_bronze_emits_transform_without_marble_lexical_collapse():
    """bronze_sculpture has no concept_refs: representation delta still emits; material is failure-gated."""
    spec = deepcopy(_candidate("v34-greek-marble-bust"))
    spec["id"] = "tiv01-roman-bronze-bust"
    spec["request"] = "Translate this adult portrait into a Roman Imperial bronze sculptural bust."
    spec["historical"] = {
        "strictness": "historically_informed",
        "packs": ["roman_imperial"],
        "subperiod": "1st century CE",
        "region": "Roman world",
        "role": "adult portrait subject",
        "occasion": "bronze portrait bust",
        "intentional_hybrids": ["modern sitter identity translated into Roman bronze sculptural language"],
    }
    spec["art"] = {
        "method": "bronze_sculpture",
        "artifact_form": "bust",
        "artifact_state": "newly_created",
        "variant": None,
    }
    spec["transformation"] = {
        "pack_id": "portrait_to_volumetric_sculpture",
        "selected_concepts": [],
        "signature_atoms": {},
    }
    assert not _errors(spec)
    result = compile_result(spec)
    pack = transformation_packs()["portrait_to_volumetric_sculpture"]
    _assert_delta_emitted(result, pack)
    assert result["resolved_concepts"] == []
    assert "lexical_realization" not in result["prompt_sections"]
    failures = result["prompt_sections"]["material_failure_checks"].casefold()
    assert "orange plastic" in failures or "stone-like diffuse" in failures
    prompt = result["prompt"].casefold()
    assert "marble sculpture" not in prompt
    assert "carved stone mass" not in prompt
    assert "volumetric_sculpture" in result["prompt_sections"]["transformation"]


def test_tiv01_mural_binds_to_wall_not_buon_fresco_or_pasted_photo():
    result = compile_result(_candidate("v34-dunhuang-mural"))
    transform = result["prompt_sections"]["transformation"].casefold()
    lexical = result["prompt_sections"]["lexical_realization"].casefold()
    failures = result["prompt_sections"]["material_failure_checks"].casefold()
    assert "architectural plane" in transform
    assert "wall surface" in transform
    assert "photograph pasted onto a wall" not in transform  # failure mode text lives in pack, not auto-emitted
    assert "mineral-pigment mural" in lexical or "mineral pigment" in lexical
    assert "wall" in lexical
    assert "buon fresco" not in result["prompt"].casefold()
    assert "digital fresco filter" in failures
    assert "Dunhuang" in result["prompt_sections"]["historical"]


def test_tiv01_relief_print_uses_contour_registration_not_paper_texture_filter():
    result = compile_result(_candidate("v34-edo-woodblock"))
    transform = result["prompt_sections"]["transformation"].casefold()
    lexical = result["prompt_sections"]["lexical_realization"].casefold()
    failures = result["prompt_sections"]["material_failure_checks"].casefold()
    assert "reproducible contour" in transform
    assert "graphic value" in transform
    assert "impressed on a physical sheet" in transform or "physical sheet" in transform
    assert "woodblock" in lexical
    assert "keyblock" in lexical or "contour" in lexical
    assert "registration" in lexical or "kento" in lexical
    assert "anime screenshot with paper texture" in failures
    assert "Edo" in result["prompt_sections"]["historical"]


def test_tiv01_decorated_artifact_wraps_object_zones_not_flat_decal():
    result = compile_result(_candidate("v34-blue-white-vase"))
    transform = result["prompt_sections"]["transformation"].casefold()
    lexical = result["prompt_sections"]["lexical_realization"].casefold()
    failures = result["prompt_sections"]["material_failure_checks"].casefold()
    assert "physical zones" in transform
    assert "object-bound" in transform
    assert "curvature" in transform or "planes" in transform
    assert "flat decal" in transform or "decal" in transform
    assert "blue-and-white" in lexical or "cobalt" in lexical
    assert "vessel" in lexical or "curvature" in lexical or "zone" in lexical
    assert "decal" in failures or "floats above glaze" in failures
    assert "historical" not in result["prompt_sections"]  # candidate intentionally era-empty


# ---------------------------------------------------------------------------
# Path comparison and lexicalization rules
# ---------------------------------------------------------------------------


def test_tiv01_with_versus_without_transformation_changes_emission_path():
    with_t = _candidate("v34-greek-marble-bust")
    without = deepcopy(with_t)
    without.pop("transformation")
    r_with = compile_result(with_t)
    r_without = compile_result(without)
    assert "transformation" in r_with["prompt_sections"]
    assert "lexical_realization" in r_with["prompt_sections"]
    assert "art_method" not in r_with["prompt_sections"]
    assert "transformation" not in r_without["prompt_sections"]
    assert "art_method" in r_without["prompt_sections"]
    assert "material_behavior" in r_without["prompt_sections"]
    assert "lexical_realization" not in r_without["prompt_sections"]
    # Era selective anchors emit only on the non-transformation path.
    assert any(k.startswith("era_") for k in r_without["prompt_sections"])
    assert not any(k.startswith("era_") for k in r_with["prompt_sections"])


def test_tiv01_lexicalization_requires_concept_refs_from_selected_packs():
    marble = compile_result(_candidate("v34-greek-marble-bust"))
    assert any(c["concept_id"] == "method.marble_sculpture" for c in marble["resolved_concepts"])
    watercolor = deepcopy(_candidate("v34-greek-marble-bust"))
    watercolor["art"]["method"] = "watercolor"
    watercolor["art"]["artifact_form"] = "album_leaf"
    watercolor["transformation"]["pack_id"] = "portrait_to_volumetric_sculpture"
    # Family gate rejects watercolor for volumetric sculpture before lexicalization.
    assert any(f["code"] == "transformation_method_incompatible" for f in _errors(watercolor))


def test_tiv01_transformation_pack_failure_modes_are_resolved_but_not_auto_prose():
    """Pack failure_modes are carried in resolution; method typical_generation_failures emit as prose."""
    spec = _candidate("v34-edo-woodblock")
    result = compile_result(spec)
    resolved = resolve_transformation(spec)
    assert "photographic portrait beneath a print filter" in resolved["failure_modes"]
    # Auto-emitted failure prose comes from the ArtMethod, not the TransformationPack list.
    assert "anime screenshot with paper texture" in result["prompt_sections"]["material_failure_checks"]


def test_tiv01_repeated_compilation_is_deterministic():
    spec = _candidate("v34-blue-white-vase")
    first = compile_result(spec)
    second = compile_result(spec)
    assert first["prompt"] == second["prompt"]
    assert first["prompt_sections"] == second["prompt_sections"]
    assert [c["concept_id"] for c in first["resolved_concepts"]] == [
        c["concept_id"] for c in second["resolved_concepts"]
    ]


# ---------------------------------------------------------------------------
# Historical combinations
# ---------------------------------------------------------------------------


def test_tiv01_hellenistic_marble_statue_emits_transform_and_marble_lexical():
    spec = deepcopy(_candidate("v34-greek-marble-bust"))
    spec["id"] = "tiv01-hellenistic-marble"
    spec["historical"]["packs"] = ["hellenistic_greek"]
    spec["historical"]["subperiod"] = "Hellenistic"
    spec["art"]["artifact_form"] = "free_standing_statue"
    spec["transformation"] = {
        "pack_id": "portrait_to_volumetric_sculpture",
        "selected_concepts": [],
        "signature_atoms": {},
    }
    result = compile_result(spec)
    assert "Hellenistic" in result["prompt_sections"]["historical"]
    assert "volumetric_sculpture" in result["prompt_sections"]["transformation"]
    assert "marble sculpture" in result["prompt_sections"]["lexical_realization"].casefold()
    assert "free standing statue" in result["prompt_sections"]["artifact_form"].casefold()


def test_tiv01_edo_ceramic_keeps_object_bound_decoration_under_era_header():
    spec = deepcopy(_candidate("v34-blue-white-vase"))
    spec["historical"] = {
        "strictness": "historically_informed",
        "packs": ["edo"],
        "subperiod": "Edo ceramic context",
        "region": "Japan",
        "role": None,
        "occasion": None,
        "intentional_hybrids": ["modern portrait as Edo-informed ceramic decoration"],
    }
    result = compile_result(spec)
    assert "Edo" in result["prompt_sections"]["historical"]
    assert "decorated_artifact" in result["prompt_sections"]["transformation"]
    assert "physical zones" in result["prompt_sections"]["transformation"].casefold()
    assert "living adult figure" not in result["prompt"].casefold()


# ---------------------------------------------------------------------------
# Reference-role / preservation boundaries
# ---------------------------------------------------------------------------


def test_tiv01_reference_roles_remain_isolated_under_transformation():
    spec = deepcopy(_candidate("v34-greek-marble-bust"))
    spec["references"] = [
        {"id": "ref-id", "roles": ["identity"]},
        {"id": "ref-outfit", "roles": ["outfit"]},
        {"id": "ref-pose", "roles": ["pose"]},
    ]
    result = compile_result(spec)
    refs = result["prompt_sections"]["references"]
    assert "ref-id supplies identity only" in refs
    assert "ref-outfit supplies outfit only" in refs
    assert "ref-pose supplies pose only" in refs
    assert "Do not import unassigned identity" in refs
    # Identity preservation coexists with non-living sculpture translation.
    assert "recognizable" in result["prompt_sections"]["identity"].casefold()
    assert "living skin" in result["prompt_sections"]["material_failure_checks"].casefold()
    assert "continuous surface rather than a living face" in result["prompt_sections"]["transformation"].casefold() or (
        "living face with a surface filter" in result["prompt_sections"]["transformation"].casefold()
    )


def test_tiv01_legal_reference_roles_enum_is_unchanged():
    schema = load_json("data/schemas/request.schema.json")
    roles = schema["properties"]["references"]["items"]["properties"]["roles"]["items"]["enum"]
    assert roles == [
        "identity",
        "pose",
        "outfit",
        "hairstyle",
        "artifact",
        "style",
        "environment",
        "layout",
        "palette",
    ]


# ---------------------------------------------------------------------------
# Rejection / negative controls (real codes only)
# ---------------------------------------------------------------------------


def test_tiv01_rejects_incompatible_art_method_family():
    spec = deepcopy(_candidate("v34-edo-woodblock"))
    spec["art"]["method"] = "marble_sculpture"
    spec["art"]["artifact_form"] = "bust"
    codes = {f["code"] for f in _errors(spec)}
    assert "transformation_method_incompatible" in codes
    with pytest.raises(ValueError, match="Cannot compile invalid spec"):
        compile_result(spec)


def test_tiv01_rejects_missing_method_or_form_for_transformation():
    spec = deepcopy(_candidate("v34-blue-white-vase"))
    spec["art"]["method"] = None
    spec["art"]["artifact_form"] = None
    codes = {f["code"] for f in _errors(spec)}
    assert "transformation_requires_artifact" in codes


def test_tiv01_rejects_unknown_transformation_pack():
    spec = deepcopy(_candidate("v34-greek-marble-bust"))
    spec["transformation"]["pack_id"] = "portrait_to_oil_painting"
    assert any(f["code"] == "unknown_transformation_pack" for f in _errors(spec))


def test_tiv01_rejects_unavailable_lexical_concept_from_other_family():
    spec = deepcopy(_candidate("v34-edo-woodblock"))
    spec["transformation"]["selected_concepts"] = ["method.marble_sculpture"]
    assert any(f["code"] == "unavailable_concept" for f in _errors(spec))
    with pytest.raises(ValueError, match="Cannot compile invalid spec|Cannot realize unresolved"):
        compile_result(spec)


def test_tiv01_rejects_non_portrait_source_representation_by_schema():
    spec = deepcopy(_candidate("v34-greek-marble-bust"))
    spec["transformation"]["source_representation"] = "landscape"
    assert any(f["code"] == "schema" for f in _errors(spec))


def test_tiv01_rejects_incompatible_artifact_form_for_method():
    spec = deepcopy(_candidate("v34-blue-white-vase"))
    spec["art"]["artifact_form"] = "free_standing_statue"
    assert any(f["code"] == "art_form_incompatible" for f in _errors(spec))


# ---------------------------------------------------------------------------
# Chained-transformation feasibility (read-only schema inspection)
# ---------------------------------------------------------------------------


def test_tiv01_request_schema_lacks_derived_lineage_fields_for_chaining():
    """A→B→C chaining is not a first-class request-schema contract today."""
    schema = load_json("data/schemas/request.schema.json")
    props = schema["properties"]
    assert "transformation" in props
    assert "references" in props
    # No dedicated derived-reference / prior-generation lineage object on the request.
    assert "derived_from" not in props
    assert "lineage" not in props
    assert "prior_generation" not in props
    ref_props = props["references"]["items"]["properties"]
    assert "sha256" not in ref_props
    assert "original_byte_sha256" not in ref_props
    assert "parent_reference_id" not in ref_props
