import hashlib
import json
from pathlib import Path

import pytest

from aipf.experiment_execution import export_host_package, import_output
from aipf.experiment_runs import create_run_plan, load_run_plan, write_run_plan


def _outputs(run):
    return [
        output
        for variant in run["variants"]
        for output in variant["outputs"]
    ]


def _provenance():
    return {
        "receipt_required": True,
        "receipt_schema_version": "1.0.0",
        "independent_invocations_required": True,
        "unique_host_generation_id_required": True,
        "image_count_per_invocation": 1,
        "finalize_receipt_before_next_invocation": True,
    }


def _receipt(run, task, image, host_generation_id):
    return {
        "schema_version": "1.0.0",
        "run_id": run["run_id"],
        "blind_id": task["blind_id"],
        "task_commitment_sha256": task["task_commitment_sha256"],
        "prompt_sha256": task["prompt_sha256"],
        "reference_inputs": task["reference_inputs"],
        "generation_mode": run["generation_mode"],
        "provider": "chatgpt",
        "model": run["model"],
        "model_snapshot": run["model_snapshot"],
        "settings": task["settings"],
        "invocation": {
            "mode": "single_sample",
            "host_generation_id": host_generation_id,
            "generated_at_utc": "2026-09-17T18:00:00+00:00",
            "image_count": 1,
        },
        "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
    }


