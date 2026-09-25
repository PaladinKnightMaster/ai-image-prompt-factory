"""Offline v1.1.1 host-evidence checks; no empirical image is created here."""
from __future__ import annotations

import json
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from aipf.exp019_analysis import analyze_exp019
from aipf.exp019_anchor import verify_external
from aipf.exp019_host import ATTESTATIONS, SOURCE_ATTESTATIONS, verify_host_attempts
from aipf.exp019_host_metadata import QUERY_ATTESTATION, load_host_session_metadata
from aipf.exp019_protocol import find_slot, frozen_protocol
from aipf.exp019_receipt import validate_run_receipt
from aipf.experiment_execution import export_host_package, import_output
from aipf.experiment_review import create_review_package, freeze_review, reveal_review
from aipf.experiment_runs import create_run_plan, load_run_plan, sha256_file, write_run_plan


def _run(tmp_path: Path) -> Path:
    return write_run_plan(create_run_plan("EXP-019"),
                          tmp_path / "private" / "experiments" / "generated-images")


def _sidecar() -> dict:
    names = ("generation_id", "request_message_id", "invoked_at_utc",
             "generation_completed_at_utc", "backend_model", "backend_model_snapshot",
             "generated_file_path", "reference_image_count", "requested_output_count",
             "returned_output_count", "edit_or_regeneration_used")
    result = {"host_product": "ChatGPT Images", "generation_mode": "host_native"}
    for name in names:
        result[name] = None
        result[name + "_status"] = "not_observable"
    for name, value in (("reference_image_count", 0), ("requested_output_count", 1),
                        ("returned_output_count", 1), ("edit_or_regeneration_used", False)):
        result[name] = value
        result[name + "_status"] = "observed"
    return result


def _image() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (8, 12), (10, 20, 30)).save(stream, format="PNG")
    return stream.getvalue()


def _stage(run_file: Path, slot: dict, sidecar: dict | None = None) -> tuple[Path, Path]:
    directory = run_file.parent / "host-import-staging" / slot["blind_id"]
    image = directory / "synthetic.png"
    image.write_bytes(_image())
    metadata = directory / "host-session.json"
    metadata.write_text(json.dumps(_sidecar() if sidecar is None else sidecar) + "\n", encoding="utf-8")
    return image, metadata


def _receipt(run_file: Path, slot: dict, image: Path, sidecar: dict, destination: Path) -> Path:
    template = (run_file.parent / "packages" / "generation-inputs" /
                "operator-receipt-templates" / f"{slot['blind_id']}.json")
    data = json.loads(template.read_text(encoding="utf-8"))
    data.update(host_returned_output_count=1, output_count=1, outcome="success",
                output_sha256=sha256_file(image), source_kind="fresh_host_generation",
                fresh_chat_attestation={name: True for name in ATTESTATIONS},
                source_origin_attestation={name: True for name in SOURCE_ATTESTATIONS},
                metadata_query_attestation=QUERY_ATTESTATION)
    for host_field, receipt_field in (("invoked_at_utc", "invoked_at_utc"),
                                      ("generation_completed_at_utc", "generation_completed_at_utc"),
                                      ("generation_id", "provider_generation_id"),
                                      ("backend_model_snapshot", "backend_snapshot")):
        data[receipt_field] = sidecar[host_field]
        data[receipt_field + "_status"] = sidecar[host_field + "_status"]
    destination.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return destination


@pytest.fixture
def offline_anchor(monkeypatch):
    import aipf.exp019_anchor as anchor
    monkeypatch.setattr(anchor, "ensure_run_root", lambda path, run: {})
    monkeypatch.setattr(anchor, "verify_external", lambda path, run, **kwargs: {})
    monkeypatch.setattr(anchor, "append_attempt_checkpoint", lambda *args: {})
    monkeypatch.setattr(anchor, "append_review_checkpoint", lambda *args: {})
    monkeypatch.setattr(anchor, "run_receipt_provenance", lambda path, run: {
        "backend": "remote_git", "ref": "refs/heads/exp-provenance/offline-test-only",
        "root_anchor_commit": "0" * 40, "terminal_anchor_commit": "0" * 40,
        "checkpoints": [{"commit": "0" * 40}, {"commit": "0" * 40}],
    })


