"""Integrity checks for the frozen, unexecuted EXP-019 textual fixture."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from aipf.experiments import plan_experiment


ROOT = Path(__file__).resolve().parents[1]
DEFINITION_PATH = ROOT / "experiments/definitions/EXP-019.json"
FIXTURE_PATH = ROOT / "experiments/fixtures/EXP-019/EXP-019-BOKASHI-01.fixture.json"
PREREG_PATH = ROOT / "experiments/preregistrations/EXP-019.PREREGISTRATION.md"
FIXTURE_SHA256 = "a47d5cb22b3ee0b83bc585db310cfe3e4a9facc2e9227777503248156d93a1b0"
DEFINITION_SHA256 = "c5ced96c0357fbecb43169b96ea438aa7fd7e7fd739f1fb34381a3fded72bfe7"
PROMPT_BINDINGS = {
    "C": (883, 144, "481ecd1360a354f545c23a012525762d4505fa8e7df8a95b034c92dc9b45b6e4"),
    "A": (788, 128, "96ec98c7ae489f2722139000bd2b6b04a040868ae1bbb4d7ec86dc7ac259bdf1"),
    "B": (892, 145, "6d202bca0d5928d8369c8b4ad8c78aefcd895c32a215c2abd6d1ec01805baf69"),
}


def test_exp019_fixture_and_prompt_bindings() -> None:
    definition_bytes = DEFINITION_PATH.read_bytes()
    fixture_bytes = FIXTURE_PATH.read_bytes()
    definition = json.loads(definition_bytes)
    fixture = json.loads(fixture_bytes)
    prereg = PREREG_PATH.read_text(encoding="utf-8")

    assert definition["experiment_id"] == "EXP-019"
    assert definition["version"] == "1.0.0"
    assert definition["status"] == "planned"
    assert fixture["fixture_id"] == "EXP-019-BOKASHI-01"
    assert fixture["version"] == "1.0.0"
    assert fixture["status"] == "frozen"
    fixture_hash = sha256(fixture_bytes).hexdigest()
    assert fixture_hash == FIXTURE_SHA256
    assert sha256(definition_bytes).hexdigest() == DEFINITION_SHA256
    assert definition["fixture"]["sha256"] == fixture_hash
    assert fixture_hash in prereg
    assert sha256(definition_bytes).hexdigest() in prereg

    planned = {item["id"]: item["prompt"] for item in plan_experiment(definition)["variants"]}
    assert set(planned) == {"C", "A", "B"}
    bindings = definition["prompt_bindings"]["conditions"]
    for condition, prompt in planned.items():
        assert prompt == fixture["common_prompt"] + " " + fixture["treatment_clauses"][condition]
        assert prompt == prompt.rstrip()
        assert len(prompt) == bindings[condition]["characters"]
        assert len(prompt.split()) == bindings[condition]["whitespace_delimited_words"]
        assert sha256(prompt.encode("utf-8")).hexdigest() == bindings[condition]["sha256"]
        assert (len(prompt), len(prompt.split()), sha256(prompt.encode("utf-8")).hexdigest()) == PROMPT_BINDINGS[condition]
    assert definition["prompt_bindings"]["token_estimate"] is None


def test_exp019_isolation_and_review_freeze() -> None:
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    config = definition["generation_config"]
    prereg = definition["preregistration"]

    assert definition["experiment_layer"] == "isolation_bench"
    assert definition["target_concept_id"] == "woodblock.bokashi"
    assert definition["requires_reference_inputs"] == fixture["reference_inputs"] == []
    assert definition["transformation"] is fixture["transformation"] is None
    assert fixture["transformation_pack"] is fixture["era"] is fixture["identity"] is fixture["named_artist"] is None
    assert definition["model_target"] == config["requested_model"] == "gpt-image-2-2026-04-21"
    assert config["api_script_model_argument"] == "--model gpt-image-2-2026-04-21"
    assert (config["width"], config["height"], config["quality"], config["background"]) == (1024, 1536, "high", "opaque")
    assert config["reference_inputs"] == [] and config["seed"] is None
    assert config["image_count_per_invocation"] == 1 and config["total_images_planned"] == 12
    assert definition["evaluation_dimensions"] == ["art_material_fidelity", "semantic_compliance", "aesthetic_quality", "technical_defects"]
    assert prereg["status"] == "frozen"
    assert prereg["replicates_per_condition"] == 4
    assert prereg["invocation_blocks"] == [["B", "A", "C"], ["C", "B", "A"], ["B", "C", "A"], ["A", "B", "C"]]
    assert Counter(sum(prereg["invocation_blocks"], [])) == {"A": 4, "B": 4, "C": 4}
    assert prereg["review"]["independent_blind_reviewers_required"] == 2
    assert prereg["review"]["freeze_both_reviews_before_reveal"] is True
    assert prereg["review"]["post_reveal_adjudication"] is False
    assert prereg["execution_provenance"]["no_execution_receipt_or_result_created_by_this_freeze"] is True
