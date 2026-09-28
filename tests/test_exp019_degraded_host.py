"""Synthetic narrow admission, integrity, blind review and aggregate export tests."""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aipf.exp019_anchor import verify_external
from aipf.exp019_analysis import analyze_exp019, validate_exp019_result
from aipf.exp019_degraded_host import (
    AMENDMENT_ID, ATTESTATION_SCHEMA, DEGRADED_DIR, STATE, QUALIFICATION,
    degraded_binding, frozen_amendment, import_degraded_host,
    prepare_degraded_host, sanitize_exp019_result,
)
from aipf.exp019_host import verify_host_attempts
from aipf.exp019_host_metadata import load_host_session_metadata
from aipf.exp019_metadata_recovery import RECOVERY_DIR, prepare_metadata_recovery
from aipf.exp019_protocol import find_slot, frozen_protocol
from aipf.experiment_execution import export_host_package, import_output, record_failed_output
from aipf.experiment_review import create_review_package, freeze_review, reveal_review
from aipf.experiment_runs import load_run_plan, sha256_file
from aipf.io import load_json
from test_exp019_execution_infrastructure import _filled_review
from test_exp019_host_metadata import _run, _sidecar, _stage, _receipt
from test_exp019_metadata_recovery import offline


def _json(path, payload):
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _incident(tmp_path):
    run_file = _run(tmp_path)
    export_host_package(run_file)
    slot = load_run_plan(run_file)["invocation_order"][0]
    raw = _sidecar()
    raw.update(generated_file_path="", generated_file_path_status="observed")
    image, sidecar = _stage(run_file, slot, raw)
    attest = tmp_path / "operator-attestations.json"
    _json(attest, {k: slot["blind_id"] if k == "opaque_slot_id" else True
                  for k in load_json(ATTESTATION_SCHEMA)["required"]})
    return run_file, slot, image, sidecar, attest


def _prepare(incident, **kwargs):
    run_file, slot, image, raw, attest = incident
    values = dict(blind_id=slot["blind_id"], expected_image_sha256=sha256_file(image),
                  expected_raw_sha256=sha256_file(raw), attestations=attest, amendment_id=AMENDMENT_ID)
    values.update(kwargs)
    return prepare_degraded_host(run_file, **values)


def _import(incident, prepared, **kwargs):
    run_file, slot, image, raw, _ = incident
    receipt = _receipt(run_file, slot, image, json.loads(raw.read_text()), run_file.parent / "operator.json")
    values = dict(blind_id=slot["blind_id"], image=image, host_metadata=raw, receipt=receipt,
                  wrapper=prepared["wrapper"], amendment_id=AMENDMENT_ID)
    values.update(kwargs)
    return import_degraded_host(run_file, **values)


def test_prepare_immutable_then_attempt_one(tmp_path, offline):
    incident = _incident(tmp_path)
    run_file, slot, image, raw, _ = incident
    before = [p.read_bytes() for p in (run_file, image, raw)]
    prepared = _prepare(incident)
    area = Path(prepared["wrapper"]).parent
    assert prepared["attempts_consumed"] == 0 and not prepared["checkpoint_created"]
    assert not offline
    assert [p.read_bytes() for p in (run_file, image, raw)] == before
    assert (area / "raw.host-session.json").read_bytes() == before[2]
    errors = json.loads((area / "rejection.json").read_text())["validator_failures"]
    assert len(errors) == 2 and all(e["field"] == "generated_file_path" for e in errors)
    wrapper_bytes = Path(prepared["wrapper"]).read_bytes()
    with pytest.raises(ValueError):
        load_host_session_metadata(raw)
    result = _import(incident, prepared)
    assert result["attempt_number"] == 1 and len(offline) == 1
    run = load_run_plan(run_file)
    _, output = find_slot(run, slot["blind_id"])
    assert len(output["attempt_events"]) == 2 and len(output["receipt_history"]) == 1
    assert (run_file.parent / "outputs" / output["image"]).read_bytes() == before[1]
    assert (run_file.parent / output["host_session_metadata"]).read_bytes() == before[2]
    assert Path(prepared["wrapper"]).read_bytes() == wrapper_bytes
    verify_host_attempts(run_file.parent, run, output, slot["position"])
    assert json.loads((area / "finalization.json").read_text())["receipt_sha256"] == output["receipt_history"][0]["sha256"]


