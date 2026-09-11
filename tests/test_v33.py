import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf.experiment_execution import (
    execute_run,
    experiment_status,
    export_host_package,
    import_output,
    record_failed_output,
)
from aipf.experiment_review import (
    create_review_package,
    freeze_review,
    reveal_review,
)
from aipf.experiment_runs import (
    create_run_plan,
    load_run_plan,
    sha256_file,
    validate_blind_ids,
    write_run_plan,
)
from aipf.io import repo_root


def _all_outputs(run):
    return [
        output
        for variant in run["variants"]
        for output in variant["outputs"]
    ]


def test_v33_run_plan_has_replicates():
    run = create_run_plan("EXP-001", replicates=4)

    assert run["experiment_id"] == "EXP-001"
    assert len(run["variants"]) == 2

    for variant in run["variants"]:
        assert len(variant["outputs"]) == 4


def test_v33_control_and_variant_prompts_differ():
    run = create_run_plan("EXP-001")

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    assert prompts["control"] != prompts["variant"]


def test_v33_prompt_hashes_differ():
    run = create_run_plan("EXP-001")

    hashes = [
        variant["prompt_sha256"]
        for variant in run["variants"]
    ]

    assert len(set(hashes)) == 2


def test_v33_host_native_is_default_without_fake_snapshot():
    run = create_run_plan("EXP-001")

    assert run["generation_mode"] == "host_native"
    assert run["model"] == "gpt-image-2"
    assert run["model_snapshot"] == "unknown"


def test_v33_api_mode_uses_pinned_snapshot():
    run = create_run_plan(
        "EXP-001",
        generation_mode="api",
    )

    assert run["generation_mode"] == "api"
    assert run["model_snapshot"] == "gpt-image-2-2026-04-21"


def test_v33_blind_ids_are_unique_and_opaque():
    run = create_run_plan("EXP-001", replicates=4)
    ids = [output["blind_id"] for output in _all_outputs(run)]

    assert len(ids) == 8
    assert len(set(ids)) == 8

    for blind_id in ids:
        lowered = blind_id.lower()
        assert "control" not in lowered
        assert "variant" not in lowered
        assert len(blind_id) == 6


def test_v33_run_schema_accepts_host_native_plan():
    run = create_run_plan("EXP-001", replicates=2)
    schema = json.loads(
        (
            repo_root()
            / "data"
            / "schemas"
            / "experiment_run.schema.json"
        ).read_text(encoding="utf-8")
    )

    errors = list(Draft202012Validator(schema).iter_errors(run))
    assert errors == []


