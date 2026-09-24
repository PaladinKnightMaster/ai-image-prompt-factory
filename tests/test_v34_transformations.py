from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf.compiler import compile_result
from aipf.io import load_json, repo_root
from aipf.linting import lint_spec
from aipf.transformations import transformation_packs


CASES = {
    "v34-greek-marble-bust": "volumetric_sculpture",
    "v34-dunhuang-mural": "architectural_mural",
    "v34-edo-woodblock": "relief_print",
    "v34-blue-white-vase": "decorated_artifact",
}


def candidate(case_id: str) -> dict:
    return load_json(f"cases/candidates/{case_id}/case.json")


def test_four_generic_packs_validate_and_are_representation_only():
    packs = transformation_packs()
    schema = load_json("data/schemas/transformation_pack.schema.json")
    assert len(packs) == 4
    assert {pack["target_representation"] for pack in packs.values()} == set(CASES.values())
    for pack in packs.values():
        Draft202012Validator(schema).validate(pack)
        assert pack["source_representation"] == "portrait"
        assert set(pack) == {"id", "version", "source_representation", "target_representation", "representation_delta", "failure_modes"}
        assert not any(label in pack["id"] for label in ("greek", "dunhuang", "edo", "ming"))


@pytest.mark.parametrize("case_id,target", CASES.items())
def test_candidates_use_common_resolver_and_realizer(case_id, target):
    spec = candidate(case_id)
    Draft202012Validator(load_json("data/schemas/request.schema.json")).validate(spec)
    assert not [f for f in lint_spec(spec) if f["level"] == "error"]
    result = compile_result(spec)
    assert result["transformation_resolution"]["target_representation"] == target
    assert result["resolved_concepts"]
    assert [row["concept_id"] for row in result["lexical_trace"]] == [row["concept_id"] for row in result["resolved_concepts"]]
    assert "lexical_realization" in result["prompt_sections"]
    assert "art_method" not in result["prompt_sections"]
    assert len(result["lexical_trace"]) < 30
    assert spec["case_record"]["output_image"] is None
    assert spec["output"]["generation_requested"] is False


def test_conditional_concepts_and_era_do_not_leak():
    greek = compile_result(candidate("v34-greek-marble-bust"))
    mural = compile_result(candidate("v34-dunhuang-mural"))
    print_case = compile_result(candidate("v34-edo-woodblock"))
    ceramic = compile_result(candidate("v34-blue-white-vase"))
    assert "pose.contrapposto" not in {x["concept_id"] for x in greek["resolved_concepts"]}
    assert "sculpture.polychromy" not in {x["concept_id"] for x in greek["resolved_concepts"]}
    assert "polychromy" not in greek["prompt"].casefold()
    assert "mural.pouncing_transfer" not in {x["concept_id"] for x in mural["resolved_concepts"]}
    assert "pouncing" not in mural["prompt"].casefold()
    assert "woodblock.bokashi" not in {x["concept_id"] for x in print_case["resolved_concepts"]}
    assert "bokashi" not in print_case["prompt"].casefold()
    assert "Ming" not in ceramic["prompt"]
    assert "ceramic.porcelain_body" not in {x["concept_id"] for x in ceramic["resolved_concepts"]}
    assert candidate("v34-blue-white-vase")["historical"]["packs"] == []
    assert "historical" not in ceramic["prompt_sections"]


def test_incompatible_method_is_rejected_by_gate():
    spec = candidate("v34-edo-woodblock")
    spec["art"]["method"] = "marble_sculpture"
    assert "transformation_method_incompatible" in {f["code"] for f in lint_spec(spec)}
    with pytest.raises(ValueError):
        compile_result(spec)


def test_legacy_request_compilation_stays_on_original_path():
    spec = load_json("cases/regression/reg-edo-ukiyoe-process/case.json")
    result = compile_result(spec)
    assert "transformation_resolution" not in result
    assert "resolved_concepts" not in result
    assert "lexical_trace" not in result
    assert "art_method" in result["prompt_sections"]
    assert "lexical_realization" not in result["prompt_sections"]


def test_no_family_specific_compiler_or_realizer_branches():
    root = repo_root()
    source = (root / "src/aipf/compiler.py").read_text(encoding="utf-8") + (root / "src/aipf/lexical_realizer.py").read_text(encoding="utf-8")
    for pack_id in transformation_packs():
        assert pack_id not in source