@pytest.mark.parametrize("field", [k for k in load_json(ATTESTATION_SCHEMA)["required"] if k != "opaque_slot_id"])
@pytest.mark.parametrize("damage", ["false", "missing"])
def test_truthful_attestations_required(tmp_path, offline, field, damage):
    incident = _incident(tmp_path)
    attest = incident[4]; data = json.loads(attest.read_text())
    if damage == "false": data[field] = False
    else: data.pop(field)
    _json(attest, data)
    with pytest.raises(ValueError): _prepare(incident)
    assert not offline and not (incident[0].parent / DEGRADED_DIR).exists()


@pytest.mark.parametrize("damage", [
    {"generated_file_path": None, "generated_file_path_status": "not_observable"},
    {"generated_file_path": "repaired"}, {"generated_file_path": " "},
    {"generation_id": "", "generation_id_status": "observed"},
    {"generation_id": "unavailable", "generation_id_status": "not_observable"},
    {"reference_image_count": 1}, {"requested_output_count": 2}, {"returned_output_count": 2},
    {"edit_or_regeneration_used": True}, {"host_product": "other"},
    {"invoked_at_utc": "garbled", "invoked_at_utc_status": "observed"},
    {"invoked_at_utc": "2020-01-01T00:00:00Z", "invoked_at_utc_status": "observed"},
    {"generation_completed_at_utc": "not-a-time", "generation_completed_at_utc_status": "observed"},
    {"unknown": True}, {"opaque_slot_id": "WRONG1"},
])
def test_only_exact_defect_and_other_semantic_gates(tmp_path, offline, damage):
    incident = _incident(tmp_path)
    raw = incident[3]; data = json.loads(raw.read_text()); data.update(damage); _json(raw, data)
    with pytest.raises(ValueError): _prepare(incident)
    assert not offline


@pytest.mark.parametrize("problem", ["non_raster", "wrong_image_hash", "wrong_raw_hash", "wrong_slot",
    "finalized", "attempt", "checkpoint", "canonical_file", "alternate_query", "manifest_query",
    "review", "analysis", "recovery_reserved", "missing_authorization", "outcome_attestation"])
def test_admission_boundaries(tmp_path, offline, monkeypatch, problem):
    incident = _incident(tmp_path); run_file, slot, image, raw, attest = incident; values = {}
    run = load_run_plan(run_file); _, output = find_slot(run, slot["blind_id"])
    if problem == "non_raster": image.write_bytes(b"not raster")
    elif problem == "wrong_image_hash": values["expected_image_sha256"] = "0" * 64
    elif problem == "wrong_raw_hash": values["expected_raw_sha256"] = "0" * 64
    elif problem == "wrong_slot": values["blind_id"] = run["invocation_order"][1]["blind_id"]
    elif problem == "finalized": output["status"] = "generated"; _json(run_file, run)
    elif problem == "attempt": output["attempt_events"] = [{"event": "started", "attempt_number": 1}]; _json(run_file, run)
    elif problem == "checkpoint":
        import aipf.exp019_anchor as anchor
        monkeypatch.setattr(anchor, "verify_external", lambda *a, **kw: {"checkpoints":[{"private_binding":{"slot_id":slot["blind_id"]}}]})
    elif problem == "canonical_file":
        path = run_file.parent / "outputs" / (slot["blind_id"] + ".png"); path.parent.mkdir(exist_ok=True); path.write_bytes(b"prior")
    elif problem in {"alternate_query", "manifest_query"}:
        package = run_file.parent / "packages" / "generation-inputs"
        if problem == "alternate_query": (package / "metadata-queries" / f"{slot['blind_id']}.txt").write_bytes(b"coached query")
        else:
            manifest = package / "manifest.json"; data = json.loads(manifest.read_text())
            data["tasks"][0]["metadata_query_sha256"] = "0" * 64; _json(manifest, data)
    elif problem in {"review", "analysis"}: (run_file.parent / (".review-private" if problem == "review" else "analysis-private")).mkdir()
    elif problem == "recovery_reserved": (run_file.parent / RECOVERY_DIR / slot["blind_id"]).mkdir(parents=True)
    elif problem == "missing_authorization": values["amendment_id"] = None
    elif problem == "outcome_attestation":
        data = json.loads(attest.read_text()); data["selection_based_on_scores"] = True; _json(attest, data)
    with pytest.raises((ValueError, OSError, KeyError)): _prepare(incident, **values)
    assert not offline


