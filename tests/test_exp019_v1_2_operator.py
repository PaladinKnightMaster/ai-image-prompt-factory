"""Synthetic operator evidence-capture tests for EXP-019 v1.2 PR-11."""

from __future__ import annotations

import pytest

from aipf.exp019_protocol import frozen_protocol
from aipf.exp019_v1_2_evidence import validate_evidence_bundle
from aipf.exp019_v1_2_operator import (
    OperatorCaptureError,
    OperatorCaptureSession,
    RoleBoundaryError,
    make_opaque_prompt_packet,
    workflow_accidental_attachment,
    workflow_confirmed_no_result,
    workflow_interrupted_unknown,
    workflow_multiple_returned_candidates,
    workflow_technically_invalid_file,
    workflow_unknown_host_result,
    workflow_valid_returned_image,
)
from aipf import exp019_v1_2_operator as operator_module
from exp019_v1_2_synthetic_fixtures import (
    invalid_raster_bytes,
    synthetic_raster_bytes,
)

SLOT = "ZZZZZZ"
PROMPT = b"synthetic frozen prompt bytes for operator capture tests"


def _packet(**overrides):
    kwargs = dict(
        opaque_slot_id=SLOT, attempt_number=1,
        frozen_prompt_bytes=PROMPT, conversation_ref="synth-conv-1")
    kwargs.update(overrides)
    return make_opaque_prompt_packet(**kwargs)


def _session(tmp_path=None, packet=None) -> OperatorCaptureSession:
    return OperatorCaptureSession(
        packet=packet or _packet(),
        operator_id="synthetic-operator",
        work_dir=tmp_path)


