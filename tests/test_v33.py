import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf.experiment_execution import (
    execute_run,
    export_host_package,
    import_output,
    record_failed_output,
)
from aipf.experiment_runs import (
    create_run_plan,
    load_run_plan,
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
