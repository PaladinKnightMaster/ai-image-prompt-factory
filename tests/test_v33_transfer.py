import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from aipf.experiment_runs import create_run_plan
from aipf.io import repo_root


TRANSFER_ROOT = Path("benchmarks/transfer")
MAPPING_REL = TRANSFER_ROOT / "mappings/EXP-007-015.v1.json"


def _load(rel):
    return json.loads((repo_root() / rel).read_text(encoding="utf-8"))


def _archetypes():
    return [
        _load(TRANSFER_ROOT / "archetypes" / f"TB-A{i:02d}.json")
        for i in range(1, 8)
    ]


def test_transfer_archetypes_validate_and_hash_their_first_party_prompts():
    schema = _load("data/schemas/transfer_archetype.schema.json")
    validator = Draft202012Validator(schema)
    archetypes = _archetypes()

    assert [item["archetype_id"] for item in archetypes] == [
        "TB-A01", "TB-A02", "TB-A03", "TB-A04", "TB-A05", "TB-A06", "TB-A07"
    ]

    for item in archetypes:
        assert list(validator.iter_errors(item)) == []
        digest = hashlib.sha256(
            item["first_party_baseline_prompt"].encode("utf-8")
        ).hexdigest()
        assert digest == item["baseline_prompt_sha256"]
        assert item["provenance"]["source_prompt_text_copied"] is False
        assert item["provenance"]["source_images_embedded"] is False
        assert item["provenance"]["creator_specific_phrasing_retained"] is False
        assert item["provenance"]["first_party_prompt"] is True
        assert item["provenance"]["publication_safe"] is True


