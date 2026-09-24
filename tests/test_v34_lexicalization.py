from __future__ import annotations

from copy import deepcopy

import pytest

from aipf.compiler import compile_result
from aipf.evaluation import evaluation_template, summarize_evaluation
from aipf.io import load_json
from aipf.lexical_realizer import realize_concept, realize_concepts
from aipf.lexicon import concepts, lookup_candidates, validate_concept_refs, validate_registry
from aipf.linting import lint_spec


def candidate(case_id: str) -> dict:
    return load_json(f"cases/candidates/{case_id}/case.json")


def test_thirty_concepts_and_canonical_evidence_validate():
    assert len(concepts()) == 30
    assert validate_registry() == []
    assert validate_concept_refs() == []
    assert all(record["visible_gloss"] and record["evidence_refs"] for record in concepts().values())


def test_duplicate_ids_fail_but_disambiguated_shared_terms_are_allowed():
    registry = load_json("references/lexicon/registry.json")
    duplicate = deepcopy(registry)
    duplicate["concepts"].append(deepcopy(duplicate["concepts"][0]))
    assert any("duplicate concept ID" in error for error in validate_registry(duplicate))
    shared = deepcopy(registry)
    second = deepcopy(shared["concepts"][1])
    second.update(id="garment.other_sense", preferred_term="marble sculpture", domain="garment", visible_gloss="a garment named with the same words but a distinct meaning")
    shared["concepts"].append(second)
    assert not any("preferred term" in error for error in validate_registry(shared))
    ambiguous = deepcopy(registry)
    second["domain"] = "art_method"
    second["retrieval_scope"] = {"art_method_ids": ["marble_sculpture"]}
    ambiguous["concepts"].append(second)
    assert any("insufficiently disambiguated" in error for error in validate_registry(ambiguous))


@pytest.mark.parametrize("phrase,concept_id,match_type", [
    ("Greek cape", "garment.himation", "retrieval_term"),
    ("big Greek cloak", "garment.himation", "retrieval_term"),
    ("old Japanese print", "method.japanese_woodblock_print", "retrieval_term"),
    ("Japanese print gradient", "woodblock.bokashi", "retrieval_term"),
    ("blue pottery", "method.blue_white_ceramic", "retrieval_term"),
    ("ancient wall painting", "method.mineral_pigment_mural", "retrieval_term"),
    ("kento registration", "woodblock.kento_registration", "alias"),
    ("bokashi", "woodblock.bokashi", "preferred_term"),
])
def test_candidate_lookup_is_non_authoritative(phrase, concept_id, match_type):
    candidates = lookup_candidates(phrase)
    assert {"concept_id": concept_id, "matched_text": phrase, "match_type": match_type} in candidates or any(
        item["concept_id"] == concept_id and item["match_type"] == match_type for item in candidates
    )
    assert all("compatibility" not in item and "historical_confidence" not in item for item in candidates)


def test_ambiguous_alias_remains_two_candidates():
    registry = load_json("references/lexicon/registry.json")
    clone = deepcopy(registry["concepts"][0])
    clone.update(id="method.other_marble_sense", preferred_term="other marble concept", visible_gloss="a different visible sense with a separate stable concept identity", retrieval_scope={"pack_ids": ["other"]}, aliases=["shared term"])
    registry["concepts"][0]["aliases"] = ["shared term"]
    registry["concepts"].append(clone)
    matches = lookup_candidates("shared term", registry)
    assert {row["concept_id"] for row in matches} == {"method.marble_sculpture", "method.other_marble_sense"}


def test_aliases_cannot_bypass_semantic_gates():
    spec = candidate("v34-greek-marble-bust")
    spec["request"] += " Greek cape."
    assert "garment.himation" in {c["concept_id"] for c in lookup_candidates(spec["request"])}
    assert "garment.himation" not in {c["concept_id"] for c in compile_result(spec)["resolved_concepts"]}
    spec["transformation"]["selected_concepts"].append("pose.contrapposto")
    assert "pose_geometry_incompatible" in {finding["code"] for finding in lint_spec(spec)}


def test_conditional_selection_requires_compatibility_and_explicit_context():
    print_spec = candidate("v34-edo-woodblock")
    print_spec["transformation"]["selected_concepts"].append("woodblock.bokashi")
    assert "woodblock.bokashi" in {row["concept_id"] for row in compile_result(print_spec)["resolved_concepts"]}
    mural = candidate("v34-dunhuang-mural")
    mural["transformation"]["selected_concepts"].append("mural.pouncing_transfer")
    assert "pouncing_unresolved" in {finding["code"] for finding in lint_spec(mural)}
    mural["evidence"] = {"claim_ids": ["mogao-pouncing-v34-001"]}
    assert "mural.pouncing_transfer" in {row["concept_id"] for row in compile_result(mural)["resolved_concepts"]}
    greek = candidate("v34-greek-marble-bust")
    greek["transformation"]["selected_concepts"].append("sculpture.polychromy")
    assert "polychromy_unresolved" in {finding["code"] for finding in lint_spec(greek)}
    greek["evidence"] = {"claim_ids": ["greek-marble-polychromy-001"]}
    assert "sculpture.polychromy" in {row["concept_id"] for row in compile_result(greek)["resolved_concepts"]}


def test_profile_controls_detail_without_inventing_modifiers():
    resolved = {"concept_id": "method.marble_sculpture", "source_component": "art_method", "resolved_modifiers": {"signature_atoms": ["carved planar transitions", "deliberate support and termination"]}}
    compact, compact_trace, _ = realize_concept(resolved, "compact")
    precise, precise_trace, _ = realize_concept(resolved, "historical_precision")
    assert "carved stone mass" in compact
    assert len(precise) > len(compact)
    assert compact_trace["concept_id"] == precise_trace["concept_id"]
    budgeted = realize_concepts([resolved], "historical_precision", budget=80)
    assert "carved stone mass" in budgeted["clauses"][0]
    assert "carved planar transitions" not in budgeted["clauses"][0]
    himation = {"concept_id": "garment.himation", "source_component": "era_pack:classical_greek", "resolved_modifiers": {}}
    text, _, _ = realize_concept(himation, "historical_precision")
    assert "wool" not in text
    with pytest.raises(ValueError):
        realize_concept({**himation, "resolved_modifiers": {"signature_atoms": ["invented wool"]}}, "historical_precision")


def test_coalescing_and_trace_do_not_duplicate_concepts():
    rows = [{"concept_id": cid, "source_component": "art_method", "resolved_modifiers": {}} for cid in ("woodblock.keyblock", "woodblock.color_block")]
    result = realize_concepts(rows + rows[:1], "compact")
    assert len(result["clauses"]) == 1
    assert [row["concept_id"] for row in result["lexical_trace"]] == ["woodblock.keyblock", "woodblock.color_block"]


def test_evaluation_keeps_transformation_as_a_separate_gate():
    template = evaluation_template("v34", candidate("v34-blue-white-vase"))
    assert "transformation_fidelity" in template["scores"]
    assert "artifact_integration" in template["scores"]
    template["scores"].update(aesthetic_quality=5, transformation_fidelity=2, artifact_integration=5)
    assert summarize_evaluation(template)["transformation_gate"] == "fail"
    assert "TERM_REALIZATION_FAILURE" in load_json("evaluation/failure_taxonomy.json")["classes"]


def test_experiment_remains_planned_and_unverified():
    experiment = load_json("experiments/definitions/EXP-019.json")
    assert experiment["status"] == "planned"
    assert [row["id"] for row in experiment["variants"]] == ["C", "A", "B"]
    assert experiment["preregistration"]["conclusion"] == "unverified"
