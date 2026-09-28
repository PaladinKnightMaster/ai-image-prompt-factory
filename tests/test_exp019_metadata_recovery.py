"""Synthetic post-start recovery evidence only; never access the real private run."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aipf.exp019_anchor import verify_external
from aipf.exp019_host import verify_host_attempts
from aipf.exp019_metadata_recovery import (
    AMENDMENT_ID, RECOVERY_DIR, frozen_amendment,
    prepare_metadata_recovery, stage_metadata_recovery,
)
from aipf.exp019_protocol import find_slot
from aipf.experiment_execution import export_host_package, import_output, record_failed_output
from aipf.experiment_runs import load_run_plan, sha256_file
from test_exp019_host_metadata import _run, _sidecar, _stage, _receipt


@pytest.fixture
def offline(monkeypatch):
    import aipf.exp019_anchor as anchor
    calls = []
    monkeypatch.setattr(anchor, "ensure_run_root", lambda *args: {})
    monkeypatch.setattr(anchor, "verify_external", lambda *args, **kwargs: {"checkpoints": []})
    monkeypatch.setattr(anchor, "append_attempt_checkpoint", lambda *args: calls.append(args))
    return calls


def _incident(tmp_path):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    bad = _sidecar()
    bad.update(generated_file_path="", generated_file_path_status="observed")
    image, sidecar = _stage(run_file, slot, bad)
    return run_file, slot, image, sidecar


def _prepare(run_file, slot):
    return prepare_metadata_recovery(run_file, blind_id=slot["blind_id"],
                                     original_conversation_available=True, no_image_change=True)


def _response(run_file, slot, *, bad=False, attestation_damage=None):
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    data = _sidecar()
    data["opaque_slot_id"] = slot["blind_id"]
    if bad:
        data.update(generated_file_path="", generated_file_path_status="observed")
    candidate = area / "incoming" / "host-session.json"
    candidate.write_text(json.dumps(data) + "\n", encoding="utf-8")
    attestation_path = area / "incoming" / "attestations.json"
    attestations = json.loads(attestation_path.read_text())
    for key in set(attestations) - {"opaque_slot_id", "replayed_query_sha256"}:
        attestations[key] = True
    if attestation_damage:
        attestations.update(attestation_damage)
    attestation_path.write_text(json.dumps(attestations) + "\n", encoding="utf-8")
    return data, candidate.read_bytes()


def test_frozen_addendum_preserves_scientific_definition():
    from aipf.exp019_protocol import frozen_protocol, DEFINITION_SHA256
    assert frozen_amendment()["id"] == AMENDMENT_ID
    definition, _ = frozen_protocol("1.1.1")
    assert definition["version"] == "1.1.1"
    assert definition["preregistration"]["retry_policy"]["decodable_output"] == "no reroll"
    assert DEFINITION_SHA256 == "13df0c72ecae7b4c9213cd34a526ee15701826b5eb3c4098a9ca3c77a8951551"


def test_prepare_preserves_rejection_and_reserves_once(tmp_path, offline):
    run_file, slot, image, sidecar = _incident(tmp_path)
    image_bytes, rejected_bytes, run_bytes = image.read_bytes(), sidecar.read_bytes(), run_file.read_bytes()
    result = _prepare(run_file, slot)
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    prepared = json.loads((area / "prepare.json").read_text())
    assert (area / "rejected.host-session.json").read_bytes() == rejected_bytes
    assert prepared["rejected_sha256"] == sha256_file(sidecar)
    assert prepared["image_sha256"] == sha256_file(image)
    assert prepared["rejection_reason"] == "EXP-019 host-session metadata sidecar schema invalid"
    assert any(item["field"] == "generated_file_path" and "non-empty" in item["reason"]
               for item in prepared["validator_failures"])
    assert prepared["generation_attempts_consumed"] == 0
    assert prepared["amendment"] == frozen_amendment()
    assert result["replay_budget"] == 1 and not result["checkpoint_created"]
    assert image.read_bytes() == image_bytes and sidecar.read_bytes() == rejected_bytes
    assert run_file.read_bytes() == run_bytes and not offline
    with pytest.raises(ValueError, match="already reserved"):
        _prepare(run_file, slot)


@pytest.mark.parametrize("problem", ["valid_sidecar", "invalid_image", "extra_staging", "wrong_slot", "finalized", "existing_attempt", "existing_checkpoint", "canonical_output"])
def test_ineligible_recovery_rejected(tmp_path, offline, monkeypatch, problem):
    run_file, slot, image, sidecar = _incident(tmp_path)
    if problem == "valid_sidecar":
        valid = _sidecar(); valid["opaque_slot_id"] = slot["blind_id"]
        sidecar.write_text(json.dumps(valid))
    elif problem == "invalid_image":
        image.write_bytes(b"not a raster")
    elif problem == "extra_staging":
        image.with_name("extra.json").write_text("{}")
    elif problem == "wrong_slot":
        slot = load_run_plan(run_file)["invocation_order"][1]
    elif problem == "finalized":
        valid = _sidecar(); valid["opaque_slot_id"] = slot["blind_id"]
        sidecar.write_text(json.dumps(valid))
        receipt = _receipt(run_file, slot, image, valid, tmp_path / "receipt.json")
        import_output(run_file, blind_id=slot["blind_id"], image=image, host_metadata=sidecar, receipt=receipt)
    elif problem == "existing_attempt":
        receipt = json.loads((run_file.parent / "packages/generation-inputs/operator-receipt-templates" / f"{slot['blind_id']}.json").read_text())
        from aipf.exp019_host import ATTESTATIONS
        receipt.update(fresh_chat_attestation={key: True for key in ATTESTATIONS},
                       host_returned_output_count=0, output_count=0, outcome="technical_failure")
        operator = tmp_path / "failure.json"; operator.write_text(json.dumps(receipt))
        record_failed_output(run_file, blind_id=slot["blind_id"], error="technical_failure", receipt=operator)
    elif problem == "existing_checkpoint":
        import aipf.exp019_anchor as anchor
        monkeypatch.setattr(anchor, "verify_external", lambda *args, **kwargs: {"checkpoints": [{"private_binding": {"slot_id": slot["blind_id"]}}]})
    else:
        output = run_file.parent / "outputs"; output.mkdir()
        (output / f"{slot['blind_id']}.png").write_bytes(image.read_bytes())
    with pytest.raises((ValueError, OSError)):
        _prepare(run_file, slot)
    assert not (run_file.parent / RECOVERY_DIR).exists()


@pytest.mark.parametrize("conversation,unchanged", [(False, True), (True, False), (False, False)])
def test_prepare_requires_operator_eligibility_attestations(tmp_path, offline, conversation, unchanged):
    run_file, slot, _, _ = _incident(tmp_path)
    with pytest.raises(ValueError, match="attestations"):
        prepare_metadata_recovery(run_file, blind_id=slot["blind_id"],
                                  original_conversation_available=conversation, no_image_change=unchanged)


@pytest.mark.parametrize("field,value", [("reference_image_count", 1), ("requested_output_count", 2),
                                       ("returned_output_count", 2), ("edit_or_regeneration_used", True)])
def test_generation_conflict_cannot_be_erased_by_metadata_replay(tmp_path, offline, field, value):
    run_file, slot, _, sidecar = _incident(tmp_path)
    data = json.loads(sidecar.read_text()); data[field] = value; data[field + "_status"] = "observed"
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="generation conflict requires protocol review"):
        _prepare(run_file, slot)
    assert not (run_file.parent / RECOVERY_DIR).exists() and not offline


@pytest.mark.parametrize("damage", ["query", "forged_manifest", "rejected", "active_sidecar", "image", "another_slot"])
def test_recovery_rejects_mutation_and_wrong_slot(tmp_path, offline, damage):
    run_file, slot, image, sidecar = _incident(tmp_path)
    _prepare(run_file, slot)
    _, _bytes = _response(run_file, slot)
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    if damage in {"query", "forged_manifest"}:
        query = run_file.parent / "packages/generation-inputs/metadata-queries" / f"{slot['blind_id']}.txt"
        query.write_bytes(b"coached query")
        if damage == "forged_manifest":
            manifest_path = query.parent.parent / "manifest.json"
            manifest = json.loads(manifest_path.read_text()); manifest["tasks"][0]["metadata_query_sha256"] = sha256_file(query)
            manifest_path.write_text(json.dumps(manifest))
    elif damage == "rejected":
        (area / "rejected.host-session.json").write_bytes(b"rewritten")
    elif damage == "active_sidecar":
        valid = _sidecar(); valid["opaque_slot_id"] = slot["blind_id"]
        sidecar.write_text(json.dumps(valid))
    elif damage == "image":
        from test_exp019_host_metadata import _image
        image.write_bytes(_image() + b"different image bytes")
    else:
        candidate = area / "incoming/host-session.json"
        payload = json.loads(candidate.read_text()); payload["opaque_slot_id"] = "AAAAAA" if slot["blind_id"] != "AAAAAA" else "BBBBBB"
        candidate.write_text(json.dumps(payload))
        assert stage_metadata_recovery(run_file, blind_id=slot["blind_id"])["status"] == "blocked"
        assert not offline
        return
    with pytest.raises(ValueError):
        stage_metadata_recovery(run_file, blind_id=slot["blind_id"])
    assert not offline


@pytest.mark.parametrize("damage", [{"same_original_conversation": False}, {"same_original_image": False},
    {"no_subsequent_image_generation": False}, {"no_image_modification": False},
    {"exact_query_unchanged": False}, {"no_coaching_or_error_disclosure": False},
    {"first_and_only_recovery_response": False}, {"replayed_query_sha256": "0" * 64}])
def test_execution_attestation_failure_exhausts_recovery(tmp_path, offline, damage):
    run_file, slot, image, sidecar = _incident(tmp_path)
    _prepare(run_file, slot); _response(run_file, slot, attestation_damage=damage)
    original = sidecar.read_bytes(); run_bytes = run_file.read_bytes()
    assert stage_metadata_recovery(run_file, blind_id=slot["blind_id"])["status"] == "blocked"
    assert sidecar.read_bytes() == original and run_file.read_bytes() == run_bytes and not offline
    with pytest.raises(ValueError, match="already consumed"):
        stage_metadata_recovery(run_file, blind_id=slot["blind_id"])


def test_invalid_recovery_retained_without_attempt_or_checkpoint(tmp_path, offline):
    run_file, slot, image, sidecar = _incident(tmp_path)
    _prepare(run_file, slot); _, candidate_bytes = _response(run_file, slot, bad=True)
    original = sidecar.read_bytes(); run_bytes = run_file.read_bytes()
    result = stage_metadata_recovery(run_file, blind_id=slot["blind_id"])
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    assert result["status"] == "blocked" and (area / "response.host-session.json").read_bytes() == candidate_bytes
    assert sidecar.read_bytes() == original and run_file.read_bytes() == run_bytes and not offline
    with pytest.raises(ValueError):
        import_output(run_file, blind_id=slot["blind_id"], image=image, host_metadata=sidecar, receipt=tmp_path / "unused.json")
    with pytest.raises(ValueError, match="cannot consume an image failure"):
        record_failed_output(run_file, blind_id=slot["blind_id"], error="technical_failure", receipt=tmp_path / "unused.json")
    with pytest.raises(ValueError, match="already consumed"):
        stage_metadata_recovery(run_file, blind_id=slot["blind_id"])


def test_manual_staged_rewrite_cannot_bypass_prepared_recovery(tmp_path, offline):
    run_file, slot, image, sidecar = _incident(tmp_path)
    _prepare(run_file, slot)
    valid = _sidecar(); valid["opaque_slot_id"] = slot["blind_id"]
    sidecar.write_text(json.dumps(valid))
    receipt = _receipt(run_file, slot, image, valid, tmp_path / "receipt.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        import_output(run_file, blind_id=slot["blind_id"], image=image, host_metadata=sidecar, receipt=receipt)
    assert not offline and image.exists() and not load_run_plan(run_file)["variants"][0]["outputs"][0]["attempt_events"]


@pytest.mark.parametrize("problem", ["invalid_utf8", "malformed_json"])
def test_unparseable_recovery_response_is_preserved_and_blocks(tmp_path, offline, problem):
    run_file, slot, image, sidecar = _incident(tmp_path)
    _prepare(run_file, slot); _response(run_file, slot)
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    content = b"\xff" if problem == "invalid_utf8" else b"{broken JSON"
    (area / "incoming/host-session.json").write_bytes(content)
    assert stage_metadata_recovery(run_file, blind_id=slot["blind_id"])["status"] == "blocked"
    assert (area / "response.host-session.json").read_bytes() == content
    assert image.exists() and sidecar.exists() and not offline


def test_recovery_rejection_time_is_stable(tmp_path, offline, monkeypatch):
    from datetime import datetime, timedelta, timezone
    import aipf.exp019_metadata_recovery as recovery
    run_file, slot, _, sidecar = _incident(tmp_path)
    future = _sidecar(); future["opaque_slot_id"] = slot["blind_id"]
    future.update(invoked_at_utc=(datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                  invoked_at_utc_status="observed")
    sidecar.write_text(json.dumps(future))
    _prepare(run_file, slot); _response(run_file, slot)
    class LaterClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(timezone.utc) + timedelta(days=4)
    monkeypatch.setattr(recovery, "datetime", LaterClock)
    # The formerly future timestamp must still be judged at the original rejection event.
    assert stage_metadata_recovery(run_file, blind_id=slot["blind_id"])["status"] == "accepted"


def test_recovery_private_query_cannot_be_coached(tmp_path, offline):
    run_file, slot, _, _ = _incident(tmp_path)
    _prepare(run_file, slot); _response(run_file, slot)
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    (area / "recovery-query.txt").write_bytes(b"please correct the previous field")
    with pytest.raises(ValueError, match="query evidence changed"):
        stage_metadata_recovery(run_file, blind_id=slot["blind_id"])
    assert not offline


def test_partial_stage_reservation_blocks_another_response(tmp_path, offline):
    run_file, slot, _, _ = _incident(tmp_path)
    _prepare(run_file, slot); _response(run_file, slot)
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    (area / "response-reserved").mkdir()
    with pytest.raises(ValueError, match="already consumed"):
        stage_metadata_recovery(run_file, blind_id=slot["blind_id"])
    assert not offline


@pytest.mark.parametrize("invalid", [False, True])
def test_recovery_cli_reports_no_attempt_and_blocked_exit(tmp_path, offline, monkeypatch, capsys, invalid):
    import sys
    from aipf.cli import main
    run_file, slot, _, _ = _incident(tmp_path)
    monkeypatch.setattr(sys, "argv", ["aipf", "experiment-metadata-recovery-prepare", str(run_file),
                                     "--blind-id", slot["blind_id"], "--original-conversation-available", "--no-image-change"])
    main(); prepared = json.loads(capsys.readouterr().out)
    assert prepared["attempts_consumed"] == 0 and prepared["amendment_id"] == AMENDMENT_ID
    _response(run_file, slot, bad=invalid)
    monkeypatch.setattr(sys, "argv", ["aipf", "experiment-metadata-recovery-stage", str(run_file), "--blind-id", slot["blind_id"]])
    if invalid:
        with pytest.raises(SystemExit) as caught:
            main()
        assert caught.value.code == 2
    else:
        main()
    result = json.loads(capsys.readouterr().out)
    assert result["attempts_consumed"] == 0 and not result["checkpoint_created"]
    assert result["status"] == ("blocked" if invalid else "accepted")
    assert not offline


def test_successful_recovery_binds_first_attempt_and_remote_privacy(tmp_path, monkeypatch):
    remote = tmp_path / "synthetic.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    monkeypatch.setenv("AIPF_EXP019_PROVENANCE_REMOTE", str(remote))
    run_file, slot, image, sidecar = _incident(tmp_path)
    before = verify_external(run_file, load_run_plan(run_file))
    run_bytes = run_file.read_bytes(); image_bytes = image.read_bytes()
    _prepare(run_file, slot); valid, candidate_bytes = _response(run_file, slot)
    assert stage_metadata_recovery(run_file, blind_id=slot["blind_id"])["status"] == "accepted"
    assert run_file.read_bytes() == run_bytes and image.read_bytes() == image_bytes and sidecar.read_bytes() == candidate_bytes
    assert verify_external(run_file, load_run_plan(run_file)) == before
    with pytest.raises(ValueError, match="already consumed"):
        stage_metadata_recovery(run_file, blind_id=slot["blind_id"])
    receipt = _receipt(run_file, slot, image, valid, tmp_path / "receipt.json")
    result = import_output(run_file, blind_id=slot["blind_id"], image=image, host_metadata=sidecar, receipt=receipt)
    assert result["attempt_number"] == 1
    current = load_run_plan(run_file); _, output = find_slot(current, slot["blind_id"])
    assert [e["event"] for e in output["attempt_events"]] == ["started", "success"]
    assert (run_file.parent / "outputs" / output["image"]).read_bytes() == image_bytes
    record = json.loads((run_file.parent / output["receipt_history"][0]["file"]).read_text())
    assert record["metadata_recovery"]["amendment"] == frozen_amendment()
    assert len(record["metadata_recovery"]["files"]) == 6
    after = verify_external(run_file, current)
    assert len(after["checkpoints"]) == 2 and after["checkpoints"][0] == before["checkpoints"][0]
    assert set(after["checkpoints"][-1]["record"]) == {"schema_version", "run_id", "sequence", "event_type", "evidence_sha256", "previous_anchor_commit"}
    remote_record = subprocess.check_output(["git", f"--git-dir={remote}", "show", f"{after['head_commit']}:checkpoint.json"]).decode()
    for secret in [str(run_file.parent), "metadata_recovery", "generated_file_path", slot["blind_id"], "Do not generate"]:
        assert secret not in remote_record
    with pytest.raises(ValueError):
        _prepare(run_file, slot)
    area = run_file.parent / RECOVERY_DIR / slot["blind_id"]
    (area / "rejected.host-session.json").write_bytes(b"changed after import")
    with pytest.raises(ValueError):
        verify_host_attempts(run_file.parent, current, output, 1)
