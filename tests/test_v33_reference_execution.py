import hashlib
import json
from pathlib import Path

from aipf.experiment_execution import export_host_package
from aipf.experiment_runs import resolve_reference_input_source


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_reference_fixture_resolver_verifies_private_hash(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "fixtures"
    image = root / "identity" / "TEST-ID" / "fixture.png"
    image.parent.mkdir(parents=True)

    payload = b"first-party synthetic fixture bytes"
    image.write_bytes(payload)

    expected = _sha256_bytes(payload)

    monkeypatch.setenv(
        "AIPF_TEST_FIXTURE_PATH",
        str(root),
    )

    reference = {
        "slot": "Reference 1",
        "role": "identity",
        "fixture_id": "TEST-ID",
        "fixture_version": "1.0.0",
        "fixture_root_env": "AIPF_TEST_FIXTURE_PATH",
        "fixture_relpath": "identity/TEST-ID/fixture.png",
        "fixture_sha256": expected,
    }

    assert resolve_reference_input_source(reference) == image.resolve()

    reference["fixture_sha256"] = "0" * 64

    try:
        resolve_reference_input_source(reference)
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("fixture hash mismatch was not rejected")


def test_host_export_carries_same_frozen_reference_to_every_task(
    tmp_path,
    monkeypatch,
):
    fixture_root = tmp_path / "fixtures"
    fixture = (
        fixture_root
        / "identity"
        / "TEST-ID"
        / "fixture.png"
    )
    fixture.parent.mkdir(parents=True)

    payload = b"frozen identity fixture"
    fixture.write_bytes(payload)
    fixture_sha = _sha256_bytes(payload)

    monkeypatch.setenv(
        "AIPF_TEST_FIXTURE_PATH",
        str(fixture_root),
    )

    reference = {
        "slot": "Reference 1",
        "role": "identity",
        "fixture_id": "TEST-ID",
        "fixture_version": "1.0.0",
        "fixture_root_env": "AIPF_TEST_FIXTURE_PATH",
        "fixture_relpath": "identity/TEST-ID/fixture.png",
        "fixture_sha256": fixture_sha,
    }

    def variant(
        variant_id,
        factor,
        prompt,
        blind_id,
    ):
        return {
            "variant_id": variant_id,
            "factor": factor,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest(),
            "outputs": [
                {
                    "replicate": 1,
                    "blind_id": blind_id,
                    "status": "planned",
                    "image": None,
                    "image_sha256": None,
                    "metadata": None,
                    "error": None,
                }
            ],
        }

    run = {
        "run_id": "TEST-REFERENCE-RUN",
        "experiment_id": "EXP-TEST",
        "experiment_version": "1.0.0",
        "created_at_utc": "2026-01-01T00:00:00+00:00",
        "status": "planned",
        "generation_mode": "host_native",
        "model": "gpt-image-2",
        "model_snapshot": "unknown",
        "reference_inputs": [reference],
        "settings": {
            "replicates": 1,
            "size": "1024x1536",
            "quality": "medium",
            "background": None,
        },
        "variants": [
            variant(
                "control",
                "repeated_identity_lock",
                "control prompt",
                "ABC234",
            ),
            variant(
                "variant",
                "single_precise_identity_lock",
                "variant prompt",
                "DEF567",
            ),
        ],
    }

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_path = run_dir / "run.json"

    run_path.write_text(
        json.dumps(run, indent=2) + "\n",
        encoding="utf-8",
    )

    result = export_host_package(run_path)

    assert result["task_count"] == 2
    assert result["reference_count"] == 1

    package = run_dir / "host-package"
    copied = package / "references" / "Reference_1.png"

    assert copied.is_file()
    assert hashlib.sha256(
        copied.read_bytes()
    ).hexdigest() == fixture_sha

    manifest = json.loads(
        (package / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(manifest["reference_inputs"]) == 1

    exported_ref = manifest["reference_inputs"][0]

    assert exported_ref == {
        "slot": "Reference 1",
        "role": "identity",
        "fixture_id": "TEST-ID",
        "fixture_version": "1.0.0",
        "fixture_sha256": fixture_sha,
        "file": "references/Reference_1.png",
    }

    assert len(manifest["tasks"]) == 2

    for task in manifest["tasks"]:
        assert task["reference_inputs"] == [
            exported_ref
        ]