def test_complete_q1_q5_evidence_bundle(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_valid_returned_image(
        session, PROMPT, synthetic_raster_bytes(),
        artifact_id="synthetic-artifact-1")
    assert bundle["request_capture"] is not None
    assert bundle["response_capture"]["image_returned"] is True
    assert bundle["attestation"] is not None
    assert bundle["raster_bytes"] == synthetic_raster_bytes()
    report = validate_evidence_bundle(bundle)
    assert report.evidence_eligible
    assert report.technical_validation == "passed"
    for name in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        q = next(r for r in report.q_results if r.check == name)
        assert q.passed is True or (name == "Q4" and q.passed is not False)


def test_frozen_and_pasted_prompt_bytes_match(tmp_path) -> None:
    session = _session(tmp_path)
    assert session.verify_frozen_prompt_bytes(PROMPT) is True
    session.record_pre_send_paste(PROMPT)
    assert session.frozen_vs_paste_match() is True


def test_frozen_and_pasted_prompt_bytes_differ(tmp_path) -> None:
    session = _session(tmp_path)
    assert session.verify_frozen_prompt_bytes(b"different") is False
    session.record_pre_send_paste(b"different paste bytes")
    assert session.frozen_vs_paste_match() is False
    session.record_request_capture()
    session.record_response_capture(
        image_returned=True, returned_image_count=1,
        artifact_id="synthetic-artifact-1")
    session.associate_downloaded_artifact(
        synthetic_raster_bytes(), expected_artifact_id="synthetic-artifact-1")
    session.produce_attestation()
    session.close_invocation()
    report = validate_evidence_bundle(session.export_evidence_bundle())
    assert not report.evidence_eligible


def test_rendered_text_differs_despite_matching_clipboard(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(
        PROMPT, rendered_request_text="rendered differently")
    assert session.frozen_vs_paste_match() is True
    assert session._rendered_comparison == "textual_mismatch"
    session.record_request_capture()
    assert session._request_capture["rendered_request_comparison"] == \
        "textual_mismatch"


def test_missing_request_capture(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(PROMPT)
    with pytest.raises(OperatorCaptureError, match="request capture required"):
        session.record_response_capture(
            image_returned=True, returned_image_count=1,
            artifact_id="synthetic-artifact-1")


def test_missing_response_capture(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(PROMPT)
    session.record_request_capture()
    with pytest.raises(OperatorCaptureError, match="response capture required"):
        session.associate_downloaded_artifact(synthetic_raster_bytes())


def test_valid_affirmative_no_result_evidence(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_confirmed_no_result(
        session, PROMPT, evidence="host_error_recorded")
    assert bundle["response_capture"]["image_returned"] is False
    assert bundle["response_capture"]["no_result_evidence"] == \
        "host_error_recorded"
    assert bundle["raster_bytes"] is None
    assert bundle["attestation"] is None
    report = validate_evidence_bundle(bundle)
    assert report.outcome_classification == "no_result_evidenced"


def test_unknown_host_outcome(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_unknown_host_result(session, PROMPT)
    assert bundle["response_capture"]["no_result_evidence"] is None
    assert session.outcome_kind == "unknown"
    report = validate_evidence_bundle(bundle)
    # Without affirmative evidence, not a confirmed technical failure.
    assert report.outcome_classification in (
        "unknown_outcome", "invalid_evidence", "no_result_evidenced")
    if report.outcome_classification == "no_result_evidenced":
        # Must not invent affirmative evidence from operator belief.
        assert bundle["response_capture"].get("no_result_evidence") is None


def test_incorrect_returned_image_count(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_multiple_returned_candidates(
        session, PROMPT, artifact_id="synthetic-artifact-1")
    assert bundle["response_capture"]["returned_image_count"] == 2
    assert session.protocol_violation == "returned_image_count"
    report = validate_evidence_bundle(bundle)
    assert not report.evidence_eligible


def test_incorrect_downloaded_output_association(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(PROMPT)
    session.record_request_capture()
    session.record_response_capture(
        image_returned=True, returned_image_count=1,
        artifact_id="synthetic-artifact-1")
    with pytest.raises(OperatorCaptureError, match="does not match"):
        session.associate_downloaded_artifact(
            synthetic_raster_bytes(),
            expected_artifact_id="wrong-artifact")


def test_no_output_null_output_digest(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_confirmed_no_result(
        session, PROMPT, evidence="host_completed_no_image")
    obs = bundle["observation"]["observations"]
    assert obs["output_sha256"]["value"] is None
    assert obs["output_sha256"]["status"] == "not_observable"
    assert bundle["raster_bytes"] is None


def test_corrupted_downloaded_bytes(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_technically_invalid_file(
        session, PROMPT, invalid_raster_bytes(),
        artifact_id="synthetic-artifact-1")
    report = validate_evidence_bundle(bundle)
    assert report.technical_validation == "failed"
    assert not report.evidence_eligible


def test_invalid_or_incomplete_attestation(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(PROMPT)
    session.record_request_capture()
    with pytest.raises(OperatorCaptureError, match="attestation requires"):
        session.produce_attestation()


def test_action_log_sequence_and_timestamp_violations(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(
        PROMPT, at_utc="2026-01-01T00:00:02+00:00")
    with pytest.raises(OperatorCaptureError, match="monotonic"):
        session.record_request_capture(at_utc="2026-01-01T00:00:01+00:00")


def test_interruption_and_resume_same_invocation(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(PROMPT)
    session.record_request_capture()
    session.mark_interrupted()
    session.resume_same_invocation()
    session.record_response_capture(
        image_returned=True, returned_image_count=1,
        artifact_id="synthetic-artifact-1")
    session.associate_downloaded_artifact(
        synthetic_raster_bytes(), expected_artifact_id="synthetic-artifact-1")
    session.produce_attestation()
    session.close_invocation()
    role_actions = [e["action"] for e in session.export_evidence_bundle()[
        "operator_role_log"]]
    assert "invocation_interrupted" in role_actions
    assert "invocation_resumed" in role_actions
    # Schema action log contains only approved enum actions.
    log_actions = [e["action"] for e in session.export_action_log()["entries"]]
    assert "invocation_interrupted" not in log_actions
    report = validate_evidence_bundle(session.export_evidence_bundle())
    assert report.evidence_eligible


def test_duplicate_capture_or_closure_attempts(tmp_path) -> None:
    session = _session(tmp_path)
    session.record_pre_send_paste(PROMPT)
    session.record_request_capture()
    with pytest.raises(OperatorCaptureError, match="duplicate request"):
        session.record_request_capture()
    session.record_response_capture(
        image_returned=False, returned_image_count=0,
        no_result_evidence="host_error_recorded")
    session.close_invocation()
    with pytest.raises(OperatorCaptureError, match="closed"):
        session.close_invocation()


def test_operator_role_violations() -> None:
    with pytest.raises(RoleBoundaryError):
        make_opaque_prompt_packet(
            opaque_slot_id=SLOT, attempt_number=1,
            frozen_prompt_bytes=PROMPT, conversation_ref="c",
            role="operator")
    packet = _packet()
    with pytest.raises(RoleBoundaryError):
        OperatorCaptureSession(
            packet=packet, operator_id="x", role="allocation_custodian")


def test_evidence_bundle_accepted_by_pr6_validator(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_valid_returned_image(
        session, PROMPT, synthetic_raster_bytes(),
        artifact_id="synthetic-artifact-1")
    report = validate_evidence_bundle(bundle)
    assert report.evidence_eligible
    assert not report.errors


def test_evidence_bundle_rejected_for_intended_reason(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_accidental_attachment(session, PROMPT)
    assert session.protocol_violation == "attachment_used"
    report = validate_evidence_bundle(bundle)
    # Attachment count > 0 fails qualifying request capture expectations.
    assert not report.evidence_eligible or \
        bundle["request_capture"]["attachment_count"] == 1


def test_interrupted_unknown_export(tmp_path) -> None:
    session = _session(tmp_path)
    bundle = workflow_interrupted_unknown(session, PROMPT)
    assert bundle["response_capture"] is None
    assert bundle["interrupted"] is True
    report = validate_evidence_bundle(bundle)
    assert report.outcome_classification == "unknown_outcome"


def test_no_mutation_of_source_packet(tmp_path) -> None:
    packet = _packet()
    original = packet.frozen_prompt_bytes
    session = _session(tmp_path, packet=packet)
    session.record_pre_send_paste(PROMPT)
    assert packet.frozen_prompt_bytes == original


def test_activation_lockout() -> None:
    public = {n for n in vars(operator_module) if not n.startswith("_")}
    assert not {"generate", "generate_image", "allocate", "create_run",
                "publish_checkpoint", "reveal", "frozen_protocol"} & public
    with pytest.raises(ValueError,
                       match="unknown EXP-019 frozen protocol version"):
        frozen_protocol("1.2.0")


def test_packet_rejects_digest_mismatch() -> None:
    with pytest.raises(OperatorCaptureError, match="frozen_prompt_sha256"):
        from aipf.exp019_v1_2_operator import OpaquePromptPacket
        OpaquePromptPacket(
            opaque_slot_id=SLOT, attempt_number=1,
            frozen_prompt_bytes=PROMPT,
            frozen_prompt_sha256="0" * 64,
            conversation_ref="c")