@pytest.mark.parametrize("target", ["raw.host-session.json", "metadata-query.txt", "attestations.json", "rejection.json",
                                    "active_raw", "active_image", "missing_rejection"])
def test_tampered_preserved_or_active_evidence_rejected(tmp_path, offline, target):
    incident = _incident(tmp_path); prepared = _prepare(incident); area = Path(prepared["wrapper"]).parent
    path = incident[3] if target == "active_raw" else incident[2] if target == "active_image" else area / target
    if target == "missing_rejection": (area / "rejection.json").unlink()
    else: path.write_bytes(path.read_bytes() + (b" " if target == "active_raw" else b"tamper"))
    before = incident[0].read_bytes()
    with pytest.raises((ValueError, FileNotFoundError)): _import(incident, prepared)
    assert not offline and incident[0].read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("host_provenance_state", None), ("source_kind", "host_response"), ("amendment", {}),
    ("raw_sidecar_sha256", "0" * 64), ("image_sha256", "0" * 64), ("query_sha256", "0" * 64),
    ("run_id", "OTHER"), ("slot_id", "WRONG1"), ("prior_attempts", 1),
    ("intended_attempt_receipt", "other.json"), ("scientific_bindings_valid", False),
    ("selected_for_quality", True),
])
def test_wrapper_tampering_rejected(tmp_path, offline, field, value):
    incident = _incident(tmp_path); prepared = _prepare(incident); path = Path(prepared["wrapper"])
    data = json.loads(path.read_text()); data[field] = value; _json(path, data)
    with pytest.raises(ValueError): _import(incident, prepared)
    assert not offline


@pytest.mark.parametrize("problem", ["normal_import", "normal_repaired_import", "missing_auth", "wrong_wrapper",
                                    "repeat_prepare", "metadata_recovery", "image_failure", "repeat_import"])