def _write_receipt(path, payload):
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def test_historical_run_does_not_require_receipt(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run_file = write_run_plan(run, tmp_path / "runs")
    exported = export_host_package(run_file)
    manifest = json.loads(
        Path(exported["manifest"]).read_text(encoding="utf-8")
    )
    assert manifest["receipt_required"] is False

    image = tmp_path / "historical.png"
    image.write_bytes(b"historical-image")
    import_output(
        run_file,
        blind_id=_outputs(run)[0]["blind_id"],
        image=image,
    )


def test_provenance_export_has_unique_task_commitments(tmp_path):
    run = create_run_plan("EXP-001", replicates=2)
    run["execution_provenance"] = _provenance()
    run_file = write_run_plan(run, tmp_path / "runs")
    exported = export_host_package(run_file)
    manifest = json.loads(
        Path(exported["manifest"]).read_text(encoding="utf-8")
    )
    assert manifest["receipt_required"] is True
    commitments = [
        task["task_commitment_sha256"] for task in manifest["tasks"]
    ]
    assert len(commitments) == 4
    assert len(set(commitments)) == 4
    for task in manifest["tasks"]:
        assert len(task["task_commitment_sha256"]) == 64
        template = Path(exported["output"]) / task["receipt_template"]
        assert template.is_file()


def test_required_receipt_cannot_be_omitted(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run["execution_provenance"] = _provenance()
    run_file = write_run_plan(run, tmp_path / "runs")
    image = tmp_path / "sample.png"
    image.write_bytes(b"receipt-required")
    with pytest.raises(ValueError, match="requires an execution receipt"):
        import_output(
            run_file,
            blind_id=_outputs(run)[0]["blind_id"],
            image=image,
        )


def test_valid_receipt_is_bound_and_preserved(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run["execution_provenance"] = _provenance()
    run_file = write_run_plan(run, tmp_path / "runs")
    exported = export_host_package(run_file)
    manifest = json.loads(
        Path(exported["manifest"]).read_text(encoding="utf-8")
    )
    task = manifest["tasks"][0]
    image = tmp_path / "sample.png"
    image.write_bytes(b"provenance-complete-image")
    receipt = _receipt(run, task, image, "host-generation-001")
    receipt_path = tmp_path / "receipt.json"
    _write_receipt(receipt_path, receipt)

    result = import_output(
        run_file,
        blind_id=task["blind_id"],
        image=image,
        receipt=receipt_path,
    )
    loaded = load_run_plan(run_file)
    output = next(
        item
        for item in _outputs(loaded)
        if item["blind_id"] == task["blind_id"]
    )
    assert output["task_commitment_sha256"] == task["task_commitment_sha256"]
    assert output["host_generation_id"] == "host-generation-001"
    assert len(output["receipt_sha256"]) == 64
    assert result["host_generation_id"] == "host-generation-001"


def test_tampered_commitment_is_rejected(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run["execution_provenance"] = _provenance()
    run_file = write_run_plan(run, tmp_path / "runs")
    exported = export_host_package(run_file)
    manifest = json.loads(
        Path(exported["manifest"]).read_text(encoding="utf-8")
    )
    task = manifest["tasks"][0]
    image = tmp_path / "sample.png"
    image.write_bytes(b"tampered")
    receipt = _receipt(run, task, image, "host-generation-tampered")
    receipt["task_commitment_sha256"] = "0" * 64
    receipt_path = tmp_path / "receipt.json"
    _write_receipt(receipt_path, receipt)
    with pytest.raises(ValueError, match="task commitment mismatch"):
        import_output(
            run_file,
            blind_id=task["blind_id"],
            image=image,
            receipt=receipt_path,
        )


def test_wrong_image_hash_is_rejected(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run["execution_provenance"] = _provenance()
    run_file = write_run_plan(run, tmp_path / "runs")
    exported = export_host_package(run_file)
    manifest = json.loads(
        Path(exported["manifest"]).read_text(encoding="utf-8")
    )
    task = manifest["tasks"][0]
    image = tmp_path / "sample.png"
    image.write_bytes(b"real-image")
    receipt = _receipt(run, task, image, "host-generation-image-hash")
    receipt["image_sha256"] = "0" * 64
    receipt_path = tmp_path / "receipt.json"
    _write_receipt(receipt_path, receipt)
    with pytest.raises(ValueError, match="image SHA-256 mismatch"):
        import_output(
            run_file,
            blind_id=task["blind_id"],
            image=image,
            receipt=receipt_path,
        )


def test_duplicate_host_generation_id_is_rejected(tmp_path):
    run = create_run_plan("EXP-001", replicates=1)
    run["execution_provenance"] = _provenance()
    run_file = write_run_plan(run, tmp_path / "runs")
    exported = export_host_package(run_file)
    manifest = json.loads(
        Path(exported["manifest"]).read_text(encoding="utf-8")
    )
    first, second = manifest["tasks"]

    first_image = tmp_path / "first.png"
    first_image.write_bytes(b"first")
    first_receipt = _receipt(
        run, first, first_image, "same-host-generation-id"
    )
    first_receipt_path = tmp_path / "first.json"
    _write_receipt(first_receipt_path, first_receipt)
    import_output(
        run_file,
        blind_id=first["blind_id"],
        image=first_image,
        receipt=first_receipt_path,
    )

    second_image = tmp_path / "second.png"
    second_image.write_bytes(b"second")
    second_receipt = _receipt(
        run, second, second_image, "same-host-generation-id"
    )
    second_receipt_path = tmp_path / "second.json"
    _write_receipt(second_receipt_path, second_receipt)
    with pytest.raises(
        ValueError, match="host_generation_id already used"
    ):
        import_output(
            run_file,
            blind_id=second["blind_id"],
            image=second_image,
            receipt=second_receipt_path,
        )


def test_exp017_is_exact_scientific_replication(monkeypatch):
    exp16 = json.loads(
        Path("experiments/definitions/EXP-016.json").read_text(
            encoding="utf-8"
        )
    )
    exp17 = json.loads(
        Path("experiments/definitions/EXP-017.json").read_text(
            encoding="utf-8"
        )
    )
    assert exp17["status"] == "executed"
    assert exp17["version"] == "1.0.0"
    assert exp17["hypothesis"] == exp16["hypothesis"]
    assert exp17["variants"] == exp16["variants"]
    assert exp17["requires_reference_inputs"] == exp16["requires_reference_inputs"]
    assert exp17["primary_dimension"] == "cross_reference_leakage_control"
    assert exp17["transfer_benchmark"]["archetype_id"] == "TB-A08"

    provenance = exp17["execution_provenance"]
    assert provenance["receipt_required"] is True
    assert provenance["independent_invocations_required"] is True
    assert provenance["unique_host_generation_id_required"] is True
    assert provenance["image_count_per_invocation"] == 1
    assert provenance["finalize_receipt_before_next_invocation"] is True

    # Public CI does not contain the private frozen fixture bytes.
    # Keep declaration/readiness validation active and stub only
    # the final private-file existence/hash lookup here.
    monkeypatch.setattr(
        "aipf.experiment_runs.resolve_reference_input_source",
        lambda reference_input: None,
    )

    run = create_run_plan("EXP-017", replicates=1)
    assert run["execution_provenance"] == provenance
    assert len(run["reference_inputs"]) == 3