def test_transfer_public_surface_contains_no_private_prompt_ids_or_creator_names():
    paths = [
        *sorted((repo_root() / TRANSFER_ROOT).rglob("*.json")),
        repo_root() / TRANSFER_ROOT / "README.md",
        repo_root() / "docs/TRANSFER_BENCHMARK.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert re.search(r"\b(?:APC|FSC|GAC|LAC|LCC)-P\d{4}\b", text) is None

    # Public transfer fixtures should describe mechanisms, not preserve
    # creator/source-corpus attribution or wording.
    for forbidden in ("AIPixLab", "Larus Canus", "Liyue AI", "MrLarus"):
        assert forbidden not in text


def test_transfer_mapping_validates_and_covers_exp007_through_exp015_once():
    mapping = _load(MAPPING_REL)
    schema = _load("data/schemas/transfer_mapping.schema.json")
    assert list(Draft202012Validator(schema).iter_errors(mapping)) == []

    ids = [item["experiment_id"] for item in mapping["mappings"]]
    assert ids == [f"EXP-{i:03d}" for i in range(7, 16)]
    assert len(ids) == len(set(ids))
    assert mapping["rules"]["one_factor_per_run"] is True
    assert mapping["rules"]["no_pattern_auto_promotion"] is True
    assert mapping["rules"]["private_corpus_as_fixture_forbidden"] is True
    assert mapping["design_basis"]["raw_private_content_embedded"] is False


def test_transfer_mapping_matches_archetype_and_experiment_versions():
    mapping = _load(MAPPING_REL)
    archetype_versions = {
        item["archetype_id"]: item["version"]
        for item in _archetypes()
    }

    for item in mapping["mappings"]:
        definition = _load(item["definition_path"])
        assert definition["experiment_id"] == item["experiment_id"]
        assert definition["version"] == item["experiment_version"]
        assert definition["version"] == "1.1.0"
        assert definition["transfer_benchmark"]["layer"] == "transfer"
        assert definition["transfer_benchmark"]["archetype_id"] == item["archetype_id"]
        assert (
            definition["transfer_benchmark"]["archetype_version"]
            == archetype_versions[item["archetype_id"]]
        )


def test_transfer_experiments_no_longer_use_the_old_generic_portrait_baseline():
    old = "Create a realistic adult portrait in a refined interior."
    for i in range(7, 16):
        definition = _load(f"experiments/definitions/EXP-{i:03d}.json")
        assert old not in definition["baseline_prompt"]


def test_exp007_transfer_ablation_only_removes_8k_masterpiece():
    run = create_run_plan("EXP-007", replicates=1)
    prompts = {item["variant_id"]: item["prompt"] for item in run["variants"]}

    assert "8K masterpiece" in prompts["control"]
    assert "8K masterpiece" not in prompts["variant"]
    assert "ultra-detailed" in prompts["control"]
    assert "ultra-detailed" in prompts["variant"]
    assert prompts["variant"] == prompts["control"].replace(
        " 8K masterpiece, ultra-detailed.",
        " ultra-detailed.",
    )


def test_exp008_transfer_changes_only_constraint_scope():
    run = create_run_plan("EXP-008", replicates=1)
    prompts = {item["variant_id"]: item["prompt"] for item in run["variants"]}

    old = "Avoid bad anatomy, extra fingers, blur, artifacts, text, watermark, logo."
    new = (
        "Avoid distorted fingers around the tray and unintended readable text "
        "on the archival tags."
    )
    assert old in prompts["control"]
    assert new in prompts["variant"]
    assert prompts["variant"] == prompts["control"].replace(old, new)


def test_exp009_transfer_changes_only_emotion_wording():
    run = create_run_plan("EXP-009", replicates=1)
    prompts = {item["variant_id"]: item["prompt"] for item in run["variants"]}

    old = "Overall mood: quiet, tense, expectant, uncertain, restrained."
    new = (
        "Overall mood: restrained anticipation, calm on the surface with a "
        "slight sense of uncertainty."
    )
    assert old in prompts["control"]
    assert new in prompts["variant"]
    assert prompts["variant"] == prompts["control"].replace(old, new)


def test_exp010_transfer_preserves_semantic_anchors_across_prompt_formats():
    run = create_run_plan("EXP-010", replicates=1)
    prompts = {
        item["variant_id"]: item["prompt"].lower()
        for item in run["variants"]
    }

    anchors = [
        "adult courier",
        "rain-darkened rooftop market",
        "blue hour",
        "folded map tube",
        "layered travel coat",
        "signal lantern",
        "three-quarter full-body",
        "asymmetric",
        "game promotional",
        "ui",
        "logos",
        "captions",
        "decorative text",
    ]
    for anchor in anchors:
        assert anchor in prompts["control"]
        assert anchor in prompts["variant"]


def test_exp011_and_exp012_use_same_fashion_transfer_archetype_for_distinct_factors():
    exp11 = _load("experiments/definitions/EXP-011.json")
    exp12 = _load("experiments/definitions/EXP-012.json")
    assert exp11["transfer_benchmark"]["archetype_id"] == "TB-A01"
    assert exp12["transfer_benchmark"]["archetype_id"] == "TB-A01"

    run11 = create_run_plan("EXP-011", replicates=1)
    p11 = {item["variant_id"]: item["prompt"] for item in run11["variants"]}
    assert "deep teal satin evening dress" in p11["control"]
    assert "bias-cut deep teal satin evening dress" in p11["variant"]

    run12 = create_run_plan("EXP-012", replicates=1)
    p12 = {item["variant_id"]: item["prompt"] for item in run12["variants"]}
    assert "lags slightly behind the turn" not in p12["control"]
    assert "lags slightly behind the turn" in p12["variant"]


def test_reference_transfer_experiments_are_blocked_until_first_party_fixtures_exist():
    mapping = _load(MAPPING_REL)
    by_id = {item["experiment_id"]: item for item in mapping["mappings"]}

    for exp_id in ("EXP-013", "EXP-014"):
        definition = _load(f"experiments/definitions/{exp_id}.json")
        assert (
            by_id[exp_id]["transfer_status"]
            == "requires_first_party_reference_fixtures"
        )
        assert definition["requires_reference_inputs"]
        assert (
            definition["transfer_benchmark"]["execution_readiness"]
            == "requires_first_party_reference_fixtures"
        )
        for fixture in definition["requires_reference_inputs"]:
            assert fixture["fixture_policy"] == "first_party_or_project_owned"
            assert fixture["hash_required"] is True


def test_exp015_changes_only_the_anachronistic_positive_object():
    run = create_run_plan("EXP-015", replicates=1)
    prompts = {item["variant_id"]: item["prompt"] for item in run["variants"]}

    assert "a compact electric desk lamp" in prompts["control"]
    assert "a ceramic oil lamp" in prompts["variant"]
    assert "Avoid modern electrical objects and anachronistic lighting fixtures." in prompts["control"]
    assert "Avoid modern electrical objects and anachronistic lighting fixtures." in prompts["variant"]
    assert prompts["variant"] == prompts["control"].replace(
        "a compact electric desk lamp",
        "a ceramic oil lamp",
    )
