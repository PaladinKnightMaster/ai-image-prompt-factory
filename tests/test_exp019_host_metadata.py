"""Offline v1.1.1 host-evidence checks; no empirical image is created here."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from aipf.exp019_analysis import analyze_exp019
from aipf.exp019_anchor import _attempt_digest, verify_external
from aipf.exp019_host import ATTESTATIONS, SOURCE_ATTESTATIONS, verify_host_attempts
from aipf.exp019_host_metadata import QUERY_ATTESTATION, SIDECAR_NAME, load_host_session_metadata
from aipf.exp019_protocol import _canonical_sha256, find_slot, frozen_protocol
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
    result = {"opaque_slot_id": "HADCEH", "host_product": "ChatGPT Images",
              "generation_mode": "host_native"}
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
    metadata = directory / SIDECAR_NAME
    payload = (_sidecar() if sidecar is None else sidecar).copy()
    payload["opaque_slot_id"] = slot["blind_id"]
    metadata.write_text(json.dumps(payload) + "\n", encoding="utf-8")
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
        query = Path(package["output"]) / task["metadata_query_file"]
        assert sha256_file(query) == task["metadata_query_sha256"]
        assert task["metadata_query_template_sha256"] == contract["metadata_query_template_sha256"]
        assert f'"opaque_slot_id" to "{task["opaque_slot_id"]}"'.encode() in query.read_bytes()
        assert b"{{OPAQUE_SLOT_ID}}" not in query.read_bytes()
        assert b"variant_id" not in query.read_bytes() and b"replicate" not in query.read_bytes()
        assert task["host_metadata_staging_relative_path"].endswith(f"/{SIDECAR_NAME}")
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
    base["opaque_slot_id"] = slot["blind_id"]
    base[field], base[field + "_status"] = datetime.now(timezone.utc).isoformat(), "observed"
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


@pytest.mark.parametrize("field", ["invoked_at_utc", "generation_completed_at_utc"])
@pytest.mark.parametrize("sentinel", ["0001-01-01T00:00:00Z", "1601-01-01T00:00:00Z",
                                       "1970-01-01T00:00:00Z", "1969-12-31T19:00:00-05:00"])
def test_observed_timestamp_sentinels_rejected(tmp_path, field, sentinel):
    metadata = _sidecar()
    metadata[field], metadata[field + "_status"] = sentinel, "observed"
    path = tmp_path / SIDECAR_NAME
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="disallowed placeholder"):
        load_host_session_metadata(path)


def test_null_not_observable_timestamps_accepted(tmp_path):
    path = tmp_path / SIDECAR_NAME
    path.write_text(json.dumps(_sidecar()), encoding="utf-8")
    assert load_host_session_metadata(path)["invoked_at_utc"] is None
    assert load_host_session_metadata(path)["generation_completed_at_utc"] is None


@pytest.mark.parametrize("field", ["invoked_at_utc", "generation_completed_at_utc"])
@pytest.mark.parametrize("offset", [-timedelta(days=30), timedelta(days=30)])
def test_observed_timestamp_outside_run_lifecycle_rejected(tmp_path, offline_anchor, field, offset):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    sidecar = _sidecar()
    sidecar[field] = (datetime.now(timezone.utc) + offset).isoformat()
    sidecar[field + "_status"] = "observed"
    image, metadata = _stage(run_file, slot, sidecar)
    receipt = _receipt(run_file, slot, image, sidecar, tmp_path / "receipt.json")
    with pytest.raises(ValueError, match="outside the run lifecycle"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      host_metadata=metadata, receipt=receipt)


@pytest.mark.parametrize("bad_slot", [None, "not-a-slot", "AAAAAA"])
def test_missing_malformed_or_wrong_sidecar_slot_rejected(tmp_path, offline_anchor, bad_slot):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    data = json.loads(metadata.read_text(encoding="utf-8"))
    if bad_slot is None:
        del data["opaque_slot_id"]
    else:
        data["opaque_slot_id"] = bad_slot if bad_slot != slot["blind_id"] else "BBBBBB"
    metadata.write_text(json.dumps(data), encoding="utf-8")
    receipt = _receipt(run_file, slot, image, data, tmp_path / "receipt.json")
    with pytest.raises(ValueError, match="schema invalid|another opaque slot"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      host_metadata=metadata, receipt=receipt)


def test_wrong_slot_sidecar_direct_and_copied_rejected(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    first, second = load_run_plan(run_file)["invocation_order"][:2]
    first_image, first_metadata = _stage(run_file, first)
    second_image, second_metadata = _stage(run_file, second)
    first_data = json.loads(first_metadata.read_text(encoding="utf-8"))
    first_receipt = _receipt(run_file, first, first_image, _sidecar(), tmp_path / "first.json")
    with pytest.raises(ValueError, match="staging directory"):
        import_output(run_file, blind_id=first["blind_id"], image=first_image,
                      host_metadata=second_metadata, receipt=first_receipt)
    import_output(run_file, blind_id=first["blind_id"], image=first_image,
                  host_metadata=first_metadata, receipt=first_receipt)
    second_metadata.write_text(json.dumps(first_data), encoding="utf-8")
    second_receipt = _receipt(run_file, second, second_image, _sidecar(), tmp_path / "second.json")
    with pytest.raises(ValueError, match="another opaque slot"):
        import_output(run_file, blind_id=second["blind_id"], image=second_image,
                      host_metadata=second_metadata, receipt=second_receipt)


def test_duplicate_and_alternate_sidecars_rejected(tmp_path, offline_anchor):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    receipt = _receipt(run_file, slot, image, _sidecar(), tmp_path / "receipt.json")
    duplicate = metadata.with_name("extra.json")
    duplicate.write_bytes(metadata.read_bytes())
    with pytest.raises(ValueError, match="ambiguous extra files"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      host_metadata=metadata, receipt=receipt)
    duplicate.unlink()
    alternate = metadata.with_name("alternate.json")
    metadata.rename(alternate)
    with pytest.raises(ValueError, match="canonical sidecar filename"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      host_metadata=alternate, receipt=receipt)


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
    canonical_sidecar = run_file.parent / output["host_session_metadata"]
    changed = json.loads(canonical_sidecar.read_text(encoding="utf-8"))
    changed["opaque_slot_id"] = "AAAAAA" if slot["blind_id"] != "AAAAAA" else "BBBBBB"
    canonical_sidecar.write_text(json.dumps(changed), encoding="utf-8")
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
    binding = output["receipt_history"][0]
    canonical = json.loads((run_file.parent / binding["file"]).read_text(encoding="utf-8"))
    frozen = run_file.parent / canonical["frozen_metadata_query_file"]
    packaged = (run_file.parent / "packages" / "generation-inputs" / "metadata-queries"
                / f"{slot['blind_id']}.txt")
    assert frozen.read_bytes() == packaged.read_bytes()
    assert canonical["packaged_metadata_query_sha256"] == sha256_file(frozen)
    assert canonical["frozen_metadata_query_sha256"] == sha256_file(frozen)
    assert "Do not generate, edit, regenerate" not in json.dumps(state)
    frozen_bytes = frozen.read_bytes()
    packaged.write_bytes(b"A changed, non-authoritative package copy.\n")
    assert verify_external(run_file, current)["checkpoints"][-1]["record"]["event_type"] == "attempt"
    frozen.write_bytes(b"A changed frozen query.\n")
    with pytest.raises(ValueError, match="frozen metadata query binding changed"):
        verify_external(run_file, current)
    frozen.write_bytes(frozen_bytes)
    canonical["packaged_metadata_query_sha256"] = "0" * 64
    (run_file.parent / binding["file"]).write_text(json.dumps(canonical) + "\n", encoding="utf-8")
    binding["sha256"] = sha256_file(run_file.parent / binding["file"])
    with pytest.raises(ValueError, match="frozen metadata query binding changed"):
        verify_external(run_file, current)


@pytest.mark.parametrize("damage", ["edited", "forged_manifest", "missing", "wrong_slot", "alternate"])
def test_packaged_query_must_match_frozen_rendering_before_import(tmp_path, offline_anchor,
                                                                   monkeypatch, damage):
    import aipf.exp019_anchor as anchor
    monkeypatch.setattr(anchor, "append_attempt_checkpoint",
                        lambda *args: pytest.fail("rejected query advanced external provenance"))
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    root = run_file.parent
    package = root / "packages" / "generation-inputs"
    query = package / "metadata-queries" / f"{slot['blind_id']}.txt"
    original = query.read_bytes()
    if damage in {"edited", "forged_manifest"}:
        assert b"Do not generate" in original
        query.write_bytes(original.replace(b"Do not generate", b"Go not generate", 1))
        if damage == "forged_manifest":
            manifest_path = package / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["tasks"][0]["metadata_query_sha256"] = sha256_file(query)
            manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    elif damage == "missing":
        query.unlink()
    elif damage == "wrong_slot":
        other = load_run_plan(run_file)["invocation_order"][1]
        query.write_bytes((query.parent / f"{other['blind_id']}.txt").read_bytes())
    else:
        (query.parent / f"{slot['blind_id']}.copy.txt").write_bytes(original)
    image, metadata = _stage(run_file, slot)
    receipt = _receipt(run_file, slot, image, _sidecar(), tmp_path / "receipt.json")
    with pytest.raises(ValueError, match="metadata query"):
        import_output(run_file, blind_id=slot["blind_id"], image=image,
                      host_metadata=metadata, receipt=receipt)
    assert image.exists() and metadata.exists()
    assert load_run_plan(run_file)["status"] == "planned"
    assert not list((root / "provenance-freeze" / "execution-receipts").glob("*.metadata-query.txt"))


def test_coordinated_local_sidecar_rewrite_fails_remote_checkpoint(tmp_path, monkeypatch):
    remote = tmp_path / "synthetic-remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(remote))
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    receipt = _receipt(run_file, slot, image, _sidecar(), tmp_path / "receipt.json")
    import_output(run_file, blind_id=slot["blind_id"], image=image,
                  host_metadata=metadata, receipt=receipt)
    run = load_run_plan(run_file)
    root = run_file.parent
    _, output = find_slot(run, slot["blind_id"])
    verify_external(run_file, run)

    sidecar_path = root / output["host_session_metadata"]
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar.update(generation_id="locally-rewritten", generation_id_status="observed")
    sidecar_path.write_text(json.dumps(sidecar) + "\n", encoding="utf-8")
    new_hash = sha256_file(sidecar_path)
    output["host_session_metadata_sha256"] = new_hash
    event = output["attempt_events"][1]
    event.update(host_session_metadata_sha256=new_hash,
                 provider_generation_id="locally-rewritten")
    event["event_sha256"] = _canonical_sha256({key: value for key, value in event.items()
                                                if key != "event_sha256"})
    binding = output["receipt_history"][0]
    binding["host_session_metadata_sha256"] = new_hash
    operator_path = root / binding["operator_file"]
    operator = json.loads(operator_path.read_text(encoding="utf-8"))
    operator.update(provider_generation_id="locally-rewritten",
                    provider_generation_id_status="observed")
    operator_path.write_text(json.dumps(operator) + "\n", encoding="utf-8")
    binding["operator_sha256"] = sha256_file(operator_path)
    metadata_path = root / "outputs" / output["metadata"]
    output_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    output_metadata.update(host_session_metadata_sha256=new_hash,
                           provider_generation_id="locally-rewritten")
    metadata_path.write_text(json.dumps(output_metadata) + "\n", encoding="utf-8")
    output["metadata_sha256"] = sha256_file(metadata_path)
    canonical_path = root / binding["file"]
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    canonical.update(host_session_metadata_sha256=new_hash,
                     operator_receipt_sha256=binding["operator_sha256"],
                     output_metadata_sha256=output["metadata_sha256"],
                     attempt_events=output["attempt_events"])
    canonical_path.write_text(json.dumps(canonical) + "\n", encoding="utf-8")
    binding["sha256"] = sha256_file(canonical_path)
    run_file.write_text(json.dumps(run) + "\n", encoding="utf-8")
    state_path = root / ".provenance-private" / "anchor-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["checkpoints"][1]["record"]["evidence_sha256"] = _attempt_digest(root, run, slot["blind_id"], 1)
    state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="remote checkpoint differs"):
        verify_external(run_file, run)


def test_coordinated_query_sidecar_receipt_rewrite_is_rejected(tmp_path, monkeypatch):
    remote = tmp_path / "synthetic-remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(remote))
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    image, metadata = _stage(run_file, slot)
    receipt = _receipt(run_file, slot, image, _sidecar(), tmp_path / "receipt.json")
    import_output(run_file, blind_id=slot["blind_id"], image=image,
                  host_metadata=metadata, receipt=receipt)
    run = load_run_plan(run_file)
    root = run_file.parent
    _, output = find_slot(run, slot["blind_id"])
    binding = output["receipt_history"][0]
    canonical_path = root / binding["file"]
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    frozen = root / canonical["frozen_metadata_query_file"]
    frozen.write_bytes(b"forged query bytes\n")
    forged_hash = sha256_file(frozen)
    sidecar_path = root / binding["host_session_metadata_file"]
    sidecar_path.write_bytes(sidecar_path.read_bytes() + b"\n")
    sidecar_hash = sha256_file(sidecar_path)
    binding["host_session_metadata_sha256"] = sidecar_hash
    output["host_session_metadata_sha256"] = sidecar_hash
    event = output["attempt_events"][1]
    event["host_session_metadata_sha256"] = sidecar_hash
    event["event_sha256"] = _canonical_sha256({k: v for k, v in event.items() if k != "event_sha256"})
    metadata_path = root / "outputs" / output["metadata"]
    output_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    output_metadata["host_session_metadata_sha256"] = sidecar_hash
    metadata_path.write_text(json.dumps(output_metadata) + "\n", encoding="utf-8")
    output["metadata_sha256"] = sha256_file(metadata_path)
    canonical.update(packaged_metadata_query_sha256=forged_hash,
                     frozen_metadata_query_sha256=forged_hash,
                     host_session_metadata_sha256=sidecar_hash,
                     output_metadata_sha256=output["metadata_sha256"],
                     attempt_events=output["attempt_events"])
    canonical_path.write_text(json.dumps(canonical) + "\n", encoding="utf-8")
    binding["sha256"] = sha256_file(canonical_path)
    run_file.write_text(json.dumps(run) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frozen metadata query binding changed"):
        verify_external(run_file, run)


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
