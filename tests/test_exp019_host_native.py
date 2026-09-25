"""Offline checks for EXP-019 v1.1 host-native import and private lifecycle."""
from __future__ import annotations

import json
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from aipf.exp019_analysis import analyze_exp019
from aipf.exp019_anchor import verify_external
from aipf.exp019_host import ATTESTATIONS, RUN_RECEIPT
from aipf.exp019_protocol import find_slot
from aipf.exp019_receipt import validate_run_receipt
from aipf.experiment_execution import execute_run, export_host_package, import_output, record_failed_output
from aipf.experiment_review import create_review_package, freeze_review, reveal_review
from aipf.experiment_runs import create_run_plan, load_run_plan, sha256_file, write_run_plan


def _run(tmp_path: Path) -> Path:
    return write_run_plan(create_run_plan("EXP-019"), tmp_path / "private" / "experiments" / "generated-images")


def _receipt(run: dict, slot: dict, attempt: int, *, outcome: str, image_hash: str | None) -> dict:
    variant, _ = find_slot(run, slot["blind_id"])
    return {
        "experiment_id": "EXP-019", "experiment_version": "1.1.0", "run_id": run["run_id"],
        "slot_id": slot["blind_id"], "attempt_number": attempt,
        "prompt_sha256": variant["prompt_sha256"], "generation_mode": "host_native",
        "host_product": "ChatGPT Images", "observed_host_label": None,
        "backend_snapshot": "unknown", "provider_generation_id": None,
        "reference_count": 0, "requested_aspect_ratio": "2:3", "requested_dimensions": None,
        "generation_request_count": 1, "host_returned_output_count": 1 if image_hash else 0,
        "output_count": 1 if image_hash else 0,
        "outcome": outcome, "output_sha256": image_hash,
        "fresh_chat_attestation": {name: True for name in ATTESTATIONS},
        "invoked_at_utc": "2026-01-01T00:00:00+00:00", "api_request_metadata": None,
    }


def _raster() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (8, 12), (10, 20, 30)).save(stream, format="PNG")
    return stream.getvalue()


def _write_receipt(tmp_path: Path, data: dict, index: int) -> Path:
    path = tmp_path / f"operator-{index}.json"
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return path


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