def test_host_metadata_export_and_missing_sidecar(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    run = load_run_plan(run_file)
    assert run["experiment_version"] == "1.1.1"
    assert "".join(s["variant_id"] for s in run["invocation_order"]) == "BACCBABCAABC"
    package = export_host_package(run_file)
    manifest = json.loads(Path(package["manifest"]).read_text(encoding="utf-8"))
    contract = frozen_protocol("1.1.1")[0]["host_evidence_contract"]
    assert len(manifest["tasks"]) == 12
    for task in manifest["tasks"]:
        query = Path(package["output"]) / task["metadata_query_template"]
        assert sha256_file(query) == task["metadata_query_template_sha256"] == contract["metadata_query_template_sha256"]
        assert "variant_id" not in task and "replicate" not in task
        assert task["requested_outputs"] == 1 and task["reference_count"] == 0
        assert b"Do not generate, edit, regenerate" in query.read_bytes()
    slot = run["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    receipt = _receipt(run_file, slot, image, _sidecar(), tmp_path / "receipt.json")
    with pytest.raises(ValueError, match="requires a same-slot host-session metadata sidecar"):
        import_output(run_file, blind_id=slot["blind_id"], image=image, receipt=receipt)
    assert image.exists() and metadata.exists()
    assert load_run_plan(run_file)["status"] == "planned"


@pytest.mark.parametrize("field", ["invoked_at_utc", "generation_completed_at_utc"])
def test_observed_timestamp_and_null_status_rules(tmp_path, offline_anchor, field):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    base = _sidecar()
    base[field], base[field + "_status"] = "2026-01-01T00:00:00+00:00", "observed"
    metadata.write_text(json.dumps(base), encoding="utf-8")
    load_host_session_metadata(metadata)
    receipt = _receipt(run_file, slot, image, base, tmp_path / "observed.json")
    assert import_output(run_file, blind_id=slot["blind_id"], image=image,
                         host_metadata=metadata, receipt=receipt)["status"] == "partial"


@pytest.mark.parametrize("field", ["invoked_at_utc", "generation_completed_at_utc"])
@pytest.mark.parametrize("value,status", [(None,"observed"), ("2026-01-01T00:00:00Z","not_observable"),
                                          ("2026-01-01T00:00:00Z","inferred"),
                                          ("2026-01-01T00:00:00","observed")])
def test_invalid_timestamp_observations_rejected(tmp_path, field, value, status):
    metadata = _sidecar()
    metadata[field], metadata[field + "_status"] = value, status
    path = tmp_path / "host-session.json"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata sidecar schema invalid|timestamp requires a timezone"):
        load_host_session_metadata(path)


def test_optional_ids_snapshot_and_sidecar_binding(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    sidecar = _sidecar()
    sidecar["generation_id"], sidecar["generation_id_status"] = "gen-observed-123", "observed"
    image, metadata = _stage(run_file, slot, sidecar)
    receipt = _receipt(run_file, slot, image, sidecar, tmp_path / "receipt.json")
    import_output(run_file, blind_id=slot["blind_id"], image=image,
                  host_metadata=metadata, receipt=receipt)
    current = load_run_plan(run_file)
    _, output = find_slot(current, slot["blind_id"])
    assert output["image_sha256"] == sha256_file(run_file.parent / "outputs" / output["image"])
    assert output["host_session_metadata_sha256"] == sha256_file(run_file.parent / output["host_session_metadata"])
    assert output["attempt_events"][1]["provider_generation_id"] == "gen-observed-123"
    assert output["attempt_events"][1]["backend_snapshot"] is None
    assert output["attempt_events"][0]["at_utc_source"] == "repository_recorded_at_utc"
    assert output["attempt_events"][0]["host_invoked_at_utc"] is None
    assert len(output["attempt_events"]) == 2  # The text-only query is not an image attempt.
    verify_host_attempts(run_file.parent, current, output, 1)
    (run_file.parent / output["host_session_metadata"]).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="host-session metadata binding changed"):
        verify_host_attempts(run_file.parent, current, output, 1)


def test_unavailable_generation_id_and_snapshot_accepted(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    sidecar = _sidecar()
    image, metadata = _stage(run_file, slot, sidecar)
    receipt = _receipt(run_file, slot, image, sidecar, tmp_path / "receipt.json")
    import_output(run_file, blind_id=slot["blind_id"], image=image,
                  host_metadata=metadata, receipt=receipt)
    _, output = find_slot(load_run_plan(run_file), slot["blind_id"])
    assert output["attempt_events"][1]["provider_generation_id"] is None
    assert output["attempt_events"][1]["backend_snapshot"] is None


def test_v110_archive_and_incomplete_real_run_preserved(tmp_path, offline_anchor):
    archive = Path(__file__).resolve().parents[1] / "experiments/archive/EXP-019-v1.1.0.json"
    old = write_run_plan(create_run_plan(str(archive)),
                         tmp_path / "private" / "experiments" / "generated-images")
    export_host_package(old)
    assert load_run_plan(old)["experiment_version"] == "1.1.0"
    assert frozen_protocol("1.1.0")[0]["version"] == "1.1.0"
    assert create_run_plan("EXP-019")["experiment_version"] == "1.1.1"
    assert old.parent.name.startswith("EXP-019-1.1.0-")
    assert create_run_plan("EXP-019")["run_id"].startswith("EXP-019-1.1.1-")


def test_v111_real_backend_binds_sidecar_without_real_generation(tmp_path, monkeypatch):
    remote = tmp_path / "synthetic-remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(remote))
    run_file = _run(tmp_path)
    export_host_package(run_file)
    run = load_run_plan(run_file)
    slot = run["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    receipt = _receipt(run_file, slot, image, _sidecar(), tmp_path / "receipt.json")
    import_output(run_file, blind_id=slot["blind_id"], image=image,
                  host_metadata=metadata, receipt=receipt)
    current = load_run_plan(run_file)
    state = verify_external(run_file, current)
    assert [c["record"]["event_type"] for c in state["checkpoints"]] == ["run_root", "attempt"]
    _, output = find_slot(current, slot["blind_id"])
    assert output["host_session_metadata_sha256"] == sha256_file(run_file.parent / output["host_session_metadata"])


def test_v111_synthetic_review_analysis_rules_unchanged(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    initial = load_run_plan(run_file)
    for index, slot in enumerate(initial["invocation_order"], 1):
        sidecar = _sidecar()
        image, metadata = _stage(run_file, slot, sidecar)
        receipt = _receipt(run_file, slot, image, sidecar, tmp_path / f"receipt-{index}.json")
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      host_metadata=metadata, receipt=receipt)
    assert load_run_plan(run_file)["status"] == "completed"
    assert validate_run_receipt(run_file)["derived_run_status"] == "completed"
    packages = {reviewer: create_review_package(run_file, reviewer_id=reviewer)
                for reviewer in ("R1", "R2")}
    for reviewer, package in packages.items():
        path = Path(package["review"])
        review = json.loads(path.read_text(encoding="utf-8"))
        mapping = json.loads((run_file.parent / ".review-private" / f"{reviewer}.mapping.json").read_text(encoding="utf-8"))
        condition = {entry["review_id"]: entry["variant_id"] for entry in mapping["entries"]}
        review["reviewer_pseudonym"] = f"synthetic-{reviewer}"
        review["attestations"] = {"independent_reviewer": True, "individual_image_review": True,
                                  "treatment_blind_until_freeze": True}
        for item in review["items"]:
            item["scores"] = {"art_material_fidelity": {"C": 3, "A": 2, "B": 4}[condition[item["review_id"]]],
                              "semantic_compliance": 4, "aesthetic_quality": 4, "technical_defects": 4}
            item["diagnostics"] = {"target_region_localization": "yes", "controlled_tonal_transition_visible": "yes",
                                   "integrated_with_flat_print_structure": "yes", "generic_global_or_3d_shading": "none",
                                   "airbrushed_or_overlay_like_gradient": "none"}
            item["failure_observations"] = {"target_gradation_materially_absent_or_generic": False}
        path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    freeze_review(packages["R1"]["review"])
    with pytest.raises(ValueError, match="both EXP-019 reviews"):
        reveal_review(run_file)
    freeze_review(packages["R2"]["review"])
    reveal_review(run_file)
    result = analyze_exp019(run_file)
    assert result["experiment_version"] == "1.1.1"
    assert result["contrasts"]["B-C"]["delta"] == 1
    assert result["contrasts"]["B-A"]["delta"] == 2
    assert result["evidence_classification"] == "supports"  # synthetic arithmetic only