def test_v33_write_and_load_run_plan(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    path = write_run_plan(run, tmp_path)
    loaded = load_run_plan(path)

    assert path.exists()
    assert loaded["run_id"] == run["run_id"]
    assert (path.parent / "control" / "prompt.txt").exists()
    assert (path.parent / "variant" / "prompt.txt").exists()


def test_v33_host_export_is_blind_safe(tmp_path):
    run = create_run_plan("EXP-001", replicates=2)
    run_path = write_run_plan(run, tmp_path / "runs")

    result = export_host_package(run_path)
    manifest_path = Path(result["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["task_count"] == 4
    assert len(manifest["tasks"]) == 4
    assert (manifest_path.parent / "README.md").exists()

    text = manifest_path.read_text(encoding="utf-8").lower()
    assert '"variant_id"' not in text
    assert '"factor"' not in text

    for task in manifest["tasks"]:
        assert task["blind_id"]
        assert task["prompt"]
        assert (
            manifest_path.parent
            / "prompts"
            / f"{task['blind_id']}.txt"
        ).exists()


def test_v33_import_output_updates_private_run(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_path = write_run_plan(run, tmp_path / "runs")
    first_blind = _all_outputs(run)[0]["blind_id"]

    image = tmp_path / "sample.png"
    image.write_bytes(b"first-party-test-image")

    result = import_output(
        run_path,
        blind_id=first_blind,
        image=image,
        provider="chatgpt",
    )
    loaded = load_run_plan(run_path)
    _variant, imported = next(
        (variant, output)
        for variant in loaded["variants"]
        for output in variant["outputs"]
        if output["blind_id"] == first_blind
    )

    assert result["blind_id"] == first_blind
    assert imported["status"] == "generated"
    assert imported["image_sha256"]
    assert imported["metadata"] == f"{first_blind}.json"
    assert loaded["status"] == "partial"
    assert Path(result["image"]).parent.name == "outputs"
    assert "control" not in result["image"].lower()
    assert "variant" not in result["image"].lower()


def test_v33_import_all_outputs_completes_run(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_path = write_run_plan(run, tmp_path / "runs")

    for index, output in enumerate(_all_outputs(run), start=1):
        image = tmp_path / f"sample-{index}.png"
        image.write_bytes(f"image-{index}".encode("utf-8"))
        import_output(
            run_path,
            blind_id=output["blind_id"],
            image=image,
        )

    loaded = load_run_plan(run_path)
    assert loaded["status"] == "completed"
    assert all(
        output["status"] == "generated"
        for output in _all_outputs(loaded)
    )


def test_v33_record_failed_output_keeps_failure(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_path = write_run_plan(run, tmp_path / "runs")
    blind_id = _all_outputs(run)[0]["blind_id"]

    result = record_failed_output(
        run_path,
        blind_id=blind_id,
        error="host generation failed",
    )
    loaded = load_run_plan(run_path)
    failed = next(
        output
        for output in _all_outputs(loaded)
        if output["blind_id"] == blind_id
    )

    assert result["status"] == "partial"
    assert failed["status"] == "failed"
    assert failed["error"] == "host generation failed"


def test_v33_execution_dry_run_requires_no_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    run = create_run_plan("EXP-001", replicates=1)
    path = write_run_plan(run, tmp_path)

    result = execute_run(path, dry_run=True)

    assert result["planned"] == 2
    assert result["generated"] == 0
    assert result["failed"] == 0
    assert result["status"] == "planned"


def test_v33_host_native_execute_directs_to_export_import(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    path = write_run_plan(run, tmp_path)

    with pytest.raises(RuntimeError, match="experiment-export"):
        execute_run(path)


def test_v33_duplicate_blind_ids_are_rejected():
    run = create_run_plan("EXP-001", replicates=1)
    outputs = _all_outputs(run)
    outputs[1]["blind_id"] = outputs[0]["blind_id"]

    with pytest.raises(ValueError, match="unique"):
        validate_blind_ids(run)



def test_exp001_pose_treatment_is_grammatical():
    run = create_run_plan("EXP-001", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    treatment = prompts["variant"]

    assert (
        "stands in a dynamic but physically grounded pose, "
        "with most body weight on the rear leg"
        in treatment
    )
    assert "stands in a most body weight" not in treatment


def test_exp001_factors_distinguish_control_and_treatment():
    run = create_run_plan("EXP-001", replicates=1)

    factors = {
        variant["variant_id"]: variant["factor"]
        for variant in run["variants"]
    }

    assert factors["control"] == "generic_pose"
    assert factors["variant"] == "explicit_pose_mechanics"


def test_exp001_only_replaces_pose_language():
    run = create_run_plan("EXP-001", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    expected = prompts["control"].replace(
        "dynamic elegant pose",
        (
            "dynamic but physically grounded pose, "
            "with most body weight on the rear leg, "
            "front leg relaxed, pelvis subtly shifted, "
            "shoulders counterbalanced, "
            "and one hand supported naturally"
        ),
    )

    assert prompts["variant"] == expected


def test_host_export_preserves_prompt_exactly(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_file = write_run_plan(run, tmp_path / "runs")

    result = export_host_package(run_file)
    manifest = json.loads(
        Path(result["manifest"]).read_text(encoding="utf-8")
    )

    expected = {
        output["blind_id"]: variant["prompt"]
        for variant in run["variants"]
        for output in variant["outputs"]
    }

    for task in manifest["tasks"]:
        assert task["prompt"] == expected[task["blind_id"]]


def test_host_export_hash_matches_prompt(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_file = write_run_plan(run, tmp_path / "runs")

    result = export_host_package(run_file)
    manifest = json.loads(
        Path(result["manifest"]).read_text(encoding="utf-8")
    )

    for task in manifest["tasks"]:
        actual = hashlib.sha256(
            task["prompt"].encode("utf-8")
        ).hexdigest()
        assert actual == task["prompt_sha256"]


def _complete_test_run(tmp_path, replicates=1):
    run = create_run_plan("EXP-001", replicates=replicates)
    run_file = write_run_plan(run, tmp_path / "runs")

    for index, output in enumerate(_all_outputs(run), start=1):
        image = tmp_path / f"review-source-{index}.png"
        image.write_bytes(f"review-image-{index}".encode("utf-8"))
        import_output(
            run_file,
            blind_id=output["blind_id"],
            image=image,
        )

    return run_file


def test_v33_review_package_requires_completed_run(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_file = write_run_plan(run, tmp_path / "runs")

    with pytest.raises(ValueError, match="completed run"):
        create_review_package(run_file)


def test_v33_review_package_is_blind_safe(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=2)
    run = load_run_plan(run_file)
    generation_ids = {
        output["blind_id"]
        for output in _all_outputs(run)
    }

    result = create_review_package(run_file)
    manifest_path = Path(result["manifest"])
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)

    assert result["review_count"] == 4
    assert manifest["review_count"] == 4
    assert result["mapping_commitment_sha256"]

    forbidden_keys = {
        "blind_id",
        "variant_id",
        "factor",
        "prompt",
        "prompt_sha256",
        "replicate",
        "image_sha256",
    }

    def walk_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)

    assert forbidden_keys.isdisjoint(set(walk_keys(manifest)))

    review_ids = {item["review_id"] for item in manifest["items"]}
    assert len(review_ids) == 4
    assert review_ids.isdisjoint(generation_ids)

    for generation_id in generation_ids:
        assert generation_id not in manifest_text

    for item in manifest["items"]:
        image = manifest_path.parent / item["image"]
        assert image.exists()
        assert image.stem == item["review_id"]
        assert set(item) == {"review_id", "image"}

    review_path = Path(result["review"])
    review_text = review_path.read_text(encoding="utf-8")
    assert "image_sha256" not in review_text

    mapping_path = (
        Path(run_file).parent / ".review-private" / "mapping.json"
    )
    assert mapping_path.exists()
    assert mapping_path.parent != manifest_path.parent

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping_by_review_id = {
        entry["review_id"]: entry for entry in mapping["entries"]
    }
    assert set(mapping_by_review_id) == review_ids

    for item in manifest["items"]:
        image = manifest_path.parent / item["image"]
        private_entry = mapping_by_review_id[item["review_id"]]
        assert private_entry["image_sha256"] == sha256_file(image)


def test_v33_review_schema_accepts_open_template(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=1)
    result = create_review_package(run_file)

    review = json.loads(
        Path(result["review"]).read_text(encoding="utf-8")
    )
    schema = json.loads(
        (
            repo_root()
            / "data"
            / "schemas"
            / "experiment_review.schema.json"
        ).read_text(encoding="utf-8")
    )

    errors = list(Draft202012Validator(schema).iter_errors(review))
    assert errors == []


def test_v33_freeze_review_requires_all_scores(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=1)
    result = create_review_package(run_file)

    with pytest.raises(ValueError, match="must be a number"):
        freeze_review(result["review"])


def test_v33_freeze_review_writes_hashed_snapshot(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=1)
    result = create_review_package(run_file)
    review_path = Path(result["review"])
    review = json.loads(review_path.read_text(encoding="utf-8"))

    for item in review["items"]:
        for dimension in review["evaluation_dimensions"]:
            item["scores"][dimension] = 4
        item["notes"] = "blind review note"

    review_path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    frozen_result = freeze_review(review_path)
    frozen_path = Path(frozen_result["review"])
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))

    assert frozen["status"] == "frozen"
    assert frozen["frozen_at_utc"]
    assert len(frozen["review_sha256"]) == 64
    assert frozen_result["review_sha256"] == frozen["review_sha256"]


def _fill_review_scores(review_path: Path, score=4):
    review = json.loads(review_path.read_text(encoding="utf-8"))
    for item in review["items"]:
        for dimension in review["evaluation_dimensions"]:
            item["scores"][dimension] = score
    review_path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_v33_status_is_treatment_blind(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=1)
    status = experiment_status(run_file)
    text = json.dumps(status).lower()

    assert status["status"] == "completed"
    assert status["total"] == 2
    assert status["generated"] == 2
    assert "variant_id" not in text
    assert "factor" not in text
    assert "generic_pose" not in text
    assert "explicit_pose_mechanics" not in text


def test_v33_review_ids_are_independent_from_generation_ids(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=2)
    run = load_run_plan(run_file)
    generation_ids = {
        output["blind_id"] for output in _all_outputs(run)
    }

    result = create_review_package(run_file)
    manifest = json.loads(
        Path(result["manifest"]).read_text(encoding="utf-8")
    )
    review_ids = {item["review_id"] for item in manifest["items"]}

    assert len(review_ids) == len(generation_ids)
    assert review_ids.isdisjoint(generation_ids)


def test_v33_review_reveal_requires_frozen_review(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=1)
    create_review_package(run_file)

    with pytest.raises(ValueError, match="frozen"):
        reveal_review(run_file)


def test_v33_review_reveal_succeeds_after_freeze(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=2)
    result = create_review_package(run_file)
    review_path = Path(result["review"])
    _fill_review_scores(review_path)
    freeze_review(review_path)

    revealed = reveal_review(run_file)
    reveal_path = Path(revealed["reveal"])
    payload = json.loads(reveal_path.read_text(encoding="utf-8"))

    assert revealed["status"] == "revealed"
    assert revealed["item_count"] == 4
    assert len(payload["items"]) == 4
    assert all("review_id" in item for item in payload["items"])
    assert all("blind_id" in item for item in payload["items"])
    assert all("variant_id" in item for item in payload["items"])
    assert all("factor" in item for item in payload["items"])


def test_v33_tampered_frozen_review_cannot_reveal(tmp_path):
    run_file = _complete_test_run(tmp_path, replicates=1)
    result = create_review_package(run_file)
    review_path = Path(result["review"])
    _fill_review_scores(review_path)
    frozen_result = freeze_review(review_path)
    frozen_path = Path(frozen_result["review"])

    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    frozen["items"][0]["scores"][
        frozen["evaluation_dimensions"][0]
    ] = 1
    frozen_path.write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash verification"):
        reveal_review(run_file)

def test_exp002_factors_distinguish_control_and_treatment():
    run = create_run_plan("EXP-002", replicates=1)

    factors = {
        variant["variant_id"]: variant["factor"]
        for variant in run["variants"]
    }

    assert factors["control"] == "material_name_only"
    assert factors["variant"] == "material_physics"


def test_exp002_material_treatment_is_grammatical():
    run = create_run_plan("EXP-002", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    treatment = prompts["variant"]

    assert (
        "geometry-following specular reflections under the existing "
        "window light, while holding a ceramic vase"
        in treatment
    )

    assert "cloth geometry and holding" not in treatment


def test_exp002_only_replaces_material_language():
    run = create_run_plan("EXP-002", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    expected = prompts["control"].replace(
        "wearing a satin outfit and holding a ceramic vase",
        (
            "wearing a satin outfit whose fabric shows smooth drape, "
            "tension folds, and geometry-following specular reflections "
            "under the existing window light, while holding a ceramic vase"
        ),
    )

    assert prompts["variant"] == expected

def test_exp004_factors_distinguish_control_and_treatment():
    run = create_run_plan("EXP-004", replicates=1)

    factors = {
        variant["variant_id"]: variant["factor"]
        for variant in run["variants"]
    }

    assert factors["control"] == "generic_holding"
    assert factors["variant"] == "explicit_hand_object_mechanics"


def test_exp004_controls_two_hand_usage():
    run = create_run_plan("EXP-004", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    assert "holding a ceramic vase with both hands" in prompts["control"]
    assert "left palm beneath its base" in prompts["variant"]
    assert "right hand steadies the neck" in prompts["variant"]


def test_exp004_treatment_avoids_artifact_visibility_confound():
    run = create_run_plan("EXP-004", replicates=1)

    treatment = next(
        variant["prompt"]
        for variant in run["variants"]
        if variant["variant_id"] == "variant"
    )

    assert "without covering the decoration" not in treatment
    assert "fingers conforming to the vase surface" in treatment
    assert "wrists aligned with the load" in treatment


def test_exp004_only_replaces_interaction_mechanics():
    run = create_run_plan("EXP-004", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    expected = prompts["control"].replace(
        "holding a ceramic vase with both hands",
        (
            "supporting a ceramic vase with the left palm beneath its base "
            "while the right hand steadies the neck, with the fingers "
            "conforming to the vase surface and the wrists aligned with the load"
        ),
    )

    assert prompts["variant"] == expected

def test_exp003_factors_distinguish_static_and_micro_story():
    run = create_run_plan("EXP-003", replicates=1)

    factors = {
        variant["variant_id"]: variant["factor"]
        for variant in run["variants"]
    }

    assert factors["control"] == "static_description"
    assert factors["variant"] == "director_micro_story"


def test_exp003_preserves_scene_facts_across_conditions():
    run = create_run_plan("EXP-003", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    for prompt in prompts.values():
        assert "midway across the room" in prompt
        assert "window" in prompt
        assert "quiet sound" in prompt
        assert "satin outfit" in prompt
        assert "ceramic vase" in prompt


def test_exp003_micro_story_uses_temporal_event_framing():
    run = create_run_plan("EXP-003", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    assert "has just paused" not in prompts["control"]
    assert "has just paused" in prompts["variant"]
    assert "turning toward a quiet sound outside the window" in prompts["variant"]


def test_exp003_only_replaces_static_event_description():
    run = create_run_plan("EXP-003", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    expected = prompts["control"].replace(
        (
            "The subject stands midway across the room, turned toward the window, "
            "wearing a satin outfit and holding a ceramic vase. "
            "A quiet sound comes from outside the window."
        ),
        (
            "The subject has just paused midway across the room, turning toward "
            "a quiet sound outside the window, while wearing a satin outfit and "
            "holding a ceramic vase."
        ),
    )

    assert prompts["variant"] == expected

def test_exp005_factors_distinguish_generic_and_explicit_depth():
    run = create_run_plan("EXP-005", replicates=1)

    factors = {
        variant["variant_id"]: variant["factor"]
        for variant in run["variants"]
    }

    assert factors["control"] == "generic_cinematic_depth"
    assert factors["variant"] == "explicit_layered_spatial_roles"


def test_exp005_preserves_scene_elements_across_conditions():
    run = create_run_plan("EXP-005", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    for prompt in prompts.values():
        assert "doorway" in prompt
        assert "window" in prompt
        assert "distant furniture" in prompt
        assert "satin outfit" in prompt
        assert "ceramic vase" in prompt
        assert "Soft directional window light" in prompt


def test_exp005_variant_only_assigns_explicit_spatial_roles():
    run = create_run_plan("EXP-005", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    expected = prompts["control"].replace(
        "Use cinematic depth to arrange the scene",
        (
            "Place the doorway in the foreground, the subject in the midground, "
            "and the window and distant furniture in the background"
        ),
    )

    assert prompts["variant"] == expected


def test_exp005_prompts_do_not_introduce_blur_or_spacing_conflicts():
    run = create_run_plan("EXP-005", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    for prompt in prompts.values():
        assert "blurred foreground" not in prompt
        assert "text, watermark" in prompt
        assert "text,watermark" not in prompt

def test_exp006_factors_distinguish_camera_brand_presence():
    run = create_run_plan("EXP-006", replicates=1)

    factors = {
        variant["variant_id"]: variant["factor"]
        for variant in run["variants"]
    }

    assert factors["control"] == "camera_brand_present"
    assert factors["variant"] == "camera_brand_removed"


def test_exp006_preserves_portrait_perspective_across_conditions():
    run = create_run_plan("EXP-006", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    for prompt in prompts.values():
        assert "85mm portrait perspective" in prompt
        assert "satin outfit" in prompt
        assert "ceramic vase" in prompt
        assert "Soft directional window light" in prompt
        assert "Foreground, midground, and background create depth" in prompt


def test_exp006_only_removes_camera_brand_wording():
    run = create_run_plan("EXP-006", replicates=1)

    prompts = {
        variant["variant_id"]: variant["prompt"]
        for variant in run["variants"]
    }

    expected = prompts["control"].replace(
        "Use an 85mm portrait perspective. Hasselblad camera.",
        "Use an 85mm portrait perspective.",
    )

    assert prompts["variant"] == expected
    assert "Hasselblad" in prompts["control"]
    assert "Hasselblad" not in prompts["variant"]


def test_exp006_scores_visible_rendering_not_prompt_brand_presence():
    definition_path = (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "definitions"
        / "EXP-006.json"
    )

    definition = json.loads(definition_path.read_text(encoding="utf-8"))

    assert "photographic_rendering_quality" in definition["evaluation_dimensions"]
    assert "camera_brand" not in definition["evaluation_dimensions"]