def test_explicit_exclusive_path(tmp_path, offline, problem):
    incident = _incident(tmp_path); prepared = _prepare(incident)
    run_file, slot, image, raw, _ = incident
    receipt = _receipt(run_file, slot, image, json.loads(raw.read_text()), run_file.parent / "operator.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        if problem.startswith("normal"):
            if problem == "normal_repaired_import":
                data=json.loads(raw.read_text()); data.update(generated_file_path=None,generated_file_path_status="not_observable"); _json(raw,data)
            import_output(run_file, blind_id=slot["blind_id"], image=image,host_metadata=raw,receipt=receipt)
        elif problem == "missing_auth": _import(incident, prepared, amendment_id=None)
        elif problem == "wrong_wrapper": _import(incident, prepared, wrapper=run_file)
        elif problem == "repeat_prepare": _prepare(incident)
        elif problem == "metadata_recovery": prepare_metadata_recovery(run_file, blind_id=slot["blind_id"],original_conversation_available=True,no_image_change=True)
        elif problem == "image_failure": record_failed_output(run_file, blind_id=slot["blind_id"],error="technical_failure",receipt=receipt)
        elif problem == "repeat_import":
            _import(incident, prepared)
            import_degraded_host(run_file, blind_id=slot["blind_id"],image=image,host_metadata=raw,receipt=receipt,wrapper=prepared["wrapper"],amendment_id=AMENDMENT_ID)
    assert len(offline) == (1 if problem == "repeat_import" else 0)


@pytest.fixture(scope="module")
def complete_chain(tmp_path_factory):
    """Production functions against an actual temporary bare remote; no mocked anchors."""
    import os
    tmp = tmp_path_factory.mktemp("degraded-full-chain")
    remote = tmp / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    prior = os.environ.get("AIPF_EXP019_PROVENANCE_REMOTE")
    os.environ["AIPF_EXP019_PROVENANCE_REMOTE"] = str(remote)
    try:
        incident = _incident(tmp); run_file = incident[0]
        prepared = _prepare(incident); _import(incident, prepared)
        initial = load_run_plan(run_file)
        # A second distinct opaque slot demonstrates generic eligibility independent of condition.
        for index, slot in enumerate(initial["invocation_order"][1:], 2):
            raw = _sidecar()
            if index == 5: raw.update(generated_file_path="", generated_file_path_status="observed")
            image, sidecar = _stage(run_file, slot, raw)
            receipt = _receipt(run_file, slot, image, raw, tmp / f"operator-{index}.json")
            if index == 5:
                attest = tmp / "attest-second.json"
                _json(attest, {k:slot["blind_id"] if k == "opaque_slot_id" else True for k in load_json(ATTESTATION_SCHEMA)["required"]})
                prep = _prepare((run_file,slot,image,sidecar,attest))
                import_degraded_host(run_file, blind_id=slot["blind_id"],image=image,host_metadata=sidecar,receipt=receipt,wrapper=prep["wrapper"],amendment_id=AMENDMENT_ID)
            else: import_output(run_file, blind_id=slot["blind_id"],image=image,host_metadata=sidecar,receipt=receipt)
        packages = {}
        for reviewer in ("R1", "R2"):
            package = create_review_package(run_file, reviewer_id=reviewer); packages[reviewer] = package
            for file in (run_file.parent / "blind-review" / reviewer).rglob("*"):
                if file.is_file():
                    content=file.read_bytes()
                    for forbidden in (STATE.encode(), b"generated_file_path", b"raw.host-session", b"conversation_permanently"):
                        assert forbidden not in content
            _filled_review(Path(package["review"]), {"C":3,"A":2,"B":4},run_file.parent / ".review-private" / f"{reviewer}.mapping.json")
            freeze_review(package["review"])
        reveal_review(run_file)
        result = analyze_exp019(run_file, output=run_file.parent / "analysis-private" / "EXP-019.analysis.json")
        public = sanitize_exp019_result(run_file, output=tmp / "sanitized.json")
        yield run_file, result, public, remote
    finally:
        if prior is None: os.environ.pop("AIPF_EXP019_PROVENANCE_REMOTE",None)
        else: os.environ["AIPF_EXP019_PROVENANCE_REMOTE"] = prior


def test_complete_real_remote_chain_review_analysis_and_export(complete_chain):
    run_file, result, public, remote = complete_chain
    state = verify_external(run_file,load_run_plan(run_file), require_reviews=True)
    assert len(state["checkpoints"]) == 15
    assert sum(c["record"]["event_type"] == "attempt" for c in state["checkpoints"]) == 12
    assert result["host_provenance"]["degraded_sample_count"] == 2
    assert result["host_provenance"]["normal_sample_count"] == 10
    assert result["safeguards"]["binding_integrity_valid"] is True
    assert "provenance_valid" not in result["safeguards"]
    assert result["contrasts"]["B-C"]["delta"] == 1 and result["contrasts"]["B-A"]["delta"] == 2
    assert result["evidence_classification"] == public["evidence_classification"] == "supports"
    assert public["host_provenance"]["qualification"] == QUALIFICATION
    assert len(result["samples"]) == 12
    payload=json.dumps(public)
    for secret in (str(run_file.parent), result["run_id"], "reviewer_pseudonym", "generation_id", "receipt_history", "image_sha256"):
        assert secret not in payload
    for slot in load_run_plan(run_file)["invocation_order"]: assert slot["blind_id"] not in payload
    ref=state["ref"]
    commits=subprocess.run(["git","--git-dir",str(remote),"rev-list",ref],capture_output=True,text=True,check=True).stdout.splitlines()
    for commit in commits:
        cp=json.loads(subprocess.run(["git","--git-dir",str(remote),"show",f"{commit}:checkpoint.json"],capture_output=True,text=True,check=True).stdout)
        assert set(cp) == {"schema_version","run_id","sequence","event_type","evidence_sha256","previous_anchor_commit"}


@pytest.mark.parametrize("damage", ["omit_summary", "full_claim", "bad_count", "omit_qualification", "raw_schema_true", "invalid_state"])
def test_degraded_result_cannot_claim_full_or_hide_qualification(complete_chain, damage):
    run_file,result,public,_ = complete_chain; changed=copy.deepcopy(result)
    if damage == "omit_summary": changed.pop("host_provenance")
    elif damage == "full_claim": changed["safeguards"]["provenance_valid"]=True
    elif damage == "bad_count": changed["host_provenance"]["degraded_sample_count"]=0
    elif damage == "omit_qualification": changed["host_provenance"].pop("qualification")
    elif damage == "raw_schema_true": changed["host_provenance"]["raw_sidecar_schema_conformant"]=True
    else: changed["host_provenance"]["state"]="invalid_unadmitted"
    assert list(Draft202012Validator(load_json("data/schemas/exp019_host_result_v1_1_1.schema.json")).iter_errors(changed))


def test_finalization_and_wrapper_tampering_blocks_verification(tmp_path, offline):
    incident=_incident(tmp_path); prepared=_prepare(incident); _import(incident,prepared)
    run=load_run_plan(incident[0]); slot=incident[1]; _,output=find_slot(run,slot["blind_id"])
    path=Path(prepared["wrapper"]).parent / "finalization.json"; data=json.loads(path.read_text()); data["receipt_sha256"]="0"*64; _json(path,data)
    with pytest.raises(ValueError, match="final receipt link"): verify_host_attempts(incident[0].parent,run,output,slot["position"])


def test_missing_marker_cannot_bypass_raw_schema(tmp_path, offline):
    incident=_incident(tmp_path); prepared=_prepare(incident); _import(incident,prepared)
    run=load_run_plan(incident[0]); slot=incident[1]; _,output=find_slot(run,slot["blind_id"])
    binding=output["receipt_history"][0]; path=incident[0].parent / binding["file"]
    data=json.loads(path.read_text()); data.pop("host_provenance_state"); _json(path,data); binding["sha256"]=sha256_file(path)
    with pytest.raises(ValueError): verify_host_attempts(incident[0].parent,run,output,slot["position"])


def test_second_addendum_preserves_first_and_definition():
    from aipf.exp019_metadata_recovery import frozen_amendment as first
    assert frozen_amendment()["id"] == AMENDMENT_ID
    assert first()["sha256"] == "b061e5ab023684df102b029d1ed1c319b0cddf24579c51215030be354730512a"
    assert frozen_protocol("1.1.1")[0]["version"] == "1.1.1"


@pytest.mark.parametrize("damage", [{"prompt_sha256":"0"*64}, {"slot_id":"WRONG1"},
    {"output_sha256":"0"*64}, {"host_returned_output_count":2}, {"output_count":2},
    {"source_kind":"replacement"}, {"metadata_query_attestation":{}},
    {"backend_snapshot":"unbound", "backend_snapshot_status":"observed"}])
def test_operator_scientific_bindings_stay_mandatory(tmp_path,offline,damage):
    incident=_incident(tmp_path); prepared=_prepare(incident); run_file,slot,image,raw,_=incident
    receipt=_receipt(run_file,slot,image,json.loads(raw.read_text()),run_file.parent / "operator.json")
    data=json.loads(receipt.read_text()); data.update(damage); _json(receipt,data)
    before=run_file.read_bytes()
    with pytest.raises(ValueError):
        import_degraded_host(run_file,blind_id=slot["blind_id"],image=image,host_metadata=raw,receipt=receipt,wrapper=prepared["wrapper"],amendment_id=AMENDMENT_ID)
    assert not offline and run_file.read_bytes() == before and image.exists() and raw.exists()


def test_cannot_switch_after_successful_metadata_recovery(tmp_path,offline):
    from test_exp019_metadata_recovery import _response
    from aipf.exp019_metadata_recovery import stage_metadata_recovery
    incident=_incident(tmp_path); run_file,slot,_,_,_=incident
    prepare_metadata_recovery(run_file,blind_id=slot["blind_id"],original_conversation_available=True,no_image_change=True)
    _response(run_file,slot)
    assert stage_metadata_recovery(run_file,blind_id=slot["blind_id"])["status"] == "accepted"
    with pytest.raises(ValueError,match="path switching"): _prepare(incident)
    assert not offline


@pytest.mark.parametrize("where", ["root", "summary", "safeguards", "contrast", "pairwise", "means"])
def test_public_schema_forbids_private_incidental_fields(complete_chain,where):
    _,_,public,_=complete_chain; data=copy.deepcopy(public)
    target={"root":data,"summary":data["host_provenance"],"safeguards":data["safeguards"],
            "contrast":data["contrasts"]["B-C"],"pairwise":data["contrasts"]["B-C"]["pairwise"],
            "means":data["condition_means"]["C"]}[where]
    target["private_path"]="synthetic-secret"
    assert list(Draft202012Validator(load_json("data/schemas/exp019_public_result_v1_1_1.schema.json")).iter_errors(data))


def test_result_recomputation_rejects_plausible_false_count(complete_chain,tmp_path):
    run_file,result,_,_=complete_chain; data=copy.deepcopy(result)
    data["host_provenance"].update(normal_sample_count=11,degraded_sample_count=1)
    path=tmp_path / "result.json"; _json(path,data)
    with pytest.raises(ValueError,match="differs from frozen evidence"): validate_exp019_result(run_file,path)
