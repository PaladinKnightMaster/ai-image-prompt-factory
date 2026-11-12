"""EIT-01 — Era-Informed Transformation Integrity.

Verifies that method-matched, evidence-compatible EraPack fragments may emit
under TransformationPack compilation without restoring living-scene anchors,
bypassing craft-process concept gates, or changing the standard path.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

import pytest

from aipf.compiler import (
    COMPILER_VERSION,
    TRANSFORMATION_COMPILER_VERSION,
    compile_result,
)
from aipf.io import load_json
from aipf.linting import lint_spec
from aipf.recipes import compile_recipe, load_recipe


def _errors(spec: dict) -> list[dict]:
    return [f for f in lint_spec(spec) if f["level"] == "error"]


def _anchor_keys(sections: dict) -> list[str]:
    return [
        k
        for k in sections
        if k.startswith("era_") and not k.startswith("era_fragment_")
    ]


def _base_transform_spec(
    *,
    case_id: str,
    request: str,
    packs: list[str],
    method: str,
    form: str,
    state: str,
    pack_id: str,
    subperiod: str | None = None,
    region: str | None = None,
    role: str | None = None,
    occasion: str | None = None,
    selected_concepts: list[str] | None = None,
    intentional_hybrids: list[str] | None = None,
    strictness: str = "historically_informed",
) -> dict:
    return {
        "version": "3.2",
        "id": case_id,
        "request": request,
        "route": "artifact_transform",
        "locks": {"adult_subject": True},
        "references": [],
        "identity": {"mode": "identity_unlocked", "locked_features": []},
        "body_transformation": {"mode": "artistic_stylization"},
        "historical": {
            "strictness": strictness,
            "packs": packs,
            "subperiod": subperiod,
            "region": region,
            "role": role,
            "occasion": occasion,
            "intentional_hybrids": intentional_hybrids or [],
        },
        "art": {
            "method": method,
            "artifact_form": form,
            "artifact_state": state,
            "variant": None,
        },
        "transformation": {
            "pack_id": pack_id,
            "selected_concepts": selected_concepts or [],
        },
        "requested_elements": [],
        "director": {
            "moment": "a settled artifact reading",
            "camera": "three-quarter object frame",
            "light_source": "one controlled key revealing object volume",
            "micro_story": "era-informed representation transform",
        },
        "output": {
            "profile": "standard",
            "aspect_ratio": "4:5",
            "text_in_image": [],
            "generation_requested": False,
        },
        "visual_patterns": {"enable_validated": False, "include": [], "exclude": []},
    }


def _e1() -> dict:
    return _base_transform_spec(
        case_id="eit-e1-hellenistic-marble",
        request="Translate this adult portrait into a Hellenistic Greek marble free-standing statue.",
        packs=["hellenistic_greek"],
        method="marble_sculpture",
        form="free_standing_statue",
        state="newly_created",
        pack_id="portrait_to_volumetric_sculpture",
        subperiod="Hellenistic",
        region="Eastern Mediterranean",
    )


def _e2() -> dict:
    return _base_transform_spec(
        case_id="eit-e2-roman-bronze-bust",
        request="Translate this adult portrait into a Roman Imperial bronze bust.",
        packs=["roman_imperial"],
        method="bronze_sculpture",
        form="bust",
        state="newly_created",
        pack_id="portrait_to_volumetric_sculpture",
        subperiod="early Imperial",
        region="Rome",
    )


def _e3() -> dict:
    return _base_transform_spec(
        case_id="eit-e3-dunhuang-mural",
        request="Translate this adult portrait into a Dunhuang mineral-pigment mural on a wall surface.",
        packs=["dunhuang"],
        method="mineral_pigment_mural",
        form="wall_surface",
        state="modern_reconstruction",
        pack_id="portrait_to_architectural_mural",
        subperiod="10th-century Mogao donor-portrait evidence family",
        region="Mogao cave-temple setting",
    )


def _e4() -> dict:
    return _base_transform_spec(
        case_id="eit-e4-edo-woodblock",
        request="Translate this adult portrait into an Edo Japanese woodblock print.",
        packs=["edo"],
        method="japanese_woodblock_print",
        form="print_sheet",
        state="newly_created",
        pack_id="portrait_to_relief_print",
        subperiod="late 18th-century color-print context",
        region="Japan",
    )


def _e5() -> dict:
    return _base_transform_spec(
        case_id="eit-e5-edo-ceramic",
        request="Translate this adult portrait into Edo-informed blue-and-white ceramic decoration on a vase.",
        packs=["edo"],
        method="blue_white_ceramic",
        form="vase",
        state="newly_created",
        pack_id="portrait_to_decorated_artifact",
        subperiod="Edo porcelain workshop context",
        region="Japan",
    )


# ---------------------------------------------------------------------------
# E1–E5 representative cases
# ---------------------------------------------------------------------------


def test_eit01_e1_hellenistic_marble_emits_sculpture_fragment():
    spec = _e1()
    assert not _errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "era_fragment_hellenistic_greek" in sections
    frag = sections["era_fragment_hellenistic_greek"].casefold()
    assert "torque" in frag or "directional movement" in frag
    assert "support" in frag or "weight" in frag
    assert _anchor_keys(sections) == []
    assert "roman" not in frag
    assert "polychromy" not in result["prompt"].casefold()
    assert "volumetric_sculpture" in sections["transformation"]
    assert "lexical_realization" in sections
    assert result["compiler_version"] == TRANSFORMATION_COMPILER_VERSION


def test_eit01_e2_roman_bronze_bust_emits_bust_fragment_without_marble_swap():
    spec = _e2()
    assert not _errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "era_fragment_roman_imperial" in sections
    frag = sections["era_fragment_roman_imperial"].casefold()
    assert "bust" in frag
    assert "truncation" in frag or "support" in frag
    assert _anchor_keys(sections) == []
    assert "marble carving" not in result["prompt"].casefold()
    # Bronze lexicalization gap remains; representation delta must still emit.
    assert "volumetric_sculpture" in sections["transformation"]
    assert result["compiler_version"] == TRANSFORMATION_COMPILER_VERSION


def test_eit01_e3_dunhuang_mural_emits_wall_bound_fragment():
    spec = _e3()
    assert not _errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "Dunhuang" in sections["historical"]
    assert "10th-century" in sections["historical"] or "Mogao" in sections["historical"]
    assert "era_fragment_dunhuang" in sections
    frag = sections["era_fragment_dunhuang"].casefold()
    assert "wall-bound" in frag or "plaster" in frag or "mineral" in frag
    assert "iconographic restraint" in frag
    assert "buon fresco" not in result["prompt"].casefold()
    assert "pouncing" not in result["prompt"].casefold()
    assert _anchor_keys(sections) == []


def test_eit01_e4_edo_print_keeps_header_and_lexicalization_without_bokashi_bypass():
    """Edo ukiyoe fragment mentions bokashi; withhold until craft concept is selected."""
    spec = _e4()
    assert not _errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "Edo" in sections["historical"]
    assert "relief_print" in sections["transformation"]
    assert "lexical_realization" in sections
    assert "era_fragment_edo" not in sections
    assert "bokashi" not in result["prompt"].casefold()
    assert "digital cartoon" not in result["prompt"].casefold()
    assert _anchor_keys(sections) == []
    # Print mechanism still comes from method lexicalization / failures.
    lexical = sections["lexical_realization"].casefold()
    assert "keyblock" in lexical or "registration" in lexical or "woodblock" in lexical


def test_eit01_e4_edo_print_fragment_emits_when_bokashi_selected():
    spec = _e4()
    spec["transformation"]["selected_concepts"] = ["woodblock.bokashi"]
    assert not _errors(spec)
    result = compile_result(spec)
    assert "era_fragment_edo" in result["prompt_sections"]
    frag = result["prompt_sections"]["era_fragment_edo"].casefold()
    assert "print logic" in frag or "registration" in frag
    assert "digital cartoon" in frag
    assert "bokashi" in result["prompt"].casefold()
    assert any(c["concept_id"] == "woodblock.bokashi" for c in result["resolved_concepts"])


def test_eit01_e5_edo_ceramic_emits_ceramic_not_print_fragment():
    spec = _e5()
    assert not _errors(spec)
    result = compile_result(spec)
    sections = result["prompt_sections"]
    assert "era_fragment_edo" in sections
    frag = sections["era_fragment_edo"].casefold()
    assert "ceramic" in frag or "blue-and-white" in frag
    assert "jingdezhen" in frag or "ming" in frag  # explicit non-import warning
    assert "digital cartoon" not in frag
    assert "registration" not in frag
    assert "living portrait" not in result["prompt"].casefold()
    assert "decorated_artifact" in sections["transformation"]
    assert _anchor_keys(sections) == []


# ---------------------------------------------------------------------------
# Negative controls
# ---------------------------------------------------------------------------


def test_eit01_no_living_portrait_fragment_for_sculpture():
    spec = _base_transform_spec(
        case_id="eit-neg-living",
        request="Translate into Classical Greek marble bust.",
        packs=["classical_greek"],
        method="marble_sculpture",
        form="bust",
        state="newly_created",
        pack_id="portrait_to_volumetric_sculpture",
        occasion="sculptural portrait",
    )
    result = compile_result(spec)
    frag = result["prompt_sections"].get("era_fragment_classical_greek", "").casefold()
    assert "living adult figure" not in frag
    assert "living person" not in frag
    assert _anchor_keys(result["prompt_sections"]) == []


def test_eit01_no_wardrobe_architecture_anchors_on_bust():
    result = compile_result(_e2())
    prompt = result["prompt"].casefold()
    assert _anchor_keys(result["prompt_sections"]) == []
    assert "anchors selectively" not in prompt


def test_eit01_no_print_fragment_substituted_onto_ceramic():
    result = compile_result(_e5())
    frag = result["prompt_sections"]["era_fragment_edo"].casefold()
    assert "carved contour hierarchy" not in frag
    assert "digital cartoon filter" not in frag


def test_eit01_no_polychromy_without_evidence():
    spec = _e1()
    result = compile_result(spec)
    assert "polychromy" not in result["prompt"].casefold()
    assert "sculpture.polychromy" not in {
        c["concept_id"] for c in result["resolved_concepts"]
    }


def test_eit01_dunhuang_strict_narrowing_still_enforced():
    spec = _e3()
    spec["historical"]["strictness"] = "strict_reconstruction"
    spec["historical"]["subperiod"] = None
    codes = {f["code"] for f in _errors(spec)}
    assert "dunhuang_strict_narrowing" in codes


def test_eit01_wuxia_overlay_is_not_historical_era_fragment():
    spec = _base_transform_spec(
        case_id="eit-neg-wuxia",
        request="Translate into marble sculpture with wuxia overlay.",
        packs=["ming", "wuxia"],
        method="marble_sculpture",
        form="bust",
        state="newly_created",
        pack_id="portrait_to_volumetric_sculpture",
        intentional_hybrids=["wuxia narrative over Ming material base"],
        strictness="fantasy_hybrid",
    )
    # Wuxia alone as era is blocked; with ming base it should compile.
    assert not _errors(spec)
    result = compile_result(spec)
    assert "overlay_wuxia" in result["prompt_sections"]
    assert not any(
        k.startswith("era_fragment_wuxia") for k in result["prompt_sections"]
    )
    assert "Genre/fantasy overlay" in result["prompt_sections"]["overlay_wuxia"]


def test_eit01_incompatible_transformation_method_gate_preserved():
    spec = _e4()
    spec["art"]["method"] = "watercolor"
    spec["art"]["artifact_form"] = "album_leaf"
    codes = {f["code"] for f in _errors(spec)}
    assert "transformation_method_incompatible" in codes


def test_eit01_no_era_content_when_no_era_selected():
    spec = _base_transform_spec(
        case_id="eit-neg-no-era",
        request="Translate into marble free-standing statue with no era pack.",
        packs=[],
        method="marble_sculpture",
        form="free_standing_statue",
        state="newly_created",
        pack_id="portrait_to_volumetric_sculpture",
    )
    result = compile_result(spec)
    assert "historical" not in result["prompt_sections"]
    assert not any(k.startswith("era_") for k in result["prompt_sections"])


def test_eit01_tang_living_fragment_not_used_as_sculpture_fallback():
    spec = _base_transform_spec(
        case_id="eit-neg-tang-fallback",
        request="Translate into marble bust with Tang pack only.",
        packs=["tang"],
        method="marble_sculpture",
        form="bust",
        state="newly_created",
        pack_id="portrait_to_volumetric_sculpture",
    )
    result = compile_result(spec)
    assert "era_fragment_tang" not in result["prompt_sections"]
    assert "living person" not in result["prompt"].casefold()
    assert "Tang" in result["prompt_sections"]["historical"]


def test_eit01_generation_requested_remains_false():
    for builder in (_e1, _e2, _e3, _e4, _e5):
        spec = builder()
        assert spec["output"]["generation_requested"] is False
        result = compile_result(spec)
        assert result["lint_findings"] is not None


# ---------------------------------------------------------------------------
# Path / version / determinism / frozen contracts
# ---------------------------------------------------------------------------


def test_eit01_standard_path_unchanged_for_non_transformation():
    case = load_json("cases/golden/05-tang-dunhuang-mural/case.json")
    spec = {
        k: v
        for k, v in case.items()
        if k not in {"title", "status", "case_record", "notes"}
    }
    result = compile_result(spec)
    assert "transformation" not in result["prompt_sections"]
    assert result["compiler_version"] == COMPILER_VERSION
    assert "era_fragment_dunhuang" in result["prompt_sections"]
    assert "art_method" in result["prompt_sections"]


def test_eit01_representation_delta_and_lexicalization_retained():
    result = compile_result(_e1())
    sections = result["prompt_sections"]
    assert "Representation change" in sections["transformation"]
    assert "lexical_realization" in sections
    assert "era_fragment_hellenistic_greek" in sections
    # Fragment should not merely restate the transformation delta.
    assert sections["era_fragment_hellenistic_greek"] not in sections["transformation"]


def test_eit01_deterministic_repeated_compilation():
    spec = _e1()
    first = compile_result(spec)
    second = compile_result(deepcopy(spec))
    assert first["prompt"] == second["prompt"]
    assert first["compiler_version"] == second["compiler_version"]
    assert sha256(first["prompt"].encode("utf-8")).hexdigest() == sha256(
        second["prompt"].encode("utf-8")
    ).hexdigest()


def test_eit01_frozen_transform_recipes_keep_prompt_digests():
    """Era-empty transformation recipes must not silently change frozen prompts."""
    expected = {
        "cr-004-marble-afterimage": "f42f2631e644e037c70ac2bf959c2587eff26fb981ae97dd169cf057b0d3d02d",
        "cr-005-silk-on-plaster": "6e3f9d6416fffc05c4e94cf81c3312a80b3564f1cd1689a54bfbe31da13984da",
        "cr-007-porcelain-echo": "ae067b7b1d6c1b1877cdd1b4f9d39d5ab0e6bc861611178b0c47b68fca4138eb",
        "cr-012-keyblock-echo": "940f156c45b14443026aefd401b91e7cf8133954c538a86504d58eb3bcecfb58",
    }
    for recipe_id, prompt_sha in expected.items():
        path = f"recipes/{recipe_id}/1.0.0.json"
        receipt = compile_recipe(load_recipe(path))
        assert receipt["prompt_sha256"] == prompt_sha
        assert receipt["compilation"]["compiler_version"] == TRANSFORMATION_COMPILER_VERSION
        assert receipt["compilation"]["prompt_sections"].get("historical") is None or (
            load_recipe(path)["semantic_spec"]["historical"]["packs"] == []
        )


def test_eit01_candidate_edo_print_still_blocks_bokashi_without_selection():
    spec = load_json("cases/candidates/v34-edo-woodblock/case.json")
    result = compile_result(spec)
    assert "bokashi" not in result["prompt"].casefold()
    assert "era_fragment_edo" not in result["prompt_sections"]
    assert "Edo" in result["prompt_sections"]["historical"]