def test_host_plan_and_export_are_opaque(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    run = load_run_plan(run_file)
    assert run_file.name == "run-private.json"
    assert run_file.parent.name == run["run_id"]
    assert run["generation_mode"] == "host_native" and run["model"] == "ChatGPT Images"
    assert run["model_snapshot"] == "unknown" and run["reference_inputs"] == []
    assert "".join(s["variant_id"] for s in run["invocation_order"]) == "BACCBABCAABC"
    package = export_host_package(run_file)
    manifest = json.loads(Path(package["manifest"]).read_text(encoding="utf-8"))
    assert len(manifest["tasks"]) == 12
    for task, slot in zip(manifest["tasks"], run["invocation_order"]):
        variant, _ = find_slot(run, slot["blind_id"])
        assert task["opaque_slot_id"] == slot["blind_id"]
        assert task["prompt"] == variant["prompt"] and task["reference_count"] == 0
        assert "variant_id" not in task and "replicate" not in task
    assert not (run_file.parent / "outputs").exists()


def test_host_profile_rejects_api_and_release_placement(tmp_path):
    with pytest.raises(ValueError, match="requires"):
        create_run_plan("EXP-019", generation_mode="api")
    with pytest.raises(ValueError, match="requires"):
        create_run_plan("EXP-019", model="gpt-image-2-2026-04-21")
    with pytest.raises(ValueError, match="release directory"):
        write_run_plan(create_run_plan("EXP-019"), tmp_path / "release" / "experiments" / "generated-images")
    run_file = _run(tmp_path)
    with pytest.raises(ValueError, match="host-native"):
        execute_run(run_file)


def test_host_attestation_and_multi_candidate_fail_closed(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    run = load_run_plan(run_file)
    slot = run["invocation_order"][0]
    image = tmp_path / "synthetic.png"
    image.write_bytes(_raster())
    bad = _receipt(run, slot, 1, outcome="success", image_hash=sha256_file(image))
    bad["fresh_chat_attestation"]["fresh_chat"] = False
    with pytest.raises(ValueError, match="attestation"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      receipt=_write_receipt(tmp_path, bad, 1))
    bad = _receipt(run, slot, 1, outcome="success", image_hash=sha256_file(image))
    bad["host_returned_output_count"] = 2
    with pytest.raises(ValueError, match="multiple candidates"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      receipt=_write_receipt(tmp_path, bad, 2))
    assert load_run_plan(run_file)["status"] == "planned"


def test_host_three_technical_failures_stop_incomplete(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    run = load_run_plan(run_file)
    slot = run["invocation_order"][0]
    for attempt in (1, 2, 3):
        operator = _write_receipt(tmp_path, _receipt(run, slot, attempt,
                                  outcome="technical_failure", image_hash=None), attempt)
        state = record_failed_output(run_file, blind_id=slot["blind_id"],
                                     error="technical_failure", receipt=operator)
        assert state["status"] == ("incomplete" if attempt == 3 else "partial")
    assert validate_run_receipt(run_file)["derived_run_status"] == "incomplete"
    with pytest.raises(ValueError, match="terminal attempt"):
        record_failed_output(run_file, blind_id=slot["blind_id"], error="technical_failure",
                             receipt=operator)


def test_host_retry_and_no_reroll(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    run = load_run_plan(run_file)
    first, second = run["invocation_order"][:2]
    image = tmp_path / "synthetic.png"
    image.write_bytes(_raster())
    with pytest.raises(ValueError, match="frozen invocation order"):
        import_output(run_file, blind_id=second["blind_id"], image=image,
                      receipt=_write_receipt(tmp_path, _receipt(run, second, 1, outcome="success", image_hash=sha256_file(image)), 90))
    failure_receipt = _write_receipt(tmp_path, _receipt(run, first, 1, outcome="technical_failure", image_hash=None), 1)
    assert record_failed_output(run_file, blind_id=first["blind_id"], error="technical_failure", receipt=failure_receipt)["status"] == "partial"
    success = _write_receipt(tmp_path, _receipt(run, first, 2, outcome="success", image_hash=sha256_file(image)), 2)
    assert import_output(run_file, blind_id=first["blind_id"], image=image, receipt=success)["status"] == "partial"
    with pytest.raises(ValueError, match="frozen invocation order"):
        import_output(run_file, blind_id=first["blind_id"], image=image, receipt=success, overwrite=True)
    current = load_run_plan(run_file)
    _variant, output = find_slot(current, first["blind_id"])
    assert [e["event"] for e in output["attempt_events"]] == ["started", "technical_failure", "started", "success"]
    metadata = json.loads((run_file.parent / "outputs" / output["metadata"]).read_text(encoding="utf-8"))
    assert metadata["actual_raster"]["width"] == 8 and metadata["actual_raster"]["height"] == 12
    assert output["image_sha256"] == sha256_file(image)


def test_host_full_synthetic_review_and_analysis(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    image = tmp_path / "synthetic.png"
    image.write_bytes(_raster())
    image_hash = sha256_file(image)
    initial = load_run_plan(run_file)
    for index, slot in enumerate(initial["invocation_order"], 1):
        operator = _write_receipt(tmp_path, _receipt(initial, slot, 1, outcome="success", image_hash=image_hash), index)
        import_output(run_file, blind_id=slot["blind_id"], image=image, receipt=operator)
    assert load_run_plan(run_file)["status"] == "completed"
    assert (run_file.parent / RUN_RECEIPT).is_file()
    validate_run_receipt(run_file)
    packages = {r: create_review_package(run_file, reviewer_id=r) for r in ("R1", "R2")}
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
    assert result["experiment_version"] == "1.1.0"
    assert result["contrasts"]["B-C"]["delta"] == 1
    assert result["contrasts"]["B-A"]["delta"] == 2
    assert result["evidence_classification"] == "supports"  # synthetic arithmetic, not empirical evidence


def test_host_import_is_anchored_to_separate_temporary_git_remote(tmp_path, monkeypatch):
    remote = tmp_path / "synthetic-remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(remote))
    run_file = _run(tmp_path)
    export_host_package(run_file)
    run = load_run_plan(run_file)
    assert verify_external(run_file, run)["checkpoints"][0]["record"]["event_type"] == "run_root"
    slot = run["invocation_order"][0]
    receipt = _write_receipt(tmp_path, _receipt(run, slot, 1, outcome="technical_failure", image_hash=None), 1)
    record_failed_output(run_file, blind_id=slot["blind_id"], error="technical_failure", receipt=receipt)
    state = verify_external(run_file, load_run_plan(run_file))
    assert [c["record"]["event_type"] for c in state["checkpoints"]] == ["run_root", "attempt"]
    image = tmp_path / "synthetic.png"
    image.write_bytes(_raster())
    success = _write_receipt(tmp_path, _receipt(run, slot, 2, outcome="success", image_hash=sha256_file(image)), 2)
    import_output(run_file, blind_id=slot["blind_id"], image=image, receipt=success)
    state = verify_external(run_file, load_run_plan(run_file))
    assert [c["record"]["event_type"] for c in state["checkpoints"]] == ["run_root", "attempt", "attempt"]
    operator_path = run_file.parent / "provenance-freeze" / "execution-receipts" / f"{slot['blind_id']}.attempt-1.operator.json"
    operator_path.write_text(operator_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="operator attestation changed"):
        verify_external(run_file, load_run_plan(run_file))
